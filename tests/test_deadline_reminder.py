from datetime import datetime, timezone

import deadline_reminder
from deadline_reminder import DeadlineRequest, build_reminder_plan, schedule_deadline_reminder


class StubCron:
    def __init__(self) -> None:
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return {"job_id": "job_123"}


class StubQueue:
    def __init__(self) -> None:
        self.calls = []

    def publish(self, **kwargs):
        self.calls.append(kwargs)
        return {"published": True}


def sample_request() -> DeadlineRequest:
    return DeadlineRequest(
        event_name="SDK 4.2 release freeze",
        event_kind="release_freeze",
        deadline_at=datetime(2027, 3, 20, 17, 0, tzinfo=timezone.utc),
        owner_email="release-bot@example.com",
        runbook_url="https://devtools.example.com/runbooks/sdk-42-freeze",
    )


def test_build_reminder_plan_uses_release_freeze_offset() -> None:
    plan = build_reminder_plan(sample_request(), "https://devtools.example.com/hooks/deadline-reminder")
    assert plan.reminder_at == datetime(2027, 3, 17, 17, 0, tzinfo=timezone.utc)
    assert plan.cron_expr == "0 17 17 3 *"
    assert plan.summary == "Reminder: SDK 4.2 release freeze due 2027-03-20 17:00 UTC"


def test_schedule_deadline_reminder_calls_cron_and_queue(monkeypatch) -> None:
    stub_cron = StubCron()
    stub_queue = StubQueue()
    monkeypatch.setattr(deadline_reminder.infrai, "cron", stub_cron)
    monkeypatch.setattr(deadline_reminder.infrai, "queue", stub_queue)

    result = schedule_deadline_reminder(
        sample_request(),
        "https://devtools.example.com/hooks/deadline-reminder",
    )

    assert result == {
        "job_id": "job_123",
        "summary": "Reminder: SDK 4.2 release freeze due 2027-03-20 17:00 UTC",
        "reminder_at": "2027-03-17T17:00:00+00:00",
        "cron_expr": "0 17 17 3 *",
    }
    assert stub_cron.calls == [
        {
            "cron_expr": "0 17 17 3 *",
            "task": "https://devtools.example.com/hooks/deadline-reminder",
            "idempotency_key": f"cron:{build_reminder_plan(sample_request(), 'https://devtools.example.com/hooks/deadline-reminder').idempotency_key}",
        }
    ]
    assert stub_queue.calls == [
        {
            "queue": "deadline-reminders",
            "payload": {
                "event_name": "SDK 4.2 release freeze",
                "event_kind": "release_freeze",
                "deadline_at": "2027-03-20T17:00:00+00:00",
                "owner_email": "release-bot@example.com",
                "runbook_url": "https://devtools.example.com/runbooks/sdk-42-freeze",
                "summary": "Reminder: SDK 4.2 release freeze due 2027-03-20 17:00 UTC",
            },
            "idempotency_key": f"queue:{build_reminder_plan(sample_request(), 'https://devtools.example.com/hooks/deadline-reminder').idempotency_key}",
        }
    ]
