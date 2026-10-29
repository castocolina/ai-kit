---
spike: 004
idea: session-self-resume
name: cron-and-limit-evidence
type: standard
validates: "Given an in-session recurring CronCreate, when it fires during a usage limit, then it either runs later or is lost"
verdict: VALIDATED
related: [001, 002]
tags: [claude-code, cronCreate, usage-limit, goal]
---

# Spike 004: CronCreate and /goal across a usage limit (transcript evidence)

## What This Validates
Given an hourly in-session `CronCreate` prompt, when it fires while the session's usage limit is
exhausted, then the fire is consumed by the limit error and is not replayed after the reset.

## Research
No safe way exists to exhaust the owner's quota on purpose, so the evidence is this run's own
Claude Code session transcript (2026-10-14 to 2026-10-25, Claude Code 2.1.299 in the session),
which carried an hourly "Quota-resume check" CronCreate through many real session and weekly
limits. `mine_transcript.py` lists every fire and the reply that followed.

## How to Run
`python3 .planning/spikes/004-cron-and-limit-evidence/mine_transcript.py <session.jsonl>`

## Investigation Trail
- Every fire inside a limit window is delivered on schedule (within about 1 s of :21/:33) and the
  turn ends at once with the limit line, e.g. `You've hit your session limit · resets 1pm
  (America/Santiago)`; on 2026-10-19..21 a weekly limit produced 56 consecutive such fires.
- No fire is replayed after the reset: the first working turn is the next scheduled fire after the
  reset time. A fire is lost, not deferred.
- The recurring job stopped after 2026-10-21T16:21Z, exactly 7 days after it was created
  (2026-10-14T16:21Z), matching the documented 7-day expiry; it was re-created on 2026-10-23.
- `/goal` pauses on a limit with `Goal paused · usage limit reached · send a message after it
  resets to continue`: it does not resume by itself; a message (a cron fire after the reset, or the
  owner) continues it.
- Reset-text grammar seen (D-37 input): `resets 12:30am (America/Santiago)`, `resets 4:50pm (...)`,
  `resets 1pm (...)`, `resets 3am (...)` when the reset is within the day, and
  `resets Oct 22, 10pm (America/Santiago)` for a later date (weekly limit). Minutes are omitted on
  the hour; the zone is always the parenthesized IANA name.
- Background-task notifications that arrive during a limit also produce an immediate limit reply.

## Results
VALIDATED from real evidence. An in-session CronCreate fire during a usage limit is lost (consumed
by the limit reply), never queued; only the next fire after the reset does work. A wake that must
land after a known reset therefore needs a one-shot at the reset time (plus margin) or an OS timer;
an hourly in-session chain works only because some later fire falls after the reset. The headless
`claude -p` exit code during a limit is still unverified (no safe way to induce it).
