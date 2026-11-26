---
phase: 40-resilient-review-sized-by-jev
plan: 11
subsystem: ai-kit-spec-review and ai-kit-spec-review-fixer (evals)
tags: [evals, review, lane-failure, ping, partial, jev, fixer]
requires: [40-10]
provides:
  - "ai-kit-spec-review evals.json: edge-flagged-lane-quota-switch, edge-ping-replaces-blocked-lane, precise-partial-report-judged-lanes, precise-jev-classifies-disagreement (15 -> 19)"
  - "evals/files/flagged/project/aikit/config.toml (double mode, review-free flagged usage_limited with pool fake:free, then review-second and review-third) and a byte copy of the active demo plan with its fold task"
  - "ai-kit-spec-review-fixer evals.json: precise-mechanical-repass-edits-listed (7 -> 8)"
affects: [40-12]
key-files:
  created:
    - skills/ai-kit-spec-review/evals/files/flagged/project/aikit/config.toml
    - skills/ai-kit-spec-review/evals/files/flagged/project/docs/superpowers/plans/demo.md
  modified:
    - skills/ai-kit-spec-review/evals/evals.json
    - skills/ai-kit-spec-review-fixer/evals/evals.json
decisions: []
metrics:
  tasks: 2
  commits: 2
---

# Phase 40 Plan 11: evals Summary

ai-kit-spec-review gains four evals for the new behaviour: a flagged lane that hits its quota switches to review-third in
the same iteration, a ping that fails with auth replaces review-second before round 1, an auth failure gives an
`Approved (partial)` report with the `Judged by:` line, and jev's classes route a fixer escalation to one mechanical
re-pass and a skip to `jev: reviewer_wrong (0.85)`. The three lane evals share a new flagged roster. The fixer gains one
eval: a re-pass edits only the finding its `Mechanical re-pass:` line names.

## Commits

| Task | Commit | Subject |
|------|--------|---------|
| 1 | b059f05 | test(40-11): add the lane-failure, partial-report and jev evals of ai-kit-spec-review |
| 2 | cd4e6fb | test(40-11): add the fixer's mechanical re-pass eval |

Cross-AI lanes (pi, router-env/my-coding), one per task from the start, each AIKIT-XAI `status=ok attempts=1`: Task 1
169 s, Task 2 54 s. No fix-up lane was needed.

## Verification (chunk executor, own runs)

- Before the lanes, every quoted output line, field and command in the five evals was checked against the code and text at
  HEAD (ping and switch event fields, the `Judged by:` / `not judged:` format, `Approved (partial)`, the jev skip format,
  the `Mechanical re-pass:` line, the Step 1 switch-before-exit rule, Cleanup keeping the folder): no correction needed.
  The planned config.toml was loaded through the real config code under a scratch HOME: no lane-setting problem, pool
  `fake:free`, mode double, a review ladder of three, no warning.
- Task 1: 19 evals; the four entries equal the plan text field for field (full setup sentence in each lane prompt), in key
  order, after the old 15; the diff is additions only, so `edge-refused-lane-exit-65` is unchanged (its guard phrase
  counts 1); config.toml has no comment line; demo.md is a byte copy of the active demo plan; the four-id count is 4.
- Task 2: 8 evals; the entry equals the plan text, with single `\n` escapes in the prompt.
- No added text names a phase, plan, decision or review id, PROVISIONAL or a machine path; model names are placeholders.
- Modules: `test_skill_evals_shape` 6, `test_spec_chain_text` 40, `test_arch_hardcoded_models` 23, `test_fold_check` 18,
  `test_skill_text_history` 45, `test_ai_kit_spec_review_fixer` 10: all ok.
- Gates after the plan (at cd4e6fb): unit + arch groups under the watchdog `200/200 modules passed` (peak 7, not killed);
  `make ruff`, `make pyright`, `make vulture`, `make pylint`, `make check-dogfood` exit 0 each. The Task 1 hook deferred
  `tests.test_ai_kit_gsd_curated_config_matrix` to push (the staged mapper names it for the new eval files); it ran under
  the watchdog at cd4e6fb: 35 tests ok in 159.2 s.

## Deviations

- The plan says the active config.toml has 12 lines; it has 11. No effect on the new file.
- Open from review cycle 2: the jev eval stays transcript-assessed; the CRITICAL/HIGH routing is proven by the
  jev_review and classify-wiring tests.
