---
phase: 17-curated-config-inventory-recommendation-engine
plan: 08
executor: cross-ai (pi router-env/my-coding)
requirements-completed: [REC-01, INV-03]
duration_s: 243
orchestrator_verify: "VERIFY 17-08: 3/3 passed"
---

# Plan 17-08: Reconcile layer and conflict-driven unsets

Added the final `recommend` reconcile layer: managed-family leftovers and inventory conflicts become per-leaf `unset` entries, runtime is set on opencode/codex with mismatch notes elsewhere, and malformed conflicts fail closed in `load_inventory`.

## Accomplishments

- Implemented `presets.is_managed`, `MANAGED_PREFIXES`/`MANAGED_KEYS`, and `RUNTIME_MANAGED_HOSTS` for D-08 family boundaries.
- Added `_reconcile_layer` with `_leftover_unsets`, `_conflict_unsets`, and `_runtime_entries` as the last layer in `_LAYERS`.
- Validated inventory `conflicts` items in `load_inventory` (malformed → exit 2, `rerun inventory`).
- Added `TestReconcileTracer`, `TestReconcileConflicts` (13 tests), and `TestReconcileComposition` (7 tests); `make test-unit`, ruff, pylint, pyright, and vulture pass.

## Files Created/Modified

- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/presets.py`
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/recommend.py`
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/plan_io.py`
- `tests/test_curated_config_recommend.py`

## Commits

- `f9caf0d` — feat(17-08): reconcile layer unsets managed leftovers and policy conflicts (D-08)
- `af95313` — feat(17-08): runtime per host and latent global conflicts in the plan (D-23, D-30, D-31)
- `035916f` — test(17-08): reconcile composes with slot, specialist and cross-AI layers
