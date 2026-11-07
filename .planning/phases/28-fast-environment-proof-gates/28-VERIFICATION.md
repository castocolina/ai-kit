---
phase: 28-fast-environment-proof-gates
verified: 2026-11-07T12:00:00Z
status: passed
score: 5/5 must-haves verified
covered_files:
  - ".planning/phases/28-fast-environment-proof-gates/28-01-PLAN.md"
  - ".planning/phases/28-fast-environment-proof-gates/28-01-SUMMARY.md"
  - ".planning/phases/28-fast-environment-proof-gates/28-02-PLAN.md"
  - ".planning/phases/28-fast-environment-proof-gates/28-02-SUMMARY.md"
  - ".planning/phases/28-fast-environment-proof-gates/28-03-PLAN.md"
  - ".planning/phases/28-fast-environment-proof-gates/28-03-SUMMARY.md"
  - ".planning/phases/28-fast-environment-proof-gates/28-04-PLAN.md"
  - ".planning/phases/28-fast-environment-proof-gates/28-04-SUMMARY.md"
  - ".planning/phases/28-fast-environment-proof-gates/28-05-PLAN.md"
  - ".planning/phases/28-fast-environment-proof-gates/28-05-SUMMARY.md"
  - ".planning/phases/28-fast-environment-proof-gates/28-06-PLAN.md"
  - ".planning/phases/28-fast-environment-proof-gates/28-06-SUMMARY.md"
  - ".planning/phases/28-fast-environment-proof-gates/28-07-PLAN.md"
  - ".planning/phases/28-fast-environment-proof-gates/28-07-SUMMARY.md"
  - ".planning/phases/28-fast-environment-proof-gates/28-08-PLAN.md"
  - ".planning/phases/28-fast-environment-proof-gates/28-08-SUMMARY.md"
  - ".planning/phases/28-fast-environment-proof-gates/28-09-PLAN.md"
  - ".planning/phases/28-fast-environment-proof-gates/28-09-SUMMARY.md"
  - ".pre-commit-config.yaml"
  - "Makefile"
  - "skills/ai-kit-spec-review/references/cross-ai.mjs"
  - "tests/host_fakes.py"
  - "tests/test_arch.py"
  - "tests/test_gate_scope.py"
  - "tools/env_matrix.py"
  - "tools/run_unittest_parallel.py"
  - "tools/staged_mapper.py"
  - "tools/time_prepush.py"
covered_digest: "v4:sha256:8e048912a737186c1ad980db172c92f31242ac0ad542983956c1e5bf68b4a348"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: passed
  previous_score: 5/5
  gaps_closed: []
  gaps_remaining: []
  regressions: []
---

# Phase 28: Fast, environment-proof gates Verification Report

**Phase Goal:** The owner can commit and push without waiting on slow tests or tests that pass or fail depending on the caller's environment.
**Verified:** 2026-11-07 at tip 7077c12 (main)
**Status:** passed
**Re-verification:** Yes. The report was stale: files it covers changed in phases 29-31 and later fixes. Re-checked against the current code; prior evidence kept where still valid.

## Observable Truths (ROADMAP success criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Commit runs only covering modules in parallel, refused on failure (GATE-01) | VERIFIED | `staged-tests` hook at `.pre-commit-config.yaml:58` (`python3 tools/run_unittest_parallel.py --staged`). `uv run python -m unittest tests.test_staged_commit_e2e`: 13 tests OK (real staged commits in a temp repo, incl. refusal). `python3 tools/staged_mapper.py --stats`: 69 units, median 4 covering modules, max 59. `tests.test_staged_mapper` (71 tests) and `tests.test_gate_scope` (57) pass. |
| 2 | Pre-push full unit/arch/wizard suites well under 2.5 min; before/after recorded; no real host binary (GATE-02) | VERIFIED | `tools/time_prepush.py` present with `tests.test_time_prepush` (32 tests) passing; AGENTS.md "Push timing" records 183.9 s before and 30.7 s after for the two test hooks. Real push measured by the owner in 28-UAT.md (all pre-push hooks, exit 0 in 77 s; test hooks 55.6 s at that time). Host-CLI tripwire and structural test present. |
| 3 | Same result in plain terminal, host session, no host CLI, long path, custom TMPDIR, outside git; structural test for host CLI (GATE-03) | VERIFIED | `make test-env-matrix` target at `Makefile:116`; `tools/env_matrix.py` covered by `tests.test_env_matrix`. Recorded 28-08 result: `matrix: identical in 6 environments`; the path-length test fix is in 28-03. 28-UAT.md test 2: `make test` inside a real pi session, EXIT=0, same as a plain terminal, no real host binary call. `tests/test_arch.py:2164` `test_no_test_calls_a_host_cli` plus non-vacuity cases pass (103 tests OK). The 6-env matrix was not re-run (about 45 min). |
| 4 | Runner self-test passes under load; budgets scale with load; real limits unchanged (GATE-04) | VERIFIED | `loadFactor()` at `cross-ai.mjs:5245`; `selfTestLoadFactor = loadFactor(measuredLoadPerCpu())` at `:5536` scales only self-test ceilings; the in-file self-test checks the factor table (`:8489`). `tests.test_cross_ai_runner_e2e`: 28 tests OK in 16.3 s. |
| 5 | Structural test fails when a test reads `.planning/`; test data under `tests/` (GATE-05) | VERIFIED | `tests/test_arch.py:2143` `test_no_test_reads_planning` and `:2161` `test_planning_reader_exceptions_stay_empty` (empty exceptions); data under `tests/fixtures/archived`. `tests.test_arch tests.test_gate_scope tests.test_staged_mapper tests.test_time_prepush`: 4/4 modules OK. |

**Score:** 5/5 truths verified.

## Requirements Coverage

| Requirement | Status | Evidence |
|-------------|--------|----------|
| GATE-01 | SATISFIED | staged hook, mapper, 13-test temp-repo e2e; `deferred-e2e` hook at `.pre-commit-config.yaml:99` |
| GATE-02 | SATISFIED | time_prepush and its tests; recorded before/after in AGENTS.md; real push in 28-UAT.md |
| GATE-03 | SATISFIED | 6-env matrix identical (28-08), `make test-env-matrix`, host-CLI structural rule, real pi session run (28-UAT.md) |
| GATE-04 | SATISFIED | `loadFactor` clamp; real limits unscaled; runner e2e passes |
| GATE-05 | SATISFIED | structural `.planning/` rule, empty exception list, passing |

No orphaned requirement IDs: REQUIREMENTS.md maps exactly GATE-01..05 to Phase 28.

## Notes

- Covered files moved after the earlier report because later phases extended the unit list, hook entries and arch rules (`.pre-commit-config.yaml`, `Makefile`, `tests/test_arch.py`, `tests/test_gate_scope.py`, `tools/run_unittest_parallel.py`, `tools/staged_mapper.py`). The current tests pin the gate shape and pass, so the phase behaviour still holds.
- Running `tests.test_staged_commit_e2e` under system python skips all 13 (pre_commit not importable); under `uv run` they run and pass.
- The full `make test`, `time_prepush.py` timing and the 6-environment matrix were not re-run in this pass (parallel runs collide; matrix is about 45 min). Their last recorded results stand in 28-08 and 28-UAT.md.

## Human Verification

Both human checks were resolved and passed (28-UAT.md, 2/2): a real commit and a real `git push` to GitHub origin with every pre-push hook (exit 0), and `make test` inside a real pi session (EXIT=0, same result as a plain terminal). No items remain.

## Gaps Summary

No gaps.

---

_Verified: 2026-11-07_
_Verifier: Claude (gsd-verifier)_
