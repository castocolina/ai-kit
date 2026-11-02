# Curated-config redesign: what the skill does today, and the gap to the owner's wishes

Research date 2026-11-02, read-only. Sources: `skills/ai-kit-gsd-curated-config/` at `27337d5`,
the project-local gsd-core (`.claude/gsd-core`, version 1.18.0), the upstream open-gsd
`docs/CONFIGURATION.md` and `docs/reference/agents.md` fetched from GitHub `main` (saved in
`upstream-docs/` beside this file), and the planning files and owner memories named in the brief.
Paths below are relative to the repo root; `pkg/` means
`skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/`.

Helper files in this folder: `probe-keys.js` (asks the local gsd-core which config keys it
accepts), `grep-sources.sh` and its output `grep-sources.out` (planning and memory search).

## 1. What the skill does today

### The v2 flow (the primary path)

1. **Inventory** (`SKILL.md:76-88`): snapshots the project to JSON. It detects the host CLI
   (`pkg/host.py:50-61`, which calls `detect_current_runtime`; fixed order pi > opencode > cursor >
   codex > claude), finds gsd-core project-local first and labels the scope `local` or `global`
   (`pkg/host.py:119-142`), reads the gsd-core version, warns when a worktree resolves a global
   install while the main checkout has a local one (`pkg/host.py:102-111`), probes every key the
   plan could write against gsd-core's own key validator, and records project facts
   (`pkg/project_facts.py:60-72`): frontend yes/no, database yes/no, instruction files present, the
   intel index, whether `claude_md_path` is set.
2. **Four questions in one message, nothing else** (`SKILL.md:90-104`):
   - `model_profile`: quality / balanced / budget / adaptive, with **adaptive recommended**
     (`SKILL.md:91`);
   - rigor: `mvp` / `standard` / `rigorous` (`SKILL.md:92-94`);
   - cross-AI plan review: yes / no / default;
   - cross-AI execution: yes / no / default.
   Nothing is asked about UI, granularity, language, branches, worktrees, graphify or the
   instruction file.
3. **Plan review** with `plan-set` / `plan-unset` for every open choice (`SKILL.md:106-158`).
4. **Dry run** showing every added, changed and removed key, one line per full key
   (`SKILL.md:160-174`).
5. **Apply** through gsd-tools `config-set`, with a backup, a marker and rollback
   (`SKILL.md:176-181`).
6. **Follow-ups**, approved as one group: effort sync, and a project-local gsd-core install, which is
   offered only on opencode and codex hosts (`pkg/followups.py:84-93`, `pkg/followups.py:276-300`).

### What `recommend` writes (the layers in `pkg/recommend.py:1163-1171`)

- **Rigor preset** (`pkg/presets.py:33-97`). Rigor bundles many things at once:
  - `mvp`: `granularity coarse`, `workflow.mvp_mode true`, effort tiers high / medium / minimal,
    Nyquist off, code review depth quick, security block on critical, `workflow.ui_review false`,
    **`intel.enabled false`**;
  - `standard`: `granularity standard`, effort tiers xhigh / high / low, `intel.enabled true`,
    `ui_review` follows the frontend fact (`pkg/presets.py:188-189`);
  - `rigorous`: `granularity fine`, TDD on, deep code review, ASVS level 2, fallow, the refactor
    trigger, `dynamic_routing.enabled true`, and **`workflow.ui_review true` whatever the project
    is**.
  - On every rigor, `workflow.ui_phase` follows the frontend fact (`pkg/presets.py:187`).
- **Tier layer**: `model_profile` plus `models.<phase>` shifts (mvp: research and verification on
  haiku; rigorous: planning on opus, verification on sonnet) (`pkg/presets.py:100-104`,
  `pkg/recommend.py:141-169`).
- **Per-tier model slots** `model_profile_overrides.<host>.<tier>` on non-Claude hosts only; on a
  Claude host this layer writes nothing (`pkg/recommend.py:340-353`).
- **Specialists**: at most seven `model_overrides.<agent>` entries (executor, code fixer, code
  reviewer, plan checker, UI auditor, DOM verifier, UI researcher) when the slot model fails a
  rule such as image input or a different vendor (`pkg/presets.py:22-30`,
  `pkg/recommend.py:722-735`). Agent tiers come from gsd-core's own catalog, not from our own
  judgment.
- **Cross-AI**: plan review lanes and the execution runner (`cross-ai.mjs`); when the user answers
  "default", execution **defaults to yes on a Claude host whenever another CLI target exists**
  (`pkg/cross_ai.py:50`, `pkg/cross_ai.py:151-158`).
- **Skills**: `agent_skills.<agent>` wiring, capped at 2 / 3 / 5 per agent by rigor.
- **Reconcile**: `runtime` is written only on opencode and codex hosts (`pkg/presets.py:167`,
  `pkg/recommend.py:1054-1061`). Every key in the managed families (`models.*`,
  `model_overrides.*`, `effort.agent_overrides.*`, `effort.routing_tier_defaults.*`,
  `dynamic_routing.*`, `review.models.*`, `review.effort.*`, `agent_skills.*`) that the plan does not
  carry is **unset** (`pkg/presets.py:143-152`, `pkg/recommend.py:1023-1030`).
- `claude_md_path` is never written by v2; inventory only reports a configured path that points at
  a missing file (`pkg/inventory.py:298-309`).

### The v1 path (kept, never tested by the owner)

`references/v1-path.md`: one `model_profile` question, then fixed steps. It does write
`claude_md_path`, preferring `AGENTS.md` (`pkg/claude_md_detect.py:13`), writes the UI flags from
the frontend fact, and writes a fixed workflow bundle (`pkg/workflow_defaults.py:19-47`). Its
critical-agent rule pins the code reviewer to opus/high and the executor, research and execution to
haiku (`pkg/critical_agents.py:34-79`).

## 2. Each wish against the code

**Order decisions so an answer opens or closes later questions (MVP first, then UI)**: missing.
The four questions are asked together in one message (`SKILL.md:90`). UI is never asked; it is
inferred only from `package.json` framework packages or framework words in `README.md`
(`pkg/frontend_detect.py:15-22`, `pkg/frontend_detect.py:73-87`). Requirements files, an explicit
statement from the user and a "new project, so ask" case are not handled. The README word match
also fires on any README that merely mentions React.

**MVP uses coarse; non-MVP asks fine or standard**: partly. Rigor already maps mvp to coarse,
standard to standard and rigorous to fine (`pkg/presets.py:35,55,73`). But "fine" is only reachable
through `rigorous`, which also turns on TDD, ASVS level 2, deep review, fallow, the refactor trigger
and dynamic routing, and lifts the price ceiling. Upstream also has
`granularities.<phase_type>` (CONFIGURATION.md:237), which the skill does not know about.

**MVP and granularity relate to model_profile**: missing. Rigor and profile are independent
questions, and the skill recommends `adaptive`, not `balanced`.

**Always read open-gsd `docs/CONFIGURATION.md`**: missing as a step. The skill instead asks the
installed gsd-core which keys it accepts, a live check that is stronger than the docs. The docs are
not shipped in the npm package (no `docs/` folder in the cached 1.17.0 and 1.13.0 packages), so
reading them means a network fetch from GitHub. Some skill text is already stale against them:
`DYNAMIC_ROUTING_EFFECT` says "no tier_models" (`pkg/presets.py:132-134`), but the local 1.18.0
accepts `dynamic_routing.tier_models.*` (probe result) and the docs describe it
(CONFIGURATION.md:1783-1850).

**Check whether the local open-gsd install is up to date**: missing. Inventory records only the
installed version. Today the local version is 1.18.0 and the published one is 1.19.0
(`pnpm view @opengsd/gsd-core version`).

**Detect global or local GSD, prefer local**: done (`pkg/host.py:119-142`, local first, scope
labelled, worktree warning).

**Do not install GSD into projects that do not need it**: partly. The skill needs a resolvable
gsd-core before it does anything (`SKILL.md:18`), and it offers an install only on opencode and
codex hosts. It never asks whether the project needs GSD at all. The installer follow-up is an `npx`
call (`pkg/followups.py:49-58`). On this machine `npm` is blocked by a tools-installer shim and `npx`
is an interactive-shell alias for `pnpm dlx`. Whether the follow-up's subprocess call still works
here is **unverified**.

**Preferred runtime is always Claude, but detect the current one**: partly. The skill detects the
host. On a Claude host it writes no `runtime` (gsd-core's default is claude). On opencode and codex
hosts it writes `runtime` as the host (`pkg/recommend.py:1054-1058`), which is the opposite of
"always Claude". Nothing states the preference.

**model_profile `balanced`**: conflicts. The skill recommends `adaptive` (`SKILL.md:91`).

**Our own per-agent tiers, classified with jev-fast-decision from `docs/reference/agents.md`**:
missing. Tiers come from gsd-core's catalog (`roles.agent_tier`). jev appears only as a
skill-wiring gate (`SKILL.md:321-324`). Upstream's default tier table is in CONFIGURATION.md:1804-1812
(11 light, 13 standard, 9 heavy).

**Use `dynamic_routing.tier_models`**: conflicts. That key is not in the key set the plan can
write (`pkg/presets.py:195-207`), yet the whole `dynamic_routing.*` family is managed. Applying v2
would therefore **unset** this repo's own `dynamic_routing.tier_models.{light,standard,heavy}`
(`.planning/config.json`), and the `enabled` flag too unless the rigor is rigorous.

**Per-agent model overrides**: partly, and it conflicts. Only the seven specialists can get one.
`model_overrides.*` is managed as a family, so the owner's planner pin (`model_overrides.gsd-planner:
opus`, kept by the "planner on opus" memory) would be **removed** by an apply: `gsd-planner` is not
a specialist.

**Effort per tier and per agent (haiku low/medium, sonnet medium to xhigh, opus medium to
xhigh)**: partly. Tier defaults come from the rigor. Per-agent effort exists only for the executor
and code fixer (medium) and, on rigorous, the code reviewer (xhigh). The owner's
`effort.agent_overrides.gsd-planner: xhigh` would also be unset. mvp's `light: minimal` becomes
`low` on Claude (CONFIGURATION.md: "minimal clamps to low on Claude").

**Read the per-phase-type models and resolution precedence sections**: partly. The skill writes
`models.<phase>` shifts and its specialists sit at the top layer, consistent with upstream
precedence (CONFIGURATION.md:1735-1745: overrides, then tier_models, then models, then profile).
It does not use `tier_models`, the second layer.

**UI phase and UI review only for real UI projects**: partly, and one conflict. `ui_phase` follows
the frontend fact. `ui_review` is forced on by `rigorous` even without a UI (`pkg/presets.py:89`).
The fact is a heuristic, not a confirmed answer.

**Avoid cross-AI execution, and ask the user to confirm when it is configured**: conflicts. On a
Claude host "default" means **yes** when any target exists (`pkg/cross_ai.py:151-156`). An existing
`workflow.cross_ai_execution: true` is not flagged for confirmation. This repo's own config has it
set to true.

**`response_language` English unless asked**: missing. The key is never written; upstream default
is unset (CONFIGURATION.md:245).

**`claude_md_path`: prefer AGENTS.md, and confirm when set to something else while AGENTS.md
exists**: partly. v1 detects with AGENTS.md first and writes it. v2 never writes it and only flags a
configured path whose file is missing; it does not flag "set to CLAUDE.md while AGENTS.md exists".
Upstream's default is `./.claude/CLAUDE.md` (CONFIGURATION.md:248), so leaving it unset is not
neutral.

**Worktrees and a separate branch per phase**: missing. `workflow.use_worktrees`,
`git.branching_strategy` (`phase`) and the branch templates are never written. `use_worktrees`
defaults to true upstream (CONFIGURATION.md:561); `branching_strategy` defaults to `none`
(CONFIGURATION.md:1308), and this repo's config has `none`.

**`intel.enabled = true`**: partly, and it conflicts. Standard and rigorous set it true; mvp sets
it **false** (`pkg/presets.py:52`).

**Graphify on, with auto update**: missing. `graphify.enabled` and `graphify.auto_update` are never
written (both default false upstream, CONFIGURATION.md:1165-1167).

**Git base branch (main, or sandbox/dev or the most up-to-date branch) and protected
main/dev/sandbox**: missing. `git.base_branch`, `git.protected_branches` and
`git.allow_default_branch_commits` are never written or detected. Upstream: base defaults to
`main`; `protected_branches` adds names to the resolved base; and a global defaults file cannot set
`git.*` (CONFIGURATION.md:2451-2453), so it must be per project.

**Every key above is valid in the local gsd-core 1.18.0**: `probe-keys.js` returned ok for
`granularity`, `granularities.execution`, `workflow.mvp_mode`, `dynamic_routing.tier_models.*`,
`dynamic_routing.provider_escalation`, `models.discuss`, `effort.*`,
`fast_mode.routing_tier_defaults.light`, `response_language`, `claude_md_path`, `intel.enabled`,
`graphify.enabled`, `graphify.auto_update`, `workflow.use_worktrees`, `git.branching_strategy`,
`git.base_branch`, `git.protected_branches`, `git.allow_default_branch_commits`, the UI flags and
`runtime`. No gsd-core change is needed for any wish.

## 3. Overlaps and contradictions with what the project already recorded

### Owner memories

- **Planner on opus** (`project_planner_opus_until_2026_10_22.md`: planner = opus, xhigh, no end
  date): the current v2 apply would unset both pins. The redesign must keep them. "balanced" already
  puts the planner on opus (CONFIGURATION.md:1648), so the override may become redundant but
  harmless. xhigh still needs a per-agent effort override.
- **GSD agent model and effort through gsd-tools** (`feedback_gsd_agent_model_effort_via_gsd_tools.md`):
  consistent with the skill (config-set plus effort sync). The memory adds a step the skill lacks:
  in a worktree session, also sync the launch directory's `.claude/agents`
  (`--config-dir <main>/.claude`). That matters because the owner wants a worktree per phase.
- **GSD project-local only** (`project_gsd_project_local_only.md`): matches "prefer local". It also
  says a new worktree has no install. With worktree-per-phase, every phase worktree needs a local
  install or `gsd_run`, which collides with "do not install GSD where it is not needed".
- **Scope, ai-kit versus tools-installer** (`project_ai_kit_scope_vs_tools_installer.md`):
  installing GSD itself belongs to tools-installer. "Check whether the local open-gsd is up to date"
  fits ai-kit as a report. Doing the update or install fits tools-installer, and the skill's existing
  installer follow-up already sits on that line.
- **Cross-AI runtimes run with full permissions** (`project_cross_ai_runtimes_full_permission.md`,
  2026-10-13: the skill should generate `cross-ai.mjs`, preference pi > cursor > opencode): this
  contradicts the new "avoid cross-AI execution" wish in emphasis. The runner can stay; the default
  answer changes. The handoff confirms the latest practice: Phase 27 ran on haiku with no cross-AI,
  at the owner's order.
- **Primary runtimes** (claude, opencode and pi primary): consistent with "prefer Claude, detect the
  current one". The open point is what "always Claude" means when the skill runs inside opencode or pi
  (see question 3).
- **jev at every decision point**: consistent with jev classifying agent tiers. Backlog 999.17
  adds a hard rule: jev is a black box. ai-kit text may only say "ask that skill, its answer is
  advisory, `needs_fallback` or no answer means the rule-based default decides". The tier
  classification must follow that rule and needs a rule-based fallback table.
- **Best over easy** (only `workflow.mvp_mode` favours simplicity): consistent with making MVP the
  first branch. It also argues for a real redesign, not another preset tweak.
- **Curated-config v1 untested, kept**: the memory says to decide v1's fate in this next milestone,
  with evidence. The redesign is that moment. v1 already holds two wished behaviours (AGENTS.md-first
  `claude_md_path`, UI flags from detection) that v2 lacks.
- **Ship each phase to the machine** (merge to local main after each phase): fits "a branch per
  phase, merged back". But this repo merges to `main` locally, while the wish names main/dev/sandbox
  as protected. The base-branch rule must tell "protected from direct commits" apart from "never
  merged into".

### Planning files

- **NEXT-MILESTONE-INPUTS.md, Theme 1**: "audit seven skills ... curated-config ... move
  provenance to a trailing section". Do it in the same rewrite, or the SKILL.md gets edited twice.
  The `Limits (as of 2026-10-23)` table and the dated phase references in SKILL.md are exactly that
  history.
- **Theme 6, re-baseline of skill-judge scores**: "the config skill reads 99 against 105 and stays
  unresolved". It is not certain this means curated-config (**unverified**), but if it does, a
  redesigned SKILL.md needs that base decided before its judge loop can pass.
- **Backlog 999.12 (runner and adapter cleanup)**: names curated-config's router rule and
  `plan_io.py` re-implementing gsd-core's skill resolution (`buildAgentSkillsBlock`). Same package;
  fold it in or sequence it.
- **Backlog 999.13 (register `workflow.cross_ai_retry`)**: only relevant if cross-AI execution
  stays a supported branch.
- **Backlog 999.16 (event-keyed playbook skill)**: its events include "new project" and "a new
  worktree is created", which overlap with the wished "new project, so ask" and worktree-per-phase
  setup.
- **Backlog 999.17 (lite or strong executor through jev)**: overlaps per-agent executor model
  choice, and imposes the black-box rule above.
- **Todo "unify the review and execute lane table, effort and escalation, jev classification"**:
  overlaps effort per tier and per agent, and jev classification. Its "spike on effort per runtime
  first" applies to the effort ladder here too.
- **Todo "make the session hooks dynamic"** (worktree indexing advice for codegraph and graphify):
  overlaps graphify auto update. GSD's `graphify.auto_update` is a GSD-owned PostToolUse hook
  rebuilding `.planning/graphs/`, while the owner's shell uses graphify's own `graphify-out/`.
  These are two different graph locations (see question 9).
- **STATE.md**: the milestone is closed and awaiting the next one. Its `milestone_name` still reads
  "GSD Curated Config v2", which is stale but harmless. Nothing in it contradicts the wishes.
- **Latest handoff** (`2026-11-02-123228-ai-kit-v13-closed-with-lessons.md`): Lesson 4 says cheap
  (haiku) executors work only with exact plans and explicit gates. That bears on which agents may go
  to haiku. Lesson 10 asks for plain words, which applies to the new question texts.
- **This repo's own `.planning/config.json`** already holds most of the wished values: balanced,
  `tier_models`, the planner on opus with xhigh, `claude_md_path ./AGENTS.md`. It also holds cross-AI
  execution on and `branching_strategy none`, which differ from the wishes. The current v2 would
  unset the tier models and the planner overrides on this very repo.

## 4. Open questions for the owner

1. **How do MVP and granularity map to the profile?** Is it MVP → coarse + `budget`, non-MVP →
   `balanced` with fine or standard? Or is it always `balanced`, with MVP changing only granularity
   and the cheaper agent overrides?
2. **What happens to the other rigor knobs?** Today "fine" comes bundled with TDD, ASVS 2, deep
   review, fallow and dynamic routing. Should fine versus standard change only granularity, or keep
   a bundle?
3. **"Always Claude" when the skill runs inside opencode or pi:** should it still write
   `runtime: claude`? Or follow the host, and only recommend Claude?
4. **Intel in MVP projects:** "intel.enabled = true" always, or only for non-MVP (today MVP turns
   it off)?
5. **Agent tiers from jev:** should jev classify once, with the result stored as a reviewed table
   in the skill, or classify on every run? The black-box rule and repeatable plans point to a stored
   table with jev as advisor.
6. **Existing per-agent pins:** should the redesign stop removing keys it did not plan (planner
   on opus, `tier_models`), or keep the "managed family" removals and carry those pins in its own
   defaults?
7. **Cross-AI review:** the wish says "avoid cross-AI execution". Does plan review through the
   referees stay on by default?
8. **Base branch:** when sandbox or dev exists, is the target the most recently updated of
   main/dev/sandbox, or a fixed order (sandbox > dev > main)? Should phase branches merge back into
   it, given the "ship each phase to local main" practice?
9. **Graphify:** GSD's own graph (`.planning/graphs/`, a GSD hook) or the owner's graphify CLI
   (`graphify-out/`)? Turning on GSD's version adds a second graph and a hook per tool call.
10. **GSD install and update:** should the skill only report "local 1.18.0, published 1.19.0" and
    point to tools-installer? Or offer the update as a follow-up, like the current opencode/codex
    installer step?
11. **"Projects that do not need GSD":** what tells the skill a project does not need GSD
    (no `.planning/`, an explicit answer)? Should the skill then stop, or still write config?
12. **The v1 path:** delete it in the redesign, or fold its two useful parts (AGENTS.md-first
    `claude_md_path`, UI flags) into the new flow and then delete it?
13. **Reading CONFIGURATION.md "always":** is a live fetch from GitHub acceptable on every run (a
    network call the skill does not make today)? Or is a pinned copy checked by a test enough, with
    the live key probe staying the authority?
