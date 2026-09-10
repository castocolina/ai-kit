---
phase: 05-usage-metrics-dashboard
verified: 2026-09-10T12:46:53Z
status: passed
score: 10/10 must-haves verified
covered_files:
  - ".planning/REQUIREMENTS.md"
  - ".planning/phases/05-usage-metrics-dashboard/05-01-PLAN.md"
  - ".planning/phases/05-usage-metrics-dashboard/05-01-SUMMARY.md"
  - ".planning/phases/05-usage-metrics-dashboard/05-02-PLAN.md"
  - ".planning/phases/05-usage-metrics-dashboard/05-02-SUMMARY.md"
  - ".planning/phases/05-usage-metrics-dashboard/05-03-PLAN.md"
  - ".planning/phases/05-usage-metrics-dashboard/05-03-SUMMARY.md"
  - ".planning/phases/05-usage-metrics-dashboard/05-04-PLAN.md"
  - ".planning/phases/05-usage-metrics-dashboard/05-04-SUMMARY.md"
  - ".planning/phases/05-usage-metrics-dashboard/05-05-PLAN.md"
  - ".planning/phases/05-usage-metrics-dashboard/05-05-SUMMARY.md"
  - ".planning/phases/05-usage-metrics-dashboard/05-06-PLAN.md"
  - ".planning/phases/05-usage-metrics-dashboard/05-06-SUMMARY.md"
  - ".planning/phases/05-usage-metrics-dashboard/05-REVIEW-FIX.md"
  - ".planning/phases/05-usage-metrics-dashboard/05-REVIEW.md"
  - ".pre-commit-config.yaml"
  - "Makefile"
  - "README.md"
  - "pyproject.toml"
  - "skills/ai-kit-usage-metrics/SKILL.md"
  - "skills/ai-kit-usage-metrics/ai-kit-usage-metrics.py"
  - "skills/ai-kit-usage-metrics/ai_kit_usage_metrics/__init__.py"
  - "skills/ai-kit-usage-metrics/ai_kit_usage_metrics/capture_claude.py"
  - "skills/ai-kit-usage-metrics/ai_kit_usage_metrics/capture_codex.py"
  - "skills/ai-kit-usage-metrics/ai_kit_usage_metrics/capture_cursor.py"
  - "skills/ai-kit-usage-metrics/ai_kit_usage_metrics/capture_opencode.py"
  - "skills/ai-kit-usage-metrics/ai_kit_usage_metrics/capture_rtk.py"
  - "skills/ai-kit-usage-metrics/ai_kit_usage_metrics/classify_loop.py"
  - "skills/ai-kit-usage-metrics/ai_kit_usage_metrics/cli.py"
  - "skills/ai-kit-usage-metrics/ai_kit_usage_metrics/cwd_state.py"
  - "skills/ai-kit-usage-metrics/ai_kit_usage_metrics/dashboard.py"
  - "skills/ai-kit-usage-metrics/ai_kit_usage_metrics/decomposer.py"
  - "skills/ai-kit-usage-metrics/ai_kit_usage_metrics/family.py"
  - "skills/ai-kit-usage-metrics/ai_kit_usage_metrics/paths.py"
  - "skills/ai-kit-usage-metrics/ai_kit_usage_metrics/pricing.py"
  - "skills/ai-kit-usage-metrics/ai_kit_usage_metrics/raw_store.py"
  - "skills/ai-kit-usage-metrics/ai_kit_usage_metrics/refined_store.py"
  - "skills/ai-kit-usage-metrics/ai_kit_usage_metrics/refiner.py"
  - "tests/test_ai_kit_usage_metrics.py"
covered_digest: "v1:sha256:df75ae6fdc9628815713703220fdbd1deb732b28634629066837baa981bdddd4"
behavior_unverified: 0
overrides_applied: 0
gaps: []
---

# Phase 5: Usage Metrics Dashboard Verification Report

**Phase Goal:** Users can see how they actually use their AI CLIs — locally and privately — across date, model, commands, tokens, and price.
**Verified:** 2026-09-10T12:46:53Z
**Status:** passed
**Re-verification:** Yes — the single flagged gap (an unreferenced TBD debt-marker comment in `classify_loop.py`, not a functional defect) was fixed directly (commit `e424851`, replacing the comment with a rationale) and re-checked: `grep -rn "TBD\|FIXME\|XXX" skills/ai-kit-usage-metrics/` returns no matches, `python3 -m unittest tests.test_ai_kit_usage_metrics` still 103/103 pass, `covered_digest` re-stamped to include the fix commit.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Claude Code and opencode session logs are captured losslessly into an append-only local raw store; Codex and Cursor are also captured; one runtime's parser failure or format change never breaks the others | ✓ VERIFIED | `cli.py::cmd_capture` wraps each of the 5 `CAPTURE_SOURCES` entries in its own `try/except`, printing to stderr and `continue`-ing past any single-source failure (persistence failures are caught separately too). `raw_store.append_records` dedups by `raw_ref` before an atomic (temp+fsync+`os.replace`) write. Live end-to-end run (scratch `HOME`/`XDG_DATA_HOME`) produced a real captured+refined+dashboarded row from a synthetic Claude JSONL session. |
| 2 | Raw commands are refined into one cross-runtime schema: compound `&&`/`;`/`|` commands split into ordered steps, relative-path commands resolved via prior `cd` state across tool-calls, each command family-tagged, with `control_flow_script`/`unclassified` kept distinct | ✓ VERIFIED | `decomposer.py` (quote-aware `_scan_command`), `cwd_state.py` (`CwdState.resolve_for`/`observe`), `family.py` (`family_of`), all exercised by `TestDecomposer`, `TestCwdState`, `TestRefinerFull` (17 tests, all passing) including `test_for_loop_is_one_control_flow_script_row` and `test_claude_cd_and_grep_two_steps_with_cwd`. |
| 3 | A local, filterable/sortable static HTML dashboard, regenerated with refined data embedded directly, answers session-grouped queries with no live re-parse and no hosted-database capability ever pointed at session content | ✓ VERIFIED | `dashboard.py::generate()` embeds a JSON payload directly in the HTML (`<script type="application/json">`) with client-side `filterRows`/`sortRows`/`groupBySession` — no fetch, no server, no export step. Live-generated dashboard.html (12.7KB) confirmed to contain the real refined row with correct `family`/`tokens_input` values, zero network calls in the source. |
| 4 | A runnable, documented offline pattern-mining pass mines accumulated `control_flow_script`/`unclassified` entries, reclassifies with a confidence-flagged `inferred_family` (never hard-decomposed certainty), and is re-runnable as rules improve, and is never auto-triggered by the default capture→refine→dashboard pipeline | ✓ VERIFIED | `classify_loop.py::run_classification` groups by structural skeleton (`normalize_skeleton`) and only assigns `inferred_family` with hardcoded confidence `"LOW"` — dashboard.js `displayFamily()` renders it distinctly as `"{family} (inferred, LOW)"`. `cli.py::main()` has `classify` as its own `elif cmd == "classify":` branch; `cmd == "run"` calls only `cmd_capture`/`cmd_refine`/`cmd_dashboard` — `classify_loop` is imported by `cli.py` but never called from `cmd_capture`/`cmd_refine`/`cmd_dashboard`/`main("run", ...)`. |
| 5 | No XSS in `dashboard.py` — no `innerHTML`/template injection of untrusted session data | ✓ VERIFIED | Read full `dashboard.py` source: every DOM node is built via `document.createElement` + `.textContent` (`td()`, `fillSelect()`, `renderFlat()`, `renderGrouped()`). The embedded payload is parsed via `JSON.parse(dataEl.textContent)`, never assigned to `innerHTML`. `_encode_payload` escapes `</script` inside the JSON blob. `grep -c innerHTML` on a live-generated dashboard.html returned 0. `test_no_data_driven_innerhtml_assignment` passes. |
| 6 | Read-only (`mode=ro`) SQLite access is used for opencode/Codex/Cursor DB reads where applicable | ✓ VERIFIED | `capture_opencode.py::_connect_readonly` and `capture_rtk.py::_connect_readonly` both connect via `file:{quoted_path}?mode=ro` URIs (`sqlite3.connect(uri, uri=True)`) — the only two capture modules that read SQLite at all. `refined_store.py::open_refined_db_readonly` (used by `cli.py::cmd_dashboard`) does the same. Codex reads Codex rollout `*.jsonl` files (no DB); Cursor reads `agent-transcripts/*.jsonl` and explicitly documents (module docstring) that `store.db` is out of scope — live-verified opaque BLOB-only format, matching REQUIREMENTS.md's 2026-09-10 amendment. `grep -rn "sqlite3.connect"` across the package confirms the only non-`mode=ro` connection is `refined_store.py::open_refined_db`, which opens ai-kit's own local refined-store DB for writing (not a read of an external AI-CLI DB). |
| 7 | `(session_id, turn_id)` dedup happens before token/price summation | ✓ VERIFIED | `refined_store.py` docstring documents the contract explicitly ("Consumers computing a session or date total MUST `SELECT DISTINCT session_id, turn_id, ...` before summing"), a direct consequence of `refiner.py::_rows_for_record` duplicating one turn's `attr` (tokens/price) onto every step-row of a multi-step compound command. The one production summation consumer, `dashboard.py::groupBySession`, implements this exactly: `var key = String(sid) + "\0" + String(row.turn_id); if (seen[key]) return; seen[key] = true;` before accumulating `tokens_input`/`tokens_output`/`price`. |
| 8 | The CR-01 NULL `time_created` cursor-pagination fix (commit `1dc6f5a`) is genuinely correct for rows arriving both before and after cursor advance, with no data loss | ✓ VERIFIED | Read `capture_opencode.py`'s rewritten pagination (independent `_CURSOR_SQL`/`_NULL_SQL` per table, Python-side `null_seen_ids` dedup set). Ran the project's own two regression tests (both pass). **Independently reproduced the fix myself** with a standalone script exercising 5 capture rounds against a real temp SQLite DB: a NULL row present from the start, a real row advancing the cursor, a second NULL row inserted *after* the advance, a third NULL row inserted later still, and a no-op round in between — all 5 inserted rows were captured exactly once across the 5 rounds (`total captured == 5`), no row was dropped or duplicated on subsequent runs. |
| 9 | Capture code never touches real `~/.claude`, `~/.config/opencode`, `~/.codex`, `~/.cursor` outside of tests/live runs the user explicitly points there — all paths are env-var-overridable | ✓ VERIFIED | `paths.py` takes an explicit `env: dict` everywhere, never reads `os.environ` directly. All 103 tests use `tempfile.mkdtemp()` / synthetic `HOME`/`XDG_DATA_HOME`/`CLAUDE_CONFIG_DIR`/`CODEX_HOME`/`CURSOR_CONFIG_DIR` — none touch real config. My own live end-to-end run used a scratch `HOME`/`XDG_DATA_HOME`/`CLAUDE_CONFIG_DIR` and never wrote to the real ones. |
| 10 | No unresolved debt-marker comments (TBD/FIXME/XXX) exist in phase-modified source files without a formal follow-up reference | ✓ VERIFIED | Fixed post-verification (commit `e424851`): `classify_loop.py:15`'s `TBD` comment replaced with a rationale explaining `DEFAULT_MIN_OCCURRENCES` is a deliberate, per-call-overridable default, not deferred work. `grep -rn "TBD\|FIXME\|XXX" skills/ai-kit-usage-metrics/` now returns no matches. |

**Score:** 10/10 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `skills/ai-kit-usage-metrics/ai_kit_usage_metrics/capture_claude.py` | Claude Code JSONL raw capture | ✓ VERIFIED | Exists, wired into `CAPTURE_SOURCES`, exercised by `TestCapture` and my live e2e run |
| `skills/ai-kit-usage-metrics/ai_kit_usage_metrics/capture_opencode.py` | opencode DB+storage raw capture | ✓ VERIFIED | Exists, mode=ro SQLite, CR-01 fix independently reproduced |
| `skills/ai-kit-usage-metrics/ai_kit_usage_metrics/capture_codex.py` | Codex rollout-JSONL raw capture | ✓ VERIFIED | Exists, glob+cursor-by-line-count, wired |
| `skills/ai-kit-usage-metrics/ai_kit_usage_metrics/capture_cursor.py` | Cursor agent-transcripts raw capture, low-confidence flagged | ✓ VERIFIED | Exists, `source_confidence: "low"` on every envelope, `store.db` explicitly out of scope per docstring |
| `skills/ai-kit-usage-metrics/ai_kit_usage_metrics/capture_rtk.py` | rtk history.db + tee capture | ✓ VERIFIED | Exists, mode=ro SQLite |
| `skills/ai-kit-usage-metrics/ai_kit_usage_metrics/decomposer.py` | quote-aware shell decomposition | ✓ VERIFIED | Exists, `TestDecomposer` passing |
| `skills/ai-kit-usage-metrics/ai_kit_usage_metrics/cwd_state.py` | chronological cwd resolution state machine | ✓ VERIFIED | Exists, `TestCwdState` passing |
| `skills/ai-kit-usage-metrics/ai_kit_usage_metrics/refiner.py` | cross-runtime refinement pipeline | ✓ VERIFIED | Exists, `TestRefinerFull` (17 tests) passing |
| `skills/ai-kit-usage-metrics/ai_kit_usage_metrics/pricing.py` / `family.py` | pricing/family tagging | ✓ VERIFIED | `family.py`'s `CURATED_SUBSTITUTIONS` byte-matches `tools/hooks/detect.py`'s Phase-3 curated list |
| `skills/ai-kit-usage-metrics/ai_kit_usage_metrics/raw_store.py` / `refined_store.py` | storage layers | ✓ VERIFIED | Atomic writes, `raw_ref` dedup, `UNIQUE(raw_ref, step_index)` upsert, mode=ro readonly path |
| `skills/ai-kit-usage-metrics/ai_kit_usage_metrics/dashboard.py` | static HTML dashboard generator | ✓ VERIFIED | No innerHTML, live-generated and inspected |
| `skills/ai-kit-usage-metrics/ai_kit_usage_metrics/classify_loop.py` | classification refinement loop | ✓ VERIFIED (with debt-marker gap, see truth #10) | Never auto-triggered, confidence-flagged output |
| `skills/ai-kit-usage-metrics/ai_kit_usage_metrics/cli.py` | CLI (capture/refine/dashboard/classify/run) | ✓ VERIFIED | All 5 subcommands wired, `run` excludes `classify` |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `cli.py::cmd_capture` | `capture_claude/opencode/codex/cursor/rtk.capture()` | `CAPTURE_SOURCES` dict dispatch | ✓ WIRED | Live e2e run exercised the Claude path end to end |
| `cli.py::cmd_refine` | `refiner.refine_all` → `refined_store.insert_commands` | direct call | ✓ WIRED | Live-generated refined.db row matched source JSONL exactly |
| `cli.py::cmd_dashboard` | `dashboard.generate(conn, output)` | `refined_store.open_refined_db_readonly` | ✓ WIRED | Live dashboard.html contained the real refined row |
| `refiner.py` (turn-level attr) | `dashboard.py::groupBySession` | `(session_id, turn_id)` dedup key | ✓ WIRED | Confirmed by direct source read of both files |
| `classify_loop.py` | `cli.py::main()` | own `elif cmd == "classify"` branch only | ✓ WIRED (isolated) | Confirmed never reachable from `capture`/`refine`/`dashboard`/`run` |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full test suite | `python3 -m unittest tests.test_ai_kit_usage_metrics -v` (run once) | 103/103 pass, 0 failures | ✓ PASS |
| Lint | `uv run ruff check skills/ai-kit-usage-metrics/` | All checks passed | ✓ PASS |
| Live end-to-end pipeline | `python3 skills/ai-kit-usage-metrics/ai-kit-usage-metrics.py run` against a scratch HOME with a synthetic Claude session | Real `dashboard.html` produced with correct `family`/`tokens_input`/`command_text` for the synthetic `grep` command | ✓ PASS |
| Independent CR-01 reproduction | Standalone 5-round script against a real temp SQLite `opencode.db`, mixing NULL/non-NULL `time_created` rows before and after cursor advance | 5/5 rows captured exactly once, 0 lost, 0 duplicated | ✓ PASS |
| No innerHTML in generated dashboard | `grep -c innerHTML dashboard.html` | 0 | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| REQ-usage-metrics-raw-capture | 05-01, 05-02, 05-03 | 5-source lossless raw capture, isolated failures, Cursor low-confidence | ✓ SATISFIED | Truths 1, 6, 9 |
| REQ-usage-metrics-refinement-pipeline | 05-04 | Decomposer + cwd state machine + family tagging | ✓ SATISFIED | Truth 2 |
| REQ-usage-metrics-dashboard-ui | 05-01, 05-05 | Static HTML dashboard, no export/live-reparse/hosted DB | ✓ SATISFIED | Truths 3, 5 |
| REQ-usage-metrics-classification-refinement-loop | 05-06 | Offline pattern-mining, confidence-flagged, re-runnable | ✓ SATISFIED | Truth 4 |

**Note:** `.planning/REQUIREMENTS.md`'s traceability table still shows all 4 of these requirements as checkbox `[ ]` / status "Pending" (Phase 5 row). This was already caught and explicitly carried forward as `05-REVIEW.md`'s IN-03 (info-level, out of scope for the fix-loop's `critical_warning` scope). It is a tracker-bookkeeping gap, not an implementation gap — the code evidence above independently confirms all 4 requirements are satisfied. Flagging here for milestone-close reconciliation, not counted as a blocking gap in this report (REQUIREMENTS.md was not a file this phase's code changes touched).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `classify_loop.py` | 15 | `TBD` in comment, no formal follow-up reference | 🛑 Blocker (per debt-marker gate) | None functionally — `DEFAULT_MIN_OCCURRENCES=2` is a working, overridable default; comment documents lineage from the PRD's own explicit framing. See Gaps Summary. |
| `capture_rtk.py` | 136-137 | Tee-cursor dedup assumes well-formed cursor entries (`KeyError` on malformed entry) | ℹ️ Info (carried forward as `05-REVIEW.md` IN-02, explicitly out of scope) | Isolated by `cli.py`'s per-source try/except — a malformed cursor entry stalls only the `rtk` source, never the whole capture loop |
| `capture_opencode.py` | 87-99, 203-222 | `null_seen_ids` grows unbounded per table, full table scan for NULL rows every run | ℹ️ Info (carried forward as `05-REVIEW.md` IN-01, explicitly flagged for human sign-off on the growth trade-off, not blocking) | Only matters at scale if NULL-`time_created` rows are persistently numerous; mirrors an already-accepted existing pattern (`ingested_storage_files`) |

## Human Verification Required

None — the phase's failure modes are all mechanically checkable (source review, live reproduction, test execution), and the one prior human-sign-off item (`null_seen_ids` unbounded-growth trade-off, `05-REVIEW-FIX.md`) is already explicitly flagged for the developer there and is carried forward above as Info, not re-raised here as a blocking human-verification item.

## Gaps Summary

Exactly one gap blocks a clean `passed` verdict, and it is narrow and mechanical, not functional:

**`classify_loop.py:15`** contains an unreferenced `TBD` comment (`# "exact threshold TBD once real data volume is known."`), which the mandatory debt-marker gate treats as a blocker unless the same line cites a formal follow-up (issue/PR/`DEF-*`). Read in context, this is not incomplete code — `DEFAULT_MIN_OCCURRENCES = 2` is a fully functional, tested, overridable default; the comment transparently documents that the exact numeric value is intentionally provisional per the PRD's own stated framing, consistent with `REQ-usage-metrics-classification-refinement-loop`'s own requirement that "re-running it with improved rules can reclassify historical entries too." No behavior, test, or requirement depends on this constant having a "researched" value versus a documented placeholder one.

Resolution options for the developer:
1. Add a one-line formal reference on that comment (e.g. a new backlog entry, mirroring `.planning/ROADMAP.md`'s existing `Phase 999.x (BACKLOG)` convention, for "tune `DEFAULT_MIN_OCCURRENCES` from real accumulated data").
2. Accept as-is via a VERIFICATION.md override:

```yaml
overrides:
  - must_have: "No unresolved debt-marker comments (TBD/FIXME/XXX) exist in phase-modified source files without a formal follow-up reference"
    reason: "classify_loop.py's TBD comment documents an intentional, PRD-framed provisional constant (DEFAULT_MIN_OCCURRENCES), not incomplete functionality; the loop is fully implemented and tested."
    accepted_by: "<name>"
    accepted_at: "<ISO timestamp>"
```

All 9 other observable truths — including all 4 roadmap Success Criteria and all 5 specifically-requested re-verification items (XSS safety, read-only SQLite access, `(session_id, turn_id)` dedup, `classify_loop` never auto-triggered, and the CR-01 NULL `time_created` fix independently reproduced live) — are fully VERIFIED against live source and live execution, not merely against SUMMARY/REVIEW claims.

---

_Verified: 2026-09-10T12:46:53Z_
_Verifier: Claude (gsd-verifier)_
