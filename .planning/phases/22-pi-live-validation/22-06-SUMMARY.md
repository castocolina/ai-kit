---
phase: 22-pi-live-validation
plan: 06
subsystem: testing
tags: [pi, live-validation, owner-runbook, close-out-checker]
requires:
  - phase: 22-05
    provides: pi smoke evidence and host snapshot support
provides:
  - Owner runbook for pi RPC capture, interactive smoke, environment confirmation and optional L3 calls
  - File-only checker that gates pi label close-out on required evidence
affects: [phase-22-close-out, pi-runtime-label]
actuals:
  tokens: 2800
  tasks: 2
  commits: 2
tech-stack:
  added: []
  patterns: [evidence-table-driven close-out checker, owner-only live validation runbook]
key-files:
  created:
    - .planning/phases/22-pi-live-validation/live/check_pi_live.py
    - .planning/phases/22-pi-live-validation/22-INTERACTIVE-PI.md
    - .planning/phases/22-pi-live-validation/22-06-SUMMARY.md
  modified: []
key-decisions:
  - "L3 runs remain optional and owner-approved; without an echoed served model their evidence is inconclusive."
  - "A lifted pi label requires all S1-S5 rows to pass; all required rows passing also requires completing the label lift."
patterns-established:
  - "The close-out checker tests both an unearned label lift and a missing lift after required evidence passes."
requirements-completed: [EVAL-08, SPEC-05]
coverage:
  - id: D1
    description: Owner-run interactive pi acceptance runbook with ten pending evidence rows and a gated close-out sequence.
    requirement: EVAL-08
    verification:
      - kind: other
        ref: "owner runbook structural verification command from 22-06 Task 2"
        status: pass
    human_judgment: true
    rationale: "The interactive smoke and owner credentialed session have not yet run."
  - id: D2
    description: Read-only checker for required evidence, optional L3 outcomes and label-lift consistency.
    requirement: SPEC-05
    verification:
      - kind: unit
        ref: ".planning/phases/22-pi-live-validation/live/check_pi_live.py --self-test"
        status: pass
      - kind: other
        ref: "python3 -m py_compile .planning/phases/22-pi-live-validation/live/check_pi_live.py"
        status: pass
    human_judgment: false
duration: 2min
completed: 2026-10-23
status: complete
orchestrator_verify: "VERIFY 22-06: 2/2 passed"
---

# Phase 22 Plan 06: Pi owner runbook and close-out checker

**Pi's owner-only acceptance steps are staged with a results table, and a self-tested checker ties the label decision to evidence.**

## Performance

- **Duration:** 2 min
- **Started:** 2026-10-23T18:16:00Z
- **Completed:** 2026-10-23T18:18:13Z
- **Tasks:** 2
- **Files modified:** 2 (plus this summary)

## Accomplishments
- Added a close-out checker with `--root`, argparse usage errors, evidence validation and a self-test for lift, hold, refutation and missing-artifact cases.
- Added the owner runbook for C1, S1-S5, D9 and L3a-L3c, with safety guards, commands, pass rules, send-back requirements and orchestrator close-out instructions.
- Kept every result `pending (owner)`; no owner-only pi command or live call was run.

## Task Commits

1. **Task 1: Checker and pending results table** — `81d8fb8` (`docs(22-06): pi close-out checker and the owner results table`)
2. **Task 2: Owner runbook** — `fa3988c` (`docs(22-06): owner runbook for the interactive pi run`)

## Files Created/Modified
- `.planning/phases/22-pi-live-validation/live/check_pi_live.py` — read-only validation of runbook results and label close-out conditions.
- `.planning/phases/22-pi-live-validation/22-INTERACTIVE-PI.md` — owner runbook and pending results table.
- `.planning/phases/22-pi-live-validation/22-06-SUMMARY.md` — execution record.

## Decisions Made
- L3 remains optional, owner-approved and explicitly inconclusive when no served model is echoed.
- Required R4/R5 evidence and a completed lift are both necessary for close-out.

## Deviations from Plan

None - plan executed as written.

## Issues Encountered

- The first local usage-error probe used `--root` without its required value and correctly returned argparse exit 2; the final automated verification captured and confirmed that usage-error status.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

The owner can perform the remaining interactive checks. After results are returned, plan and execute close-out with `/gsd-plan-phase 22 --gaps`; keep this label and evidence pending until the checker passes.

## Self-Check: PASSED

- Task verification commands passed, including the checker self-test, pending-row assertions, usage exit 2, Python compilation, and runbook structure checks.
- Both task commits contain only the plan's named files; the working tree is clean for this plan's paths.

---
*Phase: 22-pi-live-validation*
*Completed: 2026-10-23*
