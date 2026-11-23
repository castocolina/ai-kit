---
gsd_state_version: "1.0"
milestone: v2.0
milestone_name: Skill Refactor
current_phase: 35
current_phase_name: Model discovery and catalog
status: verifying
stopped_at: Phase 39 complete, ready to verify Phase 35
last_updated: "2026-11-23T20:32:09.169Z"
last_activity: 2026-11-23
last_activity_desc: Phase 39 complete, transitioned to Phase 35
state_head: 979fff733f6658684e0636bc151c804c102fe8f9
progress:
  total_phases: 41
  completed_phases: 17
  total_plans: 267
  completed_plans: 267
  percent: 41
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-11-02)

**Core value:** ai-kit must never corrupt uz's AI-CLI configuration and must never claim more certainty than it has
**Current focus:** Phase 35 — Model discovery and catalog

## Current Position

Phase: 35 — Model discovery and catalog
Plan: 28
Status: Phase complete — ready for verification
Last activity: 2026-11-23 — Phase 39 complete, transitioned to Phase 35

Progress: [████░░░░░░] 41%

## Performance Metrics

**Velocity:**

- Total plans completed: 200
- Average duration: ~36 min
- Total execution time: ~1h 59min

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1.1 Autonomous-Run Infrastructure | 1 | ~50min | ~50min |
| 1.2 Multi-CLI Runtime Foundation | 4 | - | - |
| 2 Opencode Provider Management | 2 | - | - |
| 3 Tool-Substitution Awareness Hook | 2 | - | - |
| 4 Config Doctor | 3 | - | - |
| 5 Usage Metrics Dashboard | 6 | - | - |
| 6 AGENTS.md Rules Checker Skill | 0 | - | - |
| 7 Curated GSD Config Skill | 0 | - | - |
| 8 Status-line Quota Color Refactor | 0 | - | - |
| 9 AGENTS.md Checker Prune | 0 | - | - |
| 10 Makefile Rules Checker | 0 | - | - |
| 11 Pre-commit Rules Checker | 0 | - | - |
| 12 Architecture Rules Checker | 0 | - | - |
| 13 Docker Rules Checker | 0 | - | - |
| 14 CI/CD Rules Checker | 0 | - | - |
| 15 Rules Orchestrator | 0 | - | - |
| 8.1 | 1 | - | - |
| 15.1 | 5 | - | - |
| 16.1 | 31 | - | - |
| 18.1 | 22 | - | - |
| 29.1 | 6 | - | - |
| 30.1 | 6 | - | - |
| 30.2 | 5 | - | - |
| 32.1 | 9 | - | - |
| 32.2 | 5 | - | - |
| 32.3 | 5 | - | - |
| 32.4 | 9 | - | - |
| 32.5 | 10 | - | - |
| 33 | 12 | - | - |
| 34 | 10 | - | - |
| 38 | 27 | - | - |
| 39 | 19 | - | - |

**Recent Trend:**

- Last 5 plans: 05-06, 05-05, 05-04, 05-03, 05-02 (v1.0 close-out)
- Trend: v1.0/v1.1/v1.2 complete; v1.3 roadmap created, no plans executed yet

*Updated after each plan completion*
**Per-Plan Metrics:**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| *Archived 2026-11-22 (phase 38 close): the per-plan rows are in STATE-ARCHIVE.md* | - | - | - |
| Phase 38.1 P01 | 12min | 2 tasks | 8 files |
| Phase 38.1 P02 | 10min | 2 tasks | 3 files |
| Phase 38.1 P03 | 16min | 3 tasks | 10 files |
| Phase 38.1 P04 | 16min | 3 tasks | 4 files |
| Phase 38.1 P05 | 22min | 3 tasks | 13 files |
| Phase 38.1 P06 | 36min | 3 tasks | 6 files |
| Phase 38.1 P07 | 8min | 2 tasks | 2 files |
| Phase 38.1 P08 | 16min | 2 tasks | 3 files |
| Phase 38.1 P09 | 17min | 3 tasks | 7 files |
| Phase 38.1 P10 | 9min | 2 tasks | 4 files |
| Phase 38.1 P11 | 12min | 3 tasks | 9 files |
| Phase 38.1 P12 | 25min | 3 tasks | 19 files |
| Phase 38.1 P13 | 35min | 2 tasks | 10 files |
| Phase 38.1 P14 | 25min | 2 tasks | 0 files |
| Phase 39 P01 | 15min | 3 tasks | 5 files |
| Phase 39 P02 | 15min | 3 tasks | 5 files |
| Phase 39 P03 | 15min | 2 tasks | 5 files |
| Phase 39 P04 | 17min | 3 tasks | 3 files |
| Phase 39 P05 | 12min | 2 tasks | 2 files |
| Phase 39 P07 | 13min | 2 tasks | 4 files |
| Phase 39 P08 | 18min | 3 tasks | 6 files |
| Phase 39 P09 | 16min | 3 tasks | 5 files |
| Phase 39 P06 | 20min | 3 tasks | 2 files |
| Phase 39 P10 | 18min | 2 tasks | 4 files |
| Phase 39 P11 | 22min | 3 tasks | 4 files |
| Phase 39 P12 | 32min | 3 tasks | 13 files |
| Phase 39 P13 | 14min | 3 tasks | 10 files |
| Phase 39 P14 | 17min | 3 tasks | 5 files |
| Phase 39 P15 | 15min | 2 tasks | 6 files |
| Phase 39 P16 | 15min | 2 tasks | 8 files |
| Phase 39 P17 | 36min | 3 tasks | 19 files |
| Phase 39 P18 | 70min | 2 tasks | 30 files |
| Phase 39 P19 | 60min | 2 tasks | 4 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.

- v1.0: All 5 ingested proposal PRDs (Phases 1.1-5) shipped 2026-09-09/10; no
  ADR locks any of them — roadmap approval was the acceptance step.
- v1.1: Phase numbering continues from v1.0's last phase (Phase 6 starts
  right after Phase 5) rather than resetting to 1, per `ROADMAP.md`'s Phase
  Numbering convention (2026-09-10).
- v1.1: Phases 6-8 map 1:1 to the 3 pending todos that seeded this
  milestone's scope (AGENTS.md checker, curated config skill, status-line
  color refactor) — no additional phases created, none merged, since each
  already forms a coherent, independently-deliverable unit.
  a fetch-behavior bugfix: --depth 1 already implies --single-branch per
  git-scm.com/docs/git-clone unless --no-single-branch is given.
  after a live user report that Phase 8's `util_rate_burn_ratio` formula
  (`pct / remaining_fraction`) rendered low usage well into a rate-limit
  window as an urgency color (25% used, half the window elapsed, read
  YELLOW/orange). Reverses the formula to `pct / elapsed_fraction` (a pace
  signal) per the user's explicit, live-confirmed direction choice — see
  `08.1-CONTEXT.md` for the full decision and why it reopens Phase 8's own
  "Formula Direction — Resolved" call. Independent of the v1.2 chain; a
  starting diff already exists on branch `fix/8.1-status-line-rate-burn-pace`
  (commit `fc2d8bb`), 302/302 tests passing, not yet merged to main.
- v1.2: Phase numbering continues from v1.1's last phase (Phase 9 starts
  right after Phase 8), per ROADMAP.md's Phase Numbering convention
  (2026-09-13).
- v1.2: Phases 9-15 map 1:1 to this milestone's 7 requirements (one new or
  modified skill each) and form a strict dependency chain — agents-prune ->
  makefile -> precommit -> arch -> docker -> cicd -> all — unlike v1.1's
  mutually-independent Phases 6-8. Each domain checker builds on the
  shared-package conventions and dropped-logic ownership the prior phase
  established, and the orchestrator (Phase 15) needs all 5 domain checkers
  plus the Phase 9-pruned agents checker to exist before it can aggregate
  them.
- v1.2: Phase 12 (`ai-kit-project-rules-arch`) promotes and resolves
  ROADMAP.md's former backlog entry "999.3: Architecture-layer test suite
  (BACKLOG)" at this milestone's scoped-down, form/convention-only ambition
  (arch-test Makefile target existence/chaining/AST-only verification) — NOT
  the backlog note's full dependency-direction/layering-boundary enforcement
  ambition, which stays an explicitly-flagged known gap per the design spec.
  The backlog stub itself is left unchanged in ROADMAP.md (a dated note was
  appended after it pointing to Phase 12); this is its resolution, not a
  duplicate.
- v1.3: Phase numbering continues from v1.2's last phase (Phase 15.2) — v1.3
  starts at Phase 16, per ROADMAP.md's Phase Numbering convention
  (2026-09-23). Roadmap derived from this milestone's 31 requirements
  (SPEC/INV/REC/XAI/SKL/APP/EVAL prefixes — REQUIREMENTS.md's earlier "29
  total" placeholder was a stale pre-roadmap estimate, corrected to the
  actual count during roadmap creation) into 7 phases (16-22), following the
  source spec's §10 delivery-phase split. Phase 17 (originally one
  "curated-config rewrite" phase per the spec) was split into Phase 17
  (inventory + recommend) and Phase 18 (cross-AI + skills + apply) because
  the combined scope (18 requirements) was too large for one phase; EVAL-06
  (removed-module cleanup, make test/validate green, README/SKILL.md
  updates) was grouped into Phase 18 rather than Phase 17 since it is the
  natural finish line for the whole rewrite, not just the inventory/recommend
  half. Cursor (Phase 21) and pi (Phase 22) live-validation stay their own
  standalone phases, each depending only on Phase 19 (not on each other or
  on Phase 20), per the spec's explicit "own phase, may run later, nothing
  depends on it" framing for both hosts.

### Pending Todos

- [2026-10-11] [skills] Execute the System One decision-skill plan (jev-fast-decision, 3 backends) — [todo file](.planning/todos/pending/2026-10-11-execute-system-one-decision-skill-plan.md)
- [2026-10-13] [agents] Add Cursor subagents pinned to non-fast composer-2.5 and grok — [todo file](.planning/todos/pending/2026-10-13-add-cursor-subagents-pinned-to-non-fast-composer-2-5-and-grok.md)
- [2026-10-14] [tooling] AGENTS.md quota-schedule rules and one-shot goal-prompt skill — [todo file](.planning/todos/pending/2026-10-14-agents-md-quota-schedule-rules-and-goal-prompt-skill.md)
- [2026-10-14] [skills] Wire jev-fast-decision cross-host discovery scaffolding — [todo file](.planning/todos/pending/2026-10-14-wire-jev-fast-decision-cross-host-discovery-scaffolding.md)
- [2026-10-18] [tooling] PreCompact hook pre-summarizes transcript chunks via the decision system — [todo file](.planning/todos/pending/2026-10-18-precompact-hook-pre-summarizes-chunks-via-decision-system.md)
- [2026-10-18] [tooling] Visible tool-advisory hooks (SessionStart, PreToolUse, PostToolUse) as setup knobs — [todo file](.planning/todos/pending/2026-10-18-visible-tool-advisory-hooks-pre-and-post-tool-use.md)
- [2026-10-24] [tooling] Make the ai-kit session hooks dynamic (worktree indexing advice, install-relative docs, compact metr… — [todo file](.planning/todos/pending/2026-10-24-make-the-ai-kit-session-hooks-dynamic-worktree-indexing-advi.md)
- [2026-10-30] [tooling] Unify the review/execute lane TOML, add effort and escalation, classify with jev — [todo file](.planning/todos/pending/2026-10-29-unify-review-execute-lane-toml-effort-escalation-and-jev-classification.md)
- [2026-10-31] [skills] Refactor execute-gsd and rules-agents (SJ-1, SJ-3) — [todo file](.planning/todos/pending/2026-10-31-refactor-execute-gsd-and-rules-agents-sj-1-sj-3.md)
- [2026-11-02] [verification] Pending live checks and owner decisions from v1.3 — [todo file](.planning/todos/pending/2026-11-02-pending-live-checks-and-owner-decisions-from-v1.3.md) — Needs ### Group 1: live checks still to do.
- [2026-11-02] [tooling] Tooling defects and skill-writing principle found at the v1.3 close-out — [todo file](.planning/todos/pending/2026-11-02-tooling-defects-and-skill-writing-principle-found-at-the-v1.md)
- [2026-11-06] [tooling] Low-risk review and judge notes left open by phases 28-31 — [todo file](.planning/todos/pending/2026-11-06-low-risk-review-and-judge-notes-from-phases-28-31.md)
- [2026-11-08] [tooling] Review notes left open by phase 32.1 — [todo file](.planning/todos/pending/2026-11-08-review-notes-left-open-by-phase-32-1.md)
- [2026-11-16] [runner] opencode free models, classification of the research findings and the checks still open — [todo file](.planning/todos/pending/2026-11-16-opencode-free-models-open-checks.md)
- [2026-11-16] [skills] spec-config wizard owner observations (catalog first, short choice, only chosen lanes written) — [todo file](.planning/todos/pending/2026-11-16-spec-config-wizard-owner-observations.md)
- [2026-11-17] [tooling] Wizard step for a component registry, cross-host install, self-update and scheduled updates — [todo file](.planning/todos/pending/2026-11-17-wizard-step-for-a-component-registry-cross-host-install-self.md)
- [2026-11-19] [tooling] Scan git projects and auto-update their project-local open-GSD install on a schedule — [todo file](.planning/todos/pending/2026-11-19-scan-git-projects-and-auto-update-project-local-open-gsd.md)
- [2026-11-20] [planning] Grok is not a cross-AI target: amend the 36, 37 and 38.1 specs and keep the grok code until Phase 39.1 — [todo file](.planning/todos/pending/2026-11-20-grok-is-not-a-cross-ai-target-amend-the-36-37-38-1-specs.md)
- [2026-11-20] [tooling] Keep every run ledger and resume state in a gitignored tmp folder inside the project — [todo file](.planning/todos/pending/2026-11-20-run-ledger-and-resume-state-in-gitignored-tmp.md)
- [2026-11-20] [tooling] Hand skills and MCP servers to cross-AI review and execute lanes by name, path or prose — [todo file](.planning/todos/pending/2026-11-20-skills-and-mcp-servers-for-cross-ai-lanes.md)

### Blockers/Concerns

*Archived 2026-11-22 (phase 38 close): the concerns history is in STATE-ARCHIVE.md.*

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 261102-qrx | spec-discuss interactive path runs discuss with --analyze --all --batch | 2026-11-02 | 8e1bef6 | [261102-qrx-spec-discuss-interactive-path-runs-discu](./quick/261102-qrx-spec-discuss-interactive-path-runs-discu/) |
| 261104-cxr | split cross-ai runner e2e self-test into logic and runtime shards | 2026-11-04 | 5109f80 | [261104-cxr-split-cross-ai-runner-e2e-self-test-into](./quick/261104-cxr-split-cross-ai-runner-e2e-self-test-into/) |
| 261104-hzc | Apply test-time audit cuts 1-13 and the data-file mapper change | 2026-11-04 | 429bc0d | [261104-hzc-apply-test-time-audit-cuts-1-13-and-the-](./quick/261104-hzc-apply-test-time-audit-cuts-1-13-and-the-/) |
| 261106-n8k | close the open items left by the phase 28-31 run | 2026-11-06 | 320aafc..4c68491 | [261106-n8k-close-the-open-items-left-by-the-phase-2](./quick/261106-n8k-close-the-open-items-left-by-the-phase-2/) |
| 261106-tdq | wizard Choose shows one card per component kind, walked with Enter; header Step i of N | 2026-11-06 | 2acf64f | [261106-tdq-wizard-choose-one-card-per-kind-advanced](./quick/261106-tdq-wizard-choose-one-card-per-kind-advanced/) |
| 261106-tox | wizard help line lists every key from one table, same on both host panes, grouped when tall | 2026-11-06 | bd44cef | [261106-tox-wizard-help-line-lists-every-key-from-on](./quick/261106-tox-wizard-help-line-lists-every-key-from-on/) |
| 261106-tzg | wizard drops the Cursor spend-limit override; the alert fires at the limit read from Cursor | 2026-11-06 | 8e23e75 | [261106-tzg-wizard-drops-the-cursor-spend-limit-over](./quick/261106-tzg-wizard-drops-the-cursor-spend-limit-over/) |
| 261106-ua8 | wizard Choose shows frontmatter names and descriptions; three skills' descriptions made strict YAML | 2026-11-06 | a9f6b67 | [261106-ua8-wizard-component-names-and-descriptions-](./quick/261106-ua8-wizard-component-names-and-descriptions-/) |

### Roadmap Evolution

- Phase 15.1 inserted after Phase 15: Usage Metrics Dashboard UX/Perf Overhaul — 14 UX/perf/bug findings from live dashboard.html review (empty date col, family showing garbage tokens, session-group row dup, no pagination/virtualization causing browser freeze, filter bar unordered, missing runtime column, no launch detection, price always 0, no charts, no MUI styling) (URGENT)
- Phase 15.2 inserted after Phase 15: v1.2 tech debt cleanup from milestone audit (pyright typing, 15.1 WR-01/WR-02, 15.1 lint, resolved todos) (URGENT)
- v1.3 roadmap created 2026-09-23: Phases 16-22 derived from 31 v1.3
  requirements per the approved source spec's §10 delivery-phase split
  (Phase 17 split into 17/18 for size; cursor/pi kept as separate tail
  phases per the spec).
- Phase 16.1 inserted after Phase 16: Hardening: gate scope, sibling-first imports, security/correctness fixes from the 2026-10-13 audit; closes Phase 16
- Phase 18.1 inserted after Phase 18: One runtime model: (runtime, model) candidates, native_runtime removed
- Phase 24 added after Phase 23: Spec-and-discuss chain skill (learned from the tools-installer run, 2026-10-14)
- Phase 21.1 inserted after Phase 21: Cursor project-level subagent linking (AGT-02; D-01 spike: cursor CLI ignores ~/.cursor/agents)
- Phase 21.1 moved to backlog 999.7 (2026-10-18, owner decision: cursor is a secondary runtime; Phase 21 documents manual per-file linking)
- Phase 21.1 inserted after Phase 21: Atomic reusable decision-system skills (DEC-01..03); from the 2026-10-18 todos, owner-prioritized ahead of 22/23
- Phase 21.2 inserted after Phase 21: PreCompact pre-summary hook via the decision system (PCH-01..02); from the 2026-10-18 todos, owner-prioritized ahead of 22/23
- Phase 21.3 inserted after Phase 21: Visible tool-advisory hooks as setup knobs (ADV-01..04); from the 2026-10-18 todos, owner-prioritized ahead of 22/23
- Phase 25.1 inserted after Phase 25: Configurable soft backoff, session-reset ladder, upstream error pass-through and an evidence-based error catalog (owner request 2026-10-24)
- v2.0 roadmap created 2026-11-02: Phases 28-54 (31 phases, decimal 32.1-32.4 are the skill batches after
  the re-judge baseline) from 96 v2.0 requirements; order follows the owner's constraints in the
  milestone inputs (gates and flow first, removals before the baseline, rules before dist, hooks after
  playbooks, wake after the shared quota decision).
- Phase 47.2 inserted after Phase 47.1: Goal-prompt learns rails from sessions: proposes learned rails from the current and previous session, deduplicated against AGENTS.md and the generated block (owner request 2026-11-16)

## Deferred Verification

| Phase | State | Resume |
|-------|-------|--------|
| 24 | human_needed (6/9 truths verified, 0 failed; code review fixed; skill-judge PASS r3 at 7fc3f03f with Opus 108 / my-referee-one 101 / my-referee-two 109; Nyquist partial; gates green incl. e2e-docker; shipped to main b686c7a; 2026-10-24) | owner runs the three behavior checks in 24-VERIFICATION.md (full chain on a fixture project, a no-backend run, the ledger and stop rule), ideally once in each run mode (`--auto` and interactive); polish in backlog 999.11; then `/gsd-verify-work 24` |
| 23 | human_needed (STL-01/02/05 complete, 0 gaps; security 57/58 + AR-23-04, Nyquist compliant; six gates green incl. e2e-docker; live check from the branch passed; 2026-10-24) | owner runs the 23-SPIKE.md kit S1-S7 (real Cursor login: payload capture, Dashboard responses, latency, debounce, token lifetime, included_usage_period, R12 live run), then `live/spike_check.py --record` and `--promote`; STL-03's real-response clause and STL-04 wait on it; owner decides D-12 (delete the POC credential .bak); then `/gsd-verify-work 23` |
| 22 | human_needed (automated part complete, 0 gaps; security 22/22, Nyquist 7/7; 2026-10-23) | owner runs `22-INTERACTIVE-PI.md` (C1 real RPC capture, S1-S5 interactive smoke, D9; L3a-L3c optional), then its `## Orchestrator close-out`; `live/check_pi_live.py` gates the label lift; until then the pi label stays `not live-validated` and the verdict `session-steer (static + mock evidence)`; EVAL-08 stays Pending; then `/gsd-verify-work 22` |
| 21.3 | human_needed (ADV-01..03 automatable criteria pass, 0 gaps; 2026-10-23) | owner runs the 21.3-LIVE.md matrix (L-C1..8 Claude Code, L-P1..4 pi) and the S-OC opencode spike (`opencode --standalone`) in a scratch HOME with an interactive login; `live/check_live.py 21.3-LIVE.md` must exit 0 (an S-OC pass needs a `/gsd-plan-phase 21.3 --gaps` opencode adapter plan first); then `/gsd-verify-work 21.3` |
| 21.2 | human_needed (automatable criteria pass, 0 gaps; 2026-10-23; S2 run headless on the machine install 2026-10-23, three live defects fixed in 9bcfb04/ea455dc, see 21.2-SPIKE.md S2) | owner runs live checks S3-S5 and the R9 measurements in a scratch HOME (interactive host login), then the 21.2-MEASUREMENTS.md close-out (`verdict.py`, `PRECOMPACT_VERDICTS`, ROADMAP/REQUIREMENTS amendments); until then every precompact row is `unmeasured` and default off; then `/gsd-verify-work 21.2` |
| 21.1 | human_needed (4/4 roadmap criteria, 0 gaps; 2026-10-23) | owner decides LIVE 6 (Laya accuracy_when_not_fallback 0.5 < 0.95, no calibrated winner) and the skill-judge UNRESOLVED (opencode lane: jev D8 11/15 + 2 Important, spec-discuss 1 Important; both clean-Opus rows pass); live TypeSafe/Zen checks need key + consent + budget; reinstall the global copy with `python3 tools/setup.py install --headless --skills jev-fast-decision --replace-existing`; then `/gsd-verify-work 21.1` |
| 21 | human_needed (5/5 roadmap criteria, 0 gaps; 2026-10-19) | uz runs `21-INTERACTIVE-CURSOR.md` steps 1-4; owner decides the skill-judge UNRESOLVED (pi 114 vs 116 baseline) after the pending re-judge on digest f0c43a5da52a587d; then `/gsd-verify-work 21` |
| 20 | human_needed (8/9 automated truths, 0 gaps; 2026-10-18) | uz runs `20-INTERACTIVE-OPENCODE.md`, then `/gsd-verify-work 20`; EVAL-05 stays Pending until then. The codex TUI run (EVAL-04) is deferred to backlog 999.6 (codex is a secondary runtime) |

Phase 16: 4/4 success criteria verified 2026-10-14; the one human item (real codex/pi host signal) is scheduled for Phases 20 and 22.

## Deferred Items

*Archived 2026-11-22 (phase 38 close): the milestone-close deferred items are in STATE-ARCHIVE.md.*

## Session Continuity

Last session: 2026-11-23T18:50:36.822Z
Stopped at: Phase 39 complete, ready to verify Phase 35
Resume file: None

## Operator Next Steps

- Spec and discuss phases 28-32 (`/gsd-spec-phase`, `/gsd-discuss-phase`), then `/gsd-autonomous`
