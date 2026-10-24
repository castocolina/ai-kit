---
phase: 23-host-split-status-line-for-claude-code-and-cursor-cli
plan: 11
subsystem: cursor-quota
tags: [cursor, quota, transport, credentials, stdlib]
requires:
  - phase: 23-10
    provides: Pure quota normalization and state model
provides:
  - Validated endpoint, read-only accessToken reader, redirect-refusing concurrent Dashboard transport
  - Transport/credential tests and production-backed owner probe self-test
affects: [23-12, 23-13]
actuals:
  tokens: 11200
  tasks: 2
  commits: 2
tech-stack:
  added: []
  patterns: [lazy networking imports, no-redirect opener, body-inclusive fetch deadline]
key-files:
  created: [.planning/phases/23-host-split-status-line-for-claude-code-and-cursor-cli/live/spike_probe.py]
  modified: [tools/cursor_quota.py, tests/test_cursor_quota.py]
key-decisions:
  - "Only accessToken is read; missing and unsupported credentials remain distinct hidden states."
  - "The fetch deadline bounds body reads and executor waiting; socket timeouts are individually bounded."
requirements-completed: [STL-03]
coverage:
  - id: D1
    description: "Validated endpoint, token boundary and concurrent Dashboard calls normalize successfully."
    requirement: STL-03
    verification:
      - kind: unit
        ref: tests/test_cursor_quota.py#test_auth_to_concurrent_transport_and_normalization
        status: pass
      - kind: other
        ref: "python3 -S lazy networking import check"
        status: pass
    human_judgment: false
  - id: D2
    description: "Endpoint, credential, redirect and transport failure boundaries are covered."
    requirement: STL-03
    verification:
      - kind: unit
        ref: tests/test_cursor_quota.py
        status: pass
      - kind: other
        ref: "tests/gsd_curated_eval.py secret-scan tools/cursor_quota.py tests/test_cursor_quota.py"
        status: pass
    human_judgment: false
duration: 55min
completed: 2026-10-24
status: complete
orchestrator_verify: "VERIFY 23-11: 2/2 passed"
---

# Phase 23 Plan 11: Cursor Dashboard Transport and Credential Boundary Summary

**Cursor quota transport validates endpoint policy before token access, refuses redirects, and fetches concurrently without loading networking on render imports.**

## Performance

- **Duration:** 55 min
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Added strict `cursor.sh` HTTPS endpoint validation and read-only auth path/token handling with explicit missing, unsupported and transient-error outcomes.
- Added default-TLS no-redirect opener, three concurrent Connect-JSON POSTs, required-call error handling and total deadline enforcement.
- Covered synthetic end-to-end success, endpoint boundaries, pre-token rejection, auth path and parse cases, redirect isolation, HTTP failures, optional-call degradation, malformed JSON and total deadline.
- Implemented owner-probe self-test with canned responses and token-free timing evidence.

## Task Commits

1. **Task 1: Dashboard transport and read-only token reader** - `c49a019` (`feat`)
2. **Task 2: Transport and credential boundary tables** - `c6a213f` (`test`)

## Files Created/Modified

- `tools/cursor_quota.py` - Endpoint validation, auth reader, redirect-refusing concurrent transport and hidden `auth_missing` state.
- `tests/test_cursor_quota.py` - Synthetic transport, credentials and security boundary tests.
- `.planning/phases/23-host-split-status-line-for-claude-code-and-cursor-cli/live/spike_probe.py` - Production transport self-test and token-free probe evidence.

## Decisions Made

- Imports for URL parsing, credential JSON and HTTP transport remain function-local/lazy.
- The fetch timeout is a wall-clock deadline including response-body reads and executor completion; per-socket timeouts remain separately bounded.

## Deviations from Plan

None - plan executed as specified.

## Issues Encountered

- The first deadline-test run exposed urllib response sockets already closed after buffering; the transport now checks socket state before changing the timeout. An optional hard-limit test initially inherited an individual limit, so it was corrected to use the team fixture that requires hard-limit evidence.

## User Setup Required

None - the owner-only live spike remains `not run (owner)`.

## Verification

- `uv run python tools/run_unittest_parallel.py tests.test_cursor_quota` — 1/1 module, 15 tests passed.
- `python3 -S` import check — `urllib.request` and `http.client` absent (`lazy ok`).
- Owner probe `--self-test` — passed; canned transport produced token-free timing evidence.
- Secret scan — passed.
- Scoped ruff, pylint and pyright — passed.
- Leak check — no matching fake grandchildren; no `gc.pid` in repository root.

## Next Phase Readiness

The transport and credential seam is ready for 23-12 cache and detached refresher work. Owner-only live Cursor evidence remains pending.

---
*Phase: 23-host-split-status-line-for-claude-code-and-cursor-cli*
*Completed: 2026-10-24*
