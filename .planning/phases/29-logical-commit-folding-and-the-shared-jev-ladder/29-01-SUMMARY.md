---
phase: 29-logical-commit-folding-and-the-shared-jev-ladder
plan: 01
subsystem: tooling
tags: [git, commit-fold, plumbing, temp-index, compare-and-swap, stdlib]

# Dependency graph
requires: []
provides:
  - "Fold engine tracer: schema-1 checkpoint folds to one commit per feature via a temp index, tree proofs, backup tag, compare-and-swap ref move, and the five-line report"
affects: [29-02, 29-06, 29-09, 29-10, 29-12, 29-13]

# Actuals (#2632): chars/4 over the realized diff (git diff 358113ad..HEAD = 58677 chars)
actuals:
  tokens: 14669
  tasks: 2
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "git plumbing in a temporary index (GIT_INDEX_FILE), never the working tree or real index"
    - "tree proof before any ref write, then update-ref compare-and-swap with a backup tag"
    - "fail-closed proofs: an unresolved tree id is a mismatch"

key-files:
  created:
    - skills/ai-kit-commit-fold/scripts/fold_engine.py
    - skills/ai-kit-commit-fold/scripts/fold_group.py
    - skills/ai-kit-commit-fold/scripts/fold.py
    - tests/fold_fixtures.py
    - tests/test_ai_kit_commit_fold.py
  modified:
    - pyproject.toml
    - Makefile
    - .pre-commit-config.yaml

key-decisions:
  - "Engine takes only the framework-neutral checkpoint (schema 1); unknown keys are ignored for forward compatibility"
  - "Folded commits keep the author of each feature's first commit; the committer is the current identity"
  - "Docs-only commits inherit the nearest earlier feature; docs paths and unclaimed changes go to the last feature"
  - "Tree proofs compare the segment against end and the swap target against tip; both fail closed"

patterns-established:
  - "Test seams are module functions (_before_swap) that later plans patch"
  - "Every outcome, refusals included, comes back as a Result; the CLI maps it to exit 0/1"

requirements-completed: [FLOW-01]

coverage:
  - id: D1
    description: "Two-feature checkpoint folds into exactly two commits on the tested tree, with the backup tag and a clean status"
    requirement: "FLOW-01"
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_commit_fold.py#TestFoldTracer.test_two_features_fold_into_two_commits"
        status: pass
    human_judgment: false
  - id: D2
    description: "Five-line report for every outcome and reason, with the outcome line naming unit and reason"
    requirement: "FLOW-01"
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_commit_fold.py#TestReport.test_every_outcome_and_reason_renders_the_five_line_report"
        status: pass
    human_judgment: false

# Metrics
duration: unmeasured
completed: 2026-11-04
status: complete
commits: 3
plan_head_before: 358113ad9a4aa1cfa49436075b488461f96112f8
plan_head_after: 53700cdd9ccbce4dddbd3aeeb3d25cc9e5eeec68
---

# Phase 29 Plan 01: Fold engine tracer folds a two-feature checkpoint into two commits with a five-line report

**Framework-neutral fold engine: one checkpoint in, one commit per feature out, through a temp index, a tree proof, a backup tag and a compare-and-swap ref move**

## Performance

- **Tasks:** 2 planned (3 commits, including one comment-only commit)
- **Files:** 8 changed (5 new, 3 modified)
- **Duration:** unmeasured (no start timestamp was recorded)

## Accomplishments

- A two-feature checkpoint folds 4 commits into 2 with the same final tree, the old tip tagged as `ai-kit-fold/29-01/<12 hex>`, and a clean `git status --porcelain --untracked-files=no`.
- Folded commits keep the first feature commit's author, keep first-commit order, carry the trailer `Ai-Kit-Fold: <unit>`, and route docs paths into the last feature.
- Every outcome renders the fixed five-line plain-text report; the checker rejects six-line and colour-coded text.
- `fold.py fold <checkpoint.json|->` exits 0 on folded or nothing-to-fold, 1 on refusal, 2 on unreadable input.

## Task Commits

1. **Task 1: Two-feature checkpoint folded end to end** - `9a7356f` (feat)
2. **Task 2: Report renderer for every outcome and reason** - `1aebcf7` (test)
3. **Shortcut markers for the known limits** - `53700cd` (docs, not a plan task; see Deviations)

**Plan metadata:** committed separately after this file (docs(29-01)).

## Files Created/Modified

- `skills/ai-kit-commit-fold/scripts/fold_engine.py` - checkpoint load, range commits, temp-index build, tree proofs, backup tag, compare-and-swap, report
- `skills/ai-kit-commit-fold/scripts/fold_group.py` - rule-based grouping by candidate file hits, docs paths to the last feature
- `skills/ai-kit-commit-fold/scripts/fold.py` - CLI
- `tests/fold_fixtures.py` - temp-repo helpers with pinned identity and no host config
- `tests/test_ai_kit_commit_fold.py` - 19 tests: tracer, CLI, refusals, checkpoint shape, report
- `pyproject.toml` - pyright `extraPaths` entry for the skill scripts
- `Makefile`, `.pre-commit-config.yaml` - regenerated test-group listings (`tools/gen_test_groups.py`)

## Decisions Made

- Engine reads only the schema-1 checkpoint and names no framework; plan 29-09 adds the adapters.
- Docs-only commits attach to the nearest earlier feature (jev was asked; see the call log; decided on the code's existing behaviour).
- `end` must equal `tip` until plan 29-06 adds the replay step; a checkpoint with `end` before `tip` refuses `tree_mismatch` and moves nothing.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Tree proofs could pass on two unresolved ids**
- **Found during:** Task 1 (pyright on the new code)
- **Issue:** `_rev` returns `None` on failure, so two `None` tree ids compared equal and a proof could pass without evidence.
- **Fix:** `_prove_segment` and `_prove_target` raise `tree_mismatch` when either side does not resolve.
- **Files modified:** `skills/ai-kit-commit-fold/scripts/fold_engine.py`
- **Verification:** pyright 0 errors; fold tests pass.
- **Committed in:** `9a7356f`

**2. [Rule 3 - Blocking] First Task 1 commit rejected by ruff and pylint hooks**
- **Found during:** Task 1 commit
- **Issue:** line length, `zip` without `strict=`, import order, unused `noqa`, too many locals in `_build` and `rule_features`, and two dataclasses over the instance-attribute limit.
- **Fix:** split `_build` and `rule_features` into helpers, made `zip` strict, used `from tests import fold_fixtures`, and added a documented `too-many-instance-attributes` disable on the two record dataclasses (same precedent as `tools/common_render.py` `Context`).
- **Verification:** ruff, pylint 10/10, pyright 0 errors; hooks passed on the retried commit. No commit had landed from the failed attempt.
- **Committed in:** `9a7356f`

**3. [Scope note] Shortcut markers committed separately**
- **Issue:** the house rule requires known limits to carry a `shortcut:` comment; these were added after the two plan commits.
- **Fix:** comment-only commit `53700cd` marks merges skipped (not refused), no replay after `end`, and shared-path features staged in both commits.
- **Verification:** ruff clean; the commit hook ran the covering tests.

## Issues Encountered

- The first jev call returned `invalid_input` because `reviewed_head` held a short sha. The retry with the full sha succeeded.
- The `make test` run (`tmp/p29/01/make-test.log`, exit 0) ran on `1aebcf7`. The later commit `53700cd` changes comments only.
- Task 2 was test-only. The renderer was written in Task 1, so `TestReport` passed on its first run and no red commit was made. The six-line and colour-code rejections in that class check that the checker is not vacuous.
- Choices not sent to jev: the `too-many-instance-attributes` disable versus a restructure (chose the documented disable), and the blank line before the trailer (kept git's trailer format).

## Jev call log

- c1 | docs-only commit membership (nearest earlier feature vs last feature) | answer `a`, confidence 0.10 (Laya and TypeSafe both `needs_fallback: true`; TypeSafe consent on file 2026-10-14; summaries only) | decided myself: kept `a`, which is the existing code. Check: `test_docs_path_lands_in_last_commit` passes (2 commits, docs path in the last).

## Known limits (lifted by plan 29-06)

- Merges in the range are skipped, not refused.
- No replay of commits after `end`; only `end == tip` passes the final proof (pinned by `test_end_before_tip_refuses_without_moving_the_ref`, which plan 29-06 will change).
- No shared-path merge between features.

## Self-Check

- Created files exist: `fold.py`, `fold_engine.py`, `fold_group.py`, `fold_fixtures.py`, `test_ai_kit_commit_fold.py` (all FOUND).
- Commits are ancestors of HEAD: `9a7356f`, `1aebcf7`, `53700cd` (all FOUND); `git rev-list --count 358113ad..HEAD` = 3.
- Acceptance: `rg` for `shell=True|reset --hard|"reset"` prints nothing; `GIT_INDEX_FILE|update-ref|commit-tree` all match in `fold_engine.py`; one `extraPaths` line; the module is listed in the Makefile and `.pre-commit-config.yaml`.
- Each test under 0.08 s (measured per test inside the suite run); the module total is 0.39 s.

## Self-Check: PASSED

## Verification

- `python3 tools/run_unittest_parallel.py tests.test_ai_kit_commit_fold tests.test_gate_scope`: pass (19 + 57 tests).
- `python3 tmp/p29/01/scope.py test` (`make test`): exit 0, all tiers green (`tmp/p29/01/make-test.log`).
- `python3 tmp/p29/01/scope.py close`: `clean` after the last task commit (`53700cd`), before this file was written. Other agents' processes and temp dirs were reported, not counted.
