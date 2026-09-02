---
name: ai-kit-spec-execute-gsd
description: Resolves the best available model/CLI for a GSD (Get Sh*t Done) phase, prepares GSD's own .planning/config.json (native runtime + model_profile_overrides, or workflow.cross_ai_command), then invokes GSD's own /gsd-execute-phase skill directly to perform the actual execution -- never subprocess-dispatches GSD itself. Use when ai-kit-spec-execute detects a GSD-managed plan (.planning/ directory present) and needs to run a phase with a resolved model.
---

# ai-kit-spec-execute-gsd

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
printf 'GSD_SHIM=%s\nTOOLS_PY=%s\n' "$GSD_SHIM" "$TOOLS_PY"
```

**Record both printed lines as this wave's own literal values.** Every later step's
`python3 $GSD_SHIM <subcommand> ...` invocation uses this resolved `$GSD_SHIM` path — never a bare
`python3 -m ai_kit_spec_gsd.cli`. `$TOOLS_PY` resolves `ai-kit-spec-review`'s own shim for its
`cache-path --kind quota` subcommand.

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
GSD_CONFIG_PATH="$(python3 "$GSD_SHIM" config-path --cwd "$CWD")"
RESULT_JSON="$(python3 "$GSD_SHIM" resolve-dispatch --cwd "$CWD" \
  --config-path "$GSD_CONFIG_PATH" --target-dir "$CWD" \
  --quota-path "$(python3 "$TOOLS_PY" cache-path --kind quota)" \
  --phase-prompt-file "$PHASE_PROMPT_FILE")"
RUN_ID="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["run_id"])' <<< "$RESULT_JSON")"
RESULT_MODE="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["mode"])' <<< "$RESULT_JSON")"
RESULT_KEY="$(python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("key") or "")' <<< "$RESULT_JSON")"
RESULT_CLI="$(python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("cli") or "")' <<< "$RESULT_JSON")"
RESULT_PROVENANCE="$(python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("provenance") or "")' <<< "$RESULT_JSON")"
RESULT_REASON="$(python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("reason") or "")' <<< "$RESULT_JSON")"
RESULT_MESSAGE="$(python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("message") or "")' <<< "$RESULT_JSON")"
RESULT_CROSS_AI_COMMAND="$(python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("cross_ai_command") or "")' <<< "$RESULT_JSON")"
printf 'CWD=%s\nPHASE_ID=%s\nPHASE_PROMPT_FILE=%s\nGSD_CONFIG_PATH=%s\nRUN_ID=%s\nRESULT_MODE=%s\nRESULT_KEY=%s\nRESULT_CLI=%s\nRESULT_PROVENANCE=%s\nRESULT_REASON=%s\nRESULT_MESSAGE=%s\nRESULT_CROSS_AI_COMMAND=%s\n' \
  "$CWD" "$PHASE_ID" "$PHASE_PROMPT_FILE" "$GSD_CONFIG_PATH" "$RUN_ID" "$RESULT_MODE" \
  "$RESULT_KEY" "$RESULT_CLI" "$RESULT_PROVENANCE" "$RESULT_REASON" "$RESULT_MESSAGE" \
  "$RESULT_CROSS_AI_COMMAND"
```

**Record every line of that trailing `printf`'s output as this wave's own literal values.** If
`mode == "fallback_notice"` and `reason == "malformed_config"`, print the message and STOP — do
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
`no_usable_dispatch`) is permanent, non-time-bound — print the message, run the mode-transition
cleanup below, and proceed to Step 3 with no candidate resolved (GSD's own currently-active
default runs unmodified). Never schedule a wake for these.

## Step 2: Act on the dispatch mode

- `native_tier` (either `written` value): the resolved mode is NOT cross-AI — run the
  mode-transition cleanup below before proceeding to Step 3, in case a PRIOR run of this project
  left an adapter-owned cross-AI hook active that this run's resolution superseded.
  `written=False`/`provenance="existing_gsd_config"`: GSD's own config already carries a genuine
  (non-adapter-owned) value at `model_profile_overrides[runtime][tier]` — a real user pin, honored
  as-is, nothing further to write.
  `written=True`/`provenance="resolved_candidate"`: the CLI call already wrote `runtime` (if
  needed) and `model_profile_overrides[runtime][tier]`, taking a per-run backup first.
- `cross_ai_hook`: **write GSD's own real, confirmed `workflow.*` keys** (Task 1 finding 1) via
  `write-workflow-key`, threading each call's own JSON output into the next call's `--config-json`
  (a second write against a stale snapshot would discard the first's key), `--run-id "$RUN_ID"`
  throughout.

  **`workflow.cross_ai_command` is NOT the raw external CLI command
  (`$RESULT_CROSS_AI_COMMAND`) — it is OUR OWN `dispatch-execute` subcommand, wrapping it.**
  (2026-08-30 direction: dispatch happens directly, at resolution time, through our own
  instrumented path — never a bare vendor CLI string GSD merely forwards a prompt into.) This
  gets us real heartbeat, real model/effort/service-tier control, and real cross-AI dispatch
  reinforcement guidance (composed fresh at dispatch time, not parked in a file GSD may or may
  not carry through its own PLAN.md `<objective>`/`<tasks>` extraction) — while GSD's own
  `cross_ai_delegation` step keeps doing its own real, unmodified bookkeeping (writing the
  plan's SUMMARY.md, updating STATE.md/ROADMAP.md, marking the plan handled). GSD still owns
  the piping/capture/retry mechanics (Task 1 finding 1) — this only changes WHAT command that
  hook names, not who calls it or when:
  ```bash
  RESULT_MODEL="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1]).get("model") or "")' "$RESULT_JSON")"
  FORMAT_BLOCK_PATH="$(dirname "$GSD_CONFIG_PATH")/.ai-kit-spec-execute-gsd-summary-format.md"
  python3 "$GSD_SHIM" print-summary-format-block > "$FORMAT_BLOCK_PATH"
  CROSS_AI_TIMEOUT_SECONDS=900   # GSD's own outer `timeout` wrapper, written below
  DISPATCH_TIMEOUT_SECONDS=840   # our own inner timeout -- always some margin under GSD's outer
                                  # one, so dispatch_with_heartbeat's own graceful kill-and-drain
                                  # completes before GSD's blunt outer `timeout` SIGKILLs the
                                  # whole pipeline uncleanly (mid-write, no partial output saved)
  # NO manual quoting around $TOOLS_PY/$RESULT_CLI/$RESULT_MODEL/$CWD/$FORMAT_BLOCK_PATH below --
  # GSD's own cross_ai_delegation step expands workflow.cross_ai_command's stored value as a bare
  # `${CROSS_AI_CMD}` (word-split by whitespace only, never re-parsed as shell syntax, no `eval`).
  # A quote character embedded in the stored string is NOT a quoting boundary at that point -- it
  # is just another literal character stuck onto whichever word it falls inside, so `--cli
  # \"$RESULT_CLI\"` would hand dispatch-execute the literal 8-character argument '"codex"'
  # (quotes included) instead of the bare 5-character `codex` it needs. This means values with
  # actual whitespace cannot be passed safely through this hook at all -- a real, structural
  # limitation of GSD's own naive `${CROSS_AI_CMD}` expansion (not something this adapter can fix
  # without editing GSD's own workflow prose), same as it already was for the raw external-CLI
  # command string this replaces.
  WRAPPER_COMMAND="python3 $TOOLS_PY dispatch-execute --cli $RESULT_CLI --model $RESULT_MODEL --target-dir $CWD --prompt-file - --stdout-only --timeout $DISPATCH_TIMEOUT_SECONDS --format-block-file $FORMAT_BLOCK_PATH"
  UPDATED="$(python3 "$GSD_SHIM" write-workflow-key --config-path "$GSD_CONFIG_PATH" \
    --config-json "$(cat "$GSD_CONFIG_PATH" 2>/dev/null || echo '{}')" \
    --key cross_ai_command --run-id "$RUN_ID" \
    --value-json "$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$WRAPPER_COMMAND")")"
  UPDATED="$(python3 "$GSD_SHIM" write-workflow-key --config-path "$GSD_CONFIG_PATH" \
    --config-json "$UPDATED" --key cross_ai_execution --run-id "$RUN_ID" --value-json true)"
  UPDATED="$(python3 "$GSD_SHIM" write-workflow-key --config-path "$GSD_CONFIG_PATH" \
    --config-json "$UPDATED" --key cross_ai_timeout --run-id "$RUN_ID" \
    --value-json "$CROSS_AI_TIMEOUT_SECONDS")"
  printf 'UPDATED_CONFIG_JSON=%s\nFORMAT_BLOCK_PATH=%s\n' "$UPDATED" "$FORMAT_BLOCK_PATH"
  ```
  `dispatch-execute`'s own `--stdout-only` mode prints ONLY the dispatched CLI's raw stdout (no
  JSON envelope) and exits with its real returncode — exactly the contract GSD's own recipe
  needs (`echo "$TASK_PROMPT" | timeout "${CROSS_AI_TIMEOUT}s" ${CROSS_AI_CMD} > $CANDIDATE_SUMMARY
  2>$ERROR_LOG`); heartbeat and diagnostics go to stderr only (`$ERROR_LOG`), never mixed into the
  captured summary. Live-verified end-to-end 2026-08-30 against this exact invocation shape (piped
  stdin prompt, `timeout`-wrapped, stdout redirected to a file, real exit code) for codex.

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
dispatch mode. Never touches a value the user set by hand (`clear-workflow-key` is a no-op unless
the key is adapter-owned):

```bash
CURRENT_CONFIG_JSON="$(cat "$GSD_CONFIG_PATH" 2>/dev/null || echo '{}')"
for KEY in cross_ai_command cross_ai_execution cross_ai_timeout; do
  CURRENT_CONFIG_JSON="$(python3 "$GSD_SHIM" clear-workflow-key --config-path "$GSD_CONFIG_PATH" \
    --config-json "$CURRENT_CONFIG_JSON" --key "$KEY" --run-id "$RUN_ID")"
done
```

## Step 3: Prepare confirmed-only tooling guidance, then invoke GSD's own `/gsd-execute-phase` skill

Resolve the CLI identity to prepare tooling guidance for:
- `native_tier`: use `--cli "$RESULT_CLI"` when non-empty, else `--cli claude` (a `cli=None`
  candidate dispatches as the current session itself, i.e. Claude Code — never skip tooling
  preparation for this case).
- `cross_ai_hook`: use `--cli "$RESULT_CLI"` directly (the real external vendor).
- `fallback_notice`: omit `--cli` entirely (no candidate was resolved — generic detection only).

```bash
if [ "$RESULT_MODE" = "fallback_notice" ]; then
  PREPARE_CLI=""
elif [ -z "$RESULT_CLI" ]; then
  PREPARE_CLI="claude"
else
  PREPARE_CLI="$RESULT_CLI"
fi
GUIDANCE="$(python3 "$GSD_SHIM" prepare-tooling --cli "$PREPARE_CLI" --target-dir "$CWD")"
MARKER="<!-- ai-kit-spec-execute-gsd:tooling-guidance -->"
if ! grep -qF "$MARKER" "$PHASE_PROMPT_FILE"; then
  printf '\n%s\n%s\n' "$MARKER" "$GUIDANCE" >> "$PHASE_PROMPT_FILE"
fi
```

This `prepare-tooling` subcommand (Task 4) runs `detect_tool_availability()`,
`resolve_agents_tooling_path()`, `ensure_codegraph_registered(cli)` (skipped when `--cli` is
omitted), and — only if that confirms registration — `build_codegraph_index_command(target_dir)`
before dispatch, per design spec §9's ordering guarantee. Writing the guidance into the phase file
itself (idempotently, marker-guarded) means it reaches GSD's own execution regardless of which
dispatch mode Step 2 chose — GSD's own `/gsd-execute-phase` skill reads this same phase content
whether it's running a native subagent or delegating through `cross_ai_command`.

**`RESULT_MODE = "cross_ai_hook"` needs no separate guidance-append step here anymore.**
(Superseded 2026-08-30 by Step 2's direct-dispatch wrapper — see its own note there for why.)
Earlier, this step appended cross-AI dispatch reinforcement guidance directly to
`$PHASE_PROMPT_FILE`, relying on GSD's own `cross_ai_delegation` step to carry that content
through into the prompt it pipes to the external CLI. That worked in live testing, but rests on
an assumption worth naming: GSD's own recipe extracts specific `<objective>`/`<tasks>` sections
from the plan file to build its `$TASK_PROMPT`, not necessarily the whole file verbatim — so an
appended block could in principle land outside what GSD actually extracts. Step 2's wrapper
command sidesteps this: `dispatch-execute`'s own `--format-block-file` composes the SAME
reinforcement guidance (model-selection override, incremental progress, honest failure
reporting, and GSD's own real SUMMARY.md shape) directly INTO the dispatch itself, at the moment
of the real subprocess call — guaranteed to reach the dispatched CLI regardless of what GSD's
own extraction includes. The underlying guidance functions still live in
`ai_kit_spec.dispatch_guidance` (framework-agnostic, shared with any future
`ai-kit-spec-execute-<other-framework>` adapter) and `ai_kit_spec_gsd.cross_ai_guidance` (GSD's
own real SUMMARY.md shape) — only WHERE they get composed changed, not what they say or that
they stay out of GSD's own workflow/skill files entirely.

**Then invoke GSD's own `/gsd-execute-phase` skill directly, via the `Skill` tool, for `$PHASE_ID`
— this is the entire remaining job of this skill.** There is no subprocess to run, no stdout to
capture, no heartbeat to route (Task 1 finding 3) — GSD's own workflow performs the actual
dispatch, heartbeating, and completion end-to-end in-session, using whichever mechanism Step 2 just
configured. Concretely, the executing agent calls the `Skill` tool with the skill name confirmed by
`$HOME/.claude/skills/gsd-execute-phase/SKILL.md`'s own frontmatter
(`gsd-execute-phase`), passing `$PHASE_ID` as its argument — this is a tool call the agent makes
directly, not a shell command this document can show as a `bash` fence. After that call returns,
this skill's own job is complete; any dispatch failure GSD's own skill surfaces (including its own
cross-AI retry/skip/abort UI) is GSD's problem to handle and report, not this adapter's.
