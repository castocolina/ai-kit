---
phase: 25-quota-aware-cross-ai-subprocess-supervision
plan: 03
subsystem: testing
tags: [cross-ai, classify-only, route, router-heuristic]

requires:
  - phase: 25-02
    provides: classifyStop, extractEvents, CLASSIFY_CASES and the status-line evidence tail
provides:
  - "--classify-only reads a JSON case file and prints one classification line, spawning nothing"
  - "--route-<cli> router|unknown, CONFIG.routerBacked and ROUTER_HINTS resolve the lane"
  - "router-inferred is reported but never confirms a lane"
affects: [25-06, 25-08, 25-10]

actuals:
  tokens: 26000
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "A confirmed route is the flag or an explicit CONFIG.routerBacked boolean; a name hint is advisory"

key-files:
  created: []
  modified:
    - skills/ai-kit-spec-review/references/cross-ai.mjs
    - tests/test_cross_ai_runner_e2e.py
    - tests/test_ai_kit_spec_runtimes_table.py

key-decisions:
  - "An inferred route keeps every row's base class, so a 402 stays billing"
  - "The in-process pure cases read only an explicit case route, so a rendered CONFIG.routerBacked cannot reclassify them"

patterns-established:
  - "routeOf: flag, then explicit boolean, then ROUTER_HINTS, else unknown"

requirements-completed: [QTA-01]

coverage:
  - id: D1
    description: "The runner reports route=router, route=unknown or route=router-inferred and classifies a capture without spawning"
    requirement: QTA-01
    verification:
      - kind: e2e
        ref: "node cross-ai.mjs --self-test (classify-only and route cases)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Python pins the shipped classifier's seven cases and the router hints"
    requirement: QTA-01
    verification:
      - kind: e2e
        ref: "tests.test_cross_ai_runner_e2e.TestClassifyOnly"
        status: pass
      - kind: unit
        ref: "tests.test_ai_kit_spec_runtimes_table.TestRouterHintParity"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-10-24
status: complete
orchestrator_verify: "VERIFY 25-03: 2/2 passed"
---

# Phase 25 Plan 03: Route flag and pure classify-only mode Summary

**The runner reports how it resolved its one CLI's route, and a captured message can be classified without running anything.**

## Performance

- **Duration:** 25 min
- **Started:** 2026-10-24T21:30:00Z
- **Completed:** 2026-10-24T21:55:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- `--route-<cli> router|unknown` wins over `CONFIG.routerBacked`, which wins over `ROUTER_HINTS`; the status tail prints `route=router`, `route=router-inferred` or `route=unknown`.
- A confirmed route is the only lane that promotes a row's `routerClass`; an inferred route keeps the base class (a 402 stays `billing` exit 69).
- `--classify-only <file>` prints one JSON line per case and spawns nothing; a bad file, an unknown cli or a bad route ends `status=usage` exit 2.

## Task Commits

1. **Task 1: Route resolution and the pure --classify-only mode** - `8c363b1` (feat)
2. **Task 2: Python drives the shipped classifier and pins the router hints** - (this commit) (test)

## Files Created/Modified

- `skills/ai-kit-spec-review/references/cross-ai.mjs` - `routeOf`, `ROUTER_HINTS`, `--route-<cli>`, `--classify-only`, self-test cases
- `tests/test_cross_ai_runner_e2e.py` - `TestClassifyOnly` drives the shipped runner through real node
- `tests/test_ai_kit_spec_runtimes_table.py` - `TestRouterHintParity` pins `ROUTER_HINTS` to `_ROUTER_NAME_HINTS`

## Decisions Made

The in-process pure cases (`classifyOne`) keep reading only an explicit `entry.route`. Feeding them `routeOf` made a rendered copy whose `CONFIG.routerBacked` is non-empty reclassify pinned billing fixtures as quota (`TestRenderedRunner`). The shipped `--classify-only` mode still resolves a missing route through `routeOf`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Pure cases must not inherit a rendered CONFIG route**
- **Found during:** Task 2 (Python pins classify-only output)
- **Issue:** `classifyOne` called `routeOf`, so `TestRenderedRunner`'s self-test reclassified billing fixtures as quota wherever the rendered `routerBacked` was true.
- **Fix:** `classifyOne` uses `entry.route === 'router'` only; `--classify-only` still calls `routeOf`.
- **Files modified:** `skills/ai-kit-spec-review/references/cross-ai.mjs`
- **Committed in:** `8c363b1` (amended before Task 2, unpushed)

## Authentication Gates

None.

## Known Stubs

None.

## Pre-existing failures

None.

## Deleted tests

None.

## Issues Encountered

None.

## User Setup Required

None.

## Next Phase Readiness

25-06's cycle gate can read a confirmed route (`route === 'router'`); 25-08 passes `--route-<cli>` from Python.

## Self-Check: PASSED

- `skills/ai-kit-spec-review/references/cross-ai.mjs` contains `const ROUTER_HINTS = `
- `tests/test_cross_ai_runner_e2e.py` contains `class TestClassifyOnly`
- `tests/test_ai_kit_spec_runtimes_table.py` contains `TestRouterHintParity`
- Targeted and full `--self-test` printed `self-test ok`
- Both Python modules printed `1/1 modules passed`
