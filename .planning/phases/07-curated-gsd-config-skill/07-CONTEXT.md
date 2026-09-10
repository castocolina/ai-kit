# Phase 7: Curated GSD Config Skill - Context

**Gathered:** 2026-09-10
**Status:** Ready for planning

<domain>
## Phase Boundary

A new skill that asks a small, curated question set (not the full
`gsd-config`/`gsd-settings` interrogation) and writes/merges `.planning/config.json`
with preference-driven defaults: high effort where it matters, the cheapest viable
model for local last-resort execution, cross-AI review+execution enabled and
pointed at detected, preference-matched models/CLIs, and plan-review convergence
enabled. Scaffolded via `/superpowers:writing-skills`, reviewed via `/skill-judge`,
named via `/naming-analyzer`.

</domain>

<decisions>
## Implementation Decisions

### Write mechanism
- **D-01:** The skill writes config.json by calling gsd-tools' existing CLI
  (`config-set` per key, `config-new-project` for a fresh file) rather than
  hand-writing JSON. This reuses gsd-tools' own schema manifest/validator for
  free, satisfying both "same shape gsd-settings/gsd-config produce" and
  "validates against the schema when present" — there is no separate external
  JSON-Schema file; the manifest at `gsd-core/bin/shared/config-schema.manifest.json`
  (plus capability-contributed overlay keys) IS the live schema, verified present
  and enforced by `config-set` on the installed gsd-core v1.13.0. — **Reversibility:**
  costly — switching to hand-written JSON later means re-deriving and maintaining
  a duplicate of the manifest's validation logic.
- **D-02:** Model/CLI detection and preference-pattern matching (not caring which
  provider sits behind a router) reuses the existing `ai_kit_spec` pipeline
  (`skills/ai-kit-spec-review/ai_kit_spec/`: `detect-runtimes`, `fetch-model-catalog`,
  `model_ranker.py`, `model_matcher.py`, `resolve-reviewers`) instead of building new
  detection/ranking logic. — **Reversibility:** costly — this is a real dependency on
  another skill's internals; swapping it out later means re-plumbing the whole
  model-selection step.
- **D-03:** Concrete model/effort mapping locked for config.json, independent of
  whether the target project has ai-kit's own `ONESHOT-RULES.md` Rule-7
  circuit-breaker (that mechanism is ai-kit-specific infrastructure, not assumed
  to exist elsewhere):
  - `model_overrides.gsd-executor: "haiku"` — universal default. Whenever local
    `gsd-executor` ends up running at all (cross-ai unset, unreachable, or
    failed, for any reason), it must use the cheapest tier, never sonnet/opus.
  - `model_overrides.gsd-code-reviewer: "opus"` — code review is `standard` tier
    under `balanced` (→ sonnet by default); needs an explicit override to get Opus.
  - `gsd-planner` needs no override — already `heavy` tier → Opus + `xhigh` effort
    by the built-in tier ladder under `balanced`.
  - `review.effort.opencode: "high"` for plan-review-convergence — note this may be
    a no-op confirmation since `high` is every reviewer lane's declared default
    already.
  - `workflow.cross_ai_execution: true` and `workflow.cross_ai_command` point at a
    detected, preference-matched opencode/cursor model for EXECUTION delegation
    (preferred patterns: contains "coding"/"executor", composer 2.5+, grok 4.6+,
    deepseek-flash, luna — provider-agnostic, usually router-backed).
  - `workflow.plan_review_convergence: true`, reviewer selection for PLAN REVIEW
    prefers patterns: contains "plan-review", gpt-sol, glm-5.2/5.3 (more
    expensive), opus as last resort; preferred runtimes opencode and cursor.
- **D-04:** `workflow.cross_ai_command` is a literal command string — for
  opencode/cursor EXECUTION delegation, the skill builds that string with an
  explicit `--model`/effort flag baked in from the matched candidate. Plan-review
  convergence is different: its model resolves through `review.models.<slug>` /
  `review.reviewer_instances` (structured config keys), not a hand-built command
  string — the user already has a shim supplying a sane default model there when
  a reviewer CLI is invoked without one specified, so the skill's job for that
  path is pointing the right config keys at the right slug, not constructing an
  invocation string.
- **D-05 (landmine, observed regression):** `cross_ai_command` must never bake in
  a resolved absolute path for the executable (e.g. a venv/nvm/brew-resolved
  `/.../opencode`) — this has actually happened before in this or another
  project. Always write the bare command name (`opencode`, `cursor`), resolved
  via PATH at runtime. Same path-agnostic principle as Phase 6's rule 4.
- **D-06:** `claude_md_path` is resolved by a small detection helper inside the
  skill — it checks which instruction-file variant actually exists in the target
  repo (`AGENTS.md` / `CLAUDE.local.md` / `AGENTS.local.md` / `CLAUDE.md`) and
  prefers the AGENTS.md family for multi-CLI projects, rather than writing a
  fixed default. (ai-kit's own config.json currently has `claude_md_path:
  "./CLAUDE.md"` — updating it is left to the skill actually running on ai-kit
  later, not done as part of this discussion.)
- **D-07:** Workflow-flag defaults ("most flags on") use THIS project's own
  `.planning/config.json` as the reference baseline for what "on" looks like,
  falling back to gsd-core's own built-in defaults for anything not already
  covered there — not a flag-by-flag enumeration in the curated question set.
- **D-08:** Frontend detection (to decide `ui_phase`/`ui_review` activation) — left
  as Claude's discretion on implementation (README + package manifest framework-
  signal scan), no further user input needed.

### New vs. existing config
- **D-09:** Merge mode — the skill touches only the specific keys its curated
  defaults/questions cover (model_overrides, effort, cross_ai_*, review.*, the
  workflow flags it explicitly decided on, claude_md_path). Everything else in an
  existing `config.json` is left exactly as found. When no config exists yet,
  this degrades naturally to `config-new-project` followed by applying the
  curated keys on top. — **Reversibility:** reversible — a merge-mode write is a
  small, targeted diff; switching to full-regenerate later is a flow change, not
  a migration.

### Relationship to gsd-settings/gsd-config
- **D-10:** Coexist as a faster alternative entry point. `gsd-settings`/
  `gsd-config` remain for the deep cuts (power-user knobs via `--advanced`, API
  keys/integrations via `--integrations`) this curated skill intentionally
  skips — it does not replace or wrap them.

### Claude's Discretion
- Exact phrasing/order of the small curated question set (the todo's stated
  defaults — effort, execution model preference, cross-AI on, convergence on —
  are locked; how they're asked is open).
- Frontend-detection heuristic implementation details (D-08).
- Exact fallback behavior when `ai_kit_spec`'s detection pipeline finds no
  matching model for a stated preference pattern (e.g., no detected model
  contains "coding"/"executor") — reasonable graceful degradation, not a hard
  failure, consistent with SC3's "generation still succeeds without a hard
  failure" framing for the schema-validation case.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Source todo and requirements
- `.planning/todos/pending/2026-09-09-curated-gsd-config-skill-replacing-gsd-settings-prompts.md` — original problem/solution framing and preset defaults
- `.planning/REQUIREMENTS.md` §"v1.1 Requirements" — REQ-cfg-curated-questions, REQ-cfg-writes-config, REQ-cfg-schema-validate, REQ-cfg-skill-pipeline
- `.planning/ROADMAP.md` §"Phase 7: Curated GSD Config Skill" — goal and 4 success criteria
- `.planning/ONESHOT-RULES.md` §"Non-Negotiable Rules" #2 — the Rule-7 circuit-breaker pattern referenced in discussion (ai-kit-specific, NOT assumed present in other target projects; D-03 is written to hold without it)

### Schema and config infrastructure (verified live against installed gsd-core v1.13.0)
- `~/.claude/gsd-core/bin/shared/config-schema.manifest.json` — the live, authoritative
  key-path validator `config-set`/`config-new-project` enforce; confirmed to already
  contain `model_overrides.*`, `effort.*`, `dynamic_routing.*`, `review.reviewer_instances.*`,
  `model_policy.*` dynamic key patterns
- `~/.claude/gsd-core/bin/lib/config-schema.cjs` — composes capability-contributed
  schema overlays (e.g. `ui_phase`, `intel`, `graphify.*` are capability-provided, not
  in the frozen base manifest — confirmed by grepping the manifest directly)
- open-gsd `docs/CONFIGURATION.md` (fetched from `github.com/open-gsd/gsd-core` `next`
  branch, 2026-09-10) — sections consulted: Model Profiles / Per-Agent Overrides /
  Per-Phase-Type Models / Dynamic Routing / Effort Control (lines ~1529-2016),
  Reviewer lane effort/defaults/instances (lines ~302-490). Re-verify if stale per
  rule 14 — this is `next`-branch documentation, already confirmed schema-compatible
  with the installed v1.13.0 manifest, but re-check if the installed version bumps.

### Reused detection/selection pipeline
- `skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py`, `model_ranker.py`,
  `model_matcher.py`, `cli.py` (subcommands: `detect-tools`, `detect-current-runtime`,
  `detect-runtimes`, `fetch-model-catalog`, `resolve-reviewers`, `group-models`) — the
  existing CLI/model detection+ranking pipeline D-02 reuses.

### Skills this phase uses for scaffolding
- `~/.claude/skills/gsd-settings/SKILL.md`, `~/.claude/skills/gsd-config/SKILL.md` —
  the skills this one coexists alongside (D-10); their 5-question default flow plus
  `--advanced`/`--integrations` modes are what the curated skill intentionally does
  NOT replace.
- `~/.claude/skills/skill-judge/`, `~/.claude/skills/naming-analyzer/` — review gate
  and naming step this phase's new skill must pass, same as Phase 6.
- Pipeline entry point: `/superpowers:writing-skills`.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `gsd-tools.cjs` subcommands `config-set`, `config-new-project`, `config-get`,
  `config-ensure-section` — the write path D-01 locks in.
- `ai_kit_spec` CLI (`skills/ai-kit-spec-review/ai_kit_spec/cli.py`) — full
  detect/fetch/rank/resolve pipeline for CLIs and models, already built for
  exactly this kind of preference-driven selection (D-02).

### Established Patterns
- `.planning/config.json` (this project's own, already hand-tuned) — reference
  baseline for D-07's "most flags on."
- `.planning/ONESHOT-RULES.md` Rule 2/Rule 7 — the existing cross-AI
  primary/fallback/circuit-breaker pattern, referenced but explicitly NOT
  depended on by D-03 (ai-kit-specific, not general).

### Integration Points
- New skill writes through gsd-tools CLI commands (D-01), never touches
  `.planning/config.json` directly with a file write.

</code_context>

<specifics>
## Specific Ideas

- User's exact preference patterns, to inform `ai_kit_spec` matcher configuration:
  - Plan-review model preference order: anything matching `*plan-review*`,
    `gpt-*-sol`, `glm-5.2`/`glm-5.3` (more expensive), Opus as last resort.
    Preferred runtimes: opencode, cursor.
  - Execution model preference order: anything matching `*coding*`/`*executor*`
    (provider-agnostic, usually router-backed), `composer-2.5`-or-better,
    `grok-4.6`-or-better, `deepseek-flash`, `luna`, then Haiku.
- `claude_md_path` should resolve to whichever of `AGENTS.md` / `CLAUDE.local.md`
  / `AGENTS.local.md` / `CLAUDE.md` actually exists in the target repo, preferring
  the AGENTS.md family for multi-CLI projects — verified against ai-kit's own
  config (currently `./CLAUDE.md`, not yet updated).

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within Phase 7 scope. (Updating ai-kit's own
`claude_md_path` to an AGENTS.md-family value is explicitly NOT tracked as a
separate follow-up per the user's own call — it's implicit behavior once the
skill exists and runs on this project.)

</deferred>

---

*Phase: 7-Curated GSD Config Skill*
*Context gathered: 2026-09-10*
