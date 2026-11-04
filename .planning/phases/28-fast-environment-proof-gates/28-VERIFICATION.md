---
phase: 28-fast-environment-proof-gates
verified: 2026-11-04T11:10:00Z
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
covered_digest: "v4:sha256:1670a9dd5f14d9dd4fc4325f346ecbce44bfc79275a725e435c2a830c78a1d06"
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Make a real commit touching one module, then a real `git push` to a remote, on the owner's machine"
    expected: "Commit runs only covering modules and is refused on a failure; push finishes the two test hooks in about 60 s or less; a deferred e2e notice appears only for over-budget modules"
    why_human: "A real push to a remote and the owner's real hook install were not exercised; the temp-repo e2e (13 tests) and the timed hook run cover the logic"
  - test: "Run `make test` once from inside a real opencode or pi session with the real host CLIs on PATH"
    expected: "Same pass/skip result as a plain terminal; no real host binary invoked"
    why_human: "The Claude Code case is proven live (the make test at 5109f80 ran inside a Claude Code session, rc 0, 120 s); the matrix fakes the other host signals, and agents cannot launch a real opencode or pi session"
---

# Phase 28: Fast, environment-proof gates Verification Report

**Phase Goal:** The owner can commit and push without waiting on slow tests or tests that pass or fail depending on the caller's environment.
**Verified:** 2026-11-04 at tip 29a7764
**Status:** human_needed (all automated truths verified; two owner-only checks remain)
**Re-verification:** No

## Observable Truths (ROADMAP success criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Commit runs only covering modules in parallel, refused on failure (GATE-01) | VERIFIED | `staged-tests` hook at `.pre-commit-config.yaml:57` (`run_unittest_parallel.py --staged`, commit stage). `uv run python -m unittest -v tests.test_staged_commit_e2e` rc 0, 13 tests OK (real staged commits in a temp repo, incl. refusal). `python3 tools/staged_mapper.py --stats` rc 0: 66 units, median 3 covering modules, max 47. `tests.test_staged_mapper`, `tests.test_gate_scope` pin hook shape (all OK, see below). |
| 2 | Pre-push full unit/arch/wizard suites well under 2.5 min; before/after recorded; no real host binary (GATE-02) | VERIFIED | `python3 tools/time_prepush.py` rc 0: `test-hooks=55.6s limit=60.0s ... push-worst=67.5s verdict=pass` (core 34.6 s, 81/81; wizard 21.0 s, 5/5) vs 184 s baseline (AGENTS.md:186-194 and README record before/after). Host-CLI tripwire + structural test present. |
| 3 | Same result in plain terminal, host session, no host CLI, long path, custom TMPDIR, outside git; structural test for host CLI (GATE-03) | VERIFIED | 28-08-SUMMARY: final run on 8f8e996 `matrix: identical in 6 environments`, exit 0, zero `host CLI calls:` lines (logs under tmp/p28/). Post-cxr: `tmp/quick-xai-split/env_matrix.log` `--only custom-tmpdir --only long-path` rc 0, `matrix: identical in 3 environments`. `make test` at 5109f80 rc 0 (wall 120 s, all tiers green; 29a7764 adds docs only). `tests/test_arch.py` `test_no_test_calls_a_host_cli` + non-vacuity cases pass. |
| 4 | Runner self-test passes under load; budgets scale with load; real limits unchanged (GATE-04) | VERIFIED | `loadFactor()` in `cross-ai.mjs:5245` clamps load per CPU to 1..4; `selfTestLoadFactor` applies only to self-test ceilings (`scaledMs`); real limits (`budgetMs`) untouched. `tests.test_cross_ai_runner_e2e` (29 tests, ok 17.0 s) has the injected-load factor tests; the 8 shard modules ran ok in the `make test` e2e tier. |
| 5 | Structural test fails when a test reads `.planning/`; test data under `tests/` (GATE-05) | VERIFIED | `tests/test_arch.py` `test_no_test_reads_planning` + `test_planning_reader_exceptions_stay_empty` (exceptions empty); data moved to `tests/fixtures/archived`. `python3 -m unittest tests.test_arch tests.test_gate_scope tests.test_staged_mapper tests.test_time_prepush`: Ran 230 tests, OK. |

**Score:** 5/5 truths verified.

## Requirements Coverage

| Requirement | Status | Evidence |
|-------------|--------|----------|
| GATE-01 | SATISFIED | staged hook + mapper + 13-test temp-repo e2e (rc 0); deferred-e2e hook at `.pre-commit-config.yaml:98` implements the amended over-budget rule via `E2E_RECORDED_SECS` / `split_e2e` |
| GATE-02 | SATISFIED | time_prepush rc 0, test-hooks 55.6 s <= 60 s |
| GATE-03 | SATISFIED | 6-env matrix identical (28-08), 3-env re-run after the cxr shard split identical, host-CLI structural rule |
| GATE-04 | SATISFIED | `loadFactor` 1..4 clamp; real limits unscaled; load-factor tests pass |
| GATE-05 | SATISFIED | structural `.planning/` rule, empty exception list, passing |

No orphaned requirement IDs: REQUIREMENTS.md maps exactly GATE-01..05 to Phase 28.

## Notes on the evidence the orchestrator flagged

- **`deferred-e2e=0.0s(rc=0, 0/0, no range)` is correct, not a defect.** `split_e2e` defers a module only if its recorded time in `E2E_RECORDED_SECS` is missing or above `COMMIT_E2E_BUDGET_SECS = 60`. After the cxr split every one of the 22 e2e modules is recorded and the largest is 58 s (`test_precompact_shims_e2e`); the 360.5 s `test_cross_ai_runner_e2e` is now 18 s and the shards are 23-26 s. So no covering set defers anything, and with no pushed range the hook reports 0/0. The deferral logic stays covered by `test_gate_scope` / runner tests. Risk (info): `test_precompact_shims_e2e` at 58 s is 2 s under the budget, so a slower machine would simply start deferring it to push (designed behavior).
- **check-dogfood skip:** `make check-dogfood` rc 0; the apply no-write guard did not run because checkout-local gsd-core is 1.20.0 and the guard is pinned to 1.16/1.17 (backlog 999.18). No Phase 28 requirement demands that guard run; classified as a known backlog item, not a gap.
- **System-python run of `test_staged_commit_e2e` skips all 13** (pre_commit not importable); under `uv run` (the e2e tier) they all run and pass.
- `tests/gsd_curated_eval.py` builds `.planning` paths from a `repo_root` argument; it is a helper (not a `test_*.py` reading the live project), and the structural scan passes with no exceptions. Not a gap.
- 28-REVIEW-DISPOSITION: 7 info findings skipped, WR findings fixed; no open warning.

## Anti-Patterns

None blocking found in the scanned files; working tree changes (`.planning/config.json`, an untracked goals file) predate this verification and belong to the orchestrator.

## Human Verification Required

1. **Real commit and push on the owner's machine.** Test: commit a one-module change, then `git push` to a real remote. Expected: only covering modules run, a failing one refuses the commit; push test hooks about 60 s or less. Why human: no real remote push or real hook install was exercised; logic is covered by temp-repo e2e and the timed hook run.
2. **Run from inside a real opencode or pi session.** Expected: same results as a plain terminal. Why human: the Claude Code case is proven live (the make test at 5109f80 ran inside a Claude Code session, rc 0); the matrix fakes the other host signals, and agents cannot launch a real opencode or pi session.

## Gaps Summary

No gaps. The six-environment matrix was not re-run (about 45 min); the recorded 28-08 result and the 3-environment post-split re-run were used.

---

_Verified: 2026-11-04_
_Verifier: Claude (gsd-verifier)_

## Human verification results (2026-11-04)

Both items passed; evidence in 28-UAT.md (real push to GitHub origin with every pre-push hook, and `make test` inside a real pi session).
