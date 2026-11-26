---
phase: 40-resilient-review-sized-by-jev
plan: 06
subsystem: ai-kit-spec-review (jev classification of reviewer-fixer disagreements)
tags: [review, jev, fixer, disagreements, advisory]
requires: [40-05]
provides:
  - "ai_kit_spec/jev_review.py: summary_bullets, _match, disagreement_items (severity from the report, unmatched -> owner, cap-open items by report index), _summary_text (spans and unsafe tokens omitted, redact before and after the cut), finding_item, route_for (one SKIPPABLE guard; confident mechanical -> fixer below the cap; confident reviewer_wrong on MEDIUM/LOW -> skipped), classify_disagreements (find_jev once; not needed / absent / asked), cmd_classify_disagreements with --owner-out appends"
  - "review_reports._BULLET_RE accepts the merged report's optional ` (Reviewers: <keys>)` tag"
  - "cli.py wires classify-disagreements through register_parsers and COMMANDS"
affects: [40-07, 40-09, 40-10]
key-files:
  created:
    - skills/ai-kit-spec-review/ai_kit_spec/jev_review.py
    - tests/test_jev_review.py
  modified:
    - skills/ai-kit-spec-review/ai_kit_spec/review_reports.py
    - skills/ai-kit-spec-review/ai_kit_spec/cli.py
    - Makefile
    - .pre-commit-config.yaml
decisions:
  - "jev is reached only through jev_names.find_jev and ask_items(strict=True); STABLE_TOP is imported from lane_order; the run starts in the reviewed root (functools.partial(deps.run_fn, cwd=args.cwd))"
metrics:
  tasks: 2
  commits: 2
---

# Phase 40 Plan 06: jev disagreement classification Summary

`classify-disagreements` reads the merged review report and the fixer's Fix Summary, turns every escalated or skipped finding
(and, with `--cap-reached`, every open report finding) into one advisory jev item, and routes each to `owner`, `fixer` or
`skipped`. Severity always comes from the uniquely matched report finding, never from the fixer's restatement; a bullet with no
unique match goes to the owner (`no unique report match`) and is not sent. Any severity outside MEDIUM/LOW, a non-confident
answer or `owner_decision` goes to the owner; a confident `mechanical` goes to one more fixer pass while the iteration is below
the cap; a confident `reviewer_wrong` on MEDIUM/LOW is skipped with `jev: reviewer_wrong (<top>)`. Without jev every item goes to
the owner (`"jev": "absent"`); with nothing to send no lookup runs (`"not needed"`). Each item context carries only
`Severity / Finding / Fixer / Source` summaries with backtick spans, quoted strings, path-like, `key=value`, `host:port` and long
hex or digit tokens replaced by `[omitted]` and secrets redacted before and after the cut. `--owner-out` appends each owner entry
as one JSON line per call. The merged report parser now reads the renderer's own reviewer tag.

## Commits

| Task | Commit | Subject |
|------|--------|---------|
| 1 | fc87468 | feat(40-06): classify reviewer-fixer disagreements with jev before the owner |
| 2 | ade3615 | test(40-06): pin jev disagreement routes, report severity and the payload |

Cross-AI lanes (pi, router-env/my-coding), one per task from the start, each AIKIT-XAI `status=ok attempts=1`: Task 1 582 s,
Task 2 325 s. No fix-up lane was needed.

## Verification (chunk executor, own runs)

- Task 1 acceptance: the seven `def` lines 7, `STABLE_TOP` not redefined (rg exit 1), no `SKILLS_ROOTS|JEV_ENTRY_REL|usage_limited`
  (exit 1), `functools.partial(deps.run_fn, cwd=args.cwd)` 1, the reviewer-tag group in `_BULLET_RE` 1, `jev_review` in cli.py 3,
  `test_jev_review` in the Makefile 1, subject ok.
- Task 2 acceptance: `def test_` 12, `add_argument("--owner-out"` 1, `review_log.append_event` 1, no `SERIOUS =` (exit 1), the
  three named tests 3, subject ok.
- No line over 100 characters; the test module ends with the main guard; no real jev or host CLI in tests (fake `run`, temporary
  `own_root`, patched `find_jev`).
- `tests.test_jev_review` 12, `tests.test_catalog_jev_names` 13, `tests.test_ai_kit_spec` 703 (TestParseFindings unchanged),
  `tests.test_gate_scope` 62, `tests.test_arch` 118, `tests.test_lane_settings` 50, `tests.test_arch_hardcoded_models` 23: all ok.
- Gates after the plan: unit + arch groups under the watchdog `197/197 modules passed` (peak 7 runner processes, not killed);
  `make ruff`, `make pyright`, `make vulture`, `make pylint`, `make check-dogfood` exit 0 each; the commit-deferred
  `tests.test_ai_kit_gsd_curated_config_matrix` 35 tests ok (152.6 s, under the watchdog, peak 0).

## Deviations

- The plan's cli.py and TestParseFindings line numbers were stale (import block 11-38, register 529, `_COMMANDS` 1512/1544,
  TestParseFindings 3583); the lane got corrected anchors.
- Task 2 (lane): `test_payload_holds_summaries_only` checks each context with `assertRegex` (a search) instead of the plan's
  `re.fullmatch`; the banned-material and `[omitted]` assertions are as written. Open for code review: anchor the shape check.
