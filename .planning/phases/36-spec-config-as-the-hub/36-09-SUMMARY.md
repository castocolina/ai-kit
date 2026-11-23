---
phase: 36-spec-config-as-the-hub
plan: 09
subsystem: spec-config
tags: [lane-order, jev-score, ranking]

requires: [36-01, 36-02, 36-06]
provides:
  - "skills/ai-kit-spec-review/ai_kit_spec/lane_order.py: rank, deterministic_order, facts_summary, Ranked, JEV_WINDOW, STABLE_TOP, NEUTRAL_LEVEL, EFFORT_FACT_LEVELS and the named scorer fallback reasons"
  - "skills/ai-kit-spec-review/ai_kit_spec/jev_names.py: SCORE_LEVELS, SCORE_QUESTIONS, SCORE_CONTEXT_CHARS, score_item, score_judge"

key-files:
  created:
    - skills/ai-kit-spec-review/ai_kit_spec/lane_order.py
  modified:
    - skills/ai-kit-spec-review/ai_kit_spec/jev_names.py
    - tests/test_lane_order.py

requirements-completed: []

executor: "cross-AI lane: pi router-env/my-coding, one run (660 s, AIKIT-XAI status=ok exit=0 attempts=1 cycles=0)"
---

# Phase 36 Plan 09: lane_order and the jev score seam

One commit, `7c11cef feat(36-09): rank proposal lanes` (pre-fold; 3 files, +388 -6); the commit hook ran 115/115 modules green.

## Accomplishments

- New module `lane_order.py`: the purpose-weighted scorer (`model_ranker.score_candidates`, inputs sanitised to finite numbers) orders every row with ties by key and runtime; when a judge is passed, one bounded window (the first 7 known rows plus up to 5 zero-price rows, at most 12) goes to jev as closed-fact summaries and a confident answer (top at least 0.80) re-orders its row; a low answer, error, timeout or no answer leaves the scorer position with a named reason; unknown-tier rows go last; every row carries who ranked it.
- `jev_names.py` gains the score levels, the two purpose questions, `score_item` (printable ASCII only, 240 characters) and `score_judge` (the existing client copy, no second one).
- `tests/test_lane_order.py`: 18 tests including the worst-case window fitting one jev batch.

## Deviations and notes

- None. No file outside the plan's three paths changed. The lane fixed its own line-length and optional-call findings before the commit.

## Orchestrator verification (own runs, not the executor's claims)

- `python3 tools/run_unittest_parallel.py tests.test_lane_order tests.test_catalog_jev_names tests.test_arch_hardcoded_models tests.test_arch`: exit 0, 4/4 modules (18, 13, 14 and 109 tests).
- `make ruff`, `make pyright`, `make vulture`: Passed; pylint on both source files: Passed. Read the whole `lane_order.py`, the `jev_names.py` diff (constants and texts match the plan's exact text) and the lane report.
- Real-config audit (marker-c3-p36-w3): host and other-agent files plus pi session logs only.

## Self-Check: PASSED
