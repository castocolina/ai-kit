---
phase: 23-host-split-status-line-for-claude-code-and-cursor-cli
plan: 06
subsystem: status-line
tags: [python, host-split, config, renderer]
requires:
  - phase: 23-05
    provides: staged Claude status-line module split
provides:
  - Host-parameterized common renderer and Claude HOST definition
  - ConfigSpec-driven config resolution and provider namespace
  - Host-prefix architecture rule and bad-layout error handling
affects: [23-07, 23-08, 23-13, status-line]
actuals:
  tokens: 138
  tasks: 2
  commits: 2
tech-stack:
  added: []
  patterns: [host-driven render pipeline, ConfigSpec primitive config boundary]
key-files:
  created: []
  modified: [tools/common_types.py, tools/common_config.py, tools/common_fmt.py, tools/common_render.py, tools/claude_host.py, tools/claude_payload.py, tools/status-line.py, tools/statusline-doctor.py, tests/test_status_line.py, tests/test_external_segments.py, tests/test_statusline_doctor.py, tests/test_arch.py, tests/test_setup.py, tests/fixtures/statusline_split/audit.md]
key-decisions:
  - "Typed split-module test handles as Any through importlib to preserve pre-split assertion parity while keeping pyright clean."
patterns-established:
  - "Config resolution depends on ConfigSpec primitives, not on host render objects."
  - "The common renderer receives a Host and never imports host modules."
requirements-completed: [STL-01, STL-02, STL-03]
coverage:
  - id: D1
    description: "Claude HOST drives a host-neutral packer, registry and shell while retaining the render oracle."
    requirement: STL-01
    verification:
      - kind: unit
        ref: "make test"
        status: pass
    human_judgment: false
  - id: D2
    description: "Config resolution and provider namespace are supplied by ConfigSpec, and invalid layouts yield a diagnostic line."
    requirement: STL-02
    verification:
      - kind: unit
        ref: "tests/test_status_line.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "Host prefix literals are confined to host modules and defaults reside in claude_host."
    requirement: STL-03
    verification:
      - kind: other
        ref: "make validate"
        status: pass
    human_judgment: false
duration: 72min
completed: 2026-10-24
status: complete
orchestrator_verify: "VERIFY 23-06: 2/2 passed"
---

# Phase 23: Host-split status line for Claude Code and Cursor CLI Summary

**The Claude status-line renderer and config layer now receive explicit host specifications while preserving the pre-split render oracle.**

## Performance

- **Duration:** approximately 72 min (continuation session; estimate from available run artifacts)
- **Started:** 2026-10-24T02:08:05Z
- **Completed:** 2026-10-24T03:20:04Z
- **Tasks:** 2
- **Files modified:** 13

## Accomplishments
- Added `Host`-driven registry, packer, render shell and doctor invocation; Claude's adapter and defaults assemble in `claude_host.HOST`.
- Added `ConfigSpec`-based config selection, segment/ramp defaults and external provider directory, cache and environment namespace.
- Moved host prefix validation to a non-vacuous split-module architecture test and added regression coverage for malformed layout values.
- Repaired pyright regressions in moved status-line tests using Any-typed importlib module handles; assertions remain at their pre-split typing boundary.
- Confirmed the D-05 golden fixture diff from oracle commit `4c4bcec461df3cf4e4d58e19472429b8a7b29357` is empty.

## Task Commits

1. **Task 1: Host type and host-parameterized packer, registry and shell** — `09c3d6e`.
2. **Task 2: ConfigSpec primitives and Claude defaults in claude_host** — this commit.

## Files Created/Modified
- `tools/common_types.py`, `tools/common_config.py`, `tools/common_fmt.py`, `tools/common_render.py` — host-neutral types, config, formatter and renderer.
- `tools/claude_host.py`, `tools/statusline-doctor.py` — Claude host assembly/defaults and doctor integration.
- `tests/test_status_line.py`, `tests/test_external_segments.py`, `tests/test_statusline_doctor.py`, `tests/test_arch.py`, `tests/test_setup.py` — coverage, migration and import typing.
- `tests/fixtures/statusline_split/audit.md` — updated module ownership and config-placement fate.

## Decisions Made
- Used Any-typed importlib bindings in split-module tests, as in the existing 23-04 compatibility fix, rather than narrowing moved assertions.

## Deviations from Plan

### Auto-fixed Issues

**1. Pyright regression from split-module imports**
- **Found during:** Task 2 validation.
- **Issue:** Plain module imports reintroduced 109 static typing errors across moved tests.
- **Fix:** Bound all split modules referenced by `tests/test_status_line.py` and `tests/test_external_segments.py` with `Any`-typed `importlib.import_module` handles and the pre-split parity comment.
- **Verification:** `uv run pyright` reported 0 errors; `make validate` passed.
- **Committed in:** Task 2 commit.

**Total deviations:** 1 auto-fixed (typing parity).
**Impact on plan:** Required to restore the project's zero-error type gate without changing assertions.

## Issues Encountered
- An earlier `make validate` failed with pyright errors caused by plain imports after the module split. Corrected using the repository's prior 23-04 Any-typed importlib pattern; subsequent validation passed.
- Initial attempts to remove scratch data used a shell variable in a different shell process; removal was then performed with `D=tmp/p23/06` set in the removal command.

## Deleted tests
- No tests deleted. The bootstrap-literal rule was not present at this plan's base; the host-prefix rule replaces it and has a live non-vacuity check.

## Verification
- `make test` — passed (53/53 system-unit modules, 1/1 uv module, 4/4 integration modules, 11/11 e2e modules, 1/1 architecture module; logs showed no failed module).
- `make validate` — passed.
- `uv run pyright` — 0 errors, 0 warnings, 0 informations.
- `uv run ruff check tools skills tests` — passed.
- `uv run vulture` — passed.
- Prefix-literal scan — passed (`prefix ok`).
- `git diff 4c4bcec461df3cf4e4d58e19472429b8a7b29357..HEAD -- tests/fixtures/golden` — empty.

## Next Phase Readiness
- Host-neutral config and render APIs are ready for the next Claude context refactor and Cursor host integration.

---
*Phase: 23-host-split-status-line-for-claude-code-and-cursor-cli*
*Completed: 2026-10-24*
