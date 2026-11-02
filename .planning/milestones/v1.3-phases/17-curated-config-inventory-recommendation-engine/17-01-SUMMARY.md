---
phase: 17-curated-config-inventory-recommendation-engine
plan: 01
executor: cross-ai (pi router-env/my-coding)
requirements-completed: [INV-01, REC-03]
duration_s: 898
orchestrator_verify: "VERIFY 17-01: 3/3 passed"
---

# 17-01 Execution Report

Outcome: All three tasks shipped and committed — opencode 2.x `image_input` is now read from `GET /api/model` through an always-cleaned-up private `opencode serve` probe with `opencode-api` provenance (runtimes schema 3), and ranker results carry an unrounded `score_exact` (D-15).

## Accomplishments
- `detection.py`: new `opencode_major_version`, `parse_opencode_api_models`, `_read_opencode_banner`, `probe_opencode_api_image_input` (daemon deadline timer; `finally` terminate → wait → kill; password never printed/returned), `opencode_image_input_with_source`, version-gated `detect_opencode_image_input` with injected `popen_fn`/`urlopen_fn`; `_OPENCODE_VERSION_RE` fullmatch so model listings never read as versions
- `build_runtimes_snapshot` stores `clis.opencode.image_input_source` (`opencode-api` on 2.x, `opencode` on 1.x, neither on empty map); `RUNTIMES_SCHEMA_VERSION = 3` so pre-2.x-source caches re-detect
- `catalog_build.py`: runtime meta carries the snapshot's provenance label through `_runtime_meta_from_snapshot`/`_apply_runtime_meta`; docstrings name the 2.x API + 1.x verbose paths
- `model_catalog.py`: `_VALID_IMAGE_INPUT_SOURCE` accepts `opencode-api`; `CATALOG_SCHEMA_VERSION` stays 2
- `model_ranker.py`: `_score_one_entry` returns `score_exact` (unrounded) beside the unchanged rounded `score`; sort unchanged
- New fixture `tests/fixtures/opencode_api_model.json` (the 17-SPIKE 4-model sample verbatim); new `TestOpencodeApiImageInput` (30+ cases: happy path, argv/cwd/auth pinning, all failure paths stop the server, password-leak sweep, provenance end-to-end, schema/cache re-stamp cases); `TestRuntimesSchemaVersion` updated to schema 3 semantics
- `cli-model-selection.md` line ~159 names the v2 API as the 2.x source (reference file, not SKILL.md — no skill-judge loop needed)
- Every check run locally: `python3 -m unittest tests.test_ai_kit_spec` OK (681), the plan's `-k` verify commands OK, `make ruff pylint pyright vulture` all pass, `make test-unit` passes

## Files Created/Modified
- `skills/ai-kit-spec-review/ai_kit_spec/detection.py`
- `skills/ai-kit-spec-review/ai_kit_spec/catalog_build.py`
- `skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py`
- `skills/ai-kit-spec-review/ai_kit_spec/model_ranker.py`
- `tests/test_ai_kit_spec.py`
- `tests/fixtures/opencode_api_model.json` (new)
- `skills/ai-kit-spec-config/references/cli-model-selection.md`

## Commits
- `e824d1a` feat(17-01): read opencode 2.x image_input from its v2 API (D-24)
- `abe6c06` feat(17-01): stop the opencode probe on every path; opencode-api provenance; runtimes schema 3 (D-32)
- `efbca08` feat(17-01): ranker results carry an unrounded score_exact (D-15)

## Issues Encountered
None blocking. Note: the plan's `<output>` asks for `17-01-SUMMARY.md`, but the run context explicitly forbids writing it (orchestrator-owned) — omitted accordingly. The live `detect-runtimes` probe check is marked manual-only in the plan and was not run; all automated verification passed. No processes were left running (only injected fakes were used; no real `opencode` spawned).
