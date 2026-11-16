---
created: 2026-11-08T00:00:00.000Z
title: Review notes left open by phase 32.1
area: tooling
severity: minor
files:
  - .planning/phases/32.1-batch-1-general-small-skills/32.1-REVIEW.md
  - .planning/phases/32.1-batch-1-general-small-skills/32.1-REVIEW-FIX.md
  - skills/jev-fast-decision/scripts/jev_review.py
  - skills/markdown-to-pdf/scripts/markdown_to_pdf.py
---

## Problem

The phase 32.1 code review left two info findings open by triage. Both fail visibly and lose no
data. Fix them when the owning skill is next touched.

## Notes

- 32.1 IN-03, `consent revoke <leftover>` for a name that only `JEV_ALLOW_REMOTE` lists answers
  `ok: true` and changes nothing. The `leftover` list still shows the name after the revoke, so
  nothing routes or leaks; only a caller that reads `ok` alone is misled. Fix with a `note` field
  (or `ok: false`, `reason: env_only`) and one test in Phase 34, which reworks this client; an edit
  now would stale the skill's judge record for an info finding.
- 32.1 IN-02, pandoc's `--resource-path` is a `:`-separated list, so a source folder whose name
  holds `:` splits in two and its relative images do not resolve. Rare; running pandoc with
  `cwd=<source folder>` instead removes the edge. Fix when markdown-to-pdf is next changed.
