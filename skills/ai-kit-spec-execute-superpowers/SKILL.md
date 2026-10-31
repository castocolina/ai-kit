---
name: ai-kit-spec-execute-superpowers
description: Resolves a live-quota-checked (runtime, model) pair for each task of a superpowers implementation plan and injects it at superpowers:subagent-driven-development's implementer-dispatch point, leaving that harness's TDD enforcement, agent identity/resume, task review, fix-loop and final review intact. Use when ai-kit-spec-execute detects a superpowers-generated plan (docs/superpowers/plans/*.md) being run under subagent-driven-development and needs a pair for a task, or when asked to execute or run a superpowers plan that way. Not for superpowers:executing-plans, which runs every task inline and has no subagent-dispatch point to inject into.
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

- **Never** persist `$EXCLUDED_KEYS_JSON` wholesale as `excluded_keys`: a same-wave `"quota"`
  exclusion would read as permanent (Step 2; `references/state-management.md`).
- **Never** call `resolve-injection` with `--exclude-keys-json` alone, omitting
  `--excluded-reasons-json`: prior-wave permanent reasons then read `"no_usable_dispatch"` (Step 2).
- **Never** read `key`/`runtime` off an injection result before checking `$INJECTION_MODE`:
  `quota_exhausted` and `no_candidate` carry neither (Step 2).
- **Never** put `$INJECTION_RUNTIME` into an exclusion set: a runtime id is not a ladder key (Step 3).
- **Never** fold `$ESCALATION_EXCLUDE_JSON` into `$EXCLUDED_KEYS_JSON`: it marks healthy,
  never-tried candidates excluded only for a capability floor (Step 3; `references/escalation.md`).
- **Never** let a fix-loop round overwrite `$REPORT_FILE`: `REPORT_MODE` is `write` at most once per
  task, `append` after, and every prompt after the first says APPEND (Step 3).
- **Never** parse the implementer status out of `$REPORT_FILE`, only from
  `$DISPATCH_RESULT_JSON["stdout"]` (Step 3).
- **Never switch harness, provider or model** after a failed or unusable run.
  **Never re-resolve to another candidate after a failed dispatch.** Do not re-run `resolve-injection`
  to recover; re-dispatch only the persisted injection after its one-shot wait (Step 3; ai-kit-cross-ai sections 6 and 8).
- **Never** run `trust-local` without the user's explicit yes, or ask twice in one run (Step 2).

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

First probe that `superpowers:subagent-driven-development` loads through the host's skill
mechanism; if not, STOP and tell the user (nothing to delegate to). Follow its own Setup exactly
(workspace, ledger, plan read, pre-flight scan). `$CWD`, `$PLAN_FILE`, `$TASK_N`, and `$BRIEF_FILE`
are values it already holds at each task's implementer dispatch — read them, never invent them.

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

Step 2 runs once per task, before its first dispatch, and again only for a resume without a pinned `injection_json`, a trust-local yes, or the Rounds 4–5 re-resolution (Step 3). A restored `injection_json` is pinned: it re-dispatches unchanged at any `$FIX_ROUND`. Fix rounds 1–3 reuse the task's `$INJECTION_JSON` unchanged.

**Resume check — before any resolution** (a re-invoke starts here with no memory; the task-paths
block printed `RESUME_FOUND`). `RESUME_FOUND=0`: run "Seed a new task" in
`references/state-management.md` (never from the quota-wake prompt; it keeps an already-seeded task's `$FIX_ROUND` and anchor), then
the rest of this step. `RESUME_FOUND=1`: run that file's "Restore" script. If the file held
`injection_json`, it prints `INJECTION_MODE`, `INJECTION_KEY` and `INJECTION_RUNTIME`: go straight
to Step 3, reusing the existing `$PROMPT_FILE` (switch only its WRITE sentence to APPEND; never
recompose the objective); otherwise run the rest of this step on the restored values. **Either branch, with a restored `$FIX_ROUND >= 4` and no pinned `injection_json`:** that plain result (any mode) is only the source of `ladder_keys`: never act on its mode or dispatch it; before any dispatch, compute the floor from the restored `$ESCALATION_ANCHOR_KEY` and run `references/escalation.md`'s resolve block (Step 3). Step 3 deletes a finished task's file on a successful dispatch; an owner restarting the plan deletes any other.

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
  --excluded-reasons-json "$EXCLUDED_REASONS_JSON")"
INJECTION_RC=$?
[ "$INJECTION_RC" -eq 0 ] || { echo "resolve-injection exit $INJECTION_RC"; exit "$INJECTION_RC"; }
printf '%s' "$INJECTION_JSON" > "$RUN_DIR/INJECTION_JSON.json"
INJECTION_MODE="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["mode"])' "$INJECTION_JSON")"
for n in BRIEF_FILE INJECTION_MODE; do printf '%s=%s\n' "$n" "${!n}"; done | tee -a "$SCALARS"
```

`--excluded-reasons-json` always gets the merge of `$PRIOR_REASONS_JSON` and `$WAVE_REASONS_JSON`,
never `$WAVE_REASONS_JSON` alone.

**Non-zero exit or an untrusted-project-config line** (`resolve-injection exit 2`; stderr
`ai-kit-spec: ignoring untrusted project-local config <path>; ...`): **MANDATORY: read
[`references/resolution-stops.md`](references/resolution-stops.md)** for the stop, the one-per-run
`trust-local` ask and the re-run. Never run `trust-local` unasked.

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

- **`no_candidate`, `quota_exhausted`** — **MANDATORY: read `references/resolution-stops.md`** (reason-to-fix
  list, the `any_quota_recoverable` gate, the resumable-state write); both STOP this wave and
  schedule nothing. Do NOT load it for any other mode.
- **Otherwise** `$INJECTION_JSON` carries `mode`, `key`, `runtime`, `model`, `ladder_keys`, and for
  `external_cli` also `effort`, `service_tier`. Go to Step 3 (a restored `$FIX_ROUND >= 4` with no pinned
  `injection_json`: dispatch only the result of `references/escalation.md`'s resolve block, never this pick).

## Step 3: Dispatch the implementer — apply the injection

The (runtime, model) pair contract and the native-versus-subprocess routing are defined in `ai-kit-spec-config` and `ai-kit-spec-review`; `$INJECTION_MODE` is that routing's result, never re-decided here.

**At the start of every fix round, in either mode, increment `$FIX_ROUND` and set
`ESCALATION_ANCHOR_KEY="$LAST_DISPATCHED_KEY"` first** (block below; new rounds only, never on a resume,
a re-invoke that kept its scalars or a Step-2 re-entry, which keep the round and anchor, yet at 4 or more still take the floor below). Rounds 1–3 keep `$INJECTION_JSON` and skip Step 2. A failed dispatch gets no same-round re-dispatch.

**Rounds 4–5 capability escalation (`external_cli`, and `native` on every host but Claude Code).**
At `$FIX_ROUND >= 4` after the increment, or restored at 4 or more by a resume with no pinned
`injection_json` (a pin always re-dispatches unchanged), subagent-driven-development requires "a MORE
CAPABLE model". **MANDATORY: read `references/escalation.md` in full before composing or dispatching
the round and before computing `$ESCALATION_EXCLUDE_JSON`**: the floor is relative to
`$ESCALATION_ANCHOR_KEY` (the dispatch that got stuck), never to the key Step 2 just picked, and is
applied before the round's dispatch, never after a failed one. An empty anchor, or one missing from
`ladder_keys`, dispatches nothing: STOP and ask the owner ("An empty or unknown anchor never
dispatches"). Do NOT load it at rounds 1–3.

```bash
FIX_ROUND=$((FIX_ROUND + 1)); ESCALATION_ANCHOR_KEY="$LAST_DISPATCHED_KEY"
printf 'FIX_ROUND=%s\nESCALATION_ANCHOR_KEY=%s\n' "$FIX_ROUND" "$ESCALATION_ANCHOR_KEY" | tee -a "$SCALARS"
```

**Clear the resume state when a dispatch succeeds** (only after it, never before dispatching: a native dispatch that returned, or an
`external_cli` one classified `"ok"`), so a re-invoke never restores a stale round or pinned
injection; a later stop rewrites it from the live values. It removes only this task's own file,
never the runner's lane file:

```bash
if [ -n "$RESUME_STATE_PATH" ]; then rm -f -- "$RESUME_STATE_PATH"; fi
```

**`mode == "native"`:** this host's own subagent mechanism, unchanged. On Claude Code, pass `model` as
the `Agent` tool's `model` parameter (omit it when empty) and record the returned agent identity;
fix-loop rounds 1–3 resume that same agent. Its round 4/5 model bump follows that skill's own rule (a
more capable model) and happens before the round's dispatch, after a review returned findings. On any other host the native case is
only the session default, so omit `model` and let the host use its current session. Either way, after
the dispatch run `printf 'LAST_DISPATCHED_KEY=%s\n' "$INJECTION_KEY" | tee -a "$SCALARS"` and clear the
resume state. A non-Claude native dispatch cannot raise its own model, so rounds 4–5 take the ladder escalation above. A failed native dispatch (for example an `Agent` model error) is
subagent-driven-development's own (NEVER index); stop for the owner when that skill has no route.

**`mode == "external_cli"`:** a subprocess through the supervised runner. A CLI process exits when
done, so there is no live agent to resume. Every dispatch, first attempt and every fix round,
uses subagent-driven-development's documented fallback: a fresh implementer carrying the brief
path, report-file path and findings, with the report file as the persistent memory.

**MANDATORY: read [`references/dispatch-external-cli.md`](references/dispatch-external-cli.md) in
full before the first `dispatch-task` of a task and again before acting on its result.** Do NOT
load it for `mode == "native"`. It holds the artifact setup, Compose, Status contract and
Dispatch steps, the **Classify** step (`ok`, `quota`, `real_error`) and, inside `quota`, the
**Schedule-or-stop** step. What each outcome comes to:

- **`"ok"`** — clear the resume state (block above), read the status from `stdout` only, and
  continue with subagent-driven-development's "2. Handle the report".
- **`"quota"`** — only `RETURNCODE` 75 with whole-number `retry_after_s` and `cycle` gets one
  one-shot wait and a re-dispatch of the same injection (Schedule-or-stop); every `RETURNCODE` 69
  (`stopped=hard-waits`, `stopped=cap`, or tokenless), a bare 75 and any other quota class are owner stops.
- **`"real_error"`** — stop for the owner with the pinned state written.

**Exec confinement** (reasoning: `references/design-notes.md`). Codex runs under
`--codex-sandbox workspace-write` (writes stay in the target dir plus `/tmp` and `$TMPDIR`; `.git`
writes unverified). Every other exec target has full permissions, and its stay-in-the-target-dir
guidance is not a boundary. `claude` is review-only and never runs here. pi exec is verified by the
runner's hermetic self-test only and live verification is still open (stderr prints that note); a copilot target gets a similar note:
unverified error rows, all tools allowed, the task prompt visible on argv. **Node:** subprocess
dispatch needs Node 24 (GSD's declared floor, `@opengsd/gsd-core` 1.17.0 `engines.node >=24.0.0` per
`.planning/phases/18.1-one-runtime-model/18.1-RESEARCH.md:231`, not declared in this tree; older untested).
The runner fails closed as `dispatch_unavailable` (a `real_error` stop) only when `node` is absent; an older Node may crash, and that crash is a `real_error` of the pair, never a reason to switch pairs.

## Step 4: Task review, fix loop, final review — unaffected

Whichever mode Step 3 used, subagent-driven-development's "3. Review the task", "4. The fix loop"
(rounds 1–5), and the final whole-branch review run unmodified on `$REPORT_FILE` and the real
commits; fix rounds after successful work are separate from dispatch-failure handling. This
skill's scope ends at Step 3 and never touches review, adjudication, or the ledger.

## Close the session wake

When the job ends (the final whole-branch review finished, which the caller runs, or a stop ended the
run) and only when `WAKE_OWNED=1`, run the close block in `references/session-wake.md` (never on the
one-shot wait branch of Schedule-or-stop). When `WAKE_OWNED=0`, call nothing.
