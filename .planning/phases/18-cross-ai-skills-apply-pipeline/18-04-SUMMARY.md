---
phase: 18-cross-ai-skills-apply-pipeline
plan: 04
executor: cross-ai (pi router-env/my-coding)
requirements-completed: [XAI-02]
duration_s: 222
orchestrator_verify: "VERIFY 18-04: 2/2 passed"
---

# 18-04: Cross-AI execution selection complete

Implemented pure `cross_ai.py`, wired execution defaults and artifacts into `recommend`, bumped plan schema to v2, and regenerated goldens (claude host → pi + `router-env/my-coding`).

## Accomplishments

- Added `cross_ai.py` with target selection, D-39 defaults, timeout/manager-flag helpers, and the typed cross-ai-script artifact.
- Updated `recommend.py` for D-39 exec defaults, real `workflow.cross_ai_command`/timeout/manager flags, top-level `artifacts`, and removed the Phase 17 cheap-CLI exec path.
- Set `PLAN_SCHEMA_VERSION = 2`; extended fixtures (pi router, schema 4) and regenerated all 17 golden plans.
- Extended purity guard and `TestCrossAi.test_defaults`; added `test_exec_targets_never_host`; removed `roles.cheap_other_cli`.
- Task 1 and Task 2 verify commands passed (`unittest` golden/recommend/inventory; `make test-unit`, pylint, vulture).

## Files Created/Modified

- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai.py` (new)
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/recommend.py`
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/plan_schema.py`
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/roles.py`
- `tests/test_curated_config_recommend.py`
- `tests/test_curated_config_golden.py`
- `tests/test_curated_config_inventory.py`
- `tests/fixtures/curated_config_v2/runtimes.json`
- `tests/fixtures/curated_config_v2/model-catalog.json`
- `tests/fixtures/curated_config_v2/golden/*.json` (17 files)

## Commits

- `be997c5` — feat(18-04): cross-AI execution targets and script artifact
- `3a35516` — refactor(18-04): guard cross_ai purity; drop the unused cheap-CLI pick
