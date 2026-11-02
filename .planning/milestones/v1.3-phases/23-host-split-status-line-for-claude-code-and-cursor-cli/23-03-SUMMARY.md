---
phase: 23-host-split-status-line-for-claude-code-and-cursor-cli
plan: 03
subsystem: testing
tags: [cursor, loopback, subprocess, fixtures, owner-spike]
requires: []
provides:
  - Loopback fake Connect-JSON Dashboard and Cursor runner simulator
  - Synthetic Dashboard and payload fixtures plus redacted POC payload
  - Owner-only spike runbook, capture utility, and checker
 affects: [cursor-quota, status-line, phase-23]
actuals:
  tokens: 6500
  tasks: 3
  commits: 3
tech-stack:
  added: []
  patterns: [loopback HTTP fakes, direct-child runner simulation, evidence-gated owner check]
key-files:
  created:
    - tests/cursor_fakes.py
    - tests/test_cursor_fakes.py
    - tests/fixtures/cursor/
    - .planning/phases/23-host-split-status-line-for-claude-code-and-cursor-cli/23-SPIKE.md
    - .planning/phases/23-host-split-status-line-for-claude-code-and-cursor-cli/live/spike_capture.py
    - .planning/phases/23-host-split-status-line-for-claude-code-and-cursor-cli/live/spike_check.py
  modified:
    - Makefile
    - .pre-commit-config.yaml
    - .planning/phases/23-host-split-status-line-for-claude-code-and-cursor-cli/23-SPEC.md
key-decisions:
  - "Owner-only Cursor evidence stays pending; no live request or CLI run was made."
  - "POC payload was found and redacted; only that named POC file was opened."
requirements-completed: [STL-03, STL-04]
coverage:
  - id: D1
    description: Loopback fake Dashboard, runner simulator, and synthetic response fixtures
    requirement: STL-03
    verification:
      - kind: unit
        ref: tests.test_cursor_fakes
        status: pass
    human_judgment: false
  - id: D2
    description: Synthetic and redacted payload fixtures
    requirement: STL-03
    verification:
      - kind: unit
        ref: tests.test_cursor_fakes#TestPayloadRedaction
        status: pass
      - kind: other
        ref: python3 tests/gsd_curated_eval.py secret-scan tests/fixtures/cursor
        status: pass
    human_judgment: false
  - id: D3
    description: Owner runbook and evidence checker with computed decision rule
    requirement: STL-04
    verification:
      - kind: other
        ref: spike_capture.py --self-test and spike_check.py --self-test
        status: pass
      - kind: other
        ref: spike_check.py --record 23-SPIKE.md (expected exit 1 while owner rows are pending)
        status: pass
    human_judgment: false
duration: 30min
completed: 2026-10-24
status: complete
orchestrator_verify: "VERIFY 23-03: 3/3 passed (orchestrator re-run; step 1's expected-no-match grep aborts under set -e before its test $? -eq 1: run as a condition, 0 matches, server binds 127.0.0.1 only; steps 2-3 PASS)"
---

# Phase 23 Plan 03: Cursor Fake Infrastructure and Owner Spike Summary

**Loopback Dashboard fakes, Cursor runner simulation, synthetic fixtures, and an owner-only spike kit**

## Performance

- **Duration:** approximately 30 min
- **Tasks:** 3
- **Commits:** 3
- **Files modified or created:** 19

## Accomplishments

- Added a loopback-only scripted Connect-JSON fake and runner simulator; tests show inherited stdout blocks completion and the detached DEVNULL pattern returns promptly.
- Added synthetic Dashboard fixtures and a synthetic payload. The POC payload existed; its redacted copy preserves numbers, booleans, and only the four allowed named strings. No other file under the POC worktree's `tmp/` was opened or listed.
- Added the owner runbook and self-tested capture/check tools. All live evidence rows remain `not run (owner)`.

## Task Commits

1. **Task 1: Loopback fake Dashboard and runner simulator** — `b3d490c`
2. **Task 2: Synthetic and redacted POC payload fixtures** — `f15f26b`
3. **Task 3: Owner spike kit and SPEC R5 pointer** — `08a9ce5` (summary included in this commit)

## Files Created/Modified

- `tests/cursor_fakes.py`, `tests/test_cursor_fakes.py` — local fake server, runner, fixtures loader, and behavioral tests.
- `tests/fixtures/cursor/` — synthetic Dashboard responses, synthetic payload, redacted POC payload, provenance note.
- `Makefile`, `.pre-commit-config.yaml` — regenerated test-group listings.
- `.planning/phases/23-host-split-status-line-for-claude-code-and-cursor-cli/23-SPIKE.md` — owner steps S1-S7, pending results, decision rule, and safety guidance.
- `.planning/phases/23-host-split-status-line-for-claude-code-and-cursor-cli/live/spike_capture.py`, `spike_check.py` — owner-only capture and evidence utilities.
- `.planning/phases/23-host-split-status-line-for-claude-code-and-cursor-cli/23-SPEC.md` — R5 record pointer amendment.

## Decisions Made

- Kept real responses, cadence, and latency observations owner-only; the implementation and fixtures remain explicitly synthetic/inferred pending the owner record.
- Redirect behavior is shown using stock urllib against a second loopback fake; no non-loopback network was used.

## Deviations from Plan

None - plan executed as specified.

## Issues Encountered

None. The first self-test iterations exposed implementation issues in the simulator and checker; these were fixed and the required checks were rerun successfully.

## User Setup Required

None for this plan. The later owner spike requires explicit approval because it reads Cursor credentials and consumes quota, as documented in `23-SPIKE.md`.

## Next Phase Readiness

The Part B test infrastructure and owner evidence path are ready. Real response fixtures remain absent until owner promotion.

---
*Phase: 23-host-split-status-line-for-claude-code-and-cursor-cli*
*Completed: 2026-10-24*
