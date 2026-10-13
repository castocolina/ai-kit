# Roadmap: ai-kit

## Milestones

- ✅ **v1.0 Multi-CLI Foundation & Config Safety** — Phases 1.1–5 (shipped 2026-09-10)
- ✅ **v1.1 Agent Workflow Hygiene & Tooling Polish** — Phases 6–8.1 (shipped 2026-09-13)
- ✅ **v1.2 ai-kit Rules Skill Family** — Phases 9–15.2 (shipped 2026-09-23)

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
implementation. Coordinate with `worktree-context-tools-manager-plan1`
(adds a wizard Step 0 on the same seams) and v1.3 Phase 23 C2 (per-host
status-line step). Candidate rows to add later: the Playwright MCP Chrome path
on Bazzite. Rewritten 2026-10-13 from the former "shared core for a CLI
variant" note, whose goal (engine not coupled to the TUI) is already met.
**Requirements:** TBD
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

**Moved 2026-10-13:** the host-split status line (former 999.4) was promoted to
v1.3 Phase 23 on branch `gsd/v1.3-curated-config-v2`; former 999.3 was removed
(resolved by v1.2 Phase 12; see git history).
