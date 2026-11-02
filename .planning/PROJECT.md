# ai-kit

## What This Is

Personal agent skills, slash commands, and a one-line installer, built and
maintained by uz. Skills follow the open [Agent Skills](https://agentskills.io)
standard, so beyond Claude Code they also load unmodified in any conformant
tool (opencode, Codex CLI, Gemini CLI, Cursor, Copilot CLI, Kiro, and others).
It has widened from "a Claude Code installer with some skills" into a
multi-CLI toolkit. It ships runtime detection, opencode provider management,
cross-runtime config diagnostics, a local usage-metrics dashboard, a family
of project-rules checker skills, and (since v1.3) a host-aware curated GSD
config wizard with a quota-aware cross-AI runner, a decision-system client, a
session-wake skill and a goal-prompt skill. Claude, opencode and pi are the
primary hosts; codex and cursor are secondary.

## Current State

**Shipped:** v1.3 GSD Curated Config v2 (2026-10-31), closed with
`override_closeout`: automated evidence is complete, but many live, interactive
and owner steps are carried to the owner, not done. v1.2 ai-kit Rules Skill
Family shipped 2026-09-23; v1.0 and v1.1 were archived retroactively during that
close. See `.planning/MILESTONES.md` (the v1.3 entry lists every carried item).
Phase history lives in `.planning/milestones/v1.{0,1,2,3}-phases/`; `.planning/phases/` holds only the backlog directories (999.x).

The rules-checker family (`ai-kit-project-rules-{agents,makefile,precommit,arch,docker,cicd}`
plus the `ai-kit-project-rules-all` orchestrator) shares
`skills/_shared/ai_kit_rules_common/`. The usage-metrics dashboard handles the
real ~85k-row refined store without freezing. The curated-config pipeline
(inventory, recommend, plan, apply) resolves one (runtime, model) pair per role
and renders a cross-AI runner (template 8) that runs one CLI per call under a
configurable retry ladder.

## Current Milestone: v2.0 Skill Refactor

**Goal:** Turn ai-kit's skills into a smaller, re-judged and portable set: shared config, resilient review and
execute loops, one project-rules skill of event playbooks, and installs from a committed `dist/`; every phase
ends with something the owner can see.

**Target features:**
- Fast, trustworthy gates first: changed-file tests at pre-commit, full suite at pre-push, no test calling a
  real host binary; commits compacted by logical feature (jev proposes the grouping), push per finished plan.
- Remove `ai-kit-spec-execute-gsd`, `ai-kit-opencode-providers` and `mermaid-audit`.
- Re-judge every skill with the new judge, then batch phases that improve groups of skills, each with
  new-shape evals and tests.
- One config design for every skill that keeps settings, replacing `review-spec.toml` with migration.
- `ai-kit-spec-config` as the hub: discovery on every host, a model catalog with tiers, capabilities and
  usability, separate reviewers and executors with opt-in escalation.
- Resilient review and execute loops with jev, lens skills and capability blocks; code review after
  implementation in the superpowers adapter; one shared runner with session ids and jev-sized review lanes.
- `ai-kit-project-rules`: one skill of event playbooks plus kept check scripts, AGENTS.md only, vertical
  slices, host hooks in setup, and the 5-hour quota wake grid.
- curated-config fixes, `dist/` with `npx skills` setup per host, orphaned scripts, rtk removal, a shared
  secret scanner, Laya calibration.

Input: `.planning/milestones/NEXT-MILESTONE-INPUTS.md` (rounds 1-9 and "Decisions by skill") and the research
in `.planning/research/2026-11-02-next-milestone/`.

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
- ✓ Responsive status line (`tools/claude-status-line.py`, host-split in v1.3 Phase 23 with a Cursor CLI twin `tools/cursor-status-line.py`) — zero-dependency,
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

- ✓ `ai_kit_spec` host detection, enumeration and catalog/ranker extensions;
  `ai-kit-gsd-curated-config` v2 (inventory, recommend, plan, apply; rigor ×
  profile presets; cross-AI review and execution; skill affinity); evaluated on
  claude; headless-validated on codex, opencode, cursor and pi — v1.3
- ✓ Host-split status line (Claude and Cursor CLI) with AST architecture guards
  — v1.3
- ✓ Quota-aware cross-AI runner, retry ladder and upstream error pass-through;
  `ai-kit-cross-ai`, `ai-kit-session-wake`, `ai-kit-gsd-spec-discuss`,
  `ai-kit-spec-goal-prompt`, `jev-fast-decision` — v1.3 (script-level; live
  steps below)

### Active

Milestone v2.0 (checkable requirements in `.planning/REQUIREMENTS.md`):

- [ ] Fast gates, logical-feature commit compaction and push per finished plan
- [ ] Three skills removed; every kept skill re-judged by the new judge with evals and tests
- [ ] One config design for all skills; spec-config as the hub with the model catalog
- [ ] Resilient review and execute loops, code review after execution, one shared runner
- [ ] One `ai-kit-project-rules` skill of event playbooks, host hooks in setup, the 5-hour quota grid
- [ ] curated-config fixes, `dist/` with `npx skills` setup, cleanups

Carried to the owner at the v1.3 close (checkable rows in `milestones/v1.3-REQUIREMENTS.md`; open checks in
the 2026-11-02 live-checks todo):

- [ ] Owner capture files for phases 25, 25.1, 26 and 27, and the interactive or
      live runs for phases 20-23 (EVAL-05/07/08, ADV-04, PCH-01/02, STL-03/04)
- [ ] Phase 24 chain dry run on a fixture project (SDC-01..04 are script-level only)
- [ ] Deferred skill-judge verdicts: `ai-kit-spec-goal-prompt` and
      `ai-kit-spec-config` UNRESOLVED; SJ-1, SJ-2, SJ-3 (refactor todo, backlog 999.16)
- [ ] `.planning/WINDOWS.md` entry 7 (autonomous block primitive) design decision
- [ ] EVAL-04 (backlog 999.6) and AGT-02 (backlog 999.7), deferred as secondary-runtime work

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

**State after v1.3 (2026-10-31):**
- v1.3 changed 428 files outside `.planning/` (about +149k/-18k lines) over 18 phases and 212 plans.
- All 18 phases have a VALIDATION.md; 4 are partial (16.1, 19, 21.1, 24), none missing.
- Verification: 6 phases `passed`, 11 `human_needed`, Phase 25 `gaps_found`; several read `stale` after later phases touched covered files.
- Known debt: runner-capable runtime lists are hand-copied with no drift test against the `RUNTIMES` table; AGENTS.md links the gitignored `.claude/cli-environment.md`.

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

The shipped runtime code (the `tools/claude-status-line.py` / `tools/cursor-status-line.py` entries and their `common_*`/`claude_*`/`cursor_*` modules) is deliberately
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
  remaining critical or high finding, or grade B or better on the rubric's
  percent bands, no regression beyond judge variation) before being marked
  complete. Only the current judge's verdicts count; old /120 scores are history.
- **Platforms**: Windows is out of scope (owner, 2026-11-02).
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
| One runtime model: candidates are (runtime, model) pairs; native versus subprocess is decided per call and never stored (v1.3, Phase 18.1) | One vocabulary for hosts, ranker and runner | ✓ Good — shipped, carried through phases 20-27 |
| Claude, opencode and pi are primary hosts; codex and cursor are secondary (owner, 2026-10-18) | Limits live-validation cost; codex and cursor models stay usable as reviewers and executors | — Pending: codex TUI (999.6) and cursor subagent linking (999.7) stay in the backlog |
| The cross-AI runner spawns one CLI per call and never switches harness, provider or model on its own (v1.3, Phases 25 and 25.1) | Failures are classified and reported; recovery is a retry ladder, not a silent fallback | — Pending: live router and copilot captures are owner items (25 and 25.1 OWNER-CAPTURES) |
| `jev-fast-decision` is an advisory black box, never a gate (v1.3, Phases 21.1 and 24) | A cheap judgment must not be trusted beyond its sourcing | — Pending: live TypeSafe and Zen calls and the Laya accuracy floor are owner decisions |
| Close v1.3 with `override_closeout` and carry owner items by name (2026-10-31) | The audit found no code gap; the open items need live hosts or owner decisions | ⚠️ Revisit — 24 audit items stay open until the owner works through them |
| Best implementation beats the easy one; MVP only shifts weight to simplicity; decide with jev when present (owner, 2026-11-02) | A rule for every skill, homed in the generated AGENTS.md top rules | — Pending: v2.0 rules skill |
| AGENTS.md and AGENTS.local.md are the only instruction files; CLAUDE.md is migrated away (owner, 2026-11-02) | Every primary host reads AGENTS.md; one file avoids drift | — Pending: v2.0 rules skill |
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
*Last updated: 2026-11-02 at the start of milestone v2.0*
