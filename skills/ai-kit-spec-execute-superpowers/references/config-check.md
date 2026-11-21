# No-config check (Step 1, before the start step)

MANDATORY: read this file in full before the start step and run its block 1 once per plan start. Do NOT load it at any
other point.

The adapter reads the execute lanes, so with no lanes configured it asks the owner once before the first task, and it
asks before the start step moves any commit. A resumed run of the same plan (a resume state file of the plan exists)
starts with no memory and the owner may be away: block 1 then finds the `CONFIG_CHECK=` line recorded in the plan's
scalar file and asks nothing again. A fresh start (no resume state file) clears an old `CONFIG_CHECK=` line, runs
`config-status` again and asks again, so a config written or removed since the last run counts. The adapter has no
`--no-cross-ai` flag; answer (2) is its only way to run on the session model.

## The check

**No-config check** (a resumed run of this plan whose scalar file records `CONFIG_CHECK=` skips it; a fresh start asks again). Run block 1 below and read the `CONFIG_STATE=` line it prints.
1. `active`: continue and ask nothing.
2. `pending`: continue; the trust and migration steps handle it, never setup.
3. `none`: ask once, with the host's question tool or numbered plain text, and never answer for the user:
   (1) run ai-kit-spec-config now, (2) run once on the session model, (3) stop. An empty or unrecognised answer is (3).
   (1): follow the sibling ai-kit-spec-config skill to its end, run config-status again (it must print `active`), then continue the task.
   (2): continue on the session default and print the line `no cross-AI config: ran on the session model` now and again after the final review.
   (3): stop.
4. `none` and the host has no way to ask: print `no cross-AI config: run ai-kit-spec-config; continuing on the session model, no config written`,
   continue on the session default and print that line again after the final review.
5. `none`, the answer is (1) and no ../ai-kit-spec-config/SKILL.md exists beside this skill: stop with
   `ai-kit-spec-config is not installed. Install ai-kit, then run ai-kit-spec-config.`
6. Exit code 2: show the named error line and stop; any other nonzero exit: show the first stderr line and stop.

`SPEC_CONFIG=missing` in block 1's output is point 5's fact. For answer (1), "run config-status again" means block 1 run
again (it asks nothing while no `CONFIG_CHECK=` line is recorded).

**Session-model mode** (`CONFIG_CHECK` is `once` or `notice`): no execute lane exists, so `resolve-injection` would
stop the run. For every task, run block 3 in place of Step 2's `resolve-injection` block: it writes
`$RUN_DIR/INJECTION_JSON.json` with mode `native` and an empty key, runtime and model (the shape Step 2 reads) and
records `INJECTION_MODE=native`, so the rest of Step 2 and Step 3 run unchanged and the task dispatches on the host's
own subagent mechanism with `model` omitted (the session model). Rounds 4–5 in this mode run on the session model with
no ladder escalation and no model bump.

## Block 1: check (one Bash call, before the start step)

```bash
SKILL_DIR="<Step 0 SKILL_DIR>"; TOOLS_PY="<Step 0 TOOLS_PY>"; CWD="<Step 1 CWD>"; PLAN_FILE="<Step 1 PLAN_FILE>"
for n in SKILL_DIR TOOLS_PY CWD PLAN_FILE; do case "${!n}" in ""|"<"*)
  printf 'ERROR: %s is empty or a placeholder -- fill it from Step 0/Step 1\n' "$n"; exit 1 ;; esac; done
QUOTA_PATH="$(python3 "$TOOLS_PY" cache-path --kind quota)"
PROJECT_KEY="$(python3 -c 'import hashlib,sys; print(hashlib.sha256("\n".join(sys.argv[1:3]).encode()).hexdigest()[:12])' "$CWD" "$PLAN_FILE")"
SCALARS="$(dirname "$QUOTA_PATH")/superpowers-run-${PROJECT_KEY}-scalars.env"
printf 'SCALARS=%s\n' "$SCALARS"
LAST_CHECK=""
if [ -f "$SCALARS" ]; then LAST_CHECK="$(grep '^CONFIG_CHECK=' "$SCALARS" | tail -n 1)"; fi
# a resume state file counts only when it passes the Restore check of references/state-management.md
RESUMED="$(python3 - "$(dirname "$QUOTA_PATH")" "$PROJECT_KEY" "$PLAN_FILE" <<'PY'
import glob, json, os, re, sys
folder, key, plan = sys.argv[1:4]
found = 0
for path in glob.glob(os.path.join(folder, f"superpowers-resume-{key}-task-*.json")):
    task = re.search(r"-task-(.+)\.json$", path).group(1)
    try:
        s = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        continue
    if isinstance(s, dict) and (s.get("framework"), s.get("plan_path"), str(s.get("task_index"))) == ("superpowers", plan, task):
        found = 1
print(found)
PY
)"
if [ "$RESUMED" = 1 ] && [ -n "${LAST_CHECK#CONFIG_CHECK=}" ]; then
  printf '%s\n' "$LAST_CHECK"; printf 'resumed run, already checked: ask nothing\n'; exit 0
fi
if [ -n "${LAST_CHECK#CONFIG_CHECK=}" ]; then
  printf 'CONFIG_CHECK=\n' >> "$SCALARS"; printf 'fresh start: the old CONFIG_CHECK is cleared\n'
fi
if [ -f "$(dirname "$SKILL_DIR")/ai-kit-spec-config/SKILL.md" ]; then SPEC_CONFIG=present; else SPEC_CONFIG=missing; fi
printf 'SPEC_CONFIG=%s\n' "$SPEC_CONFIG"
STATUS_OUT="$(python3 "$TOOLS_PY" config-status --role execute --cwd "$CWD")"; STATUS_RC=$?
if [ "$STATUS_RC" -ne 0 ]; then printf 'CONFIG_STATUS_EXIT=%s\n' "$STATUS_RC"; exit "$STATUS_RC"; fi
printf 'CONFIG_STATE=%s\n' "$(printf '%s\n' "$STATUS_OUT" | head -n 1)"
```

## Block 2: record the outcome (one Bash call, after the answer)

Record `active`, `pending`, answer (2) as `once`, point 4 as `notice` and a finished answer (1) as `chained`. A stop
(answer (3), point 5 or point 6) records nothing, so the next run asks again.

```bash
SCALARS="<the SCALARS path block 1 printed>"; CONFIG_CHECK="<active|pending|once|notice|chained>"
case "$SCALARS" in ""|"<"*) printf 'ERROR: SCALARS is empty or a placeholder\n'; exit 1 ;; esac
case "$CONFIG_CHECK" in active|pending|once|notice|chained) ;; *)
  printf 'ERROR: CONFIG_CHECK must be active, pending, once, notice or chained\n'; exit 1 ;; esac
mkdir -p "$(dirname "$SCALARS")"
printf 'CONFIG_CHECK=%s\n' "$CONFIG_CHECK" | tee -a "$SCALARS"
```

## Block 3: session-model injection (session-model mode only, once per task in place of the resolve-injection block)

Opened by the scalar loader like every Bash call after the Task paths block.

```bash
case "$CONFIG_CHECK" in once|notice) ;; *)
  printf 'ERROR: CONFIG_CHECK is "%s", not once or notice: run the resolve-injection block instead\n' "$CONFIG_CHECK"; exit 1 ;; esac
python3 -c 'import json,sys; open(sys.argv[1], "w", encoding="utf-8").write(json.dumps({"mode": "native", "key": "", "runtime": "", "model": "", "ladder_keys": []}))' "$RUN_DIR/INJECTION_JSON.json"
printf 'INJECTION_MODE=native\n' | tee -a "$SCALARS"
```

The Task paths block appends to the same scalar file, so every later loader holds `CONFIG_CHECK`; with `once` or
`notice`, Step 5 prints its line again after the final review.
