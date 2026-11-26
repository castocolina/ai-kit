---
phase: 40-resilient-review-sized-by-jev
plan: 01
subsystem: ai-kit-spec-review (round log, partial merge)
tags: [review, round-log, merge-reports, reasons, partial]
requires: []
provides:
  - "error_classifier.REASONS gains replaced, never_resolved, no_lane_left, ping_timeout (13 keys, typed only there as constants)"
  - "ai_kit_spec/review_log.py: append-only round log (lanes.jsonl), round states, review outcome, judged line, merge recording"
  - "merge-reports --lane-log <file> --round <N> --cwd <root>: merges the surviving lanes, prints Judged by in roster order, Approved (partial) or not reviewed; no-log path unchanged"
affects: [40-02, 40-03, 40-08, 40-09]
key-files:
  created:
    - skills/ai-kit-spec-review/ai_kit_spec/review_log.py
    - tests/test_review_log.py
  modified:
    - skills/ai-kit-spec-review/ai_kit_spec/error_classifier.py
    - skills/ai-kit-spec-review/ai_kit_spec/review_reports.py
    - skills/ai-kit-spec-review/ai_kit_spec/cli.py
    - tests/test_ai_kit_spec.py
    - Makefile
    - .pre-commit-config.yaml
decisions:
  - "record_merge leaves a readable key alone when its round-N last state is never_resolved, as it does for failed and replaced (the plan names only failed/replaced; never_resolved is the same kind of recorded failure)"
metrics:
  tasks: 3
  commits: 3
---

# Phase 40 Plan 01: round log and partial merge Summary

The closed reason list holds the four review-level reasons, `ai_kit_spec/review_log.py` records each lane's state per round in an
append-only JSON-lines file (one `os.write` per event, mode 0o600), and `merge-reports --lane-log <file> --round <N> --cwd <root>`
merges only the lanes recorded `judged`, prints `Judged by: <keys>[; not judged: <key> (<reason>[, by <key>][, round <r>])]` in the
owner's review order, reads `### Status: Approved (partial)` when any lane of any round did not judge, prints
`### Status: Failure — not reviewed: ...` with exit 1 when nothing judged, and exits 2 when a same-round remerge omits a lane already
judged. A failed or replaced lane is never turned `judged` by a readable (possibly stale) report. Without `--lane-log` the merge is
byte-identical to before (the old fail-closed tests are unchanged and green).

## Commits

| Task | Commit | Subject |
|------|--------|---------|
| 1 | 15ee789 | feat(40-01): record lane states per round and merge a partial review |
| 2 | b6258fd | test(40-01): pin the round log and the partial outcome |
| 3 | 316574a | test(40-01): add log-based twins of the fail-closed merge tests |

Cross-AI lanes (pi, router-env/my-coding), one per task from the start, each AIKIT-XAI `status=ok attempts=1`: Task 1 460 s,
Task 2 182 s, Task 3 113 s. No fix-up lane was needed.

## Verification (chunk executor, own runs)

- Acceptance: REASONS constants 4, review_log functions 6, `judged_line: str | None = None` 1, `"--lane-log"` 1, the no-log
  `print(f"### Status: Failure — {` line 1; `tests/test_review_log.py` 15 tests; Makefile 1 and hook config 2 listings;
  `tests/test_ai_kit_spec.py` 688 -> 703 tests (N + 15), the old `### Status: Failure — a, b` assertion kept (1).
- `tests.test_ai_kit_spec` 703 ok, `tests.test_review_log` 15 ok, `tests.test_ai_kit_spec_runtimes_table` 63 ok,
  `tests.test_quota_policy_text` 20 ok, `tests.test_gate_scope` 62 ok, `tests.test_arch` 118 ok,
  `tests.test_arch_hardcoded_models` 23 ok; `tests/fixtures/no_hardcoded_models_baseline.json` unchanged; no line over 100.
- Gates after the plan: unit + arch groups under the watchdog `194/194 modules passed` (peak 8 runner processes, not killed);
  `make ruff`, `make pyright`, `make vulture`, `make pylint`, `make check-dogfood` exit 0 each; the commit-deferred
  `tests.test_ai_kit_gsd_curated_config_matrix` 35 tests ok (149.9 s, under the watchdog).

## Deviations

- `record_merge` also skips a readable key whose last state is `never_resolved` (plan silent on that state; conservative).
- The lane state names `replaced`/`never_resolved` appear as state literals in review_log.py (`LANE_STATES`, the record shapes), as
  the plan text writes them; the four reason strings are typed as reasons only in error_classifier.py.
