---
phase: 05-usage-metrics-dashboard
fixed_at: 2026-09-10T12:34:23Z
review_path: .planning/phases/05-usage-metrics-dashboard/05-REVIEW.md
iteration: 2
findings_in_scope: 1
fixed: 1
skipped: 0
status: all_fixed
---

# Phase 05: Code Review Fix Report

**Fixed at:** 2026-09-10T12:34:23Z
**Source review:** .planning/phases/05-usage-metrics-dashboard/05-REVIEW.md
**Iteration:** 2

**Summary:**
- Findings in scope: 1 (fix_scope=critical_warning; REVIEW.md iteration 2 has 1 critical, 0 warning, 2 info findings — the 2 info findings, IN-01 and IN-02, are out of scope both by `fix_scope` and by explicit instruction and were skipped/not attempted)
- Fixed: 1
- Skipped: 0

## Fixed Issues

### CR-01 (residual): `NULL time_created` rows arriving after cursor advancement are still silently and permanently dropped

**Files modified:** `skills/ai-kit-usage-metrics/ai_kit_usage_metrics/capture_opencode.py`, `tests/test_ai_kit_usage_metrics.py`
**Commit:** 1dc6f5a
**Applied fix:** The iteration-1 fix (`COALESCE(time_created, 0)`) only
solved the case where a `NULL`-`time_created` row is seen *before* the
per-table cursor has advanced past a real timestamp; once advanced, a
later-arriving `NULL` row matched neither branch of the monotonic
`WHERE` clause and was silently dropped forever — same defect, narrower
trigger, as documented in REVIEW.md's reproduction.

Rewrote the pagination scheme (per REVIEW.md's suggested option 1,
"track NULL-time_created rows via a separate id-only seen set") so the
two row populations per table are paginated independently rather than
sharing one monotonic ordering key:

- `_CURSOR_SQL` now selects only rows with a real (non-`NULL`)
  `time_created`, via the same `time_created > ? OR (time_created = ?
  AND id > ?)` monotonic cursor as before, but scoped with `time_created
  IS NOT NULL` so `NULL` rows never interact with this ordering at all.
- A new `_NULL_SQL` unconditionally selects every `NULL`-`time_created`
  row each run; `_table_cursor`/`_set_table_cursor` persist a
  `null_seen_ids` set per table in the cursor JSON (mirroring the
  existing `ingested_storage_files` id-set pattern used by
  `_capture_storage`), and `_capture_table` dedups against it in Python.
  A row is captured exactly once regardless of whether it existed before
  or arrives after the time-ordered cursor has advanced past any
  timestamp.
- `stats["null_time_created"]` is now only incremented at the point a
  `NULL` row is actually captured (which, with this scheme, happens for
  every `NULL` row exactly once — there is no longer an "excluded and
  invisible" branch, since the id-set approach captures every previously
  unseen `NULL` row unconditionally rather than excluding any).
- Read-only DB access (`_connect_readonly`'s `mode=ro` URI), the
  per-table independent-cursor invariant, and the absent-DB
  zero-records-not-an-error behavior are all unchanged.

Verification performed beyond the standard 3-tier check:
- `python3 -c "import ast; ast.parse(...)"` passed on both modified files.
- Reproduced REVIEW.md's exact failure scenario directly against
  `capture_opencode.capture` in an ad hoc script: a non-`NULL` row
  advances the cursor past `time_created=1000`, a `NULL`-`time_created`
  row inserted afterward is now captured on the very next run (was
  previously silently dropped forever), and is not re-yielded on a
  subsequent run.
- Added a new permanent regression test,
  `test_null_time_created_row_arriving_after_cursor_advances_is_captured`,
  covering this exact ordering-after case (the existing
  `test_null_time_created_rows_are_captured_not_dropped` only covered the
  ordering-before/all-`NULL`-from-start case and would not have caught
  this regression).
- Ran the full suite: `python3 -m unittest tests.test_ai_kit_usage_metrics`
  — 103 tests pass (102 pre-existing + 1 new).
- Ran `uv run vulture skills/ai-kit-usage-metrics --min-confidence 60` —
  only the same pre-existing, unrelated 60%-confidence `row_factory`
  flag in `dashboard.py` remains; no new dead code introduced.

This finding involves a logic/algorithm change (the cursor-pagination
scheme), not just a syntactic patch. Syntax checks and the full test
suite (including a new targeted regression test and a manual
reproduction of the exact failure case from REVIEW.md) both pass, but
per the fixer's verification-strategy guidance for logic findings, this
is flagged as `fixed: requires human verification` — a developer should
confirm the `null_seen_ids` growth-over-time trade-off (an unbounded
per-table id list, mirroring the existing `ingested_storage_files`
pattern) is acceptable for this deployment's expected `NULL`-row volume
before considering this fully closed.

## Skipped Issues

None in scope — IN-01 and IN-02 were explicitly excluded from this
fix run's scope (both by `fix_scope=critical_warning`, which only
includes Critical/Warning findings, and by explicit instruction in this
run's task) and were not attempted. They remain carried forward
unchanged in REVIEW.md for a future iteration if promoted into scope.

---

_Fixed: 2026-09-10T12:34:23Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 2_
