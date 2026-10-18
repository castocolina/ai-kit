---
phase: 20-live-validation-on-codex-opencode
plan: 01
subsystem: testing
tags: [cross-ai, opencode, runner, review-lanes]
requires: []
provides:
  - "Template 4 opencode exec/review argv uses --standalone; model listing remains read-only against the shared service."
  - "This repository's runner is a pristine template-4 render preserving CONFIG and host-signal scrubbing."
  - "Codex/opencode host-lane exclusion is regression-tested at recommendation and plan-set boundaries."
affects: [20-02, 20-03, 20-04, 20-05, 20-06, 20-07]
actuals:
  tokens: 7000
  tasks: 2
  commits: 2
tech-stack:
  added: []
  patterns:
    - "Runner behavior changes require a template-version bump and black-box self-test assertions."
key-files:
  created: []
  modified:
    - skills/ai-kit-spec-review/references/cross-ai.mjs
    - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai.py
    - .planning/scripts/cross-ai.mjs
    - tests/test_curated_config_recommend.py
    - tests/test_curated_config_plan_edit.py
key-decisions:
  - "Keep _READY_TEMPLATE at 3 as the compatibility floor; TEMPLATE_VERSION 4 upgrades pristine template-3 runners."
  - "The host CLI is never proposed or admitted as its own review lane; intentional same-CLI review remains unresolved pending 20-07 interactive trials."
patterns-established:
  - "Regenerate the project runner through ensure-runner and verify task ownership before moving/restoring generated output."
requirements-completed: [EVAL-05]
coverage:
  - id: D1
    description: "Opencode execution and review use a private standalone server; the shared-service model-list preflight limitation is documented."
    requirement: EVAL-05
    verification:
      - kind: unit
        ref: "node skills/ai-kit-spec-review/references/cross-ai.mjs --self-test"
        status: pass
      - kind: unit
        ref: "node .planning/scripts/cross-ai.mjs --self-test"
        status: pass
    human_judgment: false
  - id: D2
    description: "Codex/opencode host slugs are excluded from recommendations and rejected by plan-set with and without --force."
    requirement: EVAL-05
    verification:
      - kind: unit
        ref: "tests.test_curated_config_recommend#test_host_slug_never_a_review_lane_on_codex_and_opencode"
        status: pass
      - kind: unit
        ref: "tests.test_curated_config_plan_edit#test_host_slug_never_a_review_lane"
        status: pass
    human_judgment: false
  - id: D3
    description: "Whether an opencode host can intentionally use its own CLI as a review lane remains unresolved pending interactive trials."
    requirement: EVAL-05
    verification: []
    human_judgment: true
    rationale: "The host-never-proposed policy is automated; same-CLI intentional review has no code-level self-skip or shape cue and requires the 20-07 interactive trials."
duration: 55min
completed: 2026-10-19
status: complete
---

# Phase 20 Plan 01: Runner template 4 and host-lane policy summary

**Template 4 isolates headless opencode runs with `--standalone`, synchronizes this repo's runner, and pins the host-is-never-a-review-lane policy for codex and opencode.**

## Performance

- **Duration:** Approximately 55 minutes
- **Started:** 2026-10-19
- **Completed:** 2026-10-19
- **Tasks:** 2
- **Files modified:** 18

## Accomplishments

- Added `--standalone` to opencode exec and review argv, extended self-test coverage, bumped the template and `TEMPLATE_VERSION` to 4, and kept `_READY_TEMPLATE = 3` as the compatibility floor.
- Regenerated `.planning/scripts/cross-ai.mjs` through `ensure-runner`, preserving its prefer order and models while synchronizing `scrubEnv`; verified it is pristine and no `.new` remains.
- Updated version pins, documentation, tooling guidance, and the seven curated-config golden plans.
- Added codex/opencode-parametrized recommendation tests and plan-set refusal tests for claude, codex, and opencode, including `--force`.
- Bootstrap dispatch host: `pi`.
- Recorded SPEC R6's unresolved assumption: host lanes are never proposed; whether `/gsd-review` can intentionally use the host CLI through another provider/model remains for the two-route interactive trials in 20-07 / `20-INTERACTIVE-OPENCODE.md`.

## Task Commits

1. **Task 1: Template 4 with opencode `--standalone` and runner synchronization** - `4e53b3e85be6106c4937f297cefd3f06e715468c`
2. **Task 2: Host-parametrized never-the-host-lane regressions** - this commit

## Files Created/Modified

- `.planning/scripts/cross-ai.mjs` - Template-4 project runner with existing CONFIG and current host-signal scrub list.
- `skills/ai-kit-spec-review/references/cross-ai.mjs` - Template 4, standalone opencode argv, and self-test assertions.
- `skills/ai-kit-spec-review/ai_kit_spec/tooling_guidance.py` - Template-version documentation.
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai.py` - `TEMPLATE_VERSION = 4`.
- `skills/ai-kit-gsd-curated-config/SKILL.md` and `references/runner.md` - Updated version references.
- `tests/test_curated_config_script.py` and `tests/test_ai_kit_gsd_curated_config.py` - Updated pins and upgrade fixtures.
- `tests/fixtures/curated_config_v2/golden/*.json` - Seven updated plan-version fields.
- `tests/test_curated_config_recommend.py` - Host-lane exclusion and copied-config replacement regressions.
- `tests/test_curated_config_plan_edit.py` - Host-slug refusal tests across three runtimes, with and without force.
- `.planning/phases/20-live-validation-on-codex-opencode/20-01-SUMMARY.md` - This summary.

## Decisions Made

- `_READY_TEMPLATE` remains 3 so template-3 runners are still ready, while `TEMPLATE_VERSION = 4` triggers their upgrade path.
- `opencode models` remains a read-only shared-service preflight because it has no `--standalone`; actual headless run/review execution uses a private server.
- The host CLI is never proposed as its own review lane. Intentional same-CLI use remains an interactive evidence question.

## Deviations from Plan

**1. Kept the edited-runner not-ready test fixture at template 2.**
- **Found during:** Task 1 verification.
- **Issue:** Edited template-3 runners are ready by design because `_READY_TEMPLATE` stays at 3.
- **Fix:** Kept the not-ready fixture at template 2 while updating the current-version pins and upgrade coverage to template 3 -> 4.
- **Files modified:** `tests/test_curated_config_script.py`.
- **Verification:** `python3 -m unittest tests.test_curated_config_script` passed.
- **Committed in:** `4e53b3e85be6106c4937f297cefd3f06e715468c`.

**Total deviations:** 1 compatibility-floor clarification. No scope change.

## Issues Encountered

- The recommendation test initially had no known planner vendor, so no review lane was recommended. A synthetic host planner candidate enabled the intended lane-selection path; tests passed.
- The first pre-commit run found Ruff SIM117 in the plan-edit test. The context managers were combined and the commit passed its hooks.
- The opencode-host intentional-review mechanics remain unverified by design and are assigned to the 20-07 interactive trials.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Later Phase 20 cross-AI dispatches can use the template-4 runner. The harness and host smoke work can proceed; opencode host-lane mechanics remain a user-run interactive item for 20-07.

---
*Phase: 20-live-validation-on-codex-opencode*
*Completed: 2026-10-19*
