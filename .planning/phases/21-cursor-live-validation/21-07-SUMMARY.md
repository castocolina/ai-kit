---
phase: 21-cursor-live-validation
plan: 07
subsystem: cross-ai-runner
tags: [cursor, PATH, runner-template, self-test]
requires:
  - phase: 21-cursor-live-validation
    provides: Scan-all guarded cursor detection and model parser from plan 21-01.
provides:
  - Runner guarded-agent resolution scans all PATH entries and resolves cwd hits explicitly.
  - Hermetic tests cover grok-first PATH lookup, cwd lookup and actual dispatch.
  - Template 5 and its tracked pristine render, version pins, docs and goldens.
affects: [21-04, cross-ai-dispatch]
actuals:
  tokens: 8900
  tasks: 2
  commits: 2
tech-stack:
  added: []
  patterns: [Scan-all guarded PATH resolution, versioned runner upgrades through ensure-runner]
key-files:
  created: []
  modified:
    - skills/ai-kit-spec-review/references/cross-ai.mjs
    - .planning/scripts/cross-ai.mjs
    - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai.py
    - tests/test_curated_config_script.py
    - tests/test_ai_kit_spec.py
key-decisions:
  - "Bump TEMPLATE_VERSION to 5 so plan_runner_upgrade's newer-version rule propagates this body fix; retain _READY_TEMPLATE = 3 because no hook-facing flag changed."
  - "Return absolute paths from PATH lookup so spawn cannot re-resolve a cwd hit and launch an earlier rejected agent."
  - "The test-template version bump now exercises template 5 to 6."
requirements-completed: [SPEC-06]
coverage:
  - id: D1
    description: Runner dispatch mirrors guarded scan-all cursor detection, including cwd PATH entries, without launching an earlier non-cursor agent.
    requirement: SPEC-06
    verification:
      - kind: e2e
        ref: node skills/ai-kit-spec-review/references/cross-ai.mjs --self-test (full hermetic suite; exit 0)
        status: pass
      - kind: e2e
        ref: tests.test_cross_ai_runner_e2e
        status: pass
    human_judgment: false
  - id: D2
    description: Template 5 is propagated to a pristine tracked runner while preserving its existing configuration.
    requirement: SPEC-06
    verification:
      - kind: unit
        ref: tests.test_curated_config_script
        status: pass
      - kind: other
        ref: ensure-runner render/config check and protected snapshot delta
        status: pass
    human_judgment: false
duration: 40min
completed: 2026-10-18
status: complete
---

# Phase 21 Plan 07: Guarded Cursor Runner Resolution Summary

**The cross-AI runner now scans PATH for the first guarded Cursor `agent`, avoids cwd-hit PATH re-resolution, and ships as a pristine template-5 render.**

## Performance

- **Duration:** 40 min
- **Started:** 2026-10-18
- **Completed:** 2026-10-18
- **Tasks:** 2
- **Files modified:** 17 in Task 2; Task 1 modified 2 files

## Accomplishments

- Added `pathHits` and changed `resolveBin` to scan every PATH entry for guarded `agent` hits, retaining the realpath basename check. PATH hits resolve to explicit paths so dispatch cannot select a rejected earlier executable.
- Added hermetic grok-first/later-Cursor, trailing-empty-segment/cwd, and cwd actual-spawn cases. Existing `bare-agent-guard` and `agent-cursor-realpath` remain green.
- Bumped the template to 5, advanced all version pins and seven golden values, updated docs including the README runner reference, and regenerated the tracked runner with `ensure-runner`.

## Task Commits

1. **Task 1: Scan all PATH entries for guarded Cursor agent** — `67d4cee`
2. **Task 2: Bump to template 5 and re-render tracked runner** — `9fcb876`

## Files Created/Modified

- `skills/ai-kit-spec-review/references/cross-ai.mjs` — guarded scan-all resolver and three self-test cases; template header/version.
- `skills/ai-kit-gsd-curated-config/references/runner.md` — scan behavior and template-5 documentation.
- `.planning/scripts/cross-ai.mjs` — pristine template-5 render; existing CONFIG preserved.
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai.py` — `TEMPLATE_VERSION = 5`.
- `skills/ai-kit-spec-review/ai_kit_spec/tooling_guidance.py`, `skills/ai-kit-gsd-curated-config/SKILL.md`, `README.md` — template-version documentation.
- `tests/test_curated_config_script.py`, `tests/test_ai_kit_gsd_curated_config.py`, `tests/test_ai_kit_spec.py` — updated version pins and template-text assertion.
- Seven `tests/fixtures/curated_config_v2/golden/*.json` files — version 5 values.

## Decisions Made

- `plan_runner_upgrade` only renders a pristine runner when the template is newer; template 5 is therefore required to propagate the resolver body change. `_READY_TEMPLATE` remains 3 because no hook-facing flag was added.
- `ensure-runner` returned `ready: true`, `runner: change`, `notes: []`. The pre-upgrade runner was pristine template 4. CONFIG values other than `scrubEnv` match; the existing prefer order is `['pi', 'cursor', 'opencode']`, and models are `{'codex': 'gpt-5.6-luna', 'cursor': 'auto', 'grok': 'grok-4.7', 'opencode': 'router-env/my-coding', 'pi': 'router-env/my-coding'}`. `scrubEnv` was refreshed to the current `HOST_SIGNAL_ENV_VARS` set by `default_scrub_env()`.
- Protected snapshot delta was exactly: `changed <worktree>/.planning/scripts/cross-ai.mjs`.

## Deviations from Plan

**1. [Rule 1 - Bug] Pin actual cwd dispatch and allow the explicit model in the hermetic fixture**
- **Found during:** Task 1.
- **Issue:** The requested actual-spawn case exposed a fixture gap: `composer-2.5` was not present in the fake cursor model listing, and a committed cwd symlink necessarily makes the runner's tree status dirty.
- **Fix:** Added `composer-2.5` to the fake listing, made the spawn test assert the cursor fake ran and the grok marker did not, and pinned the expected dirty-tree status for this test only.
- **Files modified:** `skills/ai-kit-spec-review/references/cross-ai.mjs`.
- **Verification:** The five-case guarded-agent self-test passed, including actual dispatch; the full self-test passed.
- **Committed in:** `67d4cee`.

**2. [Rule 1 - Bug] Retained template text assertion while allowing the Grok self-test fixture**
- **Found during:** Task 2.
- **Issue:** The unit test asserting no Grok references outside `scrubEnv` failed once the new hermetic fake modeled another CLI's Grok `agent`.
- **Fix:** Narrowed the test's inspected region to exclude the self-test case definitions while retaining the production template assertion.
- **Files modified:** `tests/test_ai_kit_spec.py`.
- **Verification:** Focused header/config test and all 42 unit modules passed.
- **Committed in:** `9fcb876`.

**Total deviations:** 2 auto-fixed (2 bugs). **Impact:** Both were needed to test the planned guarded dispatch behavior without weakening production assertions.

## Issues Encountered

The documented direct `python3 .../cli.py ensure-runner` invocation is not executable in this checkout because `cli.py` uses package-relative imports. Ran the equivalent repo-local module entry through `PYTHONPATH` and `main([...])`; it returned the expected ready/change result. No real AI CLI was run.

## Next Phase Readiness

The tracked runner now carries template 5 and the scan-all fix for Phase 21-04 dispatch.

---
*Phase: 21-cursor-live-validation*
*Completed: 2026-10-18*
