---
phase: 25-quota-aware-cross-ai-subprocess-supervision
plan: 04
subsystem: infra
tags: [cross-ai, quota, subprocess, live-detection, node]

requires:
  - phase: 25-quota-aware-cross-ai-subprocess-supervision
    provides: "the pattern table with terminal flags, classifyStop and the shared bounded line splitter (25-02); the route flag and confirmed router lane (25-03)"
provides:
  - "Live line watcher over the shared splitter: a terminal stderr line or terminal structured event records liveHit at once and stops the child through currentFinalize('limit') after LIMIT_GRACE_MS (1500)"
  - "Post-hoc classification of a timed-out attempt over every row, terminal and non-terminal alike, with main preferring the classified status over a bare timeout"
  - "Self-test cases pinning the live kill, the partial-line flood, the post-hoc 429 and codex error, and the answer, retry-notice and bare-codex-error negatives"
affects: [25-05, 25-06, 25-07]

actuals:
  tokens: 8800
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "One bounded splitter per stream: the relay and the watcher share one buffer, one 64 KiB cap and one flush, matching the partial buffer before a trim"
    - "A live hit stores the row; the confirmed router lane is applied when the attempt is returned, so a router billing line still reports quota"

key-files:
  created: []
  modified:
    - skills/ai-kit-spec-review/references/cross-ai.mjs

key-decisions:
  - "Live-kill eligibility stays terminal rows only; the post-hoc pass classifies captured output with every row, so a non-terminal 429 re-labels a timeout as quota while a transient or capacity match keeps timeout"
  - "A bare codex error event is recorded and never a live kill; only turn.failed carrying limit text stops the child (ruling Q1)"
  - "A delayed-answer fake mode must be in the sticky set, or the fake exits before its timer writes the answer"

patterns-established:
  - "Pattern: record the terminal signal at first sight, including an unterminated line matched before the buffer trim, so a later flood cannot hide it"

requirements-completed: [QTA-02]

coverage:
  - id: D1
    description: "A child that prints a terminal limit line and keeps running is stopped at the 1500 ms grace and classified quota"
    requirement: QTA-02
    verification:
      - kind: e2e
        ref: "node skills/ai-kit-spec-review/references/cross-ai.mjs --self-test (cases live-limit-kill, live-partial-kill, live-limit-flood, live-codex-turn-failed)"
        status: pass
    human_judgment: false
  - id: D2
    description: "A timed-out attempt is classified from what it printed: a non-terminal quota row re-labels the timeout, a transient match keeps timeout"
    requirement: QTA-02
    verification:
      - kind: e2e
        ref: "node skills/ai-kit-spec-review/references/cross-ai.mjs --self-test (cases post-hoc-timeout-429, post-hoc-timeout-codex-error, post-hoc-timeout-transient-stays, hang)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Answer text, retry notices and a bare codex error never stop a child"
    requirement: QTA-02
    verification:
      - kind: e2e
        ref: "node skills/ai-kit-spec-review/references/cross-ai.mjs --self-test (cases answer-only-ok, retry-notice-no-kill, retry-notice-429-no-kill, live-codex-bare-error-no-kill)"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-10-24
status: complete
orchestrator_verify: "VERIFY 25-04: 2/2 passed"
---

# Phase 25 Plan 04: Live Limit Detection Summary

**The runner watches the child's stderr and structured events while it runs, stops a child that prints a terminal limit signal and keeps going, and classifies a timed-out attempt from what it printed.**

## Performance

- **Duration:** 25 min
- **Started:** 2026-10-24T21:43:00Z
- **Completed:** 2026-10-24T22:08:32Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- The shared bounded line splitter now feeds the live watcher: each complete stderr line is matched against terminal rows, each complete stdout line against terminal structured events, and the partial buffer is matched before a trim so an unterminated terminal line survives a newline-free flood.
- The first terminal hit is recorded at once and, after `LIMIT_GRACE_MS` (1500), stops the still-running child through `currentFinalize('limit')` (SIGTERM, grace, SIGKILL of its group).
- A timed-out attempt with no live hit is classified after the fact over the captured stderr tail, the partial buffers and the extracted events, using every row. A quota or rate-limit match re-labels the timeout; a transient, capacity or empty match keeps `timeout` exit 124, and `main` prefers the classified status.
- Cases pin both directions: `live-limit-kill`, `live-partial-kill`, `live-partial-flood`, `live-limit-flood` and `live-codex-turn-failed` end `quota` well inside the deadline with the child dead; `post-hoc-timeout-429` and `post-hoc-timeout-codex-error` reach the deadline and are still classified `quota`; `answer-only-ok`, `retry-notice-no-kill`, `retry-notice-429-no-kill` and `live-codex-bare-error-no-kill` end `ok`.

## Task Commits

1. **Task 1: Live line watcher, terminal-signal kill and after-the-fact classification** - `3b0eaab` (feat)
2. **Task 2: Negative and adversarial cases** - committed with this summary (test)

## Files Created/Modified

- `skills/ai-kit-spec-review/references/cross-ai.mjs` - live watcher, `finalize('limit')`, post-hoc timeout classification, pi and codex fake modes, and the new self-test cases.
- `.planning/phases/25-quota-aware-cross-ai-subprocess-supervision/25-04-SUMMARY.md` - this summary.

## Decisions Made

- A live hit stores the matched row and the confirmed router lane is applied when the attempt is returned. Recording the status at match time with the lane unknown turned router billing cases into `billing` instead of `quota`.
- The delayed-answer fake modes (`retry-notice`, `retry-notice-429`) are in the sticky set. Without it the fake exits the moment the mode function returns, before its timer writes the answer.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Router billing cases lost their lane through the live hit**
- **Found during:** Task 1 (full self-test after the targeted cases passed)
- **Issue:** The live match classified with `routerLane: false` and stored the status, so `402 payment required` on a router-backed pi was recorded as `billing` and the four router cases (`billing-router`, `billing-403-router`, `dirty-billing-router`, `route-config`) exited 69 instead of 75.
- **Fix:** The live record keeps the rule id; `hitForLane` applies the confirmed route when `runCli` returns the attempt.
- **Files modified:** `skills/ai-kit-spec-review/references/cross-ai.mjs`
- **Verification:** Full `--self-test` prints `self-test ok`.
- **Committed in:** `3b0eaab` (part of the Task 1 commit)

**2. [Rule 1 - Bug] A delayed-answer fake exited before writing its answer**
- **Found during:** Task 2 (retry-notice cases)
- **Issue:** The fake calls `process.exit(0)` right after the mode function unless the mode is in `STICKY_FAKE`, so the `setTimeout` that writes the answer never ran and the attempt ended on the notice line.
- **Fix:** Added `retry-notice` and `retry-notice-429` to the sticky set, matching the existing `slowok` mode.
- **Files modified:** `skills/ai-kit-spec-review/references/cross-ai.mjs`
- **Verification:** `retry-notice-no-kill` and `retry-notice-429-no-kill` end `ok` with one pi run call.
- **Committed in:** the Task 2 commit

---

**Total deviations:** 2 auto-fixed (2 bug)
**Impact on plan:** Both fixes were required for the cases to behave as specified. No scope change.

## Issues Encountered

None.

## Self-test Duration

The full `--self-test` (every case, standalone) completed in 78 s, inside the 120 s budget.

## Deleted tests

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

The typed status from a live kill and from a classified timeout is available to the ladder (25-05/25-06) like any other failed attempt. `hang` still ends `timeout` exit 124, so Python's `run_runner_tiers` keeps its next tier.

---
*Phase: 25-quota-aware-cross-ai-subprocess-supervision*
*Completed: 2026-10-24*
