---
phase: 18-cross-ai-skills-apply-pipeline
plan: 07
executor: cross-ai (pi router-env/my-coding)
requirements-completed: [SKL-02, SKL-03]
duration_s: 334
orchestrator_verify: "VERIFY 18-07: 2/2 passed"
---

# Plan 18-07 — Skill affinity layer complete

Wired curated `skill_affinity.json` through a pure resolver into recommend’s `_skills_layer`, with ponytail on Claude-host goldens and edge-case tests for caps, gates, and silent omission of missing skills.

## Accomplishments

- Added curated `skill_affinity.json` and `skills.py` (`validate_affinity`, `skill_facts`, `locate`, `resolve`, `reference_for`) with rigor caps from `presets.SKILL_CAPS`.
- Integrated `_skills_layer` in `recommend.py`, `load_affinity` / `AFFINITY_PATH` in `plan_io.py`, and CLI recommend always loading the shipped affinity file.
- Regenerated golden plans with ponytail plugin seeded in golden HOME; Claude-host plans expose `agent_skills.*` and `skill_affinity` provenance.
- Added `TestAffinityValidation`, `TestAffinityResolve`, `TestSkillsLayer`, and `TestGoldenProperties.test_skill_cap`; updated CLI I/O purity test for the affinity read.

## Files Created/Modified

- `skills/ai-kit-gsd-curated-config/skill_affinity.json` (new)
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/skills.py` (new)
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/presets.py`
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/plan_io.py`
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/recommend.py`
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cli.py`
- `tests/test_curated_config_golden.py`
- `tests/test_curated_config_recommend.py`
- `tests/test_curated_config_skills.py`
- `tests/fixtures/curated_config_v2/golden/*.json` (regenerated)

## Commits

- `2e2717e` — feat(18-07): skill affinity layer wires ponytail within the rigor cap
- `12f0cfe` — test(18-07): affinity resolution edges and missing-skill silence
