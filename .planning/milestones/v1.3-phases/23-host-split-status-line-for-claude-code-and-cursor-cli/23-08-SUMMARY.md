---
phase: 23-host-split-status-line-for-claude-code-and-cursor-cli
plan: 08
subsystem: statusline
tags: [claude, migration, atomic-files]
requires:
  - phase: 23-07
    provides: Host-split Claude renderer and payload contract
provides:
  - Hard rename of the Claude status-line entry and sample
  - Atomic create-if-absent helper and owned-command/config migration
  - README upgrade/recovery guidance
affects: [setup, statusline, phase-23-14]
actuals:
  tokens: 2500
  tasks: 2
  commits: 2
tech-stack:
  added: []
  patterns: [exact-argv ownership parser, link-based create-if-absent publication]
key-files:
  created: [tools/command_ownership.py]
  modified: [tools/setup.py, tests/test_setup.py, README.md]
key-decisions:
  - "Bare --headless remains a no-op; migration runs on interactive setup/reconfigure and opted-in headless runs."
patterns-established:
  - "Only a recognized Python command with the exact old script argument is eligible for migration."
requirements-completed: [STL-01]
coverage:
  - id: D1
    description: Claude entry and sample are hard-renamed, and setup wires/renders the new entry.
    requirement: STL-01
    verification:
      - kind: unit
        ref: tests.test_setup#TestHeadlessInstall.test_headless_with_statusline_wires_and_renders_new_entry
        status: pass
    human_judgment: false
  - id: D2
    description: Owned status-line commands and old TOML migrate without overwriting existing content.
    requirement: STL-01
    verification:
      - kind: unit
        ref: tests.test_setup#TestStatuslineMigration
        status: pass
    human_judgment: false
  - id: D3
    description: Atomic create-if-absent publication retains existing destinations and cleans temporary files.
    verification:
      - kind: unit
        ref: tests.test_setup#TestCreateIfAbsent
        status: pass
    human_judgment: false
duration: 16min
completed: 2026-10-24
status: complete
orchestrator_verify: "VERIFY 23-08: 2/2 passed (+ failure-injection matrix 8c0da9d; lazy command_ownership import 0ecb088; make test and make validate exit 0)"
---

# Phase 23 Plan 08: Claude Status-Line Rename and Migration Summary

**Renamed the Claude entry and recipe, and added conservative, atomic upgrade migration.**

## Performance

- **Duration:** 16 min
- **Tasks:** 2
- **Files modified:** 24

## Accomplishments

- Renamed `tools/status-line.py` and `tools/statusline.toml.sample` without compatibility shims; updated references and the moved precompact probe reference.
- Added `create_if_absent`, the conservative `command_ownership` parser, and `migrate_statusline`; wired migration before setup writes, while bare `--headless` remains a no-op.
- Documented hard-rename recovery and the foreign-command/both-TOMLs rules in README.
- The recorded `create_if_absent` child processes all exited; the leak check was empty. No `ps` scan or process-name selection was used.

## Task Commits

1. **Task 1: Hard rename end to end** — `67ea9b2` (`refactor(23-08): rename the Claude entry and sample (no shim)`).
2. **Task 2: Migration and race-safe helper** — `949aeb3` (`feat(23-08): idempotent atomic status-line migration and create-if-absent`).
3. **Failure-injection matrix** — recorded in the continuation commit listed below.

## Files Created/Modified

- `tools/claude-status-line.py`, `tools/claude-statusline.toml.sample` — renamed Claude renderer and recipe.
- `tools/command_ownership.py` — conservative Python argv ownership parser.
- `tools/setup.py` — new paths, atomic publication, migration and setup call sites.
- `tests/test_setup.py`, `tests/test_status_line.py`, `tests/test_external_segments.py`, `tests/test_statusline_doctor.py`, `tests/test_wizard_pty.py`, `tests/test_system_memory_e2e.py`, `tests/test_worktree_e2e.py`, `tests/test_tool_substitution_hook.py`, `tests/test_claude_precompact.py`, `tests/test_arch.py`, `tests/test_install.sh` — rename references and migration/render tests.
- `tools/claude_host.py`, `tools/statusline-doctor.py`, `tools/wizard_app.py`, `tools/install.sh`, `tools/hooks/precompact_core.py`, `pyproject.toml`, `README.md` — references and documentation.

## Deviations from Plan

None. The continuation added failure-injection coverage for fsync cleanup, link fallback, lost publication races, unreadable settings, dry-run behavior, and command-before-TOML ordering/publication failure. A type-narrowing defect in the migration helper was also corrected.

## Issues Encountered

None.

## Deleted tests

None.

## Pre-existing failures

None.

## Verification

- Task 1: rename/reference gate passed (`references ok`); scoped `tests.test_setup`, `tests.test_status_line`, `tests.test_external_segments`, `tests.test_statusline_doctor`, and `tests.test_arch`: 5/5 modules passed.
- Task 2 and continuation: `uv run python tools/run_unittest_parallel.py tests.test_setup`: `1/1 modules passed` (364 tests); all 16 recorded child PIDs exited.
- `uv run ruff check tools/setup.py tests/test_setup.py` passed; `uv run pyright` reported 0 errors, 0 warnings, 0 informations.
- Global `make test` and `make validate` are wave-barrier checks and were not run by this executor.

## Next Phase Readiness

The renamed paths and shared command-ownership parser are available for Plan 23-14. Global gates remain for the orchestrator's serialized wave barrier.

---
*Phase: 23-host-split-status-line-for-claude-code-and-cursor-cli*
*Completed: 2026-10-24*
