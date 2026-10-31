---
name: ai-kit-spec-execute-gsd
description: "Resolves the best available, quota-checked (runtime, model) pair for a GSD (Get Sh*t Done) phase, prepares GSD's own .planning/config.json (a native-tier pin, or workflow.cross_ai_command naming the project's supervised runner), then invokes GSD's own /gsd-execute-phase skill directly -- never subprocess-dispatches GSD itself. Use when (1) ai-kit-spec-execute detects a GSD-managed plan (`.planning/PROJECT.md` present) and needs to run a phase with a resolved pair, (2) a GSD phase needs a native-tier model pin written before execution, or (3) a GSD plan is opted into cross-AI delegation (frontmatter cross_ai true) and needs the hook wired before /gsd-execute-phase runs. Claude Code only (it uses the Skill tool and GSD's per-project .claude install); on any other host it stops and names the by-hand /gsd-execute-phase path."
---

# ai-kit-spec-execute-gsd

## NEVER

- **Never subprocess-dispatch GSD itself** — this skill only prepares `.planning/config.json` and
  then hands the phase to GSD's own `/gsd-execute-phase`.
- **Never hand-edit `.planning/config.json`** — every write goes through the shim, which calls
  gsd-tools' own `config-set` (validation, locking, workstream-aware path) and records ownership.
- **Never write `workflow.cross_ai_command` without checking the plan's `cross_ai: true`
  frontmatter**, and never put a raw vendor CLI string there: the hook names the project's own
  supervised runner (Step 2). A custom entry (a `command`, no `runtime`) is never a GSD hook
  (`references/dispatch-notes.md`).
- **Never run `trust-local` without an explicit yes**, and never ask twice in one wave.
- **Never parse an empty result** — exit 2 from any shim call means STOP and relay stderr.
- **Never re-resolve to another candidate after a failed dispatch, and never re-run Step 1 to
  recover from a cross-AI stop.** A fresh `resolve-dispatch` walks the candidate list again and
  can rewrite `workflow.cross_ai_command` to another pair. The wake re-enters through GSD: it
  answers GSD's pending retry, or runs `/gsd-execute-phase` with the hook unchanged. The one
  allowed re-run is Step 1's own, after the owner says yes to `trust-local`.
- **Never answer GSD's `skip`** (it falls back to the native executor), and never switch
  harness, provider or model.
- **Only the scheduled wake answers GSD's `retry`.** On any exit 75 carrying `retry_after_s=`,
  answer nothing in that turn; the one-shot wake waits that delay and retries the same lane, CLI
  and model. Every other stop answers `abort` (Step 3).
- **A `fallback_notice`, or a runner-setup failure, stops after cleanup and reports.** It never
  continues to GSD's native execution unless the owner explicitly decides to.

**Trust model.** Project-local `.aikit/review-spec.toml` entries count only after `trust-local`.
The gsd-core tooling has no such gate: the shim runs the first `gsd-tools.cjs` it finds,
project-local first (`<root>/gsd-core`, `<root>/.claude/gsd-core`, `<root>/.codex/gsd-core`, root
being `RUNTIME_DIR` or the git top level), with `node`, so running this skill in a cloned repo
executes that repo's JavaScript. `resolve-dispatch` and the `*-workflow-keys` calls print
`ai-kit: gsd-core <version> at <path>` on stderr; if that path is in a repo you have not
reviewed, stop and check it.

**Cross-AI caller contract:** [`../ai-kit-cross-ai/SKILL.md`](../ai-kit-cross-ai/SKILL.md), a
MANDATORY read at Step 3's stop handling; if that sibling is missing, STOP.

## Step 0: Scope, then resolve the shim path

**Claude Code only.** Everything GSD-related here (the `Skill` call, the `.claude/` GSD install
Step 3 confirms, the Step 3 wake via a one-shot `CronCreate` at `retry_after_s`) is designed for
Claude Code. Other runtimes can often load Claude Code skills, commands and agents, but this
skill is not designed for them. On any other host, STOP before the block below and run
nothing: tell the owner to run `/gsd-execute-phase <phase_id>` by hand with that host's own GSD
install; never report a missing GSD or ask for a reinstall there.

**Host check.** Claude Code exports `CLAUDECODE` to every process it spawns; it is the variable
`detect_current_runtime()` in `ai-kit-spec-review`'s `ai_kit_spec/detection.py` reads for
`claude` (a truthy check, so an empty value counts as absent). The first lines of the block below
fail closed on it (exit 2, nothing else run). The host's own tool list decides the other half:
without the `Skill` tool, STOP the same way. A missing scheduler tool is not part of the check;
it only changes the exit-75 branch (Step 3).

This skill is not guaranteed a `CLAUDE_PLUGIN_ROOT` — take the FIRST existing of, in order (this
skill's own directory and its siblings first, so the shims match the `SKILL.md` you loaded, not an
older install elsewhere), and resolve `ai-kit-spec-review`'s own shim in the SAME call:

```bash
[ -n "$CLAUDECODE" ] || {
  echo "ai-kit-spec-execute-gsd: CLAUDECODE is empty, so this is not Claude Code; STOP, run /gsd-execute-phase by hand"
  exit 2; }
SKILL_MD="<absolute path to THIS SKILL.md>"
case "$SKILL_MD" in */SKILL.md) [ -f "$SKILL_MD" ] ;; *) false ;; esac || {
  echo "ai-kit-spec-execute-gsd: set SKILL_MD to this SKILL.md's real path; nothing run"; exit 2; }
for d in "$(dirname "$SKILL_MD")" \
         "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/ai-kit-spec-execute-gsd}" \
         "$HOME/.claude/skills/ai-kit-spec-execute-gsd"; do
  [ -d "$d" ] && { GSD_SKILL_DIR="$d"; break; }
done
GSD_SHIM="$GSD_SKILL_DIR/ai-kit-spec-gsd.py"
for d in "$(dirname "$GSD_SKILL_DIR")/ai-kit-spec-review" \
         "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/ai-kit-spec-review}" \
         "$HOME/.claude/skills/ai-kit-spec-review"; do
  [ -d "$d" ] && { REVIEW_SPEC_SKILL_DIR="$d"; break; }
done
TOOLS_PY="$REVIEW_SPEC_SKILL_DIR/ai-kit-spec.py"
for d in "$(dirname "$GSD_SKILL_DIR")/ai-kit-gsd-curated-config" \
         "${CLAUDE_PLUGIN_ROOT:+$CLAUDE_PLUGIN_ROOT/skills/ai-kit-gsd-curated-config}" \
         "$HOME/.claude/skills/ai-kit-gsd-curated-config"; do
  [ -d "$d" ] && { CURATED_SKILL_DIR="$d"; break; }
done
CURATED_PY="${CURATED_SKILL_DIR:+$CURATED_SKILL_DIR/ai-kit-gsd-curated-config.py}"
[ -n "$GSD_SKILL_DIR" ] && [ -n "$REVIEW_SPEC_SKILL_DIR" ] || {
  echo "ai-kit-spec-execute-gsd: this skill's or ai-kit-spec-review's directory not found; STOP"
  exit 2; }
[ -f "$GSD_SHIM" ] || { echo "ai-kit-spec-execute-gsd: $GSD_SHIM not found; STOP"; exit 2; }
printf 'GSD_SHIM=%s\nTOOLS_PY=%s\nCURATED_PY=%s\n' "$GSD_SHIM" "$TOOLS_PY" "$CURATED_PY"
```

**Record all three printed lines as this wave's own literal values.** Every later
`python3 $GSD_SHIM <subcommand> ...` uses this resolved path, never a bare
`python3 -m ai_kit_spec_gsd.cli`. `$TOOLS_PY` is `ai-kit-spec-review`'s shim (`cache-path --kind
quota`). `$CURATED_PY` is `ai-kit-gsd-curated-config`'s shim, which Step 2 uses to render or
upgrade the project runner; it prints empty when that skill is not installed, which only a
`cross_ai_hook` run needs. **If the block exits 2, STOP** and relay it.

**Every separate `Bash` tool call starts a fresh shell**: a variable set in one call is gone by
the next. Steps 1–3 are separate `Bash` calls; every `$VAR` denotes the literal value most
recently captured for it via a `printf`, re-substituted verbatim into later commands.

`$CWD`, `$PHASE_ID`, and `$PHASE_PROMPT_FILE` (bound in Step 1) are **inputs this skill is invoked
WITH, never values it invents or infers.** Invoked without `cwd`, `phase_id` and the exact phase
prompt file (a phase can hold several plan files), STOP and ask the user.

## Step 1: Resolve the dispatch decision via the CLI entrypoint

**One `Bash` call:**

```bash
CWD="<this skill's own entry-precondition project root -- supplied by the caller>"
PHASE_ID="<this skill's own entry-precondition phase id -- supplied by the caller>"
PHASE_PROMPT_FILE="<the exact phase prompt/context file path -- supplied by the caller>"
# GSD's /gsd-execute-phase (Step 3) runs in this session's workspace, never in --cwd.
[ -n "$CWD" ] && [ "$(cd "$CWD" 2>/dev/null && pwd -P)" = "$(pwd -P)" ] || {
  echo "ai-kit-spec-execute-gsd: $CWD is not this session's workspace ($(pwd -P))"; exit 2; }
GSD_CONFIG_PATH="$(python3 "$GSD_SHIM" config-path --cwd "$CWD")" || exit 2  # honors workstreams
QUOTA_PATH="$(python3 "$TOOLS_PY" cache-path --kind quota)" || exit 2  # never pass an empty path
RESULT_JSON="$(python3 "$GSD_SHIM" resolve-dispatch --cwd "$CWD" \
  --target-dir "$CWD" \
  --quota-path "$QUOTA_PATH" \
  --phase-prompt-file "$PHASE_PROMPT_FILE")"
RC=$?  # exit 1 is write_failed, which still prints JSON; a crash prints none
{ [ "$RC" -eq 2 ] || { [ "$RC" -ne 0 ] && [ -z "$RESULT_JSON" ]; }; } && exit 2
printf 'CWD=%s\nPHASE_ID=%s\nPHASE_PROMPT_FILE=%s\nGSD_CONFIG_PATH=%s\n' \
  "$CWD" "$PHASE_ID" "$PHASE_PROMPT_FILE" "$GSD_CONFIG_PATH"
python3 -c 'import json,sys
d = json.loads(sys.argv[1])
for k in ("run_id", "mode", "key", "runtime", "model", "provenance", "reason", "message",
          "cross_ai_command"):
    print(("RUN_ID" if k == "run_id" else "RESULT_" + k.upper()) + "=" + str(d.get(k) or ""))
print("RESULT_JSON=" + json.dumps(d))' "$RESULT_JSON" || exit 2
```

**Record every printed `KEY=value` line as this wave's own literal values.**

**If the call exits 2, STOP and relay its stderr verbatim** — nothing was written and there is no
JSON to parse. The causes: `$CWD` is not the directory this host's shell calls start in (the
Skill call in Step 3 cannot be pointed at another checkout; the owner re-invokes from `$CWD`),
a shim crash with no JSON, `node` is not on PATH, no `gsd-tools.cjs` was found (project-local
gsd-core first, then the host homes), gsd-tools could not resolve a config path for `$CWD`, a
malformed `review-spec.toml`, or an entry with `purpose = "execute"` that can never execute (a
custom `command` entry, grok, or claude with a model outside its alias set).

**If `resolve-dispatch` stderr prints `ignoring untrusted project-local config`**, this decision
was made from the global config only, and a `native_tier` result may already have written it.
Relay the line verbatim, show `python3 "$TOOLS_PY" trust-local --cwd "$CWD" --show` (each local
reviewer's argv, the prompt as `<prompt>`; writes nothing), and ask once. On yes, run
`python3 "$TOOLS_PY" trust-local --cwd "$CWD"` and **re-run this whole Step 1 (new `run_id`)**
before Step 2; it overwrites only adapter-owned values. On no, continue with this
result and do not ask again this wave. Never trust unasked.

If `mode == "write_failed"` (exit 1): a `gsd-tools config-set` failed mid-write. Earlier keys were
reverted in reverse order; `reverted` lists them, `revert_failed` lists any whose revert failed
(they still hold the new value and need a hand fix). Print the `RESULT_JSON=` line captured above
and STOP: no Step 2/3.

If `mode == "fallback_notice"` and `reason == "malformed_config"`, print the message and STOP: no
Step 2/3 (the cleanup refuses a malformed config, so none runs).

If `mode == "fallback_notice"` and `reason == "quota_exhausted"` (genuine, time-bound exhaustion
found before any handoff to GSD): **MANDATORY: read
[`references/resumable-state.md`](references/resumable-state.md) and run its block**
with `RESUME_VIA=skill` to write the resumable state file. Then run the mode-transition cleanup
(Step 2) and STOP for this wave: report the probe reasons and the exact state path the block
prints (`RESUME_STATE_PATH=…`). Nothing is scheduled; the owner re-invokes when quota is back
(do not proceed to Step 3 unless the owner explicitly chooses native execution; then follow
Step 2's `fallback_notice` bullet — GSD's own default runs, unless an earlier wave left an
adapter-written pin: read `model_profile` and `model_profile_overrides` in `$GSD_CONFIG_PATH`
and tell the owner).

Every other `fallback_notice` reason is permanent:

- `no_configured_candidate`: `review-spec.toml` has no `[[reviewers]]` entry at all.
- `all_candidates_context_rejected`: every candidate's `context_limit` is below this phase's
  estimated required context.
- `unsafe_hook_token`: the model id holds a character GSD's unquoted hook cannot carry.
- `unsupported_model_id`: the model id is outside its runtime's grammar (Step 2).
- `no_usable_dispatch`: no quota-available candidate has a native GSD tier or a CLI with an
  execute builder; each skipped one got a stderr warning, and `key` names the top one.

Print the message, run Step 2's cleanup, and STOP and report the reason.
Never proceed to Step 3 (GSD's native executor) unless the owner explicitly chooses native
execution; then follow Step 2's `fallback_notice` bullet. Nothing is scheduled.

## Step 2: Act on the dispatch mode

A reviewer or executor is a (runtime, model) pair. Each call runs it natively when its runtime is the current host and the host can select that model; otherwise it runs as a subprocess through the supervised runner. An entry with neither a runtime nor a model is the session default, which the host always runs natively. Today only Claude Code selects a model per call (its sonnet, opus, haiku and fable aliases); every other host runs only its session default natively. Precisely: no runtime and no `command`; a `command` entry is custom.
GSD's `native_tier` is the exception: GSD's own runtime runs the pin, decided without a host
check. Only the tiers `opus`, `sonnet` and `haiku` become a pin (a claude alias, or a curated
`tier`, naming one of them). `fable` is not a GSD tier: that candidate is skipped, and a skipped
`fable` entry explains an unexpected `fallback_notice` or a later candidate winning.

**Mindset.** Resolve the mode fresh every run (quota, CLIs, `cross_ai: true` change); run the
cleanup even for a non-cross-AI mode so a stale hook never keeps dispatching.

**Pending plans.** GSD delegates only plans that have no SUMMARY yet and whose frontmatter
carries `cross_ai: true`. List them first, in one `Bash` call. It assumes GSD's layout:
`NN-MM-PLAN.md` beside `NN-MM-SUMMARY.md` in the directory of `$PHASE_PROMPT_FILE`. With no
`*-PLAN.md` file (plans named another way) it prints `NO_PLANS=1`: the layout
differs, so STOP and ask, in every mode. With `*-PLAN.md` files that all have a SUMMARY, it prints `NOTHING_PENDING=1`: record it as a
literal. The phase has nothing to delegate and no executor to configure: write no hook (in
`cross_ai_hook` mode run only the cleanup below, never the setup reference), and go to Step 3,
which confirms GSD's skill, skips `prepare-tooling` when it is set, then invokes so GSD only
verifies the phase.

```bash
TOTAL=0 PENDING=0
for p in "$(dirname "$PHASE_PROMPT_FILE")"/*-PLAN.md; do
  [ -f "$p" ] || continue
  TOTAL=1
  [ ! -f "${p%-PLAN.md}-SUMMARY.md" ] || continue
  PENDING=1
  awk 'NR == 1 && /^---/ {f = 1; next} f && /^---/ {exit}
       f && /^cross_ai:[[:space:]]*true[[:space:]]*$/ {o = 1} END {exit !o}' "$p" && o=1 || o=0
  printf 'PENDING_PLAN=%s CROSS_AI=%s\n' "$p" "$o"
done
case "$TOTAL$PENDING" in 10) echo NOTHING_PENDING=1 ;; 00) echo NO_PLANS=1 ;; esac  # exit 0
```

- `native_tier`: GSD's own runtime runs the pair as a tier pin (no host check). Run the
  mode-transition cleanup below before Step 3.
  The pin is the scalar `model_profile` for claude, else `model_profile_overrides.<runtime>.<tier>`.
  `RESULT_PROVENANCE=existing_gsd_config`: GSD's own config already carries a genuine
  (non-adapter-owned) value at that key — a real user pin, honored as-is, nothing further to
  write. An existing user `model_profile` is kept even when it differs from the resolved tier.
  `RESULT_PROVENANCE=resolved_candidate`: the CLI call already wrote the pin, taking a
  per-run backup first — `model_profile` for claude, else `runtime` (if needed) and
  `model_profile_overrides.<runtime>.<tier>`.
  The pin persists: no cleanup or subcommand removes it, so a later `cross_ai_hook` or
  `fallback_notice` wave runs native plans under it.
  The pin governs only plans GSD does not delegate. When the cleanup prints `USER_HOOK=1`, the
  project's own hook stays enabled: `cross_ai_command` plus `cross_ai_execution: true`, both
  user-owned and never cleared. GSD then delegates every pending plan with `CROSS_AI=1` through
  that hook, not the resolved pin. If any line has `CROSS_AI=1`, tell the owner so and ask once
  whether to continue. On no, STOP. Never edit their hook.
- `cross_ai_hook`: the pair runs as a subprocess through the project's own supervised runner.
  **Check the opt-in before any write, including `ensure-runner`.** Continue only with at least
  one `PENDING_PLAN` line. If any `PENDING_PLAN` line has `CROSS_AI=0`, do not write the hook and do not render the runner. Print this warning, run
  the mode-transition cleanup, and STOP — "plan <path> does not have `cross_ai: true` in its
  frontmatter — the hook was not written. Add the key, or say explicitly to run this phase on
  GSD's native executor." Never write the hook and warn afterwards, and never treat the warning
  as permission to continue. A workflow-level write alone never makes GSD delegate.
  **MANDATORY: then read [`references/cross-ai-hook-setup.md`](references/cross-ai-hook-setup.md)
  in full and run its block as one `Bash` call.** It renders or upgrades the runner and the
  guidance file, writes GSD's own `workflow.*` keys in one `write-workflow-keys` call (the same
  `run_id` as Step 1), and lists what each exit means. Its `RESULT_MODE=` line replaces the
  Step 1 value; a `fallback_notice` there STOPS after its cleanup.

  **`workflow.cross_ai_command` names the project's own supervised runner, never the raw
  vendor CLI.** GSD's `cross_ai_delegation` step still owns the piping, capture, retry and
  bookkeeping (the plan's SUMMARY.md, STATE.md, ROADMAP.md); only the command changes, and no
  prior curated-config apply is needed. `ensure-runner` never overwrites a user-edited runner: on
  the current template it is kept, and a pending upgrade gets a `.new` file plus notes. The hook
  stays unquoted on purpose (GSD word-splits and globs it; `references/dispatch-notes.md`).

  **Exec confinement.** Codex runs under `--codex-sandbox workspace-write` (writes stay in the
  project dir plus `/tmp` and `$TMPDIR`). Every other exec target runs with full permissions; the
  guidance file's project-dir-only sentence is guidance, not a boundary. pi exec is verified by
  the runner's hermetic self-test only, and live verification is still open. stderr prints the pi
  and copilot notes before the hook is written; relay them. Per-runtime detail and the Node floor:
  `references/dispatch-notes.md` and the setup reference.
- `fallback_notice`: already handled in Step 1 (a probe-time `quota_exhausted` STOP, or one of the
  permanent reasons). Run the mode-transition cleanup below, then STOP and report. Do not continue
  to Step 3. Only when the owner explicitly says to run this phase natively, go straight to
  Step 3 with `RESULT_MODE=fallback_notice`: never re-run Step 1 or 2 for it (the cleanup
  already ran).

**Mode-transition cleanup** — run this whenever the resolved `mode` is `native_tier` or
`fallback_notice` (i.e. NOT `cross_ai_hook`), and when the `cross_ai_hook` opt-in check or the
nothing-pending case above stops or skips the setup, before any later step. It never touches a value
the user set by hand (`clear-workflow-keys` is a no-op unless the key is adapter-owned, and
reports what it kept), except a `cross_ai_timeout` below 1800 that Step 2 raised: that key is
deleted and the user's lower value is not restored (`references/cross-ai-hook-setup.md`). For
`native_tier`, a successful cleanup continues to Step 3 (after the `USER_HOOK` check above). For
`fallback_notice`, a successful cleanup STOPS and reports: continuing would run GSD's native
executor, which takes an explicit owner decision:

```bash
[ -n "$RUN_ID" ] && [ -d "$CWD" ] && [ -f "$GSD_SHIM" ] || {
  echo "ai-kit-spec-execute-gsd: set RUN_ID, CWD, GSD_SHIM; nothing cleared"; exit 2; }
CLEAR="$(python3 "$GSD_SHIM" clear-workflow-keys --cwd "$CWD" --run-id "$RUN_ID" \
  --key cross_ai_command --key cross_ai_execution --key cross_ai_timeout)"
if [ $? -ne 0 ]; then  # exit 1 also covers a non-empty revert_failed (only after a failed key)
  echo "$CLEAR"
  echo "ai-kit-spec-execute-gsd: cleanup failed; an old hook may still be active -- not running Step 3"
  exit 1
fi
python3 -c 'import json,sys; k = json.loads(sys.argv[1]).get("kept") or {}
on = k.get("cross_ai_command") and str(k.get("cross_ai_execution")).lower() == "true"
print("USER_HOOK=%d" % bool(on))' "$CLEAR"
```

**Only a successful cleanup reaches Step 3.** Exit 1 means a clear failed and was rolled back,
so a prior run's adapter-owned hook can still be active: STOP, show the output, and name the keys
still holding a value (`failed`, `revert_failed`); never hand the phase to GSD with that hook
possibly live. Exit 2 (no `node` or `gsd-tools.cjs`, no config path, or a malformed config): STOP.

## Step 3: Prepare confirmed-only tooling guidance, then invoke GSD's own `/gsd-execute-phase` skill

**Confirm GSD's skill before any write or arming.** Check, in order:
`$CWD/.claude/commands/gsd-execute-phase.md`, then
`$CWD/.claude/skills/gsd-execute-phase/SKILL.md` (GSD installs per project), and only as
a last fallback `$HOME/.claude/skills/gsd-execute-phase/SKILL.md`. Read the first that exists
for its `name`. If none exists or none is readable,
that is an environment problem, not a dispatch failure: STOP before `prepare-tooling` and the wake
(the cleanup already ran), do not retry, and report the error with every path checked so the
owner can repair GSD.
When `RESULT_MODE` is not `native_tier`, report a pin an earlier wave left at every stop.

Resolve the runtime to prepare tooling guidance for:
- `native_tier` or `cross_ai_hook`: use `--runtime "$RESULT_RUNTIME"`.
- `fallback_notice`: omit `--runtime` (nothing resolved; reached only after the owner chose native).

```bash
NOTHING_PENDING="<1 if Step 2 recorded NOTHING_PENDING=1, else 0>"
case "$NOTHING_PENDING" in 0|1) ;; *)
  echo "ai-kit-spec-execute-gsd: set NOTHING_PENDING to 1 or 0; nothing written"; exit 2;; esac
case "$RESULT_MODE:$RESULT_RUNTIME" in fallback_notice:*|native_tier:?*|cross_ai_hook:?*) ;; *)
  echo "ai-kit-spec-execute-gsd: set RESULT_MODE and RESULT_RUNTIME; nothing written"; exit 2;; esac
[ -d "$CWD" ] && [ -f "$GSD_SHIM" ] || { echo "ai-kit-spec-execute-gsd: set CWD, GSD_SHIM;" \
  "nothing written"; exit 2; }
if [ "$RESULT_MODE" = "fallback_notice" ]; then
  CLI_ARGS=()
else
  CLI_ARGS=(--runtime "$RESULT_RUNTIME")
fi
if [ "$NOTHING_PENDING" = 1 ]; then
  echo "nothing pending: prepare-tooling skipped, phase file untouched"
elif [ "$RESULT_MODE" = "cross_ai_hook" ]; then
  # GSD delegates every pending plan, so no native executor reads a phase-file block:
  # index codegraph and write nothing.
  python3 "$GSD_SHIM" prepare-tooling "${CLI_ARGS[@]}" --target-dir "$CWD" >/dev/null || exit 2
else
  python3 "$GSD_SHIM" prepare-tooling "${CLI_ARGS[@]}" --target-dir "$CWD" \
    --phase-file "$PHASE_PROMPT_FILE" || exit 2
fi
```

**If it exits 2, STOP and relay its stderr**; the phase file is untouched. Causes: a failed or
empty producer, an older release's single-marker block (delete it by hand), malformed markers
(none, or one start before one end), or a read/write error.

`prepare-tooling` probes codegraph for that runtime (report-only, 15 s timeout; skipped without
`--runtime`); when it is missing or unhealthy the install command lands on stderr: relay it
verbatim, never run it. With `--phase-file` it writes a marker-guarded block atomically. That
block reaches only GSD's native executor, best-effort (GSD reads CONTEXT.md and RESEARCH.md only
at `context_window` 500000 or more, and in worktree mode from a commit without this uncommitted
edit), so never report it as delivered. A delegated plan gets guidance from
`.planning/scripts/cross-ai-guidance.md` (Step 2).

**Session wake (multi-plan phases).** **MANDATORY before the invoke when the phase holds two
or more pending `*-PLAN.md` files (no SUMMARY):** read
[`references/session-wake.md`](references/session-wake.md) "Arm" and run its block as written
(fewer than two pending plans arm nothing). It records `WAKE_SHIM`, `WAKE_OWNED`, `WAKE_HOST` and `WAKE_ID` as literal values; the wake is
this run's only when it printed `armed` (`WAKE_OWNED=1`). Never fail the run on the wake.

**Then invoke GSD's own `/gsd-execute-phase` skill directly, via the `Skill` tool, for `$PHASE_ID`
— this is the entire remaining job of this skill.** GSD's workflow does the dispatch,
heartbeating and completion in-session, through whatever Step 2 configured. Call the `Skill`
tool with the name confirmed above and `$PHASE_ID` as its argument. If that call still fails to resolve, report the error, run the close step and STOP; do
not retry. The rules below govern every answer to GSD's retry/skip/abort prompt.

**MANDATORY on any cross-AI stop:** read [`../ai-kit-cross-ai/SKILL.md`](../ai-kit-cross-ai/SKILL.md)
sections 4 and 6-8 before answering GSD's prompt. Relay the runner's `cross-ai: report`,
`cross-ai: upstream` and `AIKIT-XAI` lines verbatim from GSD's `$ERROR_LOG` (the hook's stderr,
read in full, never a truncated tail), then run the block in
[`references/resumable-state.md`](references/resumable-state.md) with
`RESUME_VIA=gsd-execute-phase` so the owner has a durable record.

Every stop other than an exit 75 carrying `retry_after_s=` (a bare 75, any 69 including
`stopped=hard-waits` or `stopped=cap`, 1, 2, 124, 127, or exit 0 with an invalid summary, which
GSD also offers retry/skip/abort for) gets the notice and the answer `abort`, schedules nothing
and re-arms nothing. `abort` ends only that plan's prompt: stay inside the `Skill` call, answer
any further prompt by these same rules, and go to the close step only once `/gsd-execute-phase`
itself has returned. Never answer `skip` (NEVER list).

For an exit 75 carrying `retry_after_s=` (transient ladder exhausted or confirmed-router quota),
answer nothing to GSD's prompt in that turn and **MANDATORY: read
[`references/session-wake.md`](references/session-wake.md) "Quota wake"**: it re-arms the session
wake when `WAKE_OWNED=1` and schedules one one-shot `CronCreate` wake at `retry_after_s` that
retries the same lane, CLI and model (variant A when `WAKE_OWNED=1`, B when 0). With a
scheduler this branch continues the run and never closes the wake. Without it nothing can
retry in-session: the run stops here with the handoff printed, and an owned OS-timer wake
(`WAKE_OWNED=1`) is deliberately left armed, because it resumes the session only after the host
exits. Do not run the close step there either. After a session exit the owner runs
`/gsd-execute-phase <PHASE_ID>` and never re-invokes this skill (that re-runs Step 1).

**Close the session wake.** **MANDATORY at every end of this skill's job:** the phase completed;
`/gsd-execute-phase` returned after a stop answered `abort`; `/gsd-execute-phase` ended any other way (a checkpoint or verification
gap left for the owner, a non-cross-AI failure); or the `Skill` call failed after arming. Run the "Close" block of [`references/session-wake.md`](references/session-wake.md); it calls
nothing when `WAKE_OWNED=0`. Never run it on the exit-75 `retry_after_s=` branch above, with or
without a scheduler.
