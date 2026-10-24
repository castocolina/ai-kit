---
phase: 23-host-split-status-line-for-claude-code-and-cursor-cli
plan: 02
subsystem: testing
tags: [status-line, ast, audit, unittest]
requires: []
provides:
  - 182-row status-line split audit and base-blob AST integrity check
  - Per-row reviewed classification reasons with taint disagreement rules and non-vacuity tests
affects: [23-04, 23-05, 23-06, 23-07, 23-08, 23-09]
actuals:
  tokens: 9000
  tasks: 2
  commits: 2
tech-stack:
  added: []
  patterns: [AST-derived audit fixture, taint propagation to fixpoint]
key-files:
  created: [tests/fixtures/statusline_split/audit.md]
  modified: [tests/test_arch.py]
key-decisions:
  - "Pinned taint vocabulary yields 23 seed and 10 propagated rows; do not reuse the unreproducible 29/9 estimate."
patterns-established:
  - "Position-keyed audit rows preserve source order and distinguish same-named definitions."
requirements-completed: [STL-01]
coverage:
  - id: D1
    description: "182-row ASCII move and conformance audit checked against the base git blob."
    requirement: STL-01
    verification:
      - kind: unit
        ref: tests.test_arch.TestSplitAudit
        status: pass
      - kind: other
        ref: "python3 -m unittest tests.test_arch"
        status: pass
    human_judgment: false
  - id: D2
    description: "Reviewed reasons explain taint disagreements, and non-vacuity tests cover audit integrity rules."
    requirement: STL-01
    verification:
      - kind: unit
        ref: tests.test_arch.TestArchNonVacuity
        status: pass
      - kind: other
        ref: make arch-test
        status: pass
    human_judgment: false
duration: 12min
completed: 2026-10-24
status: complete
orchestrator_verify: "VERIFY 23-02: 2/2 passed (orchestrator re-run; the plan's verify read audit_rows() as a list, but its action specifies (headers, rows): unpacked, then 182 rows, 23 seed/10 prop, reasons ok, test_arch 40 OK)"
---

# Phase 23 Plan 02: Status-line Split Audit Summary

**A reviewed, 182-row audit maps every definition in the pre-split renderer to its staged destination and validates against the pinned base blob.**

## Performance

- **Duration:** 12 min
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Added the ASCII audit table with AST hashes, staged module mapping, neutrality, fate and taint for all 182 top-level definitions.
- Added base-blob comparison, pinned-vocabulary taint propagation and classification validation in `tests/test_arch.py`.
- Reviewed each row's reason and added tests for missing rows, hash changes, ordering, duplicate names and taint disagreements.

## Task Commits

1. **Task 1: Generated table and base-blob check** - `f05a4c5`.
2. **Task 2: Reviewed reasons and non-vacuity twins** - `e650de1`.

## Files Created/Modified

- `tests/fixtures/statusline_split/audit.md` - machine-readable move and conformance map.
- `tests/test_arch.py` - audit parser, integrity/taint checkers and non-vacuity tests.

## Decisions Made

- The pinned vocabulary computes 23 seed and 10 propagated taint rows; the research note's 29/9 figures are not reproduced.

## Deviations from Plan

None - plan executed as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

The audit map is available to the staged move plans. Project-wide gates remain the orchestrator's wave barrier.
