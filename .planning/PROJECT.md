# ai-kit

## What This Is

Personal agent skills, slash commands, and a one-line installer, built and
maintained by uz. Skills follow the open [Agent Skills](https://agentskills.io)
standard, so beyond Claude Code they also load unmodified in any conformant
tool (opencode, Codex CLI, Gemini CLI, Cursor, Copilot CLI, Kiro, and others).
It has widened from "a Claude Code installer with some skills" into a
multi-CLI toolkit. It ships runtime detection, opencode provider management,
cross-runtime config diagnostics, a local usage-metrics dashboard, and a family
of project-rules checker skills.

## Current State

**Shipped:** v1.2 ai-kit Rules Skill Family (2026-09-23). v1.0 and v1.1 were
archived retroactively during the same close. See `.planning/MILESTONES.md`.
Phase history lives in `.planning/milestones/v1.{0,1,2}-phases/`.

The rules-checker family (`ai-kit-project-rules-{agents,makefile,precommit,arch,docker,cicd}`
plus the `ai-kit-project-rules-all` orchestrator) shares
`skills/_shared/ai_kit_rules_common/`. The usage-metrics dashboard handles the
real ~85k-row refined store without freezing.

## Current Milestone: v1.3 GSD Curated Config v2

**Goal:** Rewrite `ai-kit-gsd-curated-config` into a host-aware, role-scored GSD config wizard
that configures a target project's `.planning/config.json` in four questions plus one
review-and-adjust pass, so every GSD agent runs on the model that best fits its role on the
runtime hosting the session. Source spec (approved 2026-09-23):
`docs/superpowers/specs/2026-09-23-gsd-curated-config-v2-design.md`.

**Target features:**
- `ai_kit_spec` extensions — host detection pi > opencode > cursor > codex > claude;
  pi/codex/claude model enumeration; `image_input`/`reasoning_modes` catalog data;
  planning/general/mechanical/execution/review ranker purposes
- Hardening (Phase 16.1) — gate scope, sibling-first imports, security and correctness fixes
  from the 2026-10-13 audit; closes Phase 16
- Curated-config rewrite — inventory → recommend → `plan.json` → plan-set → apply
  (dry-run, backup/restore); three model layers plus an execution override; rigor
  (MVP/Standard/Rigorous) × profile presets; counterpart cross-AI review and cheap
  cross-AI execution through a generated `.planning/scripts/cross-ai.mjs`
  (pi > cursor > opencode); curated `skill_affinity.json`
- One runtime model (Phase 18.1) — model candidates as (runtime, model) pairs
- Evaluation on claude — writing-skills RED/GREEN, `/skill-judge` in code review,
  real-gsd-tools `resolve-model` check for all 35 agents, live smoke
- Live validation on codex and opencode; cursor (Phase 21) and pi (Phase 22) as independent
  phases that may run any time after Phase 19

## Core Value

ai-kit must never corrupt uz's AI-CLI configuration and must never claim more
certainty than it has: every config write is atomic and explicitly confirmed,
every diagnostic is honestly labeled by its confidence/sourcing, and every
"this capability is active" claim (tool substitutions, runtime identity) is
verified live rather than assumed from a catalog.

## Requirements

### Validated

<!-- Shipped and confirmed valuable, per README.md at ingest time. -->

- ✓ One-line installer (`tools/install.sh`) — clones/updates the repo, verifies
  and symlinks skills/commands/agents into `~/.claude/`, prunes broken links,
  wires the status line. Idempotent, with a tarball fallback when `git` is
  absent.
- ✓ Interactive Textual install wizard (`tools/setup.py`) — install-picks
  screen + 2-D status-line layout board, fail-closed with no headless-defaults
  mode.
- ✓ Responsive status line (`tools/status-line.py`) — zero-dependency,
  stdlib-only renderer with configurable segments, ramps, and external
  drop-in segment providers; validated by `tools/statusline-doctor.py`.
- ✓ `ai-kit-spec-review` skill family (`ai-kit-spec-review`,
  `ai-kit-spec-review-checklist`, `ai-kit-spec-review-fixer`,
  `ai-kit-spec-config`) — framework-aware review-and-fix loop for specs/plans
  across superpowers, GSD, OpenSpec, Spec Kit, Kiro, BMAD.
- ✓ `ai-kit-spec-execute` / `ai-kit-spec-execute-gsd` — routes plan execution
  to the framework that generated it; resolves model/CLI for GSD phases
  without subprocess-dispatching GSD.
- ✓ Assorted utility skills — `commit-message`, `cst-refactor`,
  `mermaid-audit`, `markdown-to-pdf`.

- ✓ Multi-CLI runtime foundation — hardened installer fetch, runtime
  self-detection, opencode sidebar/status research — v1.0
- ✓ Opencode provider management — list/remove custom providers safely — v1.0
- ✓ Tool-substitution awareness hook — live-verified rtk briefing at session
  start — v1.0
- ✓ Config doctor — cross-runtime config diagnostics with confirmed apply — v1.0
- ✓ Usage metrics dashboard — local capture/refine/visualize of AI-CLI usage —
  v1.0, overhauled for scale and data correctness in v1.2 (Phase 15.1)
- ✓ AGENTS.md rules checker skill — v1.1, pruned to prose scope as
  `ai-kit-project-rules-agents` in v1.2
- ✓ Curated GSD config skill (`ai-kit-gsd-curated-config` v1) — v1.1
- ✓ Status-line quota-color refactor — burn-pace coloring — v1.1
- ✓ Project-rules checker family (makefile, precommit, arch, docker, cicd)
  plus the `ai-kit-project-rules-all` orchestrator — v1.2

### Active

<!-- v1.3 scope; checkable requirements live in REQUIREMENTS.md. -->

- [ ] `ai_kit_spec` host detection, enumeration and catalog/ranker extensions
- [ ] `ai-kit-gsd-curated-config` v2 — inventory/recommend/plan/apply pipeline,
      rigor × profile presets, cross-AI review/execution, skill affinity
- [ ] v2 evaluated on claude and live-validated on codex and opencode

### Out of Scope

<!-- Explicit boundaries surfaced by the 5 ingested PRDs' own Non-Goals /
     rejected-alternatives sections. -->

- Bulk "apply all" in config doctor — every apply is per-item and explicitly
  confirmed; a bulk default was considered and rejected as too risky for
  security-relevant settings.
- Folding config doctor into `tools/statusline-doctor.py` — different domain
  (that script validates the statusline renderer's own config, not runtime
  behavioral settings); kept as a dedicated screen instead.
- A SessionStart-equivalent hook for opencode — opencode has no documented
  injection point today; the gap is accepted and documented, not silently
  absent, pending upstream support.
- A hosted-database capability pointed at usage-metrics session content —
  session data must never leave the local machine; the dashboard is a
  pipeline-regenerated static HTML file with refined data embedded
  directly (no export/import step, no browser-sandboxed Artifact
  mechanism).
- Presenting opencode's "session retention" as a real, settable config value
  in config doctor — no such setting exists upstream; shown informational-only,
  never offered as an apply action.
- Real dependency-direction/layering enforcement in `ai-kit-project-rules-arch`
  — v1.2 scoped it to form/convention-only checks. It remains an explicitly
  flagged known gap (Backlog 999.3).

## Context

**Host facts (live-verified 2026-10-15):**
- gsd-core: 1.16.0
- GSD installs missing on: ~/.codex/gsd-core, ~/.config/opencode/gsd-core, ~/.cursor/gsd-core, ~/.pi/gsd-core
- ~/.gsd/defaults.json runtime: codex
- Artificial Analysis key: set
- Live catalog fetch scored: 150 of 195 entries

ai-kit is a solo-maintainer (uz) toolkit that started as a Claude-Code-only
installer + status line and grew a family of spec-review/execute skills.

**State after v1.2 (2026-09-23):**
- The unit suite has about 2535 tests.
- The only failing test is `TestRenderRealMmdc`, caused by an environment problem (an incomplete pnpm-global mermaid-cli install).
- Pyright reports 0 errors.
- Known debt: pre-v1.2 ruff/pylint findings in `tools/status-line.py`, `tools/wizard_app.py` and `tests/test_ai_kit_spec_superpowers.py`.
- No v1.2 phase has a Nyquist VALIDATION.md.

v1.0's scope came from 5 PRDs ingested from `docs/prds/` — all framed
by their authors as **proposals**, not yet-accepted decisions (no ADRs exist
in this repo for them). Ingest ran cross-reference cycle detection across the
5 PRDs; two prior runs found and the user resolved a 3-node then a residual
2-node cycle by removing named back-references, leaving a clean DAG (see
`.planning/INGEST-CONFLICTS.md` for the full trail). Three real
cross-PRD build dependencies survive the DAG and shape phase order below:
Config Doctor reuses Opencode Provider Management's atomic-write/surgical-edit
pattern and folds in a Non-Goals note from Tool-Substitution Awareness Hook;
Usage Metrics Dashboard mirrors Tool-Substitution Awareness Hook's curated
substitution list as its single source of truth for command-family tagging.

The shipped runtime code (`tools/status-line.py`) is deliberately
stdlib-only; `uv`/`textual` are dev/wizard-only and never required at render
time. All 5 proposal PRDs preserve this split — no new runtime dependency is
introduced without an explicit, justified exception.

## Constraints

- **Language discipline (non-negotiable)**: All documentation, planning
  artifacts, commit messages, code comments, and any other written project
  artifact are written in English only, regardless of what language the
  conversation with uz happens to be in. Never mix languages within a single
  document or file (no "Spanglish" — no English narration interleaved with
  verbatim quotes or headers in another language); translate quoted
  non-English input faithfully into English rather than leaving it verbatim.
  Conversing with uz in another language is fine — everything written to a
  file must be English.
- **Privacy**: Usage-metrics raw and refined data never leaves the local
  machine — no hosted database, no network calls from the capture/refine
  pipeline.
- **Config safety**: Every write to a runtime's config file (opencode.jsonc,
  Codex TOML, Claude JSON) is atomic (temp file + rename) and, for JSONC
  surgical edits, preserves every other byte of the file untouched.
- **Confidence labeling**: No diagnostic or detection result is presented
  with more certainty than its actual sourcing — community-reverse-engineered
  formats, informational-only settings, and inferred classifications must be
  visibly flagged as such, never shown at the same confidence as an
  officially documented behavior.
- **Skill-quality gate**: Any new or materially updated `SKILL.md` produced
  by this milestone's phases passes the `skill-judge` review loop (no
  remaining Critical/Important finding, or score ≥ 96/120, no regression vs.
  baseline) before being marked complete.
- **Runtime dependency discipline**: Shipped/runtime code stays stdlib-only
  (Python 3.11+ where TOML parsing is needed); `uv`/`textual`-class
  dependencies stay dev- or wizard-only, per existing project convention.

## Key Decisions

<!-- No ADR-type documents existed in this ingest set — nothing below is a
     locked decision. All 5 source PRDs are explicit proposals; this table
     tracks provisional scope-adoption only. -->

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Adopt all 5 ingested proposal PRDs as this milestone's roadmap scope | 0 blockers, 0 competing variants after cycle resolution (`.planning/intel/SYNTHESIS.md`); each PRD already defines its own measurable acceptance criteria | ✓ Good — all 5 shipped in v1.0 |
| Sequence Multi-CLI Runtime Foundation, Opencode Provider Management, and Tool-Substitution Awareness Hook ahead of Config Doctor and Usage Metrics Dashboard | Real cross-PRD reuse dependencies found during ingest (surgical-edit pattern, curated substitution list) — see Context | ✓ Good — reuse landed as planned |
| Split the AGENTS.md checker into a single-domain rules family sharing `ai_kit_rules_common` (v1.2) | One checker was accumulating Makefile, pre-commit and prose domains; a shared package prevents divergent copies | ✓ Good — 6 checkers plus an orchestrator, no divergent copies (v1.2 integration check) |
| Rate-limit coloring by burn pace, not remaining fraction (v1.1, Phase 8.1) | Phase 8's formula flagged early-window light usage as RED | Superseded 2026-10-09 by absolute gap coloring (`docs/superpowers/specs/2026-10-09-statusline-quota-window-gap-design.md`): the pace ratio treated low usage late in a window as healthy |
| Close milestones with a cleanup phase before archiving, not with accepted debt (v1.2, Phase 15.2) | The audit found in-milestone defects (pyright error, sort-key asymmetry) that were cheap to fix | ✓ Good — closed at pyright 0 errors |
| Track `.planning/` in git from 2026-09-16 | Earlier milestones lost their start-date history | ⚠️ Revisit — v1.0 dates are only partially recoverable |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-09-23 after starting milestone v1.3*
