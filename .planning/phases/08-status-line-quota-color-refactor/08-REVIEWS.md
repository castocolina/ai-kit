---
phase: 8
reviewers: [opencode]
reviewed_at: 2026-09-11T02:14:27Z
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

## Cycle 2 note on reviewer model substitution

The configured `opencode` lane model (`review.models.opencode: "xai/grok-4.6"` in
`.planning/config.json`) failed outright on invocation this cycle with a billing
error from the provider (`personal-team-blocked:spending-limit: You have run out
of credits or need a Grok subscription`), confirmed by a direct
`opencode run --model xai/grok-4.6` probe before falling back. This is a genuine
provider-side block, not a sandbox/repo-access denial. To avoid reporting a false
"no concerns" result for a lane that never actually read the plan, the `opencode`
CLI was re-invoked for this one run with `openai/gpt-5.6-sol` substituted as the
model (confirmed working via a direct probe first), with `.planning/config.json`
restored to its original pinned value (`xai/grok-4.6`) immediately afterward — no
net change to the repo's committed config. The substitution is recorded in
`model_sources` above rather than silently reported as `"pinned"`.

## OpenCode Review

## 08-01

### Summary

The implementation steps are technically sound: `pct / remaining_fraction` satisfies SC1 for the planned fixtures, and the D-03/D-04 guards are ordered correctly. All six cycle-1 fixes remain present. However, convergence is incomplete because the amended ROADMAP example and the canonical requirement still contradict the corrected formula and unchanged ramp.

### Strengths

- **SC1 formula direction is correct.** The default ramp is GREEN below 50, YELLOW below 80, then RED+bold (`tools/status-line.py:168-173`), with strict upper-bound selection (`tools/status-line.py:1324-1329`). Direct execution confirmed 50% with 4h remaining gives `50 / 0.8 = 62.5` → YELLOW, while 1h remaining gives `50 / 0.2 = 250` → RED+bold. This matches the direction asserted by `08-01-PLAN.md:291-307`.
- **The color-only mechanism is well isolated.** The current renderer selects color from `pct` separately from `round(pct)` and the reset suffix (`tools/status-line.py:1638-1643`). Replacing only the value passed to `util_rate_color` as directed by `08-01-PLAN.md:243-253` preserves displayed text.
- **D-03 and D-04 are correctly placed after the formula flip.** The plan handles invalid negative and greater-than-one remaining fractions first by restoring `1.0`, then handles zero with `INF` (`08-01-PLAN.md:203-226`). This agrees with the amended decisions at `08-CONTEXT.md:67-91` and prevents stale or skewed data from becoming max-red.
- **The six prior actionable findings remain addressed.** The spike is mandatory before implementation (`08-01-PLAN.md:119-169`); separate same-key renders are explicit (`:291-301`); the clock comment is updated (`:254-261`); SC2 uses full-string equality (`:313-323`); clock skew receives raw-pct fallback coverage (`:337-346`); and `_UNIT_SECONDS` is explicitly limited to generic unit conversion (`:171-184`).
- **Existing architecture and test patterns support the plan.** Rate boundaries already have exact 50/80 coverage (`tests/test_status_line.py:151-155`), deterministic rendering patches `time.time()` (`tests/test_status_line.py:2555-2566`), and the role-prefix check accepts the planned `util_` functions in block 5 (`tests/test_arch.py:316-352`).

### Concerns

- **HIGH: The amended SC4 example is impossible under the locked ramp.** `ROADMAP.md:237` says 50% with 4h remaining reads red and 1h remaining reads an "even more urgent color." Actual arithmetic gives YELLOW then RED+bold, and RED+bold is already the final band (`tools/status-line.py:172`, `tools/status-line.py:1324-1329`). This directly contradicts the plan's correct expectations at `08-01-PLAN.md:110-112`.
- **HIGH: The canonical requirement still specifies the superseded direction.** `REQUIREMENTS.md:69` says usage near window start reads red while lower usage late can read green/blue. Under the corrected formula, urgency rises as remaining time shrinks. The plan nevertheless claims full requirement satisfaction at `08-01-PLAN.md:381-385`. The repository instructions require formally amending REQUIREMENTS when verified facts contradict it.
- **MEDIUM: Stale formula prose remains in phase artifacts.** `08-CONTEXT.md:181-185` retains the old early-red/late-green example, while the round-1 ledger still describes `(pct, elapsed_fraction)` rather than the current remaining-fraction matrix (`08-01-PLAN.md:398-405`). The executable task is clear, but these passages can mislead future reviewers.
- **LOW: The unknown-key test does not independently exercise both lookup failures.** `"nonsense_unit"` misses both `_NUM_WORDS` and the unit table (`08-01-PLAN.md:109`), while the implementation contract requires fallback when either lookup fails (`:187-193`). A one-sided implementation error could escape that test.

### Suggestions

- Amend `ROADMAP.md:237` to the values the real ramp produces: 50% with 4h remaining is YELLOW; the same 50% with 1h remaining is RED+bold.
- Amend `REQUIREMENTS.md:69` and `08-CONTEXT.md:181-185` to use the same corrected, same-percentage example.
- Update the round-1 ledger wording from elapsed-fraction pairs to remaining-fraction pairs and correct its matrix count.
- Add separate parser cases such as `"eleven_hour"` and `"five_fortnight"`.

### Risk Assessment

**HIGH.** The code plan itself is low-risk and the original formula-direction defect is resolved against SC1. The overall Plan-Revision Conflict is **not fully resolved**, because the revised ROADMAP example is incompatible with the actual ramp and REQUIREMENTS still carries the superseded behavior. Fix those canonical artifacts before execution.

---

## Consensus Summary

Only one reviewer lane (OpenCode, `openai/gpt-5.6-sol`, reasoning=high — substituted in-run for the configured `xai/grok-4.6`, which is blocked by a provider billing/credit limit; see the substitution note above) ran for this cycle — `--opencode` was explicitly requested. The review is source-grounded, citing concrete `tools/status-line.py`, `tests/test_status_line.py`, `ROADMAP.md`, and `REQUIREMENTS.md` line numbers for every strength and concern, so findings are treated at full weight (no `[reviewed-without-repo-access]` or `[reviewed-without-source-citations]` marker present). Independent verification during REVIEWS.md assembly confirmed the reviewer's core arithmetic: `50/0.8 = 62.5` (YELLOW) and `50/0.2 = 250` (RED+bold) against the unchanged `theme.ramps["rate"]` thresholds at `tools/status-line.py:168-173`/`1324-1329`, and confirmed `REQUIREMENTS.md:69` still reads the pre-amendment burn-pace example verbatim.

The net effect: the formula-direction defect that cycle 1 flagged as a `REVISION_CONFLICT` is correctly fixed in the code-facing artifacts (CONTEXT.md D-01/D-03/D-04, and 08-01-PLAN.md's own tasks), but the 2026-09-11 amendment pass that was supposed to close that conflict did not fully propagate: ROADMAP.md's SC4 worked example now asserts a qualitative outcome ("4h remaining reads red, 1h remaining reads even more urgent than red") that is arithmetically impossible against the real 3-band ramp and the corrected formula, and REQUIREMENTS.md's REQ-stln-time-relative-color was never touched at all and still states the original, SC1-incompatible burn-pace example. This is a new, narrower conflict than cycle 1's: the *formula* is now right, but two of the three locked planning documents describing it are not internally consistent with either the formula or each other.

### Agreed Strengths
N/A — single reviewer this cycle; no cross-reviewer agreement to synthesize.

### Agreed Concerns
N/A — single reviewer this cycle; no cross-reviewer agreement to synthesize.

### Divergent Views
N/A — single reviewer this cycle.
