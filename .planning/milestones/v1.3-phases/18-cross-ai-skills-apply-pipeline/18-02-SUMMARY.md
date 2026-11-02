---
phase: 18-cross-ai-skills-apply-pipeline
plan: 02
executor: cross-ai (pi router-env/my-coding)
requirements-completed: [XAI-01, SKL-01, APP-04]
duration_s: 381
orchestrator_verify: "VERIFY 18-02: 3/3 passed"
---

# 18-02: Inventory schema 2 — gsd-core lanes, skills roots, and key probes

Extended the read-only gsd-core node query and inventory to carry review lanes, skills roots, installed runtimes, and expanded key probes; recommend output and Phase 17 golden plans are unchanged.

## Accomplishments

- Node tables script v2 returns `review_lanes` via `mergeReviewerLanes`/`loadRegistry`, `skills_roots` via `getGlobalSkillsBase`, and probes `agent_skills.<agent>` plus lane model/effort keys merged with preset probes.
- Inventory schema 2 persists `gsd_core.review_lanes`, `gsd_core.skills_roots`, and `installed_runtimes`; null registry or skills-home failures become empty data with explicit warnings.
- `plan_io.load_inventory` validates all six lane fields and skills root values; schema 1 is refused with `; rerun inventory`.
- `PROBED_EXTRA_KEYS` are probed in `closed_key_set` but not managed (avoids 17 D-08 unsetting hand-set timeout/execute/trusted roots).
- Opencode resolves `<project>/.opencode/gsd-core` first (`_HOST_FIRST_ROOT`); pi behavior generalized.
- Regenerated `gsd_tables_1_16.json`; hermetic `tables_answer` mirrors real node; e2e `TestRealGsdLanes` and unit boundary tests added.

## Files Created/Modified

- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/gsd_catalog.py`
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/inventory.py`
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/plan_io.py`
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/presets.py`
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/host.py`
- `tests/fixtures/curated_config_v2/gsd_tables_1_16.json`
- `tests/test_curated_config_e2e.py`
- `tests/test_curated_config_inventory.py`
- `tests/test_curated_config_recommend.py`
- `tests/test_curated_config_golden.py`

## Commits

- `7044828` — feat(18-02): inventory reads gsd-core review lanes and skills roots
- `3295729` — feat(18-02): probe lane and skill keys; regenerate gsd tables fixture
- `9e4ab50` — feat(18-02): inventory boundary validation and the opencode local root
