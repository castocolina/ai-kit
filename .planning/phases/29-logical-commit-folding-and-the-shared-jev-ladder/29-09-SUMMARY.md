---
phase: 29-logical-commit-folding-and-the-shared-jev-ladder
plan: 09
subsystem: tooling
tags: [git, commit-fold, gsd, superpowers, adapters, status, stdlib]

# Dependency graph
requires:
  - phase: 29-01
    provides: fold engine tracer (checkpoint fold, tree proofs, backup tag, five-line report)
  - phase: 29-06
    provides: refusal guards, merge-back handling and replay in the engine
provides:
  - "fold.py gsd --phase N: folds every finished plan of a GSD phase, in plan order, each on its own checkpoint"
  - "fold.py superpowers --plan FILE [--base SHA] [--base-branch NAME]: folds a finished superpowers plan branch"
  - "fold.py status --phase N: read-only per-plan backstop, always exits 0"
affects: [29-12, 29-13]

# Tech tracking
tech-stack:
  added: []
  patterns: [plan-scope commit ownership, per-plan first-parent run, adapter-built schema-1 checkpoint]

key-files:
  created:
    - skills/ai-kit-commit-fold/scripts/fold_adapters.py
    - tests/test_ai_kit_commit_fold_adapters.py
  modified:
    - skills/ai-kit-commit-fold/scripts/fold.py
    - skills/ai-kit-commit-fold/scripts/fold_engine.py
    - tests/fold_fixtures.py
    - tests/test_ai_kit_commit_fold.py
    - Makefile
    - .pre-commit-config.yaml

key-decisions:
  - "A GSD plan's run is the first-parent span from its first to its last commit owned by that plan; a commit of another plan, or a merge-back naming no single plan, inside the span refuses plan_not_contiguous"
  - "Candidates come from PLAN.md task elements (name and files); a task without a files element is skipped; ids are t1, t2 in the order of the candidates that remain"
  - "gsd folds finished plans only; a plan with one commit is skipped silently and the phase-level nothing-to-fold report prints only when no plan folded (jev asked, needs_fallback, decided by the executor)"
  - "superpowers base is --base (resolved) or the merge-base with the base branch; the adapter never reads commits below the base"
  - "The base branch is git.base_branch in config, else origin/HEAD, else main, else master"

patterns-established:
  - "Adapters name the framework and build the checkpoint; fold_engine.py names no framework (rg-checked)"
  - "One two-feature assertion (assert_two_feature_fold) runs on both the GSD and the superpowers fixtures"

requirements-completed: [FLOW-01]

# Metrics
duration: unrecorded (start time not captured in this run)
completed: 2026-11-04
status: complete

# Actuals (chars/4 over the realized diff; estimate was 50000 tokens for 2 tasks)
actuals:
  tokens: 15300
  tasks: 2
  commits: 2
plan_head_before: 9e7f0673c34fa9f5a1d1b9fc208986509169f185
plan_head_after: 934c94df91e3e29754ff57c182f8a94a1ab7673b
commits: 2
---

# Phase 29 Plan 09: GSD and superpowers fold adapters, and fold status Summary

GSD phases and superpowers plan branches now fold through the shared engine: `fold.py gsd --phase N` folds each finished plan in plan order, `fold.py superpowers --plan FILE` folds a plan branch, and `fold.py status --phase N` lists each plan read-only; a re-run folds nothing.

## Performance

- **Tasks:** 2 of 2 complete
- **Commits:** 2 task commits (12a709a, 934c94d); this SUMMARY is the plan's final docs commit
- **Plan base:** 9e7f067; HEAD at SUMMARY write: 934c94d

## Accomplishments

- `fold_adapters.py`: padded phase and phase dir lookup, base-branch resolution, GSD PLAN.md task parsing, superpowers plan-section parsing, plan ownership (`_owner`), per-plan checkpoint (`gsd_checkpoint`, `superpowers_checkpoint`), and `phase_status`.
- `fold.py`: `gsd`, `superpowers` and `status` subcommands next to the existing `fold`; `gsd` loops over finished plans and stops at the first refusal (exit 1).
- Refusals: `plan_not_contiguous` (another plan's commit, or an unattributable merge-back, inside a plan's run) and `detached_head`, both added to the engine's reason set.
- Test module `tests/test_ai_kit_commit_fold_adapters.py`: 16 tests across `TestGsdAdapter`, `TestParsers` and `TestSuperpowersAdapter`, on shared fixtures built once per class.
- Generated test listings (`Makefile`, `.pre-commit-config.yaml`) regenerated with `tools/gen_test_groups.py` and committed with the new module.

## Task Commits

1. **Task 1: GSD fold by phase, with ownership and status** - `12a709a` (feat)
2. **Task 2: superpowers adapter, base handling and detached refusal** - `934c94d` (feat)

## Files Created/Modified

- `skills/ai-kit-commit-fold/scripts/fold_adapters.py` - new: GSD and superpowers adapters, ownership, status.
- `skills/ai-kit-commit-fold/scripts/fold.py` - `gsd`, `superpowers`, `status` subcommands.
- `skills/ai-kit-commit-fold/scripts/fold_engine.py` - two reasons; merge-check wording names no framework.
- `tests/fold_fixtures.py` - `gsd_project`, `gsd_plan_commits`, `gsd_plan_text`, `superpowers_project`.
- `tests/test_ai_kit_commit_fold_adapters.py` - new adapter tests and `assert_two_feature_fold`.
- `tests/test_ai_kit_commit_fold.py` - reason-count pin moves from 11 to 13.
- `Makefile`, `.pre-commit-config.yaml` - generated listings include the new module.

## Decisions Made

See `key-decisions` in the frontmatter. The one choice that went to jev (the nothing-to-fold report) is in the jev call log below.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Acceptance criterion] Framework name in the engine**
- **Found during:** Task 1 acceptance check
- **Issue:** `rg -n "gsd|GSD|superpowers" fold_engine.py` matched a docstring and an error message left by plan 29-06 ("GSD's own merge-backs"), so the engine did not name no framework as the plan requires.
- **Fix:** Both wordings now say "the checkpoint's own merge-backs". No test pinned the message text.
- **Files modified:** `skills/ai-kit-commit-fold/scripts/fold_engine.py`
- **Commit:** 12a709a

**2. [Rule 1 - Test pin] Reason count**
- **Found during:** Task 1 test run
- **Issue:** `TestReport` pinned 11 refusal reasons; the plan adds two.
- **Fix:** Pin moved to 13.
- **Files modified:** `tests/test_ai_kit_commit_fold.py`
- **Commit:** 12a709a

### Process Deviation

**Task split built by stripping, not by a separate branch.** The superpowers code was written in the same pass as the GSD code. To commit Task 1 alone, I removed the superpowers parts with a scratch script (`tmp/p29/09/split_task1.py`, gitignored, not in the repo), checked Task 1 with its tests, committed it, then restored the full files for Task 2. Both commits passed the commit hooks; the Task 1 commit ran the full unit and arch suites because the listing file is shared machinery.

## Verification

- `tests.test_ai_kit_commit_fold_adapters`: 16/16 ok (also after the split, 11/11 for the Task 1 state).
- `tests.test_ai_kit_commit_fold` and `tests.test_gate_scope`: ok.
- `make test` run through `scope.py test` (log `tmp/p29/09/make-test.log`): unit 83/83, unit-uv 1/1, integration 6/6, e2e 22/23. One e2e module failed (see Deferred Issues); make stopped at the e2e tier, so arch was not reached in that run.
- Re-runs after that failure: `tests.test_precompact_shims_e2e` alone 24/24 ok; `make e2e-test` 23/23 ok (log `tmp/p29/09/e2e-retry.log`); `make arch-test` 1/1 ok (log `tmp/p29/09/arch-test.log`).
- A single `make test` exit 0 was therefore not obtained in this run; every tier is green on HEAD, with the one e2e flake observed once.
- ruff, pylint (10/10) and pyright (0 errors) on the fold scripts and the new tests: clean.
- `rg -n "gsd|GSD|superpowers" skills/ai-kit-commit-fold/scripts/fold_engine.py`: no match.
- `rg -c "assert_two_feature_fold\(" tests/test_ai_kit_commit_fold_adapters.py`: 3.
- `scope.py close`: `clean`, exit 0, after the last task commit (934c94d). The reported block lists other sessions' processes in the main checkout; none were touched.

## Known Limits

- A non-merge commit whose scope names a plan of another phase has no owner and is folded with the plan that surrounds it (the spec's `None` outcome). A plan's mitigation (T-29-27) covers other plans of the same phase, not other phases' commits. jev chose this reading (see call 3); flagged as a residual risk for the owner.
- A `status` error prints `status: <reason>: <detail>` and exits 0 (per the plan); the other plans' lines are not printed when the phase cannot be read.
- Superpowers candidates come from `### Task N` sections with Files bullets; a section without any file bullet is not a candidate.

## Self-Check

Check run after the last task commit and before this file was written:
- FOUND: `skills/ai-kit-commit-fold/scripts/fold_adapters.py`, `skills/ai-kit-commit-fold/scripts/fold.py`, `tests/test_ai_kit_commit_fold_adapters.py`
- FOUND: commit `12a709a` (Task 1) and `934c94d` (Task 2) are ancestors of HEAD

## Self-Check: PASSED

## Deferred Issues

- **Precompact shim e2e flake (outside this plan).** `tests/test_precompact_shims_e2e.py::TestShimsE2E::test_shims_hanging_interpreter_killed` (host `pi`) failed once in the first full e2e run with "ProcessLookupError not raised": a process the test expects to be dead still answered `kill(pid, 0)` right after the shim timed out. It passed on an isolated re-run and on the e2e tier re-run. The module and its harness (`tests/fixtures/precompact/run_shim.mjs`) contain no fold or git code; the likely cause is a timing race between the kill and reaping of the killed child, but that is not verified. Not fixed here; flagged for uz, who should decide whether to tighten that check.
- Make's full `make test` exit 0 in one run is outstanding until that flake is resolved or the check is stabilised.

## Threat Flags

None. The adapters read local plan files and local git history only; no new network endpoint, auth path or schema change. No package was installed (T-29-SC).

## jev-fast-decision call log

Client: `GSD_PATH_JEV=1 GSD_PATH_JEV_TIMEOUT_SECONDS=20 python3 -B skills/jev-fast-decision/scripts/jev_review.py ladder < tmp/p29/09/jev-N.json` (in-repo path). Consent: TypeSafe was already on file (granted 2026-10-14); the ladder reported it in `consent_used`, and no new consent was given. Only value-free summaries were sent. One first attempt with the shorthand `criterion`/`evidence` keys for a noul item was rejected as `invalid_input` (`unknown_key`); it was re-sent in the noul shape and answered.

- **call 1 (f1, noul, "the failing e2e check is caused by code changed in this plan")**: answer `yes`, confidence 0.88 (Laya; TypeSafe and OpenCode not asked). I verified it against the code before acting: neither the failing module nor its harness mentions fold or git. Decided: not caused by this plan's code. Test left unchanged; recorded under Deferred Issues.
- **call 2 (c1, choice, "per-plan report for a plan with nothing to fold")**: Laya `b` at 0.58 and TypeSafe `b` at 0.54, both `needs_fallback`, so decided by the executor. Chose option (a): skip silently, print the phase-level nothing-to-fold report only when no plan folded. This matches the plan's wording for that report.
- **call 3 (c2, choice, "foreign-phase plan-scoped commit inside a run")**: TypeSafe `a` at 0.98 (no fallback, decided by TypeSafe); Laya `b` at 0.52 (`needs_fallback`). Chose `a`, the spec's stated outcome (leave unowned), with the residual risk recorded under Known Limits.

*Phase: 29-logical-commit-folding-and-the-shared-jev-ladder*
