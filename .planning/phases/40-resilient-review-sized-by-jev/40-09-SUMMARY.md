---
phase: 40-resilient-review-sized-by-jev
plan: 09
subsystem: ai-kit-spec-review (docs: lane failure, ping, partial status, jev)
tags: [review, docs, lane-failure, ping, switch, partial, sizing, fold]
requires: [40-08]
provides:
  - "references/lane-failure.md: Ping before a round, Flagged-lane switch (blocked-until read through --blocked-status <pool>), Partial status, Reasons (13 rows locked to REASONS), jev classes and sizing, Commands, Evidence"
  - "SKILL.md: Size the review, Ping before the round, --lane-log line, Flagged lane first, edited fails-closed sentence, one-exception sentence, Fold check, Step 1.5 merge rule, Step 2 partial and not-reviewed rows, Step 5 partial row and Judged-by sentence, Single reviewer row, edit-lens and Cleanup sentences, narrowed hard rule, Evidence bullet"
  - "references/cross-ai-dispatch.md: switch-first and logged-merge sentences, resume argv --lane-log/--round, resume payload quota_json/lane_log/framework_id/doc_archetypes, switch-first resume branch, fold check before the resume merge, Then size the review paragraph"
  - "ai-kit-cross-ai SKILL.md: section 8 owner-configured exception, section 1 pointer"
affects: [40-10, 40-12]
key-files:
  created:
    - skills/ai-kit-spec-review/references/lane-failure.md
    - tests/test_lane_failure_text.py
  modified:
    - skills/ai-kit-spec-review/SKILL.md
    - skills/ai-kit-spec-review/references/cross-ai-dispatch.md
    - skills/ai-kit-cross-ai/SKILL.md
    - Makefile
    - .pre-commit-config.yaml
decisions:
  - "Lean SKILL.md (orchestrator rule): the Size-the-review and Ping-before-the-round paragraphs carry no detail that lane-failure.md holds (signals and jev sizing, round-1 versus later-round cadence)"
metrics:
  tasks: 3
  commits: 3
---

# Phase 40 Plan 09: lane-failure docs Summary

The new reference `references/lane-failure.md` documents the ping before each round, the flagged-lane switch with the
blocked-until reading through the runner's `--blocked-status <pool>`, the partial status (`Approved (partial)`,
`Failure — not reviewed`), the 13 failure reasons (a test locks the table to `REASONS`, with a non-vacuity case), jev's
summaries-only classes and review sizing, and the six verbatim commands. The review SKILL.md reaches every new subcommand
from its steps (sizing, ping with its exit 3 and exit 2 stops, the serialized flagged switch, the fold check, the logged
merge, the partial rows) and narrows the hard rule to unflagged lanes; the old blanket wording fails a test. The dispatch
reference gains the switch-first exit and resume branches, the extended resume payload and the sizing point; the cross-AI
caller contract names the one owner-configured exception without switch wording.

## Commits

| Task | Commit | Subject |
|------|--------|---------|
| 1 | c6bd8bb | docs(40-09): add references/lane-failure.md with its reason-table lock |
| 2 | 4d76a3b | docs(40-09): wire sizing, ping, flagged switch, fold check and partial merge into SKILL.md |
| 3 | c9371fa | docs(40-09): add the logged exit and resume branches, partial rows, the sizing point and the cross-AI exception |

Cross-AI lanes (pi, router-env/my-coding), one per task from the start, each AIKIT-XAI `status=ok attempts=1`: Task 1 335 s
(its hook ran the full unit and arch groups), Task 2 259 s, Task 3 224 s. No fix-up lane was needed.

## Verification (chunk executor, own runs)

- Task 1: summaries-only sentence 1, listings (Makefile 1, `.pre-commit-config.yaml` 2), no id, `router-env/`, `referee-`,
  PROVISIONAL or date in lane-failure.md, seven headings in order, 13 reason rows, `--blocked-status <pool>` 1; every output
  line, flag and exit code the text quotes was checked against the code before the lane ran.
- Task 2: narrowed rule 1, pinned sentence 1, `### Status: Approved (partial)` 2, `references/lane-failure.md` 8,
  `so Step 1.5 fails closed.` gone, `for one lane at a time, never two at once` 1, the three pinned Step 2 rows byte-identical.
- Task 3: exception sentence 1, section 1 pointer 1, `size-review` 1, `switch-lane` 2, `merge-reports --lane-log` 3,
  switch-first bullet 1, `quota_json "$QUOTA_JSON"` 1, five named tests 5; the Cap reached and Escalation Required cells
  unchanged for plan 40-10; the dispatch and cross-AI diffs hold only the named lines.
- Modules: `test_lane_failure_text` 16, `test_skill_text_history` 45, `test_gate_scope` 62, `test_quota_policy_text` 20,
  `test_spec_chain_text` 40, `test_ai_kit_spec_review_checklist` 13, `test_ai_kit_spec_runtimes_table` 63,
  `test_cross_ai_docs_text` 39, `test_ai_kit_spec_review_fixer` 9, `test_cross_ai_skill_text` 40,
  `test_spec_config_flow_text` 40, `test_cross_ai_settings_text` 23, `test_ai_kit_spec_goal_prompt_render` 93,
  `test_ai_kit_spec_goal_prompt_cli` 50: all ok.
- Gates after the plan (at c9371fa): unit + arch groups under the watchdog `200/200 modules passed` (peak 7, not killed);
  `make ruff`, `make pyright`, `make vulture`, `make pylint`, `make check-dogfood` exit 0 each. The Task 1 hook deferred
  `tests.test_ai_kit_gsd_curated_config_matrix` to push; it ran under the watchdog at bc71c45 (after plan 40-10): 35 tests ok
  in 150.7 s.
- The lane-failure.md literals were also checked after the lanes: ping exit 3 (`PING_EXIT_NO_LANE`), exit 2 from the CLI's
  `ConfigError` handler, `QUOTA_TTL_SECONDS = 3600`, `STABLE_TOP = 0.80`, and the `not judged` entry shape in review_log.py.

## Deviations

- Lean SKILL.md (orchestrator rule for this run): Task 2 steps 2 and 3 use shorter paragraphs. Size the review drops the
  sentence on signals and jev sizing; Ping before the round drops the round-1 and later-round sentence. Both sentences stay
  in lane-failure.md and in the dispatch reference's sizing paragraph; no test or acceptance check names them. The review
  SKILL.md body still grew from 6540 to 7352 words (cross-AI SKILL.md 7769 to 7803): an open item for the judge loop.
- The new SKILL.md paragraphs are single long lines; the two inside Step 1's numbered list sit without a blank line, so they
  render as part of that list item. Wording such as "today's path" is copied from the plan; left for the judge loop.
