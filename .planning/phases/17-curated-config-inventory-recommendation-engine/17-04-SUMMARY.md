---
phase: 17-curated-config-inventory-recommendation-engine
plan: 04
executor: cross-ai (pi router-env/my-coding)
requirements-completed: [REC-03, INV-02]
duration_s: 446
orchestrator_verify: "VERIFY 17-04: 3/3 passed"
---

# Plan 17-04: Tier→model slot layer complete

Implemented the `model_profile_overrides` recommendation layer with role-based picks, edge-case fallbacks, and determinism tests; verified with `make test-unit` and lint.

## Accomplishments

- Added pure `roles.py` helpers (ceiling, family picks, effort variants, tie order, `cheap_other_cli`, `used_tiers`).
- Extended `presets.py` with `PRICE_PERCENTILE` and `CODEX_EFFECT`; wired `_slot_layer` / `_tier_slot` / `_pi_slot` in `recommend.py` (Claude skip, codex enumeration fallback, MVP cheap cross-AI default).
- Added tests: `TestRolesHelpers`, `TestSlotTracer`, `TestSlotEdges`, `TestDeterminism`; updated `TestCrossAi` and `TestPurity` for `roles.py`.
- Stabilized `inventory_digest` for candidate order (R7); all 57 recommend tests and `make test-unit` pass; `make ruff pylint pyright vulture` pass.

## Files Created/Modified

- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/roles.py` (new)
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/presets.py`
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/recommend.py`
- `tests/test_curated_config_recommend.py`

## Commits

- `c3b8b70` — feat(17-04): tier->model layer keeps valid native slots and overrides by role score (includes Tasks 2–3 changes in one logical commit)
