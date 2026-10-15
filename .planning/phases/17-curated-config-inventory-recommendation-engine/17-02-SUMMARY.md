---
phase: 17-curated-config-inventory-recommendation-engine
plan: 02
executor: cross-ai (pi router-env/my-coding)
requirements-completed: [REC-01, REC-02, REC-05, REC-06]
duration_s: 188
orchestrator_verify: "VERIFY 17-02: 3/3 passed"
---

# Plan 17-02 Complete

Delivered the pure `recommend` engine: inventory → canonical `plan.json` with §5 presets, tier layer, cross-AI reservations, key drops, fail-closed loading, and purity guarantees.

## Accomplishments

- Added `recommend` CLI subcommand (`load_inventory` → `build_plan` → atomic `write_plan`) and `gsd_catalog.load_ai_kit_spec_module()` shim.
- Implemented `presets.py` (§5 tables, `preset_values`, `closed_key_set`, `get_dotted`, `flatten_config`), `plan_io.py` (schema validation, digest, canonical JSON), and pure `recommend.build_plan` with preset/tier/cross-AI layers and rejected-key drops.
- Added `tests/test_curated_config_recommend.py` (tracer, table-driven presets, phase shifts, cross-AI, key drop, effects, inventory validation, purity, atomic write); registered in Makefile and `.pre-commit-config.yaml`.
- Verified: `python3 -m unittest tests.test_curated_config_recommend tests.test_ai_kit_gsd_curated_config tests.test_gate_scope` OK; `make ruff pylint pyright vulture` OK; `make test-unit` OK.

## Files Created/Modified

- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/presets.py` (new)
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/plan_io.py` (new)
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/recommend.py` (new)
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cli.py`
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/gsd_catalog.py`
- `tests/test_curated_config_recommend.py` (new)
- `Makefile`
- `.pre-commit-config.yaml`

## Commits

- `cef31436e6863677d818e3b3ab3fe025d4db8016` — feat(17-02): recommend writes a canonical plan.json from an inventory
- `05113827270bcc6c5d238d00c34ed4447f8bc821` — feat(17-02): rigor presets, phase shifts, cross-AI reservations, key drop
- `7a616f9c6546d881044df0278df88c7892153e51` — test(17-02): fail-closed inventory loading and recommend purity
