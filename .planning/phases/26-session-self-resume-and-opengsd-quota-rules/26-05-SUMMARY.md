---
phase: 26-session-self-resume-and-opengsd-quota-rules
plan: 05
subsystem: session-wake
tags: [systemd, session-resume, concurrency, flock, notify-send, python]
requires:
  - phase: 26-02
    provides: The D-10 fire order, state/lock primitives and the one finish step
  - phase: 26-03
    provides: status/arm refresh and the generated test-group listings
  - phase: 26-04
    provides: session_exists probes and per-host resume rows
provides:
  - TestOverlap: two concurrent real fire processes on one gone session run exactly one resume and both wakes count
  - TestFireInterleaving: eight deterministic in-process interleavings (disarm, re-arm, done, refresh, count-entry) that must never yield a resume
  - TestFireSequence: every D-10 liveness edge, the done-first ordering, the not_before boundary and the missing-state empty edge
  - TestGiveUp: the 24-wake cap finalization through unknown/spawn-127/live-host/resume routes, one notice each, the bounded desktop notify, the held-lock hand-off and the resume timeout
  - TestDisarm: the lock wait, the in-fire-child fallback, idle done, foreign created paths, foreign same-named folders and one-field-invalid states removed by name
  - fire.notify with NOTIFY_TIMEOUT_S, disarm's blocking lock and done's idle disarm
affects: [phase-26, phase-27, session-wake]
actuals:
  tokens: 14000
  tasks: 3
  commits: 3
tech-stack:
  added: []
  patterns: [readiness-barrier polling instead of timing guesses, patched-function interleaving points, hold-lock helper printing a locked line]
key-files:
  created: [tests/test_ai_kit_session_wake_fire.py]
  modified: [skills/ai-kit-session-wake/ai_kit_session_wake/fire.py, skills/ai-kit-session-wake/ai_kit_session_wake/state.py, tests/session_wake_fakes.py, tests/test_ai_kit_session_wake.py, Makefile, .pre-commit-config.yaml]
key-decisions:
  - "Overlap tests use a readiness barrier (poll the fake log for the resume call) and hold_lock's `locked` line, never millisecond timing (review round 1)."
  - "Every 24th-wake route (unknown probe, spawn error 127, live host, normal resume, wake 25) goes through the one finish step and gives up exactly once with its notice (review round 1)."
  - "The interleaving tests patch the exact function fire calls (is_alive, session_exists, the count's update_state) with wrappers that run the real function and then the interleaved action (review rounds 1-3)."
  - "Disarm removes only paths equal to one of the wake's seven seams-derived absolute paths; a same-named file in any other folder is foreign and survives (review round 2)."
  - "fire logs `invalid state (<reason>)` naming the failing field, and validate_state's identity reason names host/session_id explicitly."
requirements-completed: [QTA-04]
coverage:
  - id: D1
    description: Two concurrent real fire processes on one gone session run exactly one resume; both wakes are counted in the state file; the second fire reports a resume already running.
    requirement: QTA-04
    verification:
      - kind: unit
        ref: tests.test_ai_kit_session_wake_fire.TestOverlap.test_two_concurrent_fires_one_resume_two_wakes
        status: pass
      - kind: unit
        ref: tests.test_ai_kit_session_wake_fire.TestOverlap.test_update_state_serializes_fifty_plus_fifty_increments
        status: pass
    human_judgment: false
  - id: D2
    description: No done, disarm, re-arm or refresh landing between a fire's checks and its spawn can make it resume (eight deterministic cases).
    requirement: QTA-04
    verification:
      - kind: unit
        ref: tests.test_ai_kit_session_wake_fire.TestFireInterleaving
        status: pass
    human_judgment: false
  - id: D3
    description: The D-10 order's liveness edges, done-first, the not_before boundary and the missing-state empty edge behave exactly as specified.
    requirement: QTA-04
    verification:
      - kind: unit
        ref: tests.test_ai_kit_session_wake_fire.TestFireSequence
        status: pass
    human_judgment: false
  - id: D4
    description: The cap gives up loudly exactly once on every 24th-wake route, with a bounded desktop notice that never fails the fire, and a hung resume cannot block later wakes (group kill, exit 124).
    requirement: QTA-04
    verification:
      - kind: unit
        ref: tests.test_ai_kit_session_wake_fire.TestGiveUp
        status: pass
    human_judgment: false
  - id: D5
    description: Every disarm path removes exactly the wake's own paths, waits for a running resume, falls back to the marker inside a fire child, and done cleans up when idle.
    requirement: QTA-04
    verification:
      - kind: unit
        ref: tests.test_ai_kit_session_wake_fire.TestDisarm
        status: pass
    human_judgment: false
duration: 40min
completed: 2026-10-29
status: complete
orchestrator_verify: "VERIFY 26-05: 3/3 passed"
orchestrator_verify: "VERIFY 26-05: 3/3 passed"
---

# Phase 26 Plan 05 Summary

**fire pinned under real concurrency: one resume per session, every interleaving inert, the loud 24-wake cap with its bounded desktop notice, the resume timeout, and disarm/done under every trigger**

## Accomplishments
- `TestOverlap`: two shim `fire` subprocesses on one killed session, the second started only after a readiness barrier (the resume call in the fake log), yield exactly one fake-claude call, `wake_count` 2, the second's stdout saying a resume is already running, both exit 0; a companion test drives two processes incrementing one scratch state 50 times each to exactly 100.
- `TestFireInterleaving` (eight cases, deterministic, in-process): a `disarm`, a `disarm` plus first re-arm from live host B, a direct `.done`, a live re-arm, a re-arm whose B then exits, a same-arm refresh moving `not_before` to now + 3600 s, a same-arm reset refresh at the count entry with count 23, and a disarm-plus-first-arm at the count entry — none makes a fake host call or prints a give-up line; B's or the refresh's files and counts stay intact. No `fire`/`lock_session`/`update_state` defect was exposed: 26-02's inode re-checks already hold.
- `TestFireSequence`: a live host logs `host alive; log only` and counts one; a reaped pid, a reused pid with another start time and a reused pid with another boot id each resume exactly once; a `.done` marker with a live host disarms before any count (an `update_state` spy stays empty) or resume; a missing state with both unit files runs `disable --now`, `clean --what=state`, `daemon-reload` for the derived timer; a fire one second before `not_before` is not counted, a fire exactly at `not_before` counts.
- `TestGiveUp`: from count 23 the 24th wake resumes then disarms naming the state path and `last resume exit`; from 24 the next fire gives up without resuming; the give-up runs the fake `notify-send` once with a session bus, not at all without it, survives a failing notifier, and is bounded (`NOTIFY_TIMEOUT_S` 0.5 + a 5 s fake still exits 0 in under 3 s); the cap finalization is pinned through the `unknown` probe, a removed `cli_path` (notice names `last resume exit 127`), a live host and a normal resume, each with exactly one notice; a held lock leaves the wake counted at 24 with no notice and the next fire gives up once; `RESUME_TIMEOUT_S` 1 against a 30 s fake host kills the child and its group, records 124 and frees the lock; `FAKE_HOST_EXIT=3` records 3.
- `TestDisarm`: nothing armed prints `nothing to disarm`; a 2 s lock hold makes a `disarm` subprocess finish only after the release and then remove everything; `disarm` inside a fire child writes `.done` and removes nothing; idle `done` disarms at once, and with the lock held it writes the marker only; the three triggers each leave no `ai-kit-session-wake-*` file in the unit dir, its wants dir or the state dir; foreign `created` entries (`keep.txt`, another session's state file) and same-named files under foreign `user/`, `session-wake/`, `timers/`, `timers.target.wants/` folders are printed `skipped foreign path` and survive; eight one-field-invalid states are removed by name with `invalid state (<failing field>)` logged and the foreign file surviving.
- `fire.notify(seams, summary, body)` with `NOTIFY_TIMEOUT_S = 5`: `notify-send` only when on the seams PATH and a session bus is reachable, every error ignored; `disarm` takes the session lock blocking (with the in-fire-child marker fallback), `done` disarms when the lock is free and defers to a running resume otherwise.

## Task Commits
1. Task 1 — `e053d58` (`test(26-05): two concurrent wakes run one resume and count both`)
2. Task 2 — `50a0b95` (`feat(26-05): pin the fire order, the cap give-up notice and the resume timeout`)
3. Task 3 — this commit (`feat(26-05): disarm waits for a running resume and done cleans up when idle`)

## Files Created/Modified
- `tests/test_ai_kit_session_wake_fire.py` — created: TestOverlap, TestFireInterleaving, TestFireSequence, TestGiveUp, TestDisarm over the shared scratch/fakes base.
- `skills/ai-kit-session-wake/ai_kit_session_wake/fire.py` — `notify` + `NOTIFY_TIMEOUT_S` + `NOTIFY_SUMMARY`, `give_up` calls the bounded desktop notice after its journal line; `disarm` gains the blocking lock and the in-fire-child `.done` fallback (`_disarm_locked` extracted); `done` gains the idle disarm and the running-resume deferral; fire's invalid-state log now names the failing field.
- `skills/ai-kit-session-wake/ai_kit_session_wake/state.py` — `_identity_problem` names `host`/`session_id` explicitly in the mismatch reason.
- `tests/session_wake_fakes.py` — `FAKE_HOST_SLEEP=<seconds>` sleeps that span before exiting, `FAKE_HOST_EXIT=<code>`; `fake_notify_send` (`FAKE_NOTIFY_FAIL`, `FAKE_NOTIFY_SLEEP`); `hold_lock(path, seconds)` printing `locked`.
- `tests/test_ai_kit_session_wake.py` — re-pinned `TestPermissionMode._stand_in` to `FAKE_HOST_SLEEP: "600"` (the fake-host sleep is seconds now; the pin keeps the stand-in alive for the whole test, see Deviations).
- `Makefile`, `.pre-commit-config.yaml` — regenerated listings naming `tests.test_ai_kit_session_wake_fire` (`tools/gen_test_groups.py`).

## Decisions Made
- The overlap test's readiness barrier polls the fake log for the resume call instead of sleeping, because the resume call is logged strictly after the first fire takes the lock — the barrier is a proof, not a timing guess (review round 1).
- The interleaving wrappers capture the real function before patching and run the interleaved action through `cli.main`, so the patch scope is exactly fire's call site and the action exercises the real arm/disarm paths (review rounds 1-3).
- `done` with an invalid or missing state but a free lock removes by name (same rule as `disarm`), keeping one removal rule per sourcing class.

## Deviations from Plan

### Auto-fixed Issues

**1. TestPermissionMode's host stand-in re-pinned to the new FAKE_HOST_SLEEP semantics**
- **Found during:** Task 1
- **Issue:** `fake_host`'s `FAKE_HOST_SLEEP` changed from sleep-until-killed to sleep-`<seconds>`-then-exit (the plan's Task 1/2 fake switches require bounded spans); `TestPermissionMode._stand_in` (outside this plan's file list) used `"1"` as an alive stand-in and would have raced arm
- **Fix:** re-pinned the value to `"600"` in `tests/test_ai_kit_session_wake.py` — a pin update, not a loosening (run rule 11)
- **Files modified:** tests/test_ai_kit_session_wake.py
- **Verification:** `tests.test_ai_kit_session_wake` green (41 tests)

### Issues Encountered

- None. Every planned step ran as written; no verification was skipped.
