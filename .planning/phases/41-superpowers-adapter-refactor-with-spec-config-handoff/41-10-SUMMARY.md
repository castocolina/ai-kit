---
phase: 41-superpowers-adapter-refactor-with-spec-config-handoff
plan: 10
subsystem: superpowers adapter (executor switch code slice)
tags: [superpowers, lanes, quota, pool, executor-switch]
requires: [41-09]
provides:
  - "assemble_candidates: candidate keys `pool` (lane_settings.lane_free_pool) and `roster_entry` (the raw roster entry of the same config read)"
  - "external_cli injection and the dispatch_superpowers_task candidate carry `pool`; execute_dispatch._runner_spec(...)._replace(pool=candidate.get(\"pool\")) so --pool reaches the runner only for a flagged pooled lane"
  - "lane_switch: `role: str = \"review\"` on review_lane, _route, next_lane, replacement_row; new flagged_lane(config, key, reason, role=\"review\"); flagged_replacement keeps five parameters and delegates"
  - "dispatch_injection.quota_evidence(dispatch_result) -> bool (runner status quota or reason quota only; a transient 69/75 is never evidence)"
  - "adapter cli: _blocked_pool_quota(deps, loaded, request, existing_quota) and CliDeps.clock_fn; resolve-injection stamps a still-blocked flagged pool before the quota refresh and lets an expired pool be retried once by its first eligible lane"
affects: [41-11]
key-files:
  created:
    - tests/test_adapter_executor_switch.py
  modified:
    - skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/dispatch_injection.py
    - skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/cli.py
    - skills/ai-kit-spec-review/ai_kit_spec/execute_dispatch.py
    - skills/ai-kit-spec-review/ai_kit_spec/lane_switch.py
    - tests/test_lane_settings.py
    - Makefile
    - .pre-commit-config.yaml
decisions:
  - "Owner confirmed the executor switch (2026-11-25): it reuses the flagged-lane switch module and the runner's --blocked-status reader; no second copy of the selection rule."
  - "The blocked step ranks with the builder's own narrowing on the post-exclusion request; the saved ladder_keys stay the full ladder for resume and escalation."
metrics:
  tasks: 3
  commits: 3
---

# Phase 41 Plan 10: executor switch code slice Summary

A flagged pooled execute lane now carries its pool through the candidate, the injection and the dispatch candidate to the
runner spec, so `--pool <provider>:free` reaches the runner for that lane only. The shared switch helpers in `lane_switch`
take a `role` (review by default, review callers byte-identical), `flagged_lane` holds the quota-and-flag check, and
`quota_evidence` tells runner-proven quota from a transient failure for the quota-stop subcommand of plan 41-11.
`resolve-injection` skips a lane whose pool is still blocked and lets an expired pool be retried once by its first eligible
spawned lane; a missing node, runner or bad record blocks nothing, and unflagged or native lanes never read a record.

## Commits

| Task | Commit | Subject |
|------|--------|---------|
| 1 | 729834d | feat(41-10): pass a flagged execute lane's pool to the runner |
| 2 | 4d8c576 | feat(41-10): let the flagged-lane switch helpers serve the execute role and tell quota evidence from a transient failure |
| 3 | 5dc789e | feat(41-10): skip a blocked pool at executor selection and try an expired one once |

Cross-AI lanes (pi, router-env/my-coding), one per task from the per-task prompts with checked anchors
(`tmp/run-2026-11-23/anchors-41-10.md`, re-checked at a00b877), each AIKIT-XAI `status=ok attempts=1`: Task 1 374 s (hook
full unit+arch 229/229 + uv 23/23, Makefile staged, one ruff E501 retry inside the lane), Task 2 219 s (hook 165/165 + uv
22/22), Task 3 189 s (hook 26/26). Tasks 1 and 2 deferred `tests.test_ai_kit_gsd_curated_config_matrix` to push.

## Verification (chunk executor, own runs)

- Task 1: `"pool": lane_settings.lane_free_pool(r),` 1; `lane_free_pool` absent from execute_dispatch.py; Makefile names the
  new module; the `_replace(pool=candidate.get("pool"))` call is wrapped over two lines (see Deviations).
- Task 2: `role: str = "review"` 5; the `flagged_lane` signature 1; `if flagged_lane(config, key, reason) is not None else None` 1;
  the `quota_evidence` signature 1; tests/test_lane_switch.py and tests/test_lane_ping.py unchanged over the whole plan.
- Task 3: `lane_switch.blocked_cache_entries(` 1, `clock_fn` 2, `deps.compute_ladder_keys_fn(request, loaded.routes)` 1 in cli.py;
  `"roster_entry": r,` 1; no `execute_lanes_fn` / `_execute_lanes`; 16 tests in the new module.
- Scope a00b877..5dc789e = the eight files_modified; no phase, plan, decision or requirement id in added lines; no flag literal
  added to code; tests/fixtures/no_hardcoded_models_baseline.json unchanged.
- Modules: adapter_executor_switch 16, lane_switch 30, lane_ping 34, lane_settings 58, ai_kit_spec_superpowers 175,
  ai_kit_spec_runner_dispatch 80, gate_scope 62, adapter_session_fallback 27, arch 118, arch_hardcoded_models 23,
  role_orders 29, adapter_single_definitions 9: all ok.
- Gates after the plan: unit + arch groups under the watchdog `206/206 modules passed` (peak 9, not killed); `make ruff`,
  `make pyright`, `make vulture`, `make check-dogfood` exit 0 (`check-dogfood: ok`; judge stale-digest and facts-drift notes
  only); `make pylint` exit 0 on a re-run (the first run stopped on a transient uv cache error, `Failed to query Python
  interpreter`, before pylint started).
- Deferred e2e: `tests.test_ai_kit_gsd_curated_config_matrix` under the watchdog, 35 tests ok in 150.4 s, `1/1 modules passed`
  (guard exit 0, peak 2, not killed).
- No SKILL.md changed (ai-kit-spec-execute-superpowers body stays 3763 words, 290 lines).

## Deviations

- Task 1: `_runner_spec`'s `._replace(` call is wrapped over two lines (one line passes the 100-character limit), so the
  plan's one-line acceptance grep prints 0; the code is the planned call. Its docstring no longer carries an old decision tag.
- Task 2: the test helper `execute_switch` is an `if ... is None: return None` pair (the one-line form passes 100 characters);
  the no-fallback case's second lane is flagged in another pool (no eligible fallback either way).
- Task 3: `test_sole_blocked_pool_with_session_fallback_runs_native` writes a global config whose lane carries no
  `usage_limited`/`pool` (a free lane there is refused without a data-use record); the resolved roster the command uses is
  still the flagged lane, so the test proves the session fallback beside a blocked pool. Its `_resolve` types `node` as
  `str | None` and the expired-pool test narrows `refreshed` with an assert (pyright).
- No change to tests/test_lane_settings.py in Task 3: Task 1's allowed-reader row already covers dispatch_injection.py.
