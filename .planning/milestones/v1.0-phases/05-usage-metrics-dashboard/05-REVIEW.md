---
phase: 05-usage-metrics-dashboard
reviewed: 2026-09-10T13:00:00Z
depth: standard
files_reviewed: 24
files_reviewed_list:
  - skills/ai-kit-usage-metrics/SKILL.md
  - skills/ai-kit-usage-metrics/ai-kit-usage-metrics.py
  - skills/ai-kit-usage-metrics/ai_kit_usage_metrics/__init__.py
  - skills/ai-kit-usage-metrics/ai_kit_usage_metrics/paths.py
  - skills/ai-kit-usage-metrics/ai_kit_usage_metrics/capture_claude.py
  - skills/ai-kit-usage-metrics/ai_kit_usage_metrics/capture_opencode.py
  - skills/ai-kit-usage-metrics/ai_kit_usage_metrics/capture_codex.py
  - skills/ai-kit-usage-metrics/ai_kit_usage_metrics/capture_cursor.py
  - skills/ai-kit-usage-metrics/ai_kit_usage_metrics/capture_rtk.py
  - skills/ai-kit-usage-metrics/ai_kit_usage_metrics/raw_store.py
  - skills/ai-kit-usage-metrics/ai_kit_usage_metrics/refined_store.py
  - skills/ai-kit-usage-metrics/ai_kit_usage_metrics/refiner.py
  - skills/ai-kit-usage-metrics/ai_kit_usage_metrics/decomposer.py
  - skills/ai-kit-usage-metrics/ai_kit_usage_metrics/cwd_state.py
  - skills/ai-kit-usage-metrics/ai_kit_usage_metrics/classify_loop.py
  - skills/ai-kit-usage-metrics/ai_kit_usage_metrics/family.py
  - skills/ai-kit-usage-metrics/ai_kit_usage_metrics/pricing.py
  - skills/ai-kit-usage-metrics/ai_kit_usage_metrics/dashboard.py
  - skills/ai-kit-usage-metrics/ai_kit_usage_metrics/cli.py
  - tests/test_ai_kit_usage_metrics.py
  - Makefile
  - .pre-commit-config.yaml
  - pyproject.toml
  - README.md
  - .planning/REQUIREMENTS.md
findings:
  critical: 0
  warning: 0
  info: 3
  total: 3
status: clean
---

# Phase 05: Code Review Report

**Reviewed:** 2026-09-10
**Depth:** standard
**Files Reviewed:** 24
**Status:** clean

## Summary

This is iteration 3 (final allowed iteration) of the fix/re-review loop, verifying commit
`1dc6f5a` which fixed the residual CR-01 finding from `05-REVIEW.iter3.md`. That finding was:
a `NULL time_created` row inserted into `opencode.db`'s `session`/`message`/`part` tables
*after* the per-table monotonic cursor had already advanced past a real (non-zero)
`time_created` value was permanently and silently dropped, because
`COALESCE(time_created, 0)` made such a row sort at "already-passed" position `0` forever.

**CR-01 is now fully fixed and verified correct and complete.** The fix restructures
`capture_opencode.py`'s pagination so the two row populations per table are tracked on
independent dimensions instead of sharing one monotonic sort key:

- `_CURSOR_SQL` now scopes to `time_created IS NOT NULL` and paginates only real-timestamp
  rows via the original `(time_created, id) > (cursor)` monotonic tuple — `NULL` rows never
  interact with this ordering at all, so they can no longer be "passed" by it.
- `_NULL_SQL` selects every `NULL`-`time_created` row unconditionally on every run; dedup is
  done in Python against a per-table `null_seen_ids` id set persisted in the cursor JSON
  (`_table_cursor`/`_set_table_cursor`), mirroring the existing `ingested_storage_files`
  id-set pattern already used by `_capture_storage`.

This eliminates ordering-dependence entirely: a `NULL` row is captured exactly once on
whichever run first observes it, regardless of whether it existed before the time-ordered
cursor advanced (iteration-1 test) or arrives after (iteration-2 regression test, now added).
I independently traced both code paths and reproduced both scenarios via the test suite:

- `test_null_time_created_rows_are_captured_not_dropped` (before-cursor-advance / all-NULL-
  from-start case) — passes, and the second run correctly yields zero records (dedup works).
- `test_null_time_created_row_arriving_after_cursor_advances_is_captured` (the exact
  ordering-after regression this iteration's fix targets) — passes: a real-timestamp row
  advances the cursor to a non-zero value, a subsequently-inserted `NULL` row is captured on
  the very next run with `stats["null_time_created"] == 1`, and a third run correctly yields
  zero records.

I ran the full suite (`uv run python3 -m unittest tests.test_ai_kit_usage_metrics -v`): all
103 tests pass, no failures, no skips. `uv run vulture skills/ai-kit-usage-metrics
--min-confidence 60` shows only the same pre-existing, unrelated 60%-confidence
`row_factory` flag in `dashboard.py` — no new dead code from this fix. `ast.parse` confirms
the modified file is syntactically valid.

**No regressions found.** The commit touches only `capture_opencode.py` and
`tests/test_ai_kit_usage_metrics.py`; no other reviewed file changed. I re-verified all
standing safety invariants directly against current file contents (not merely by absence of
diff):

- **No writes to real AI-CLI config trees:** `paths.py` (untouched) never reads
  `os.environ` directly — every path resolver takes an explicit `env: dict` parameter, so
  test/production paths are fully injectable and isolated.
- **Env-var-overridable paths:** confirmed intact via `TestPaths` suite (all passing),
  covering `CLAUDE_CONFIG_DIR`, `CODEX_HOME`, `CURSOR_CONFIG_DIR`, `XDG_DATA_HOME` overrides.
- **No XSS in `dashboard.py`:** untouched by this fix; still builds all DOM nodes via
  `document.createElement`/`.textContent` only, data payload is parsed via
  `JSON.parse(dataEl.textContent)` rather than any `innerHTML` assignment.
  `test_no_data_driven_innerhtml_assignment` passes.
- **Read-only `mode=ro` SQLite access:** `capture_opencode.py`, `capture_rtk.py`, and
  `refined_store.py` all still connect via `file:...?mode=ro` URIs; the fix's rewritten
  `_capture_table` uses the same pre-existing `conn` (opened via `_connect_readonly` in
  `capture()`) for both the new `_CURSOR_SQL` and `_NULL_SQL` queries — no new write path
  introduced.
- **`(session_id, turn_id)` dedup contract:** `refined_store.py` untouched; its documented
  invariant (dedup on `UNIQUE(raw_ref, step_index)`, with the docstring's `SELECT DISTINCT
  session_id, turn_id, ...` guidance for consumers) is unchanged.
- **`classify_loop.py` never auto-triggered:** `cli.py` untouched; `classify` remains its own
  explicit `elif cmd == "classify":` branch in `main()`, never invoked from `run`/`capture`.
- **Atomic/idempotent capture:** `raw_store.append_records` still dedups by `raw_ref` before
  writing (a defense-in-depth layer independent of the cursor logic — even a hypothetical
  cursor-tracking bug could not produce duplicate JSONL lines), and `write_cursor`/
  `_atomic_write_text` (untouched) still write via temp-file + `fsync` + `os.replace`. Cursor
  JSON corruption degrades gracefully to `{}` in `read_cursor`, which would only cause
  re-capture (harmless, since `append_records` dedups downstream) rather than a crash or
  silent write to the wrong location.

All previously-verified WR-01 through WR-04 fixes remain intact (none of their files —
`cli.py`, `refiner.py`, `pyproject.toml`, `family.py` — were touched by this iteration's
commit).

## Info

### IN-01: `null_seen_ids` grows unbounded per table

**File:** `skills/ai-kit-usage-metrics/ai_kit_usage_metrics/capture_opencode.py:87-99,203-222`

**Issue:** `null_seen_ids` is a per-table set of every `NULL`-`time_created` row id ever
observed, persisted verbatim (as a sorted list) in the cursor JSON and re-loaded in full on
every capture run. `_NULL_SQL` also does a full unconditional table scan for `NULL` rows on
every run (`SELECT * FROM {table} WHERE time_created IS NULL`), so both the cursor file size
and the per-run scan cost grow monotonically with total lifetime `NULL`-row volume for that
table, with no eviction. This mirrors the already-accepted `ingested_storage_files` pattern
in `_capture_storage`, so it is consistent with existing project conventions, and the
iteration-2 fix report already flagged this trade-off for human sign-off. Per this
iteration's task instructions this is intentionally not a blocking finding — flagged as Info
only, per explicit remit not to block on it.

**Fix:** If `NULL`-`time_created` rows are expected to be rare/transient in practice (e.g.
only in-flight opencode sessions before the upstream tool backfills a timestamp), no action
needed. If a table is observed to carry a persistently large `NULL` population, consider
capping `null_seen_ids` (e.g. an id high-water-mark scoped only to `NULL` rows, if `id` has a
usable total order) or documenting an expected upper bound in `SKILL.md`.

### IN-02 (carried forward, unfixed): `capture_rtk.py` tee-cursor dedup assumes well-formed cursor entries

**File:** `skills/ai-kit-usage-metrics/ai_kit_usage_metrics/capture_rtk.py:136-137`

**Issue:** Unchanged since iteration 1:

```python
ingested = list(cursor.get("ingested_tee_files") or [])
seen = {(entry["filename"], entry["sha256"]) for entry in ingested if isinstance(entry, dict)}
```

A `cursors/rtk.json` entry missing `"filename"` or `"sha256"` raises `KeyError`, which —
thanks to WR-01's fix — now only aborts the `rtk` source's capture for that run (isolated
from other sources) rather than the whole `cmd_capture` loop, but the underlying `rtk`
source itself still silently stalls on that one malformed entry indefinitely with no
diagnostic beyond the generic `capture[rtk] failed: 'filename'` stderr line. Out of this
iteration's fix scope (Critical/Warning only); carried forward unchanged.

**Fix:** Use `.get()` and skip malformed entries defensively:
`{(e.get("filename"), e.get("sha256")) for e in ingested if isinstance(e, dict) and e.get("filename") and e.get("sha256")}`.

### IN-03 (carried forward, unfixed): `.planning/REQUIREMENTS.md` still marks Phase 5's requirements as pending

**File:** `.planning/REQUIREMENTS.md:41-44,79-82`

**Issue:** Unchanged since iteration 1: `REQ-usage-metrics-raw-capture`,
`REQ-usage-metrics-refinement-pipeline`, `REQ-usage-metrics-dashboard-ui`, and
`REQ-usage-metrics-classification-refinement-loop` are still checkbox `[ ]` with a `Pending`
status in the traceability table, despite Phase 05 shipping six plans (`05-01` through
`05-06`, each with a `SUMMARY.md`) implementing this scope. Out of this iteration's fix scope;
carried forward unchanged.

**Fix:** Confirm whether flipping these to `[x]`/`Done` is intentionally deferred to
milestone-close, or reconcile the tracker now.

---

_Reviewed: 2026-09-10_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
