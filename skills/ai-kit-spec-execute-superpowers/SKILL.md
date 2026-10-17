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
- **Never** schedule `CronCreate` when `any_quota_recoverable == False` or on `no_candidate` — no
  wait fixes a permanent failure; STOP and report instead (Step 2).
- **Never** run `trust-local` without the user's explicit yes, and never ask twice in one run
  (Step 2).

`CronCreate` and the `Agent` tool are Claude Code tools. On another host, use its own scheduler and
subagent mechanism, or STOP and tell the user to resume by hand.

## Step 0: Resolve the shim path

Take the FIRST existing candidate, in one `Bash` call:

```bash
for d in "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/ai-kit-spec-execute-superpowers}" \
         "$HOME/.claude/skills/ai-kit-spec-execute-superpowers" \
         "$(git rev-parse --show-toplevel 2>/dev/null)/skills/ai-kit-spec-execute-superpowers" \
         "$(pwd)/skills/ai-kit-spec-execute-superpowers"; do
  [ -n "$d" ] && [ -d "$d" ] && { SKILL_DIR="$d"; break; }
done
if [ -z "$SKILL_DIR" ]; then
  printf 'ERROR: could not resolve skills/ai-kit-spec-execute-superpowers under any known '
  printf 'installation shape (CLAUDE_PLUGIN_ROOT, ~/.claude/skills, git toplevel, or cwd) -- '
  printf 'STOP and tell the user rather than guessing a path.\n'
  exit 1
fi
SHIM="$SKILL_DIR/ai-kit-spec-superpowers.py"
for d in "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/ai-kit-spec-review}" \
         "$HOME/.claude/skills/ai-kit-spec-review" \
         "$(dirname "$SKILL_DIR")/ai-kit-spec-review"; do
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

**Record both printed lines as literal values.** Every later call uses `python3 "$SHIM"
<subcommand>`; `$TOOLS_PY` is `ai-kit-spec-review`'s shim, used for `cache-path --kind quota` and
`trust-local`. Every `Bash` call starts a fresh shell, so every `$VAR` below means the literal value
last captured for it via `printf`, re-substituted verbatim.

## Step 1: Load the plan under subagent-driven-development, unmodified

Follow that skill's own Setup exactly (workspace, ledger, plan read, pre-flight scan). `$CWD`,
`$PLAN_FILE`, `$TASK_N`, and `$BRIEF_FILE` below are values that skill already holds when it
dispatches each task's implementer — read them, never invent them.

## Step 2: Before each task's implementer dispatch — resolve the injection

**Before touching any exclusion-set variable, ask:** is this exclusion permanent (auth, config,
real error) or same-wave only (quota)? Mislabeling it does not crash; it silently either retries a
broken candidate forever or locks out a recovered one, wave after wave.

The state is a three-set split: `$PRIOR_EXCLUDED_KEYS_JSON`/`$PRIOR_REASONS_JSON` (permanent,
carried across resumes), `$WAVE_TRIED_JSON`/`$WAVE_REASONS_JSON` (this wave only), and the derived
unions `$EXCLUDED_KEYS_JSON`/`$EXCLUDED_REASONS_JSON` passed to `resolve-injection`, plus
`$FIX_ROUND`. **MANDATORY: before writing or reading any of these, or the resumable-state file,
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
printf 'INJECTION_JSON=%s\nINJECTION_MODE=%s\n' "$INJECTION_JSON" "$INJECTION_MODE"
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
  quota: do **not** schedule `CronCreate`. STOP this wave and report `detail`.
- **`quota_exhausted`** — read `any_quota_recoverable`
  (`python3 -c 'import json,sys; print(json.loads(sys.argv[1])["any_quota_recoverable"])' "$INJECTION_JSON"`).
  It, not `all_auth_failures`, is the gate. `reasons` holds `"quota"`, `"auth"`,
  `"billing_or_access"`, `"capacity"`, `"git_timeout"`, `"timeout"`, `"configuration"`,
  `"dispatch_unavailable"`, `"real_error"`, `"no_usable_dispatch"` (a prior wave's permanent
  failure), or a route name (`"bad_model"`, `"review_only"`,
  `"not_installed"`, `"no_inventory"`, `"unknown_runtime"`, `"no_model"`). Only `"quota"` is
  worth waiting for. A skip route is recorded under that route name and never picked.
  - **`any_quota_recoverable == False`** — every candidate failed for a reason waiting never fixes.
    Do **not** schedule `CronCreate`. STOP this wave and tell the user which key needs what fix,
    read off `reasons`: `"auth"` needs login or entitlement, `"billing_or_access"` credits or
    model access, `"configuration"` a fixed model id, prompt or flag (the runner refused it),
    `"capacity"` a later retry or another model, `"git_timeout"` a look at the repo (the runner's
    work-tree check timed out, not the CLI), `"timeout"`/`"dispatch_unavailable"` an
    investigation of the CLI, `"real_error"` its own diagnosis. This stop is the adapter's own
    call, not one of subagent-driven-development's four stop-and-ask conditions; see
    `references/design-notes.md`.
  - **`any_quota_recoverable == True`** — at least one candidate is quota-exhausted, which is
    time-bound. Write resumable state, schedule an hourly `CronCreate` wake, then STOP this wave
    without dispatching. **MANDATORY: read `references/state-management.md`'s "Resumable state"
    sections first** — they give the exact bash for merging `tried`/`reasons` into the wave sets,
    computing `$RESUME_EXCLUDED_KEYS_JSON` with the `resume-exclusions` subcommand (never inline
    set arithmetic), and the `STATE_JSON` passed to `write-resumable-state`. `CronCreate` prompt:
    `"re-check quota via probe-quota and, once restored, resume ai-kit-spec-execute-superpowers
    from $RESUME_STATE_PATH"`. Tell the user the job is session-scoped: it vanishes when the
    session exits, fires only while the session is idle, and expires after 7 days.
- **Otherwise** `$INJECTION_JSON` carries `mode`, `key`, `runtime`, `model`, `ladder_keys`, and for
  `external_cli` also `effort`, `service_tier`. Go to Step 3.

## Step 3: Dispatch the implementer — apply the injection

A reviewer or executor is a (runtime, model) pair. Each call runs it natively when its runtime is the current host and the host can select that model; otherwise it runs as a subprocess through the supervised runner. An entry with neither a runtime nor a model is the session default, which the host always runs natively. Today only Claude Code selects a model per call (its sonnet, opus, haiku and fable aliases); every other host runs only its session default natively.

**`mode == "native"`:** this host's own subagent mechanism, unchanged. On Claude Code, pass `model`
as the `Agent` tool's `model` parameter (omit it when empty) and record the returned agent identity;
fix-loop rounds 1–3 resume that same agent. Its round 4/5 model bump is that skill's own judgment,
with no ladder. On any other host the native case is only the session default, so omit `model` and
let the host use its current session.

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
printf 'PROMPT_FILE=%s\nFORMAT_BLOCK_FILE=%s\nREPORT_FILE=%s\n' \
  "$PROMPT_FILE" "$FORMAT_BLOCK_FILE" "$REPORT_FILE"
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
   only a short status line. On the task's first dispatch the prompt says WRITE `$REPORT_FILE`; on
   every later dispatch it says "APPEND your detailed report to the end of `$REPORT_FILE` — do not
   overwrite its existing contents from earlier rounds." (`--report-mode` only controls
   `dispatch-task`'s own stdout fallback, never what the CLI does to the file.) On a fix round, also
   append the open findings verbatim. **At the start of every fix round, increment `$FIX_ROUND`
   first** (not for a same-round quota retry), then apply the Rounds 4–5 rule below, then compose.
2. **Write the status contract** (`DONE` / `DONE_WITH_CONCERNS` / `NEEDS_CONTEXT` / `BLOCKED`, from
   implementer-prompt.md's "After Review Findings") to `$FORMAT_BLOCK_FILE`. It becomes the
   dispatch's format block.
3. **Dispatch.** `dispatch-task` prepares tooling guidance itself and runs the pair through the
   supervised runner. `--timeout 900` is a fixed constant: a candidate's per-entry `timeout_tiers`
   is not plumbed into this adapter.

```bash
DISPATCH_RESULT_JSON="$(python3 "$SHIM" dispatch-task --injection-json "$INJECTION_JSON" \
  --prompt-file "$PROMPT_FILE" --target-dir "$CWD" --heartbeat-interval 60 --timeout 900 \
  --format-block-file "$FORMAT_BLOCK_FILE" --report-file "$REPORT_FILE" \
  --report-mode "$REPORT_MODE")"
printf 'DISPATCH_RESULT_JSON=%s\n' "$DISPATCH_RESULT_JSON"
```

`--heartbeat-interval` is required but unused: the runner prints its own heartbeat.

   Then `REPORT_MODE=append`. If the CLI wrote `$REPORT_FILE` itself, `dispatch-task` leaves it
   untouched; only when the file is unchanged does it write or append the captured stdout, behind a
   marker line. Either way, review and the fix loop read `$REPORT_FILE` like a native report.

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
  `$REPORT_FILE` for one.
- **`"quota"`** — this candidate ran out of quota mid-dispatch. Record it as a wave-tried key WITH
  the `"quota"` reason, never straight into `$EXCLUDED_KEYS_JSON` without one:

```bash
WAVE_TRIED_JSON="$(python3 -c 'import json,sys; print(json.dumps(sorted(set(json.loads(sys.argv[1])) | {sys.argv[2]})))' \
  "$WAVE_TRIED_JSON" "$INJECTION_KEY")"
WAVE_REASONS_JSON="$(python3 -c 'import json,sys; d=json.loads(sys.argv[1]); d[sys.argv[2]]="quota"; print(json.dumps(d))' \
  "$WAVE_REASONS_JSON" "$INJECTION_KEY")"
EXCLUDED_KEYS_JSON="$(python3 -c 'import json,sys; print(json.dumps(sorted(set(json.loads(sys.argv[1])) | set(json.loads(sys.argv[2])))))' \
  "$PRIOR_EXCLUDED_KEYS_JSON" "$WAVE_TRIED_JSON")"
```

  Then re-run Step 2's `resolve-injection` with the same shape: the new `--exclude-keys-json`, a
  recomputed `--excluded-reasons-json` (prior merged with the updated wave reasons), and, when this
  round is capability-escalated (`$ESCALATION_EXCLUDE_JSON` non-empty), also
  `--escalation-excluded-keys-json "$ESCALATION_EXCLUDE_JSON"` so the retry keeps the capability
  floor. Retry Step 3 with the new injection; never re-dispatch the same candidate blind. If the
  re-resolution reports `quota_exhausted` (it does so even when every candidate is now excluded),
  follow Step 2's `any_quota_recoverable` branch, which also merges its `tried`/`reasons` into the
  wave sets.
- **`"real_error"`** — never retried unchanged. Handle it as subagent-driven-development's
  `BLOCKED`: more context and retry, a capability-escalated candidate (below), split the task, or
  rule on a plan defect.

**Exec confinement.** Codex runs under `--codex-sandbox workspace-write`: the runner uses
`--sandbox workspace-write` instead of the bypass, so writes stay inside the target dir plus
`/tmp` and `$TMPDIR`, which workspace-write always allows. Whether that sandbox also allows writes
inside `.git` is unverified. Every other exec target runs with full permissions; the guidance it
receives tells it to write only inside the target dir, and that prose is guidance, not a boundary.
`claude` is review-only: routing skips an exec-mode `claude` candidate on any other host, so it
never runs here. pi exec uses the runner's pi formula, verified by its hermetic self-test only;
live verification is Phase 22, and stderr prints that note before the run.

**The one exception.** Every subprocess runs through the supervised runner, except a custom entry
(a `command` and no `runtime`): exec mode never runs it. With `purpose = "execute"`,
`resolve-injection` exits 2; otherwise it is skipped with a stderr warning (routed `review_only`)
and never reaches `dispatch-task`. In review it runs through the fixed-argv custom launcher on the
same supervision core.

**Node.** Subprocess dispatch needs Node 24 (GSD's declared floor); older versions untested.
Without Node, the runner fails closed as `dispatch_unavailable`
(`ai-kit-spec: subprocess dispatch needs Node`) and the session default still runs.

**Rounds 4–5 capability escalation (`external_cli` only).** When `$FIX_ROUND >= 4` after the
increment, subagent-driven-development requires "a MORE CAPABLE model". Excluding the stuck key and
re-walking the ladder does not guarantee that — the next survivor may be weaker. **MANDATORY:
before computing `$ESCALATION_EXCLUDE_JSON` or passing `--escalation-excluded-keys-json`, read
`references/escalation.md` in full.** It defines the ladder-position capability proxy, the exact
computation and its edge cases, why the set never joins `$EXCLUDED_KEYS_JSON`, and how to branch
when the re-resolution reports `quota_exhausted` or `no_candidate` (an escalation-only exclusion
has empty `reasons`/`detail`, so report the excluded ladder keys by name).

## Step 4: Task review, fix loop, final review — unaffected

Whichever mode Step 3 used, subagent-driven-development's "3. Review the task", "4. The fix loop"
(rounds 1–5), and the final whole-branch review run unmodified on `$REPORT_FILE` and the real
commits. This skill's scope ends at Step 3; it never touches review, fix-loop adjudication, or the
ledger.
