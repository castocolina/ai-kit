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

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1.1: Autonomous-Run Infrastructure (INSERTED)** - Wire mandatory cross-AI plan-review convergence and cross-AI execution delegation, and build the clean-room Docker/Podman E2E harness, so Phases 1.2-5 can run under `/gsd-autonomous` per `.planning/ONESHOT-RULES.md` (completed 2026-09-09)
- [x] **Phase 1.2: Multi-CLI Runtime Foundation** - Harden the installer's git fetch, add runtime self-detection, and research opencode's sidebar/status-bar viability (completed 2026-09-09)
- [x] **Phase 2: Opencode Provider Management** - List and safely remove custom opencode providers via atomic, surgical JSONC edits (completed 2026-09-09)
- [x] **Phase 3: Tool-Substitution Awareness Hook** - Inject a live-verified rtk tool-substitution briefing into Claude Code session starts (completed 2026-09-09)
- [x] **Phase 4: Config Doctor** - One-screen, confidence-labeled config diagnostics across Claude Code/opencode/Codex with confirmed per-item apply (completed 2026-09-10)
- [x] **Phase 5: Usage Metrics Dashboard** - Capture, refine, and locally visualize how uz actually uses AI CLIs (completed 2026-09-10)
- [ ] **Phase 6: AGENTS.md Rules Checker Skill** - Wrap `/agent-md-refactor` with a house-ruleset checker for Makefile target shape and the accumulated workflow rules
- [ ] **Phase 7: Curated GSD Config Skill** - Small curated question set that writes and schema-validates `.planning/config.json`, replacing `gsd-settings`/`gsd-config`'s full interrogation
- [ ] **Phase 8: Status-line Quota Color Refactor** - Rate-limit bucket coloring becomes relative to time-left-in-window, not raw usage percentage

## Phase Details

### Phase 1.1: Autonomous-Run Infrastructure (INSERTED)

**Goal**: Phases 1.2-5 of this milestone can run unattended under `/gsd-autonomous`, with every plan mandatorily routed through cross-AI plan-review convergence, execution optionally delegated to cross-AI, and every phase's `make test` re-verified in a genuinely clean-room container before being trusted.
**Depends on**: Nothing (infrastructure; must complete before Phase 1.2 is planned so `/gsd-plan-phase 1.2` already runs under convergence)
**Requirements**: None (infrastructure-only; no product-facing PRD requirement maps to this phase — see `.planning/PROJECT.md`'s Key Decisions for why no ADR-locked requirement exists for tooling work like this)
**Success Criteria** (what must be TRUE):

  1. `.planning/config.json` has `workflow.plan_review_convergence: true`, `review.default_reviewers`/`review.models` pointing at a correctly-configured opencode route, and `workflow.cross_ai_execution: true` with `cross_ai_command` pointing at a correctly-configured opencode route — every subsequent `PLAN.md` in this milestone is produced under convergence. This criterion verifies config correctness plus a documented, exercised Rule 2 fallback, never perpetual live availability — route reachability is inherently transient, evidenced by `.planning/phases/01.1-autonomous-run-infrastructure-inserted/01.1-REVIEWS.md`: cycle 1 (the primary `router-env/my-plan-review` route unreachable twice, the Rule 2 fallback to `openai/gpt-5.6-sol` engaging and succeeding) and cycle 2 (the primary route AND the Rule 2 fallback route unreachable simultaneously, triggering the Rule 7 circuit-breaker manual-review path). (amended 2026-09-09, see `01.1-REVIEWS.md` [77fd340] cycle 2 New Concerns.)
  2. `make e2e-docker` builds a container with no pre-existing `~/.claude`, `~/.cursor`, `~/.config/opencode`, or `~/.codex`, and passes the full `make test`+`make lint` suite inside it.
  3. `.planning/ONESHOT-AUTONOMOUS.md` and `.planning/ONESHOT-RULES.md` exist, are internally consistent with this project's real Makefile targets and `config.json`, and name real, live-verified cross-AI routes (no invented model names).
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

**Plans**: 3 plans

Plans:

- [ ] 06-01-PLAN.md — Scaffold + Makefile target-shape checker + stack-cache architecture (REQ-agtmd-makefile-rules, REQ-agtmd-workflow-rules, REQ-agtmd-skill-pipeline)
- [ ] 06-02-PLAN.md — Remediation payload + research-dispatch cache close-out + full SKILL.md wrap narrative (REQ-agtmd-wrapper, REQ-agtmd-makefile-rules)
- [ ] 06-03-PLAN.md — skill-judge loop, naming-analyzer + rename, README row (REQ-agtmd-skill-pipeline, REQ-agtmd-wrapper)

### Phase 7: Curated GSD Config Skill

**Goal**: Setting up or refreshing `.planning/config.json` for a GSD project takes a short, curated question set instead of the full `gsd-config`/`gsd-settings` interrogation, while still producing a valid config.
**Depends on**: Nothing (independent of Phases 1.1-6 and of Phase 8)
**Requirements**: REQ-cfg-curated-questions, REQ-cfg-writes-config, REQ-cfg-schema-validate, REQ-cfg-skill-pipeline
**Success Criteria** (what must be TRUE):

  1. Running the new skill asks only a small, curated question set (not the full `gsd-config`/`gsd-settings` interrogation) and, without prompting for them, applies the preset defaults: high effort for analysis tasks, Haiku for execution tasks, cross-AI execution enabled, and plan-review convergence enabled.
  2. The skill writes `.planning/config.json` in the same shape `gsd-settings`/`gsd-config` produce today — an existing GSD workflow that reads `config.json` accepts the generated file without modification.
  3. When an open-GSD config JSON schema is present on the system, the generated config validates against it; when no schema is present, generation still succeeds without a hard failure.
  4. The skill's SKILL.md is scaffolded via `/superpowers:writing-skills`, reviewed via `/skill-judge` (no remaining Critical/Important finding), and carries the name chosen by `/naming-analyzer`.

**Plans**: 4 plans

Plans:

- [ ] 07-01-PLAN.md — Tracer (`ensure-project`/`apply-profile`) + live-derived critical-agent model/effort overrides (D-01, D-03)
- [ ] 07-02-PLAN.md — Model/CLI detection + preference-pattern matching; cross-AI execution command + structured plan-review keys (D-02, D-04, D-05)
- [ ] 07-03-PLAN.md — `claude_md_path`/frontend detection, D-07 workflow-flag defaults bundle, merge-mode end-to-end integration test (D-06, D-07, D-08, D-09)
- [ ] 07-04-PLAN.md — SKILL.md scaffold + skill-judge loop, naming-analyzer + rename, full gate registration, README row (SC4, D-10)

### Phase 8: Status-line Quota Color Refactor

**Goal**: The status line's rate-limit bucket coloring reflects real urgency — how much of the window's time is left versus how much quota is used — instead of raw usage percentage alone.
**Depends on**: Nothing (independent of Phases 1.1-7)
**Requirements**: REQ-stln-time-relative-color, REQ-stln-ramp-tests
**Success Criteria** (what must be TRUE):

  1. Two rate-limit buckets with identical `used_percentage` but different time remaining before `resets_at` render different colors — the bucket with less time left is flagged more urgently.
  2. **Color-only change**: the displayed `used_percentage` number and the `resets_at`-derived reset-time suffix are byte-identical to today's output — only the ramp color selection changes. No other rendered value is touched.
  3. **No hardcoded window/time values**: every timing input (window start/elapsed fraction, `resets_at`) is read from the Claude-provided rate-limit context on each render; nothing about the 5h/7d window length or "how much time has passed" is a hardcoded constant in the formula.
  4. The color computation is derived from a formula comparing `used_percentage` against remaining-fraction-of-window (a burn-rate signal): `ratio = used_percentage / remaining_fraction`, where `remaining_fraction = 1 - elapsed_fraction`, fed into the unchanged `theme.ramps["rate"]` thresholds (`[(50,"GREEN"),(80,"YELLOW"),("inf","RED+bold")]`). Worked example, verified directly against that ramp: identical 50% usage with 4h remaining in a 5h window gives `50 / 0.8 = 62.5` → YELLOW; the same 50% usage with only 1h remaining gives `50 / 0.2 = 250` → RED+bold — strictly more urgent, never less, satisfying SC1. (RED+bold is the ramp's final band; "more urgent than RED+bold" is not a representable state, so no worked example may claim one.) Confirmed by a throwaway spike script before the formula is locked in, per the project's theory-to-hypothesis-to-spike convention. (Amended 2026-09-11, corrected again same day after cycle-2 review: the original worked example used two DIFFERENT usage percentages at two different points in time — a burn-PACE framing mathematically incompatible with SC1's same-usage invariant; `pct/elapsed_fraction` satisfied that example but was monotonically backwards relative to SC1. The first correction attempt switched the formula to `pct/remaining_fraction` but kept an arithmetically-impossible worked example ("1h remaining reads even more urgent than red" — RED+bold has no more-urgent band above it); this text now states the real, directly-computed ramp outputs. See `08-REVIEWS.md` cycle 1 and cycle 2, `08-CONTEXT.md`'s D-01–D-04, and `REQUIREMENTS.md`'s matching correction to `REQ-stln-time-relative-color`.)
  5. `tests/test_status_line.py`'s existing ramp test pattern (`test_render_time_colors_by_slo_sla_ramp`) is extended with new cases covering the time-relative formula, including a case asserting the displayed percentage/reset-suffix text is unchanged, and the full suite passes.

**Plans**: 1 plan

Plans:

- [ ] 08-01-PLAN.md — Burn-rate ratio helpers (`util_rate_window_seconds` + `util_rate_burn_ratio`) wired into `util_rate_group_str`'s rate-limit ramp call site, plus ramp-boundary test coverage extending the existing pattern (REQ-stln-time-relative-color, REQ-stln-ramp-tests)

## Progress

**Execution Order:**
Phases execute in numeric order: 1.1 → 1.2 → 2 → 3 → 4 → 5 → 6 → 7 → 8 (Phases 6, 7, and 8 are mutually independent — v1.1 scope, order among them is a scheduling choice, not a dependency)

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1.1. Autonomous-Run Infrastructure (INSERTED) | 1/1 | Complete    | 2026-09-09 |
| 1.2. Multi-CLI Runtime Foundation | 4/4 | Complete    | 2026-09-09 |
| 2. Opencode Provider Management | 2/2 | Complete    | 2026-09-09 |
| 3. Tool-Substitution Awareness Hook | 2/2 | Complete    | 2026-09-09 |
| 4. Config Doctor | 3/3 | Complete    | 2026-09-10 |
| 5. Usage Metrics Dashboard | 6/6 | Complete    | 2026-09-10 |
| 6. AGENTS.md Rules Checker Skill | 0/3 | Not started | - |
| 7. Curated GSD Config Skill | 0/TBD | Not started | - |
| 8. Status-line Quota Color Refactor | 0/1 | Not started | - |

## Backlog

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
</content>
