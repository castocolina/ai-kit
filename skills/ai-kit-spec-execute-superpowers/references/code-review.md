# Code review (after the final review, before Step 5)

MANDATORY: read this file in full once the final whole-branch review passes, before Step 5. Do NOT load it at any other point.

The whole plan's diff (`$FOLD_BASE..HEAD`) is reviewed after subagent-driven-development's final whole-branch review and before the fold step, in at most 3 rounds: it passes when no CRITICAL or HIGH finding is open; MEDIUM and LOW findings are listed and never block. Hold subagent-driven-development's finishing step until this step passes and Step 5 has run. The rounds run on spec review's lanes with spec review's ping, flagged switch and partial report. A resumed run always re-enters at the start block. Every `$VAR` is restored by the scalar loader (`SKILL.md`, Step 0).

## Round inputs

Load superpowers' `requesting-code-review` through the host's skill mechanism, unmodified: `BASE_SHA` is `$FOLD_BASE`, `HEAD_SHA` is the reviewed head, the plan is `$PLAN_FILE`, the description is one line saying in plain words what the plan built (`code-review-prompt` puts it on one line, drops control characters and redacts secret shapes; paths and quoted text stay).

## Start a round

One `Bash` call. `<SCALARS path printed by the task-paths block>` is the literal path the task-paths block printed (the same shape as `references/fold-step.md`).

```bash
SCALARS="<SCALARS path printed by the task-paths block>"
while IFS== read -r k v; do [[ $k =~ ^[A-Z][A-Z0-9_]*$ ]] || continue; printf -v "$k" '%s' "$v"; done < "$SCALARS"
for n in TOOLS_PY CWD PLAN_FILE FOLD_BASE QUOTA_PATH PROJECT_KEY; do case "${!n}" in ""|"<"*)
  printf 'ERROR: %s is empty or a placeholder -- fill it from the scalar file\n' "$n"; exit 1 ;; esac; done
CR_DIR="$(dirname "$QUOTA_PATH")/superpowers-run-${PROJECT_KEY}-code-review"; mkdir -p "$CR_DIR"
HEAD_SHA="$(git -C "$CWD" rev-parse HEAD)" || exit 1
HEAD_TREE="$(git -C "$CWD" rev-parse 'HEAD^{tree}')" || exit 1
read -r ST_ROUND ST_HEAD ST_STATE <<< "$(python3 -c 'import json,sys,os; p=sys.argv[1]; s=json.load(open(p)) if os.path.exists(p) else {"round": 0, "reviewed_head": "-", "state": "none"}; print(s["round"], s["reviewed_head"], s["state"])' "$CR_DIR/state.json")"
ST_TREE="$(git -C "$CWD" rev-parse -q --verify "${ST_HEAD}^{tree}" 2>/dev/null)"  # trees, not commits: a fold rewrite keeps the tree
case "$ST_STATE" in
  none) N=1 ;;
  owner_wait) printf 'CODE_REVIEW_NEXT=fix %s\n' "$ST_ROUND"; exit 0 ;;
  fix_dispatched)
    if [ "$ST_TREE" = "$HEAD_TREE" ]; then printf 'ERROR: the round-%s fix left the reviewed tree unchanged -- STOP and tell the user\n' "$ST_ROUND"; exit 1; fi
    N=$((ST_ROUND + 1)) ;;
  pass)
    if [ "$ST_TREE" = "$HEAD_TREE" ]; then printf 'CODE_REVIEW_NEXT=fold\n'; exit 0; fi
    printf 'ERROR: HEAD moved after the code review ended (%s) -- STOP and tell the user\n' "$CR_DIR/state.json"; exit 1 ;;
  owner_accepted|cap_stop)
    if [ "$ST_TREE" != "$HEAD_TREE" ]; then printf 'CODE_REVIEW_NEXT=cap_stop_moved %s\n' "$ST_ROUND"; exit 0; fi
    if [ "$ST_STATE" = owner_accepted ]; then printf 'CODE_REVIEW_NEXT=fold\n'; exit 0; fi
    printf 'CODE_REVIEW_NEXT=cap_stop %s\n' "$ST_ROUND"; exit 0 ;;
  *) printf 'ERROR: unreadable %s -- STOP and tell the user\n' "$CR_DIR/state.json"; exit 1 ;;
esac
rm -f "$CR_DIR/iter$N-"*  # the interrupted attempt's files, so a stale .exit is never read
printf '%s\n' "$HEAD_SHA" > "$CR_DIR/iter$N-head"
printf 'CODE_REVIEW_ROUND=%s\n' "$N" | tee -a "$SCALARS"
python3 "$TOOLS_PY" code-review-prompt --base "$FOLD_BASE" --head "$HEAD_SHA" --plan "$PLAN_FILE" \
  --description "<one line: what the plan built>" --out "$CR_DIR/iter$N-prompt.txt" || exit $?
python3 "$TOOLS_PY" code-review-paths --base "$FOLD_BASE" --head "$HEAD_SHA" --cwd "$CWD" > "$CR_DIR/iter$N-paths.json" || exit $?
CS="$(python3 "$TOOLS_PY" config-status --role review --cwd "$CWD")"; CS_EXIT=$?
printf 'CODE_REVIEW_NEXT=review %s\nREVIEW_LANES=%s CS_EXIT=%s\n' "$N" "${CS%%$'\n'*}" "$CS_EXIT"
```

- `CODE_REVIEW_NEXT=fold`: go to Step 5.
- `CODE_REVIEW_NEXT=fix <R>`: the round-R owner answers or fix were interrupted (`owner_wait`); run the `VERDICT_EXIT=1` branch for round R again from its first step, asking the owner again.
- `CODE_REVIEW_NEXT=cap_stop <R>`: no further review; follow the cap stop below.
- `CODE_REVIEW_NEXT=cap_stop_moved <R>`: HEAD's tree changed after the round-R cap stop or the owner's accept; follow `## Review the new head` below.
- `CODE_REVIEW_NEXT=review <N>` with `REVIEW_LANES=active CS_EXIT=0`: run the lane blocks. With `REVIEW_LANES=none CS_EXIT=0`: session-model mode, run the session-model block. Any other `REVIEW_LANES` or `CS_EXIT` (pending, untrusted, an error, exit 2): stop for the owner with that output ([`resolution-stops.md#owner-stop`](resolution-stops.md#owner-stop)); never fall back to the session model.

`code-review-paths` drops a path holding a control character with a stderr note, so the one-path-per-line `mapfile` handoff below keeps one path per argument. The stderr of `code-review-paths` may name a missing lens (`ai-kit-spec: lens <name> not installed; the review runs without it`): repeat it in the final message; the review still runs.

## Session-model mode (no review lanes)

Dispatch superpowers' code reviewer natively as `requesting-code-review` says, unmodified, with the prompt file's base, head and plan plus the lens lines printed by the native lens command of the one-lane block below (`capability-block ... --role review --native`), and write its whole report with the file-write tool to `$CR_DIR/iter$N-native.md`.

```bash
SCALARS="<SCALARS path printed by the task-paths block>"
while IFS== read -r k v; do [[ $k =~ ^[A-Z][A-Z0-9_]*$ ]] || continue; printf -v "$k" '%s' "$v"; done < "$SCALARS"
CR_DIR="$(dirname "$QUOTA_PATH")/superpowers-run-${PROJECT_KEY}-code-review"; N="$CODE_REVIEW_ROUND"
python3 "$TOOLS_PY" code-review-normalize --report "$CR_DIR/iter$N-native.md" --out "$CR_DIR/iter$N-report.md"; echo "NORMALIZE_EXIT=$?"
[ -f "$CR_DIR/iter$N-report.md" ] && python3 "$TOOLS_PY" classify-findings --cwd "$CWD" --report "$CR_DIR/iter$N-report.md" --out "$CR_DIR/iter$N-fit.json" --out-report "$CR_DIR/iter$N-report.md" || rm -f "$CR_DIR/iter$N-fit.json"
```

`NORMALIZE_EXIT=0`: go to the verdict block. Any other value: no lane judged; stop for the owner with the stderr line.

## Lanes (review lanes configured)

### Resolve and ping

```bash
SCALARS="<SCALARS path printed by the task-paths block>"
while IFS== read -r k v; do [[ $k =~ ^[A-Z][A-Z0-9_]*$ ]] || continue; printf -v "$k" '%s' "$v"; done < "$SCALARS"
CR_DIR="$(dirname "$QUOTA_PATH")/superpowers-run-${PROJECT_KEY}-code-review"; N="$CODE_REVIEW_ROUND"
python3 "$TOOLS_PY" probe-quota --cwd "$CWD" --quota-path "$QUOTA_PATH" || exit $?
python3 "$TOOLS_PY" resolve-reviewers --cwd "$CWD" --quota-path "$QUOTA_PATH" --source-vendor "<this host model's vendor: anthropic for a Claude session>" --cross-ai > "$CR_DIR/reviewers.json" || exit $?
python3 "$TOOLS_PY" ping-lanes --cwd "$CWD" --reviewers-json "$CR_DIR/reviewers.json" --lane-log "$CR_DIR/iter$N-lanes.jsonl" --round "$N" --quota-path "$QUOTA_PATH"; echo "PING_EXIT=$?"
```

`PING_EXIT=3` (no lane left) or `PING_EXIT=2` (configuration error): stop for the owner with that stderr line. On 0, run the one-lane block once per entry of `reviewers.json` (index 0 first), one lane at a time, each to its `.exit` file, so `switch-lane` keeps its one writer.

### One lane

```bash
SCALARS="<SCALARS path printed by the task-paths block>"
while IFS== read -r k v; do [[ $k =~ ^[A-Z][A-Z0-9_]*$ ]] || continue; printf -v "$k" '%s' "$v"; done < "$SCALARS"
CR_DIR="$(dirname "$QUOTA_PATH")/superpowers-run-${PROJECT_KEY}-code-review"; N="$CODE_REVIEW_ROUND"
I="<this entry's reviewers.json index>"
ROUTE="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))[int(sys.argv[2])].get("route", ""))' "$CR_DIR/reviewers.json" "$I")"
mapfile -t CR_PATHS < <(python3 -c 'import json,sys; sys.stdout.write("".join(p + "\n" for p in json.load(open(sys.argv[1]))))' "$CR_DIR/iter$N-paths.json")
if [ "$ROUTE" = native ]; then printf 'LANE=%s ROUTE=native\n' "$I"; exit 0; fi
TIMEOUT_TIERS="$(python3 "$TOOLS_PY" resolve-timeout-tiers --cwd "$CWD" --reviewers-json "$CR_DIR/reviewers.json" --index "$I")"
python3 "$TOOLS_PY" dispatch-reviewer --cwd "$CWD" --reviewers-json "$CR_DIR/reviewers.json" --index "$I" \
  --prompt-file "$CR_DIR/iter$N-prompt.txt" --timeout-tiers "$TIMEOUT_TIERS" --files "${CR_PATHS[@]}" \
  --stdout-only --lane-log "$CR_DIR/iter$N-lanes.jsonl" --round "$N" --transport-record "$(dirname "$QUOTA_PATH")/superpowers-run-${PROJECT_KEY}-transport.json" \
  > "$CR_DIR/iter$N-lane$I.md" 2> "$CR_DIR/iter$N-lane$I.err"; echo "$?" > "$CR_DIR/iter$N-lane$I.exit"
printf 'LANE=%s EXIT=%s\n' "$I" "$(cat "$CR_DIR/iter$N-lane$I.exit")"
```

`ROUTE=native`: this host runs the lane as spec review's Step 1 runs a native entry, with the prompt file's text plus the lens lines printed by `python3 "$TOOLS_PY" capability-block --runtime <the session's own runtime id> --model <the session model id> --role review --native --cwd "$CWD" --files <each path of iter$N-paths.json>`, writes the report to `$CR_DIR/iter$N-lane$I.md` and `0` to `$CR_DIR/iter$N-lane$I.exit` with the file-write tool. A custom command lane gets no lens lines: the custom launcher has no lens input, so its review runs without the lenses (a known limit). A nonzero exit on an entry whose `extra.usage_limited` is `true`: run `python3 "$TOOLS_PY" switch-lane --cwd "$CWD" --reviewers-json "$CR_DIR/reviewers.json" --index "$I" --lane-log "$CR_DIR/iter$N-lanes.jsonl" --round "$N"` once; on `switched <old> -> <new>` run this block again for the same index; any other answer leaves the lane failed. Never switch an unflagged lane. Any other nonzero exit is a failed lane; a lane that must wait for quota is an owner stop (no wake is armed inside the code review). Wait until every lane has its `.exit` file or has failed, then run the collect block.

### Collect

```bash
SCALARS="<SCALARS path printed by the task-paths block>"
while IFS== read -r k v; do [[ $k =~ ^[A-Z][A-Z0-9_]*$ ]] || continue; printf -v "$k" '%s' "$v"; done < "$SCALARS"
CR_DIR="$(dirname "$QUOTA_PATH")/superpowers-run-${PROJECT_KEY}-code-review"; N="$CODE_REVIEW_ROUND"
COUNT="$(python3 -c 'import json,sys; print(len(json.load(open(sys.argv[1]))))' "$CR_DIR/reviewers.json")"
MERGE_ARGS=()
FIT_FILES=()
for ((I = 0; I < COUNT; I++)); do
  KEY="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))[int(sys.argv[2])]["key"])' "$CR_DIR/reviewers.json" "$I")"
  if [ "$(cat "$CR_DIR/iter$N-lane$I.exit" 2>/dev/null)" = 0 ]; then
    python3 "$TOOLS_PY" code-review-normalize --report "$CR_DIR/iter$N-lane$I.md" --out "$CR_DIR/iter$N-lane$I.norm.md" || printf 'lane %s failed: incomplete report\n' "$KEY"
    if [ -f "$CR_DIR/iter$N-lane$I.norm.md" ] && python3 "$TOOLS_PY" classify-findings --cwd "$CWD" --report "$CR_DIR/iter$N-lane$I.norm.md" --out "$CR_DIR/iter$N-lane$I.fit.json" --out-report "$CR_DIR/iter$N-lane$I.norm.md"; then FIT_FILES+=("$CR_DIR/iter$N-lane$I.fit.json"); else rm -f "$CR_DIR/iter$N-lane$I.fit.json"; fi
  else printf 'lane %s failed: exit %s\n' "$KEY" "$(cat "$CR_DIR/iter$N-lane$I.exit" 2>/dev/null || printf missing)"; fi
  MERGE_ARGS+=("$KEY=$CR_DIR/iter$N-lane$I.norm.md")
done
if [ "${#FIT_FILES[@]}" -gt 0 ]; then python3 -c 'import json,sys; json.dump([r for p in sys.argv[2:] for r in json.load(open(p))], open(sys.argv[1], "w"))' "$CR_DIR/iter$N-fit.json" "${FIT_FILES[@]}" || rm -f "$CR_DIR/iter$N-fit.json"; fi
python3 "$TOOLS_PY" merge-reports --doc-paths "$PLAN_FILE" --cwd "$CWD" --lane-log "$CR_DIR/iter$N-lanes.jsonl" --round "$N" "${MERGE_ARGS[@]}" > "$CR_DIR/iter$N-report.md"; echo "MERGE_EXIT=$?"
```

A lane without a normalized report is a failed lane and the merge keeps the judged lanes (a partial report with a `Judged by:` line). `MERGE_EXIT` other than 0 (no lane judged, or exit 2): stop for the owner with the merge output and the round log `$CR_DIR/iter$N-lanes.jsonl`.

## Verdict

```bash
SCALARS="<SCALARS path printed by the task-paths block>"
while IFS== read -r k v; do [[ $k =~ ^[A-Z][A-Z0-9_]*$ ]] || continue; printf -v "$k" '%s' "$v"; done < "$SCALARS"
CR_DIR="$(dirname "$QUOTA_PATH")/superpowers-run-${PROJECT_KEY}-code-review"; N="$CODE_REVIEW_ROUND"
FIT_ARGS=(); if [ -f "$CR_DIR/iter$N-fit.json" ]; then FIT_ARGS=(--fit-json "$CR_DIR/iter$N-fit.json"); fi
python3 "$TOOLS_PY" code-review-verdict --report "$CR_DIR/iter$N-report.md" --round "$N" --cap 3 "${FIT_ARGS[@]}" > "$CR_DIR/iter$N-verdict.json"
VERDICT_EXIT=$?; echo "VERDICT_EXIT=$VERDICT_EXIT"; cat "$CR_DIR/iter$N-verdict.json"
case "$VERDICT_EXIT" in 0) ST=pass ;; 1) ST=owner_wait ;; 3) ST=cap_stop ;; *) exit "$VERDICT_EXIT" ;; esac
printf '{"round": %s, "reviewed_head": "%s", "state": "%s"}\n' "$N" "$(cat "$CR_DIR/iter$N-head")" "$ST" > "$CR_DIR/state.json.tmp" && mv "$CR_DIR/state.json.tmp" "$CR_DIR/state.json"
```

`classify-findings` runs on each lane's normalized report before the merge, and on the session model's report: it asks jev, when present, whether each finding's severity fits the kind of problem, the test tier, reproducibility, end-user reach and MVP versus production, from summaries only: the severity and the five labels each finding ends with; never a title, location, code, diffs or file contents. A `higher` answer raises a finding one level and a `lower` answer moves only MEDIUM to LOW, so a CRITICAL or HIGH finding is never lowered on jev's word. It rewrites that report with the fitted severities, so `$CR_DIR/iter$N-report.md`, which the verdict, `receiving-code-review`, the gray-area classifier and the cap stop read, carries them, and a MEDIUM raised to HIGH blocks and routes as HIGH; the verdict re-checks every row of `iter$N-fit.json` against that rule and against the report. Without jev, on a low answer, or for a finding with no labels (all five read unknown, so it is never sent to jev), each finding keeps the reviewer's severity (`decided_by: default`); relay each `ai-kit-spec: finding fit:` line. The fit is advisory and never stops the loop: a report whose `classify-findings` fails stays as reviewed and adds no rows. The fit runs in this code-review loop only; spec review's own loop is unchanged.

- `VERDICT_EXIT=0` (`pass`): name the verdict's `listed` findings (MEDIUM and LOW) and the report's `Judged by:` line in the final message, then continue to Step 5.
- `VERDICT_EXIT=1` (`fix`): follow superpowers' `receiving-code-review` on `$CR_DIR/iter$N-report.md`, unmodified, with the gray-area rule below. Ask the owner about every `owner` route and wait for the answers before any fix. Write `$CR_DIR/iter$N-fix-prompt.md` with the file-write tool: the CRITICAL and HIGH findings and the `fixer` items not routed to the owner, plus the owner's answered items with the owner's answer. Bind the fix dispatch in the scalar file first: `printf 'PROMPT_FILE=%s\nREPORT_FILE=%s\nREPORT_MODE=write\nDISPATCH_BASE=%s\n' "$CR_DIR/iter$N-fix-prompt.md" "$CR_DIR/iter$N-fix-report.md" "$CR_DIR/iter$N-fix-dispatch" | tee -a "$SCALARS"` (its own report file, never the last task's; `FORMAT_BLOCK_FILE` stays the last task's). The prompt tells the implementer to WRITE its report to `$CR_DIR/iter$N-fix-report.md`. Dispatch it as one fix implementer through Step 3's dispatch block only (the native branch, or for `external_cli` the Dispatch block and then the Classify block of `dispatch-external-cli.md`, reading `STATUS` from its `ok` branch) with the last task's pinned injection (`$RUN_DIR/INJECTION_JSON.json`, no `resolve-injection`); skip Step 3's round-increment and escalation blocks and leave `FIX_ROUND` unchanged. Branch on the `class` of `CLASSIFICATION` right after the Classify block, before any of its task branches: on `ok` run only that branch's status block; any other class relays the runner's `cross-ai: report`, `cross-ai: upstream` and `AIKIT-XAI` lines and stops for the owner without the task-level failure handling (no Flagged switch, no Read tokens or Write state, no task resume file, no Schedule-or-stop wait or wake). A status other than `DONE` or `DONE_WITH_CONCERNS` stops for the owner too; either stop leaves `state.json` at `owner_wait`. On `DONE` or `DONE_WITH_CONCERNS` record the fix: `printf '{"round": %s, "reviewed_head": "%s", "state": "fix_dispatched", "fix_head": "%s"}\n' "$N" "$(cat "$CR_DIR/iter$N-head")" "$(git -C "$CWD" rev-parse HEAD)" > "$CR_DIR/state.json.tmp" && mv "$CR_DIR/state.json.tmp" "$CR_DIR/state.json"`, then run the start block again (the next round starts only from `fix_dispatched` with a tree different from the reviewed one).
- `VERDICT_EXIT=3` (`cap_stop`): the cap is reached with a CRITICAL or HIGH finding open. Show the last report and the verdict's `blocking` list and stop as [`resolution-stops.md#owner-stop`](resolution-stops.md#owner-stop) says for a code review cap stop; Step 5 does not run.
- `VERDICT_EXIT=4` or `2`: the report is incomplete or unreadable; stop for the owner with the stderr line (no state is written).

## Cap stop answer

At `CODE_REVIEW_NEXT=cap_stop`, ask the owner once: accept the open findings, or stop. Accept writes `state.json` with `"state": "owner_accepted"` and, as `reviewed_head`, the head of the report shown (`$CR_DIR/iter<R>-head`, never the current HEAD) (same `printf` and `mv` as the verdict block) and continues to Step 5; stop closes the plan's lane transports, then ends the run: run one bash block holding the scalar loader line of `## Start a round` and the line `python3 "$SHIM" close-transports --transport-record "$(dirname "$QUOTA_PATH")/superpowers-run-${PROJECT_KEY}-transport.json" > "$(dirname "$QUOTA_PATH")/superpowers-run-${PROJECT_KEY}-close-transports.json" 2>&1 || printf 'WARNING: close-transports exited %s; the runner sweep closes leftovers at its next start\n' "$?" >&2` (a failure is a warning, never a stop). No further review round runs.

## Review the new head

At `CODE_REVIEW_NEXT=cap_stop_moved <R>`, HEAD's tree is no longer the tree the round-R report reviewed (the owner changed the code after the cap stop or the accept), so accepting the open findings would not cover it. Ask the owner once: review the new head, or stop (the stop of `## Cap stop answer`). Review the new head writes a fresh state, a new 3-round budget for the owner's change, then runs the start block again:

```bash
SCALARS="<SCALARS path printed by the task-paths block>"
while IFS== read -r k v; do [[ $k =~ ^[A-Z][A-Z0-9_]*$ ]] || continue; printf -v "$k" '%s' "$v"; done < "$SCALARS"
CR_DIR="$(dirname "$QUOTA_PATH")/superpowers-run-${PROJECT_KEY}-code-review"
printf '{"round": 0, "reviewed_head": "-", "state": "none"}\n' > "$CR_DIR/state.json.tmp" && mv "$CR_DIR/state.json.tmp" "$CR_DIR/state.json"
```

## Gray areas (receiving-code-review's stop-and-discuss point)

Before asking the owner about any item `receiving-code-review` stops on, write those items to `$CR_DIR/iter$N-discuss.md` as `### Findings escalated` followed by one bullet per item, `- **<the finding title as the report names it>** — Severity: <its severity>. Reason for escalation: <why it needs a discussion>. Caller decision needed.`, then run:

```bash
SCALARS="<SCALARS path printed by the task-paths block>"
while IFS== read -r k v; do [[ $k =~ ^[A-Z][A-Z0-9_]*$ ]] || continue; printf -v "$k" '%s' "$v"; done < "$SCALARS"
CR_DIR="$(dirname "$QUOTA_PATH")/superpowers-run-${PROJECT_KEY}-code-review"; N="$CODE_REVIEW_ROUND"
python3 "$TOOLS_PY" classify-disagreements --kind code --cwd "$CWD" --report "$CR_DIR/iter$N-report.md" \
  --fix-summary "$CR_DIR/iter$N-discuss.md" --iteration "$N" --cap 3 > "$CR_DIR/iter$N-routes.json"; echo "CLASSIFY_EXIT=$?"
```

Ask the owner only about the `owner` routes of `iter$N-routes.json`. A `fixer` item joins this round's fix; a `skipped` item is not fixed and is named in the final message with its reason. A CRITICAL or HIGH item always reaches the owner. Without jev, every item goes to the owner, as today. A nonzero `CLASSIFY_EXIT` sends every gray item to the owner.
