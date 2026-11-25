---
phase: 40-resilient-review-sized-by-jev
plan: 05
subsystem: ai-kit-spec-review (blocked-pool decisions in ping-lanes and Step 0.7 probe-quota)
tags: [review, lanes, quota, pool, blocked-until, ping]
requires: [40-04]
provides:
  - "lane_switch.py: quota_entry(now_s, detail), pool_status(lane, now_s, reader) -> blocked / expired / none, pool_keys(lanes), pool_decisions(lanes, order, now_s, reader) -> blocked / expired-retry / expired-wait / none (one functools.cache read per pool); pool_blocked delegates to pool_status; blocked_cache_entries built on pool_decisions; blocked_until and blocked_reader take timeout_s"
  - "lane_ping.py: PingSeams.read_fn / decisions / started, _lane, _read_pools (one concurrent read per pool before the workers; an unfinished or raising read is absent), _budget_s; _ping_one returns the quota entry without a probe for blocked / expired-wait and gives the probe min(timeout_s, int(remaining)); cmd_ping_lanes passes role=review and the blocked reader with the ping timeout"
  - "cli.py: _cmd_probe_quota blocked-pool pre-pass for --role review only"
affects: [40-09, 40-10]
key-files:
  created: []
  modified:
    - skills/ai-kit-spec-review/ai_kit_spec/lane_switch.py
    - skills/ai-kit-spec-review/ai_kit_spec/lane_ping.py
    - skills/ai-kit-spec-review/ai_kit_spec/cli.py
    - tests/test_lane_switch.py
    - tests/test_lane_ping.py
    - tests/test_role_orders.py
decisions:
  - "The owner confirmed D-05 on 2026-11-25: no PROVISIONAL label in this plan's code, comments, docstrings, tests or commit messages (plan text, SPEC and CONTEXT amended in 1f3cdcf before the lanes)"
  - "The decision lanes of ping-lanes follow reviewers.json row order (dict.fromkeys over run.reviewers), not the reversed key map of _statuses, so the first row of an expired pool takes the retry"
metrics:
  tasks: 2
  commits: 2
---

# Phase 40 Plan 05: blocked-pool decisions Summary

`ping-lanes` now reads each distinct pool of its flagged pooled original lanes once, all pools concurrently, before any probe
worker starts, and passes a per-key decision into the workers: a `blocked` or `expired-wait` lane gets the unavailable `quota`
entry with no probe and goes through the normal replacement path; the first lane of an expired pool (row order) is probed once;
`none` keeps the round cadence. The reads and the originals' probes share one `timeout_s` budget from the start of the reads (a
probe gets the remaining whole seconds; under one second is `ping_timeout` with no probe); candidates keep their own full budget.
With no flagged pooled lane nothing is read and plan 40-02's path is unchanged. Step 0.7 `probe-quota --role review` runs the same
decisions as a pre-pass before `refresh_quota_cache`: blocked and waiting lanes get the `quota` entry, the retry lane loses any
cached entry, a cleared record drops only a cached `quota` failure, and unflagged lanes are never touched; execute and both run
no pre-pass. `ping-lanes` probes run with `role="review"`, so a flagged pooled runtime lane passes `--pool`.

## Commits

| Task | Commit | Subject |
|------|--------|---------|
| 1 | d5b93e0 | feat(40-05): decide blocked pools once before the ping workers |
| 2 | efaf793 | feat(40-05): skip blocked pools in the Step 0.7 quota walk |

Cross-AI lanes (pi, router-env/my-coding), one per task from the start, each AIKIT-XAI `status=ok attempts=1`: Task 1 258 s,
Task 2 201 s. No fix-up lane was needed; the plan's overrun rule (Task 3) was not used.

## Verification (chunk executor, own runs)

- Task 1 acceptance: `read_fn` 3, the four `def` lines 4, `_read_pools` 1, `role="review"` 1, no reader or flag literal in
  lane_ping.py (rg exit 1), no `PING_REUSE_S` (exit 1), the eight named ping tests 8, the two named lane_switch tests 2, subject ok.
- Task 2 acceptance: `lane_switch.blocked_cache_entries` in cli.py 1, no reader or flag literal in cli.py (exit 1),
  `functools.cache(reader)` 1, `pool_decisions(lanes, ladder, now_s, reader)` 1, `class TestProbeQuotaBlockedPool` 1, subject ok.
- No `PROVISIONAL` in any added line; `--blocked-status` typed only in lane_switch.py; no line over 100 characters;
  `tests/fixtures/no_hardcoded_models_baseline.json` unchanged; no new test spawns node (fake `which_fn` and exact fake `run_fn`,
  with `unexpected == []` and exact read counts asserted).
- `tests.test_lane_ping` 31, `tests.test_lane_switch` 26, `tests.test_role_orders` 29, `tests.test_lane_settings` 50,
  `tests.test_ai_kit_spec` 703, `tests.test_ai_kit_spec_runner_dispatch` 80, `tests.test_runner_flags` 24, `tests.test_arch` 118,
  `tests.test_arch_hardcoded_models` 23: all ok.
- Gates after the plan: unit + arch groups under the watchdog `196/196 modules passed` (peak 8 runner processes, not killed);
  `make ruff`, `make pyright`, `make vulture`, `make pylint`, `make check-dogfood` exit 0 each; the commit-deferred
  `tests.test_ai_kit_gsd_curated_config_matrix` 35 tests ok (151.7 s, under the watchdog, peak 0).

## Deviations

- Owner decision applied: D-05 confirmed, so the plan's PROVISIONAL truths, docstring prefixes, comments and ` (provisional)`
  commit suffixes were not written (plan text cleaned in 1f3cdcf). Plan 40-03's free-pool `PROVISIONAL` label in
  tests/test_lane_switch.py stays as written there.
- Task 1 (anchor fix given to the lane): `_statuses` keys its rows map from `reversed(run.reviewers)`; the decision order is
  taken from the reviewers.json rows instead, as the plan's E7 intends.
- Task 1 (lane): the budget arithmetic sits in `_budget_s` (allowed by the plan); `_ping_one` also keeps `begin` for the final
  deadline check. `test_blocked_flagged_lane_is_replaced_without_a_probe` also asserts `lane_switch.pool_keys(...)`.
  `TestPingBlockedPoolCli` inherits `TestPingLanes`, so its three tests run twice (as the plan specified).
