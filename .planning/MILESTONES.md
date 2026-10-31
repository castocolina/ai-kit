# Milestones

## v1.3 GSD Curated Config v2 (Shipped: 2026-10-31)

**Phases completed:** 18 phases (16, 16.1, 17, 18, 18.1, 19, 20, 21, 21.1-21.3, 22-27, plus inserted 25.1), 212 plans, 230 tasks
**Timeline:** 2026-09-23 → 2026-10-31
**Closeout type:** override_closeout (6 phases verified `passed`, 11 `human_needed`, Phase 25 `gaps_found`; most read `stale` after later phases touched covered files)
**Audit:** `milestones/v1.3-MILESTONE-AUDIT.md` — tech_debt, requirements 65/80 satisfied (13 owner-pending, 2 deferred to backlog, 0 unsatisfied), gaps INT-1..3 closed
**Archive:** `milestones/v1.3-ROADMAP.md`, `milestones/v1.3-REQUIREMENTS.md`. The v1.3 phase directories stay in `.planning/phases/` (not moved to `milestones/v1.3-phases/`): the owner kits and several tests (`tests/test_pi_live_tools.py`, `tests/test_tool_advisor_core.py`) read files in them, and the carried owner items below live there.

**Key accomplishments:**

- Curated-config v2 (16-19): cross-AI skills and apply pipeline, one-runtime model, inventory and recommendation engine, evaluation on Claude.
- Live validation per host (20-22): codex and opencode headless, cursor, pi. Codex and cursor are secondary; the labels read "validated headless ... interactive confirmation pending".
- Decision-system skills (21.1-21.3): `jev-fast-decision` client, PreCompact pre-summary hook, visible tool-advisory hooks as setup knobs.
- Host-split status line for Claude Code and Cursor CLI (23), with AST guards in `tests/test_arch.py`.
- `ai-kit-gsd-spec-discuss` (24), the quota-aware cross-AI runner with a configurable retry ladder and upstream error pass-through (25, 25.1), `ai-kit-session-wake` (26) and `ai-kit-spec-goal-prompt` (27).
- Audit gaps INT-1..3 (goal-prompt versus cross-AI wait wording, a broken session-wake link, README rows) closed before the close.

### Carried to the owner (not done)

Known verification overrides: 24 open items shown by the pre-close audit were disclosed, not suppressed (no `audit-open acknowledge`); 8 earlier acknowledgements carry forward. Each item stays visible in `.planning/STATE.md` (Deferred Items) and the milestone archive.

- **Owner capture files** (all under `.planning/phases/`): `25-quota-aware-cross-ai-subprocess-supervision/25-OWNER-CAPTURES.md` (C1-C7), `25.1-configurable-cross-ai-retry-ladder-and-upstream-error-propag/25.1-OWNER-CAPTURES.md` (O1-O10), `26-session-self-resume-and-opengsd-quota-rules/26-OWNER-CAPTURES.md` (captures 1-11), `27-one-shot-goal-and-loop-prompt-skill/27-OWNER-CAPTURES.md` (A1-A5, PI_SKILLS, 27-10 items a-g).
- **Interactive and live runs:** `20-.../20-INTERACTIVE-CODEX.md` and `20-INTERACTIVE-OPENCODE.md` (EVAL-04 deferred to 999.6, EVAL-05), `21-.../21-INTERACTIVE-CURSOR.md` (EVAL-07), `22-.../22-INTERACTIVE-PI.md` (C1 real pi capture, S1-S5, EVAL-08), `21.3-.../21.3-LIVE.md` (ADV-04), the Phase 21.2 spike steps S2-S5 and R9 measurement (PCH-01/02; the hook stays off), the Phase 23 spikes S1-S7 (STL-03/04) and the credential-bearing POC `cli-config.json.bak` delete (D-12).
- **human_needed / human_verification:** `*-VERIFICATION.md` of phases 20, 21, 21.1, 21.2, 21.3, 22, 23, 24, 25.1, 26, 27 and `16-UAT.md` (1 pending scenario); Phase 25 reads `gaps_found` (stale; its only gap is the skill-judge gate, superseded by owner deferrals).
- **Deferred skill-judge verdicts and owner decisions:** `ai-kit-spec-goal-prompt` UNRESOLVED (111/125 = 88.8%, base 90.4%, awaiting an Owner-decision line); `ai-kit-spec-config` UNRESOLVED (99 vs base 105); SJ-1 (execute-gsd 101 vs 105), SJ-2 (execute-superpowers, FAIL 86/120) and SJ-3 (project-rules-agents, FAIL 93) deferred by Owner-decision lines to the refactor todo and backlog 999.16; Phase 20 owner decisions (WR-12, fix-cap accounting, RUN-106, IN-07); Phase 21.1 Laya accuracy 0.5 below the 0.95 floor, opencode judge lane 11/15, live TypeSafe/Zen calls.
- **Phase 24 chain dry run:** never produced on a fixture project (SC1/R3/R4, SC2/R6, SC3/R8); SDC-01..04 are script-level satisfied only. ROADMAP SC2, SDC-02 and SPEC R5/R10 wording is stale against 21.1 and still needs a formal amendment.
- **WINDOWS #7** (`.planning/WINDOWS.md`): the autonomous block names an unverified primitive in its heading only; an open design decision.
- **Backlog open on purpose:** 999.16 (event-keyed playbook skill for the rules family, feasibility check first) and 999.17 (lite or strong executor choice through jev-fast-decision). No 999.x item was completed by a v1.3 phase, so none was removed; the remaining list is in `.planning/ROADMAP.md` § Backlog.

### Known Gaps

Unchecked at close (`milestones/v1.3-REQUIREMENTS.md`): EVAL-04 (deferred to 999.6), AGT-02 (deferred to 999.7), and owner-pending EVAL-05, EVAL-07, EVAL-08, SDC-01..04, PCH-01, PCH-02, ADV-04, STL-03, STL-04, GPS-04. Automated evidence is complete for each; the open part is the live or owner step named above.

---

## v1.2 ai-kit Rules Skill Family (Shipped: 2026-09-23)

**Phases completed:** 9 phases (9–15, plus inserted 15.1 and 15.2), 28 plans
**Timeline:** 2026-09-13 → 2026-09-23
**Closeout type:** override_closeout
**Audit:** `milestones/v1.2-MILESTONE-AUDIT.md` — tech_debt, requirements 7/7, integration 7/7, flows 2/2

**Key accomplishments:**

- Pruned the AGENTS.md checker to prose-only scope as `ai-kit-project-rules-agents`, and re-homed its Makefile logic into the new `ai-kit-project-rules-makefile` (validate-<category> parity, help/fail reachability, recipe cap, docker build-before-up).
- Shipped four more single-domain checkers on the shared `ai_kit_rules_common` package: pre-commit (Makefile↔hook parity, 6-category taxonomy, ruff checks), architecture (`arch-test` shape/chaining), Docker Compose (healthchecks, `depends_on`, hot-reload), and CI/CD (GitLab/GitHub reuse of Makefile/pre-commit/package.json/Gradle).
- `ai-kit-project-rules-all` fans out to all 6 checkers and merges one criticality-ordered report. It was dogfooded live against this repo with zero failures.
- Every new SKILL.md cleared `/skill-judge` (97–103/120, 0 Critical/Important) and `/naming-analyzer`.
- Phase 15.1 overhauled the usage-metrics dashboard against the real ~85k-row store:
  - virtualized Material UI with runtime/subfamily filters, one date range and charts;
  - five live-found data bugs fixed (opencode/cursor NULL dates, family noise, null-vs-zero price, session dedup, codex `custom_tool_call` shape).
- Phase 15.2 closed the audit's in-milestone debt:
  - pyright back to 0 errors (`PairRow` TypedDict);
  - symmetric flat/grouped sort-key fallback with node regression tests;
  - test-file lint fixed;
  - resolved todos moved to `todos/completed/`.

**Known verification overrides:** 8 newly acknowledged, 0 carried forward.
- **Stale verifications:** phases 9–13 and 15.1 (and v1.1's 6, 8 and 8.1) read `stale` in `init.manager`. Commits after each verification touched files it covered. None regressed: `make test` passes with 2535 tests, and the only error is the known mmdc environment failure.
- **Acknowledged deferred items:** pre-v1.2 ruff/pylint debt in `tools/status-line.py`, `tools/wizard_app.py` and `tests/test_ai_kit_spec_superpowers.py`. Also the mmdc environment failure (an incomplete pnpm-global `@mermaid-js/mermaid-cli`), which is not a code defect.
- **Nyquist:** `/gsd-validate-phase` never ran for v1.2 phases. This is a coverage TODO, not a failure.

---

## v1.1 Agent Workflow Hygiene & Tooling Polish (Shipped: 2026-09-13)

**Phases completed:** 4 phases (6, 7, 8, plus inserted 8.1), 9 plans
**Timeline:** 2026-09-10 → 2026-09-13
**Closeout type:** retroactive. The milestone was not formally closed at the time; it was archived during the v1.2 close.
**Audit:** `milestones/v1.1-MILESTONE-AUDIT.md`

**Key accomplishments:**

- AGENTS.md house-rules checker skill (17-rule ruleset, per-stack tooling cache, criticality-ordered `/agent-md-refactor` hand-off). v1.2 later renamed it and split it into the rules family.
- `ai-kit-gsd-curated-config`: writes `.planning/config.json` through `gsd-tools` only, using live opencode/cursor model detection and cross-AI command wiring.
- Status-line rate-limit coloring is driven by burn pace (`used_percentage / elapsed_fraction`). Phase 8.1 reversed Phase 8's remaining-fraction formula.

---

## v1.0 Multi-CLI Foundation & Config Safety (Shipped: 2026-09-10)

**Phases completed:** 6 phases (1.1, 1.2, 2–5), 18 plans
**Timeline:** phases completed 2026-09-09 → 2026-09-10. The start date can't be recovered from git, because `.planning/` was first committed on 2026-09-16.
**Closeout type:** retroactive. The phase directories were archived to `milestones/v1.0-phases/` without a formal close. The roadmap archive was written during the v1.2 close.

**Key accomplishments:**

- Autonomous-run infrastructure: cross-AI plan-review convergence plus a clean-room Docker/Podman E2E harness.
- Multi-CLI runtime foundation: hardened installer fetch, runtime self-detection, and opencode UI research.
- Opencode provider management and the tool-substitution awareness hook (atomic surgical JSONC edits; live-verified rtk briefing).
- Config Doctor (confidence-labeled, per-item confirmed apply) and the usage-metrics capture → refine → dashboard pipeline.
