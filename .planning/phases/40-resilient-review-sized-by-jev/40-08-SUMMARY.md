---
phase: 40-resilient-review-sized-by-jev
plan: 08
subsystem: ai-kit-spec-review (superpowers fold-step check)
tags: [review, fold, superpowers, merge-reports]
requires: [40-07]
provides:
  - "ai_kit_spec/fold_check.py: FOLD_SKILL, FOLD_TODO, EXTRA_TAG, FINDING_LINE, _real_lines (CommonMark fences: closes only on the same character, a run at least as long, no info string), fold_finding (last real task section, bounded at the next level 1-3 heading), wants_check, read_extra_findings (argparse type, fail closed), cmd_check_fold_step (exit 2 = not checked), register_parsers, COMMANDS"
  - "cli.py: check-fold-step registered; merge-reports --extra-findings merged FIRST under the tag fold-check in both the no-log and the lane-log merge, never a lane"
affects: [40-09, 40-10, 40-11, 40-13]
key-files:
  created:
    - skills/ai-kit-spec-review/ai_kit_spec/fold_check.py
    - tests/test_fold_check.py
    - tests/fixtures/fold_step/without_fold.md
    - tests/fixtures/fold_step/with_fold.md
    - tests/fixtures/fold_step/fold_in_fence.md
    - tests/fixtures/fold_step/fold_under_self_review.md
    - tests/fixtures/fold_step/fold_in_long_fence.md
  modified:
    - skills/ai-kit-spec-review/ai_kit_spec/cli.py
    - skills/ai-kit-spec-review/evals/files/active/project/docs/superpowers/plans/demo.md
    - skills/ai-kit-spec-review/evals/files/no-config/project/docs/superpowers/plans/demo.md
    - Makefile
    - .pre-commit-config.yaml
decisions:
  - "The fold wording is a constant in fold_check.py (no cross-skill import); a test pins it against the superpowers adapter's SKILL.md"
metrics:
  tasks: 3
  commits: 3
---

# Phase 40 Plan 08: fold-step check Summary

`check-fold-step --doc <path> --framework <id|none> --archetype <a>` prints a two-line HIGH finding (`Plan has no fold step`,
located `<doc as given>, last ### Task`, with a `Required:` edit naming `### Task <n+1>: Fold the plan's commits
(ai-kit-commit-fold)`) only for a superpowers plan whose last real task names no fold step; fenced blocks and trailing non-task
sections never count. `merge-reports --extra-findings <file>` merges that file's bullets first under the tag `fold-check`, so a
clean merge becomes `Issues Found`, a reviewer finding at the same location keeps only its tag, and the file never joins a lane
list. An unreadable or unparseable extra file exits 2 before any output. The active and no-config eval plans now end with the fold
task, so their approval evals stay valid.

## Commits

| Task | Commit | Subject |
|------|--------|---------|
| 1 | a79df84 | feat(40-08): add check-fold-step and merge-reports --extra-findings |
| 2 | b0289a9 | test(40-08): pin the fold-check edges and the extra-findings merge |
| 3 | 44f5d0e | test(40-08): add the fold task to the review eval plans and pin the adapter wording |

Cross-AI lanes (pi, router-env/my-coding), one per task from the start, each AIKIT-XAI `status=ok attempts=1`: Task 1 384 s
(its hook ran the full unit and arch groups), Task 2 88 s, Task 3 157 s. No fix-up lane was needed.

## Verification (chunk executor, own runs)

- Task 1 acceptance: `FOLD_TODO` line 1, `fold_check.` in cli.py 3, `args.extra_findings or []` 2, `test_fold_check` in the
  Makefile 1 and in `.pre-commit-config.yaml` 2, no other skill or `cli` import (exit 1), `Location: {doc}, last ### Task.` 1,
  subject ok; `without_fold.md` is a byte copy of the active eval plan (cmp 0); the cli.py diff is exactly the five named edits.
- Task 2 acceptance: the five named tests 5, the four-backtick opening line 1, the `with_fold.md` fold task line 1,
  `## Self-Review` 1, subject ok; the exact no-log failure line `### Status: Failure — a` is asserted as written.
- Task 3 acceptance: the fold task line 1 in each eval plan, the execute-only plan unchanged (exit 1), the two wording tests 2;
  the module holds 18 tests and ends with the main guard.
- No added line names a phase, plan or decision id.
- `tests.test_fold_check` 18, `tests.test_skill_evals_shape` 6, `tests.test_spec_chain_text` 40,
  `tests.test_skill_text_history` 45, `tests.test_ai_kit_spec` 703, `tests.test_arch` 118, `tests.test_gate_scope` 62: all ok.
- Gates after the plan (at 44f5d0e): unit + arch groups under the watchdog `199/199 modules passed` (peak 8 runner processes,
  not killed); `make ruff`, `make pyright`, `make vulture`, `make pylint`, `make check-dogfood` exit 0 each; the commit-deferred
  `tests.test_ai_kit_gsd_curated_config_matrix` 35 tests ok (159.5 s, under the watchdog).

## Deviations

- The plan's cli.py line numbers were stale (import block 11-39, register block 522-531, `_cmd_merge_reports` 999,
  `_merge_with_lane_log` 1034, `_COMMANDS` 1514); the lanes got corrected anchors. No other deviation.
