# Roadmap: ai-kit

## Milestones

- ✅ **v1.0 Multi-CLI Foundation & Config Safety** — Phases 1.1–5 (shipped 2026-09-10)
- ✅ **v1.1 Agent Workflow Hygiene & Tooling Polish** — Phases 6–8.1 (shipped 2026-09-13)
- ✅ **v1.2 ai-kit Rules Skill Family** — Phases 9–15.2 (shipped 2026-09-23)
- 🚧 **v1.3 GSD Curated Config v2** — Phases 16–22 (in progress)

Phase numbering continues across milestone boundaries and is never reset. Integer `0`
and `999` are reserved by `gsd-core`'s phase-id parser as non-milestone sentinels
(`999.x` = Backlog).

## Phases

<details>
<summary>✅ v1.0 Multi-CLI Foundation & Config Safety (Phases 1.1–5) — SHIPPED 2026-09-10</summary>

- [x] Phase 1.1: Autonomous-Run Infrastructure (INSERTED) (1/1 plans) — completed 2026-09-09
- [x] Phase 1.2: Multi-CLI Runtime Foundation (4/4 plans) — completed 2026-09-09
- [x] Phase 2: Opencode Provider Management (2/2 plans) — completed 2026-09-09
- [x] Phase 3: Tool-Substitution Awareness Hook (2/2 plans) — completed 2026-09-09
- [x] Phase 4: Config Doctor (3/3 plans) — completed 2026-09-10
- [x] Phase 5: Usage Metrics Dashboard (6/6 plans) — completed 2026-09-10

Full details: `milestones/v1.0-ROADMAP.md` · phase dirs: `milestones/v1.0-phases/`

</details>

<details>
<summary>✅ v1.1 Agent Workflow Hygiene & Tooling Polish (Phases 6–8.1) — SHIPPED 2026-09-13</summary>

- [x] Phase 6: AGENTS.md Rules Checker Skill (3/3 plans) — completed 2026-09-11
- [x] Phase 7: Curated GSD Config Skill (4/4 plans) — completed 2026-09-11
- [x] Phase 8: Status-line Quota Color Refactor (1/1 plan) — completed 2026-09-10
- [x] Phase 8.1: Status-line Rate-Burn Pace Fix (INSERTED) (1/1 plan) — completed 2026-09-13

Full details: `milestones/v1.1-ROADMAP.md` · phase dirs: `milestones/v1.1-phases/`

</details>

<details>
<summary>✅ v1.2 ai-kit Rules Skill Family (Phases 9–15.2) — SHIPPED 2026-09-23</summary>

- [x] Phase 9: AGENTS.md Checker Prune (ai-kit-project-rules-agents) (2/2 plans) — completed 2026-09-14
- [x] Phase 10: Makefile Rules Checker (ai-kit-project-rules-makefile) (3/3 plans) — completed 2026-09-14
- [x] Phase 11: Pre-commit Rules Checker (ai-kit-project-rules-precommit) (4/4 plans) — completed 2026-09-14
- [x] Phase 12: Architecture Rules Checker (ai-kit-project-rules-arch) (3/3 plans) — completed 2026-09-14
- [x] Phase 13: Docker Rules Checker (ai-kit-project-rules-docker) (4/4 plans) — completed 2026-09-14
- [x] Phase 14: CI/CD Rules Checker (ai-kit-project-rules-cicd) (4/4 plans) — completed 2026-09-14
- [x] Phase 15: Rules Orchestrator (ai-kit-project-rules-all) (2/2 plans) — completed 2026-09-14
- [x] Phase 15.1: Usage Metrics Dashboard UX/Perf Overhaul (INSERTED) (5/5 plans) — completed 2026-09-21
- [x] Phase 15.2: v1.2 Tech Debt Cleanup (pre-close) (INSERTED) (1/1 plan) — completed 2026-09-23

Full details: `milestones/v1.2-ROADMAP.md` · phase dirs: `milestones/v1.2-phases/`

</details>

### 🚧 v1.3 GSD Curated Config v2 (Phases 16–27) — IN PROGRESS

**Milestone Goal:** Rewrite `ai-kit-gsd-curated-config` into a host-aware, role-scored GSD config
wizard that configures a target project's `.planning/config.json` in four questions plus one
review-and-adjust pass, so every GSD agent runs on the model that best fits its role on the
runtime hosting the session. Source spec:
`docs/superpowers/specs/2026-09-23-gsd-curated-config-v2-design.md`.

- [x] **Phase 16: ai_kit_spec Extensions** - Host detection, model enumeration, and catalog/ranker extensions for pi and codex, plus richer catalog fields (completed 2026-10-15)
- [x] **Phase 16.1: Hardening** (INSERTED) - Gate scope, sibling-first imports, security and correctness fixes from the 2026-10-13 audit; closes Phase 16 (completed 2026-10-15)
- [x] **Phase 17: Curated-Config Inventory & Recommendation Engine** - Read-only project/host inventory and a pure `recommend` function that produces an explainable `plan.json` (completed 2026-10-15)
- [ ] **Phase 18: Cross-AI, Skills & Apply Pipeline** - Plan adjustment, cross-AI review/execution wiring, skill-affinity mapping, and a safe backup/restore apply flow
- [ ] **Phase 18.1: One runtime model** (INSERTED) - Model candidates become (runtime, model) pairs; `native_runtime` and the `native_claude`/cursor-agent naming go away
- [ ] **Phase 19: Evaluation on Claude** - Skill pressure-testing, `/skill-judge` gate, and a live smoke run + `resolve-model` proof from the claude host
- [ ] **Phase 20: Live Validation on Codex + Opencode** - Live smoke runs from the codex and opencode hosts, resolving the two open verifications from the spec
- [ ] **Phase 21: Cursor Live Validation** - Live smoke run from the cursor host (independent; may run any time after Phase 19)
- [ ] **Phase 22: Pi Live Validation** - Live smoke run from the pi host (independent; may run any time after Phase 19)
- [ ] **Phase 23: Host-split status line for Claude Code and Cursor CLI** - Split `tools/status-line.py` per host and ship a Cursor CLI status line with the shared 5/10/15 proximity gauge (promoted from backlog 999.4; independent of Phases 17–22)
- [ ] **Phase 24: Spec-and-discuss chain skill** - Installable skill that runs spec → discuss over a phase range with optional Laya/TypeSafe decisions, quality over simplicity unless MVP mode
- [ ] **Phase 25: Quota-aware cross-AI subprocess supervision** - Route-aware quota classification and a 10-minute / 4-hour wait-and-resume for cross-AI children (from todo 2026-10-14)
- [ ] **Phase 26: Session self-resume and OpenGSD quota rules** - The orchestrating session wakes itself after its own quota stalls; `ai-kit-project-rules-agents` emits both quota directives for OpenGSD projects (spike first)
- [ ] **Phase 27: One-shot goal and loop prompt skill** - A skill that picks `/goal`, schedule/loop or `/gsd-autonomous` for a set of phases or plans and emits a ready-to-paste prompt whose definition of done requires green e2e tests

## Phase Details

### Phase 16: ai_kit_spec Extensions

**Goal**: The shared `ai_kit_spec` package correctly detects pi and codex host sessions, enumerates
all five hosts' real models, and carries the richer catalog/ranker fields the curated-config
rewrite depends on.
**Depends on**: Nothing (first phase of v1.3)
**Requirements**: SPEC-01, SPEC-02, SPEC-03, SPEC-04
**Success Criteria** (what must be TRUE):

  1. `detect-current-runtime` correctly identifies pi (`PI_CODING_AGENT`) and codex
     (`CODEX_THREAD_ID`/`CODEX_VERSION`) sessions in addition to opencode/cursor/claude, honoring
     precedence pi > opencode > cursor > codex > claude when several signals are set.
  2. `detect-runtimes` enumerates real model lists for codex
     (`codex debug models`), and claude (hardcoded aliases + catalog full ids + dated fallback) by invoking the actual
     binaries — never shell functions/aliases — with parsers validated against fixtures captured
     from real CLI output.
  3. Model catalog entries can carry optional `image_input` and `reasoning_modes` (existing field) data, and
     cache files written before this change (without these fields) still load without error.
  4. The ranker accepts `planning`, `general`, `mechanical`, `execution`, `review` purposes via the
     ranking-weights file, and existing `review`/`execute` callers keep working unchanged as
     aliases.
**Plans**: 6/6 plans complete

Plans:
**Wave 1**

- [x] 16-01-PLAN.md — codex model enumeration (`codex debug models` fixture) end-to-end into runtimes.json and catalog `reasoning_modes`

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 16-02-PLAN.md — pi/codex host detection with pi > opencode > cursor > codex > claude precedence; `pi` accepted as native_runtime

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 16-03-PLAN.md — `schema_version` on runtimes.json and model-catalog.json (`_meta`); unversioned caches refresh under `--if-stale`

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 16-04-PLAN.md — claude enumeration: aliases + catalog full ids + dated fallback, never executing claude; catalog-aware `--if-stale` so the real detect → fetch order reaches catalog ids without waiting for the TTL, with every recorded id materialized as an `anthropic/<id>` catalog entry in the same fetch

**Wave 5** *(blocked on Wave 4 completion)*

- [x] 16-05-PLAN.md — optional `image_input` (with `image_input_source` provenance) from models.dev modalities and `opencode models --verbose`

**Wave 6** *(blocked on Wave 5 completion)*

- [x] 16-06-PLAN.md — ranker purposes planning/general/mechanical/execution/review, execute/review aliases, mechanical floor; phase gate (`make test` + `make validate`, causal triage against the pre-phase base)

### Phase 16.1: Hardening (INSERTED)

**Goal**: The quality gate checks the code that actually ships, v1.3 tests exercise v1.3 code,
and the security and correctness defects found by the 2026-10-13 audit are fixed, so Phase 16
can be verified and closed on trustworthy evidence. Source:
`.planning/research/2026-10-13-audit/00-SYNTHESIS.md` §A, §B, §P.
**Depends on**: Phase 16
**Requirements**: HARD-01, HARD-02, HARD-03, HARD-04, HARD-05
**Success Criteria** (what must be TRUE):

  1. The ruff and py-compile hook scopes cover every shipped Python file (the 34 skipped ones *(amended 2026-10-14 from 36; 16.1-SPEC counts 157 of 191 selected)*
     included, `ai_kit_spec/` and superpowers among them), `make validate` runs every test module
     the repo has, and `make validate` is green.
  2. `model_detect.py` (curated-config) and `dispatch.py` (rules-all) resolve their own sibling
     packages before `~/.claude/skills`, and a test proves a branch checkout imports the branch's
     `ai_kit_spec`, not the installed one.
  3. A reviewer `command` from a project's `.aikit/review-spec.toml` never runs until the user
     trusts that file (per content hash), and no reviewer command runs through `shell=True`;
     the usage-metrics dashboard escapes `<` so no `</script` variant (any case) breaks out.
  4. A `Status: Failure` lane never merges into Approved; the quota/transient classifiers match
     only stderr and structured error fields, never the model's answer text; inherited host
     signals (`AI_AGENT` and similar) are scrubbed from child environments; the unrunnable claude and grok
     execute builders are deleted; `gsd_config.py` writes through
     `gsd-tools query config-set` instead of editing the JSON.
  5. The smaller safety items are fixed: codegraph probe timeout and no silent global install, a
     `review-spec.toml` parse error is reported instead of disabling cross-AI, `install.sh
     --branch`/`--dry-run` honored on an existing clone, unique cache temp names, an atomic
     uninstall `settings.json` write, and the AGENTS.md checker survives image links.
     `gsd_catalog.py` and `ai-kit-spec-execute-gsd/SKILL.md` resolve the project-local
     `.claude/gsd-core` before any global one (GSD is installed per repo).
  6. Phase 16 is closed: its VERIFICATION.md exists, the live checks ran (`runtimes.json` carries
     `schema_version`, `model-catalog.json` exists), and STATE, REQUIREMENTS and ROADMAP show it
     complete. The stale v1.3 facts are refreshed before Phase 17 planning (gsd-core 1.16, GSD
     installs missing on other hosts, `~/.gsd/defaults.json` `runtime: codex`, a configured
     Artificial Analysis key, so the ranking is scored).
  7. The phase is executed through `.planning/scripts/cross-ai.mjs` (pi first), as the dogfood run
     for Phase 18's runner. The usage-metrics store compaction (audit A10) stays out of scope.
**Plans**: 31/31 plans complete

Plans:
- Wave 1
  - [x] 16.1-02-PLAN.md — dashboard payload `<` escaping and AGENTS.md checker link handling
  - [x] 16.1-03-PLAN.md — parallel test-runner groups with a 40% CPU cap; every tier and hook through the runner
  - [x] 16.1-04-PLAN.md — sibling-first skill resolution and pylint/pyright groundwork
  - [x] 16.1-29-PLAN.md — `cache_write_json` through mkstemp: unique temp names per writer
- Wave 2
  - [x] 16.1-01-PLAN.md — delete claude/grok execute builders; unsupported execute CLIs fail with exit 2
  - [x] 16.1-05-PLAN.md — `install.sh --branch`/`--dry-run` on existing clones; atomic uninstall write
- Wave 3
  - [x] 16.1-06-PLAN.md — argv-only reviewer dispatch and host-signal scrubbing
  - [x] 16.1-07-PLAN.md — shared project-local-first gsd-tools resolver and wrappers; curated-config imports them
- Wave 4
  - [x] 16.1-08-PLAN.md — trust gate for project-local reviewer commands; loud config errors
  - [x] 16.1-30-PLAN.md — host-signal scrub pinned through every dispatcher with real children
- Wave 5
  - [x] 16.1-09-PLAN.md — shared error classifier and Failure-aware report merging
  - [x] 16.1-10-PLAN.md — GSD config writes through gsd-tools config-set with an undo log
- Wave 6
  - [x] 16.1-11-PLAN.md — codegraph probe with timeout and no install; no `shell=True` rule
  - [x] 16.1-12-PLAN.md — spec-review/spec-config SKILL.md failure, trust and argv wording
- Wave 7
  - [x] 16.1-13-PLAN.md — lint sweep: ai-kit-spec CLI dispatch table and dispatch modules
  - [x] 16.1-15-PLAN.md — lint sweep: tools/ SessionStart hooks and config doctor
  - [x] 16.1-16-PLAN.md — lint sweep: markdown-to-pdf, mermaid-audit, cst-refactor template as data
  - [x] 16.1-18-PLAN.md — lint sweep: opencode-providers, curated-config, spec-discuss
  - [x] 16.1-19-PLAN.md — lint sweep: agents, all, arch, cicd and docker project-rules skills
  - [x] 16.1-26-PLAN.md — lint sweep: makefile and precommit project-rules skills, shared library
  - [x] 16.1-31-PLAN.md — execute-gsd SKILL.md: config-set subcommands, project-local GSD, report-only probe; skill-judge
- Wave 8
  - [x] 16.1-17-PLAN.md — lint sweep: usage-metrics
  - [x] 16.1-25-PLAN.md — lint sweep: tools/ wizard; tools-wide zero findings
  - [x] 16.1-27-PLAN.md — lint sweep: remaining ai-kit-spec-review modules
- Wave 9
  - [x] 16.1-14-PLAN.md — lint sweep: execute-gsd adapter
  - [x] 16.1-28-PLAN.md — lint sweep: execute-superpowers adapter and detect_framework
  - [x] 16.1-21-PLAN.md — tools-side tests clean under pyright and vulture
  - [x] 16.1-22-PLAN.md — skills-side tests clean under pyright and vulture
- Wave 10
  - [x] 16.1-20-PLAN.md — spec-family tests clean under pyright and vulture
- Wave 11
  - [x] 16.1-23-PLAN.md — widen the gate over every shipped Python file; full gate green
- Wave 12
  - [x] 16.1-24-PLAN.md — Phase 16 live checks, verifier re-run and completion

### Phase 17: Curated-Config Inventory & Recommendation Engine

**Goal**: The rewritten `ai-kit-gsd-curated-config` can inventory a target project/host and turn
that inventory plus a profile/rigor choice into a pure, explainable, minimal recommendation
plan — without writing anything.
**Depends on**: Phase 16.1
**Requirements**: INV-01, INV-02, INV-03, REC-01, REC-02, REC-03, REC-04, REC-05, REC-06
**Success Criteria** (what must be TRUE):

  1. `inventory --project-dir` emits one JSON document covering host, the host's own gsd-core
     (path/version/valid keys), model candidates as (runtime, model) pairs (scores, price,
     `image_input`, reasoning levels), skills, project facts, existing config, and detected conflicts
     (`model_policy` presence, cross-host `runtime` mismatch) — reading the catalog from
     `~/.cache/ai-kit/spec` and refreshing `--if-stale`, falling back to a stale-cache warning
     when refresh fails, and to native tier maps (Claude/Codex) or per-slot prompts
     (Cursor/opencode/pi) when no cache exists at all.
  2. `recommend` is a pure function of inventory + profile + rigor + cross-AI answers — the same
     inputs always produce the same `plan.json`, and every entry carries `key`, `value`, `why`,
     `source`.
  3. The three model layers are set correctly per rigor/profile: tier via `model_profile`
     (+ `models.<phase_type>` only where the rigor preset shifts a whole phase), tier→model via
     `model_profile_overrides.<host>.{opus,sonnet,haiku}` chosen by role score under the rigor
     price ceiling with host-specific formatting (Claude skipped unless pinned, Codex ids with
     `reasoning_effort`, Cursor effort-suffixed), and at most 7 specialist `model_overrides`
     following the counterpart/vision/frontend rules, with an explicit "no in-runtime
     counterpart" note on single-provider hosts.
  4. Keys unknown to the host's installed gsd-core version are dropped from the plan with a
     visible note rather than silently written.
**Plans**: 9/9 plans complete

Plans (sequential, one wave each: plans land one at a time in a shared checkout, and each
plan's checks also run the modules the previous plan touched):
- Wave 1
  - [x] 17-01-PLAN.md — opencode 2.x `/api/model` image_input probe, runtimes schema 3, ranker `score_exact`
- Wave 2
  - [x] 17-02-PLAN.md — `recommend` tracer: presets, canonical plan.json, cross-AI reservations, key drop
- Wave 3
  - [x] 17-03-PLAN.md — `inventory` tracer: project-local gsd-core, tables and probed valid keys
- Wave 4
  - [x] 17-04-PLAN.md — tier→model layer: price ceilings, native keep, needs_choice and tie order
- Wave 5
  - [x] 17-05-PLAN.md — catalog adapter: fresh/stale/none states and scored (runtime, model) candidates
- Wave 6
  - [x] 17-06-PLAN.md — specialist overrides: execution, counterpart and vision rules, cap of 7
- Wave 7
  - [x] 17-07-PLAN.md — project facts, existing config, conflicts/info, read-only guarantee
- Wave 8
  - [x] 17-08-PLAN.md — reconcile layer: managed-family unsets, policy leaves, runtime per host
- Wave 9
  - [x] 17-09-PLAN.md — shared-fixture goldens for 5 hosts x 3 rigors, properties, phase gate

### Phase 18: Cross-AI, Skills & Apply Pipeline

**Goal**: A user can adjust the recommended plan, have cross-AI review/execution and per-agent
skills wired in, and safely apply the result to a target project's `.planning/config.json` —
with the v2 flow living alongside the unchanged v1 CLI.
**Depends on**: Phase 17
**Requirements**: XAI-01, XAI-02, SKL-01, SKL-02, SKL-03, SKL-04, APP-01, APP-02, APP-03, APP-04, EVAL-06, SPEC-05 (moved here from Phase 22, 18 D-25)
**Success Criteria** (what must be TRUE):

  1. The user can adjust the plan with `plan-set`/`plan-unset`, and each adjustment is recorded
     with `source: user`.
  2. Cross-AI review sets `workflow.plan_review_convergence` + `review.default_reviewers` (lane ≠ host,
     reviewer provider ≠ planning provider, best `review` score) + `review.models.<lane>` /
     `review.effort.<lane>`; review lanes keep GSD's own lane definitions. Cross-AI execution
     sets `workflow.cross_ai_execution` + `workflow.cross_ai_command = node .planning/scripts/cross-ai.mjs`, a
     script generated per project (amended 2026-10-13, see XAI-02): preference order default
     pi > cursor > opencode (grok is not a target), a model per CLI, unattended full-permission
     flags, bare tool profile by default; `workflow.cross_ai_timeout` ≥ 1800 s; the supervision
     contract holds. Execution defaults on for Claude/Codex and off for opencode/cursor/pi, and
     the report tells the user to run `--cross-ai` while setting `manager.flags.execute`.
  3. Skill inventory covers host skill dirs, project `skills/`, and Claude plugin skills;
     `skill_affinity.json` maps skill families to agents (gated by TDD/frontend/db project facts,
     capped per rigor) shown as bare names and written in gsd-core's required reference form as
     `agent_skills.<agent>`; a recommended-but-missing skill is silently omitted (never offered or
     installed); unknown installed skills get user-confirmed proposed
     mappings, and symlinked skills escaping the global root get a proposed
     `trusted_global_roots` entry.
  4. `apply --dry-run` validates every key against the host gsd-core's valid keys and prints a
     diff without writing; a real `apply` backs up to `config.json.bak-<ts>`, writes only through
     `gsd-tools config-new-project`/`config-set`, restores the backup and names the failing key on
     any error (keeping the newest 3 backups), and runs the required follow-ups (gsd-core's own installer
     pinned to the resolved version, local scope; `effort sync --apply`) only after one grouped user approval, recommending
     `/gsd-map-codebase` separately.
  5. The v1 CLI and its modules still work unchanged next to the new v2 subcommands (no
     removal), `make test` (v1 tests included) and `make validate` are green, the README row is updated, and
     SKILL.md labels cursor and pi "not live-validated" until their respective phases pass.
  6. Ponytail (Claude plugin v5.1.0, addressable as `global:ponytail:<skill>`) is a first-class
     recommended skill set in `skill_affinity.json`: core `ponytail` → planner, executor,
     code-fixer; `ponytail-review`/`ponytail-audit` → code-reviewer and auditors;
     `ponytail-debt` → verifier (amended 2026-10-14); within the per-rigor cap (2/3/5). Whether non-Claude
     hosts can address it (the plugin ships `AGENTS.md` and `gemini-extension.json`) is checked
     and recorded. 18-CONTEXT.md's "ponytail does not exist" note is stale (folded from backlog
     999.4, 2026-10-13).
  7. When a System One backend is detected (local Laya or a TypeSafe key), `jev-fast-decision` is
     recommended in `agent_skills` for `gsd-advisor-researcher` and `gsd-assumptions-analyzer`
     (the discuss-phase decision agents), and is never recommended when no backend is present.
**Plans**: 15/22 plans executed (strictly serial waves 1-22, cross-AI executed)

Plans:
**Wave 1**
- [x] 18-01-PLAN.md — pi RPC model enumeration + router merge proof, strict config-set encoder, presence-only secret check

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 18-02-PLAN.md — inventory: gsd-core review lanes, skills roots, extra key probes (schema 2)

**Wave 3** *(blocked on Wave 2 completion)*
- [x] 18-03-PLAN.md — skill scan (real paths, root escape, Claude plugins), ponytail visibility, System One backend

**Wave 4** *(blocked on Wave 3 completion)*
- [x] 18-04-PLAN.md — cross-AI execution tracer: pi target, script artifact (plan schema 2), purity guard

**Wave 5** *(blocked on Wave 4 completion)*
- [x] 18-05-PLAN.md — execution target selection edges and the D-39 default matrix

**Wave 6** *(blocked on Wave 5 completion)*
- [x] 18-06-PLAN.md — review lanes from the gsd-core registry (vendor, ranking, claude alias, effort)

**Wave 7** *(blocked on Wave 6 completion)*
- [x] 18-07-PLAN.md — skill_affinity.json + skills layer (caps, reference forms, missing-skill rule)

**Wave 8** *(blocked on Wave 7 completion)*
- [x] 18-08-PLAN.md — trusted-root choice, capped unknown-skill proposals, jev gate, pi effect

**Wave 9** *(blocked on Wave 8 completion)*
- [x] 18-09-PLAN.md — runner template: hermetic black-box self-test, runtime blocks, status line

**Wave 10** *(blocked on Wave 9 completion)*
- [x] 18-10-PLAN.md — runner: stderr classification, exit classes, tree id, fallback, group kill

**Wave 11** *(blocked on Wave 10 completion)*
- [x] 18-11-PLAN.md — runner: model preflight and transient retries

**Wave 12** *(blocked on Wave 11 completion)*
- [x] 18-12-PLAN.md — runner: review contract, claude review block, live deadline, knobs

**Wave 13** *(blocked on Wave 12 completion)*
- [x] 18-13-PLAN.md — runner renderer with sha256 header and .new edit protection

**Wave 14** *(blocked on Wave 13 completion)*
- [x] 18-14-PLAN.md — plan-set (refusals, force, D-44 guard, trusted-root approval)

**Wave 15** *(blocked on Wave 14 completion)*
- [x] 18-15-PLAN.md — script pseudo-keys, plan-unset, execution toggles

**Wave 16** *(blocked on Wave 15 completion)*
- [ ] 18-16-PLAN.md — config backups, verbatim restore, apply marker

**Wave 17** *(blocked on Wave 16 completion)*
- [ ] 18-17-PLAN.md — apply --dry-run (diff, refusals, inventory digest)

**Wave 18** *(blocked on Wave 17 completion)*
- [ ] 18-18-PLAN.md — apply write path through gsd-tools + agent-skills check (real gsd-tools E2E)

**Wave 19** *(blocked on Wave 18 completion)*
- [ ] 18-19-PLAN.md — apply proofs: Nth-key restore, prune, re-apply per D-20, reconcile, write discipline

**Wave 20** *(blocked on Wave 19 completion)*
- [ ] 18-20-PLAN.md — follow-ups behind one approval (pinned installer, effort sync, opencode local root)

**Wave 21** *(blocked on Wave 20 completion)*
- [ ] 18-21-PLAN.md — SKILL.md v2 flow, README row, command drift test, skill-judge self-check

**Wave 22** *(blocked on Wave 21 completion)*
- [ ] 18-22-PLAN.md — full gate run and source-of-truth amendments

### Phase 18.1: One runtime model (INSERTED)

**Goal**: ai-kit describes every model candidate the same way, as a (runtime, model) pair, so
"native" stops being a special schema field and routing no longer depends on vendor-specific
names. Source: `.planning/research/2026-10-13-audit/18-runtime-detection-and-subprocess-supervision.md`.
**Depends on**: Phase 18
**Requirements**: RTM-01, RTM-02, RTM-03
**Success Criteria** (what must be TRUE):

  1. A candidate resolves to a native subagent when its runtime is the current host and the host
     can select that model, and to a subprocess through `cross-ai.mjs` otherwise; `native_runtime`
     is gone from the schema and code, and an old config that still carries it loads with a
     visible note.
  2. The `native_claude` naming and the cursor / cursor-agent split are gone: one `cursor`
     runtime id, whose binary is `cursor-agent`.
  3. The affected SKILL.md files and AGENTS.md's Architecture section use the one-model wording,
     and every rewritten SKILL.md passes `/skill-judge` in code review.
**Plans**: TBD

### Phase 19: Evaluation on Claude

**Goal**: The rewritten skill is proven correct end to end from inside a real Claude Code
session — pressure-tested, code-reviewed, and confirmed to make `gsd-tools` resolve every agent's
model exactly as planned.
**Depends on**: Phase 18.1
**Requirements**: EVAL-01, EVAL-02, EVAL-03, APP-05
**Success Criteria** (what must be TRUE):

  1. SKILL.md (rewritten for the four-question + review flow) passes `writing-skills` RED/GREEN
     pressure scenarios B (Claude Rigorous + cross-AI), C (opencode + routers, no catalog),
     D (existing v1 config) and E ("just apply it"), with no-skill and v1 baselines.
  2. `/skill-judge` runs as part of code review and SKILL.md scores ≥96/120 with no
     Critical/Important findings.
  3. A live smoke run from the claude host — `inventory` + `recommend` + `apply` (dry-run, then
     real on a scratch project) — completes without corrupting the scratch project's config.
  4. After `apply`, `gsd-tools resolve-model <agent>` with `GSD_RUNTIME=claude` returns the
     planned model for all 35 agents, proven against the real installed `gsd-tools`.
**Plans**: TBD

### Phase 20: Live Validation on Codex + Opencode

**Goal**: The skill is confirmed working from real codex and opencode host sessions, resolving
the two open verifications the spec left pending.
**Depends on**: Phase 19
**Requirements**: EVAL-04, EVAL-05
**Success Criteria** (what must be TRUE):

  1. A live smoke run from the codex host (`inventory` + `recommend` + `apply`) completes
     successfully, and the codex session env signal (`CODEX_THREAD_ID`/`CODEX_VERSION`) is
     confirmed live rather than only source-inspected.
  2. A live smoke run from the opencode host completes successfully, and whether the opencode
     review lane is usable from an opencode host is confirmed and reflected in the recommendation
     logic and SKILL.md.
**Plans**: TBD

### Phase 21: Cursor Live Validation

**Goal**: The skill is confirmed working from a real cursor host session; cursor's
"not live-validated" label is lifted.
**Depends on**: Phase 19 (independent of Phase 20; may run any time afterward, and nothing
downstream depends on it). AGT-01 does not depend on Phase 19 and may run first, or any time,
within this phase.
**Requirements**: EVAL-07, SPEC-06, AGT-01
**Success Criteria** (what must be TRUE):

  1. A live smoke run from the cursor host (`inventory` + `recommend` + `apply`, dry-run then
     real) completes successfully on a scratch project.
  2. SKILL.md's "not live-validated" label for cursor is removed once the smoke run passes.
  3. `cursor-agent` is detected and enumerated even when wrapped by a shell function/alias
     (SPEC-06, deferred from Phase 16).
  4. ai-kit ships Cursor executor subagents `composer-worker` and `grok-worker`, each pinned to a
     non-fast model, from a `cursor-agents/` folder linked into `~/.cursor/agents` by
     `tools/setup.py` (wizard Choose-step rows when Cursor is detected, plus a headless
     `--cursor-agents` flag, both tested); a live delegation shows
     the pinned model in the Task call and one run is confirmed non-fast in the Cursor usage
     dashboard (AGT-01; source todo
     `.planning/todos/pending/2026-10-13-add-cursor-subagents-pinned-to-non-fast-composer-2-5-and-grok.md`).
**Plans**: TBD

### Phase 22: Pi Live Validation

**Goal**: The skill is confirmed working from a real pi host session; pi's "not live-validated"
label is lifted.
**Depends on**: Phase 19 (independent of Phases 20–21; may run any time afterward, and nothing
downstream depends on it)
**Requirements**: EVAL-08
**Success Criteria** (what must be TRUE):

  1. A live smoke run from the pi host (`inventory` + `recommend` + `apply`, dry-run then real)
     completes successfully on a scratch project. A live spike first settles whether per-agent
     models take effect on a pi host at all (gsd-core 1.16's registry declares pi with
     `namedDispatch: false`, `maxDepth: 0` and a plugin-only install), and pi plans claim only
     the verified effect (amended 2026-10-14, replacing "per-agent `pi --model` wiring via the
     subagent extension").
  2. SKILL.md's "not live-validated" label for pi is removed once the smoke run passes.
  3. `detect-runtimes`' pi parser (added in Phase 18 for SPEC-05) is re-verified against the live
     RPC `get_available_models` output (amended 2026-10-15 per 22 D-04).
**Plans**: TBD

### Phase 23: Host-split status line for Claude Code and Cursor CLI

**Goal**: Ship a Cursor CLI status line next to the Claude Code one. Split `tools/status-line.py`
into a host-neutral `common_statusline.py`, one module per host (`claude_statusline.py`,
`cursor_statusline.py`) and an isolated `cursor_quota.py` (the only network and credential code),
with thin `claude-status-line.py` / `cursor-status-line.py` entries (module names are shorthand: the
layout follows the owner-reviewed role split, 23 D-02). The Cursor line shows model +
context and three separate quota segments: API usage, included usage (auto + models), and extra
(on-demand) usage against its ceiling, plus the billing-cycle reset. Every quota segment on both
hosts uses one shared proximity gauge: spend % vs elapsed % of its window/cycle, bands of 5 / 10 /
15 points from optimal (green / yellow / orange / red), keeping the `+`/`-` sign. Cursor quota
comes from the undocumented Dashboard API and is always marked inferred (`≈`).
**Depends on**: none inside v1.3 (independent of Phases 17–22). Before planning: ~~decide
`worktree-context-tools-manager-plan1`~~ *(decided by uz 2026-10-14: it does not land in ai-kit;
its useful parts are a tools-installer todo)*, and copy the host-split spec + REVIEW from branch
`spec/host-split-statusline` into `.planning/specs/`. The 5 gap-gauge commits `d23749b..52def0f`
are already on this branch; mark the gap spec accepted and amend PROJECT.md (burn pace superseded).
**Requirements**: STL-01, STL-02, STL-03, STL-04, STL-05 (defined 2026-10-14 in the Phase 23 spec)
**Success Criteria** (what must be TRUE):

  1. Phase A (split): the Claude render is byte-identical before and after the split, the split
     files stay ruff/pylint clean (the old debt was cleared on 2026-10-13), and the stale
     `docs/architecture/status-line-pipeline.md` is fixed or deleted.
  2. Phase B (Cursor host): the Cursor line renders model, context and the three quota segments
     (API / included / extra), each individually placeable, all colored by the shared gauge; the
     cache keeps `data_fetched_at` apart from `last_attempt_at`/`last_error`, hides quota on
     401/403 and after `cycle_end`, restricts `CURSOR_API_ENDPOINT` to https `*.cursor.sh`, puts
     timeouts on every `git` call, shows resets in local time, and shows an error segment on a bad
     TOML value instead of crashing; redacted real Dashboard responses are test fixtures.
  3. Render vs fetch timing is measured (the user keeps a timing metric) before choosing an inline
     fetch with a cache or a background refresher; "Cursor kills slow renders" is not assumed.
  4. Phase C1/C2: `setup.py --with-statusline[=claude,cursor]` wires each detected host headless,
     and the wizard runs the verify/replace/keep status-line flow per detected host.
  5. Both entries are reachable after v1.3 merges to `main`; `tests/test_arch.py` banner and
     role-prefix rules pass for the new modules; `make test` and `make validate` are green.

**Linked assets:** spec + REVIEW on `spec/host-split-statusline`; POC branch
`poc/cursor-statusline` (reference only, never promoted or merged; inventory what works first);
research notes 13 and 13b; todo `2026-10-12-promote-cursor-statusline-poc-into-999-4.md` on main.
**Plans**: TBD

### Phase 24: Spec-and-discuss chain skill

**Goal**: ai-kit ships an installable, shareable skill that takes a range of GSD phases through
`/gsd-spec-phase --auto` and then the assumptions-mode discuss (the intent of the user's
`--analyze --all --batch --assumptions` invocation; the literal `--assumptions` flag writes no
files, 24 D-01), one phase at a time. Gray-area decisions go through an optional decision-model ladder (local Laya →
TypeSafe direct → the main model's own reasoning) and are logged. The design rule is
quality over simplicity, except under `workflow.mvp_mode`. Learned from the tools-installer
run of 2026-10-13/14 and this milestone's own Phases 16.1–23.
**Depends on**: Phase 16.1's gate widening (D-01, D-06) for R13's regex-based gate coverage (24 D-23); otherwise none inside v1.3 (it drives GSD workflows; it is dogfooded on Phases 16.1–23)
**Requirements**: SDC-01, SDC-02, SDC-03, SDC-04
**Success Criteria** (what must be TRUE):

  1. Given a phase range (`--from N --to M`, or a list), the skill runs spec then discuss for each
     phase in order with the learned behavior (24 D-01). With no range it reads the roadmap, proposes the
     not-yet-discussed range, and asks the user once.
  2. Decision models are optional and detected, never assumed: Laya through TCP reachability of a
     configured local URL, TypeSafe through a key present by name, jev-fast-decision through its
     install (amended 2026-10-14, 18 D-36 / 24 D-08, D-09). With none
     present, every decision falls to the main model's reasoning, and the chain still completes.
     Remote backends need the user's standing consent, and only summaries are sent.
  3. Every decision is logged with one column per backend used plus the locked decision and its
     reason. A model answer that contradicts the project docs is overridden and the override is
     logged. The chain stops only on a critical, contradictory question.
  4. Under `workflow.mvp_mode: true` the recommendation favors the simpler design without lowering
     the quality of what reaches the product's user. Otherwise the best design wins over the
     smallest diff, and ponytail findings feed the choice without deciding it.
  5. The skill is named `ai-kit-gsd-spec-discuss` (chosen in its spec, 2026-10-14). It is
     auto-discovered by `tools/setup.py` (no registry entry), has a README row, and it passes `/skill-judge` in code review.
**Plans**: 1 plan

Plans:
- [x] 24-01-PLAN.md — the skill, its three scripts, tests, gates and README row

### Phase 25: Quota-aware cross-AI subprocess supervision

**Goal**: When a cross-AI child (pi, opencode, cursor, codex) stops on a usage limit, the
orchestrator tells a limit that recovers by waiting from one that never will, waits and resumes
only the unfinished work for the first, and stops and reports for the second, instead of
failing or retrying blindly. Source: todo
`2026-10-14-agents-md-quota-schedule-rules-and-goal-prompt-skill.md` (part 1, mechanism B).
**Depends on**: Phase 18.1 (one runner, closed status table); amends 18 D-27's exit classes
before the runner is planned.
**Requirements**: QTA-01, QTA-02, QTA-03
**Success Criteria** (what must be TRUE):

  1. A per-CLI table of quota, limit and billing message patterns is built from observed child
     output, each pattern labelled verified or unverified.
  2. Classification is route-aware. On a router-backed route (`infer_fallback_quota`, e.g.
     `router-env/*`), a billing or limit error can come from the last paid model of a fallback
     chain whose subscription tiers recover within minutes or hours, so it is wait-recoverable.
     On a direct third-party provider route (OpenCode Zen, Cursor API models) a billing or
     access error is not recoverable by waiting: report it and move to the next candidate.
  3. Limits are detected both live (stdout/stderr while the child runs) and after the fact (a
     timeout or an exit with partial work).
  4. A wait-recoverable limit is re-checked every 10 minutes for at most 4 hours. Before resuming,
     the working tree is checked and only the unfinished work is re-dispatched (the runner's
     per-CLI `resume`). After 4 hours it stops and reports; it never loops forever.
  5. The same policy runs in the runner and in `ai-kit-spec-review` / `ai-kit-spec-execute*`,
     replacing their hourly `CronCreate` wake.
**Plans**: TBD

### Phase 26: Session self-resume and OpenGSD quota rules

**Goal**: An orchestrating session that runs out of its own quota resumes by itself, through a
wake mechanism that survives the stall, and OpenGSD projects get both quota directives in their
AGENTS.md. Source: the same todo (part 1, mechanism A and the rules-skill rule).
**Depends on**: Phase 25 (the subprocess directive's wording). A spike runs before planning:
whether `claude -p --continue` *(amended 2026-10-14, 26-SPEC R3: `--resume <session-id>`, never "most recent")* (or each host's equivalent) started from an OS timer re-enters the
right session; codex, pi and opencode facts are third-party only so far.
**Requirements**: QTA-04, QTA-05, QTA-06 *(QTA-06 added 2026-10-14)*
**Success Criteria** (what must be TRUE):

  1. Per host, the skill detects which wake primitives outlive the session (an OS timer or a cloud
     routine) and which die with it (`CronCreate`, `ScheduleWakeup`, `/loop`), and picks by
     survival. Unverified host behavior is flagged.
  2. The main agent sets an hourly wake that re-enters the same session; the session-resume
     mechanism and the subprocess mechanism (Phase 25) stay separate, each with its own trigger.
  3. `ai-kit-project-rules-agents` gains a rule *(amended 2026-10-14: two rules, R18 and R19)*, active only for OpenGSD projects, that checks
     and remediates both directives as separate items.
  4. *(Added 2026-10-14, QTA-06.)* The same checker gains a language-agnostic rule for every
     project with a detected stack: AGENTS.md says unit tests run in parallel, with workers capped
     at 40% of the available CPUs and never a hardcoded core count, in the detected stack's own
     form. Remediation writes that form into the rules section.
**Plans**: TBD

### Phase 27: One-shot goal and loop prompt skill

**Goal**: The user names a set of GSD phases or superpowers plans and gets a ready-to-paste
prompt for a separate agent session that carries everything needed to finish them: the chosen
execution strategy, rails, quota handling and a definition of done that requires green e2e
tests. Source: the same todo (part 2).
**Depends on**: Phases 25 and 26 (quota directives); reuses Phase 24's skill patterns.
**Requirements**: GPS-01, GPS-02, GPS-03, GPS-04
**Success Criteria** (what must be TRUE):

  1. After a few questions, the skill detects the host and its goal, loop and schedule primitives
     (tools, not only slash commands), the GSD/OpenGSD scope (phases; spec, discuss and plan files
     present) or the superpowers plans, and picks one to three strategies from a selection matrix
     (`/goal`, schedule or `/loop`, `/gsd-autonomous`).
  2. The generated `.md` holds the copy-paste prompt with rails: AGENTS.md first, candidate
     skills, pre-commit enforced, definition-of-done checks, stop-if rules and a final summary.
     Superpowers plans get one subagent per plan; OpenGSD plans get cross-AI convergence declared
     in each plan, with a path for projects whose cross-AI setup is incomplete.
  3. **E2E is the core of the definition of done.** The prompt names the project's real e2e
     commands (real app launch, PTY/TUI drive, a browser for web), requires them green before
     "done", and makes the agent print the evidence (command output, screenshots or TUI
     snapshots) where a transcript-judged `/goal` can see it. With no e2e suite, creating one
     comes first.
  4. jev is used only for advisory, text-based checks (e.g. how close the delivered work is to
     the stated objectives); never as a gate and never to judge UI quality or mockup fidelity,
     since it answers typed questions on text. The skill passes `/skill-judge`.
**Plans**: TBD

## Backlog

### Phase 999.1: Config Doctor reachable from the setup wizard (BACKLOG)

**Goal:** [Captured for future planning] Config Doctor (v1.0 Phase 4) is a
standalone `textual` TUI reached only through `setup.py --config-doctor`; the
setup wizard (`tools/wizard_app.py`: housekeeping, Choose, Arrange, Review,
Done) never offers it, and `make doctor` runs the different status-line
doctor. Make Config Doctor reachable from the wizard (for example an entry on
the Done step, or a dedicated step) reusing the existing stdlib-only engine
(`config_doctor_checks.py` / `config_doctor_readers.py` /
`config_doctor_appliers.py`) and `config_doctor_app.py` screen, with no second
implementation. Coordinate with v1.3 Phase 23 C2 (per-host
status-line step); `worktree-context-tools-manager-plan1` no longer lands (2026-10-14). Candidate rows to add later: the Playwright MCP Chrome path
on Bazzite. Rewritten 2026-10-13 from the former "shared core for a CLI
variant" note, whose goal (engine not coupled to the TUI) is already met.
**Requirements:** TBD
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.2: Cursor hooks path ignores CURSOR_CONFIG_DIR (BACKLOG)

**Goal:** [Captured for future planning] `tools/setup.py`'s single `Paths.cursor_dir`
(`CURSOR_CONFIG_DIR` or `~/.cursor`) is used for Cursor hook wiring, but the Cursor CLI
(2026.10.01 bundle) always reads user hooks from `~/.cursor/hooks.json` and ignores both
`CURSOR_CONFIG_DIR` and `XDG_CONFIG_HOME`. When `CURSOR_CONFIG_DIR` is set, ai-kit writes hooks
where the CLI never looks. Resolve the hooks path separately from the config dir (Phase 23 D-21
adds the config-dir resolver for the status line), re-verify against current Cursor docs, and
check Phase 21's `cursor-agents` destination against the same split. Found by the Phase 23
assumptions analysis, 2026-10-14.
**Requirements:** TBD
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.5: Idle watchdog for the cross-AI runner (BACKLOG)

**Goal:** [Captured for future planning] The Phase 18 cross-AI runner
(`.planning/scripts/cross-ai.mjs`, rendered from the ai-kit-spec-review template) kills the
child's process group only at the overall deadline (outer `workflow.cross_ai_timeout` minus the
D-29 margin). A child that hangs without output burns the whole window. Add an opt-in idle
watchdog: kill the process group after N seconds with no stdout/stderr growth, then exit with the
existing status vocabulary (a `retry-later` or `fallback` action, never a new exit class). It needs
a self-test case and a default that is safe for slow, quiet models. Deferred by 18 D-43
(RUN-46, 2026-10-15): not required by SPEC R5/D-27, and the runner is the largest new code in
Phase 18.
**Requirements:** TBD
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)
