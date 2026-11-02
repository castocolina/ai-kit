---
phase: 18-cross-ai-skills-apply-pipeline
plan: 06
executor: cross-ai (pi router-env/my-coding)
requirements-completed: [XAI-01]
duration_s: 333
orchestrator_verify: "VERIFY 18-06: 2/2 passed"
---

# Plan 18-06 — Cross-AI review lanes complete

Review lane selection is wired from the gsd-core registry through recommend, goldens were regenerated, and SPEC R2 edge cases are covered by tests.

## Accomplishments

- Added `cross_ai.py` lane API (`eligible_lanes`, `lane_pool`, `lane_value`, `select_lanes`, `lane_effort`) with vendor-different rules, router-first ranking, and rigorous two-lane re-pick.
- Implemented the review branch in `recommend._cross_ai_layer`: convergence flag, `review.default_reviewers`, per-lane model/effort keys (Claude alias + opencode effort effects), and fail-open notes when no lane qualifies.
- Regenerated 17 goldens (Phase 18 placeholder removed); added `TestGoldenProperties.test_lanes_never_host` and `TestReviewLanes` (18 cases including host/pi prohibition and O7 claude alias).
- Updated `TestCrossAi` and golden property checks for cross-runtime review entries.

## Files Created/Modified

- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai.py`
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/recommend.py`
- `tests/test_curated_config_cross_ai.py`
- `tests/test_curated_config_recommend.py`
- `tests/test_curated_config_golden.py`
- `tests/fixtures/curated_config_v2/golden/*.json` (7 plans with review convergence)

## Commits

- `a5aa28a` — feat(18-06): review lanes from the gsd-core registry
- `238bce2` — test(18-06): review lane edges, claude alias and host prohibition
