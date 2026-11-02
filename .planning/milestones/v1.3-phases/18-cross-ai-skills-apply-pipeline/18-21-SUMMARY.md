---
phase: 18-cross-ai-skills-apply-pipeline
plan: 21
executor: cross-ai (pi router-env/my-coding)
requirements-completed: [EVAL-06]
duration_s: 171
orchestrator_verify: "VERIFY 18-21: 2/2 passed"
---

# Plan 18-21: Curated-config SKILL.md v2-primary documentation

Shipped v2-primary `SKILL.md`, README row update, command drift tests, and skill-judge self-check evidence (PASS).

## Accomplishments

- Rewrote `skills/ai-kit-gsd-curated-config/SKILL.md` with v2 as the primary flow, v1 secondary, cross-AI/`.new`/failure-state rules, limits, and required honesty statements (≤270 lines).
- Updated the README `ai-kit-gsd-curated-config` row for the v2 pipeline (single ASCII table row).
- Added `TestSkillDocCommands` (parser drift, v2-primary ordering, required-statement pins); `python3 -m unittest tests.test_curated_config_apply -k TestSkillDocCommands` passes.
- Added `.planning/phases/18-cross-ai-skills-apply-pipeline/18-SKILL-JUDGE.md` with RUN-49 self-check scoring 103/120 (baseline 100), no Critical/Important findings, `## Verdict: PASS`.
- Verified `.planning/scripts/cross-ai.mjs` unchanged.

## Files Created/Modified

- `skills/ai-kit-gsd-curated-config/SKILL.md`
- `README.md`
- `tests/test_curated_config_apply.py`
- `.planning/phases/18-cross-ai-skills-apply-pipeline/18-SKILL-JUDGE.md`

## Commits

- `7009d22` — docs(18-21): curated-config SKILL.md v2 flow with a command drift test
- `ca8576e` — docs(18-21): skill-judge self-check evidence for the curated-config SKILL.md
- `ba3b158` — docs(18-21): align skill-judge judged blob with committed SKILL.md
