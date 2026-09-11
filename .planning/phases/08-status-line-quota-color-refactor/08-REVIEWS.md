---
phase: 8
reviewers: [opencode]
reviewed_at: 2026-09-11T01:29:02Z
plans_reviewed: [.planning/phases/08-status-line-quota-color-refactor/08-01-PLAN.md]
models:
  opencode: "xai/grok-4.6 (reasoning=high)"
model_sources:
  opencode: "pinned"
---

# Cross-AI Plan Review — Phase 8

## Plan-Revision Conflicts

None.

## OpenCode Review

## 08-01

### Summary

The plan hits the right call site (`util_rate_group_str` at `tools/status-line.py:1641`), leaves `util_rate_color` / `theme.ramps["rate"]` alone, and correctly rejects CONTEXT D-01's `* 100` formula. It will not satisfy ROADMAP SC1 as written: burn-rate (`pct / elapsed_fraction`) flags **early** identical usage as more urgent, not "less time left." Task 2 never asserts which bucket is redder, and SC4's required spike is missing — so the 50/80 ramp's blow-up in the first minutes of a window is unexamined.

### Strengths

- **Call site and color-only constraint match the code.** `util_rate_group_str` is the only caller of `util_rate_color` (`tools/status-line.py:1641`). Display still uses `round(pct)` and `suffix_fn(reset)` (`:1642-1643`); swapping the color input cannot change the percentage or reset suffix.
- **D-01 `* 100` correction is right.** `50 / (0.2 * 100) = 2.5` would land in GREEN (`util_pick_color` at `:1326-1328`, ramp at `:172`). `50 / 0.2 = 250` hits the last band. `pct / 1.0 == pct` is what makes D-04's "reduces to today's color" claim true.
- **D-04 plus unmocked `time.time()` keeps existing tests green.** Current rate-limit tests use `resets_at = NOW + …` with `NOW = 1_000_000` (`tests/test_status_line.py:38`, `:489-544`) and do **not** patch `time.time()`. Against a 2026 clock those stamps are already in the past, so the planned `elapsed_fraction >= 1.0 → return pct` path preserves today's colors. Assertions are `strip()`-based (`:490-544`), so even a real color shift would not fail them.
- **Line numbers and test-pattern correction check out.** `util_rate_color` `:1473`, `util_pick_color` `:1324`, `_RAMP_DEFAULTS["rate"]` `:172`, `fmt_rate_key_label` / `_NUM_WORDS` / `_UNIT_ABBR` `:1254-1272`, `INF` `:240`, `TestPickColor` `:136`, `TestCooperativeBuilders` `:361`, `test_render_time_colors_by_slo_sla_ramp` `:472` (render_time ramp, not rate). Extending `test_h_rate_limit_*` instead is the right move.
- **`now` on `util_rate_burn_ratio` matches how this file tests time.** Golden already patches `sl.time.time` to `NOW` (`:2559-2560`). Pure helper tests can pass `now=NOW` without a patch.
- **Arch and golden are safe without extra edits.** New `util_*` defs in banner 5 satisfy `tests/test_arch.py:316-343`. Golden compares stripped lines (`:2587`) and `alt_h_rate_limit` defaults off (`tools/status-line.py:84`).
- **Threat model is honest.** No new input, write, or trust boundary.

### Concerns

- **HIGH — SC1 and the formula point opposite ways.** ROADMAP SC1 (`ROADMAP.md:234`) and must-have truth 1 say the bucket with **less time left** is more urgent. The original todo uses the same example (80% with 5 minutes left vs 4 hours left). D-01 / Task 1 implement burn-rate. For identical 50% on `five_hour`:
  - `resets_at = NOW+3600*4` (4h left, elapsed 0.2) → ratio 250 → `RED+bold` (`:172`, `:1326-1328`)
  - `resets_at = NOW+3600` (1h left, elapsed 0.8) → ratio 62.5 → `YELLOW`
  Early/high remaining is redder. Task 2's `test_h_rate_limit_colors_by_urgency_not_raw_pct` only requires two different escapes, so both interpretations pass. D-01 is the discuss-phase lock; SC1/must-haves were not amended (`AGENTS.md` requires that when a verified fact contradicts ROADMAP/REQUIREMENTS).
- **MEDIUM — SC4 spike never happens.** ROADMAP SC4 (`:237`) and the source todo require a throwaway spike before locking the formula. The plan goes straight to helpers. Two arithmetic points do not show the 50/80 ramp's behavior at small elapsed: 5% used at 5 minutes of a 5h window is `5 / (300/18000) ≈ 300` → `RED+bold`. Near `elapsed_fraction == 0`, D-03 paints **any** nonzero `pct` max-red, including 1%. That may be intended; it is not demonstrated.
- **MEDIUM — `elapsed_fraction < 0` is treated as "window start."** If `resets_at - now > window_seconds` (clock skew, or a window longer than the key-derived duration), D-03 returns `INF`. Golden's own stamp shows the shape: `resets_at = 1750000000` vs `NOW = 1_000_000` (`tests/fixtures/golden/inputs.json:13`) would be hugely negative elapsed and max-red if that segment were on. Production skew of a minute at window open does the same for 1% usage. D-04's "don't invent urgency" stance is the better fallback here; the plan does not distinguish "exactly at start" from "model does not fit."
- **MEDIUM — Task 2 cannot put two `five_hour` keys in one dict.** The SC1 test must be two `seg_alt_h_rate_limit` calls (or two different hourly keys). The plan says "two five_hour buckets" without saying "two renders." An executor stuffing both into one `rate_limits` dict silently overwrites.
- **LOW — `util_rate_group_str`'s clock comment becomes stale.** `:1627-1630` says visibility never compares `resets_at` to the clock. After this change, **color** does. Leave the visibility rule; say that color now uses `time.time()`.
- **LOW — SC2 test as specified is weaker than SC2.** Existing rich-form checks are `assertIn` (`:491-495`), not full-string equality. Pinning SC2 needs the full stripped rich string (or equality with the pre-change output), not a restatement of `assertIn("5h: 42%", …)`.
- **LOW — `_UNIT_SECONDS` (3600/86400/604800/2592000) is a unit table, not a 5h/7d window constant.** That matches D-02. A pedantic SC3 reading still sees hardcoded seconds; CONTEXT already accepted this. Keep week as `7*86400` out of the table — the `7` must stay in `_NUM_WORDS["seven"]`.

### Suggestions

- Amend ROADMAP SC1 / REQUIREMENTS example / must-have 1 to: same `used_percentage`, **higher burn** (less elapsed fraction) is more urgent. Or change the formula to remaining-time urgency and rewrite Task 1's 50/20→250 cases. Do not ship both wordings.
- In Task 2, assert direction under `mock.patch.object(sl.time, "time", return_value=NOW)`: 50% / 4h remaining contains `THEME.c("RED+bold")`; 50% / 1h remaining contains `THEME.c("YELLOW")` and not red.
- State "two separate `seg_alt_h_rate_limit` calls," not two `five_hour` entries in one dict.
- Before locking D-03, tabulate `(pct, elapsed)` against the live ramp — 1% at t=0, 5% at 5 min, 50% at 1h, 30% at 4h, 50% at 5 min. That is the spike SC4 asked for; it can stay throwaway.
- If `elapsed_fraction < 0` (remaining > parsed window), return `pct` like D-04 instead of `INF`. Reserve the INF clamp for `elapsed_fraction == 0` (and maybe a tiny epsilon).
- SC2: `self.assertEqual(strip(rich), "<exact current rich string>")` using the `:488-495` fixture, with time mocked to `NOW`.
- After wiring color to `time.time()`, one sentence on the `:1627` comment: visibility still ignores the clock; color does not.

### Risk Assessment

**MEDIUM.** Scope is small, the call site is unique, D-05 and SC2 text-identity are mechanically sound, and existing `strip()` tests will not go red on Task 1. The phase still has a success-criteria fork (SC1 vs D-01) and no spike for the ratio's early-window cliff. Execution will implement burn-rate and can claim SC1 only by ignoring its wording. Resolve that in the plan (and ROADMAP) before coding.

---

## Consensus Summary

Only one reviewer lane (OpenCode, `xai/grok-4.6`, reasoning=high) ran for this cycle — `--opencode` was explicitly requested. The review is source-grounded, citing concrete `tools/status-line.py` and `tests/test_status_line.py` line numbers for every strength and concern, so findings are treated at full weight (no `[reviewed-without-repo-access]` or `[reviewed-without-source-citations]` marker present).

### Agreed Strengths
N/A — single reviewer this cycle; no cross-reviewer agreement to synthesize.

### Agreed Concerns
N/A — single reviewer this cycle; no cross-reviewer agreement to synthesize.

### Divergent Views
N/A — single reviewer this cycle.
