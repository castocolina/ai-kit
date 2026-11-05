---
phase: 29-logical-commit-folding-and-the-shared-jev-ladder
plan: 10
subsystem: tooling
tags: [git, commit-fold, jev, grouping, stdlib]

# Dependency graph
requires:
  - phase: 29-03
    provides: jev-fast-decision ladder entry point (`jev_review.py ladder`) and its per-item output shape
  - phase: 29-06
    provides: rule grouping with shared-path and code-with-test merges, and the replay of later commits
provides:
  - jev-proposed feature grouping through fold_group.group_features, with the rules deciding on every failure
  - a lookup copy of the skills roots that finds the installed jev client, the fold skill's own root first
affects: [29-09, 29-13]

# Actuals (#2632): chars/4 over the realized diff (git diff 9e7f067..HEAD, 22022 chars)
actuals:
  tokens: 5505
  tasks: 2
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "jev is reached only as a subprocess (argv list, one item per call, stdin JSON); no import of any jev module"
    - "a jev grouping is used only when every commit has an answer and passes the partition check; any other outcome leaves the rules in charge and names the reason in the report note"

key-files:
  created: []
  modified:
    - skills/ai-kit-commit-fold/scripts/fold_group.py
    - tests/test_ai_kit_commit_fold.py

key-decisions:
  - "jev is asked once per commit that has code paths: one choice item each, the candidate ids as options; docs-only commits are not sent and take the nearest earlier feature as the rules do"
  - "validate_partition refuses a commit placed twice, a commit left out, a commit outside the range, and a code file split from its test_<stem>.py; a shared path is not refused, the existing merge keeps it whole"
  - "the out-of-range guard stays (jev call g1): without it an assignment naming an unknown commit reaches a KeyError in the ownership loop instead of falling back to the rules"
  - "an old client (exit 2, `invalid choice`) gets the update note; any other unanswered commit gets `jev: no answer for c<i>`; the jev note comes first in the report note, the rule notes after it"
  - "fold.py is unchanged, so the GSD and superpowers adapters receive the jev proposal through the same group_features seam"

patterns-established:
  - "The jev item carries the commit subject, path names and candidate titles only, with the context capped at 1400 characters and titles at 200; a test pins the exact context text and the five item keys"

requirements-completed: [FLOW-01, JEV-06]

# Metrics
duration: unmeasured (no start timestamp recorded before the first task)
completed: 2026-11-04
status: complete
commits: 2
plan_head_before: 9e7f0673c34fa9f5a1d1b9fc208986509169f185
plan_head_after: 8930dcda549603817355474267a7793d0ccd6d81
---

# Phase 29 Plan 10: jev proposes the fold grouping, the rules decide

**group_features asks jev-fast-decision's ladder once per commit; a grouping is used only when every commit is answered and passes the partition check, otherwise the rules decide and the report names why**

## Performance

- **Tasks:** 2 of 2
- **Commits:** 2 task commits (measured with `git rev-list --count 9e7f067..HEAD` before this file was written)
- **Duration:** unmeasured

## Accomplishments

- `fold_group.py` gained the lookup copy (`JEV_ENTRY_REL`, `SKILLS_ROOTS`, `skills_roots`, `find_jev`), the item builder `jev_item`, the one-call `ask_jev`, the partition check `validate_partition` and `jev_features`. `group_features` now asks jev first and falls back to `rule_features`.
- The jev item holds only the commit subject, the path names and the candidate titles. The test records every stdin payload from a fake client and checks the five keys and the exact context text, and a marker written inside `a.py` never reaches the client.
- Report notes: `grouping: jev` on success; `jev: no answer for c<i>`, `jev: entry point missing; update jev-fast-decision (re-run the ai-kit installer)` and `jev rejected: <reason>` when jev does not decide.
- With jev absent, unreachable (the real client and a closed Laya port, no consent) or faked, the two-feature fixture still folds into the same two commits. A faked wrong split, a partial answer, an old client and a key-shaped subject (refused by the ladder's guard) all fall back to the same two commits.
- The skill's own skills root is searched first, so an installed copy beside the fold skill is found without any user-level install.

## Task Commits

1. **Task 1: a copied fold skill with jev beside it folds the two-feature checkpoint on jev's answer; without jev, or with no backend, the rules decide the same two commits** - `19c74c8` (feat)
2. **Task 2: wrong, partial, old and unsafe jev answers fall back to the rules** - `8930dcd` (test)

Task 2 needed no change to `fold_group.py`: the Task 1 implementation already covered every fallback path, so its commit holds tests only.

## Verification

- `python3 tools/run_unittest_parallel.py tests.test_ai_kit_commit_fold`: 53 tests ok (the nine `TestJevGrouping` cases plus the 44 existing ones).
- `python3 tmp/p29/10/scope.py test` (the plan's one `make test`): exit 0. Unit 82/82, then 1/1, 6/6, 23/23 and 1/1 modules passed; `tests/test_install.sh`: 45 passed, 0 failed.
- `ruff check`, `pylint` (10.00/10) and `pyright` clean on both touched files.
- `SKILLS_ROOTS` of `fold_group.py` equals `jev_ladder.py`'s, compared by parsed value; no `import jev_*` or `from jev` in the skill's scripts; `fold.py` has no commit from this plan.
- `python3 tmp/p29/10/scope.py close`: `clean`. The `reported (not this run)` lines are other sessions' processes and other plans' temp dirs, which are not counted.

## Jev Call Log

| id | question | answer | confidence | what was done |
|----|----------|--------|------------|---------------|
| g1 | keep or remove the out-of-range guard in `validate_partition` (choice) | keep (backend laya, top 0.7602, needs_fallback false; TypeSafe column not asked) | 0.76 | kept the guard: without it an unknown sha reaches a `KeyError` in the ownership loop; added the `commit not in range` case to the partition test |

The two lint fixes below (pylint too-many-locals, a pyright narrowing error) were decided without a jev call; the refactors were the only options that kept the behaviour, and the module tests confirmed it.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical] Out-of-range guard in `validate_partition`**
- **Found during:** Task 2, while settling the partition check's cases
- **Issue:** the plan does not list it, but without it an assignment naming a commit outside the range makes `validate_partition` raise `KeyError` in the ownership loop, and the fold would abort instead of falling back to the rules
- **Fix:** guard returns `commit not in range`; pinned by a case in `test_partition_check_names_each_refusal`
- **Files modified:** `skills/ai-kit-commit-fold/scripts/fold_group.py`, `tests/test_ai_kit_commit_fold.py`
- **Commit:** `19c74c8` (guard), `8930dcd` (test case)

**2. [Rule 3 - Blocking] Lint findings in the new code**
- **Found during:** Task 1, before the commit
- **Issue:** pylint `too-many-locals` (16/15) in `jev_features`; pyright `reportOptionalMemberAccess` in `ask_jev`
- **Fix:** the per-commit ask loop moved to `_ask_commits`; the row check in `ask_jev` returns early for a non-dict row or a missing `decided_by`. No behaviour change
- **Commit:** `19c74c8`

### Notes

- The in-process fold tests (`TestFoldTracer`, `TestFoldGuards`, `TestFoldMerges` and the rest) fold through `group_features`, which now searches the repo's own skills dir and finds the in-repo jev client. Each such fold makes one real call that returns no answer, because `JEV_LAYA_URL` is a closed port and `HOME` is a temp dir, so they still get the rule grouping. This is a real subprocess per fold, not a fake; it adds wall time that was not measured against a baseline.
- The `TestJevGrouping` cases use the fake client from `write_fake_jev` except for the real-client cases (no backend, key-shaped subject).

## Auth Gates

None.

## Known Stubs

None.

## Threat Flags

None. The jev call is a subprocess with an argv list and stdin JSON; no new network endpoint, auth path or file access beyond the existing lookup.

## Self-Check: PASSED

- Files exist: `skills/ai-kit-commit-fold/scripts/fold_group.py`, `tests/test_ai_kit_commit_fold.py`, `.planning/phases/29-logical-commit-folding-and-the-shared-jev-ladder/29-10-SUMMARY.md`.
- Commits exist in history: `19c74c8` (feat, Task 1), `8930dcd` (test, Task 2).
- `.planning/STATE.md` and `.planning/ROADMAP.md` are not modified by this plan.
