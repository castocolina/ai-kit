# Phase 8: Status-line Quota Color Refactor - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-10
**Phase:** 8-Status-line Quota Color Refactor
**Areas discussed:** Burn-rate formula, Edge cases, Where the logic lives

---

## Burn-rate formula

Options presented:
- Ratio into existing ramp (used% / elapsed%), reusing theme.ramps["rate"] unchanged (recommended)
- Difference (used% - elapsed%*100) mapped onto a new ramp with new thresholds

**User's choice:** Ratio into existing ramp (recommended option).
**Notes:** Verified arithmetically during discussion that this formula reproduces the roadmap's own worked example exactly against the unchanged existing ramp thresholds (50/80/inf): 50% used at hour 1-of-5 → ratio 250 → red; 30% used at hour 4-of-5 → ratio 37.5 → green.

---

## Edge cases

Options presented:
- elapsed=0 clamps to max urgency; past resets_at clamps to elapsed=1.0 (recommended, both)
- Something should differ (free text)

**User's choice:** Both as described (recommended option).

---

## Where the logic lives

Options presented:
- New upstream helper computes the ratio; util_rate_color stays unchanged (recommended)
- util_rate_color's signature changes to take resets_at/window-seconds directly

**User's choice:** New upstream helper (recommended option).

---

## Claude's Discretion

- Exact name of the new window-duration/ratio helper function.
- Exact clamp ceiling value for the elapsed=0 "top band" case.

## Deferred Ideas

None — discussion stayed within Phase 8 scope.
