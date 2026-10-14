---
phase: 16
review: 16-REVIEW.md
titles: json
findings:
  - id: WR-01
    severity: warning
    disposition: open
    title: "Unsorted import block fails the gated ruff hook"
  - id: WR-02
    severity: warning
    disposition: open
    title: "Two new `_FIELD_TYPES` comment lines exceed the 100-column ruff limit"
  - id: WR-03
    severity: warning
    disposition: open
    title: "Nested `if` in `_apply_runtime_meta` (SIM102)"
  - id: WR-04
    severity: warning
    disposition: open
    title: "Nested `if` and if/else block flagged in `model_ranker.py` (SIM102/SIM108)"
  - id: IN-01
    severity: info
    disposition: open
    title: "Awkward `json.dump` call formatting in a new test helper"
open: 5
total: 5
recorded: 2026-10-14T15:50:17.994Z
---

# Phase 16: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| WR-01 | warning | open | - |
| WR-02 | warning | open | - |
| WR-03 | warning | open | - |
| WR-04 | warning | open | - |
| IN-01 | info | open | - |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
