---
phase: 26-session-self-resume-and-opengsd-quota-rules
plan: 07
subsystem: session-wake
tags: [claude-code-hooks, stopfailure, rate-limit, process-group, deadline, opt-in]

# Dependency graph
requires:
  - phase: 26-session-self-resume-and-opengsd-quota-rules plan 06
    provides: the reset parser, reset_inferred wake fields, redaction of evidence
provides:
  - arm --only-if-armed (refresh an existing wake only; keep recorded identity without a pid)
  - tools/hooks/claude_session_wake.py, a fail-open StopFailure hook with one 8 s deadline
  - HOOK_REGISTRY row session-wake (claude, StopFailure, rate_limit, experimental, off)
affects: [26-08, 26-09, 26-10, 26-12]

actuals:
  tokens: 12751
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "A hook child runs in its own session; the hook kills its group at a monotonic deadline"
    - "Hook-id pins are extended by index-free lookups (precompact cell read by header name)"

key-files:
  created:
    - tools/hooks/claude_session_wake.py
    - tests/test_claude_session_wake_hook.py
  modified:
    - skills/ai-kit-session-wake/ai_kit_session_wake/arm.py
    - skills/ai-kit-session-wake/ai_kit_session_wake/cli.py
    - tests/test_arch.py
    - tools/setup.py
    - tools/hooks/README.md
    - README.md
    - tests/test_hook_registry.py
    - tests/test_hook_registry_e2e.py
    - tests/test_tool_substitution_hook.py
    - tests/test_wizard_pty.py
    - Makefile
    - .pre-commit-config.yaml

key-decisions:
  - "tests/test_arch.py rule 11 allowlist gains tools/hooks/claude_session_wake.py: the hook's arm child needs start_new_session=True to kill its group at the deadline, the same pattern as fire.py (26-02). Without it the group kill would target the host's own process group."
  - "The hook's payload fields that carry the reset text remain unverified (RESEARCH Q5); with no `resets` text the hook does nothing. The row is experimental and off by default."
  - "The hook tests run the hook under an explicit scratch env with a stand-in host process; no real Claude Code, systemd or home is touched."

patterns-established:
  - "Deadline test: slow stdin trickle and a slow child each must exit under 9 s, and the child group (shim plus grandchild) must be dead afterwards."

requirements-completed: [QTA-04]

coverage:
  - id: D1
    description: "A StopFailure payload carrying the reset text refreshes an armed session wake to reset + 60 s (reset_inferred, second OnCalendar line); unarmed sessions and payloads without `resets` write nothing"
    requirement: "QTA-04"
    verification:
      - kind: unit
        ref: "tests/test_claude_session_wake_hook.py#TestStopFailureHook"
        status: pass
  - id: D2
    description: "The hook exits by itself before the 10 s row timeout: slow input and slow child both finish under 9 s, and the child's process group is killed"
    requirement: "QTA-04"
    verification:
      - kind: unit
        ref: "tests/test_claude_session_wake_hook.py#TestHookDeadline"
        status: pass
  - id: D3
    description: "arm --only-if-armed exits 0 with `not armed; nothing refreshed` before any probe when no state exists"
    requirement: "QTA-04"
    verification:
      - kind: unit
        ref: "tests/test_claude_session_wake_hook.py#TestStopFailureHook"
        status: pass
  - id: D4
    description: "session-wake is registered as an opt-in, experimental, default-off Claude row and documented in the hook README and the --with-hooks table"
    requirement: "QTA-04"
    verification:
      - kind: integration
        ref: "tests/test_wizard_pty.py"
        status: pass
      - kind: e2e
        ref: "tests/test_hook_registry_e2e.py#test_each_id_alone_wires_only_its_entries"
        status: pass
      - kind: unit
        ref: "tests/test_hook_registry.py#TestRegistryShape"
        status: pass

metrics:
  duration: "not measured"
  completed: "2026-10-30"
orchestrator_verify: "VERIFY 26-07: 2/2 passed"
---

# Phase 26 Plan 07: StopFailure hook passes the reset text to an armed wake Summary

**An opt-in, fail-open StopFailure hook refreshes an armed session wake to the host's reset + 60 s, with one 8 s deadline and a session-wake registry row that is off by default.**

## Performance

- **Tasks:** 2 (both committed)
- **Commits:** `d83a520`, `d670fa4`

## Accomplishments

- `arm --only-if-armed`: exits 0 with `not armed; nothing refreshed` before any probe when no state file exists; on a refresh with no resolvable pid it keeps the recorded pid, start time, boot id, launch dir and CLI.
- `tools/hooks/claude_session_wake.py`: reads one StopFailure event, requires a string `session_id` and the `resets ` marker in `error`, `error_details` or `last_assistant_message`, then runs `arm --host claude --only-if-armed --reset-text` as an argv list (no shell) in its own session.
- One monotonic 8 s deadline covers the bounded stdin read and the arm child; the child gets the time left, is skipped under 1 s left, and its whole process group is SIGKILLed at the deadline. The row's registered timeout is 10 s.
- `HOOK_REGISTRY` row `session-wake` (claude, `StopFailure`, matcher `rate_limit`, timeout 10, experimental, default off) with a 127-character `HOOK_SUMMARIES` entry.
- Hook-id pins extended in `test_hook_registry`, `test_hook_registry_e2e`, `test_wizard_pty` and `test_tool_substitution_hook`; the host-table precompact cell is now read by header name, not position.
- Docs: `tools/hooks/README.md` (host-coverage column and a description line), `README.md` (HOOKS group sentence, `--with-hooks` table, "six ids").

## Files Created/Modified

- `tools/hooks/claude_session_wake.py` - new fail-open StopFailure hook
- `tests/test_claude_session_wake_hook.py` - new: TestStopFailureHook (7 tests with TestHookDeadline)
- `skills/ai-kit-session-wake/ai_kit_session_wake/arm.py` - `only_if_armed`, `_not_armed`, `_recorded_target`
- `skills/ai-kit-session-wake/ai_kit_session_wake/cli.py` - `--only-if-armed` flag
- `tests/test_arch.py` - rule 11 allowlist entry for the hook's session child
- `tools/setup.py` - `session-wake` HOOK_REGISTRY row and HOOK_SUMMARIES entry
- `tools/hooks/README.md`, `README.md` - session-wake docs
- `tests/test_hook_registry.py`, `tests/test_hook_registry_e2e.py`, `tests/test_wizard_pty.py`, `tests/test_tool_substitution_hook.py` - pins extended
- `Makefile`, `.pre-commit-config.yaml` - regenerated test-group listings

## Commits

- `d83a520` feat(26-07): StopFailure hook passes the reset text to an armed session wake
- `d670fa4` feat(26-07): register the session-wake StopFailure hook, off by default

## Decisions Made

- **Rule 11 allowlist extended for the hook.** Rule 11 allows `start_new_session=True` only in the runner, two probes, `cursor_quota.py` and `fire.py`. The plan requires the hook's arm child to run in its own session so the deadline can kill its group; without that, the kill would reach the host's process group. The entry carries a comment, matching `fire.py`.
- **Reset-text payload fields remain unverified** (RESEARCH Q5, Open Question 2). The row is experimental and off; the hook does nothing without a `resets` marker.

## Deviations from Plan

- **Auto-fixed (pre-commit):** the first commit attempt failed ruff SIM105 (twice) and pylint R1732 and R0911. Fixed with `contextlib.suppress`, a `with Popen` block, and moving the `only_if_armed` check into `_not_armed`/`_recorded_target`. Re-ran the module tests, arch and pyright before the successful commit.
- **Test pins:** `test_tool_substitution_hook`'s precompact cell lookup changed from `[-1]` to a header-name lookup, because `session-wake` is now the last column. Same assertions, same cells.

## Issues Encountered

- The first `d83a520` commit attempt failed the pre-commit hooks (ruff, pylint), so git created no commit; the fixes were made and the same paths re-staged explicitly for the commit that landed.
- Pylint reports messages in `tests/test_arch.py` when run on the whole tree, but the hook gates `tools/` and `skills/` only; those messages predate this plan and were not touched.
- A `bash -c` loop running `commands/evals/explain-pr-changes.json` against `router-env/my-referee-one` (PID 616726) is running in this environment. It is not part of this plan, was not started by this executor, and was left alone.

## Next Phase Readiness

- The hook is wired and registered but off by default; whether the StopFailure payload carries the reset text stays an open question (RESEARCH Q5) that a live run must settle before the row leaves experimental.

## Self-Check

- [x] `tests.test_claude_session_wake_hook` (TestStopFailureHook, TestHookDeadline) pass; module group 3/3; arch 1/1; `make test-unit` 61/61.
- [x] pyright 0 errors; pre-commit hooks passed on both commits.
- [x] Processes started for verification are gone (the `sleep 60` and `sleep 120` stand-ins and gc-late grandchildren).
- [x] No `gc.pid` or scratch files left in the repo root; scratch lives under `tmp/p26/07/`.
