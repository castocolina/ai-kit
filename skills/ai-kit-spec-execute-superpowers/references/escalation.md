# Step 3 reference: Rounds 4–5 capability escalation

MANDATORY read before computing `$ESCALATION_EXCLUDE_JSON` or re-running `resolve-injection` with
`--escalation-excluded-keys-json`. Every rule below is load-bearing.

## When it applies

Right after a fix round's `$FIX_ROUND` increment, before composing that round's prompt, and on a
resume with no pinned `injection_json` that re-enters Step 2 with a restored `$FIX_ROUND` (no
increment then; the restore rule is [`state-management.md#pinned-resume`](state-management.md#pinned-resume)), whenever `$FIX_ROUND >= 4` and the stuck dispatch cannot raise
its own model:

- `external_cli` (a subprocess through the supervised runner), always;
- `native` on any host but Claude Code: those hosts run only their session default natively, so
  the native dispatch has no model to bump.

A `native` round on Claude Code is unchanged: its round 4/5 bump is subagent-driven-development's
own Model Selection judgment (the `Agent` tool's `model`), with no ladder. A custom entry (a
`command` and no `runtime`) never executes (`purpose = "execute"` exits 2 at `resolve-injection`,
otherwise it is skipped with route `no_formula`: a custom lane runs in review mode only), so it never reaches this rule. A task whose injection carries `"fallback": "session"` runs rounds 4 and 5 like session-model mode: no ladder escalation and no empty-anchor stop; the round dispatches natively on the same injection again (`SKILL.md` Step 3).

subagent-driven-development requires rounds 4–5 to "dispatch a fresh implementer on a MORE CAPABLE
model". Excluding the stuck key and re-walking the ladder does not guarantee that — the next
survivor may be weaker. The config has no capability-tier field (`strength` is free text, read by
no resolution logic), so the execute order (`ladder_keys`: the `[lanes.policy.execute]` ladder,
most-preferred first, then any unlisted execute lane, the same order `resolve-injection` walks) is
the capability proxy: only a candidate ranked **strictly above** the stuck one counts as a bump.

## The stuck key is the round-start anchor, never this round's fresh pick

The floor is relative to `$ESCALATION_ANCHOR_KEY` — `$LAST_DISPATCHED_KEY` copied once when this
fix round started (the dispatch whose report the round is fixing), persisted as
`escalation_anchor_key` and restored on resume (`references/state-management.md`). There is no
same-round retry: a failed dispatch stops (except the flagged-lane switch, which at rounds 4–5 moves only to a lane this round's gate allowed, of
[resolution-stops.md](resolution-stops.md#owner-stop)), and the anchor stays the key the round started from, so
a bumped candidate that later hits quota stays eligible once its quota recovers. Never use the
`$INJECTION_KEY` Step 2 just resolved: after a quota wait or an owner resume, that fresh pick can
already be the more-capable candidate, and a floor computed from it would exclude the very bump it
found. Example:
ladder `A > B`, B is stuck, round 4 waits on quota-exhausted A; after the resume Step 2 picks A,
and a floor relative to A would exclude both and stop falsely.

**An empty or unknown anchor never dispatches.** The stop is decided in [`resolution-stops.md#owner-stop`](resolution-stops.md#owner-stop) ("Rounds 4–5 re-resolution"); this paragraph holds only the owner-pick mechanics. Only on an explicit pick, delete any `$RUN_DIR/ESCALATION_ALLOWED_JSON.json` (a stale gate result), write every other `ladder_keys` entry to
`$RUN_DIR/ESCALATION_EXCLUDE_JSON.json`, run the block under "Re-running resolve-injection with the
floor" and dispatch it as a user-chosen bump only when `$INJECTION_KEY` equals the picked key (any other result is an owner stop; the allowed-key check below belongs to the automatic round only).

Otherwise run the escalation gate. It reads the anchor lane's `escalate_runtime` and `escalate_model` flags from the live roster and writes the keys this round must not take and the keys it may take:

```bash
python3 "$SHIM" escalation-gate --cwd "$CWD" --anchor-key "$ESCALATION_ANCHOR_KEY" \
  --injection-file "$RUN_DIR/INJECTION_JSON.json" --out-dir "$RUN_DIR" || exit $?
echo "ESCALATION_EXCLUDE_JSON saved to $RUN_DIR/ESCALATION_EXCLUDE_JSON.json"
```

`escalation-gate` reads `ladder_keys` from the saved injection file (every `resolve-injection` result carries it) and prints `escalate`, `allowed`, `exclude` and `reason`; only on success does it write `ESCALATION_EXCLUDE_JSON.json` and `ESCALATION_ALLOWED_JSON.json` into `$RUN_DIR`, and a failed write removes both, so no mixed or stale pair is left. `exclude` is every key of the live execute roster and of `ladder_keys` except the allowed ones, so a lane added since the ladder was saved is never picked. With both flags on, the allowed keys are every key ranked above the anchor: the capability floor. With one flag, only keys ranked strictly above the anchor whose kind matches stay allowed, nearest first: `escalate_runtime` keeps another runtime, `escalate_model` the anchor's runtime with another model. With both off, or no key above that matches, `escalate` is false, stderr says `ai-kit-spec: fix round stays on <anchor>: ...` and only the anchor is allowed, so the re-resolve below picks the anchor's own lane. An empty or unknown anchor (missing from `ladder_keys` or from the live execute roster) exits 3 with the STOP line and writes nothing; a non-boolean flag, or an unreadable injection file (not a JSON object with a `ladder_keys` list of strings), exits 2 and writes nothing.

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
  --escalation-excluded-keys-json "$ESCALATION_EXCLUDE_JSON" --fix-round "${FIX_ROUND:-0}" --no-fallback)"
INJECTION_RC=$?
[ "$INJECTION_RC" -eq 0 ] || { echo "resolve-injection exit $INJECTION_RC"; exit "$INJECTION_RC"; }
printf '%s' "$INJECTION_JSON" > "$RUN_DIR/INJECTION_JSON.json"
INJECTION_MODE="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["mode"])' "$INJECTION_JSON")"
printf 'INJECTION_MODE=%s\n' "$INJECTION_MODE" | tee -a "$SCALARS"
```

Then handle the result exactly as Step 2 does (the `resolve-injection exit 2` stop and the untrusted
config line in `references/resolution-stops.md`, the `INJECTION_KEY`/`INJECTION_RUNTIME` block). A real candidate (`native` or `external_cli`) of the automatic round (the gate ran this round) must be a key the gate allowed: run the check block below first; the owner-directed paths (the owner pick above and `state-management.md`'s "Owner-named replacement pair") delete any `ESCALATION_ALLOWED_JSON.json` before their re-resolve and check that `$INJECTION_KEY` equals the owner's named key instead. When the gate printed `escalate` true, the pick is this round's bumped implementer: dispatch it without reassigning
`$EXCLUDED_KEYS_JSON`, framed as subagent-driven-development requires: "A prior implementer
attempted this task [N] times; you own it now. Read the report file for what was tried." Report
the pick as ranked above the anchor in the execute order: its greater capability is inferred from that order, not verified. When the gate printed `escalate` false, the pick is the anchor's own lane: the same lane, not a bump; dispatch it as a normal fix round and tell the owner the stuck task stays on its lane, naming the task. This run is the pre-dispatch choice for a fix round, not a recovery
from a failed dispatch: a dispatch that then fails does not re-enter it (NEVER index; [`resolution-stops.md#owner-stop`](resolution-stops.md#owner-stop) decides the stop or the one-shot wake).

```bash
ALLOWED_KEYS="$(cat "$RUN_DIR/ESCALATION_ALLOWED_JSON.json")"
python3 -c 'import json,sys; sys.exit(0 if sys.argv[2] in json.loads(sys.argv[1]) else 1)' "$ALLOWED_KEYS" "$INJECTION_KEY" || { echo "STOP: $INJECTION_KEY is not a key the escalation gate allowed"; exit 1; }
```

A non-zero exit is an owner stop ([`resolution-stops.md#owner-stop`](resolution-stops.md#owner-stop)).

The floor needs no separate persistence: it is recomputed every time by `escalation-gate` from the saved `ladder_keys` and
`$ESCALATION_ANCHOR_KEY`, and the latter is persisted. Round 5's stuck key is round 4's bumped
candidate, ranked above round 4's stuck key, so round 5's floor is at least as strict.

## If the re-resolution reports quota_exhausted or no_candidate

Read `any_quota_recoverable` and stop exactly as [`resolution-stops.md#owner-stop`](resolution-stops.md#owner-stop) says under "Rounds 4–5 re-resolution".
