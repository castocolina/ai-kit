# Phase 8: Status-line Quota Color Refactor - Context

**Gathered:** 2026-09-10
**Status:** Ready for planning

<domain>
## Phase Boundary

A color-only refactor of `tools/status-line.py`'s rate-limit bucket rendering:
the displayed `used_percentage` and `resets_at`-derived reset suffix stay
byte-identical; only which ramp color (`theme.ramps["rate"]`) gets picked
changes, driven by a burn-rate signal (usage vs. remaining-fraction-of-window)
instead of raw usage percentage alone. No hardcoded window/time constants —
every timing input comes from the Claude-provided rate-limit context
(`resets_at`, and the bucket key name itself) on each render.

</domain>

<decisions>
## Implementation Decisions

### Burn-rate formula
- **D-01 (amended 2026-09-11 — supersedes the original draft of this decision):**
  The color is picked by feeding a ratio — `used_percentage / remaining_fraction`,
  where `remaining_fraction = 1 - elapsed_fraction` — into the EXISTING
  `theme.ramps["rate"]` thresholds (50/80/inf) unchanged. No new ramp is
  designed or tuned. — **Reversibility:** reversible — swapping the formula
  later only changes what value feeds the same existing `util_pick_color`
  call; the ramp and its thresholds are untouched either way.

  **Why this supersedes the original `pct / elapsed_fraction` draft:** that
  formula was chosen to reproduce ROADMAP.md SC4's original worked example
  (50% used at hour 1-of-5 → red; 30% used at hour 4-of-5 → green/blue) — but
  that example compares two DIFFERENT usage percentages at two different
  points in time (a burn-*pace* framing), which is mathematically
  incompatible with SC1's actual requirement: for the SAME `used_percentage`,
  less time remaining must render MORE urgently, never less. `pct /
  elapsed_fraction` is provably monotonically decreasing in `elapsed_fraction`
  for fixed `pct` — exactly backwards from SC1. Live-verified during Phase 8's
  plan-review convergence cycle 1 (opencode reviewer): identical 50% usage,
  4h-remaining-of-5h (elapsed=0.2) → old formula gives ratio 250 → RED, while
  1h-remaining (elapsed=0.8) → ratio 62.5 → YELLOW — less time left rendering
  LESS urgently. `pct / remaining_fraction` fixes the direction: for fixed
  `pct`, the ratio strictly increases as `remaining_fraction` shrinks (less
  time left), satisfying SC1 by construction. ROADMAP.md SC4's worked example
  text is corrected to match (see ROADMAP.md's own 2026-09-11 amendment note)
  rather than kept as the (now known-inconsistent) standard to design around.
  See `08-REVIEWS.md`'s resolved `## Plan-Revision Conflicts` entry for the
  full arithmetic proof.
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
- **D-03 (amended 2026-09-11 — the risky edge moved when D-01's formula flipped):**
  With `ratio = pct / remaining_fraction`, the division-by-zero risk is no
  longer at `elapsed_fraction == 0` (that case is now perfectly safe:
  `remaining_fraction == 1`, so `ratio == pct` — no clamp needed at all,
  reducing cleanly to raw-percentage behavior at window start). The risky edge
  is now `remaining_fraction == 0` (i.e. `elapsed_fraction == 1` — the render
  happens at/after the window's nominal reset moment while `resets_at` still
  reads as "now or later," a narrow timing-race case distinct from D-04's
  "resets_at already in the past" case below). Treat this as maximally urgent
  — clamp straight to the ramp's top band — which is the semantically correct
  call: you are at the literal edge of the window with no time left to pace
  against.
- **D-04 (amended 2026-09-11 — clamp direction flipped to match D-01):** When
  `resets_at` is already in the past (the existing
  `test_h/w_rate_limit_shows_bucket_even_with_past_reset` cases deliberately
  still show a stale bucket), this is the "we don't have a reliable read on
  the current window, don't invent urgency" fallback — under the corrected
  D-01 formula this means clamping `remaining_fraction` to `1.0` (NOT `0.0`,
  which would wrongly trigger D-03's max-urgency clamp for stale data). This
  reduces to `ratio == pct` — today's raw-percentage behavior — for this
  already-tested case, preserving the original zero-regression intent. (The
  original pre-amendment text clamped `elapsed_fraction` to `1.0` for this
  same case, which was correct under the old formula; the corrected
  formulation is `remaining_fraction = 1.0`, the equivalent safe value under
  the new one.)

  **Clarifying note (amended 2026-09-11, post-implementation code review +
  independent verification):** D-03's "at/after the window's nominal reset
  moment" clamp is reachable in practice ONLY at the exact floating-point tie
  `remaining_fraction == 0.0` — the literal instant `now == resets_at` to
  float precision, which exists purely to avoid a `ZeroDivisionError`
  (`pct / 0.0` raises in Python). ANY `remaining_fraction` that is negative,
  even by a sub-second epsilon (`resets_at` a fraction of a second in the
  past, the overwhelmingly common real-world shape since `time.time()` has
  sub-second precision and `resets_at` is integer-second), takes D-04's
  "already in the past" fallback instead — by design, since D-04 itself says
  "any amount past," not "meaningfully past." This was flagged as WARNING
  WR-01 in `08-REVIEW.md` and independently reproduced during phase
  verification; on inspection it is not a defect — the implementation
  matches both decisions' literal wording, the exact-tie case D-03 describes
  is just narrower in practice than the prose might suggest to a future
  reader. No ROADMAP success criterion requires the exact-tie path be
  reachable from a real `time.time()` call — SC1's own worked example
  (`50/0.8=62.5` vs `50/0.2=250`) only exercises the ordinary non-edge
  division, which is unaffected.

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

- (Superseded 2026-09-11 — see D-01's amendment note for the full history.)
  The roadmap's worked example is now: identical 50% usage with 4h remaining
  in a 5h window reads YELLOW (`50/0.8=62.5`), while the SAME 50% usage with
  only 1h remaining reads RED+bold (`50/0.2=250`) — against the UNCHANGED
  existing ramp thresholds, using `ratio = pct / remaining_fraction`. This
  satisfies ROADMAP SC1's same-usage, less-time-left-is-more-urgent invariant
  by construction; the original pre-amendment example here used two different
  usage percentages at two different times (a burn-pace framing) and was
  mathematically incompatible with SC1.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within Phase 8 scope.

</deferred>

---

*Phase: 8-Status-line Quota Color Refactor*
*Context gathered: 2026-09-10*
