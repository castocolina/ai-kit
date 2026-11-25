---
phase: 40-resilient-review-sized-by-jev
plan: 02
subsystem: ai-kit-spec-review (pre-round ping, lane selection)
tags: [review, ping, lanes, quota, timeout]
requires: [40-01]
provides:
  - "ai_kit_spec/lane_switch.py: next_lane (owner's review order only, dispatchable route), replacement_row, write_rows (atomic), review_routes"
  - "ai_kit_spec/lane_ping.py: ping-lanes subcommand; concurrent probes, replacement of a blocked lane, round-log events, quota cache write-back, exit 3 on zero lanes"
  - "quota.ProbeSeams.timeout_s (default 30) reaching both the runner spec and the custom launcher tier; ping-lanes --timeout"
affects: [40-03, 40-04, 40-05, 40-09, 40-12]
key-files:
  created:
    - skills/ai-kit-spec-review/ai_kit_spec/lane_switch.py
    - skills/ai-kit-spec-review/ai_kit_spec/lane_ping.py
    - tests/test_lane_ping.py
  modified:
    - skills/ai-kit-spec-review/ai_kit_spec/cli.py
    - skills/ai-kit-spec-review/ai_kit_spec/quota.py
    - tests/test_lane_settings.py
    - Makefile
    - .pre-commit-config.yaml
decisions:
  - "The lane-reader guard is a per-module allowlist (ALLOWED_READERS: runner_dispatch.py -> lane_escalation, lane_switch.py -> lane_fallback); lane_ping.py and every other module stay reader-free"
metrics:
  tasks: 3
  commits: 3
---

# Phase 40 Plan 02: pre-round ping Summary

`ping-lanes --cwd --reviewers-json --lane-log --round --quota-path [--timeout]` probes every chosen non-native lane at once (one
thread pool, results matched by key, identical keys pinged once), replaces a blocked lane with the next selectable lane of the
owner's review order (`lane_switch.next_lane`; a key outside the order, such as a judge lane, is recorded `failed` and never
replaced; a rejected candidate gets its own `failed` event), writes the replacement into the blocked row's slot of reviewers.json
atomically, records `chosen`/`replaced`/`failed` events in the round log, writes every probe into the quota cache without reading
the cache as proof of a ping, skips in round N > 1 only a lane judged in round N-1 within `QUOTA_TTL_SECONDS` (`fresh`), and stops
with exit 3, a stop event and `ai-kit-spec: no lane left: ...` on stderr when no lane is left (reviewers.json unchanged). Each
probe gets its own timeout (`ProbeSeams.timeout_s`, default 30 s); a probe at or past its deadline, or with the probe reason
`timeout`, is `ping_timeout`; a named probe exception fails only its lane with `real_error`.

## Commits

| Task | Commit | Subject |
|------|--------|---------|
| 1 | 604df64 | feat(40-02): ping every chosen lane before a round and replace a blocked one |
| 2 | 735d614 | feat(40-02): give each ping its own timeout and record ping_timeout |
| 3 | 456d32b | test(40-02): pin ping cadence, round-1 probing, dedup and the judge-style file |

Cross-AI lanes (pi, router-env/my-coding), one per task from the start, each AIKIT-XAI `status=ok attempts=1`: Task 1 511 s,
Task 2 239 s, Task 3 123 s. No fix-up lane was needed.

## Verification (chunk executor, own runs)

- Task 1 acceptance: lane_switch functions 4, lane_ping functions 3, `lane_ping` in cli.py 3, `test_lane_ping` in Makefile 1,
  `ALLOWED_READERS` 1, `allow_escalation` gone; no flag literal and no new-reason literal in lane_switch.py or lane_ping.py.
- Task 2 acceptance: `timeout_s: int = 30` 1, the `resolved.extra, 30, cwd=cwd` literal gone, the named exception tuple 2,
  `"--timeout"` 1.
- Task 3 acceptance: `tests/test_lane_ping.py` 20 tests, `class TestPingCadence` 1, no `REUSE`; lane_ping.py unchanged by Task 3.
- `tests.test_lane_ping` 20 ok, `tests.test_lane_settings` 49 ok, `tests.test_ai_kit_spec` 703 ok,
  `tests.test_ai_kit_spec_runner_dispatch` 80 ok, `tests.test_role_orders` 24 ok, `tests.test_gate_scope` 62 ok,
  `tests.test_arch` 118 ok, `tests.test_arch_hardcoded_models` 23 ok; `tests/fixtures/no_hardcoded_models_baseline.json`
  unchanged; test model literals only `placeholder-model-<n>` and `fake/placeholder-model-1`.
- Gates after the plan: unit + arch groups under the watchdog `195/195 modules passed` (peak 9 runner processes, not killed);
  `make ruff`, `make pyright`, `make vulture`, `make pylint`, `make check-dogfood` exit 0 each; the commit-deferred
  `tests.test_ai_kit_gsd_curated_config_matrix` 35 tests ok (149.4 s, under the watchdog).

## Deviations

- Task 1: the lane wrapped the plan's one-line docstrings and split helpers (`_event`, `_failure`) to meet ruff line length and the
  pylint caps; behaviour as the plan states.
- Task 2: `_positive_int` also turns a non-integer text into the same argparse error (the plan names only values below 1).
