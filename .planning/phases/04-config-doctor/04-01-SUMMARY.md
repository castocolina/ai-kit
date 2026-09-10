---
phase: 04-config-doctor
plan: 01
subsystem: config-doctor
tags: [config-doctor, tracer, textual, cleanupPeriodDays, 3-state-reader]

requires: []
provides:
  - "stdlib-only tools/config_doctor_readers.py with 3-state JSON/JSONC/TOML readers"
  - "stdlib-only tools/config_doctor_checks.py declarative engine (one Claude retention row)"
  - "tools/config_doctor_app.py Textual review screen, import-free of the engine"
  - "setup.py --config-doctor flag launching the TUI via stdin_on_tty()"
  - "tests.test_config_doctor and tests.test_config_doctor_pty wired into make test, pre-commit, py-compile, and pyright"
affects: [04-config-doctor]

actuals:
  tokens: 40000
  tasks: 2
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Three-state config readers (absent / ok / unreadable) so a missing key default is never conflated with an unreadable file"
    - "Presence-gated catalog: skip missing files, omit zero-row sections, degrade unreadable files to current_display=unknown"
    - "Function-scoped sibling imports inside cmd_config_doctor to stay E402-clean without a per-file ignore"

key-files:
  created:
    - tools/config_doctor_readers.py
    - tools/config_doctor_checks.py
    - tools/config_doctor_app.py
    - tests/test_config_doctor.py
    - tests/test_config_doctor_pty.py
    - .planning/phases/04-config-doctor/04-01-SUMMARY.md
  modified:
    - tools/setup.py
    - Makefile
    - .pre-commit-config.yaml
    - pyproject.toml

key-decisions:
  - "JSONC comment/trailing-comma helpers are ported (not imported) from the ai-kit-opencode-providers skill, matching the tools/ vs skills/ layering rule."
  - "Cursor cli-config.json follows Cursor CLI's three-step precedence (CURSOR_CONFIG_DIR, then XDG_CONFIG_HOME/cursor, then ~/.cursor), not the installer's shorter hooks.json path."
  - "cleanupPeriodDays: 0 is never recommended; apply stays None until Wave 3."

patterns-established:
  - "Config Doctor engine stays import-clean of textual, setup.py, wizard_app.py, and every skills/* package from the first line."
  - "Gate registration is asserted by tests that parse Makefile / pre-commit / pyproject as text, not assumed."

requirements-completed: []

coverage:
  - id: D-01
    description: "One Claude Code cleanupPeriodDays row travels from a scratch settings.json through build_catalog to a rendered --config-doctor table showing 15 / 3650 / code.claude.com"
    requirement: REQ-config-doctor-review-screen
    verification:
      - kind: pty
        ref: "tests.test_config_doctor_pty.TestConfigDoctorPty.test_config_doctor_renders_one_real_row_end_to_end"
        status: pass
    human_judgment: false
  - id: D-03
    description: "A runtime with no config file present is omitted entirely; all four files present with zero matching rows still yield only the Claude section"
    requirement: REQ-config-doctor-diagnostic-checks
    verification:
      - kind: unit
        ref: "tests.test_config_doctor.TestPresence"
        status: pass
    human_judgment: false
  - id: D-07
    description: "--config-doctor under piped stdin is still drivable because cmd_config_doctor wraps the TUI in stdin_on_tty()"
    requirement: REQ-config-doctor-review-screen
    verification:
      - kind: pty
        ref: "tests.test_config_doctor_pty.TestConfigDoctorPty.test_config_doctor_renders_under_piped_stdin"
        status: pass
    human_judgment: false
  - id: SC-2
    description: "Malformed JSON and non-dict top-level values show current_display=unknown; an absent cleanupPeriodDays key shows the documented default 30"
    requirement: REQ-config-doctor-review-screen
    verification:
      - kind: unit
        ref: "tests.test_config_doctor.TestUnknownDegrade"
        status: pass
    human_judgment: false

completed: 2026-09-09
status: complete
---

# Phase 4 Plan 01: Config Doctor Tracer Summary

**One real Claude Code retention row, from a config-file-presence probe through the declarative engine to a Textual review screen launched by `setup.py --config-doctor`.**

## Performance

- **Tasks:** 2
- **Files created:** 5 (plus this SUMMARY)
- **Files modified:** 4

## Accomplishments

- `read_json_checked` / `read_jsonc_checked` / `read_toml_checked` implement the 3-state contract (absent / ok-dict / unreadable). JSONC stripping is a local port of the opencode-providers skill's read-only helpers. `read_toml_checked` is a new function, not `setup.read_toml`.
- `build_catalog(env)` probes all four runtime config paths, skips missing files, omits zero-row sections, and degrades an unreadable file to `current_display="unknown"` without calling `row.read` when `reads_section_file` is True. The tracer row `claude-retention` recommends `3650`, never `0`.
- `ConfigDoctorApp` renders a DataTable plus a why/source detail pane, escaping every config-sourced string through `rich.markup.escape()`. Empty catalogs show a plain "no supported AI-CLI config file" message.
- `setup.py --config-doctor` is a flag (the `doctor` subcommand is untouched), returns before install dispatch, and wraps the TUI in `stdin_on_tty()` so `curl | bash` remains drivable.

## Task Commits

1. **Task 1: Tracer — Claude Code retention row through `--config-doctor`** — `4cd3c4e` (feat)
2. **Task 2: Presence/unknown degrade + quality-gate registration** — `daa47d6` (feat)

## Files Created/Modified

- `tools/config_doctor_readers.py` — 3-state JSON/JSONC/TOML readers + `get_nested`
- `tools/config_doctor_checks.py` — `CheckRow`, path resolver, `evaluate_row`, `build_catalog`, one row
- `tools/config_doctor_app.py` — Textual review screen
- `tools/setup.py` — `--config-doctor` flag, `cmd_config_doctor`
- `tests/test_config_doctor.py` — readers, tracer catalog, presence, unknown, gate registration
- `tests/test_config_doctor_pty.py` — PTY render + piped-stdin `curl | bash` shape
- `Makefile`, `.pre-commit-config.yaml`, `pyproject.toml` — module and lint wiring

## Decisions Made

None beyond the plan. Followed D-01, D-03, D-06, D-07 and Phase 3's function-scoped import / gate-registration precedents.

## Deviations from Plan

- JSONC helper docstrings cite the hyphenated skill name (`ai-kit-opencode-providers`) rather than the underscore package path. The plan's verify grep treats `ai_kit_opencode_providers` as a forbidden import, so the citation was worded to keep that grep clean while still attributing the port. The helpers are copied, not imported.

**Total deviations:** 1
**Impact on plan:** None. Layering and attribution both hold.

## Issues Encountered

None.

## User Setup Required

None. Wave 2 (04-02) expands the catalog to all researched rows. Wave 3 (04-03) wires apply. A real `--config-doctor` run on this machine will only show runtimes whose config files actually exist.

## Next Phase Readiness

Ready for 04-02 (full Checks Catalog, still read-only). ROADMAP Phase 4 success criteria 1 and 2 are true for this plan's tracer scope: one cited Claude Code row renders with its real current value, and a missing or unreadable config degrades rather than lying.

## Verification (captured)

```
$ python3 -m unittest tests.test_config_doctor -v
Ran 21 tests in 0.003s
OK

$ python3 -m unittest tests.test_config_doctor_pty -v
Ran 2 tests in 1.506s
OK

$ python3 -m unittest tests.test_config_doctor.TestPresence tests.test_config_doctor.TestUnknownDegrade -v
Ran 9 tests in 0.001s
OK

$ python3 -m unittest tests.test_config_doctor.TestGateRegistration -v
Ran 5 tests in 0.001s
OK

$ grep -rn "import setup\|from setup import\|import wizard_app\|ai_kit_opencode_providers" tools/config_doctor_checks.py tools/config_doctor_readers.py
# no matches (exit 1 — the passing outcome)

$ grep -A40 "def cmd_config_doctor" tools/setup.py | grep -c "stdin_on_tty"
1

$ grep -v '^#' Makefile | grep -c 'tests\.test_config_doctor\b'
1

$ grep -v '^#' Makefile | grep -c 'tests\.test_config_doctor_pty\b'
1

$ uv run pre-commit run py-compile --files tools/config_doctor_checks.py tools/config_doctor_readers.py tools/config_doctor_app.py
py-compile...............................................................Passed

$ make lint
python3 -m py_compile ... tools/config_doctor_*.py   # exit 0
```

## Self-Check: PASSED

- [x] PTY test renders cleanupPeriodDays current `15`, recommended `3650`, and `code.claude.com`
- [x] Piped-stdin PTY test proves `stdin_on_tty()` wrap
- [x] Missing config files yield `{"sections": []}`; zero-row runtimes are omitted separately
- [x] Malformed / non-dict JSON show `"unknown"`; absent key shows `"30"`
- [x] Engine modules import nothing from textual, setup.py, wizard_app.py, or skills packages
- [x] `--config-doctor` is a flag that returns before install dispatch
- [x] `tests.test_config_doctor` and `tests.test_config_doctor_pty` are in Makefile and pre-commit
- [x] `tools/config_doctor_*.py` is in py-compile and pyright; pylint/vulture are not widened
- [x] Production commits exist (`4cd3c4e`, `daa47d6`)

---
*Phase: 04-config-doctor*
*Completed: 2026-09-09*
