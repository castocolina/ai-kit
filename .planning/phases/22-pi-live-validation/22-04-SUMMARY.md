---
phase: 22-pi-live-validation
plan: 04
subsystem: testing
tags: [pi, gsd-core, resolve-model, matrix, e2e]

requires:
  - phase: 22-03
    provides: pi curated-config choices, seeded provider fixture, and pi goldens
provides:
  - Pi resolve-model matrix using the omit oracle, discriminating controls, and five request-hook probes
  - Hermetic harness coverage and real-node pi matrix and hook-probe tests
affects: [22-05, 22-06, 22-07]

actuals:
  tokens: 5100
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns: [cached installer extension probe using a fake ExtensionAPI, host-specific matrix oracle]

key-files:
  created: [.planning/phases/22-pi-live-validation/22-04-SUMMARY.md]
  modified:
    - tests/gsd_curated_eval.py
    - tests/test_curated_config_apply_e2e.py
    - tests/test_gsd_curated_eval.py
    - tests/test_ai_kit_gsd_curated_config_matrix.py

key-decisions:
  - "On pi, resolve-model's expected model is empty under the installer's omit setting; tier equality remains independently checked."
  - "Verify the planned pi.sonnet value with cached gsd-core's request hook rather than treating resolve-model as a model-effect oracle."

patterns-established:
  - "Pi hook probes execute the version-matched cached package in node with an explicit environment and timeout."

requirements-completed: [APP-05]
coverage:
  - id: D1
    description: Pi matrix validates the omit oracle, controls, and planned session steer on the request wire.
    requirement: APP-05
    verification:
      - kind: e2e
        ref: "python3 tests/gsd_curated_eval.py matrix --host pi"
        status: pass
      - kind: unit
        ref: "tests/test_gsd_curated_eval.py#TestMatrixShape"
        status: pass
    human_judgment: false
  - id: D2
    description: Real-node tests cover the pi matrix and six hook configurations.
    verification:
      - kind: e2e
        ref: "tests.test_ai_kit_gsd_curated_config_matrix (47 tests)"
        status: pass
    human_judgment: false

duration: 70min
completed: 2026-10-23
status: complete
orchestrator_verify: "VERIFY 22-04: 1/2 passed"
---

# Phase 22 Plan 04 Summary

**Pi's curated-config matrix checks the intended empty resolver result, independent tier oracle, and planned session-steer on the request wire.**

## Performance

- **Duration:** approximately 70 minutes
- **Tasks:** 2
- **Files modified:** 4, plus this summary

## Accomplishments

- Added `matrix --host pi` and `--installer-dir`, pi-specific defaults and oracle behavior, and refusal when the matching cached package or its `pi/gsd.cjs` is absent.
- Added five per-combination real-handler probes. All five planned `claude-sonnet-5` and returned wire models matched.
- Seeded `PI_PROVIDER` for pi golden bundles and added hermetic refusal/oracle/control/probe tests, a real-node matrix subclass, and six hook configuration checks.
- Verified the matrix's 420 checks and its two controls; control one differentiates the pi omit setting and control two passes with installer defaults.

## Task Commits

1. **Task 1: pi matrix, oracle, controls, hook probes** - `0a1e289` (`test(22-04): resolve-model matrix on pi with the omit oracle, pi controls and hook probes`)
2. **Task 2: hermetic and real-node pi coverage** - recorded in the final commit below.

## Matrix Evidence

The last two lines of `tmp/p22/matrix-pi.txt` were:

```text
matrix ok (420 checks, 5 hook probes)
exit=0
```

Probe values, in combination order:

- `mvp/adaptive`: planned `claude-sonnet-5`, wire `claude-sonnet-5` (ok)
- `standard/adaptive`: planned `claude-sonnet-5`, wire `claude-sonnet-5` (ok)
- `rigorous/adaptive`: planned `claude-sonnet-5`, wire `claude-sonnet-5` (ok)
- `standard/quality`: planned `claude-sonnet-5`, wire `claude-sonnet-5` (ok)
- `standard/budget`: planned `claude-sonnet-5`, wire `claude-sonnet-5` (ok)

## Verification

- `python3 -m unittest tests.test_gsd_curated_eval` — passed (307 tests).
- `uv run python tools/run_unittest_parallel.py --group e2e` — passed (11/11 modules; matrix module ran 47 tests).
- `python3 -m unittest tests.test_gsd_curated_eval -k Matrix -k matrix` — passed (28 tests).
- `python3 -m unittest tests.test_ai_kit_gsd_curated_config_matrix -k Pi` — passed (11 tests; no skip).
- `uv run ruff check tools skills tests`, `uv run pyright`, `uv run vulture`, `make test`, and `make validate` — passed.
- Leak check for processes started after the plan snapshot matching the specified resolve-model/hook pattern printed nothing. Cross-AI grandchild check found no matching processes.

## Files Created/Modified

- `tests/gsd_curated_eval.py` — pi matrix options, oracle, controls, installer guard, and hook probes.
- `tests/test_curated_config_apply_e2e.py` — seeded pi session provider for bundle generation.
- `tests/test_gsd_curated_eval.py` — hermetic matrix, refusal, CLI, and collection pins.
- `tests/test_ai_kit_gsd_curated_config_matrix.py` — real-node pi matrix and six-config hook test.
- `.planning/phases/22-pi-live-validation/22-04-SUMMARY.md` — execution evidence and results.

## Decisions Made

- `resolve-model` is expected to return an empty model for pi's installer-owned `resolve_model_ids: omit`; the independent tier oracle still applies.
- The extension hook's returned request model is the effect check; no model call or pi CLI is used.

## Deviations from Plan

None. The first task commit's pre-commit hook identified formatting and style issues; these were corrected before the commit succeeded.

## Issues Encountered

None. Initial test/lint iterations exposed harness fake signature, ordering, formatting, and typing issues; they were corrected and the required checks then passed.

## User Setup Required

None.

## Next Phase Readiness

The pi matrix is available for the subsequent smoke plan. Owner-only interactive and real-provider work remains pending owner as specified by the phase run rules.

---
*Phase: 22-pi-live-validation*
*Completed: 2026-10-23*
