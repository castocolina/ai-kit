# ai-kit

## What This Is

Personal agent skills, slash commands, and a one-line installer, built and
maintained by uz. Skills follow the open [Agent Skills](https://agentskills.io)
standard, so beyond Claude Code they also load unmodified in any conformant
tool (opencode, Codex CLI, Gemini CLI, Cursor, Copilot CLI, Kiro, and others).
The project is now deliberately widening from "a Claude Code installer with
some skills" toward genuine multi-CLI support — runtime detection, opencode
provider management, and cross-runtime config diagnostics are all in active
proposal.

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

### Active

<!-- Current milestone scope: 5 ingested proposal PRDs. Detailed, checkable
     requirements live in REQUIREMENTS.md; this is the feature-level summary. -->

- [ ] Multi-CLI runtime foundation — hardened installer fetch, runtime
      self-detection, opencode sidebar/status research
- [ ] Opencode provider management — list/remove custom providers safely
- [ ] Tool-substitution awareness hook — live-verified rtk briefing at
      session start
- [ ] Config doctor — cross-runtime config diagnostics with confirmed apply
- [ ] Usage metrics dashboard — local capture/refine/visualize of AI-CLI
      usage

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
- A hosted-database capability behind the usage-metrics dashboard Artifact —
  session data must never leave the local machine; the dashboard reads a
  local export only.
- Presenting opencode's "session retention" as a real, settable config value
  in config doctor — no such setting exists upstream; shown informational-only,
  never offered as an apply action.

## Context

ai-kit is a solo-maintainer (uz) toolkit that started as a Claude-Code-only
installer + status line and grew a family of spec-review/execute skills. This
milestone's scope comes from 5 PRDs ingested from `docs/prds/` — all framed
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
| Adopt all 5 ingested proposal PRDs as this milestone's roadmap scope | 0 blockers, 0 competing variants after cycle resolution (`.planning/intel/SYNTHESIS.md`); each PRD already defines its own measurable acceptance criteria | — Pending (roadmap approval is the acceptance step; no PRD is ADR-locked) |
| Sequence Multi-CLI Runtime Foundation, Opencode Provider Management, and Tool-Substitution Awareness Hook ahead of Config Doctor and Usage Metrics Dashboard | Real cross-PRD reuse dependencies found during ingest (surgical-edit pattern, curated substitution list) — see Context | — Pending |

---
*Last updated: 2026-09-07 after initial ingest of 5 proposal PRDs*
