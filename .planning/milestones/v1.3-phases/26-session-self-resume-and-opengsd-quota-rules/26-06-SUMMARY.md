---
phase: 26-session-self-resume-and-opengsd-quota-rules
plan: 06
subsystem: session-wake
tags: [systemd-timer, zoneinfo, reset-parser, redaction, rollback, quota]

# Dependency graph
requires:
  - phase: 26-session-self-resume-and-opengsd-quota-rules plan 05
    provides: arm/state/units seams, the fire order with not_before, refresh
      semantics, fakes and scratch-env test harness
provides:
  - reset_parse.py: RESET_RE grammar (spike 004), parse_reset_text, parse_reset_at,
    check_bounds (7-day, strictly future), calendar_line, redact (the runner's
    policy ported), cap_code_points, iso_z
  - arm flags --reset-text/--reset-at (mutually exclusive), ArmOptions.reset,
    reset_inferred wake fields and the second absolute OnCalendar= line
  - status/arm "inferred" reporting and the one-shot companion line
  - the arm rollback: a failed first arm undoes itself, a failed refresh restores
    the previous fields and unit bytes
  - tests/test_ai_kit_session_wake_reset.py (tracer, grammar, bounds, evidence)
  - TestArmRollback in tests/test_ai_kit_session_wake.py; fake systemctl
    FAKE_SYSTEMCTL_FAIL / FAKE_SYSTEMCTL_PARTIAL switches
affects: [26-07 (hook path feeds --reset-text), 26-08..26-12, executors]

# Actuals (#2632) — pairs with the plan's `estimate` to calibrate future estimates.
actuals:
  tokens: 47000
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "reset parse bound to (now, now + 7 d] with named-zone zoneinfo, fold=0"
    - "runner redaction policy ported verbatim to Python for stored evidence"
    - "rollback protocol: first arm deletes what it wrote, refresh restores saved bytes"

key-files:
  created:
    - skills/ai-kit-session-wake/ai_kit_session_wake/reset_parse.py
    - tests/test_ai_kit_session_wake_reset.py
  modified:
    - skills/ai-kit-session-wake/ai_kit_session_wake/arm.py
    - skills/ai-kit-session-wake/ai_kit_session_wake/cli.py
    - skills/ai-kit-session-wake/ai_kit_session_wake/units.py
    - tests/session_wake_fakes.py
    - tests/test_ai_kit_session_wake.py
    - Makefile
    - .pre-commit-config.yaml

key-decisions:
  - "A refused reset arms the hourly wake on a refresh too (the previous reset
     fields do not stand): SC 5 reads 'the hourly wake stands' as the arm result,
     not as a keep"
  - "render_timer accepts the full OnCalendar= line (calendar_line output); a bare
     time value is still prefixed for convenience"
  - "reset line reaches the unit only through calendar_line of the parsed UTC
     datetime; the raw host text never enters a unit file (T-26-19)"

patterns-established:
  - "ResetArg (kind, value) carried in ArmOptions.reset; parse at arm time with
     seams.now(), refuse with reason, hourly fallback printed, exit 0"
  - "_FinishPlan(refreshed, rollback) so _finish_arm stays within pylint's
     5-positional-argument limit; rollback closures capture saved unit bytes"

requirements-completed: [QTA-04]

coverage:
  - id: D1
    description: "A host-reported reset (text or epoch/ISO) moves the next wake to
      reset + 60 s, adds the second absolute OnCalendar line beside hourly, and arm
      and status mark it inferred with the companion one-shot time"
    requirement: QTA-04
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_session_wake_reset.py#TestResetTracer.test_limit_text_moves_the_wake_and_the_fire_honors_not_before"
        status: pass
      - kind: unit
        ref: "tests/test_ai_kit_session_wake_reset.py#TestResetTracer.test_refused_reset_arms_hourly"
        status: pass
    human_judgment: false
  - id: D2
    description: "The reset grammar, rollover, 7-day bounds, zone failures,
      --reset-at forms and the evidence redaction are pinned"
    requirement: QTA-04
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_session_wake_reset.py#TestResetGrammar"
        status: pass
      - kind: unit
        ref: "tests/test_ai_kit_session_wake_reset.py#TestResetBounds"
        status: pass
      - kind: unit
        ref: "tests/test_ai_kit_session_wake_reset.py#TestResetEvidence"
        status: pass
    human_judgment: false
  - id: D3
    description: "A failed first arm leaves nothing behind; a failed refresh restores
      the previous wake's fields and unit bytes and removes nothing"
    requirement: QTA-04
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_session_wake.py#TestArmRollback.test_failed_first_arm_leaves_nothing"
        status: pass
      - kind: unit
        ref: "tests/test_ai_kit_session_wake.py#TestArmRollback.test_partial_enable_is_undone"
        status: pass
      - kind: unit
        ref: "tests/test_ai_kit_session_wake.py#TestArmRollback.test_failed_refresh_restores_the_previous_wake"
        status: pass
      - kind: unit
        ref: "tests/test_ai_kit_session_wake.py#TestArmRollback.test_failing_rollback_step_is_named_and_nothing_is_removed"
        status: pass
    human_judgment: false

# Metrics
duration: 28min
completed: 2026-10-30
status: complete
orchestrator_verify: "VERIFY 26-06: 3/3 passed"
---

# Phase 26 Plan 06: Reset-driven wake and arm rollback Summary

**A host-reported reset (limit text or epoch/ISO) arms the persistent timer's second
`OnCalendar=` at reset + 60 s flagged inferred everywhere, with the runner's redaction
policy guarding the stored evidence, and `arm` now rolls back a failed first arm and
restores a failed refresh.**

## Performance

- **Duration:** 28 min
- **Started:** 2026-10-29T23:50:00-03:00
- **Completed:** 2026-10-30T00:18:00-03:00
- **Tasks:** 3
- **Files modified:** 9

## Accomplishments
- `reset_parse.py` parses every spike-004 reset form (`resets 12:30am`, `4:50pm`,
  `1pm`, `3am`, dated `Oct 22, 10pm`) in its named IANA zone through `zoneinfo`
  (fold=0, no tzdata), bounds it to (now, now + 7 d], and renders
  `OnCalendar=YYYY-MM-DD HH:MM:SS UTC`; `--reset-at` takes epoch or offset-bearing
  ISO, refusing naive times.
- `arm --reset-text/--reset-at` (mutually exclusive) set `not_before = reset + 60 s`,
  `wake_source reset_inferred`, `reset_at` (ISO UTC) and `reset_evidence` (the
  runner's redaction ported to Python — quote-aware key/value rules for plain and
  escaped JSON, shape rules, copy replacement, 32+ hex runs — capped at 2000 code
  points); the changed timer text triggers daemon-reload + restart; refusals print
  their reason and the hourly wake stands (exit 0); `status` prints the inferred line.
- The arm rollback (moved from 26-03): a failed first arm runs `disable --now`,
  deletes everything it wrote (state, lock, units, wants link, stamp) and
  `daemon-reload`s; a failed refresh restores the previous fields through
  `update_state` (keeping a concurrent count), writes the saved unit bytes back,
  `daemon-reload`s and restarts the changed timer, deleting nothing; both exit 2
  naming the failing verb and any rollback step that also failed.
- New pins: `TestResetTracer` (2 tests), `TestResetGrammar`/`TestResetBounds`/
  `TestResetEvidence` (15 tests), `TestArmRollback` (4 tests); fake systemctl gained
  `FAKE_SYSTEMCTL_FAIL`/`FAKE_SYSTEMCTL_PARTIAL`.

## Task Commits

Each task was committed atomically:

1. **Task 1: reset + 60 s timer line, inferred status, fire honors not_before** -
   `ab25eb4` (feat)
2. **Task 2: pin the reset grammar, bounds, zones and evidence** - `ed5bd6b` (test)
3. **Task 3: arm rolls back a failed first arm and restores a failed refresh** -
   this commit (feat)

## Files Created/Modified
- `skills/ai-kit-session-wake/ai_kit_session_wake/reset_parse.py` - the reset
  grammar, bounds, calendar line and the redaction port (stdlib only)
- `skills/ai-kit-session-wake/ai_kit_session_wake/arm.py` - reset flags into
  ArmOptions, reset fields, reset timer line, inferred/companion output, rollback
- `skills/ai-kit-session-wake/ai_kit_session_wake/cli.py` - `--reset-text`/
  `--reset-at`, the status inferred line
- `skills/ai-kit-session-wake/ai_kit_session_wake/units.py` - render_timer takes the
  full `OnCalendar=` reset line
- `tests/test_ai_kit_session_wake_reset.py` - tracer, grammar, bounds, evidence
- `tests/test_ai_kit_session_wake.py` - TestArmRollback
- `tests/session_wake_fakes.py` - FAIL/PARTIAL switches on the fake systemctl
- `Makefile`, `.pre-commit-config.yaml` - generated listings name the new module

## Decisions Made
- A refused reset on a refresh also arms the hourly wake (SC 5's "the hourly wake
  stands" is the arm result in both cases); without reset flags the refresh still
  keeps the previous reset fields (26-03).
- The dated form's refusal reason is uniformly `reset date is not within the next
  7 days`; an impossible calendar date (Feb 30) gets its own `reset date does not
  exist` reason.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Task ordering] The grammar/bounds/evidence classes landed with Task 1**
- **Found during:** Task 1/2
- **Issue:** the plan lists `tests/test_ai_kit_session_wake_reset.py` as a Task 1
  file, so the tracer commit already carried the Task 2 classes (they drove the
  parser green during Task 1); Task 2's red-first step had nothing left to add for
  those classes
- **Fix:** Task 2 added the remaining boundary pins instead (date-less
  strictly-after-now rollover, `--reset-at` 7-day edges, hex-run redaction) in the
  `test(26-06)` commit; every `<behavior>` case of Task 2 is pinned and green
- **Files modified:** tests/test_ai_kit_session_wake_reset.py
- **Verification:** Task 2's verify command (class log OK, `make test-unit` green)
- **Committed in:** ed5bd6b (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (task ordering, Rule 1 category)
**Impact on plan:** none — all Task 2 behaviors are pinned; only the commit
grouping differs from the plan's ideal red-first split.

## Issues Encountered
- The orchestrator committed an unrelated `docs: todo` capture (1a0b07b) on this
  branch while Task 1 was in flight; it was left untouched and is not part of this
  plan's commits. My first Task-1 commit attempt failed on the pylint hook because
  a lint fix was made after `git add`; re-staging fixed it (no `--no-verify`).

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- 26-07 can feed the `StopFailure` hook row's `last_assistant_message` /
  `error_details` text straight into `arm --reset-text`; the parser and its
  evidence redaction accept those payload shapes (pinned).
- 26-03's refresh/restart semantics are unchanged and the rollback spec they point
  to now exists (26-CONTEXT D-06/D-13/D-28).

---
*Phase: 26-session-self-resume-and-opengsd-quota-rules*
*Completed: 2026-10-30*
