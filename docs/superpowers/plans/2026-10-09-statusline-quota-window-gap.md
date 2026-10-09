# Status-line Quota Window Gap Coloring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Color each quota-limit window by the absolute gap (in percentage points) between token usage and elapsed window time — ≤5 GREEN, <11 YELLOW, ≤15 ORANGE, >15 RED — with a signed `(+N)`/`(-N)` marker in the rich tier, replacing the pace-ratio formula.

**Architecture:** Three new pure helpers in `tools/status-line.py` (`util_rate_gap` returns the signed gap or None; `util_gap_color` grades `abs(gap)` against inclusive bounds directly, bypassing the strictly-below `util_pick_color`; `util_gap_sign` renders the marker) wired into the existing `util_rate_group_str` loop. `util_rate_gap` computes the window's *remaining percentage* first (`remaining_pct = (reset - now) * 100.0 / window_seconds`) and derives elapsed as `100.0 - remaining_pct` — the spec's worked-check values (±5, ±2, ±30, ±55, ±38) are float-exact under this formulation, verified against the actual module. The old pace helpers (`util_rate_burn_ratio`, `util_rate_color`) are deleted; `theme.ramps["rate"]` stays in config for parse compat but is no longer read for quota coloring. All work happens in the worktree at `.claude/worktrees/window-pct` (branch `exercise/window-pct`).

**Tech Stack:** Python 3.12 stdlib only, `unittest` (not pytest), ruff/pylint/pyright-clean.

**Spec:** `docs/superpowers/specs/2026-10-09-statusline-quota-window-gap-design.md` (same worktree)

## Global Constraints

- Runtime code stays stdlib-only — no third-party imports in `tools/status-line.py` or `tests/`.
- New top-level functions carry the `util_` role prefix and live inside the existing rate-helper banner block (`tests/test_arch.py` enforces this via AST — arch-test must pass).
- Gap bands are fixed, verbatim from the spec: `delta <= 5.0` GREEN; `delta < 11.0` YELLOW; `delta <= 15.0` ORANGE; else RED. Not configurable.
- Gap arithmetic is float-exact for every spec worked-check fixture (remaining-percentage-first formulation). Tests assert derived gap values with `assertAlmostEqual` (repo precedent, matching the old `TestRateBurnRatio`), so float editorializing never creeps into the fixed bands.
- Fallback (gap not computable) is `WHITE`, no marker — never the old 50/80 ramp.
- The old `elapsed_fraction < 1e-9` guard is REMOVED: elapsed == 0 is a normal computable case.
- Displayed percentage stays `round(used_percentage)`; color uses the raw float.
- All line numbers in the Files blocks refer to the PRE-TASK-1 file state. Task 1 inserts helper code and a test class into `tools/status-line.py` and `tests/test_status_line.py`, shifting every later reference — anchor on the quoted function/class/test names and verbatim content, not raw line numbers.
- **No inserted runtime code, docstring, or comment may contain the strings `util_rate_burn_ratio`, `util_rate_color`, or `test_burn_ratio_`** — Task 3 Step 4's verification gate requires zero matches for those names after the deletion, so the plan's own verbatim text must never trip it. Refer to the deleted helpers as "the pace ratio"/"the pace-ratio helpers" instead.
- All written artifacts in English.

---

### Task 1: Pure gap helpers — `util_rate_gap`, `util_gap_color`, `util_gap_sign`

**Files:**
- Modify: `tools/status-line.py` (insert after `util_rate_burn_ratio`, which ends at line 1515 — inside the same banner block)
- Test: `tests/test_status_line.py` (add `TestRateGap` class after `TestRateBurnRatio`, which ends at line 274)

**Interfaces:**
- Consumes: `util_rate_window_seconds(key) -> int | None` (existing, status-line.py:1479), `Theme.c(spec) -> str` (existing).
- Produces (used by Task 2):
  - `util_rate_gap(pct: float, key: str, reset: int | None, now: float) -> float | None` — SIGNED percentage-point gap (`used - elapsed_pct`), or `None` when the window is unreliable.
  - `util_gap_color(delta: float, theme: "Theme") -> str` — resolved ANSI escape for the band.
  - `util_gap_sign(gap: float) -> str` — `" (+N)"` / `" (-N)"` / `""`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_status_line.py`, immediately after the `TestRateBurnRatio` class:

```python
class TestRateGap(unittest.TestCase):
    """Pure-function tests for util_rate_gap (SIGNED percentage-point gap
    between used_percentage and the window's elapsed percentage),
    util_gap_color (absolute-gap band picker, inclusive bounds), and
    util_gap_sign -- the quota-window coloring defined by
    docs/superpowers/specs/2026-10-09-statusline-quota-window-gap-design.md."""

    def test_gap_signed_behind_and_ahead(self):
        # 45% of a 5h window elapsed (reset = NOW + 0.55 * 18000 = NOW + 9900):
        # 50% used is 5 points AHEAD (+5); 40% used is 5 points BEHIND (-5).
        self.assertAlmostEqual(sl.util_rate_gap(50, "five_hour", NOW + 9900, NOW), 5.0)
        self.assertAlmostEqual(sl.util_rate_gap(40, "five_hour", NOW + 9900, NOW), -5.0)

    def test_gap_color_bands_inclusive_bounds(self):
        cases = [(5.0, "GREEN"), (5.001, "YELLOW"), (10.999, "YELLOW"),
                 (11.0, "ORANGE"), (15.0, "ORANGE"), (15.001, "RED")]
        for delta, want in cases:
            self.assertEqual(sl.util_gap_color(delta, THEME), THEME.c(want), delta)

    def test_gap_live_spec_case_45_elapsed(self):
        # Spec worked checks: 45% elapsed + 43% used -> delta 2 GREEN;
        # 45% elapsed + 15% used -> delta 30 RED.
        gap_ok = sl.util_rate_gap(43, "five_hour", NOW + 9900, NOW)
        self.assertAlmostEqual(gap_ok, -2.0)
        self.assertEqual(sl.util_gap_color(abs(gap_ok), THEME), THEME.c("GREEN"))
        gap_bad = sl.util_rate_gap(15, "five_hour", NOW + 9900, NOW)
        self.assertAlmostEqual(gap_bad, -30.0)
        self.assertEqual(sl.util_gap_color(abs(gap_bad), THEME), THEME.c("RED"))

    def test_gap_at_window_start_color_and_gap(self):
        # elapsed_fraction == 0 (the old 1e-9 guard is gone): 0% used is a
        # 0 gap, grading GREEN; 6% used is a 6-point gap, grading YELLOW --
        # the spec's §Tests start-of-window cases pinned at BOTH levels.
        gap_zero = sl.util_rate_gap(0, "five_hour", NOW + 5 * 3600, NOW)
        self.assertAlmostEqual(gap_zero, 0.0)
        self.assertEqual(sl.util_gap_color(gap_zero, THEME), THEME.c("GREEN"))
        gap_six = sl.util_rate_gap(6, "five_hour", NOW + 5 * 3600, NOW)
        self.assertAlmostEqual(gap_six, 6.0)
        self.assertEqual(sl.util_gap_color(gap_six, THEME), THEME.c("YELLOW"))

    def test_gap_at_exact_reset_elapsed_is_100(self):
        # reset == now: elapsed_pct 100 (remaining_pct 0.0 exact). 100% used
        # -> 0 gap; 0% used -> -100.
        self.assertAlmostEqual(sl.util_rate_gap(100, "five_hour", NOW, NOW), 0.0)
        self.assertAlmostEqual(sl.util_rate_gap(0, "five_hour", NOW, NOW), -100.0)

    def test_gap_missing_reset_is_none(self):
        self.assertIsNone(sl.util_rate_gap(50, "five_hour", None, NOW))

    def test_gap_past_reset_is_none(self):
        self.assertIsNone(sl.util_rate_gap(50, "five_hour", NOW - 1, NOW))

    def test_gap_clock_skew_is_none(self):
        # 6h remaining of a 5h window: remaining_pct = 120 > 100.
        self.assertIsNone(sl.util_rate_gap(50, "five_hour", NOW + 3600 * 6, NOW))

    def test_gap_unknown_key_is_none(self):
        self.assertIsNone(sl.util_rate_gap(50, "nonsense_unit", NOW + 3600, NOW))

    def test_gap_sign_marks(self):
        self.assertEqual(sl.util_gap_sign(5.0), " (+5)")
        self.assertEqual(sl.util_gap_sign(-5.0), " (-5)")
        self.assertEqual(sl.util_gap_sign(0.4), "")      # rounds to 0
        self.assertEqual(sl.util_gap_sign(-0.4), "")     # rounds to 0
        self.assertEqual(sl.util_gap_sign(0.6), " (+1)")  # banker's: 0.5 -> 0
        self.assertEqual(sl.util_gap_sign(-0.6), " (-1)")
        self.assertEqual(sl.util_gap_sign(-55.0), " (-55)")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_status_line.TestRateGap -v`
Expected: FAIL with `AttributeError: ... has no attribute 'util_rate_gap'`

- [ ] **Step 3: Write the three helpers**

In `tools/status-line.py`, immediately after `util_rate_burn_ratio` (line 1515), insert:

```python
def util_rate_gap(pct: float, key: str, reset: int | None, now: float) -> float | None:
    """Signed percentage-point gap between used_percentage and the window's
    elapsed percentage (positive: usage ahead of elapsed time; negative:
    behind). None when the window can't be reliably derived (unparseable
    key, missing reset, a resets_at already in the past [remaining_pct < 0],
    or a resets_at implying more time remaining than the key's parsed
    window allows [remaining_pct > 100] -- clock skew or window/key
    mismatch). Replaces the pace ratio (pct / elapsed_fraction): the gap
    is computed from the remaining percentage directly -- no division by
    an elapsed fraction -- so elapsed == 0 (window just started) is a
    normal computable case, not a fallback."""
    window_seconds = util_rate_window_seconds(key)
    if window_seconds is None or reset is None:
        return None
    remaining_pct = (reset - now) * 100.0 / window_seconds
    if remaining_pct < 0.0 or remaining_pct > 100.0:
        return None
    return pct - (100.0 - remaining_pct)


def util_gap_color(delta: float, theme: "Theme") -> str:
    """Quota-gap band color: |gap| in percentage points graded against the
    spec's INCLUSIVE bounds (<=5 GREEN, <11 YELLOW, <=15 ORANGE, >15 RED).
    Deliberately NOT util_pick_color -- that helper is strictly-below and
    cannot express <=5 / <11 / 11..15-inclusive."""
    if delta <= 5.0:
        return theme.c("GREEN")
    if delta < 11.0:
        return theme.c("YELLOW")
    if delta <= 15.0:
        return theme.c("ORANGE")
    return theme.c("RED")


def util_gap_sign(gap: float) -> str:
    """' (+N)' / ' (-N)' marker for a signed quota gap (positive: usage
    ahead of elapsed time; negative: behind); omitted when the gap rounds
    to 0 (Python banker's rounding: +/-0.5 -> 0, +/-0.6 -> 1)."""
    n = round(gap)
    if n == 0:
        return ""
    return f" ({'+' if n > 0 else '-'}{abs(n)})"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_status_line.TestRateGap -v`
Expected: PASS (10 tests — the `TestRateGap` class above defines exactly 10 test methods). Also `python3 -m unittest tests.test_status_line -v` — old `TestRateBurnRatio` still passes (old helpers untouched).

- [ ] **Step 5: Commit**

```bash
git add tools/status-line.py tests/test_status_line.py
git commit -m "feat(statusline): add pure gap helpers util_rate_gap/util_gap_color/util_gap_sign"
```

---

### Task 2: Wire gap coloring into `util_rate_group_str` + render-level tests + README

**Files:**
- Modify: `tools/status-line.py:1664-1694` (`util_rate_group_str` body) and its clock-dependence comment (lines 1673-1679)
- Test: `tests/test_status_line.py:644-706` (replace the four pace/color tests, update the display test)
- Modify: `README.md:192-198` (rate-limit segments paragraph)

**Interfaces:**
- Consumes: `util_rate_gap` / `util_gap_color` / `util_gap_sign` (Task 1, exact signatures above), `theme.c("WHITE")` (palette name exists, status-line.py:158).
- Produces: `util_rate_group_str(rate_limits, hourly, show_reset, theme)` — signature unchanged. Segment text in the rich tier gains `(+N)`/`(-N)` between the percentage and the reset suffix; terse tier byte-identical.

- [ ] **Step 1: Write the failing render tests**

In `tests/test_status_line.py`, replace `test_h_rate_limit_colors_by_pace_more_elapsed_time_is_less_urgent` (lines 644-660), `test_rate_limit_past_reset_color_matches_raw_pct` (674-686), `test_h_rate_limit_clock_skew_falls_back_to_raw_pct` (688-695), and `test_h_rate_limit_live_regression_low_pct_late_in_window_is_green` (697-706) with:

```python
    def test_h_rate_limit_colors_by_absolute_gap(self):
        # Absolute-gap direction (spec): 45% of a 5h window elapsed, 15%
        # used is 30 points apart -> RED; 43% used is 2 points -> GREEN.
        # Reverses the pace ratio's "low usage late in the window is calm".
        # Separate calls -- same key in a shared dict would collide.
        with mock.patch.object(sl.time, "time", return_value=NOW):
            rl_low = {"five_hour": {"used_percentage": 15, "resets_at": NOW + 9900}}
            out_low = sl.seg_alt_h_rate_limit(_data(rate_limits=rl_low), 200, THEME)
            self.assertIn(THEME.c("RED"), out_low)
            self.assertNotIn(THEME.c("GREEN"), out_low)
            self.assertIn(" (-30)", strip(out_low))

            rl_ok = {"five_hour": {"used_percentage": 43, "resets_at": NOW + 9900}}
            out_ok = sl.seg_alt_h_rate_limit(_data(rate_limits=rl_ok), 200, THEME)
            self.assertIn(THEME.c("GREEN"), out_ok)
            self.assertNotIn(THEME.c("RED"), out_ok)
            self.assertIn(" (-2)", strip(out_ok))

    def test_h_rate_limit_positive_sign_marks_usage_ahead(self):
        # Signed marker: 50% used with 45% elapsed is 5 points ahead -> (+5).
        # gap = 50 - (100.0 - 9900.0 * 100.0 / 18000) = 5.0 float-exact, so
        # abs(gap) hits the GREEN band's <= 5.0 boundary exactly.
        with mock.patch.object(sl.time, "time", return_value=NOW):
            rl = {"five_hour": {"used_percentage": 50, "resets_at": NOW + 9900}}
            out = sl.seg_alt_h_rate_limit(_data(rate_limits=rl), 200, THEME)
            self.assertIn(" (+5)", strip(out))
            self.assertIn(THEME.c("GREEN"), out)

    def test_h_rate_limit_unreliable_window_paints_white_no_marker(self):
        # Past reset and clock skew both make the gap uncomputable: WHITE,
        # no marker, bucket still visible (spec fallback, not the old ramp).
        # The marker-absence asserts are per spec ("the fallback case renders
        # no marker"); the missing-reset case is equality-pinned separately
        # by test_rate_limit_no_reset_stamp_when_absent.
        with mock.patch.object(sl.time, "time", return_value=NOW):
            rl_past = {"five_hour": {"used_percentage": 50, "resets_at": NOW - 1}}
            out_past = sl.seg_alt_h_rate_limit(_data(rate_limits=rl_past), 200, THEME)
            self.assertIn(THEME.c("WHITE"), out_past)
            self.assertNotIn(THEME.c("RED"), out_past)
            self.assertNotIn(" (+", strip(out_past))
            self.assertNotIn(" (-", strip(out_past))

            rl_skew = {"five_hour": {"used_percentage": 50, "resets_at": NOW + 3600 * 6}}
            out_skew = sl.seg_alt_h_rate_limit(_data(rate_limits=rl_skew), 200, THEME)
            self.assertIn(THEME.c("WHITE"), out_skew)
            self.assertNotIn(" (+", strip(out_skew))
            self.assertNotIn(" (-", strip(out_skew))

    def test_h_rate_limit_live_regression_low_pct_late_in_window_is_red(self):
        # Reversal pinned by the spec: the Phase 8.1 live case (25% used,
        # 4h of a 5h window elapsed -> 80%) was GREEN under the pace ratio
        # (25/0.8 = 31.25); the absolute gap is 55 points -> RED.
        with mock.patch.object(sl.time, "time", return_value=NOW):
            rl = {"five_hour": {"used_percentage": 25, "resets_at": NOW + 3600}}
            out = sl.seg_alt_h_rate_limit(_data(rate_limits=rl), 200, THEME)
            self.assertIn(THEME.c("RED"), out)
            self.assertNotIn(THEME.c("GREEN"), out)
            self.assertIn(" (-55)", strip(out))
```

And update the existing display test `test_h_rate_limit_display_unchanged_by_color_refactor` (lines 662-672) — the expected string gains the marker (42 used, 80% elapsed -> `-38`):

```python
    def test_h_rate_limit_display_unchanged_by_color_refactor(self):
        # Rich-tier text is the old format plus the signed gap marker
        # between the percentage and the reset suffix; the terse/narrow
        # tier stays byte-identical (its own test pins that).
        with mock.patch.object(sl.time, "time", return_value=NOW):
            rl = {"five_hour": {"used_percentage": 42, "resets_at": NOW + 3600}}
            out = strip(sl.seg_alt_h_rate_limit(_data(rate_limits=rl), 200, THEME))
            self.assertEqual(
                out,
                f"⚡️ 5h: 42% (-38) (↺ {sl.datetime.fromtimestamp(NOW + 3600).strftime('%H:%M')})",
            )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest tests.test_status_line -v`
Expected: FAIL — the new tests find the old pace colors (RED+bold/GREEN) and no `(-38)` marker in the display test.

- [ ] **Step 3: Rewire `util_rate_group_str`**

In `tools/status-line.py`, inside `util_rate_group_str`, update the clock-dependence comment (lines 1673-1679) to say "the gap below weighs used_percentage against how much of the bucket's window has already elapsed (elapsed pct, via `now` and each bucket's resets_at)", and replace:

```python
        ratio = util_rate_burn_ratio(pct, key, reset, now)
        color = util_rate_color(ratio, theme)
        suffix = suffix_fn(reset) if show_reset else ""
        parts.append(f"{fmt_rate_key_label(key)}: {color}{round(pct)}%{RESET}{suffix}")
```

with:

```python
        gap = util_rate_gap(pct, key, reset, now)
        if gap is None:
            color = theme.c("WHITE")
            mark = ""
        else:
            color = util_gap_color(abs(gap), theme)
            # Same tier gate as the reset suffix (spec: the narrow/terse tier
            # omits the marker) -- seg_alt_h_rate_limit renders the terse
            # tier via util_rate_group_str(rl, True, False, theme), so an
            # ungated mark would leak into it.
            mark = util_gap_sign(gap) if show_reset else ""
        suffix = suffix_fn(reset) if show_reset else ""
        parts.append(f"{fmt_rate_key_label(key)}: {color}{round(pct)}%{RESET}{mark}{suffix}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest tests.test_status_line -v`
Expected: PASS. The narrow-tier test (`test_h_rate_limit_shows_time_only_reset_then_drops_it_when_narrow`, expects `⚡️ 5h: 42%`) and `test_rate_limit_no_reset_stamp_when_absent` pass unchanged — the marker rides the `show_reset` gate and no-reset buckets have no gap.

- [ ] **Step 5: Update the README**

In `README.md`, append to the rate-limit segments paragraph (after the `7d: 13% (↺ Sun 14:10)` sentence, line 196):

```markdown
Color is an absolute pace gap: |used% − elapsed%| in percentage points — ≤5 green, under 11
yellow, ≤15 orange, more red — with a signed `(+N)`/`(-N)` marker (usage ahead of / behind
elapsed time, omitted at 0) in the rich tier. An unreliable window (missing/past `resets_at`,
clock skew) paints the percentage white and shows no marker.
```

- [ ] **Step 6: Commit**

```bash
git add tools/status-line.py tests/test_status_line.py README.md
git commit -m "feat(statusline): color quota windows by absolute usage/time gap with signed marker"
```

---

### Task 3: Delete the superseded pace helpers and their tests (keeping the window-seconds parsing tests)

**Files:**
- Modify: `tools/status-line.py:1479-1520` (delete `util_rate_burn_ratio` at 1492-1515 and `util_rate_color` at 1518-1520; keep `util_rate_window_seconds` at 1479-1489)
- Test: `tests/test_status_line.py` (refocus the `TestRateBurnRatio` class, lines 179-274: DELETE only its ten `test_burn_ratio_*` methods — defs at lines 205, 214, 224, 232, 241, 249, 255, 258, 265, 268 — KEEP the four `test_window_seconds_*` parsing tests at 188-203 verbatim — the spec's §Tests mandates "Keep `util_rate_window_seconds` parsing tests. They are unchanged"; rewrite `test_rate_ramp_bands`, lines 151-155)

**Interfaces:**
- Consumes: nothing new.
- Produces: no runtime callers of `util_rate_color`/`util_rate_burn_ratio` remain (the quota path now uses the Task 1 helpers); the four `test_window_seconds_*` parsing tests survive under the renamed class `TestWindowSeconds` (the parser `util_rate_gap` depends on keeps its coverage); `theme.ramps["rate"]` still resolves from `_RAMP_DEFAULTS`/`[ramp.rate]` config but nothing reads it for coloring.

- [ ] **Step 1: Rewrite `test_rate_ramp_bands` to not use the deleted color helper**

In `tests/test_status_line.py`, replace lines 151-155:

```python
    def test_rate_ramp_bands(self):
        # [ramp.rate] still resolves into theme.ramps["rate"] (config parse
        # compat, kept so existing overrides don't error) but quota coloring
        # no longer reads it -- assert the resolved structure directly,
        # without the pace-era color helper (this refactoring deletes it).
        self.assertEqual(
            [(ceil, c) for ceil, c in THEME.ramps["rate"]],
            [(50.0, THEME.c("GREEN")), (80.0, THEME.c("YELLOW")),
             (float("inf"), THEME.c("RED+bold"))],
        )
```

- [ ] **Step 2: Refocus the test class — delete only the pace-ratio tests, keep the parsing tests**

In `tests/test_status_line.py`, replace the class header, docstring, and four parsing tests (lines 179-203) with the renamed class below, and DELETE the ten `test_burn_ratio_*` methods (lines 205-274) outright. The four parsing test bodies are repeated here verbatim from the current file — they do not change:

```python
class TestWindowSeconds(unittest.TestCase):
    """Pure-function tests for util_rate_window_seconds (the window-key
    parser util_rate_gap now depends on). The four parsing tests are
    unchanged from the pace-ratio era; the pace-ratio tests that shared
    this class are deleted along with their helpers -- per
    docs/superpowers/specs/2026-10-09-statusline-quota-window-gap-design.md
    §Tests: "Keep util_rate_window_seconds parsing tests. They are
    unchanged"."""

    def test_window_seconds_parses_known_keys(self):
        self.assertEqual(sl.util_rate_window_seconds("five_hour"), 5 * 3600)
        self.assertEqual(sl.util_rate_window_seconds("seven_day"), 7 * 86400)

    def test_window_seconds_none_when_both_words_unknown(self):
        self.assertIsNone(sl.util_rate_window_seconds("nonsense_unit"))

    def test_window_seconds_none_when_only_number_word_unknown(self):
        # "hour" IS a valid _UNIT_SECONDS key; "eleven" is NOT in _NUM_WORDS --
        # isolates a ONE-SIDED lookup failure.
        self.assertIsNone(sl.util_rate_window_seconds("eleven_hour"))

    def test_window_seconds_none_when_only_unit_word_unknown(self):
        # Mirror case: "five" IS a valid _NUM_WORDS key; "fortnight" is NOT in
        # _UNIT_SECONDS.
        self.assertIsNone(sl.util_rate_window_seconds("five_fortnight"))
```

- [ ] **Step 3: Delete the old helpers**

Delete `util_rate_burn_ratio` (tools/status-line.py:1492-1515, docstring included) and `util_rate_color` (1518-1520, docstring included) from `tools/status-line.py`. Keep `util_rate_window_seconds` (1479-1489) — Task 1's `util_rate_gap` calls it.

- [ ] **Step 4: Verify nothing else references the deleted names, and the parsing tests survived**

By this point every pre-existing reference is gone via earlier steps: the runtime call pair (status-line.py:1690-1691) was replaced in Task 2 Step 3, the render tests referencing them (tests/test_status_line.py:645, 678, 686, 695) were replaced in Task 2 Step 1, and line 155 was rewritten in Step 1 above — the plan's inserted docstrings/comments avoid the deleted names on purpose (Global Constraints). So this gate is now satisfiable:

Run: `rg -n "util_rate_burn_ratio|util_rate_color|burn_ratio|TestRateBurnRatio" tools/ tests/`
Expected: no matches (the broadened pattern also catches stray pace-era test method names).
Run: `rg -c "def test_window_seconds_" tests/test_status_line.py`
Expected: `4` — the parsing tests Task 1's `util_rate_gap` depends on are still present.

- [ ] **Step 5: Run the full status-line suite plus arch**

Run: `python3 -m unittest tests.test_status_line -v` and `python3 -m unittest tests.test_arch -v`
Expected: PASS. (`test_arch` proves the three new `util_`-prefixed functions satisfy the role-prefix convention.)

- [ ] **Step 6: Run the aggregate unit tier**

Run: `make test-unit`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add tools/status-line.py tests/test_status_line.py
git commit -m "refactor(statusline): drop pace-ratio helpers superseded by gap coloring"
```
