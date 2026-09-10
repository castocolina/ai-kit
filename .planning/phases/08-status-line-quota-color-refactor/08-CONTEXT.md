# Phase 8: Status-line Quota Color Refactor - Context

**Gathered:** 2026-09-10
**Status:** Ready for planning

<domain>
## Phase Boundary

A color-only refactor of `tools/status-line.py`'s rate-limit bucket rendering:
the displayed `used_percentage` and `resets_at`-derived reset suffix stay
byte-identical; only which ramp color (`theme.ramps["rate"]`) gets picked
changes, driven by a burn-rate signal (usage vs. elapsed-fraction-of-window)
instead of raw usage percentage alone. No hardcoded window/time constants —
every timing input comes from the Claude-provided rate-limit context
(`resets_at`, and the bucket key name itself) on each render.

</domain>

<decisions>
## Implementation Decisions

### Burn-rate formula
- **D-01:** The color is picked by feeding a ratio — `used_percentage /
  (elapsed_fraction * 100)` — into the EXISTING `theme.ramps["rate"]` thresholds
  (50/80/inf) unchanged. This reproduces the roadmap's own worked example by
  construction: 50% used at hour 1-of-5 (elapsed=20%) → ratio 250 → red; 30%
  used at hour 4-of-5 (elapsed=80%) → ratio 37.5 → green/blue per the ramp. No
  new ramp is designed or tuned. — **Reversibility:** reversible — swapping the
  formula later only changes what value feeds the same existing
  `util_pick_color` call; the ramp and its thresholds are untouched either way.
- **D-02:** `elapsed_fraction` is derived per-render from two inputs, both
  already available without any hardcoded window-length constant:
  - `resets_at` (provided per bucket, as today)
  - the bucket's window duration, parsed from the bucket KEY NAME itself (e.g.
    `"five_hour"` → 5×3600s, `"seven_day"` → 7×86400s) — reusing the existing
    `_NUM_WORDS`/`_UNIT_ABBR` word-to-number tables already used by
    `fmt_rate_key_label` for display formatting. This is a generic word parser,
    not a hardcoded "the window is 5 hours" constant — it decodes whatever
    bucket name Anthropic sends, satisfying SC3 ("nothing about window length
    ... is a hardcoded constant in the formula").
  - `elapsed_fraction = 1 - (resets_at - now) / window_seconds`, where `now`
    comes from `time.time()` at render time (consistent with this file's
    existing test convention of `mock.patch.object(sl.time, "time",
    return_value=NOW)` for determinism — no new clock-injection mechanism
    needed).

### Edge cases
- **D-03:** When `elapsed_fraction` is 0 (render happens at/near the exact
  window start), any nonzero usage is treated as maximally urgent — the ratio
  clamps straight to the ramp's top band rather than computing a literal
  division-by-zero or an arbitrarily huge number.
- **D-04:** When `resets_at` is already in the past (the existing
  `test_h/w_rate_limit_shows_bucket_even_with_past_reset` cases deliberately
  still show a stale bucket), `elapsed_fraction` clamps to `1.0`. This is the
  "we don't have a reliable read on the current window, don't invent urgency"
  fallback, and it exactly reduces to today's raw-percentage behavior for this
  already-tested case — zero regression risk there.

### Where the logic lives
- **D-05:** `util_rate_color(pct, theme)` stays exactly as it is today — a pure
  pct→color picker, untouched, zero risk to its existing callers/tests. A new
  small `util_`-prefixed helper (naming TBD at planning time) computes the
  burn-rate ratio: parses window-seconds from the bucket key, applies the D-03/
  D-04 clamps, and returns the single combined number that `util_rate_group_str`
  then hands to the existing `util_rate_color` call — matching this file's
  established convention of small, single-purpose, independently testable
  `util_` functions. — **Reversibility:** reversible — this is an internal
  function-boundary choice; moving the math later is a local refactor, not a
  migration (no public/tested surface changes shape).

### Claude's Discretion
- Exact name of the new window-duration/ratio helper function.
- Exact clamp ceiling for D-03's "top band" value (any value that lands in the
  ramp's last tuple entry satisfies the requirement — no specific number is
  mandated).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Source todo and requirements
- `.planning/todos/pending/2026-09-10-refactor-status-line-quota-percentage-and-colors-to-be-relat.md` — original problem framing
- `.planning/REQUIREMENTS.md` §"v1.1 Requirements" — REQ-stln-time-relative-color, REQ-stln-ramp-tests
- `.planning/ROADMAP.md` §"Phase 8: Status-line Quota Color Refactor" — goal and 5 success criteria (including the explicit color-only and no-hardcoded-timing constraints, and the worked burn-rate example)

### Code this phase touches
- `tools/status-line.py`:
  - `util_rate_group_str` (~line 1619) — call site; where the new helper's
    output gets computed and handed to `util_rate_color`
  - `util_rate_color` (~line 1473) — stays unchanged (D-05)
  - `util_pick_color` (~line 1324) — stays unchanged; ramp-threshold picker reused as-is
  - `theme.ramps["rate"]` (~line 172, `[(50, "GREEN"), (80, "YELLOW"), ("inf", "RED+bold")]`) — reused unchanged (D-01)
  - `fmt_rate_key_label` (~line 1267), `_NUM_WORDS`/`_UNIT_ABBR` (~line 1254-1264) — existing key-name parsing this phase's window-duration derivation reuses (D-02)
  - `util_hour_reset_suffix` / `util_week_reset_suffix` (~line 1604-1616) — unchanged; these produce the reset-time suffix SC2 requires to stay byte-identical

### Tests this phase extends
- `tests/test_status_line.py`:
  - **Correction to the todo/roadmap's own reference**: `test_render_time_colors_by_slo_sla_ramp`
    (~line 471) tests `seg_render_time`'s SLO/SLA ramp — a DIFFERENT ramp for
    execution duration, not the rate-limit ramp. It is a useful PATTERN
    reference (how a ramp-color test is structured) but is not itself being
    extended. The actual rate-limit-ramp tests to extend live at
    `test_h_rate_limit_shows_time_only_reset_then_drops_it_when_narrow` and
    neighboring `test_h_rate_limit_*`/`test_w_rate_limit_*`/
    `test_rate_limit_no_reset_stamp_when_absent` tests (~lines 488-543),
    including the two past-`resets_at` tests D-04 must not regress
    (`test_h_rate_limit_shows_bucket_even_with_past_reset`,
    `test_w_rate_limit_shows_bucket_even_with_past_reset`, ~lines 538-545).
  - `NOW = 1_000_000` fixed epoch constant (line 38) and the
    `mock.patch.object(sl.time, "time", return_value=NOW)` pattern (~line 2559-2560)
    are the established determinism mechanism for any new time-relative test case.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_NUM_WORDS`/`_UNIT_ABBR` word-to-number tables (already used by
  `fmt_rate_key_label`) — directly reusable for window-duration parsing (D-02).
- The `mock.patch.object(sl.time, "time", return_value=NOW)` test pattern —
  reusable for deterministic time-relative test cases.

### Established Patterns
- Every `util_` function in this file is small, pure, and independently
  testable (the file's own section-5 header comment: "util_ — pure
  non-format helpers"). D-05 follows this convention rather than overloading
  an existing function.
- `util_rate_group_str` already has a comment explicitly calling out that
  bucket visibility "never depends on comparing resets_at against the clock" —
  this phase's color change is additive to that function, not a contradiction
  of it (visibility logic is untouched; only the color computation changes).

### Integration Points
- The new helper is called from inside `util_rate_group_str`'s existing loop
  (where `pct` and `reset` are already extracted per bucket), immediately
  before the existing `color = util_rate_color(pct, theme)` line.

</code_context>

<specifics>
## Specific Ideas

- The roadmap's own worked example (50%+ usage in hour 1-of-5 reads red; 30%
  usage at hour 4-of-5 of the same window can read green/blue) is reproduced
  exactly by the ratio formula against the UNCHANGED existing ramp thresholds
  — confirmed arithmetically during this discussion (50/20=250 > 80 → red;
  30/80=37.5 < 50 → green), not just assumed.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within Phase 8 scope.

</deferred>

---

*Phase: 8-Status-line Quota Color Refactor*
*Context gathered: 2026-09-10*
