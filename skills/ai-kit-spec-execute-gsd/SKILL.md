---
name: ai-kit-spec-execute-gsd
description: "Resolves the best available (runtime, model) pair for a GSD (Get Sh*t Done) phase, prepares GSD's own .planning/config.json (a native-tier pin of runtime plus model_profile_overrides, or workflow.cross_ai_command naming the project's supervised runner), then invokes GSD's own /gsd-execute-phase skill directly to perform the actual execution -- never subprocess-dispatches GSD itself. Use when (1) ai-kit-spec-execute detects a GSD-managed plan (.planning/ directory present) and needs to run a phase with a resolved pair, (2) a GSD phase needs a native-tier model pin (runtime + model_profile_overrides) written before execution, or (3) a GSD plan is opted into cross-AI delegation (frontmatter cross_ai true) and needs workflow.cross_ai_command wired to the project's supervised runner before /gsd-execute-phase runs."
---

# ai-kit-spec-execute-gsd

## NEVER

- **Never subprocess-dispatch GSD itself** — this skill only prepares `.planning/config.json` and
  then hands the phase to GSD's own `/gsd-execute-phase`.
- **Never hand-edit `.planning/config.json`** — every write goes through the shim, which calls
  gsd-tools' own `config-set` (validation, locking, workstream-aware path) and records ownership.
- **Never write `workflow.cross_ai_command` without checking the plan's `cross_ai: true`
  frontmatter**, and never put the raw vendor CLI string there — the hook names the project's own
  supervised runner (Step 2), never a raw vendor CLI string. A custom entry (a `command` and no
  `runtime`) is the one exception to "every subprocess runs through the runner": it runs through
  the fixed-argv custom launcher on the same supervision core, and only as a reviewer, so it is
  never a GSD hook: with `purpose = "execute"` `resolve-dispatch` exits 2, otherwise exec mode
  skips it as `review_only`.
- **Never run `trust-local` without an explicit yes**, and never ask twice in one wave.
- **Never parse an empty result** — exit 2 from any shim call means STOP and relay stderr.

**Trust model.** Project-local `.aikit/review-spec.toml` entries count only after `trust-local`.
The gsd-core tooling does not have that gate: like GSD's own launcher, the shim runs the first
`gsd-tools.cjs` it finds, project-local first (`<root>/gsd-core`, `<root>/.claude/gsd-core`,
`<root>/.codex/gsd-core`, where root is `RUNTIME_DIR` or the git top level), with `node` and no
trust step. So running this skill in a cloned repo executes that repo's JavaScript, the same as
running its GSD commands; the host's own folder trust is the only gate. `resolve-dispatch` and
the `*-workflow-keys` calls print `ai-kit: gsd-core <version> at <path>` on stderr; if that path
is inside a repo you have not reviewed, stop and check it.

**Host-specific steps.** `CronCreate` (Step 1's quota wake) and the `Skill` tool (Step 3) are
Claude Code tools. On another host, use its own scheduler and skill-invocation mechanism, or tell
the user to resume or run `/gsd-execute-phase` by hand.

## Step 0: Resolve the shim path

This skill is not guaranteed a `CLAUDE_PLUGIN_ROOT` — take the FIRST existing of, in order (same
pattern `ai-kit-spec-review/SKILL.md` uses for its own `ai-kit-spec.py`), and resolve
`ai-kit-spec-review`'s own shim in the SAME call:

```bash
for d in "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/ai-kit-spec-execute-gsd}" \
         "$HOME/.claude/skills/ai-kit-spec-execute-gsd" \
         "$(dirname "<absolute path to THIS SKILL.md>")"; do
  [ -d "$d" ] && { GSD_SKILL_DIR="$d"; break; }
done
GSD_SHIM="$GSD_SKILL_DIR/ai-kit-spec-gsd.py"
for d in "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/ai-kit-spec-review}" \
         "$HOME/.claude/skills/ai-kit-spec-review" \
         "$(dirname "$GSD_SKILL_DIR")/ai-kit-spec-review"; do
  [ -d "$d" ] && { REVIEW_SPEC_SKILL_DIR="$d"; break; }
done
TOOLS_PY="$REVIEW_SPEC_SKILL_DIR/ai-kit-spec.py"
for d in "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/ai-kit-gsd-curated-config}" \
         "$HOME/.claude/skills/ai-kit-gsd-curated-config" \
         "$(dirname "$GSD_SKILL_DIR")/ai-kit-gsd-curated-config"; do
  [ -d "$d" ] && { CURATED_SKILL_DIR="$d"; break; }
done
CURATED_PY="$CURATED_SKILL_DIR/ai-kit-gsd-curated-config.py"
printf 'GSD_SHIM=%s\nTOOLS_PY=%s\nCURATED_PY=%s\n' "$GSD_SHIM" "$TOOLS_PY" "$CURATED_PY"
```

**Record all three printed lines as this wave's own literal values.** Every later step's
`python3 $GSD_SHIM <subcommand> ...` invocation uses this resolved `$GSD_SHIM` path — never a bare
`python3 -m ai_kit_spec_gsd.cli`. `$TOOLS_PY` resolves `ai-kit-spec-review`'s own shim for its
`cache-path --kind quota` subcommand. `$CURATED_PY` resolves `ai-kit-gsd-curated-config`'s shim,
which Step 2 uses to render or upgrade the project runner.

**Every separate `Bash` tool call in this harness starts a fresh shell** — a variable set in one
call is gone by the next. Steps 1–3 below are written as separate `Bash` calls; every `$VAR`
denotes the literal value most recently captured for it via a `printf`, re-substituted verbatim
into every later command — never an actual persisting shell variable across a call boundary.

`$CWD`, `$PHASE_ID`, and `$PHASE_PROMPT_FILE` (bound in Step 1) are **inputs this skill is invoked
WITH, never values it invents or infers.** If this skill is ever invoked without `cwd` and
`phase_id`, STOP and ask the user rather than guessing.

## Step 1: Resolve the dispatch decision via the CLI entrypoint

**One `Bash` call:**

```bash
CWD="<this skill's own entry-precondition project root -- supplied by the caller>"
PHASE_ID="<this skill's own entry-precondition phase id -- supplied by the caller>"
PHASE_PROMPT_FILE="<this phase's own prompt/context file path -- located via CWD/PHASE_ID>"
GSD_CONFIG_PATH="$(python3 "$GSD_SHIM" config-path --cwd "$CWD")" || exit 2  # honors workstreams
RESULT_JSON="$(python3 "$GSD_SHIM" resolve-dispatch --cwd "$CWD" \
  --target-dir "$CWD" \
  --quota-path "$(python3 "$TOOLS_PY" cache-path --kind quota)" \
  --phase-prompt-file "$PHASE_PROMPT_FILE")"
[ $? -eq 2 ] && exit 2  # exit 1 is write_failed, which still prints JSON
RUN_ID="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["run_id"])' <<< "$RESULT_JSON")"
RESULT_MODE="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["mode"])' <<< "$RESULT_JSON")"
RESULT_KEY="$(python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("key") or "")' <<< "$RESULT_JSON")"
RESULT_RUNTIME="$(python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("runtime") or "")' <<< "$RESULT_JSON")"
RESULT_PROVENANCE="$(python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("provenance") or "")' <<< "$RESULT_JSON")"
RESULT_REASON="$(python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("reason") or "")' <<< "$RESULT_JSON")"
RESULT_MESSAGE="$(python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("message") or "")' <<< "$RESULT_JSON")"
RESULT_CROSS_AI_COMMAND="$(python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("cross_ai_command") or "")' <<< "$RESULT_JSON")"
RESULT_MODEL="$(python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("model") or "")' <<< "$RESULT_JSON")"
printf 'CWD=%s\nPHASE_ID=%s\nPHASE_PROMPT_FILE=%s\nGSD_CONFIG_PATH=%s\nRUN_ID=%s\nRESULT_MODE=%s\nRESULT_KEY=%s\nRESULT_RUNTIME=%s\nRESULT_MODEL=%s\nRESULT_PROVENANCE=%s\nRESULT_REASON=%s\nRESULT_MESSAGE=%s\nRESULT_CROSS_AI_COMMAND=%s\n' \
  "$CWD" "$PHASE_ID" "$PHASE_PROMPT_FILE" "$GSD_CONFIG_PATH" "$RUN_ID" "$RESULT_MODE" \
  "$RESULT_KEY" "$RESULT_RUNTIME" "$RESULT_MODEL" "$RESULT_PROVENANCE" "$RESULT_REASON" "$RESULT_MESSAGE" \
  "$RESULT_CROSS_AI_COMMAND"
printf 'RESULT_JSON=%s\n' "$(python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))' <<< "$RESULT_JSON")"
```

**Record every line of that trailing `printf`'s output as this wave's own literal values.**

**If the call exits 2, STOP and relay its stderr verbatim** — nothing was written and there is no
JSON to parse. The causes: `node` is not on PATH, no `gsd-tools.cjs` was found (project-local
gsd-core first, then the host homes), gsd-tools could not resolve a config path for `$CWD`, a
malformed `review-spec.toml`, or an entry with `purpose = "execute"` that can never execute (a
custom `command` entry, grok, or claude with a model outside its alias set).

**If `resolve-dispatch` stderr prints `ignoring untrusted project-local config`**, this decision
was made from the global config only, and a `native_tier` result may already have written it.
Relay the line verbatim, show `python3 "$TOOLS_PY" trust-local --cwd "$CWD" --show` (each local
reviewer's argv, the prompt as `<prompt>`; writes nothing), and ask once. On yes, run
`python3 "$TOOLS_PY" trust-local --cwd "$CWD"` and **re-run this whole Step 1 (new `run_id`)**
before Step 2 — the re-run overwrites only adapter-owned values. On no, continue with this
result and do not ask again this wave. Never trust on the user's behalf.

If `mode == "write_failed"` (exit 1): a `gsd-tools config-set` failed mid-write. Keys applied
earlier in that attempt were reverted in reverse order; `reverted` lists them, and
`revert_failed` lists any whose revert itself failed — those keys still hold the new value and
need a hand fix. Print the `RESULT_JSON=` line captured above to the user and STOP — do not
proceed to Step 2/3.

If `mode == "fallback_notice"` and `reason == "malformed_config"`, print the message and STOP — do
not proceed to Step 2/3 at all.

If `mode == "fallback_notice"` and `reason == "quota_exhausted"`: this is a genuine, time-bound
exhaustion discovered before any handoff to GSD — write resumable state and schedule an hourly
`CronCreate` wake (below), then STOP for this wave (do not proceed to Step 3 — GSD's own default
would run with no configuration change, which the caller may prefer to defer rather than accept
immediately):

```bash
PROJECT_KEY="$(python3 -c "import hashlib,sys; print(hashlib.sha256(sys.argv[1].encode()).hexdigest()[:12])" "$CWD")"
RESUME_STATE_PATH="$(dirname "$(python3 "$TOOLS_PY" cache-path --kind quota)")/gsd-resume-${PROJECT_KEY}-${PHASE_ID}.json"
STATE_JSON="$(python3 -c '
import json, sys
print(json.dumps({"framework": "gsd", "project_path": sys.argv[1],
                   "config_path": sys.argv[2], "phase_id": sys.argv[3]}))' \
  "$CWD" "$GSD_CONFIG_PATH" "$PHASE_ID")"
python3 "$GSD_SHIM" write-resumable-state --path "$RESUME_STATE_PATH" --state-json "$STATE_JSON"
```

Then schedule a `CronCreate` job: hourly interval, prompt `"re-check quota via probe-quota and,
once restored, resume ai-kit-spec-execute-gsd from $RESUME_STATE_PATH"`. `CronCreate` jobs are
session-scoped (design spec §10) — they vanish if the session exits, only fire while the session
is idle, and recurring jobs auto-expire after 7 days; tell the user this explicitly.

Every other `fallback_notice` reason (`no_configured_candidate`, `all_candidates_context_rejected`,
`no_usable_dispatch` — no candidate has a native GSD tier or a CLI with an execute builder, so
the execute-CLI screen skipped them all with a stderr warning each; `key` names the top one) is
permanent, non-time-bound — print the message, run the mode-transition
cleanup below, and proceed to Step 3 with no candidate resolved (GSD's own currently-active
default runs unmodified). Never schedule a wake for these.

## Step 2: Act on the dispatch mode

A reviewer or executor is a (runtime, model) pair. Each call runs it natively when its runtime is the current host and the host can select that model; otherwise it runs as a subprocess through the supervised runner. An entry with neither a runtime nor a model is the session default, which the host always runs natively. Today only Claude Code selects a model per call (its sonnet, opus, haiku and fable aliases); every other host runs only its session default natively.

GSD's `native_tier` is the exception: a session default or a claude alias becomes a tier pin
that GSD's own runtime runs, decided without a host check (D-25).

**Mindset before writing anything here:**
- Resolve dispatch mode fresh every run, never reuse a cached decision — quota state, installed
  CLIs, and per-plan `cross_ai: true` opt-in can all change between runs, and a stale cached mode
  would silently dispatch through the wrong path.
- Before writing `workflow.cross_ai_command`, ask yourself: is this plan's frontmatter actually
  opted in (`cross_ai: true`)? A workflow-level write alone never makes GSD delegate to cross-AI
  (see the explicit scope-boundary note below) — writing the hook without checking the plan's own
  opt-in would silently misconfigure a plan the user never asked to run cross-AI.
- Run the mode-transition cleanup even when this run resolves a non-cross-AI mode — a stale
  adapter-owned hook from a PRIOR run must never keep dispatching cross-AI just because THIS run
  didn't touch it.

- `native_tier` (either `written` value): GSD's own runtime runs the pair as a tier pin (no host
  check, D-25), so the resolved mode is NOT cross-AI — run the mode-transition cleanup below
  before proceeding to Step 3, in case a PRIOR run of this project left an adapter-owned cross-AI
  hook active that this run's resolution superseded.
  `written=False`/`provenance="existing_gsd_config"`: GSD's own config already carries a genuine
  (non-adapter-owned) value at `model_profile_overrides[runtime][tier]` — a real user pin, honored
  as-is, nothing further to write.
  `written=True`/`provenance="resolved_candidate"`: the CLI call already wrote the pin, taking a
  per-run backup first — `model_profile` for a claude tier, else `runtime` (if needed) and
  `model_profile_overrides[runtime][tier]`.
- `cross_ai_hook`: the pair runs as a subprocess through the project's own supervised runner.
  **Write GSD's own real, confirmed `workflow.*` keys** (Task 1 finding 1) in one
  `write-workflow-keys` call (`--cwd "$CWD"`, `--run-id "$RUN_ID"` — the same `run_id` from
  Step 1), without threading a config snapshot between calls. Exit 1 means a key failed and
  earlier keys from that call were reverted (any in `revert_failed` still hold the new value);
  exit 2 means gsd-tools could not be resolved, as in Step 1. Show the output to the user and STOP.
  A model id the unquoted hook cannot carry comes back from Step 1 as `fallback_notice` with
  reason `unsafe_hook_token` instead of a broken hook string. That includes a cursor model id
  carrying brackets (`model[effort=high]`): GSD globs the unquoted hook, so cursor effort/fast
  brackets are argv-only (ai-kit's own Python dispatch), never hook-capable.

  **`workflow.cross_ai_command` is NOT the raw external CLI command — it names the project's own
  supervised runner**, and the guidance file is tracked next to it under `.planning/scripts/`.
  GSD's own `cross_ai_delegation` step keeps doing its own real, unmodified bookkeeping (writing
  the plan's SUMMARY.md, updating STATE.md/ROADMAP.md, marking the plan handled) and still owns
  the piping/capture/retry mechanics — this only changes WHAT command that hook names, not who
  calls it or when. The runner is rendered or upgraded here, so the hook works without a prior
  curated-config apply:
  ```bash
  # RESULT_MODEL is the value Step 1 printed; never re-parse RESULT_JSON here.
  # NO manual quoting around the stored command's tokens -- this is deliberate, required by how
  # GSD expands this value. Read only if you need to know why:
  # references/dispatch-notes.md#why-no-manual-quoting-around-workflowcross_ai_commands-values
  # The producer runs first and its status is checked before anything is written: a failure or
  # empty guidance must never reach ensure-runner, and a not-ready runner writes nothing.
  GUIDANCE="$(python3 "$GSD_SHIM" print-dispatch-guidance --runtime "$RESULT_RUNTIME" --model "$RESULT_MODEL")"
  GUIDANCE_RC=$?
  if [ "$GUIDANCE_RC" -ne 0 ] || [ -z "$GUIDANCE" ] || [ ! -f "$CURATED_PY" ]; then
    echo "ai-kit-spec-execute-gsd: dispatch guidance unavailable (exit $GUIDANCE_RC); nothing written"
    CLEAR="$(python3 "$GSD_SHIM" clear-workflow-keys --cwd "$CWD" --run-id "$RUN_ID" \
      --key cross_ai_command --key cross_ai_execution --key cross_ai_timeout)"
    CLEAR_RC=$?
    if [ "$CLEAR_RC" -ne 0 ] || printf '%s' "$CLEAR" | grep -q 'revert_failed'; then
      echo "$CLEAR"
      echo "ai-kit-spec-execute-gsd: cleanup failed; an old hook may still be active"
      exit 1
    fi
    RESULT_MODE="fallback_notice"
  else
    mkdir -p "$CWD/tmp"
    ENSURE_FILE="$(mktemp "$CWD/tmp/ensure.XXXXXX")"
    printf '%s\n' "$GUIDANCE" | python3 "$CURATED_PY" ensure-runner --cwd "$CWD" --guidance-file - > "$ENSURE_FILE"
    ENSURE_RC=${PIPESTATUS[1]}
    ENSURE="$(cat "$ENSURE_FILE")"
    rm -f "$ENSURE_FILE"
    if [ "$ENSURE_RC" -eq 0 ]; then
      WRITE="$(python3 "$GSD_SHIM" write-workflow-keys --cwd "$CWD" --run-id "$RUN_ID" \
        --set "cross_ai_command=$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$RESULT_CROSS_AI_COMMAND")" \
        --set cross_ai_execution=true \
        --set cross_ai_timeout=900)"
      WRITE_RC=$?
      if [ "$WRITE_RC" -ne 0 ]; then
        echo "$WRITE"
        echo "ai-kit-spec-execute-gsd: writing the hook failed (exit $WRITE_RC)"
        exit 1
      fi
    else
      echo "ai-kit-spec-execute-gsd: the project runner is not ready (exit $ENSURE_RC); nothing written"
      echo "$ENSURE"
      CLEAR="$(python3 "$GSD_SHIM" clear-workflow-keys --cwd "$CWD" --run-id "$RUN_ID" \
        --key cross_ai_command --key cross_ai_execution --key cross_ai_timeout)"
      CLEAR_RC=$?
      if [ "$CLEAR_RC" -ne 0 ] || printf '%s' "$CLEAR" | grep -q 'revert_failed'; then
        echo "$CLEAR"
        echo "ai-kit-spec-execute-gsd: cleanup failed; an old hook may still be active"
        exit 1
      fi
      RESULT_MODE="fallback_notice"
    fi
  fi
  printf 'RESULT_MODE=%s\n' "$RESULT_MODE"
  ```
  A non-zero producer exit, empty guidance, a missing curated shim, or an `ensure-runner` exit of
  1 (not ready: a user-edited runner on an older or foreign template gets a `.new` file plus the
  printed notes) or 2 (error)
  writes nothing: show the printed notes to the user and continue as `fallback_notice` only after
  the cleanup call above exits 0. If that cleanup exits non-zero, or its output names keys in
  `revert_failed`, STOP and show it: an old hook may still be active. Exit 0 writes the hook and
  the 900-second timeout. The `RESULT_MODE=` line this block prints replaces the Step 1 value for
  every later step, so Step 3 follows the mode that was actually set up.

  **Hook setup.** This skill renders or upgrades the runner and the guidance file through
  curated-config `ensure-runner`; a user-edited runner is never overwritten: on the current
  template it is kept and ready, and when an upgrade is pending it gets a `.new` file instead,
  with the printed notes. The guidance file goes before the prompt and the runner's own
  preamble is off, so nothing is said twice. The hook stays unquoted because GSD expands the stored
  value by word splitting and pathname expansion, never as shell syntax — see `references/dispatch-notes.md`.

  **Exec confinement.** Codex runs under `--codex-sandbox workspace-write`: the runner uses
  `--sandbox workspace-write` instead of the bypass, so writes stay inside the project dir plus
  `/tmp` and `$TMPDIR`, which workspace-write always allows. Whether that sandbox also allows
  writes inside `.git` is unverified. Every other exec target runs with full permissions; the
  guidance file tells it to write only inside the project dir, and that prose is guidance, not a
  boundary. `claude` is review-only and never a hook target. pi exec uses the runner's pi formula,
  verified by its hermetic self-test only; live verification is Phase 22, and stderr prints that
  note before the hook is written.

  **Node.** Subprocess dispatch needs Node 24 (GSD's declared floor); older versions untested.
  The hook starts with `node .planning/scripts/cross-ai.mjs`, so without Node it cannot launch and
  never reaches the runner's `dispatch_unavailable` path. Step 1 already stops when `node` is not
  on PATH. If Node disappears between Step 1 and the hook, do not claim a native fallback: run the
  mode-transition cleanup below and, only when it exits 0, hand the phase to GSD with no hook; if
  the cleanup fails, STOP and show its output.

  **Explicit scope boundary (Global Constraints): this workflow-level write alone does NOT make
  GSD delegate to cross-AI.** Real GSD also requires the TARGET PLAN's own frontmatter to carry
  `cross_ai: true` (Task 1 finding 1 — activation is per-plan). Check the plan file(s) covering
  this phase for that frontmatter key; if any is missing it, print an explicit warning to the user
  ("workflow.cross_ai_command is configured, but plan <path> does not have `cross_ai: true` in its
  frontmatter — GSD will NOT delegate this plan to cross-AI without it; add it by hand, or GSD's
  own currently-active native default will run for this plan instead") — never silently proceed as
  if the workflow write alone were sufficient.
- `fallback_notice`: already handled in Step 1 (either a probe-time `quota_exhausted` STOP, or one
  of the three permanent reasons that fall through to here). Run the mode-transition cleanup below.

**Mode-transition cleanup** — run this whenever the resolved `mode` is `native_tier` or
`fallback_notice` (i.e. NOT `cross_ai_hook`), BEFORE proceeding to Step 3, so a stale adapter-owned
cross-AI hook from a PRIOR run never stays silently active once a LATER run resolves a different
dispatch mode. Never touches a value the user set by hand (`clear-workflow-keys` is a no-op unless
the key is adapter-owned):

```bash
python3 "$GSD_SHIM" clear-workflow-keys --cwd "$CWD" --run-id "$RUN_ID" \
  --key cross_ai_command --key cross_ai_execution --key cross_ai_timeout
```

## Step 3: Prepare confirmed-only tooling guidance, then invoke GSD's own `/gsd-execute-phase` skill

Resolve the runtime to prepare tooling guidance for:
- `native_tier`: use `--runtime "$RESULT_RUNTIME"` (the adapter fills the native Claude alias).
- `cross_ai_hook`: use `--runtime "$RESULT_RUNTIME"` directly (the runtime the hook runs).
- `fallback_notice`: omit `--runtime` entirely (no candidate was resolved — generic detection only).

```bash
if [ "$RESULT_MODE" = "fallback_notice" ]; then
  CLI_ARGS=()
else
  CLI_ARGS=(--runtime "$RESULT_RUNTIME")
fi
GUIDANCE="$(python3 "$GSD_SHIM" prepare-tooling "${CLI_ARGS[@]}" --target-dir "$CWD")"
GUIDANCE_RC=$?
if [ "$GUIDANCE_RC" -ne 0 ] || [ -z "$GUIDANCE" ]; then
  echo "ai-kit-spec-execute-gsd: prepare-tooling failed (exit $GUIDANCE_RC); phase file untouched"
  exit 2
fi
START="<!-- ai-kit-spec-execute-gsd:tooling-guidance:start -->"
END="<!-- ai-kit-spec-execute-gsd:tooling-guidance:end -->"
python3 -c 'import pathlib,sys
p,s,e,g=sys.argv[1:]
t=pathlib.Path(p).read_text()
b,a=(t.find(s),t.find(e))
if b!=-1 and a!=-1:
    t=t[:b]+t[a+len(e):]
elif b!=-1:
    sys.exit(2)
pathlib.Path(p).write_text(t.rstrip("\n")+"\n\n"+s+"\n"+g+"\n"+e+"\n")' \
  "$PHASE_PROMPT_FILE" "$START" "$END" "$GUIDANCE" || {
  echo "ai-kit-spec-execute-gsd: guidance block has no end marker; phase file untouched"
  exit 2
}
```

This `prepare-tooling` subcommand (Task 4) runs `detect_tool_availability()`,
`resolve_agents_tooling_path()`, then `probe_codegraph(cli)` (report-only, 15 s timeout; skipped
when `--runtime` is omitted). When codegraph is missing or unhealthy, the shim prints the exact install
command on stderr — relay that line to the user verbatim and never run it on their behalf
(installing is the user's call through their own tooling). Only when the probe finds codegraph
registered and not known unhealthy (codex health is unknown, so it gets a stderr note) does it run
`run_codegraph_index(target_dir)` (`codegraph sync`, then `codegraph init` on failure), per design
spec §9's ordering guarantee. Writing the guidance into the phase file itself (idempotently,
marker-guarded) means it reaches GSD's own execution regardless of which dispatch mode Step 2
chose — GSD's own `/gsd-execute-phase` skill reads this same phase content whether it's running a
native subagent or delegating through `cross_ai_command`.

**`RESULT_MODE = "cross_ai_hook"` needs no separate guidance-append step here anymore**: Step 2
writes the guidance into the tracked file the hook places before the prompt. Read only if you
need the history of why this step used to append guidance here and why that changed:
`references/dispatch-notes.md#history-the-guidance-file-supersedes-the-old-guidance-append-step`.

**Then invoke GSD's own `/gsd-execute-phase` skill directly, via the `Skill` tool, for `$PHASE_ID`
— this is the entire remaining job of this skill.** There is no subprocess to run, no stdout to
capture, no heartbeat to route (Task 1 finding 3) — GSD's own workflow performs the actual
dispatch, heartbeating, and completion end-to-end in-session, using whichever mechanism Step 2 just
configured. Concretely, the executing agent calls the `Skill` tool with the skill name confirmed
by checking, in order: `<project>/.claude/commands/gsd-execute-phase.md` (GSD is installed per
project), then `$HOME/.claude/skills/gsd-execute-phase/SKILL.md` — use whichever exists first and
read its frontmatter for the skill name (typically `gsd-execute-phase`), passing `$PHASE_ID` as its
argument. This is a tool call the agent makes directly, not a shell command this document can show
as a `bash` fence. After that call returns, this skill's own job is complete; any dispatch failure
GSD's own skill surfaces (including its own cross-AI retry/skip/abort UI) is GSD's problem to
handle and report, not this adapter's.

If the `Skill` tool call itself fails to resolve — e.g. `gsd-execute-phase` isn't installed or its
definition is missing/unreadable — that is a genuine environment problem, not a dispatch failure:
STOP, do not retry, and report the exact resolution error to the user along with both paths
checked: `<project>/.claude/commands/gsd-execute-phase.md` and
`$HOME/.claude/skills/gsd-execute-phase/SKILL.md` so they can reinstall or repair GSD.
