# Step 2 reference: exclusion-set state management

MANDATORY read before writing to, or reading from, `$EXCLUDED_KEYS_JSON` / `$EXCLUDED_REASONS_JSON`
or the resumable-state JSON file. Every rule below is load-bearing.

## The variable set

Each value is this task's own state, re-`printf`'d after every change and re-substituted
literally into the next call (Step 0's convention: every `Bash` call starts a fresh shell).

`$EXCLUDED_KEYS_JSON` is a working union of two differently-sourced sets. **Never persist it
wholesale as `excluded_keys`**: a same-wave `"quota"` exclusion would then look permanent and stay
locked out after a resume. Track the inputs separately for the task's whole lifetime:

- `$PRIOR_EXCLUDED_KEYS_JSON` — the permanent exclusions this task resumed with (`'[]'` for a new
  task): `resume-exclusions`' output from an earlier wave, already stripped of every `"quota"` key.
  It changes only across a resume.
- `$PRIOR_REASONS_JSON` — `{key: reason}` for every key in `$PRIOR_EXCLUDED_KEYS_JSON`, restored
  from the same state file (`'{}'` for a new task). Without it, `resolve-injection` reports every
  excluded key it has no reason for as the generic `"no_usable_dispatch"`, replacing a real
  `"auth"` or `"configuration"` in the report the user acts on. It changes only across a resume.
- `$WAVE_TRIED_JSON` / `$WAVE_REASONS_JSON` — every key tried and rejected during this live wave
  (a `resolve-injection` result's `tried`/`reasons` on `quota_exhausted`, and a mid-dispatch
  `"quota"` failure in Step 3), with its reason. Reset to `'[]'`/`'{}'` for a new task and on
  every resume.
- `$EXCLUDED_KEYS_JSON` — the union of `$PRIOR_EXCLUDED_KEYS_JSON` and `$WAVE_TRIED_JSON`,
  recomputed whenever either changes; the only value passed as `--exclude-keys-json`. It is a
  two-set union, never three: the Rounds 4–5 floor (`$ESCALATION_EXCLUDE_JSON`,
  `references/escalation.md`) has its own `--escalation-excluded-keys-json` argument and never
  joins it.
- `$EXCLUDED_REASONS_JSON` — `$PRIOR_REASONS_JSON` merged with `$WAVE_REASONS_JSON` (the wave
  wins on a collision), recomputed at each `resolve-injection` call; the only value passed as
  `--excluded-reasons-json`. Never `$WAVE_REASONS_JSON` alone: a re-resolution whose exclusions
  already cover every candidate discovers no reasons of its own, and a resumed wave would lose
  every earlier wave's real reason.
- `$FIX_ROUND` — the fix round the task is on.
- `$LAST_DISPATCHED_KEY` — the key of the most recent `dispatch-task` for this task (empty before
  the first), same-round retries included.
- `$ESCALATION_ANCHOR_KEY` — `$LAST_DISPATCHED_KEY` copied when a fix round starts, unchanged by
  that round's retries and by a resume. The Rounds 4–5 floor is computed from it, never from a
  fresh pick.

Neither derived union is ever persisted; always recompute it from its inputs.

## Initial and resume values

A new task: `FIX_ROUND=0`, `PRIOR_EXCLUDED_KEYS_JSON='[]'`, `PRIOR_REASONS_JSON='{}'`,
`WAVE_TRIED_JSON='[]'`, `WAVE_REASONS_JSON='{}'`, `EXCLUDED_KEYS_JSON='[]'`,
`LAST_DISPATCHED_KEY=''`, `ESCALATION_ANCHOR_KEY=''`.

Resuming from `$RESUME_STATE_PATH`: `fix_round` into `$FIX_ROUND`, `excluded_keys` into
`$PRIOR_EXCLUDED_KEYS_JSON`, `reasons` (only entries whose key is in `excluded_keys`; an older
state file may hold more) into `$PRIOR_REASONS_JSON`, `last_dispatched_key` and
`escalation_anchor_key` (each empty when absent) into `$LAST_DISPATCHED_KEY` and
`$ESCALATION_ANCHOR_KEY`; reset `WAVE_TRIED_JSON='[]'`, `WAVE_REASONS_JSON='{}'`;
set `EXCLUDED_KEYS_JSON="$PRIOR_EXCLUDED_KEYS_JSON"`; then re-enter Step 2. A candidate that was
only quota-exhausted when the state was written is eligible again: the next `resolve-injection`
refreshes quota, so it gets a real chance to have recovered. A permanently excluded one is never
retried, and the task keeps its fix round and its escalation anchor.

## Resumable state: writing it and scheduling the wake

When `INJECTION_MODE == "quota_exhausted"` and `any_quota_recoverable == True`: write resumable
state and schedule an hourly wake, then STOP this wave (do not dispatch this task). One `Bash`
call:

```bash
PROJECT_KEY="$(python3 -c "import hashlib,sys; print(hashlib.sha256(sys.argv[1].encode()).hexdigest()[:12])" "$CWD")"
RESUME_STATE_PATH="$(dirname "$QUOTA_PATH")/superpowers-resume-${PROJECT_KEY}-task-${TASK_N}.json"
# Fold THIS result's tried/reasons into the wave sets first, so a key from either Step 2 or
# Step 3's mid-dispatch quota branch keeps its real reason.
WAVE_TRIED_JSON="$(python3 -c 'import json,sys; print(json.dumps(sorted(set(json.loads(sys.argv[1])) | set(json.loads(sys.argv[2])["tried"]))))' \
  "$WAVE_TRIED_JSON" "$INJECTION_JSON")"
WAVE_REASONS_JSON="$(python3 -c 'import json,sys; a=json.loads(sys.argv[1]); a.update(json.loads(sys.argv[2])["reasons"]); print(json.dumps(a))' \
  "$WAVE_REASONS_JSON" "$INJECTION_JSON")"
# The persisted exclusions come from the tested subcommand, never inline set arithmetic: it drops
# every "quota" key and keeps permanent ones. --prior-excluded-keys-json is the PRIOR set, never
# the derived $EXCLUDED_KEYS_JSON, which carries no reasons.
RESUME_EXCLUDED_KEYS_JSON="$(python3 "$SHIM" resume-exclusions --tried-json "$WAVE_TRIED_JSON" \
  --reasons-json "$WAVE_REASONS_JSON" --prior-excluded-keys-json "$PRIOR_EXCLUDED_KEYS_JSON")"
# resume-exclusions returns keys only: persist prior reasons merged with this wave's, or a key
# carried over from an earlier wave loses its reason from the second resume on. Keep only the
# persisted keys' reasons: a dropped "quota" reason must not resurface as a prior one.
PERSIST_REASONS_JSON="$(python3 -c 'import json,sys; a=json.loads(sys.argv[1]); a.update(json.loads(sys.argv[2])); k=set(json.loads(sys.argv[3])); print(json.dumps({x: r for x, r in a.items() if x in k}))' \
  "$PRIOR_REASONS_JSON" "$WAVE_REASONS_JSON" "$RESUME_EXCLUDED_KEYS_JSON")"
STATE_JSON="$(python3 -c '
import json, sys
print(json.dumps({"framework": "superpowers", "plan_path": sys.argv[1], "task_index": sys.argv[2],
                   "fix_round": int(sys.argv[3]), "excluded_keys": json.loads(sys.argv[4]),
                   "tried": json.loads(sys.argv[5]), "reasons": json.loads(sys.argv[6]),
                   "last_dispatched_key": sys.argv[7], "escalation_anchor_key": sys.argv[8]}))' \
  "$PLAN_FILE" "$TASK_N" "$FIX_ROUND" "$RESUME_EXCLUDED_KEYS_JSON" "$WAVE_TRIED_JSON" \
  "$PERSIST_REASONS_JSON" "$LAST_DISPATCHED_KEY" "$ESCALATION_ANCHOR_KEY")"
python3 "$SHIM" write-resumable-state --path "$RESUME_STATE_PATH" --state-json "$STATE_JSON"
printf 'RESUME_STATE_PATH=%s\nWAVE_TRIED_JSON=%s\nWAVE_REASONS_JSON=%s\n' \
  "$RESUME_STATE_PATH" "$WAVE_TRIED_JSON" "$WAVE_REASONS_JSON"
```

Schedule `CronCreate`: hourly interval, prompt `"re-check quota via probe-quota and, once restored,
resume ai-kit-spec-execute-superpowers from $RESUME_STATE_PATH"` (substitute the printed path).
`CronCreate` jobs are session-scoped (design spec §10) — they vanish if the session exits, only fire
while the session is idle, and recurring jobs auto-expire after 7 days; tell the user this
explicitly. On a host without a scheduler, tell the user the state path and that they resume by
hand.
