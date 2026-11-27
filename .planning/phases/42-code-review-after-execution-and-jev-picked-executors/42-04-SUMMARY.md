---
phase: 42-code-review-after-execution-and-jev-picked-executors
plan: 04
subsystem: ai-kit-spec-review (code-review core)
tags: [code-review, verdict, normalization, lens, jev, classify]
requires: [42-03]
provides:
  - "ai_kit_spec/code_review.py: CODE_REVIEW_CAP = 3, BLOCKING, SEVERITIES, SUPERPOWERS_SEVERITY, TITLE_CHARS, INCOMPLETE, MISSING_LENS, CONTROL_PATH, REVIEW_LENS, UI_LENS, CODE_REVIEW_PROMPT, IncompleteReport, Verdict, normalize_report, render_report, review_verdict, review_paths, missing_lenses, register_parsers, COMMANDS"
  - "ai-kit-spec.py subcommands: code-review-prompt, code-review-normalize (exit 0, 4 incomplete, 2 unreadable), code-review-paths (JSON list; missing-lens and dropped control-character lines on stderr), code-review-verdict (exit 0 pass, 1 fix, 3 cap stop, 4 incomplete, 2 bad input)"
  - "jev_review.py: CODE_CLASSIFY_QUESTION, CODE_CLASSES, NO_MATCH, ClassifyOptions, finding_item(..., kind), classify_disagreements(items, env, run, opts), classify-disagreements --kind code|document"
affects: [42-05, 42-06]
key-files:
  created:
    - skills/ai-kit-spec-review/ai_kit_spec/code_review.py
    - tests/test_code_review.py
  modified:
    - skills/ai-kit-spec-review/ai_kit_spec/cli.py
    - skills/ai-kit-spec-review/ai_kit_spec/jev_review.py
    - tests/test_jev_review.py
    - Makefile
    - .pre-commit-config.yaml
decisions:
  - "The reviewer prompt's free-text change description goes through jev_review._summary_text (imported, not copied), so the prompt carries the redacted summary only and never code or a diff (orchestrator rule for this run)"
metrics:
  tasks: 3
  commits: 3
---

# Phase 42 Plan 04: code-review core Summary

`code_review.py` holds the code-review loop's pure parts. `normalize_report` reads an ai-kit report or a superpowers
code-reviewer report (`#### Critical` as CRITICAL, `#### Important` as HIGH, `#### Minor` as LOW, location from an
indented `File:` line or the first `path:line`, an unlocated finding tagged with the raw report's file stem) and
refuses an incomplete one: no Status line and no Assessment line with a severity heading, a mixed shape, a Failure
status, a CRITICAL or HIGH section with text but no parsed finding and no explicit empty marker, a rendered report
that does not parse back, or invalid UTF-8. `review_verdict` passes when no CRITICAL or HIGH finding is open, gives
`fix` below the cap of 3 and `cap_stop` at it; MEDIUM and LOW are listed and never block; the Status line never
decides. `review_paths` lists `git diff --name-only -z --diff-filter=d` losslessly (sorted, unique, a leading `-`
path as `./<path>`, a bad revision refused before git runs); the CLI drops a path holding a control character with a
stderr note and names a missing `ponytail-review` (always) or `impeccable` (UI path) lens from the skill discovery.
`classify-disagreements --kind code` sends only the severity, the redacted title and the source token with
code-worded classes; routing, the CRITICAL and HIGH exception and the no-jev path are unchanged; a summary line that
is no summary bullet exits 3 under `--kind code`; the default kind keeps today's item text.

## Commits

- `1419d66` feat(42-04): code-review report normalization, pass rule and cap on ai-kit-spec.py (Task 1)
- `333a651` feat(42-04): lossless changed paths and the missing-lens note for the code review (Task 2)
- `a42c49b` feat(42-04): classify code-review gray areas with code-worded classes (Task 3)

## Lane history

- Task 1: per-task fix-up lane `42-04-fix-a` (pi router-env/my-coding), status ok, 1036 s, one commit; first commit
  attempt refused by the ruff hook (RUF059 in the new test), fixed by the lane; hook 231/231 modules plus uv modules;
  the hook deferred `tests.test_ai_kit_gsd_curated_config_matrix` to push.
- Task 2: lane `42-04-fix-b`, status ok, 550 s, one commit; hook 163/163 plus 21/21 under uv; same deferral.
- Task 3: lane `42-04-fix-c`, status ok, 814 s, one commit; hook 163/163 plus 21/21 under uv; same deferral.

## Checks (orchestrator chunk, own runs)

- Acceptance greps of all three tasks: every EXPECT value met; scope from the plan base 4fe6f18 lists only the
  plan's seven paths; `task_classification.py` untouched; no superpowers plugin or skills/ai-kit-commit-fold/ path.
- Makefile and `.pre-commit-config.yaml` add only `tests.test_code_review`; added shipped lines carry no phase,
  decision or requirement id and no date; `tests/fixtures/no_hardcoded_models_baseline.json` unchanged.
- Modules: `tests.test_code_review` (42 tests), `tests.test_jev_review` (41), `tests.test_ai_kit_spec` (705),
  `test_gate_scope`, `test_arch`, `test_arch_hardcoded_models`, `test_skill_text_history`: all ok.
- Deferred e2e `tests.test_ai_kit_gsd_curated_config_matrix` run under the guard after Task 1 and after Task 3:
  35 tests ok each time.
- No SKILL.md changed.

## Deviations

- Orchestrator rule applied in Task 1: `cmd_code_review_prompt` formats `--description` through
  `jev_review._summary_text(..., TITLE_CHARS)` (imported, the form executor_pick.py uses); a `TestReviewPrompt`
  assertion pins `Change: fix [omitted] retry` for `--description "fix src/a.py:3 retry"`.
- `_superpowers_findings` asserts its heading match is not None (pyright narrowing; no behaviour change).
- `TestReviewPaths.setUp` creates both `src/` and `SRC/` (both files are distinct on a case-sensitive filesystem).
- `CONTROL_PATH` is two adjacent literals (line length); the emitted line is identical.
- The Task 3 CLI test helper returns `(code, stdout, stderr, calls)` because the malformed-summary case needs the exit
  code and stderr; pyright needed `str | None` annotations on two helper parameters.
- The SKILL.md and `references/lane-failure.md` invocations of `classify-disagreements` do not pass `--kind code` yet;
  the adapter's code-review reference (a later plan) calls it.
