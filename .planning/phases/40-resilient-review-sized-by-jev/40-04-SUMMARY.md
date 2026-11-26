---
phase: 40-resilient-review-sized-by-jev
plan: 04
subsystem: ai-kit-spec-review (blocked-until read, --pool on review runs)
tags: [review, lanes, quota, pool, blocked-until]
requires: [40-03]
provides:
  - "lane_settings.lane_pool(entry): the pool of a usage_limited lane whose pool fullmatches POOL_RX, else None (also on a non-boolean flag)"
  - "lane_switch.py: _parse_status, blocked_until (cross-ai.mjs --blocked-status <pool> through detection.bounded_run; every failure reads None), pool_blocked (equal time counts as passed), blocked_reader(deps), blocked_cache_entries (still-blocked pool -> unavailable quota entry stamped now; passed block drops a cached quota failure)"
  - "runner_dispatch.RunnerSpec.pool and --pool after every runner_flags flag; quota.ProbeSeams.role (default '', only 'review' passes a pool); probe-quota passes --role into the seams; dispatch_reviewer sets the pool"
affects: [40-05, 40-09]
key-files:
  created: []
  modified:
    - skills/ai-kit-spec-review/ai_kit_spec/lane_switch.py
    - skills/ai-kit-spec-review/ai_kit_spec/lane_settings.py
    - skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py
    - skills/ai-kit-spec-review/ai_kit_spec/reviewer_dispatch.py
    - skills/ai-kit-spec-review/ai_kit_spec/quota.py
    - skills/ai-kit-spec-review/ai_kit_spec/cli.py
    - tests/test_lane_switch.py
    - tests/test_lane_settings.py
    - tests/test_runner_flags.py
decisions:
  - "The owner confirmed the blocked-until reading (read only through cross-ai.mjs --blocked-status; a missing runner or a bad record never blocks a lane): the plan's PROVISIONAL labels, docstring prefixes and '(provisional)' commit suffixes were not written"
  - "review_spec keeps five parameters (pylint max-args 5); the two review callers set the pool with review_spec(...)._replace(pool=...)"
metrics:
  tasks: 3
  commits: 3
---

# Phase 40 Plan 04: blocked-until read and --pool Summary

`lane_switch.blocked_until(pool)` reads a pool's blocked-until time only through `node <template> --blocked-status <pool>`,
spawned through `detection.bounded_run` with the preview timeout; one stdout line `blocked_until=<ISO Z|-> failures=<n>` gives a
UTC time, and no node, no template, a spawn error, an undecodable output, a non-zero exit, any other shape, `-` or an impossible
date read as None and never block. `pool_blocked` asks only for a lane whose `lane_settings.lane_pool` is set (flagged
`usage_limited` with a valid pool) and blocks only while the time is later than now. `blocked_cache_entries` is the quota-cache
rule plan 40-05 wires into Step 0.7. A review dispatch and a `role="review"` probe of a flagged pooled lane add `--pool <pool>`
after every existing `runner_flags` flag; `check-reviewer`, the effort probe, execute-role probes and every other spec are
unchanged (byte-equal flags).

## Commits

| Task | Commit | Subject |
|------|--------|---------|
| 1 | c9d332d | feat(40-04): read a pool's blocked-until time through the runner |
| 2 | d44042c | feat(40-04): pass --pool for a usage_limited review lane |
| 3 | e8bc841 | feat(40-04): skip a blocked pool and retry it once after its time |

Cross-AI lanes (pi, router-env/my-coding), one per task from the start, each AIKIT-XAI `status=ok attempts=1`: Task 1 215 s,
Task 2 214 s, Task 3 201 s. No fix-up lane was needed.

## Verification (chunk executor, own runs)

- Task 1 acceptance: `blocked_until`/`pool_blocked`/`blocked_reader` 3, `def lane_pool` 1, the `quota.py` allowance 1, the
  `(OSError, subprocess.SubprocessError, ValueError)` catch 1, `_parse_status` 1, `--blocked-status` typed only in
  lane_switch.py, no process-session literal in lane_switch.py, no `PROVISIONAL` in any product file of this plan.
- Task 2 acceptance: `pool: str | None = None` 1, `flags += ["--pool", spec.pool]` 1, `class TestPoolFlag` 1,
  `_replace(role=args.role)` 1, `role: str = ""` 1, `lane_pool` in reviewer_dispatch.py 1,
  `test_check_reviewer_never_passes_the_pool` 1, `review_spec` keeps five parameters 1.
- Task 3 acceptance: `def blocked_cache_entries` 1, the five named tests 5.
- `tests.test_lane_switch` 24 ok, `tests.test_lane_settings` 50 ok, `tests.test_runner_flags` 24 ok,
  `tests.test_ai_kit_spec_runner_dispatch` 80 ok, `tests.test_runner_describe` 20 ok, `tests.test_ai_kit_spec` 703 ok,
  `tests.test_effort_probe` 23 ok, `tests.test_lane_ping` 20 ok, `tests.test_arch` 118 ok, `tests.test_arch_hardcoded_models` 23
  ok; no line over 100 characters; `tests/fixtures/no_hardcoded_models_baseline.json` unchanged; no new test spawns node.
- Gates after the plan: unit + arch groups under the watchdog `196/196 modules passed` (peak 7 runner processes, not killed);
  `make ruff`, `make pyright`, `make vulture`, `make pylint`, `make check-dogfood` exit 0 each; the commit-deferred
  `tests.test_ai_kit_gsd_curated_config_matrix` 35 tests ok (155.0 s, under the watchdog, peak 2).

## Deviations

- Owner decision applied: the blocked-until reading is confirmed, so the plan's `PROVISIONAL:` docstring prefixes, the
  `RunnerSpec.pool` comment prefix, the acceptance count `PROVISIONAL >= 4` (now: none) and the ` (provisional)` commit
  suffixes were dropped. The free-pool `PROVISIONAL` label of plan 40-03's same-pool test stays as written there.
- Task 1 (plan miss): the reader name `lane_pool` is also the name of the existing module `ai_kit_spec.lane_pool`, imported by
  lane_order.py and propose_cmds.py, so the token-based reader scan flagged them; the lane added commented `ALLOWED_READERS`
  entries for those two files. Open for code review: rename the reader or make the scan call-aware, so those two modules are
  not allowed to call the reader.
- Task 3: the `_read` test helper's `node`/`template` parameters are typed `str | None` (pyright); the cache-rule test adds a
  blocked lane `lane-d` outside the ladder to prove an off-ladder lane is untouched.
