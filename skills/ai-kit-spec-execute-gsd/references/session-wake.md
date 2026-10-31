# Session wake, quota wake and close (Claude Code)

`SKILL.md` Step 3 sends you here at three points: before the invoke (**Arm**), on an exit 75
carrying `retry_after_s=` (**Quota wake**) and at every end of the job (**Close**). Every
`$VAR` below is a literal value recorded earlier in the wave (Step 0, Step 1, the arm block).
Never fail the run on the wake.

## Arm

Arm only when the phase holds two or more pending plans (a `*-PLAN.md` with no `*-SUMMARY.md`); fewer arm nothing. The wake
is owned by this run only when this block itself prints `armed`; a refusal, exit 3 or
`refreshed` (a wake that existed before this run) leaves `WAKE_OWNED=0`, and the quota-wake
re-arm and the close step then call nothing. The first line reads this session's id from
`CLAUDE_CODE_SESSION_ID`, the variable the wake CLI's claude host row defaults from. The block
passes `--host claude` itself: left to detection, a nested host signal (pi, opencode, cursor, codex) outranks claude and aims the wake at the wrong host. With it
empty, `arm` has no session to record and exits 2, so the block skips it and leaves
`WAKE_OWNED=0`. Run it as one `Bash` call:

```bash
WAKE_SESSION_ID="${CLAUDE_CODE_SESSION_ID:-}"
PLAN_COUNT=0
for p in "$(dirname "$PHASE_PROMPT_FILE")"/*-PLAN.md; do
  { [ ! -f "$p" ] || [ -f "${p%-PLAN.md}-SUMMARY.md" ]; } || PLAN_COUNT=$((PLAN_COUNT + 1))
done
WAKE_OWNED=0
WAKE_SHIM="$(dirname "$(dirname "$GSD_SHIM")")/ai-kit-session-wake/ai-kit-session-wake.py"
if [ "$PLAN_COUNT" -lt 2 ]; then
  echo "fewer than two pending plans: no session wake"
elif [ ! -f "$WAKE_SHIM" ]; then
  echo "ai-kit-session-wake not installed; no session wake"
elif [ -z "$WAKE_SESSION_ID" ]; then
  echo "CLAUDE_CODE_SESSION_ID is empty in this shell; no session wake"
else
  WAKE_OUT="$(python3 "$WAKE_SHIM" arm --host claude --session-id "$WAKE_SESSION_ID" --ref "$(dirname "$GSD_CONFIG_PATH")/STATE.md" 2>&1)"
  WAKE_RC=$?
  echo "$WAKE_OUT"
  echo "session wake arm exit $WAKE_RC"
  WAKE_LINE="$(printf '%s\n' "$WAKE_OUT" | grep '^armed ' | head -n 1)"
  if [ "$WAKE_RC" -eq 0 ] && [ -n "$WAKE_LINE" ]; then
    WAKE_HOST_ID="${WAKE_LINE#armed }"
    WAKE_HOST="${WAKE_HOST_ID%%-*}"
    WAKE_ID="${WAKE_HOST_ID#*-}"
    WAKE_OWNED=1
  fi
fi
printf 'WAKE_SHIM=%s\nWAKE_OWNED=%s\nWAKE_HOST=%s\nWAKE_ID=%s\n' \
  "$WAKE_SHIM" "$WAKE_OWNED" "${WAKE_HOST:-}" "${WAKE_ID:-}"
```

**Record the printed `WAKE_SHIM`, `WAKE_OWNED`, `WAKE_HOST` and `WAKE_ID` as literal values.**
A refusal (exit 2) is printed above and the run goes on with no wake. When `arm` prints a
`companion:` line (here or at the re-arm below), act on it as
[`../../ai-kit-session-wake/SKILL.md`](../../ai-kit-session-wake/SKILL.md) says under "When `arm`
prints a companion time".

## Quota wake (exit 75 carrying `retry_after_s=`)

The transient ladder is exhausted or a confirmed-router quota hit. Answer nothing to GSD's
prompt in that turn; the one-shot wake below retries the same lane, CLI and model.

1. `RESUME_STATE_PATH` is the literal the [`resumable-state.md`](resumable-state.md) block
   printed in `SKILL.md`'s stop handling (`RESUME_VIA=gsd-execute-phase`); run that block now if
   it has not run.
2. Re-arm the session wake with that state file, only when this run owns it (`WAKE_OWNED=1`). It
   passes no `--reset-at` on purpose: that would print a `companion:` line and a second
   one-shot. The OS-timer wake keeps its own schedule and matters only if the session dies; the
   one-shot in step 3 is the retry trigger:

```bash
if [ "$WAKE_OWNED" = 1 ]; then
  python3 "$WAKE_SHIM" arm --host "$WAKE_HOST" --session-id "$WAKE_ID" --ref "$RESUME_STATE_PATH"
fi
```

3. Where `CronCreate` is callable, schedule one one-shot wake at `retry_after_s` (load it if
   deferred; whole-minute rounding and the under-60 s case: ai-kit-cross-ai section 6) whose
   prompt is one of the two texts below, with each angle-bracket value replaced by its recorded
   literal. Use variant A when `WAKE_OWNED=1` and variant B when `WAKE_OWNED=0` (B has no
   `done` command, since this run owns no wake to close).

Variant A (`WAKE_OWNED=1`):

```text
Quota wake for phase <PHASE_ID> (ai-kit-spec-execute-gsd; state at <RESUME_STATE_PATH>).
Do not re-run Step 1 and do not change the hook. Two branches:
GSD's retry/skip/abort prompt is still pending: answer retry, and nothing else.
GSD already exited: run /gsd-execute-phase <PHASE_ID> with the hook unchanged.
When GSD ends and no further retry is waiting (completed, aborted, a checkpoint or a failure), run this once: python3 <WAKE_SHIM> done --host <WAKE_HOST> --session-id <WAKE_ID>
```

Variant B (`WAKE_OWNED=0`):

```text
Quota wake for phase <PHASE_ID> (ai-kit-spec-execute-gsd; state at <RESUME_STATE_PATH>).
Do not re-run Step 1 and do not change the hook. Two branches:
GSD's retry/skip/abort prompt is still pending: answer retry, and nothing else.
GSD already exited: run /gsd-execute-phase <PHASE_ID> with the hook unchanged.
```

The job lives only as long as the session. After a session exit the owner runs
`/gsd-execute-phase <PHASE_ID>` from the state file's `project_path` with the hook unchanged,
and never re-invokes this skill (that re-runs Step 1, which can rewrite the hook).

Each subsequent exit 75 carrying `retry_after_s=` gets one new one-shot wake at its own delay.
Never schedule before the current invocation exits, and never use a repeated or fixed-interval
job. Whether a wake fires while GSD's prompt is pending is unverified, which is why the prompt's
first branch exists. A host without that scheduler prints `retry_after_s`, the
`RESUME_STATE_PATH=` and the wake prompt, labels the printed re-invoke unverified, lets the
owner run it, and stops there. An owned OS-timer wake (`WAKE_OWNED=1`) is deliberately left
armed in that case: it resumes the session only after the host process exits, so the owner's
handoff and the armed wake cover the stop. Do not run the Close block there.
A `stopped=hard-waits` or `stopped=cap` exit 69 is a terminal owner stop: the runner refuses that lane until the owner deletes the state file it names, which starts a new
episode.

## Close

Run this at every end of the job, and only when `WAKE_OWNED=1`: the phase completed;
`/gsd-execute-phase` returned after a stop answered `abort`; `/gsd-execute-phase` ended any other way (a checkpoint or
verification gap left for the owner, a non-cross-AI failure); or the `Skill` call failed after arming:

```bash
if [ "$WAKE_OWNED" = 1 ]; then
  python3 "$WAKE_SHIM" done --host "$WAKE_HOST" --session-id "$WAKE_ID"
fi
```

Never run it on the exit-75 `retry_after_s=` branch. With a scheduler that branch continues the
run and its one-shot wake still needs the session; without it the run stops with the handoff
printed and the OS-timer wake stays armed on purpose (see "Quota wake"). When `WAKE_OWNED=0`,
call nothing.
