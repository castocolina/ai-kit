# open-gsd: setting combinations, granularity numbers, model-profile how-to, changelog, graph refresh

Researched 2026-11-02, read-only. Builds on `1-open-gsd-config-docs.md` (not repeated here).
Upstream = open-gsd/gsd-core branch `next` (the default branch), fetched with `gh api`.
Local = `.claude/gsd-core/` (VERSION 1.18.0).

Files in this folder:
- `q5_fetch.sh`, `q5_fetch2.sh`: download the upstream files into `upstream-docs/` and `upstream-docs/next/`.
- `q5_changelog.py`: summarizes the changelog sections newer than a given version.
- `q5_granularity.sh`: lists every granularity count statement, upstream and local.

---

## 1. "Common Setting Combinations" (CONFIGURATION.md, end of Workflow Toggles)

Quoted faithfully. The intro reads: "The following combinations of `mode`, `granularity`,
`model_profile`, and workflow toggles are commonly used together. See [Configure model
profiles](how-to/configure-model-profiles.md) for setup guidance."

The table has six keys per scenario. `research`, `plan_check` and `verifier` are `workflow.*` toggles.

- **Prototyping**: `mode: yolo`, `granularity: coarse`, `model_profile: budget`, research `false`,
  plan_check `false`, verifier `false`.
- **Normal development**: `mode: interactive`, `granularity: standard`, `model_profile: balanced`,
  research `true`, plan_check `true`, verifier `true`.
- **Production release**: `mode: interactive`, `granularity: fine`, `model_profile: quality`,
  research `true`, plan_check `true`, verifier `true`.

No purpose text goes beyond the scenario name. USER-GUIDE.md repeats the same table as
"Speed vs Quality Presets", calling the rows "Normal dev" and "Production". Its only extra line is:
"When running in `yolo` mode, set `workflow.skip_discuss: true` via `/gsd-settings`."

**Neither table mentions `mvp_mode` or `dynamic_routing`.** I searched CONFIGURATION.md,
USER-GUIDE.md and FEATURES.md and found no recommended pairing of `mvp_mode` with any other key.
The docs present `dynamic_routing` on its own, as "structurally a *cost lever*: you pay Opus rates
only for the hard cases that warrant Opus. Compose with `model_overrides` for per-agent exceptions
(override always wins)". The how-to shows `tier_models` light=haiku, standard=sonnet, heavy=opus.

**A second, implicit pairing** comes from the `/gsd-new-project` auto mode. It lives in
`workflows/new-project/steps/auto-mode-config.md`, and the file is the same locally and on `next`.
- Auto mode is YOLO ("auto = YOLO").
- It labels **"Coarse (Recommended)"** for granularity and **"Adaptive (Recommended)"** for the
  model profile ("heavy roles use the highest-tier model available on the active runtime, light
  roles use the cheapest").
- Earlier research found that auto mode also forces MVP on every phase.
- So the de facto auto preset is: yolo + coarse + adaptive + MVP + research, plan check and
  verifier all on. That conflicts with the doc's "Prototyping" row, which turns those three
  toggles off and uses `budget`. Nothing enforces either preset.

---

## 2. How granularity changes phase and plan counts

**Authoritative: 2-4 / 4-6 / 6-10 phases.** Two things make this the current number:
- The agent that actually builds the roadmap uses it.
- The roadmapper says outright that the older numbers were replaced.

`agents/gsd-roadmapper.md` (Granularity Calibration), identical locally and on `next`:

> Read granularity from config.json. Granularity controls compression tolerance.
> | Coarse | 2-4 | Combine aggressively, critical path only |
> | Standard | 4-6 | Balanced grouping (tightened from 5-8 in 2026-05; downstream observation that the prior baseline encouraged ~15-20% over-fragmentation, often manifesting as thin "maintenance" phases that would have been better folded into a neighbor) |
> | Fine | 6-10 | Let natural boundaries stand |
> **Key:** Derive phases from work, then apply granularity as compression guidance. Don't pad small projects or compress complex ones.

The same numbers appear in CONFIGURATION.md Core Settings ("Controls phase count: `coarse` (2-4),
`standard` (4-6), `fine` (6-10)") and FEATURES.md line 262.

**Plans per phase** come from the planner, `references/planner-guidance.md` (same locally and on
`next`): Coarse 1-3, Standard 3-5, Fine 5-10 plans, with 2-3 tasks per plan in each case.

**Stale numbers, 3-5 / 5-8 / 8-12 phases.** These are pre-2026-05 values that were never updated.
They are still on `next`, so this is not a local-only drift. Each place, with its local path:
- `workflows/new-project.md` lines 479-481: the interactive question "Fewer, broader phases (3-5
  phases, 1-3 plans each)" / "(5-8 phases, 3-5 plans each)" / "(8-12 phases, 5-10 plans each)".
  The plan counts there match the planner; only the phase counts are stale.
- `workflows/new-project/steps/auto-mode-config.md` lines 16-18: the same text in auto mode.
- `templates/roadmap.md` line 108: "Phase count depends on granularity setting (coarse: 3-5,
  standard: 5-8, fine: 8-12)".
- `references/gate-prompts.md` line 87: the `depth-select` pattern, "Quick (3-5 phases, skip
  research) | Standard (5-8 phases, default) | Comprehensive (8-12 phases, deep research)". This
  one uses the old depth names, not the granularity names.

So the user picks from stale numbers, and the roadmapper then applies the tighter ones. An ai-kit
skill that explains granularity should quote 2-4/4-6/6-10 phases and 1-3/3-5/5-10 plans. It should
treat the question text as an upstream doc bug, which could be reported upstream.

---

## 3. `docs/how-to/configure-model-profiles.md` (upstream `next`, 334 lines)

### The procedure, in its order
1. **Pick a profile.**
   - Profiles: `quality`, `balanced` (the default), `budget`, `adaptive`, `inherit`. The table
     shows Planner/Executor/Researchers/Verifier per profile; "All 33 shipped agents" have a
     per-profile tier in `model-catalog.json` (the catalog actually has 35).
   - Two ways to set it: "Quick switch via command: `/gsd-config --profile <name>`", or "**Or
     edit `.planning/config.json` directly**".
2. **Per-agent exceptions: `model_overrides`.**
   - Values: `opus|sonnet|haiku|fable|inherit` or any full model ID.
   - On Claude, a full ID naming the current tier default collapses to the tier alias. Any other
     full ID resolves verbatim, with a warn-once note (#4192).
   - It can be set per project or in `~/.gsd/defaults.json`; per project wins on conflict.
   - **Codex and OpenCode bake the model in at install time:** "after editing `model_overrides`
     you must re-run the installer" (`npx @opengsd/gsd-core@latest --codex --global`). Workflow
     entry commands warn when config is newer than the agent files; Claude is unaffected.
3. **Phase-type tiers: `models`.**
   - Six slots, tier aliases plus `inherit` only. "For a fully-qualified model ID, use
     `model_overrides` per agent instead."
   - It combines with a `model_overrides` exception.
4. **Dynamic routing.**
   - Set `dynamic_routing.enabled: true` with `tier_models` {light: haiku, standard: sonnet,
     heavy: opus}, `escalate_on_failure: true` and `max_escalations: 1`.
   - On a soft failure the agent is re-spawned one tier up. "Agents that already sit at `heavy`
     cannot escalate further."
   - `escalate_on_failure: false` keeps the fixed tier-to-model map without the retries.
   - **`provider_escalation`**: an ordered list of fallback model IDs that is used only on
     quota or rate-limit failures. The walk is capped at `min(max_escalations, list length)`,
     and GSD waits out `Retry-After`.
   - When the list is spent, GSD "names every model it tried and hands you the normal recovery
     prompt". This is close to ai-kit's own quota-routing idea.
5. **Non-Anthropic runtimes.**
   - `resolve_model_ids: "omit"` is set by the installer.
   - Codex passes model and effort on each spawn only when the spawn schema advertises them.
     Otherwise you pin real Codex IDs in `model_overrides`; tier aliases and `claude-*` IDs are
     dropped with a warning.
   - It suggests a Sol/Terra/Luna split by agent, or by `models` phase type.
6. **Precedence**, then a "Choosing the right lever" table. The rows are profile / `models` /
   `model_overrides` / full ID / `model_profile_overrides.claude.<tier>` to pin a generation /
   `dynamic_routing` / `inherit`.

### What the how-to does NOT cover
- **Effort.** The how-to never explains how to set effort. It only says "Effort is a separate
  lever from model, and it is now per-model" and links to CONFIGURATION.md.
- **`gsd-tools` commands.** It names no `config-set`, no `effort sync` and no `gsd-tools`
  command at all. Its only two routes are `/gsd-config --profile` and hand-editing config.json.
  So the how-to does **not** say "use gsd-tools instead of hand-editing".
- **Where the command guidance actually lives.** It is spread across CONFIGURATION.md and the
  local workflows:
  - CONFIGURATION.md shows `gsd config-set <key> <value>` in many places (review lanes,
    planner stall, chunked planning, hooks, security, and others), and `gsd-tools query
    config-set ...` for agent_skills, mempalace and features.
  - The local `/gsd-settings` workflows write every value through `gsd_run query config-set <key>
    <value>`. `settings-advanced.md` says: "Apply each selected value via `gsd_run query
    config-set <key> <value>` so the central [validator runs]".
  - `/gsd-config --profile <name>` runs `gsd-tools query config-set-model-profile`
    (`.claude/commands/gsd-config.md`).
  - Effort apply step, local `references/model-profiles.md`: "An effort config change has no
    effect until `gsd_run effort sync --apply` re-syncs the agent files". CONFIGURATION.md adds
    that `effort sync` also maintains the OpenCode `variant` key "so changing `effort` config
    does not require a reinstall".
- **Precedence lists disagree.** The how-to lists **6** layers: model_overrides →
  dynamic_routing.tier_models → models → **model_profile_overrides.<runtime>.<tier>** ("honored on
  the claude runtime too", #4192) → model_profile → runtime default. CONFIGURATION.md lists 5
  layers twice and leaves out `model_profile_overrides`. Earlier research showed that
  `model_profile_overrides` maps a tier to a model *after* the tier is chosen, so the how-to's
  list mixes two stages. I did not test this live.

### Commands checked against the local 1.18.0 `gsd-tools.cjs` (read-only, or in a throwaway temp dir)

Every command these docs name exists locally:
- `config-set <key.path> <value>` exists, and the `query` prefix is accepted and stripped:
  `gsd_run query config-get model_profile` and `gsd_run config-get model_profile` both returned
  `"balanced"`.
- `config-get`, `config-set-model-profile <quality|balanced|budget|adaptive|inherit>` and
  `resolve-execution`, `resolve-model` and `resolve-granularity` all exist.
- `effort sync`: "Available: sync". It is a **dry run by default**. `--apply` writes, and it
  also takes `--dry-run`, `--config-dir <dir>` and `--runtime <rt>`. A dry run in this repo
  returned `synced 0, skipped 35`, so the agent files match the config.
- The `gsd_run` launcher exists at `.claude/gsd-core/bin/gsd_run`. It is not on PATH outside a
  GSD session. There is no `gsd` binary anywhere, and the npm package exposes only `gsd-core`,
  `gsd-tools`, `gsd_run` and `gsd-mcp-server`. So the docs' bare `gsd config-set ...` only works
  through the npm bin or a session alias; a skill should call
  `node <project>/.claude/gsd-core/bin/gsd-tools.cjs` or that project's `gsd_run`.

Two catches found in the temp-dir test, both on local 1.18.0:
- **`config-set` does not validate effort values.** `config-set
  effort.routing_tier_defaults.heavy bogus` returned `updated: true`. The resolver then silently
  ignored the value: `resolve-execution gsd-planner` reported `effort: xhigh`. Earlier research
  found the same silent drop for full IDs in `models.<phase>`. A skill must validate effort values
  itself (`minimal|low|medium|high|xhigh|max|inherit`).
- **`effort sync` targets the install's own `.claude/agents`, not the current directory.** I ran
  ai-kit's `gsd-tools.cjs effort sync` from a temp project. It reported `agents_dir:
  <ai-kit>/.claude/agents` and planned 19 changes computed from the temp project's config. It
  was a dry run, so nothing was written; `git status` was unchanged. In apply mode, calling one
  project's gsd-tools from another project would rewrite the wrong project's agents. Always use
  the target project's own `gsd-tools`, or pass `--config-dir`.

Smaller doc gaps:
- CONFIGURATION.md documents `query resolve-execution --json`. Local 1.18.0 rejects that:
  "Unknown flag for resolve-execution: --json". It prints JSON by default.
- The local `settings-advanced.md` lets you set `effort.*` keys but never runs `effort sync`, so
  a change made there does nothing on Claude until someone syncs.

---

## 4. CHANGELOG

**Location:** the repo root, `CHANGELOG.md`, is the same on `main` and `next`. The local
`/gsd-update` workflow downloads
`https://raw.githubusercontent.com/open-gsd/gsd-core/main/CHANGELOG.md`.
`docs/RELEASE-NOTES-LEGACY.md` covers the pre-fork era. The install itself ships no changelog.

**Format:**
- It follows "Keep a Changelog" 1.1.0, with an `## [Unreleased]` section and
  `## [x.y.z] - YYYY-MM-DD` headings.
- It uses only the sections Added, Changed, Fixed, Removed and Security. Counts across 27
  releases: Added 19, Changed 19, Fixed 25, Removed 8, Security 13.
- Each bullet is a bold one-line title plus a long prose explanation and issue/PR numbers.
- **No severity labels** appear on bullets, and there is **no "Breaking" section or marker**.
  Breaking or behavior changes show up only as prose in Changed or Removed. Advisory IDs
  (GHSA/CVSS) appear only for dev-dependency bumps.
- **Security has its own section.** A skill can therefore flag "a Security section exists in the
  range" mechanically. Severity has to be judged from the prose.

**Versioning and publishing:**
- npm package `@opengsd/gsd-core`. The registry's dist-tags, read with an HTTPS GET, are
  `latest: 1.19.0` and `next: 1.7.0-rc.6`. The `next` dist-tag is stale and older than latest, so
  `/gsd-update --next` would currently point backwards.
- 44 versions are published.
- GitHub tags and releases use the `v1.19.0` form, and rc tags such as `v1.7.0-rc.6` exist. The
  release cadence is about weekly.
- Local version file: `.claude/gsd-core/VERSION`. Hook files also carry
  `# gsd-hook-version: 1.18.0`.
- Upstream's own check, `bin/check-latest-version.cjs`, shells out to `npm view
  @opengsd/gsd-core version`. **On this machine `npm` is banned**: the tools-installer wrapper
  refuses it. A skill should do one of these instead:
  - GET `https://registry.npmjs.org/-/package/@opengsd%2fgsd-core/dist-tags`, which is stdlib
    and needs no npm.
  - Run `gh api repos/open-gsd/gsd-core/releases/latest`.

  Then compare against `VERSION`, and slice CHANGELOG.md between the two `## [x.y.z]` headings.
  `q5_changelog.py` here does that slice.

**Changes from 1.18.0 to 1.19.0** (the only release newer than local; 2026-10-26; 12 Added,
1 Changed, 56 Fixed, 3 Security, 0 Removed). Rated for a project on 1.18.0 (ai-kit: Claude-hosted,
with pi and opencode as other primary runtimes, worktrees, no UI). Overall it is a **minor**
release: nothing breaking, but it has one security fix worth taking.
- **Security, worth updating for:**
  - "Typed text can no longer close the argument-capture heredoc on an installed GSD". A line
    `GSD_ARGS_END` in command arguments ended the heredoc, "and the lines after it ran as shell".
    Each install now writes a random terminator.
  - **It needs a reinstall to take effect**: "an install made before this change gets its random
    terminator the next time you reinstall".
  - This is a shell-injection path through typed or pasted arguments. I rate it the most
    important item, but low exposure for a solo user. The 1.18.0 fix "Typed command arguments no
    longer run as shell inside workflow snippets" was the first half of it.
- **Security, guard hardening:** two secret-read-guard bypasses were closed (a heredoc inside a
  `$( )`; `grep -if.env`-style bundled flags). The Fixed section has one more: a nested shell
  behind a wrapper with flags. These are the hook that blocks reading `.env` files. They matter
  if you rely on that guard; the impact is moderate.
- **Pi (a primary runtime here):**
  - Added: Pi can run GSD agent roles via a `gsd_dispatch` tool.
  - Added: `/skill:gsd-debug` runs on Pi.
  - Added: GSD guard hooks now run on Pi.
  - Added: `pi install npm:@opengsd/gsd-core` as a package.
  - Fixed: "Pi can start GSD workflows".

  This is **relevant to ai-kit**. On 1.18.0, Pi stopped at every `gsd-*` agent step and its
  guards were silent.
- **Fixes that touch how ai-kit works:**
  - "The post-wave UI safety gate no longer halts a project with no frontend". This is relevant
    because, as earlier research found, the UI gate can trip on non-UI words.
  - "Running a committing command from a subdirectory of a linked worktree no longer commits into
    the main checkout".
  - "A read-only `git` call ... can no longer fail someone else's commit with `index.lock`".
  - "`state begin-phase` no longer leaves an untracked `.planning/milestone.lock` that blocks
    `/gsd-ship`".
  - "In a multi-plan wave each executor is now dispatched against its own isolation record".
  - "`gsd_run` now stays resolvable for the rest of a Claude Code session".
  - "`config-new-project` now refuses the choices `config-set` refuses".
  - "A first install no longer silently replaces a user skill that shares a shipped GSD skill's
    name".
- **Behavior change to be aware of:** "A plan-checker return of `## VERIFICATION PASSED` that
  still lists BLOCKER or WARNING entries is now handled as `## ISSUES FOUND`". This is stricter,
  so plans that used to pass with caveats now loop. `/gsd-health --repair` can clear a legacy
  `pass_with_caveats` report.
- **Changed (1):** `/gsd-review` local-server detection moved into `review-lane availability`.
  A server that stalls the body now reads as available.
- **New opt-in:** `git.repo_tagging` (`single` by default) plus `milestone release-tags` for
  multi-repo releases. Not relevant here.
- **Registry listings:** three community capabilities (markdown linting, SOTA numerics, PR
  workflow). Information only.

---

## 5. Where graphify and intel refresh run in the lifecycle

**Short answer:** GSD never refreshes graphify or intel at phase close, ship or milestone
completion. I grepped `transition.md`, `complete-milestone.md`, `ship.md` and `verify-work.md`,
both locally and on `next`; none mentions graphify or intel. Only the following triggers exist.

**Graphify (`.planning/graphs/`):**
- Builds are manual: `/gsd-graphify build`.
- Automatic rebuild comes only from the opt-in PostToolUse hook `hooks/gsd-graphify-update.sh`.
  It is installed and registered in this repo's `.claude/settings.local.json`. Header:
  > "PostToolUse hook (Bash matcher) that auto-rebuilds the project knowledge graph after main HEAD
  > advances on the default branch. OPT-IN (issue #3347 AC): no-op unless .planning/config.json has
  > BOTH graphify.enabled: true graphify.auto_update: true"
  > Gate 2: "tool_input.command matches a HEAD-advancing git op (shell-direct or the exact
  > `gsd-tools query commit` command shape ...)"; Gate 4: "Current branch == default branch
  > (git.base_branch override, else main/master/trunk)".
- So the trigger is **any commit, merge, pull, rebase or cherry-pick on the default branch**, not
  a lifecycle step. With phase branches or worktrees it fires only when work lands on main, which
  in practice means merge or ship time. With the default `branching_strategy: none`, where
  executors commit on main, it fires on every commit.
- `references/planner-graphify-auto-update.md` explains why: the graph "is consumed automatically
  (every `gsd-planner` and `gsd-phase-researcher` step) but produced manually (`/gsd-graphify
  build` per session at best)".
- The capability manifest on `next` (`capabilities/graphify/capability.json`) declares `"hooks":
  [], "steps": []`. No lifecycle step is registered.

**Intel (`.planning/intel/`):**
- The only lifecycle step is in `capabilities/intel/capability.json` on `next`: `{"point":
  "plan:pre", "ref": {"command": "intel api-surface"}, "produces":
  [".planning/intel/API-SURFACE.md"], "when": "intel.enabled", "onError": "skip"}`. It is
  consumed in local `workflows/plan-phase.md` §7.9, "Regenerate API-SURFACE.md (intel gate)",
  with `gsd_run intel api-surface`.
- This regenerates only the API surface, before each plan-phase. A full intel refresh is manual:
  `/gsd-map-codebase --query refresh` ("spawns an agent for refresh", `gsd-intel-updater`).
  `bin/lib/intel.cjs` points to "Run gsd-tools intel update or spawn gsd-intel-updater agent".

**Related but separate: the codebase map (`.planning/codebase/`, not graphify or intel).**
`execute-phase/steps/codebase-drift-gate.md` runs `gsd_run verify codebase-drift` at
`execute:wave:post`. On drift it suggests, or with the auto-remap directive spawns,
`gsd-codebase-mapper` ("Run /gsd-map-codebase --paths {affected_paths} to refresh planning
context"), then runs `stamp-codebase-map`. This is the only refresh tied to phase execution.

So an ai-kit rule like "refresh the graph at phase close" would be ai-kit's own addition. Upstream
offers per-commit on main (graphify, opt-in) and per plan-phase (intel API surface) only.

---

I skipped: reading the 1.18.0-and-older changelog bodies beyond titles, the full USER-GUIDE and
FEATURES, and a live test of the how-to's six-layer precedence (`model_profile_overrides` against
`models`).
Risk: the `effort sync` targeting catch and the `config-set` effort validation gap were seen on
local 1.18.0 only; check them again after updating to 1.19.0.
