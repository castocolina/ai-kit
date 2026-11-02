---
phase: 17-curated-config-inventory-recommendation-engine
plan: 03
executor: cross-ai (pi router-env/my-coding)
requirements-completed: [INV-01, REC-06]
duration_s: 222
orchestrator_verify: "VERIFY 17-03: 3/3 passed"
---

# Plan 17-03 — Read-only inventory tracer

Shipped the `inventory` subcommand with gsd-core resolution, one-node table/key probing, and full test coverage; `make test-unit` and lint gates pass.

## Accomplishments

- Added `local_gsd_core_roots()` in `gsd_tools.py` and wired `gsd_core_roots()` to reuse it (drift-safe with existing tests).
- Extended `gsd_catalog.py` with `query_gsd_tables`, config-schema resolution, and strict `_parse_tables_output` fail-closed parsing.
- Implemented `host.py` (pi-first `.pi/gsd-core`, scope labelling, worktree global warning) and `inventory.py` (`build_inventory` read-only orchestration).
- Registered CLI `inventory --project-dir [--host]` emitting canonical JSON via `plan_io.canonical_json`.
- Added `tests/test_curated_config_inventory.py` (fake trees, `FakeRun`, `real_gsd_run`, resolution, probe failures, real gsd-core smoke for all five hosts).
- Regenerated Makefile / `.pre-commit-config.yaml` test listings via `gen_test_groups.py`.

## Files Created/Modified

- `skills/ai-kit-spec-review/ai_kit_spec/gsd_tools.py`
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/gsd_catalog.py`
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/host.py` (new)
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/inventory.py` (new)
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cli.py`
- `tests/test_curated_config_inventory.py` (new)
- `Makefile`, `.pre-commit-config.yaml`

## Commits

- `c69a31b` — feat(17-03): inventory reports the project's own gsd-core tables and probed keys (Tasks 1–2: tracer, resolution, and tests)
- `781b317` — test(17-03): a failed isValidConfigKey probe fails closed (D-31) (Task 3: pyright-safe parse guard)

## Issues Encountered

- Task 2 was not a separate git commit; D-11 resolution and `TestGsdCoreResolution` landed in `c69a31b` with the Task 1 tracer because the implementation was delivered atomically.
