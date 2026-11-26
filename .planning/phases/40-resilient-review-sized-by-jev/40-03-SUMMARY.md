---
phase: 40-resilient-review-sized-by-jev
plan: 03
subsystem: ai-kit-spec-review (flagged-lane switch, dispatch round log)
tags: [review, lanes, quota, switch, resume]
requires: [40-02]
provides:
  - "ai_kit_spec/lane_switch.py: flagged_replacement (only reason quota on a usage_limited lane, through lane_usage_limit and next_lane), _refusal (no record, a state, lane changed), switch-lane subcommand (one writer at a time, read-only config with migrate=False)"
  - "cli.py: dispatch-reviewer --lane-log/--round; _record_dispatch_failure (refusal, malformed entry, failed result) and _record_dispatch_success (a successful dispatch appends chosen and supersedes an earlier failed attempt of the same round)"
affects: [40-04, 40-05, 40-09]
key-files:
  created:
    - tests/test_lane_switch.py
  modified:
    - skills/ai-kit-spec-review/ai_kit_spec/lane_switch.py
    - skills/ai-kit-spec-review/ai_kit_spec/cli.py
    - tests/test_lane_settings.py
    - Makefile
    - .pre-commit-config.yaml
decisions:
  - "lane_switch.py may call two lane readers (ALLOWED_READERS: lane_fallback, lane_usage_limit); a planted lane_usage_limit call outside that allowance is still caught"
metrics:
  tasks: 2
  commits: 2
---

# Phase 40 Plan 03: flagged-lane switch Summary

`dispatch-reviewer --lane-log <file> --round <N>` records every dispatch that fails (a refusal or a malformed entry as
`configuration`, a failed result with its own reason, the `--stdout-only` production path included) and, on success, a `chosen`
event, so a lane whose first attempt failed and whose one-shot resume succeeds is judged by the merge. `switch-lane --cwd
--reviewers-json --index --lane-log --round` switches only a lane the owner flagged `usage_limited` whose last round event is
`failed` / `quota`, to the first eligible lane of the owner's review order (rows already in reviewers.json and lanes already
failed or replaced are excluded), writes the replacement row at the same index atomically and logs `replaced` (cause `quota`)
plus `chosen`; every other case prints `not switched <key>: <reason or state>` (exit 1, no file change). `--round` below 1 or
`--index` below 0 exit 2; a row whose runtime, model or command no longer matches the config lane is `lane changed`.

## Commits

| Task | Commit | Subject |
|------|--------|---------|
| 1 | c6ae774 | feat(40-03): switch a usage_limited lane that hit quota to its fallback |
| 2 | f986e48 | feat(40-03): supersede a failed attempt on a successful dispatch and pin that only a flagged lane on quota switches |

Cross-AI lanes (pi, router-env/my-coding), one per task from the start, each AIKIT-XAI `status=ok attempts=1`: Task 1 439 s,
Task 2 263 s. No fix-up lane was needed.

## Verification (chunk executor, own runs)

- Task 1 acceptance: lane_switch functions 3, `lane_usage_limit` 1, `_record_dispatch_failure` 4, `test_lane_switch` in Makefile
  1, the `ALLOWED_READERS` pair 1, `--stdout-only` in the test 1 (2 after Task 2), `migrate=False` 1.
- Task 2 acceptance: `tests/test_lane_switch.py` 19 tests, `def _record_dispatch_success` 1, `class TestFlaggedReplacement` 1,
  no `window_exceeded`. Red proof (lane-made, before the cli.py edit, saved in the run's scratch `p40-03/red.log`):
  `=== tests.test_lane_switch: FAILED (rc=1) in 0.3s  Ran 19 tests in 0.169s` and
  `FAIL: test_resumed_lane_after_a_failed_attempt_is_judged (tests.test_lane_switch.TestFlaggedSwitch.test_resumed_lane_after_a_failed_attempt_is_judged)`
  (`AssertionError: 'failed' != 'chosen'`); green after the edit.
- `tests.test_lane_switch` 19 ok, `tests.test_lane_settings` 49 ok, `tests.test_gate_scope` 62 ok, `tests.test_ai_kit_spec` 703
  ok, `tests.test_lane_ping` 20 ok, `tests.test_arch` 118 ok, `tests.test_arch_hardcoded_models` 23 ok;
  `tests/fixtures/no_hardcoded_models_baseline.json` unchanged; test model literals only `placeholder-model-<n>`.
- Gates after the plan: unit + arch groups under the watchdog `196/196 modules passed` (peak 8 runner processes, not killed);
  `make ruff`, `make pyright`, `make vulture`, `make pylint`, `make check-dogfood` exit 0 each; the commit-deferred
  `tests.test_ai_kit_gsd_curated_config_matrix` 35 tests ok (150.5 s, under the watchdog, peak 0).

## Deviations

- Task 1: the post-dispatch check reads `result.get("reason")` instead of `result["reason"]`, because an existing dispatch test
  fake returns a result without a `reason` key; behaviour is the same for every real result.
- Task 1: `cmd_switch_lane` implements one order (round/index check, rows and index, round states, read-only config,
  `_refusal`, routes and exclude, `flagged_replacement`), the plan's `_refusal` route; the plan's inline `no record` / state
  checks are inside `_refusal`, not repeated.
- Open from the plan's review (unchanged): a refused switch may still run read-only route discovery; a prompt-read or
  `--timeout-tiers` parse failure exits before the logged path, so the log keeps the earlier attempt's reason.
