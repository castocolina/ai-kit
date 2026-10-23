---
phase: 22-pi-live-validation
plan: 03
subsystem: curated-config
tags: [pi, inventory, recommendation, plan-edit, documentation]
requires:
  - phase: 22-01
    provides: pi session-steer verdict from static and mock evidence
  - phase: 22-02
    provides: pi runtime inventory and model fixtures
provides:
  - pi inventory records validated PI_PROVIDER for pi hosts only
  - pi.sonnet offers session-provider bare model ids and carries the session-wide evidence label
  - plan-set rejects pi.sonnet values outside the inventory's provider model ids, including with --force
  - pi documentation states the static/mock verdict while retaining the live-validation label
  - three pi recommendation goldens updated
 affects: [22-04, 22-05, curated-config]
actuals:
  tokens: 4500
  tasks: 3
  commits: 4
tech-stack:
  added: []
  patterns: [inventory-bound environment facts, force-immune candidate validation]
key-files:
  created: [.planning/phases/22-pi-live-validation/22-03-SUMMARY.md]
  modified:
    - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/inventory.py
    - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/roles.py
    - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/recommend.py
    - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/plan_edit.py
    - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/apply.py
    - skills/ai-kit-gsd-curated-config/SKILL.md
    - tests/test_curated_config_recommend.py
    - tests/test_curated_config_golden.py
    - tests/test_curated_config_inventory.py
    - tests/test_curated_config_plan_edit.py
    - tests/test_curated_config_apply.py
    - tests/fixtures/curated_config_v2/golden/pi-mvp-adaptive.json
    - tests/fixtures/curated_config_v2/golden/pi-rigorous-adaptive.json
    - tests/fixtures/curated_config_v2/golden/pi-standard-adaptive.json
key-decisions:
  - "Use only PI_PROVIDER and validate it as a provider id; do not record other session environment values."
  - "Guard pi.sonnet against session-provider candidates independently of plan candidate fields, and make the restriction immune to --force."
  - "Retain not-live-validated wording pending the owner interactive run."
requirements-completed: [EVAL-08]
coverage:
  - id: D1
    description: Pi inventory provider discovery, session-scoped recommendation candidates, and guarded plan-set behavior.
    requirement: EVAL-08
    verification:
      - kind: unit
        ref: tests.test_curated_config_inventory#test_pi_session_provider_recorded_on_pi_only
        status: pass
      - kind: unit
        ref: tests.test_curated_config_recommend#test_pi_sonnet_candidates_are_session_provider_bare_ids
        status: pass
      - kind: unit
        ref: tests.test_curated_config_plan_edit#test_pi_sonnet_other_values_refused_even_forced
        status: pass
    human_judgment: false
  - id: D2
    description: Pi plan goldens and documentation state the supported session-steer verdict without lifting the live-validation label.
    requirement: EVAL-08
    verification:
      - kind: unit
        ref: tests.test_curated_config_golden#TestGoldenPlans
        status: pass
      - kind: unit
        ref: tests.test_curated_config_apply#test_pi_row_keeps_label_and_states_verdict
        status: pass
    human_judgment: false
metrics:
  duration: 35min
  completed: 2026-10-23
status: complete
---

# Phase 22 Plan 03: Pi session-steer recommendations Summary

**Pi plans now offer only session-provider bare ids for `pi.sonnet`, with a force-immune guard and evidence-qualified documentation.**

## Performance

- **Duration:** 35 min
- **Started:** 2026-10-23
- **Completed:** 2026-10-23
- **Tasks:** 3
- **Files modified:** 14 product/test/fixture files, plus this summary

## Accomplishments

- Inventory captures a pattern-validated `PI_PROVIDER` on pi only; recommendation filters pi candidates to sorted bare ids for that provider.
- `pi.sonnet` is labeled as a session-wide steer; plans continue to omit per-agent overrides and `pi.opus`/`pi.haiku` entries. Three pi goldens pin the provider candidate and effect text.
- `plan-set` refuses values not served by the inventory's provider even with `--force`; without a provider, the refusal directs users to inventory inside pi or `plan-unset`.
- SKILL.md describes the static/mock verdict, the pending interactive validation, and the limits of the effect. The pi live-validation label remains.
- Re-checked gsd-core 1.17.0: `canonicalizeRuntimeName("pi")` output was `null`; `.claude/gsd-core/VERSION` output was `1.17.0`. Updated `_PI_SKILL_SKIP` from 1.16.0 to 1.17.0 because the behavior remains unchanged.

## Task Commits

1. **Task 1: provider-specific pi recommendations and goldens** - `996f2d8`
2. **Task 2: force-immune pi.sonnet guard and tests** - `ebbede0`
3. **Task 3: verdict documentation and gsd-core version re-check** - `4dd0bd8`
4. **Plan summary** - committed separately after the task commits.

## Files Created/Modified

- `inventory.py`, `roles.py`, `recommend.py` - record provider and build filtered bare-id candidates.
- `plan_edit.py` - validate selected pi model against inventory provider candidates, regardless of force.
- `apply.py`, `SKILL.md` - update upstream version citation and explain the pi verdict.
- Recommend, golden, inventory, plan-edit, and apply tests; three pi adaptive goldens.

## Decisions Made

- Recorded only the validated provider identifier from the process environment on pi hosts.
- Restricted plan-set to the inventory-derived ids because gsd-core writes the selected string into requests verbatim.
- Kept the live-validation label because owner-only interactive evidence has not run.

## Deviations from Plan

None - plan executed as written.

## Issues Encountered

None.

## Deleted tests

None.

## Verification

- Filtered pi tests: 9 tests passed; complete plan-edit, recommendation, and inventory modules passed (315 tests).
- Recommendation, golden, skills, and inventory modules passed (339 tests).
- Apply module passed (99 tests).
- Golden assertions confirmed exactly three pi goldens changed and each pins only `anthropic/claude-sonnet-5` as bare candidate `claude-sonnet-5`.
- `uv run ruff check tools skills tests`, `uv run pyright`, and `uv run vulture` passed.
- `make test` passed, including unit, integration, e2e, installer, and architecture groups.
- `make validate` passed all configured hooks.

## Next Phase Readiness

Ready for 22-04 matrix work. Owner-only interactive smoke and live-provider checks remain pending as required; the pi label has not been lifted.

---
*Phase: 22-pi-live-validation*
*Completed: 2026-10-23*
