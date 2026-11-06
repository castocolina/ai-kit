# Step 3 reference: the `external_cli` dispatch

MANDATORY read in full before the first `dispatch-task` of a task and again before acting on its
result. Do NOT load it for `mode == "native"`. `SKILL.md` Step 3 sends you here; every `$VAR`
below is restored by the scalar loader that opens each `Bash` call (`SKILL.md`, Step 0), and a block
that prints scalars appends them to `$SCALARS` with `tee -a`. The steps, in order: **Artifact
setup**, **Compose**, **Status contract**, **Dispatch**, **Classify** (`ok`, `quota`,
`real_error`), and inside `quota` the named steps **Relay**, **Read tokens**, **Write state** and
**Schedule-or-stop**. Other files refer to them by these names, never by number.

## Artifact setup

Create the artifact paths once, derived from `$BRIEF_FILE` (`…/task-N-brief.md`):

```bash
TASK_STATE_DIR="$(dirname "$BRIEF_FILE")/.ai-kit-spec-execute-superpowers"
mkdir -p "$TASK_STATE_DIR"
PROMPT_FILE="$TASK_STATE_DIR/task-${TASK_N}-prompt.txt"
FORMAT_BLOCK_FILE="$TASK_STATE_DIR/task-${TASK_N}-format-block.md"
REPORT_FILE="${BRIEF_FILE%-brief.md}-report.md"
DISPATCH_BASE="$(mktemp -d)/task-${TASK_N}-dispatch"  # outside the repo: never a tree change
for n in PROMPT_FILE FORMAT_BLOCK_FILE REPORT_FILE DISPATCH_BASE; do printf '%s=%s\n' "$n" "${!n}"; done | tee -a "$SCALARS"
```

`$REPORT_FILE` is the path subagent-driven-development's review and ledger already read; the
other two are this adapter's scratch files. Set the initial report mode as soon as it is known — a
resumed task may already have a partial report:

```bash
if [ -s "$REPORT_FILE" ]; then REPORT_MODE=append; else REPORT_MODE=write; fi
printf 'REPORT_MODE=%s\n' "$REPORT_MODE" | tee -a "$SCALARS"
```

After EVERY `dispatch-task` call, whatever its outcome, set `REPORT_MODE=append` and never set it
back to `write` for this task.

## Compose

Compose the prompt from subagent-driven-development's implementer-prompt.md template (the controller
holds it from Step 1's loaded skill; brief path, context, report-file path, the "you do not dispatch subagents" contract) into
`$PROMPT_FILE`. It must tell the CLI to put its detailed report in `$REPORT_FILE` and return
only a short status line. Put everything the implementer is asked to do inside one
`<objective>…</objective>` block, and keep the WRITE/APPEND report sentence below outside it:
the runner's task digest hashes only the objective text, so a quota wake that changes WRITE to
APPEND still reuses the session. List the task's repo-relative paths in one comma-separated
`<files>…</files>` block: the runner retries in a new session over a changed tree only when
every changed path is listed there. The first dispatch says WRITE `$REPORT_FILE`; every later
one says "APPEND your detailed report to the end of `$REPORT_FILE` — do not overwrite its
existing contents from earlier rounds." (`--report-mode` only controls `dispatch-task`'s own
stdout fallback, never what the CLI does to the file.) On a fix round, also append the open
findings verbatim inside the `<objective>` (the digest hashes only the objective, so a changed
finding set is a new task; the round start in `SKILL.md` Step 3 has already run).

Inside the `<objective>`, put this line before the task text, so every implementer reads the unit brief: `Unit brief: read .aikit/brief/SKILL.md in $CWD after the plan and spec; it lists the previous unit's changed files and the documents that mention them. If it is missing, says no brief, or names another unit, say so and continue.`

## Status contract

Write the status contract (`DONE` / `DONE_WITH_CONCERNS` / `NEEDS_CONTEXT` / `BLOCKED`, from
implementer-prompt.md's "After Review Findings") to `$FORMAT_BLOCK_FILE`, and require the reply
to declare exactly one of them on a line of its own, `STATUS: <word>`. It becomes the
dispatch's format block.

## Dispatch

`dispatch-task` prepares tooling guidance itself and runs the pair through the supervised
runner. `--timeout 1800` is a fixed constant and the budget for the whole call, every retry rung
included (`references/design-notes.md`). **Hard rule:** run this call in the background (the
Bash tool's `run_in_background`, or `&` plus a poll loop on a host without it), never under a
foreground tool timeout, which kills it and loses the evidence lines. It is finished only when
the `.exit` file exists; poll for it in a later call.

```bash
mkdir -p "$(dirname "$DISPATCH_BASE")"  # a long wait may outlive the temp dir
rm -f "$DISPATCH_BASE.exit"
python3 "$SHIM" dispatch-task --injection-json "$(cat "$RUN_DIR/INJECTION_JSON.json")" \
  --prompt-file "$PROMPT_FILE" --target-dir "$CWD" --heartbeat-interval 60 --timeout 1800 \
  --format-block-file "$FORMAT_BLOCK_FILE" --report-file "$REPORT_FILE" \
  --report-mode "$REPORT_MODE" > "$DISPATCH_BASE.json" 2> "$DISPATCH_BASE.err"
echo "$?" > "$DISPATCH_BASE.exit"
```

The quotes around `"$(cat ...)"` are mandatory: they keep the JSON one argv.

Then, in a new call once `$DISPATCH_BASE.exit` exists (the file only marks completion; the shim
exits 0 after a dispatch and the outcome is in the JSON):

```bash
REPORT_MODE=append
printf 'REPORT_MODE=%s\n' "$REPORT_MODE" | tee -a "$SCALARS"
```

`DISPATCH_RESULT_JSON` is the file `$DISPATCH_BASE.json`; every block below that needs it starts with
`DISPATCH_RESULT_JSON="$(cat "$DISPATCH_BASE.json")"`, and its text is never pasted into a command.
An empty `DISPATCH_RESULT_JSON` (a missing prompt file or a non-`external_cli` injection: a
local error, no JSON, no `AIKIT-XAI` line) skips Classify: relay the tail of
`$DISPATCH_BASE.err` verbatim, then stop exactly as the `real_error` branch does (pinned state
write, report the path), with no re-resolve. A non-`external_cli` injection fails the same way
on every re-invoke, so tell the owner this case needs a replacement pair they name (state-management.md,
"Owner-named replacement pair").

The runner's evidence lines (`cross-ai: report`, `cross-ai: upstream`, `AIKIT-XAI`, and a
`cross-ai: state` or `cross-ai: lane stopped=` path) are in `$DISPATCH_BASE.err`.
`--heartbeat-interval` is required but unused (the runner prints its own heartbeat).

If the CLI wrote `$REPORT_FILE` itself, `dispatch-task` leaves it untouched; otherwise it writes or
appends the captured stdout behind a marker line. Review and the fix loop read `$REPORT_FILE`
like a native report either way.

## Classify

```bash
DISPATCH_RESULT_JSON="$(cat "$DISPATCH_BASE.json")"
CLASSIFICATION="$(python3 "$SHIM" classify-dispatch-failure --dispatch-result-json "$DISPATCH_RESULT_JSON")"
printf 'CLASSIFICATION=%s\n' "$CLASSIFICATION"
```

- **`"ok"`** — run `printf 'LAST_DISPATCHED_KEY=%s\n' "$INJECTION_KEY" | tee -a "$SCALARS"` (only an
  `ok` dispatch sets the next round's escalation anchor; `quota` and `real_error` never do), clear
  the resume state (`SKILL.md` Step 3, "Clear the resume state"), then continue
  with subagent-driven-development's "2. Handle the report", reading the status from `stdout`,
  never from `$REPORT_FILE`:

```bash
DISPATCH_RESULT_JSON="$(cat "$DISPATCH_BASE.json")"
STATUS="$(python3 "$SHIM" implementer-status --dispatch-result-json "$DISPATCH_RESULT_JSON")"
printf 'STATUS=%s\n' "$STATUS"
```

  `implementer-status` counts only a line that declares a status, never a status word inside
  prose; no declaration, or two different ones, prints `BLOCKED` (never scan `$REPORT_FILE`). For a
  `BLOCKED` from an external CLI, follow the handler's BLOCKED routes in its "2. Handle the report" (1 more context, 3 split,
  4 plan defect) on the same pair, but never its route 2 ("more capable model") on your own: that is a model switch
  after an unusable run, so stop and report for the owner's decision.
- **`"quota"`** — the runner's hard-tier outcome: a confirmed-router quota stop or an exhausted
  transient ladder carrying `retry_after_s=`, and also the terminal `RETURNCODE` 69 hard-tier
  stops and a bare `RETURNCODE` 75; **Schedule-or-stop** below decides wait versus stop. The
  classifier also returns `"quota"` when `reason == "quota"` at any other `RETURNCODE`; that case
  is an owner stop too (no re-resolve: NEVER index). In this
  order:

  **Relay.** Relay the `cross-ai: report`, `cross-ai: upstream` and `AIKIT-XAI` lines verbatim
  from `$DISPATCH_BASE.err` before folding, reading tokens or writing state: a later step must
  not act on a stop it has not relayed. Then fold this key in as a wave-tried key WITH the
  `"quota"` reason, never straight into `$EXCLUDED_KEYS_JSON` without one. The `real_error` branch
  has its own complete fold block (never this one):

```bash
FOLD_REASON=quota
PRIOR_EXCLUDED_KEYS_JSON="$(cat "$RUN_DIR/PRIOR_EXCLUDED_KEYS_JSON.json")"
WAVE_TRIED_JSON="$(cat "$RUN_DIR/WAVE_TRIED_JSON.json")"
WAVE_REASONS_JSON="$(cat "$RUN_DIR/WAVE_REASONS_JSON.json")"
WAVE_TRIED_JSON="$(python3 -c 'import json,sys; print(json.dumps(sorted(set(json.loads(sys.argv[1])) | {sys.argv[2]})))' \
  "$WAVE_TRIED_JSON" "$INJECTION_KEY")"
WAVE_REASONS_JSON="$(python3 -c 'import json,sys; d=json.loads(sys.argv[1]); d[sys.argv[2]]=sys.argv[3]; print(json.dumps(d))' \
  "$WAVE_REASONS_JSON" "$INJECTION_KEY" "$FOLD_REASON")"
EXCLUDED_KEYS_JSON="$(python3 -c 'import json,sys; print(json.dumps(sorted(set(json.loads(sys.argv[1])) | set(json.loads(sys.argv[2])))))' \
  "$PRIOR_EXCLUDED_KEYS_JSON" "$WAVE_TRIED_JSON")"
printf '%s' "$WAVE_TRIED_JSON" > "$RUN_DIR/WAVE_TRIED_JSON.json"
printf '%s' "$WAVE_REASONS_JSON" > "$RUN_DIR/WAVE_REASONS_JSON.json"
printf '%s' "$EXCLUDED_KEYS_JSON" > "$RUN_DIR/EXCLUDED_KEYS_JSON.json"
printf 'FOLD_REASON=%s\n' "$FOLD_REASON"
```

  **Read tokens.** `retry_after_s` and `cycle` are in the nested `status` dict parsed from the
  runner's `AIKIT-XAI` line, not at the top level of `$DISPATCH_RESULT_JSON`:

```bash
DISPATCH_RESULT_JSON="$(cat "$DISPATCH_BASE.json")"
RETURNCODE="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1]).get("returncode"))' "$DISPATCH_RESULT_JSON")"
RETRY_AFTER_S="$(python3 -c 'import json,sys; d=json.loads(sys.argv[1]); s=d.get("status") or {}; print("" if s.get("retry_after_s") is None else s.get("retry_after_s"))' "$DISPATCH_RESULT_JSON")"
CYCLE="$(python3 -c 'import json,sys; d=json.loads(sys.argv[1]); s=d.get("status") or {}; print("" if s.get("cycle") is None else s.get("cycle"))' "$DISPATCH_RESULT_JSON")"
printf 'RETURNCODE=%s\nRETRY_AFTER_S=%s\nCYCLE=%s\n' "$RETURNCODE" "$RETRY_AFTER_S" "$CYCLE" | tee -a "$SCALARS"
```

  **Write state.** Runs for every classified `"quota"`, owner stops included, so each stop has a
  `$RESUME_STATE_PATH` to report. This branch already folded this key into the wave sets, so run the pinned
  variant of the resumable-state bash, shown in full in `references/state-management.md` under
  "Pinned-injection state write": it uses the loaded `RESUME_STATE_PATH` and persists
  `INJECTION_JSON.json` as `injection_json`, so the wake re-dispatches this exact injection. Do not
  edit the Step 2 block by hand.

  **Schedule-or-stop.** Only a classified `"quota"` with `RETURNCODE` 75 and `RETRY_AFTER_S` and
  `CYCLE` both matching `[0-9]+` gets the one-shot wait and re-dispatch of the same task, lane and
  model (a hint such as `600s` classifies `real_error` and never reaches this branch). A tokenless
  runner `RETURNCODE` 69 or 75 whose status is `transient` or `quota` is classified `quota` but is
  an owner stop: relay, write pinned state, schedule nothing. A `RETURNCODE` 69
  (`stopped=hard-waits`, `stopped=cap`, or a `cross-ai: lane stopped=` refusal) is an owner stop
  after relaying the evidence, including that line's state path, whose deletion is the owner's
  reset; schedule nothing and re-arm nothing. A bare `RETURNCODE` 75 is also an owner stop.
  On the one-shot wait path only, first re-arm the wake with that state file, using the
  recorded identity (the block calls nothing when `WAKE_OWNED=0`):

```bash
if [ "$WAKE_OWNED" = 1 ]; then
  python3 "$WAKE_SHIM" arm --host "$WAKE_HOST" --session-id "$WAKE_ID" --ref "$RESUME_STATE_PATH"
fi
```

  Where `CronCreate` is callable, schedule one one-shot wake at `retry_after_s` (`RETRY_AFTER_S`;
  whole-minute rounding and the under-60 s case: ai-kit-cross-ai section 6) with the wake
  prompt; the job lives only as long as the session. **MANDATORY: read
  `references/quota-wake.md` in full before scheduling or printing a wake** (Do NOT load it on an
  owner stop) — it holds the
  prompt, its fourteen placeholders and the woken run's resume rules. A host without that
  scheduler, or a wait it cannot represent, schedules nothing: it prints `retry_after_s`,
  `$RESUME_STATE_PATH` and that same prompt, marks the printed row unverified, and the owner
  runs it. Never a repeated or fixed-interval job. Either way, pause and end the turn:
  do not start the next task until the wake's "ok" path has handled this task's report. No
  other stop (the cap, auth, off-router billing, permission, bad model, `not_installed`, a bare
  `RETURNCODE` 75) is scheduled; for each, report `$RESUME_STATE_PATH`: an owner re-invoke
  re-dispatches the pinned injection, or runs the "Owner-named replacement pair" recipe in
  `references/state-management.md` for a pair the owner names.
- **`"real_error"`** — a failed external dispatch stops for the owner (NEVER index). Relay the runner's report, upstream and `AIKIT-XAI` lines from `$DISPATCH_BASE.err`
  verbatim first (a pre-spawn refusal has none: relay its `ai-kit-spec:` line), then read
  `$DISPATCH_RESULT_JSON`'s `reason` and report its fix with the reason-to-fix list in
  `references/resolution-stops.md`. Only a `real_error` reason proper (a crash, an empty answer, no change) offers the owner
  more context and a retry, a split of the task, or a ruling on a plan defect. Before stopping,
  fold the failed key into the wave sets with its real reason, so a replacement pair the owner
  names cannot re-pick it. Run this complete block as printed (not the quota block above):

```bash
DISPATCH_RESULT_JSON="$(cat "$DISPATCH_BASE.json")"
FOLD_REASON="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1] or "{}").get("reason") or "real_error")' "$DISPATCH_RESULT_JSON")"
PRIOR_EXCLUDED_KEYS_JSON="$(cat "$RUN_DIR/PRIOR_EXCLUDED_KEYS_JSON.json")"
WAVE_TRIED_JSON="$(cat "$RUN_DIR/WAVE_TRIED_JSON.json")"
WAVE_REASONS_JSON="$(cat "$RUN_DIR/WAVE_REASONS_JSON.json")"
WAVE_TRIED_JSON="$(python3 -c 'import json,sys; print(json.dumps(sorted(set(json.loads(sys.argv[1])) | {sys.argv[2]})))' \
  "$WAVE_TRIED_JSON" "$INJECTION_KEY")"
WAVE_REASONS_JSON="$(python3 -c 'import json,sys; d=json.loads(sys.argv[1]); d[sys.argv[2]]=sys.argv[3]; print(json.dumps(d))' \
  "$WAVE_REASONS_JSON" "$INJECTION_KEY" "$FOLD_REASON")"
EXCLUDED_KEYS_JSON="$(python3 -c 'import json,sys; print(json.dumps(sorted(set(json.loads(sys.argv[1])) | set(json.loads(sys.argv[2])))))' \
  "$PRIOR_EXCLUDED_KEYS_JSON" "$WAVE_TRIED_JSON")"
printf '%s' "$WAVE_TRIED_JSON" > "$RUN_DIR/WAVE_TRIED_JSON.json"
printf '%s' "$WAVE_REASONS_JSON" > "$RUN_DIR/WAVE_REASONS_JSON.json"
printf '%s' "$EXCLUDED_KEYS_JSON" > "$RUN_DIR/EXCLUDED_KEYS_JSON.json"
printf 'FOLD_REASON=%s\n' "$FOLD_REASON"
```

  Then run the "Pinned-injection state write" block (`references/state-management.md`) and report
  `$RESUME_STATE_PATH`: it keeps the pair, the fix round and the anchor, so a re-invoke after the
  fix re-dispatches the same injection. For a different pair, the owner names it and you follow
  state-management.md's "Owner-named replacement pair".
