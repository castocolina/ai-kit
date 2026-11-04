---
phase: 28
review: 28-REVIEW.md
titles: json
findings:
  - id: IN-01
    severity: info
    disposition: skipped
    title: "`--pushed` trusts a covering set the mapper marked untrusted"
  - id: IN-02
    severity: info
    disposition: skipped
    title: "The guard result regex fails closed on interleaved stderr"
  - id: IN-03
    severity: info
    disposition: skipped
    title: "The matrix's final cleanup can override its verdict"
  - id: IN-04
    severity: info
    disposition: skipped
    title: "A missing module is reported twice per environment"
  - id: IN-05
    severity: info
    disposition: skipped
    title: "The shortcut comment's gsd-core version is stale"
  - id: IN-06
    severity: info
    disposition: skipped
    title: "Generality without instantiation: an empty `ALL_SKIP_OK` allowlist and its stale checker"
  - id: IN-07
    severity: info
    disposition: fixed
    title: "The WR-01 regression test claims a unit-uv module but uses two integration modules"
  - id: WR-01
    severity: warning
    disposition: fixed
    title: "A full run at commit drops the covering unit-uv and integration modules"
  - id: WR-02
    severity: warning
    disposition: fixed
    title: "`check-dogfood` reports `ok` when zero no-write guards executed"
  - id: WR-03
    severity: warning
    disposition: fixed
    title: "The mapper misses tool-to-tool loads"
open: 0
total: 10
recorded: 2026-11-04T12:17:48.405Z
---

# Phase 28: Code Review Disposition

| Finding | Severity | Disposition | Source |
|---------|----------|-------------|--------|
| IN-01 | info | skipped | 28-REVIEW-FIX.md |
| IN-02 | info | skipped | 28-REVIEW-FIX.md |
| IN-03 | info | skipped | 28-REVIEW-FIX.md |
| IN-04 | info | skipped | 28-REVIEW-FIX.md |
| IN-05 | info | skipped | 28-REVIEW-FIX.md |
| IN-06 | info | skipped | 28-REVIEW-FIX.md |
| IN-07 | info | fixed | 28-REVIEW-FIX.md |
| WR-01 | warning | fixed | 28-REVIEW-FIX.md (not in the current review) |
| WR-02 | warning | fixed | 28-REVIEW-FIX.md (not in the current review) |
| WR-03 | warning | fixed | 28-REVIEW-FIX.md (not in the current review) |

Dispositions: `open` (recorded, not yet triaged), `fixed`, `skipped`, `deferred`.
Set `deferred` by hand and put the reason in the Source cell; both are preserved. A `|` in the reason is kept as prose and escaped on the next run.
Re-running the gate keeps every row it can. A row the current review no longer reports is kept and its Source cell flagged, so a finding does not leave this record silently. ONE exception: when a finding id is REUSED by a different finding, the earlier decision cannot keep a row — the id is taken — and it is dropped. A RECORDED decision (anything but `open`) is named on the console when that happens; a row still at `open` is replaced silently, because `open` records no decision to lose.
