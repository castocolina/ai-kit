---
phase: 8
reviewers: [opencode]
reviewed_at: 2026-09-11T02:30:39Z
plans_reviewed: [.planning/phases/08-status-line-quota-color-refactor/08-01-PLAN.md]
models:
  opencode: "openai/gpt-5.6-sol (reasoning=high)"
model_sources:
  opencode: "fallback-billing-exhausted"
---

# Cross-AI Plan Review — Phase 8

<!-- gsd:plan-revision-conflicts:begin -->
## Plan-Revision Conflicts

- [x] REVISION_CONFLICT formula_direction/08-01 -- required_property: identical used_percentage with less time remaining renders a more urgent color than more time remaining, per ROADMAP SC1 | conflicts with: ROADMAP SC4's worked example plus CONTEXT.md D-01's locked burn-rate formula pct divided by elapsed_fraction, which is provably monotonically decreasing in elapsed_fraction for any fixed pct, the opposite direction | alternatives: keep the burn-rate formula and amend SC1's wording to a pace framing, or switch to pct divided by remaining fraction and rewrite SC4's worked example plus D-01; no single monotonic formula satisfies both as currently worded | resolved: switched to pct divided by remaining_fraction (1 - elapsed_fraction); SC1 is the authoritative, directly-testable "what must be TRUE" statement and is kept as-is; ROADMAP SC4's worked example and CONTEXT.md D-01/D-03/D-04 amended 2026-09-11 to match (see ROADMAP.md and 08-CONTEXT.md amendment notes)
<!-- gsd:plan-revision-conflicts:end -->

## Cycle 3 note on reviewer model substitution

Per this project's documented Rule 2 fallback (applied identically in cycle 2): before
invoking the review, the pinned `opencode` lane model
(`review.models.opencode: "xai/grok-4.6"` in `.planning/config.json`) was probed directly
with `opencode run --model xai/grok-4.6 "Reply with exactly: PONG"`. It failed with the
same provider-side billing error as cycle 2: `personal-team-blocked:spending-limit: You
have run out of credits or need a Grok subscription.` A fallback probe of
`opencode run --model openai/gpt-5.6-sol "Reply with exactly: PONG"` succeeded (`PONG`).

`.planning/config.json`'s `review.models.opencode` was temporarily set to
`openai/gpt-5.6-sol` for the one `review-lane invoke` call this cycle needed, then
restored immediately afterward to its original committed value (`xai/grok-4.6`) — verified
via `git diff --stat .planning/config.json` showing no diff after restoration. The
substitution is recorded in `model_sources` above as `fallback-billing-exhausted`, matching
cycle 2's convention, rather than silently reported as `"pinned"`.

## Verification performed before re-invoking the reviewer

Before spending a reviewer invocation, the four cycle-2 findings were independently
re-verified against the current file contents (not taken on faith from commit messages):

- **HIGH (ROADMAP.md SC4 worked example):** `ROADMAP.md:237` now reads the real ramp
  outputs — 50% usage with 4h remaining in a 5h window gives `50/0.8=62.5` → YELLOW; the
  same 50% with 1h remaining gives `50/0.2=250` → RED+bold. Confirmed fixed.
- **HIGH (REQUIREMENTS.md REQ-stln-time-relative-color):** `REQUIREMENTS.md:69` now states
  the same corrected, same-usage example matching the `pct / remaining_fraction` formula.
  Confirmed fixed.
- **MEDIUM (08-01-PLAN.md round-1 ledger wording):** the Round 1 ledger entry at
  `08-01-PLAN.md` (Review Dispositions Ledger) now explicitly notes the wording was
  corrected 2026-09-11 to describe `(pct, remaining_fraction)` pairs instead of
  `(pct, elapsed_fraction)` pairs. Confirmed fixed.
- **LOW (nonsense_unit one-sided isolation):** `08-01-PLAN.md`'s Task 1 behavior now lists
  `"eleven_hour"` (isolates the number-word lookup failing alone) and `"five_fortnight"`
  (isolates the unit-word lookup failing alone) alongside the original `"nonsense_unit"`
  (both lookups failing together). Confirmed fixed.

`08-CONTEXT.md`'s "Specific Ideas" section (flagged by cycle 2 as carrying stale prose at
the old ~181-185 line range) was also checked: it now reads "(Superseded 2026-09-11 — see
D-01's amendment note...)" followed by the corrected worked example. Confirmed fixed; no
stale formula prose remains there.

## OpenCode Review

## 08-01

### Summary

The plan covers the phase goal and all four cycle-2 corrections are present. The formula, production call path, edge behavior, and color-only isolation agree with the current source. However, two proposed integration tests calculate their expected color incorrectly, so the plan is not ready for execution without revision.

### Strengths

- **Formula and canonical artifacts now agree.** `ROADMAP.md` gives the realizable YELLOW/RED+bold example at `.planning/ROADMAP.md:234-238`; the requirement matches at `.planning/REQUIREMENTS.md:69`; and D-01 uses `pct / remaining_fraction` at `.planning/phases/08-status-line-quota-color-refactor/08-CONTEXT.md:23-29`. This matches the actual strict-upper-bound ramp at `tools/status-line.py:168-173` and `tools/status-line.py:1324-1329`.
- **The color-only change is correctly isolated.** The current renderer calculates color separately from `round(pct)` and the reset suffix at `tools/status-line.py:1638-1643`; the proposed call-site-only replacement at `08-01-PLAN.md:243-261` leaves displayed text untouched.
- **Cycle-2 ledger wording is corrected.** The round-1 spike disposition now consistently uses remaining-fraction pairs at `08-01-PLAN.md:398-400`.
- **One-sided parser failures are covered.** `"eleven_hour"` and `"five_fortnight"` independently exercise number and unit lookup misses at `08-01-PLAN.md:108-110`.
- **Edge handling is explicit.** Missing, stale, zero, full-window, and greater-than-one remaining fractions have defined behavior at `08-01-PLAN.md:113-116` and `08-01-PLAN.md:195-226`.
- **Architecture placement is correct.** The helpers are assigned to the existing `util_` block beginning at `tools/status-line.py:1275`, matching the enforced prefix rule at `tests/test_arch.py:316-352`.

### Concerns

- **HIGH: Two integration tests compute an empty expected color.** Location: `08-01-PLAN.md:325-346`. `theme.ramps["rate"]` already contains resolved ANSI escapes, so `util_pick_color(50, THEME.ramps["rate"])` returns `"\x1b[33m"` directly (`tools/status-line.py:1324-1329`, `tools/status-line.py:1852-1861`). Passing that escape into `THEME.c(...)` fails color-spec parsing and returns `""` (`tools/status-line.py:1777-1794`). Consequently, an equality assertion fails or an `assertIn("", output)` passes vacuously. Required: compare directly against `sl.util_rate_color(50, THEME)` or `sl.util_pick_color(50, THEME.ramps["rate"])`, following `tests/test_status_line.py:151-155`.
- **MEDIUM: The task is marked TDD but sequences implementation before tests.** Location: `08-01-PLAN.md:105`, `08-01-PLAN.md:171-268`. The action adds both helpers and changes the call site before adding `TestRateBurnRatio`, and verification only describes the final green run at `08-01-PLAN.md:270-273`. Required: after the spike, add the tests first, run them to establish the expected failure, then implement and rerun.
- **MEDIUM: The threat model incorrectly claims there is no input trust boundary.** Location: `08-01-PLAN.md:362-371`. Rate-limit keys and values originate in JSON read from stdin at `tools/status-line.py:2466-2478` and are copied into `Context.rate_limits` at `tools/status-line.py:1723-1758`. The proposed parser is safe because it uses bounded string operations and falls back on unknown values, but the input is still external to the renderer. Required: identify the existing stdin boundary and document the graceful unknown-key/type failure behavior rather than claiming no boundary exists.
- **LOW: The proposed 30-day month conversion invents duration semantics.** Location: `08-01-PLAN.md:171-184`. Existing month handling only abbreviates display text at `tools/status-line.py:1261-1272`; it does not establish that a month is exactly 2,592,000 seconds. Required: omit non-fixed month units and fall back to raw percentage unless an exact window duration is available.
- **LOW: Minor canonical wording remains stale.** Location: `.planning/REQUIREMENTS.md:69` names nonexistent `util_render_rate_limits`, while the real function is `util_rate_group_str` at `tools/status-line.py:1619`; `.planning/phases/08-status-line-quota-color-refactor/08-CONTEXT.md:12` still says "usage vs. elapsed-fraction" despite D-01 specifying remaining fraction at lines 23-26. Required: align these references with the implemented integration point and corrected divisor.

### Suggestions

- Replace both `THEME.c(sl.util_pick_color(...))` expressions with `sl.util_rate_color(50, THEME)`.
- Assert the expected escape is present and `THEME.c("RED+bold")` is absent in raw-percentage fallback cases.
- Reorder Task 1 into spike, failing tests, implementation, passing tests.
- Rewrite the threat boundary around externally supplied stdin JSON and the existing safe fallback.
- Remove the speculative month conversion and correct the two remaining canonical references.

### Risk Assessment

**HIGH.** The production formula and edge-case design are otherwise low-risk, but two tests intended to prove stale-reset and clock-skew fallback behavior currently cannot assert the expected color correctly. That leaves material behavior unverified while allowing a potentially vacuous test implementation.

### Status: Issues Found - fix and re-invoke

---

## Consensus Summary

Only one reviewer lane (OpenCode, `openai/gpt-5.6-sol`, reasoning=high — substituted in-run for the configured `xai/grok-4.6`, which is blocked by a provider billing/credit limit; see the substitution note above) ran for this cycle — `--opencode` was explicitly requested. The review is source-grounded, citing concrete `tools/status-line.py`, `tests/test_status_line.py`, `ROADMAP.md`, `REQUIREMENTS.md`, and `08-01-PLAN.md` line numbers for every strength and concern, so findings are treated at full weight. Independent re-derivation during REVIEWS.md assembly confirmed the reviewer's core claim: `theme.ramps["rate"]` stores pre-resolved ANSI escapes (`tools/status-line.py`'s `Theme` docstring: "ramps band -> [(ceil, escape)]"), so `util_pick_color(50, THEME.ramps["rate"])` returns an already-resolved escape such as `"\x1b[33m"`; feeding that string into `Theme.c(spec)` (`util_parse_color`) fails every branch (not `#`, not alpha-leading for a palette-name lookup, not a bare `[0-9;]+` SGR-params string because of the leading `\x1b[` and trailing `m`) and returns `None`, which `Theme.c` converts to `""` via its `or ""` fallback. The two integration test assertions at `08-01-PLAN.md:325-346` genuinely double-wrap the already-resolved color through `THEME.c(...)`, and the HIGH finding is confirmed as a real, reproducible defect in the plan's proposed test code — not yet present in `tools/status-line.py` itself, which this phase has not yet touched.

All four cycle-2 findings (2 HIGH, 1 MEDIUM, 1 LOW) were independently re-verified against the current file contents before this cycle's reviewer was invoked, and are confirmed resolved: `ROADMAP.md:237`'s SC4 worked example now matches the real ramp outputs; `REQUIREMENTS.md:69`'s `REQ-stln-time-relative-color` now states the same corrected example; `08-01-PLAN.md`'s round-1 ledger entry now describes `(pct, remaining_fraction)` pairs; and the `nonsense_unit` test now has two additional one-sided cases (`"eleven_hour"`, `"five_fortnight"`). `08-CONTEXT.md`'s previously-stale "Specific Ideas" prose is also now corrected.

This cycle's reviewer surfaced one NEW HIGH (the double-wrapped-color test defect above) plus two MEDIUM findings (TDD task-ordering sequencing; an arguable trust-boundary omission in the threat model — the plan treats `used_percentage`/`resets_at` as already-trusted renderer inputs sourced from Claude's own rate-limit context rather than raw attacker-controlled data, which is a defensible but debatable position) and two LOW findings (a speculative exact-30-day month-duration assumption; two remaining stale cross-references — a nonexistent `util_render_rate_limits` name in `REQUIREMENTS.md:69`, and lingering "elapsed-fraction" phrasing in `08-CONTEXT.md:12`'s domain summary that predates D-01's correction). None of these were present in the cycle-2 report; they were introduced by, or survived through, the interim fix pass between cycle 2 and cycle 3.

**Convergence status: NOT YET CONVERGED.** This is the third and final allowed review cycle for Phase 8 (`max_cycles=3`). One HIGH concern remains open — the plan's proposed integration tests at `08-01-PLAN.md:325-346` must be corrected before execution, as currently written they would either fail for the wrong reason or pass vacuously against an empty-string comparison. Per this project's convergence policy, further review cycles are not available; the remaining HIGH and the actionable MEDIUM/LOW findings should be addressed directly during execution (or via a manual fix-and-verify pass) rather than through another `/gsd-review` cycle.

### Agreed Strengths
N/A — single reviewer this cycle; no cross-reviewer agreement to synthesize.

### Agreed Concerns
N/A — single reviewer this cycle; no cross-reviewer agreement to synthesize.

### Divergent Views
N/A — single reviewer this cycle.
