---
phase: 18-cross-ai-skills-apply-pipeline
plan: 08
executor: cross-ai (pi router-env/my-coding)
requirements-completed: [SKL-02, SKL-03, SKL-04]
duration_s: 176
orchestrator_verify: "VERIFY 18-08: 2/2 passed"
---

# Plan 18-08 — Skills layer (trusted roots, proposals, notes)

Escaping global skills now surface a `needs_choice` trusted-root entry; unknown skills become capped proposals; jev and pi behaviors are reflected in plan notes and effects.

## Accomplishments

- Implemented `PROPOSAL_CAP`, `trusted_roots`, `proposals`, `existing_roots`, `covered`, and wiring helpers in `skills.py`; `locate` skips escaping project copies; `resolve` leaves outside-HOME escaping globals unwired with notes.
- Extended `_skills_layer` with the trusted-root entry (merged approval list in `why`), proposal notes, jev session gate note, and pi `agent_skills.*` effect.
- Seeded golden HOME with symlinked `react-dev` and regenerated goldens; added `TestTrustedRoots`, `TestProposals`, and `TestSkillNotes`.
- Verified `python3 -m unittest tests.test_curated_config_skills tests.test_curated_config_golden tests.test_curated_config_recommend` and `make test-unit`.

## Files Created/Modified

- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/skills.py`
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/recommend.py`
- `tests/test_curated_config_golden.py`
- `tests/test_curated_config_skills.py`
- `tests/fixtures/curated_config_v2/golden/*.json` (8 golden plans)

## Commits

- `03649b3` — feat(18-08): trusted-root choice for escaping skills
- `8428b37` — feat(18-08): capped skill proposals, jev gate note, pi effect
