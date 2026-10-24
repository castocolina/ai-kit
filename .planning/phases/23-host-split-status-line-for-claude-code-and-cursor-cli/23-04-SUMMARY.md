---
phase: 23-host-split-status-line-for-claude-code-and-cursor-cli
plan: 04
subsystem: status-line
tags: [python, ast, status-line, architecture]
requires:
  - phase: 23-01
    provides: Claude render byte-oracle
  - phase: 23-02
    provides: Reviewed status-line split audit
provides:
  - Stage 1 and stage 2 pure moves from the Claude status-line monolith
  - Per-module architecture rules and audit-driven split conformance checks
affects: [23-05, status-line]
actuals:
  tokens: 500
  tasks: 3
  commits: 3
tech-stack:
  added: []
  patterns: [AST-backed split conformance, per-module architecture invariants]
key-files:
  created: []
  modified: [tests/test_arch.py, tools/common_config.py, tools/status-line.py]
key-decisions:
  - "Kept the existing split hash and location checkers as pure audit-map-driven helpers."
requirements-completed: [STL-01]
coverage:
  - id: D1
    description: Stage 1 and stage 2 definitions moved according to the audit table without assertion changes.
    requirement: STL-01
    verification:
      - kind: unit
        ref: "python3 tmp/p23/04/split_check_tests.py"
        status: pass
      - kind: unit
        ref: "tests/test_status_line.py#oracle classes"
        status: pass
    human_judgment: false
  - id: D2
    description: Split modules are checked for architecture rules and moved rows are checked against the audit AST and location map.
    requirement: STL-01
    verification:
      - kind: unit
        ref: "python3 tools/run_unittest_parallel.py tests.test_arch"
        status: pass
      - kind: other
        ref: "split_hash_mismatches(include_generalized=True) and split_location_problems()"
        status: pass
    human_judgment: false
duration: under 1h
completed: 2026-10-24
status: complete
orchestrator_verify: "(orchestrator: Task 3 finished by a continuation run; pyright fixed by restoring pre-split Any typing parity, 4245cbf)"
---

# Phase 23 Plan 04: Staged Claude Status-Line Split Summary

**The Claude status-line's first two audit stages are mechanically split into shared and Claude modules, with per-module architecture and AST-conformance guards.**

## Performance

- **Duration:** Under one hour for this continuation.
- **Tasks:** 3 (Tasks 1 and 2 were committed before this continuation; Task 3 completed here).
- **Files modified in Task 3:** 1.

## Accomplishments

- Stage 1 pure move committed as `bc3bfaa`; stage 2 pure move committed as `5a80d49`.
- Added per-split-module checks for architecture rules 2, 3, 4, 5, 6 and 7, with non-vacuity coverage.
- Added AST hash and location conformance checks for audit rows and non-vacuity tests for changed definitions and misplaced rows.
- Verified the assertion-diff checker reports unchanged assertions in each of the three rewritten test files.

## Task Commits

1. **Task 1: Stage 1 split move** — `bc3bfaa` (`refactor(23-04): stage 1 split move (types, formatters, helpers)`).
2. **Task 2: Stage 2 split move** — `5a80d49` (`refactor(23-04): stage 2 split move (config, probes, Claude payload)`).
3. **Task 3: Per-module architecture rules and split conformance** — `a8c8b57` (`test(23-04): per-module arch rules and split conformance`).

## Files Created/Modified

- `tests/test_arch.py` — per-module rules, audit conformance helpers and non-vacuity tests.
- `tools/common_config.py`, `tools/status-line.py`, and the other split modules — stage 2 move (Task 2, commit `5a80d49`).
- `tmp/p23/04/split_move.py` — disposable mover retained for plan 23-05.
- `tmp/p23/04/split_rewrite_tests.py` — disposable test rewriter retained for plan 23-05.
- `tmp/p23/04/split_check_tests.py` — assertion-diff checker retained; rerun with `python3 tmp/p23/04/split_check_tests.py`.

## Decisions Made

Kept the conformance logic driven by the reviewed audit table, reversing public-name changes before AST hashing and checking moved definitions' unique locations.

## Deviations from Plan

None - plan executed as instructed for the remaining task.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

The stage 1 and stage 2 move tooling remains under `tmp/p23/04/` for plan 23-05. The assertion-diff checker can be rerun with `python3 tmp/p23/04/split_check_tests.py`.

---
*Phase: 23-host-split-status-line-for-claude-code-and-cursor-cli*
*Completed: 2026-10-24*
