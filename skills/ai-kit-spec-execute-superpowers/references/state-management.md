# Step 2 reference: exclusion-set state management

MANDATORY read before writing to, or reading from, `$EXCLUDED_KEYS_JSON` / `$EXCLUDED_REASONS_JSON`
or the resumable-state JSON file. This is the full bookkeeping detail for Step 2 of
`SKILL.md` — relocated here only so the top-level routing stays short; every fact below is load-
bearing and none of it is optional.

## The variable set

`$FIX_ROUND` and `$EXCLUDED_KEYS_JSON` are this task's own wave state, carried across every `Bash`
call for its lifetime (re-`printf`'d and re-substituted each time, per Step 0's own convention) —
HIGH finding: resumable state must capture the complete excluded-candidate set and which fix round
a resume lands on, not just the ladder position at the moment of exhaustion.

**CRITICAL finding (recurrence guard): `$EXCLUDED_KEYS_JSON` is a working union of TWO
differently-provenanced sets — never persist it wholesale as `excluded_keys`, or a same-wave
`"quota"` exclusion becomes indistinguishable from a genuinely permanent one and is never eligible
again after a resume, exactly the bug `resume-exclusions` (Task 3) was built to prevent.** Track
the two sets separately for the task's whole lifetime:

- `$PRIOR_EXCLUDED_KEYS_JSON` — the genuinely permanent exclusion set this task resumed with (or
  `'[]'` for a brand-new task). This is `compute_resume_exclusions`' own OUTPUT from a previous
  wave, already reason-filtered — every key in it stayed excluded because its reason was something
  other than `"quota"`. Never add to this set directly; it only changes across a resume (below).
- `$PRIOR_REASONS_JSON` — the `{key: reason}` map for every key in `$PRIOR_EXCLUDED_KEYS_JSON`,
  restored alongside it from the SAME persisted `$RESUME_STATE_PATH` (`STATE_JSON` already writes
  this wave's own `reasons` field — the resumable-state block below — so restoring it costs
  nothing new to persist). `'{}'` for a brand-new task. **Important finding, recurrence guard:
  without this, a resumed wave that later hits `quota_exhausted` again has no way to recover WHY an
  old permanent exclusion failed — `cli.py`'s own `_emit_quota_exhausted` falls back every excluded
  key missing from `--excluded-reasons-json` to the generic `"no_usable_dispatch"`, silently
  replacing a real `"auth"` or `"configuration"` reason with a meaningless one in the user-facing
  report Step 2 instructs reading.** Never add to this set directly; it only changes across a
  resume (below).
- `$WAVE_TRIED_JSON` / `$WAVE_REASONS_JSON` — every candidate key tried and rejected DURING THIS
  LIVE WAVE (both a `resolve-injection` call's own `tried`/`reasons` when it reports
  `quota_exhausted`, and a mid-dispatch `"quota"` failure caught in Step 3), paired with the reason
  each one failed for. Reset to `'[]'`/`'{}'` at the very first dispatch of a NEW task AND on every
  resume (a resume already folded any earlier wave's non-quota reasons into
  `$PRIOR_EXCLUDED_KEYS_JSON`/`$PRIOR_REASONS_JSON` via `resume-exclusions`, so the new wave starts
  with a clean slate and re-discovers THIS wave's own reasons fresh rather than replaying stale
  ones — `$PRIOR_REASONS_JSON` is a separate, never-reset channel for the OLD wave's reasons, merged
  back in only at the point of calling `resolve-injection`, below).
- `$EXCLUDED_KEYS_JSON` — recomputed as the UNION of `$PRIOR_EXCLUDED_KEYS_JSON` and
  `$WAVE_TRIED_JSON` every time either input changes; this is the ONLY one ever passed to
  `resolve-injection --exclude-keys-json`. Because it is a derived value, never persist it directly
  either — always recompute it, and always persist `$PRIOR_EXCLUDED_KEYS_JSON` /
  `$WAVE_TRIED_JSON` / `$WAVE_REASONS_JSON` (or their `resume-exclusions` output) instead. **This is
  a two-set union, never three** — the Rounds 4–5 capability-escalation rule
  (`references/escalation.md`) tracks a THIRD, unrelated set, `$ESCALATION_EXCLUDE_JSON` (healthy,
  never-attempted candidates excluded purely to enforce that round's capability floor, never a
  failure), and passes it to `resolve-injection` through its own separate
  `--escalation-excluded-keys-json` argument — it never joins this union and `$EXCLUDED_KEYS_JSON`
  is never reassigned to include it.
- `$EXCLUDED_REASONS_JSON` — recomputed the same way, as the MERGE of `$PRIOR_REASONS_JSON` and
  `$WAVE_REASONS_JSON` (`$WAVE_REASONS_JSON` wins on key collision, being the freshest information)
  every time either input changes; this is the ONLY one ever passed to `resolve-injection
  --excluded-reasons-json`. Like `$EXCLUDED_KEYS_JSON`, never persist it directly — recompute it at
  the point of each `resolve-injection` call from its two real inputs instead.

## Initial and resume values

At the very first dispatch of a NEW task: `FIX_ROUND=0`, `PRIOR_EXCLUDED_KEYS_JSON='[]'`,
`PRIOR_REASONS_JSON='{}'`, `WAVE_TRIED_JSON='[]'`, `WAVE_REASONS_JSON='{}'`, and
`EXCLUDED_KEYS_JSON='[]'`. Resuming from a persisted `$RESUME_STATE_PATH` (below): read `fix_round`
into `$FIX_ROUND`, the persisted `excluded_keys` into `$PRIOR_EXCLUDED_KEYS_JSON`, and the persisted
`reasons` into `$PRIOR_REASONS_JSON` (these are already permanent — `resume-exclusions` dropped
every quota-only key, and `reasons` carries the real reason for every key that survived that drop,
before persisting them); reset `$WAVE_TRIED_JSON='[]'` and `$WAVE_REASONS_JSON='{}'` for the fresh
wave; set `EXCLUDED_KEYS_JSON="$PRIOR_EXCLUDED_KEYS_JSON"`.

## Why both reason sets must be merged into `--excluded-reasons-json`

**`--excluded-reasons-json "$EXCLUDED_REASONS_JSON"` — CRITICAL finding, recurrence guard.** Every
`resolve-injection` call in `SKILL.md` passes the FULL accumulated reasons alongside its excluded
keys, not just the keys — this means merging `$PRIOR_REASONS_JSON` (restored on resume, covering
keys excluded in an EARLIER wave) with `$WAVE_REASONS_JSON` (discovered so far THIS wave), never
`$WAVE_REASONS_JSON` alone. Two distinct bugs this closes: (1) without `$WAVE_REASONS_JSON` at all,
a re-resolution call whose `--exclude-keys-json` already covers every configured candidate for this
task would have no way to report a real `quota_exhausted` outcome (its own ladder walk never
starts, so it discovers no reasons of its own), and a re-resolution call that DOES find a fresh
`quota_exhausted` result would lose every earlier-excluded candidate's own reason from
`any_quota_recoverable`'s computation; (2) without also merging in `$PRIOR_REASONS_JSON` on a
resumed wave, every key in `$PRIOR_EXCLUDED_KEYS_JSON` is present in `--exclude-keys-json` but
absent from `--excluded-reasons-json` — `cli.py`'s own `_emit_quota_exhausted` then falls each one
back to the generic `"no_usable_dispatch"` (`cli.py`'s own `merged_reasons.setdefault(key,
"no_usable_dispatch")`), silently discarding a real `"auth"`/`"configuration"`/etc. reason a PRIOR
wave already discovered and persisted for exactly this purpose.

## Resumable state: writing it and scheduling the wake

When `INJECTION_MODE == "quota_exhausted"` and `any_quota_recoverable == True` (at least one
candidate is a genuine, time-bound quota exhaustion, discovered before dispatch): write resumable
state and schedule an hourly `CronCreate` wake, then STOP this wave (do not dispatch this task):

```bash
PROJECT_KEY="$(python3 -c "import hashlib,sys; print(hashlib.sha256(sys.argv[1].encode()).hexdigest()[:12])" "$CWD")"
RESUME_STATE_PATH="$(dirname "$QUOTA_PATH")/superpowers-resume-${PROJECT_KEY}-task-${TASK_N}.json"
# CRITICAL finding (recurrence guard, second layer): fold THIS resolve-injection call's own
# tried/reasons into the wave-accumulated sets BEFORE computing what to persist. Without this
# merge, a candidate excluded earlier in the SAME wave purely because of Step 3's mid-dispatch
# "quota" branch (below) would never have its reason recorded here at all -- persisting it would
# either drop it silently (wrong: it really was tried and failed, the harness should know) or, if
# folded in unlabeled via $EXCLUDED_KEYS_JSON directly, get treated as permanent regardless of its
# real (temporary) reason. Merging into $WAVE_TRIED_JSON/$WAVE_REASONS_JSON keeps every wave-tried
# key's real reason attached no matter which step (Step 2 or Step 3) discovered it.
WAVE_TRIED_JSON="$(python3 -c 'import json,sys; print(json.dumps(sorted(set(json.loads(sys.argv[1])) | set(json.loads(sys.argv[2])["tried"]))))' \
  "$WAVE_TRIED_JSON" "$INJECTION_JSON")"
WAVE_REASONS_JSON="$(python3 -c 'import json,sys; a=json.loads(sys.argv[1]); a.update(json.loads(sys.argv[2])["reasons"]); print(json.dumps(a))' \
  "$WAVE_REASONS_JSON" "$INJECTION_JSON")"
# CRITICAL finding (recurrence guard): compute the PERSISTED exclusion set via the tested
# resume-exclusions subcommand, never inline, untested set arithmetic -- a "quota" reason is
# deliberately dropped so the candidate is eligible again once quota genuinely recovers; only
# permanent reasons (auth/timeout/configuration/dispatch_unavailable/no_usable_dispatch/
# real_error) are carried forward into the persisted excluded_keys set. `--prior-excluded-keys-json`
# is `$PRIOR_EXCLUDED_KEYS_JSON` (the genuinely permanent set this wave started with) -- NEVER
# `$EXCLUDED_KEYS_JSON`, which is a derived union and would re-feed already-permanent keys back in
# as if they were freshly-tried (harmless) but, worse, would offer no way to tell a same-wave
# "quota" entry apart from a permanent one, since $EXCLUDED_KEYS_JSON carries no reasons at all.
RESUME_EXCLUDED_KEYS_JSON="$(python3 "$SHIM" resume-exclusions --tried-json "$WAVE_TRIED_JSON" \
  --reasons-json "$WAVE_REASONS_JSON" --prior-excluded-keys-json "$PRIOR_EXCLUDED_KEYS_JSON")"
# Important finding, recurrence guard: the persisted "reasons" field must carry PRIOR_REASONS_JSON
# merged with WAVE_REASONS_JSON, never WAVE_REASONS_JSON alone -- compute_resume_exclusions (above)
# returns ONLY keys, not reasons, so a key carried forward unchanged from $PRIOR_EXCLUDED_KEYS_JSON
# (permanent from an EARLIER wave, never re-tried this wave) would otherwise have no entry in the
# freshly-written "reasons" field at all. Persisting WAVE_REASONS_JSON alone works for a task's
# FIRST resume (the reader falls back to "no_usable_dispatch" harmlessly, since $PRIOR_REASONS_JSON
# was still '{}' then) but silently loses real reasons on every resume AFTER the first, once
# $PRIOR_REASONS_JSON itself is non-empty and needs to be carried forward in what gets persisted.
PERSIST_REASONS_JSON="$(python3 -c 'import json,sys; a=json.loads(sys.argv[1]); a.update(json.loads(sys.argv[2])); print(json.dumps(a))' \
  "$PRIOR_REASONS_JSON" "$WAVE_REASONS_JSON")"
STATE_JSON="$(python3 -c '
import json, sys
print(json.dumps({"framework": "superpowers", "plan_path": sys.argv[1], "task_index": sys.argv[2],
                   "fix_round": int(sys.argv[3]), "excluded_keys": json.loads(sys.argv[4]),
                   "tried": json.loads(sys.argv[5]), "reasons": json.loads(sys.argv[6])}))' \
  "$PLAN_FILE" "$TASK_N" "$FIX_ROUND" "$RESUME_EXCLUDED_KEYS_JSON" "$WAVE_TRIED_JSON" "$PERSIST_REASONS_JSON")"
python3 "$SHIM" write-resumable-state --path "$RESUME_STATE_PATH" --state-json "$STATE_JSON"
```

Schedule `CronCreate`: hourly interval, prompt `"re-check quota via probe-quota and, once restored,
resume ai-kit-spec-execute-superpowers from $RESUME_STATE_PATH"`. `CronCreate` jobs are
session-scoped (design spec §10) — they vanish if the session exits, only fire while the session is
idle, and recurring jobs auto-expire after 7 days; tell the user this explicitly.

## Reading resumable state back

**On resume**, read `fix_round` back into `$FIX_ROUND`, `excluded_keys` back into
`$PRIOR_EXCLUDED_KEYS_JSON`, and `reasons` back into `$PRIOR_REASONS_JSON` (never directly into
`$EXCLUDED_KEYS_JSON`/`$WAVE_REASONS_JSON` — see the variable-set split above; `reasons` here is
already the merged `$PERSIST_REASONS_JSON` this same block just wrote, so restoring it recovers
every permanently-excluded key's real reason, including one from a wave BEFORE the one that most
recently persisted — Important finding, recurrence guard: without restoring this, a resumed wave
that later hits `quota_exhausted` again would have no way to recover WHY an old permanent exclusion
failed, and `cli.py`'s own `_emit_quota_exhausted` would silently relabel it `"no_usable_dispatch"`
in the user-facing report), reset `$WAVE_TRIED_JSON='[]'`/`$WAVE_REASONS_JSON='{}'` for the fresh
wave, and recompute `EXCLUDED_KEYS_JSON="$PRIOR_EXCLUDED_KEYS_JSON"` before re-entering Step 2 —
CRITICAL finding (recurrence guard): the persisted `excluded_keys` set contains ONLY permanent
exclusions (`compute_resume_exclusions` already dropped every merely-`"quota"`-reason key, including
one discovered mid-dispatch in Step 3), so a candidate that was genuinely quota-exhausted at persist
time — whether discovered here in Step 2 or mid-dispatch in Step 3 — is automatically eligible again
here — the very next `resolve-injection` call always refreshes quota fresh, giving it a real chance
to have recovered, rather than being permanently locked out by its own earlier exhaustion event. The
walk continues exactly where it left off otherwise: never re-trying an already-permanently-excluded
candidate and never losing which fix round the task was on.
