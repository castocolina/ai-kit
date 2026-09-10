---
phase: 03-tool-substitution-awareness-hook
plan: 01
subsystem: hooks
tags: [rtk, session-start, detect, atomic-write, settings.json]

requires: []
provides:
  - "stdlib-only tools/hooks/detect.py with five curated pairs and a four-state rtk probe"
  - "Claude Code SessionStart wrapper emitting hookSpecificOutput.additionalContext"
  - "atomic append-if-absent wire_hook_claude from the wizard commit callback"
  - "tests.test_tool_substitution_hook wired into make test, pre-commit, py-compile, and pyright"
affects: [03-tool-substitution-awareness-hook]

actuals:
  tokens: 28000
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Three-state JSON reader (_read_json_checked) so absent / ok / unreadable are never conflated"
    - "Shared _load_hook_config + per-element _hook_entries_shape_ok refuse a config they cannot fully interpret"
    - "Function-scoped sibling import inside main() to stay E402-clean without a per-file ignore"

key-files:
  created:
    - tools/hooks/detect.py
    - tools/hooks/claude_session_start.py
    - tests/test_tool_substitution_hook.py
    - .planning/phases/03-tool-substitution-awareness-hook/03-01-SUMMARY.md
  modified:
    - tools/setup.py
    - Makefile
    - .pre-commit-config.yaml
    - pyproject.toml

key-decisions:
  - "Fresh settings.json files are created at mode 0o600, the measured mode of both hosts' own config files, not a umask-derived mode."
  - "compose_message is host-agnostic; no AI-CLI product name appears in the injected string."
  - "The [ok] Hook: + rtk hook line is the only rtk signal; the Cursor hook: line is unused because its semantics are unverified."

patterns-established:
  - "Hook wiring lives in the wizard commit closure, outside the status-line adopt gate, so abort is a structural no-op."
  - "Gate registration is asserted by tests that parse Makefile / pre-commit / pyproject as text, not assumed."

requirements-completed:
  - REQ-tool-substitution-detection-composition
  - REQ-tool-substitution-hook-wiring

coverage:
  - id: D1
    description: "A wired Claude Code SessionStart entry runs the wrapper and emits additionalContext naming a curated modern tool present on a scratch PATH, leaving foreign entries untouched"
    requirement: REQ-tool-substitution-hook-wiring
    verification:
      - kind: unit
        ref: "tests.test_tool_substitution_hook.TestClaudeWrapper.test_tracer_wired_entry_runs_and_emits_context"
        status: pass
    human_judgment: false
  - id: D2
    description: "Unparseable, non-dict, non-dict-element, and nested-non-dict settings.json files are refused with a warning and left byte-identical"
    requirement: REQ-tool-substitution-hook-wiring
    verification:
      - kind: unit
        ref: "tests.test_tool_substitution_hook.TestWiring"
        status: pass
    human_judgment: false
  - id: D3
    description: "detect_substitutions reports five curated pairs and four named rtk states; hang/crash/reformat/absent all degrade rather than raise"
    requirement: REQ-tool-substitution-detection-composition
    verification:
      - kind: unit
        ref: "tests.test_tool_substitution_hook.TestDetect"
        status: pass
    human_judgment: false
  - id: D4
    description: "compose_message is compact, host-agnostic, free of rtk stdout, and honest about rewrite confirmation"
    requirement: REQ-tool-substitution-detection-composition
    verification:
      - kind: unit
        ref: "tests.test_tool_substitution_hook.TestCompose"
        status: pass
    human_judgment: false
  - id: D5
    description: "tools/hooks is registered in make test, py-compile, ruff, and pyright, with registration asserted rather than assumed"
    requirement: REQ-tool-substitution-hook-wiring
    verification:
      - kind: unit
        ref: "tests.test_tool_substitution_hook.TestGateRegistration"
        status: pass
    human_judgment: false

completed: 2026-09-09
status: complete
---

# Phase 3 Plan 01: Tool-Substitution Awareness Hook Summary

**Live-verified rtk substitution briefing at Claude Code SessionStart: five curated pairs, four rtk states, atomic append-if-absent wiring that refuses a config it cannot parse.**

## Performance

- **Tasks:** 3
- **Files created:** 3 (plus this SUMMARY)
- **Files modified:** 4

## Accomplishments

- `detect_substitutions()` reports the five curated pairs against an injected PATH and classifies rtk as absent, confirmed, not-registered, or unreadable. A hang, crash, reformat, or non-zero exit degrades to unreadable and never raises; absent rtk skips the subprocess entirely.
- `compose_message()` emits a two-part host-agnostic briefing from a fixed template. A rewrite claim is made only when the hook is confirmed; all three non-confirmed signals share a no-rewrite-confirmed line when modern binaries are present. Probe stdout and host product names never reach the injected string. Flags in `TOOL_GUIDANCE` were live-verified against bat 0.26.1, rg 15.2.0, fd 10.4.2, sd 1.0.0, and eza v0.23.5.
- `claude_session_start.py` drains stdin in bounded chunks, emits a SessionStart envelope or `{}`, and exits 0 on every path. The sibling `detect` import sits inside `main()` so ruff stays E402-clean without a per-file ignore.
- `wire_hook_claude()` is called from the wizard commit closure (not `cmd_install`), writes through `_atomic_write_json` at mode `0o600` on create, and refuses unparseable / non-dict / malformed-element configs byte-identically.

## Task Commits

1. **Task 1: Tracer — PATH probe to wired SessionStart** — `5cd47f2` (feat)
2. **Task 2: Four-state rtk probe over the curated pair list** — `e60e7ad` (feat)
3. **Task 3: Compact host-agnostic substitution briefing** — `099b658` (feat)

## Files Created/Modified

- `tools/hooks/detect.py` — detection + composition core
- `tools/hooks/claude_session_start.py` — Claude Code SessionStart wrapper
- `tools/setup.py` — three-state reader, atomic JSON writer, hook wiring, wizard commit call site
- `tests/test_tool_substitution_hook.py` — tracer, wiring, detect, compose, gate registration
- `Makefile`, `.pre-commit-config.yaml`, `pyproject.toml` — module and lint wiring

## Decisions Made

None beyond the plan. Followed the locked D-01 through D-08 decisions and the three review-round amendments (create mode `0o600`, function-scoped import, wizard-commit fixture pre-creates `claude_dir`).

## Deviations from Plan

None — plan executed exactly as written.

**Total deviations:** 0
**Impact on plan:** None.

## Issues Encountered

None.

## User Setup Required

None. Plan 03-02 adds Cursor wiring and uninstall symmetry. A real Claude Code session will pick up the briefing only after a wizard install (or reconfigure) on a machine whose `~/.claude` directory already exists.

## Next Phase Readiness

Ready for 03-02 (Cursor `sessionStart` wiring + `unwire_hook_claude` / `unwire_hook_cursor` from `cmd_uninstall`). ROADMAP Phase 3 success criteria 1, 2, and 3 are true for this plan's Claude Code scope: a wired session start emits a live-verified briefing, rtk-absent degrades rather than lying, and the wrapper exits 0 with parseable JSON on every path.

## Verification (captured)

```
$ python3 -m unittest tests.test_tool_substitution_hook -v
Ran 38 tests in 2.617s
OK

$ python3 -m unittest tests.test_tool_substitution_hook.TestDetect -v
Ran 10 tests in 2.012s
OK

$ python3 -m unittest tests.test_tool_substitution_hook.TestCompose -v
Ran 12 tests in 0.020s
OK

$ python3 -m unittest tests.test_tool_substitution_hook.TestGateRegistration -v
Ran 5 tests in 0.001s
OK

$ uv run ruff check tools/hooks/
All checks passed

$ uv run pylint tools/setup.py
Your code has been rated at 10.00/10

$ uv run pre-commit run py-compile --files tools/hooks/detect.py tools/hooks/claude_session_start.py
py-compile...............................................................Passed

$ make lint
python3 -m py_compile ... tools/hooks/*.py   # exit 0

$ make test
Ran 1293 tests in 14.676s
OK (skipped=19)
16 passed, 0 failed   # tests/test_install.sh
```

## Self-Check: PASSED

- [x] Tracer wires a SessionStart entry whose command emits `additionalContext` naming `rg`
- [x] Unparseable / non-dict / malformed-element configs are refused byte-identically
- [x] Atomic-write failure leaves the target byte-identical with no stray temp file
- [x] Created settings files land at mode `0o600`
- [x] Four rtk states covered; hanging probe returns under 5 seconds
- [x] Compose is host-agnostic, compact, and never interpolates probe stdout
- [x] `tests.test_tool_substitution_hook` is in Makefile and pre-commit
- [x] `tools/hooks` is in py-compile, ruff, and pyright; registration asserted by tests
- [x] Production commits exist (`5cd47f2`, `e60e7ad`, `099b658`)

---
*Phase: 03-tool-substitution-awareness-hook*
*Completed: 2026-09-09*
