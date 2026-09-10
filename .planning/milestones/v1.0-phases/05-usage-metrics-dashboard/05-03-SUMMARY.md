---
phase: 05-usage-metrics-dashboard
plan: 03
subsystem: usage-metrics
tags: [usage-metrics, codex, cursor, jsonl, raw-capture]

requires:
  - "05-01 CaptureResult contract and 8-key envelope"
  - "05-02 CAPTURE_SOURCES registry (claude, opencode, rtk) plus envelope-extension sibling keys"
provides:
  - "capture_codex: recursive YYYY/MM/DD/rollout-*.jsonl with filename-derived session_id"
  - "capture_cursor: agent-transcripts JSONL only, source_confidence=low, store.db excluded"
  - "CAPTURE_SOURCES grown to 5 entries (claude, opencode, rtk, codex, cursor)"
affects: [05-usage-metrics-dashboard]

actuals:
  tokens: 90000
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Recursive glob for date-nested JSONL (Codex YYYY/MM/DD) and 2-level uuid nesting (Cursor agent-transcripts)"
    - "Filename/path-derived session_id as a top-level envelope sibling, independent of per-file cursor resume"
    - "source_confidence=low as a top-level envelope sibling (not a payload wrapper)"
    - "AST-based sqlite3-absence check so the Cursor docstring may name store.db/blobs in prose"

key-files:
  created:
    - skills/ai-kit-usage-metrics/ai_kit_usage_metrics/capture_codex.py
    - skills/ai-kit-usage-metrics/ai_kit_usage_metrics/capture_cursor.py
    - .planning/phases/05-usage-metrics-dashboard/05-03-SUMMARY.md
  modified:
    - skills/ai-kit-usage-metrics/ai_kit_usage_metrics/paths.py
    - skills/ai-kit-usage-metrics/ai_kit_usage_metrics/cli.py
    - skills/ai-kit-usage-metrics/SKILL.md
    - .planning/REQUIREMENTS.md
    - tests/test_ai_kit_usage_metrics.py

key-decisions:
  - "Codex function_call.arguments stays a JSON-encoded STRING through capture; 05-04 json.loads it."
  - "Codex session_id is parsed from the rollout filename UUID, never from payload.session_id, so resume past session_meta still groups."
  - "Cursor store.db is a documented exclusion (opaque blobs, empty meta); REQUIREMENTS.md carries a dated amendment."
  - "cursor_projects_dir is 2-step (CURSOR_CONFIG_DIR then $HOME/.cursor); the XDG_CONFIG_HOME/cursor CLI-config leg is not ported."

patterns-established:
  - "JSONL capture modules mirror capture_claude's per-file line-count cursor, malformed-line-still-captured discipline, and missing-directory zero-records short-circuit."
  - "Source-specific metadata (session_id, source_confidence, timestamp) sits as envelope sibling keys; payload is always the parsed line directly."
  - "SKILL.md Scope names all 5 live sources and Cursor's low-confidence / store.db-excluded caveat."

requirements-completed: []

coverage:
  - id: D-02
    description: "Lossless Codex capture: session_meta / event_msg / function_call; arguments stays a str; malformed mid-file kept"
    requirement: REQ-usage-metrics-raw-capture
    verification:
      - kind: unit
        ref: "tests.test_ai_kit_usage_metrics.TestCaptureCodex.test_rollout_verbatim_no_arguments_reparse_and_session_id"
        status: pass
      - kind: unit
        ref: "tests.test_ai_kit_usage_metrics.TestCaptureCodex.test_malformed_line_mid_file_captured_losslessly"
        status: pass
    human_judgment: false
  - id: D-02-cursor
    description: "Lossless Cursor capture of agent-transcripts JSONL; every envelope source_confidence=low and session_id from containing uuid dir"
    requirement: REQ-usage-metrics-raw-capture
    verification:
      - kind: unit
        ref: "tests.test_ai_kit_usage_metrics.TestCaptureCursor.test_transcripts_low_confidence_session_id_and_direct_payload"
        status: pass
      - kind: unit
        ref: "tests.test_ai_kit_usage_metrics.TestCaptureCursor.test_malformed_line_mid_file_captured_losslessly"
        status: pass
    human_judgment: false
  - id: T-05-10
    description: "Cursor store.db is out of scope; capture_cursor.py has no sqlite3 import or attribute access"
    requirement: REQ-usage-metrics-raw-capture
    verification:
      - kind: unit
        ref: "tests.test_ai_kit_usage_metrics.TestCaptureCursor.test_no_sqlite3_import_or_attribute_access"
        status: pass
      - kind: ast
        ref: "ast.parse walk Import/ImportFrom; sqlite3 absent (exit 0)"
        status: pass
      - kind: grep
        ref: "grep -c Amended 2026-09-10 REQUIREMENTS.md -> 1"
        status: pass
    human_judgment: false

completed: 2026-09-10
status: complete
---

# Phase 5 Plan 03: Codex + Cursor Raw Capture Summary

**Codex rollout JSONL and Cursor agent-transcripts JSONL plug into Wave 1's CAPTURE_SOURCES registry, completing the 5-entry v1 source set. Cursor stays low-confidence; store.db stays out.**

## Performance

- **Tasks:** 2
- **Files created:** 2 (plus this SUMMARY)
- **Files modified:** 5
- **Commits:** 2

## Accomplishments

- `capture_codex.capture` glob-walks `${CODEX_HOME:-$HOME/.codex}/sessions/**/rollout-*.jsonl` (recursive, covering the live `YYYY/MM/DD/` nesting). Per-file line-count cursor. Envelope is Wave 1's 8-key contract plus filename-derived `session_id`. `function_call.arguments` is left as a JSON-encoded string. Missing sessions dir is zero records. Malformed lines are captured (`parse_status="malformed"`, `raw_text` verbatim). A filename without a trailing UUID degrades `session_id` to `None`.
- `capture_cursor.capture` glob-walks `${CURSOR_CONFIG_DIR:-$HOME/.cursor}/projects/*/agent-transcripts/*/*.jsonl`. Every envelope carries `source_confidence="low"`, `session_id` from the containing uuid directory, and `timestamp=None`. `payload` is the parsed line directly (no Cursor-specific wrapper). `store.db` is never opened; the module has no `sqlite3` import (AST-checked). Optional `working_directory` on Shell tool_use does not crash capture.
- `CAPTURE_SOURCES` is now `claude` / `opencode` / `rtk` / `codex` / `cursor`. `SKILL.md` Scope names all five and Cursor's low-confidence / `store.db`-excluded caveat.
- `.planning/REQUIREMENTS.md` carries a dated 2026-09-10 amendment confirming Cursor `store.db` is out of scope for this milestone.
- Path helpers `codex_sessions_dir` and `cursor_projects_dir` take explicit `env: dict`. Cursor is 2-step only (`CURSOR_CONFIG_DIR` then `$HOME/.cursor`); the `XDG_CONFIG_HOME/cursor` CLI-config leg is not ported, stated in a code comment.

## Task Commits

1. **Task 1: Codex raw capture** — `a774d30` (feat)
2. **Task 2: Cursor raw capture** — `be0394a` (feat)

## Files Created/Modified

- `skills/ai-kit-usage-metrics/ai_kit_usage_metrics/capture_codex.py` — new
- `skills/ai-kit-usage-metrics/ai_kit_usage_metrics/capture_cursor.py` — new
- `skills/ai-kit-usage-metrics/ai_kit_usage_metrics/paths.py` — `codex_sessions_dir`, `cursor_projects_dir`
- `skills/ai-kit-usage-metrics/ai_kit_usage_metrics/cli.py` — CAPTURE_SOURCES entries
- `skills/ai-kit-usage-metrics/SKILL.md` — Wave 3 Scope
- `.planning/REQUIREMENTS.md` — dated store.db exclusion amendment
- `tests/test_ai_kit_usage_metrics.py` — TestCaptureCodex + TestCaptureCursor (+ path tests)

## Decisions Made

None beyond the plan. Followed Round 1 Cursor envelope-extension (not payload wrapper), Round 1 2-step cursor path, Round 2 8-key envelope + malformed-still-captured, Round 3 filename-derived Codex `session_id`.

## Deviations from Plan

None.

**Total deviations:** 0

## Issues Encountered

None. Tests were written first, failed on missing modules, then passed after implementation. All verification used scratch `CODEX_HOME` / `CURSOR_CONFIG_DIR` trees; the real `~/.codex/sessions/` and `~/.cursor/` trees were never listed or read.

## User Setup Required

None. Real `run` against live `~/.codex/sessions/` or `~/.cursor/projects/` is user-initiated later — every automated read used scratch env overrides.

## Next Phase Readiness

Ready for 05-04 (cwd-resolution state machine and mechanical decomposer against the full 5-source raw set). REQ-usage-metrics-raw-capture's Codex + Cursor portion is now implemented; refinement of those envelopes remains 05-04.

## Verification (captured)

```
$ python3 -m unittest tests.test_ai_kit_usage_metrics -v
Ran 42 tests in 0.011s
OK

$ python3 -c "import ast,sys; tree=ast.parse(open('skills/ai-kit-usage-metrics/ai_kit_usage_metrics/capture_cursor.py').read()); names=[n.name.split('.')[0] for node in ast.walk(tree) if isinstance(node,(ast.Import,ast.ImportFrom)) for n in getattr(node,'names',[])]; sys.exit(1 if 'sqlite3' in names else 0)"
# exit 0

$ grep -c "amended 2026-09-10\|Amended 2026-09-10" .planning/REQUIREMENTS.md
1

$ python3 -m py_compile skills/ai-kit-usage-metrics/ai-kit-usage-metrics.py skills/ai-kit-usage-metrics/ai_kit_usage_metrics/*.py
# exit 0

$ make lint
shellcheck tools/install.sh tests/test_install.sh
python3 -m py_compile tools/setup.py tools/status-line.py tools/statusline-doctor.py tools/hooks/*.py tools/config_doctor_*.py skills/ai-kit-usage-metrics/ai-kit-usage-metrics.py skills/ai-kit-usage-metrics/ai_kit_usage_metrics/*.py
```

## Self-Check: PASSED

- [x] Codex capture glob-walks recursive YYYY/MM/DD/rollout-*.jsonl
- [x] CODEX_HOME honored; missing sessions dir yields zero records
- [x] function_call.arguments remains a Python str, never a dict
- [x] Every envelope from one rollout file shares the filename-derived session_id
- [x] Cursor capture glob-walks projects/*/agent-transcripts/*/*.jsonl
- [x] Every Cursor envelope has source_confidence=low and session_id as top-level fields; payload is the parsed line
- [x] Optional working_directory does not crash capture
- [x] Malformed JSON and invalid UTF-8 degrade losslessly for both sources
- [x] AST scan finds zero sqlite3 imports/calls in capture_cursor.py
- [x] REQUIREMENTS.md dated amendment documents store.db exclusion
- [x] CAPTURE_SOURCES has exactly 5 entries
- [x] 42 tests, 0 failures; make lint py_compile clean
- [x] Production commits exist (`a774d30`, `be0394a`)

---
*Phase: 05-usage-metrics-dashboard*
*Completed: 2026-09-10*
