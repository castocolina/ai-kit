---
phase: 23-host-split-status-line-for-claude-code-and-cursor-cli
plan: 10
subsystem: cursor-quota
tags: [cursor, quota, normalization, cache-state, stdlib]
requires:
  - phase: 23-03
    provides: Synthetic Dashboard fixtures and fixture loader
provides:
  - Pure token-free Cursor Dashboard normalization and cache state functions
  - Synthetic quota cache for a deterministic wizard preview
  - Fixture-driven normalization and state edge tests
affects: [23-11, 23-12, 23-13]
actuals:
  tokens: 3600
  tasks: 2
  commits: 2
tech-stack:
  added: []
  patterns: [strict numeric parsing, pure cache-state derivation, inferred quota confidence]
key-files:
  created: [tools/cursor_quota.py, tests/test_cursor_quota.py]
  modified: [Makefile, .pre-commit-config.yaml]
key-decisions:
  - "Missing non-optional spend counters normalize to proto3 zero; missing optional percentages remain absent."
  - "Team pooled limits classify only with GetHardLimit evidence; missing evidence remains unavailable."
requirements-completed: [STL-03]
coverage:
  - id: D1
    description: Pure normalization, state, refresh, and synthetic-cache functions
    requirement: STL-03
    verification:
      - kind: unit
        ref: tests/test_cursor_quota.py
        status: pass
      - kind: other
        ref: uv run pyright tools/cursor_quota.py tests/test_cursor_quota.py
        status: pass
      - kind: other
        ref: uv run pylint tools/cursor_quota.py
        status: pass
    human_judgment: false
  - id: D2
    description: New test module is included in generated unit listings
    verification:
      - kind: unit
        ref: tests/test_gate_scope.py
        status: pass
    human_judgment: false
duration: 20min
completed: 2026-10-24
status: complete
orchestrator_verify: "VERIFY 23-10: 2/2 passed (orchestrator re-run; the verify grepped '^Ran'/'^OK$' in run_unittest_parallel output, which prints 'Ran N tests' inline and no OK line: 1/1 modules passed (8 tests), unit group 53/53, pyright 0 errors)"
---

# Phase 23 Plan 10: Cursor Quota Normalization and State Summary

**Pure Cursor Dashboard normalization and deterministic quota-cache states, with synthetic fixture coverage.**

## Performance

- **Duration:** 20 min
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Added typed `QuotaResult`, strict numeric and epoch parsing, unit conversion, inferred on-demand classifications, and included-window derivation.
- Implemented cache freshness, auth/network error ordering, cycle-end hiding, negative refresh caching, and a token-free synthetic preview cache.
- Added fixture-based tests for parsing, team evidence, units, windows, cache-state edges, and refresh behavior; generated test groups were refreshed.

## Task Commits

1. **Task 1: Three synthetic responses -> normalized data -> cache -> QuotaResult** - `48425b5` (`feat`)
2. **Task 2: Normalization and state edge tables** - `5e88137` (`test`)

## Files Created/Modified

- `tools/cursor_quota.py` - Pure Cursor quota normalization, state, refresh and synthetic-cache functions.
- `tests/test_cursor_quota.py` - Synthetic fixture tables and state edge cases.
- `Makefile` - Generated unit test listing includes the quota module.
- `.pre-commit-config.yaml` - Generated unit and hook test listings include the quota module.

## Decisions Made

- Team pooled limits require hard-limit evidence; absent or failed evidence remains unavailable.
- Missing non-optional numeric spend values use proto3 zero semantics; optional percentages stay absent.

## Deviations from Plan

None - plan executed as written.

**Total deviations:** 0. **Impact:** No scope change.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Verification

- `python3 -m unittest tests.test_cursor_quota` — 8 tests passed.
- `make test-unit` — 53/53 modules passed; unit-uv passed.
- `make arch-test` — passed.
- `uv run pyright` — 0 errors.
- Scoped ruff and pylint checks passed; AST check confirmed no module-level networking imports.

## Next Phase Readiness

The quota core and fixture contract are ready for the transport and credential increment. Owner-only live Cursor checks remain outside this plan.

---
*Phase: 23-host-split-status-line-for-claude-code-and-cursor-cli*
*Completed: 2026-10-24*
