---
phase: 03-tool-substitution-awareness-hook
verified: 2026-09-09T00:00:00Z
status: passed
score: 9/9 must-haves verified
covered_files:
  - ".planning/REQUIREMENTS.md"
  - ".planning/ROADMAP.md"
  - ".planning/phases/03-tool-substitution-awareness-hook/03-01-PLAN.md"
  - ".planning/phases/03-tool-substitution-awareness-hook/03-01-SUMMARY.md"
  - ".planning/phases/03-tool-substitution-awareness-hook/03-02-PLAN.md"
  - ".planning/phases/03-tool-substitution-awareness-hook/03-02-SUMMARY.md"
  - ".planning/phases/03-tool-substitution-awareness-hook/03-CONTEXT.md"
  - ".planning/phases/03-tool-substitution-awareness-hook/03-DISCUSSION-LOG.md"
  - ".planning/phases/03-tool-substitution-awareness-hook/03-RESEARCH.md"
  - ".planning/phases/03-tool-substitution-awareness-hook/03-REVIEW-FIX.md"
  - ".planning/phases/03-tool-substitution-awareness-hook/03-REVIEW.md"
  - ".planning/phases/03-tool-substitution-awareness-hook/03-REVIEWS.md"
  - ".pre-commit-config.yaml"
  - "Makefile"
  - "README.md"
  - "pyproject.toml"
  - "tests/test_tool_substitution_hook.py"
  - "tools/hooks/README.md"
  - "tools/hooks/claude_session_start.py"
  - "tools/hooks/cursor_session_start.py"
  - "tools/hooks/detect.py"
  - "tools/setup.py"
covered_digest: "v1:sha256:999dba35557338a616df27a6bd07b2f7f78911d35fe31c270e838d23fe70a0e9"
behavior_unverified: 0
overrides_applied: 0
---

# Phase 3: Tool-Substitution Awareness Hook Verification Report

**Phase Goal:** Claude Code sessions start with an accurate, live-verified explanation of which rtk-driven tool substitutions are actually active on this machine (amended 2026-09-08: Cursor also wired, opencode is the one accepted gap).
**Verified:** 2026-09-09
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Phase 3 Success Criteria + REQUIREMENTS)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | SC-1: session start/compact shows a composed message naming only genuinely-installed substitutions from the 5 curated pairs, never reciting catalog intent as verified | ✓ VERIFIED | `tools/hooks/detect.py::detect_substitutions()` computes `installed` per pair via live `shutil.which()`; `compose_message()` only emits lines for pairs where `installed` is true. Independently ran `echo '{}' \| python3 -S tools/hooks/claude_session_start.py` on this machine (real rtk 0.44.1 + bat/rg/fd/sd/eza installed) and got a correct two-part message naming all 5 tools with live-verified flags. `registry.toml`/`audience` (REQUIREMENTS' literal wording) does not exist in the real installed rtk — CONTEXT.md D-06 documents this correction (curated pairs × binary presence × `rtk init --show`), which is what the code implements. |
| 2 | SC-2: when rtk isn't installed, message says so plainly or omits substitution content — never phantom substitutions | ✓ VERIFIED | `compose_message()`: rewrite-notice line only appears when `rtk_hook_active`; otherwise (rtk absent/not-registered/unreadable) a "No rtk rewrite is confirmed active" line appears only if a modern binary is present, else `""`. Independently reproduced: with PATH restricted to a python3-only scratch dir (no rtk/modern binaries reachable), the wrapper emitted bare `{}` — no phantom claims. |
| 3 | SC-3: hook never perceptibly delays session start/compaction, degrades rather than errors when rtk/tools-installer absent | ✓ VERIFIED | `RTK_PROBE_TIMEOUT_SECONDS = 2.0` bounds the `rtk init --show` subprocess; a hang/crash/non-zero-exit degrades to `RTK_SIGNAL_UNREADABLE` (never raises — `except Exception: return RTK_SIGNAL_UNREADABLE`). Both wrappers wrap detect+compose in `try/except Exception` and always emit `{}` and exit 0 on any failure (including a missing sibling `detect.py`, reproduced directly: wrapper alone on PATH → `{}` exit 0). Timed a real invocation on this machine: `real 0m0.025s`. `tests.test_tool_substitution_hook.TestDetect.test_hanging_rtk_returns_within_budget` passes. |
| 4 | SC-4: opencode's lack of an injection point documented, not silently absent; Cursor is NOT a gap and gets the same briefing wired | ✓ VERIFIED | `tools/hooks/README.md`'s Host Coverage table and `tools/hooks/detect.py`'s module docstring both state Claude Code and Cursor are wired and opencode is the one accepted, documented gap. `tools/hooks/cursor_session_start.py` imports the same `detect` module and calls the same `detect_substitutions()`/`compose_message()` functions as the Claude wrapper — confirmed identical composed message from both wrappers in a direct run on this machine. |
| 5 | REQ-tool-substitution-hook-wiring: Claude Code hook wired via `wire_hook_claude`, called from the wizard commit closure, append-if-absent, never touches foreign entries | ✓ VERIFIED | `tools/setup.py:2326` calls `wire_hook_claude(paths.settings, paths.claude_hook, dry)` inside `_make_wizard_commit`'s `commit` closure. Independently ran `wire_hook_claude` against a scratch `settings.json` seeded with a real `rtk hook claude` entry (no `matcher` key): after wiring, rtk's entry was byte/value-identical and a new `matcher: "startup\|compact"` entry was appended; re-wiring produced no duplicate (entry count stayed 2). |
| 6 | REQ-tool-substitution-hook-wiring: Cursor hook wired via `wire_hook_cursor`, same `compose_message()` core, flat lowercase-keyed array | ✓ VERIFIED | `tools/setup.py:2327` calls `wire_hook_cursor(paths.cursor_hooks, paths.cursor_hook, dry)` in the same commit closure. Independently ran `wire_hook_cursor` against a scratch `hooks.json` seeded with a real GSD `sessionStart` entry (`gsd-managed: true`): after wiring, GSD's entry was value-identical and a new flat `{"type": "command", "command": ...}` entry was appended with no `matcher` key. |
| 7 | REQ-tool-substitution-hook-wiring: `cmd_uninstall` symmetrically removes only ai-kit's own hook entries, foreign entries (GSD's, rtk's) untouched | ✓ VERIFIED | `tools/setup.py:2590-2591` calls `unwire_hook_claude(paths.settings, dry)` and `unwire_hook_cursor(paths.cursor_hooks, dry)` from `cmd_uninstall`. Independently ran both unwire functions against the scratch configs from the wiring test above: `rtk hook claude`'s entry and GSD's `sessionStart` entry (with `gsd-managed: true`) both survived value-identical; ai-kit's own appended entries were the only ones removed. |
| 8 | REQ-tool-substitution-detection-composition: pure, independently-tested detection + composition functions, curated set is single source of truth | ✓ VERIFIED | `CURATED_SUBSTITUTIONS` is the one named module constant with exactly the 5 pairs. `tests.test_tool_substitution_hook.TestDetect`/`TestCompose` build real executable stub binaries on a scratch PATH (not mocks) and assert against real `shutil.which()`/`subprocess.run()` behavior — confirmed by reading the test file (`fake_bin()` helper, `tempfile.mkdtemp()`-based scratch PATHs). |
| 9 | Verification commands (this task's instruction 6) | ✓ VERIFIED | See Behavioral Spot-Checks and Anti-Patterns sections below. |

**Score:** 9/9 truths verified (0 present-but-behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tools/hooks/detect.py` | Detection + composition core, 5 curated pairs, 4-state rtk probe | ✓ VERIFIED | 153 lines, substantive, imported by both wrappers and the test suite |
| `tools/hooks/claude_session_start.py` | Claude Code SessionStart wrapper | ✓ VERIFIED | 88 lines; drains stdin, emits `hookSpecificOutput.additionalContext` envelope or `{}`, always exits 0 |
| `tools/hooks/cursor_session_start.py` | Cursor sessionStart wrapper | ✓ VERIFIED | 84 lines; emits `{additional_context: ...}` or `{}`, same detect/compose core |
| `tools/hooks/README.md` | Host-coverage + non-goals docs | ✓ VERIFIED | Documents Claude Code/Cursor wired, opencode accepted gap, two non-goals |
| `tools/setup.py` (new functions) | `wire_hook_claude`, `wire_hook_cursor`, `unwire_hook_claude`, `unwire_hook_cursor`, `_load_hook_config`, `_hook_entries_shape_ok`, `_atomic_write_json`, `_read_json_checked` | ✓ VERIFIED | All present, called from wizard commit closure and `cmd_uninstall`; independently exercised end-to-end (see truths 5-7) |
| `tests/test_tool_substitution_hook.py` | Full test coverage | ✓ VERIFIED | 1295 lines; 73+ test methods across `TestClaudeWrapper`, `TestWiring`, `TestDetect`, `TestCompose`, `TestCursorWrapper`, `TestCursorWiring`, `TestUnwire`, `TestHostCoverageDocs`, `TestGateRegistration` |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `_make_wizard_commit`'s `commit` closure | `wire_hook_claude` / `wire_hook_cursor` | direct call at `tools/setup.py:2326-2327` | ✓ WIRED | Confirmed by reading the closure body; runs on Review-confirm alongside `apply_selection` |
| `cmd_uninstall` | `unwire_hook_claude` / `unwire_hook_cursor` | direct call at `tools/setup.py:2590-2591` | ✓ WIRED | Confirmed alongside pre-existing `unwire_statusline` call |
| `claude_session_start.py` / `cursor_session_start.py` | `tools/hooks/detect.py` | sibling `sys.path` insert + `import detect` inside `main()` | ✓ WIRED | Confirmed via direct execution producing real detection output; import sits inside `main()` (E402-clean, no per-file ruff ignore added) |
| `Makefile` / `.pre-commit-config.yaml` / `pyproject.toml` | `tests/test_tool_substitution_hook` / `tools/hooks/` | explicit unittest module list, py-compile files regex, pyright include | ✓ WIRED | `TestGateRegistration` parses these files as text and asserts the entries exist; independently confirmed `make lint` compiles `tools/hooks/*.py` and `python3 -m unittest tests.test_tool_substitution_hook` runs 73 tests |

### Behavioral Spot-Checks (independently run, this verification)

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Live detection against real installed rtk/bat/rg/fd/sd/eza | `echo '{}' \| python3 -S tools/hooks/claude_session_start.py` | Correct 2-part message naming all 5 pairs with live-verified flags, rewrite-active line present (rtk confirmed) | ✓ PASS |
| Cursor wrapper emits identical message core | `echo '{}' \| python3 -S tools/hooks/cursor_session_start.py` | Same message body, `additional_context` envelope | ✓ PASS |
| Graceful degradation: missing sibling `detect.py` | wrapper alone on scratch dir | `{}` exit 0 | ✓ PASS |
| Graceful degradation: rtk/tools absent from PATH | wrapper + detect.py, PATH restricted to python3-only dir | `{}` exit 0 (no phantom claims) | ✓ PASS |
| No perceptible delay | `time (echo '{}' \| python3 -S tools/hooks/claude_session_start.py)` | `real 0m0.025s` | ✓ PASS |
| `wire_hook_claude`/`wire_hook_cursor` append-if-absent, foreign entries untouched | direct Python call against scratch settings.json/hooks.json seeded with real `rtk hook claude` and GSD `sessionStart` entries | Foreign entries value-identical; ai-kit entry appended once, re-wire does not duplicate | ✓ PASS |
| `unwire_hook_claude`/`unwire_hook_cursor` remove only ai-kit's entry | direct Python call against the same scratch configs post-wire | rtk's and GSD's entries survive value-identical; ai-kit's entries removed | ✓ PASS |
| `python3 -m unittest tests.test_tool_substitution_hook tests.test_setup -v` | full run | `Ran 316 tests ... OK (skipped=19)` | ✓ PASS |
| `make lint` | full run | exit 0, `tools/hooks/*.py` included in `py_compile` list | ✓ PASS |
| `make validate` | full run | Failed only on the confirmed pre-existing baseline (25 ruff errors + 5 pylint C0301, all in `tools/status-line.py`/`tools/wizard_app.py`/`tests/test_ai_kit_spec.py`/`tests/test_ai_kit_spec_superpowers.py`); `pyright`, `vulture`, `shellcheck`, `py-compile`, `unittest (core)`, `unittest (wizard — uv)` all Passed | ✓ PASS (matches expected baseline exactly) |

### Baseline Confirmation (Instruction 6)

`make validate`'s only failures (ruff: 25 errors, pylint: 5×C0301, exit via pylint exit-code 16) are entirely in `tools/status-line.py`, `tools/wizard_app.py`, `tests/test_ai_kit_spec.py`, and `tests/test_ai_kit_spec_superpowers.py` — confirmed by parsing every `--> file:line` reference in the captured output. Cross-checked against `git show --stat` for every Phase 3 commit (`5cd47f2`, `e60e7ad`, `099b658`, `4b9e0cc`, `6bd2f32`, `aa2571f`, `41e015a`, `d7643c5`, `3ae2a50`, `872da35`): none of them touch any of those four files. Nothing in `tools/hooks/*`, `tools/setup.py`'s new functions, or `tests/test_tool_substitution_hook.py` appears in the failure list.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| REQ-tool-substitution-detection-composition | 03-01-PLAN.md | Live-detection + composition functions, curated set single source of truth | ✓ SATISFIED | Truths 1, 2, 8 above |
| REQ-tool-substitution-hook-wiring | 03-01-PLAN.md, 03-02-PLAN.md | SessionStart (Claude+Cursor) hook wiring, graceful degradation, opencode gap documented, symmetric uninstall | ✓ SATISFIED | Truths 3-7 above |

Both requirements remain unchecked (`[ ]`) in `.planning/REQUIREMENTS.md` and Phase 3's roadmap checkbox/progress-table entry is still `[ ]` / "Planned" — this is a bookkeeping gap in the milestone tracking documents, not a code gap (normally closed by the ship/complete-phase step that follows verification). Noted for completeness; does not affect the pass verdict since it carries no functional risk.

### Anti-Patterns Found

None. Scanned `tools/hooks/*.py`, `tools/hooks/README.md`, `tests/test_tool_substitution_hook.py`, and the new `tools/setup.py` regions (lines 1355-1580, 1687-1727) for `TBD|FIXME|XXX|TODO|HACK|PLACEHOLDER` and stub-shaped patterns — zero matches.

### Human Verification Required

None. All truths were verifiable via direct code execution against real and scratch environments; no visual/UX judgment call remains.

### Gaps Summary

No gaps. All 9 observable truths verified with direct evidence (not SUMMARY.md claims): live-verified detection against this machine's real rtk 0.44.1 + bat/rg/fd/sd/eza installation, graceful degradation reproduced directly for a missing `detect.py` sibling and an rtk-absent PATH, both hosts' wiring/unwiring functions independently exercised end-to-end against scratch configs seeded with real foreign entries (rtk's own, GSD's own) that survived value-identical, opencode gap documented in two places, and the full required test/lint/validate command set run with results matching the documented pre-existing baseline exactly.

---

_Verified: 2026-09-09_
_Verifier: Claude (gsd-verifier)_
