---
phase: 23-host-split-status-line-for-claude-code-and-cursor-cli
plan: 12
subsystem: cursor-quota
tags: [cursor, quota, cache, flock, detached-refresh]
requires:
  - phase: 23-11
    provides: Credential reader and Dashboard transport
provides:
  - Private atomic Cursor quota cache and non-blocking flock refresher
  - Detached cache-refresh CLI and cache-only read path
affects: [23-13]
actuals:
  tokens: 9200
  tasks: 2
  commits: 2
tech-stack:
  added: []
  patterns: [0600 atomic cache publication, child-owned advisory flock, detached refresh]
key-files:
  created: []
  modified: [tools/cursor_quota.py, tests/test_cursor_quota.py, tests/test_arch.py]
key-decisions:
  - "A render probes and releases the lock before spawning; the child independently acquires and holds its own lock."
  - "A cache write refuses paths outside a verified, owned cursor cache directory."
requirements-completed: [STL-03, STL-04]
coverage:
  - id: D1
    description: Private atomic quota cache and single-flight refresh lifecycle
    requirement: STL-03
    verification:
      - kind: unit
        ref: tests/test_cursor_quota.py
        status: pass
      - kind: other
        ref: "python3 -S tools/cursor_quota.py --refresh: scratch-HOME auth_missing cache and mode check"
        status: pass
    human_judgment: false
  - id: D2
    description: Detached refresher survives a killed render process and publishes token-free negative cache
    requirement: STL-04
    verification:
      - kind: unit
        ref: tests/test_cursor_quota.py#test_production_read_spawns_detached_refresher
        status: pass
    human_judgment: false
  - id: D3
    description: Architecture suite remains green
    verification:
      - kind: unit
        ref: tests/test_arch.py
        status: fail
    human_judgment: true
    rationale: Two existing common_fmt role-prefix failures reproduce unchanged at the plan base commit; rules report util_window_gap in block 2.CFG_ lacking the fmt_ prefix.
duration: 110min
completed: 2026-10-24
status: halted
orchestrator_verify: "(orchestrator: test_arch caught util_window_gap from 23-07 in a cfg_ block, moved in 27d0add; 23-12's pyright errors fixed in f2f7bfd)"
---

# Phase 23 Plan 12: Cursor quota cache and detached refresher summary

**Cursor quota reads return cache state immediately while a detached, flock-protected child refreshes token-free cache data.**

## Performance

- **Duration:** approximately 110 min
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Implemented private 0700 cache directory checks, tolerant reads and atomic 0600 JSON writes using fsync and replace.
- Added sibling lock-file probing and child-owned non-blocking flock, cache freshness recheck, detached `--refresh` CLI and negative-cache preservation.
- Tested cache permissions, token exclusion, symlink refusal, atomic-write failure, lock contention, SIGKILL release, stale-data preservation and killed-render survival.
- Added the refresher exception to architecture rule 11.

## Task Commits

1. **Task 1: Cache, lock and detached refresher** - `9f93d9c` (`feat`)
2. **Task 2: Concurrency, failure and kill coverage** - `e65b4df` (`test`; includes this summary)

## Files Created/Modified

- `tools/cursor_quota.py` - Cache, lock, detached spawn, refresh lifecycle and CLI.
- `tests/test_cursor_quota.py` - Cache, concurrency, negative-cache, SIGKILL and runner-simulator tests.
- `tests/test_arch.py` - Rule 11 allowlist entry for the detached refresher.

## Decisions Made

- Render-side flock probe is immediately released and passes no descriptor; the child obtains its own lock.
- The lock file remains in place; kernel release on process death is the recovery mechanism.

## Deviations from Plan

- **[Rule 1 - Existing failure] Architecture test gate is red at the plan base.** Found during: Task 1 verification. `tests.test_arch` fails two role-prefix checks in `common_fmt.py` because `util_window_gap` falls under a `CFG_` banner. Verified unchanged by archiving the task base and rerunning `tests.test_arch`. The task scope permits only the rule 11 allowlist edit in that file, so the unrelated source/banner correction was not included.

**Total deviations:** 1 existing-failure report. **Impact:** quota tests and CLI verification pass; the plan's combined required architecture gate remains blocked by the reproduced base failure.

## Issues Encountered

- The required combined `tests.test_cursor_quota` + `tests.test_arch` verification does not pass: the quota module passes, while architecture has the two verified pre-existing common_fmt failures described above.
- Leak check: `ps -eo pid,args | grep -E 'gc-late|node -e while' | grep -v grep` returned no matches.

## User Setup Required

None. Live Cursor checks remain not run (owner).

## Next Phase Readiness

The cache and refresher implementation is available, but plan closure is blocked until the common_fmt architecture failures are resolved and targeted verification is green.

---
*Phase: 23-host-split-status-line-for-claude-code-and-cursor-cli*
*Completed: 2026-10-24*
