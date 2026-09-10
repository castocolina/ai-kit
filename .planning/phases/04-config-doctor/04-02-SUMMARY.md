---
phase: 04-config-doctor
plan: 02
subsystem: config-doctor
tags: [config-doctor, checks-catalog, ReadContext, rtk-cursor-integration]

requires:
  - phase: 04-config-doctor
    provides: Wave 1 tracer engine, 3-state readers, one Claude retention row
provides:
  - "CONFIG_DOCTOR_ROWS grown from 1 to 25 research-cited CheckRow records"
  - "ReadContext (data/env/runner) so env-only and subprocess-probed rows share the engine"
  - "Cross-runtime rtk-Cursor-integration section ungated by config-file presence"
  - "Full 25-row, 5-section PTY render of setup.py --config-doctor"
affects: [04-config-doctor]

actuals:
  tokens: 45000
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "ReadContext NamedTuple (data, env, runner) replaces evaluate_row(row, data)"
    - "reads_section_file=False rows survive an unreadable section file"
    - "Cross-runtime catalog pass has no os.path.isfile gate"

key-files:
  created:
    - .planning/phases/04-config-doctor/04-02-SUMMARY.md
  modified:
    - tools/config_doctor_checks.py
    - tools/config_doctor_readers.py
    - tests/test_config_doctor.py
    - tests/test_config_doctor_pty.py

key-decisions:
  - "claude-telemetry and cursor-sandbox-json set reads_section_file=False so their values survive an unreadable section file."
  - "opencode-model-options confidence is LOW because this machine's router-env provider id is unverified (Assumption A2)."
  - "cursor-local-retention and cursor-cli-telemetry return UNKNOWN unconditionally; apply stays None permanently."
  - "_probe_rtk_cursor_hook matches Cursor plus lowercase hook, never a case-sensitive Hook, against the live-verified rtk v0.44.1 line."

patterns-established:
  - "Permanently informational rows state apply stays None permanently in their own why text, distinct from not-yet-wired."
  - "A present-but-non-dict value (permission, modelParameters) degrades to unknown rather than a guessed repr."

requirements-completed: []

coverage:
  - id: T1-CLAUDE-OPENCODE
    description: "Claude Code rows 2/2b/3/3b/4 and opencode rows 5/6/7/7b evaluate against realistic fixtures; claude-telemetry survives unreadable settings.json"
    requirement: REQ-config-doctor-diagnostic-checks
    verification:
      - kind: unit
        ref: "tests.test_config_doctor.TestClaudeRowsExpanded"
        status: pass
      - kind: unit
        ref: "tests.test_config_doctor.TestOpencodeRows"
        status: pass
    human_judgment: false
  - id: T2-CODEX-CURSOR
    description: "Codex rows 8-11 and Cursor rows 13-19 evaluate against realistic fixtures; rows 17/18 are unconditional unknown; row 15b reads sandbox.json independently"
    requirement: REQ-config-doctor-diagnostic-checks
    verification:
      - kind: unit
        ref: "tests.test_config_doctor.TestCodexRows"
        status: pass
      - kind: unit
        ref: "tests.test_config_doctor.TestCursorRows"
        status: pass
    human_judgment: false
  - id: T3-CROSS-FULL
    description: "rtk-cursor-integration appears with zero config files present; 25 rows across 5 sections render under a real PTY"
    requirement: REQ-config-doctor-review-screen
    verification:
      - kind: unit
        ref: "tests.test_config_doctor.TestCrossRuntimeRow"
        status: pass
      - kind: unit
        ref: "tests.test_config_doctor.TestFullCatalogRegression"
        status: pass
      - kind: pty
        ref: "tests.test_config_doctor_pty.TestConfigDoctorPty.test_full_catalog_renders_under_pty_without_crashing"
        status: pass
    human_judgment: false

completed: 2026-09-10
status: complete
---

# Phase 4 Plan 02: Config Doctor Full Checks Catalog Summary

**Every researched Checks Catalog row except the explicitly-excluded row 20 is now a read-only CheckRow: 25 records across Claude Code, opencode, Codex, Cursor, and a cross-runtime rtk-Cursor-integration section.**

## Performance

- **Tasks:** 3
- **Files created:** 1 (this SUMMARY)
- **Files modified:** 4

## Accomplishments

- `ReadContext` (`data`, `env`, `runner`) is the `evaluate_row` contract. Row 1's reader was updated in the same commit as the new Claude/opencode rows; Wave 1 assertions still pass.
- `claude-telemetry` reads `ctx.env` with `reads_section_file=False` and still reports `1` when `settings.json` is unreadable. Its `why` scopes the claim to the process environment, not a `settings.json` `"env"` block.
- `opencode-retention` states `apply` stays `None` permanently. `opencode-permissions` returns `UNKNOWN` for a non-dict `"permission"` value. `opencode-model-options` is `LOW` confidence and names `router-env`.
- Codex rows 8-11 and Cursor rows 13-19 are in the catalog. Rows 17 and 18 return `UNKNOWN` unconditionally. Row 15b reads `sandbox.json` itself (Common Pitfall 5 / Open Question 1).
- `_probe_rtk_cursor_hook` ports the Phase 3 bounded subprocess pattern and matches `"Cursor"` plus lowercase `"hook"`. The cross-runtime pass has no `os.path.isfile` gate. 25 rows across 5 sections render under a real PTY.

## Task Commits

1. **Task 1: Claude Code remaining rows, opencode catalog, ReadContext** — `8b72d4c` (feat)
2. **Task 2: Codex catalog and Cursor catalog** — `5bac8c3` (feat)
3. **Task 3: rtk-Cursor-integration and full-catalog PTY** — `330a5c1` (feat)

## Files Created/Modified

- `tools/config_doctor_checks.py` — `ReadContext`, 24 new rows, cross-runtime pass
- `tools/config_doctor_readers.py` — `_probe_rtk_cursor_hook`
- `tests/test_config_doctor.py` — Claude/opencode/Codex/Cursor/cross/full-catalog tests
- `tests/test_config_doctor_pty.py` — full-catalog PTY render

## Decisions Made

None beyond the plan. Followed RESEARCH citations, Common Pitfalls 3-7, Open Questions 1-3, and Assumption A2.

## Deviations from Plan

- `read_rtk_cursor_integration` honors `env["PATH"]` when present (so tests can isolate a stub `rtk` without rewriting process PATH), then falls back to `os.environ["PATH"]`. The plan named `shutil.which("rtk")` with no path argument; the extra lookup is required so a scratch `env` that does not carry `PATH` still finds a real binary, while tests that *do* set `env["PATH"]` stay isolated from the host `rtk`.

**Total deviations:** 1
**Impact on plan:** None. Probe classification and the three display states are unchanged.

## Issues Encountered

Isolating process `PATH` to a scratch bin that contains only the `rtk` stub made the stub's `cat <<EOF` produce empty stdout (no `cat` on PATH). Tests now put the stub first on `env["PATH"]` and leave the process PATH intact so the stub can still run `cat`.

## User Setup Required

None. Wave 3 (04-03) wires apply by editing these same `CheckRow` records in place. A real `--config-doctor` run on this machine will show every runtime whose config file exists, plus the ungated cross-runtime row.

## Next Phase Readiness

Ready for 04-03 (apply writers). `CONFIG_DOCTOR_ROWS` holds every row `04-RESEARCH.md` documents except the explicitly-excluded row 20. Every row still has `apply=None`.

## Verification (captured)

```
$ python3 -m unittest tests.test_config_doctor -v
Ran 47 tests in 0.048s
OK

$ python3 -m unittest tests.test_config_doctor_pty -v
Ran 3 tests in 2.315s
OK

$ python3 -c "import sys; sys.path.insert(0, 'tools'); import importlib.util as u; s=u.spec_from_file_location('cdc','tools/config_doctor_checks.py'); m=u.module_from_spec(s); s.loader.exec_module(m); print(len(m.CONFIG_DOCTOR_ROWS))"
25

$ make lint
shellcheck tools/install.sh tests/test_install.sh
python3 -m py_compile tools/setup.py tools/status-line.py tools/statusline-doctor.py tools/hooks/*.py tools/config_doctor_*.py
```

## Self-Check: PASSED

- [x] `CONFIG_DOCTOR_ROWS` contains exactly 25 rows
- [x] `ReadContext` has fields `data`, `env`, `runner`; every `read` accepts `ctx`
- [x] `claude-telemetry` survives unreadable `settings.json`; other Claude rows degrade to `"unknown"`
- [x] `opencode-permissions` non-dict value degrades to `"unknown"`
- [x] `opencode-model-options` confidence is `"LOW"` and `why` names `"router-env"`
- [x] Codex/Cursor rows evaluate against realistic fixtures; rows 17/18 are unconditional `"unknown"`
- [x] `cursor-sandbox-json` reads `sandbox.json` independently of `cli-config.json`
- [x] Cross-runtime row appears with zero config files present; three probe states covered
- [x] Full catalog PTY test renders without crashing (3 PTY tests, 0 failures)
- [x] Production commits exist (`8b72d4c`, `5bac8c3`, `330a5c1`)

---
*Phase: 04-config-doctor*
*Completed: 2026-09-10*
