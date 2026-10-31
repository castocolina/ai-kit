# Session wake reference: arm and close

MANDATORY read in full before the first task's implementer dispatch of a plan with two or more
tasks (arm), and again when this skill's job ends (close). Do NOT load it for a single-task plan.
Each block opens with the scalar loader (`SKILL.md`, Step 0).

## Arm the session wake

Run this block once per plan, not once per task: before the first task's implementer dispatch, only
when `$PLAN_FILE` holds two or more `### Task <n>` headings. It skips itself on the loaded
`WAKE_OWNED=1`, so every later task and any re-invoked or wake-resumed run leaves the wake alone
(`arm` would print `refreshed` and overwrite `WAKE_OWNED`). The wake is owned by this run only when
this block itself prints `armed`; a refusal, exit 3 or `refreshed` (a wake that existed before this
run, closed by its owner: the ai-kit-session-wake skill's Arm section) leaves `WAKE_OWNED=0`, and the
stop re-arm and the close step then call nothing. Never fail the run on the wake. Fill the first
line (the id is not in the scalar file yet): on claude leave it empty. pi and opencode have no
verified session variable: put an id there only when the owner or the host gave one or the wake
state file a resume prompt names holds it (the ai-kit-session-wake skill's Arm section), never a
guess or the newest session file. Otherwise leave it empty: `arm` refuses (exit 2), the block prints
it and the run goes on with `WAKE_OWNED=0`. One `Bash` call:

```bash
WAKE_SESSION_ID="<an id the owner, host or resume state gave, else empty>"
if [ "${WAKE_OWNED:-0}" = 1 ]; then echo "session wake already owned by this plan: arm skipped"; exit 0; fi
case "$WAKE_SESSION_ID" in *"<"*)
  echo "ERROR: WAKE_SESSION_ID is a placeholder -- fill it with a given id or empty it"; exit 1 ;; esac
TASK_COUNT=$(grep -cE '^### Task [0-9]' "$PLAN_FILE")
WAKE_OWNED=0
WAKE_SHIM="$(dirname "$SKILL_DIR")/ai-kit-session-wake/ai-kit-session-wake.py"
if [ "$TASK_COUNT" -lt 2 ]; then
  echo "single-task plan: no session wake"
elif [ ! -f "$WAKE_SHIM" ]; then
  echo "ai-kit-session-wake not installed; no session wake"
else
  WAKE_OUT="$(python3 "$WAKE_SHIM" arm ${WAKE_SESSION_ID:+--session-id "$WAKE_SESSION_ID"} --ref "$PLAN_FILE" 2>&1)"
  WAKE_RC=$?
  echo "$WAKE_OUT"
  echo "session wake arm exit $WAKE_RC"
  WAKE_LINE="$(printf '%s\n' "$WAKE_OUT" | grep '^armed ' | head -n 1)"
  if [ "$WAKE_RC" -eq 0 ] && [ -n "$WAKE_LINE" ]; then
    WAKE_HOST_ID="${WAKE_LINE#armed }"
    # host ids (claude, pi, opencode, codex) hold no hyphen: split at the first, WAKE_ID keeps the rest whole
    WAKE_HOST="${WAKE_HOST_ID%%-*}"
    WAKE_ID="${WAKE_HOST_ID#*-}"
    WAKE_OWNED=1
  fi
fi
for n in WAKE_SHIM WAKE_OWNED WAKE_HOST WAKE_ID; do printf '%s=%s\n' "$n" "${!n:-}"; done | tee -a "$SCALARS"
```

The `WAKE_*` values now persist for every later task. When `arm` prints a `companion:` line (here
or at the re-arm below), act on it as [`../../ai-kit-session-wake/SKILL.md`](../../ai-kit-session-wake/SKILL.md)
says under "When `arm` prints a companion time" only; Do NOT load the rest of ai-kit-session-wake
(this file uses just its `arm` and `done` subcommands).

## Close the session wake

When this skill's job ends (the final whole-branch review finished, which the caller runs and
this skill never does, or a stop ended the run: STOP this wave, or an owner stop) and only when
`WAKE_OWNED=1`, run:

```bash
if [ "$WAKE_OWNED" = 1 ]; then
  python3 "$WAKE_SHIM" done --host "$WAKE_HOST" --session-id "$WAKE_ID"
  echo 'WAKE_OWNED=0' >> "$SCALARS"  # a later run of this plan arms its own wake
fi
```

Never run it on the one-shot wait branch of Schedule-or-stop, which continues the run, nor for a
task still waiting on its wake. When `WAKE_OWNED=0`, call nothing: a `refreshed` arm left the earlier
wake to its owner, who runs `done` or `disarm` by hand.
