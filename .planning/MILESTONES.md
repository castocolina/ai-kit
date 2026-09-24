# Milestones

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
