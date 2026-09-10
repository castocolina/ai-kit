---
created: 2026-09-10T00:00:00.000Z
title: Refactor status line quota window percentage/colors to be time-left relative
area: tooling
resolves_phase: 8
severity: minor
files:
  - tools/status-line.py
---

## Problem

`tools/status-line.py` currently colors the rate-limit quota buckets (hourly and weekly)
purely by `used_percentage` via `util_rate_color()` → `theme.ramps["rate"]`
(`util_render_rate_limits`, tools/status-line.py:1620-1643), with `resets_at` only used to
render a reset-time suffix (`util_hour_reset_suffix` / `util_week_reset_suffix`,
tools/status-line.py:1604-1616) — never factored into the percentage or the color itself.

This is misleading: e.g. 80% used with 4 hours still left in the window reads the same
color as 80% used with 5 minutes left, even though the second is a much more urgent signal
(burn rate vs. time remaining, not raw usage).

## Solution

TBD — refactor the quota percentage/color computation to be relative to time remaining in
the window (hourly and weekly buckets both have a `resets_at`), not just raw
`used_percentage`. Likely needs a burn-rate-vs-time-left ramp (e.g. compare
`used_percentage` against elapsed-fraction-of-window, not an absolute static ramp) feeding
into `util_pick_color` / `theme.ramps["rate"]`. Needs its own spike per the
theory→hypothesis→spike methodology before locking the formula — check existing
`tests/test_status_line.py` (e.g. `test_render_time_colors_by_slo_sla_ramp`) for the
existing ramp-testing pattern to extend.
