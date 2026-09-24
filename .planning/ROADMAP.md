# Roadmap: ai-kit

## Overview

This milestone turns 5 ingested proposal PRDs (`docs/prds/ai-kit-*-v1.0-prd.md`
— **not yet ADR-locked, all explicitly framed by their authors as proposals**)
into 5 delivery phases. The journey: first widen ai-kit's own foundation for
running under multiple AI CLIs (hardened installer, runtime self-detection,
opencode UI research), then ship two independent config-safety building
blocks (opencode provider management's atomic surgical-edit pattern,
tool-substitution's live-verified detection + curated substitution list) that
the final two phases explicitly reuse — Config Doctor borrows the surgical-edit
pattern and folds in a tool-substitution Non-Goals note, and the Usage Metrics
Dashboard mirrors the same curated substitution list for command-family
tagging. Approving this roadmap is this milestone's acceptance step for the 5
proposals; no separate ADR exists for them (see PROJECT.md Key Decisions).

**v1.1 addendum (Agent Workflow Hygiene & Tooling Polish):** Phases 6-8 below
add this milestone's scope, sourced directly from 3 pending todos captured
during v1.0 rather than new research. Two are new skills (an AGENTS.md house-
rules checker, and a curated GSD config-writing skill) sharing the same
skill-authoring pipeline (`/superpowers:writing-skills` → `/skill-judge` →
`/naming-analyzer`); the third is a status-line coloring-formula refactor.
All three are independent of each other and of the completed v1.0 phases
above — see PROJECT.md's "Current Milestone" section for the v1.1 goal.

**v1.2 addendum (ai-kit Rules Skill Family):** Phases 9-15 below complete the
rules-checker skill family designed in
`docs/superpowers/specs/2026-09-12-ai-kit-rules-skill-family-design.md`. The
prior, already-merged `ai-kit-rules-shared-package` plan extracted
domain-agnostic infrastructure into `skills/_shared/ai_kit_rules_common/`;
this milestone finishes pruning the AGENTS.md checker down to
AGENTS.md-prose scope, then builds five new single-domain checkers
(Makefile, pre-commit, architecture-test-shape, Docker Compose, CI/CD) plus
an orchestrator that aggregates all six. Sequencing matters here, unlike
v1.1's mutually-independent phases: the AGENTS.md prune must land before the
Makefile checker can safely claim the dropped logic, each subsequent domain
checker builds on the shared-package and skill-authoring conventions the
prior one established, and the orchestrator needs all 5 domain checkers (plus
the pruned agents checker) to exist before it can aggregate them — so Phases
9-15 run strictly in order (9 → 10 → 11 → 12 → 13 → 14 → 15), not in
parallel. Phase 12 (the architecture checker) also promotes and resolves the
Backlog's "Phase 999.3: Architecture-layer test suite" entry at this
milestone's scoped-down, form/convention-only ambition — see that phase's own
goal for the resolution note. See PROJECT.md's "Current Milestone" section
for the full v1.2 goal.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)
- **Note (2026-09-08):** `gsd-core`'s phase-id parser reserves integer `0` (and `999`) as a
  non-milestone sentinel range (same bucket as this roadmap's own `999.x` Backlog
  entries) — a `0.x` phase can never resolve as a real milestone phase. To insert a
  phase before the original Phase 1, Phase 1 itself was renumbered to **1.2** and the
  insertion became **1.1** (both children of integer milestone 1, ordered
  1.1 → 1.2), rather than using `0.1`. Live-verified against `phase-id.cjs`'s
  `SENTINEL_RANGES = [0, 999]` before making this call — see Phase 1.1's own
  `1.1-DISCUSSION-LOG.md` for the investigation.
- **Note (2026-09-10):** Phase numbering continues across milestone boundaries —
  v1.1 starts at Phase 6, immediately after v1.0's last phase (Phase 5). Phase
  numbers are never reset at a new milestone.
- **Note (2026-09-13):** Phase numbering continues the same way across the
  v1.1 → v1.2 boundary — v1.2 starts at Phase 9, immediately after v1.1's
  last phase (Phase 8). Unlike v1.1's mutually-independent Phases 6-8,
  Phases 9-15 form a strict dependency chain (9 → 10 → 11 → 12 → 13 → 14 →
  15) per REQUIREMENTS.md's v1.2 section — each phase must complete before
  the next is planned.

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1.1: Autonomous-Run Infrastructure (INSERTED)** - Wire mandatory cross-AI plan-review convergence and cross-AI execution delegation, and build the clean-room Docker/Podman E2E harness, so Phases 1.2-5 can run under `/gsd-autonomous` per `.planning/ONESHOT-RULES.md` (completed 2026-09-09)
- [x] **Phase 1.2: Multi-CLI Runtime Foundation** - Harden the installer's git fetch, add runtime self-detection, and research opencode's sidebar/status-bar viability (completed 2026-09-09)
- [x] **Phase 2: Opencode Provider Management** - List and safely remove custom opencode providers via atomic, surgical JSONC edits (completed 2026-09-09)
- [x] **Phase 3: Tool-Substitution Awareness Hook** - Inject a live-verified rtk tool-substitution briefing into Claude Code session starts (completed 2026-09-09)
- [x] **Phase 4: Config Doctor** - One-screen, confidence-labeled config diagnostics across Claude Code/opencode/Codex with confirmed per-item apply (completed 2026-09-10)
- [x] **Phase 5: Usage Metrics Dashboard** - Capture, refine, and locally visualize how uz actually uses AI CLIs (completed 2026-09-10)
- [x] **Phase 6: AGENTS.md Rules Checker Skill** - Wrap `/agent-md-refactor` with a house-ruleset checker for Makefile target shape and the accumulated workflow rules (completed 2026-09-11)
- [x] **Phase 7: Curated GSD Config Skill** - Small curated question set that writes and schema-validates `.planning/config.json`, replacing `gsd-settings`/`gsd-config`'s full interrogation (completed 2026-09-11)
- [x] **Phase 8: Status-line Quota Color Refactor** - Rate-limit bucket coloring becomes relative to time-left-in-window, not raw usage percentage (completed 2026-09-10)
- [x] **Phase 8.1: Status-line Rate-Burn Pace Fix (INSERTED)** - Reverses Phase 8's burn-rate formula direction to `pct / elapsed_fraction` (pace), fixing a live regression where low usage well into a rate-limit window rendered as an urgency color (completed 2026-09-13)
- [x] **Phase 9: AGENTS.md Checker Prune (ai-kit-project-rules-agents)** - Prune the renamed AGENTS.md/CLAUDE.md checker to AGENTS.md-prose scope only, dropping all Makefile-specific logic (completed 2026-09-14)
- [x] **Phase 10: Makefile Rules Checker (ai-kit-project-rules-makefile)** - New skill inherits the dropped Makefile logic plus `validate-<category>` parity, help/fail reachability, recipe-length cap, docker build-before-up, shellcheck threshold, and an advisory ordering heuristic (completed 2026-09-14)
- [x] **Phase 11: Pre-commit Rules Checker (ai-kit-project-rules-precommit)** - New skill checks Makefile↔pre-commit parity and applies the 6-category tooling taxonomy plus ruff/golangci-lint-specific checks (completed 2026-09-14)
- [x] **Phase 12: Architecture Rules Checker (ai-kit-project-rules-arch)** - New skill verifies `arch-test` Makefile target shape/chaining/AST-only-ness; promotes and resolves backlog Phase 999.3 at form/convention-only scope (completed 2026-09-14)
- [x] **Phase 13: Docker Rules Checker (ai-kit-project-rules-docker)** - New skill checks the docker-compose target family, healthcheck conventions, `depends_on` discipline, hot-reload convention, and runbook presence (completed 2026-09-14)
- [x] **Phase 14: CI/CD Rules Checker (ai-kit-project-rules-cicd)** - New skill checks that CI config reuses Makefile/pre-commit/package.json/Gradle commands instead of duplicating tool invocations inline (completed 2026-09-14)
- [x] **Phase 15: Rules Orchestrator (ai-kit-project-rules-all)** - New orchestrator skill runs all 6 checkers' `check`/`remediate` and aggregates one criticality-ordered report (completed 2026-09-14)

## Phase Details

### Phase 1.1: Autonomous-Run Infrastructure (INSERTED)

**Goal**: Phases 1.2-5 of this milestone can run unattended under `/gsd-autonomous`, with every plan mandatorily routed through cross-AI plan-review convergence, execution optionally delegated to cross-AI, and every phase's `make test` re-verified in a genuinely clean-room container before being trusted.
**Depends on**: Nothing (infrastructure; must complete before Phase 1.2 is planned so `/gsd-plan-phase 1.2` already runs under convergence)
**Requirements**: None (infrastructure-only; no product-facing PRD requirement maps to this phase — see `.planning/PROJECT.md`'s Key Decisions for why no ADR-locked requirement exists for tooling work like this)
**Success Criteria** (what must be TRUE):

  1. `.planning/config.json` has `workflow.plan_review_convergence: true`, `review.default_reviewers`/`review.models` pointing at a correctly-configured opencode route, and `workflow.cross_ai_execution: true` with `cross_ai_command` pointing at a correctly-configured opencode route — every subsequent `PLAN.md` in this milestone is produced under convergence. This criterion verifies config correctness plus a documented, exercised Rule 2 fallback, never perpetual live availability — route reachability is inherently transient, evidenced by `.planning/phases/01.1-autonomous-run-infrastructure-inserted/01.1-REVIEWS.md`: cycle 1 (the primary `router-env/my-plan-review` route unreachable twice, the Rule 2 fallback to `openai/gpt-5.6-sol` engaging and succeeding) and cycle 2 (the primary route AND the Rule 2 fallback route unreachable simultaneously, triggering the Rule 7 circuit-breaker manual-review path). (amended 2026-09-09, see `01.1-REVIEWS.md` [77fd340] cycle 2 New Concerns.)
  2. `make e2e-docker` builds a container with no pre-existing `~/.claude`, `~/.cursor`, `~/.config/opencode`, or `~/.codex`, and passes the full `make test`+`make lint` suite inside it.
  3. `.planning/ONESHOT-ENTRY-PROMPT.md` and `.planning/ONESHOT-RULES.md` exist, are internally consistent with this project's real Makefile targets and `config.json`, and name real, live-verified cross-AI routes (no invented model names).
  4. `workflow.plan_review_convergence: true` is set in `.planning/config.json`, and the real entry points that fire the convergence mechanism (`/gsd-plan-review-convergence <phase>`, or `/gsd-autonomous --converge`/`--cross-ai`) actually do so when invoked — proven in-scope by this phase's own `.planning/phases/01.1-autonomous-run-infrastructure-inserted/01.1-REVIEWS.md`, a real convergence run against this phase's own `01.1-01-PLAN.md`. A bare `/gsd-plan-phase` invocation never triggers convergence on its own. (amended 2026-09-09, see `01.1-CONTEXT.md` D-02 and `01.1-RESEARCH.md` Pitfall 3 for why a bare `/gsd-plan-phase` invocation never auto-invokes convergence; re-amended same day per `01.1-REVIEWS.md` [d896183] HIGH concerns 1-2, which found the first amendment's own proposed verification action would itself require invoking convergence against a not-yet-planned Phase 1.2 before Phase 1.1 closes — this wording instead grounds the proof in Phase 1.1's own already-completed convergence run)

**Plans**: 1/1 plans executed

Plans:

- [x] 01.1-01-PLAN.md — Fix Dockerfile `make` gap + PTY deadline flake and verify `make e2e-docker` green; formally amend Success Criterion 4's wording; document the D-09 fixture convention and re-confirm Success Criteria 1 and 3

### Phase 1.2: Multi-CLI Runtime Foundation

**Goal**: ai-kit's installer and model-catalog tooling are hardened and runtime-aware as the project expands beyond Claude Code toward opencode and Codex.
**Depends on**: Phase 1.1 (needs the cross-AI plan-review convergence wired before this phase is planned)
**Requirements**: REQ-multi-cli-install-single-branch, REQ-multi-cli-runtime-detection, REQ-multi-cli-opencode-ui-research
**Success Criteria** (what must be TRUE):

  1. Running the installer only ever fetches the target branch's history (single-branch clone) via its primary git path, never pulling unrelated refs — while the tarball-fallback and already-cloned `git pull --ff-only` paths stay byte-identical.
  2. Asking "which CLI is ai-kit running under right now" gets a reliable, empirically-confirmed answer (`claude`/`opencode`/`codex`/`cursor`/`unknown`) reflected in the model catalog's `native_runtime` field for entries with `cli: None` — never set on entries with a real `cli` value. (Amended 2026-09-09: `cli: None`/`cli`-omitted semantics live in `review-spec.toml`'s native `[[reviewers]]` entries, not in `model_catalog.py` — plan 01.2-02 added `native_runtime` schema validation to both `config_io.py` (functionally-reachable) and `model_catalog.py` (forward-compatible only), each enforcing the "never set with a real `cli` value" invariant as a machine-checked rejection, not prose-only. See `01.2-02-PLAN.md`'s Open Question 1 resolution.)
  3. `ai-kit-spec-config`'s wizard visibly labels `native_runtime` in its ranked candidate output, and the change passes `skill-judge` review. (Amended 2026-09-09: "ranked candidate output" resolves to Step 2.7's native-entry ask, not Step 2.2's ranked CLI-candidate block — a native entry never goes through Step 2.2, so no native row exists there to annotate. See `01.2-04-PLAN.md`.)
  4. A committed markdown research report exists enumerating opencode's documented plugin hooks, assessing each for sidebar/status-bar viability, cross-referencing `anomalyco/opencode#5971`, and giving an explicit recommendation.

**Plans**: 4/4 plans executed

Plans:

- [x] 01.2-01-PLAN.md — Harden tools/install.sh's primary git clone with `--single-branch` (REQ-multi-cli-install-single-branch)
- [x] 01.2-02-PLAN.md — Implement detect_current_runtime() + native_runtime schema validation in model_catalog.py/config_io.py, resolving RESEARCH.md's Open Question 1 (REQ-multi-cli-runtime-detection)
- [x] 01.2-03-PLAN.md — Write the opencode sidebar/status-bar plugin viability research report (REQ-multi-cli-opencode-ui-research)
- [x] 01.2-04-PLAN.md — Wire native_runtime into ai-kit-spec-config's wizard (Step 2.7/Step 3) and pass skill-judge review (REQ-multi-cli-runtime-detection)

**UI hint**: yes

### Phase 2: Opencode Provider Management

**Goal**: Users can safely inspect and remove custom opencode providers from their config without hand-editing JSONC or risking corruption.
**Depends on**: Nothing (independent of Phase 1.2)
**Requirements**: REQ-opencode-provider-list-remove, REQ-opencode-provider-cross-reference-check
**Success Criteria** (what must be TRUE):

  1. Running the new skill's `list` subcommand shows every custom provider's id, `npm` package, and `baseURL` — never the `apiKey` value.
  2. Running `remove <id>` deletes exactly that provider's block while every other byte of `opencode.jsonc` (comments, formatting, unrelated providers) stays byte-identical — including when a provider's value contains a literal `{`/`}` — and the write is atomic (temp file + rename).
  3. Removing a non-existent id produces a clear no-op message instead of a crash or silent success.
  4. Before removing, the user is warned by name of every place the target id is referenced in `.aikit/review-spec.toml` or the cached model catalog, without removal ever being blocked on that warning.

**Plans**: 2 plans

Plans:

- [x] 02-01-PLAN.md — Tracer-first `remove <id>` slice, the four-state JSONC scanner (string/escape/line-comment/block-comment) with depth-1 anchoring, the mode-preserving atomic writer, the comma-position case split, and `list` (REQ-opencode-provider-list-remove)
- [x] 02-02-PLAN.md — Complete the cross-reference scan (both review-spec tiers + cached catalog) with a per-source audit trail, write and skill-judge the new SKILL.md, and close behind `make test`/`lint`/`validate`/`e2e-docker` (REQ-opencode-provider-cross-reference-check)

### Phase 3: Tool-Substitution Awareness Hook

**Goal**: Claude Code sessions start with an accurate, live-verified explanation of which rtk-driven tool substitutions are actually active on this machine.
**Depends on**: Nothing (independent of Phases 1.2 and 2)
**Requirements**: REQ-tool-substitution-detection-composition, REQ-tool-substitution-hook-wiring
**Success Criteria** (what must be TRUE):

  1. At session start and after compaction, Claude Code shows a composed message naming only the tool substitutions (`cat`↔`bat`, `grep`↔`rg`, `find`↔`fd`, `sed`↔`sd`, `ls`↔`eza`) genuinely installed right now — never reciting `registry.toml` catalog intent as verified fact.
  2. When `rtk` isn't installed, the message says so plainly (or omits substitution content) instead of listing phantom substitutions.
  3. The hook never perceptibly delays session start or post-compaction resume, and degrades to a shorter/empty message instead of erroring when `rtk`/`tools-installer` is absent.
  4. opencode's current lack of an equivalent injection point is documented in the hook's own code or wrapping skill/doc, not silently absent — Cursor is NOT part of this gap: it has its own `sessionStart` hook type and gets the equivalent briefing wired for it too (amended 2026-09-08, live-verified during Phase 4 discussion).

**Plans**: 2 plans

Plans:

- [x] 03-01-PLAN.md — Tracer-first slice from a live PATH probe to a wired Claude Code `SessionStart` entry, the four-state `rtk init --show` detection contract over the curated 5-pair list, the two-part host-agnostic message composition, and the atomic append-if-absent `settings.json` wiring (REQ-tool-substitution-detection-composition, REQ-tool-substitution-hook-wiring)
- [x] 03-02-PLAN.md — Cursor `sessionStart` wiring against its lowercase-keyed flat array, D-10's symmetric `unwire_hook_*` in `cmd_uninstall`, and the host-coverage doc recording opencode as the one accepted gap; closes behind `make test`/`lint`/`validate`/`e2e-docker` (REQ-tool-substitution-hook-wiring)

### Phase 4: Config Doctor

**Goal**: Users get a single, trustworthy screen showing how their Claude Code / opencode / Codex / Cursor configuration compares to recommended settings, and can apply fixes with confidence.
**Depends on**: Phase 2 (reuses its atomic-write + surgical-edit pattern for the apply flow), Phase 3 (folds in its Non-Goals note as the cross-runtime `rtk`-Cursor-integration check)
**Requirements**: REQ-config-doctor-diagnostic-checks, REQ-config-doctor-review-screen, REQ-config-doctor-apply-flow
**Success Criteria** (what must be TRUE):

  1. One command shows every row of the Checks Catalog (plus the folded-in cross-runtime `rtk`-Cursor-integration check) across every runtime with a config file present, each with current value, recommended value, and citation — including Cursor's own researched rows (amended 2026-09-08; row count no longer fixed at 12 pending that research).
  2. A runtime with no config file present has its whole section skipped rather than shown as failing checks; a value that can't be determined shows as "unknown," never silently pass/fail.
  3. Lower-confidence or no-real-backing-setting rows (Codex reasoning effort, opencode retention) are visibly labeled as such and never offered as apply actions.
  4. Choosing to apply a change requires an explicit, per-item confirmation naming the exact change about to be made — there is no bulk "apply all," and security-relevant applies show the literal resulting config before writing.
  5. Applying a JSONC change to opencode preserves every other byte of the file, using the same tested surgical-edit approach as Phase 2's provider-management skill.

**Plans**: 3 plans

Plans:

- [x] 04-01-PLAN.md — Tracer: one Claude Code retention row read-only end-to-end through `--config-doctor`'s review screen (REQ-config-doctor-diagnostic-checks, REQ-config-doctor-review-screen)
- [x] 04-02-PLAN.md — Full Checks Catalog across all four runtimes plus the cross-runtime rtk-Cursor-integration row, read-only (REQ-config-doctor-diagnostic-checks, REQ-config-doctor-review-screen)
- [x] 04-03-PLAN.md — Apply flow: atomic/surgical writers, per-item confirm with literal-resulting-config for security-relevant rows, no bulk apply-all (REQ-config-doctor-apply-flow)

**UI hint**: yes

### Phase 5: Usage Metrics Dashboard

**Goal**: Users can see how they actually use their AI CLIs — locally and privately — across date, model, commands, tokens, and price.
**Depends on**: Phase 3 (mirrors its curated tool-substitution set as the single source of truth for command-family tagging)
**Requirements**: REQ-usage-metrics-raw-capture, REQ-usage-metrics-refinement-pipeline, REQ-usage-metrics-dashboard-ui, REQ-usage-metrics-classification-refinement-loop
**Success Criteria** (what must be TRUE):

  1. ai-kit losslessly captures Claude Code and opencode session logs (Codex and Cursor following as later plans within this phase) into an append-only local raw store, where one runtime's parser failure or log-format change never breaks the others' output.
  2. Raw commands are refined into one cross-runtime schema: compound `&&`/`;`/`|` commands split into ordered steps, relative-path commands resolved via prior `cd` state carried across separate tool-calls in the same session, and each command tagged with its curated "family" (e.g. `rg` tagged `grep`) — with `control_flow_script` and `unclassified` kept as distinct buckets.
  3. A local, filterable/sortable static HTML dashboard (regenerated by the pipeline script with refined data embedded directly — no export/import step, no browser-sandboxed Artifact mechanism) answers a query like "how many grep-family invocations this month, grouped by session" directly from already-refined local data, with no live re-parse and no hosted-database capability ever pointed at session content (amended 2026-09-08, see `05-CONTEXT.md` D-08/D-09/D-10).
  4. A periodic offline pattern-mining pass can be run against accumulated `unclassified`/`control_flow_script` entries to reclassify them (confidence-flagged as `inferred_family`, never shown with hard-decomposed certainty), and re-running it with improved rules reclassifies historical entries too since raw is retained losslessly.

**Plans**: 6 plans

Plans:

- [x] 05-01-PLAN.md — Tracer: Claude Code raw capture -> minimal refined SQLite (simple commands) -> embedded static HTML dashboard, end to end (REQ-usage-metrics-raw-capture, REQ-usage-metrics-refinement-pipeline, REQ-usage-metrics-dashboard-ui)
- [x] 05-02-PLAN.md — opencode raw capture (session/message/part) plus rtk history.db + tee log ingestion (REQ-usage-metrics-raw-capture)
- [x] 05-03-PLAN.md — Codex + Cursor raw capture, Cursor flagged low-confidence (REQ-usage-metrics-raw-capture)
- [x] 05-04-PLAN.md — Full refinement pipeline: mechanical &&/;/| decomposer, cwd-resolution state machine, family tagging across all 5 sources (REQ-usage-metrics-refinement-pipeline)
- [x] 05-05-PLAN.md — Full dashboard UI: filter/sort across the 5 MVP axes, session grouping, SKILL.md + skill-judge (REQ-usage-metrics-dashboard-ui)
- [x] 05-06-PLAN.md — Classification refinement loop: pattern-mining pass, confidence-flagged inferred_family (REQ-usage-metrics-classification-refinement-loop)

**UI hint**: yes

### Phase 6: AGENTS.md Rules Checker Skill

**Goal**: Agents working against any repo's AGENTS.md/CLAUDE.md-style instruction file get an automated check against ai-kit's accumulated house ruleset, not just a generic progressive-disclosure refactor.
**Depends on**: Nothing (independent of Phases 1.1-5 and of Phases 7-8)
**Requirements**: REQ-agtmd-wrapper, REQ-agtmd-makefile-rules, REQ-agtmd-workflow-rules, REQ-agtmd-skill-pipeline
**Success Criteria** (what must be TRUE):

  1. Running the skill against a house AGENTS.md missing one or more required Makefile targets (`setup-env`, a target per pre-commit hook 1:1 with `.pre-commit-config.yaml`, a `validate` target chaining all hook targets lightest-first, `test`/`test-unit` alias, `test-integration`, `e2e-test`, `arch-test`) flags each gap by name, with a per-language tool recommendation (e.g. gofmt/black/prettier for formatting).
  2. Running the skill against an AGENTS.md missing any of the accumulated workflow rules (English-only communication, per-plan commit compaction, cross-AI plan-review + path-agnostic cross-AI execution, rtk/modern-CLI/CodeGraph/graphify tool-awareness, no-absolute-paths, no-excuse-deflection, stale-knowledge verification, theory-hypothesis-spike methodology, no-orphaned-processes, `./tmp/` ephemeral-file convention, README/nested-docs currency, no-uncommitted-files-at-close, concise documentation) flags each missing rule individually rather than returning one generic pass/fail.
  3. Invoking the new skill is observably distinct from invoking plain `/agent-md-refactor` directly — it wraps that skill's refactor pass and adds the house-rule check on top, rather than duplicating or replacing it.
  4. The skill's SKILL.md is scaffolded via `/superpowers:writing-skills`, passes `/skill-judge` with no remaining Critical/Important finding, and carries the name chosen by `/naming-analyzer` — never assumed upfront.

**Plans**: 3/3 plans executed

Plans:

- [x] 06-01-PLAN.md — Scaffold + Makefile target-shape checker + stack-cache architecture (REQ-agtmd-makefile-rules, REQ-agtmd-workflow-rules, REQ-agtmd-skill-pipeline)
- [x] 06-02-PLAN.md — Remediation payload + research-dispatch cache close-out + full SKILL.md wrap narrative (REQ-agtmd-wrapper, REQ-agtmd-makefile-rules)
- [x] 06-03-PLAN.md — skill-judge loop, naming-analyzer + rename, README row (REQ-agtmd-skill-pipeline, REQ-agtmd-wrapper)

### Phase 7: Curated GSD Config Skill

**Goal**: Setting up or refreshing `.planning/config.json` for a GSD project takes a short, curated question set instead of the full `gsd-config`/`gsd-settings` interrogation, while still producing a valid config.
**Depends on**: Nothing (independent of Phases 1.1-6 and of Phase 8)
**Requirements**: REQ-cfg-curated-questions, REQ-cfg-writes-config, REQ-cfg-schema-validate, REQ-cfg-skill-pipeline
**Success Criteria** (what must be TRUE):

  1. Running the new skill asks only a small, curated question set (not the full `gsd-config`/`gsd-settings` interrogation) and, without prompting for them, applies the preset defaults: high effort for analysis tasks, Haiku for execution tasks, cross-AI execution enabled, and plan-review convergence enabled.
  2. The skill writes `.planning/config.json` in the same shape `gsd-settings`/`gsd-config` produce today — an existing GSD workflow that reads `config.json` accepts the generated file without modification.
  3. When an open-GSD config JSON schema is present on the system, the generated config validates against it; when no schema is present, generation still succeeds without a hard failure.
  4. The skill's SKILL.md is scaffolded via `/superpowers:writing-skills`, reviewed via `/skill-judge` (no remaining Critical/Important finding), and carries the name chosen by `/naming-analyzer`.

**Plans**: 4/4 plans executed

Plans:

- [x] 07-01-PLAN.md — Tracer (`ensure-project`/`apply-profile`) + live-derived critical-agent model/effort overrides (D-01, D-03)
- [x] 07-02-PLAN.md — Model/CLI detection + preference-pattern matching; cross-AI execution command + structured plan-review keys (D-02, D-04, D-05)
- [x] 07-03-PLAN.md — `claude_md_path`/frontend detection, D-07 workflow-flag defaults bundle, merge-mode end-to-end integration test (D-06, D-07, D-08, D-09)
- [x] 07-04-PLAN.md — SKILL.md scaffold + skill-judge loop, naming-analyzer + rename, full gate registration, README row (SC4, D-10)

### Phase 8: Status-line Quota Color Refactor

**Goal**: The status line's rate-limit bucket coloring reflects real urgency — how much of the window's time is left versus how much quota is used — instead of raw usage percentage alone.
**Depends on**: Nothing (independent of Phases 1.1-7)
**Requirements**: REQ-stln-time-relative-color, REQ-stln-ramp-tests
**Success Criteria** (what must be TRUE):

  1. Two rate-limit buckets with identical `used_percentage` but different time remaining before `resets_at` render different colors — the bucket with less time left is flagged more urgently. Superseded by Phase 8.1: Phase 8.1 reverses the direction (for a fixed `used_percentage`, MORE elapsed time now renders LESS urgently, not more); this criterion is retained as a record of what Phase 8 shipped rather than a live claim. See Phase 8.1's SC1 plus D-01.
  2. **Color-only change**: the displayed `used_percentage` number and the `resets_at`-derived reset-time suffix are byte-identical to today's output — only the ramp color selection changes. No other rendered value is touched.
  3. **No hardcoded window/time values**: every timing input (window start/elapsed fraction, `resets_at`) is read from the Claude-provided rate-limit context on each render; nothing about the 5h/7d window length or "how much time has passed" is a hardcoded constant in the formula.
  4. The color computation is derived from a formula comparing `used_percentage` against remaining-fraction-of-window (a burn-rate signal): `ratio = used_percentage / remaining_fraction`, where `remaining_fraction = 1 - elapsed_fraction`, fed into the unchanged `theme.ramps["rate"]` thresholds (`[(50,"GREEN"),(80,"YELLOW"),("inf","RED+bold")]`). Worked example, verified directly against that ramp: identical 50% usage with 4h remaining in a 5h window gives `50 / 0.8 = 62.5` → YELLOW; the same 50% usage with only 1h remaining gives `50 / 0.2 = 250` → RED+bold — strictly more urgent, never less, satisfying SC1. (RED+bold is the ramp's final band; "more urgent than RED+bold" is not a representable state, so no worked example may claim one.) Confirmed by a throwaway spike script before the formula is locked in, per the project's theory-to-hypothesis-to-spike convention. (Amended 2026-09-11, corrected again same day after cycle-2 review: the original worked example used two DIFFERENT usage percentages at two different points in time — a burn-PACE framing mathematically incompatible with SC1's same-usage invariant; `pct/elapsed_fraction` satisfied that example but was monotonically backwards relative to SC1. The first correction attempt switched the formula to `pct/remaining_fraction` but kept an arithmetically-impossible worked example ("1h remaining reads even more urgent than red" — RED+bold has no more-urgent band above it); this text now states the real, directly-computed ramp outputs. See `08-REVIEWS.md` cycle 1 and cycle 2, `08-CONTEXT.md`'s D-01–D-04, and `REQUIREMENTS.md`'s matching correction to `REQ-stln-time-relative-color`.) Superseded by Phase 8.1: Phase 8.1 reverses the direction to `used_percentage / elapsed_fraction`; this criterion is retained as a record of what Phase 8 shipped rather than a live claim. See Phase 8.1's SC1 plus D-01.
  5. `tests/test_status_line.py`'s existing ramp test pattern (`test_render_time_colors_by_slo_sla_ramp`) is extended with new cases covering the time-relative formula, including a case asserting the displayed percentage/reset-suffix text is unchanged, and the full suite passes.

**Plans**: 1/1 plans executed

Plans:

- [x] 08-01-PLAN.md — Burn-rate ratio helpers (`util_rate_window_seconds` + `util_rate_burn_ratio`) wired into `util_rate_group_str`'s rate-limit ramp call site, plus ramp-boundary test coverage extending the existing pattern (REQ-stln-time-relative-color, REQ-stln-ramp-tests)

### Phase 8.1: Status-line Rate-Burn Pace Fix (INSERTED)

**Goal**: The rate-limit burn-rate formula reflects real urgency as a PACE signal (usage relative to time already elapsed), not as "less time remaining is always more urgent" — fixing a live regression where low usage well into a window rendered as a warning color.
**Depends on**: Nothing (independent of Phase 8 and of Phases 9-15; a direct reversal of one formula inside Phase 8's own deliverable)
**Requirements**: REQ-stln-time-relative-color
**Success Criteria** (what must be TRUE):

  1. The ratio fed into the unchanged `theme.ramps["rate"]` thresholds is `used_percentage / elapsed_fraction` (`elapsed_fraction = 1 - remaining_fraction`), not `used_percentage / remaining_fraction`. Worked example matching the live-reported regression: 25% used with 4h already elapsed of a 5h window (`elapsed_fraction = 0.8`, `remaining_fraction = 0.2`) — the superseded Phase 8 formula gives `25 / 0.2 = 125` → RED+bold (the bug: low usage well into the window read as urgent); this formula gives `25 / 0.8 = 31.25` → GREEN. See `08.1-CONTEXT.md` D-01/D-02 and `tests/test_status_line.py`'s `TestRateBurnRatio` for the full set of pinned boundary cases.
  2. **Color-only change, same as Phase 8's own SC2**: the displayed `used_percentage` number and `resets_at`-derived reset-time suffix stay byte-identical — only the ramp color selection changes.
  3. `elapsed_fraction ~ 0` (too early in the window) falls back to raw `pct` rather than spiking toward the ramp's top band on no real signal — mirrors, at the opposite edge, Phase 8's own D-03/D-04 fallback behavior for stale/missing/out-of-range `resets_at`.
  4. `tests/test_status_line.py`'s `TestRateBurnRatio` and the render-level `test_h_rate_limit_colors_by_pace_more_elapsed_time_is_less_urgent` pin the reversed direction, and the full suite (`make test-unit` / `python3 -m unittest tests.test_status_line`) passes.

**Plans**: 0/1 plans executed (starting diff already exists on branch `fix/8.1-status-line-rate-burn-pace`, commit `fc2d8bb` — see `08.1-CONTEXT.md` D-04)

Plans:

- [x] 08.1-01-PLAN.md — Land the `fix/8.1-status-line-rate-burn-pace` branch's diff verbatim (cherry-pick `fc2d8bb`), close the two gaps the re-review found (stale call-site/render-test commentary, the unpinned SC1 25%-worked-example case), and formally amend REQUIREMENTS.md's REQ-stln-time-relative-color (REQ-stln-time-relative-color)

### Phase 9: AGENTS.md Checker Prune (ai-kit-project-rules-agents)

**Goal**: The AGENTS.md/CLAUDE.md checker — renamed from `ai-kit-agents-md-rules-checker` to `ai-kit-project-rules-agents` — is pruned to AGENTS.md-prose scope only, so the Makefile-specific logic it currently carries can be cleanly re-homed in Phase 10 without two skills claiming the same checks.
**Depends on**: Nothing new (first phase of this milestone; builds on the already-merged `ai-kit-rules-shared-package` plan's `skills/_shared/ai_kit_rules_common/` extraction). Must complete before Phase 10 is planned, so the dropped Makefile logic has exactly one owner at every point in time.
**Requirements**: REQ-rules-agents-prune
**Success Criteria** (what must be TRUE):

  1. The skill directory is renamed to `ai-kit-project-rules-agents`, and its `check` command returns only `{"workflow": [...]}` (no `"makefile"` key) when run against any target repo.
  2. `makefile_checker.py`, the Makefile-specific `stack_cache.py`/`stack_detect.py`, and the `cache-path`/`cache-update` subcommands are removed from the skill's source tree; the skill retains `rules.py` (all 17 rules) and `rule_checker.py`, now importing the shared `ai_kit_rules_common` classification engine rather than a local copy. Subcommand wording corrected by Phase 9: `cache-update` was the only removed CLI subcommand (`main` dispatched exactly `check`, `remediate`, and `cache-update`); `cache_path` is a plain module-level function in `stack_cache.py` that leaves as a side effect of that module's deletion, never a removed subcommand -- see 09-01-PLAN.md's objective for the same correction recorded on the code side.
  3. `SKILL.md`'s scope line and examples drop all Makefile/`.pre-commit-config.yaml` language, while the existing `/agent-md-refactor` hand-off for AGENTS.md content is unchanged.
  4. The renamed/updated test suite (`tests/test_ai_kit_agents_md_rules_checker.py` or its renamed equivalent) passes with no test exercising the removed Makefile-checking code paths, and `make test` is green.
  5. `/skill-judge` review of the pruned `SKILL.md` shows no remaining Critical/Important finding (or a score ≥ 96/120) with no regression against the pre-prune baseline (98/120). Baseline corrected by Phase 9: the 98/120 figure above is the design spec's own pre-fix number (per 09-CONTEXT.md's skill-judge regression-baseline note); the verified pre-prune baseline is 100/120, measured fresh in this phase against the recovered pre-phase `SKILL.md` blob rather than taken from any cited figure, and is recorded as evidence in this phase's `09-SKILL-JUDGE.md`.

**Plans**: 1/2 plans executed

Plans:

- [x] 09-01-PLAN.md — Rename the skill/package/entrypoint/test file to `ai-kit-project-rules-agents` and repoint every live reference (D-01/D-02) with stale-bytecode cleanup (D-03), then prune `makefile_checker.py`/`stack_detect.py`/the Makefile-tooling `stack_cache.py`/the `cache-path`+`cache-update` subcommands so `check` returns `{"workflow": [...]}` only, relocating the tooling-payload validator into `ai-kit-project-rules-makefile`'s tree (D-04) and re-homing the shared remediation coverage into `tests/test_ai_kit_rules_common.py` (REQ-rules-agents-prune)
- [x] 09-02-PLAN.md — Prune `SKILL.md` and the README registration row to AGENTS.md-prose scope while keeping the `/agent-md-refactor` Steps A/B/C hand-off intact, run `/skill-judge` as this phase's review gate against a freshly measured pre-prune baseline with committed evidence, and formally correct Success Criterion 5's cited baseline figure and Success Criterion 2's subcommand wording (REQ-rules-agents-prune)

### Phase 10: Makefile Rules Checker (ai-kit-project-rules-makefile)

**Goal**: A new skill `ai-kit-project-rules-makefile` owns every Makefile-specific check dropped by Phase 9's prune, plus the new parity/reachability/recipe-length/ordering checks the design spec adds on top.
**Depends on**: Phase 9 (must land first so this skill can safely claim the dropped `makefile_checker.py` logic without leaving a capability gap where neither skill checks it)
**Requirements**: REQ-rules-makefile
**Success Criteria** (what must be TRUE):

  1. Running the new skill's `check` against a target repo's Makefile reproduces every check the old Makefile-checker performed (`REQUIRED_STATIC_TARGETS` shape, `validate`'s chain-incomplete check, the `test`/`test-unit` pairing check) with the same finding shape as before the Phase 9 prune. Inherited-check scope corrected by Phase 10: the pre-prune entry point (verified at commit `9d672b9`'s `skills/ai-kit-project-rules-agents/ai_kit_project_rules_agents/makefile_checker.py`) also emitted a fourth finding kind, the pre-commit-vs-pre-push stage split, which the design spec assigns to the `ai-kit-project-rules-precommit` skill (Phase 11) instead; this phase moved `check_precommit_prepush_split` to the shared package with no caller here, proven by fixture in plan 10-01.
  2. For each tooling category with a concrete target present, the skill requires a matching `validate-<short-name>` alias (e.g. `validate-security`, `validate-duplicate`, `validate-dead`) and flags `validate` when it does not chain all of them — proven by a fixture Makefile with e.g. a `security-scanner` target present but no `validate-security` target.
  3. A fixture Makefile with no `help`-reachable target (no `.DEFAULT_GOAL := help` and no catch-all `%:` rule) is flagged; a fixture with one of those mechanisms present is not.
  4. A fixture Makefile recipe body longer than 3 lines (excluding the help/fail-printing target itself) is flagged as a finding recommending extraction to a `.sh` script; a paired fixture with a 3-line-or-shorter recipe triggers no finding.
  5. A `docker-up`-shaped target without a `docker-build`-shaped Make prerequisite is flagged; once a fixture repo has ≥5 bash scripts and no `shellcheck` target wired into `.pre-commit-config.yaml`, that absence is flagged; and an advisory (non-blocking) reordering suggestion fires when a fixture's `validate` prerequisite list declares a slow tool before a fast one.

**Plans**: 3/3 plans executed

Plans:

- [x] 10-01-PLAN.md — Extract the shared Makefile/pre-commit parsing primitives, stack detection and criticality vocabulary into `skills/_shared/ai_kit_rules_common/` (D-01/D-02/D-05), then wire the new skill end-to-end so a real invocation reproduces the three inherited checks, and re-home the 15 Makefile-domain test classes recovered from Phase 9's rename commit (REQ-rules-makefile)
- [x] 10-02-PLAN.md — The six new checks with paired triggering/non-triggering fixtures: the `validate-<category>` alias family, help/fail reachability, the 3-line recipe cap, Docker build-before-up, the shellcheck threshold, and the advisory ordering heuristic made genuinely non-blocking through `remediate` (REQ-rules-makefile)
- [x] 10-03-PLAN.md — Write `SKILL.md` and the README row, run `/skill-judge` as the phase's code-review gate with committed evidence and `/naming-analyzer` as the pipeline's confirmation step, and formally amend ROADMAP SC1 + REQUIREMENTS' REQ-rules-makefile where the live pre-prune source contradicts their wording (REQ-rules-makefile)

### Phase 11: Pre-commit Rules Checker (ai-kit-project-rules-precommit)

**Goal**: A new skill `ai-kit-project-rules-precommit` verifies Makefile↔pre-commit parity and applies the 6-category cross-language tooling taxonomy to flag configuration anti-patterns.
**Depends on**: Phase 10 (sequenced per this milestone's dependency order; the parity check needs the Makefile-target-parsing conventions `ai-kit-project-rules-makefile` established, and this skill follows the same shared-package/skill-authoring pattern the prior phase set)
**Requirements**: REQ-rules-precommit
**Success Criteria** (what must be TRUE):

  1. A fixture repo with a pre-commit hook id that has no matching single-tool Makefile target is flagged; a fixture with a Makefile target that has no matching hook id is also flagged — the parity check runs both directions, not just one. Parity-check ownership corrected by Phase 11: the sibling `ai-kit-project-rules-makefile` skill (Phase 10) already emits its own finding when a pre-commit hook id has no matching Makefile target, verified via a live invocation of that sibling's own `check` entrypoint against a fixture Makefile/pre-commit-config pair (this plan's own AMENDMENT-BASIS-OK precondition check); what this phase's own parity check adds is the second direction (a Makefile target with no matching hook) plus a reconciliation recommendation in this skill's own domain covering both directions, and the overlap between the two findings is deliberate per the design spec's ownership assignment, not a duplication to remove.
  2. Detected tooling from a fixture `.pre-commit-config.yaml` (e.g. ruff, mypy, bandit, eslint) is classified into exactly one of the 6 taxonomy categories (Formatting/Type-checking/Linting/Security/Duplicate-code/Dead-code), matching the baseline stack tables with no tool left unclassified.
  3. A fixture with ruff `select = ["ALL"]` (or an equivalent "enable-everything" config for another ecosystem) is flagged; a paired fixture with a curated `extend-select` is not.
  4. A fixture repo with zero Duplicate-code-category tooling is flagged for that category; a fixture with zero Dead-code-category tooling is flagged for that category; a fixture with both categories present triggers neither finding.
  5. Ruff-specific checks each prove discrimination with a paired fixture (`ANN`/`TC`-only "type safety" claims flagged; `preview = true` without a pinned CI ruff version flagged; a child config silently discarding a parent's `lint.ignore` flagged), and the golangci-lint-specific check flags standalone `staticcheck` run alongside golangci-lint with staticcheck already enabled.

**Plans**: 4/4 plans executed

Plans:

- [x] 11-01-PLAN.md — Wire the new `ai-kit-project-rules-precommit` skill end-to-end: the bidirectional Makefile↔pre-commit parity check, the inherited pre-commit-vs-pre-push stage splitter given the caller Phase 10 withheld from it, the shared taxonomy vocabulary, `precommit` as a structural kind in the shared remediation ordering, the cache namespace and `cache-update` research step, and registration in every quality gate (REQ-rules-precommit)
- [x] 11-02-PLAN.md — Converge the family's per-language tool knowledge into `skills/_shared/ai_kit_rules_common/tool_catalog.py` (baseline stacks, derived tool index, 6-to-5 category alias table with its drift guard, the locked pairs table), classify every detected tool into exactly one of the 6 taxonomy categories with its confidence reported, and flag complete absence of Duplicate-code or Dead-code tooling (REQ-rules-precommit)
- [x] 11-03-PLAN.md — The configuration anti-patterns with paired fixtures: one degrade-not-crash reader layer for untrusted target-repo configs, the cross-ecosystem enable-everything heuristic plus its explicit unreadable-config limitation, the three ruff-specific checks, and pairs-table evaluation with the presumed-complementary default including the golangci-lint standalone-staticcheck redundancy (REQ-rules-precommit)
- [x] 11-04-PLAN.md — Write `SKILL.md` and the README row, run `/skill-judge` as the phase's code-review gate with committed evidence and `/naming-analyzer` as the pipeline's confirmation step, and formally amend ROADMAP SC1 + REQUIREMENTS' REQ-rules-precommit where the live tree contradicts their wording (REQ-rules-precommit)

### Phase 12: Architecture Rules Checker (ai-kit-project-rules-arch)

**Goal**: A new skill `ai-kit-project-rules-arch` verifies a repo has an `arch-test`-shaped Makefile target, chained into `test`, and (where discoverable) AST-only — carrying baseline per-stack canonical-tool knowledge without attempting real dependency-direction/layering-boundary enforcement. This phase **promotes and resolves** the Backlog's "Phase 999.3: Architecture-layer test suite" entry at exactly this milestone's scoped-down, form/convention-only ambition; that backlog note's fuller dependency-direction/layering-boundary ambition remains an explicitly-flagged known gap, not built here, per the design spec's own scope note. The backlog stub itself is left unchanged in ROADMAP.md — this phase is its resolution, not a second, separate item.
**Depends on**: Phase 11 (sequenced per this milestone's dependency order; shares the shared-package conventions and skill-authoring pattern the prior domain checkers established)
**Requirements**: REQ-rules-arch
**Success Criteria** (what must be TRUE):

  1. Running the skill against ai-kit's own repo — which already has `arch-test` chained into `test` in its Makefile, backed by `tests/test_arch.py` — produces no finding for target existence or chaining.
  2. A fixture repo with no `arch-test`-shaped target is flagged; a fixture repo where `test` does not list `arch-test` as a prerequisite is flagged as a distinct finding from target-existence.
  3. Where the backing test file is discoverable, the skill verifies it is AST-only — proven by a paired fixture: a check file that only parses source via `ast` (or equivalent) passes, a check file that `importlib.import_module`s its target is flagged.
  4. The skill's remediation output names the canonical tool per stack (Python: import-linter, Node/TS: dependency-cruiser, Java: ArchUnit) and explicitly states the Rust/Go known gap rather than asserting a false canonical tool for those languages.
  5. This phase's own PLAN/SUMMARY artifacts record the backlog-resolution note described in this phase's Goal above, so the resolution is traceable from the backlog entry to this phase without editing the backlog stub itself.

**Plans**: 3/3 plans executed

Plans:

- [x] 12-01-PLAN.md — Wire `ai-kit-project-rules-arch` end-to-end: arch-test-shaped target existence and `test`-chaining as two distinct findings, the shared structural-kind tuple grown by one name, and the skill registered in every quality gate (SC1, SC2)
- [x] 12-02-PLAN.md — Target-aware AST-only correlation for the backing test file (12-CONTEXT D-01/D-02) plus the hardcoded per-stack canonical-tool baseline with the Rust/Go known gap (SC3, SC4)
- [x] 12-03-PLAN.md — SKILL.md, README row, `/skill-judge` code-review gate with committed evidence, `/naming-analyzer` confirmation, mechanical SC5 backlog-resolution traceability, and the dated correction to 12-CONTEXT.md's D-01 scouting claim (SC5)

### Phase 13: Docker Rules Checker (ai-kit-project-rules-docker)

**Goal**: A new skill `ai-kit-project-rules-docker` checks docker-compose/Makefile conventions for local-dev Docker workflows: the target family, healthcheck conventions, `depends_on` discipline, the hot-reload convention, and runbook presence.
**Depends on**: Phase 12 (sequenced per this milestone's dependency order; reuses the shared package and skill-authoring conventions)
**Requirements**: REQ-rules-docker
**Success Criteria** (what must be TRUE):

  1. A fixture Makefile missing one or more of the target family (`docker-up`, `docker-health`, `docker-stop`, `docker-clean`, `docker-prune`, `docker-events-up`, `docker-events-monitor`, `docker-events-test`) is flagged by name for each missing target; a fixture with the full family present is not.
  2. A fixture `docker-compose.yml` service with a healthcheck `timeout`/`start_period`/`interval` exceeding 2s/10s/5s respectively is flagged; a paired fixture within all three bounds is not.
  3. A `depends_on` entry using bare ordering (no `condition: service_healthy`) is flagged; a paired entry using `condition: service_healthy` is not.
  4. A local-dev service definition using the production image/entrypoint baked at build time (no bind-mount plus dev command override) is flagged as missing the hot-reload convention; a paired fixture using the bind-mount convention is not.
  5. The absence of `docker/local/README.md` is flagged as a missing runbook requirement; its presence is not.

**Plans**: 4/4 plans executed

Plans:

- [x] 13-01-PLAN.md — Wire `ai-kit-project-rules-docker` end-to-end on the two non-compose criteria: the root-scoped Docker applicability gate, the eight-target family as one finding per missing name, the `docker/local/README.md` runbook check, the shared structural-kind tuple grown by one name, and the skill registered in every quality gate (SC1, SC5)
- [x] 13-02-PLAN.md — The indentation-aware, stdlib-only compose parser (13-CONTEXT D-01/D-02) plus the shared YAML-text primitives, the healthcheck timing bounds, and `depends_on` discipline across all three bare-ordering forms (SC2, SC3)
- [x] 13-03-PLAN.md — Stack-aware hot-reload convention for local-dev services (13-CONTEXT D-03/D-04/D-05): per-stack hot-reload knowledge added to the shared tool catalog, and a three-outcome check that never asserts "no hot reload" from an unrecognized command (SC4)
- [x] 13-04-PLAN.md — SKILL.md with its six honesty-about-limits statements, the README row, the `/skill-judge` code-review gate with committed evidence, `/naming-analyzer` confirmation, and two dated append-only corrections to 13-CONTEXT.md

### Phase 14: CI/CD Rules Checker (ai-kit-project-rules-cicd)

**Goal**: A new skill `ai-kit-project-rules-cicd` checks that CI config reuses existing Makefile/pre-commit/`package.json`/Gradle commands rather than duplicating tool invocations inline in CI YAML.
**Depends on**: Phase 13 (sequenced per this milestone's dependency order; reuses the shared package and skill-authoring conventions)
**Requirements**: REQ-rules-cicd
**Success Criteria** (what must be TRUE):

  1. A fixture CI workflow (`.github/workflows/*.yml` or `.gitlab-ci.yml`) that runs a tool directly (e.g. `ruff check .`) when an equivalent single-tool Makefile target (e.g. `make ruff`) already exists is flagged, naming both the duplicated invocation and the target it should call instead.
  2. A fixture CI workflow that calls `make <target>`/`npm run <script>`/the equivalent Gradle task for every tool it needs — with no direct tool invocation duplicating an existing command — produces no finding.
  3. The check recognizes reuse sources across all four command surfaces named in the requirement (Makefile targets, pre-commit hooks, `package.json` scripts, Gradle tasks), each covered by at least one paired (triggering / non-triggering) fixture.
  4. The skill reuses the shared `ai_kit_rules_common` classification/cache package rather than re-implementing its own parsing primitives, and its own test module imports from `skills/_shared/` the same way the other domain checkers do.

**Plans**: 4/4 plans executed

Plans:

- [x] 14-01-PLAN.md — Tracer: wire `ai-kit-project-rules-cicd` end-to-end on the `.gitlab-ci.yml` reader and the Makefile-target reuse surface — the root-scoped applicability gate, the command-key match rule with its one catalog-grounded widening, the tool-shaped identity gate, the complete reuse-invocation table, the shared `yaml_text` block primitives and new `command_text` grammar module, `cicd` appended to the shared structural-kind tuple, and the skill registered in every quality gate (SC1 GitLab half, SC2, SC3 Makefile pair, SC4)
- [x] 14-02-PLAN.md — The GitHub Actions reader (sequence-of-mapping steps, block-scalar `run:` bodies, the unfetched `uses:` step) and the pre-commit-hook reuse surface on the shared `precommit_parse` reader, with surface precedence settled for all four surfaces (SC1 GitHub half, SC3 pre-commit pair)
- [x] 14-03-PLAN.md — The `package.json`-script surface with lockfile-driven runner resolution and the Gradle-task surface with its pinned plugin table gated on real plugin evidence, completing SC3's four-surface paired-fixture requirement and SC2's remaining half
- [x] 14-04-PLAN.md — `SKILL.md` with its ten honesty-about-limits statements, the README row, the `/skill-judge` code-review gate with committed evidence at a named commit, `/naming-analyzer` confirmation, and dated append-only corrections to `14-CONTEXT.md`

### Phase 15: Rules Orchestrator (ai-kit-project-rules-all)

**Goal**: A new orchestrator skill `ai-kit-project-rules-all` runs all 6 checkers' `check`/`remediate` against one target repo and aggregates their findings into one criticality-ordered report, preserving the existing `/agent-md-refactor` hand-off for AGENTS.md-domain findings only.
**Depends on**: Phase 14 (needs all 5 new domain checkers — makefile, precommit, arch, docker, cicd — plus the Phase 9-pruned agents checker — to exist before it can invoke and aggregate them)
**Requirements**: REQ-rules-all
**Success Criteria** (what must be TRUE):

  1. Running the orchestrator against a target repo invokes all 6 checkers' `check` (agents, makefile, precommit, arch, docker, cicd), and the aggregated report contains findings from every domain that has any, with none silently dropped.
  2. The aggregated report is ordered by criticality across domains (not grouped flatly in invocation order), using the same criticality vocabulary each individual checker's own `remediate` output already uses.
  3. For AGENTS.md-domain findings specifically, the orchestrator still surfaces the `/agent-md-refactor` hand-off; for every other domain's findings, the report is inline and report-only, with no auto-apply — consistent with the family-wide detect-and-report-only scope boundary.
  4. An integration-style test stubs all 6 checkers' `check` output and asserts the aggregation/ordering logic, without needing every individual checker's full logic re-exercised inside that test.
  5. Cross-skill merging of findings across domains exists only inside this orchestrator — no individual checker's own `remediation.py` usage is changed to perform cross-domain merging, per the "Cross-skill remediation merging ownership" protocol in `.planning/intel/constraints.md`.

**Plans**: 2/2 plans executed

Plans:

- [x] 15-01-PLAN.md — Subprocess fan-out (D-01/D-02/D-04/D-05/D-06) and pure cross-domain criticality merge with AGENTS.md hand-off tagging, dogfooded against this repo's own 6 real sibling checkers (SC1, SC2, SC3's data half, SC4, SC5)
- [x] 15-02-PLAN.md — SKILL.md (Step A/B/C hand-off cross-reference, 8 honesty-about-limits statements), registration across README.md/.pre-commit-config.yaml/pyproject.toml, /skill-judge gate, and /naming-analyzer confirmation (SC3's documentation half)

## Progress

**Execution Order:**
Phases execute in numeric order: 1.1 → 1.2 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 8.1 → 9 → 10 → 11 → 12 → 13 → 14 → 15 (Phases 6, 7, and 8 are mutually independent — v1.1 scope, order among them is a scheduling choice, not a dependency. Phase 8.1 is an INSERTED decimal amendment to Phase 8 — same "mutually independent" status, and independent of the v1.2 chain too; it can run at any point relative to Phases 9-15. Phases 9-15 are v1.2 scope and form a strict dependency chain — each must complete before the next is planned, per REQUIREMENTS.md's v1.2 section and this roadmap's v1.2 addendum above.)

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1.1. Autonomous-Run Infrastructure (INSERTED) | 1/1 | Complete    | 2026-09-09 |
| 1.2. Multi-CLI Runtime Foundation | 4/4 | Complete    | 2026-09-09 |
| 2. Opencode Provider Management | 2/2 | Complete    | 2026-09-09 |
| 3. Tool-Substitution Awareness Hook | 2/2 | Complete    | 2026-09-09 |
| 4. Config Doctor | 3/3 | Complete    | 2026-09-10 |
| 5. Usage Metrics Dashboard | 6/6 | Complete    | 2026-09-10 |
| 6. AGENTS.md Rules Checker Skill | 3/3 | Complete    | 2026-09-11 |
| 7. Curated GSD Config Skill | 4/4 | Complete    | 2026-09-11 |
| 8. Status-line Quota Color Refactor | 1/1 | Complete    | 2026-09-10 |
| 9. AGENTS.md Checker Prune | 2/2 | Complete    | 2026-09-14 |
| 10. Makefile Rules Checker | 3/3 | Complete    | 2026-09-14 |
| 11. Pre-commit Rules Checker | 4/4 | Complete    | 2026-09-14 |
| 12. Architecture Rules Checker | 3/3 | Complete    | 2026-09-14 |
| 13. Docker Rules Checker | 4/4 | Complete    | 2026-09-14 |
| 14. CI/CD Rules Checker | 4/4 | Complete    | 2026-09-14 |
| 15. Rules Orchestrator | 2/2 | Complete    | 2026-09-14 |

## Backlog

### Phase 15.2: v1.2 Tech Debt Cleanup (pre-close) (INSERTED)

**Goal:** Close the in-milestone tech debt found by `.planning/v1.2-MILESTONE-AUDIT.md` so v1.2 can close as a verified (not override) closeout.
**Requirements**: none new (debt closure for REQ-rules-precommit / Phase 15.1)
**Depends on:** Phase 15.1
**Plans:** 1/1 plans executed

**Success Criteria** (what must be TRUE):

  1. `uv run pyright` reports 0 errors: `REDUNDANT_VS_COMPLEMENTARY_PAIRS` in `skills/_shared/ai_kit_rules_common/tool_catalog.py` is typed so `pair_checks.py:178`'s unpack type-checks, with no runtime behavior change (all rules-checker tests still pass).
  2. Usage-metrics dashboard `buildCurrentRowsFromFiltered()` guards the flat-mode sort key symmetrically to `GROUPED_SORT_KEYS` (WR-01), and node-executed regression tests cover both directions — grouped-only key in flat mode and flat-only key in grouped mode (WR-02).
  3. `uv run ruff check tests/test_ai_kit_usage_metrics.py` is clean (E501 at :1279, UP031 at :3803).
  4. The 3 pending todos whose `resolves_phase` is 6/7/8 are moved to `.planning/todos/completed/` (GSD's `todo complete` convention).

Out of scope: pre-v1.2 lint in `tools/status-line.py`, `tools/wizard_app.py`, `tests/test_ai_kit_spec_superpowers.py`; the mmdc environment failure; Nyquist VALIDATION backfill.

Plans:
**Wave 1**

- [x] 15.2-01-PLAN.md — Tracer: symmetric flat/grouped sort-key fallback + node regression tests both directions + test-file ruff fix (WR-01/WR-02, SC2/SC3); PairRow TypedDict for pyright 0 errors (SC1); move resolved todos to todos/completed + full gate sweep (SC4)

### Phase 15.1: Usage Metrics Dashboard UX/Perf Overhaul: dashboard launch detection, pagination/virtualization for large datasets, filter bar reordered runtime->model->family->subfamily->command, runtime column, MUI-based visual redesign, charts, empty date column bug, price always-zero investigation, family showing garbage tokens, session-group row duplication bug, default last-week prefilter, unified date-range picker (INSERTED)

**Goal:** The usage-metrics dashboard renders the full refined dataset without freezing
the browser, in a Material-designed light/dark UI with runtime and subfamily filters, one
unified date range, a full-command detail dialog and three charts — and all five
data-correctness bugs found live against the real 84,082-row refined store are fixed and
independently verified: opencode's and cursor's 100%-NULL dates, `family` derived from
opaque script blobs, an unknown price rendering as a blank cell rather than as unknown,
session sums deduping on a turn id that may not exist, and codex's current tool-call shape
never reaching the refiner at all.
**Requirements**: none — inserted urgent-work phase with no formal REQ-IDs; traceability
runs on `15.1-CONTEXT.md`'s decision IDs D-01 through D-19, every one of which is covered
by at least one plan.
**Depends on:** Phase 15
**Plans:** 5/5 plans complete

Plans:
**Wave 1**

- [x] 15.1-01-PLAN.md — Tracer: opencode date fix, Material/CDN dashboard shell, ONE virtualized painter serving both flat and grouped modes, runtime column, auto-open — wired end-to-end

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 15.1-02-PLAN.md — Remaining refiner fixes: command-shape family guard, cursor timestamp recovery, codex custom_tool_call branch plus its workdir resolver, canonical `subfamily_of()` with option arity

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 15.1-03-PLAN.md — Filter bar and column redesign: runtime and subfamily axes, unified from/to date range, wrapped two-line command cell, null-versus-zero rendering

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 15.1-04-PLAN.md — Full-command dialog with sibling-resolved decomposer breakdown, turn-identity session dedup, empty/loading/error states

**Wave 5** *(blocked on Wave 4 completion)*

- [x] 15.1-05-PLAN.md — Dual-axis spend chart and capped distribution chart with dedup-before-sum, split filter/sort update path, SKILL.md realignment, phase-wide gates and real-store re-refine

### Phase 999.1: Shared core for Config Doctor's TUI and a future CLI variant (BACKLOG)

**Goal:** [Captured for future planning] Phase 4 (Config Doctor) builds the
review screen as a `textual` TUI (D-05/D-06 in
`.planning/phases/04-config-doctor/04-CONTEXT.md`). The user's proposal: a
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
`.planning/phases/05-usage-metrics-dashboard/05-CONTEXT.md`) — but does not
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
