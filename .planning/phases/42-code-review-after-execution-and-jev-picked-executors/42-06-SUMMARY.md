---
phase: 42-code-review-after-execution-and-jev-picked-executors
plan: 06
subsystem: ai-kit-spec-review (jev_review, code_review) and ai-kit-spec-execute-superpowers (dispatch, code review)
tags: [jev, lane-result, code-review, fit, adapter]
requires: [42-05]
provides:
  - "jev_review.py: classify-execute-result (done, partial, another_round; allowlisted status tokens only; handover status) and classify-findings (fits, higher, lower from the severity and five labels only; CRITICAL and HIGH never lowered)"
  - "code_review.py: SEVERITY_ORDER, fit_severity, apply_fit, check_fit, finding_labels, render_adjusted, the Labels tail in CODE_REVIEW_PROMPT, code-review-verdict --fit-json; the summary-text redaction helpers now live here"
  - "dispatch-external-cli.md ok branch and the SKILL.md native branch call classify-execute-result; code-review.md fits each lane report before the merge and passes the rows to the verdict"
affects: [42-09, 42-10, 42-11]
key-files:
  modified:
    - skills/ai-kit-spec-review/ai_kit_spec/jev_review.py
    - skills/ai-kit-spec-review/ai_kit_spec/code_review.py
    - skills/ai-kit-spec-execute-superpowers/references/dispatch-external-cli.md
    - skills/ai-kit-spec-execute-superpowers/references/code-review.md
    - skills/ai-kit-spec-execute-superpowers/SKILL.md
    - tests/test_jev_review.py
    - tests/test_code_review.py
    - tests/test_ai_kit_spec_superpowers.py
decisions:
  - "Import cycle (orchestrator decision): OMITTED, _SPAN_RE, _UNSAFE_TOKEN_RE and _summary_text moved from jev_review.py into code_review.py; jev_review imports code_review and re-imports the four names (noqa F401, pylint disable-next unused-import), so every old name stays importable from jev_review; secret_shapes.py untouched"
metrics:
  tasks: 3
  commits: 3
---

# Phase 42 Plan 06: lane-result classification Summary

Before a loop continues, jev classifies each lane result, with a deterministic default when jev is absent, errors or
answers low, and the output names who decided. An execute run's status tokens (implementer status, runner status,
finding codes, coverage; anything outside the allowlists dropped) give `done`, `partial` or `another_round`; the class
starts no dispatch and only turns a `DONE` into `DONE_WITH_CONCERNS` when the class is not `done`. Each code-review
finding's severity and five labels give `fits`, `higher` (one level up) or `lower` (MEDIUM to LOW only); CRITICAL and
HIGH are never lowered. The fit runs per lane before the merge, so the merged report carries the fitted severities,
and `code-review-verdict --fit-json` recomputes every row and exits 2 when a row breaks the rule or a CRITICAL or HIGH
result is missing from the report.

## Commits

- `fedd9c3` feat(42-06): classify execute lane results through jev with the status default (Task 1)
- `8138b57` feat(42-06): fit review findings through jev and re-check the fit in the verdict (Task 2)
- `2956cb1` docs(42-06): fit each lane's code-review findings before the merge (Task 3)

## Lane history

- Task 1: per-task fix-up lane `42-06-fix-a` (pi router-env/my-coding), status ok, 587 s, one commit; hook 168/168 +
  22/22 uv.
- Task 2: lane `42-06-fix-b`, status ok, 1354 s, one commit; hook 163/163 + 21/21 uv.
- Task 3: lane `42-06-fix-c`, status ok, 598 s, one commit; hook 29/29.
- The Task 1 and Task 2 commit hooks deferred `tests.test_ai_kit_gsd_curated_config_matrix` to push (over the 60 s
  commit budget). I ran it myself under the guard at clean HEADs: at `fedd9c3` 35 tests ok in 149.5 s, at `8138b57`
  35 tests ok in 151.2 s (guard peak 0, no kill). The Task 3 hook deferred nothing (the lane's statement, not raw
  hook output; no `tests/*e2e*.py` module names code-review.md or the superpowers test module).
- Removed test lines over the plan range: the renamed classifier pin, the old real-`ai-kit-spec.py` `TOOLS_PY` (replaced
  by the jev-refusing wrapper) and the old prompt bullet (extended to the labelled bullet); none weakens an assertion.

## Checks (orchestrator chunk, own runs)

- Acceptance greps of all three tasks: every EXPECT value met; `rg -c "jev_names|jev_review"` on code_review.py prints
  nothing; the four moved definitions exist only in code_review.py.
- Import cycle gone: `tmp/run-2026-11-23/p42-06/cycle_check.py` (fresh interpreters, `-I`) prints `jev_review-first
  rc=0` and `code_review-first rc=0` with jev_review importing code_review (it printed the same before the move only
  because the import did not exist yet).
- Modules: `test_jev_review` (59 tests), `test_code_review` (57), `test_ai_kit_spec_superpowers` (208),
  `test_adapter_single_definitions` (11), `test_skill_text_history` (45), `test_arch` (118),
  `test_arch_hardcoded_models` (23), `test_lane_settings` (58): all ok.
- Scope from the plan base `d458ea8`: exactly the eight `files_modified` paths. Added shipped lines carry no phase,
  decision or requirement id and no date; `tests/fixtures/no_hardcoded_models_baseline.json` unchanged.
- Adapter SKILL.md: 297 lines before and after (one existing line edited); body words 3931 -> 3956.

## Deviations

- Orchestrator rule (import cycle): the move of the four redaction names into code_review.py happened inside Task 2
  (both files are in this plan's scope); ruff's isort set the re-import's name order (`_SPAN_RE, _UNSAFE_TOKEN_RE,
  OMITTED, _summary_text`).
- Plan text versus code: code_review.py's imports were one line, not the two the plan quoted; `render_report` takes a
  `tag` parameter (`render_adjusted` uses its default).
- `finding_labels` tests feed the parsed `why` text, which ends without the bullet's final period (the shape
  `normalize_report` produces); the CLI test proves labels reach jev from a real normalized report.
- Lint-driven wrapping of the plan's long literals and docstrings (content identical); `tests/test_jev_review.py`
  imports `pathlib` for the template read.
- Task 1's order pin reads "`implementer-status` comes before `classify-execute-result`" (`assertLess`), the only
  layout that works because the classification reads `$STATUS`.
- Task 3's two new transition tests assert slightly more than the plan lists (the merged report's reviewers line, the
  full state record, `owner_wait`), following the inherited tests' pattern.
