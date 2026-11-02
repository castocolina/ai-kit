---
phase: 26-session-self-resume-and-opengsd-quota-rules
plan: 02
subsystem: infra
tags: [session-wake, systemd-user-timer, resume, liveness, arch-rules]

requires:
  - phase: 26-session-self-resume-and-opengsd-quota-rules plan 01
    provides: AI_KIT_CROSS_AI_CHILD runner marker (scrubbed by the wake's child env)
provides:
  - skills/ai-kit-session-wake package (arm/disarm/fire/done CLI, seams, state, liveness, units, hosts) with the final D-10 fire order
  - tests/session_wake_fakes.py (scoped env, fake systemctl/loginctl/host CLIs, fixed seams)
  - AST isolation rules check_wake_isolation / check_no_wake_import with non-vacuity cases (D-25)
affects: [26-03, 26-04, 26-05, 26-06, 26-07, 26-10, 27]

actuals:
  tokens: 54700  # (2010 + 178) changed lines across both commits, chars/4
  tasks: 2
  commits: 2

key-files:
  created:
    - skills/ai-kit-session-wake/ai-kit-session-wake.py
    - skills/ai-kit-session-wake/ai_kit_session_wake/{__init__,state,liveness,hosts,units,arm,fire,cli}.py
    - tests/session_wake_fakes.py
    - tests/test_ai_kit_session_wake.py
  modified:
    - tests/test_arch.py
    - pyproject.toml
    - Makefile
    - .pre-commit-config.yaml

key-decisions:
  - "fire is written once here in the final D-10 order, with the round-1/2/3 review fixes in place: counted increment re-checks arm_id and not_before under the state lock; state, .done and liveness are re-read under the session lock and again right before Popen; one _finish cap step after every exit past the count"
  - "validate_state guards every read; an invalid state is removed by name only, and created paths are deleted only when they equal one of seven owned absolute paths derived from seams.env (owned_path)"

patterns-established:
  - "Seams dataclass (env, now, proc_root) threads environment/clock/proc through the whole package; state.py is the only os.environ/time.time reader"
  - "Fake-backed test env: scratch PATH/HOME/XDG only, fake systemctl/loginctl/host CLIs logging JSON lines to AI_KIT_FAKE_LOG"

requirements-completed: []

coverage:
  - id: D1
    description: "Arm writes state, lock and both units, prints wrote/systemctl creates lines, and runs daemon-reload + enable --now; fire with the host gone resumes the exact recorded id once (exact argv, launch cwd, stdin /dev/null, scrubbed env, wake marker); done by the resumed agent disarms everything and never stops its own service"
    requirement: QTA-04
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_session_wake.py#TestWakeTracer.test_arm_host_gone_one_resume_then_done_removes_all"
        status: pass
      - kind: unit
        ref: "tests/test_ai_kit_session_wake.py#TestWakeTracer.test_shim_help_names_the_subcommands"
        status: pass
    human_judgment: false
  - id: D2
    description: "RESUME_PROMPT is a code constant pinned to the D-16/D-36 text; only {state_path} is filled in"
    requirement: QTA-04
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_session_wake.py#TestWakeTracer.test_resume_prompt_is_pinned"
        status: pass
    human_judgment: false
  - id: D3
    description: "AST isolation both ways between the session wake and Phase 25, rule 8 extended to the wake package and tools/hooks/*.py, each checker with non-vacuity cases (D-25)"
    requirement: QTA-04
    verification:
      - kind: unit
        ref: "tests/test_arch.py#TestSessionWakeIsolation (4 tests) + TestArchNonVacuity.test_wake_isolation_flags_phase25_reach / .test_no_wake_import_flags_phase25_code"
        status: pass
    human_judgment: false

duration: 52min
completed: 2026-10-29
status: complete
orchestrator_verify: "VERIFY 26-02: 2/2 passed"
---

# Phase 26 Plan 02: Session wake end to end Summary

**The ai-kit-session-wake package arms a claude session, resumes the exact id once after its process dies, and disarms itself completely via done; AST rules now keep it isolated from Phase 25.**

## Accomplishments
- New skill package `skills/ai-kit-session-wake/` (shim + 8 modules): seams-threaded state (validated reads, atomic writes, inode-checked flock), /proc liveness (pid + start + boot id, no comm), the claude host row, systemd user unit rendering with full quoting, arm (refresh-safe `arm_id`, O_EXCL lock), and `fire` in the final D-10 order including the round-1/2/3 review fixes (re-checks under the lock, one `_finish` cap step, `owned_path`-limited deletion).
- `TestWakeTracer` proves one full path on fakes: arm at T0 (state schema, six created paths, four `wrote` + two `systemctl creates` lines, daemon-reload then enable --now), host killed, fire at T0+120 runs exactly one resume with the exact argv in the launch dir with stdin from /dev/null and the scrubbed env plus `AI_KIT_SESSION_WAKE_FIRE`, and the resumed agent's `done` removes every file with disable --now -> clean --what=state -> daemon-reload and no `stop`. The prompt is pinned; the shim `--help` subprocess names all four subcommands.
- Arch rules (D-25): `check_wake_isolation` / `check_no_wake_import` with `TestSessionWakeIsolation` live checks and every non-vacuity case from the plan's behavior list (including both substring catches); rule 8 extended to the wake package and every `tools/hooks/*.py`.
- pyright `extraPaths` gains the new skill; the generated Makefile/pre-commit listings name `tests.test_ai_kit_session_wake` (via `tools/gen_test_groups.py`).

## Task Commits
1. **Task 1: arm, host gone, one resume of the exact id, done, everything removed** - `2875cce` (feat)
2. **Task 2: AST isolation between the session wake and Phase 25, with non-vacuity cases, and rule 8 over the new code and every hook** - this commit (test), includes this SUMMARY

## Files Created/Modified
- `skills/ai-kit-session-wake/**` - the package, shim and CLI (no SKILL.md yet; 26-10 writes it)
- `tests/session_wake_fakes.py` - scratch env, fake binaries, fixed seams, host stand-in
- `tests/test_ai_kit_session_wake.py` - TestWakeTracer (3 tests) + ArmOptions shape
- `tests/test_arch.py` - D-25 checkers, TestSessionWakeIsolation, non-vacuity cases
- `pyproject.toml`, `Makefile`, `.pre-commit-config.yaml` - pyright path and generated test-group listings

## Decisions Made
- `fire`'s step (9) re-check and step (7) share one loop in `_under_lock`: the identical re-check runs twice, once before and once after the session probe (the probe can take 30 s), exactly as the plan's order states.
- The resume child's `Popen` carries a localized `pylint: disable=consider-using-with`: the child must outlive any context manager; the fire waits explicitly (D-10 step 6).

## Deviations from Plan

### Auto-fixed Issues

**1. [run rule 11 - re-pinned outside test] `TestArchitecture.test_rule11_one_supervisor`**
- **Found during:** Task 2 (arch group red phase)
- **Issue:** rule 11 flags `start_new_session=True` outside its allowlist; the wake's single resume legitimately runs in its own session (D-10 step 6), so the new `fire.py` tripped the existing pin.
- **Fix:** added `skills/ai-kit-session-wake/ai_kit_session_wake/fire.py` to `_START_NEW_SESSION_ALLOWED` with the D-10 justification comment. Pin updated, not loosened: the entry is one named module, and the non-vacuity assertion (`owner_count >= 1`, foreign files still flagged) is unchanged and still green.
- **Files modified:** tests/test_arch.py
- **Verification:** arch group 1/1 (66 tests); `make test-unit` 58/58.
- **Committed in:** this commit (Task 2)

---

**Total deviations:** 1 re-pin (rule 11 allowlist), required by the plan's own design (the resume must be killable as a group).
**Impact on plan:** No scope creep; the assertion that guards single-supervision keeps its teeth.

## Issues Encountered
None. Pre-commit hooks (ruff, pylint, py-compile) passed on both commits without `--no-verify`; `uv run pyright` was clean (0 errors) before each commit.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- 26-03 can add `status`/`matrix` and the arm hardening onto a working arm/fire/disarm core; 26-05's interleaving and validation tests can drive `fire`'s already-final D-10 order; 26-04 adds host rows to `HOSTS` only.
- The fire/disarm/rename seams (`Seams.env`, `now`, `proc_root`) are the only knobs 26-05's deterministic interleaving tests should need.

---
*Phase: 26-session-self-resume-and-opengsd-quota-rules*
*Completed: 2026-10-29*
