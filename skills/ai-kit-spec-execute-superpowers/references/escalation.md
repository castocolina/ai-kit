# Step 3 reference: Rounds 4–5 capability escalation

MANDATORY read before computing `$ESCALATION_EXCLUDE_JSON` or re-running `resolve-injection` with
`--escalation-excluded-keys-json`. Every rule below is load-bearing.

## When it applies

Right after a fix round's `$FIX_ROUND` increment, before composing that round's prompt, and on a
resume that re-enters Step 2 with a restored `$FIX_ROUND` (no increment then, so the rule must be
applied here before any dispatch), whenever `$FIX_ROUND >= 4` and the stuck dispatch cannot raise
its own model:

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

## The stuck key is the round-start anchor, never this round's fresh pick

The floor is relative to `$ESCALATION_ANCHOR_KEY` — `$LAST_DISPATCHED_KEY` copied once when this
fix round started (the dispatch whose report the round is fixing), persisted as
`escalation_anchor_key` and restored on resume (`references/state-management.md`). There is no
same-round retry: a failed dispatch stops, and the anchor stays the key the round started from, so
a bumped candidate that later hits quota stays eligible once its quota recovers. Never use the
`$INJECTION_KEY` Step 2 just resolved: after a quota wait or an owner resume, that fresh pick can
already be the more-capable candidate, and a floor computed from it would exclude the very bump it
found. Example:
ladder `A > B`, B is stuck, round 4 waits on quota-exhausted A; after the resume Step 2 picks A,
and a floor relative to A would exclude both and stop falsely.

**An empty or unknown anchor never dispatches.** When `$ESCALATION_ANCHOR_KEY` is empty (an old
state file) or missing from `ladder_keys` (the config changed), there is no order to bump along,
so no pick is a verified bump. Do not re-run `resolve-injection` for this round. STOP and ask the
user to name a candidate from `ladder_keys` they judge more capable than the stuck implementer,
or to stop. Only on an explicit pick, write every other `ladder_keys` entry to
`$RUN_DIR/ESCALATION_EXCLUDE_JSON.json`, run the block under "Re-running resolve-injection with the
floor" and dispatch it as a user-chosen bump.

Otherwise compute the floor:

```bash
INJECTION_JSON="$(cat "$RUN_DIR/INJECTION_JSON.json")"
LADDER_KEYS_JSON="$(python3 -c 'import json,sys; print(json.dumps(json.loads(sys.argv[1])["ladder_keys"]))' "$INJECTION_JSON")"
ESCALATION_EXCLUDE_JSON="$(python3 -c '
import json, sys
ladder = json.loads(sys.argv[1]); stuck = sys.argv[2]
idx = ladder.index(stuck) if stuck in ladder else len(ladder)
print(json.dumps(sorted(set(ladder[idx:]) | {stuck})))
' "$LADDER_KEYS_JSON" "$ESCALATION_ANCHOR_KEY")"
printf '%s' "$ESCALATION_EXCLUDE_JSON" > "$RUN_DIR/ESCALATION_EXCLUDE_JSON.json"
echo "ESCALATION_EXCLUDE_JSON saved to $RUN_DIR/ESCALATION_EXCLUDE_JSON.json"
```

`ladder_keys` is in every `resolve-injection` result (every mode, `quota_exhausted` included): the
full ranked candidate list before any exclusion. `{stuck}` is unioned in explicitly, so the stuck
key is excluded even when it is missing from `ladder_keys`; the not-found fallback is
`len(ladder)` (exclude nothing else), never `0` (which would exclude the whole ladder).

## Re-running resolve-injection with the floor

Pass `$ESCALATION_EXCLUDE_JSON` **only** through `--escalation-excluded-keys-json`, never folded
into `$EXCLUDED_KEYS_JSON`. Its keys are healthy, never-tried candidates excluded only to enforce
the floor; `$EXCLUDED_KEYS_JSON` stays the union of `$PRIOR_EXCLUDED_KEYS_JSON` and
`$WAVE_TRIED_JSON`, and the next recompute of that union (a mid-dispatch quota retry, a resume)
would silently drop floor keys folded into it.

Run this variant of Step 2's `resolve-injection` block (rounds 1–3 run no resolution and reuse
`$INJECTION_JSON`). It is the same block plus `--escalation-excluded-keys-json`; use it as
printed (it loads the task's current JSON files):

```bash
PRIOR_REASONS_JSON="$(cat "$RUN_DIR/PRIOR_REASONS_JSON.json")"
WAVE_REASONS_JSON="$(cat "$RUN_DIR/WAVE_REASONS_JSON.json")"
EXCLUDED_KEYS_JSON="$(cat "$RUN_DIR/EXCLUDED_KEYS_JSON.json")"
ESCALATION_EXCLUDE_JSON="$(cat "$RUN_DIR/ESCALATION_EXCLUDE_JSON.json")"
EXCLUDED_REASONS_JSON="$(python3 -c 'import json,sys; a=json.loads(sys.argv[1]); a.update(json.loads(sys.argv[2])); print(json.dumps(a))' \
  "$PRIOR_REASONS_JSON" "$WAVE_REASONS_JSON")"
INJECTION_JSON="$(python3 "$SHIM" resolve-injection --cwd "$CWD" --task-file "$BRIEF_FILE" \
  --quota-path "$QUOTA_PATH" --exclude-keys-json "$EXCLUDED_KEYS_JSON" \
  --excluded-reasons-json "$EXCLUDED_REASONS_JSON" \
  --escalation-excluded-keys-json "$ESCALATION_EXCLUDE_JSON")"
INJECTION_RC=$?
[ "$INJECTION_RC" -eq 0 ] || { echo "resolve-injection exit $INJECTION_RC"; exit "$INJECTION_RC"; }
printf '%s' "$INJECTION_JSON" > "$RUN_DIR/INJECTION_JSON.json"
INJECTION_MODE="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["mode"])' "$INJECTION_JSON")"
printf 'INJECTION_MODE=%s\n' "$INJECTION_MODE" | tee -a "$SCALARS"
```

Then handle the result exactly as Step 2 does (the `resolve-injection exit 2` stop, the untrusted
config line, the `INJECTION_KEY`/`INJECTION_RUNTIME` block). A real candidate (`native` or
`external_cli`) is this round's bumped implementer: dispatch it without reassigning
`$EXCLUDED_KEYS_JSON`, framed as subagent-driven-development requires: "A prior implementer
attempted this task [N] times; you own it now. Read the report file for what was tried." Report
the pick as ranked above the anchor in `policy.ladder`: its greater capability is inferred from
that order, not verified. This run is the pre-dispatch choice for a fix round, not a recovery
from a failed dispatch: a dispatch that then fails does not re-enter it (NEVER index; Step 3's
`"quota"` and `"real_error"` branches decide the stop or the one-shot wake).

The floor needs no separate persistence: it is recomputed every time from `$LADDER_KEYS_JSON` and
`$ESCALATION_ANCHOR_KEY`, and the latter is persisted. Round 5's stuck key is round 4's bumped
candidate, ranked above round 4's stuck key, so round 5's floor is at least as strict.

## If the re-resolution reports quota_exhausted or no_candidate

Read `any_quota_recoverable` exactly as Step 2 does:

- **`True`** — a more-capable candidate is only temporarily out of quota. Follow Step 2's
  recoverable branch: merge this result's `tried`/`reasons` into the wave sets, compute
  `$RESUME_EXCLUDED_KEYS_JSON` with `resume-exclusions`, write `$STATE_JSON` (with this round's
  `$FIX_ROUND`, `$LAST_DISPATCHED_KEY` and `$ESCALATION_ANCHOR_KEY`) via `write-resumable-state`,
  then stop the wave for a later re-run by the owner (which keys come back, and the permanent exclusion of the rest: Step 2). Never
  dispatch a same-or-weaker candidate as a substitute.
- **`False`, or `no_candidate`** — no more-capable candidate is eligible for automatic quota
  recovery (Step 2's `False` branch: this stop writes no resumable-state file; the round and anchor scalars persist, so the re-invoke keeps the floor). Do not fall through to a same-or-weaker one. Nothing is scheduled. STOP and
  tell the user that rounds 4–5 cannot honor the capability bump with the current ladder, reading
  `reasons`/`detail` for which candidates failed and why. When the pool was narrowed only by the
  floor (the stuck key is top-ranked), `reasons`/`detail` are empty by design: name the keys in
  `$ESCALATION_EXCLUDE_JSON` instead. For a native stuck dispatch on a non-Claude host, also say
  how to unblock it: put a more capable routable pair above `$ESCALATION_ANCHOR_KEY` in
  `policy.ladder`, then resume. Switching this session's model does not help: the session default
  keeps its ladder key, which the floor still excludes. This stop is the adapter's own
  call, not one of subagent-driven-development's four stop-and-ask conditions.
