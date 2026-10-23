---
phase: 21-cursor-live-validation
plan: 02
subsystem: cursor-agents
tags: [cursor, subagents, frontmatter, unittest]
requires:
  - phase: 21-01
    provides: Cursor model listing parser and captured model fixture
provides:
  - Two explicitly pinned non-fast Cursor worker agents with parser, model-listing and catalog-collision coverage.
  - README guidance for manual per-file linking until backlog 999.7.
affects: [backlog-999.7, cursor-agent]
actuals:
  tokens: 2100
  tasks: 2
  commits: 2
tech-stack:
  added: []
  patterns: [Bundle-compatible frontmatter parser test, node -e dialect parity oracle]
key-files:
  created:
    - cursor-agents/composer-worker.md
    - cursor-agents/grok-worker.md
    - tests/test_cursor_agents.py
  modified:
    - tests/test_curated_config_e2e.py
    - tests/test_ai_kit_spec.py
    - Makefile
    - .pre-commit-config.yaml
    - README.md
key-decisions:
  - "Kept Cursor agents in cursor-agents/ rather than agents/ because agents/ is linked into Claude's agent directory."
  - "The live GSD catalog test skips only when node or checkout-local model-catalog.cjs is unavailable; a failed available query fails the test."
requirements-completed: [AGT-01]
coverage:
  - id: D1
    description: Two Cursor executor subagents are pinned to captured non-fast model ids and checked against the bundle parsing rules.
    requirement: AGT-01
    verification:
      - kind: unit
        ref: tests.test_cursor_agents (10 tests, including node parity and captured model twin checks)
        status: pass
      - kind: e2e
        ref: tests.test_curated_config_e2e.TestCursorAgentNamesAbsentFromCatalog
        status: pass
    human_judgment: false
  - id: D2
    description: README explains the agent directory, why it is separate from agents/, and the manual linking path.
    verification:
      - kind: other
        ref: README.md cursor-agents paragraph
        status: pass
    human_judgment: false
  - id: D3
    description: New unit module is registered and passes unit-tier and configured lint checks.
    verification:
      - kind: unit
        ref: python3 tools/run_unittest_parallel.py --group unit (43/43 modules passed)
        status: pass
      - kind: other
        ref: ruff, pyright and vulture pre-commit hooks
        status: pass
    human_judgment: false
duration: 0min
completed: 2026-10-18
status: complete
orchestrator_verify: "VERIFY 21-02: 1/2 passed"
---

# Phase 21 Plan 02: Cursor Worker Agents Summary

**Two Cursor executor agents now use explicit non-fast model pins, with parser, listing, catalog, and registration checks.**

## Performance

- **Duration:** Single execution session
- **Started:** 2026-10-18
- **Completed:** 2026-10-18
- **Tasks:** 2
- **Files modified/created:** 8

## Accomplishments

- Shipped `composer-worker` pinned to `composer-2.5` and `grok-worker` pinned to `grok-4.7-medium` in `cursor-agents/`.
- Added a Python port of the Cursor bundle parser, allowlist and edge-case tests, captured-listing non-fast twin checks, and a scoped Node regex-dialect parity oracle.
- Added an e2e live catalog collision check that fails on query failure, registered the unit module in generated listings, and documented manual per-file linking and backlog 999.7.

## Task Commits

1. **Task 1: Ship Cursor agents and parser/catalog tests** — `009f1ff`
2. **Task 2: Document cursor-agents and pass validate-hook lint** — recorded with this summary commit.

## Files Created/Modified

- `cursor-agents/composer-worker.md` — executor prompt pinned to composer-2.5.
- `cursor-agents/grok-worker.md` — executor prompt pinned to grok-4.7-medium.
- `tests/test_cursor_agents.py` — bundle parser port, static rules, model pins and Node parity.
- `tests/test_curated_config_e2e.py` — live GSD catalog collision check.
- `Makefile`, `.pre-commit-config.yaml` — generated unit-group registration.
- `tests/test_ai_kit_spec.py` — narrowed a `None` typing issue surfaced by the tree-wide pyright gate.
- `README.md` — directory purpose and manual linking instructions.

## Decisions Made

- Kept these files outside `agents/` to prevent Claude from loading Cursor-specific model pins.
- Kept the catalog cross-check in the e2e tier because it runs real Node against checkout-local gsd-core.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected pyright optional-value narrowing surfaced by the tree-wide hook**
- **Found during:** Task 2 lint
- **Issue:** Pyright reported optional-value errors in the new tests and the adjacent captured Cursor listing test from Task 1.
- **Fix:** Added explicit post-assert narrowing for parser results, node discovery, and the catalog query result.
- **Files modified:** `tests/test_cursor_agents.py`, `tests/test_curated_config_e2e.py`, `tests/test_ai_kit_spec.py`.
- **Verification:** `uv run pre-commit run pyright --hook-stage pre-push --files tests/test_cursor_agents.py` passed (the hook is tree-wide); ruff, vulture, and all 43 unit modules passed.
- **Committed in:** Task 2 commit.

**Total deviations:** 1 auto-fixed (1 bug). **Impact:** Type narrowing makes the new and immediately related parser tests valid under the configured whole-tree checker.

## Issues Encountered

`tests/gsd_curated_eval.py snapshot --check tmp/p21/plan02.before.json` reported a changed `.planning/config.json`. The snapshot was captured before an independent orchestrator commit (`dd163c4`) changed that file. Capturing a fresh post-change baseline and checking it returned `snapshot ok`; no orchestrator config change was reverted.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

AGT-01 files and tests are ready for later project-level linking work in backlog 999.7. No live Cursor CLI or user configuration was used.

---
*Phase: 21-cursor-live-validation*
*Completed: 2026-10-18*
