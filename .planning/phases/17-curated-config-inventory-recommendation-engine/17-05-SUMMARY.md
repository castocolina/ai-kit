---
phase: 17-curated-config-inventory-recommendation-engine
plan: 05
executor: cross-ai (pi router-env/my-coding)
requirements-completed: [INV-01, INV-02]
duration_s: 420
orchestrator_verify: "VERIFY 17-05: 3/3 passed"
---

# Plan 17-05 — Inventory catalog refresh and scored candidates

Inventory now refreshes the ai-kit catalog via `ai-kit-spec.py`, emits fresh/stale/none state, and lists scored (runtime, model) candidates for recommend.

## Accomplishments

- Added `catalog_adapter.py` with `refresh_catalog`, `_catalog_state`, and `build_candidates` (R3 states, D-12..D-15, subprocess `env=` + 120s timeout).
- Wired `inventory.py` to attach `catalog`, `candidates`, `candidate_heuristic_fields`, and merged warnings; added `InventoryOpts.refresh`.
- Added `inventory --refresh` to force `--save` detect and full catalog fetch without `--if-stale`.
- Extended tests with `FakeRun` ai-kit-spec handling, `seed_cache`, `TestCatalogTracer`, `TestCatalogStates`, `TestBuildCandidates`, and real-gsd fallback recording.

## Files Created/Modified

- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/catalog_adapter.py` (new)
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/inventory.py`
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cli.py`
- `tests/test_curated_config_inventory.py`

## Commits

- `07f84dc` — feat(17-05): inventory refreshes the catalog and lists scored runtime/model candidates
- `e7b61c7` — feat(17-05): distinct fresh/stale/none catalog markers and --refresh
- `70d7250` — test(17-05): pin fast twins, families, strict vendors, router confirmation and scores
