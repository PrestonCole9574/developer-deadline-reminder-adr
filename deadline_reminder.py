from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import uuid5, NAMESPACE_URL

import infrai

EventKind = Literal["build_cut", "release_freeze", "support_sunset"]


@dataclass(frozen=True)
class DeadlineRequest:
    event_name: str
    event_kind: EventKind
    deadline_at: datetime
    owner_email: str
    runbook_url: str

    def normalized(self) -> "DeadlineRequest":
        if self.deadline_at.tzinfo is None:
            raise ValueError("deadline_at must be timezone-aware")
        return DeadlineRequest(
            event_name=self.event_name.strip(),
            event_kind=self.event_kind,
            deadline_at=self.deadline_at.astimezone(timezone.utc),
            owner_email=self.owner_email.strip().lower(),
            runbook_url=self.runbook_url.strip(),
        )


@dataclass(frozen=True)
class ReminderPlan:
    reminder_at: datetime
    cron_expr: str
    summary: str
    task_url: str
    idempotency_key: str
    payload: dict


OFFSET_HOURS = {
    "build_cut": 24,
    "release_freeze": 72,
    "support_sunset": 168,
}


def _to_cron_expr(when: datetime) -> str:
    return f"{when.minute} {when.hour} {when.day} {when.month} *"


def build_reminder_plan(request: DeadlineRequest, task_url: str) -> ReminderPlan:
    item = request.normalized()
    offset_hours = OFFSET_HOURS[item.event_kind]
    reminder_at = item.deadline_at - timedelta(hours=offset_hours)
    summary = (
        f"Reminder: {item.event_name} due "
        f"{item.deadline_at.strftime('%Y-%m-%d %H:%M UTC')}"
    )
    stable_key = str(
        uuid5(
            NAMESPACE_URL,
            f"{item.event_name}|{item.event_kind}|{item.deadline_at.isoformat()}|{item.owner_email}",
        )
    )
    payload = {
        "event_name": item.event_name,
        "event_kind": item.event_kind,
        "deadline_at": item.deadline_at.isoformat(),
        "owner_email": item.owner_email,
        "runbook_url": item.runbook_url,
        "summary": summary,
    }
    return ReminderPlan(
        reminder_at=reminder_at,
        cron_expr=_to_cron_expr(reminder_at),
        summary=summary,
        task_url=task_url,
        idempotency_key=stable_key,
        payload=payload,
    )


def schedule_deadline_reminder(request: DeadlineRequest, task_url: str) -> dict:
    plan = build_reminder_plan(request, task_url)
    cron_result = infrai.cron.create(
        cron_expr=plan.cron_expr,
        task=plan.task_url,
        idempotency_key=f"cron:{plan.idempotency_key}",
    )
    infrai.queue.publish(
        queue="deadline-reminders",
        payload=plan.payload,
        idempotency_key=f"queue:{plan.idempotency_key}",
    )
    return {
        "job_id": cron_result.get("job_id"),
        "summary": plan.summary,
        "reminder_at": plan.reminder_at.isoformat(),
        "cron_expr": plan.cron_expr,
    }
