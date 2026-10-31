# Step 2 reference: exclusion-set state management

MANDATORY read before writing to, or reading from, `$EXCLUDED_KEYS_JSON` / `$EXCLUDED_REASONS_JSON`
or the resumable-state JSON file. Every rule below is load-bearing.

## The variable set

Each value is this task's own state, and every `Bash` call starts a fresh shell. Scalars
(`$FIX_ROUND`, the keys, the paths) are appended to the plan's scalar file `$SCALARS` after every
change (`printf 'NAME=%s\n' "$NAME" | tee -a "$SCALARS"`; the last line for a name wins) and
restored by the loader that opens every `Bash` call (`SKILL.md`, Step 0); never re-typed from
memory. **JSON values follow the quoting rule: never paste their text into a command.** Each
lives in `$RUN_DIR/<NAME>.json` (`$RUN_DIR`: the task-paths block): `PRIOR_EXCLUDED_KEYS_JSON`,
`PRIOR_REASONS_JSON`, `WAVE_TRIED_JSON`, `WAVE_REASONS_JSON`, `EXCLUDED_KEYS_JSON`,
`INJECTION_JSON` and `ESCALATION_EXCLUDE_JSON`. A block that reads one starts with
`NAME="$(cat "$RUN_DIR/NAME.json")"`; one that changes it ends with
`printf '%s' "$NAME" > "$RUN_DIR/NAME.json"`. A JSON value printed for the report is never copied
back. `DISPATCH_RESULT_JSON` is the file `$DISPATCH_BASE.json`, read the same way.

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
  the first). A failed dispatch is not retried in the same round, so this records the dispatch
  that ran, not a retry.
- `$ESCALATION_ANCHOR_KEY` — `$LAST_DISPATCHED_KEY` copied when a fix round starts, unchanged by a
  resume. The Rounds 4–5 floor is computed from it, never from a fresh pick.

Neither derived union is ever persisted; always recompute it from its inputs.

## Initial and resume values

**Seed a new task:** `FIX_ROUND=0`, `LAST_DISPATCHED_KEY=''`, `ESCALATION_ANCHOR_KEY=''` and the
JSON files empty. The scalar file is per plan, so a task is marked `SEEDED_TASK=<TASK_N>` and the
three scalars are seeded only when the loaded `SEEDED_TASK` is another task: a stop that wrote no
resumable-state file (`RESUME_FOUND=0` on re-invoke) keeps its `$FIX_ROUND`, anchor and last
dispatched key, so the Rounds 4–5 floor still applies. The JSON files are always emptied (that
stop saved no exclusions). An owner restarting the plan deletes the scalar file with the state files.

```bash
if [ "${SEEDED_TASK:-}" = "$TASK_N" ]; then echo "task $TASK_N already seeded: kept FIX_ROUND=$FIX_ROUND"
else printf 'SEEDED_TASK=%s\nFIX_ROUND=0\nLAST_DISPATCHED_KEY=\nESCALATION_ANCHOR_KEY=\n' "$TASK_N" | tee -a "$SCALARS"; fi
for n in PRIOR_EXCLUDED_KEYS_JSON WAVE_TRIED_JSON EXCLUDED_KEYS_JSON; do printf '[]' > "$RUN_DIR/$n.json"; done
for n in PRIOR_REASONS_JSON WAVE_REASONS_JSON; do printf '{}' > "$RUN_DIR/$n.json"; done
```

**Restore** from `$RESUME_STATE_PATH` (the file the task-paths block found; a wake or an owner
re-invoke both arrive here). The script checks that `framework` is `superpowers`, `plan_path` is
`$PLAN_FILE` and `task_index` is `$TASK_N` (on any mismatch it exits non-zero: STOP and report
the path, never restore it). It writes `excluded_keys` to `PRIOR_EXCLUDED_KEYS_JSON` and, as
`EXCLUDED_KEYS_JSON`, a copy; `reasons` (only entries whose key is in `excluded_keys`; an older state
file may hold more) to `PRIOR_REASONS_JSON`; empties `WAVE_TRIED_JSON`/`WAVE_REASONS_JSON`; writes
`INJECTION_JSON` when the file holds `injection_json`; and prints the scalars, appending the same
lines to `$SCALARS` (`FIX_ROUND`, `LAST_DISPATCHED_KEY` and `ESCALATION_ANCHOR_KEY`, each empty when
absent); then re-enter Step 2 (the printed `INJECTION_MODE`, `INJECTION_KEY` and `INJECTION_RUNTIME`
mean it holds a pinned injection: go to Step 3 instead).

```bash
python3 - "$RESUME_STATE_PATH" "$RUN_DIR" "$PLAN_FILE" "$TASK_N" "$SCALARS" <<'PY'
import json, os, sys
path, run_dir, plan, task, scalars = sys.argv[1:6]
s = json.load(open(path, encoding="utf-8"))
if (s.get("framework"), s.get("plan_path"), str(s.get("task_index"))) != ("superpowers", plan, task):
    sys.exit("state file does not match this plan and task: " + path)
def put(name, value):
    with open(os.path.join(run_dir, name + ".json"), "w", encoding="utf-8") as f:
        f.write(json.dumps(value))
keys = s.get("excluded_keys") or []
put("PRIOR_EXCLUDED_KEYS_JSON", keys)
put("EXCLUDED_KEYS_JSON", keys)
put("PRIOR_REASONS_JSON", {k: r for k, r in (s.get("reasons") or {}).items() if k in keys})
put("WAVE_TRIED_JSON", [])
put("WAVE_REASONS_JSON", {})
out = ["FIX_ROUND=%s" % int(s.get("fix_round") or 0),
       "LAST_DISPATCHED_KEY=%s" % (s.get("last_dispatched_key") or ""),
       "ESCALATION_ANCHOR_KEY=%s" % (s.get("escalation_anchor_key") or "")]
inj = s.get("injection_json")
if inj:
    put("INJECTION_JSON", inj)
    out += ["INJECTION_MODE=%s" % inj.get("mode"), "INJECTION_KEY=%s" % (inj.get("key") or ""),
            "INJECTION_RUNTIME=%s" % (inj.get("runtime") or "")]
out = [line.replace("\n", " ") for line in out]  # one line per scalar
print("\n".join(out))
with open(scalars, "a", encoding="utf-8") as f:
    f.write("\n".join(out) + "\n")
PY
```

A resume does not increment the round, so with a restored `$FIX_ROUND >= 4` apply the Rounds 4–5
rule (`references/escalation.md`) to that Step 2 result, with the floor computed from the restored
`$ESCALATION_ANCHOR_KEY`, before any dispatch. A candidate that was only quota-exhausted when the
state was written is eligible again: the next `resolve-injection`
refreshes quota, so it gets a real chance to have recovered. A permanently excluded one is never
retried, and the task keeps its fix round and its escalation anchor.

That Step 2 re-entry applies only when the file holds no `injection_json` (a stop before any
dispatch, where selection along the ladder is still pre-dispatch). When it holds `injection_json`,
a dispatch on that pair already failed: both the one-shot wake after a `RETURNCODE` 75 carrying
`retry_after_s=` and `cycle=` (router quota or a spent transient ladder) and an owner's plain
"resume" re-dispatch that object unchanged through Step 3's `dispatch-task` and skip
`resolve-injection`, so no recovered or different candidate replaces the lane. Only an owner
who names a replacement pair re-enters Step 2, with that choice ("Owner-named replacement pair"). After the 4-hour cap the
pinned lane refuses with exit 69 until its last attempt is about 4 hours old or the owner
deletes the state file the refusal names; report that instead of re-resolving.

## Resumable state: writing it

Both write blocks below (and every block that reads `$RESUME_STATE_PATH`) need the loader first:
the task-paths block alone sets `PROJECT_KEY` and `RESUME_STATE_PATH` and appends them to
`$SCALARS`, so the last line is always the current task's. A block here never assigns either name
and exits non-zero on an empty `$RESUME_STATE_PATH`.

When `INJECTION_MODE == "quota_exhausted"` and `any_quota_recoverable == True`: write resumable
state, then STOP this wave and report the reasons per key and the state path (the owner
re-invokes to resume). Nothing is scheduled. Do not dispatch this task. One `Bash` call.

Only a `"quota"` key is dropped from the saved exclusions and gets a fresh chance on resume. Every
other co-tried key, `"capacity"` included, is persisted as a permanent exclusion
(`compute_resume_exclusions`), so say so in the stop report: the owner retries such a key by
deleting the state file or by naming it ("Owner-named replacement pair").

Step 3's failed-dispatch paths (`"quota"` and `"real_error"`) do not edit this block. They run
the "Pinned-injection state write" variant below, which drops the two `WAVE_*` fold lines and
persists the current `$INJECTION_JSON` as `injection_json`.

```bash
# RESUME_STATE_PATH comes from the loaded scalars (the task-paths block set it): never recompute it.
if [ -z "$RESUME_STATE_PATH" ]; then echo "ERROR: RESUME_STATE_PATH is empty -- run the loader first"; exit 1; fi
INJECTION_JSON="$(cat "$RUN_DIR/INJECTION_JSON.json")"
PRIOR_EXCLUDED_KEYS_JSON="$(cat "$RUN_DIR/PRIOR_EXCLUDED_KEYS_JSON.json")"
PRIOR_REASONS_JSON="$(cat "$RUN_DIR/PRIOR_REASONS_JSON.json")"
WAVE_TRIED_JSON="$(cat "$RUN_DIR/WAVE_TRIED_JSON.json")"
WAVE_REASONS_JSON="$(cat "$RUN_DIR/WAVE_REASONS_JSON.json")"
# Fold THIS result's tried/reasons into the wave sets first, so a key from either Step 2 or
# Step 3's mid-dispatch quota branch keeps its real reason.
WAVE_TRIED_JSON="$(python3 -c 'import json,sys; print(json.dumps(sorted(set(json.loads(sys.argv[1])) | set(json.loads(sys.argv[2])["tried"]))))' \
  "$WAVE_TRIED_JSON" "$INJECTION_JSON")"
WAVE_REASONS_JSON="$(python3 -c 'import json,sys; a=json.loads(sys.argv[1]); a.update(json.loads(sys.argv[2])["reasons"]); print(json.dumps(a))' \
  "$WAVE_REASONS_JSON" "$INJECTION_JSON")"
printf '%s' "$WAVE_TRIED_JSON" > "$RUN_DIR/WAVE_TRIED_JSON.json"
printf '%s' "$WAVE_REASONS_JSON" > "$RUN_DIR/WAVE_REASONS_JSON.json"
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
printf 'RESUME_STATE_PATH=%s\n' "$RESUME_STATE_PATH"
```

Then STOP this wave and report the reasons per key and `$RESUME_STATE_PATH`. Nothing is
scheduled; the owner re-invokes to resume.

## Pinned-injection state write

Step 3's `"quota"` branch (after its own fold) and `"real_error"` branch run this block verbatim
instead of the one above. It is the same write with the two `WAVE_*` fold lines removed and
`injection_json` added, so a wake or an owner re-invoke re-dispatches the exact injection that
stopped, at the same fix round and anchor. Do not assemble it by editing the block above.

```bash
# RESUME_STATE_PATH comes from the loaded scalars (the task-paths block set it): never recompute it.
if [ -z "$RESUME_STATE_PATH" ]; then echo "ERROR: RESUME_STATE_PATH is empty -- run the loader first"; exit 1; fi
INJECTION_JSON="$(cat "$RUN_DIR/INJECTION_JSON.json")"
PRIOR_EXCLUDED_KEYS_JSON="$(cat "$RUN_DIR/PRIOR_EXCLUDED_KEYS_JSON.json")"
PRIOR_REASONS_JSON="$(cat "$RUN_DIR/PRIOR_REASONS_JSON.json")"
WAVE_TRIED_JSON="$(cat "$RUN_DIR/WAVE_TRIED_JSON.json")"
WAVE_REASONS_JSON="$(cat "$RUN_DIR/WAVE_REASONS_JSON.json")"
RESUME_EXCLUDED_KEYS_JSON="$(python3 "$SHIM" resume-exclusions --tried-json "$WAVE_TRIED_JSON" \
  --reasons-json "$WAVE_REASONS_JSON" --prior-excluded-keys-json "$PRIOR_EXCLUDED_KEYS_JSON")"
PERSIST_REASONS_JSON="$(python3 -c 'import json,sys; a=json.loads(sys.argv[1]); a.update(json.loads(sys.argv[2])); k=set(json.loads(sys.argv[3])); print(json.dumps({x: r for x, r in a.items() if x in k}))' \
  "$PRIOR_REASONS_JSON" "$WAVE_REASONS_JSON" "$RESUME_EXCLUDED_KEYS_JSON")"
STATE_JSON="$(python3 -c '
import json, sys
print(json.dumps({"framework": "superpowers", "plan_path": sys.argv[1], "task_index": sys.argv[2],
                   "fix_round": int(sys.argv[3]), "excluded_keys": json.loads(sys.argv[4]),
                   "tried": json.loads(sys.argv[5]), "reasons": json.loads(sys.argv[6]),
                   "last_dispatched_key": sys.argv[7], "escalation_anchor_key": sys.argv[8],
                   "injection_json": json.loads(sys.argv[9])}))' \
  "$PLAN_FILE" "$TASK_N" "$FIX_ROUND" "$RESUME_EXCLUDED_KEYS_JSON" "$WAVE_TRIED_JSON" \
  "$PERSIST_REASONS_JSON" "$LAST_DISPATCHED_KEY" "$ESCALATION_ANCHOR_KEY" "$INJECTION_JSON")"
python3 "$SHIM" write-resumable-state --path "$RESUME_STATE_PATH" --state-json "$STATE_JSON"
printf 'RESUME_STATE_PATH=%s\n' "$RESUME_STATE_PATH"
```

## Owner-named replacement pair

After a pinned stop (a `real_error`, a bad injection, an owner stop on quota), the owner may name a
different pair. `resolve-injection` has no argument that pins a key, so exclude every other key:
the owner's pair is the only candidate left. This needs the stopped task's `injection_json` (its
`ladder_keys`, the failed `key`); a stop with none re-enters plain Step 2 once the owner fixed
the cause. The recipe also removes the owner's key from the prior permanent exclusions, so naming
a permanently excluded key (`"capacity"`, say) retries it. On a re-invoke run "Restore" first, then
fill the two literals and run:

```bash
OWNER_KEY="<the ladder key the owner named, exactly as in ladder_keys>"
FAILED_REASON="<the failed key's real reason from the stop report: auth, timeout, real_error, ...>"
python3 - "$RUN_DIR" "$OWNER_KEY" "$FAILED_REASON" <<'PY'
import json, os, sys
run_dir, owner, reason = sys.argv[1:4]
def get(name):
    with open(os.path.join(run_dir, name + ".json"), encoding="utf-8") as f:
        return json.load(f)
def put(name, value):
    with open(os.path.join(run_dir, name + ".json"), "w", encoding="utf-8") as f:
        f.write(json.dumps(value))
inj = get("INJECTION_JSON")
failed, ladder = inj["key"], inj["ladder_keys"]
if owner == failed:
    sys.exit("owner named the failed pair: re-dispatch the pinned injection instead")
if owner not in ladder:
    sys.exit("owner key is not in ladder_keys: " + owner)
tried = sorted(set(get("WAVE_TRIED_JSON")) | {failed})
reasons = {**get("WAVE_REASONS_JSON"), failed: reason}
put("WAVE_TRIED_JSON", tried)
put("WAVE_REASONS_JSON", reasons)
# resolve-injection drops every excluded key, so the owner's key leaves every exclusion set first
prior = set(get("PRIOR_EXCLUDED_KEYS_JSON")) - {owner}
put("PRIOR_EXCLUDED_KEYS_JSON", sorted(prior))
put("PRIOR_REASONS_JSON", {k: v for k, v in get("PRIOR_REASONS_JSON").items() if k != owner})
put("EXCLUDED_KEYS_JSON", sorted((prior | set(tried)) - {owner}))
put("ESCALATION_EXCLUDE_JSON", sorted(set(ladder) - {owner}))
PY
```

Then run `references/escalation.md`'s "Re-running resolve-injection with the floor" block unchanged
(it reads `ESCALATION_EXCLUDE_JSON` from the file), handle the result as Step 2 does, and confirm
`$INJECTION_KEY` equals `$OWNER_KEY`. A different key, `quota_exhausted` or `no_candidate` means
the owner's pair is not eligible right now: STOP and report `reasons`/`detail`, never dispatch
another key. The fix round, `$LAST_DISPATCHED_KEY` and `$ESCALATION_ANCHOR_KEY` stay as they are,
`REPORT_MODE` stays `append`, and the new pick is dispatched and pinned like any other.
