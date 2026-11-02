---
phase: 17-curated-config-inventory-recommendation-engine
plan: 06
executor: cross-ai (pi router-env/my-coding)
requirements-completed: [REC-04]
duration_s: 405
orchestrator_verify: "VERIFY 17-06: 3/3 passed"
---

# Plan 17-06: Specialist `model_overrides` layer

Specialist recommendations now emit at most seven `model_overrides` entries (only when slot rules fail), with notes for single-provider hosts, vision gaps, and unconfirmed routers.

## Accomplishments

- Added `roles.CLAUDE_ALIASES` / `claude_alias_for()` and `_specialist_layer` with execution, counterpart, and vision helpers wired after `_slot_layer` in `_LAYERS`.
- Execution prefers user-confirmed `execute` routers; counterparts use fixed `review` ranking vs planner/execution vendors; vision/ui-researcher use `general` with `image_input`; pi writes no overrides; claude values are aliases.
- Added `TestSpecialistTracer`, `TestSpecialistRules`, and `TestSpecialistProperties` (including purpose pin, budget W2, cap matrix, shuffle stability, vendor strictness).
- Verified: `python3 -m unittest tests.test_curated_config_recommend tests.test_curated_config_inventory`, `make ruff pylint pyright vulture`, and `make test-unit`.

## Files Created/Modified

- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/roles.py`
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/recommend.py`
- `tests/test_curated_config_recommend.py`

## Commits

- `b47740c` — feat(17-06): specialist overrides only where the slot fails its rule
- `703cfa2` — test(17-06): single-provider, vision, frontend, router and claude alias rules
- `bbea34a` — test(17-06): at most 7 specialist overrides, order-independent, strict vendors
