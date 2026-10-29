---
phase: 26-session-self-resume-and-opengsd-quota-rules
plan: 03
subsystem: session-wake
tags: [systemd, session-resume, survival-matrix, python]
requires:
  - phase: 26-02
    provides: Session wake state, arm/fire/disarm primitives and fake seams
provides:
  - Idempotent session wake refresh preserving wake counters and metadata
  - Session-id validation, filtered service PATH and linger fallback support
  - Evidence-labelled survival matrix, matrix JSON output and status command
affects: [phase-26, phase-27, session-wake]
actuals:
  tokens: 4100
  tasks: 3
  commits: 6
tech-stack:
  added: []
  patterns: [serialized state refresh, evidence-labelled matrix rows]
key-files:
  created: [skills/ai-kit-session-wake/ai_kit_session_wake/matrix.py]
  modified: [skills/ai-kit-session-wake/ai_kit_session_wake/arm.py, skills/ai-kit-session-wake/ai_kit_session_wake/cli.py, skills/ai-kit-session-wake/ai_kit_session_wake/state.py, skills/ai-kit-session-wake/ai_kit_session_wake/units.py, tests/session_wake_fakes.py, tests/test_ai_kit_session_wake.py]
key-decisions:
  - "Refresh updates the existing state through the serialized updater and retains the arm identity and wake count."
  - "When systemd is unavailable, arm returns the no-surviving-primitive exit code and surfaces the in-session option."
requirements-completed: [QTA-04]
coverage:
  - id: D1
    description: Re-arm refreshes session process details and retains wake state.
    requirement: QTA-04
    verification:
      - kind: unit
        ref: tests.test_ai_kit_session_wake.TestRearm
        status: pass
      - kind: unit
        ref: tests.test_ai_kit_session_wake.TestRearm.test_changed_timer_text_restarts_after_reload
        status: pass
    human_judgment: false
  - id: D2
    description: Exact session ids, two-session isolation, secret exclusion, atomic writes/modes, filtered PATH, interpreter validation and linger fallback.
    requirement: QTA-04
    verification:
      - kind: unit
        ref: tests.test_ai_kit_session_wake.TestArmIdentity
        status: pass
      - kind: unit
        ref: tests.test_ai_kit_session_wake.TestArmSafety
        status: pass
      - kind: unit
        ref: tests.test_ai_kit_session_wake.TestArmIdentity.test_two_sessions_disarm_and_fire_only_the_selected_id
        status: pass
      - kind: unit
        ref: tests.test_ai_kit_session_wake.TestArmSafety.test_secret_sentinels_never_reach_any_written_file_or_systemctl_log
        status: pass
      - kind: unit
        ref: tests.test_ai_kit_session_wake.TestArmSafety.test_atomic_refresh_failure_preserves_bytes_and_modes
        status: pass
      - kind: unit
        ref: tests.test_ai_kit_session_wake.TestArmSafety.test_shebang_interpreter_is_checked_against_filtered_path
        status: pass
      - kind: unit
        ref: tests.test_ai_kit_session_wake.TestArmSafety.test_missing_absolute_shebang_interpreter_refused
        status: pass
    human_judgment: false
  - id: D3
    description: Survival matrix JSON, primitive selection, restart-on-change and complete status reporting.
    requirement: QTA-04
    verification:
      - kind: unit
        ref: tests.test_ai_kit_session_wake.TestMatrix
        status: pass
      - kind: unit
        ref: tests.test_ai_kit_session_wake.TestArmPrimitive
        status: pass
      - kind: unit
        ref: tests.test_ai_kit_session_wake.TestStatus.test_status_displays_armed_state_alive_and_paths
        status: pass
      - kind: unit
        ref: tests.test_ai_kit_session_wake.TestStatus.test_invalid_status_and_rearm_leave_state_and_systemctl_log_unchanged
        status: pass
      - kind: unit
        ref: tests.test_ai_kit_session_wake.TestArmPrimitive.test_no_systemd_fallback_and_unknown_host
        status: pass
      - kind: unit
        ref: tests.test_ai_kit_session_wake.TestRearm.test_changed_timer_text_restarts_after_reload
        status: pass
    human_judgment: false
duration: 60min
completed: 2026-10-29
status: complete
orchestrator_verify: "VERIFY 26-03: 3/3 passed"
---

# Phase 26 Plan 03 Summary

**Re-arm state refresh, safe session identifiers, evidence-labelled wake matrix, and CLI status/matrix commands**

## Accomplishments
- Re-arming refreshes process identity while keeping the wake count, arm time, refs and existing arm identity; unit files are only rewritten when content changes.
- Added exact id validation, two-session separation, secret exclusion, atomic refresh guarantees and file modes, PATH filtering, interpreter checks, and linger warnings/fallback.
- Added the host survival data table, `matrix --json` contract, survival-based arm selection, timer restart when changed, and populated/invalid status reporting.
- Targeted Task 1, Task 2 and Task 3 verify commands passed; `make test-unit`, the CLI JSON smoke check and whole-tree `uv run pyright` passed.

## Task Commits
1. Task 1 — `d9e216a` (`feat(26-03): re-arm refreshes the host process and keeps the wake state`)
2. Task 2 — `c298301` (`feat(26-03): exact ids, isolated sessions, no secrets, atomic writes, a startable unit env and linger`)
3. Task 3 — `3e3c4f2` (`feat(26-03): survival matrix, matrix --json, status and arm by survival`)
4. Follow-up safety tests — `b3edad1` (`test(26-03): cover session isolation, secret exclusion, atomic writes and interpreter checks`)
5. Follow-up matrix/status tests and behavior fixes — `7606684` (`test(26-03): verify survival selection and complete status output`)
6. Refresh metadata and status argument handling — `f876d02` (`test(26-03): pin refresh metadata and complete status argument handling`)

## Files Created/Modified
- `skills/ai-kit-session-wake/ai_kit_session_wake/arm.py` — refresh, interpreter and survival checks.
- `skills/ai-kit-session-wake/ai_kit_session_wake/state.py` — precise refused-id message.
- `skills/ai-kit-session-wake/ai_kit_session_wake/units.py` — filtered service PATH and linger file fallback.
- `skills/ai-kit-session-wake/ai_kit_session_wake/matrix.py` — evidence-labelled wake survival records and JSON/text renderers.
- `skills/ai-kit-session-wake/ai_kit_session_wake/cli.py` — `status` and `matrix` commands.
- `tests/session_wake_fakes.py` — optional fake shebang support.
- `tests/test_ai_kit_session_wake.py` — refresh metadata/restart, identity/isolation, safety, matrix, primitive selection and status tests.

## Issues Encountered
- Pre-commit initially found lint, pylint complexity and test expectation errors; these were fixed before the task commits. A whole-tree unit run exposed the new `systemctl --user show -p Version` call in the legacy expected call list; the expectation was extended and the full unit tier passed. The plan's systemctl fake originally indexed arguments after `--user` incorrectly; corrected so `systemd_available`, `is-active`, and status checks are exercised through the fake.

## Next Phase Readiness
- Matrix schema and CLI are available for Phase 27; the plan's targeted tests and unit tier passed.
