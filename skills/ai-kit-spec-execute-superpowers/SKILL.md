---
name: ai-kit-spec-execute-superpowers
description: Resolves the best available, live-quota-checked (runtime, model) pair for each task in a superpowers-generated implementation plan, then delegates actual execution to superpowers:subagent-driven-development, injecting the resolved pair at its implementer-dispatch point without bypassing that harness's TDD enforcement, agent-identity/resume, task review, fix-loop, or final-review pattern. Use when ai-kit-spec-execute detects a superpowers-generated plan (docs/superpowers/plans/*.md) being run under subagent-driven-development and needs to resolve a pair for it; not for superpowers:executing-plans, which executes every task inline with no subagent-dispatch point to inject into.
---

# ai-kit-spec-execute-superpowers

**This skill never dispatches a task itself.** It resolves WHICH pair a task should use, then hands
that resolution to `superpowers:subagent-driven-development` at its one documented dispatch point
("1. Dispatch the implementer"). That skill keeps full ownership of TDD enforcement,
fresh-subagent-per-task, agent identity and resume, task review, fix loops, and the final
whole-branch review. `superpowers:executing-plans` is out of scope: it runs every task inline,
with no dispatch point to inject into.

Rationale for the rules below (why each exists, what broke without it) lives in
`references/design-notes.md`. Read it only when a rule looks arbitrary.

## NEVER

Each item is repeated at its point of use; this is the index.

- **Never** persist `$EXCLUDED_KEYS_JSON` wholesale as `excluded_keys` — it is a working union of a
  permanent set and a same-wave set; persisting it makes a temporary `"quota"` exclusion
  indistinguishable from a permanent one (Step 2; `references/state-management.md`).
- **Never** call `resolve-injection` with `--exclude-keys-json` alone, omitting
  `--excluded-reasons-json` — every prior-wave permanent reason then reads as
  `"no_usable_dispatch"` (Step 2).
- **Never** read `key`/`runtime` off an injection result before checking `$INJECTION_MODE` —
  `quota_exhausted` and `no_candidate` carry neither field (Step 2).
- **Never** put `$INJECTION_RUNTIME` into an exclusion set — it is a runtime id, not a ladder key,
  so it excludes nothing (Step 3).
- **Never** fold `$ESCALATION_EXCLUDE_JSON` into `$EXCLUDED_KEYS_JSON` — it marks healthy,
  never-tried candidates excluded only to enforce a capability floor (Step 3;
  `references/escalation.md`).
- **Never** let a fix-loop round overwrite `$REPORT_FILE` — `REPORT_MODE` is `write` at most once
  per task, `append` after that, and every prompt after the first says APPEND (Step 3).
- **Never** parse the implementer status out of `$REPORT_FILE` — read it from
  `$DISPATCH_RESULT_JSON["stdout"]` only (Step 3).
- **Never** re-resolve to another candidate after a failed dispatch or re-run
  `resolve-injection` to recover; re-dispatch only the persisted injection after its one-shot
  wait (Step 3).
- **Never** run `trust-local` without the user's explicit yes, and never ask twice in one run
  (Step 2).

The `Agent` tool is a Claude Code tool, and so is the one-shot `CronCreate` at `retry_after_s`.
On another host, use its own subagent mechanism (or STOP and tell the user to resume by hand)
and Step 3 point 4's print path for the wake.

**Cross-AI caller contract:** [`../ai-kit-cross-ai/SKILL.md`](../ai-kit-cross-ai/SKILL.md).
MANDATORY: read it before the first `dispatch-task` and again before acting on any non-zero exit
(sections 4, 6 and 8). Never switch harness, provider or model after a failed or unusable run;
pre-dispatch selection and the Rounds 4–5 bump (Step 3) are the only key changes, both before
anything has failed.

## Step 0: Resolve the shim path

Take the FIRST existing candidate, in one `Bash` call:

```bash
for d in "$(dirname "<absolute path to THIS SKILL.md>")" \
         "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/ai-kit-spec-execute-superpowers}" \
         "$HOME/.claude/skills/ai-kit-spec-execute-superpowers" \
         "$(git rev-parse --show-toplevel 2>/dev/null)/skills/ai-kit-spec-execute-superpowers" \
         "$(pwd)/skills/ai-kit-spec-execute-superpowers"; do
  [ -n "$d" ] && [ -d "$d" ] && { SKILL_DIR="$d"; break; }
done
if [ -z "$SKILL_DIR" ]; then
  printf 'ERROR: could not resolve skills/ai-kit-spec-execute-superpowers under any known '
  printf 'installation shape (this SKILL.md, CLAUDE_PLUGIN_ROOT, ~/.claude/skills, git toplevel, or cwd) -- '
  printf 'STOP and tell the user rather than guessing a path.\n'
  exit 1
fi
SHIM="$SKILL_DIR/ai-kit-spec-superpowers.py"
for d in "$(dirname "$SKILL_DIR")/ai-kit-spec-review" \
         "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/ai-kit-spec-review}" \
         "$HOME/.claude/skills/ai-kit-spec-review"; do
  [ -d "$d" ] && { REVIEW_SKILL_DIR="$d"; break; }
done
if [ -z "$REVIEW_SKILL_DIR" ]; then
  printf 'ERROR: could not resolve skills/ai-kit-spec-review under any known installation shape '
  printf '(CLAUDE_PLUGIN_ROOT, ~/.claude/skills, or alongside this skill'\''s own resolved '
  printf 'directory) -- STOP and tell the user rather than guessing a path.\n'
  exit 1
fi
TOOLS_PY="$REVIEW_SKILL_DIR/ai-kit-spec.py"
printf 'SHIM=%s\nTOOLS_PY=%s\n' "$SHIM" "$TOOLS_PY"
```

The loaded skill's own directory and its sibling are tried first, so the shims that run match
the `SKILL.md` you are following, not an older install elsewhere. **Record both printed lines as
literal values.** Every later call uses `python3 "$SHIM"
<subcommand>`; `$TOOLS_PY` is `ai-kit-spec-review`'s shim, used for `cache-path --kind quota` and
`trust-local`. Every `Bash` call starts a fresh shell, so every `$VAR` below means the literal value
last captured for it via `printf`, re-substituted verbatim.

## Step 1: Load the plan under subagent-driven-development, unmodified

Follow that skill's own Setup exactly (workspace, ledger, plan read, pre-flight scan). `$CWD`,
`$PLAN_FILE`, `$TASK_N`, and `$BRIEF_FILE` below are values that skill already holds when it
dispatches each task's implementer — read them, never invent them.

## Arm the session wake (plans with two or more tasks, D-23)

Before the first implementer dispatch below, arm the session wake only when `$PLAN_FILE` holds two
or more `### Task <n>` headings. A single-task plan arms nothing. The wake is owned by this run only
when this block itself prints `armed`; a refusal, exit 3 or `refreshed` (a wake that existed before
this run) leaves `WAKE_OWNED=0`, and the stop re-arm and the close step then call nothing. Never
fail the run on the wake. Run this one `Bash` call:

```bash
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
    WAKE_HOST="${WAKE_HOST_ID%%-*}"
    WAKE_ID="${WAKE_HOST_ID#*-}"
    WAKE_OWNED=1
  fi
fi
printf 'WAKE_SHIM=%s\nWAKE_OWNED=%s\nWAKE_HOST=%s\nWAKE_ID=%s\n' \
  "$WAKE_SHIM" "$WAKE_OWNED" "${WAKE_HOST:-}" "${WAKE_ID:-}"
```

**Record the printed `WAKE_SHIM`, `WAKE_OWNED`, `WAKE_HOST` and `WAKE_ID` as literal values.**
The identity: on claude the shim reads the session itself; on pi and opencode the recorded
`WAKE_SESSION_ID` must hold this session's exact id (the ai-kit-session-wake skill's Arm section),
never a guess from the newest session file. Without it `arm` refuses (exit 2): the refusal is
printed above and the run goes on with no wake.

## Step 2: Before each task's implementer dispatch — resolve the injection

**Before touching any exclusion-set variable, ask:** is this exclusion permanent (auth, config,
real error) or same-wave only (quota)? Mislabeling it does not crash; it silently either retries a
broken candidate forever or locks out a recovered one, wave after wave.

The state is a three-set split: `$PRIOR_EXCLUDED_KEYS_JSON`/`$PRIOR_REASONS_JSON` (permanent,
carried across resumes), `$WAVE_TRIED_JSON`/`$WAVE_REASONS_JSON` (this wave only), and the derived
unions `$EXCLUDED_KEYS_JSON`/`$EXCLUDED_REASONS_JSON` passed to `resolve-injection`, plus
`$FIX_ROUND`, `$LAST_DISPATCHED_KEY` and `$ESCALATION_ANCHOR_KEY`. **MANDATORY: before writing or reading any of these, or the resumable-state file,
read `references/state-management.md` in full** — it defines each variable's initial and resume
values and the exact resumable-state bash.

Right after that skill's `scripts/task-brief PLAN_FILE N` writes `$BRIEF_FILE`:

```bash
QUOTA_PATH="$(python3 "$TOOLS_PY" cache-path --kind quota)"
EXCLUDED_REASONS_JSON="$(python3 -c 'import json,sys; a=json.loads(sys.argv[1]); a.update(json.loads(sys.argv[2])); print(json.dumps(a))' \
  "$PRIOR_REASONS_JSON" "$WAVE_REASONS_JSON")"
INJECTION_JSON="$(python3 "$SHIM" resolve-injection --cwd "$CWD" --task-file "$BRIEF_FILE" \
  --quota-path "$QUOTA_PATH" --exclude-keys-json "$EXCLUDED_KEYS_JSON" \
  --excluded-reasons-json "$EXCLUDED_REASONS_JSON")"
INJECTION_MODE="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["mode"])' "$INJECTION_JSON")"
printf 'QUOTA_PATH=%s\nINJECTION_JSON=%s\nINJECTION_MODE=%s\n' \
  "$QUOTA_PATH" "$INJECTION_JSON" "$INJECTION_MODE"
```

`--excluded-reasons-json` always gets the merge of `$PRIOR_REASONS_JSON` and `$WAVE_REASONS_JSON`,
never `$WAVE_REASONS_JSON` alone.

**If `resolve-injection` exits 2** (empty `$INJECTION_JSON`): a malformed `review-spec.toml`, or an
entry with `purpose = "execute"` that can never execute (a custom `command` entry, grok, or a
claude pair that does not run natively). STOP and relay its stderr verbatim.

**If its stderr prints `ignoring untrusted project-local config`**, this resolution used the global
config only. Ask **once per run**: relay the line verbatim, show
`python3 "$TOOLS_PY" trust-local --cwd "$CWD" --show` (one JSON line per local reviewer with the
argv it would run, the prompt shown as `<prompt>`; writes nothing), and ask whether to trust it.
On yes, run `python3 "$TOOLS_PY" trust-local --cwd "$CWD"` and re-run this step's
`resolve-injection` before dispatching. On no, continue on the global-only result and do not ask
again this run, even though the line repeats on every task and fix round. Never trust on the
user's behalf.

**Branch on `$INJECTION_MODE` before reading any other field.** Only `native` and
`external_cli` carry `key`/`runtime`. Both come from one routing decision, never from a stored
field: `native` when this host runs the pair itself, `external_cli` when it runs as a subprocess.
A route of `unverified` still dispatches as `external_cli`: the runtime's model list was
unavailable after one refresh, so neither ai-kit nor the runner checks the model before the CLI
runs, and stderr prints `ai-kit-spec: dispatching <key> unverified: ...`.

```bash
if [ "$INJECTION_MODE" != "quota_exhausted" ] && [ "$INJECTION_MODE" != "no_candidate" ]; then
  INJECTION_KEY="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["key"])' "$INJECTION_JSON")"
  INJECTION_RUNTIME="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1]).get("runtime") or "")' \
    "$INJECTION_JSON")"
  printf 'INJECTION_KEY=%s\nINJECTION_RUNTIME=%s\n' "$INJECTION_KEY" "$INJECTION_RUNTIME"
fi
```

Record both when the block ran. `$INJECTION_KEY` is the ladder key (e.g. `codex/terra`);
`$INJECTION_RUNTIME` is the runtime id (e.g. `codex`), empty for the session default.

- **`no_candidate`** — nothing configured for this task survives affinity/context narrowing (read
  `detail`, e.g. every `context_limit` is below the task's `required_context`). A curation gap, not
  quota. STOP this wave and report `detail`. Nothing is scheduled.
- **`quota_exhausted`** — read `any_quota_recoverable`
  (`python3 -c 'import json,sys; print(json.loads(sys.argv[1])["any_quota_recoverable"])' "$INJECTION_JSON"`).
  It, not `all_auth_failures`, is the gate. `reasons` holds `"quota"`, `"auth"`,
  `"billing_or_access"`, `"capacity"`, `"git_timeout"`, `"timeout"`, `"configuration"`,
  `"dispatch_unavailable"`, `"real_error"`, `"no_usable_dispatch"` (a prior wave's permanent
  failure), or a route name (`"bad_model"`, `"review_only"`,
  `"not_installed"`, `"no_inventory"`, `"unknown_runtime"`, `"no_model"`). Only `"quota"` is
  worth waiting for. A skip route is recorded under that route name and never picked.
  - **`any_quota_recoverable == False`** — no candidate is eligible for automatic quota recovery
    (only `"quota"` is). Some reasons may still clear later by themselves (`"capacity"`), others
    need a fix first (credentials, configuration). STOP this wave and tell the user which key needs
    what fix, read off `reasons`: `"auth"` needs login or entitlement, `"billing_or_access"` credits or
    model access, `"configuration"` a fixed model id, prompt or flag (the runner refused it),
    `"capacity"` a later retry on the same lane, `"git_timeout"` a look at the repo (the runner's
    work-tree check timed out, not the CLI), `"timeout"`/`"dispatch_unavailable"` an
    investigation of the CLI, `"real_error"` its own diagnosis. Nothing is scheduled. This stop is
    the adapter's own
    call, not one of subagent-driven-development's four stop-and-ask conditions; see
    `references/design-notes.md`.
  - **`any_quota_recoverable == True`** — at least one candidate is quota-exhausted, which is
    time-bound. Write resumable state, then STOP this wave and report the reasons per key and the
    state path; the owner re-invokes to resume. Nothing is scheduled. **MANDATORY: read
    `references/state-management.md`'s "Resumable state" sections first** — they give the exact
    bash for merging `tried`/`reasons` into the wave sets, computing `$RESUME_EXCLUDED_KEYS_JSON`
    with the `resume-exclusions` subcommand (never inline set arithmetic), and the `STATE_JSON`
    passed to `write-resumable-state`.
- **Otherwise** `$INJECTION_JSON` carries `mode`, `key`, `runtime`, `model`, `ladder_keys`, and for
  `external_cli` also `effort`, `service_tier`. Go to Step 3.

## Step 3: Dispatch the implementer — apply the injection

A reviewer or executor is a (runtime, model) pair. Each call runs it natively when its runtime is the current host and the host can select that model; otherwise it runs as a subprocess through the supervised runner. An entry with neither a runtime nor a model is the session default, which the host always runs natively. Today only Claude Code selects a model per call (its sonnet, opus, haiku and fable aliases); every other host runs only its session default natively.

**`mode == "native"`:** this host's own subagent mechanism, unchanged. On Claude Code, pass `model`
as the `Agent` tool's `model` parameter (omit it when empty) and record the returned agent identity;
fix-loop rounds 1–3 resume that same agent. Its round 4/5 model bump follows that skill's own
rule (a more capable model) and happens before the round's dispatch, after a review returned
findings: pre-dispatch selection, never a switch after a failed dispatch. On any other host the native case is only the session default, so omit `model` and
let the host use its current session. Either way, record `LAST_DISPATCHED_KEY="$INJECTION_KEY"`
after the dispatch. A non-Claude native dispatch cannot raise its own model, so rounds 4–5 take
the ladder escalation below; when it finds nothing higher, it stops and asks for a more capable
routable pair above it in `policy.ladder`.

**`mode == "external_cli"`:** a subprocess through the supervised runner. A CLI process exits when
done, so there is no live agent to resume.
Every dispatch, first attempt and every fix round, uses subagent-driven-development's documented
fallback: a fresh implementer carrying the brief path, the report-file path, and the findings, with
the report file as the persistent memory.

Create the artifact paths once, derived from `$BRIEF_FILE` (`…/task-N-brief.md`):

```bash
TASK_STATE_DIR="$(dirname "$BRIEF_FILE")/.ai-kit-spec-execute-superpowers"
mkdir -p "$TASK_STATE_DIR"
PROMPT_FILE="$TASK_STATE_DIR/task-${TASK_N}-prompt.txt"
FORMAT_BLOCK_FILE="$TASK_STATE_DIR/task-${TASK_N}-format-block.md"
REPORT_FILE="${BRIEF_FILE%-brief.md}-report.md"
DISPATCH_BASE="$(mktemp -d)/task-${TASK_N}-dispatch"  # outside the repo: never a tree change
printf 'PROMPT_FILE=%s\nFORMAT_BLOCK_FILE=%s\nREPORT_FILE=%s\nDISPATCH_BASE=%s\n' \
  "$PROMPT_FILE" "$FORMAT_BLOCK_FILE" "$REPORT_FILE" "$DISPATCH_BASE"
```

`$REPORT_FILE` (`…/task-N-report.md`) is the path subagent-driven-development's review and ledger
already read. The other two are this adapter's scratch files.

Set the initial report mode as soon as `$REPORT_FILE` is known — a resumed task may already have a
partial report:

```bash
if [ -s "$REPORT_FILE" ]; then REPORT_MODE=append; else REPORT_MODE=write; fi
printf 'REPORT_MODE=%s\n' "$REPORT_MODE"
```

After EVERY `dispatch-task` call, whatever its outcome, set `REPORT_MODE=append` and never set it
back to `write` for this task.

1. **Compose the prompt** from subagent-driven-development's implementer-prompt.md template (brief
   path, context, report-file path, the "you do not dispatch subagents" contract) into
   `$PROMPT_FILE`. It must tell the CLI to put its detailed report in `$REPORT_FILE` and return
   only a short status line. Put everything the implementer is asked to do inside one
   `<objective>…</objective>` block, and keep the WRITE/APPEND report sentence below outside it:
   the runner's task digest hashes only the objective text, so a quota wake that changes WRITE to
   APPEND still reuses the session. List the task's repo-relative paths in one comma-separated
   `<files>…</files>` block: the runner retries in a new session over a changed tree only when
   every changed path is listed there. On the task's first dispatch the prompt says WRITE `$REPORT_FILE`; on
   every later dispatch it says "APPEND your detailed report to the end of `$REPORT_FILE` — do not
   overwrite its existing contents from earlier rounds." (`--report-mode` only controls
   `dispatch-task`'s own stdout fallback, never what the CLI does to the file.) On a fix round, also
   append the open findings verbatim. **At the start of every fix round, increment `$FIX_ROUND`
   and set `ESCALATION_ANCHOR_KEY="$LAST_DISPATCHED_KEY"` first** (not on resume), then apply the
   Rounds 4–5 rule below, then compose. A failed dispatch does not get a same-round re-dispatch.
2. **Write the status contract** (`DONE` / `DONE_WITH_CONCERNS` / `NEEDS_CONTEXT` / `BLOCKED`, from
   implementer-prompt.md's "After Review Findings") to `$FORMAT_BLOCK_FILE`. It becomes the
   dispatch's format block.
3. **Dispatch.** `dispatch-task` prepares tooling guidance itself and runs the pair through the
   supervised runner. `--timeout 1800` is a fixed constant and the budget for the whole call,
   every retry rung included (curated-config's runner floor); a candidate's per-entry
   `timeout_tiers` is not plumbed into this adapter. **Hard rule:** run this call backgrounded,
   never under a foreground tool timeout, which kills it and loses the evidence lines. It is finished only when the `.exit` file exists.

```bash
rm -f "$DISPATCH_BASE.exit"
python3 "$SHIM" dispatch-task --injection-json "$INJECTION_JSON" \
  --prompt-file "$PROMPT_FILE" --target-dir "$CWD" --heartbeat-interval 60 --timeout 1800 \
  --format-block-file "$FORMAT_BLOCK_FILE" --report-file "$REPORT_FILE" \
  --report-mode "$REPORT_MODE" > "$DISPATCH_BASE.json" 2> "$DISPATCH_BASE.err"
echo "$?" > "$DISPATCH_BASE.exit"
```

   Then, in a new call once `$DISPATCH_BASE.exit` exists:

```bash
DISPATCH_EXIT="$(cat "$DISPATCH_BASE.exit")"
DISPATCH_RESULT_JSON="$(cat "$DISPATCH_BASE.json")"
# A refused candidate or a missing prompt file exits non-zero with no JSON: relay the tail of
# $DISPATCH_BASE.err verbatim and STOP as real_error, with no re-resolve.
[ -n "$DISPATCH_RESULT_JSON" ] || { echo "dispatch-task exit $DISPATCH_EXIT, no result"; exit 1; }
REPORT_MODE=append
LAST_DISPATCHED_KEY="$INJECTION_KEY"
printf 'DISPATCH_RESULT_JSON=%s\nREPORT_MODE=%s\nLAST_DISPATCHED_KEY=%s\n' \
  "$DISPATCH_RESULT_JSON" "$REPORT_MODE" "$LAST_DISPATCHED_KEY"
```

   The runner's evidence lines (`cross-ai: report`, `cross-ai: upstream`, `AIKIT-XAI`, and a
   `cross-ai: state` or `cross-ai: lane stopped=` path) are in `$DISPATCH_BASE.err`.

   `--heartbeat-interval` is required but unused: the runner prints its own heartbeat.

   The second block switches `REPORT_MODE` to `append` and records `$LAST_DISPATCHED_KEY`, which
   the next fix round copies into its escalation anchor (a native dispatch records its key the
   same way). If the CLI
   wrote `$REPORT_FILE` itself, `dispatch-task` leaves it untouched; only when the file is
   unchanged does it write or append the captured stdout, behind a marker line. Either way,
   review and the fix loop read `$REPORT_FILE` like a native report.

4. **Classify the outcome:**

```bash
CLASSIFICATION="$(python3 "$SHIM" classify-dispatch-failure --dispatch-result-json "$DISPATCH_RESULT_JSON")"
```

- **`"ok"`** — continue with subagent-driven-development's "2. Handle the report", reading the
  status from `stdout`, never from `$REPORT_FILE`:

```bash
STATUS_LINE="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["stdout"])' "$DISPATCH_RESULT_JSON")"
STATUS="$(printf '%s\n' "$STATUS_LINE" | rg -o '\b(DONE_WITH_CONCERNS|NEEDS_CONTEXT|BLOCKED|DONE)\b' | tail -1)"
```

  An empty `$STATUS` means the CLI emitted no status word: treat it as `BLOCKED`, and do not scan
  `$REPORT_FILE` for one. For a `BLOCKED` from an external CLI, follow that handler's
  more-context, split and plan-defect routes on the same pair, but never its "more capable
  model" route on your own: that is a model switch after an unusable run, so stop and report
  for the owner's decision.
- **`"quota"`** — the runner's hard-tier outcome: a confirmed-router quota stop or an exhausted
  transient ladder carrying `retry_after_s=`, and also the terminal exit-69 hard-tier stops and a
  bare exit 75; point 4 decides wait versus stop. Record it as a wave-tried key
  WITH the `"quota"` reason, never straight into `$EXCLUDED_KEYS_JSON` without one:

```bash
WAVE_TRIED_JSON="$(python3 -c 'import json,sys; print(json.dumps(sorted(set(json.loads(sys.argv[1])) | {sys.argv[2]})))' \
  "$WAVE_TRIED_JSON" "$INJECTION_KEY")"
WAVE_REASONS_JSON="$(python3 -c 'import json,sys; d=json.loads(sys.argv[1]); d[sys.argv[2]]="quota"; print(json.dumps(d))' \
  "$WAVE_REASONS_JSON" "$INJECTION_KEY")"
EXCLUDED_KEYS_JSON="$(python3 -c 'import json,sys; print(json.dumps(sorted(set(json.loads(sys.argv[1])) | set(json.loads(sys.argv[2])))))' \
  "$PRIOR_EXCLUDED_KEYS_JSON" "$WAVE_TRIED_JSON")"
printf 'WAVE_TRIED_JSON=%s\nWAVE_REASONS_JSON=%s\nEXCLUDED_KEYS_JSON=%s\n' \
  "$WAVE_TRIED_JSON" "$WAVE_REASONS_JSON" "$EXCLUDED_KEYS_JSON"
```

  Never re-resolve to another candidate after a failed dispatch. The evidence lines come before
  that fold, because a later step must not act on a stop it has not relayed. Then, in this order:

  1. **Relay evidence first.** On a stop, relay the `cross-ai: report`, `cross-ai: upstream`
     and `AIKIT-XAI` lines verbatim from `$DISPATCH_BASE.err` before reading tokens or writing
     state, then run the fold block above.
  2. **Read the tokens.** `retry_after_s` and `cycle` are in the nested `status` dict parsed
     from the runner's `AIKIT-XAI` line, not at the top level of `$DISPATCH_RESULT_JSON`:

```bash
RETURNCODE="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1]).get("returncode"))' "$DISPATCH_RESULT_JSON")"
RETRY_AFTER_S="$(python3 -c 'import json,sys; d=json.loads(sys.argv[1]); s=d.get("status") or {}; print("" if s.get("retry_after_s") is None else s.get("retry_after_s"))' "$DISPATCH_RESULT_JSON")"
CYCLE="$(python3 -c 'import json,sys; d=json.loads(sys.argv[1]); s=d.get("status") or {}; print("" if s.get("cycle") is None else s.get("cycle"))' "$DISPATCH_RESULT_JSON")"
printf 'RETURNCODE=%s\nRETRY_AFTER_S=%s\nCYCLE=%s\n' "$RETURNCODE" "$RETRY_AFTER_S" "$CYCLE"
```

  3. **Write the state.** This branch already folded this key into the wave sets, so run the
     quota-branch variant of the resumable-state bash, shown in full in
     `references/state-management.md` under "Quota-branch state write": it keeps `PROJECT_KEY`
     and `RESUME_STATE_PATH` and persists `$INJECTION_JSON` as `injection_json`, so the wake
     re-dispatches this exact injection. Do not edit the Step 2 block by hand. When
     `WAKE_OWNED=1`, re-arm the wake with that state file (D-36), using the recorded identity.
     Run this block (it calls nothing when `WAKE_OWNED=0`):

```bash
if [ "$WAKE_OWNED" = 1 ]; then
  python3 "$WAKE_SHIM" arm --host "$WAKE_HOST" --session-id "$WAKE_ID" --ref "$RESUME_STATE_PATH"
fi
```
  4. **Schedule or stop.** Only exit 75 with whole-number `RETRY_AFTER_S` and `CYCLE` gets the
     one-shot wait and re-dispatch of the same task, lane and model. A runner exit 69 or 75 whose
     status is `transient` or `quota` reaches this branch; an exit 69 (`stopped=hard-waits`,
     `stopped=cap`, or a `cross-ai: lane stopped=` refusal) is an owner stop after relaying the
     evidence, including that line's state path, whose deletion is the owner's reset; schedule
     nothing. A bare exit 75 is also an owner stop.
     Where `CronCreate` is callable, schedule one one-shot wake at `retry_after_s` (`RETRY_AFTER_S`;
     whole-minute rounding and the under-60 s case: ai-kit-cross-ai section 6) with the fenced
     prompt below; the job lives only as long as the session. A host without that scheduler, or
     a wait it cannot represent, schedules nothing: it prints `retry_after_s`,
     `$RESUME_STATE_PATH` and that same prompt, marks the printed row unverified, and the owner
     runs it. Never a repeated or fixed-interval job. Either way, STOP this wave and end the turn:
     do not start the next task until the wake's "ok" path has handled this task's report. No
     other stop (the cap, auth, off-router billing, permission, bad model, `not_installed`, a bare
     exit 75) is scheduled; for each, report `$RESUME_STATE_PATH`: an owner re-invoke re-dispatches
     the pinned injection, or re-enters Step 2 only with a replacement pair the owner names.

```text
Quota wake for this one task. Do not resolve a candidate, do not read the plan and do not
re-enter Step 2. Load the ai-kit-spec-execute-superpowers skill, then:
1. Bind SHIM=<SHIM>, CWD=<CWD>, QUOTA_PATH=<QUOTA_PATH>, DISPATCH_BASE=<DISPATCH_BASE>,
   PROMPT_FILE=<PROMPT_FILE>, FORMAT_BLOCK_FILE=<FORMAT_BLOCK_FILE>, REPORT_FILE=<REPORT_FILE>,
   RESUME_STATE_PATH=<RESUME_STATE_PATH> and REPORT_MODE=append.
2. From that state file bind PLAN_FILE (plan_path), TASK_N (task_index) and the restore list in
   references/state-management.md "Initial and resume values" (not its Step 2 re-entry); set
   INJECTION_JSON from injection_json and INJECTION_KEY from injection_json["key"].
3. If PROMPT_FILE still says WRITE the report, replace only that sentence with the APPEND
   sentence; leave the <objective> block byte-identical.
4. Run Step 3 point 3 (both blocks, the dispatch backgrounded) and point 4 as written. Every
   Bash call starts a fresh shell: substitute each value above literally in each call.
5. On "ok", load superpowers:subagent-driven-development, restore its ledger for PLAN_FILE and
   continue at "2. Handle the report" for task TASK_N.
```

  Substitute the eight placeholders (`<DISPATCH_BASE>` is the one Step 3 printed). The
  objective block stays byte-identical to the dispatch that just stopped: the runner reuses its
  session only when the task digest matches, and rewriting the objective would start a
  different task on the same lane. The report sentence sits outside it, so switching WRITE to
  APPEND never overwrites the partial report.

  **Resume of that wake.** Restoring `$RESUME_STATE_PATH` for this re-invoke keeps `injection_json`
  pinned and does not enter Step 2. An owner's plain resume keeps it pinned too; Step 2 re-resolves
  only when the owner names a replacement pair (`references/state-management.md`). A stop on the
  re-dispatched run re-enters this same quota branch; it does not pick another candidate.
- **`"real_error"`** — a failed external dispatch stops for the owner. Never resolve another
  candidate. Relay the runner's report, upstream and `AIKIT-XAI` lines from `$DISPATCH_BASE.err`
  verbatim first, then read `$DISPATCH_RESULT_JSON`'s
  `reason` and report its fix with Step 2's reason-to-fix list (auth, billing or access,
  configuration, capacity, `git_timeout`, timeout, `dispatch_unavailable`). Only a `real_error` reason proper
  (a crash, an empty answer, no change) offers the owner more context and a retry, a split of
  the task, or a ruling on a plan defect.

Task-review fix rounds after successful work (Step 4) are separate from dispatch-failure handling
and keep their own rules.

**Two current rules.** Pre-dispatch selection along the owner-configured ladder (the candidate
`resolve-injection` picks, and the Rounds 4–5 re-resolution before a fix-round dispatch) is the
shipped behavior, still awaiting the owner's confirmation. Nothing after a failure is authorized:
a failed or unusable run never switches harness, provider or model and never moves the work to
the native session. The runner owns the soft retry ladder; the owner decides. History:
`references/design-notes.md`.

**Exec confinement.** Codex runs under `--codex-sandbox workspace-write`: the runner uses
`--sandbox workspace-write` instead of the bypass, so writes stay inside the target dir plus
`/tmp` and `$TMPDIR`, which workspace-write always allows. Whether that sandbox also allows writes
inside `.git` is unverified. Every other exec target runs with full permissions; the guidance it
receives tells it to write only inside the target dir, and that prose is guidance, not a boundary.
`claude` is review-only: routing skips an exec-mode `claude` candidate on any other host, so it
never runs here. pi exec uses the runner's pi formula, verified by its hermetic self-test only;
live verification is still open, and stderr prints that note before the run. A copilot exec
target gets the same kind of note: its error rows are unverified, it runs with all tools allowed,
and the task prompt is visible on argv.

**The one exception.** Every subprocess runs through the supervised runner, except a custom entry
(a `command` and no `runtime`), which exec mode never runs (Step 2's exit 2, or a `review_only`
skip).

**Node.** Subprocess dispatch needs Node 24 (GSD's declared floor); older versions untested.
Without Node, the runner fails closed as `dispatch_unavailable`
(`ai-kit-spec: subprocess dispatch needs Node`). `resolve-injection`'s pre-dispatch walk can still
pick a native session-default entry; a dispatch that already failed that way is `real_error` and
stops for the owner.

**Rounds 4–5 capability escalation (`external_cli`, and `native` on every host but Claude
Code).** When `$FIX_ROUND >= 4` after the increment, subagent-driven-development requires "a MORE
CAPABLE model". Excluding the stuck key and re-walking the ladder does not guarantee that — the
next survivor may be weaker. The floor is relative to `$ESCALATION_ANCHOR_KEY` (the dispatch that
got stuck, fixed for the whole round and persisted across resumes), never to the key Step 2 just
picked. This re-resolution happens before the round's dispatch, so it is authorized pre-dispatch
selection along the owner-configured ladder. A failed dispatch is not retried in the same round
and never triggers it. **MANDATORY: before
computing `$ESCALATION_EXCLUDE_JSON` or passing `--escalation-excluded-keys-json`, read
`references/escalation.md` in full.** It defines the ladder-position capability proxy, the exact
computation and its edge cases, why the set never joins `$EXCLUDED_KEYS_JSON`, and how to branch
when the re-resolution reports `quota_exhausted` or `no_candidate` (an escalation-only exclusion
has empty `reasons`/`detail`, so report the excluded ladder keys by name).

## Step 4: Task review, fix loop, final review — unaffected

Whichever mode Step 3 used, subagent-driven-development's "3. Review the task", "4. The fix loop"
(rounds 1–5), and the final whole-branch review run unmodified on `$REPORT_FILE` and the real
commits. This skill's scope ends at Step 3; it never touches review, fix-loop adjudication, or the
ledger.

## Close the session wake (D-23)

When this skill's job ends (the final whole-branch review finished, or a stop ended the run:
STOP this wave, or an owner stop) and only when `WAKE_OWNED=1`, run:

```bash
if [ "$WAKE_OWNED" = 1 ]; then
  python3 "$WAKE_SHIM" done --host "$WAKE_HOST" --session-id "$WAKE_ID"
fi
```

Never run it on the one-shot wait branch of point 4, which continues the run, nor for a task still
waiting on its wake. When `WAKE_OWNED=0`, call nothing.
