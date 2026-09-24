---
phase: 08-status-line-quota-color-refactor
reviewed: 2026-09-11T03:08:56Z
depth: standard
files_reviewed: 2
files_reviewed_list:
  - tools/status-line.py
  - tests/test_status_line.py
findings:
  critical: 0
  warning: 3
  info: 2
  total: 5
status: issues_found
---

# Phase 8: Code Review Report

**Reviewed:** 2026-09-11T03:08:56Z
**Depth:** standard
**Files Reviewed:** 2
**Status:** issues_found

## Summary

Reviewed `tools/status-line.py`'s new `_UNIT_SECONDS` table, `util_rate_window_seconds`,
and `util_rate_burn_ratio` helpers (commits `b80a26a`, `f8bfa3d`, `aac4c20`), their
integration into `util_rate_group_str`'s call site, and the new `TestRateBurnRatio` /
`TestCooperativeBuilders` tests in `tests/test_status_line.py`, against the locked
design in `08-01-PLAN.md`/`08-CONTEXT.md` (D-01 through D-05) and ROADMAP.md's Phase 8
success criteria.

The core formula (`ratio = pct / remaining_fraction`) is mathematically sound and
satisfies SC1 for all in-range `remaining_fraction` values in `(0, 1]` — it is
strictly monotonic and continuous up to the `INF` clamp at `remaining_fraction ≈ 0`.
SC2 (byte-identical display) and SC3 (no hardcoded window-length constant) both hold:
the display f-string still renders raw `pct`, and `_UNIT_SECONDS` is a generic
unit-conversion table structurally identical to the pre-existing `_UNIT_ABBR` table.
`util_rate_color`, `util_pick_color`, and `theme.ramps["rate"]` are untouched (D-05).
All 302 tests in `test_status_line.py` and all 22 `test_arch.py` structural checks
pass; `make lint`'s `py_compile` step passes cleanly.

However, one implementation detail undermines a documented design guarantee (D-03's
"maximally urgent at the literal window-reset instant" clamp is effectively
unreachable from real wall-clock `time.time()` calls approaching from the
"just-passed" side — see WR-01), and the test for that exact clamp only exercises it
with a contrived exact-integer input that cannot occur in production. Two further
WARNING-level quality/robustness gaps are noted below. No BLOCKER-level defects were
found — the formula direction, clamp ordering, and SC1–SC5 compliance all hold as
specified.

## Warnings

### WR-01: D-03's "exact window-reset instant" max-urgency clamp is unreachable from the side it is meant to cover, and the only test for it uses an input real `time.time()` can never produce

**File:** `tools/status-line.py:1492-1507` (`util_rate_burn_ratio`)
**Issue:**
D-03 (`08-CONTEXT.md` lines 67-78) intends: "the render happens at/after the window's
nominal reset moment... treat this as maximally urgent." The implementation is:

```python
remaining_fraction = (reset - now) / window_seconds
if remaining_fraction < 0.0 or remaining_fraction > 1.0:
    remaining_fraction = 1.0
if abs(remaining_fraction) < 1e-9:
    return INF if pct > 0 else 0.0
return pct / remaining_fraction
```

Because `remaining_fraction < 0.0` is checked *before* the epsilon check, **any**
negative value — no matter how infinitesimally small — is clamped to `1.0` (the D-04
"don't invent urgency" fallback) and never reaches the `abs(remaining_fraction) < 1e-9`
branch. In production, `reset` is an integer second (`int(reset_raw)`,
`status-line.py:1681`) while `now = time.time()` (`status-line.py:1667`) has
sub-second (float) precision. The probability that `reset - now` lands exactly on
`0.0` — rather than landing on some small negative value microseconds after the
nominal reset second — is effectively zero. Verified directly:

```python
>>> util_rate_burn_ratio(50, 18000, reset=1_000_000, now=1_000_000.37)
50.0   # falls to D-04's raw-pct fallback, NOT D-03's INF clamp
>>> util_rate_burn_ratio(50, 18000, reset=1_000_000, now=1_000_000 - 1e-7)
inf    # only reachable from the "not yet reset" side
```

So in real usage, the moment a bucket's window nominally resets, the status line
immediately reverts to the *least* urgent raw-percentage color (D-04's fallback)
rather than the maximally-urgent `INF`/RED+bold D-03 was designed to show at that
instant — the two clamps are meant to cover disjoint cases but the ordering means
D-03's branch is reachable only from a razor-thin (<1ns, effectively never) window on
the positive side. This isn't user-visible for long (Anthropic will send an updated
`resets_at` on the next render), but it does mean D-03 as implemented does not deliver
the guarantee documented for it, and the existing unit test
(`test_burn_ratio_at_exact_window_reset_clamps_to_max_urgency`,
`tests/test_status_line.py:207-213`) only proves the clamp fires when `now == reset`
as *exact* equal values — an input shape that direct pure-function calls can produce
but `time.time()` cannot — so the test gives false confidence that this path is
exercised by real renders.
**Fix:** Either (a) widen the epsilon check to also catch small negative values before
the `< 0.0` clamp fires (e.g. check `abs(remaining_fraction) < 1e-9` first, then apply
the `< 0.0 / > 1.0` clamps), or (b) explicitly document that D-03's clamp is a
defensive/theoretical guarantee rather than one reachable in practice, and adjust the
test to use a realistic sub-second `now` approaching from both sides to demonstrate
the actual (asymmetric) production behavior instead of the exact-equality case.

### WR-02: `seg_alt_h_rate_limit`/`seg_alt_w_rate_limit` compute `now` independently for each of their two eager candidate renders

**File:** `tools/status-line.py:2450-2466`, `tools/status-line.py:1667`
**Issue:** `seg_alt_h_rate_limit` and `seg_alt_w_rate_limit` each call
`util_rate_group_str` twice (once with `show_reset=True`, once `False`) inside an
eagerly-evaluated list literal passed to `util_first_fitting`. Each invocation of
`util_rate_group_str` now calls `now = time.time()` independently
(`status-line.py:1667`), so a single logical render reads the wall clock twice. Only
one of the two candidate strings is ultimately selected by `util_first_fitting`, so
this currently has no observable effect on output — but it is new behavior introduced
by this phase (previously `util_rate_group_str` never touched the clock), and it means
the two discarded/kept candidates are not guaranteed to be computed against the same
`now`, which would become an actual (if vanishingly rare) correctness issue if either
candidate's rendering logic changes to ever combine or compare them in the future.
**Fix:** Thread a single `now = time.time()` value down from `seg_alt_h_rate_limit`/
`seg_alt_w_rate_limit` into both `util_rate_group_str` calls (e.g. add a `now: float`
parameter to `util_rate_group_str`, defaulting to `None` → `time.time()` for any other
direct callers) so one render reads the clock once.

### WR-03: `remaining_fraction > 1.0` and `remaining_fraction < 0.0` are silently conflated into the identical `1.0` clamp, losing the semantic distinction D-04's own text draws between them

**File:** `tools/status-line.py:1503-1504`
**Issue:** The code's single `if remaining_fraction < 0.0 or remaining_fraction > 1.0: remaining_fraction = 1.0` line is correct per D-04's letter (both boundaries get the same pct-unchanged fallback), but it means a genuine clock-skew/window-mismatch case (`remaining_fraction > 1.0`, e.g. `resets_at` 6h out on a 5h-keyed bucket) and a genuinely stale/expired bucket (`remaining_fraction < 0.0`) are now indistinguishable to any future maintainer reading the ratio's output alone — there is no log, metric, or comment at the call site distinguishing which fallback path fired. This is a minor diagnosability gap: if Anthropic's `resets_at` semantics ever drift (e.g. consistently sending a window-mismatched value), there is no signal in this code path to notice it.
**Fix:** Not required for correctness, but consider a one-line debug-only comment or (if this file has a debug/verbose flag elsewhere) a conditional stderr note distinguishing the two fallback reasons, to ease future diagnosis without changing the return value.

## Info

### IN-01: `util_rate_window_seconds` has no direct test for a plural-number-word key (e.g. `"two_weeks"`)

**File:** `tests/test_status_line.py:179-261` (`TestRateBurnRatio`)
**Issue:** The 13 `TestRateBurnRatio` tests cover `five_hour`/`seven_day` and the
one-sided-miss cases (`eleven_hour`, `five_fortnight`), but no test exercises a
non-`"hour"/"day"` unit (`week`/`weeks`/`month`/`months`) going through
`util_rate_window_seconds` successfully, despite `_UNIT_SECONDS` defining entries for
all four. This isn't a bug — the parsing logic is uniform across all eight `_UNIT_SECONDS` keys — but it's a minor coverage gap for a table that exists specifically to support bucket keys this project hasn't yet observed (per the plan's own deferred note on the month-scale assumption).
**Fix:** Add one assertion for `util_rate_window_seconds("two_weeks")` (or similar) to
exercise a second unit family beyond hour/day.

### IN-02: `abs(remaining_fraction) < 1e-9` uses `abs()` on a value that can no longer be negative at that point

**File:** `tools/status-line.py:1505`
**Issue:** By the time this line executes, the preceding `if remaining_fraction < 0.0 or remaining_fraction > 1.0: remaining_fraction = 1.0` has already eliminated every negative value (any negative value, including ones near zero, was just clamped to `1.0`). `abs()` is therefore a no-op here — harmless, but it reads as if negative near-zero values are still expected to reach this line, which (per WR-01) they cannot.
**Fix:** Drop `abs()` in favor of a plain `remaining_fraction < 1e-9` comparison, or add a one-line comment explaining why `abs()` is kept despite being currently redundant (e.g. "defensive, in case the clamp above is ever reordered").

---

_Reviewed: 2026-09-11T03:08:56Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
