---
phase: 25-quota-aware-cross-ai-subprocess-supervision
plan: 06
subsystem: infra
tags: [cross-ai, runner, quota-cycles, node, template-7]

requires:
  - phase: 25-05
    provides: the pure ladderNext, the 3 plus 3 transient rungs and the dirty-tree gate
provides:
  - router quota cycles that span runner calls under a hard 4-hour cap
  - a 0600 lane-and-model state file with due_at, last_sid and task_digest
  - attempt and report evidence lines plus attempts and cycles status tokens
  - runner template 7
affects: [25-07, 25-09, 25-10]

actuals:
  tokens: 12000
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns: [quota cycles persist across calls in an XDG state file]

key-files:
  created: []
  modified:
    - skills/ai-kit-spec-review/references/cross-ai.mjs
    - skills/ai-kit-spec-review/ai_kit_spec/tooling_guidance.py
    - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai.py
    - tests/test_curated_config_script.py
    - tests/test_ai_kit_gsd_curated_config.py
    - tests/test_ai_kit_spec.py
    - tests/fixtures/curated_config_v2/golden

key-decisions:
  - "A cap stop exits 69 with no retry_after_s; a rungs or deadline stop exits 75 with the cooldown"
  - "The child timer clamps to the quota cap itself; the 60 s reserve only gates admitting the next rung"
  - "A dirty-tree stop inside a quota cycle keeps status=quota and reports stopped=dirty-tree"
  - "reportAndFinish emits the one report line for every non-ok exit, so no stop path can skip it"

patterns-established:
  - "Cycle state lives at $XDG_STATE_HOME/ai-kit/spec/cycles/<sha>/<cli>-<model>.json, mode 0600"
  - "Version pins read the shipped template version instead of a literal, so the next bump needs no test edit"

requirements-completed: [QTA-03, QTA-01]

coverage:
  - id: D1
    description: "A confirmed router quota walks 3 same-session retries and 3 new sessions, then exits 75 with retry_after_s and cycle and a state file"
    requirement: QTA-03
    verification:
      - kind: e2e
        ref: "node cross-ai.mjs --self-test#router-quota-one-cycle,router-quota-second-cycle"
        status: pass
    human_judgment: false
  - id: D2
    description: "A re-entry before due_at spawns nothing, a stale file starts fresh, and an active episode past the cap exits 69"
    requirement: QTA-03
    verification:
      - kind: e2e
        ref: "node cross-ai.mjs --self-test#router-quota-early-reentry,stale-state-fresh-start,expired-state-cap-stop"
        status: pass
    human_judgment: false
  - id: D3
    description: "Off-router and inferred quota stop after one call with no cycle state"
    requirement: QTA-03
    verification:
      - kind: e2e
        ref: "node cross-ai.mjs --self-test#plain-quota-no-retry,inferred-quota-stop,inferred-quota-no-cycle"
        status: pass
    human_judgment: false
  - id: D4
    description: "Every stop prints attempt lines and one report line, and no line carries a key"
    requirement: QTA-01
    verification:
      - kind: e2e
        ref: "node cross-ai.mjs --self-test#sentinel-evidence"
        status: pass
    human_judgment: false
  - id: D5
    description: "Template 7 is pinned by tests that read the shipped version and by the golden fixtures"
    requirement: QTA-03
    verification:
      - kind: unit
        ref: "tests.test_ai_kit_spec#test_header_and_config_contract, tests.test_curated_config_golden"
        status: pass
    human_judgment: false

duration: 150min
completed: 2026-10-24
status: complete
orchestrator_verify: "VERIFY 25-06: 3/3 passed"
---

# Phase 25 Plan 06: Router Quota Cycles Summary

**Router quota cycles across calls under a 4-hour cap, with evidence on every stop, shipped as runner template 7**

## Performance

- **Duration:** 150 min
- **Started:** 2026-10-24T22:10:00Z
- **Completed:** 2026-10-24T23:40:00Z
- **Tasks:** 3
- **Files modified:** 15

## Accomplishments

- A confirmed router quota walks the 3 plus 3 rungs inside one call, then exits 75 with
  `retry_after_s` and `cycle` and a 0600 state file the next call reads.
- The 4-hour cap is wall-clock from `first_seen`: a stale file starts fresh, an active episode
  past the cap exits 69 before spawning, and a child timer is clamped to the cap.
- Every non-ok run prints `cross-ai: attempt` lines and one `cross-ai: report` line, and the
  status line carries `attempts=` and `cycles=`.
- The template header reads `template=7`, `TEMPLATE_VERSION` is 7, and the version pins read the
  shipped version instead of a literal.

## Task Commits

Each task was committed atomically:

1. **Task 1: Router quota cycles with cooldown and the 4-hour cap** - `d9dd76b` (feat)
2. **Task 2: Attempt lines, the report line and the sentinel scan** - `6f03285` (feat)
3. **Task 3: Template 7, the dirty-tree demotion cases and the version pins** - `5f6fd32` (feat)

## Files Created/Modified

- `skills/ai-kit-spec-review/references/cross-ai.mjs` - quota cycles, the state file, evidence
  lines and the template 7 header
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai.py` - `TEMPLATE_VERSION = 7`
- `skills/ai-kit-spec-review/ai_kit_spec/tooling_guidance.py` - the template v7 docstring
- `tests/test_curated_config_script.py` - version pins read the shipped template
- `tests/test_ai_kit_gsd_curated_config.py` - the same, for the apply path
- `tests/test_ai_kit_spec.py` - the header version and the CONFIG dict pin template 7
- `tests/fixtures/curated_config_v2/golden` - seven goldens regenerated at version 7

## Decisions Made

- A cap stop exits 69 without `retry_after_s`, while a rungs or deadline stop exits 75 with the
  cooldown: the caller only waits when another cycle can still happen.
- The child timer clamps to the quota cap itself. The 60 s reserve stays an admission rule, so a
  child admitted with 8 s of cap left is stopped at the cap rather than refused.
- A dirty-tree stop inside a quota cycle reports `status=quota` with `stopped=dirty-tree`, which
  keeps the quota exit code the demotion cases pin.
- One helper, `reportAndFinish`, writes the single report line for every non-ok exit. The early
  exits (usage, no model, not installed, signal, bad model) go through it too.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] The quota child timer was clamped to the call deadline, which a self-test copy never sets**
- **Found during:** Task 1 (the cap-clamp case)
- **Issue:** `runOnce` bounded every child by `runDeadline`, and a copy spawned with an explicit
  outer timeout still left the quota end unreachable, so the cap clamp never fired.
- **Fix:** `runCli` passes the quota end as the child limit when a cycle is active, and the case
  sets `--outer-timeout 200` with 8 s of cap remaining.
- **Files modified:** `skills/ai-kit-spec-review/references/cross-ai.mjs`
- **Verification:** `quota-cap-clamp-child` exits 69 `stopped=cap` well inside the case budget
- **Committed in:** `d9dd76b` (Task 1 commit)

**2. [Rule 2 - Missing] A dirty-tree stop dropped the quota status**
- **Found during:** Task 3 (the dirty-billing-router case)
- **Issue:** The rung-2 gate returns `transient`, so a router quota over edits exited
  `status=transient` instead of the pinned `status=quota`.
- **Fix:** A quota cycle keeps `status=quota` when the gate stops it and reports
  `stopped=dirty-tree`.
- **Files modified:** `skills/ai-kit-spec-review/references/cross-ai.mjs`
- **Verification:** `dirty-billing-router` runs 4 calls on one session and exits 75
- **Committed in:** `5f6fd32` (Task 3 commit)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 missing behavior)
**Impact on plan:** Both were required for the plan's own cases to pass. No scope added.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The full self-test printed `self-test ok` in 116 s, inside the 120 s budget.
- 25-07 re-renders the dogfood `.planning/scripts/cross-ai.mjs` onto template 7 next, and nothing
  lands between this commit and that re-render.
- The curated-config, golden, spec and runner e2e modules passed:
  `2/2 modules passed` for the curated-config pair, `2/2 modules passed` for spec plus golden,
  and `1/1 modules passed` for `tests.test_cross_ai_runner_e2e`.

## Self-Check: PASSED

- `d9dd76b`, `6f03285` and `5f6fd32` are in `git log`; this summary amends the last of them.
- `25-06-SUMMARY.md` is committed with the last task.

---
*Phase: 25-quota-aware-cross-ai-subprocess-supervision*
*Completed: 2026-10-24*
