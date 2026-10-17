# Step 3 reference: Rounds 4–5 capability escalation

MANDATORY read before computing `$ESCALATION_EXCLUDE_JSON` or re-running `resolve-injection` with
`--escalation-excluded-keys-json`. Every rule below is load-bearing.

## When it applies

Right after a fix round's `$FIX_ROUND` increment, before composing that round's prompt, whenever
`$FIX_ROUND >= 4` and the stuck dispatch cannot raise its own model:

- `external_cli` (a subprocess through the supervised runner), always;
- `native` on any host but Claude Code: those hosts run only their session default natively, so
  the native dispatch has no model to bump.

A `native` round on Claude Code is unchanged: its round 4/5 bump is subagent-driven-development's
own Model Selection judgment (the `Agent` tool's `model`), with no ladder. A custom entry (a
`command` and no `runtime`) never executes (`purpose = "execute"` exits 2 at `resolve-injection`,
otherwise it is skipped as `review_only`), so it never reaches this rule.

subagent-driven-development requires rounds 4–5 to "dispatch a fresh implementer on a MORE CAPABLE
model". Excluding the stuck key and re-walking the ladder does not guarantee that — the next
survivor may be weaker. The config has no capability-tier field (`strength` is free text, read by
no resolution logic), so the ladder order (`policy.ladder`, most-preferred first, the same order
`resolve-injection` walks) is the capability proxy: only a candidate ranked **strictly above** the
stuck one counts as a bump.

## The stuck key is the last dispatch, never this round's fresh pick

The floor is relative to `$LAST_DISPATCHED_KEY` — the key of the most recent `dispatch-task` for
this task (set after every dispatch in Step 3, persisted as `last_dispatched_key` in resumable
state, restored on resume; see `references/state-management.md`). Never use the `$INJECTION_KEY`
Step 2 just resolved: after a quota wait or a resume, that fresh pick can already be the
more-capable candidate, and a floor computed from it would exclude the very bump it found. Example:
ladder `A > B`, B is stuck, round 4 waits on quota-exhausted A; after the resume Step 2 picks A,
and a floor relative to A would exclude both and stop falsely.

```bash
LADDER_KEYS_JSON="$(python3 -c 'import json,sys; print(json.dumps(json.loads(sys.argv[1])["ladder_keys"]))' "$INJECTION_JSON")"
ESCALATION_EXCLUDE_JSON="$(python3 -c '
import json, sys
ladder = json.loads(sys.argv[1]); stuck = sys.argv[2]
idx = ladder.index(stuck) if stuck in ladder else len(ladder)
print(json.dumps(sorted(set(ladder[idx:]) | {stuck})))
' "$LADDER_KEYS_JSON" "$LAST_DISPATCHED_KEY")"
printf 'LADDER_KEYS_JSON=%s\nESCALATION_EXCLUDE_JSON=%s\n' "$LADDER_KEYS_JSON" "$ESCALATION_EXCLUDE_JSON"
```

`ladder_keys` is in every `resolve-injection` result (every mode, `quota_exhausted` included): the
full ranked candidate list before any exclusion. `{stuck}` is unioned in explicitly, so the stuck
key is excluded even when it is missing from `ladder_keys`; the not-found fallback is
`len(ladder)` (exclude nothing else), never `0` (which would exclude the whole ladder). When the
stuck key is missing from `ladder_keys` there is no order to bump along: the pick is only a
different candidate, not a verified bump — tell the user so.

## Re-running resolve-injection with the floor

Pass `$ESCALATION_EXCLUDE_JSON` **only** through `--escalation-excluded-keys-json`, never folded
into `$EXCLUDED_KEYS_JSON`. Its keys are healthy, never-tried candidates excluded only to enforce
the floor; `$EXCLUDED_KEYS_JSON` stays the union of `$PRIOR_EXCLUDED_KEYS_JSON` and
`$WAVE_TRIED_JSON`, and the next recompute of that union (a mid-dispatch quota retry, a resume)
would silently drop floor keys folded into it.

Re-run `resolve-injection` with this round's same `--exclude-keys-json` and
`--excluded-reasons-json`, plus `--escalation-excluded-keys-json "$ESCALATION_EXCLUDE_JSON"`. A real
candidate (`native` or `external_cli`) is this round's bumped implementer: dispatch it without
reassigning `$EXCLUDED_KEYS_JSON`, framed as subagent-driven-development requires: "A prior
implementer attempted this task [N] times; you own it now. Read the report file for what was
tried." A mid-dispatch quota retry in this round keeps passing the same floor.

The floor needs no separate persistence: it is recomputed every time from `$LADDER_KEYS_JSON` and
`$LAST_DISPATCHED_KEY`, and the latter is persisted. Round 5's stuck key is round 4's bumped
candidate, ranked above round 4's stuck key, so round 5's floor is at least as strict.

## If the re-resolution reports quota_exhausted or no_candidate

Read `any_quota_recoverable` exactly as Step 2 does:

- **`True`** — a more-capable candidate is only temporarily out of quota. Follow Step 2's
  recoverable branch: merge this result's `tried`/`reasons` into the wave sets, compute
  `$RESUME_EXCLUDED_KEYS_JSON` with `resume-exclusions`, write `$STATE_JSON` (with this round's
  `$FIX_ROUND` and `$LAST_DISPATCHED_KEY`) via `write-resumable-state`, schedule the wake, then
  stop the wave. Never dispatch a same-or-weaker candidate as a substitute.
- **`False`, or `no_candidate`** — no more-capable candidate is available, and waiting will not
  change that. Do not fall through to a same-or-weaker one and do not schedule a wake. STOP and
  tell the user that rounds 4–5 cannot honor the capability bump with the current ladder, reading
  `reasons`/`detail` for which candidates failed and why. When the pool was narrowed only by the
  floor (the stuck key is top-ranked), `reasons`/`detail` are empty by design: name the keys in
  `$ESCALATION_EXCLUDE_JSON` instead. For a native stuck dispatch on a non-Claude host, also say
  how to unblock it: switch this session to a more capable model and resume, or put a more capable
  routable pair above `$LAST_DISPATCHED_KEY` in `policy.ladder`. This stop is the adapter's own
  call, not one of subagent-driven-development's four stop-and-ask conditions.
