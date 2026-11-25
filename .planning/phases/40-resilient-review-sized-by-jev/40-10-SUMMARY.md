---
phase: 40-resilient-review-sized-by-jev
plan: 10
subsystem: ai-kit-spec-review (docs: loop diagram, apply-findings, fixer re-pass rule)
tags: [review, docs, diagram, classify, jev, fixer, fold]
requires: [40-09]
provides:
  - "references/loop-diagram.md: size-review, ping-lanes (exit 3 No lane left), flagged switch, fold check, lane-log merge, Approved (partial), Not reviewed and classify nodes; every next-iteration edge goes through the ping; a --no-cross-ai edge from Start straight to dispatch"
  - "references/apply-findings.md: Round context paragraph, the Step 3a template line - Mechanical re-pass: <MECHANICAL_TITLES>, the classify paragraph with the summaries-only sentence, the fold-finding note in Step 3b-skill"
  - "SKILL.md: Step 2 cap cell runs classify-disagreements --cap-reached --owner-out; Step 4 Classify first paragraph and Edits Applied row; Step 5 Cap reached and Escalation Required cells name the jev routes; the owner-items line below the Step 5 table"
  - "ai-kit-spec-review-fixer SKILL.md: one Editing rules row for the mechanical re-pass"
affects: [40-12]
key-files:
  modified:
    - skills/ai-kit-spec-review/references/loop-diagram.md
    - skills/ai-kit-spec-review/references/apply-findings.md
    - skills/ai-kit-spec-review/SKILL.md
    - skills/ai-kit-spec-review-fixer/SKILL.md
    - tests/test_lane_failure_text.py
    - tests/test_ai_kit_spec_review_fixer.py
decisions:
  - "Lean SKILL.md (orchestrator rule): the Classify first paragraph leaves out the clause that repeats lane-failure.md (owner items reach the final Surface); the owner-items line below the Step 5 table and the Step 4 owner-items wording keep the behaviour"
metrics:
  tasks: 3
  commits: 3
---

# Phase 40 Plan 10: diagram, apply-findings and fixer Summary

The optional loop diagram now shows sizing and the ping as the active cross-AI path only, the exit-3 `No lane left` stop,
the flagged-lane switch, the fold check, the lane-log merge, the `Approved (partial)` and `Not reviewed` outcomes and the
classify step; every next iteration passes through the ping. apply-findings.md gains the round context, the
`Mechanical re-pass:` template line, the classify step (summaries only to jev, at most one re-pass, CRITICAL or HIGH always
to the user) and the note that sends the fold finding to `superpowers:writing-plans` for that plan only. SKILL.md classifies
disagreements before acting on any fixer status and at the cap, and the Step 5 rows say what the owner sees for owner,
fixer and skipped items. The fixer gets one rule row: on a re-pass it edits only the named findings, and its escalation
conditions win over jev's class.

## Commits

| Task | Commit | Subject |
|------|--------|---------|
| 1 | 9a87b24 | docs(40-10): show sizing, ping, switch, fold check and partial outcomes in the loop diagram |
| 2 | 49055a5 | docs(40-10): add round context, the mechanical re-pass line, the classify step and the fold note to apply-findings |
| 3 | bc71c45 | docs(40-10): add the fixer's mechanical re-pass rule |

Cross-AI lanes (pi, router-env/my-coding), one per task from the start, each AIKIT-XAI `status=ok attempts=1`: Task 1 188 s,
Task 2 181 s, Task 3 111 s. No fix-up lane was needed.

## Verification (chunk executor, own runs)

- Task 1: active-path label 1, exit-3 edge 1, partial edge 1, three named tests 3; the only removed lines are the nine
  replaced edges; the dot block read whole matches the plan's steps 1-8.
- Task 2: re-pass template line 1, apply-findings summaries-only sentence 1, Edits Applied row 1, `--cap-reached` 1,
  `owner-items.json` 5, six named tests 6; the three pinned Step 2 status cells are byte-identical; the owner-items line is
  its own paragraph after the Step 5 table.
- Task 3: the rule row 1 (directly below the CRITICAL or HIGH row), `test_mechanical_repass_rule` 1.
- No added line names a phase, plan, decision or review id, or PROVISIONAL.
- Modules: `test_lane_failure_text` 25, `test_skill_text_history` 45, `test_ai_kit_spec_review_checklist` 13,
  `test_ai_kit_spec_runtimes_table` 63, `test_ai_kit_spec_review_fixer` 10, `test_quota_policy_text` 20,
  `test_cross_ai_docs_text` 39, `test_spec_chain_text` 40, `test_skill_frontmatter` 7: all ok.
- Gates after the plan (at bc71c45): unit + arch groups under the watchdog `200/200 modules passed` (peak 7, not killed);
  `make ruff`, `make pyright`, `make vulture`, `make pylint`, `make check-dogfood` exit 0 each. The Task 2 hook deferred
  `tests.test_ai_kit_gsd_curated_config_matrix` to push; it ran under the watchdog at bc71c45: 35 tests ok in 150.7 s.

## Deviations

- Lean SKILL.md: Task 2 step B leaves out one clause that repeats lane-failure.md (see decisions). The review SKILL.md body
  grew from 7352 to 7687 words (6540 before plan 40-09); the fixer SKILL.md body from 1725 to 1848. Open for the judge loop.
- The plan says to keep the diagram's pending-lane (hard tier) nodes; the diagram had none before this plan, so that truth
  has nothing to keep. Open for code review.
