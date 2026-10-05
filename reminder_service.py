from __future__ import annotations

import argparse
from datetime import datetime

from deadline_reminder import DeadlineRequest, schedule_deadline_reminder

DEFAULT_TASK_URL = "https://devtools.example.com/hooks/deadline-reminder"


def demo_request() -> DeadlineRequest:
    return DeadlineRequest(
        event_name="SDK 4.2 release freeze",
        event_kind="release_freeze",
        deadline_at=datetime.fromisoformat("2027-03-20T17:00:00+00:00"),
        owner_email="release-bot@example.com",
        runbook_url="https://devtools.example.com/runbooks/sdk-42-freeze",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Schedule a developer deadline reminder")
    parser.add_argument("--demo", action="store_true", help="schedule the built-in example")
    args = parser.parse_args()

    if not args.demo:
        parser.error("use --demo")

    result = schedule_deadline_reminder(demo_request(), DEFAULT_TASK_URL)
    print(f"scheduled job: {result['job_id']}")
    print(f"queued summary: {result['summary']}")


if __name__ == "__main__":
    main()
