---
name: ai-kit-spec-execute-superpowers
description: Runs a superpowers implementation plan (docs/superpowers/plans/*.md) under superpowers:subagent-driven-development, resolving a live-quota-checked (runtime, model) pair for each task's implementer dispatch (native or external CLI), with quota waits and fix-round escalation; it starts the plan's unit branch before the first task and folds, pushes and readies it after the final review through ai-kit-commit-fold. Use when ai-kit-spec-execute detects a superpowers plan run under subagent-driven-development, or when asked to execute or run a superpowers plan that way, including its per-task model choice. Not for superpowers:executing-plans (inline, no dispatch point) or for folding a branch on its own (ai-kit-commit-fold).
---

# ai-kit-spec-execute-superpowers

**This skill never dispatches a task without a resolved pair.** It resolves WHICH pair a task should
use, then applies that resolution at `superpowers:subagent-driven-development`'s one documented
dispatch point ("1. Dispatch the implementer"): a native pair goes to that host's own subagent
mechanism, an `external_cli` pair is dispatched through the shim's `dispatch-task` and the
supervised runner (Step 3). That skill keeps full ownership of TDD enforcement,
fresh-subagent-per-task, agent identity and resume, task review, fix loops, and the final
whole-branch review. `superpowers:executing-plans` is out of scope: no dispatch point to inject into.
Rationale for each rule lives in `references/design-notes.md`: read it when one looks arbitrary,
Do NOT load it otherwise.

## NEVER

Each rule is stated here; other places point back to it.

- **Never** persist `$EXCLUDED_KEYS_JSON` wholesale as `excluded_keys`: a same-wave `"quota"` exclusion would read as permanent (Step 2; `references/state-management.md`).
- **Never** call `resolve-injection` with `--exclude-keys-json` alone, omitting `--excluded-reasons-json`: prior-wave permanent reasons then read `"no_usable_dispatch"` (Step 2).
- **Never** read `key`/`runtime` off an injection result before checking `$INJECTION_MODE`: `quota_exhausted` and `no_candidate` carry neither (Step 2).
- **Never** put `$INJECTION_RUNTIME` into an exclusion set: a runtime id is not a ladder key (Step 3).
- **Never** fold `$ESCALATION_EXCLUDE_JSON` into `$EXCLUDED_KEYS_JSON`: it marks healthy,
  never-tried candidates excluded only for a capability floor (Step 3; `references/escalation.md`).
- **Never** let a fix-loop round overwrite `$REPORT_FILE`: `REPORT_MODE` is `write` at most once per
  task, `append` after, and every prompt after the first says APPEND (Step 3).
- **Never** parse the implementer status out of `$REPORT_FILE`, only from `$DISPATCH_RESULT_JSON["stdout"]` (Step 3).
- **Never switch harness, provider or model** after a failed or unusable run.
  **Never re-resolve to another candidate after a failed dispatch.** Do not re-run `resolve-injection`
  to recover; re-dispatch only the persisted injection after its one-shot wait (Step 3; ai-kit-cross-ai sections 6 and 8). The one exception is a lane the owner flagged `usage_limited` that stops on quota: it moves to its configured fallback ([references/resolution-stops.md#owner-stop](references/resolution-stops.md#owner-stop)).
- **Never** run `trust-local` without the user's explicit yes, or ask twice in one run (Step 2).
- **Never** run `fold.py boundary --next` during a run: it rewrites this unit's `.aikit/brief/SKILL.md` as `unit: next`, replacing the current unit's brief, with or without `--repo` (Step 1).

The `Agent` tool and the one-shot `CronCreate` at `retry_after_s` are Claude Code tools. On another
host, use its own subagent mechanism (or STOP and tell the user to resume by hand) and the
Schedule-or-stop step's print path (`references/dispatch-external-cli.md`).

**Cross-AI caller contract:** [`../ai-kit-cross-ai/SKILL.md`](../ai-kit-cross-ai/SKILL.md).
MANDATORY: read it before the first `dispatch-task` and again before acting on any non-zero runner
`returncode` in `$DISPATCH_RESULT_JSON` (sections 4, 6, 8). Do NOT load it at any other point.
The only key changes are pre-dispatch selection, the Rounds 4–5 bump (Step 3) and a pair the owner
names after a stop (`references/state-management.md`, "Owner-named replacement pair").

## Step 0: Resolve the shim path

Take the FIRST candidate that holds the shim file, in one `Bash` call:

```bash
for d in "$(dirname "<absolute path to THIS SKILL.md>")" \
         "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/ai-kit-spec-execute-superpowers}" \
         "$HOME/.claude/skills/ai-kit-spec-execute-superpowers" \
         "$(git rev-parse --show-toplevel 2>/dev/null)/skills/ai-kit-spec-execute-superpowers" \
         "$(pwd)/skills/ai-kit-spec-execute-superpowers"; do
  case "$d" in ""|.|*"<"*) continue ;; esac  # an unfilled placeholder (dirname gives ".") is never a path
  [ -f "$d/ai-kit-spec-superpowers.py" ] && { SKILL_DIR="$d"; break; }
done
if [ -z "$SKILL_DIR" ]; then
  printf 'ERROR: could not resolve skills/ai-kit-spec-execute-superpowers under any known installation shape (this SKILL.md, CLAUDE_PLUGIN_ROOT, ~/.claude/skills, git toplevel, or cwd) -- STOP and tell the user rather than guessing a path.\n'
  exit 1
fi
SHIM="$SKILL_DIR/ai-kit-spec-superpowers.py"
REVIEW_SKILL_DIR="$(dirname "$SKILL_DIR")/ai-kit-spec-review"
if [ ! -d "$REVIEW_SKILL_DIR" ]; then
  printf 'ERROR: ai-kit-spec-review is not installed beside %s, where the shim imports it from -- STOP and tell the user rather than guessing a path.\n' "$SKILL_DIR"
  exit 1
fi
TOOLS_PY="$REVIEW_SKILL_DIR/ai-kit-spec.py"
printf 'SKILL_DIR=%s\nSHIM=%s\nTOOLS_PY=%s\n' "$SKILL_DIR" "$SHIM" "$TOOLS_PY"
```

Replace `<absolute path to THIS SKILL.md>` with the absolute path of the SKILL.md you just loaded.
This skill's own directory is tried first, so the shims match the `SKILL.md` you follow; the
review skill must be its sibling (the shim puts both on `sys.path`). **Record all three printed
lines**: the task-paths block below feeds them into the scalar file. Every later call uses
`python3 "$SHIM" <subcommand>`; `$TOOLS_PY` is `ai-kit-spec-review`'s shim (`cache-path`, `trust-local`).

**Scalars live in a file, not in your memory.** Every `Bash` call starts a fresh shell, so each
scalar `$VAR` (path, key, id, round, wake identity) is appended to the plan's scalar file as
`NAME=value` by `| tee -a "$SCALARS"` on the block that prints it; the last line for a name wins.
**From the task-paths block on, every `Bash` call in this skill and its references opens with this
loader (the listings omit it)**; `SCALARS` is the one literal you re-type:

```bash
SCALARS="<the path the task-paths block printed>"
while IFS== read -r k v; do [[ $k =~ ^[A-Z][A-Z0-9_]*$ ]] || continue; printf -v "$k" '%s' "$v"; done < "$SCALARS"
```

The loader only assigns, never `source`s or `eval`s, so quotes, `$` and backticks stay inert; scalar values are single-line. **Quoting rule: never paste JSON text into a command.** Passing `"$NAME"` or
`"$(cat file)"` as an argv is safe: a double-quoted expansion is never re-parsed, so quotes, `$`, backticks and newlines stay inert.
`INJECTION_JSON`, `PRIOR_*`, `WAVE_*`, `EXCLUDED_KEYS_JSON` and `ESCALATION_EXCLUDE_JSON` live in
`$RUN_DIR/<NAME>.json`, `DISPATCH_RESULT_JSON` is `$DISPATCH_BASE.json`; a call loads one with
`NAME="$(cat "$RUN_DIR/NAME.json")"` and saves a change with `printf '%s' "$NAME" > "$RUN_DIR/NAME.json"`.

## Step 1: Load the plan under subagent-driven-development, unmodified

First probe that `superpowers:subagent-driven-development` loads through the host's skill mechanism; if not, STOP and tell the user (nothing to delegate to). Follow its own Setup exactly (workspace, ledger, plan read, pre-flight scan). `$CWD`, `$PLAN_FILE`, `$TASK_N`, and `$BRIEF_FILE` are values it already holds at each task's implementer dispatch — read them, never invent them.

**No-config check, before the start step: MANDATORY: read [`references/config-check.md`](references/config-check.md) in full and run its block 1 once per plan.** It runs `config-status`, asks the owner at most once when no lanes exist (run ai-kit-spec-config now, run once on the session model, or stop) before any commit moves, and records `CONFIG_CHECK=` in the plan's scalar file so a resumed run never asks again (a fresh start checks again). Load it at three points only: here, for block 3 in session-model mode (Step 2), and for its notice line at Step 5.

Before the first task, start the plan's unit: **MANDATORY: read [`references/start-step.md`](references/start-step.md) in full and run its block once** (`fold.py start --plan`; it handles every refusal). superpowers' planning skills commit the spec and plan before this step; `start` carries those local-only commits onto the unit branch, so they stay in its PR and below `FOLD_BASE`: each commit that touches the plan file or the spec on the plan's `**Spec:**` line, even a spec committed on its own. The plan already exists when this skill runs, so this skill never briefs a plan writer and never runs `fold.py boundary --next` (see NEVER): that command rewrites the same `.aikit/brief/SKILL.md` as `unit: next`, replacing the wave brief the start block just wrote for this unit (`--repo` defaults to the current directory). A project that briefs its superpowers plan writer does that before the plan exists, from its own instruction file.

After the Task paths block prints `SCALARS`, record the start commit once (later tasks keep it, and Step 5 clears it once the unit is folded, so a later run of the same plan records its own):
`[ -n "$FOLD_BASE" ] || printf 'FOLD_BASE=%s\n' "$(git -C "$CWD" rev-parse HEAD)" | tee -a "$SCALARS"`;
after a yes to running without the unit flow, also `printf 'UNIT_FLOW=0\n' | tee -a "$SCALARS"`.
If the plan's last `### Task` does not name `ai-kit-commit-fold`, add a final todo `Fold the plan's commits (ai-kit-commit-fold)` to subagent-driven-development's task list; never edit the plan file.

## Task paths (the first action for every task)

Run once per task, before the wake block: it computes the task's paths, checks for a resume
state file and appends everything to the plan's scalar file. Fill the first two lines from Step 0
and Step 1 (a fresh shell holds nothing); the guard stops on an empty or placeholder value.
**Record the printed `SCALARS` as the loader's literal.**

```bash
SKILL_DIR="<Step 0 SKILL_DIR>"; SHIM="<Step 0 SHIM>"; TOOLS_PY="<Step 0 TOOLS_PY>"
CWD="<Step 1 CWD>"; PLAN_FILE="<Step 1 PLAN_FILE>"; TASK_N="<Step 1 TASK_N>"
for n in SKILL_DIR SHIM TOOLS_PY CWD PLAN_FILE TASK_N; do case "${!n}" in ""|"<"*)
  printf 'ERROR: %s is empty or a placeholder -- fill it from Step 0/Step 1\n' "$n"; exit 1 ;; esac; done
QUOTA_PATH="$(python3 "$TOOLS_PY" cache-path --kind quota)"
PROJECT_KEY="$(python3 -c 'import hashlib,sys; print(hashlib.sha256("\n".join(sys.argv[1:3]).encode()).hexdigest()[:12])' "$CWD" "$PLAN_FILE")"
RESUME_STATE_PATH="$(dirname "$QUOTA_PATH")/superpowers-resume-${PROJECT_KEY}-task-${TASK_N}.json"
RUN_DIR="$(dirname "$QUOTA_PATH")/superpowers-run-${PROJECT_KEY}-task-${TASK_N}"
SCALARS="$(dirname "$QUOTA_PATH")/superpowers-run-${PROJECT_KEY}-scalars.env"
mkdir -p "$RUN_DIR"
if [ -f "$RESUME_STATE_PATH" ]; then RESUME_FOUND=1; else RESUME_FOUND=0; fi
for n in SCALARS SKILL_DIR SHIM TOOLS_PY CWD PLAN_FILE TASK_N QUOTA_PATH PROJECT_KEY RESUME_STATE_PATH \
  RUN_DIR RESUME_FOUND; do printf '%s=%s\n' "$n" "${!n}"; done | tee -a "$SCALARS"
```

## Arm the session wake (plans with two or more tasks)

**MANDATORY: read [`references/session-wake.md`](references/session-wake.md) in full, once per plan,
before the first task's implementer dispatch**, and run its arm block only when `$PLAN_FILE` holds two
or more `### Task <n>` headings. Do NOT load it for a single-task plan. It sets `WAKE_OWNED`,
`WAKE_HOST` and `WAKE_ID` for every later task; a failed or refused arm never fails the run.

## Step 2: Before each task's implementer dispatch — resolve the injection

**Before touching any exclusion-set variable, ask:** is this exclusion permanent (auth, config,
real error) or same-wave only (quota)? Mislabeling it either retries a broken candidate forever
or locks out a recovered one.

The state is three sets (permanent exclusions, this wave's tried keys, the derived unions passed to
`resolve-injection`) plus the scalars `$FIX_ROUND`, `$LAST_DISPATCHED_KEY` and
`$ESCALATION_ANCHOR_KEY`. **MANDATORY: before writing or reading any exclusion-set variable or the
resumable-state file, read `references/state-management.md` in full** — it names every variable,
its initial and resume values, and the exact resumable-state bash.

Step 2 runs once per task, before its first dispatch, and again only for a resume without a pinned `injection_json`, a trust-local yes, or the Rounds 4–5 re-resolution (Step 3). A restored `injection_json` is pinned ([`references/state-management.md#pinned-resume`](references/state-management.md#pinned-resume)). Fix rounds 1–3 reuse the task's `$INJECTION_JSON` unchanged. **Session-model mode:** when the scalar `CONFIG_CHECK` is `once` or `notice`, run block 3 of `references/config-check.md` in place of the `resolve-injection` block for every task (it writes `$RUN_DIR/INJECTION_JSON.json` with mode `native` and an empty key, runtime and model, and records `INJECTION_MODE=native`); the rest of Step 2 and Step 3 run unchanged, so the task dispatches natively with `model` omitted (the session model).

**Resume check — before any resolution** (a re-invoke starts here with no memory; the task-paths block printed `RESUME_FOUND`): run [`references/state-management.md#pinned-resume`](references/state-management.md#pinned-resume) — Seed on `RESUME_FOUND=0` (never from the quota-wake prompt), Restore on `RESUME_FOUND=1`. A pinned injection goes straight to Step 3, reusing the existing `$PROMPT_FILE` (switch only its WRITE sentence to APPEND; never recompose the objective); otherwise run the rest of this step on the restored values, and a restored `$FIX_ROUND >= 4` ends in `references/escalation.md`'s resolve block (Step 3).

Right after that skill's `scripts/task-brief PLAN_FILE N` writes `$BRIEF_FILE`:

```bash
BRIEF_FILE="<the path task-brief wrote>"
PRIOR_REASONS_JSON="$(cat "$RUN_DIR/PRIOR_REASONS_JSON.json")"
WAVE_REASONS_JSON="$(cat "$RUN_DIR/WAVE_REASONS_JSON.json")"
EXCLUDED_KEYS_JSON="$(cat "$RUN_DIR/EXCLUDED_KEYS_JSON.json")"
EXCLUDED_REASONS_JSON="$(python3 -c 'import json,sys; a=json.loads(sys.argv[1]); a.update(json.loads(sys.argv[2])); print(json.dumps(a))' \
  "$PRIOR_REASONS_JSON" "$WAVE_REASONS_JSON")"
INJECTION_JSON="$(python3 "$SHIM" resolve-injection --cwd "$CWD" --task-file "$BRIEF_FILE" \
  --quota-path "$QUOTA_PATH" --exclude-keys-json "$EXCLUDED_KEYS_JSON" \
  --excluded-reasons-json "$EXCLUDED_REASONS_JSON" --fix-round "${FIX_ROUND:-0}")"
INJECTION_RC=$?
[ "$INJECTION_RC" -eq 0 ] || { echo "resolve-injection exit $INJECTION_RC"; exit "$INJECTION_RC"; }
printf '%s' "$INJECTION_JSON" > "$RUN_DIR/INJECTION_JSON.json"
INJECTION_MODE="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["mode"])' "$INJECTION_JSON")"
for n in BRIEF_FILE INJECTION_MODE; do printf '%s=%s\n' "$n" "${!n}"; done | tee -a "$SCALARS"
```

`--excluded-reasons-json` always gets the merge of `$PRIOR_REASONS_JSON` and `$WAVE_REASONS_JSON`,
never `$WAVE_REASONS_JSON` alone.

**Non-zero exit or an untrusted-project-config line** (`resolve-injection exit 2`; stderr `ai-kit-spec: ignoring untrusted project-local config <path>; ...`): **MANDATORY: read [`references/resolution-stops.md#owner-stop`](references/resolution-stops.md#owner-stop)** for the stop, the one-per-run `trust-local` ask and the re-run. Never run `trust-local` unasked.

**Restored `$FIX_ROUND >= 4` with no pinned `injection_json`, checked first:** after a zero exit and the trust handling above, this result in any mode (`no_candidate` and `quota_exhausted` included) supplies only `ladder_keys` and skips the mode branch below: go straight to `references/escalation.md`'s resolve block (Step 3), whose result alone meets the owner stop ("Rounds 4–5 re-resolution"; [`references/state-management.md#pinned-resume`](references/state-management.md#pinned-resume)).

**Branch on `$INJECTION_MODE` before reading any other field.** Only `native` and `external_cli`
carry `key`/`runtime` (`$INJECTION_KEY` is the ladder key such as `codex/terra`, `$INJECTION_RUNTIME`
the runtime id, empty for the session default); both come from one routing decision, never a stored field.
A route of `unverified` still dispatches as `external_cli`: the model list was unavailable, so
nothing checks the model first, and stderr prints `ai-kit-spec: dispatching <key> unverified: ...`.

```bash
INJECTION_JSON="$(cat "$RUN_DIR/INJECTION_JSON.json")"
if [ "$INJECTION_MODE" != "quota_exhausted" ] && [ "$INJECTION_MODE" != "no_candidate" ]; then
  INJECTION_KEY="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["key"])' "$INJECTION_JSON")"
  INJECTION_RUNTIME="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1]).get("runtime") or "")' \
    "$INJECTION_JSON")"
  printf 'INJECTION_KEY=%s\nINJECTION_RUNTIME=%s\n' "$INJECTION_KEY" "$INJECTION_RUNTIME" | tee -a "$SCALARS"
fi
```

- **`no_candidate`, `quota_exhausted`** — **MANDATORY: read [`references/resolution-stops.md#owner-stop`](references/resolution-stops.md#owner-stop)** (reason-to-fix list, the `any_quota_recoverable` gate, the resumable-state write). Do NOT load it for any other mode at this mode check.
- **Otherwise** `$INJECTION_JSON` carries `mode`, `key`, `runtime`, `model`, `ladder_keys`, and for
  `external_cli` also `effort`, `service_tier`. Go to Step 3 (a restored `$FIX_ROUND >= 4` with no pinned
  `injection_json`: dispatch only the result of `references/escalation.md`'s resolve block, never this pick).

## Step 3: Dispatch the implementer — apply the injection

The (runtime, model) pair contract and the native-versus-subprocess routing are defined in `ai-kit-spec-config` and `ai-kit-spec-review`; `$INJECTION_MODE` is that routing's result, never re-decided here.

**At the start of every fix round, in either mode, increment `$FIX_ROUND` and set
`ESCALATION_ANCHOR_KEY="$LAST_DISPATCHED_KEY"` first** (block below; new rounds only, never on a resume,
a re-invoke that kept its scalars or a Step-2 re-entry, which keep the round and anchor, yet at 4 or more still take the floor below). Rounds 1–3 keep `$INJECTION_JSON` and skip Step 2. A failed dispatch gets no same-round re-dispatch, except the flagged-lane switch ([references/resolution-stops.md#owner-stop](references/resolution-stops.md#owner-stop)). Run the block below only at a new round: a restored `$FIX_ROUND` already counts the round, so the resume path never runs it: at a restored round of 4 or more with no pinned `injection_json` it goes to `references/escalation.md`'s resolve block; at rounds 1–3, or with a pinned injection, it dispatches through Step 3 unchanged.

**Session fallback (`"fallback": "session"` in `$INJECTION_JSON`), checked before the escalation and native rules below:** an exception inside the native branch below, never a second launch path. At rounds 4–5 it runs on the session model with no ladder escalation and no model bump (the rounds 4–5 paragraph below), then dispatches through the native branch below unchanged, with its `model` as the `Agent` tool's `model` on Claude Code (omitted when empty: the session model); relay the stderr notice of its first selection to the owner; a pinned resume keeps the saved injection ([`references/resolution-stops.md#owner-stop`](references/resolution-stops.md#owner-stop), [`references/state-management.md#pinned-resume`](references/state-management.md#pinned-resume)).

**Rounds 4–5 capability escalation (`external_cli`, and `native` on every host but Claude Code).**
At `$FIX_ROUND >= 4` after the increment, or restored at 4 or more by a resume with no pinned
`injection_json` (a pin always re-dispatches unchanged), subagent-driven-development requires "a MORE
CAPABLE model". **MANDATORY: read `references/escalation.md` in full before composing or dispatching
the round and before computing `$ESCALATION_EXCLUDE_JSON`**: the floor is relative to
`$ESCALATION_ANCHOR_KEY` (the dispatch that got stuck), never to the key Step 2 just picked, and is
applied before the round's dispatch, never after a failed one. An empty or unknown anchor is an owner
stop ([`references/resolution-stops.md#owner-stop`](references/resolution-stops.md#owner-stop)).
Do NOT load it at rounds 1–3. In session-model mode, or when the task's injection carries the session fallback, rounds 4–5 run on the session model with no ladder escalation and no model bump; the escalation rule above applies to every other mode. The stuck lane's `escalate_runtime` and `escalate_model` flags decide whether, and along which kind, the round moves (`references/escalation.md`).

```bash
FIX_ROUND=$((FIX_ROUND + 1)); ESCALATION_ANCHOR_KEY="$LAST_DISPATCHED_KEY"  # new round only, never on a resume
printf 'FIX_ROUND=%s\nESCALATION_ANCHOR_KEY=%s\n' "$FIX_ROUND" "$ESCALATION_ANCHOR_KEY" | tee -a "$SCALARS"
```

**Clear the resume state when a dispatch succeeds** (only after it, never before dispatching: a native dispatch that returned, or an
`external_cli` one classified `"ok"`), so a re-invoke never restores a stale round or pinned
injection; a later stop rewrites it from the live values. It removes only this task's own file,
never the runner's lane file:

```bash
if [ -n "$RESUME_STATE_PATH" ]; then rm -f -- "$RESUME_STATE_PATH"; fi
```

Every implementer brief, native or `external_cli`, starts with this unit-brief line before the task text: `Unit brief: read .aikit/brief/SKILL.md in $CWD after the plan and spec; it lists the previous unit's changed files and the documents that mention them. If it is missing, says no brief, or names another unit, say so and continue.`

**Gates and commit guard (both branches; the one input recipe).** At a task's first actual dispatch, that is whenever the loaded scalar `GUIDANCE_READY` is not `$TASK_N`, write `$RUN_DIR/gates.txt` with the project's gate commands and `$RUN_DIR/guard.txt` with the caller's commit-guard text, then record `GUIDANCE_READY`; later dispatches of the task reuse both files, and a fresh start of the plan clears `GUIDANCE_READY` (sources, deletes and the scalar line: [`references/state-management.md#gates-and-guard-inputs`](references/state-management.md#gates-and-guard-inputs)). Both branches pass `--gates-file` and `--guard-file` only for a file that exists and `--owner-config .aikit/config.toml` always: the native branch, a session-fallback dispatch included, runs the block below, launches only when that block exits 0 (a non-zero exit is an input error: stop for the owner through [`references/resolution-stops.md#owner-stop`](references/resolution-stops.md#owner-stop), naming the error line it printed) and appends `$RUN_DIR/guidance.txt` to its brief; the `external_cli` branch runs the Dispatch block of `references/dispatch-external-cli.md`.

**`mode == "native"`:** this host's own subagent mechanism, unchanged. The native brief carries the same unit-brief line above. On Claude Code, pass `model` as
the `Agent` tool's `model` parameter (omit it when empty) and record the returned agent identity;
fix-loop rounds 1–3 resume that same agent. Its round 4/5 model bump follows that skill's own rule (a
more capable model) and happens before the round's dispatch, after a review returned findings. On any other host the native case is
only the session default, so omit `model` and let the host use its current session. Either way, after
the dispatch run `printf 'LAST_DISPATCHED_KEY=%s\n' "$INJECTION_KEY" | tee -a "$SCALARS"` and clear the
resume state. A non-Claude native dispatch cannot raise its own model, so rounds 4–5 take the ladder escalation above. A failed native dispatch (for example an `Agent` model error) is
subagent-driven-development's own (NEVER index); stop for the owner when that skill has no route ([`references/resolution-stops.md#owner-stop`](references/resolution-stops.md#owner-stop)). Every native launch (the session fallback and a failed native launch included) runs one audit: before it `rm -f "$RUN_DIR/host-config-before.json"` and `python3 "$SHIM" host-config-audit --snapshot "$RUN_DIR/host-config-before.json"`, after it `python3 "$SHIM" host-config-audit --compare "$RUN_DIR/host-config-before.json"`, then `rm -f "$RUN_DIR/host-config-before.json"`; relay every `ai-kit-spec: observation:` line it prints as an observation, never a stop ([host-config audit](references/dispatch-external-cli.md#host-config-audit)). The runner's real-home guard is not applicable to a native dispatch: the subagent runs in this session's own process.

```bash
GUIDE_ARGS=(--owner-config .aikit/config.toml)
[ -f "$RUN_DIR/gates.txt" ] && GUIDE_ARGS+=(--gates-file "$RUN_DIR/gates.txt")
[ -f "$RUN_DIR/guard.txt" ] && GUIDE_ARGS+=(--guard-file "$RUN_DIR/guard.txt")
python3 "$SHIM" print-guidance "${GUIDE_ARGS[@]}" > "$RUN_DIR/guidance.txt"
```

**`mode == "external_cli"`:** a subprocess through the supervised runner. A CLI process exits when
done, so there is no live agent to resume. Every dispatch, first attempt and every fix round,
uses subagent-driven-development's documented fallback: a fresh implementer carrying the brief
path, report-file path and findings, with the report file as the persistent memory.

**MANDATORY: read [`references/dispatch-external-cli.md`](references/dispatch-external-cli.md) in
full before the first `dispatch-task` of a task and again before acting on its result.** Do NOT
load it for `mode == "native"`. It holds the artifact setup, Compose, Status contract and
Dispatch steps, the **Classify** step (`ok`, `quota_cycle`, `quota`, `real_error`) and, inside `quota_cycle` and `quota`, the
**Schedule-or-stop** step. `ok` continues in Classify; whether every other outcome waits once or stops (the one-shot `quota_cycle` wait, `quota` with the runner's `stopped=hard-waits` and `stopped=cap`, `real_error`) is decided once in [`references/resolution-stops.md#owner-stop`](references/resolution-stops.md#owner-stop): **MANDATORY: read it before acting on any outcome other than `ok`**.

**Exec confinement** (reasoning: `references/design-notes.md`). Codex runs under
`--codex-sandbox workspace-write` (writes stay in the target dir plus `/tmp`, `$TMPDIR` and any writable root the owner's codex
configuration adds, so this is not an unconditional boundary; the writable roots and protected paths are defined in the official Codex source named in Evidence). A task that must commit checks the lane's effective policy there and in the owner's codex configuration first; when Git metadata is read-only, stop for the owner ([`references/resolution-stops.md#owner-stop`](references/resolution-stops.md#owner-stop)). Every other exec target has full permissions, and its stay-in-the-target-dir
guidance is not a boundary. A `claude` lane takes the route the shim returns: a supported alias on a Claude Code host can be native; any other `claude` pair runs as a subprocess or is skipped with the route the shim names (`no_formula` only when the runner's recorded `--describe` facts give it no exec formula). pi exec is verified by the
runner's hermetic self-test only and live verification is still open (stderr prints that note); a copilot target gets a similar note:
unverified error rows, all tools allowed, the task prompt visible on argv. **Node:** subprocess dispatch is tested on Node 24 (ai-kit's tested floor); older versions untested (GSD's own floor: Evidence). The runner fails closed as `dispatch_unavailable` (a `real_error` stop) only when `node` is absent; an older Node may crash, and that crash is a `real_error` of the pair, never a reason to switch pairs.

## Step 4: Task review, fix loop, final review — unaffected

Whichever mode Step 3 used, subagent-driven-development's "3. Review the task", "4. The fix loop"
(rounds 1–5), and the final whole-branch review run unmodified on `$REPORT_FILE` and the real
commits; fix rounds after successful work are separate from dispatch-failure handling. This
skill's scope ends at Step 3 until Step 5 and never touches review, adjudication, or the ledger.

## Step 5: Fold the finished plan (after the final review, before the finishing step)

**MANDATORY: read [`references/fold-step.md`](references/fold-step.md) in full and run its block once the final whole-branch review passes.** The block runs `fold.py checkpoint --plan "$PLAN_FILE" --base "$FOLD_BASE" --final` (the unit's last checkpoint, with the fold step's range kept), then `fold.py ready --plan "$PLAN_FILE"`. A refusal stops the run and shows the report; never move the branch by hand. When the last report's outcome is `done` or `nothing to do`, clear the run's start scalars, `printf 'FOLD_BASE=\nUNIT_FLOW=\n' | tee -a "$SCALARS"`, so the next run of this plan records its own; any other outcome keeps them for the re-run. superpowers' finishing step does not merge, push or open a PR for this unit: ai-kit's unit flow does, and pushes only with push consent. A plan run inline, without this skill, runs the same three commands from the fold skill's `references/adapter-guide.md`. When the scalar `CONFIG_CHECK` is `once` or `notice`, print its notice line from `references/config-check.md` again after the fold block.

## Close the session wake

When the job ends (the final whole-branch review finished, which the caller runs, or a stop listed in [`references/resolution-stops.md#owner-stop`](references/resolution-stops.md#owner-stop) ended the run) and only when `WAKE_OWNED=1`, run the close block in `references/session-wake.md` (never on the one-shot wait branch of Schedule-or-stop). When `WAKE_OWNED=0`, call nothing.

## Evidence

- Node: Node 24 is ai-kit's tested floor for the runner; this tree declares no `engines` field. GSD's declared floor is its package's `engines.node`, read live with `npm view @opengsd/gsd-core engines`, never copied here.
- Codex sandbox: the workspace-write writable roots and protected paths are defined at https://developers.openai.com/codex/agent-approvals-security.
