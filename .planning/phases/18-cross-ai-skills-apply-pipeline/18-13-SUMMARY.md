---
phase: 18-cross-ai-skills-apply-pipeline
plan: 13
executor: cross-ai (pi router-env/my-coding)
requirements-completed: [XAI-02]
duration_s: 306
orchestrator_verify: "VERIFY 18-13: 3/3 passed"
---

# Plan 18-13: Cross-AI runner render and edit protection

Delivered stamped runner rendering, atomic bytes writes, edit-safe planning/writing, and unit/E2E coverage; live `.planning/scripts/cross-ai.mjs` was not modified.

## Accomplishments

- Added `cross_ai_script.py`: CONFIG injection, D-26 sha256 header stamping, `script_state` classification, `plan_script` / `write_script` with re-read protection and `.new` diversion for non-pristine or racing edits
- Added `cache_write_bytes` in `cache.py` with `cache_write_text` delegating to it
- E2E `TestRenderedRunner`: rendered script is pristine, `--self-test` passes, deadline 1770s under 1800s timeout
- Unit tests in `test_curated_config_script.py` for idempotency, edit protection, intervening edit/create, template bump, CRLF hashing, and `command_argv`
- `TestCacheWriteBytes` for atomic binary writes; `test-unit` and `e2e-test` green

## Files Created/Modified

- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai_script.py` (new)
- `skills/ai-kit-spec-review/ai_kit_spec/cache.py`
- `tests/test_cross_ai_runner_e2e.py`
- `tests/test_curated_config_script.py` (new)
- `tests/test_ai_kit_spec.py`
- `Makefile`, `.pre-commit-config.yaml` (via `gen_test_groups.py`)

## Commits

- `ef2276f` — feat(18-13): render the cross-AI runner with a stamped sha256 header
- `8004ed2` — test(18-13): runner render edit protection and determinism
- `0bc638e` — test(18-13): atomic bytes writer
