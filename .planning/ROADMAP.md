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

### 🚧 v1.3 GSD Curated Config v2 (Phases 16–22) — IN PROGRESS

**Milestone Goal:** Rewrite `ai-kit-gsd-curated-config` into a host-aware, role-scored GSD config
wizard that configures a target project's `.planning/config.json` in four questions plus one
review-and-adjust pass, so every GSD agent runs on the model that best fits its role on the
runtime hosting the session. Source spec:
`docs/superpowers/specs/2026-09-23-gsd-curated-config-v2-design.md`.

- [ ] **Phase 16: ai_kit_spec Extensions** - Host detection, model enumeration, and catalog/ranker extensions for pi and codex, plus richer catalog fields
- [ ] **Phase 17: Curated-Config Inventory & Recommendation Engine** - Read-only project/host inventory and a pure `recommend` function that produces an explainable `plan.json`
- [ ] **Phase 18: Cross-AI, Skills & Apply Pipeline** - Plan adjustment, cross-AI review/execution wiring, skill-affinity mapping, and a safe backup/restore apply flow
- [ ] **Phase 19: Evaluation on Claude** - Skill pressure-testing, `/skill-judge` gate, and a live smoke run + `resolve-model` proof from the claude host
- [ ] **Phase 20: Live Validation on Codex + Opencode** - Live smoke runs from the codex and opencode hosts, resolving the two open verifications from the spec
- [ ] **Phase 21: Cursor Live Validation** - Live smoke run from the cursor host (independent; may run any time after Phase 19)
- [ ] **Phase 22: Pi Live Validation** - Live smoke run from the pi host (independent; may run any time after Phase 19)

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
**Plans**: 6/6 plans executed

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

### Phase 17: Curated-Config Inventory & Recommendation Engine

**Goal**: The rewritten `ai-kit-gsd-curated-config` can inventory a target project/host and turn
that inventory plus a profile/rigor choice into a pure, explainable, minimal recommendation
plan — without writing anything.
**Depends on**: Phase 16
**Requirements**: INV-01, INV-02, INV-03, REC-01, REC-02, REC-03, REC-04, REC-05, REC-06
**Success Criteria** (what must be TRUE):

  1. `inventory --project-dir` emits one JSON document covering host, the host's own gsd-core
     (path/version/valid keys), host models (scores, price, `image_input`, reasoning levels),
     other CLIs' models, skills, project facts, existing config, and detected conflicts
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
**Plans**: TBD

### Phase 18: Cross-AI, Skills & Apply Pipeline

**Goal**: A user can adjust the recommended plan, have cross-AI review/execution and per-agent
skills wired in, and safely apply the result to a target project's `.planning/config.json` —
with the v2 flow living alongside the unchanged v1 CLI.
**Depends on**: Phase 17
**Requirements**: XAI-01, XAI-02, SKL-01, SKL-02, SKL-03, APP-01, APP-02, APP-03, APP-04, EVAL-06
**Success Criteria** (what must be TRUE):

  1. The user can adjust the plan with `plan-set`/`plan-unset`, and each adjustment is recorded
     with `source: user`.
  2. Cross-AI review sets `plan_review_convergence` + `review.default_reviewers` (lane ≠ host,
     reviewer provider ≠ planning provider, best `review` score) + `review.models.<lane>` /
     `review.effort.<lane>`; cross-AI execution sets `cross_ai_execution` + `cross_ai_command`
     (bare CLI name via `build_execute_command`) with a rigor-dependent timeout, defaulting on
     for Claude/Codex and off for opencode/cursor/pi, and the report tells the user to run
     `--cross-ai` while setting `manager.flags.execute`.
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
     any error (keeping the newest 3 backups), and runs the required follow-ups (`gsd install
     <host>`, `effort sync --apply`) only after one grouped user approval, recommending
     `/gsd-map-codebase` separately.
  5. The v1 CLI and its modules still work unchanged next to the new v2 subcommands (no
     removal), `make test` (v1 tests included) and `make validate` are green, the README row is updated, and
     SKILL.md labels cursor and pi "not live-validated" until their respective phases pass.
**Plans**: TBD

### Phase 19: Evaluation on Claude

**Goal**: The rewritten skill is proven correct end to end from inside a real Claude Code
session — pressure-tested, code-reviewed, and confirmed to make `gsd-tools` resolve every agent's
model exactly as planned.
**Depends on**: Phase 18
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
     non-fast model, linked into `~/.cursor/agents` by `tools/setup.py`; a live delegation shows
     the pinned model in the Task call and one run is confirmed non-fast in the Cursor usage
     dashboard (AGT-01; source todo
     `.planning/todos/pending/2026-10-13-add-cursor-subagents-pinned-to-non-fast-composer-2-5-and-grok.md`).
**Plans**: TBD

### Phase 22: Pi Live Validation

**Goal**: The skill is confirmed working from a real pi host session; pi's "not live-validated"
label is lifted.
**Depends on**: Phase 19 (independent of Phases 20–21; may run any time afterward, and nothing
downstream depends on it)
**Requirements**: EVAL-08, SPEC-05
**Success Criteria** (what must be TRUE):

  1. A live smoke run from the pi host (`inventory` + `recommend` + `apply`, dry-run then real)
     completes successfully on a scratch project, including per-agent `pi --model` process wiring
     via the subagent extension.
  2. SKILL.md's "not live-validated" label for pi is removed once the smoke run passes.
  3. `detect-runtimes` enumerates pi models (`pi --list-models`) via a fixture-backed parser
     (SPEC-05, deferred from Phase 16).
**Plans**: TBD

## Backlog

### Phase 999.1: Shared core for Config Doctor's TUI and a future CLI variant (BACKLOG)

**Goal:** [Captured for future planning] Phase 4 (Config Doctor) builds the
review screen as a `textual` TUI (D-05/D-06 in
`.planning/milestones/v1.0-phases/04-config-doctor/04-CONTEXT.md`). The user's proposal: a
future CLI-mode Config Doctor should never be a second, independently-written
implementation — the check-running/apply engine (D-01's declarative registry:
read current value, compare to recommended, apply on confirm) should be
extracted into a shared core module, with both the TUI and a future
plain-CLI/scriptable front-end sitting on top of that same core. Not built in
Phase 4 (which ships TUI-only) — this is a note that Phase 4's engine should
be written without coupling check/apply logic directly to `textual` widgets,
so a CLI front-end can be added later without a rewrite. Framed by the user
as a pattern GSD itself could recognize/scaffold ("core logic shared across a
TUI and a CLI front-end"), not just an ai-kit-specific task.
**Requirements:** TBD
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.2: Cron/scheduling automation for usage-metrics daily ingestion (BACKLOG)

**Goal:** [Captured for future planning] Phase 5 (Usage Metrics Dashboard)
builds the ingestion/refinement pipeline script to be idempotent and
incremental — safe to run once a day (D-07 in
`.planning/milestones/v1.0-phases/05-usage-metrics-dashboard/05-CONTEXT.md`) — but does not
wire an actual recurring trigger for it. Not built in Phase 5 (manual
invocation only) — this is a note that a future phase should add a real
daily automation mechanism (cron job, systemd user timer, or equivalent)
that invokes the already-idempotent pipeline script, without requiring any
change to the script itself. Deferred explicitly by the user during Phase 5
discussion ("the cron can stay deferred to the backlog for now").
**Requirements:** TBD
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.3: Architecture-layer test suite (BACKLOG)

**Goal:** [Captured for future planning] `tests/test_arch.py` currently
enforces structural invariants (banner-block boundaries, `cfg_`/`probe_`/
`fmt_`/`util_`/`core_`/`seg_` role-prefix conventions) for a single file,
`tools/status-line.py`, via AST parsing. The user's proposal: extend this
into a real architecture-layer test suite following standard
software-architecture testing practices — e.g. dependency-direction rules
(runtime code never importing dev-only packages), layering boundaries
enforced across the whole `tools/`/`skills/` tree (not just one file), and
similar fitness functions for other structurally-significant modules
(`tools/setup.py`, the `ai_kit_spec` package). Not built yet — this is a
note that architecture-fitness testing should generalize beyond the current
single-file, single-convention check. Raised while drafting this project's
`AGENTS.md`/`docs/agent-instructions/testing.md`.
**Requirements:** TBD
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

**Note (2026-09-13):** Promoted and resolved at a scoped-down,
form/convention-only ambition by v1.2's Phase 12 (`ai-kit-project-rules-arch`
— see `REQ-rules-arch`). Phase 12 verifies `arch-test` Makefile target
existence/chaining/AST-only-ness; the fuller dependency-direction/layering-
boundary enforcement ambition described above remains an explicitly-flagged
known gap, not built by Phase 12. This stub is left as-is for history; it is
not duplicated as a second active roadmap item.

### Phase 999.4: Ponytail as a first-class recommended skill set in curated GSD setup (BACKLOG)

**Goal:** [Captured for future planning] **The user puts strong emphasis on this.** When the
curated GSD setup (`ai-kit-gsd-curated-config` v2) builds the per-agent skills list
(`agent_skills.<agent>`), the ponytail plugin must be one of the skills it recommends. The plugin
is now installed as a Claude plugin, v5.1.0, and provides:
- `ponytail:ponytail` (smallest complete change);
- `ponytail:ponytail-audit` (whole-repo audit);
- `ponytail:ponytail-review`;
- `ponytail:ponytail-debt`;
- `ponytail:ponytail-gain`;
- `ponytail:ponytail-help`.

These cover planning, auditing, execution and review, so they would help across the GSD
workflow, including on ai-kit itself.

This overlaps Phase 18 (SKL-01..03, design §7 `skill_affinity.json`), which is not executed yet:
- `18-CONTEXT.md` says ponytail "does not exist … so per D-03 it is simply not mentioned". That
  is now stale: ponytail is installed and addressable as `global:ponytail:<skill>`, which works on
  the Claude host only. The plugin also ships `AGENTS.md` and `gemini-extension.json`, so check
  whether other hosts can address it too.
- Map each ponytail command to agents, not only the core skill:
  - core `ponytail` → planner, executor, code-fixer (design §7 "token economy");
  - `ponytail-review` and `ponytail-audit` → code-reviewer and the auditors;
  - `ponytail-debt` → planner or verifier.
- Respect the per-agent skill cap per rigor (2/3/5).

Preferred route: fold this into Phase 18 when it is planned (amend `18-CONTEXT.md` D-03 and the
§7 mapping), rather than leaving it as a separate later phase.
**Requirements:** TBD
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)
