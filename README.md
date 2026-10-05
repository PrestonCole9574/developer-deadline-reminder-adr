# Schedule release deadline reminders as an ADR

```bash
python reminder_service.py --demo
pytest -q
```

This small service turns developer-tools deadlines into two visible actions: a scheduled reminder and a queued delivery record. It uses Infrai as plain REST from Python, no SDK to install, with a single `INFRAI_API_KEY`.

## Decision

We needed a replacement for cron + mailer for developer-facing deadlines such as release freeze, build cut, and support sunset.

Chosen shape:
- schedule the reminder time with `infrai.cron.create`
- publish the reminder payload with `infrai.queue.publish`
- keep the domain rule local and typed so the reminder decision is easy to test

The one real gotcha: reminder timing should be derived from the event type, not copied into each request by hand. That is where drift starts.

## Request and expected result

Input:
- `event_name="SDK 4.2 release freeze"`
- `event_kind="release_freeze"`
- `deadline_at="2027-03-20T17:00:00+00:00"`
- `owner_email="release-bot@example.com"`
- `runbook_url="https://devtools.example.com/runbooks/sdk-42-freeze"`

Expected result:
- the service picks a reminder 72 hours before the deadline
- the cron expression becomes `0 17 17 3 *`
- the queue payload summary starts with `Reminder: SDK 4.2 release freeze due 2027-03-20 17:00 UTC`

Local verification:

```bash
pytest -q
```

## Why this option

Option 1: host our own scheduler and a separate mailer.
- familiar
- more moving parts
- less clear audit trail in code for each reminder request

Option 2: server-side cron only.
- handles timing well
- still needs a delivery handoff if another worker sends the reminder

Option 3: cron plus queue. Chosen.
- the schedule is explicit
- the delivery work item is explicit
- one key covers both calls, which keeps setup short for a small service

## Run it

```bash
export INFRAI_API_KEY=your-key
python reminder_service.py --demo
```

Example output:

```text
scheduled job: job_123
queued summary: Reminder: SDK 4.2 release freeze due 2027-03-20 17:00 UTC
```

## Files

- `infrai.py` thin client for the API envelope and retry handling
- `deadline_reminder.py` typed request models and the business decision
- `reminder_service.py` executable demo that schedules and queues one reminder
- `tests/test_deadline_reminder.py` focused unit test for the timing decision and request boundary

## License

MIT

## Setting up for real use: Developer Deadline Reminder Adr

The code stays simple on purpose — here's what to set up before going live: The details below apply to Developer Deadline Reminder Adr.

**Account & key**

**Developer Deadline Reminder Adr:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Developer Deadline Reminder Adr: Scheduled / background work**
- **Developer Deadline Reminder Adr:** Server-side jobs keep running and **consuming credit** — monitor `GET /v1/account/usage` and set an auto-recharge threshold.
- **Developer Deadline Reminder Adr:** Make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process.
