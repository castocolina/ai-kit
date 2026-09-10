---
phase: 03-tool-substitution-awareness-hook
plan: 02
subsystem: hooks
tags: [rtk, session-start, cursor, uninstall, atomic-write, hooks.json]

requires:
  - "tools/hooks/detect.py with five curated pairs and a four-state rtk probe (03-01)"
  - "tools/setup.py's _read_json_checked / _load_hook_config / _hook_entries_shape_ok / _atomic_write_json (03-01)"
provides:
  - "tools/hooks/cursor_session_start.py wrapping the same compose_message() core for Cursor's sessionStart"
  - "wire_hook_cursor appending a flat, lowercase-keyed Cursor hooks.json entry, append-if-absent"
  - "unwire_hook_claude / unwire_hook_cursor removing only ai-kit's own entries from cmd_uninstall"
  - "tools/hooks/README.md documenting host coverage (Claude Code + Cursor wired, opencode accepted gap)"
affects: [03-tool-substitution-awareness-hook, 04-config-doctor]

actuals:
  tokens: 88000
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Cross-AI execution (opencode run --model router-env/my-coding) committed all 3 tasks correctly but was cut off by its own wrapper timeout before its final make validate/e2e-docker gates and before writing this SUMMARY.md — completed directly per ONESHOT-RULES Rule 1 (never trust a self-reported pass without independent re-verification)."
    - "unwire_hook_* reuses plan 01's _load_hook_config with the same nested flag the wire side uses per host, so a malformed array element or nested hooks member is refused (byte-identical, warning on stderr) rather than raising out of cmd_uninstall."

key-files:
  created:
    - tools/hooks/cursor_session_start.py
    - tools/hooks/README.md
    - .planning/phases/03-tool-substitution-awareness-hook/03-02-SUMMARY.md
  modified:
    - tools/setup.py
    - tests/test_tool_substitution_hook.py
    - README.md

key-decisions:
  - "wire_hook_cursor / unwire_hook_cursor are gated on os.path.isdir(paths.cursor_dir); ai-kit never materializes a Cursor configuration on a machine that has never run Cursor."
  - "Cursor's bare-{} envelope claim is documented as OBSERVED (Cursor's own installed gsd-cursor-session-start.js writes that shape on its error path); the same claim for Claude Code is documented as INFERRED, not asserted as verified for both hosts."
  - "unwire_hook_claude passes nested=True to _load_hook_config (Claude's array is nested); unwire_hook_cursor leaves it false (Cursor's array is flat) — getting this backwards would silently reopen the element-crash path review round 2 found."
  - "Independent post-execution gap closure (commit 41e015a, this segment) fixed 5 new pyright reportOptional* errors and 3 new ruff findings (SIM108/SIM110/SIM117x4/I001) introduced by the cross-AI run's own commits, distinct from the confirmed pre-existing tools/status-line.py / tools/wizard_app.py baseline (25 ruff + 5 pylint C0301)."

patterns-established:
  - "A cross-AI execution run that exits 0 at the wrapper level but never emits its own EXECUTION COMPLETE marker must be treated as truncated, not complete — check for the marker, not just the wrapper's exit code, before trusting a background dispatch."

requirements-completed:
  - REQ-tool-substitution-hook-wiring

coverage:
  - id: D6
    description: "A Cursor sessionStart entry receives the same composed briefing a Claude Code entry receives, wrapped in Cursor's own bare-{} / additional_context envelope"
    requirement: REQ-tool-substitution-hook-wiring
    verification:
      - kind: unit
        ref: "tests.test_tool_substitution_hook.TestCursorWrapper.test_both_hosts_carry_the_same_message"
        status: pass
    human_judgment: false
  - id: D7
    description: "wire_hook_cursor appends a flat, lowercase-keyed entry, is append-if-absent, refuses unparseable/non-dict/malformed-element hooks.json byte-identically, and never modifies GSD's own entry or an existing top-level version"
    requirement: REQ-tool-substitution-hook-wiring
    verification:
      - kind: unit
        ref: "tests.test_tool_substitution_hook.TestCursorWiring"
        status: pass
    human_judgment: false
  - id: D8
    description: "unwire_hook_claude and unwire_hook_cursor remove only ai-kit's own entry from cmd_uninstall, leaving foreign entries (GSD's, rtk's) value-identical, and are a no-op on a config with no ai-kit entry or on a second uninstall"
    requirement: REQ-tool-substitution-hook-wiring
    verification:
      - kind: unit
        ref: "tests.test_tool_substitution_hook.TestUnwire"
        status: pass
    human_judgment: false
  - id: D9
    description: "tools/hooks/README.md documents Claude Code and Cursor as wired and opencode as the one accepted, explained gap; tools/hooks/detect.py's docstring agrees"
    requirement: REQ-tool-substitution-hook-wiring
    verification:
      - kind: unit
        ref: "tests.test_tool_substitution_hook.TestHostCoverageDocs"
        status: pass
    human_judgment: false
  - id: D10
    description: "make test, make lint, make validate, and make e2e-docker are all green with the two hook scripts and widened installer in place"
    requirement: REQ-tool-substitution-hook-wiring
    verification:
      - kind: integration
        ref: "make e2e-docker (clean-room container, no rtk/bat/rg/fd/sd/eza on PATH)"
        status: pass
    human_judgment: false

completed: 2026-09-09
status: complete
---

# Phase 3 Plan 02: Cursor Wiring, Uninstall Symmetry, Host-Coverage Docs Summary

**Cursor's own sessionStart hook now receives the identical rtk-substitution briefing Claude Code receives; `cmd_uninstall` gained the symmetric removal it was missing; opencode's gap is documented, not silent.**

## Performance

- **Tasks:** 3
- **Files created:** 2 (plus this SUMMARY)
- **Files modified:** 3

## Accomplishments

- `tools/hooks/cursor_session_start.py` mirrors `claude_session_start.py`'s shape exactly (realpath `sys.path` insert, guarded stdin drain, fail-open `{}` on any exception) and differs only in its envelope: `{"additional_context": message}` or bare `{}`, matching Cursor's own already-installed `gsd-cursor-session-start.js` error-path precedent.
- `wire_hook_cursor()` reads through plan 01's `_load_hook_config(cursor_hooks, CURSOR_HOOK_EVENT)` (nested=False — Cursor's array is flat), appends a `{"type": "command", "command": ...}` object with no `matcher` and no nested `hooks` wrapper, is append-if-absent, refuses an unparseable/non-dict/malformed-element file byte-identically, and writes `version: 1` only when the file was created from nothing.
- `unwire_hook_claude()` (nested=True) and `unwire_hook_cursor()` (nested=False) remove only ai-kit's own marker-matched entry from `cmd_uninstall`, leaving GSD's and any foreign entry value-identical; both are called from `cmd_uninstall` alongside the pre-existing `unwire_statusline` call.
- `tools/hooks/README.md` documents host coverage (Claude Code wired, Cursor wired, opencode an accepted documented gap) and two non-goals (no `PreToolUse` interception, no modification of rtk's own hook registration); `README.md`'s `## Other tools` and `## Layout` sections link to it.
- The cross-AI execution run (opencode/router-env, task tag `03-02`) committed all 3 tasks correctly but was cut off by its own wrapper timeout mid-Task-3, before running `make validate`/`make e2e-docker` and before writing this SUMMARY.md. Independent re-verification (ONESHOT-RULES Rule 1) found 5 genuine new pyright `reportOptionalMemberAccess`/`reportOptionalSubscript` errors and 3 new ruff findings (SIM108, SIM110, SIM117×4, I001) in the run's own commits, confirmed via `git blame` to be phase-own (not the pre-existing `tools/status-line.py`/`tools/wizard_app.py` baseline). Fixed directly and committed as `41e015a`.

## Task Commits

1. **Task 1: Wire the same briefing into Cursor's sessionStart** — `4b9e0cc` (feat)
2. **Task 2: Close D-10's uninstall gap** — `6bd2f32` (feat)
3. **Task 3: Document host coverage** — `aa2571f` (docs)
4. **Gap closure: pyright/ruff findings from the cross-AI run** — `41e015a` (fix, this segment)

## Files Created/Modified

- `tools/hooks/cursor_session_start.py` — Cursor sessionStart wrapper
- `tools/hooks/README.md` — host-coverage and non-goals documentation
- `tools/setup.py` — `CURSOR_HOOK_EVENT`, `CURSOR_HOOK_MARKER`, `Paths.cursor_dir`/`cursor_hooks`/`cursor_hook`, `wire_hook_cursor`, `unwire_hook_claude`, `unwire_hook_cursor`, wizard-commit and `cmd_uninstall` call sites
- `tests/test_tool_substitution_hook.py` — `TestCursorWrapper`, `TestCursorWiring`, `TestUnwire`, `TestHostCoverageDocs`, extended `TestGateRegistration`
- `README.md` — `## Other tools` paragraph, `## Layout` tree entry

## Decisions Made

None beyond the plan. Followed the locked plan decisions on the nested-flag split between hosts, the OBSERVED-vs-INFERRED envelope-claim wording, and the `created`-flag-driven `version` rule.

## Deviations from Plan

None in the substantive implementation — all 3 tasks match the plan's `<action>` blocks. The only deviation was procedural: the cross-AI executor did not itself complete the final verification gates or write this SUMMARY.md before its own timeout; that closure was done directly in this segment rather than re-dispatching the whole plan.

**Total deviations:** 0 (implementation) / 1 (procedural — closure work completed by orchestrator, not by the cross-AI executor)
**Impact on plan:** None — same commits, same code, gates now independently confirmed green.

## Issues Encountered

Cross-AI execution run was truncated by its own internal timeout before reaching its required `make validate`/`make e2e-docker` gates, landing 3 valid task commits but no completion marker. Diagnosed via absence of an `EXECUTION COMPLETE` marker in the run's captured output despite the wrapper process exiting 0. See Accomplishments above for the fixes applied.

## User Setup Required

None. A real Claude Code or Cursor session will pick up the briefing only after a wizard install (or reconfigure) on a machine whose `~/.claude` or `~/.cursor` directory already exists — per ONESHOT-RULES Rule 5, this run never touched uz's real config; all verification used scratch HOME / the `make e2e-docker` clean-room harness.

## Next Phase Readiness

ROADMAP Phase 3 success criteria 1 and 4 (as amended 2026-09-08) are now both true: Cursor is wired, not a gap; opencode's lack of an injection point is documented in both `tools/hooks/README.md` and `tools/hooks/detect.py`'s docstring. Ready for phase-level code review and goal-backward verification.

## Verification (captured, this segment)

```
$ python3 -m unittest tests.test_tool_substitution_hook -v
Ran 73 tests in 2.728s
OK

$ make lint
shellcheck tools/install.sh tests/test_install.sh
python3 -m py_compile tools/setup.py tools/status-line.py tools/statusline-doctor.py tools/hooks/*.py
# exit 0

$ make validate
pylint: Your code has been rated at 9.98/10 (unchanged — same pre-existing tools/status-line.py/tools/wizard_app.py baseline: 25 ruff + 5 C0301, confirmed via git blame to predate this phase)
pyright...................................................................Passed
vulture....................................................................Passed
shellcheck.................................................................Passed
py-compile.................................................................Passed
unittest (core).............................................................Passed
unittest (wizard — uv)......................................................Passed

$ make e2e-docker
Ran 1328 tests in 19.840s
OK (skipped=20)
16 passed, 0 failed   # tests/test_install.sh
==> ai-kit clean-room E2E: PASS
```

## Self-Check: PASSED

- [x] Cursor wrapper emits the same message payload as the Claude wrapper for the same scratch PATH
- [x] `wire_hook_cursor` is append-if-absent, flat-shaped, and refuses malformed/unparseable configs byte-identically
- [x] GSD's own Cursor entry (including `gsd-managed`) survives value-identical after wiring
- [x] `unwire_hook_claude`/`unwire_hook_cursor` remove only ai-kit's entry; foreign entries and no-ai-kit-entry configs are untouched; uninstalling twice is a no-op
- [x] Atomic-write failure injection leaves both wire and unwire targets byte-identical with no stray temp file
- [x] `tools/hooks/README.md` documents Cursor as wired and opencode as the one accepted gap; `TestHostCoverageDocs` passes
- [x] `make test`, `make lint`, `make validate`, `make e2e-docker` all green (independently re-run this segment, not trusted from the cross-AI run's own truncated report)
- [x] Production commits exist (`4b9e0cc`, `6bd2f32`, `aa2571f`) plus this segment's gap-closure commit (`41e015a`)

---
*Phase: 03-tool-substitution-awareness-hook*
*Completed: 2026-09-09*
