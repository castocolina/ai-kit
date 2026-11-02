---
phase: 17-curated-config-inventory-recommendation-engine
plan: 09
executor: cross-ai (pi router-env/my-coding)
requirements-completed: [INV-01, REC-02, REC-03, REC-04]
duration_s: 321
orchestrator_verify: "VERIFY 17-09: 3/3 passed"
---

# Plan 17-09: Golden fixtures and phase gate

Pinned curated-config v2 with shared fixtures, 17 digest-masked golden plans, property/conflicts tests, SPEC amendments (D-17/D-18/D-29), and green `make test` / `make validate`.

## Accomplishments

- Added `tests/fixtures/curated_config_v2/` (gsd-core 1.16 tables, trimmed runtimes/catalog, synthetic pi) and `tests/test_curated_config_golden.py` (D-20 builder, `UPDATE_GOLDEN`, real-gsd tables check, golden byte compare, R8–R10/R13 properties, conflicts end-to-end, fixture hygiene).
- Committed 17 golden plans under `tests/fixtures/curated_config_v2/golden/` (`inventory_digest` masked to `<digest>`).
- Hermetic `tables_answer` transposes gsd-core agent-first `MODEL_PROFILES` to profile-first for `recommend` (raw tables fixture stays agent-first for `TestGoldenTables`).
- Amended `17-SPEC.md` for R4 (Codex `op: keep`), R9 (router on opencode golden, D-17 dynamic routing note), R11 (`workflow.live_dom_uat` / D-29).
- Regenerated test groups in `Makefile` and `.pre-commit-config.yaml`. Phase 17 plan commits did not touch `tools/` or any `SKILL.md`/`README.md` — `make e2e-docker` and skill-judge for inventory/recommend docs remain Phase 18 requirement 15.

## Files Created/Modified

- `tests/fixtures/curated_config_v2/gsd_tables_1_16.json`, `runtimes.json`, `model-catalog.json`
- `tests/fixtures/curated_config_v2/golden/*.json` (17 plans)
- `tests/test_curated_config_golden.py`
- `Makefile`, `.pre-commit-config.yaml`
- `.planning/phases/17-curated-config-inventory-recommendation-engine/17-SPEC.md`

## Commits

- `3e706f1` — test(17-09): codex golden plan built end to end from shared fixtures (D-20)
- `0bcd6fd` — test(17-09): 17 golden plans, cross-host properties and conflicts end to end (R8, R9, R10, R13)
- `8a4c618` — docs(17-09): amend SPEC R4 (codex keep entries), R9 (router golden, dynamic routing) and R11 (live_dom_uat, D-29)
