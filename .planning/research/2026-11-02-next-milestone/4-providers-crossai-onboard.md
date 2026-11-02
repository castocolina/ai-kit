# Research: provider discovery, cross-AI lessons, onboard versus new milestone

Read-only research, 2026-11-02. Helper scripts in this folder: `q1_scan.sh`, `q1_sources.sh`
(question 1), `q2_check.sh`, `q2_other_projects.sh` (question 2), `q3_onboard_projection.json` (the
real output of the onboard routing step, which wrote nothing: `git status` was clean before and after).

## 1. The opencode providers skill and provider/model discovery

### What the skill does today

`skills/ai-kit-opencode-providers/` (about 1,000 lines) is a small config editor, not a discovery tool.
It has two commands:

- `list`: reads the `"provider"` block of the user's `opencode.jsonc` and prints id, npm package and
  base URL (never the key).
- `remove <id>`: deletes one provider entry from `opencode.jsonc`, keeping comments and formatting,
  through an atomic write. Before deleting, it scans three places for references and only warns: the
  local review config (`.aikit/review-spec.toml`), the global review config and the cached model
  catalog (`~/.cache/ai-kit/spec/model-catalog.json`).

It never runs `opencode`, never reads `auth.json` and has no "add" or "edit". It came from the v1.0
"opencode provider management" phase and its PRD (`docs/prds/ai-kit-opencode-provider-management-v1.0-prd.md`).

### Who uses it

Nothing calls or imports it at runtime. The references are:

- Its own test (`tests/test_ai_kit_opencode_providers.py`), the unit-test lists in `Makefile` and
  `.pre-commit-config.yaml`, the pyright paths in `pyproject.toml`, the gate-scope regex in
  `tests/test_gate_scope.py`, a forbidden-words check in `tests/test_ai_kit_spec_runtimes_table.py`,
  and one README row.
- The installer installs it like any other skill (no special entry).
- Code was copied out of it rather than imported: the JSONC scanner into `tools/config_doctor_readers.py`
  and `tools/config_doctor_appliers.py`; the atomic writer into `tools/setup.py` and
  `skills/ai-kit-usage-metrics/ai_kit_usage_metrics/raw_store.py`; the path helper pattern into
  `ai_kit_usage_metrics/paths.py`. The docstrings say "ported from" on purpose (no cross-skill imports).

So the owner's reading is right in one sense: as a skill it is a narrow config editor few people
need. But the shared "which providers and models does each runtime have" code the owner wants is
not here; it already exists elsewhere (next section).

### Where provider and model discovery happens, per place

- **`skills/ai-kit-spec-review/ai_kit_spec/detection.py`: the real shared discovery code.** The
  `RUNTIMES` table names, per runtime, its binaries, the environment variable that says "this process
  runs inside it", the listing command and the model-name suffix grammar. The listers run real CLI
  commands: `opencode models` (plus a private `opencode serve` probe on opencode 2.x for image input),
  `cursor-agent models`, `codex debug models` (JSON, with effort levels), pi over its RPC mode
  (`get_available_models`, with thinking levels). Claude has no listing command, so its ids are four
  fixed aliases (fable, opus, sonnet, haiku) plus ids taken from the model catalog, with a dated fallback list.
  `build_runtimes_snapshot` gathers all of it into `~/.cache/ai-kit/spec/runtimes.json` (30-day cache,
  schema version 7). `routing.py` re-lists one runtime when a requested model is missing.
- **`model_catalog.py`, `catalog_build.py`, `model_sources.py` (same package): model facts.** They fetch
  models.dev and Artificial Analysis over HTTP and merge prices, context sizes and capabilities into
  `~/.cache/ai-kit/spec/model-catalog.json`. CLI commands: `detect-runtimes`, `fetch-model-catalog`,
  `group-models`.
- **`ai-kit-spec-config` skill:** no code of its own for discovery; its SKILL.md calls
  `detect-runtimes --save` and `fetch-model-catalog` above.
- **Curated config (`skills/ai-kit-gsd-curated-config/`):** reuses the same pipeline.
  `model_detect.py` and `catalog_adapter.py` run `detect-runtimes` and `fetch-model-catalog` as
  subprocesses, then read the two caches; `gsd_catalog.py` asks gsd-core's own `model-catalog.cjs` (a
  different source: GSD's per-agent model profiles, not what a runtime offers); `host.py` and
  `cross_ai_script.py` import the runtime table's host signals. Its SKILL.md says providers defined
  only in a project's `opencode.json` are not candidates.
- **Cross-AI runner rendering:** `cross_ai_build.py` imports `runtime_id` and the runner templates; the
  rendered `cross-ai.mjs` carries its own runtime list (only tested as a superset of `RUNTIMES`).
- **Execute adapters (`ai-kit-spec-execute-gsd`, `-superpowers`):** import `ai_kit_spec` directly and
  route through the runtimes cache; no discovery of their own.
- **Session wake (`ai-kit-session-wake/hosts.py`):** imports host signals; runs `opencode session list`
  (sessions, not models).
- **jev client (`skills/jev-fast-decision/scripts/jev_review.py`):** its own backend table (Laya,
  TypeSafe, Zen) with fixed model lists per backend and key files; not runtime discovery.
- **Config doctor (`tools/config_doctor_checks.py`):** `resolve_runtime_config_paths` finds each
  runtime's config file (Claude settings, `opencode.jsonc`, Codex `config.toml`, Cursor
  `cli-config.json`) to check settings, not models.
- **Status lines (`tools/claude_*`, `tools/cursor_*`, `tools/common_*`):** the model name comes from the
  host's own JSON on stdin; `cursor_quota.py` reads Cursor's `auth.json` for the quota API. No model
  discovery. They must stay standard-library only and must not import skill code.
- **Opencode providers skill:** reads the `"provider"` block of `opencode.jsonc` (config-defined
  providers only) and reads the review configs and model catalog for references.
- **Cursor subagents todo:** documents a hand-run `cursor-agent --list-models` listing.

### Duplication found

- Opencode config path (`OPENCODE_CONFIG_DIR`, then XDG, then `~/.config/opencode/opencode.jsonc`):
  written twice, in the providers skill's `config_paths.py` and in `config_doctor_checks.py`.
- Model catalog path: three copies (`ai_kit_spec/model_catalog.py`, the providers skill, usage-metrics).
- JSONC scanner: one original plus two ported copies (config doctor readers and appliers).
- Atomic JSON write: at least three copies (providers skill, `tools/setup.py`, usage-metrics), plus
  the cache writer in `ai_kit_spec/cache.py`.
- Runtime lists copied by hand (runner list, host list, host-binary map, plan-editor error text, the
  JS runner's list): already in the tooling todo ("runtime lists copied by hand ... no test comparing
  them with the runtime table").
- Not duplicated: actual model listing. Only `detection.py` runs the listing commands.

### Does a shared discovery module exist, and does the idea fit AGENTS.md

Yes, in substance: `ai_kit_spec/detection.py` plus the two caches (`runtimes.json`,
`model-catalog.json`) and the `detect-runtimes` / `fetch-model-catalog` commands. It is the single
source of truth AGENTS.md names, and the other skills already use it. What is missing:

1. It lives inside one skill (`ai-kit-spec-review`), so other skills reach it by sibling-path imports or
   by running that skill's CLI. There is a working precedent for a shared package:
   `skills/_shared/ai_kit_rules_common/`, which the rules skills reach through a path computed from their
   own real location. A `skills/_shared/` runtime-discovery package (the runtime table, listers, cache
   paths, opencode config path) fits the architecture, as long as `RUNTIMES` keeps one home and
   "installed" and "hosting this process" stay separate questions.
2. Config-defined opencode providers are not read by discovery; it relies on `opencode models`
   listing them. Whether `opencode models` includes providers that exist only in `opencode.jsonc` was
   not checked here (unverified).
3. The status lines cannot use a skill package (standard-library-only runtime code, and the arch test
   keeps host modules apart). That is fine: they need no discovery.

Risk to note: the `_shared` pattern works because installed skills are symlinks back into the
checkout. The backlog item to install skills as real copies through the `skills` CLI (999.14) would
break it unless `_shared` is copied too. A discovery package should be planned together with that item.

Suggested shape for the owner to discuss (not decided): turn the providers skill's "list" into one
view of a broader "what does each runtime offer" command built on the existing detection code, keep
`remove` as is or drop it, and move the copied path helpers to the shared package.

### Existing backlog or todo items on this

None about a shared provider or model discovery module, nor about the providers skill's purpose.
Closest items: the tooling todo's "runtime lists copied by hand" entry, the "secret-shape scanner, four
copies, share one?" owner decision, and the lane-table todo (effort support per model must be detected
per runtime, which needs this discovery). Suggest adding a todo or backlog entry.

## 2. Cross-AI lessons: are they all captured?

Mostly yes. The big lessons file `.planning/phases/999.15-cross-ai-chain-skill-for-execute-and-review-runs/999.15-LESSONS.md`
(509 lines) and the shipped runner and skills (`skills/ai-kit-cross-ai/`, `references/cross-ai.mjs`,
`cross-ai-errors.json`) already cover: the retry ladder, quota by route, wait once on `retry_after_s`,
timeouts of 1800 s and more, the real-home guard and the real-config time check after runs, reviewer
lanes escaping their read-only brief, false completion and fabricated hashes, plan defects that look
like executor failures, leaked processes, prompt rails, wake on quota, error rows, the idle watchdog
(999.5) and pi's silent stdout. The "explicit `--model`" rule is in the Cursor subagents todo.

### The lane-table capture from the owner

It is captured: todo `2026-10-29-unify-review-execute-lane-toml-effort-escalation-and-jev-classification.md`
covers one `[[reviewers]]` table for both roles (as an open question), effort support per model,
escalation across runtimes in declared order and across models of one runtime (both opt-in, off by
default), and jev classification of input and output, behind an on/off switch in the TOML. It is also
listed in the inputs document (features theme) and is a prerequisite of the cross-AI chain skill (999.15).

### Lessons NOT captured anywhere in todo, backlog or the inputs document

1. **The memory file for the retry ladder is out of date and contradicts the shipped policy.**
   `feedback_external_run_retry_ladder.md` still says "wait several minutes (10 min default, 4 h cap)"
   after a router quota error; the shipped policy since the Phase 25.1 work is "wait once, for
   `retry_after_s`, never a repeated job". The milestone audit fixed the same contradiction in the
   goal-prompt skill, but not in memory. llm-env's `AGENTS.md` also still says "wait several minutes".
2. **The memory rule "poll output growth to tell slow from broken" is wrong for pi.** The lessons file
   says so (pi `-p` prints nothing until the end), but `diagnosing_killed_background_cli_dispatches.md`
   is unchanged.
3. **`.planning/config.json` does not match the owner's reviewer rules.** It lists referee-one, -two and
   -three as three parallel default reviewers, all through `opencode`; memory says run one and two
   through pi, use three only to replace a failed one, and keep going with whatever single judge is
   available. Nothing in todo or backlog says to encode the substitution rule or the pi route in config
   or tooling.
4. **Referee findings were mostly refuted in llm-env.** The llm-env handoff of 2026-11-02 says reviewers
   refuted most of the referee lane's findings and only the native lane found real defects; the ai-kit
   rule is "no native Opus judge". This trade-off is not recorded in ai-kit.
5. **Briefs for cheap executors.** The close handoff's lesson 4 says every executor brief must name the
   exact gates ("run the unit and arch groups") and the commit-guard block (`<sequential_execution>`),
   and a plan checker must re-read amended plans before execution. The live-checks todo records only the
   symptoms (arch test left red, uneven commit guard) as owner proposals; no item says "add these to the
   brief template".
6. **Effort only for review and planning roles.** Memory (full-permission note) says set high effort only
   for review and planning; the lane-table todo asks whether a model supports effort, not which role gets it.
7. **Masked opencode review-lane errors and stale codex login.** GSD's opencode review lane hides a 403
   behind a generic "no assistant text" stub; `codex login status` says "logged in" while the refresh token
   is dead. The codex string is in the runner's error catalogue; the opencode masking is not recorded
   (probably obsolete now that reviews run through pi; worth one line in the 999.15 lessons).
8. **llm-env's monitoring rule.** "Poll output and `ps` by PID at least every 5 minutes; never
   `pgrep -f`/`pkill -f` with a self-matching pattern." Not in ai-kit's runner lessons; partly covered
   by the idle watchdog (999.5).

Process lessons from the close handoff (time-box subagents, scripts in files, plain words) live only in
memory files. That is enough for agent behaviour; the playbook-skill idea (999.16) has a "subagent
delegated" event that could hold them.

Other projects: of the recent Claude project folders, only ai-kit has a memory folder (agent-toolkit,
llm-env, tools-installer and the old v1.3 worktree have none). Only the llm-env `AGENTS.md` and its
newest handoff were skimmed, which gave items 1, 4 and 8. No large transcripts were read.

## 3. `/gsd-onboard` or `/gsd-new-milestone` first

### What onboard does

`.claude/gsd-core/workflows/onboard.md` is a router. It runs `gsd-tools init onboard`, which works out
one next step, prints which command to run, and exits. It never runs that command itself. The only file
it writes itself is `.planning/onboarding/SUMMARY.md`, and only if it is missing; it never overwrites.
The order of checks (`bin/lib/onboard-projection.cjs`): missing codebase map, partial planning, docs to
ingest, new project, write summary, ready.

Real result on this repo (`q3_onboard_projection.json`):

- next step: `map-codebase` ("existing code was detected, but the required `.planning/codebase/` map is
  missing"); none of the seven map files exist.
- `onboarding/SUMMARY.md` already exists (written 2026-10-18 during v1.3; it says the map was skipped by
  the owner's choice because the repo is CodeGraph-indexed).
- `REQUIREMENTS.md` is missing (normal: it was archived as `v1.3-REQUIREMENTS.md` at the milestone close).
- 77 doc candidates found.

So running onboard now would: (a) ask to map the codebase; (b) if skipped, see that `REQUIREMENTS.md`
is missing and say "planning is incomplete, run a lower-level command" without naming one. That is a
false alarm after a milestone close: `/gsd-new-milestone` is the command that writes the new
`REQUIREMENTS.md`. It is built for a repo with no GSD setup, or a half-set-up one, not for one with a
closed milestone. It would overwrite nothing.

### What `/gsd-new-milestone` does

`.claude/gsd-core/workflows/new-milestone.md` is the "existing project, next cycle" command. It reads
`PROJECT.md`, `MILESTONES.md` and `STATE.md`, takes the milestone goals from the conversation (or a
`MILESTONE-CONTEXT.md`), offers matching seeds, picks the version, updates `PROJECT.md` and `STATE.md`,
optionally runs four parallel researchers into `.planning/research/`, writes `REQUIREMENTS.md`, calls the
roadmapper to add phases (numbering continues after 27 unless `--reset-phase-numbers`), and commits.
The researchers and the planner use a codebase map only if it exists ("from PROJECT.md or codebase map").

### Verdict

`/gsd-new-milestone` is the right first step, fed with `.planning/milestones/NEXT-MILESTONE-INPUTS.md`
after the owner's own topics are added (the inputs file's "How to start" already says this). Onboard
first adds nothing except the map prompt.

The only real value would be mapping (`/gsd-map-codebase`). Weigh it on its own:

- For: researchers, the planner and discuss-phase would read seven ready-made documents (stack,
  architecture, structure, conventions, testing, integrations, concerns) instead of exploring each time;
  useful if the milestone has broad refactors (the skill refactor, a shared discovery package).
- Against: this repo already has CodeGraph, which gives the same context live. The map goes stale, and
  once it exists `execute-plan` updates it after every plan and amends the commit (more churn per plan).
  The owner skipped it on purpose in v1.3.
- If wanted, run `codegraph sync` and then `/gsd-map-codebase` directly (owner's memory rule), not
  through onboard. A one-off `CONCERNS.md` could also help the milestone discussion without keeping the
  full map.

Side note: `.planning/milestone.lock` holds a claim for phase 16 from a session of 2026-09-24. It is
gitignored and advisory, and expires by age, so it should not block anything; `validate health` will show it.

---
Skipped: did not run `opencode models` to see whether config-only providers appear in it; did not read
`new-milestone/steps/*.md` in full or any large transcript. Risk: items 3 and 4 in question 2 are
owner-policy conflicts (config versus memory, native versus referee), not defects an agent should fix alone.
