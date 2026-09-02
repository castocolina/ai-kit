# Step 3 reference: Rounds 4–5 capability escalation

MANDATORY read before computing `$ESCALATION_EXCLUDE_JSON` or re-running `resolve-injection` with
`--escalation-excluded-keys-json`. This is the full math and reasoning for Rounds 4–5
capability escalation in Step 3 of `SKILL.md` — relocated here only so the top-level routing stays
short; every fact below is load-bearing and none of it is optional.

## When this applies, and why a plain ladder-exclusion walk is not enough

**Rounds 4–5 capability escalation (`mode == "external_cli"` only) — CRITICAL finding.** Applied at
the START of composing the dispatch prompt, immediately AFTER that round's `$FIX_ROUND` increment
(never before it — the check reads the POST-increment value) and BEFORE composing that round's
prompt, whenever `$FIX_ROUND >= 4` (i.e. `subagent-driven-development`'s own fix-loop, unmodified
per Step 4, has re-entered this dispatch point for the 4th or 5th time on this task) AND the mode in
play is `external_cli` (a `native_claude` fix-loop round is unchanged — its round 4/5 model-tier
bump is that skill's own `Agent`-tool dispatch judgment, made fresh each round exactly as
`subagent-driven-development`'s own Model Selection section already specifies, with no ladder
involved). `subagent-driven-development`'s own Model Selection section requires rounds 4–5 to
"dispatch a fresh implementer on a MORE CAPABLE model" — a genuine capability bump, not merely a
different one.

Naively excluding the stuck candidate's key and letting `resolve-injection` re-walk the ladder does
NOT guarantee this: the next surviving candidate by quota/affinity/context ranking could easily be
LESS capable than the one that got stuck. Today's config schema has no dedicated capability-tier
field (Global Constraints — `strength` is free text, not yet consumed by any resolution logic), so
this adapter uses the ladder's own established preference ordering (`policy.ladder`, authored
most-preferred-first — the same convention the GSD adapter's ladder walk already relies on, and the
same ordering `resolve-injection` already walks best-first) as the capability-tier proxy: only a
candidate ranked STRICTLY ABOVE the stuck candidate's own ladder position — never at the SAME
position, and never the stuck candidate itself — counts as a real capability bump. `resolve-
injection`'s JSON output (every mode, including `quota_exhausted`) now carries `ladder_keys` — the
full ranked candidate-key list `assemble_candidates` produced, BEFORE any `--exclude-keys-json`
filtering (Task 3, CRITICAL finding fix) — precisely so this computation is possible from data
`SKILL.md` already has:

```bash
LADDER_KEYS_JSON="$(python3 -c 'import json,sys; print(json.dumps(json.loads(sys.argv[1])["ladder_keys"]))' "$INJECTION_JSON")"
ESCALATION_EXCLUDE_JSON="$(python3 -c '
import json, sys
ladder = json.loads(sys.argv[1]); stuck = sys.argv[2]
idx = ladder.index(stuck) if stuck in ladder else len(ladder)
print(json.dumps(sorted(set(ladder[idx:]) | {stuck})))
' "$LADDER_KEYS_JSON" "$INJECTION_KEY")"
```

**CRITICAL finding (incomplete ladder, recurrence guard): `{stuck}` is unioned in explicitly, and
the not-found fallback is `len(ladder)` (exclude nothing extra), never `0` (exclude the WHOLE
ladder).** `$LADDER_KEYS_JSON` now comes from `compute_ladder_keys` (Task 2/3, CRITICAL finding
fix) — the full narrowed+ranked candidate set, not merely `policy.ladder`'s configured keys — so
`stuck` (`$INJECTION_KEY`) is expected to appear in it whenever the same task/config produced both.
But relying on that alone is fragile — a prior revision's `idx = ... if stuck in ladder else 0`
fallback had a real bug even independent of `ladder_keys`' own completeness: when `stuck` is absent
from `ladder`, `ladder[idx:]` excludes ladder MEMBERS only, and `stuck` itself, never being a
member, was never added to the exclude set at all — leaving the very candidate this round is
escalating away from immediately eligible for reselection. Explicitly unioning `{stuck}` closes
that regardless of whether `stuck` is found in `ladder`, and `len(ladder)` (rather than `0`) as the
not-found fallback avoids the OPPOSITE overcorrection — excluding the entire ladder when the index
is unknown, which would have blocked every real candidate, not just same-or-weaker ones.

## Re-running resolve-injection with the escalation floor

**CRITICAL finding (recurrence guard): `$ESCALATION_EXCLUDE_JSON` is passed ONLY via the new,
separate `--escalation-excluded-keys-json` argument, NEVER folded into `$EXCLUDED_KEYS_JSON` or
assigned back into it.** `$EXCLUDED_KEYS_JSON` keeps exactly the meaning `references/state-
management.md` defines for it — the recomputed union of `$PRIOR_EXCLUDED_KEYS_JSON` and
`$WAVE_TRIED_JSON`, the ONLY value ever passed as `--exclude-keys-json` — for this task's entire
lifetime, with no third exception carved out here. `$ESCALATION_EXCLUDE_JSON` is a different kind of
thing: every key in it is a healthy, never-attempted candidate excluded purely to enforce this
round's capability floor, not a candidate that was tried and failed — folding it into
`$EXCLUDED_KEYS_JSON` (a prior revision did exactly this) would make the very next union recompute
(Step 3's own mid-dispatch `"quota"` branch, or a resume re-entering Step 2) silently drop those
keys again, since neither `$PRIOR_EXCLUDED_KEYS_JSON` nor `$WAVE_TRIED_JSON` ever recorded them —
letting a later resolution re-select a same-or-weaker candidate this round explicitly ruled out.

Re-run `resolve-injection` with the SAME `--exclude-keys-json "$EXCLUDED_KEYS_JSON"` and
`--excluded-reasons-json "$EXCLUDED_REASONS_JSON"` this round already had, adding
`--escalation-excluded-keys-json "$ESCALATION_EXCLUDE_JSON"` (same call shape as Step 2's own
`resolve-injection` invocation, plus this one extra argument) — this excludes every
genuinely-tried-and-failed candidate exactly as before, AND every candidate ranked at-or-below the
stuck one — i.e. same-or-weaker — never just the stuck one alone. If it resolves to a real candidate
(`native_claude`/`external_cli`), that IS the capability-bumped implementer for this round: proceed
with the new injection WITHOUT reassigning `$EXCLUDED_KEYS_JSON`, framing the dispatch exactly as
`subagent-driven-development`'s own text requires: "A prior implementer attempted this task [N]
times; you own it now. Read the report file for what was tried."

**`$ESCALATION_EXCLUDE_JSON` needs no persistence across rounds or resumes to guarantee round 5
never regresses to a same-or-weaker candidate already ruled out in round 4**: it is recomputed from
scratch every time this check fires, purely from `$LADDER_KEYS_JSON` (stable for this task) and
THAT round's own freshly-resolved `$INJECTION_KEY` — and `$INJECTION_KEY` for round 5 can only be a
candidate this same rule already proved was ranked strictly above round 4's stuck candidate (or
round 4's escalation-bumped candidate itself, if it later failed and became round 5's own stuck
candidate) — so round 5's `idx` is never worse than round 4's, and round 5's freshly recomputed
`ladder[idx:]` is automatically at least as restrictive. A resume behaves the same way: Step 2
resolves fresh from `$PRIOR_EXCLUDED_KEYS_JSON` alone (no escalation floor), and if `$FIX_ROUND >=
4` still holds, this check re-fires against whatever `$INJECTION_KEY` Step 2 just landed on,
re-deriving the correct floor before that round's implementer is ever dispatched.

## If re-resolution reports quota_exhausted instead

**HIGH finding: this must not simply discard resumable state and the auto-wake.** Read
`any_quota_recoverable` from that result exactly as Step 2 does, and branch the same way:

- **`any_quota_recoverable == True`** — at least one of the more-capable candidates is only
  temporarily unavailable. This is genuinely time-bound, so treat it exactly like Step 2's own
  `any_quota_recoverable == True` branch, verbatim: merge this call's own `tried`/`reasons` into
  `$WAVE_TRIED_JSON`/`$WAVE_REASONS_JSON`, compute `$RESUME_EXCLUDED_KEYS_JSON` via
  `resume-exclusions` against `$PRIOR_EXCLUDED_KEYS_JSON`, write `$STATE_JSON` (including this
  round's own current `$FIX_ROUND`, already incremented) via `write-resumable-state`, and schedule
  the hourly `CronCreate` wake — THEN stop this wave. Never dispatch a same-or-weaker candidate as a
  substitute just because persistence happened; the capability-bump requirement is still unmet this
  round, resumable exactly as Step 2's own quota-exhaustion case is (see `references/state-
  management.md`).
- **`any_quota_recoverable == False`, or re-resolution finds no candidate at all** (the
  `no_candidate` mode — defined in Step 2, "If `INJECTION_MODE == "no_candidate"`") — no ruling or
  wait fixes this: no genuinely more-capable candidate is currently available for reasons waiting
  never resolves. Do **not** silently fall through to a same-or-weaker one, and do **not** schedule
  a futile `CronCreate` wake. STOP and report to the user, plainly, that rounds 4–5 cannot honor the
  capability-bump requirement with the currently configured/available ladder, reading
  `reasons`/`detail` off the result for exactly which candidates and why — justified on this
  adapter's own terms exactly as Step 2's own `any_quota_recoverable == False` branch is, not by
  claiming membership in `subagent-driven-development`'s own four stop-and-ask conditions verbatim.
  **MEDIUM finding: when the re-resolution narrowed the pool purely via
  `--escalation-excluded-keys-json` — the common case, where the stuck candidate is top-ranked and
  everything at-or-below it on the ladder is escalation-excluded, with nothing in
  `--exclude-keys-json` genuinely failed — `reasons`/`detail` come back empty by design
  (escalation-excluded keys never get a reason), so there is nothing to read off the result.** In
  that case, report instead that no candidate ranked above `$INJECTION_KEY` on the ladder is
  available for a fresh (non-escalation) pick — name the excluded keys from
  `$ESCALATION_EXCLUDE_JSON` (the same ladder keys this step passed as
  `--escalation-excluded-keys-json`) explicitly, so the user sees which candidates were excluded and
  why even though the result's own `reasons` map is empty.
