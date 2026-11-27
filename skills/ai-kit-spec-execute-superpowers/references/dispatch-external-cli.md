# Step 3 reference: the `external_cli` dispatch

MANDATORY read in full before the first `dispatch-task` of a task and again before acting on its
result. Do NOT load it for `mode == "native"`. `SKILL.md` Step 3 sends you here; every `$VAR`
below is restored by the scalar loader that opens each `Bash` call (`SKILL.md`, Step 0), and a block
that prints scalars appends them to `$SCALARS` with `tee -a`. The steps, in order: **Artifact
setup**, **Compose**, **Status contract**, **Dispatch**, **Classify** (`ok`, `quota_cycle`, `quota`,
`real_error`), and inside `quota_cycle` and `quota` the named steps **Relay**, **Flagged switch**, **Read tokens**, **Write state** and
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
APPEND keeps the same task (whether the CLI session continues depends on the runtime: sandboxed
codex has no resume form and starts a fresh one). List the task's repo-relative paths in one comma-separated
`<files>…</files>` block: the runner retries in a new session over a changed tree only when
every changed path is listed there. The first dispatch says WRITE `$REPORT_FILE`; every later
one says "APPEND your detailed report to the end of `$REPORT_FILE` — do not overwrite its
existing contents from earlier rounds." (`--report-mode` only controls `dispatch-task`'s own
stdout fallback, never what the CLI does to the file.) On a fix round, also append the open
findings verbatim inside the `<objective>` (the digest hashes only the objective, so a changed
finding set is a new task; the round start in `SKILL.md` Step 3 has already run).

Inside the `<objective>`, put the unit-brief line from `SKILL.md` Step 3 (it names `.aikit/brief/SKILL.md`) before the task text, so every implementer reads the unit brief.

**Gates and commit guard.** `$RUN_DIR/gates.txt` and `$RUN_DIR/guard.txt` follow the one input recipe in `SKILL.md` Step 3 ("Gates and commit guard"); never write or rewrite them here. `dispatch-task` frames each once in the guidance and says a gate is judged by its exit code alone; `--owner-config .aikit/config.toml` adds an instruction for the implementer (never stage, commit or revert that file; leave it out of a clean-tree check), which nothing enforces.

The runner reports `coverage=n/a` for this prompt by design: its coverage check counts the task blocks in the whole prompt, and ai-kit's own text adds none (wrapping the task would turn a missed commit into a `partial` stop). Gate, guard or verify text the caller supplies is copied verbatim, so a task tag inside it would be counted. No counter here claims progress it cannot see.

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
GUIDE_ARGS=(--owner-config .aikit/config.toml)
[ -f "$RUN_DIR/gates.txt" ] && GUIDE_ARGS+=(--gates-file "$RUN_DIR/gates.txt")
[ -f "$RUN_DIR/guard.txt" ] && GUIDE_ARGS+=(--guard-file "$RUN_DIR/guard.txt")
python3 "$SHIM" dispatch-task --injection-json "$(cat "$RUN_DIR/INJECTION_JSON.json")" \
  --prompt-file "$PROMPT_FILE" --target-dir "$CWD" --heartbeat-interval 60 --timeout 1800 \
  --format-block-file "$FORMAT_BLOCK_FILE" --report-file "$REPORT_FILE" \
  --report-mode "$REPORT_MODE" "${GUIDE_ARGS[@]}" > "$DISPATCH_BASE.json" 2> "$DISPATCH_BASE.err"
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

## Host-config audit

`dispatch-task` snapshots the modification times of these files under the lane's HOME before and after the lane: `.claude/settings.json`, `.claude.json`, `.config/opencode/opencode.json`, `.config/opencode/opencode.jsonc`, `.codex/config.toml`, `.cursor/cli-config.json`, `.cursor/mcp.json`, `.cursor/hooks.json`, `.copilot/mcp-config.json`, `.gsd/defaults.json` (files only; it never lists a folder). Each changed file prints exactly this line in `$DISPATCH_BASE.err`: `ai-kit-spec: observation: <path> changed during the lane; a host may rewrite its own config, so this does not show the lane changed it` (`<path>` is the absolute path), and its absolute path goes into the result's `host_config_changed`; a file whose modification time could not be read prints `ai-kit-spec: observation: host-config audit unavailable for <path>` instead and is never reported as changed; a dispatch that fails or raises still reports. Relay those lines verbatim right after `dispatch-task` returns, before the empty-result stop (an empty `DISPATCH_RESULT_JSON`), before `## Classify` and whichever class follows (`ok`, `quota_cycle`, `quota` or `real_error`): they are observations (a host may rewrite its own config), never a stop, a retry or a reason to change the classification. Config folders moved by `CLAUDE_CONFIG_DIR`, `CODEX_HOME`, `XDG_CONFIG_HOME` or `OPENCODE_CONFIG_DIR` are not checked, and the output says so. A native dispatch runs the same audit through `host-config-audit` (SKILL.md Step 3); there a missing snapshot prints the `audit unavailable` observation, relayed like any other.

## Classify

```bash
DISPATCH_RESULT_JSON="$(cat "$DISPATCH_BASE.json")"
CLASSIFICATION="$(python3 "$SHIM" classify-dispatch-failure --dispatch-result-json "$DISPATCH_RESULT_JSON")"
printf 'CLASSIFICATION=%s\n' "$CLASSIFICATION" | tee -a "$SCALARS"
```

It prints one JSON object, for example `{"class": "quota_cycle", "retry_after_s": 600, "cycle": 2}`, and this is the only classifier call: branch on its `class` (`ok`, `quota_cycle`, `quota` or `real_error`); `retry_after_s` and `cycle` are whole numbers, or `null` when the runner printed none or a malformed one. The runner statuses `locked` and `partial` always classify `real_error`. An answer that is not that object schedules nothing: stop exactly as the `real_error` branch does.

- **`"ok"`** — run `printf 'LAST_DISPATCHED_KEY=%s\n' "$INJECTION_KEY" | tee -a "$SCALARS"` (only an
  `ok` dispatch sets the next round's escalation anchor; `quota_cycle`, `quota` and `real_error` never do), clear
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
- **`"quota_cycle"`** and **`"quota"`** — the runner's hard-tier outcome: `quota_cycle` is a confirmed-router quota stop or an exhausted
  transient ladder carrying whole-number `retry_after_s=` and `cycle=` (exit 75); `quota` is the terminal `RETURNCODE` 69 hard-tier
  stops and a bare `RETURNCODE` 75. The
  classifier also returns `"quota"` when `reason == "quota"` at any other `RETURNCODE`. Whether each case waits once or stops is decided in [`resolution-stops.md#owner-stop`](resolution-stops.md#owner-stop) ("Dispatch-time stops"); **Schedule-or-stop** below holds only the wait and schedule blocks. In this
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

  **Flagged switch.** Runs for every classified "quota_cycle" and "quota", before Read tokens, before the one-shot wait and before any owner stop. Only a lane the owner flagged `usage_limited` whose runner result proves quota moves to its configured fallback of another pool, and only when the replacement resolves; a transient or capacity result, any other lane, and a replacement that does not resolve change nothing. At fix round 4 or 5 the switch stays inside the escalation gate: the block passes the gate's `ESCALATION_EXCLUDE_JSON.json` as a second exclude file, so the fallback must be a lane the gate allowed (above the stuck lane, along its enabled flags; with both flags off, no move to another runtime or model) that the switch rule also accepts; when no lane passes both, executor-fallback answers `no fallback`, `SWITCHED=0`, and the stop rules below report the flagged lane, never a replacement; at round 4 or later with no gate file the block runs no switch at all (`SWITCHED=0`). A switched answer carries the new key and `exclude`, every other key of the task's `ladder_keys`, which the re-resolve passes as its escalation exclusion so it can only return that key.

```bash
SWITCHED=0
SWITCH_RC=0
SWITCH_KEY=""
rm -f "$RUN_DIR/SWITCH_JSON.json"
GATE_EXCLUDE=()
if [ "${FIX_ROUND:-0}" -ge 4 ]; then
  if [ -f "$RUN_DIR/ESCALATION_EXCLUDE_JSON.json" ]; then GATE_EXCLUDE=(--exclude-keys-file "$RUN_DIR/ESCALATION_EXCLUDE_JSON.json"); else SWITCH_RC=1; fi
fi
if [ "$SWITCH_RC" -eq 0 ]; then
  python3 "$SHIM" executor-fallback --cwd "$CWD" --key "$INJECTION_KEY" --dispatch-result "$DISPATCH_BASE.json" \
    --exclude-keys-file "$RUN_DIR/EXCLUDED_KEYS_JSON.json" "${GATE_EXCLUDE[@]}" --injection-file "$RUN_DIR/INJECTION_JSON.json" > "$RUN_DIR/SWITCH_JSON.json" || SWITCH_RC=$?
fi
if [ "$SWITCH_RC" -eq 0 ]; then
  SWITCH_KEY="$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); k=d.get("key"); print(k if d.get("switched") is True and isinstance(k, str) else "")' "$RUN_DIR/SWITCH_JSON.json" 2>/dev/null)"
fi
if [ -n "$SWITCH_KEY" ]; then
  PRIOR_REASONS_JSON="$(cat "$RUN_DIR/PRIOR_REASONS_JSON.json")"
  WAVE_REASONS_JSON="$(cat "$RUN_DIR/WAVE_REASONS_JSON.json")"
  EXCLUDED_KEYS_JSON="$(cat "$RUN_DIR/EXCLUDED_KEYS_JSON.json")"
  EXCLUDED_REASONS_JSON="$(python3 -c 'import json,sys; a=json.loads(sys.argv[1]); a.update(json.loads(sys.argv[2])); print(json.dumps(a))' \
    "$PRIOR_REASONS_JSON" "$WAVE_REASONS_JSON")"
  SWITCH_EXCLUDE_JSON="$(python3 -c 'import json,sys; print(json.dumps(json.load(open(sys.argv[1]))["exclude"]))' "$RUN_DIR/SWITCH_JSON.json" 2>/dev/null)"
  python3 "$SHIM" resolve-injection --cwd "$CWD" --task-file "$BRIEF_FILE" \
    --quota-path "$QUOTA_PATH" --exclude-keys-json "$EXCLUDED_KEYS_JSON" \
    --excluded-reasons-json "$EXCLUDED_REASONS_JSON" \
    --escalation-excluded-keys-json "$SWITCH_EXCLUDE_JSON" --no-fallback > "$RUN_DIR/SWITCH_INJECTION_JSON.json"
  RESOLVE_RC=$?
  if [ "$RESOLVE_RC" -eq 0 ] && python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); sys.exit(0 if isinstance(d, dict) and d.get("mode") in ("external_cli", "native") and d.get("key") == sys.argv[2] else 1)' "$RUN_DIR/SWITCH_INJECTION_JSON.json" "$SWITCH_KEY" 2>/dev/null; then
    NEW_MODE="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["mode"])' "$RUN_DIR/SWITCH_INJECTION_JSON.json")"
    NEW_RUNTIME="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("runtime") or "")' "$RUN_DIR/SWITCH_INJECTION_JSON.json")"
    if cp "$RUN_DIR/INJECTION_JSON.json" "$RUN_DIR/SWITCH_BACKUP_JSON.json" && mv "$RUN_DIR/SWITCH_INJECTION_JSON.json" "$RUN_DIR/INJECTION_JSON.json"; then
      if printf 'INJECTION_MODE=%s\nINJECTION_KEY=%s\nINJECTION_RUNTIME=%s\n' "$NEW_MODE" "$SWITCH_KEY" "$NEW_RUNTIME" >> "$SCALARS"; then
        SWITCHED=1
      else
        mv "$RUN_DIR/SWITCH_BACKUP_JSON.json" "$RUN_DIR/INJECTION_JSON.json"
      fi
    fi
  fi
fi
rm -f "$RUN_DIR/SWITCH_INJECTION_JSON.json" "$RUN_DIR/SWITCH_BACKUP_JSON.json"
if [ "$SWITCHED" -eq 1 ]; then
  INJECTION_JSON="$(cat "$RUN_DIR/INJECTION_JSON.json")"
  INJECTION_MODE="$NEW_MODE"
  INJECTION_KEY="$SWITCH_KEY"
  INJECTION_RUNTIME="$NEW_RUNTIME"
fi
printf 'SWITCHED=%s\n' "$SWITCHED" | tee -a "$SCALARS"
```

  `SWITCHED=1` is set only after the move and the scalar write both succeed; a failed copy or move leaves the original in place, and a failed scalar write after the move puts the backup back, so the original injection and classification go on. The block writes no wave file: Relay's fold above already added the failed key to `WAVE_TRIED_JSON.json`, `WAVE_REASONS_JSON.json` (reason `quota`) and `EXCLUDED_KEYS_JSON.json`, and the block never touches `PRIOR_EXCLUDED_KEYS_JSON.json` or `PRIOR_REASONS_JSON.json`, so the switch clears no permanent exclusion.

  With `SWITCHED=1`, tell the owner in one line which lane moved to which fallback and why (its usage_limited flag and the quota the runner reported), then dispatch the new injection in this same round as Step 3 dispatches its mode (`external_cli`: this file's Dispatch step and Classify again; `native`: a fresh native subagent through Step 3's native launch, never a resume of a prior agent, in any fix round: the failed external dispatch left no native agent to resume); `REPORT_MODE` stays as it is. Read tokens, Write state and Schedule-or-stop do not run for the old lane, so no resume file is written for it. The fallback is never itself flagged, so a quota stop on it goes on to Read tokens like any other. With `SWITCHED=0` (an exit 1 or 2 of executor-fallback, a resolve that failed or printed anything but the switched key in `external_cli` or `native` mode, a failed copy, move or scalar write) nothing changed: the original classification and injection go on to Read tokens below. `$RUN_DIR/SWITCH_JSON.json` keeps this round's switch answer for the report; the block deletes one left by an earlier switch before it runs, so a round that ran no switch leaves none.

  **Read tokens.** `retry_after_s` and `cycle` are the keys of `$CLASSIFICATION` (the scalar loader restores it): whole numbers or `null`. Never parse the dispatch result by hand.

  **Write state.** Runs for every classified `"quota_cycle"` and `"quota"`, owner stops included, so each stop has a
  `$RESUME_STATE_PATH` to report. This branch already folded this key into the wave sets, so run the pinned
  variant of the resumable-state bash, shown in full in `references/state-management.md` under
  "Pinned-injection state write": it uses the loaded `RESUME_STATE_PATH` and persists
  `INJECTION_JSON.json` as `injection_json`, so the wake re-dispatches this exact injection. Do not
  edit the Step 2 block by hand. If that block exits non-zero, nothing was saved: skip
  Schedule-or-stop, show the error and stop for the owner (schedule and re-arm nothing).

  **Schedule-or-stop.** **MANDATORY: read [`resolution-stops.md#owner-stop`](resolution-stops.md#owner-stop) ("Dispatch-time stops") before scheduling or stopping**: it decides whether this outcome waits once or stops; on an owner stop, schedule nothing, re-arm nothing and report as that list says.
  On the one-shot wait path only, first re-arm the wake with that state file, using the
  recorded identity (the block calls nothing when `WAKE_OWNED=0`):

```bash
if [ "$WAKE_OWNED" = 1 ]; then
  python3 "$WAKE_SHIM" arm --host "$WAKE_HOST" --session-id "$WAKE_ID" --ref "$RESUME_STATE_PATH"
fi
```

  Where `CronCreate` is callable, schedule one one-shot wake at `retry_after_s` (`$CLASSIFICATION`'s `retry_after_s`;
  whole-minute rounding and the under-60 s case: ai-kit-cross-ai section 6) with the wake
  prompt; the job lives only as long as the session. **MANDATORY: read
  `references/quota-wake.md` in full before scheduling or printing a wake** (Do NOT load it on an
  owner stop) — it holds the
  prompt, its fourteen placeholders and the woken run's resume rules. A host without that
  scheduler, or a wait it cannot represent, schedules nothing: it prints `retry_after_s`,
  `$RESUME_STATE_PATH` and that same prompt, marks the printed row unverified, and the owner
  runs it. Never a repeated or fixed-interval job. Either way, pause and end the turn:
  do not start the next task until the wake's "ok" path has handled this task's report.
- **`"real_error"`** — an owner stop decided in [`resolution-stops.md#owner-stop`](resolution-stops.md#owner-stop) ("Dispatch-time stops"; NEVER index); its mechanics follow. Relay the runner's report, upstream and `AIKIT-XAI` lines from `$DISPATCH_BASE.err`
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
  fix re-dispatches the same injection ([`state-management.md#pinned-resume`](state-management.md#pinned-resume)). For a different pair, the owner names it and you follow
  state-management.md's "Owner-named replacement pair".
