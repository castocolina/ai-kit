# ai-kit-gsd-curated-config v2 — host-aware, role-scored GSD config wizard

Date: 2026-09-23
Status: draft, awaiting user review
Supersedes: Phase 07 decisions D-03 (haiku executor floor + opus/high heavy sweep), D-07 (fixed
workflow bundle copied from this repo), and the "never more than one question" rule. D-01
(writes only via `gsd-tools config-set`/`config-new-project`), D-05 (bare command name in
`cross_ai_command`), D-09 (merge mode) and D-10 (coexist with `gsd-settings`/`gsd-config`) stay.

## 1. Intent

Configure a target project's `.planning/config.json` for open-gsd so that every GSD agent runs on
the model that best fits its role *on the runtime hosting the session*, with rigor-appropriate
gates, effort, cross-AI review/execution and per-agent skills — in four questions plus one
review-and-adjust pass, instead of the full `gsd-settings`/`gsd-config` interrogation.

Success criteria:
- Host runtime detected correctly for pi, opencode, cursor, claude, codex (preference order when
  several signals are set: pi > opencode > cursor > claude > codex).
- The gsd-core read is the one installed for the detected host (versions differ per host today:
  claude 1.14.0, opencode/codex 1.13.0, cursor 1.12.0).
- After `apply`, `gsd-tools resolve-model <agent>` in the target project returns, for every agent,
  the model the plan promised (end-to-end proof, see §8).
- Config is minimal: tier choice via profile / `models.<phase_type>`, tier→model via
  `model_profile_overrides.<host>.<tier>`, and at most 7 `model_overrides` (the specialist list
  in §4), usually fewer.
- Never corrupts an existing config: backup before apply, restore on failure.

Out of scope: portable multi-runtime configs (explicit decision: host only), API keys and
integrations (stay in `/gsd-config --integrations`), installing skills or CLIs without consent.

## 2. Research facts the design depends on

Verified against installed gsd-core 1.14.0 (`~/.claude/gsd-core`) and the `next` docs.

- `models.<phase_type>` accepts **tier aliases only** (`opus|sonnet|haiku|inherit`). Phase types:
  planning, discuss, research, execution, verification, completion. `verification` mixes
  plan-checker, code-reviewer, ui-auditor, security-auditor, etc.
- `model_profile_overrides.<runtime>.<opus|sonnet|haiku>` takes a model id or
  `{model, reasoning_effort}` (schema pattern confirmed). This is the tier→concrete-model layer.
- Resolution order (`model-resolver.cjs` `resolveModelInternal`): `model_overrides[agent]` →
  tier from `models[phase]` / profile → **`model_policy`** (step 2.5) → runtime tier map merged
  with `model_profile_overrides` (step 3) → omit → claude tier override → alias.
  ⇒ an existing `model_policy` shadows our `model_profile_overrides`; must be detected.
- `model_policy.budget` only selects columns of named-provider presets (stale: opus-4-8,
  gpt-5.6). With `provider: generic`, `high/medium/low` are tier slots, not budgets. Not used.
- `runtimeTierDefaults.cursor` is `null`: without `model_profile_overrides.cursor.*` a Cursor
  host falls back to Claude aliases. opencode bakes models into agent frontmatter at install
  time → `gsd install opencode` needed after changes.
- `dynamic_routing.{enabled, escalate_on_failure, max_escalations, tier_models.*}` escalates
  light→standard→heavy on failure; `model_overrides` still wins over it.
- Effort: `effort.default`, `effort.routing_tier_defaults.{light,standard,heavy}`,
  `effort.agent_overrides.<agent>`; applied with `gsd-tools effort sync --apply`.
- Cross-AI review lanes: claude, codex, coderabbit, opencode, qwen, cursor, agy, kimi-code,
  ollama, lm-studio, llama-cpp (+gemini in 1.14). **pi is not a lane.** `/gsd-review`
  self-skips the host lane (cursor, claude confirmed). Keys: `review.default_reviewers`,
  `review.models.<lane>`, `review.effort.<lane>`, `review.reviewer_instances.<name>`.
- Cross-AI execution delegates only plans with frontmatter `cross_ai: true` (or run with
  `--cross-ai`); one `workflow.cross_ai_command` for all.
- Per-agent models across providers: Cursor subagent `model:` takes any catalog id (Anthropic,
  OpenAI, xAI, Google, Moonshot, Zhipu; blocked models/legacy plans fall back); opencode agent
  `model:` any `provider/id`; pi via the subagent extension (one `pi --model` process per agent);
  Codex OpenAI-only; Claude Code Claude-only.
- Host env signals: `PI_CODING_AGENT`, `OPENCODE`, `CURSOR_AGENT`, `CLAUDECODE`,
  `CODEX_THREAD_ID`/`CODEX_SANDBOX` (codex signal source-inspected, not live-verified).
- `agent_skills.<agent>` accepts `path`, `global:<name>`, `global:<plugin>:<skill>` (Claude only).
  Injection bypasses the "skill never self-activates" problem (relevant for ponytail).
- `intel.enabled` (default false) builds `.planning/intel/`; `plan_review.source_grounding_authority:
  intel` requires it.

## 3. Architecture

```
inventory ──► recommend ──► plan.json ──► (agent shows, asks, adjusts via plan-set) ──► apply --dry-run ──► apply
```

CLI `ai-kit-gsd-curated-config.py`, subcommands replacing the current 11:

- `inventory --project-dir DIR [--refresh]` → JSON (read-only):
  `host`, `gsd_core {path, version, valid_keys}`, `host_models [{id, provider, scores, price,
  image_input, reasoning_levels}]`, `other_clis {cli: [models]}`, `skills [{name, form, source,
  description}]`, `project {frontend, db, claude_md_path, intel_index_present}`,
  `existing_config`, `conflicts [model_policy_present, runtime_mismatch, ...]`.
- `recommend --inventory inv.json --profile P --rigor R [--cross-ai-review y|n]
  [--cross-ai-exec y|n] --out plan.json` → pure function of its inputs. Every entry:
  `{key, value, why, source: preset|catalog-score|curated-affinity|user}`.
- `plan-set --plan plan.json KEY VALUE` / `plan-unset` → user adjustments (`source: user`).
- `apply --project-dir DIR --plan plan.json [--dry-run]` → validates every key against the host
  gsd-core's valid keys, backs up config, `ensure` (config-new-project), `config-set` each entry,
  prints diff, then prints (never runs silently) follow-ups: `gsd install <host>`,
  `effort sync --apply`, `/gsd-map-codebase` when intel is on without an index.

Modules (package `ai_kit_gsd_curated_config/`):
- `host.py` — host detection (delegates to `ai_kit_spec` `detect-current-runtime`) + host gsd-core
  resolution (host's own config dir first, then the existing candidate list).
- `gsd_catalog.py` — kept; adds `valid_keys` (schema manifest + capability-registry keys).
- `catalog_adapter.py` — reads `~/.cache/ai-kit/spec` catalog, refreshes via `ai_kit_spec`
  `detect-runtimes --if-stale` + `fetch-model-catalog --if-stale`; stale-but-present cache is used
  with a warning when refresh fails.
- `roles.py` — role profiles and scoring (§4).
- `presets.py` — rigor × profile tables (§5), data only.
- `cross_ai.py` — review lane + execution command selection (§6); reuses `ai_kit_spec`
  `build_execute_command` (kept from `cross_ai_build.py`).
- `skills.py` + `skill_affinity.json` — skill inventory and mapping (§7).
- `plan_io.py`, `recommend.py`, `apply.py`, `gsd_write.py` (kept, only module that shells out
  for writes), `cli.py`.
- Removed: `preference_match.py` name ladders, `critical_agents.py`, `workflow_defaults.py`.

### 3.1 Prerequisite work in `ai_kit_spec` (sub-project A)

Shared package in `skills/ai-kit-spec-review/ai_kit_spec/`, backward compatible:
- `detect_current_runtime`: add `pi` (`PI_CODING_AGENT`) and codex `CODEX_THREAD_ID`/
  `CODEX_SANDBOX`; order pi > opencode > cursor > claude > codex.
- `detect-runtimes`: enumerate pi (`pi --list-models`), codex (`codex debug models`), claude
  (static alias list: fable, opus, sonnet, haiku + full ids). Invoke real binaries, never shell
  functions/aliases (the user's `cursor-agent` and `claude` are wrapped).
- Catalog schema: optional `image_input: bool` (from models.dev modalities / `opencode models
  --verbose` / pi table), optional `reasoning_levels: list`.
- Ranker: add purposes `planning`, `general`, `mechanical`, `execution`, `review` via weights in
  the existing ranking-weights file (keep `review`/`execute` as aliases).

## 4. Model assignment (three layers + execution override)

Role profiles, scored from catalog fields (intelligence/coding/agentic index, price, image_input):
- **planning → slot `opus`**: max intelligence+agentic, price weight low.
- **general → slot `sonnet`**: researchers, verifier, debugger, doc-writer; score/price balance.
- **mechanical → slot `haiku`**: cheapest model above a minimum coding score; effort
  `minimal`/`low` via `effort.routing_tier_defaults.light`.
- **execution → `model_overrides.gsd-executor` + `gsd-code-fixer`**: coding+agentic, high price
  weight, effort `medium` via `effort.agent_overrides`. Separate from `sonnet` so researchers are
  not dragged to a coding-tuned model. Typical picks: Cursor `composer-2.5`; opencode/pi a
  DeepSeek/Kimi/`router-env/my-coding` class model; Codex `gpt-5.6-terra` (luna in MVP);
  Claude `haiku`/`sonnet` natively, or cross-AI execution (§6).

Layers written:
1. Role → tier: `model_profile` (+ `models.<phase_type>` only where the rigor preset shifts a
   whole phase).
2. Tier → model: `model_profile_overrides.<host>.{opus,sonnet,haiku}`. Claude host: native aliases
   (layer skipped unless user pins). Codex: OpenAI ids with `reasoning_effort`. Cursor: ids with
   effort suffix (`-high`) where the model has one.
3. Specialists `model_overrides.<agent>` (full host ids), only when the slot fails the rule:
   - `gsd-plan-checker`: provider ≠ planning-slot provider (counterpart).
   - `gsd-code-reviewer`: provider ≠ execution provider.
   - `gsd-ui-auditor`, `gsd-dom-verifier`: must have `image_input`.
   - `gsd-ui-researcher`: best frontend-capable model when the project has a frontend.
   - `gsd-executor`, `gsd-code-fixer`: execution role.

Price ceiling for slot filling comes from rigor (MVP low, Standard medium, Rigorous high).
Single-provider hosts (Claude, Codex, or a multi-provider host with one provider configured):
counterpart impossible in-runtime → plan says so explicitly and points to cross-AI review.
If no catalog is available at all: Claude/Codex use native tier maps; Cursor/opencode/pi ask the
user to pick per slot from the raw model list.

## 5. Presets (profile × rigor)

Profile (`quality|balanced|budget|adaptive`, recommended `adaptive`) = which tier each agent gets
(GSD native columns). Rigor = gates, effort, slot price ceiling, optional `models.*`.

**MVP (fast)**: `granularity: coarse`, `workflow.mvp_mode: true`; `models.research: haiku`,
`models.verification: haiku` (specialist overrides still apply); effort heavy `high` / standard
`medium` / light `minimal`, executor `medium`; research/plan_check/verifier/pattern_mapper on;
nyquist off, `tdd_mode: false`, `code_review_depth: quick`, `security_asvs_level: 1`,
`security_block_on: critical`, `ui_phase` = frontend, `ui_review: false`, `intel.enabled: false`,
`plan_review_convergence: false`, fallow off. Recommend cross-AI review **no**, execution **yes**
on Claude/Codex when a cheap candidate exists.

**Standard**: `granularity: standard`, no `models.*`; effort GSD defaults (heavy `xhigh`, standard
`high`, light `low`), executor `medium`; nyquist on, `code_review_depth: standard`, ASVS 1 /
block_on `high`, `ui_review` = frontend, **`intel.enabled: true`**, in-runtime counterpart
plan-checker. Recommend convergence **yes** on Claude/Codex when another CLI exists, optional
elsewhere.

**Rigorous**: `granularity: fine`, `models.planning: opus`, `models.verification: sonnet`; effort
heavy `xhigh`, standard `high`, light `low`, code-reviewer `xhigh`, executor `medium`/`high`;
`tdd_mode: true`, `plan_review_convergence: true`, `code_review_depth: deep`, ASVS 2 / block_on
`medium`, `ui_review: true` + `live_dom_uat` when frontend and a browser MCP exist,
**`intel.enabled: true`** + `plan_review.source_grounding_authority: intel` when the index exists,
`code_quality.fallow.enabled: true` (`standard`), `refactor.trigger_enabled: true`,
**`dynamic_routing.enabled: true`** with `escalate_on_failure: true`, `max_escalations: 1`.
Recommend cross-AI review **yes**.

Keys unknown to the host's gsd-core version are dropped from the plan with a note (e.g. cursor
1.12 may lack newer keys).

## 6. Cross-AI

Review (question: "use cross-AI plan-review convergence?", default from rigor):
- In-runtime layer (opencode/cursor/pi): counterpart `gsd-plan-checker` override (§4), always
  when ≥2 providers exist.
- Cross-AI layer: `workflow.plan_review_convergence: true`, `review.default_reviewers: [lane]`,
  `review.models.<lane>`, `review.effort.<lane>` (`high`; `xhigh` in Rigorous). Lane choice:
  lane ≠ host (GSD self-skips it anyway; pi has no lane), reviewer model provider ≠ planning-slot
  provider, then best `review` score. From Claude/Codex this is the only source of a different
  provider.
- Whether the opencode lane can be used from an opencode host (no documented self-skip) is
  verified during implementation; until then it is not recommended.

Execution (question: "delegate plan execution to another CLI?", recommended on Claude/Codex):
- `workflow.cross_ai_execution: true`, `workflow.cross_ai_command` built by `ai_kit_spec`
  `build_execute_command` with the bare CLI name (D-05), `workflow.cross_ai_timeout` 300 (MVP) /
  600 (Standard, Rigorous). Candidate = best `execution` score among other CLIs' models
  (composer via cursor-agent, DeepSeek/Kimi via opencode, ...).
- Plans only go cross-AI with `cross_ai: true` frontmatter or `--cross-ai`; the report tells the
  user to run `/gsd-execute-phase N --cross-ai` (and sets `manager.flags.execute: "--cross-ai"`).
- On opencode/cursor/pi the question defaults to **no**: the executor override already runs a
  cheap execution model in-runtime.
- Mechanical agents cannot be delegated cross-AI on Claude/Codex; they stay on haiku/luna.

## 7. Skills per agent

- Inventory: host skill dirs (`~/.claude/skills`, `~/.agents/skills`, opencode/cursor/pi skill
  dirs, project `skills/`), plus Claude plugin skills (only addressable on the Claude host).
- `skill_affinity.json` (dated, editable) maps skill families → agents, gated by project facts:
  - token economy (ponytail, reducing-entropy) → planner, executor, code-fixer;
  - `test-driven-development` → executor, only when `tdd_mode`;
  - security-review → security-auditor, code-reviewer;
  - frontend (react-dev, mui, frontend-design, design-system-starter) → ui-researcher, executor,
    ui-auditor, only when frontend;
  - docs (crafting-effective-readmes, mermaid-diagrams, c4-architecture,
    writing-clearly-and-concisely) → doc-writer;
  - database-schema-designer → planner, only when a DB is detected;
  - systematic-debugging → debugger.
- Unknown skills: SKILL.md instructs the host agent to propose mappings from descriptions; the user
  confirms. Max 3 skills per agent.
- A recommended-but-missing skill (e.g. ponytail) is explained (purpose, measured effect,
  alternatives) and offered for install; never installed without consent.
- Skills behind symlinks escaping the global root get a proposed
  `agent_skills_security.trusted_global_roots` entry, shown for approval.

## 8. Error handling

- No gsd-core for the host → exit 2 with the searched paths (unchanged behavior).
- Catalog refresh fails → stale cache + warning; no cache → §4 fallback.
- `model_policy` present (project or `~/.gsd/defaults.json`) → conflict listed; plan proposes
  removing it from the project config (it would shadow `model_profile_overrides`).
- `runtime` already set to another host → offer migration (rewrite host-specific keys).
- `apply`: dry-run validates all keys first; real run copies `config.json` to
  `.planning/config.json.bak-<timestamp>` and restores it if any `config-set` fails, reporting the
  failing key.
- Follow-up commands (`gsd install`, `effort sync --apply`) are printed and run only after the
  user approves.

## 9. Testing and evaluation

- Unit: `recommend` golden tests from synthetic inventories for 5 hosts × 3 rigor × adaptive
  (+ spot checks for quality/budget); role scoring; counterpart rule; vision rule; single-provider
  warning; unknown-key dropping; skill affinity gating.
- `ai_kit_spec` additions: detection env matrix, pi/codex/claude enumeration parsers (fixtures
  from the real CLI output captured in this session), `image_input` extraction.
- Integration: `apply` against a temp project using the real installed `gsd-tools` (skipped when
  absent), then `gsd-tools resolve-model <agent>` for all 35 agents with `GSD_RUNTIME=<host>` must
  match the plan; backup/restore on an injected failure.
- Skill eval: `superpowers:writing-skills` RED/GREEN pressure scenarios (baseline subagent without
  the skill vs. with it) for: Cursor host MVP, Claude host Rigorous with cross-AI, pi host with a
  missing ponytail skill; then `/skill-judge` on SKILL.md (part of code review, per project rule).
- Live smoke: `inventory` + `recommend` + `apply --dry-run` run from opencode, cursor-agent, pi,
  codex and claude on a scratch project; record results in the phase summary.
- `make validate` registration unchanged (tests module + py_compile globs already cover the
  package); README row updated.
