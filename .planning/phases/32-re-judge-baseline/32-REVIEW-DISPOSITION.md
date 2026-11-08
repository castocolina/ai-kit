---
phase: 32
review: 32-REVIEW.md
titles: json
findings:
  - id: IN-01
    severity: info
    disposition: fixed
    title: "Two record shapes still end `check`/`report` in a traceback or an unnamed problem line"
  - id: IN-02
    severity: info
    disposition: fixed
    title: "Ingest's `_load_record` still crashes on a partial record, though the brief says those are refused"
  - id: WR-01
    severity: warning
    disposition: fixed
    title: "`check` crashes on a malformed record or loop file; `check-dogfood` loses its output"
  - id: WR-02
    severity: warning
    disposition: fixed
    title: "A retried ingest keeps the first attempt's manifest"
  - id: WR-03
    severity: warning
    disposition: fixed
    title: "The verdict-line scan depends on JSON key order"
  - id: WR-04
    severity: warning
    disposition: fixed
    title: "The jev call's outer timeout equals the ladder's own deadline"
  - id: WR-05
    severity: warning
    disposition: fixed
    title: "Two env values `ask_jev` sets are overwritten by the ladder (necessity)"
open: 0
total: 7
recorded: 2026-11-07T19:50:38.628Z
---

# Phase 32: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| IN-01 | info | fixed | 3d51506 (orchestrator; 32-REVIEW-FIX.md, Orchestrator fixes) |
| IN-02 | info | fixed | 3d51506 (orchestrator; 32-REVIEW-FIX.md, Orchestrator fixes) |
| WR-01 | warning | fixed | 32-REVIEW-FIX.md (not in the current review) |
| WR-02 | warning | fixed | 32-REVIEW-FIX.md (not in the current review) |
| WR-03 | warning | fixed | 32-REVIEW-FIX.md (not in the current review) |
| WR-04 | warning | fixed | 32-REVIEW-FIX.md (not in the current review) |
| WR-05 | warning | fixed | 32-REVIEW-FIX.md (not in the current review) |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
