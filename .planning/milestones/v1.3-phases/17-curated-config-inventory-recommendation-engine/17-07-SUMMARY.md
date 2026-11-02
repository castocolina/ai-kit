---
phase: 17-curated-config-inventory-recommendation-engine
plan: 07
executor: cross-ai (pi router-env/my-coding)
requirements-completed: [INV-01, INV-03]
duration_s: 453
orchestrator_verify: "VERIFY 17-07: 3/3 passed"
---

# Plan 17-07 — Complete inventory, conflicts, and read-only project facts

Inventory now emits the full INV-01 snapshot (project facts, allow-listed configs, conflicts/info, skills) and passes through `recommend` end to end without writing to the project tree.

## Accomplishments

- Added `project_facts.py` (instruction files, frontend/db heuristics, intel index, skills) and `package_json_deps()` in `frontend_detect.py` for shared manifest parsing.
- Extended `inventory.py` with allow-listed `_existing_config` / `_global_defaults`, expanded `_probe_keys`, `classify_conflicts` (D-10, D-21, D-31), and full `build_inventory` output including `info`.
- Added tests: `TestCompleteInventory` (inventory → recommend), `TestConflictMatrix` (15 cases), `TestProjectFacts`, `TestReadOnly`, `TestReadOnlyRealGsd`; updated `FakeRun` for `config-path`.
- Verified: `python3 -m unittest tests.test_curated_config_inventory tests.test_curated_config_recommend tests.test_ai_kit_gsd_curated_config`, `make ruff pylint pyright vulture`, and `make test-unit`.

## Files Created/Modified

- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/project_facts.py` (new)
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/frontend_detect.py`
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/inventory.py`
- `tests/test_curated_config_inventory.py`

## Commits

- `75e5932` — feat(17-07): complete inventory with project facts, existing config and conflicts (tasks 1–3 implementation and tests in one logical commit)
