# open-gsd configuration fact sheet: models, effort and workflow toggles

Researched 2026-11-02. Read-only. Nothing in the repo outside this folder was changed.

## Sources and version status

- Online, `next` branch (the default branch of open-gsd/gsd-core), fetched raw:
  `docs/CONFIGURATION.md` (2,523 lines), `docs/reference/agents.md` (909 lines),
  `docs/how-to/install-on-your-runtime.md`, `README.md`, and the shipped manifests
  `gsd-core/bin/shared/{model-catalog,config-schema.manifest,config-defaults.manifest}.json`.
  Both doc paths still exist at the given locations; nothing has moved.
- Local, project-local install: `.claude/gsd-core/` with `VERSION` = 1.18.0, install marker
  `.claude/gsd-core/.gsd-runtime` = `claude`. Read `references/model-profiles.md`,
  `references/planning-config.md`, `references/mvp-concepts.md`, `references/planner-mvp-mode.md`,
  `workflows/plan-phase.md`, `workflows/new-project.md`, `workflows/execute-phase*.md`,
  `workflows/review.md`, `agents/gsd-roadmapper.md`, `bin/shared/*.json`, `bin/lib/*.cjs`.
- Live checks: two probe scripts in this folder (`stack-probe.sh`, `stack-probe-2.sh`) ran the
  local `gsd-tools.cjs resolve-model` / `resolve-execution` / `resolve-granularity` against
  synthetic configs in throwaway temp directories. `agents-table.py` joins agents.md to the catalog.

**Is the local install out of date?** It is one minor release behind. GitHub releases list
v1.19.0 (2026-10-26) as the latest, and `package.json` on `next` reads 1.19.0. The local 1.18.0
release came out on 2026-10-19. For this topic the gap is tiny: the local
`model-catalog.json` is byte-for-byte equal to `next` once both are sorted. The only schema and
defaults difference is the new `git.repo_tagging` key (default `"single"`) on `next`. The local
install has no `docs/` folder. Its `references/` files are shorter, older copies of the same
material, and they differ from the online docs in a few places (listed under "Local versus online").

Note on version labels: the online docs tag sections "added in v1.40/v1.41/v1.42/v1.43". That is
the older numbering from before the fork. The current line is 1.x (1.18/1.19), so do not read those
labels as "newer than 1.19".

---

## 1. `model_profile`, `mvp_mode` and `granularity`

### `model_profile`
- Key exists. Default is `balanced` (CONFIGURATION.md, Core Settings; local `config-defaults.manifest.json`).
- Values: `quality`, `balanced`, `budget`, `adaptive`, `inherit`. Doc line: "Model tier for each agent".
- Profile Philosophy (CONFIGURATION.md, Model Profiles):
  - `quality`: "Opus for all decision-making, Sonnet for verification"
  - `balanced`: "Opus for planning only, Sonnet for everything else" (the default)
  - `budget`: "Sonnet for code-writing, Haiku for research/verification"
  - `inherit`: "All agents use current session model". Use it for non-Anthropic providers.
  - `adaptive` is not in that online table. The local `model-profiles.md` describes it as
    "Opus for planning and debugging, Sonnet for execution, research, and verification, Haiku for
    mapping, checking, and auditing".
- Implementation fact (catalog): `adaptive` is not a hand-written column. It is
  `adaptiveTierMap = {heavy: opus, standard: sonnet, light: haiku}` applied to each agent's
  routing tier. So `adaptive` equals "model by routing tier". The catalog calls `quality`
  `golden` internally.
- The profile picks a tier alias (opus/sonnet/haiku). The runtime then maps that alias to a real
  model. On Claude the alias is passed through. Other runtimes use the built-in tier maps (codex,
  opencode, qwen, ...), `model_profile_overrides.<runtime>.<tier>` and `model_policy`. See the
  Runtime-Aware Profiles and Model Policy Presets sections of CONFIGURATION.md.

### `granularity`
- Key exists at the top level. Default is `standard`. Values are `coarse`, `standard`, `fine`.
  CONFIGURATION.md Core Settings: "Controls phase count: `coarse` (2-4), `standard` (4-6), `fine` (6-10)".
- Per-phase-type override: `granularities.<planning|discuss|research|execution|verification|completion>`.
  Precedence: "`granularities[phaseType]` → `granularity` (global) → `planning.granularity` →
  `'standard'`". The `/gsd-plan-phase --granularity` flag beats all of these (local `plan-phase.md`).
- It is used in two places:
  - The roadmapper reads it as phase-count "compression guidance": Coarse 2-4 "Combine
    aggressively, critical path only"; Standard 4-6; Fine 6-10 "Let natural boundaries stand"
    (`agents/gsd-roadmapper.md`, Granularity Calibration).
  - The planner reads it as plans per phase: Coarse 1-3, Standard 3-5, Fine 5-10, with 2-3 tasks
    per plan in every case (`references/planner-guidance.md`).
  - Both say: "Granularity determines compression tolerance, not a target."
- Inconsistency: the `/gsd-new-project` question gives different numbers: "Coarse 3-5 phases,
  1-3 plans each / Standard 5-8, 3-5 / Fine 8-12, 5-10" (`workflows/new-project.md`).

### `workflow.mvp_mode`
- Key exists. Default `false`. CONFIGURATION.md, Workflow Toggles: "Persist the MVP-mode flag in
  config so every phase defaults to MVP framing without requiring `--mvp` on the CLI. Resolved via
  the precedence chain: `--mvp` CLI flag → ROADMAP.md `**Mode:** mvp` field → this config value →
  `false`. When `true`, the planner, executor, verifier, and discovery surfaces treat the phase as
  an MVP vertical slice (UI → API → DB) of one user-visible capability instead of a horizontal layer."
- MVP is per phase, not per project. `/gsd-new-project` asks "Vertical MVP vs Horizontal Layers"
  and, for MVP, writes `**Mode:** mvp` under every phase in ROADMAP.md. In auto mode it forces
  `PROJECT_MODE=mvp` without asking (`workflows/new-project.md`). Per-phase changes go through
  `/gsd-mvp-phase`.
- Effects: user-story phase goals, a Walking Skeleton plan plus `SKELETON.md` on Phase 1 of a new
  project, and MVP-framed UAT. TDD is a separate setting: "`TDD_MODE` is independent of
  `MVP_MODE`" (`references/mvp-concepts.md`).
- Vertical slicing is already the default without MVP. `references/planner-mvp-mode.md`: "the
  **default** tracer-first decomposition: every phase LEADS with one thin end-to-end
  `type="tracer"` slice ... `--no-tracer` restores standard horizontal-layer planning. The MVP
  enrichment ... appl[ies] *on top*".

### Are they tied together?
- **Not in code.** `resolve-granularity planning` returned `standard` with `{"workflow":{"mvp_mode":true}}`
  and `fine` with `{"granularity":"fine","workflow":{"mvp_mode":true}}`. MVP mode does not change
  granularity. No doc or workflow mentions MVP together with granularity.
- **Not tied to the model profile either.** The only place they appear together is a doc example,
  CONFIGURATION.md "Common Setting Combinations": Prototyping = `yolo` + `coarse` + `budget` with
  research/plan_check/verifier off; Normal = `interactive` + `standard` + `balanced`; Production
  release = `interactive` + `fine` + `quality`. That table is advice. Nothing enforces it.

---

## 2. Tiers, per-agent overrides and effort: exact keys

There are two tier vocabularies, and they are easy to confuse:
- **Model tiers** `opus` / `sonnet` / `haiku`. They are used by `model_profile`, `models.*`,
  `model_overrides`, `model_profile_overrides.<runtime>.<tier>` and `model_policy.runtime_tiers.<runtime>.<tier>`.
- **Routing tiers** `light` / `standard` / `heavy`. Every agent has one in the catalog
  (`routingTier`). They are used by `dynamic_routing.tier_models.*`, `effort.routing_tier_defaults.*`,
  `fast_mode.routing_tier_defaults.*` and the `adaptive` profile.

Exact keys (local `config-schema.manifest.json` dynamic patterns, identical on `next`):

| Purpose | Key | Default |
|---|---|---|
| Model per routing tier | `dynamic_routing.tier_models.<light\|standard\|heavy>` | none |
| Switch for the above | `dynamic_routing.enabled` | `false` |
| Escalation | `dynamic_routing.escalate_on_failure` (`true`), `dynamic_routing.max_escalations` (`1`), `dynamic_routing.provider_escalation` (string[]) | |
| Model per phase type | `models.<planning\|discuss\|research\|execution\|verification\|completion>` | none |
| Model per agent | `model_overrides.<agent-id>` | none |
| Tier alias to model, per runtime | `model_profile_overrides.<runtime>.<opus\|sonnet\|haiku>` (string or `{model, reasoning_effort}`) | none |
| Provider presets | `model_policy.provider/.budget/.high/.medium/.low`, `model_policy.runtime_tiers.<runtime>.<opus\|sonnet\|haiku>` | none |
| Effort, global | `effort.default` | `high` |
| Effort per routing tier | `effort.routing_tier_defaults.<light\|standard\|heavy>` | `low` / `high` / `xhigh` |
| Effort per agent | `effort.agent_overrides.<agent-id>` | none |
| Fast mode | `fast_mode.enabled`, `fast_mode.routing_tier_defaults.*` (light `true`), `fast_mode.agent_overrides.*` | `false` |
| Reviewer CLI effort | `review.effort.<claude\|codex\|opencode>` | lane default `high` |

- **`dynamic_routing.tier_models`** is documented as "enum `opus`, `sonnet`, `haiku` ... Tier
  alias". In practice the local resolver **accepted and returned a full ID**:
  `tier_models.heavy = "anthropic/claude-opus-4-8"` resolved `gsd-planner` to
  `anthropic/claude-opus-4-8`, and `config-set` accepted it. That behavior is undocumented, so do
  not rely on it.
- **`models.<phase_type>`** is tier-only ("intentionally tier-only"). A full ID there was **silently
  ignored**: `models.execution = "openai/gpt-5"` left `gsd-executor` on the profile tier, even
  though `config-set` accepted the value.
- **Agent-to-tier mapping.** The online table under "Agent default tiers" lists 33 agents:
  - light (11): codebase-mapper, doc-classifier, doc-verifier, integration-checker,
    intel-updater, nyquist-auditor, pattern-mapper, plan-checker, research-synthesizer,
    ui-auditor, ui-checker
  - standard (13): advisor-researcher, ai-researcher, code-fixer, code-reviewer,
    doc-synthesizer, doc-writer, domain-researcher, eval-auditor, executor, phase-researcher,
    project-researcher, ui-researcher, verifier
  - heavy (9): assumptions-analyzer, debug-session-manager, debugger, eval-planner,
    framework-selector, planner, roadmapper, security-auditor, user-profiler

  The catalog has 35 agents. The two the table leaves out, `gsd-dom-verifier` and
  `gsd-mempalace-curator`, are both light. The full per-agent list is in section 4.
- **Per-agent model override:** use `model_overrides`. Valid values are "`opus`, `sonnet`,
  `haiku`, `fable`, `inherit`, or any fully-qualified model ID". On Codex and OpenCode the model
  is baked in at install time, so "running `gsd install <runtime>` after editing
  `model_overrides` is required".
- **Effort precedence** (CONFIGURATION.md, Effort Control), highest first: invocation `--effort` →
  `effort.agent_overrides[agent]` → `effort.routing_tier_defaults[tier]` ("merged per-tier over
  the built-in tier defaults") → `effort.default` → `"high"`. Valid values: `minimal`, `low`,
  `medium`, `high`, `xhigh`, `max`, `inherit`.
  - The ladder is a single shared one: `minimal < low < medium < high < xhigh < max`. It is
    rendered per runtime: Claude frontmatter `effort`, Codex `model_reasoning_effort`, OpenCode
    `variant`.
  - Effort is set at install time. The local `model-profiles.md` says "An effort config change
    has no effect until `gsd_run effort sync --apply` re-syncs the agent files" (on Claude:
    `.claude/agents/gsd-*.md` frontmatter).
  - Model, by contrast, resolves per spawn: "`model` and `effort` resolve through different
    mechanisms at different times — they do not share the ladder".
  - Effort is keyed to the **routing tier**, never to the model tier. Its default does not change
    when the model changes.
- **Global defaults quirk** (CONFIGURATION.md, Global Defaults): in a real project, model-side keys
  in `~/.gsd/defaults.json` (`model_profile`, `model_overrides`, `models`, `dynamic_routing`,
  `runtime`, ...) are **inert**. "`effort` is the exception": the global `effort` block is merged.
  The `git.*` keys never resolve from the global file.

**Live stacking check** (local 1.18.0, `resolve-execution`):
- `budget` profile + `dynamic_routing` (light=sonnet, standard=opus, heavy=opus) +
  `model_overrides.gsd-executor = haiku` + `effort.routing_tier_defaults.standard = medium` +
  `effort.agent_overrides.gsd-planner = max` gave:

| Agent | Model | Effort |
|---|---|---|
| planner | opus | max |
| executor | haiku | medium |
| codebase-mapper | sonnet | low |
| roadmapper | opus | xhigh |

- Every layer was honored.
- With `dynamic_routing` on, `models.planning = haiku` did **not** apply to the planner (it got
  opus). Dynamic routing outranks `models`.

---

## 3. "Per-Phase-Type Models" and "Resolution precedence" (CONFIGURATION.md, Model Profiles)

**Per-Phase-Type Models (`models`).** This lets you tune by phase type instead of naming agents:
"Opus for planning and execution, Sonnet for the rest" in two lines. There are six slots.

Phase type to agents, as documented:
- planning: planner, roadmapper, pattern-mapper
- discuss: assumptions-analyzer
- research: phase-researcher, project-researcher, research-synthesizer, codebase-mapper,
  ui-researcher
- execution: executor, debugger, doc-writer
- verification: verifier, plan-checker, integration-checker, nyquist-auditor, ui-checker,
  ui-auditor, doc-verifier, code-reviewer
- completion: "reserved — no subagent today"

The docs say "`discuss` and `completion` are ... a no-op until a subagent maps to them". Two
corrections from the live check:
- `discuss` does map: the catalog gives `gsd-assumptions-analyzer` phaseType `discuss`, and the
  doc table itself lists it.
- The real mapping is the catalog's `phaseType` on **all 35 agents**, which is wider than the doc
  table. `models.verification = opus` also moved `gsd-security-auditor` and `gsd-dom-verifier`
  to opus, and the AI and doc agents have phase types too (see section 4).

Accepted values are tier aliases plus `inherit` only. "If you need a fully-qualified model ID ...
use `model_overrides` per agent instead."

**Resolution precedence (highest → lowest).** The docs give it twice (once under Per-Phase-Type
Models and once under Dynamic Routing), with the same content:
1. `model_overrides[<agent>]`: "per-agent; full IDs; targeted exception"
2. `dynamic_routing.tier_models[<tier>]`: "when enabled"
3. `models[<phase_type>]`: "coarse phase-level tier"
4. `model_profile` (per-agent column): "global tier strategy"
5. Runtime default

"The five layers compose top-down ... Mix freely — the precedence rule above resolves any overlap
deterministically."

Two other precedence lists apply after the tier is chosen. Both put `model_overrides` first.
- Runtime-aware: `model_overrides` → runtime tier map plus `model_profile_overrides` →
  `resolve_model_ids: "omit"` → Claude alias → `inherit`.
- `model_policy`: `model_overrides` → `model_policy.runtime_tiers` → flat high/medium/low →
  `model_profile_overrides` → catalog default → profile alias.

The local `model-profiles.md` explains how they fit: "Steps 2–4 select the *tier*; a
`model_profile_overrides.<runtime>.<tier>` entry then maps that tier to a concrete model."

---

## 4. `docs/reference/agents.md`: every agent

agents.md says "22 primary agents plus ... 13 advanced/specialized agents (35 shipped agents total)".
agents.md documents only "Model (balanced)" for each agent. It has **no tier field**. The routing
tier and phase type below come from `model-catalog.json` (the same on `next` and on local 1.18.0).

Format: agent — role (agents.md) — balanced model — phase type / routing tier.

- project-researcher — researches the domain ecosystem before the roadmap — Sonnet — research / standard
- phase-researcher — researches how to implement a phase before planning — Sonnet — research / standard
- ui-researcher — produces UI design contracts for frontend phases — Sonnet — research / standard
- assumptions-analyzer — analyzes the codebase for a phase and returns assumptions with evidence (discuss_mode=assumptions) — Sonnet — discuss / heavy
- advisor-researcher — researches one gray-area decision in discuss advisor mode — Sonnet — research / standard
- research-synthesizer — combines parallel researcher outputs — Sonnet — research / light
- planner — creates executable phase plans — **Opus** — planning / heavy
- roadmapper — creates roadmaps with phase breakdown — Sonnet — planning / heavy
- executor — executes plans with atomic commits — Sonnet — execution / standard
- plan-checker — verifies plans will achieve phase goals (max 3 iterations) — Sonnet — verification / light
- integration-checker — verifies cross-phase integration and E2E flows — Sonnet — verification / light
- ui-checker — validates UI-SPEC.md contracts — Sonnet — verification / light
- verifier — verifies phase goal achievement, goal-backward — Sonnet — verification / standard
- dom-verifier — checks wave UI criteria in a live DOM; additive, never blocks — Sonnet — verification / light
- nyquist-auditor — fills validation gaps by generating tests — Sonnet — verification / light
- ui-auditor — retroactive 6-pillar visual audit — Sonnet — verification / light
- security-auditor — verifies threat mitigations exist in code — Sonnet — verification / heavy
- codebase-mapper — explores the codebase and writes analysis docs — **Haiku** — research / light
- debugger — investigates bugs with persistent state — Sonnet — execution / heavy
- user-profiler — scores a developer profile from session messages — Sonnet — research / heavy
- doc-writer — writes and updates project docs — Sonnet — execution / standard
- doc-verifier — verifies doc claims against the codebase — Sonnet — verification / light
- pattern-mapper — maps new files to existing analogs (PATTERNS.md) — Sonnet — planning / light
- debug-session-manager — runs the /gsd-debug loop in an isolated context — Sonnet — execution / heavy
- code-reviewer — reviews source for bugs and security; writes REVIEW.md — Sonnet — verification / standard
- code-fixer — applies REVIEW.md fixes with atomic commits — Sonnet — execution / standard
- ai-researcher — distills AI framework docs into AI-SPEC guidance — Sonnet — research / standard
- domain-researcher — domain and evaluation context for AI systems — Sonnet — research / standard
- eval-planner — designs the AI eval strategy (AI-SPEC sections 5-7) — Sonnet per doc, **Opus per catalog** — planning / heavy
- eval-auditor — retroactive AI eval coverage audit — Sonnet — verification / standard
- framework-selector — interviews the user and ranks AI frameworks — Sonnet — planning / heavy
- intel-updater — writes the `.planning/intel/` knowledge base — Sonnet — research / light
- doc-classifier — classifies one planning doc (ADR/PRD/SPEC/DOC) — **Haiku** — research / light
- doc-synthesizer — merges classified docs, flags conflicts — Sonnet — research / standard
- mempalace-curator — ship-time MemPalace curation — Sonnet — research / light

Of the 35 agents, the doc and the catalog disagree on one: `gsd-eval-planner`, whose balanced model
is Sonnet in the doc and opus in the catalog. The resolver follows the catalog.

---

## 5. Other toggles

**UI phase and UI review.** All defaults are `true`. The keys are owned by the `ui` capability in
`bin/lib/capability-registry.cjs` rather than the central schema, but they are valid.
- `workflow.ui_phase`: "Generate UI design contracts for frontend phases". It runs the
  `ui-phase` step at `plan:pre`.
- `workflow.ui_safety_gate`: "Prompt to run /gsd-ui-phase for frontend phases during plan-phase".
  It is a **blocking** gate at `plan:pre` and `execute:wave:post` (`onError: halt`).
- `workflow.ui_review`: "Run visual quality audit (`/gsd-ui-review`) after phase execution in
  autonomous mode". It is a `verify:post` step.
- `workflow.ui_interaction_capture` (default `false`) and `workflow.live_dom_uat` (default `false`)
  are opt-in extras.
- **How "frontend" is detected.** `check ui-plan-gate` matches the ROADMAP phase section against
  `UI, interface, frontend, component, layout, page, screen, view, form, dashboard, widget`
  (`bin/lib/ui-safety-gate.cjs`, whole words, case-insensitive). It also looks for static frontend
  evidence such as react or vue in the manifest (`ui-frontend-evidence.cjs`).
- Without frontend indicators the gate "Skip[s] silently". With indicators and no UI-SPEC:
  - In auto or pipeline mode, it runs `/gsd-ui-phase` automatically.
  - In manual mode, a blocking gate "EXIT[s] the plan-phase workflow".
  - `--skip-ui` bypasses it (`workflows/plan-phase.md` §5.6).

**`intel.enabled`.** Default `false`; it is a capability activation key. "When `true`,
`/gsd-map-codebase --query` commands build and query a JSON index in `.planning/intel/`"
(Feature Flags). `plan_review.source_grounding_authority: "intel"` requires it.

**Graphify** (CONFIGURATION.md, Graphify Settings):

| Key | Default | Notes |
|---|---|---|
| `graphify.enabled` | `false` | The `/gsd-graphify` graph in `.planning/graphs/` |
| `graphify.build_timeout` | `300` | Seconds |
| `graphify.auto_update` | `false` | "Opt-in". It needs `graphify.enabled` too |
| `graphify.graph_path` | unset | Umbrella or multi-repo graph |

- What `auto_update` does: a PostToolUse hook `gsd-graphify-update.sh` rebuilds the graph in the
  background "after `git commit/merge/pull/rebase --continue/cherry-pick` on the default branch
  (`git.base_branch` override, else `main`/`master`/`trunk`)". It is CI-aware and does nothing if
  `graphify` is not on PATH.
- The planner and phase-researcher prefer the `graphify` CLI when it is on PATH: "There is **no
  config key for this**".

**`response_language`.** Default none (`null`). "Language for agent responses (e.g., `"pt"`,
`"ko"`, `"ja"`). Propagates to all spawned agents". Every workflow must honor it. One exception:
the spec-phase edge probe gets an English translation.

**`claude_md_path`.** Default `./.claude/CLAUDE.md`. "Custom output path for the generated CLAUDE.md
... keeps GSD-generated content from polluting a hand-crafted repo-root `CLAUDE.md`." A file without
GSD markers is never overwritten unless `--force`. The companion key is
`claude_md_assembly.mode` (`embed` or `link`).

**Git** (CONFIGURATION.md, Git Branching):
- `git.branching_strategy`: `none` (default), `phase` or `milestone`.
  - `phase`: branch at the start of execute-phase; "User merges after phase".
  - `milestone`: branch at the first execute-phase; merged at complete-milestone.
- `git.base_branch`: the online table says default `main`. The local manifest and
  `planning-config.md` say `null` ("auto-detects from `git symbolic-ref refs/remotes/origin/HEAD`,
  falling back to `"main"`"). These two disagree.
- Other git keys:
  - `git.protected_branches`
  - `git.allow_default_branch_commits` (`false`): the executor's pre-commit guard refuses commits
    on the default branch unless this is set
  - `git.create_tag` (`true`)
  - `git.repo_tagging` (new on `next`)
  - the `git.*_branch_template` keys
  - The whole `git.*` block is project-only and never read from global defaults.
- **No "worktree per phase" key exists.**
  - `workflow.use_worktrees` (default `true`) isolates **each executor within a wave**.
    Claude and Cursor do this through their own harness; GSD creates the worktrees for codex,
    opencode and kimi. Every other runtime runs sequentially.
  - `workflow.worktree_skip_hooks` (default `false`).
  - `worktree.baseRef` lives in `.claude/settings.local.json`, not in config.json; `"head"` keeps
    parallel waves working on a diverged branch.
  - Branch-per-phase comes from `branching_strategy: "phase"`, not from worktrees.

**Cross-AI execution:**
- Keys: `workflow.cross_ai_execution` (`false`), `workflow.cross_ai_command` (none; "Receives the
  phase prompt via stdin. Must produce SUMMARY.md-compatible output"), `workflow.cross_ai_timeout`
  (`300` s).
- **The config flag alone delegates nothing.** A plan is delegated only if its frontmatter has
  `cross_ai: true` **and** config `workflow.cross_ai_execution` is `true`. The other route is the
  `--cross-ai` flag, which forces every ready plan (`execute-phase/detail/elaboration.md` §2).
  `--no-cross-ai` turns it off for the run.
- **No up-front confirmation.** It warns on a dirty tree and runs the command under a timeout.
  It asks only on failure: "offer **retry** / **skip** (falls back to the normal executor) /
  **abort**".
- `manager.flags.execute: "--cross-ai"` can append the flag automatically.

**Cross-AI review:**
- Keys:
  - `review.default_reviewers` (null = all detected)
  - `review.reviewer_instances.<name>.{cli,model,agent}`
  - `review.models.<lane>`
  - `review.effort.<lane>`
  - `review.timeouts.<lane>`
  - `review.parallel_lanes` (`false`)
  - `review.max_prompt_tokens*`
  - `review.context_window_tokens.*`
- `workflow.plan_review_convergence` (default `false`) gates `/gsd-plan-review-convergence`.
  "A `/gsd-autonomous --converge` dispatch overrides this gate for its own run".
- Prompts:
  - Lanes over the prompt budget are refused, never trimmed.
  - The only explicit consent is **egress consent for HTTP lanes** (ollama, lm_studio,
    llama_cpp). If the configured host changes, the lane is blocked with `egress_host_changed`
    until you consent again.
  - Convergence asks the user ("Proceed anyway" / "Manual review") only when it hits max cycles
    with concerns left.
- **Gates:** `gates.execute_next_plan`, `gates.confirm_transition` and
  `gates.confirm_milestone_scope` (all `true`) "only appl[y] under `mode: "interactive"`";
  `yolo` auto-approves.

---

## 6. Runtime detection, and global versus project-local install

**Which runtime GSD reports** (local `bin/lib/host-runtime-detection.cjs`, `resolveReportedRuntime`).
It checks these in order:
1. `GSD_RUNTIME` env var
2. config `runtime` key
3. the install marker `.gsd-runtime` (here `claude`)
4. host sniffing, which only detects **Codex** (env `CODEX_SANDBOX` / `CODEX_SANDBOX_NETWORK_DISABLED`,
   or `CODEX_HOME` with a `config.toml`)
5. default `claude`

There is no opencode/pi env sniffing.

The docs (Core Settings, `runtime`) say detection "affects reporting and the agent-installation
check only; it never feeds tier resolution, which still reads this key alone". So for model
resolution, only the config `runtime` key (or `GSD_RUNTIME`) counts.

Other runtime facts:
- A non-Claude install writes `resolve_model_ids: "omit"` into `~/.gsd/defaults.json` and stamps
  the install marker.
- Built-in tier maps exist for: claude, codex, qwen, opencode, copilot, hermes, kilo, pi.
- Group B runtimes (cline, cursor, windsurf, augment, trae, codebuddy, antigravity) have "no
  built-in default".
- The executor isolation capability is per runtime (see Git above).

**Global versus local install:**
- README: "The installer prompts for your runtime ... and whether to install globally or
  locally."
- install-on-your-runtime.md: "install globally (all projects) or locally (this project only)".
  Its per-runtime examples all use `--global`, for example `npx @opengsd/gsd-core@latest --claude --global`.
- Installing both is "a supported configuration", but on Claude Code "the global skill always
  wins the `/gsd-<name>` trigger over the local command". `/gsd-health` reports this as `W028`.
- With a global skill, a project with its own `.claude/gsd-core/` still gets its own workflow
  specs, "it does not extend to the skill's `references/`/`templates/` includes".
- `--kimi --local` "is intentionally deferred".
- Changing `agent_tools`, `model_overrides` (Codex/OpenCode) or effort means re-running
  `gsd install <runtime>` or `effort sync`.

---

## Local 1.18.0 versus online `next`: differences found

- Version: 1.18.0 locally against 1.19.0 on `next`. The only schema difference is `git.repo_tagging`.
- Local `references/model-profiles.md`:
  - Its `adaptive` column says `gsd-roadmapper` = sonnet. The catalog and the online doc say
    opus, and the live resolver returned opus. The local doc is wrong.
  - Its tier table lists only 18 agents (light 9, standard 6, heavy 3). Online lists 33; the
    catalog has 35.
- The `git.base_branch` default is `main` online and `null` (auto-detect) locally. The code
  default is `null`.
- Online-only material that has no copy in the local references: the effort section, the
  `granularities`, `model_policy`, `fast_mode` and `review.effort` keys, and the
  agents.md 35-agent roster.

---

## Surprises against the owner's beliefs

1. **"model_profile + tier_models + per-agent override + effort per tier/agent all exist and
   stack."** They exist and they stack (confirmed live), with these catches:
   - `dynamic_routing.tier_models` is ignored unless `dynamic_routing.enabled: true`.
   - When enabled, it **outranks** `models.<phase>` and the profile for every agent. It also
     turns on failure escalation (`escalate_on_failure` defaults to `true`).
   - Its slots are keyed `light/standard/heavy`, not `opus/sonnet/haiku`. They are documented as
     tier aliases only, though a full ID worked live (undocumented).
   - `models.<phase>` silently drops full IDs.
   - Effort follows the routing tier, not the chosen model. It is baked at install time and needs
     `effort sync --apply`, while model changes apply on the next spawn.
   - A global `~/.gsd/defaults.json` cannot set model keys for a real project. Only `effort`
     carries over.
   - The doc's phase-type table understates reach: the catalog gives every one of the 35 agents a
     phase type.
2. **"MVP should mean coarse granularity."** Nothing in GSD ties them together.
   - `mvp_mode` is a per-phase planning mode (vertical slice, user story, walking skeleton).
     `granularity` is phase and plan count. `resolve-granularity` ignores `mvp_mode`.
   - The only pairing of `coarse` is the advisory "Prototyping" row (`yolo` + `coarse` +
     `budget` + research/check/verifier off).
   - `/gsd-new-project` in auto mode already forces MVP on every phase, whatever the granularity.
3. **"Non-MVP picks fine or standard."** This is not documented either. Granularity defaults to
   `standard` regardless of mode, and the docs pair `fine` with "Production release" + `quality`.
   Non-MVP planning is still tracer-first vertical slicing by default; only `--no-tracer` gives
   horizontal layers. The new-project question and the roadmapper also disagree on what each
   granularity means (3-5/5-8/8-12 against 2-4/4-6/6-10 phases).
4. **"UI phase/review only matter for UI projects."** Mostly true, with these catches:
   - All three toggles default to `true`.
   - The trigger is a keyword match on each phase's ROADMAP text. It includes common non-UI words
     (`interface`, `view`, `form`, `page`, `layout`, `component`), so a CLI or library phase can
     trip it.
   - In manual mode `ui_safety_gate` then **blocks** planning until a UI-SPEC exists or you pass
     `--skip-ui`. In auto mode it spawns `/gsd-ui-phase`.
   - Setting `ui_safety_gate: false` keeps auto-generation but drops the block. Setting
     `ui_phase` and `ui_review` to `false` is the clean opt-out for a non-UI project.

Skipped: I did not read the online FEATURES.md, the how-to/configure-model-profiles.md or
INVENTORY.md, and I did not live-test `model_policy`, `fast_mode` or the non-Claude tier maps.
