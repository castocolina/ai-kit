---
phase: 42-code-review-after-execution-and-jev-picked-executors
plan: 05
subsystem: ai-kit-spec-execute-superpowers (code review step)
tags: [code-review, adapter, fold, state, lanes]
requires: [42-04]
provides:
  - "references/code-review.md: the capped code-review loop (start, session-model, resolve and ping, one lane, collect, verdict, cap stop answer, gray areas) with the durable state.json round record"
  - "SKILL.md heading `## Code review (after the final review, before Step 5)` (MANDATORY pointer), Step 4 and Step 5 trigger edits, CODE_REVIEW_ROUND cleared and the run folder removed at a done fold"
  - "resolution-stops.md `### Code review cap stop`; fold-step.md trigger and the state gate (pass or owner_accepted, reviewed_head tree equals HEAD's tree)"
  - "tests: TestCodeReviewStep (pins), TestCodeReviewTransitions (published blocks on fake lanes), TestFoldStep fixture and refusal tests"
affects: [42-06, 42-09, 42-11]
key-files:
  created:
    - skills/ai-kit-spec-execute-superpowers/references/code-review.md
  modified:
    - skills/ai-kit-spec-execute-superpowers/SKILL.md
    - skills/ai-kit-spec-execute-superpowers/references/resolution-stops.md
    - skills/ai-kit-spec-execute-superpowers/references/fold-step.md
    - tests/test_ai_kit_spec_superpowers.py
decisions:
  - "The Round inputs prose states the description redaction of code-review-prompt (first 80 characters, paths and quoted text become [omitted]); the start block keeps the `<one line: what the plan built>` placeholder (orchestrator rule for this run)"
metrics:
  tasks: 3
  commits: 3
---

# Phase 42 Plan 05: code review step Summary

After subagent-driven-development's final whole-branch review the adapter runs a code review step before the fold:
at most 3 rounds on spec review's lanes (config-status `active`: probe-quota, resolve-reviewers, ping-lanes, one
dispatch-reviewer per lane with the changed paths as `--files`, the native lens command for a native lane, switch-lane
only for a flagged lane; `none`: the session model's reviewer; any other status is an owner stop, never native).
Every report goes through `code-review-normalize`; failed or incomplete lanes leave a partial merged report with a
`Judged by:` line; `code-review-verdict --cap 3` decides pass (no CRITICAL or HIGH open), fix (owner answers first,
gray items through `classify-disagreements --kind code`, one fix implementer through Step 3's dispatch block with
the pinned injection, `FIX_ROUND` unchanged) or cap stop. `state.json` records `{round, reviewed_head, state}`
atomically; a re-invoke re-enters at the start block. The fold block refuses unless the review passed or was
accepted for the tree of the current HEAD.

## Commits

- `ae9950b` docs(42-05): add the capped code review step after the final review (Task 1)
- `897d541` docs(42-05): list the code review cap stop and bind the fold to the reviewed head (Task 2)
- `9e54cc8` test(42-05): run the code review round blocks on fake lanes (Task 3)

## Lane history

- Task 1: per-task fix-up lane `42-05-fix-a` (pi router-env/my-coding), status ok, 532 s, one commit; hook 29/29.
- Task 2: lane `42-05-fix-b`, status ok, 410 s, one commit; hook 29/29.
- Task 3: lane `42-05-fix-c`, status ok, 652 s, one commit; hook 4/4. The lanes report no e2e module deferred to push
  (their final messages, not raw hook output); no `*e2e*` test module names the files this plan changed.

## Checks (orchestrator chunk, own runs)

- Acceptance greps of all three tasks: every EXPECT value met; SKILL.md 293 -> 297 lines, body words 3857 -> 3931;
  code-review.md has 7 bash blocks; fold-step.md's `for n in SKILL_DIR PLAN_FILE FOLD_BASE CWD; do` and
  `FOLD_PY=""` lines are byte-unchanged; scope from the plan base 1a9df9d lists only the five plan paths.
- Added shipped lines carry no phase, decision or requirement id and no date;
  `tests/fixtures/no_hardcoded_models_baseline.json` unchanged.
- Modules: `tests.test_ai_kit_spec_superpowers` (203 tests), `test_adapter_single_definitions`,
  `test_skill_text_history`, `test_flow_docs`, `test_fold_check`, `test_lane_failure_text`, `test_skill_evals_shape`,
  `test_arch`: all ok.
- Before the lanes, a probe (scratch HOME, temporary repo, no config) confirmed the collect and verdict semantics:
  `merge-reports --lane-log` on a fresh round log gives `Judged by: fake/lane-a; not judged: fake/lane-b (real_error)`
  with `### Status: Approved (partial)`; `config-status` prints `none` first; normalize writes no output file on exit 4.

## Deviations

- Orchestrator rule: the `## Round inputs` clause names the description redaction; the placeholder stays byte for byte.
- The plan's quoted snippets carried `\"` escapes inside code spans; the reference uses plain quotes (the pinned verdict
  line and the JSON the start block reads need them).
- The start block's third line is `CR_DIR=...; mkdir -p "$CR_DIR"` and `N` comes from the state case (the task's own
  start-block list); the other six blocks open with the full loader including `N="$CODE_REVIEW_ROUND"`.
- `## Lanes` holds three `###` subsections (Resolve and ping, One lane, Collect); a one-line intro under
  `## Start a round` mirrors fold-step.md; two bash comments carry the task's parentheticals.
- fold-step.md: the plan's explanatory parenthetical after the `if` line is not written into the shell (it is not
  valid shell); the same-tree rewrite is proven by `test_same_tree_rewrite_still_folds`.
- Tests: `TestFoldStep` keeps the state path as `self.cr_state`; `TestCodeReviewTransitions` creates `CR_DIR` in
  setUp, `_lanes` takes `(text, exit)` pairs, the class docstring wraps for E501; the verdict block itself exits 0 for
  verdicts 0/1/3, so tests read the `VERDICT_EXIT=<n>` line and the state record.
