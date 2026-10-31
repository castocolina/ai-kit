# Cross-AI hook setup

`SKILL.md` Step 2 sends you here in `cross_ai_hook` mode, after the plan opt-in check passed.
Run the block below as ONE `Bash` call, with every `$VAR` replaced by the literal value Steps 0
and 1 printed (`$GSD_SHIM`, `$CURATED_PY`, `$CWD`, `$RUN_ID`, `$RESULT_RUNTIME`, `$RESULT_MODEL`,
`$RESULT_CROSS_AI_COMMAND`). Never re-parse `RESULT_JSON` here. `RESULT_MODE` is not an input:
the block sets it itself (`cross_ai_hook`, or `fallback_notice` when nothing was written).

The producer runs first and its status is checked before anything is written: a failure or
empty guidance never reaches `ensure-runner`, and a not-ready runner writes no config key. The stored
command gets NO manual quoting around its tokens; that is deliberate, see
[dispatch-notes.md](dispatch-notes.md#why-no-manual-quoting-around-workflowcross_ai_commands-values).

```bash
RESULT_MODE="cross_ai_hook"
clear_hook() {  # exit 1 also covers a non-empty revert_failed, which only follows a failed key
  CLEAR="$(python3 "$GSD_SHIM" clear-workflow-keys --cwd "$CWD" --run-id "$RUN_ID" \
    --key cross_ai_command --key cross_ai_execution --key cross_ai_timeout)" || {
    echo "$CLEAR"
    echo "ai-kit-spec-execute-gsd: cleanup failed; an old hook may still be active"
    exit 1
  }
}
GUIDANCE="$(python3 "$GSD_SHIM" print-dispatch-guidance --runtime "$RESULT_RUNTIME" --model "$RESULT_MODEL")"
GUIDANCE_RC=$?
if [ ! -f "$CURATED_PY" ]; then
  echo "ai-kit-spec-execute-gsd: the ai-kit-gsd-curated-config skill is not installed (CURATED_PY empty); nothing written"
  clear_hook
  RESULT_MODE="fallback_notice"
elif [ "$GUIDANCE_RC" -ne 0 ] || [ -z "$GUIDANCE" ]; then
  echo "ai-kit-spec-execute-gsd: dispatch guidance unavailable (exit $GUIDANCE_RC); nothing written"
  clear_hook
  RESULT_MODE="fallback_notice"
else
  ENSURE_FILE="$(mktemp)"
  printf '%s\n' "$GUIDANCE" | python3 "$CURATED_PY" ensure-runner --cwd "$CWD" --guidance-file - > "$ENSURE_FILE"
  ENSURE_RC=${PIPESTATUS[1]}
  ENSURE="$(cat "$ENSURE_FILE")"
  rm -f "$ENSURE_FILE"
  if [ "$ENSURE_RC" -eq 0 ]; then
    [ -n "$ENSURE" ] && echo "$ENSURE"  # a kept, user-edited runner reports notes on success too
    WRITE="$(python3 "$GSD_SHIM" write-workflow-keys --cwd "$CWD" --run-id "$RUN_ID" \
      --set "cross_ai_command=$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$RESULT_CROSS_AI_COMMAND")" \
      --set cross_ai_execution=true \
      --min cross_ai_timeout=1800)"
    WRITE_RC=$?
    if [ "$WRITE_RC" -ne 0 ]; then
      echo "$WRITE"
      echo "ai-kit-spec-execute-gsd: writing the hook failed (exit $WRITE_RC)"
      exit 1
    fi
  else
    echo "ai-kit-spec-execute-gsd: the project runner is not ready (exit $ENSURE_RC); no hook written"
    echo "$ENSURE"
    clear_hook
    RESULT_MODE="fallback_notice"
  fi
fi
printf 'RESULT_MODE=%s\n' "$RESULT_MODE"
```

## What each outcome means

- **`RESULT_MODE=fallback_notice`, exit 0.** A missing curated-config shim (`CURATED_PY` printed
  empty; its own message says to install `ai-kit-gsd-curated-config`), a non-zero producer exit
  or empty guidance ("dispatch guidance unavailable"), or an `ensure-runner` exit of 1 (not
  ready: a user-edited runner on an older or foreign template gets a `.new` file plus the
  printed notes) or 2 (error) wrote no config key, and the cleanup succeeded. STOP and report
  the notes. A runner-setup failure never continues into Step 3, because Step 3 would hand the
  phase to GSD's native executor. Continue only when the owner explicitly says to run this
  phase natively: then go straight to Step 3 with `RESULT_MODE=fallback_notice`, never
  re-running Step 1 or 2.
- **Exit 1 from the cleanup.** A clear failed and was rolled back; an old hook may still be
  active. STOP and show the output, naming the keys in `failed` and `revert_failed`.
- **Exit 1 from the write.** A key failed and earlier keys from that call were reverted (any in
  `revert_failed` still hold the new value). Exit 2 inside either shim call means `node` or
  `gsd-tools.cjs` was not found, gsd-tools could not resolve the config path, the config is
  malformed, or (write only) a `--set`/`--min` spec did not parse. Show the output and STOP.
- **`RESULT_MODE=cross_ai_hook`, exit 0.** The hook is written, `cross_ai_execution` is on, and
  `cross_ai_timeout` is raised to 1800 seconds (curated-config's runner floor) unless it already
  holds an int of at least that. A user value of at least 1800 is left as is and stays theirs. A
  lower one is raised and owned, so a later cleanup deletes the key and does not restore the
  user's lower value: GSD then uses its own 300 s default. Tell the owner; the original is in
  the per-run backup `<config>.ai-kit-spec-execute-gsd.<run_id>.bak`. Relay any notes
  `ensure-runner` printed.

The printed `RESULT_MODE=` line replaces the Step 1 value for every later step, so Step 3
follows the mode that was actually set up.

## Node

Subprocess dispatch needs Node 24 (GSD's floor, unverified: the installed gsd-core declares
none); older versions untested. The hook starts with `node .planning/scripts/cross-ai.mjs`, so
without Node it cannot launch and never reaches the runner's `dispatch_unavailable` path. Step 1
already stops when `node` is not on PATH. If Node disappears between Step 1 and the hook, do not
claim a native fallback: run the mode-transition cleanup (`SKILL.md` Step 2) and STOP. Hand the
phase to GSD with no hook only when the owner explicitly decides to run it natively. If the
cleanup fails, STOP and show its output.
