---
phase: 23-host-split-status-line-for-claude-code-and-cursor-cli
plan: 15
subsystem: ui
tags: [cursor, status-line, doctor, quota, host-split]

# Dependency graph
requires:
  - phase: 23-08
    provides: claude-status-line.py entry and claude_host.HOST assembly
  - phase: 23-13
    provides: cursor_host.HOST, cursor_quota cache/lock/refresh probes and QuotaResult
provides:
  - statusline-doctor.py --host claude|cursor (default claude, byte-compatible)
  - Per-host validation, dry render and env help derived from the host ConfigSpec
  - Cursor quota fetch-status report with the inferred-confidence label, foreground
    refresh only on explicit manual --doctor --host cursor
affects: [status-line, cursor, phase-23-16, phase-23-17]

# Actuals (#2632) — pairs with the plan's `estimate` to calibrate future estimates.
actuals:
  tokens: 11000
  tasks: 2
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Doctor commands take a Host (default claude_host.HOST) so every pre-existing
      call site and test keeps working unchanged

key-files:
  created: []
  modified:
    - tools/statusline-doctor.py
    - tests/test_statusline_doctor.py
    - README.md

key-decisions:
  - "The quota refresh runs BEFORE the dry render in cmd_doctor so the render reads
    the just-refreshed cache and spawns no detached refresher; the report text is
    still printed after the health lines."
  - "The fetch seam (cursor_quota.probe_refresh's own default) resolves at call time;
    tests inject fakes explicitly and patch the real fetch seam and detached spawn
    as a network-denial backstop, so no test can reach the network."
  - "env_help returns the verbatim _ENV_HELP for the Claude prefix and generates the
    same layout from the ConfigSpec for other hosts (D-20)."

patterns-established:
  - "Doctor refresh ordering: warm the cache first, dry-render second — never let
    introspection trigger the detached-refresh path."

requirements-completed: [STL-05, STL-03]

coverage:
  - id: D1
    description: "--host claude|cursor selects the diagnosed line; every command uses
      the host's ConfigSpec, builders, sample payload and doctor suffix; default
      host keeps the Claude doctor byte-compatible."
    requirement: STL-05
    verification:
      - kind: unit
        ref: tests/test_statusline_doctor.py#TestHostSwitch.test_help_default_host_lists_host_flag_and_claude_env
        status: pass
      - kind: unit
        ref: tests/test_statusline_doctor.py#TestHostSwitch.test_help_cursor_host_lists_cursor_env
        status: pass
      - kind: unit
        ref: "python3 -S tools/statusline-doctor.py --host cursor --help (scratch env)"
        status: pass
    human_judgment: false
  - id: D2
    description: "env_help is host-derived: Claude's text equals the previous _ENV_HELP
      byte for byte; Cursor's lists AI_KIT_CURSOR_CONFIG_FILE, AI_KIT_CURSOR_SEGMENT_<KEY>
      and AI_KIT_CURSOR_PROVIDER_ and no CC_AI_KIT_ name."
    requirement: STL-05
    verification:
      - kind: unit
        ref: tests/test_statusline_doctor.py#TestHostSwitch.test_env_help_claude_matches_legacy_text
        status: pass
      - kind: unit
        ref: tests/test_statusline_doctor.py#TestHostSwitch.test_env_help_cursor_lists_cursor_names
        status: pass
    human_judgment: false
  - id: D3
    description: "Cursor doctor reports quota state, data age, token-free diagnostic and
      the 'inferred — undocumented Cursor API' label; auth states point at
      cursor-agent login / unsupported login type / missing login; exit stays 0."
    requirement: STL-03
    verification:
      - kind: unit
        ref: tests/test_statusline_doctor.py#TestCursorDoctor.test_doctor_ok_reports_config_builders_and_quota
        status: pass
      - kind: unit
        ref: tests/test_statusline_doctor.py#TestCursorDoctor.test_doctor_auth_expired_points_at_login
        status: pass
    human_judgment: false
  - id: D4
    description: "Only an explicit manual --doctor --host cursor fetches: one foreground
      refresh when the single-flight lock is free, otherwise the report says a refresh
      is in progress; tests deny the network and any detached spawn as a backstop and
      assert zero fetches/spawns on the offline paths."
    requirement: STL-03
    verification:
      - kind: unit
        ref: tests/test_statusline_doctor.py#TestCursorDoctor.test_doctor_lock_held_skips_refresh
        status: pass
      - kind: unit
        ref: tests/test_statusline_doctor.py#TestCursorDoctor.test_token_absent_from_stdout_and_stderr
        status: pass
    human_judgment: false
  - id: D5
    description: "The synthetic auth token appears in neither stdout nor stderr (SPEC R8)."
    requirement: STL-03
    verification:
      - kind: unit
        ref: tests/test_statusline_doctor.py#TestCursorDoctor.test_token_absent_from_stdout_and_stderr
        status: pass
    human_judgment: false
  - id: D6
    description: "Per-host --check flags Claude-only segment keys for Cursor and
      --print-config prints the Cursor segments with the segments-cursor providers dir."
    requirement: STL-05
    verification:
      - kind: unit
        ref: tests/test_statusline_doctor.py#TestCursorDoctor.test_check_cursor_flags_claude_only_segment
        status: pass
      - kind: unit
        ref: tests/test_statusline_doctor.py#TestCursorDoctor.test_print_config_cursor_lists_cursor_segments_dir
        status: pass
    human_judgment: false
  - id: D7
    description: "Project-wide gates stay green: make test and make validate exit 0;
      every pre-existing doctor and external-segment test passes unchanged."
    requirement: STL-05
    verification:
      - kind: other
        ref: make test
        status: pass
      - kind: other
        ref: make validate
        status: pass
    human_judgment: false

# Metrics
duration: 40min
completed: 2026-10-24
status: complete
orchestrator_verify: "VERIFY 23-15: 2/2 passed"
---

# Plan 23-15: status-line doctor `--host` with Cursor quota status Summary

**statusline-doctor.py diagnoses either status line via `--host claude|cursor` (default
Claude, byte-compatible), with a Cursor quota fetch-status report labeled
`inferred — undocumented Cursor API` that only an explicit manual doctor invocation may refresh.**

## Performance

- **Duration:** 40 min
- **Started:** 2026-10-24T00:00:00Z
- **Completed:** 2026-10-24T00:40:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- `--host claude|cursor` (default claude) end to end: per-host config validation,
  dry render of the host's builders against a host sample (`_DOCTOR_SAMPLE_CURSOR`
  mirrors the synthetic Cursor payload shape), and host-derived env help read first
  via `parse_known_args` so `--host cursor --help` lists the `AI_KIT_CURSOR_*` names.
- Cursor quota report: one foreground refresh when the single-flight lock is free,
  "refresh is in progress" when held; prints `state`, data age, token-free
  diagnostic and the confidence label, plus per-state auth guidance
  (`cursor-agent login` / unsupported login type / no login found). The refresh
  runs before the dry render so the render never spawns a detached refresher.
- Strict fetch boundary: only manual `--doctor --host cursor` fetches; the fetch
  default resolves at call time; tests inject fakes and deny the real fetch seam and
  detached spawns as a network backstop; a synthetic-auth test proves the token
  never reaches stdout/stderr (SPEC R8).
- Claude doctor byte-compatible: every pre-existing doctor and external-segment
  test passes unchanged; `env_help(claude_host.SPEC) == _ENV_HELP` byte for byte.

## Task Commits

Each task was committed atomically:

1. **Task 1: `--host cursor --doctor` end to end** - `146a239` (feat)
2. **Task 2: Per-host check, print-config and env help; README doctor line** - this
   commit (test; carries README, the pyright-strict test fix and this summary)

**Plan metadata:** not committed by the executor (orchestrator-owned).

## Files Created/Modified

- `tools/statusline-doctor.py` - `--host` switch, HOSTS map, per-host validation/dry
  render/env help, `quota_report` with the inferred-confidence label
- `tests/test_statusline_doctor.py` - TestHostSwitch + TestCursorDoctor suites
  (host parsing, env help, quota states, lock-held, token absence, network backstop)
- `README.md` - doctor section documents `--host claude|cursor` and the Cursor
  quota confidence label

## Decisions Made

- Refresh-before-render ordering inside `cmd_doctor` (see key-decisions): keeps the
  dry render offline-spawn-free while printing the quota block after the health lines.
- Kept `_ENV_HELP` as the literal Claude help string; `env_help(spec)` returns it
  verbatim for the Claude prefix and generates the layout for other hosts.

## Deviations from Plan

None - plan executed as written. The per-host `--check`/`--print-config`/`env_help`
code landed in the Task 1 commit because Task 1's doctor plumbing and Task 2's
behavior tests are interdependent; Task 2 carries the README change, the full gates
and this summary.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- 23-16 (wizard per-host preview/commit) can rely on the doctor's offline
  validation and on `quota_report` as the reference for fetch-boundary wording.
- Owner-only rows (live Cursor spike, real Dashboard responses) stay
  `not run (owner)` per the phase run rules.

---
*Phase: 23-host-split-status-line-for-claude-code-and-cursor-cli*
*Completed: 2026-10-24*
