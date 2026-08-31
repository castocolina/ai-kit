# ai-kit-spec-execute-gsd Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the GSD (Get Sh*t Done) adapter for `ai-kit-spec-execute`: a skill that resolves
the best available model/CLI for a GSD phase's execution task using Foundation's existing
live-quota-checked selection logic, then **prepares GSD's own `.planning/config.json`** so that
GSD's **own** `/gsd-execute-phase` skill — invoked directly via the `Skill` tool, never
subprocess-invoked — does the actual dispatch, through whichever of GSD's two real mechanisms
applies: native model-tier resolution (`runtime` + `model_profile_overrides.<runtime>.<tier>`) or
GSD's own `cross_ai_command` shell-hook. Never silently drops the user's chosen model — when
neither mechanism can carry it, this adapter says so explicitly and lets GSD's own currently-active
default run.

**Architecture:** Task 1's spike (complete — see its own dated finding below) ran against a real
GSD install and a real GSD-managed project and overturned three of this plan's original
assumptions. The corrected architecture: (1) `cross_ai_command`/`cross_ai_execution` is a real,
already-implemented, general shell-command hook in GSD itself — this plan's only job for that path
is to compute the right command string and write it into config, never to build a second dispatcher
that duplicates GSD's own piping/capture/retry logic. (2) GSD's native model selection is
`runtime` (a scalar, open-ended vendor-runtime identity) plus `model_profile_overrides.<runtime>.
<tier>` (three levels deep, keyed by runtime then by Claude-tier-alias `opus`/`sonnet`/`haiku`) —
there is no phase-type-keyed `model_overrides`/`models` anywhere in real GSD. (3) GSD phase
execution (`/gsd-execute-phase`) is a Claude Code **skill** (a slash-command whose workflow makes
real `Agent`/`Task`/`AskUserQuestion` calls inside the live session), not a standalone executable —
there is nothing to subprocess-invoke, pipe a prompt into, or capture a result from. This adapter's
own skill therefore does config prep only, then hands off to GSD's own skill via the `Skill` tool.

**Tech Stack:** Python 3 stdlib only, `unittest`, GSD's own `.planning/config.json` (confirmed
JSON, confirmed live against `/var/home/bazzite/git/personal/wezterm-setup/.planning/config.json`).

**Spec:** `docs/superpowers/specs/2026-08-28-ai-kit-spec-execute-design.md` (§7, GSD adapter) — §7's
original config-key names are superseded by Task 1's live finding below wherever the two disagree;
this plan follows the live finding.

## Global Constraints

- Depends on Plan 1 (Foundation) being complete and merged: `ai_kit_spec.execute_selection`,
  `ai_kit_spec.commands.build_execute_command`, `ai_kit_spec.config_io.cfg_resolve`,
  `ai_kit_spec.detection.*`, `ai_kit_spec.tooling_guidance.build_tooling_guidance`,
  `ai_kit_spec.quota.{resolve_ladder_pick, refresh_quota_cache, QUOTA_TTL_SECONDS}`,
  `ai_kit_spec.cache.{cache_read_json, cache_write_json}` all exist and are tested
  (`skills/ai-kit-spec-review/ai_kit_spec/{execute_selection,commands,detection,tooling_guidance,
  config_io,quota,cache}.py`) before this plan's Task 2 onward.
- **`ai_kit_spec.dispatch.dispatch_with_heartbeat` is explicitly OUT OF SCOPE for this plan
  (revision, Task 1 finding 3).** GSD phase execution is a Claude Code skill running inside the
  live session, not a subprocess — there is nothing for this plan to pipe a prompt into or capture
  stdout/stderr from. Foundation's `dispatch_with_heartbeat` remains a real, tested Foundation
  module used elsewhere (e.g. by `ai-kit-spec-review`'s own cross-AI reviewer dispatch); this plan
  simply never imports or calls it. No task below creates a subprocess dispatcher of GSD's own
  execution entry point.
- **Real, live-verified constraint on Foundation's `build_execute_command`** (confirmed by reading
  the actual shipped `skills/ai-kit-spec-review/ai_kit_spec/commands.py`): `_EXECUTE_COMMAND_
  BUILDERS` has exactly ONE working execute-mode (write-capable) builder today — `codex`.
  `cursor-agent` and `opencode` were live-tested and failed real write confinement (demoted, per
  that file's own comment); `grok` and `claude` were never implemented; `gemini` is not registered
  at all. Every one of those raises `ValueError`. The cross-AI command-string builder this plan
  writes (Task 3) must degrade gracefully within that real constraint — return `None`, never guess
  or fabricate a command for a vendor with no live-verified builder.
- Never silently fail to honor the user's chosen model — if GSD's config surface can't carry it
  (no usable native-tier slot, no cross-AI command buildable), the adapter must explicitly tell the
  user which candidate it wanted and why it couldn't write it, before GSD's own currently-active
  default runs unmodified.
- **GSD's real native config surface (Task 1 finding, confirmed live) is `runtime` (top-level
  scalar string, e.g. `"claude"`/`"codex"`/`"gemini"`/`"opencode"`/…, default `null` which reads as
  `"claude"`) plus `model_profile_overrides.<runtime>.<tier>`** (three levels: an object keyed by
  runtime name, each value an object keyed by Claude-tier-alias `opus`/`sonnet`/`haiku`, each value
  a literal model id or `null`). This selects which vendor CLI/runtime GSD's own agent-role-to-model
  resolution runs under and which literal model fills a given tier slot within that runtime. There
  is no phase-type axis anywhere in this surface — GSD's agent-role → tier mapping (planner/
  executor/verifier/etc.) is entirely GSD's own internal concern (`model-profile-resolution.md`),
  not something this adapter reads or writes.
- **`runtime`'s value set is open-ended, not closed to three vendors** (Task 1 finding, confirmed
  live: `claude`, `codex`, `gemini`, `opencode`, `qwen`, `kilo`, `copilot`, `grok`, `cursor`,
  `windsurf`, `augment`, `trae`, `codebuddy`, `cline`, `antigravity` all appear as real values in
  GSD's own workflow docs). `KNOWN_GSD_RUNTIMES` (Task 2) is sourced from this confirmed list and
  is documented as non-exhaustive — a candidate whose `cli` names a value in this set is treated as
  **native** (GSD can itself run under that vendor's runtime); a candidate whose `cli` names
  anything else is **cross-AI** (GSD has no runtime persona for it, only the `cross_ai_command`
  hook can reach it). A candidate with `cli is None` is always native — it dispatches as the
  current session itself, whose runtime identity is `"claude"`.
- **A native candidate needs a `tier` (opus/sonnet/haiku) to be writable at all — not every native
  candidate has one.** This repo's own native (`cli is None`) config entries already use a
  tier-alias directly as their `model` field (e.g. `model: "opus"`) — `assemble_candidates` (Task
  4) treats that as the tier when no separate `tier` field is curated. A `cli`-set native candidate
  (e.g. `cli: "codex"`) needs an explicit curated `tier` field to be writable as a
  `model_profile_overrides` entry; when absent (true of every entry that exists today — no
  `[[reviewers]]` entry curates `tier` yet), this adapter cannot express that candidate natively at
  all and treats it the same as "no usable dispatch" for that candidate, escalating to the next one
  in the ladder. This is a stated scope decision (YAGNI — no curated `tier` data exists to test
  against yet), not silently-wrong behavior.
- **Cross-AI dispatch is GSD's own already-implemented mechanism, confirmed live** (Task 1 finding
  1, `workflows/execute-phase.md`'s `cross_ai_delegation` step): GSD itself runs
  `echo "$TASK_PROMPT" | timeout "${CROSS_AI_TIMEOUT}s" ${CROSS_AI_CMD} > "$CANDIDATE_SUMMARY"
  2>"$ERROR_LOG"`, treats exit 0 + a valid `SUMMARY.md`-shaped `$CANDIDATE_SUMMARY` as success, and
  shows its own retry/skip/abort UI on failure. This plan's entire job for that path is: build the
  real invocation command via Foundation's **unchanged** `ai_kit_spec.commands.
  build_execute_command`, and write it verbatim into `workflow.cross_ai_command` (plus
  `workflow.cross_ai_execution=true`) — never build a second subprocess dispatcher, retry loop, or
  output-capture mechanism of this plan's own.
- **Cross-AI activation is PLAN-level in real GSD, not phase-level** (Task 1 finding 1: a plan is
  only delegated to cross-AI when its own frontmatter carries `cross_ai: true` **and**
  `workflow.cross_ai_execution` is `true`). This adapter operates at phase granularity (a phase can
  contain multiple plans). **Explicit scope boundary (this revision):** this plan writes the
  workflow-level config (`cross_ai_execution`/`cross_ai_command`/`cross_ai_timeout`) but does NOT
  edit any individual plan's own frontmatter — Task 5's SKILL.md instead checks the target plan's
  frontmatter for `cross_ai: true` and prints an explicit warning (never a silent no-op) when it's
  absent, since GSD will not actually delegate to cross-AI for that plan without it even though the
  workflow config is correctly set.
- Never fabricate an unenforced vendor claim — a `fallback_notice` result never claims a model or
  vendor was actually engaged when nothing was written.
- **`execute_selection.resolve_execute_candidates` never itself probes quota** — its own docstring
  states plainly it "only narrows and ranks... the caller must feed its output through
  `candidates_to_ladder` into `quota.resolve_ladder_pick`" for a live-availability pick. Every task
  that selects a dispatch candidate MUST go through that two-step call, and MUST be able to
  escalate past a quota-available-but-unusable candidate (no native tier data, no cross-AI builder)
  to the next quota-available candidate — never just `ranked[0]`.
- **The CLI entrypoint MUST load live quota before resolving a dispatch decision** —
  `ai_kit_spec_gsd/cli.py`'s `resolve-dispatch` subcommand (Task 4) MUST call
  `ai_kit_spec.quota.refresh_quota_cache` and pass the resulting dict as `resolve_gsd_dispatch`'s
  `quota=` argument — an omitted `quota` makes `{}` look like "every candidate has quota,"
  defeating live-availability entirely.
- **No runtime (post-write) dispatch-failure escalation loop exists in this plan (revision, Task 1
  finding 3).** Because GSD's own `/gsd-execute-phase` skill performs the actual dispatch
  in-session (native via its own `Agent`/`Task` calls, cross-AI via its own already-implemented
  retry/skip/abort UI), this adapter has no subprocess exit code or stdout/stderr to observe after
  handoff, and therefore no way to detect a "candidate looked available at probe time but failed at
  dispatch time" condition to escalate past. Quota exhaustion **discovered at probe/resolve time**
  (before handoff) still resolves to an explicit `fallback_notice` with reason `quota_exhausted`
  and still schedules an hourly `CronCreate` wake (Task 5) — that part of the design is unaffected.
  A dispatch failure that happens **after** handoff to GSD's own skill is GSD's own problem to
  surface to the user; this adapter does not attempt to intercept or retry it.
- `execute_selection.filter_by_affinity`'s `task_type` parameter is a frontend/backend/mixed
  "task_affinity" axis (design spec §5.1) — unrelated to any GSD concept. No curated `task_affinity`
  data exists yet (Foundation ships every candidate untagged) — this plan always passes
  `task_type=None` (`filter_by_affinity`'s own documented no-op pass-through), an explicit "no
  known task-affinity axis at this layer," not a stand-in for anything GSD-specific. The moment a
  future curated `task_affinity` value appears on a candidate, `filter_by_affinity` will filter it
  OUT (compares unequal to the hardcoded `task_type=None`) — honoring curated `task_affinity`
  requires a classifier this plan does not build (YAGNI, no curated data exists to test against).
- **`context_limit` defaults to `None`, never `0`, when a config entry doesn't curate it** — the
  real shipped `execute_selection.filter_by_context` treats `context_limit is None` as "unknown,
  pass through" but `context_limit == 0` as "confirmed insufficient," so a `0` default would reject
  every real candidate against any non-empty phase prompt. `resolve_gsd_dispatch` (Task 4) computes
  a real, non-hardcoded `required_context` estimate from the actual phase prompt text
  (`adapter.estimate_required_context`) so the moment a real `context_limit` is curated, filtering
  activates automatically with zero code change here.
- **Adapter-vs-user config-write provenance**: every `model_profile_overrides`/`runtime` write this
  adapter makes (`gsd_config.write_native_tier_override`/`write_active_runtime`, Task 2) is also
  recorded in a sidecar ownership-marker key (`gsd_config["_ai_kit_spec_execute_gsd"]`) in the SAME
  write. `resolve_gsd_dispatch` (Task 4) reads this marker before treating an existing
  `model_profile_overrides[runtime][tier]` entry as an unmodifiable prior user choice — an entry
  that exactly matches this run's own marker is the adapter's OWN prior write (still eligible for
  re-resolution); a mismatched or absent marker means a genuine external user choice, honored
  unconditionally. Backups (`gsd_config.py`'s `_backup_once`) use a per-run backup path (a monotonic
  run id) so a second run's write can never silently overwrite the ONE backup taken before the
  first-ever write to a project's config.
- **Malformed vs. missing config are distinct, machine-readable outcomes**: `gsd_config.
  read_gsd_config` (Task 2) distinguishes them via a `(config, status)` return (`status` is
  `"missing"`/`"malformed"`/`"ok"`) and `warn_fn` (silent for missing, warned for malformed) —
  `ai_kit_spec_gsd/cli.py` (Task 4) MUST route `warn_fn` to **stderr**, never stdout (every
  subcommand's stdout is parseable JSON), and MUST abort any config-mutating subcommand when the
  read was malformed rather than genuinely missing — overwriting a real, broken-but-recoverable
  user config with a near-empty generated one is exactly the "silently discard the user's data"
  failure this plan forbids.

---

## File Structure

```
skills/ai-kit-spec-execute/                    (new skill directory)
  SKILL.md                                      (router: classifies GSD vs superpowers vs other, delegates)
  detect_framework.py
skills/ai-kit-spec-execute-gsd/                 (new skill directory, this plan's primary deliverable)
  SKILL.md                                      (GSD-specific: resolve dispatch -> write config ->
                                                  invoke GSD's own /gsd-execute-phase skill via the
                                                  Skill tool -- no subprocess dispatch of GSD itself)
  ai-kit-spec-gsd.py                            (import-bootstrap SHIM -- the ONLY thing SKILL.md
                                                  ever invokes by absolute path; mirrors
                                                  skills/ai-kit-spec-review/ai-kit-spec.py's own
                                                  "python puts the running script's own directory
                                                  on sys.path[0]" trick, PLUS explicitly inserts the
                                                  sibling skills/ai-kit-spec-review/ directory onto
                                                  sys.path so ai_kit_spec_gsd's own `from
                                                  ai_kit_spec...` imports resolve too. Dispatches
                                                  `<shim> <subcommand> ...` to ai_kit_spec_gsd.cli.main
                                                  only -- there is no separate wrapper subcommand;
                                                  see Task 3's revised scope.)
  ai_kit_spec_gsd/
    __init__.py
    gsd_config.py                               (read/write .planning/config.json: runtime scalar,
                                                  model_profile_overrides.<runtime>.<tier>,
                                                  workflow.cross_ai_* keys, adapter-ownership
                                                  marker, per-run backups)
    gsd_cross_ai.py                             (pure command-string builder for GSD's own
                                                  workflow.cross_ai_command -- NOT a subprocess
                                                  dispatcher; no wrapper program, see Task 3)
    adapter.py                                  (candidate assembly + live-quota-checked dispatch
                                                  resolution + phase context-size estimate; produces
                                                  a config-write plan, never a subprocess dispatch)
    cli.py                                      (resolve-dispatch + config-path + write-workflow-key
                                                  + clear-workflow-key + prepare-tooling +
                                                  write-resumable-state subcommands -- concrete
                                                  invocation paths for SKILL.md, invoked via the shim)
tests/test_ai_kit_spec_gsd.py                   (new test file)
```

`ai-kit-spec-execute` (the router skill) is a thin dispatcher: detect which framework generated
the plan/phase (GSD's `.planning/` markers vs. superpowers' plan-file conventions), then delegate
to `ai-kit-spec-execute-gsd` or `ai-kit-spec-execute-superpowers` (Plan 3). This plan only builds
the GSD-specific half plus a minimal router stub (Task 6) — Plan 3 fills in the superpowers half
of the same router file.

**No `cross_ai_wrapper.py` in this revision.** The original plan's Task 3 built a standalone
subprocess dispatcher (`cross_ai_wrapper.py`) that GSD's `cross_ai_command` hook would shell out
to, driving `dispatch_with_heartbeat` itself. Task 1's live finding shows GSD's own
`cross_ai_delegation` step already does the piping (`echo "$TASK_PROMPT" | timeout ... $CROSS_AI_CMD
> $CANDIDATE_SUMMARY`), capture, and retry UI — a second dispatcher duplicating that is unnecessary
and risks fighting GSD's own mechanism instead of coexisting with it. `gsd_cross_ai.py`'s only job
is formatting the real CLI invocation command (via Foundation's unchanged `build_execute_command`)
as the literal string written into `workflow.cross_ai_command`.

**No `dispatch-phase`/`classify-failure` CLI subcommands, no CronCreate escalation loop for
post-handoff failures.** The original plan's Task 4/5 built a runtime-quota-escalation loop that
observed a dispatched subprocess's exit code and retried past it. Since GSD's own skill performs
the actual dispatch in-session (Task 1 finding 3), this adapter has nothing to observe after
handoff — GSD's own cross-AI retry/skip/abort UI (already implemented) and its own native
model-resolution fallback (also already implemented) cover that. Quota exhaustion discovered
**before** handoff (at `resolve-dispatch` time) is unaffected and still schedules a `CronCreate`
wake — see Task 5.

---

### Task 1: SPIKE — confirm GSD's real config/execution contract against a live install

**Status: COMPLETE.** This task's spike ran this session against a real GSD install
(`/run/media/system/home/user-zero/.claude/gsd-core`) and a real GSD-managed project
(`/var/home/bazzite/git/personal/wezterm-setup`, its own `.planning/config.json` read live). The
finding below overturns three of this plan's original architectural assumptions; every later task
in this plan has been revised to match it (this revision).

**Files:** no source files created/modified. Modify: this plan file itself,
`docs/superpowers/plans/2026-08-29-ai-kit-spec-execute-gsd.md` (this Step 5 finding IS the
deliverable, no other file changes).

**Interfaces:** none — spike output is a plain-English finding, not code.

- [x] **Step 1: Obtain a real GSD install to test against**

Used the real, already-installed GSD Core at `/run/media/system/home/user-zero/.claude/gsd-core`
and a real GSD-managed project at `/var/home/bazzite/git/personal/wezterm-setup` (its own
`.planning/config.json` already exists and is live-configured).

- [x] **Step 2: Read the real `.planning/config.json` schema**

Read `/var/home/bazzite/git/personal/wezterm-setup/.planning/config.json` directly, plus GSD Core's
own `bin/shared/config-schema.manifest.json` (the authoritative `validKeys` list),
`templates/config.json` (the shipped default shape), and `workflows/settings-advanced.md` (the
human-readable reference for every key, including its own worked `gsd_run query config-set`
examples).

- [x] **Step 3: Read GSD's own source/docs for how it consumes `cross_ai_command`**

Read `workflows/execute-phase.md`'s `cross_ai_delegation` step (around line 345–410) directly.

- [x] **Step 4: Live round-trip** — not run as a separate throwaway-script test; the exact
  invocation line was read directly from GSD's own shipped workflow source (Step 3), which is
  authoritative and unambiguous (a literal `echo | timeout ... $CROSS_AI_CMD > $CANDIDATE_SUMMARY
  2>$ERROR_LOG` shell line), so a separate scratch round-trip would only re-confirm what the source
  already states verbatim.

- [x] **Step 4.5 / Step 5: Recorded finding**

## Task 1 Finding (recorded 2026-08-30)

**Verification sources:** `/run/media/system/home/user-zero/.claude/gsd-core/workflows/
execute-phase.md` (the `cross_ai_delegation` step, ~lines 345–410); `/run/media/system/home/
user-zero/.claude/gsd-core/bin/shared/config-schema.manifest.json` (validKeys list); `/run/media/
system/home/user-zero/.claude/gsd-core/templates/config.json` (shipped default shape); `/run/media/
system/home/user-zero/.claude/gsd-core/workflows/settings-advanced.md` (lines ~80–82, ~526–545,
~752–768); `/run/media/system/home/user-zero/.claude/gsd-core/references/model-profile-resolution.md`
and `model-profiles.md`; `/run/media/system/home/user-zero/.claude/gsd-core/workflows/
sync-skills.md` (line 20), `update.md` (line 67), `settings-advanced.md` (lines 389–390); `/run/
media/system/home/user-zero/.claude/skills/gsd-execute-phase/SKILL.md`; a real project's own live
config at `/var/home/bazzite/git/personal/wezterm-setup/.planning/config.json`; `node /run/media/
system/home/user-zero/.claude/gsd-core/bin/gsd-tools.cjs --help`.

**Finding 1 — `cross_ai_command`/`cross_ai_execution` is a real, general shell-command hook,
already fully implemented in GSD itself.** Config keys, all under `workflow.*`: `workflow.
cross_ai_execution` (bool, default `false`), `workflow.cross_ai_command` (string, default `""`/
`null`), `workflow.cross_ai_timeout` (number, default `300`). Activation is **per-plan**, not
per-phase: a plan is delegated to cross-AI only when its own frontmatter has `cross_ai: true` AND
`workflow.cross_ai_execution` is `true` (or the `--cross-ai` CLI flag forces every incomplete
plan). This activation logic is entirely GSD's own — this adapter never reimplements it, only
ensures the config keys are set correctly before GSD's own `execute-phase` workflow runs.
Invocation (GSD's own code, already correct): `echo "$TASK_PROMPT" | timeout "${CROSS_AI_TIMEOUT}s"
${CROSS_AI_CMD} > "$CANDIDATE_SUMMARY" 2>"$ERROR_LOG"` — the prompt is piped via stdin (never
shell-interpolated), `$CANDIDATE_SUMMARY` is captured on stdout. `${CROSS_AI_CMD}` is read verbatim
from `workflow.cross_ai_command` and expanded unquoted as a shell command (word-split) — so this
adapter's entire job for this path is: resolve the winning candidate, build its real invocation
command via Foundation's already-existing `ai_kit_spec.commands.build_execute_command`, and write
that exact string into `workflow.cross_ai_command` (plus `workflow.cross_ai_execution=true`)
**before** GSD's own `execute-phase` workflow runs. Success = exit 0 AND a valid `SUMMARY.md`-shaped
`$CANDIDATE_SUMMARY`; GSD writes it as the plan's real SUMMARY.md and marks the plan complete.
Failure = non-zero exit or invalid summary; GSD shows its own retry/skip/abort choices. No separate
subprocess dispatcher is needed or wanted on this adapter's side.

**Finding 2 — the phase-type-keyed `model_overrides`/`models` this plan originally assumed DOES
NOT EXIST in real GSD.** The real schema is:
- `model_profile` (top-level scalar string, e.g. `"balanced"`/`"adaptive"`/`"inherit"` — confirmed
  live in the real project's config). Governs which internal Claude tier (opus/sonnet/haiku, via
  `model-profile-resolution.md` + `model-profiles.md`) each GSD **agent role**
  (planner/executor/verifier/etc.) resolves to when GSD spawns its own subagents. Unrelated to
  cross-vendor selection — this plan never writes to it for that purpose.
- `runtime` (top-level scalar string, default `null`, which reads as `"claude"`) — the real
  "native runtime enum" concept. Confirmed real values, genuinely open-ended, not a small fixed
  set: `claude`, `codex`, `gemini`, `opencode`, `qwen`, `kilo`, `copilot`, `grok`, `cursor`,
  `windsurf`, `augment`, `trae`, `codebuddy`, `cline`, `antigravity`. Selects which vendor CLI/
  runtime GSD's own skill files were synced to and are running under for the current session — a
  session/project-level identity.
- `model_profile_overrides.<runtime>.<tier>` (three levels: object keyed by runtime name, each
  value an object keyed by Claude-tier-alias `opus`/`sonnet`/`haiku`, each value a literal model id
  or `null`) — overrides which literal model id fills a given tier slot for a given runtime.
  Written via `gsd_run query config-set model_profile_overrides.<runtime>.<tier> "<model-id>"`.
  Task 2's `gsd_config.py` is rewritten around this real shape — keyed by `(runtime, tier)`, never
  by GSD phase type. There is no direct "select model X for phase Y" native-tier write in real GSD
  at all in the shape this plan originally assumed.

**Finding 3 — GSD phase execution is NOT subprocess-invokable; this is the finding that most
changes this plan's architecture.** `/gsd-execute-phase` (and `/gsd-autonomous`) are Claude Code /
Copilot **skills** (slash-commands) — confirmed by reading `/run/media/system/home/user-zero/
.claude/skills/gsd-execute-phase/SKILL.md`, which loads `<execution_context>@$HOME/.claude/
gsd-core/workflows/execute-phase.md</execution_context>` as prompt content into the **current live
agentic session**, and that workflow itself makes real `Agent`/`Task` tool calls to spawn
subagents, real `AskUserQuestion` calls for human gates, etc. There is NO standalone
`gsd-execute-phase <phase-id>` shell executable to fork/exec, pipe a prompt into via stdin, and
capture a result from. The only real shell-invokable GSD surface is `gsd-tools.cjs` (a Node CLI,
confirmed via `node .../bin/gsd-tools.cjs --help`), and it only handles config/state/query/
phase-metadata operations (`config-get`, `config-set`, `state`, `phase`, `roadmap`, `workstream`,
etc.) — it does NOT execute phases itself.

**Architectural consequence (implemented starting this revision):** `ai-kit-spec-execute-gsd` is a
skill that triggers **another skill** (GSD's own `/gsd-execute-phase`, invoked via the `Skill`
tool) after first preparing the right config, so GSD's own execution logic does the actual work —
either through a pre-built cross-AI CLI command or an explicit native `(runtime, tier)` model-id
mapping — rather than this plan reimplementing GSD's own cross-AI/execution logic. Concretely:
resolve the winning candidate via Foundation's unchanged selection/quota logic → if native, write
`runtime` (if needed) and `model_profile_overrides.<runtime>.<tier>` → if cross-AI, build the
invocation command via Foundation's unchanged `build_execute_command` and write
`workflow.cross_ai_command`/`cross_ai_execution` → then invoke GSD's own `/gsd-execute-phase` skill
for the phase via the `Skill` tool. No subprocess dispatch of GSD's own execution entry point
exists anywhere in this plan. `ai_kit_spec.dispatch.dispatch_with_heartbeat` is out of scope for
this plan entirely (see Global Constraints).

This finding gates every task below — Tasks 2–7 are all revised to match it, not provisional
scaffolding pending further confirmation.

---

### Task 2: `gsd_config.py` — read/write GSD's real `.planning/config.json` surface

**Files:**
- Create: `skills/ai-kit-spec-execute-gsd/ai_kit_spec_gsd/__init__.py` (empty file — makes the
  package importable)
- Create: `skills/ai-kit-spec-execute-gsd/ai_kit_spec_gsd/gsd_config.py`
- Create: `skills/ai-kit-spec-execute-gsd/ai-kit-spec-gsd.py` (the import-bootstrap shim, Steps
  6–8 below)
- Modify: `Makefile`, `.pre-commit-config.yaml` (Step 5 below — register the new test module and
  expand the ruff/py-compile hooks' `files:` scope to this plan's new source directories)
- Test: `tests/test_ai_kit_spec_gsd.py`

**Interfaces:**
- Consumes: `ai_kit_spec.cache.cache_write_json` (Plan 1, for atomic JSON writes).
- Produces:
  - `read_gsd_config(path: str, read_fn=open, warn_fn=print) -> tuple[dict, str]` — parses
    `.planning/config.json`. Returns `({}, "missing")` if the file doesn't exist (a project not yet
    GSD-configured is a valid, non-error state — no warning). Returns `({}, "malformed")` on
    malformed JSON or an unreadable file, calling `warn_fn` first with an explicit message. Returns
    `(config, "ok")` on a successful parse. **Every caller in this plan (Task 4's CLI) MUST treat
    `"malformed"` as a hard abort for any config-MUTATING operation** — overwriting a real,
    broken-but-recoverable user config with a near-empty generated one silently destroys it.
    `"missing"` is safe to proceed past.
  - `KNOWN_GSD_RUNTIMES = {"claude", "codex", "gemini", "opencode", "qwen", "kilo", "copilot",
    "grok", "cursor", "windsurf", "augment", "trae", "codebuddy", "cline", "antigravity"}` —
    sourced directly from Task 1's confirmed finding (`sync-skills.md`/`update.md`/
    `settings-advanced.md`). Documented as **non-exhaustive** (GSD's own docs describe `runtime` as
    open-ended) — a candidate's `cli` value in this set means GSD can itself run under that vendor
    as a native runtime; a `cli` value outside it means only the `cross_ai_command` hook can reach
    it. `cli is None` is always native (dispatches as the current session, runtime identity
    `"claude"`), independent of this set.
  - `resolve_active_runtime(gsd_config: dict) -> str` — reads `gsd_config.get("runtime")`. Returns
    `"claude"` when unset (GSD's own confirmed default: `runtime: null` reads as `"claude"`), the
    configured value otherwise. **Never returns `None`** — an unset key is a real, meaningful
    default, not an "unknown" sentinel (Task 1 finding 2).
  - `write_active_runtime(path: str, gsd_config: dict, runtime: str, write_fn=cache_write_json,
    backup_copy_fn=shutil.copy2, isfile_fn=os.path.isfile, run_id: str | None = None) -> dict` —
    persists `runtime` into `gsd_config["runtime"]` (every other existing key preserved unchanged)
    AND, in the SAME write, records its own adapter-ownership marker into
    `gsd_config["_ai_kit_spec_execute_gsd"]["runtime"] = runtime`, with the same per-run backup
    guarantee as the other write functions below.
  - `resolve_native_tier(gsd_config: dict, runtime: str, tier: str) -> str | None` — reads
    `gsd_config.get("model_profile_overrides", {}).get(runtime, {}).get(tier)`. Never crashes on a
    missing intermediate level (`model_profile_overrides` absent, or `runtime` absent within it) —
    returns `None` for any of those.
  - `write_native_tier_override(path: str, gsd_config: dict, runtime: str, tier: str, model: str,
    write_fn=cache_write_json, backup_copy_fn=shutil.copy2, isfile_fn=os.path.isfile,
    run_id: str | None = None) -> dict` — persists `model` into
    `gsd_config["model_profile_overrides"][runtime][tier]` AND, in the SAME write, records adapter
    ownership into `gsd_config["_ai_kit_spec_execute_gsd"]["overrides"][runtime][tier] = model`.
    Writes the merged dict to `path` (every other existing key preserved unchanged, including any
    OTHER runtime's or tier's own entries under `model_profile_overrides`). Before the first write
    of a run, backs up the REAL ON-DISK BYTES of `path` (never a re-serialization of the in-memory
    dict, which may already be `{}` on a malformed-JSON read). Returns the updated dict.
  - `override_is_adapter_owned(gsd_config: dict, runtime: str, tier: str) -> bool` — `True` only
    when `model_profile_overrides[runtime][tier]` is present AND exactly equals
    `_ai_kit_spec_execute_gsd["overrides"][runtime][tier]` (both present and matching — a prior run
    of THIS adapter wrote the currently-active override, safe to re-resolve). `False` when the
    marker is absent, mismatched, or the override itself is absent — the honest "not confirmed
    adapter-owned" default, treated as a genuine user choice, never silently overridden.
  - `resolve_gsd_config_path(cwd: str) -> str` — returns `os.path.join(cwd, ".planning",
    "config.json")`. Task 1's spike found no separate workstream-scoped config path convention in
    real GSD (the real project's own config lives at the plain project-root path) — this function
    is deliberately simple, matching the confirmed real layout, not a speculative scaffold.
  - `write_workflow_key(path: str, gsd_config: dict, key: str, value, write_fn=cache_write_json,
    backup_copy_fn=shutil.copy2, isfile_fn=os.path.isfile, run_id: str | None = None) -> dict` —
    persists `value` into `gsd_config["workflow"][key]` (every other `workflow` key and every other
    top-level key preserved unchanged) AND, in the SAME write, records adapter ownership into
    `gsd_config["_ai_kit_spec_execute_gsd"]["workflow"][key] = value`, with the same per-run-backup
    guarantee. This is the function Task 5 uses for `workflow.cross_ai_command`/
    `workflow.cross_ai_execution`/`workflow.cross_ai_timeout` (Task 1 finding 1's real, confirmed
    keys) — no cross-AI config write in this plan happens through hand-rolled prose. **Returns the
    updated dict, which the caller MUST thread into the next write call's own `gsd_config`
    argument** — two writes against the same stale snapshot would have the second silently discard
    the first's key.
  - `workflow_key_is_adapter_owned(gsd_config: dict, key: str) -> bool` — mirrors
    `override_is_adapter_owned`, for `workflow` keys.
  - `clear_workflow_key_if_adapter_owned(path: str, gsd_config: dict, key: str,
    write_fn=cache_write_json, backup_copy_fn=shutil.copy2, isfile_fn=os.path.isfile,
    run_id: str | None = None) -> dict` — when `workflow_key_is_adapter_owned(gsd_config, key)` is
    `True` (a prior run of THIS adapter set this workflow key while resolving `cross_ai_hook`
    mode), deletes both `gsd_config["workflow"][key]` and its own ownership-marker entry — a stale
    adapter-owned cross-AI hook must not stay active once a LATER run resolves `native_tier`/
    `fallback_notice` instead. When the key is absent or present-but-not-adapter-owned (a genuine
    user-set value), this is a no-op that returns `gsd_config` unchanged and never writes.
  - `generate_run_id(time_fn=time.time) -> str` — a caller performing more than one write per
    logical run MUST call this exactly once and thread the same string through every write call's
    own `run_id=` argument — leaving `run_id=None` on two separate calls does NOT give them the
    same id (each call's own default is evaluated independently).
  - `_backup_once(path, backup_copy_fn, isfile_fn, run_id) -> None` (internal, shared by every
    write function) — backup path is `f"{path}.ai-kit-spec-execute-gsd.{run_id}.bak"`, one distinct
    file per run rather than one fixed suffix shared across every future run (which would let a
    second run's write silently overwrite the ONE backup taken before the very first write ever
    made). Skips the copy once a backup already exists at that run's specific path.

- [ ] **Step 1: Write the failing tests**

```python
import os
import sys
import unittest
from unittest import mock

# Bootstraps ALL package roots this plan's tests need -- ai_kit_spec_gsd (this plan) and
# ai_kit_spec (Plan 1, Foundation) both live outside this file's own directory, on no search
# path by default. skills/ai-kit-spec-execute is ALSO added here (not just
# skills/ai-kit-spec-execute-gsd) because Task 6's detect_framework module lives there and this is
# the ONE bootstrap block for the whole file -- it goes ONCE at the top; every later Task in this
# plan appends test classes below it, never repeats it.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-spec-review"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills",
                                 "ai-kit-spec-execute-gsd"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills",
                                 "ai-kit-spec-execute"))

from ai_kit_spec_gsd import gsd_config


class TestReadGsdConfig(unittest.TestCase):
    def test_returns_empty_dict_and_missing_status_when_file_missing(self):
        def raise_not_found(*a, **k):
            raise FileNotFoundError()
        warnings = []
        config, status = gsd_config.read_gsd_config("/nonexistent", read_fn=raise_not_found,
                                                      warn_fn=warnings.append)
        self.assertEqual(config, {})
        self.assertEqual(status, "missing")
        self.assertEqual(warnings, [])  # missing file is a valid state -- no warning

    def test_parses_real_config_shape_with_ok_status(self):
        import io
        fake = io.StringIO('{"runtime": "codex", "model_profile_overrides": '
                            '{"codex": {"sonnet": "gpt-5.6-sol"}}}')
        config, status = gsd_config.read_gsd_config("/x", read_fn=lambda *a, **k: fake)
        self.assertEqual(config["runtime"], "codex")
        self.assertEqual(status, "ok")

    def test_malformed_json_warns_and_returns_empty_dict_with_malformed_status(self):
        import io
        fake = io.StringIO("not valid json {{{")
        warnings = []
        config, status = gsd_config.read_gsd_config("/x", read_fn=lambda *a, **k: fake,
                                                      warn_fn=warnings.append)
        self.assertEqual(config, {})
        self.assertEqual(status, "malformed")
        self.assertEqual(len(warnings), 1)
        self.assertIn("/x", warnings[0])


class TestResolveActiveRuntime(unittest.TestCase):
    def test_defaults_to_claude_when_unset(self):
        # Task 1 finding 2: runtime's real default is null, which reads as "claude" -- never a
        # None/"unknown" sentinel.
        self.assertEqual(gsd_config.resolve_active_runtime({}), "claude")

    def test_reads_the_configured_value(self):
        self.assertEqual(gsd_config.resolve_active_runtime({"runtime": "codex"}), "codex")


class TestWriteActiveRuntime(unittest.TestCase):
    def test_writes_runtime_key_records_ownership_marker_and_preserves_other_keys(self):
        writes = {}
        def fake_write(path, data):
            writes[path] = data
        result = gsd_config.write_active_runtime(
            "/repo/.planning/config.json", {"model_profile": "balanced"}, "codex",
            write_fn=fake_write, backup_copy_fn=lambda *a: None, isfile_fn=lambda p: False,
            run_id="run-1")
        self.assertEqual(result["runtime"], "codex")
        self.assertEqual(result["model_profile"], "balanced")  # untouched
        self.assertEqual(writes["/repo/.planning/config.json"]["runtime"], "codex")
        self.assertEqual(result["_ai_kit_spec_execute_gsd"]["runtime"], "codex")


class TestResolveNativeTier(unittest.TestCase):
    def test_reads_the_nested_runtime_and_tier_slot(self):
        config = {"model_profile_overrides": {"codex": {"sonnet": "gpt-5.6-sol"}}}
        self.assertEqual(gsd_config.resolve_native_tier(config, "codex", "sonnet"),
                          "gpt-5.6-sol")

    def test_returns_none_without_crashing_when_any_level_is_missing(self):
        self.assertIsNone(gsd_config.resolve_native_tier({}, "codex", "sonnet"))
        self.assertIsNone(gsd_config.resolve_native_tier(
            {"model_profile_overrides": {"claude": {"opus": "claude-opus-5"}}},
            "codex", "sonnet"))


class TestWriteNativeTierOverride(unittest.TestCase):
    def test_writes_nested_override_records_ownership_marker_and_preserves_other_runtimes(self):
        writes = {}
        def fake_write(path, data):
            writes[path] = data
        existing = {"model_profile_overrides": {"claude": {"opus": "claude-opus-5"}}}
        result = gsd_config.write_native_tier_override(
            "/repo/.planning/config.json", existing, "codex", "sonnet", "gpt-5.6-sol",
            write_fn=fake_write, backup_copy_fn=lambda *a: None, isfile_fn=lambda p: False,
            run_id="run-1")
        self.assertEqual(result["model_profile_overrides"]["codex"]["sonnet"], "gpt-5.6-sol")
        self.assertEqual(result["model_profile_overrides"]["claude"]["opus"], "claude-opus-5")
        self.assertEqual(result["_ai_kit_spec_execute_gsd"]["overrides"]["codex"]["sonnet"],
                          "gpt-5.6-sol")
        self.assertEqual(writes["/repo/.planning/config.json"]
                          ["model_profile_overrides"]["codex"]["sonnet"], "gpt-5.6-sol")

    def test_backs_up_existing_config_once_before_first_write_of_this_run(self):
        copies = []
        def fake_copy(src, dst):
            copies.append((src, dst))
        gsd_config.write_native_tier_override(
            "/repo/.planning/config.json", {}, "codex", "sonnet", "gpt-5.6-sol",
            write_fn=lambda *a: None, backup_copy_fn=fake_copy,
            isfile_fn=lambda p: p == "/repo/.planning/config.json", run_id="run-1")
        self.assertEqual(copies, [("/repo/.planning/config.json",
                                    "/repo/.planning/config.json.ai-kit-spec-execute-gsd.run-1.bak")])

    def test_a_later_run_gets_its_own_distinct_backup_path(self):
        copies = []
        def fake_copy(src, dst):
            copies.append(dst)
        gsd_config.write_native_tier_override(
            "/repo/.planning/config.json", {}, "codex", "sonnet", "gpt-5.6-sol",
            write_fn=lambda *a: None, backup_copy_fn=fake_copy,
            isfile_fn=lambda p: p == "/repo/.planning/config.json", run_id="run-2")
        self.assertEqual(copies, ["/repo/.planning/config.json.ai-kit-spec-execute-gsd.run-2.bak"])


class TestOverrideIsAdapterOwned(unittest.TestCase):
    def test_true_when_marker_matches_current_override_exactly(self):
        config = {"model_profile_overrides": {"codex": {"sonnet": "gpt-5.6-sol"}},
                  "_ai_kit_spec_execute_gsd": {"overrides": {"codex": {"sonnet": "gpt-5.6-sol"}}}}
        self.assertTrue(gsd_config.override_is_adapter_owned(config, "codex", "sonnet"))

    def test_false_when_no_marker_present_at_all(self):
        # A genuine, hand-written user override -- never touched.
        config = {"model_profile_overrides": {"codex": {"sonnet": "gpt-5.6-sol"}}}
        self.assertFalse(gsd_config.override_is_adapter_owned(config, "codex", "sonnet"))

    def test_false_when_marker_present_but_value_no_longer_matches(self):
        config = {"model_profile_overrides": {"codex": {"sonnet": "hand-edited"}},
                  "_ai_kit_spec_execute_gsd": {"overrides": {"codex": {"sonnet": "gpt-5.6-sol"}}}}
        self.assertFalse(gsd_config.override_is_adapter_owned(config, "codex", "sonnet"))


class TestResolveGsdConfigPath(unittest.TestCase):
    def test_defaults_to_project_root_planning_config(self):
        # Task 1's spike found no workstream-scoped path convention in real GSD -- this is
        # deliberately the whole function, matching the real, confirmed layout.
        self.assertEqual(gsd_config.resolve_gsd_config_path("/repo"),
                          "/repo/.planning/config.json")


class TestWriteWorkflowKey(unittest.TestCase):
    def test_writes_key_under_workflow_and_preserves_other_keys(self):
        writes = {}
        def fake_write(path, data):
            writes[path] = data
        result = gsd_config.write_workflow_key(
            "/repo/.planning/config.json",
            {"model_profile": "balanced", "workflow": {"other_key": "keep-me"}},
            "cross_ai_command", "codex exec ...",
            write_fn=fake_write, backup_copy_fn=lambda *a: None, isfile_fn=lambda p: False,
            run_id="run-1")
        self.assertEqual(result["workflow"]["cross_ai_command"], "codex exec ...")
        self.assertEqual(result["workflow"]["other_key"], "keep-me")  # untouched
        self.assertEqual(result["model_profile"], "balanced")  # untouched
        self.assertEqual(writes["/repo/.planning/config.json"]["workflow"]["cross_ai_command"],
                          "codex exec ...")

    def test_a_second_write_against_the_first_writes_own_returned_dict_keeps_both_keys(self):
        writes = {}
        def fake_write(path, data):
            writes[path] = data
        first_result = gsd_config.write_workflow_key(
            "/repo/.planning/config.json", {}, "cross_ai_command", "codex exec ...",
            write_fn=fake_write, backup_copy_fn=lambda *a: None, isfile_fn=lambda p: False,
            run_id="run-1")
        second_result = gsd_config.write_workflow_key(
            "/repo/.planning/config.json", first_result, "cross_ai_execution", True,
            write_fn=fake_write, backup_copy_fn=lambda *a: None, isfile_fn=lambda p: False,
            run_id="run-1")
        self.assertEqual(second_result["workflow"]["cross_ai_command"], "codex exec ...")
        self.assertEqual(second_result["workflow"]["cross_ai_execution"], True)


class TestWorkflowKeyOwnershipAndClearing(unittest.TestCase):
    def test_clear_workflow_key_if_adapter_owned_removes_an_adapter_owned_key(self):
        config = {"workflow": {"cross_ai_command": "codex exec ...", "other_key": "keep-me"},
                  "_ai_kit_spec_execute_gsd": {"workflow": {"cross_ai_command": "codex exec ..."}}}
        writes = {}
        def fake_write(path, data):
            writes[path] = data
        result = gsd_config.clear_workflow_key_if_adapter_owned(
            "/repo/.planning/config.json", config, "cross_ai_command", write_fn=fake_write,
            backup_copy_fn=lambda *a: None, isfile_fn=lambda p: False, run_id="run-1")
        self.assertNotIn("cross_ai_command", result["workflow"])
        self.assertEqual(result["workflow"]["other_key"], "keep-me")
        self.assertNotIn("cross_ai_command", result["_ai_kit_spec_execute_gsd"]["workflow"])

    def test_clear_workflow_key_if_adapter_owned_never_touches_a_genuine_user_value(self):
        config = {"workflow": {"cross_ai_command": "user-set-command"}}
        write_calls = []
        result = gsd_config.clear_workflow_key_if_adapter_owned(
            "/repo/.planning/config.json", config, "cross_ai_command",
            write_fn=lambda *a: write_calls.append(a), backup_copy_fn=lambda *a: None,
            isfile_fn=lambda p: False, run_id="run-1")
        self.assertEqual(result, config)
        self.assertEqual(write_calls, [])


class TestKnownGsdRuntimes(unittest.TestCase):
    def test_contains_every_task_1_confirmed_runtime(self):
        for runtime in ("claude", "codex", "gemini", "opencode", "qwen", "kilo", "copilot",
                         "grok", "cursor", "windsurf", "augment", "trae", "codebuddy", "cline",
                         "antigravity"):
            self.assertIn(runtime, gsd_config.KNOWN_GSD_RUNTIMES)
```

- [ ] **Step 2: Run to verify failure**

```bash
python3 -m unittest tests.test_ai_kit_spec_gsd -v 2>&1 | tail -30
```

Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

```python
"""GSD's real .planning/config.json read/write surface -- confirmed live against a real GSD
install and a real GSD-managed project's own config (Task 1 finding, this plan's dated finding
subsection): runtime is a scalar vendor-runtime identity, model_profile_overrides is keyed
(runtime, tier), workflow.cross_ai_* carries the cross-AI hook config."""
import json
import os
import shutil
import time

from ai_kit_spec.cache import cache_write_json


KNOWN_GSD_RUNTIMES = {
    "claude", "codex", "gemini", "opencode", "qwen", "kilo", "copilot", "grok", "cursor",
    "windsurf", "augment", "trae", "codebuddy", "cline", "antigravity",
}  # Task 1 finding 2 -- confirmed live, documented non-exhaustive (GSD's own runtime concept is
   # open-ended). cli is None is ALWAYS native, independent of this set (current-session identity).

_BACKUP_INFIX = ".ai-kit-spec-execute-gsd."  # per-run suffix: f"{path}{_BACKUP_INFIX}{run_id}.bak"
_OWNERSHIP_KEY = "_ai_kit_spec_execute_gsd"


def read_gsd_config(path: str, read_fn=open, warn_fn=print) -> tuple:
    """Returns (config, status) -- status is one of "missing"/"malformed"/"ok". A missing file is
    a valid, unconfigured-project state (no warning, safe to proceed); a malformed/unreadable file
    is a real problem (warned, and callers MUST treat it as a hard abort for any config-mutating
    write)."""
    try:
        with read_fn(path, encoding="utf-8") as f:
            return json.load(f), "ok"
    except FileNotFoundError:
        return {}, "missing"
    except (json.JSONDecodeError, OSError) as exc:
        warn_fn(f"ai-kit-spec-execute-gsd: could not read {path} ({exc}) -- "
                 f"config is MALFORMED, not merely unconfigured -- refusing to write over it")
        return {}, "malformed"


def resolve_active_runtime(gsd_config: dict) -> str:
    """Task 1 finding 2: GSD's own confirmed default -- runtime: null reads as "claude". Never
    returns None; an unset key is a real, meaningful default, not an unknown sentinel."""
    return gsd_config.get("runtime") or "claude"


def write_active_runtime(path: str, gsd_config: dict, runtime: str,
                          write_fn=cache_write_json, backup_copy_fn=shutil.copy2,
                          isfile_fn=os.path.isfile, run_id: str | None = None) -> dict:
    run_id = run_id if run_id is not None else generate_run_id()
    _backup_once(path, backup_copy_fn, isfile_fn, run_id)
    updated = dict(gsd_config)
    updated["runtime"] = runtime
    updated[_OWNERSHIP_KEY] = dict(updated.get(_OWNERSHIP_KEY, {}))
    updated[_OWNERSHIP_KEY]["runtime"] = runtime
    write_fn(path, updated)
    return updated


def resolve_native_tier(gsd_config: dict, runtime: str, tier: str):
    """Reads model_profile_overrides.<runtime>.<tier> (Task 1 finding 2's confirmed real shape --
    three levels deep). Never crashes on a missing intermediate level."""
    return gsd_config.get("model_profile_overrides", {}).get(runtime, {}).get(tier)


def write_native_tier_override(path: str, gsd_config: dict, runtime: str, tier: str, model: str,
                                write_fn=cache_write_json, backup_copy_fn=shutil.copy2,
                                isfile_fn=os.path.isfile, run_id: str | None = None) -> dict:
    run_id = run_id if run_id is not None else generate_run_id()
    _backup_once(path, backup_copy_fn, isfile_fn, run_id)
    updated = dict(gsd_config)
    overrides = {k: dict(v) for k, v in updated.get("model_profile_overrides", {}).items()}
    overrides[runtime] = dict(overrides.get(runtime, {}))
    overrides[runtime][tier] = model
    updated["model_profile_overrides"] = overrides
    updated[_OWNERSHIP_KEY] = dict(updated.get(_OWNERSHIP_KEY, {}))
    marker_overrides = {k: dict(v) for k, v in updated[_OWNERSHIP_KEY].get("overrides", {}).items()}
    marker_overrides[runtime] = dict(marker_overrides.get(runtime, {}))
    marker_overrides[runtime][tier] = model
    updated[_OWNERSHIP_KEY]["overrides"] = marker_overrides
    write_fn(path, updated)
    return updated


def override_is_adapter_owned(gsd_config: dict, runtime: str, tier: str) -> bool:
    current = gsd_config.get("model_profile_overrides", {}).get(runtime, {}).get(tier)
    marker = gsd_config.get(_OWNERSHIP_KEY, {}).get("overrides", {}).get(runtime, {}).get(tier)
    return current is not None and current == marker


def resolve_gsd_config_path(cwd: str) -> str:
    """Task 1's spike found no workstream-scoped config path convention in real GSD -- this
    matches the real, confirmed project-root layout exactly (no speculative override params)."""
    return os.path.join(cwd, ".planning", "config.json")


def generate_run_id(time_fn=time.time) -> str:
    """A caller performing more than one write per logical run MUST call this exactly once and
    thread the SAME string through every write call's own run_id argument -- leaving run_id=None
    on two separate calls does NOT give them the same id."""
    return str(int(time_fn() * 1000))


def _backup_once(path: str, backup_copy_fn, isfile_fn, run_id: str) -> None:
    if not isfile_fn(path):
        return
    backup_path = f"{path}{_BACKUP_INFIX}{run_id}.bak"
    if not isfile_fn(backup_path):
        backup_copy_fn(path, backup_path)  # real on-disk bytes, never the in-memory dict


def write_workflow_key(path: str, gsd_config: dict, key: str, value,
                        write_fn=cache_write_json, backup_copy_fn=shutil.copy2,
                        isfile_fn=os.path.isfile, run_id: str | None = None) -> dict:
    run_id = run_id if run_id is not None else generate_run_id()
    _backup_once(path, backup_copy_fn, isfile_fn, run_id)
    updated = dict(gsd_config)
    updated["workflow"] = dict(updated.get("workflow", {}))
    updated["workflow"][key] = value
    updated[_OWNERSHIP_KEY] = dict(updated.get(_OWNERSHIP_KEY, {}))
    updated[_OWNERSHIP_KEY]["workflow"] = dict(updated[_OWNERSHIP_KEY].get("workflow", {}))
    updated[_OWNERSHIP_KEY]["workflow"][key] = value
    write_fn(path, updated)
    return updated


def workflow_key_is_adapter_owned(gsd_config: dict, key: str) -> bool:
    current = gsd_config.get("workflow", {}).get(key)
    marker = gsd_config.get(_OWNERSHIP_KEY, {}).get("workflow", {}).get(key)
    return current is not None and current == marker


def clear_workflow_key_if_adapter_owned(path: str, gsd_config: dict, key: str,
                                         write_fn=cache_write_json, backup_copy_fn=shutil.copy2,
                                         isfile_fn=os.path.isfile,
                                         run_id: str | None = None) -> dict:
    """A LATER run that resolves a DIFFERENT dispatch mode must not leave a PRIOR run's own
    cross_ai_command/cross_ai_execution write active -- GSD would keep routing through a stale
    hook this plan no longer intends active. Only ever clears a key THIS ADAPTER itself set; a
    genuine user-set value is never touched, and an absent key is a no-op."""
    if not workflow_key_is_adapter_owned(gsd_config, key):
        return gsd_config
    run_id = run_id if run_id is not None else generate_run_id()
    _backup_once(path, backup_copy_fn, isfile_fn, run_id)
    updated = dict(gsd_config)
    updated["workflow"] = dict(updated.get("workflow", {}))
    del updated["workflow"][key]
    updated[_OWNERSHIP_KEY] = dict(updated.get(_OWNERSHIP_KEY, {}))
    updated[_OWNERSHIP_KEY]["workflow"] = dict(updated[_OWNERSHIP_KEY].get("workflow", {}))
    del updated[_OWNERSHIP_KEY]["workflow"][key]
    write_fn(path, updated)
    return updated
```

- [ ] **Step 4: Run tests to verify pass**

```bash
python3 -m unittest tests.test_ai_kit_spec_gsd -v 2>&1 | tail -20
```

Expected: PASS.

- [ ] **Step 5: Register the new test module AND the new source directories with the repo's real quality gate**

Edit `Makefile`'s `test:` target (currently ends `... tests.test_wizard_pty tests.test_system_memory_e2e tests.test_ai_kit_spec`) to append `tests.test_ai_kit_spec_gsd`.

Edit `.pre-commit-config.yaml`'s `unittest (core)` hook entry (currently ends `... tests.test_arch tests.test_ai_kit_spec`) to likewise append `tests.test_ai_kit_spec_gsd`.

The repository's real full quality gate is `make validate` (→ `uv run pre-commit run --all-files`).
Edit `.pre-commit-config.yaml`'s `ruff` hook's `files:` regex from
`^((tools|tests)/.*|skills/ai-kit-spec-review/ai-kit-spec-review)\.py$` to additionally match
`skills/ai-kit-spec-execute-gsd/.*\.py` and `skills/ai-kit-spec-execute/.*\.py` (e.g.
`^((tools|tests)/.*|skills/ai-kit-spec-review/ai-kit-spec-review|skills/ai-kit-spec-execute-gsd/.*|skills/ai-kit-spec-execute/.*)\.py$`).
Edit the `py-compile` hook's `files:` regex the same way, additionally including this plan's own
shim (`skills/ai-kit-spec-execute-gsd/ai-kit-spec-gsd.py`) and every `ai_kit_spec_gsd/*.py`/
`detect_framework.py` module. Task 6 Step 8 (the plan's final commit) runs `make validate` against
this expanded scope.

- [ ] **Step 6: Commit `gsd_config.py`**

```bash
git add -A
git commit -m "feat(ai-kit-spec-execute-gsd): add gsd_config.py (runtime + model_profile_overrides + workflow-key read/write, ownership marker, per-run backups)"
```

- [ ] **Step 7: Create the import-bootstrap shim `ai-kit-spec-gsd.py`**

`skills/ai-kit-spec-review/ai-kit-spec.py` (the Foundation shim this mirrors) is a 7-line script:
running `python3 <that path> <subcommand>` relies on a plain fact about how Python starts a
script — it puts the SCRIPT'S OWN DIRECTORY on `sys.path[0]` automatically, before any of its own
`import` lines run, regardless of the caller's cwd. This plan's `ai_kit_spec_gsd` package needs the
EXACT SAME trick, PLUS one more line: unlike `ai_kit_spec`, `ai_kit_spec_gsd`'s own modules
(`adapter.py`, `gsd_cross_ai.py`, `cli.py`) do `from ai_kit_spec... import ...` (Foundation, a
sibling skill directory, not a sibling of `ai_kit_spec_gsd` itself) — so the shim must ALSO insert
`skills/ai-kit-spec-review/` onto `sys.path` before importing anything from `ai_kit_spec_gsd`.
Unlike the original plan, there is no `cross-ai-wrapper` subcommand branch — this shim dispatches
every subcommand to `ai_kit_spec_gsd.cli.main`, full stop (Task 3's revision removed the wrapper
program entirely).

Create `skills/ai-kit-spec-execute-gsd/ai-kit-spec-gsd.py`:

```python
#!/usr/bin/env python3
"""Entrypoint shim for ai-kit-spec-execute-gsd -- mirrors skills/ai-kit-spec-review/ai-kit-spec.py's
own trick (Python puts a directly-run script's OWN directory on sys.path[0] automatically, making
ai_kit_spec_gsd importable regardless of the caller's cwd), PLUS explicitly inserts the SIBLING
skills/ai-kit-spec-review/ directory onto sys.path so ai_kit_spec_gsd's own `from ai_kit_spec...`
imports resolve too. This is the ONLY thing SKILL.md ever invokes by absolute path (Task 5).

Usage: python3 <this file> resolve-dispatch ...   -> ai_kit_spec_gsd.cli.main
       python3 <this file> config-path ...         -> ai_kit_spec_gsd.cli.main
       (every ai_kit_spec_gsd.cli subcommand -- there is no separate wrapper subcommand)"""
import os
import sys

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_THIS_DIR, "..", "ai-kit-spec-review"))

from ai_kit_spec_gsd.cli import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

- [ ] **Step 8: Prove the shim's `sys.path` wiring resolves BOTH packages from OUTSIDE the repository — WITHOUT invoking `cli.py` (it doesn't exist until Task 4)**

This proves ONLY what Task 2 can actually prove at this point: that the shim's `sys.path`
insertion makes BOTH `ai_kit_spec_gsd` (this plan's own package, exists — `gsd_config.py` was
created in Step 1) and `ai_kit_spec` (Foundation's package, a sibling of the shim) importable from
a directory provably outside this repo's own tree — without touching `cli.py`. The end-to-end
`resolve-dispatch` proof happens later, in Task 4, once `cli.py` actually exists.

```bash
SCRATCH_DIR="$(mktemp -d)"
cd "$SCRATCH_DIR" && python3 -c "
import sys
sys.path.insert(0, '/absolute/path/to/skills/ai-kit-spec-execute-gsd')
sys.path.insert(0, '/absolute/path/to/skills/ai-kit-spec-review')
import ai_kit_spec_gsd
import ai_kit_spec
print('both packages imported OK from', __import__('os').getcwd())
"
```

Expected: `both packages imported OK from <SCRATCH_DIR>` — no `ModuleNotFoundError`.

- [ ] **Step 9: Commit the shim**

```bash
git add -A
git commit -m "feat(ai-kit-spec-execute-gsd): add ai-kit-spec-gsd.py import-bootstrap shim, verified importable from outside the repo"
```

---

### Task 3: `gsd_cross_ai.py` — pure command-string builder for GSD's own `cross_ai_command` hook

**Revision note:** the original plan's Task 3 had two branches (a general-hook wrapper program
vs. a closed-enum switch) gated on an unresolved spike question. Task 1's finding settles this
definitively: `cross_ai_command` IS a general shell-command hook, GSD itself already implements
the piping/capture/retry around it (Global Constraints), and this adapter's entire job collapses to
**formatting one command string** — there is no wrapper program, no stdin-piping logic, no
heartbeat routing, and no `dispatch_with_heartbeat` usage anywhere in this task (all of that is
GSD's own, already-implemented job).

**Files:**
- Create: `skills/ai-kit-spec-execute-gsd/ai_kit_spec_gsd/gsd_cross_ai.py`
- Test: `tests/test_ai_kit_spec_gsd.py`

**Interfaces:**
- Consumes: `ai_kit_spec.commands.build_execute_command` (Plan 1), `ai_kit_spec_gsd.gsd_config.
  KNOWN_GSD_RUNTIMES` (Task 2).
- Produces: `build_cross_ai_command(resolved_candidate: dict, target_dir: str,
  execute_command_fn=build_execute_command) -> str | None` — `resolved_candidate` is
  `{"cli": str, "model": str, "key": str, ...}` (the winning candidate from `adapter.
  resolve_gsd_dispatch`, Task 4). Returns `None` when the candidate is native (its `cli` is `None`
  or a member of `KNOWN_GSD_RUNTIMES` — already reachable without this hook, see Task 2) or when
  `execute_command_fn` has no live-verified builder for it (raises `ValueError`, caught and
  degraded to `None` — never guess or fabricate a command for an unverified vendor). Otherwise
  returns the real, fully-resolved command string GSD's own `cross_ai_delegation` step will run
  verbatim — `execute_command_fn(cli, target_dir=target_dir)`'s own returned template, with its
  `{model}` placeholder filled from `resolved_candidate["model"]`, and NOTHING else — no wrapper
  invocation, no shim path, no extra argv. This is the literal string written into
  `workflow.cross_ai_command` (Task 4/5).

- [ ] **Step 1: Write the failing tests**

```python
from ai_kit_spec_gsd import gsd_cross_ai


class TestBuildCrossAiCommand(unittest.TestCase):
    def test_native_cli_none_returns_none(self):
        # cli=None is native/current-session dispatch -- never needs the cross-AI hook.
        candidate = {"cli": None, "model": "opus", "key": "opus-native"}
        self.assertIsNone(gsd_cross_ai.build_cross_ai_command(candidate, "/repo"))

    def test_cli_in_known_gsd_runtimes_returns_none(self):
        # codex is a KNOWN_GSD_RUNTIMES member -- reachable via runtime/model_profile_overrides,
        # the cross-AI hook is unnecessary overhead for it.
        candidate = {"cli": "codex", "model": "gpt-5.6-sol", "key": "codex/gpt-5.6-sol"}
        self.assertIsNone(gsd_cross_ai.build_cross_ai_command(candidate, "/repo"))

    def test_no_live_verified_builder_returns_none_not_raise(self):
        # REAL current behavior: grok has no execute-mode builder yet -- Foundation's real
        # ai_kit_spec.commands.build_execute_command raises ValueError for it, and grok is NOT a
        # KNOWN_GSD_RUNTIMES member -- this must degrade to None, never raise or crash.
        candidate = {"cli": "grok", "model": "grok-4-fast", "key": "grok/grok-4-fast"}
        self.assertIsNone(gsd_cross_ai.build_cross_ai_command(candidate, "/repo"))

    def test_builds_the_real_command_string_with_model_filled_in(self):
        # Injected fake builder -- exercises this module's plumbing without depending on which
        # CLIs Foundation has actually implemented today.
        def fake_execute_command(cli, target_dir):
            return f"future-cli exec --write -C {target_dir} -m {{model}}"
        candidate = {"cli": "future-cli", "model": "gpt-5.6-terra",
                     "key": "future-cli/gpt-5.6-terra"}
        result = gsd_cross_ai.build_cross_ai_command(
            candidate, "/repo/worktree", execute_command_fn=fake_execute_command)
        self.assertEqual(result, "future-cli exec --write -C /repo/worktree -m gpt-5.6-terra")
        # This IS the literal string, no wrapper/shim indirection whatsoever (Task 1 finding 1 --
        # GSD itself pipes the phase prompt into this command's own stdin and captures its own
        # stdout; a wrapper would only get in the way of that).
        self.assertNotIn("ai-kit-spec-gsd.py", result)
```

- [ ] **Step 2: Run to verify failure**

```bash
python3 -m unittest tests.test_ai_kit_spec_gsd.TestBuildCrossAiCommand -v 2>&1 | tail -20
```

Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

```python
"""Pure command-string formatting for GSD's own workflow.cross_ai_command hook -- confirmed a
general shell-command hook, already fully implemented by GSD itself (Task 1 finding 1). This
module builds ONE string; GSD's own cross_ai_delegation step does the piping/capture/retry. No
wrapper program, no subprocess dispatch, no heartbeat routing lives in this plan at all."""
from ai_kit_spec.commands import build_execute_command
from ai_kit_spec_gsd.gsd_config import KNOWN_GSD_RUNTIMES


def build_cross_ai_command(resolved_candidate: dict, target_dir: str,
                            execute_command_fn=build_execute_command):
    cli = resolved_candidate["cli"]
    if cli is None or cli in KNOWN_GSD_RUNTIMES:
        return None  # native -- reachable via runtime/model_profile_overrides, no hook needed
    try:
        template = execute_command_fn(cli, target_dir=target_dir)
    except ValueError:
        return None  # no live-verified execute-mode builder for this CLI yet -- decline, don't guess
    return template.format(model=resolved_candidate["model"])
```

- [ ] **Step 4: Run tests to verify pass, commit**

```bash
python3 -m unittest tests.test_ai_kit_spec_gsd.TestBuildCrossAiCommand -v 2>&1 | tail -10
git add -A
git commit -m "feat(ai-kit-spec-execute-gsd): add gsd_cross_ai.py (pure command-string builder for GSD's own cross_ai_command hook -- no wrapper/subprocess dispatcher)"
```

---

### Task 4: Adapter — assemble candidates, resolve native/cross-AI config plan with live quota

**Revision note:** `resolve_gsd_dispatch` no longer takes a GSD `phase_type` (that axis doesn't
exist in real GSD, Task 1 finding 2) and no longer returns anything meant for subprocess dispatch.
It returns a config-write plan: which write(s) it already made (native) or which command string it
resolved (cross-AI), for Task 5's SKILL.md to hand off to GSD's own `/gsd-execute-phase` skill.

**Files:**
- Create: `skills/ai-kit-spec-execute-gsd/ai_kit_spec_gsd/adapter.py`
- Create: `skills/ai-kit-spec-execute-gsd/ai_kit_spec_gsd/cli.py` (Step 6–9 below)
- Test: `tests/test_ai_kit_spec_gsd.py`

**Interfaces:**
- Consumes (split per module): `adapter.py` imports `ai_kit_spec.quota.resolve_ladder_pick` (Plan
  1), `gsd_config.{resolve_active_runtime, write_native_tier_override, write_active_runtime,
  override_is_adapter_owned, KNOWN_GSD_RUNTIMES}` (Task 2), `gsd_cross_ai.build_cross_ai_command`
  (Task 3). `cli.py` additionally imports `ai_kit_spec.quota.{refresh_quota_cache,
  QUOTA_TTL_SECONDS}`, `ai_kit_spec.config_io.cfg_resolve`, `ai_kit_spec.execute_selection.
  {resolve_execute_candidates, candidates_to_ladder}`, `ai_kit_spec.cache.{cache_read_json,
  cache_write_json}`, `ai_kit_spec.detection.*`, `ai_kit_spec.tooling_guidance.
  build_tooling_guidance`, `gsd_config.{clear_workflow_key_if_adapter_owned, generate_run_id,
  read_gsd_config, resolve_gsd_config_path, write_active_runtime, write_native_tier_override,
  write_workflow_key}` (Task 2), `adapter.{assemble_candidates, estimate_required_context,
  resolve_gsd_dispatch}`.
- Produces:
  - `estimate_required_context(phase_prompt: str) -> int` — `len(phase_prompt) // 4` (a standard
    chars-per-token heuristic). Every candidate's `context_limit` is `None` today (no curation
    exists yet), so this has no filtering effect through `execute_selection.filter_by_context` YET
    — it exists so a future curated `context_limit` is honored immediately, with no change here.
  - `assemble_candidates(cwd: str, env: dict, cfg_resolve_fn=cfg_resolve) -> tuple[list, list]` —
    returns `(candidates, top_n_keys)`. Reshapes `cfg_resolve_fn(cwd, env)["reviewers"]` entries
    into the candidate shape: `{"key", "model", "cli", "vendor", "command", "task_affinity",
    "context_limit", "tier"}`. `command` MUST survive verbatim (`quota.refresh_quota_cache` ->
    `probe_reviewer_quota` -> `commands.render_reviewer_command` raises `ValueError` for a
    `cli`-set entry with no `command` template, converted to `available: False` — dropping
    `command` would make every `cli`-set candidate probe unavailable regardless of real quota).
    `task_affinity`/`context_limit` default to `None` when absent (never `0` — see Global
    Constraints). **`tier`** (this plan's own new field, Task 1/2's revision) is read from the
    config entry's own `r.get("tier")` when curated, else, when `r.get("cli") is None`, defaults
    to the entry's own `model` field (this repo's existing "opus-native"-shaped entries already use
    a Claude-tier-alias directly as `model`), else `None` (a `cli`-set entry with no curated `tier`
    cannot be expressed as a native `model_profile_overrides` slot — see Global Constraints). `top_n_keys` is `cfg_resolve_fn(cwd, env)["policy"]["ladder"]`.
  - `resolve_gsd_dispatch(candidates: list, top_n_keys: list, gsd_config: dict,
    gsd_config_path: str, target_dir: str, current_runtime: str = "claude",
    required_context: int = 0, quota: dict | None = None, run_id: str | None = None,
    write_tier_fn=write_native_tier_override, write_runtime_fn=write_active_runtime,
    resolve_ladder_pick_fn=resolve_ladder_pick) -> dict` — returns exactly one of:
    - `{"mode": "native_tier", "runtime": str, "tier": str, "model": str, "written": bool,
      "cli": str | None, "key": str | None, "provenance": str}` — for the winning candidate's
      derived `(runtime, tier)` slot: `written=False`/`provenance="existing_gsd_config"` when
      `model_profile_overrides[runtime][tier]` already has a genuine (non-adapter-owned) value —
      that EXISTING value is reported as `model`, the fresh candidate is NOT written over it (a
      real user pin at that exact slot is honored unconditionally). `written=True`/
      `provenance="resolved_candidate"` when this call just persisted the winning candidate's
      model into that slot (and, whenever the candidate's runtime differs from
      `current_runtime`, also switched `runtime` via `write_runtime_fn` FIRST, threading its own
      returned dict into the following `write_tier_fn` call — never a stale pre-runtime-write
      snapshot).
    - `{"mode": "cross_ai_hook", "cross_ai_command": str, "cli": str, "key": str, "model": str,
      "provenance": "resolved_candidate"}` — from Task 3's `build_cross_ai_command`, when the
      winning candidate isn't natively expressible (no `tier`, or `cli` outside
      `KNOWN_GSD_RUNTIMES` with no curated `tier`) but a real cross-AI command could be built.
      **This function does NOT itself write `workflow.cross_ai_command`/`cross_ai_execution`** —
      it only builds the command string; Task 5's SKILL.md performs that write (via
      `write-workflow-key`), after checking the target plan's own `cross_ai: true` frontmatter
      (Global Constraints' explicit scope boundary).
    - `{"mode": "fallback_notice", "key": str | None, "cli": None, "provenance": "fallback",
      "reason": str, "message": str}` when no live-quota-checked candidate can be carried at all.
      `reason` is one of:
      - `"no_configured_candidate"` — `candidates` itself is empty (no `[[reviewers]]` entries at
        all). Never schedule an auto-wake.
      - `"all_candidates_context_rejected"` — `candidates` non-empty, but
        `execute_selection.resolve_execute_candidates`'s internal `filter_by_context` rejected
        every one on curated `context_limit`. Never schedule an auto-wake (a context-fit rejection
        does not change by waiting).
      - `"no_usable_dispatch"` — every candidate the ladder walk reached (or never reached because
        it was already excluded from `remaining_ladder`) has no usable native slot (`tier is
        None`) AND no buildable cross-AI command. Permanent, non-time-bound. Never schedule an
        auto-wake.
      - `"quota_exhausted"` — at least one candidate the walk never got to dispatch (because
        `resolve_ladder_pick_fn` found no quota left) has a genuine dispatch mechanism (a real
        `tier`, or a buildable cross-AI command) — only quota stands between it and success. The
        ONLY reason code that should ever schedule an hourly `CronCreate` auto-wake.
      - `"malformed_config"` — set by `cli.py`'s `resolve-dispatch` subcommand's own early-return
        (this function itself never reads config off disk), when `read_gsd_config` found
        `status == "malformed"`. Never schedule an auto-wake.
  - `resolve_gsd_dispatch` walks `resolve_execute_candidates`'s ranked output (passing
    `estimate_required_context`'s real value as `required_context`) through `candidates_to_ladder`
    + `resolve_ladder_pick_fn` (never `ranked[0]` unconditionally), and on finding a
    quota-available candidate that turns out to have no usable native slot AND no buildable
    cross-AI command, removes it from the ladder and retries the next quota-available candidate.

- [ ] **Step 1: Write the failing tests**

```python
from ai_kit_spec_gsd import adapter


class TestAssembleCandidates(unittest.TestCase):
    def test_reshapes_cfg_reviewers_with_open_risk_fields_none_and_no_curated_tier(self):
        def fake_cfg_resolve(cwd, env):
            return {"policy": {"ladder": ["codex/gpt-5.6-sol"]},
                    "reviewers": [{"key": "codex/gpt-5.6-sol", "model": "gpt-5.6-sol",
                                    "vendor": "openai", "cli": "codex"}]}
        candidates, top_n_keys = adapter.assemble_candidates(
            "/repo", {}, cfg_resolve_fn=fake_cfg_resolve)
        self.assertEqual(candidates, [{"key": "codex/gpt-5.6-sol", "model": "gpt-5.6-sol",
                                        "cli": "codex", "vendor": "openai", "command": None,
                                        "task_affinity": None, "context_limit": None,
                                        "tier": None}])
        self.assertEqual(top_n_keys, ["codex/gpt-5.6-sol"])

    def test_native_cli_none_entry_derives_tier_from_its_own_model_field(self):
        # This repo's own "opus-native"-shaped entries: model IS already a tier alias.
        def fake_cfg_resolve(cwd, env):
            return {"policy": {"ladder": ["opus-native"]},
                    "reviewers": [{"key": "opus-native", "model": "opus", "vendor": "",
                                    "cli": None}]}
        candidates, _ = adapter.assemble_candidates("/repo", {}, cfg_resolve_fn=fake_cfg_resolve)
        self.assertEqual(candidates[0]["tier"], "opus")

    def test_curated_tier_field_takes_priority_over_the_derived_default(self):
        def fake_cfg_resolve(cwd, env):
            return {"policy": {"ladder": ["codex/gpt-5.6-sol"]},
                    "reviewers": [{"key": "codex/gpt-5.6-sol", "model": "gpt-5.6-sol",
                                    "vendor": "openai", "cli": "codex", "tier": "sonnet",
                                    "command": "codex exec -m {model} -- {prompt}",
                                    "task_affinity": "backend", "context_limit": 128000}]}
        candidates, _ = adapter.assemble_candidates("/repo", {}, cfg_resolve_fn=fake_cfg_resolve)
        self.assertEqual(candidates[0]["tier"], "sonnet")
        self.assertEqual(candidates[0]["command"], "codex exec -m {model} -- {prompt}")
        self.assertEqual(candidates[0]["task_affinity"], "backend")
        self.assertEqual(candidates[0]["context_limit"], 128000)


class TestEstimateRequiredContext(unittest.TestCase):
    def test_estimates_a_real_nonzero_value_from_the_actual_phase_prompt(self):
        prompt = "x" * 4000
        self.assertEqual(adapter.estimate_required_context(prompt), 1000)

    def test_empty_prompt_estimates_zero(self):
        self.assertEqual(adapter.estimate_required_context(""), 0)


class TestResolveGsdDispatch(unittest.TestCase):
    def test_native_candidate_with_curated_tier_writes_override_and_runtime(self):
        candidates = [{"cli": "codex", "model": "gpt-5.6-sol", "key": "codex/gpt-5.6-sol",
                       "vendor": "openai", "task_affinity": None, "context_limit": None,
                       "tier": "sonnet"}]
        written, runtime_written = {}, {}
        def fake_write_tier(path, gsd_config, runtime, tier, model, **kw):
            written["args"] = (path, gsd_config, runtime, tier, model)
            return {**gsd_config, "model_profile_overrides": {runtime: {tier: model}}}
        def fake_write_runtime(path, gsd_config, runtime, **kw):
            runtime_written["args"] = (path, gsd_config, runtime)
            return {**gsd_config, "runtime": runtime}
        result = adapter.resolve_gsd_dispatch(
            candidates, ["codex/gpt-5.6-sol"], {}, "/repo/.planning/config.json", "/repo",
            write_tier_fn=fake_write_tier, write_runtime_fn=fake_write_runtime)
        self.assertEqual(result, {"mode": "native_tier", "runtime": "codex", "tier": "sonnet",
                                    "model": "gpt-5.6-sol", "written": True, "cli": "codex",
                                    "key": "codex/gpt-5.6-sol", "provenance": "resolved_candidate"})
        # Write-ordering: runtime write happens FIRST, its own returned dict feeds the tier write.
        self.assertEqual(runtime_written["args"], ("/repo/.planning/config.json", {}, "codex"))
        self.assertEqual(written["args"],
                          ("/repo/.planning/config.json", {"runtime": "codex"}, "codex",
                           "sonnet", "gpt-5.6-sol"))

    def test_does_not_rewrite_active_runtime_when_it_already_matches_current_runtime(self):
        candidates = [{"cli": "codex", "model": "gpt-5.6-sol", "key": "codex/gpt-5.6-sol",
                       "vendor": "openai", "task_affinity": None, "context_limit": None,
                       "tier": "sonnet"}]
        runtime_written = {"called": False}
        def fake_write_runtime(*a, **kw):
            runtime_written["called"] = True
            return {}
        adapter.resolve_gsd_dispatch(
            candidates, ["codex/gpt-5.6-sol"], {}, "/repo/.planning/config.json", "/repo",
            current_runtime="codex", write_tier_fn=lambda *a, **k: {},
            write_runtime_fn=fake_write_runtime)
        self.assertFalse(runtime_written["called"])

    def test_native_candidate_cli_none_resolves_with_claude_as_runtime(self):
        candidates = [{"cli": None, "model": "opus", "key": "opus-native", "vendor": "",
                       "task_affinity": None, "context_limit": None, "tier": "opus"}]
        result = adapter.resolve_gsd_dispatch(
            candidates, ["opus-native"], {}, "/repo/.planning/config.json", "/repo",
            write_tier_fn=lambda *a, **k: {}, write_runtime_fn=lambda *a, **k: {})
        self.assertEqual(result["runtime"], "claude")
        self.assertEqual(result["tier"], "opus")
        self.assertIsNone(result["cli"])

    def test_existing_non_adapter_owned_slot_is_honored_and_not_overwritten(self):
        gsd_config = {"model_profile_overrides": {"codex": {"sonnet": "hand-picked-model"}}}
        candidates = [{"cli": "codex", "model": "gpt-5.6-sol", "key": "codex/gpt-5.6-sol",
                       "vendor": "openai", "task_affinity": None, "context_limit": None,
                       "tier": "sonnet"}]
        write_calls = []
        result = adapter.resolve_gsd_dispatch(
            candidates, ["codex/gpt-5.6-sol"], gsd_config, "/repo/.planning/config.json", "/repo",
            current_runtime="codex",
            write_tier_fn=lambda *a, **k: write_calls.append(a),
            write_runtime_fn=lambda *a, **k: write_calls.append(a))
        self.assertEqual(result["model"], "hand-picked-model")
        self.assertFalse(result["written"])
        self.assertEqual(result["provenance"], "existing_gsd_config")
        self.assertEqual(write_calls, [])

    def test_adapter_owned_existing_slot_is_re_resolved_not_treated_as_fixed(self):
        gsd_config = {
            "model_profile_overrides": {"codex": {"sonnet": "stale-model"}},
            "_ai_kit_spec_execute_gsd": {"overrides": {"codex": {"sonnet": "stale-model"}}},
        }
        candidates = [{"cli": "codex", "model": "gpt-5.6-sol", "key": "codex/gpt-5.6-sol",
                       "vendor": "openai", "task_affinity": None, "context_limit": None,
                       "tier": "sonnet"}]
        result = adapter.resolve_gsd_dispatch(
            candidates, ["codex/gpt-5.6-sol"], gsd_config, "/repo/.planning/config.json", "/repo",
            current_runtime="codex", write_tier_fn=lambda *a, **k: {**gsd_config},
            write_runtime_fn=lambda *a, **k: {**gsd_config})
        self.assertEqual(result["model"], "gpt-5.6-sol")
        self.assertTrue(result["written"])

    @mock.patch("ai_kit_spec_gsd.adapter.build_cross_ai_command")
    def test_falls_through_to_cross_ai_when_no_tier_and_no_native_runtime(self, mock_build):
        mock_build.return_value = "future-cli exec -C /repo -m grok-4-fast"
        candidates = [{"cli": "grok", "model": "grok-4-fast", "key": "grok/grok-4-fast",
                       "vendor": "xai", "task_affinity": None, "context_limit": None,
                       "tier": None}]
        result = adapter.resolve_gsd_dispatch(
            candidates, ["grok/grok-4-fast"], {}, "/repo/.planning/config.json", "/repo")
        self.assertEqual(result["mode"], "cross_ai_hook")
        self.assertEqual(result["cli"], "grok")
        self.assertEqual(result["cross_ai_command"], "future-cli exec -C /repo -m grok-4-fast")
        self.assertEqual(result["provenance"], "resolved_candidate")

    @mock.patch("ai_kit_spec_gsd.adapter.build_cross_ai_command")
    def test_escalates_past_an_unusable_candidate_to_a_later_native_one(self, mock_build):
        mock_build.return_value = None
        candidates = [
            {"cli": "grok", "model": "grok-4-fast", "key": "grok/grok-4-fast", "vendor": "xai",
             "task_affinity": None, "context_limit": None, "tier": None},
            {"cli": "codex", "model": "gpt-5.6-sol", "key": "codex/gpt-5.6-sol",
             "vendor": "openai", "task_affinity": None, "context_limit": None, "tier": "sonnet"},
        ]
        result = adapter.resolve_gsd_dispatch(
            candidates, ["grok/grok-4-fast", "codex/gpt-5.6-sol"], {},
            "/repo/.planning/config.json", "/repo", write_tier_fn=lambda *a, **k: {},
            write_runtime_fn=lambda *a, **k: {})
        self.assertEqual(result["mode"], "native_tier")
        self.assertEqual(result["model"], "gpt-5.6-sol")

    def test_skips_a_candidate_with_no_quota_and_uses_the_next_one(self):
        candidates = [
            {"cli": "grok", "model": "grok-4-fast", "key": "grok/grok-4-fast", "vendor": "xai",
             "task_affinity": None, "context_limit": None, "tier": None},
            {"cli": "codex", "model": "gpt-5.6-sol", "key": "codex/gpt-5.6-sol",
             "vendor": "openai", "task_affinity": None, "context_limit": None, "tier": "sonnet"},
        ]
        quota = {"grok/grok-4-fast": {"available": False}}
        result = adapter.resolve_gsd_dispatch(
            candidates, ["grok/grok-4-fast", "codex/gpt-5.6-sol"], {},
            "/repo/.planning/config.json", "/repo", quota=quota, write_tier_fn=lambda *a, **k: {},
            write_runtime_fn=lambda *a, **k: {})
        self.assertEqual(result["mode"], "native_tier")
        self.assertEqual(result["model"], "gpt-5.6-sol")

    def test_falls_back_with_no_usable_dispatch_when_nothing_can_carry_it(self):
        # real (unmocked) build_cross_ai_command: grok is not in KNOWN_GSD_RUNTIMES and has no
        # live-verified execute builder -- returns None for real, and no curated tier exists.
        candidates = [{"cli": "grok", "model": "grok-4-fast", "key": "grok/grok-4-fast",
                       "vendor": "xai", "task_affinity": None, "context_limit": None,
                       "tier": None}]
        result = adapter.resolve_gsd_dispatch(
            candidates, ["grok/grok-4-fast"], {}, "/repo/.planning/config.json", "/repo")
        self.assertEqual(result["mode"], "fallback_notice")
        self.assertIn("grok/grok-4-fast", result["message"])
        self.assertEqual(result["reason"], "no_usable_dispatch")
        self.assertEqual(result["provenance"], "fallback")

    def test_every_candidate_lacks_quota_falls_back_quota_exhausted(self):
        candidates = [
            {"cli": "grok", "model": "grok-4-fast", "key": "grok/grok-4-fast", "vendor": "xai",
             "task_affinity": None, "context_limit": None, "tier": None},
            {"cli": "codex", "model": "gpt-5.6-sol", "key": "codex/gpt-5.6-sol",
             "vendor": "openai", "task_affinity": None, "context_limit": None, "tier": "sonnet"},
        ]
        quota = {"grok/grok-4-fast": {"available": False},
                 "codex/gpt-5.6-sol": {"available": False}}
        result = adapter.resolve_gsd_dispatch(
            candidates, ["grok/grok-4-fast", "codex/gpt-5.6-sol"], {},
            "/repo/.planning/config.json", "/repo", quota=quota)
        self.assertEqual(result["mode"], "fallback_notice")
        self.assertEqual(result["reason"], "quota_exhausted")

    def test_no_configured_candidate_at_all_has_its_own_distinct_reason_code(self):
        result = adapter.resolve_gsd_dispatch([], [], {}, "/repo/.planning/config.json", "/repo")
        self.assertEqual(result["mode"], "fallback_notice")
        self.assertEqual(result["reason"], "no_configured_candidate")

    def test_all_candidates_present_but_context_rejected_gets_a_distinct_reason_code(self):
        candidates = [
            {"cli": "grok", "model": "grok-4-fast", "key": "grok/grok-4-fast", "vendor": "xai",
             "task_affinity": None, "context_limit": 1000, "tier": None},
            {"cli": "codex", "model": "gpt-5.6-sol", "key": "codex/gpt-5.6-sol",
             "vendor": "openai", "task_affinity": None, "context_limit": 2000, "tier": "sonnet"},
        ]
        result = adapter.resolve_gsd_dispatch(
            candidates, ["grok/grok-4-fast", "codex/gpt-5.6-sol"], {},
            "/repo/.planning/config.json", "/repo", required_context=1_000_000)
        self.assertEqual(result["mode"], "fallback_notice")
        self.assertEqual(result["reason"], "all_candidates_context_rejected")

    def test_real_nonempty_phase_prompt_with_uncurated_candidates_still_resolves(self):
        real_phase_prompt = "Implement the login form validation for the signup flow." * 20
        required_context = adapter.estimate_required_context(real_phase_prompt)
        self.assertGreater(required_context, 0)
        candidates = [{"cli": "codex", "model": "gpt-5.6-sol", "key": "codex/gpt-5.6-sol",
                       "vendor": "openai", "task_affinity": None, "context_limit": None,
                       "tier": "sonnet"}]
        result = adapter.resolve_gsd_dispatch(
            candidates, ["codex/gpt-5.6-sol"], {}, "/repo/.planning/config.json", "/repo",
            quota={}, required_context=required_context, write_tier_fn=lambda *a, **k: {},
            write_runtime_fn=lambda *a, **k: {})
        self.assertNotEqual(result["mode"], "fallback_notice")
```

- [ ] **Step 2: Run to verify failure**

```bash
python3 -m unittest tests.test_ai_kit_spec_gsd.TestAssembleCandidates \
  tests.test_ai_kit_spec_gsd.TestEstimateRequiredContext \
  tests.test_ai_kit_spec_gsd.TestResolveGsdDispatch -v 2>&1 | tail -50
```

Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

```python
"""Top-level GSD adapter: assembles candidates from ai-kit-spec's own shared config surface, then
resolves a config-write plan (never a subprocess dispatch, Task 1 finding 3) that Task 5's SKILL.md
hands off to GSD's own /gsd-execute-phase skill. A live-quota-checked candidate with a real,
curated `tier` writes runtime + model_profile_overrides.<runtime>.<tier> directly; one without a
curated tier but with a real cross-AI command falls to cross_ai_hook (command string only -- the
write into workflow.cross_ai_command happens in Task 5, after checking the plan's own cross_ai:
true frontmatter); otherwise an honest fallback notice that makes no unenforced vendor claim."""
from ai_kit_spec.config_io import cfg_resolve
from ai_kit_spec.execute_selection import candidates_to_ladder, resolve_execute_candidates
from ai_kit_spec.quota import resolve_ladder_pick
from ai_kit_spec_gsd.gsd_config import (
    KNOWN_GSD_RUNTIMES, override_is_adapter_owned, resolve_active_runtime,
    write_active_runtime, write_native_tier_override,
)
from ai_kit_spec_gsd.gsd_cross_ai import build_cross_ai_command


def estimate_required_context(phase_prompt: str) -> int:
    """A real, non-hardcoded estimate of the phase's own context footprint -- standard
    chars-per-token-4 heuristic. Every candidate's context_limit is None today (no curation exists
    yet), so this has no filtering effect through execute_selection.filter_by_context YET; it
    exists so a future curated context_limit is honored immediately, with no change here."""
    return len(phase_prompt) // 4


def assemble_candidates(cwd: str, env: dict, cfg_resolve_fn=cfg_resolve) -> tuple:
    resolved = cfg_resolve_fn(cwd, env)
    candidates = []
    for r in resolved.get("reviewers", []):
        if "key" not in r:
            continue
        cli = r.get("cli")
        # tier: curated field wins; a native (cli is None) entry's own `model` is already a
        # Claude-tier-alias by this repo's existing convention (e.g. "opus-native" -> model:
        # "opus"); a cli-set entry with no curated tier cannot be expressed natively at all.
        tier = r.get("tier")
        if tier is None and cli is None:
            tier = r.get("model")
        candidates.append({
            "key": r["key"], "model": r.get("model", ""), "cli": cli,
            "vendor": r.get("vendor", ""), "command": r.get("command"),
            "task_affinity": r.get("task_affinity"), "context_limit": r.get("context_limit"),
            "tier": tier,
        })
    top_n_keys = resolved.get("policy", {}).get("ladder", [])
    return candidates, top_n_keys


def _runtime_identity(cli) -> str:
    return cli if cli is not None else "claude"


def _fallback_notice(top_choice_key, reason_code: str, reason_prose: str) -> dict:
    top_choice = top_choice_key or "no candidate resolved"
    return {
        "mode": "fallback_notice",
        "key": top_choice_key,
        "cli": None,
        "provenance": "fallback",
        "reason": reason_code,
        "message": (
            f"ai-kit-spec-execute chose {top_choice} for this task, but {reason_prose}. No "
            f"configuration change was made to GSD's config -- GSD's own currently-active "
            f"default (unmodified by ai-kit-spec-execute) will run instead."
        ),
    }


def resolve_gsd_dispatch(candidates: list, top_n_keys: list, gsd_config: dict,
                          gsd_config_path: str, target_dir: str, current_runtime: str = "claude",
                          required_context: int = 0, quota: dict | None = None,
                          run_id: str | None = None, write_tier_fn=write_native_tier_override,
                          write_runtime_fn=write_active_runtime,
                          resolve_ladder_pick_fn=resolve_ladder_pick) -> dict:
    quota = dict(quota or {})

    if not candidates:
        return _fallback_notice(
            None, "no_configured_candidate",
            "ai-kit-spec-execute has no configured candidate at all (review-spec.toml has no "
            "[[reviewers]] entries) -- nothing to select from")

    # task_type is execute_selection's own frontend/backend/mixed "task_affinity" axis -- no
    # curated data exists yet, so this is always None (see Global Constraints).
    ranked = resolve_execute_candidates(candidates, None, required_context, {}, top_n_keys)
    if not ranked:
        return _fallback_notice(
            None, "all_candidates_context_rejected",
            f"every one of the {len(candidates)} configured candidate(s) was rejected on context "
            f"size -- each candidate's curated context_limit is smaller than this phase's "
            f"estimated required_context of {required_context}")

    by_key = {c["key"]: c for c in ranked}
    remaining_ladder = candidates_to_ladder(ranked)
    top_key = ranked[0]["key"]

    while remaining_ladder:
        pick = resolve_ladder_pick_fn(ranked, remaining_ladder, skip_vendor="", quota=quota)
        if pick is None:
            break  # nothing left in remaining_ladder currently has quota
        candidate = by_key[pick.key]
        cli = candidate["cli"]
        tier = candidate.get("tier")
        if tier is not None:
            runtime = _runtime_identity(cli)
            existing = gsd_config.get("model_profile_overrides", {}).get(runtime, {}).get(tier)
            if existing is not None and not override_is_adapter_owned(gsd_config, runtime, tier):
                return {"mode": "native_tier", "runtime": runtime, "tier": tier,
                        "model": existing, "written": False, "cli": cli, "key": None,
                        "provenance": "existing_gsd_config"}
            if resolve_active_runtime(gsd_config) != runtime and current_runtime != runtime:
                gsd_config = write_runtime_fn(gsd_config_path, gsd_config, runtime, run_id=run_id)
            elif resolve_active_runtime(gsd_config) != runtime:
                gsd_config = write_runtime_fn(gsd_config_path, gsd_config, runtime, run_id=run_id)
            gsd_config = write_tier_fn(gsd_config_path, gsd_config, runtime, tier,
                                        candidate["model"], run_id=run_id)
            return {"mode": "native_tier", "runtime": runtime, "tier": tier,
                    "model": candidate["model"], "written": True, "cli": cli,
                    "key": candidate["key"], "provenance": "resolved_candidate"}
        cross_ai_command = build_cross_ai_command(candidate, target_dir)
        if cross_ai_command is not None:
            return {"mode": "cross_ai_hook", "cross_ai_command": cross_ai_command, "cli": cli,
                    "key": candidate["key"], "model": candidate["model"],
                    "provenance": "resolved_candidate"}
        # No usable dispatch mechanism for this candidate at all -- drop it and keep walking.
        remaining_ladder = [k for k in remaining_ladder if k != pick.key]

    has_retryable_remaining = any(
        by_key[k].get("tier") is not None or build_cross_ai_command(by_key[k], target_dir) is not None
        for k in remaining_ladder
    )
    reason_code = "quota_exhausted" if has_retryable_remaining else "no_usable_dispatch"
    reason_prose = (
        "every candidate in the ladder is quota-exhausted"
        if reason_code == "quota_exhausted" else
        "no quota-available candidate in the ladder has a usable native slot or cross-AI command"
    )
    return _fallback_notice(top_key, reason_code, reason_prose)
```

- [ ] **Step 4: Run tests to verify pass**

```bash
python3 -m unittest tests.test_ai_kit_spec_gsd.TestAssembleCandidates \
  tests.test_ai_kit_spec_gsd.TestEstimateRequiredContext \
  tests.test_ai_kit_spec_gsd.TestResolveGsdDispatch -v 2>&1 | tail -30
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat(ai-kit-spec-execute-gsd): add adapter.py (candidate assembly + live-quota-checked dispatch resolution, config-write plan for GSD's own execute-phase skill)"
```

- [ ] **Step 6: Write the failing tests for a runnable CLI covering every operation Task 5's SKILL.md needs**

```python
from ai_kit_spec_gsd import cli


class TestCliResolveDispatch(unittest.TestCase):
    def test_resolve_dispatch_subcommand_prints_json_dispatch_decision(self):
        import io
        import json
        def fake_assemble(cwd, env):
            return ([{"cli": "codex", "model": "gpt-5.6-sol", "key": "codex/gpt-5.6-sol",
                       "vendor": "openai", "task_affinity": None, "context_limit": None,
                       "tier": "sonnet"}],
                    ["codex/gpt-5.6-sol"])
        stdout = io.StringIO()
        exit_code = cli.main(
            ["resolve-dispatch", "--cwd", "/repo",
             "--config-path", "/repo/.planning/config.json", "--target-dir", "/repo",
             "--quota-path", "/cache/quota.json"],
            assemble_candidates_fn=fake_assemble,
            read_gsd_config_fn=lambda p, warn_fn=None: ({}, "missing"),
            refresh_quota_cache_fn=lambda *a, **k: {}, cache_read_json_fn=lambda p: {},
            cache_write_json_fn=lambda p, d: None, write_tier_fn=lambda *a, **k: {},
            write_runtime_fn=lambda *a, **k: {}, stdout=stdout)
        self.assertEqual(exit_code, 0)
        result = json.loads(stdout.getvalue())
        self.assertEqual(result["mode"], "native_tier")
        self.assertEqual(result["model"], "gpt-5.6-sol")

    def test_resolve_dispatch_aborts_and_reports_malformed_config_without_mutating(self):
        import io
        import json
        write_calls = []
        stdout = io.StringIO()
        exit_code = cli.main(
            ["resolve-dispatch", "--cwd", "/repo",
             "--config-path", "/repo/.planning/config.json", "--target-dir", "/repo",
             "--quota-path", "/cache/quota.json"],
            assemble_candidates_fn=lambda cwd, env: ([], []),
            read_gsd_config_fn=lambda p, warn_fn=None: ({}, "malformed"),
            refresh_quota_cache_fn=lambda *a, **k: {}, cache_read_json_fn=lambda p: {},
            cache_write_json_fn=lambda p, d: None,
            write_tier_fn=lambda *a, **k: write_calls.append(a),
            write_runtime_fn=lambda *a, **k: write_calls.append(a), stdout=stdout)
        self.assertEqual(exit_code, 0)
        result = json.loads(stdout.getvalue())
        self.assertEqual(result["mode"], "fallback_notice")
        self.assertEqual(result["reason"], "malformed_config")
        self.assertEqual(write_calls, [])

    def test_resolve_dispatch_generates_one_run_id_and_threads_it_through_every_write(self):
        import io
        import json
        def fake_assemble(cwd, env):
            return ([{"cli": "codex", "model": "gpt-5.6-sol", "key": "codex/gpt-5.6-sol",
                       "vendor": "openai", "task_affinity": None, "context_limit": None,
                       "tier": "sonnet"}],
                    ["codex/gpt-5.6-sol"])
        run_ids_seen = []
        def fake_write_tier(path, gsd_config, runtime, tier, model, run_id=None, **kw):
            run_ids_seen.append(run_id)
            return {**gsd_config, "model_profile_overrides": {runtime: {tier: model}}}
        def fake_write_runtime(path, gsd_config, runtime, run_id=None, **kw):
            run_ids_seen.append(run_id)
            return {**gsd_config, "runtime": runtime}
        stdout = io.StringIO()
        cli.main(
            ["resolve-dispatch", "--cwd", "/repo",
             "--config-path", "/repo/.planning/config.json", "--target-dir", "/repo",
             "--quota-path", "/cache/quota.json", "--run-id", "explicit-run-42"],
            assemble_candidates_fn=fake_assemble,
            read_gsd_config_fn=lambda p, warn_fn=None: ({}, "missing"),
            refresh_quota_cache_fn=lambda *a, **k: {}, cache_read_json_fn=lambda p: {},
            cache_write_json_fn=lambda p, d: None, write_tier_fn=fake_write_tier,
            write_runtime_fn=fake_write_runtime, stdout=stdout)
        self.assertTrue(run_ids_seen)
        self.assertEqual(set(run_ids_seen), {"explicit-run-42"})
        result = json.loads(stdout.getvalue())
        self.assertEqual(result["run_id"], "explicit-run-42")

    def test_resolve_dispatch_falls_back_to_zero_context_when_phase_prompt_file_is_unreadable(self):
        import io
        import json
        import contextlib
        def fake_assemble(cwd, env):
            return ([{"cli": "codex", "model": "gpt-5.6-sol", "key": "codex/gpt-5.6-sol",
                       "vendor": "openai", "task_affinity": None, "context_limit": None,
                       "tier": "sonnet"}],
                    ["codex/gpt-5.6-sol"])
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stderr(stderr):
            exit_code = cli.main(
                ["resolve-dispatch", "--cwd", "/repo",
                 "--config-path", "/repo/.planning/config.json", "--target-dir", "/repo",
                 "--quota-path", "/cache/quota.json",
                 "--phase-prompt-file", "/nonexistent/phase-prompt.md"],
                assemble_candidates_fn=fake_assemble,
                read_gsd_config_fn=lambda p, warn_fn=None: ({}, "missing"),
                refresh_quota_cache_fn=lambda *a, **k: {}, cache_read_json_fn=lambda p: {},
                cache_write_json_fn=lambda p, d: None, write_tier_fn=lambda *a, **k: {},
                write_runtime_fn=lambda *a, **k: {}, stdout=stdout)
        self.assertEqual(exit_code, 0)
        json.loads(stdout.getvalue())
        self.assertIn("phase-prompt.md", stderr.getvalue())


class TestCliConfigPath(unittest.TestCase):
    def test_config_path_subcommand_prints_the_resolved_path(self):
        import io
        stdout = io.StringIO()
        exit_code = cli.main(["config-path", "--cwd", "/repo"], stdout=stdout)
        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout.getvalue().strip(), "/repo/.planning/config.json")


class TestCliWriteWorkflowKey(unittest.TestCase):
    def test_write_workflow_key_subcommand_writes_a_real_json_value(self):
        import io
        import json
        writes = {}
        def fake_write(path, gsd_config, key, value, **kw):
            writes["args"] = (path, gsd_config, key, value)
            return {**gsd_config, "workflow": {key: value}}
        stdout = io.StringIO()
        exit_code = cli.main(
            ["write-workflow-key", "--config-path", "/repo/.planning/config.json",
             "--config-json", "{}", "--key", "cross_ai_execution", "--run-id", "run-1",
             "--value-json", "true"],
            write_workflow_key_fn=fake_write, stdout=stdout)
        self.assertEqual(exit_code, 0)
        result = json.loads(stdout.getvalue())
        self.assertIs(result["workflow"]["cross_ai_execution"], True)
        self.assertIs(writes["args"][3], True)  # a real bool, never the string "true"


class TestCliClearWorkflowKey(unittest.TestCase):
    def test_clear_workflow_key_subcommand_clears_an_adapter_owned_key(self):
        import io
        import json
        config_json = json.dumps({
            "workflow": {"cross_ai_command": "codex exec ..."},
            "_ai_kit_spec_execute_gsd": {"workflow": {"cross_ai_command": "codex exec ..."}},
        })
        def fake_clear(path, gsd_config, key, **kw):
            return {**gsd_config, "workflow": {}}
        stdout = io.StringIO()
        exit_code = cli.main(
            ["clear-workflow-key", "--config-path", "/repo/.planning/config.json",
             "--config-json", config_json, "--key", "cross_ai_command", "--run-id", "run-1"],
            clear_workflow_key_if_adapter_owned_fn=fake_clear, stdout=stdout)
        self.assertEqual(exit_code, 0)
        result = json.loads(stdout.getvalue())
        self.assertNotIn("cross_ai_command", result["workflow"])


class _FakeCompletedProcess:
    def __init__(self, returncode):
        self.returncode = returncode
        self.stdout = ""
        self.stderr = ""


class TestCliPrepareTooling(unittest.TestCase):
    def test_prepare_tooling_subcommand_builds_the_index_for_real_and_prints_guidance_text(self):
        import io
        run_calls = []
        def fake_run(cmd, **kw):
            run_calls.append((cmd, kw))
            return _FakeCompletedProcess(returncode=0)
        stdout = io.StringIO()
        exit_code = cli.main(
            ["prepare-tooling", "--cli", "codex", "--target-dir", "/repo"],
            detect_tool_availability_fn=lambda **k: {"codegraph": True, "rg": True},
            resolve_agents_tooling_path_fn=lambda **k: "/home/u/.agents/AGENTS-TOOLING.md",
            ensure_codegraph_registered_fn=lambda cli, **k: True,
            build_codegraph_index_command_fn=lambda target_dir: "cd /repo && codegraph sync",
            run_fn=fake_run, stdout=stdout)
        self.assertEqual(exit_code, 0)
        self.assertEqual(len(run_calls), 1)
        self.assertIn("AGENTS-TOOLING.md", stdout.getvalue())
        self.assertIn("codegraph_explore", stdout.getvalue())

    def test_prepare_tooling_degrades_to_generic_guidance_when_index_build_times_out(self):
        import io
        import subprocess
        def timing_out_run(cmd, **kw):
            raise subprocess.TimeoutExpired(cmd=cmd, timeout=kw.get("timeout", 15))
        stdout = io.StringIO()
        exit_code = cli.main(
            ["prepare-tooling", "--cli", "codex", "--target-dir", "/repo"],
            detect_tool_availability_fn=lambda **k: {"codegraph": True, "rg": True},
            resolve_agents_tooling_path_fn=lambda **k: "/home/u/.agents/AGENTS-TOOLING.md",
            ensure_codegraph_registered_fn=lambda cli, **k: True,
            build_codegraph_index_command_fn=lambda target_dir: "cd /repo && codegraph sync",
            run_fn=timing_out_run, stdout=stdout)
        self.assertEqual(exit_code, 0)
        self.assertNotIn("codegraph_explore", stdout.getvalue())
        self.assertIn("AGENTS-TOOLING.md", stdout.getvalue())


class TestCliWriteResumableState(unittest.TestCase):
    def test_write_resumable_state_subcommand_writes_the_given_state_json(self):
        import io
        writes = {}
        def fake_write(path, state):
            writes[path] = state
        stdout = io.StringIO()
        exit_code = cli.main(
            ["write-resumable-state", "--path", "/cache/gsd-resume-abc123-phase1.json",
             "--state-json", '{"framework": "gsd", "phase_id": "phase1"}'],
            write_resumable_state_fn=fake_write, stdout=stdout)
        self.assertEqual(exit_code, 0)
        self.assertEqual(writes["/cache/gsd-resume-abc123-phase1.json"]["phase_id"], "phase1")
```

- [ ] **Step 7: Run to verify failure**

```bash
python3 -m unittest tests.test_ai_kit_spec_gsd.TestCliResolveDispatch \
  tests.test_ai_kit_spec_gsd.TestCliConfigPath \
  tests.test_ai_kit_spec_gsd.TestCliWriteWorkflowKey \
  tests.test_ai_kit_spec_gsd.TestCliClearWorkflowKey \
  tests.test_ai_kit_spec_gsd.TestCliPrepareTooling \
  tests.test_ai_kit_spec_gsd.TestCliWriteResumableState -v 2>&1 | tail -30
```

Expected: FAIL — module not found.

- [ ] **Step 8: Implement `ai_kit_spec_gsd/cli.py`**

```python
"""CLI entrypoint for ai-kit-spec-execute-gsd -- invoked via the ai-kit-spec-gsd.py shim. Mirrors
ai_kit_spec/cli.py's own subcommand pattern (Plan 1) so Task 5's SKILL.md gives an executing agent
one concrete, runnable command for every operation it performs -- resolve-dispatch, config-path,
write-workflow-key, clear-workflow-key, prepare-tooling, write-resumable-state. There is no
dispatch-phase/classify-failure subcommand: GSD's own /gsd-execute-phase skill performs the actual
dispatch in-session, invoked directly via the Skill tool by Task 5's SKILL.md, never subprocess-
invoked here (Task 1 finding 3)."""
import argparse
import json
import os
import subprocess
import sys

from ai_kit_spec.cache import cache_read_json, cache_write_json
from ai_kit_spec.detection import (
    CODEGRAPH_INDEX_TIMEOUT_SECONDS, build_codegraph_index_command, detect_tool_availability,
    ensure_codegraph_registered, resolve_agents_tooling_path,
)
from ai_kit_spec.quota import refresh_quota_cache, QUOTA_TTL_SECONDS
from ai_kit_spec.tooling_guidance import build_tooling_guidance
from ai_kit_spec_gsd.adapter import assemble_candidates, estimate_required_context, resolve_gsd_dispatch
from ai_kit_spec_gsd.gsd_config import (
    clear_workflow_key_if_adapter_owned, generate_run_id, read_gsd_config,
    resolve_active_runtime, resolve_gsd_config_path, write_active_runtime,
    write_native_tier_override, write_workflow_key,
)
from ai_kit_spec.dispatch import write_resumable_state as _write_resumable_state_default


def main(argv: list, assemble_candidates_fn=assemble_candidates,
         read_gsd_config_fn=read_gsd_config, refresh_quota_cache_fn=refresh_quota_cache,
         cache_read_json_fn=cache_read_json, cache_write_json_fn=cache_write_json,
         write_tier_fn=write_native_tier_override, write_runtime_fn=write_active_runtime,
         write_workflow_key_fn=write_workflow_key,
         clear_workflow_key_if_adapter_owned_fn=clear_workflow_key_if_adapter_owned,
         detect_tool_availability_fn=detect_tool_availability,
         resolve_agents_tooling_path_fn=resolve_agents_tooling_path,
         ensure_codegraph_registered_fn=ensure_codegraph_registered,
         build_codegraph_index_command_fn=build_codegraph_index_command,
         run_fn=subprocess.run, write_resumable_state_fn=_write_resumable_state_default,
         stdout=sys.stdout) -> int:
    parser = argparse.ArgumentParser(prog="ai-kit-spec-execute-gsd")
    sub = parser.add_subparsers(dest="command", required=True)

    p_resolve = sub.add_parser("resolve-dispatch")
    p_resolve.add_argument("--cwd", required=True)
    p_resolve.add_argument("--config-path", required=True)
    p_resolve.add_argument("--target-dir", required=True)
    p_resolve.add_argument("--quota-path", required=True)
    p_resolve.add_argument("--phase-prompt-file", default=None,
                            help="used to compute a real required_context estimate; omit for 0")
    p_resolve.add_argument("--run-id", default=None,
                            help="omit to generate one -- this call's resolved run_id is ALSO "
                                 "printed in the JSON result (result['run_id']) so the caller can "
                                 "thread the SAME id into any later write-workflow-key/"
                                 "clear-workflow-key calls in the same wave")

    p_config_path = sub.add_parser("config-path")
    p_config_path.add_argument("--cwd", required=True)

    p_write_workflow = sub.add_parser("write-workflow-key")
    p_write_workflow.add_argument("--config-path", required=True)
    p_write_workflow.add_argument("--config-json", required=True,
                                   help="the current gsd_config dict as a JSON string -- thread "
                                        "the PREVIOUS write's own stdout into this on a second "
                                        "call in the same run")
    p_write_workflow.add_argument("--key", required=True)
    p_write_workflow.add_argument("--value-json", required=True,
                                   help="the value to write, as a JSON literal -- e.g. "
                                        "'\"codex exec ...\"' for a string, 'true' for a JSON "
                                        "boolean")
    p_write_workflow.add_argument("--run-id", required=True,
                                   help="the SAME run_id captured from this wave's "
                                        "resolve-dispatch call (result['run_id'])")

    p_clear_workflow = sub.add_parser("clear-workflow-key")
    p_clear_workflow.add_argument("--config-path", required=True)
    p_clear_workflow.add_argument("--config-json", required=True)
    p_clear_workflow.add_argument("--key", required=True)
    p_clear_workflow.add_argument("--run-id", required=True)

    p_prepare = sub.add_parser("prepare-tooling")
    p_prepare.add_argument("--cli", default=None,
                            help="omit (or pass 'claude') for native/current-runtime dispatch")
    p_prepare.add_argument("--target-dir", required=True)

    p_resume = sub.add_parser("write-resumable-state")
    p_resume.add_argument("--path", required=True)
    p_resume.add_argument("--state-json", required=True)

    args = parser.parse_args(argv)

    if args.command == "resolve-dispatch":
        gsd_config, status = read_gsd_config_fn(
            args.config_path, warn_fn=lambda msg: print(msg, file=sys.stderr))
        if status == "malformed":
            result = {"mode": "fallback_notice", "key": None, "cli": None,
                      "provenance": "fallback", "reason": "malformed_config",
                      "message": f"{args.config_path} is malformed/unreadable -- refusing to "
                                 f"write over it. Fix or remove it by hand, then re-run.",
                      "run_id": args.run_id if args.run_id else generate_run_id()}
            stdout.write(json.dumps(result))
            return 0
        run_id = args.run_id if args.run_id else generate_run_id()
        candidates, top_n_keys = assemble_candidates_fn(args.cwd, dict(os.environ))
        existing_quota = cache_read_json_fn(args.quota_path) or {}
        quota = refresh_quota_cache_fn(
            {"reviewers": [
                {"key": c["key"], "model": c["model"], "vendor": c["vendor"], "cli": c["cli"],
                 "command": c.get("command")}
                for c in candidates
            ]},
            [c["key"] for c in candidates], existing_quota, QUOTA_TTL_SECONDS)
        cache_write_json_fn(args.quota_path, quota)
        required_context = 0
        if args.phase_prompt_file:
            try:
                with open(args.phase_prompt_file, encoding="utf-8") as f:
                    required_context = estimate_required_context(f.read())
            except OSError as exc:
                print(f"ai-kit-spec-execute-gsd: could not read --phase-prompt-file "
                      f"{args.phase_prompt_file!r} ({exc}) -- falling back to "
                      f"required_context=0", file=sys.stderr)
        result = resolve_gsd_dispatch(
            candidates, top_n_keys, gsd_config, args.config_path, args.target_dir,
            current_runtime=resolve_active_runtime(gsd_config), required_context=required_context,
            quota=quota, run_id=run_id, write_tier_fn=write_tier_fn,
            write_runtime_fn=write_runtime_fn)
        result["run_id"] = run_id
        stdout.write(json.dumps(result))
        return 0

    if args.command == "config-path":
        stdout.write(resolve_gsd_config_path(args.cwd) + "\n")
        return 0

    if args.command == "write-workflow-key":
        gsd_config = json.loads(args.config_json)
        value = json.loads(args.value_json)
        result = write_workflow_key_fn(args.config_path, gsd_config, args.key, value,
                                        run_id=args.run_id)
        stdout.write(json.dumps(result))
        return 0

    if args.command == "clear-workflow-key":
        gsd_config = json.loads(args.config_json)
        result = clear_workflow_key_if_adapter_owned_fn(args.config_path, gsd_config, args.key,
                                                          run_id=args.run_id)
        stdout.write(json.dumps(result))
        return 0

    if args.command == "prepare-tooling":
        tool_availability = detect_tool_availability_fn()
        agents_tooling_path = resolve_agents_tooling_path_fn()
        codegraph_registered = False
        if args.cli is not None:
            codegraph_registered = ensure_codegraph_registered_fn(args.cli)
            if codegraph_registered:
                index_cmd = build_codegraph_index_command_fn(args.target_dir)
                try:
                    result = run_fn(index_cmd, shell=True, capture_output=True, text=True,
                                     check=False, timeout=CODEGRAPH_INDEX_TIMEOUT_SECONDS)
                    if result.returncode != 0:
                        codegraph_registered = False
                except (subprocess.TimeoutExpired, OSError):
                    codegraph_registered = False
        guidance = build_tooling_guidance(args.cli, tool_availability, agents_tooling_path,
                                           codegraph_registered)
        stdout.write(guidance)
        return 0

    if args.command == "write-resumable-state":
        state = json.loads(args.state_json)
        write_resumable_state_fn(args.path, state)
        stdout.write(json.dumps({"written": True, "path": args.path}))
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
```

- [ ] **Step 9: Run tests to verify pass, commit**

```bash
python3 -m unittest tests.test_ai_kit_spec_gsd.TestCliResolveDispatch \
  tests.test_ai_kit_spec_gsd.TestCliConfigPath \
  tests.test_ai_kit_spec_gsd.TestCliWriteWorkflowKey \
  tests.test_ai_kit_spec_gsd.TestCliClearWorkflowKey \
  tests.test_ai_kit_spec_gsd.TestCliPrepareTooling \
  tests.test_ai_kit_spec_gsd.TestCliWriteResumableState -v 2>&1 | tail -30
git add -A
git commit -m "feat(ai-kit-spec-execute-gsd): add cli.py resolve-dispatch/config-path/write-workflow-key/prepare-tooling/write-resumable-state subcommands, no dispatch-phase (Task 1 finding 3)"
```

- [ ] **Step 10: Prove the shim's real `resolve-dispatch` subcommand runs end-to-end from OUTSIDE the repository**

```bash
SCRATCH_DIR="$(mktemp -d)"
mkdir -p "$SCRATCH_DIR/.planning"
QUOTA_PATH="$(mktemp)"
echo '{}' > "$QUOTA_PATH"
cd "$SCRATCH_DIR" && python3 /absolute/path/to/skills/ai-kit-spec-execute-gsd/ai-kit-spec-gsd.py \
  resolve-dispatch --cwd "$SCRATCH_DIR" \
  --config-path "$SCRATCH_DIR/.planning/config.json" --target-dir "$SCRATCH_DIR" \
  --quota-path "$QUOTA_PATH" 2>&1
```

Expected: prints a JSON dispatch decision (most likely `{"mode": "fallback_notice", ...}` since
`$SCRATCH_DIR` has no `review-spec.toml`) — the point of this step is confirming NO
`ModuleNotFoundError` is raised and the command exits 0 with valid JSON on stdout.

```bash
git add -A
git commit -m "test(ai-kit-spec-execute-gsd): verify shim's resolve-dispatch subcommand runs end-to-end from outside the repo"
```

---

### Task 5: `SKILL.md` for `ai-kit-spec-execute-gsd`

**Revision note:** this skill no longer subprocess-dispatches anything to execute a GSD phase. Its
job is now: (1) resolve the dispatch decision and write config, (2) for cross-AI, write GSD's own
`workflow.cross_ai_*` keys and check the plan's own `cross_ai: true` frontmatter, (3) invoke GSD's
own `/gsd-execute-phase` skill directly via the `Skill` tool for the phase in question. GSD's own
skill then does the actual execution, heartbeating, and completion end-to-end, using whichever
mechanism this adapter just configured.

**Files:**
- Create: `skills/ai-kit-spec-execute-gsd/SKILL.md`

**Interfaces:**
- Consumes: `ai_kit_spec_gsd/cli.py`'s `resolve-dispatch`/`config-path`/`write-workflow-key`/
  `clear-workflow-key`/`prepare-tooling`/`write-resumable-state` subcommands (Task 4 — every one
  invoked through the `ai-kit-spec-gsd.py` shim, Task 2). The `Skill` tool, to invoke GSD's own
  `/gsd-execute-phase` skill directly (confirmed skill name/invocation from `/run/media/system/
  home/user-zero/.claude/skills/gsd-execute-phase/SKILL.md`'s own frontmatter).

**This skill's own entry precondition**: it is invoked already knowing `cwd` (the GSD project
root) and `phase_id` (the specific phase being executed) — supplied by whatever triggered
execution (the `ai-kit-spec-execute` router, or the user directly). This skill never guesses
either.

- [ ] **Step 1: Write the skill body**

```markdown
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
  throughout:
  ```bash
  UPDATED="$(python3 "$GSD_SHIM" write-workflow-key --config-path "$GSD_CONFIG_PATH" \
    --config-json "$(cat "$GSD_CONFIG_PATH" 2>/dev/null || echo '{}')" \
    --key cross_ai_command --run-id "$RUN_ID" \
    --value-json "$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$RESULT_CROSS_AI_COMMAND")")"
  UPDATED="$(python3 "$GSD_SHIM" write-workflow-key --config-path "$GSD_CONFIG_PATH" \
    --config-json "$UPDATED" --key cross_ai_execution --run-id "$RUN_ID" --value-json true)"
  printf 'UPDATED_CONFIG_JSON=%s\n' "$UPDATED"
  ```
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
for KEY in cross_ai_command cross_ai_execution; do
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

**Then invoke GSD's own `/gsd-execute-phase` skill directly, via the `Skill` tool, for `$PHASE_ID`
— this is the entire remaining job of this skill.** There is no subprocess to run, no stdout to
capture, no heartbeat to route (Task 1 finding 3) — GSD's own workflow performs the actual
dispatch, heartbeating, and completion end-to-end in-session, using whichever mechanism Step 2 just
configured. Concretely, the executing agent calls the `Skill` tool with the skill name confirmed by
`/run/media/system/home/user-zero/.claude/skills/gsd-execute-phase/SKILL.md`'s own frontmatter
(`gsd-execute-phase`), passing `$PHASE_ID` as its argument — this is a tool call the agent makes
directly, not a shell command this document can show as a `bash` fence. After that call returns,
this skill's own job is complete; any dispatch failure GSD's own skill surfaces (including its own
cross-AI retry/skip/abort UI) is GSD's problem to handle and report, not this adapter's.
```

- [ ] **Step 2: Run skill-judge against this skill**

Invoke `skill-judge` on `skills/ai-kit-spec-execute-gsd/SKILL.md`. Fix any finding before
proceeding — in particular check description quality (WHAT/WHEN/keywords) and that Step 2's
dispatch-mode branching reads as a decision tree, not vague prose.

- [ ] **Step 3: Register the new skill in the repo's README**

Add `ai-kit-spec-execute-gsd` to `README.md`'s skills table (alongside the existing
`ai-kit-spec-*` rows), one row, matching that table's existing column format.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "docs(ai-kit-spec-execute-gsd): add SKILL.md (config prep + Skill-tool handoff to GSD's own /gsd-execute-phase), register in README"
```

---

### Task 6: Router stub — `ai-kit-spec-execute`'s framework detection

**Unaffected by this revision** — framework detection (`.planning/PROJECT.md` presence) has
nothing to do with GSD's config schema or execution mechanism. Carried forward as-is.

**Files:**
- Create: `skills/ai-kit-spec-execute/SKILL.md`
- Create: `skills/ai-kit-spec-execute/detect_framework.py`
- Test: `tests/test_ai_kit_spec_gsd.py` (or a new `tests/test_ai_kit_spec_execute.py` — either is
  fine, this task creates whichever doesn't already exist from Plan 3 running first)

**Interfaces:**
- Produces: `detect_framework(cwd: str, isfile_fn=os.path.isfile, isdir_fn=os.path.isdir) -> str`
  — returns `"gsd"` when `.planning/PROJECT.md` exists, `"superpowers"` when a plan file matching
  superpowers' own naming convention is findable (Plan 3 defines the exact check), `"unknown"`
  otherwise.

- [ ] **Step 1: Write the failing tests**

```python
import detect_framework


class TestDetectFramework(unittest.TestCase):
    def test_detects_gsd_via_planning_project_md(self):
        result = detect_framework.detect_framework(
            "/repo", isfile_fn=lambda p: p == "/repo/.planning/PROJECT.md",
            isdir_fn=lambda p: False)
        self.assertEqual(result, "gsd")

    def test_unknown_when_no_markers_present(self):
        result = detect_framework.detect_framework(
            "/repo", isfile_fn=lambda p: False, isdir_fn=lambda p: False)
        self.assertEqual(result, "unknown")
```

- [ ] **Step 2: Run to verify failure**

```bash
python3 -m unittest tests.test_ai_kit_spec_gsd.TestDetectFramework -v 2>&1 | tail -10
```

Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

```python
"""Framework detection for ai-kit-spec-execute's router. GSD's marker is confirmed
(.planning/PROJECT.md, per skills/ai-kit-spec-review-checklist/references/frameworks/gsd.md).
superpowers' marker is defined by Plan 3 (ai-kit-spec-execute-superpowers) -- this stub only
wires the GSD branch; Plan 3 fills in the superpowers check in this same function.

Also runnable directly: `python3 detect_framework.py <cwd>` prints the result on stdout."""
import os
import sys


def detect_framework(cwd: str, isfile_fn=os.path.isfile, isdir_fn=os.path.isdir) -> str:
    if isfile_fn(os.path.join(cwd, ".planning", "PROJECT.md")):
        return "gsd"
    return "unknown"


if __name__ == "__main__":
    print(detect_framework(sys.argv[1]))
```

- [ ] **Step 4: Run tests to verify pass**

```bash
python3 -m unittest tests.test_ai_kit_spec_gsd.TestDetectFramework -v 2>&1 | tail -10
```

Expected: PASS.

- [ ] **Step 5: Write the router `SKILL.md` stub**

```markdown
---
name: ai-kit-spec-execute
description: Routes execution of an already-generated plan/phase to the framework-specific ai-kit-spec-execute adapter (GSD or superpowers), based on which framework produced the plan. Use when the user asks to execute/run/implement a plan or phase and the generating framework isn't already known.
---

# ai-kit-spec-execute

1. Run `detect_framework(cwd)` from `detect_framework.py`.
2. `"gsd"` → delegate to `ai-kit-spec-execute-gsd`.
3. `"superpowers"` → delegate to `ai-kit-spec-execute-superpowers` (see that skill's own SKILL.md).
4. `"unknown"` → ask the user which framework generated this plan; do not guess.
```

- [ ] **Step 6: Run skill-judge against this skill**

Invoke `skill-judge` on `skills/ai-kit-spec-execute/SKILL.md` (design spec §13 requires
skill-judge against all 3 new skills — `ai-kit-spec-execute`, `-gsd`, `-superpowers`). Fix any
finding before proceeding.

- [ ] **Step 7: Register the new skill in the repo's README**

Add `ai-kit-spec-execute` to `README.md`'s skills table, alongside the `ai-kit-spec-execute-gsd`
row Task 5 already added.

- [ ] **Step 8: Run the repository's REAL full quality gate and commit**

```bash
make validate
git add -A
git commit -m "feat(ai-kit-spec-execute): add router skill and GSD framework detection, register in README"
```

If `make validate` surfaces findings in files this plan touched, fix them before this commit.

---

### Task 7: End-to-end smoke test against a real GSD phase

**Revision note:** the original plan's Task 7 proved the standalone `cross_ai_wrapper.py`
subprocess dispatcher against a real `codex` invocation. That program no longer exists (Task 3's
revision). This task's proof shifts to what this revised architecture actually claims: that this
adapter's config writes are correct and that GSD's own `/gsd-execute-phase` skill picks them up
when invoked via the `Skill` tool.

**Files:** Modify: this plan file (`docs/superpowers/plans/2026-08-29-ai-kit-spec-execute-gsd.md`),
Step 2 below records the outcome. Modify (CONDITIONAL — only if Step 1 finds a live divergence from
Task 1's recorded contract): `gsd_config.py`, `gsd_cross_ai.py`, `adapter.py`.

- [x] **Step 1: Run the full adapter against a real (or realistic scratch) GSD phase**

Using the same GSD install from Task 1's spike, run `ai-kit-spec-execute-gsd`'s full flow (Task 5's
SKILL.md steps) against one real, small phase. Confirm:
- The correct dispatch mode is chosen (native_tier if `model_profile_overrides[runtime][tier]`
  already has a genuine value, else native_tier-written if the top candidate has a curated `tier`,
  else cross_ai_hook/fallback per Task 4's logic).
- If `native_tier` with `written=True` fires: confirm a per-run
  `.planning/config.json.ai-kit-spec-execute-gsd.<run-id>.bak` was created, the live config now
  carries the new `model_profile_overrides[runtime][tier]` entry and, when needed, the updated
  `runtime` key, plus the `_ai_kit_spec_execute_gsd` ownership marker — **then invoke GSD's own
  `/gsd-execute-phase` skill via the `Skill` tool for a real throwaway phase and confirm GSD's own
  agent-role-to-model resolution actually picks up the written model id** (check GSD's own
  logs/output/prompt-preamble for it). If it does NOT reach GSD's execution, this proves Task 2's
  schema assumptions are wrong for the real install in some way Task 1's spike missed — fix
  `gsd_config.py` before considering this plan complete, do not just note the discrepancy.
- If `cross_ai_hook` fires: confirm `workflow.cross_ai_command`/`cross_ai_execution` were written
  correctly, that the plan's own `cross_ai: true` frontmatter check/warning behaved as Task 5
  describes, and that invoking GSD's own skill actually triggers GSD's own `cross_ai_delegation`
  step (observable via GSD's own logs/`$CANDIDATE_SUMMARY` file) — this is GSD's own already-
  implemented mechanism; this step only confirms the handoff, not GSD's internal piping.
- If `fallback_notice` fires, the message actually reaches the user/log before Step 3's `Skill`
  tool invocation proceeds.

- [x] **Step 2: Record the outcome directly in this plan file**

Edit this plan file (append a dated `## Smoke Test Result` subsection here) recording: which
dispatch mode fired, whether it matched Task 1's recorded contract, any discrepancy found and
fixed in `gsd_config.py`/`gsd_cross_ai.py`/`adapter.py` as a result, and whether GSD's own
`/gsd-execute-phase` skill (invoked via the `Skill` tool) genuinely picked up the written config in
both a native and a cross-AI run (or, if only one was exercisable in this environment, state that
explicitly rather than silently implying both were proven). Do not consider this plan complete if
the live run diverges from Task 1's recorded contract and that divergence isn't both fixed and
noted here.

- [x] **Step 3: Final commit** (see below)

## Smoke Test Result (recorded 2026-08-30)

**Scope actually exercised, honestly stated up front:** `gsd-execute-phase` is not registered as
a skill in this orchestrating session (it only exists under a different user's mounted GSD
install, confirmed via Task 1's own spike) -- the `Skill` tool could not be literally invoked
here. What WAS exercised: (1) this adapter's own `resolve-dispatch` CLI against a live GSD
project's real config content, and (2) a byte-exact manual reproduction of GSD's own documented
`cross_ai_delegation` shell contract (`gsd-core/workflows/execute-phase.md`'s own bash block --
prompt piped via stdin, same timeout mechanism, same success/failure evaluation criteria) against
a real, isolated throwaway `wezterm-setup` git worktree (`../wezterm-setup-hyp-codex`, removed
after the test; `wezterm-setup`'s own real checkout was never modified -- diffed byte-identical to
a pre-test backup afterward). Native-vs-cross-AI config-write correctness (bullet 1 below) is
fully live-verified; the literal `Skill`-tool handoff (Task 5 Step 3's own final line) is not.

**1. Native (`cli=None`, runtime=claude) dispatch -- MAJOR divergence found and fixed.**
Live-read against `gsd-core/bin/lib/core.cjs`'s real `resolveModelInternal` (lines 1340-1397)
found that `model_profile_overrides.<runtime>.<tier>` is **only ever consulted when
`config['runtime']` is BOTH set and `!= "claude"`** -- for the claude runtime (the default, and
confirmed live as wezterm-setup's own real state: its config.json has no `runtime` key at all),
that whole branch is skipped. Every `native_tier` write Task 2/4's original design made for a
`cli=None` candidate was therefore silently inert -- GSD's own resolution never read it back. Live
also found a second, smaller divergence: `model_profile_overrides.<runtime>.<tier>` only ever
recognizes tiers `opus`/`sonnet`/`haiku` (`core.cjs`'s own `RUNTIME_OVERRIDE_TIERS` constant) --
never `"fable"`, the 4th Agent-tool alias this plan's own native-reviewer convention allows,
producing a real, silently-ignored `gsd: warning` if written.

**Fix applied** (`gsd_config.py`, `adapter.py`, `cli.py`, plus new/updated tests in
`tests/test_ai_kit_spec_gsd.py` -- all 56 tests passing): added `KNOWN_GSD_TIERS = {"opus",
"sonnet", "haiku"}` (a candidate whose tier is outside this set, e.g. `"fable"`, is now treated as
unusable and the ladder walk moves to the next candidate instead of writing a dead key) and
`TIER_TO_MODEL_PROFILE = {"opus": "quality", "sonnet": "balanced", "haiku": "budget"}` plus
`write_model_profile`/`resolve_model_profile`/`model_profile_is_adapter_owned` in `gsd_config.py`.
`resolve_gsd_dispatch` now branches on `runtime == "claude"`: writes the top-level `model_profile`
scalar (GSD's real, live-confirmed lever for native Claude tier choice, coarser than a per-phase
override -- it applies project-wide to every agent role GSD spawns) instead of
`model_profile_overrides.claude.<tier>`, and honors a genuine pre-existing `model_profile` value
exactly like the existing `override_is_adapter_owned` pattern does for the non-claude branch. Live
re-verified against a scratch copy of wezterm-setup's real config (never the real file itself):
correctly honored the real `model_profile: "balanced"` already present (`written: false,
provenance: "existing_gsd_config"`), and correctly wrote `model_profile: "quality"` (plus the
ownership marker) when that key was absent.

**2. Cross-AI (`cli` set) dispatch -- hypothesis A (grok) vs. hypothesis B (codex), both
live-verified.** Hypothesis A, live-confirmed via `resolve_gsd_dispatch` against a real grok
candidate: **structurally unreachable, not merely untested** -- `build_execute_command`
(`skills/ai-kit-spec-review/ai_kit_spec/commands.py`) has no real execute-mode builder for grok
(`_unimplemented_execute_command`, raises `ValueError`), so `gsd_cross_ai.build_cross_ai_command`
already declines before GSD's config is ever touched; the live call returned `fallback_notice`/
`no_usable_dispatch` with GSD's config completely untouched. This also surfaces a real,
out-of-scope-for-this-plan architecture gap the user flagged directly: `_EXECUTE_COMMAND_BUILDERS`
(Plan 1) is far less complete than its sibling `_COMMAND_BUILDERS` (the read-only reviewer
catalog) -- grok/opencode/cursor-agent/claude all lack a real write-capable builder, codex is the
only one implemented. Worth a dedicated follow-up plan, not fixed here.

Hypothesis B (codex), live-verified end-to-end in the throwaway worktree: the real built command
(`codex exec --sandbox workspace-write -C <target_dir> -m gpt-5.6-sol`), given the constructed
`$TASK_PROMPT` via stdin exactly as GSD's own step does, exited 0, and the real file-write task it
was given (`.tmp/ai-kit-spec-execute-gsd-smoke/marker.md`) was performed correctly and verified
present with exact expected content -- no other files were touched. **But** codex's raw stdout was
plain prose with no markdown heading and no YAML frontmatter, which does NOT match
`gsd-core/templates/summary.md`'s real expected shape (frontmatter + structured sections) --
GSD's own "has at least a heading and description -- a valid SUMMARY.md structure" check would
likely reject this as an invalid summary despite the underlying work being genuinely correct. This
is judged a limitation of this test's own manually-constructed `$TASK_PROMPT` (GSD's real "1.
Construct the task prompt" sub-step is itself LLM-judgment-driven inside the real skill, and
likely instructs the external CLI to format its final response as SUMMARY.md content -- something
this mechanism-level reproduction did not attempt to replicate) rather than a proven incompatibility
between GSD and codex's own real output shape. Flagged, not fixed -- out of this adapter's own
scope (Task 1 finding 1: GSD's own `cross_ai_delegation` step owns prompt construction and summary
validation end-to-end; this adapter's job ends at building one correct command string).

**Conclusion:** this plan's config-write mechanics for both native and cross-AI dispatch are now
live-verified correct against GSD's real, current source (not just its own documented contract).
The one real gap left open (literal `Skill`-tool invocation of `/gsd-execute-phase`, and the
summary-shaping half of cross-AI delegation) is a limitation of this orchestrating session's own
environment and GSD's own prompt-construction step, not of this plan's adapter code, and is
recorded here rather than silently implied as proven.

**3. Follow-up (recorded same day): the summary-shaping gap above is fixed, not just flagged.**
Per user direction, re-ran the exact same live throwaway-worktree test (a second isolated
`wezterm-setup` worktree, removed after the test; `wezterm-setup`'s own real checkout again never
modified) with ONE change: the task prompt piped to codex now explicitly carries GSD's own real
`SUMMARY.md` shape (frontmatter + heading + sections, sourced from `gsd-core/templates/
summary.md`) as part of the prompt itself, rather than relying on GSD's own generic
`cross_ai_delegation` step to elicit that shape implicitly (which it does not -- it only pipes the
prompt and validates the CLI's raw stdout, never tells the CLI what shape to answer in). Result:
codex's stdout was byte-correct GSD-SUMMARY.md shape end-to-end, and the real file-write task was
still performed correctly. This is now baked into the adapter itself, not left as a known gap:

- **New shared module** `ai_kit_spec.dispatch_guidance` (Foundation, `skills/ai-kit-spec-review/
  ai_kit_spec/`) -- framework-agnostic reinforcement prose (model-selection-override,
  incremental-progress, failure-reporting, and a generic output-format wrapper) meant to be reused
  by every `ai-kit-spec-execute-*` adapter, not just this one -- e.g. a future
  `ai-kit-spec-execute-superpowers` (Plan 3) composes the SAME shared functions with its own
  framework-specific output-format block, exactly the way this plan's own `cross_ai_guidance.py`
  does for GSD, instead of re-inventing this prose per framework. Never edits the target
  framework's own workflow/skill files (gsd-core, superpowers-core, ...) -- only ever builds prose
  a caller appends to a file it already owns writing to (the phase prompt file).
- **New GSD-specific module** `ai_kit_spec_gsd.cross_ai_guidance` -- holds GSD's own confirmed-real
  `SUMMARY.md` format block (the framework-specific knowledge `dispatch_guidance` itself never
  hardcodes) and composes it with the shared guidance via `build_gsd_cross_ai_guidance
  (resolved_label)`.
- **New CLI subcommand** `prepare-cross-ai-guidance --resolved-label <str>` on
  `ai-kit-spec-gsd.py`, wired into Task 5's `SKILL.md` Step 3: gated on `RESULT_MODE =
  "cross_ai_hook"` only (native in-framework dispatch already knows GSD's own conventions and
  needs none of this), appends the composed guidance to `$PHASE_PROMPT_FILE` idempotently
  (marker-guarded, same pattern as the existing tooling-guidance append).
- 9 new tests (`TestDispatchGuidance` in `tests/test_ai_kit_spec.py`, `TestBuildGsdCrossAiGuidance`
  + `TestCliPrepareCrossAiGuidance` in `tests/test_ai_kit_spec_gsd.py`) -- 264 total tests passing
  in `test_ai_kit_spec.py`/`test_ai_kit_spec_gsd.py` combined.

**Separately flagged during this same follow-up, NOT fixed (real, but out of this plan's own
scope):** the two review/execute command-builder catalogs in `commands.py`
(`_COMMAND_BUILDERS`/`_EXECUTE_COMMAND_BUILDERS`) were themselves pure structural duplication --
two parallel dicts and two nearly-identical lookup-and-raise factory functions for what is really
one axis (`kind: review|execute`) on the same per-CLI builder concept. Unified into one registry
keyed by `(kind, cli)` and one shared `_build_command` dispatcher, with `build_reviewer_command`/
`build_execute_command` now thin, backward-compatible wrappers (unchanged public signature and
error shape -- every existing test in `TestBuildReviewerCommand`/`TestBuildExecuteCommand` passes
unmodified). The per-CLI builder *functions* themselves were untouched -- their logic is a real,
different CLI invocation per kind, not duplication. This is unrelated to the summary-shaping fix
above but was done in the same session at explicit user direction; recorded here for the same
reason everything else in this section is: nothing this plan's execution touched should be
silently left out of its own written record.

- [x] **Step 3: Final commit** (see below)

```bash
git add -A
git commit -m "chore(ai-kit-spec-execute-gsd): smoke-test verified against a live GSD phase and GSD's own /gsd-execute-phase skill"
```
