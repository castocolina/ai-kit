# Status-line quota windows — absolute gap coloring

Date: 2026-10-09
Status: accepted, implemented on `gsd/v1.3-curated-config-v2` in `d23749b..52def0f` (marked 2026-10-14 per ROADMAP Phase 23)

## Intent

Color each quota-limit window by how far token usage is from time elapsed, in percentage points. Close is calm. Far, in either direction, is not.

This replaces the pace ratio in `util_rate_burn_ratio` (`used_percentage / elapsed_fraction`) and the `theme.ramps["rate"]` bands `(50 GREEN, 80 YELLOW, inf RED+bold)`. That ratio treats low usage late in the window as healthy. This spec does the opposite on purpose: 45% of the window elapsed and 15% used is red, because the two percentages are 30 points apart.

## What stays

- The displayed number is still `round(used_percentage)`, not the gap and not elapsed time. The rich tier prefixes it with a pace sign — `+` when usage is at or behind the window clock (under pace: slack), `-` when usage burns faster than the clock — so a 0% reading early in a window renders `+0%`. The sign's magnitude is carried by the color band, never shown next to the number. The narrow/terse tier omits the sign (same tier gate as the reset stamp).
- The label and reset suffix stay (`5h: 42% (↺ 14:10)`, `7d: 13% (↺ Sun 14:10)`).
- A bucket is still shown whenever it reports `used_percentage`. A past `resets_at` does not hide it.
- Window length still comes from the bucket key via `util_rate_window_seconds` (`five_hour` = 5h, `seven_day` = 7d, and any other key that parser already accepts, including `eight_hour` and `one_day`). No new windows.
- Elapsed time still comes from `resets_at` and `now`. Nothing about window length is hardcoded in the color formula.

## Algorithm

For each bucket that already reaches `util_rate_group_str`:

```
window_seconds = util_rate_window_seconds(key)
elapsed_fraction = 1 - (resets_at - now) / window_seconds
elapsed_pct = elapsed_fraction * 100
delta = abs(used_percentage - elapsed_pct)
```

`delta` is an absolute difference of percentage points. It is not a ratio, and it is not `abs(used - elapsed) / elapsed`.

The helper returns the SIGNED gap (`used_percentage - elapsed_pct`), not the absolute value: the color bands grade `abs(gap)`, and the displayed percentage's prefix sign is the gap direction INVERTED — `+` when the gap is ≤ 0 (usage at or behind the window clock), `-` when the gap is > 0 (usage ahead: burning faster than the window). No magnitude is shown next to the sign.

Color `delta` with these bounds. `11` and `15` belong to orange. `5` belongs to green.

| delta | color |
|---|---|
| ≤ 5 | GREEN |
| > 5 and < 11 | YELLOW |
| ≥ 11 and ≤ 15 | ORANGE |
| > 15 | RED |

`ORANGE` is the existing palette entry (`38;5;208`). These four colors are plain palette names, not `+bold`.

Do not feed `delta` through `util_pick_color`. That helper is strictly-below, so it cannot express `≤ 5`, `< 11`, and `11`–`15` inclusive. Compare the bounds directly.

`theme.ramps["rate"]` is no longer the color source for quota windows. Leave the ramp in config so an existing `[ramp.rate]` override still parses. Quota coloring does not read it.

Color uses the raw `used_percentage`, not the rounded number on screen. A displayed `45%` can be `44.6` and must be colored as `44.6`.

Sign examples at 45% elapsed: 50% used renders `-50%` (gap +5: ahead of the clock); 40% used renders `+40%` (gap -5: behind). The anchor case — 0% used with 0.6% elapsed — renders `+0%`. The fallback case (gap not computable) renders no sign.

## When elapsed percentage cannot be computed

Unparseable key, missing `resets_at`, `elapsed_fraction < 0`, or `elapsed_fraction > 1`.

Do not invent a gap, and do not fall back to the old 50/80 ramp. Those are different scales. Render the percentage in `WHITE`. Still show the bucket.

A near-zero elapsed fraction is computable. The old `elapsed_fraction < 1e-9` guard existed only because dividing by it exploded. Absolute difference does not. At the start of the window, `delta = abs(used_percentage - elapsed_pct)` and the table above applies. `0` used at the start is green. `6` used at the start is yellow.

## Worked checks

Window math, not a special case: a 7d window that ends Sunday 22:00 starts Sunday 22:00 seven days earlier. `elapsed_pct = (now - start) / 7d * 100`. That is the same quantity as `elapsed_fraction * 100` when `resets_at` is that Sunday 22:00.

| elapsed % | used % | delta | color |
|---:|---:|---:|---|
| 45 | 43 | 2 | GREEN |
| 45 | 15 | 30 | RED |
| 45 | 50 | 5 | GREEN |
| 45 | 56 | 11 | ORANGE |
| 45 | 60 | 15 | ORANGE |
| 45 | 61 | 16 | RED |
| 80 | 25 | 55 | RED |

The last row is the Phase 8.1 live case (25% used, 4h of a 5h window elapsed). The old formula returns 31.25 and paints GREEN. This spec paints RED. That reversal is required.

On the exact reset instant, `elapsed_pct` is 100. `delta = abs(used_percentage - 100)`. A bucket that used 100% is green. A bucket that used 0% is red.

## Tests

Replace the pace-ratio assertions in `tests/test_status_line.py` (`TestRateBurnRatio` and the render-level pace color tests) with the table above, plus:

- `delta == 5` is GREEN. `delta == 5.001` is YELLOW.
- `delta == 10.999` is YELLOW. `delta == 11` is ORANGE.
- `delta == 15` is ORANGE. `delta == 15.001` is RED.
- `elapsed_fraction == 0` with `used_percentage == 0` is GREEN. The same instant with `used_percentage == 6` is YELLOW.
- Missing reset, past reset, clock skew (`resets_at` further out than the key's window), and unknown key paint WHITE, and the bucket is still visible.
- `util_gap_sign`: `+5.0 -> "-"`, `-5.0 -> "+"`, `0.0 -> "+"`, `0.4 -> "-"`, `-0.4 -> "+"`.
- The narrow/terse tier still renders `5h: 42%` with no sign. The rich tier renders `5h: +42%` (42 used, 80% elapsed: usage behind the clock) plus the existing reset suffix. Only color and the sign prefix change.

Keep `util_rate_window_seconds` parsing tests. They are unchanged.

## Out of scope

- Changing context, chat-size, render-time, or slowest ramps.
- Showing elapsed percentage in the label.
- A configurable margin. The bounds above are fixed.
- Guessing a window length the key parser does not already know.
