---
phase: 05-usage-metrics-dashboard
plan: 02
subsystem: usage-metrics
tags: [usage-metrics, opencode, rtk, sqlite, raw-capture]

requires:
  - "05-01 CaptureResult contract and CAPTURE_SOURCES registry"
provides:
  - "capture_opencode: session/message/part TEXT-PK tuple-cursor + storage/**/*.json"
  - "capture_rtk: history.db commands/parse_failures + tee/*.log with sha256 idempotency"
  - "CAPTURE_SOURCES grown to 3 entries (claude, opencode, rtk)"
affects: [05-usage-metrics-dashboard]

actuals:
  tokens: 70000
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "URI-quoted file:?mode=ro SQLite connections for every external live DB"
    - "Per-source cursor blob shape is free-form; raw_store stays shape-agnostic"
    - "(time_created, id) tuple cursor for TEXT PRIMARY KEY tables; plain id > for INTEGER PKs"
    - "Tee idempotency is (filename, sha256) membership so rewritten files re-capture"

key-files:
  created:
    - skills/ai-kit-usage-metrics/ai_kit_usage_metrics/capture_opencode.py
    - skills/ai-kit-usage-metrics/ai_kit_usage_metrics/capture_rtk.py
    - .planning/phases/05-usage-metrics-dashboard/05-02-SUMMARY.md
  modified:
    - skills/ai-kit-usage-metrics/ai_kit_usage_metrics/paths.py
    - skills/ai-kit-usage-metrics/ai_kit_usage_metrics/cli.py
    - skills/ai-kit-usage-metrics/SKILL.md
    - tests/test_ai_kit_usage_metrics.py

key-decisions:
  - "session rows have no data column; raw_text is json.dumps of the whole row dict (documented exception)."
  - "legacy_storage_file envelopes are captured losslessly but not refined this milestone (mirrors rtk tee/parse_failure)."
  - "rtk tee cursor stores {filename, sha256} pairs so a max_files rotation reuse is treated as a new capture."

patterns-established:
  - "New capture modules mirror capture_claude's CaptureResult + _empty_stats + absent-path short-circuit."
  - "Every external SQLite open uses urllib.parse.quote(path) inside file:?mode=ro."
  - "SKILL.md Scope names only the live sources this wave covers; Codex/Cursor stay explicitly out."

requirements-completed: []

coverage:
  - id: D-02
    description: "Lossless opencode capture: session/message/part plus nested storage JSON; malformed data kept with parse_status=malformed"
    requirement: REQ-usage-metrics-raw-capture
    verification:
      - kind: unit
        ref: "tests.test_ai_kit_usage_metrics.TestCaptureOpencode.test_session_message_part_lossless_and_verbatim"
        status: pass
      - kind: unit
        ref: "tests.test_ai_kit_usage_metrics.TestCaptureOpencode.test_nested_storage_json_captured_losslessly"
        status: pass
    human_judgment: false
  - id: D-06
    description: "rtk history.db + tee logs captured; OTEL explicitly absent from capture_rtk.py"
    requirement: REQ-usage-metrics-raw-capture
    verification:
      - kind: unit
        ref: "tests.test_ai_kit_usage_metrics.TestCaptureRtk.test_history_and_parse_failures_tagged"
        status: pass
      - kind: unit
        ref: "tests.test_ai_kit_usage_metrics.TestCaptureRtk.test_tee_logs_matching_and_nonmatching_filenames"
        status: pass
      - kind: grep
        ref: "grep -ic otel capture_rtk.py -> 0"
        status: pass
    human_judgment: false
  - id: T-05-06
    description: "Both new capture modules open external DBs exclusively via mode=ro URI"
    requirement: REQ-usage-metrics-raw-capture
    verification:
      - kind: grep
        ref: "grep -c mode=ro capture_opencode.py / capture_rtk.py -> 1 each"
        status: pass
      - kind: unit
        ref: "tests.test_ai_kit_usage_metrics.TestCaptureOpencode.test_absent_db_returns_zero_without_connecting"
        status: pass
    human_judgment: false

completed: 2026-09-10
status: complete
---

# Phase 5 Plan 02: opencode + rtk Raw Capture Summary

**opencode's session/message/part tables and storage tree, plus rtk's history.db and tee logs, plug into Wave 1's CAPTURE_SOURCES registry with the same CaptureResult envelope contract.**

## Performance

- **Tasks:** 2
- **Files created:** 2 (plus this SUMMARY)
- **Files modified:** 4
- **Commits:** 2

## Accomplishments

- `capture_opencode.capture` opens `opencode.db` only when present, via URI-quoted `file:?mode=ro`. Queries `session`, `message`, and `part` with independent `(time_created, id)` tuple cursors (TEXT PKs). Yields every part type losslessly; malformed `data` keeps verbatim `raw_text` and `parse_status="malformed"`. Recursive `storage/**/*.json` walk uses `glob(..., recursive=True)` and an `ingested_storage_files` membership cursor.
- `capture_rtk.capture` independently short-circuits absent `history.db` / `tee/` directory. Captures `commands` (`source_type="history"`) and `parse_failures` with integer `id > cursor` (live INTEGER PKs). Tee files carry `sha256`; same filename with different hash re-captures. Non-`^(\d+)_` filenames still captured with `captured_epoch=None`.
- `CAPTURE_SOURCES` is now `claude` / `opencode` / `rtk`. `SKILL.md` Scope names those three live sources and keeps Codex/Cursor explicitly out.
- Path helpers `opencode_db_path`, `opencode_storage_dir`, `rtk_history_db_path`, `rtk_tee_dir` all take explicit `env: dict`.

## Task Commits

1. **Task 1: opencode raw capture** — `2740323` (feat)
2. **Task 2: rtk raw capture** — `0362042` (feat)

## Files Created/Modified

- `skills/ai-kit-usage-metrics/ai_kit_usage_metrics/capture_opencode.py` — new
- `skills/ai-kit-usage-metrics/ai_kit_usage_metrics/capture_rtk.py` — new
- `skills/ai-kit-usage-metrics/ai_kit_usage_metrics/paths.py` — opencode + rtk source paths
- `skills/ai-kit-usage-metrics/ai_kit_usage_metrics/cli.py` — CAPTURE_SOURCES entries
- `skills/ai-kit-usage-metrics/SKILL.md` — Wave 2 Scope
- `tests/test_ai_kit_usage_metrics.py` — TestCaptureOpencode + TestCaptureRtk (+ path tests)

## Decisions Made

None beyond the plan. Followed Round 1 TEXT-PK tuple cursor, Round 3 recursive storage glob, Round 1 tee sha256 defensive check, and D-06's OTEL exclusion.

## Deviations from Plan

None.

**Total deviations:** 0

## Issues Encountered

None. Stale `__pycache__` briefly shadowed a mid-edit `capture_rtk` change during TDD; cleared and re-ran green.

## User Setup Required

None. Real `run` against live `~/.local/share/opencode/` or `~/.local/share/rtk/` is user-initiated later — every automated read used scratch `XDG_DATA_HOME`.

## Next Phase Readiness

Ready for 05-03 (Codex + Cursor capture). Wave 2 raw sources complete D-06's opencode+rtk portion of REQ-usage-metrics-raw-capture. Refinement of those envelopes remains 05-04.

## Verification (captured)

```
$ python3 -m unittest tests.test_ai_kit_usage_metrics -v
Ran 30 tests in 0.009s
OK

$ grep -c "mode=ro" skills/ai-kit-usage-metrics/ai_kit_usage_metrics/capture_opencode.py
1
$ grep -c "mode=ro" skills/ai-kit-usage-metrics/ai_kit_usage_metrics/capture_rtk.py
1

$ grep -ic "otel" skills/ai-kit-usage-metrics/ai_kit_usage_metrics/capture_rtk.py
0

$ grep -cE "FROM session|FROM message" skills/ai-kit-usage-metrics/ai_kit_usage_metrics/capture_opencode.py
3

$ make lint
shellcheck tools/install.sh tests/test_install.sh
python3 -m py_compile tools/setup.py tools/status-line.py tools/statusline-doctor.py tools/hooks/*.py tools/config_doctor_*.py skills/ai-kit-usage-metrics/ai-kit-usage-metrics.py skills/ai-kit-usage-metrics/ai_kit_usage_metrics/*.py
```

## Self-Check: PASSED

- [x] opencode capture queries session, message, AND part via URI-quoted mode=ro
- [x] Absent opencode.db never calls sqlite3.connect (mock-proven)
- [x] (time_created, id) tuple cursor does not re-yield same-timestamp rows
- [x] Nested storage/session_diff/*.json captured as legacy_storage_file
- [x] Malformed part data kept with parse_status=malformed and verbatim raw_text
- [x] rtk history + parse_failures + tee (matching and non-matching names) captured
- [x] Tee same-filename different-hash re-captured; same hash skipped
- [x] No otel/OTEL/telemetry string in capture_rtk.py
- [x] CAPTURE_SOURCES has 3 entries; Wave 1 dispatch loop unchanged
- [x] 30 tests, 0 failures; make lint py_compile clean
- [x] Production commits exist (`2740323`, `0362042`)

---
*Phase: 05-usage-metrics-dashboard*
*Completed: 2026-09-10*
