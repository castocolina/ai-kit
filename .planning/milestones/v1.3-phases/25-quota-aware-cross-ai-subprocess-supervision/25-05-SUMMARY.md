---
phase: 25-quota-aware-cross-ai-subprocess-supervision
plan: 05
subsystem: infra
tags: [cross-ai, runner, transient-ladder, node]

requires:
  - phase: 25-04
    provides: live and after-the-fact classification, session-id capture per CLI
provides:
  - transient ladder in the runner template (3 same-session retries, then 3 new sessions)
  - dirty-tree gate that lets a new session continue only the prompt's own files
  - status transient mapped to the capacity reason
affects: [25-06, 25-07, 25-10]

actuals:
  tokens: 6000
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns: [pure ladderNext drives every retry decision, per-attempt child timer]

key-files:
  created: []
  modified:
    - skills/ai-kit-spec-review/references/cross-ai.mjs
    - skills/ai-kit-spec-review/ai_kit_spec/error_classifier.py
    - tests/test_ai_kit_spec.py
    - tests/test_ai_kit_spec_runner_dispatch.py
    - tests/test_ai_kit_spec_runtimes_table.py
    - tests/test_cross_ai_runner_e2e.py

key-decisions:
  - "A deadline shorter than the 60 s reserve still runs the current attempt; the reserve only gates the next rung"
  - "A transient failure that cannot start a rung reports transient, not timeout; timeout/124 stays only for a no-budget timeout stop"
  - "The post-run tree snapshot reads against the finalize window, so an attempt may use the whole call deadline"

patterns-established:
  - "ladderNext is pure and table-free; runCli logs every decision and asks it for the next step"
  - "rung 2 over a dirty tree requires changedPaths to be a subset of promptFiles"

requirements-completed: [QTA-03]

coverage:
  - id: D1
    description: "A transient failure retries up to 3 times in the same session, then up to 3 times in new sessions, and reports transient"
    requirement: QTA-03
    verification:
      - kind: e2e
        ref: "node cross-ai.mjs --self-test#ladder-transient-exhausted"
        status: pass
    human_judgment: false
  - id: D2
    description: "A new session continues only when every changed path is listed in the prompt"
    requirement: QTA-03
    verification:
      - kind: e2e
        ref: "node cross-ai.mjs --self-test#ladder-dirty-inside,ladder-dirty-outside,ladder-non-git"
        status: pass
    human_judgment: false

duration: 120min
completed: 2026-10-24
status: complete
orchestrator_verify: "VERIFY 25-05: 3/3 passed"
---

# Phase 25 Plan 05: Transient Ladder Summary

**The runner retries a transient failure 3 times in the same session and 3 times in new sessions on the same CLI and model, then reports `transient`, which Python maps to `capacity`.**

## Performance

- **Duration:** about 120 min
- **Started:** 2026-10-24T20:40Z
- **Completed:** 2026-10-24T22:39Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments

- A transient failure, including a quota-free timeout, walks rung 1 then rung 2 and the exhausted ladder reports `status=transient` exit 75.
- A new session continues over a dirty tree only when `git diff-tree` shows changes limited to the prompt's `<files>` paths.
- `STATUS_TO_REASON["transient"]` is `capacity`, and the CONFIG contract test pins the new keys.

## Task Commits

1. **Task 1: rung 1 and rung 2 through runCli** - `c058517` (feat)
2. **Task 2: the dirty-tree rule** - `88fdc21` (feat)
3. **Task 3: rung availability per CLI and pure ladder checks** - this commit (test)

## Files Created/Modified

- `skills/ai-kit-spec-review/references/cross-ai.mjs` - `ladderNext`, the rung loop, `promptFiles`, `changedPaths`, status `transient`
- `skills/ai-kit-spec-review/ai_kit_spec/error_classifier.py` - `transient` maps to `capacity`
- `tests/test_ai_kit_spec.py` - CONFIG contract updated
- `tests/test_ai_kit_spec_runner_dispatch.py` - `transient` in the billing/capacity map test
- `tests/test_ai_kit_spec_runtimes_table.py` - `reason_for_status` row for `transient`
- `tests/test_cross_ai_runner_e2e.py` - `fake/capacity` expects `transient`, self-test caps raised to 300 s

## Self-test timing

The full `--self-test` passed in 105 s (budget 120 s). The `hangonce` mode adds about 12 s of real waiting for `ladder-timeout-then-ok`; every other new case uses injected times and no real sleep.

## Decisions Made

- A deadline shorter than the 60 s reserve still runs the current attempt. The earlier reading gave `backoff-deadline` a zero-second child, so the fake never ran and the failure was classified as a timeout.
- A transient failure that stops before any rung reports `transient`. `timeout`/124 stays only for a timeout that had no budget for a rung, which is what `ladder-timeout-no-budget` pins.
- The post-run tree snapshot reads against the finalize window. Reading it against the call deadline made `outer-race` report `git_timeout`, because the attempt now legitimately runs until the deadline.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Existing cases assumed the child always got the whole deadline**
- **Found during:** Task 1
- **Issue:** `backoff-deadline` and `post-hoc-timeout-transient-stays` got a zero-second child and reported `timeout`; `outer-race` lost its tree snapshot.
- **Fix:** a deadline below the reserve still runs the attempt, and the snapshot reads against the finalize window. `outer-race` clears the fake git hang flag once the attempt ends.
- **Files modified:** `skills/ai-kit-spec-review/references/cross-ai.mjs`
- **Verification:** full `--self-test` passes
- **Committed in:** `c058517`

**2. [Rule 1 - Bug] The codex fake cut its own stdout**
- **Found during:** Task 3
- **Issue:** `process.exitCode = 1` still ended the process before the runner read `thread.started`, and the review fake edited `a.txt`.
- **Fix:** the event400 mode delays its exit by 50 ms and edits nothing.
- **Files modified:** `skills/ai-kit-spec-review/references/cross-ai.mjs`
- **Verification:** `ladder-codex-exec-resume` and `ladder-codex-review-fresh` pass
- **Committed in:** this commit

---

**Total deviations:** 2 auto-fixed (2 bug)
**Impact on plan:** both keep existing cases true under the new timer. No scope change.

## Issues Encountered

None.

## Deleted tests

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- 25-06 adds the quota branch to `ladderNext` and bumps the header to template 7.
- The two e2e self-test caps are 300 s. `make e2e-test` was not run in this plan; the orchestrator barrier runs `make test`.

---
*Phase: 25-quota-aware-cross-ai-subprocess-supervision*
*Completed: 2026-10-24*
