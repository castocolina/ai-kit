---
phase: 22-pi-live-validation
plan: 01
subsystem: testing
tags: [pi, gsd-core, localhost-mock, live-validation]
requires:
  - phase: 19-evaluation-on-claude
    provides: scratch-project smoke and pinned gsd-core conventions
provides:
  - L0-L2 pi model-steering evidence and staged L3 owner checks
  - localhost-only mock provider with a self-test
affects: [22-02, 22-03, 22-04, 22-06]
actuals:
  tokens: 1850
  tasks: 2
  commits: 2
tech-stack:
  added: []
  patterns: [stdlib localhost mock, evidence ladder]
key-files:
  created:
    - .planning/phases/22-pi-live-validation/live/pi_mock_provider.py
    - .planning/phases/22-pi-live-validation/22-SPIKE-PI-AGENTS.md
    - .planning/phases/22-pi-live-validation/22-01-SUMMARY.md
  modified: []
key-decisions:
  - "L2 A-C produced the session-steer verdict; D remains observation-only."
  - "L3 real-provider checks remain owner-only."
requirements-completed: [EVAL-08]
coverage:
  - id: D1
    description: L0-L2 pi steering spike evidence and mechanical verdict
    requirement: EVAL-08
    verification:
      - kind: e2e
        ref: "scratch pi against localhost mock (arms A-D)"
        status: pass
      - kind: other
        ref: "22-SPIKE-PI-AGENTS.md verdict consistency check"
        status: pass
    human_judgment: false
  - id: D2
    description: Localhost mock provider self-test
    verification:
      - kind: unit
        ref: "python3 .planning/phases/22-pi-live-validation/live/pi_mock_provider.py --self-test"
        status: pass
    human_judgment: false
  - id: D3
    description: Real-provider L3 confirmation
    verification: []
    human_judgment: true
    rationale: "Requires owner approval and a real model call; staged as pending owner work."
duration: 30min
completed: 2026-10-23
status: complete
---

# Phase 22 Plan 01: Pi Agent Model Spike Summary

**A scratch pi 1.3.0 run shows `pi.sonnet` changes the localhost wire model while opus-only and no-override runs preserve the selected model.**

## Performance

- **Duration:** 30 min
- **Started:** 2026-10-23
- **Completed:** 2026-10-23
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Implemented and self-tested a stdlib mock provider bound exclusively to `127.0.0.1`; it logs request path and model only.
- Recorded installed-version L0 source citations, six L1 fake-API cases, four serialized L2 arms and three owner-only L3 rows.
- Mechanically verified `verdict: session-steer (static + mock evidence)` from arms A-C; D cannot affect the verdict.
- `skills-root pi` and the `resolve-model` oracle gap are documented as findings with no in-phase fix needed.

## Task Commits

1. **Task 1: localhost mock and pi.sonnet arm** — `4a0197b` (`docs(22-01)`)
2. **Task 2: L0-L2 evidence and verdict plus summary** — recorded in this commit.

## Files Created/Modified

- `.planning/phases/22-pi-live-validation/live/pi_mock_provider.py` — localhost mock, SSE/non-stream responses, and self-test.
- `.planning/phases/22-pi-live-validation/22-SPIKE-PI-AGENTS.md` — static, fake API, mock-wire, owner, findings and verdict evidence.
- `.planning/phases/22-pi-live-validation/22-01-SUMMARY.md` — plan outcome and verification record.

## Decisions Made

- The A-C wire results determine the verdict. Arm D records trust behavior only and cannot block.
- L3 remains owner-only; no real provider or credentials were used.

## Deviations from Plan

The mock's initial SIGTERM handler could not shut down the serving loop from its own thread. It was changed to call `shutdown()` on a helper thread; the mock self-test and subsequent arm cleanup verified clean termination.

**Total deviations:** 1 auto-fixed (correctness). **Impact:** required to ensure each serialized mock process stops cleanly.

## Issues Encountered

The first arm's shell invocation reached the mock, recorded exit 0 and completed pi's response, but the outer command timed out waiting for the initial mock shutdown implementation. The handler was corrected before the remaining arms; no pi process or mock was left running. All arm logs were non-empty. No other issues.

## Leak and scratch cleanup

- L2 arms ran one at a time; each mock was killed and waited for before the next arm.
- The post-snapshot leak check for `pi_mock_provider.py` / `pi --mode json` printed nothing. The required `gc-late` / `node -e while` check also printed nothing.
- Scratch removal guard passed: the resolved path was a non-symlink directory under the system temp directory, owned by the current user; it was removed.

## User Setup Required

None. L3 rows are owner work staged in `22-INTERACTIVE-PI.md` when that plan lands.

## Next Phase Readiness

The verdict supports the session-wide `pi.sonnet` opt-in work; owner-only L3 and interactive validation remain pending.

---
*Phase: 22-pi-live-validation*
*Completed: 2026-10-23*
