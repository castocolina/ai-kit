---
phase: 18-cross-ai-skills-apply-pipeline
plan: 01
executor: cross-ai (pi router-env/my-coding)
requirements-completed: [XAI-02, SPEC-05, APP-03, SKL-04]
duration_s: 251
orchestrator_verify: "VERIFY 18-01: 3/3 passed"
---

# Plan 18-01 — Shared ai_kit_spec groundwork

All three tasks completed; verification passed (`916` unit tests OK, `make test-unit` OK, `cross-ai.mjs` unchanged).

## Accomplishments

- Added pi to `KNOWN_CLIS`, bumped `RUNTIMES_SCHEMA_VERSION` to 4, and implemented RPC `get_available_models` parsing/detection with snapshot fields (`models`, `reasoning_modes`, `image_input`).
- Proved D-45 router merge and pi `router_confirmed` candidate join via catalog build + `build_candidates` tests (no `catalog_build.py` change needed).
- Hardened pi parser/snapshot edge cases (malformed exit-0 output omits models; valid empty listing yields `[]`).
- Added `encode_value_strict`, `ConfigCall`, and `config_set_strict` for the v2 write path; added `secret_is_set` for presence-only secret checks.

## Files Created/Modified

- `skills/ai-kit-spec-review/ai_kit_spec/detection.py`
- `skills/ai-kit-spec-review/ai_kit_spec/gsd_tools.py`
- `skills/ai-kit-spec-review/ai_kit_spec/local_secrets.py`
- `tests/fixtures/pi_rpc_get_available_models.json` (created)
- `tests/test_ai_kit_spec.py`
- `tests/test_ai_kit_spec_gsd_tools.py`
- `tests/test_curated_config_inventory.py`

## Commits

- `fc7e495` — feat(18-01): enumerate pi models from RPC get_available_models
- `714850e` — test(18-01): pi parser and snapshot edge cases
- `5481a96` — feat(18-01): strict config-set encoder and presence-only secret check
