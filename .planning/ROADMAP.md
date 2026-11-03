# Roadmap: ai-kit

## Milestones

- ✅ **v1.0 Multi-CLI Foundation & Config Safety** — Phases 1.1–5 (shipped 2026-09-10)
- ✅ **v1.1 Agent Workflow Hygiene & Tooling Polish** — Phases 6–8.1 (shipped 2026-09-13)
- ✅ **v1.2 ai-kit Rules Skill Family** — Phases 9–15.2 (shipped 2026-09-23)
- ✅ **v1.3 GSD Curated Config v2** — Phases 16–27 (shipped 2026-10-31; owner items carried, see below)
- 🚧 **v2.0 Skill Refactor** — Phases 28–54 (in progress)

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

<details>
<summary>✅ v1.3 GSD Curated Config v2 (Phases 16–27) — SHIPPED 2026-10-31</summary>

- [x] Phase 16: ai_kit_spec Extensions (6/6 plans)
- [x] Phase 16.1: Hardening (INSERTED) (31/31 plans)
- [x] Phase 17: Curated-Config Inventory & Recommendation Engine (9/9 plans)
- [x] Phase 18: Cross-AI, Skills & Apply Pipeline (22/22 plans)
- [x] Phase 18.1: One runtime model (INSERTED) (22/22 plans)
- [x] Phase 19: Evaluation on Claude (10/10 plans)
- [x] Phase 20: Live Validation on Codex + Opencode (7/7 plans) — human_needed
- [x] Phase 21: Cursor Live Validation (7/7 plans) — human_needed
- [x] Phase 21.1: Atomic reusable decision-system skills (INSERTED) (7/7 plans) — human_needed
- [x] Phase 21.2: PreCompact pre-summary hook (INSERTED) (5/5 plans) — human_needed
- [x] Phase 21.3: Visible tool-advisory hooks (INSERTED) (8/8 plans) — human_needed
- [x] Phase 22: Pi Live Validation (7/7 plans) — human_needed
- [x] Phase 23: Host-split status line for Claude Code and Cursor CLI (18/18 plans) — human_needed
- [x] Phase 24: Spec-and-discuss chain skill (1/1 plan) — human_needed
- [x] Phase 25: Quota-aware cross-AI subprocess supervision (11/11 plans) — human_needed
- [x] Phase 25.1: Configurable cross-AI retry ladder and upstream error propagation (INSERTED) (15/15 plans) — human_needed
- [x] Phase 26: Session self-resume and OpenGSD quota rules (12/12 plans) — human_needed
- [x] Phase 27: One-shot goal and loop prompt skill (14/14 plans) — human_needed

**Carried to the owner (not done):** every `*-OWNER-CAPTURES.md` (phases 25, 25.1, 26, 27), the
interactive and live runs (20, 21, 21.2, 21.3, 22, 23), every `human_needed` verification, the
deferred skill-judge verdicts (`ai-kit-spec-goal-prompt` and `ai-kit-spec-config` UNRESOLVED; SJ-1,
SJ-2, SJ-3 deferred), the Phase 24 chain dry run, and `.planning/WINDOWS.md` entry 7. The full list
with paths is in the v1.3 entry of `MILESTONES.md`.

Full details: `milestones/v1.3-ROADMAP.md` · phase dirs: `milestones/v1.3-phases/`

</details>

### 🚧 v2.0 Skill Refactor (In Progress)

**Milestone Goal:** Turn ai-kit's skills into a smaller, re-judged and portable set: shared config, resilient
review and execute loops, one project-rules skill of event playbooks, and installs from a committed `dist/`;
every phase ends with something the owner can see.

Phases 28-32 are self-contained and meant to be specced and discussed before `/gsd-autonomous` runs the rest.
Decimal phases 32.1-32.4 are the skill batches that follow the re-judge baseline. Phase 30.1 was inserted on
2026-11-03 (Round 10) so the wizard's component cards exist before Phase 31 and later phases change the
component list. Phase 30.2 was split out of 30.1 on 2026-11-03, during 30.1's spec, for Cursor status-line parity. Phase 29.1 was split out of Phase 29 on 2026-11-03, during Phase 29's spec, when the owner
added superpowers plans and both PR-chaining backends: Phase 29 keeps the local folding step and the jev ladder,
29.1 the branches, pushes, PRs and merge chain. Phases 38.1, 45.1 and 47.1 were split out on 2026-11-03, when the ideas and rules audit added requirements that overloaded 38, 45 and 47. Every phase that adds or changes a SKILL.md carries a judge-bar criterion citing JDG-04.

Each phase lists **Code anchors**: the existing files and symbols it changes or hooks into, the new files it
creates (`new:`), and the docs it must update (`docs:`). They were found with `codegraph explore` on
2026-11-03; "unknown until research" marks what the phase researcher must locate first.

- [ ] **Phase 28: Fast, environment-proof gates** - Commit runs only the covering tests; push runs the full suites fast with fakes only
- [ ] **Phase 29: Logical-commit folding and the shared jev ladder** - Each finished GSD or superpowers plan becomes logical-feature commits; every caller chains jev as a black box
- [ ] **Phase 29.1: Stacked phase branches, chained PRs and the merge chain (INSERTED)** - Stacked branches, a push per plan, chained PRs and an owner-started merge chain
- [ ] **Phase 30: Phase-boundary index refresh, code-exploration rules and lens wiring** - codegraph sync, graphify rebuild and a changed-symbols brief at every phase boundary
- [ ] **Phase 30.1: Setup wizard, component cards and host status-line panes (INSERTED)** - One card per component kind, host-styled status-line panes, config doctor reachable from the wizard
- [ ] **Phase 30.2: Cursor status-line parity (INSERTED)** - Cursor status line brought back to the approved proof of concept and to Claude's look where the data allows
- [ ] **Phase 31: Removals and small defects** - Three skills and rtk gone, seven small known defects fixed *(amended 2026-11-03, 31 spec: seven items per DEF-01)*
- [ ] **Phase 32: Re-judge baseline** - One current-judge report for every kept skill, plus strict frontmatter and text checks
- [ ] **Phase 32.1: Batch 1, general small skills** - cst-refactor, markdown-to-pdf, jev-fast-decision, spec-review-fixer and usage-metrics reach the bar
- [ ] **Phase 32.2: Batch 2, spec review family** - spec-review, checklist, spec-config and spec-execute reach the bar
- [ ] **Phase 32.3: Batch 3, execution and session skills** - spec-execute-superpowers, cross-ai and session-wake reach the bar; one shared secret scanner
- [ ] **Phase 32.4: Batch 4, planning skills and the closing report** - goal-prompt, spec-discuss and curated-config reach the bar; every kept skill has evals
- [ ] **Phase 33: One config design** - One documented config for every ai-kit setting; review-spec.toml migrates on its own
- [ ] **Phase 34: jev backends by host and Laya calibration** - jev picks its backend per host from ai-kit's config; Laya measured against its floor
- [ ] **Phase 35: Model discovery and catalog** - spec-config lists every model on every host with honest source, usability and tier labels
- [ ] **Phase 36: spec-config as the hub** - Every spec skill chains spec-config; reviewers and executors kept apart with opt-in escalation
- [ ] **Phase 37: Shared runner options and session ids** - One runner for GSD cross-AI and ai-kit lanes, with per-call settings and resumable sessions
- [ ] **Phase 38: Runner hardening and run safety** - Idle watchdog, the Phase 25 cleanup, a run lock with a tree baseline, and a plan-versus-commits check before done
- [ ] **Phase 38.1: Runner error classification and retry policy (INSERTED)** - Wider error catalogue, stdout limit matching, router cooldowns and the owner's retry policy
- [ ] **Phase 39: Lane capability blocks and lens skills** - Each lane is told only the tools it really has; lens skills reach reviewers
- [ ] **Phase 40: Resilient review sized by jev** - A failing lane no longer ends a review; jev sizes and classifies
- [ ] **Phase 41: Superpowers adapter refactor with spec-config handoff** - One resume path, one stop path, session-model fallback, complete executor briefs
- [ ] **Phase 42: Code review after execution and jev-picked executors** - Implementation is reviewed in a capped loop; jev picks the executor and lane transport
- [ ] **Phase 43: curated-config reads docs at the installed tag** - Version-pinned open-gsd docs and a grouped question cascade
- [ ] **Phase 44: curated-config writes the agreed settings** - Profile, routing, models, effort, skills and graphify flags written through gsd-tools
- [ ] **Phase 45: Project rules, one skill and AGENTS.md only** - `ai-kit-project-rules` replaces seven skills, adapts to the model and migrates Claude files into AGENTS.md for every host
- [ ] **Phase 45.1: Project rules, generated top rules and never list (INSERTED)** - The generated block's top rules, owner-talk, run and test rules and the never list, with reasons
- [ ] **Phase 46: Project rules, area runbooks** - Makefile, CI, README and per-stack runbooks that write working config
- [ ] **Phase 47: Project rules, development-loop playbooks and the quota decision** - Playbooks for session start, worktree created, end of unit, CI wait, PR review, delegation and quota; shared quota logic decided
- [ ] **Phase 47.1: Project rules, lifecycle playbooks (INSERTED)** - Requirement intake, audit, milestone close and worktree closed
- [ ] **Phase 48: Host hooks, spikes and status** - Host-hook facts recorded; `setup.py hooks status` shows what is on per host
- [ ] **Phase 49: Host hooks, dispatcher and session hooks** - One dispatcher per host reads layered settings; toggling never rewrites a host config
- [ ] **Phase 50: The 5-hour wake grid and limit capture** - Wakes armed on the 5-hour grid and before a session runs out; the next real usage limit captured
- [ ] **Phase 51: Trustworthy notices and macOS** - Readable, checked desktop notices; launchd on macOS or a clear refusal
- [ ] **Phase 52: Script ownership and a committed dist** - Every script owned; `dist/skills/` generated, committed and drift-checked
- [ ] **Phase 53: Install through npx skills and the README** - Headless per-host sync and documented installs
- [ ] **Phase 54: Owner-attended live checks and consent items** - Live checks, Cursor subagents, jev global marker and image questions, v1.3 housekeeping

## Phase Details

### Phase 28: Fast, environment-proof gates
**Goal**: The owner can commit and push without waiting on slow tests or tests that pass or fail depending on the caller's environment.
**Depends on**: Nothing (first v2.0 phase; it runs before the phase-branch flow of Phase 29 exists)
**Requirements**: GATE-01, GATE-02, GATE-03, GATE-04, GATE-05
**Code anchors**: `.pre-commit-config.yaml` (`unittest`, `unittest-wizard` hook stages); `tools/run_unittest_parallel.py` (`group_modules`, `hook_groups`, `main`, `worker_count`); `tools/gen_test_groups.py`; `Makefile`; `tests/test_gate_scope.py`; real host-binary callers `tests/test_ai_kit_spec_goal_prompt_host.py`, `tests/gsd_curated_eval.py`; runner self-test budgets in `skills/ai-kit-spec-review/references/cross-ai.mjs` (`budgetMs`, self-test cases); new: staged-file to test-module mapper (home unknown until research), structural test for real host-CLI calls; new: structural test that fails when a test reads a `.planning/` path (beside `tests/test_gate_scope.py`; home unknown until research); docs: AGENTS.md Testing, README testing section
**Success Criteria** (what must be TRUE):
  1. Committing a change to one module runs, in parallel, only the test modules that cover it (through imports and the runner's test lists), and the commit is refused when one of them fails. *(amended 2026-11-03, 28 D-01: 81 of 95 test modules reach code through path strings, `sys.path` inserts or subprocesses, not imports; the mapper is a name index over tests and their helpers, which includes imports)*
  2. The pre-push stage runs the full unit, arch and wizard suites in clearly less wall time than the 2.5 minutes measured on 2026-11-02; the before and after times are recorded, and no test calls a real host binary. *(amended 2026-11-03, 28 SPEC R3: re-measured at 184 s (core 162.9 s, wizard 21.0 s, 24 CPUs); the target is 60 s or less for both test hooks)*
  3. The suites give the same result from a plain terminal, from inside a host session, with no host CLI on PATH, from a long checkout path, with a custom TMPDIR and from outside a git repository; a structural test fails when a test calls a real host CLI.
  4. The runner's self-test passes under simulated host load because its budgets scale with load, while the real run limits are unchanged.
  5. A structural test fails when a test module reads a path under `.planning/`, and every test's data lives under `tests/`.
**Optional, not a requirement**: ai-kit is a desktop and CLI tool, so concurrency tests on its shared state (candidates: status-line caches and state files, the wake schedule, the jev answer log, two setup runs at once) are nice to have, never required (RULE-24's project-kind rule). The run lock (Phase 38) and the wake grid's no-double-arm check (Phase 50) keep their concurrency tests.
**Plans**: TBD

### Phase 29: Logical-commit folding and the shared jev ladder
**Goal**: Every finished GSD or superpowers plan is folded into logical-feature commits by one reusable step that follows one written folding policy, and every caller reaches jev by chaining the `jev-fast-decision` skill as a black box.
**Depends on**: Phase 28
**Requirements**: FLOW-01, JEV-06
**Scope**: general — the folding step, its policy and the jev ladder serve any GSD or superpowers project through ai-kit's skills; ai-kit is the first user; fixtures are one GSD and one superpowers fixture project. *(amended 2026-11-03, 29.1 spec: ai-kit's flow is framework-neutral: the fold engine takes a unit's checkpoint (commit range, tested tip, feature candidates) through the unit contract of Phase 29.1 (FLOW-10); GSD and superpowers are its first two thin adapters, and another spec-driven system plugs in through the same contract)*
**Code anchors**: new: the folding step and its written folding policy (home unknown until research), its tree-equality check and old-tip backup tag; GSD plan end (`.claude/gsd-core/workflows/execute-plan.md`, executor task commits and the `docs({phase}-{plan})` commit) and superpowers plan end (`skills/ai-kit-spec-execute-superpowers/`, superpowers' finishing step); jev ladder caller now in `skills/ai-kit-gsd-spec-discuss/scripts/decide.py` (`ladder`, `detect`, `client_candidates`, `find_client`) -> owned by `skills/jev-fast-decision/` with one documented entry point; callers: `skills/ai-kit-spec-goal-prompt/scripts/gp_host.py` (`DECIDE_CLI`, `jev_status`), `gp_sections.py` (gray-area and report text), `tools/hooks/precompact_core.py` (`find_client`), `tools/hooks/claude_decision_probe.py`; tests `tests/test_ai_kit_gsd_spec_discuss.py`, `tests/test_jev_fast_decision.py`, goal-prompt tests; docs: `skills/jev-fast-decision/SKILL.md`, `reference.md`, `skills/ai-kit-gsd-spec-discuss/SKILL.md`, `references/decision-table.md`, `skills/ai-kit-spec-goal-prompt/SKILL.md`
**Success Criteria** (what must be TRUE):
  1. A finished GSD plan with two features, and a finished superpowers plan with two features, each end as two commits, grouped by jev's proposal or by the agent when jev is absent. Commits on main or on a branch whose PR has merged are never rewritten. The folding runs in a subagent that reports in five lines or fewer; before the swap the folded tip's tree equals the tested tree and the old tip carries a local backup tag, and no step uses `reset --hard` (fixture tests). *(amended 2026-11-03, 29 spec: commits already pushed to an unmerged phase or plan branch may be folded again; the push itself, with `--force-with-lease`, is Phase 29.1)*
  2. The folding policy is written once (logical-feature grouping, never one squash per plan or phase, the tree check before the swap, a local backup tag deleted when the PR merges, `--force-with-lease` only on unmerged branches, the primary remote only), the folding step implements it, and a doc-contract test pins each rule.
  3. The jev ladder is owned by `jev-fast-decision` and reached through one documented entry point; spec-discuss, the folding step, goal-prompt and the two hooks that use jev chain that skill and still finish when the skill or every decision backend is missing; no caller imports another skill's code or files; skill text treats jev as a black box (ask that skill and follow its SKILL.md; no backend, consent or probe detail; `needs_fallback` or no answer means the rule-based default decides).
  4. Every SKILL.md this phase adds or materially changes meets the judge bar (JDG-04): new-shape evals and tests, no critical or high finding or grade B or better, no regression beyond judge variation.
**Plans**: TBD

### Phase 29.1: Stacked phase branches, chained PRs and the merge chain (INSERTED)
**Goal**: Each GSD phase, and each superpowers plan, runs on its own branch stacked on the previous one, each finished plan is pushed, each unit has one PR chained on the previous one, and an owner-started merge chain moves main. *(amended 2026-11-03, 29.1 spec: through one framework-neutral unit contract with thin adapters; a hotfix reaches its target without entering the stack)*
**Depends on**: Phase 29 (the folding step). Inserted 2026-11-03 when Phase 29's spec split the remote half out of Phase 29.
**Requirements**: FLOW-02, FLOW-03, FLOW-05, FLOW-07, FLOW-10, FLOW-11
**Scope**: the branch, push, PR and merge-chain flow is general (any GSD or superpowers project, through ai-kit's skills), tested on one GSD fixture project and one superpowers fixture project; FLOW-05 and FLOW-07 are ai-kit dogfood, each with a general counterpart (CUR-04 in Phase 44; RULE-17 in Phase 47).
**Code anchors**: new: phase-branch stacking and per-plan push (home unknown until research); GSD branch creation in `.claude/gsd-core/workflows/execute-phase.md` (`handle_branching`: a new phase branch forks off `origin/<git.base-branch>`, an existing one is reused) and PR creation in `workflows/ship.md` (`--base`); `.planning/config.json` `git.*` branching keys, written through `.claude/gsd-core/bin/gsd-tools.cjs config-set`; `gh stack` (github/gh-stack) when installed, plain `gh pr create/edit --base` otherwise; new: the unit contract and its GSD and superpowers adapters (superpowers' `finishing-a-development-branch` push and PR options bypassed for a unit); new: hotfix start and stack cascade (`git rebase --update-refs`, `gh stack rebase`); GSD `worktree.baseRef` (`gsd-tools worktree set-baseref`) for stacked branches; new: merge-chain command; one-time push and PR consent in the personal `.aikit/` settings; `.planning/INGEST-CONFLICTS.md` (archived so `validate health` is clean); AGENTS.md Workflow ship rule with a new doc-contract test; docs: AGENTS.md Workflow, README
**Success Criteria** (what must be TRUE):
  1. A GSD phase runs on its own branch stacked on the previous phase's branch, and a superpowers plan on its own branch stacked on the previous plan's branch; each finished plan is pushed to it, and each unit has one PR opened against the previous unit's branch, through `gh stack` when it is installed and plain `gh` otherwise (the owner consents once per project to pushes and PRs from this flow, recorded in the personal ai-kit settings until revoked).
  2. Pushes go to the primary remote only and use `--force-with-lease`; main and any branch whose PR has merged are never force-pushed.
  3. An owner-started merge chain merges the PRs bottom-up with merge commits (never squash), retargets the next PR, fast-forwards local main and deletes the merged unit's local backup tags.
  4. In MVP mode on a main-only fixture project, the phase branch fast-forwards into main and main is pushed after each finished plan, with no PR and no review step.
  5. (ai-kit dogfood of CUR-04) ai-kit's `.planning/config.json` reads branch per phase, set through the project's `gsd-tools`, and the planning health check is clean (the v1.2 `INGEST-CONFLICTS.md` archived into the milestones archive).
  6. (ai-kit dogfood of RULE-17) AGENTS.md's Workflow section states how a finished phase ships: gates green on the phase branch, an installer dry run and the new hooks against a scratch HOME, then the install and a live re-check from the phase branch's tip; local main moves only when the stacked PRs merge; a doc-contract test pins it.
  7. Every SKILL.md this phase adds or materially changes meets the judge bar (JDG-04): new-shape evals and tests, no critical or high finding or grade B or better, no regression beyond judge variation.
  8. (added 2026-11-03, 29.1 spec) The flow knows only units, checkpoints and target branches through one documented contract; the GSD and superpowers adapters are thin, and a synthetic third adapter drives the whole flow in a fixture with no change to the flow's code (FLOW-10).
  9. (added 2026-11-03, 29.1 spec) A hotfix to a configured target branch merges ahead of an open stack without entering it; the stack is then rebased onto the updated trunk and pushed with `--force-with-lease`, and a conflict restores every branch *(amended 2026-11-03, 29.1 D-07: a conflict is first resolved by an agent keeping both sides' intent, GSD's planning files merged by content, and the gates run on the result; every branch is restored and the flow stops only when the resolution or the gates fail; the report names every resolved file and how)*; an owner-attended live check on a throwaway private GitHub repo proves both PR backends and the hotfix (FLOW-11).
**Plans**: TBD

### Phase 30: Phase-boundary index refresh, code-exploration rules and lens wiring
**Goal**: At every phase boundary the next phase's researcher, planner and executor see the symbols that changed and the documents that mention them, on whatever branch the work is on.
**Depends on**: Phase 29.1 *(amended 2026-11-03, 29 spec: the phase branches now arrive in 29.1)*
**Requirements**: FLOW-04, FLOW-06, DESIGN-01, LENS-01, FLOW-12, FLOW-13
*(Amended 2026-11-03: the global-sentence rewrite came from the 30 spec; the setup-dev tool installs came from 30 D-04, with code anchors `Makefile` `setup-env`/`dev` and AGENTS.md Commands.)*
**Code anchors**: new: phase-boundary step (`codegraph sync`, graphify rebuild, changed-symbols brief; hook point in GSD's phase transition unknown until research); `graphify-out/` and a graphify exclude for `.planning/milestones/` (mechanism unknown until research); house rules in `skills/ai-kit-project-rules-agents/ai_kit_project_rules_agents/rules.py`; tool-advisor advice in `tools/hooks/advisor_core.py`, `tools/hooks/claude_tool_advisor.py`; new: graphify runbook (`docs/run-book/graphify.md`); lens wiring in `.planning/config.json` `agent_skills` and `workflow.ui_review` (set through `gsd-tools config-set`); docs: AGENTS.md Code Exploration, `.claude/cli-environment.md` *(amended 2026-11-03, 30 spec: the step lives in the unit-flow engine of Phase 29.1 and runs at the unit's start, `plan:pre` and `execute:wave:pre` of wave 1, since GSD's transition dispatches no hook; the exclude is a committed root `.graphifyignore`; new: ai-kit's worktree-created indexing hook (`post-checkout`); `agent_skills_security.trusted_global_roots`; the superpowers adapter `skills/ai-kit-spec-execute-superpowers/` carries the brief; `.claude/cli-environment.md` is gitignored and local-only, so it is not a deliverable)*
**Success Criteria** (what must be TRUE):
  1. Closing a phase on its branch syncs the codegraph index and rebuilds the graphify graph with archived milestones excluded, with no commit to main needed. *(amended 2026-11-03, 30 spec: for every unit, at its start, before its planning and before its first execution wave, on its own branch; codegraph and graphify are created or refreshed automatically whenever their CLI is installed, and every new ai-kit worktree is indexed the same way without blocking git)*
  2. The next phase's brief lists the new or changed symbols to hook into and the documents that mention them, and that phase's researcher, planner and executor read it.
  3. ai-kit's AGENTS.md, the current house rules and the tool-advisor hook's advice all say to explore code with codegraph when it is indexed and to keep graphify for GSD's document discovery.
  4. A runbook says how to build the graphify index (archived milestones excluded), when it refreshes (every phase boundary plus GSD's auto-update after commits) and how.
  5. `gsd-tools query agent-skills` shows `impeccable` for the UI researcher, checker and auditor, `ponytail` for the planner and plan checker and `ponytail-review` for the code reviewer, all as `global:` names; UI review is on; with a lens removed from a scratch home the agent runs and reports the missing lens.
  6. ai-kit's AGENTS.md states the design rule (simple is not easy; never a half-done feature or mediocre value to save a few uncomplicated steps; ponytail governs how code is built, reusing existing components and known design patterns before new code, not how much ships; MVP only shifts the weight), the ponytail and review lenses are briefed with it, and a doc-contract test pins the text.
  7. In a scratch HOME, install rewrites only codegraph's "indexing is the user's decision" sentence in the four synthetic global instruction files with a backup, a second run gives no diff, `--dry-run` writes nothing, and the config doctor reports the installer's wording when it is back. *(amended 2026-11-03, 30 spec: added, FLOW-12; code anchors `tools/setup.py`, `tools/config_doctor_checks.py`, `tools/config_doctor_appliers.py`, new: shared marked-block editor)*
  8. With the five flow tools missing and fake installers in a scratch HOME, `make setup-dev` installs the four that can install, reports the one that cannot and exits 0, and a worktree made with hooks uninstalled is still indexed at the next boundary point. *(amended 2026-11-03, 30 D-04: added, FLOW-13 and the resilient-indexing rule)*
  9. Every SKILL.md this phase adds or materially changes meets the judge bar (JDG-04). *(amended 2026-11-03, 30 spec: added, renumbered 9 after FLOW-12 and FLOW-13; the superpowers adapter changes to carry the brief)*
**Plans**: TBD

### Phase 30.1: Setup wizard, component cards and host status-line panes (INSERTED)
**Goal**: The owner opens the setup wizard and sees one card per component kind and a styled pane per status-line host, before later phases add or remove skills, agents, commands and hooks.
**Depends on**: Phase 28 (fast wizard suite). Inserted before Phase 31 because the removals, the project-rules merge (45), the host hooks (48-49) and dist (52-53) all change the component list.
**Requirements**: FEAT-01, FEAT-06, WIZ-01, WIZ-02, WIZ-03, WIZ-05
*(Requirements amended 2026-11-03 in the 30.1 spec: the Cursor parity requirement moved to Phase 30.2; the real-render preview requirement was added.)*
**Code anchors**: `tools/wizard_app.py` (`WizardApp._compose_choose`, `_render_choose`, `_choose_category_groups`, `_choose_component_row`, `_key_choose`, `_review_component_rows`, `WizardApp.CSS`, `_host_pane`, `_render_arrange_board`, `_chip`, `_adoption_gate_markup`, `_render_done`, `HostView`); `tools/setup.py` (`CATEGORIES`, `Selection`, `_build_wizard_context`, `_hook_selection_items`, `_host_view`, `_HOST_LABELS`, `current_segments`, `load_segment_inventory`, `cmd_config_doctor`, `launch_wizard`); `tools/segments_inventory.toml` (`hosts`); Cursor defaults `SPEC` in `tools/cursor_host.py` (source of the disabled chips unknown until research); `tools/config_doctor_app.py` (`ConfigDoctorApp`, `run_config_doctor`); tests `tests/test_wizard_app.py`, `tests/test_wizard_pty.py`, `tests/wizard_fixtures.py`, `tests/test_setup.py`; config doctor rows in `tools/config_doctor_checks.py` (Playwright MCP Chrome path decision); docs: README "The install wizard", `docs/wizard-redesign/mockup-textual.html`
**Success Criteria** (what must be TRUE):
  1. Run under `uv run` with a scratch HOME, the first screen shows one card per component kind (skills, agents, commands, hooks); a kind with nothing to install shows no card, and toggling and the Review counts work per card.
  2. The Claude status-line pane keeps today's layout with an orange accent background and "Claude Code" in bold; the Cursor pane uses a gray accent.
  3. ~~The Cursor pane has a toggle that keeps Cursor's own default status line; confirming with it on leaves the scratch `cli-config.json` without ai-kit's status line.~~ *(amended 2026-11-03, 30.1 spec: the state was backwards and the toggle is on both hosts)* Both host panes have an on/off toggle that starts at what is wired now; confirming with it off leaves the scratch host config without any `statusLine` (a foreign one removed only after it is shown, backed up and confirmed), and with it on wires ai-kit's.
  4. ~~Cursor's board shows no chip for a segment the Cursor status line cannot show, while a segment that is only switched off stays in the tray.~~ *(amended 2026-11-03, 30.1 spec: parity moved to Phase 30.2 as WIZ-04)* Each host's board preview is a real render through that host's renderer, titled with the host on screen, and the tray title does not say "disabled" (WIZ-05).
  5. The config doctor opens from the wizard, reusing `ConfigDoctorApp` and the existing engine with no second implementation. *(amended 2026-11-03, 30.1 spec: `d` on Done, Esc back to Done, one screen class; every apply refuses an unparseable file and backs up first)*
  6. A recorded owner decision says whether the config doctor gets a Playwright MCP Chrome path row; an added row uses the existing engine and its confidence labels. *(amended 2026-11-03, 30.1 spec: decided — the row and its apply write `env.PLAYWRIGHT_MCP_EXECUTABLE_PATH` to the flatpak Chrome wrapper in a scratch `settings.json` with a backup)*
**Plans**: TBD
**UI hint**: yes

### Phase 30.2: Cursor status-line parity (INSERTED)
**Goal**: The Cursor status line looks like the proof of concept the owner approved and like Claude's on every aspect the hosts share. The phase starts from the proof of concept as the visual reference, traces why Phase 23's host-split implementation diverged from it (each difference lost, decided otherwise or never ported), and closes the gap; real data differences are flagged, never faked.
**Depends on**: Phase 30.1 (its real-render board preview shows this phase's icons and samples in the wizard). Inserted 2026-11-03 by Phase 30.1's spec, when the owner's "disabled chips" complaint turned out to be the Cursor preview not matching Claude's.
**Requirements**: WIZ-04
**Code anchors**: `tools/cursor_host.py` (`SEGMENTS`, `LAYOUT`, `SPEC`), `tools/cursor_segments.py` (`seg_cursor_included`, `seg_cursor_api`, `seg_cursor_extra`, `seg_cursor_reset`, `_colored`), `tools/cursor_payload.py` (`core_cursor_context`), `tools/cursor_quota.py`; `tools/common_segments.py` (`seg_path`, `seg_git_dirty`, `seg_model`, `seg_alt_term_dimensions`), `tools/common_probe.py` (RSS helpers), `tools/common_types.py` (`util_icon`, `util_gap_color`); Claude's reference `tools/claude_segments.py` (`util_rate_group_str`, `seg_alt_process_memory`, `seg_alt_time_ago`) and `tools/claude_probes.py` (`probe_rss_bytes`); `tools/segments_inventory.toml` (icons, Cursor samples); `tools/statusline-doctor.py`; the proof of concept on branch `archive/poc/cursor-statusline`: `tools/cursor-status-line-poc.py`, `tools/cursor-statusline-poc.toml.sample`, `tests/test_cursor_status_line_poc.py`, `docs/superpowers/plans/2026-10-11-cursor-statusline-poc.md`; the design `.planning/specs/2026-10-10-host-split-statusline-design.md` and its `-REVIEW.md`; Phase 23 archive `.planning/milestones/v1.3-phases/23-host-split-status-line-for-claude-code-and-cursor-cli/` (`23-CONTEXT.md` D-12 "the POC is reference only", `23-SPIKE.md`, `live/`); `tests/fixtures/cursor/payload_poc_redacted.json`, `tests/fixtures/sample-input-cursor.json`; todo `.planning/todos/pending/2026-10-12-promote-cursor-statusline-poc-into-999-4.md`; tests `tests/test_cursor_*.py`, `tests/test_arch.py` (host-family rules); no screenshots of the proof of concept were found in the branch or the archive (unknown until research); docs: README status-line section
**Success Criteria** (what must be TRUE):
  1. A recorded trace lists each visual difference between the proof of concept and the shipped Cursor status line, classes it as lost, decided otherwise (naming the Phase 23 decision) or never ported, and records whether it is closed or kept.
  2. Every Cursor segment shows an icon in the real render and in the wizard preview; the five shared segments carry the same icon on both hosts.
  3. A Cursor process-memory segment uses Claude's calculation and finds the Cursor CLI process by its program path; its label says unverified until a live Cursor session confirms it. *(amended 2026-11-03, 30.2 D-02: by its command line or its program path; live, the process is named `MainThread`, runs `<cursor-agent>/versions/<v>/node`, with `cursor-agent` in its command line)*
  4. Cursor's quota segments use Claude's ramp and window format where Cursor's data allows; each real data difference (one monthly billing cycle, no hourly window) is flagged visibly on the line or in the doctor, never filled with invented values.
  5. `alt_term_dimensions` never shows a 0 row count on Cursor.
  6. Cursor's inventory samples match its renderer (no borrowed Claude samples), so the wizard's fallback preview agrees with the real render.
  7. With the Cursor CLI installed and logged in, an owner-attended live Cursor run from the phase branch tip is recorded and closes Phase 23's S7 visual check; without it, the check and the wizard render Cursor's sample data through the real renderer, labelled sample data; nothing installs Cursor. *(added 2026-11-03, 30.2 SPEC R11 and D-08)*
  8. The extra-spend alert (amount in bold red) is set from the wizard with a toggle and a dollar threshold, stored in the Cursor TOML, invalid values refused. *(added 2026-11-03, 30.2 SPEC R12 and D-03)*
**Plans**: TBD

### Phase 31: Removals and small defects
**Goal**: `ai-kit-spec-execute-gsd`, `ai-kit-opencode-providers`, `mermaid-audit` and rtk are gone and the known small defects are fixed, so the baseline judges and later vendors only kept skills.
**Depends on**: Phase 28, Phase 30.1 (the component cards are in place before the component list changes), Phase 30.2 *(amended 2026-11-03, 30.1 spec: 30.2 inserted before 31)*
**Requirements**: RMV-01, RMV-02, RMV-03, RMV-04, DEF-01
**Code anchors**: remove `skills/ai-kit-spec-execute-gsd/`, `skills/ai-kit-opencode-providers/`, `skills/mermaid-audit/` with `tests/test_ai_kit_spec_gsd*.py`, `tests/test_ai_kit_opencode_providers.py`, `tests/test_mermaid_style.py`, `pyproject.toml` and `tests/test_gate_scope.py` entries; execute router `skills/ai-kit-spec-execute/` (`SKILL.md`, `detect_framework.py`); stale links via `tools/setup.py` (`stale_link_candidates`, `prune_stale`); providers references in `tools/setup.py`, `tools/config_doctor_readers.py`, `tools/config_doctor_appliers.py`, `skills/ai-kit-usage-metrics/ai_kit_usage_metrics/{paths,raw_store}.py`; `skills/markdown-to-pdf/scripts/render_mermaid.py`; rtk in `ai_kit_usage_metrics/{capture_rtk,cli,dashboard,refiner,refined_store,paths}.py`, `tools/config_doctor_{checks,readers}.py`, `skills/_shared/ai_kit_rules_common/tool_presence.py`, `ai_kit_project_rules_agents/rules.py`; DEF-01 targets `tools/setup.py` `PI_SKILLS`/`_pi_entries`, `skills/ai-kit-gsd-spec-discuss/scripts/edge_floor.py`, `skills/ai-kit-spec-goal-prompt/scripts/goal_prompt.py` (detect), `ai_kit_spec/routing.py` docstring, `ai_kit_spec/detection.py` `RUNTIMES` drift; new: rtk-mention test, runtime-list drift test; code only the removed adapter used: `ai_kit_spec/runner_dispatch.py` (`project_runner_command` guidance prepend, `PROJECT_GUIDANCE_PATH`), curated-config `cross_ai_build.py` (the `cross-ai-guidance.md` it writes), `ai_kit_spec/gsd_tools.py` (`prior_value`); the rtk mention in AGENTS.md Tools and Stack; docs: README skills table, AGENTS.md (`.claude/cli-environment.md` link), `skills/ai-kit-spec-execute/SKILL.md`, `skills/ai-kit-spec-config/SKILL.md`, `skills/ai-kit-usage-metrics/SKILL.md`
**Success Criteria** (what must be TRUE):
  1. The three removed skills are absent from `skills/`, the tests, the runner's test lists, the README and the docs; asking the execute router to run a GSD plan points to `/gsd-execute-phase`; the installer removes their stale links in a scratch home. Code only the removed adapter used (the runner guidance prepend, `PROJECT_GUIDANCE_PATH`, the `cross-ai-guidance.md` curated-config writes, `gsd_tools.prior_value`) is gone too.
  2. spec-config reports a stale opencode provider the way the removed providers skill did.
  3. A test fails on any rtk mention outside history files, and the tree passes it (tool lists, guidance, house rules, config-doctor advice and usage-metrics sources), including the house rule that recommends rtk and AGENTS.md's Tools and Stack section.
  4. Each of the seven listed small defects has a fix and a regression test (for example: pi's install includes the wake and cross-AI skills, a drift test ties the hand-copied runtime lists to the runtime table, AGENTS.md no longer links a gitignored file).
  *(amended 2026-11-03, 31 spec: code anchors corrected — only the `prior_value` and execute-gsd SKILL.md cases of `tests/test_ai_kit_spec_gsd_tools.py` go, since it tests the kept `gsd_tools`; the guidance file is written by curated-config `cross_ai_script.py` and `cli.py --guidance-file`, not `cross_ai_build.py`; `.pre-commit-config.yaml` also lists the removed tests; criterion 3's rtk test exempts usage-metrics' rtk reader, which keeps reading existing data; the installer fix also covers alias spellings and checkout runs (DEF-01 amended))*
  5. Every SKILL.md this phase adds or materially changes meets the judge bar (JDG-04): new-shape evals and tests, no critical or high finding or grade B or better, no regression beyond judge variation.
**Plans**: TBD

### Phase 32: Re-judge baseline
**Goal**: The owner has one current-judge report for every kept skill, which sets the work of the batch phases, and every SKILL.md passes strict frontmatter and history-free text checks.
**Depends on**: Phase 31, Phase 29 (shared jev client, used for JDG-06's judge count)
**Requirements**: JDG-01, JDG-02, JDG-04, JDG-05, JDG-06, JDG-07, JDG-08
**Code anchors**: every `skills/*/SKILL.md`; judge scripts to promote from `.planning/research/2026-11-02-next-milestone/p27-judge-scripts/` (`gates.sh`, `build_report.py`, `digest.py`); new: tracked verdict checker under `tools/` (name unknown until research), strict frontmatter test, skill-text history test, re-judge report; jev score through the Phase 29 shared client; AGENTS.md skill-judge rule (round cap, refute by running, one-line behaviour-not-history rule); the verdict checker's repo-root resolution and round count; docs: AGENTS.md skill-judge rule
**Success Criteria** (what must be TRUE):
  1. A re-judge report scores each of the 15 kept skills with the current judge (two judges chosen from what the environment offers, native opus at xhigh as fallback); old /120 scores appear only as history, and the seven project-rules skills are listed as excluded because they are being replaced; the judge prompt embeds the rubric and its cited spec sources and states one reading of the flat `tests/test_*.py` layout and of skills without `scripts/`, the same for every skill.
  2. The verdict checker is a tracked tool that takes the skill and judge lists as arguments, and it names no referee, resolves the repository root itself (the same digest from a sub-folder) and reports the round count.
  3. The report shows for each skill why one or two judges ran: deterministic signals plus jev's score, a floor of one, two when the last verdict sat within judge noise of a grade boundary or had a high finding.
  4. A strict frontmatter check (strict YAML, 1,024-character description cap, matching what `npx skills` accepts) passes on every SKILL.md in the tree.
  5. A text check fails on tool versions, dates or observation logs in a skill's main flow, a hardcoded referee name, or shipped text pointing into a planning folder; every kept skill passes it, with provenance in a trailing evidence section; ai-kit's AGENTS.md states the rule in one line.
  6. AGENTS.md's skill-judge rule caps a judge loop at a stated number of rounds and requires a disputed finding to be refuted by running the code; the verdict checker flags a loop past the cap.
  7. The judge bar (JDG-04) is recorded per judged skill, and every later phase that adds or changes a SKILL.md has a success criterion that cites it.
**Plans**: TBD

### Phase 32.1: Batch 1, general small skills
**Goal**: `cst-refactor`, `markdown-to-pdf`, `jev-fast-decision`, `ai-kit-spec-review-fixer` and `ai-kit-usage-metrics` reach the judge bar with new-shape evals and tests.
**Depends on**: Phase 32
**Requirements**: JEV-02
**Code anchors**: `skills/cst-refactor/`, `skills/markdown-to-pdf/`, `skills/jev-fast-decision/` (`SKILL.md`, `reference.md`, `scripts/jev_review.py` Zen rung `ZEN_KEY_FILE`, `backends/`), `skills/ai-kit-spec-review-fixer/`, `skills/ai-kit-usage-metrics/`; new: `evals/evals.json` and trigger queries per skill, unit tests; docs: each SKILL.md
**Success Criteria** (what must be TRUE):
  1. Each of the five skills has `evals/evals.json`, about 20 trigger queries (half near-misses) and tests that run in the unit tier.
  2. The re-judge report shows each of the five with no critical or high finding, or grade B or better, and no regression beyond judge variation.
  3. `jev-fast-decision`'s skill text, scripts and tests no longer mention OpenCode Zen.
**Plans**: TBD

### Phase 32.2: Batch 2, spec review family
**Goal**: `ai-kit-spec-review`, `ai-kit-spec-review-checklist`, `ai-kit-spec-config` and `ai-kit-spec-execute` reach the judge bar with new-shape evals and tests, and the cheap-execution ranking works again.
**Depends on**: Phase 32
**Requirements**: HUB-04
**Code anchors**: `skills/ai-kit-spec-review/` (`SKILL.md`, `evals/`), `skills/ai-kit-spec-review-checklist/`, `skills/ai-kit-spec-config/`, `skills/ai-kit-spec-execute/`; cheap-execution ranking in `skills/ai-kit-spec-review/ai_kit_spec/model_ranker.py` (`mechanical` weights and `coding_index` floor) and `references/ranking-weights.toml`; new: evals, null-index catalog fixture; docs: each SKILL.md
**Success Criteria** (what must be TRUE):
  1. Each of the four skills has `evals/evals.json`, about 20 trigger queries (half near-misses) and tests that run in the unit tier.
  2. The re-judge report shows each of the four with no critical or high finding, or grade B or better, and no regression beyond judge variation.
  3. The cheap-execution ranking returns candidates from a catalog fixture where Artificial Analysis gives null coding and agentic indexes.
**Plans**: TBD

### Phase 32.3: Batch 3, execution and session skills
**Goal**: `ai-kit-spec-execute-superpowers`, `ai-kit-cross-ai` and `ai-kit-session-wake` reach the judge bar with new-shape evals and tests, and the four secret-scanner copies become one.
**Depends on**: Phase 32, Phase 29 (shared jev client)
**Requirements**: DEF-02
**Code anchors**: `skills/ai-kit-spec-execute-superpowers/`, `skills/ai-kit-cross-ai/`, `skills/ai-kit-session-wake/`; secret-scanner copies in `skills/ai-kit-session-wake/ai_kit_session_wake/reset_parse.py`, `skills/ai-kit-spec-goal-prompt/scripts/gp_common.py`, `skills/ai-kit-spec-review/references/cross-ai.mjs` (`redactSecrets`), fourth copy unknown until research; new: one shared scanner (home must survive copy installs, DIST-03), evals; docs: each SKILL.md
**Success Criteria** (what must be TRUE):
  1. Each of the three skills has `evals/evals.json`, about 20 trigger queries (half near-misses) and tests that run in the unit tier.
  2. The re-judge report shows each of the three with no critical or high finding, or grade B or better, and no regression beyond judge variation.
  3. One shared secret-shape scanner with more key shapes replaces the four copies; tests show every former caller catches the new shapes, and a copy install of each caller still works.
**Plans**: TBD

### Phase 32.4: Batch 4, planning skills and the closing report
**Goal**: `ai-kit-spec-goal-prompt`, `ai-kit-gsd-spec-discuss` and `ai-kit-gsd-curated-config` reach the judge bar with their known fixes, and the refreshed report shows every kept skill with evals and tests.
**Depends on**: Phase 32.1, Phase 32.2, Phase 32.3
**Requirements**: FLOW-08, FLOW-09, JDG-03, CUR-06, DEF-03, DEF-04, DEF-06, DEF-07
**Code anchors**: `skills/ai-kit-spec-goal-prompt/scripts/` (`gp_render.py`, `gp_sections.py` refusal of long lines), `skills/ai-kit-gsd-spec-discuss/` (`SKILL.md`, `scripts/decide.py`), `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cli.py` (the `review.effort.opencode` write) and `presets.py`; new: evals for the three skills, closing re-judge report; goal-prompt rails in `skills/ai-kit-spec-goal-prompt/scripts/gp_sections.py` (`rail_sections`, `stop_lines`) with `tests/test_ai_kit_spec_goal_prompt_render.py`; goal-prompt entry `goal_prompt.py` (`build_parser`) for the spec-discuss handoff; spec-discuss analyze-mode and auto-mode text in its `SKILL.md`; docs: each SKILL.md
**Success Criteria** (what must be TRUE):
  1. goal-prompt wraps long lists and commands over several lines instead of refusing them.
  2. Each of the eight spec-discuss polish items has a fix and a pinned doc-contract test, including analyze-mode trade-offs written as one header per option with pros and cons bullets and interactive questions that first say what each named item is and who uses it.
  3. curated-config no longer writes `review.effort.opencode = "high"`, and a test pins it.
  4. The refreshed re-judge report shows all 15 kept skills with `evals/evals.json`, trigger queries and tests (JDG-03), each meeting the judge bar (JDG-04).
  5. In auto mode spec-discuss ends by preparing the autonomous-run prompt for the discussed range through goal-prompt, which stops only on a blocker; without goal-prompt it says so and stops.
  6. goal-prompt's rails say when a run may ask the owner, forbid ending a turn with a waiting message while independent work remains, and require the local time, running step and start time in every progress ping, each pinned by a doc-contract test within the prompt's length caps.
  7. spec-discuss lists the recommended run mode first with `(Recommended)`, and its text documents the one-subagent-per-phase interactive relay (questions out in batches, answers back to the same subagent); doc-contract tests pin both.
**Plans**: TBD

### Phase 33: One config design
**Goal**: Every setting ai-kit keeps follows one recorded config design under neutral names, and existing `review-spec.toml` files migrate on their own.
**Depends on**: Phase 32.4
**Requirements**: CFG-01, CFG-02, CFG-03, CFG-04
**Code anchors**: `skills/ai-kit-spec-review/ai_kit_spec/config_io.py`, `trust.py`, `cli.py`, `quota.py`; `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/dispatch_injection.py` (`cfg_resolve`, `assemble_candidates`); runner `cross-ai.mjs` (`aiKitConfigDir`, `loadOverlay`, `workflowValue`, `resolveRetry`); status-line config `tools/common_config.py`; jev consent state in `skills/jev-fast-decision/scripts/jev_review.py`; `ai_kit_spec/local_secrets.py`; new: settings inventory and decision record, migration code; docs: `skills/ai-kit-spec-config/SKILL.md`, README config section
**Success Criteria** (what must be TRUE):
  1. A recorded decision, backed by an inventory of every setting (reviewers and executors with the trust file, hooks, project rules, status line, jev consent, secrets, runner retry), chooses one file with a section per area or one file per concern, project layer over user layer.
  2. A project with an old `review-spec.toml` (local or global) is migrated on the first run with nothing lost, and every caller reads the new config.
  3. The runner reads its retry settings from ai-kit's config; a GSD `config.json` carrying a `workflow.cross_ai_retry` block is migrated once and not read again.
  4. Tests show every config write is atomic and keeps comments, formatting and unrelated entries.
  5. Every SKILL.md this phase adds or materially changes meets the judge bar (JDG-04): new-shape evals and tests, no critical or high finding or grade B or better, no regression beyond judge variation.
**Plans**: TBD

### Phase 34: jev backends by host and Laya calibration
**Goal**: jev picks its backend per host from ai-kit's config, with the home-file key strictly last, and Laya's accuracy is measured against its floor.
**Depends on**: Phase 33
**Requirements**: JEV-01, JEV-03, JEV-07
**Code anchors**: `skills/jev-fast-decision/scripts/jev_review.py` (`LAYA_DEFAULT_URL`, `_laya_url`, `_backend_choice`, `_typesafe_key_sources`, `_keyed_remotes`, `probe_report`); `scripts/eval_cases.py` (`calibrate`, `_run_calibration`); the Phase 33 config reader; jev on/off knob read by `skills/ai-kit-gsd-spec-discuss/scripts/decide.py` (`find_client`, `client_ok`) and the Phase 29 shared client; docs: `skills/jev-fast-decision/SKILL.md`, `reference.md`, new: calibration how-to
**Success Criteria** (what must be TRUE):
  1. jev's probe shows the backend it picked on each host: Laya first at the URL from ai-kit's config (asked once on the first run when no Laya answers), TypeSafe from the environment, the home-file key fallback last; tests run in a scratch home; the probe names a missing key source and the multiplexer hint without printing a value, and the home-file fallback is removed once agent shells inherit the key (or kept with a recorded reason).
  2. A calibration run records Laya's accuracy against its floor and the re-judged opencode judge lane, and the calibration script has a documented how-to.
  3. `jev-fast-decision` keeps its judge result with no regression beyond judge variation.
  4. With the jev knob off every skill behaves as if jev were not installed, and the knob is asked once when absent (scratch-home tests).
**Plans**: TBD

### Phase 35: Model discovery and catalog
**Goal**: spec-config shows every model the machine can reach, with where it was listed from, whether it is usable, and catalog facts labeled by how sure they are.
**Depends on**: Phase 33
**Requirements**: HUB-02, HUB-03, HUB-06, HUB-08
**Code anchors**: `skills/ai-kit-spec-review/ai_kit_spec/detection.py` (`detect_opencode_models`, `detect_cursor_agent_models`, `detect_codex_models`, `parse_*` listings); `model_sources.py` (`fetch_models_dev`, `fetch_artificial_analysis`); `catalog_build.py` (`build_model_catalog`); `model_catalog.py` (`merge_catalog_entry`, `split_catalog_meta`); `model_matcher.py`; `cache.py`; new: Arena source, copilot and pi listing, usability state; opencode entry of the runner's `RUNTIMES` table in `skills/ai-kit-spec-review/references/cross-ai.mjs`; `detection.py` (`parse_opencode_api_models`); attribution in `model_sources.py` (`fetch_artificial_analysis`); docs: `skills/ai-kit-spec-config/SKILL.md`
**Success Criteria** (what must be TRUE):
  1. spec-config lists providers and models from claude, opencode, pi, cursor, codex and copilot, each with where it was listed from and a separate usability state (verified with date, rejected with the error, or visibly unverified).
  2. Each model carries a tier (four or more, effort-aware), class, relative cost, modalities and strengths merged from models.dev, Artificial Analysis and the Arena leaderboard, each value labeled measured or judged, with cache times; each source's required attribution is shown, no Artificial Analysis data is committed or shipped, and Arena data comes from the official CC-BY-4.0 dataset.
  3. Removed models and providers no longer configured are flagged as stale in the output.
  4. The opencode CLI profile and the runner comments match the installed opencode's own `--help` (providers, effort levels, `opencode models` flags), and a test fails on a flag the recorded help lacks.
  5. Every SKILL.md this phase adds or materially changes meets the judge bar (JDG-04): new-shape evals and tests, no critical or high finding or grade B or better, no regression beyond judge variation.
**Plans**: TBD

### Phase 36: spec-config as the hub
**Goal**: Every `ai-kit-spec-*` skill reaches its config through spec-config, and the config keeps reviewers and executors apart with opt-in escalation.
**Depends on**: Phase 35
**Requirements**: HUB-01, HUB-05, HUB-07
**Code anchors**: `skills/ai-kit-spec-config/SKILL.md` and `references/`; `ai_kit_spec/config_io.py`, `model_ranker.py`; missing-config chain in `skills/ai-kit-spec-review/SKILL.md`, `skills/ai-kit-spec-execute/SKILL.md`, `skills/ai-kit-spec-execute-superpowers/SKILL.md`; new: hardcoded-referee test; effort form per runtime in `ai_kit_spec/runner_dispatch.py` (`build_runner_argv`, `runner_flags`); docs: those SKILL.md files, README
**Success Criteria** (what must be TRUE):
  1. Running a spec skill on a project with no config chains spec-config; with spec-config missing it fails with a message naming the fix; `--no-cross-ai` still runs on the session model with no config.
  2. The written config separates reviewers from executors, each with priorities, effort per model and runtime and model escalation flags that are off by default; an effort is passed only when the model supports it, in the runtime's own form, and never dropped silently.
  3. jev ranks the candidates (flagship-class models for review and coding-class models for execution by default) and the owner picks; a test fails when a skill, rail or default hardcodes a referee name.
  4. Every SKILL.md this phase adds or materially changes meets the judge bar (JDG-04): new-shape evals and tests, no critical or high finding or grade B or better, no regression beyond judge variation.
**Plans**: TBD

### Phase 37: Shared runner options and session ids
**Goal**: One runner serves open-gsd cross-AI and ai-kit review and execute, with settings per call and sessions a lane can resume.
**Depends on**: Phase 36
**Requirements**: RUN-01, RUN-02, RUN-06
**Code anchors**: `skills/ai-kit-spec-review/references/cross-ai.mjs` (`parseArgs`, `runCli`, `runOnce`, `sameSessionArgv`, `newSessionArgv`); `ai_kit_spec/runner_dispatch.py`; render path `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai_script.py`, `cross_ai_build.py`; rendered copy `.planning/scripts/cross-ai.mjs`; new: template-vs-copy sync test; docs: `skills/ai-kit-cross-ai/SKILL.md`, `skills/ai-kit-spec-review/references/cross-ai-dispatch.md`, `skills/ai-kit-gsd-curated-config/references/runner.md`
**Success Criteria** (what must be TRUE):
  1. A runner call names runtime, provider and model, effort, escalation flags and the role (review or execute), taken from the config or from the calling skill's decision, and GSD cross-AI and ai-kit lanes both use it.
  2. A call accepts a session id and prints the one it used, and a second round with that id resumes the session (shown with a fake CLI).
  3. A test fails when the rendered project copy drifts from the runner template.
  4. Every SKILL.md this phase adds or materially changes meets the judge bar (JDG-04): new-shape evals and tests, no critical or high finding or grade B or better, no regression beyond judge variation.
**Plans**: TBD

### Phase 38: Runner hardening and run safety
**Goal**: A hung lane no longer burns the whole window, the Phase 25 review cleanup lands, and an execute run neither starts on a checkout another run holds nor counts as done when its commits do not match its plan.
**Depends on**: Phase 37
**Requirements**: RUN-03, RUN-04, RUN-07, RUN-08
**Code anchors**: `skills/ai-kit-spec-review/references/cross-ai.mjs` (new idle watchdog; dead `runCli` state, live-detection plumbing and clamp helpers to remove; tree-state helpers `treeState`, `stateSig`, `evidenceOf`, `gitFailStatus` to build the baseline on; self-test harness moved to a new sibling file); router rule in `ai_kit_spec/model_heuristics.py` (`infer_is_router`, `infer_fallback_quota`) and curated-config's router check; quota-cycle class in `ai_kit_spec_superpowers/dispatch_injection.py` (`classify_dispatch_failure`); curated-config `plan_io.py` (its skill-block code, to call gsd-core's `buildAgentSkillsBlock`); timeout restore in curated-config cleanup (symbol unknown until research); new: run lock and start-of-run baseline record, planned-tasks-versus-commits coverage check; docs: `skills/ai-kit-cross-ai/SKILL.md`, runner.md
**Success Criteria** (what must be TRUE):
  1. With the opt-in watchdog on, a fake lane that stops printing has its process group ended after the set idle time, with an exit from the existing vocabulary; the default does not trip on a slow, quiet fake model, and the runner self-test has a case for it.
  2. The Phase 25 cleanup is visible: one confirmed-router rule, a quota-cycle class, rendered runner copies without the long self-test, the user's lower timeout restored on cleanup, curated-config's `plan_io.py` calling gsd-core's `buildAgentSkillsBlock`, and the dead `runCli` state, live-detection plumbing and clamp helpers gone.
  3. An execute run records a start-of-run tree baseline and takes a run lock: two runs started at once on the same checkout leave one running and the other refused with a clear message, and a stale lock from a dead process is reported and cleared.
  4. A fake execute lane whose commits miss a planned task, that exits early, whose summary admits skipped work, or whose diff touches a forbidden file is reported as partial or failed, never done.
  5. Every SKILL.md this phase adds or materially changes meets the judge bar (JDG-04): new-shape evals and tests, no critical or high finding or grade B or better, no regression beyond judge variation.
**Plans**: TBD

### Phase 38.1: Runner error classification and retry policy (INSERTED)
**Goal**: Every real-run failure the runner sees gets the right class from either output channel, and the retry policy the owner chose sets the runner's defaults.
**Depends on**: Phase 38 (quota-cycle class), Phase 33 (retry settings in ai-kit's config)
**Requirements**: RUN-05, RUN-09, RUN-10, RUN-11
**Code anchors**: `skills/ai-kit-spec-review/references/cross-ai.mjs` (`classifyOne`, `routeOf`, `resolveRetry`, `ladderNext`, `hardWaitFor`, and the Claude usage-limit matcher's stream handling); `references/cross-ai-errors.json`, `ai_kit_spec/cross_ai_catalog.py`, `error_classifier.py`; rendered copy `.planning/scripts/cross-ai.mjs` through the Phase 37 sync test; new: retry-policy decision record, captured router cooldown log fixture; docs: `skills/ai-kit-cross-ai/SKILL.md`, `skills/ai-kit-gsd-curated-config/references/runner.md`
**Success Criteria** (what must be TRUE):
  1. The error catalogue classifies the listed real-run bodies (provider not configured, policy budget 429, data inspection 400, context length 400, a plan-not-open code, 502/503 capacity, copilot's "model not available") and promotes the rows that now have evidence; the model-cooldown class is set from its observed durations (2 minutes to over 2 hours).
  2. A usage-limit message printed on stdout gets the same quota class as one printed on stderr; a test covers both channels.
  3. The router's cooldown wording is classified as a quota cycle with its reset time from a captured log line, or a recorded owner decision says why not.
  4. A recorded owner decision sets the retry policy (soft retries for transient faults, periodic retries for 5xx and quota errors with early-reset checks, the 10-minute and 4-hour ladder against the shipped single wait); the runner's defaults in ai-kit's config follow it, with a test per policy branch.
  5. Every SKILL.md this phase adds or materially changes meets the judge bar (JDG-04): new-shape evals and tests, no critical or high finding or grade B or better, no regression beyond judge variation.
**Plans**: TBD

### Phase 39: Lane capability blocks and lens skills
**Goal**: Every review or execute lane is told exactly the tools and skills it can use, and lens skills present on the machine reach reviewers.
**Depends on**: Phase 37
**Requirements**: REV-03, REV-04, REV-05
**Code anchors**: `ai_kit_spec/reviewer_dispatch.py` (`_reviewer_full_prompt`, `dispatch_reviewer`), `tooling_guidance.py` (`build_tooling_guidance`), `execute_dispatch.py` (`build_execute_guidance`), `runner_dispatch.py` (final argv); skill scan in curated-config `skill_scan.py`; new: role-keyed per-host skill table (home unknown until research), capability block builder; new: optional config-time jev role classifier for unknown skills; docs: `skills/ai-kit-spec-review/references/tooling-guidance.md`, `reviewer-prompts.md`, `SKILL.md`
**Success Criteria** (what must be TRUE):
  1. One role-keyed table of the skills (and MCP servers where a host allows it) present on each host is rescanned every run and read by review, execute and curated-config; an optional config-time jev step sorts an unknown skill into a role, and the owner confirms each sort.
  2. Each lane's prompt carries a capability block built from its final argv (read-only or write, shell or not, the tools found on the child's PATH, codegraph only with an index); a lane without a shell is told about no shell tool.
  3. Lens skills present in the environment (the ponytail family, reducing-entropy, naming-analyzer, simplify, impeccable for UI) reach reviewers by path, and file-editing lenses run as a pass after approval; a lens is inlined where the lane cannot load it by path (Claude built-ins, pi through an allow-listed `--skill`).
  4. Every SKILL.md this phase adds or materially changes meets the judge bar (JDG-04): new-shape evals and tests, no critical or high finding or grade B or better, no regression beyond judge variation.
**Plans**: TBD

### Phase 40: Resilient review sized by jev
**Goal**: A review survives a failing lane, and jev sizes the review and classifies disagreements before the owner is asked.
**Depends on**: Phase 39
**Requirements**: REV-01, REV-02, REV-06, REV-07, REV-08
*(The superpowers fold-step finding was added 2026-11-03 from Phase 29's decision D-03.)*
**Code anchors**: `skills/ai-kit-spec-review/SKILL.md` loop, `ai_kit_spec/reviewer_dispatch.py`, `quota.py`, `routing.py` (`route_all`); `skills/ai-kit-spec-review-fixer/SKILL.md`; jev through the shared client; new: lane ping before a round, beside `route_all` in `routing.py` and `dispatch_reviewer`; docs: `references/apply-findings.md`, `references/loop-diagram.md`
**Success Criteria** (what must be TRUE):
  1. When a lane fails mid-review, spec-review switches to the next lane in the user's preference order and the review finishes.
  2. jev classifies reviewer-fixer disagreements and gray areas before the owner is asked; without jev the owner is asked as before.
  3. jev picks the reviewer and one or two lanes for a plan from files touched, complexity, task count and category, on top of deterministic signals (security, data, irreversible operations), and the review log shows why.
  4. Before a review or judge round each chosen lane is pinged; a fake blocked lane is replaced from the owner's order, the round continues with at least one lane, and the log records which lanes judged.
  6. A superpowers plan fixture without an explicit fold step at its end gets a spec-review finding, and the same plan with the step gets none. *(added 2026-11-03, 29 D-03)*
  5. Every SKILL.md this phase adds or materially changes meets the judge bar (JDG-04): new-shape evals and tests, no critical or high finding or grade B or better, no regression beyond judge variation.
**Plans**: TBD

### Phase 41: Superpowers adapter refactor with spec-config handoff
**Goal**: The superpowers execute adapter has one resume path and one stop path, hands off to spec-config when unconfigured, and every executor brief carries the gates.
**Depends on**: Phase 36, Phase 37
**Requirements**: EXE-01, EXE-04, EXE-05, EXE-08
**Code anchors**: `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/dispatch_injection.py` (`compute_resume_exclusions`, `dispatch_superpowers_task`, `classify_dispatch_failure`, `implementer_status`), `cli.py`, `ai-kit-spec-superpowers.py`; `ai_kit_spec/execute_dispatch.py`, `execute_selection.py`; executor brief template (file unknown until research); real-home guard `AI_KIT_REFUSE_REAL_HOME` in `tools/setup.py`; the runner's execute argv in `cross-ai.mjs` (`runCli`) and `ai_kit_spec/runner_dispatch.py` (`RunnerSpec`); new: before-and-after audit of real host-config modification times; docs: superpowers `SKILL.md` and `references/`
**Success Criteria** (what must be TRUE):
  1. The adapter keeps one pinned-resume path and one owner-stop path, and with no config it hands off to spec-config (this code changes once, in this phase).
  2. With no configured executor available and the fallback flag on, a task runs on the session's own model with jev choosing haiku or sonnet; with the flag off, the error names spec-config as the fix.
  3. Every executor brief lists the unit and arch gates and the commit guard block, and its verify lines pass when a tool prints a version banner; clean-tree checks ignore the owner's config file, the progress counter matches the tasks done, and the agent-branch allow-list applies the same way on every path.
  4. In an ai-kit checkout every executor lane runs with `AI_KIT_REFUSE_REAL_HOME=1`, and a fake lane that touches a real host config is reported from the before-and-after modification times.
  5. Every SKILL.md this phase adds or materially changes meets the judge bar (JDG-04): new-shape evals and tests, no critical or high finding or grade B or better, no regression beyond judge variation.
**Plans**: TBD

### Phase 42: Code review after execution and jev-picked executors
**Goal**: Implementation is reviewed and fixed in a capped loop with the same lanes as spec review, jev picks each executor, and lanes reuse their transport.
**Depends on**: Phase 40, Phase 41
**Requirements**: EXE-02, EXE-03, EXE-06, EXE-07, LENS-02
**Code anchors**: `ai_kit_spec_superpowers/task_classification.py`, `dispatch_injection.py`; `ai_kit_spec/execute_selection.py`; new: capped code-review loop, lane-transport chooser and herdr pane transport, session-id spike record; new: lane-result classifier through the shared jev client, used by `ai_kit_spec/reviewer_dispatch.py` and `dispatch_injection.py` (`implementer_status`); herdr result file and pane sweep; docs: superpowers `SKILL.md`
**Success Criteria** (what must be TRUE):
  1. After implementation, superpowers' `requesting-code-review` runs and ai-kit's capped loop iterates with the same review lanes until the review passes or the cap stops it; jev classifies the gray areas at `receiving-code-review`'s stop-and-discuss point before the owner is asked.
  2. jev picks the executor for a plan or task from what is available (router lite or strong coding models, haiku or sonnet at low, medium or high effort, composer on Cursor, a cheap Copilot model), and the run log shows the pick and why; plans written for a lite executor follow lite instructions.
  3. A spike on session ids and headless resume is recorded; each lane's transport (subprocess, resumed session, herdr pane) is chosen per lane, reused within a plan and renewed after a set number of rounds; this covers execute, spec-review and code-review lanes; a herdr lane reports through a result file, its pane closes at plan close, and a start-of-run sweep closes leftover ai-kit panes.
  4. The post-execution code review loads `ponytail-review`, and `impeccable` when the diff touches UI, from the role-keyed table on the same lanes as spec review; with a lens absent the review still runs and notes it.
  5. jev classifies each lane result (execute: done, partial or another round; review: severity fit by kind, test tier, reproducibility, end-user reach, MVP versus production) before the loop continues; without jev a deterministic default decides and the log says which did.
  6. Every SKILL.md this phase adds or materially changes meets the judge bar (JDG-04): new-shape evals and tests, no critical or high finding or grade B or better, no regression beyond judge variation.
**Plans**: TBD

### Phase 43: curated-config reads docs at the installed tag
**Goal**: curated-config reasons from the open-gsd docs of the installed version and asks its questions as one grouped cascade.
**Depends on**: Phase 32.4
**Requirements**: CUR-01, CUR-02, CUR-10
**Code anchors**: `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/gsd_catalog.py` (`resolve_gsd_tools_path`), `inventory.py`, `cli.py` (question flow), `claude_md_detect.py`, `frontend_detect.py`; new: version-tagged docs fetcher cached under `.aikit/`; the kept v1 path in curated-config `cli.py` (v1 subcommand list unknown until research); new: v1 run record on a fixture project and decision record; docs: curated-config `SKILL.md`
**Success Criteria** (what must be TRUE):
  1. curated-config reads open-gsd docs at the installed version's tag, cached per version under `.aikit/`, and offers a local update only when the changelog makes it worth it, labeled by impact.
  2. Questions come grouped in a cascade: MVP, UI, granularity beside MVP, runtime (Claude preferred, asking when another host is detected), base branch detected from the merge flow.
  3. A recorded run of each v1 curated-config subcommand on a fixture project backs an owner decision to keep, merge or remove each one; no v1 code is removed before its run is recorded.
  4. Every SKILL.md this phase adds or materially changes meets the judge bar (JDG-04): new-shape evals and tests, no critical or high finding or grade B or better, no regression beyond judge variation.
**Plans**: TBD

### Phase 44: curated-config writes the agreed settings
**Goal**: On a fixture project, curated-config writes the agreed profile, routing, models, effort, skills and graph flags through `gsd-tools` and removes nothing it did not plan.
**Depends on**: Phase 43, Phase 39 (shared role-keyed skill table)
**Requirements**: CUR-03, CUR-04, CUR-05, CUR-07, CUR-08, CUR-09, LENS-03
**Code anchors**: curated-config `presets.py`, `recommend.py`, `roles.py`, `critical_agents.py`, `workflow_defaults.py`, `plan_edit.py`, `apply.py`, `skills.py` (`resolve`, `proposals`); `ai_kit_spec/gsd_tools.py` (`GsdTools`); the Phase 39 role-keyed table; `followups.py` (`effort_sync_argv`, `EFFORT_SYNC_HOSTS`) for the per-directory effort sync; `workflow_defaults.py` for `workflow.use_worktrees` and the plan-checker keys (GSD's own default unknown until research); docs: curated-config `SKILL.md`
**Success Criteria** (what must be TRUE):
  1. It sets the balanced profile, dynamic routing, tier models and per-agent models and effort classified with jev, all through the project's `gsd-tools` with effort values validated, and a test shows a setting it did not plan survives.
  2. UI phases and review are on only for UI projects, cross-AI execution asks for confirmation, `response_language` is English, `claude_md_path` names a real AGENTS.md, branch per phase and intel are on; `workflow.use_worktrees` stays on unless the owner turns it off, and the cases where GSD itself turns it off are stated.
  3. Skills are assigned to GSD agents by responsibility from the skills actually available, through the shared role-keyed table.
  4. With graphify installed it turns on `graphify.enabled` and `graphify.auto_update` and says what they do; it never leaves the graph switched off silently.
  5. It proposes the lens wiring from the skills present (`impeccable` only for UI projects, plugin skills only on runtimes that can load them), and run on ai-kit itself it proposes no change to that wiring.
  6. After an effort change it runs `effort sync --apply` for the checkout and a worktree session's launch directory and reports any agent file left with the old effort (fixture with two agents directories).
  7. It sets the GSD keys that make the plan checker re-read a plan amended by review before execution, citing the installed GSD docs, or records that GSD already does this and writes nothing.
  8. Every SKILL.md this phase adds or materially changes meets the judge bar (JDG-04): new-shape evals and tests, no critical or high finding or grade B or better, no regression beyond judge variation.
**Plans**: TBD

### Phase 45: Project rules, one skill and AGENTS.md only
**Goal**: One `ai-kit-project-rules` skill replaces the seven rules skills, reproduces today's audit on ai-kit, adapts to the model it runs on, and turns a Claude-only project into an AGENTS.md project that every host loads.
**Depends on**: Phase 39 (role-keyed skill table for the vertical-slices runbook)
**Requirements**: RULE-01, RULE-02, RULE-04, RULE-10, RULE-11, RULE-27
*(The fold-engine move was added 2026-11-03 from Phase 29's decision D-01.)*
**Code anchors**: `skills/ai-kit-project-rules-{agents,makefile,precommit,arch,docker,cicd,all}/` and `skills/_shared/ai_kit_rules_common/` -> new: `skills/ai-kit-project-rules/` (library inside), `docs/run-book/<topic>.md` writer, model-strength modes (strong, delegated, weak) in its orchestrator; host instruction wiring through ai-kit's atomic writers (`tools/config_doctor_appliers.py` `set_jsonc_value`, `atomic_write_json`; `tools/setup.py` `_atomic_write_json`); their `tests/test_ai_kit_project_rules_*.py`, `tests/test_ai_kit_rules_common.py`, `pyproject.toml`, `tests/test_gate_scope.py` entries; `tools/setup.py` component list (wizard skills card); docs: README skills table, new SKILL.md
**Success Criteria** (what must be TRUE):
  1. `ai-kit-project-rules` replaces the seven `ai-kit-project-rules-*` skills with the shared library inside it, and its audit on ai-kit reproduces today's findings.
  2. On a fixture with only a Claude instructions file, bootstrap asks, migrates it into AGENTS.md, removes the Claude file and adds the line that loads AGENTS.local.md; the audit flags a Claude file that reappears; in a new worktree AGENTS.local.md is a link to the main checkout's file, and Claude's use of the load line stays labeled unverified until a live check records it.
  3. Runbooks land at `docs/run-book/<topic>.md` with a hash header; a developer's edit survives a second bootstrap, and a second bootstrap on an unchanged project gives no diff.
  4. Bootstrap wires every detected host that does not load AGENTS.md and AGENTS.local.md natively (for example opencode's `instructions`) through the atomic writers, a fixture test per host shows both files loaded, and a recorded owner decision settles AGENTS.local.md precedence on Claude.
  5. On a strong model the skill applies its rules itself or delegates areas to subagents with only the orchestrator writing; without subagents it runs the areas in sequence; on a weak model it writes templates only with pending items labeled (a fixture test per mode).
  6. The new skill has evals, trigger queries and tests and passes the judge bar (JDG-04).
  7. The commit-fold engine from Phase 29's temporary `ai-kit-commit-fold` skill lives inside `ai-kit-project-rules`; `skills/ai-kit-commit-fold/` is gone, and the GSD wave-end extension and the superpowers adapter reach the engine in its new home with their tests unchanged in what they assert. *(added 2026-11-03, 29 D-01)*
**Plans**: TBD

### Phase 45.1: Project rules, generated top rules and never list (INSERTED)
**Goal**: The block the rules skill writes into a project's AGENTS.md tells every agent how to build, test, talk to the owner and run unattended, and what never to do, with the reasons.
**Depends on**: Phase 45
**Requirements**: RULE-03, RULE-12, RULE-13, RULE-14, RULE-15, RULE-24, RULE-26, DESIGN-02
**Code anchors**: generated-block writer in `skills/ai-kit-project-rules/` (new in Phase 45); report formatting carried over from `skills/ai-kit-project-rules-agents/ai_kit_project_rules_agents/rule_checker.py` (`check_workflow_rules`) and `rules.py`; the Phase 39 role-keyed table for the vertical-slices runbook; the Phase 29 shared jev client; new: `docs/run-book/` vertical-slices and decisions runbook templates, the project-kind record (API or multi-user, desktop or CLI), fixture projects of each kind; docs: the skill's SKILL.md and references
**Success Criteria** (what must be TRUE):
  1. The generated block carries the top rules and the general never list, placed below the owner's hand-written sections with no collision, repetition or contradiction.
  2. The vertical-slices rule points to a runbook that names the lens skills per stage from the role-keyed table and defines what "visible at the end of phase 1" means for a UI and for an API.
  3. The generated top rules carry the same design rule as ai-kit's AGENTS.md, with its line pointing to a decisions runbook, pinned by a test on a fixture project.
  4. The asking and writing rules are in the block (ask only for a locked-decision ambiguity, a package or security gate or a human-eyes call; say what each item is before asking; package questions lead with purpose and alternatives; plain words, no codes; trade-offs as headers and bullets), and the skill's own report leads each finding with its plain title.
  5. The run rules (no waiting endings, jev at every decision point when installed) and the never list (no real credential files, no command strings from project config, scripts resolve the repo root and search with `--hidden`) are in the block, each pinned by a fixture test.
  6. The block carries the test-run rules with their reasons (parallel by default to save time on large or slow suites, a commented exception set, CPU-share workers a setting may only lower) and requires concurrency tests on shared state for an API or multi-user fixture, while a desktop or CLI fixture gets them as optional.
  7. Every SKILL.md this phase adds or materially changes meets the judge bar (JDG-04): new-shape evals and tests, no critical or high finding or grade B or better, no regression beyond judge variation.
  8. The generated top rules carry the recommended-option-first rule and the verify-host-limits-first rule.
**Plans**: TBD

### Phase 46: Project rules, area runbooks
**Goal**: The rules skill writes working Makefile, CI, README and per-stack setup into a project, and ai-kit itself follows it.
**Depends on**: Phase 45.1
**Requirements**: RULE-05, RULE-07, RULE-08, RULE-09, RULE-16, RULE-25
**Code anchors**: `skills/ai-kit-project-rules/` Makefile, CI and stack parts (from `makefile_checker.py`, the cicd checker, `ai_kit_rules_common/stack_detect.py`, `stack_cache.py`); ai-kit's own `Makefile` (`setup-dev`, `setup-docker`, `setup-env` alias), `.gitlab-ci.yml` and its `include:` files, `AGENTS.md`; new: `docs/run-book/` area runbooks; new: Node stack runbook (pnpm) and testing runbook (parallel runner, exception set, CPU-share workers, concurrency template by project kind); ai-kit's `docker/local/README.md` moved to `docs/run-book/`; docs: README
**Success Criteria** (what must be TRUE):
  1. Fresh Python and Node fixtures bootstrapped by the skill pass `make validate` and `make test`, with `setup-dev`, `setup-docker` (and `setup-env` as an alias), `validate-<category>` aliases only for categories with more than one tool under a cap, and recipes of three lines or fewer. *(amended 2026-11-03, 30 D-04: coupling — `setup-dev` installs the flow's missing tools through guarded steps (RULE-05 amended); ai-kit's own target already ships in Phase 30, FLOW-13)*
  2. The skill chains `crafting-effective-readmes` for the README, a diagram skill for README diagrams, and `agent-md-refactor` through a wrapper.
  3. Per-stack research is time-boxed and cached per category for the five known stacks, and the CI check follows GitLab `include:` files, so it sees ai-kit's include-built `.gitlab-ci.yml`.
  4. ai-kit's own AGENTS.md carries the generated block below the owner's sections, and each of ai-kit's own rule violations is fixed, covered by a rule change, or recorded as an owner decision; the block brings the session-wake rule, the cross-AI runner pointer (GSD-only rules only in GSD projects) and the general test-run and CPU-share rules, and the docker runbook lives under `docs/run-book/`.
  5. A fresh Node fixture gets `pnpm-lock.yaml`, while a project with another lockfile keeps it.
  6. The testing runbook configures parallel unit runs by default (integration and e2e where the stack allows) with a commented exception set and CPU-share workers a setting may only lower; an API or multi-user fixture gets a required concurrency test template on shared state, and a CLI fixture gets it as optional.
  7. Every SKILL.md this phase adds or materially changes meets the judge bar (JDG-04): new-shape evals and tests, no critical or high finding or grade B or better, no regression beyond judge variation.
**Open question (for the phase researcher)**: how to enforce the test-run and concurrency rules (RULE-24, RULE-25), for example a planning-time check, a gate test or a plan-checker criterion; evaluate during planning.
**Plans**: TBD

### Phase 47: Project rules, development-loop playbooks and the quota decision
**Goal**: An agent knows what to do at each development-loop event because the rules skill's playbooks say so, starting from one pointer in AGENTS.md, and where the shared quota logic lives is decided before the quota playbook is written.
**Depends on**: Phase 46, Phase 41 (the superpowers adapter calls the end-of-unit playbook)
**Requirements**: RULE-06, RULE-17, RULE-18, RULE-19, WAKE-03
**Code anchors**: new: playbooks under `skills/ai-kit-project-rules/`, git `post-checkout` hook writer, quota decision record, delegation brief header; end-of-plan call from `skills/ai-kit-spec-execute-superpowers/` (`SKILL.md`, `dispatch_injection.py`); brief builders that take the header: `ai_kit_spec/reviewer_dispatch.py` (`_reviewer_full_prompt`), `execute_dispatch.py` (`build_execute_guidance`), goal-prompt `gp_sections.py` (`rail_sections`); worktree gsd-tools check reusing `ai_kit_spec/gsd_tools.py` (`gsd_tools_candidates`, `local_gsd_core_roots`); `skills/ai-kit-session-wake/` (possible move into a playbook); docs: generated AGENTS.md block pointer, session-wake `SKILL.md`
**Success Criteria** (what must be TRUE):
  1. `git worktree add` on a fixture runs `setup-dev` through the git `post-checkout` hook the skill writes, and a fixture worktree that cannot run its project `gsd-tools` gets a message naming the install step.
  2. The end-of-plan playbook runs the gates and the commit folding, flags a stray untracked file, and flags a close-out count or verdict that differs from the current verdict and summary files; the superpowers adapter calls it at the end of a plan.
  3. Playbooks for session start, CI wait and the PR review loop (reusing an existing feedback skill first) exist and are reachable from the generated block's pointer.
  4. The delegation playbook time-boxes pieces to about 20-30 minutes with one verifiable result each, forbids extra spawned reviewers unless asked and says how to report running agents and shells; its brief header appears in every brief that spec-review, the superpowers adapter and goal-prompt generate.
  5. A recorded decision says where the shared quota logic lives (library, playbook or skill) for session-wake, the rules playbook and the runner; the quota playbook follows it, arms a wake at the reset before stopping, removes it when the run ends, and its pings give the local time, the running step and its start time.
  6. Every SKILL.md this phase adds or materially changes meets the judge bar (JDG-04): new-shape evals and tests, no critical or high finding or grade B or better, no regression beyond judge variation.
**Plans**: TBD

### Phase 47.1: Project rules, lifecycle playbooks (INSERTED)
**Goal**: Requirement intake, audits, milestone close and worktree close each have a playbook, so no owner idea or rule is lost, no live check is asked for that the logs already answer, and no branch or open item is dropped at a close.
**Depends on**: Phase 47, Phase 32.3 (shared secret scanner)
**Requirements**: RULE-20, RULE-21, RULE-22, RULE-23
**Code anchors**: new: intake, audit, milestone-close and worktree-closed playbooks under `skills/ai-kit-project-rules/`, a redacted transcript and log search step (home unknown until research), a branch classifier on `git merge-tree` and `git cherry`, a fixture repository with a rewritten branch; the shared secret scanner from Phase 32.3; the generated block's pointer from Phase 45.1; docs: the skill's SKILL.md, AGENTS.md Workflow (through RULE-09's block)
**Success Criteria** (what must be TRUE):
  1. The intake playbook, run on a fixture with a seeded earlier request, labels it (implemented, partly done, decided otherwise, deferred, lost or claimed but missing) before it becomes a requirement, and routes every owner idea to a requirement and every working rule to a flow agents read.
  2. The audit playbook closes a pending check from redacted transcripts and logs that hold the evidence, and asks for a live run only when they do not.
  3. The milestone-close playbook writes one inputs file of every open item by theme with size, dependencies and who acts, fails the close on an item that lives only in a review note, and moves planning folders dry run first with every reference repointed in one commit.
  4. The worktree-closed and milestone-close playbooks classify a fixture's branches by content, tag a branch that is not hash-merged before deleting it, and run the shared secret scanner and a home-path check before any push.
  5. Every SKILL.md this phase adds or materially changes meets the judge bar (JDG-04): new-shape evals and tests, no critical or high finding or grade B or better, no regression beyond judge variation.
**Plans**: TBD

### Phase 48: Host hooks, spikes and status
**Goal**: The owner can see which ai-kit hooks are on for each host, and the host-hook facts the event catalogue needs are recorded.
**Depends on**: Phase 47.1
**Requirements**: HOOK-01, HOOK-04, HOOK-05, HOOK-06
**Code anchors**: `tools/setup.py` (`HOOK_REGISTRY`, `HOOK_IDS`, `hook_rows`, CLI parser in `main` for new `hooks status`, `Paths` `cursor_hooks`, `wire_hook_cursor`); `tools/hooks/` (`README.md`, `pi/`, `opencode/`); new: spike records; docs: `tools/hooks/README.md`, README hooks section
**Success Criteria** (what must be TRUE):
  1. The spike results are recorded: reset time in Claude's stop-failure event, pi's briefing, opencode child sessions, codex trust under `codex exec`, copilot running `.claude` hooks, background rewake (the owner runs any spike that needs an interactive login).
  2. `setup.py hooks status` on this machine shows which ai-kit hooks are on for each host.
  3. Cursor hooks respect `CURSOR_CONFIG_DIR` as re-verified against current Cursor docs, shown in a scratch-home test; the `cursor-agents` destination is checked against the same split.
  4. The guard spike is recorded per host: which command shapes still stop the flow and why (`cd` first, including into the project folder, then chains, pipes, heredocs and subshells), whether a hook's `ask` prompts under `bypassPermissions` on Claude, and how each guard action compares in stopped-flow count, plus the equivalent (or its absence) on opencode, pi and Cursor.
**Plans**: TBD

### Phase 49: Host hooks, dispatcher and session hooks
**Goal**: One dispatcher hook per host decides at fire time what to run, so switching a hook never rewrites a host config, and session hooks adapt to worktrees.
**Coupling (2026-11-03, from Phase 29's spec)**: the owner wants the commit-folding policy (Phase 29, carried by the Phase 47 playbook) to reach any environment where ai-kit's advisory hook is installed; whether the dispatcher reminds of it at commit or push time is this phase's discuss to decide.
**Depends on**: Phase 48
**Requirements**: HOOK-02, HOOK-03, HOOK-07
**Code anchors**: new: one dispatcher per host in `tools/hooks/` and an event catalogue; `tools/setup.py` (`wire_claude_rows`, `wire_hook_cursor`, `apply_hook_selection`, `wire_hook_rows`); `tools/hooks/claude_session_start.py`, `cursor_session_start.py`, `precompact_core.py`, `claude_precompact.py`; the wizard hooks card from Phase 30.1; layered settings from the Phase 33 design; docs: `tools/hooks/README.md`
**Success Criteria** (what must be TRUE):
  1. Switching a hook on or off changes layered ai-kit settings only; a test shows the host config bytes unchanged, and the dispatcher reads the new state the next time it fires.
  2. The dispatcher reports its launch mode (direct, herdr, subagent, subprocess); a hook advises and never blocks, printing one line naming the playbook to load, and agentless events such as the git hook run only commands from an opt-in list.
  3. Session hooks give indexing advice in a new worktree or checkout naming only installed tools; doc paths are install-relative and reach the model context as well as the user line, tested from a scratch `XDG_DATA_HOME/ai-kit` install; compaction metrics record window size and compaction duration, with inferred numbers flagged.
  4. With the complex-command guard on, a heredoc, a subshell, a `cd` or a chain of three or more segments gets the action HOOK-06's comparison picked (by default the one that stops the flow least), and a denial tells the agent why and what to do instead (drop the `cd`, use absolute paths, write a script under `tmp/`, or split the call); `cmd | head` and `a && b` pass; switching the guard off changes ai-kit settings only.
**Plans**: TBD

### Phase 50: The 5-hour wake grid and limit capture
**Goal**: Wakes are armed on the 5-hour grid and just before a session runs out, built where Phase 47's quota decision put the shared logic, and the next real usage limit is captured.
**Depends on**: Phase 49
**Requirements**: WAKE-01, WAKE-02, WAKE-06
**Code anchors**: `skills/ai-kit-session-wake/ai_kit_session_wake/arm.py` (`arm`, `_refresh_arm`), `state.py`, `hosts.py`; status-line payload readers `tools/claude_payload.py`, `tools/claude_segments.py` (`util_rate_window_seconds`, rate-limit window); stop-failure hook `tools/hooks/claude_session_wake.py`; new: opt-in capture hook; docs: session-wake `SKILL.md` and references
**Success Criteria** (what must be TRUE):
  1. From a status-line payload fixture, a wake is armed on the 5-hour grid from the first detected window (for example 01:01, then every 5 hours, capped at 7 days) and is visible in the wake status; the code sits where Phase 47's quota decision says; two sessions arming the same grid slot at once leave exactly one wake (concurrent arm test).
  2. A wake is armed just before a session is known to run out.
  3. An opt-in capture hook records the field names and a redacted payload of a usage-limit event (tested with a fake; the real capture happens at the next real Claude limit).
  4. Every SKILL.md this phase adds or materially changes meets the judge bar (JDG-04): new-shape evals and tests, no critical or high finding or grade B or better, no regression beyond judge variation.
**Plans**: TBD

### Phase 51: Trustworthy notices and macOS
**Goal**: Desktop notices are checked and readable, and macOS either works through launchd or refuses clearly.
**Depends on**: Phase 50
**Requirements**: WAKE-04, WAKE-05
**Code anchors**: `skills/ai-kit-session-wake/ai_kit_session_wake/fire.py` (`notify`), `units.py` (`render_timer`, `render_service`, `systemd_available`); new: launchd units or refusal, fake notifiers in tests; docs: session-wake `SKILL.md`
**Success Criteria** (what must be TRUE):
  1. Desktop notices check paths before firing, say what was checked, show the host, a short session id, the reason and the journal command long enough to read, and are tested with fake notifiers; a missing session store gets its own text, and a failed notice never fails the wake.
  2. On macOS the wake and notice work through launchd, or arming refuses with a clear "unsupported" message; macOS behaviour stays labeled unverified until the owner runs it on a Mac.
  3. Every SKILL.md this phase adds or materially changes meets the judge bar (JDG-04): new-shape evals and tests, no critical or high finding or grade B or better, no regression beyond judge variation.
**Plans**: TBD

### Phase 52: Script ownership and a committed dist
**Goal**: Every script belongs to the skill or tool that uses it, and a committed `dist/` holds what each skill ships.
**Depends on**: Phase 47.1 (the seven rules skills are gone and every playbook exists before dist vendors anything)
**Requirements**: DIST-01, DIST-03, DIST-05, ARCH-01, ARCH-02
**Code anchors**: orphan list in `.planning/research/2026-11-02-next-milestone/13-orphaned-scripts.md` (for example `ai_kit_spec/cross_ai_catalog.py`); stale jev scratchpad `.planning/docs/system-one-decision-skill/scratchpad/`; new: `dist/skills/<name>/`, dist build script and drift check, group or vendor rule for `skills/_shared/`; `tests/test_arch.py` (`TestArchNonVacuity`) extended to whole-tree layering rules; JSONC scanner and atomic writer copies in `tools/config_doctor_readers.py` (`strip_jsonc_comments`, `read_json_checked`), `tools/config_doctor_appliers.py` (`atomic_write_json`, `atomic_write_text`), `tools/setup.py` (`_jsonc_reader`, `_atomic_write_json`), other copies unknown until research; AGENTS.md Architecture and Testing (the 999.3 mentions), PROJECT.md Out of Scope; docs: README
**Success Criteria** (what must be TRUE):
  1. An orphan check lists no script outside the skill or tool that uses it; the stale jev scratchpad is deleted with its plan and review history kept as research, and dead functions are removed.
  2. A committed `dist/skills/<name>/` is generated from `skills/` without evals and tests, and a rebuild-and-diff check fails on drift.
  3. A copy install of each skill into a scratch home works, with code-sharing skills installed as a group or vendored.
  4. A whole-tree layering test over `tools/` and `skills/` fails on a cross-layer import, a non-vacuity check proves each rule catches its violation, and AGENTS.md and PROJECT.md point to it instead of backlog 999.3.
  5. The JSONC scanner and the atomic JSON writer each have one shared implementation that survives copy installs, and a test fails on a new copy.
**Plans**: TBD

### Phase 53: Install through npx skills and the README
**Goal**: Setup syncs the selected hosts from `dist/` through `npx skills`, and the README documents both install routes.
**Depends on**: Phase 52
**Requirements**: DIST-02, DIST-04, DIST-06, DIST-07
**Code anchors**: `tools/setup.py` install path (`link_one`, `installed_links`, `stale_link_candidates`, `prune_stale`, `_pi_entries`, `cmd_install`, `cmd_install_headless`); `tools/install.sh` (`main`); the wizard commit path (`WizardApp._run_commit`); new: pinned `npx skills add` call with dry run; `tools/setup.py` (`sync_pi_links`, `_headless_link_skills`) for duplicate-free host skill lists; a config-doctor duplicate-skill row; AGENTS.md Architecture (ai-kit installs only its own skills); docs: README install section
**Success Criteria** (what must be TRUE):
  1. Setup shows a dry run, then syncs each selected host headless with one pinned `npx skills add ... -a <host> -g --copy -y` call, passes the CLI's output through, and removes only ai-kit's own links (scratch-home test; the install on this machine runs with the owner's consent); existing ai-kit symlinks migrate to copies, and ai-kit copies of removed or renamed skills are removed with other skills untouched.
  2. The README documents install as a plugin and through `npx skills`.
  3. The wizard's skills card commits through the same `npx skills` sync, confirmed by a run of the wizard under `uv run` with a scratch HOME.
  4. After sync, each host lists every skill once and pi keeps its own list beside codex's shared `~/.agents/skills` (scratch-home test; the config doctor reports duplicates on this machine).
  5. AGENTS.md states that ai-kit installs only its own skills, and an installer test fails when setup writes a skill ai-kit does not own.
**Plans**: TBD
**UI hint**: yes

### Phase 54: Owner-attended live checks and consent items
**Goal**: The items that need the owner, a live host or consent are done and recorded.
**Depends on**: Phase 53
**Requirements**: JEV-04, JEV-05, FEAT-02, FEAT-03, FEAT-04, FEAT-05, DEF-05
**Code anchors**: `cursor-agents/` and new per-file linking in `tools/setup.py`; jev marker block through the `_atomic_write_json`-style writers (target files unknown until research); `skills/jev-fast-decision/scripts/jev_review.py` image and box builders; live-check records; `.planning/todos/pending/`, git tags, `.planning/WINDOWS.md`; owner-attended live-check records; the two archived June branches against the split status line (`tools/claude_segments.py`; external segment providers unknown until research); docs: jev `SKILL.md`, README Cursor agents
**Success Criteria** (what must be TRUE):
  1. The pinned Cursor subagents link per file into a project's `.cursor/agents` with a `--skills`-style selection, never overwrite a non-ai-kit file and remove only ai-kit's links; docs say where and why not `~/.cursor/agents`; Cursor's explore-subagent model knob is checked; the owner confirms one run as non-fast in the Cursor usage dashboard.
  2. The agent-run live checks (real wake resume, wake during a GSD prompt, pointer form, native-execution and done-when wording, quota-checked task, chain without a decision backend, pi model-name grammar, background permission mode, launch-and-wait for opencode and pi, large-roadmap detection) run with herdr and a scratch home, and each result is recorded.
  3. With the owner's consent, a short jev marker block reaches the four global instruction files through ai-kit's atomic writers. *(amended 2026-11-03, 30 spec: through the marked-block editor Phase 30 builds for FLOW-12)*
  4. After a TypeSafe spike with a key and consent, jev answers image and bounding-box questions; a named caller judges a delivered screen against a mockup, the request limits are recorded as live facts, and the Laya cell is re-checked.
  5. Housekeeping is done: the six delivered v1.3 todos are closed, the two unneeded tags dropped, the stale archived wording decided, Windows ledger entry 7 waived, and the v1.3 tag pushed with the owner's consent; the remaining archive tags are kept or dropped by recorded decision.
  6. The owner-attended live checks are recorded (the next real Claude limit's payload, output channel and resume behaviour; reboot survival of the wake and notices; the Cursor status line after login; the Phase 21.2 PreCompact delivery; the Phase 21.3 hook matrix on opencode; optionally pi steering), each flipping or keeping its unverified label. *(amended 2026-11-03, 30.1 D-20: plus whether `env.PLAYWRIGHT_MCP_EXECUTABLE_PATH` reaches the Playwright plugin's MCP process and whether a headed launch through the flatpak Chrome wrapper works)*
  7. A recorded owner decision ports or drops each of the two June ideas; a port lands on the split status line with tests.
  8. Every SKILL.md this phase adds or materially changes meets the judge bar (JDG-04): new-shape evals and tests, no critical or high finding or grade B or better, no regression beyond judge variation.
**Plans**: TBD

## Progress

**Execution Order:** 28 → 29 → 29.1 → 30 → 30.1 → 30.2 → 31 → 32 → 32.1 → 32.2 → 32.3 → 32.4 → 33 → ... → 38 → 38.1 → 39 → ... → 45 → 45.1 → 46 → 47 → 47.1 → 48 → ... → 54

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 28. Fast, environment-proof gates | 0/TBD | Not started | - |
| 29. Logical-commit folding and the shared jev ladder | 0/TBD | Not started | - |
| 29.1. Stacked phase branches, chained PRs and the merge chain | 0/TBD | Not started | - |
| 30. Phase-boundary index refresh and code-exploration rules | 0/TBD | Not started | - |
| 30.1. Setup wizard, component cards and host status-line panes | 0/TBD | Not started | - |
| 30.2. Cursor status-line parity | 0/TBD | Not started | - |
| 31. Removals and small defects | 0/TBD | Not started | - |
| 32. Re-judge baseline | 0/TBD | Not started | - |
| 32.1. Batch 1, general small skills | 0/TBD | Not started | - |
| 32.2. Batch 2, spec review family | 0/TBD | Not started | - |
| 32.3. Batch 3, execution and session skills | 0/TBD | Not started | - |
| 32.4. Batch 4, planning skills and the closing report | 0/TBD | Not started | - |
| 33. One config design | 0/TBD | Not started | - |
| 34. jev backends by host and Laya calibration | 0/TBD | Not started | - |
| 35. Model discovery and catalog | 0/TBD | Not started | - |
| 36. spec-config as the hub | 0/TBD | Not started | - |
| 37. Shared runner options and session ids | 0/TBD | Not started | - |
| 38. Runner hardening and run safety | 0/TBD | Not started | - |
| 38.1. Runner error classification and retry policy | 0/TBD | Not started | - |
| 39. Lane capability blocks and lens skills | 0/TBD | Not started | - |
| 40. Resilient review sized by jev | 0/TBD | Not started | - |
| 41. Superpowers adapter refactor with spec-config handoff | 0/TBD | Not started | - |
| 42. Code review after execution and jev-picked executors | 0/TBD | Not started | - |
| 43. curated-config reads docs at the installed tag | 0/TBD | Not started | - |
| 44. curated-config writes the agreed settings | 0/TBD | Not started | - |
| 45. Project rules, one skill and AGENTS.md only | 0/TBD | Not started | - |
| 45.1. Project rules, generated top rules and never list | 0/TBD | Not started | - |
| 46. Project rules, area runbooks | 0/TBD | Not started | - |
| 47. Project rules, development-loop playbooks and the quota decision | 0/TBD | Not started | - |
| 47.1. Project rules, lifecycle playbooks | 0/TBD | Not started | - |
| 48. Host hooks, spikes and status | 0/TBD | Not started | - |
| 49. Host hooks, dispatcher and session hooks | 0/TBD | Not started | - |
| 50. The 5-hour wake grid and limit capture | 0/TBD | Not started | - |
| 51. Trustworthy notices and macOS | 0/TBD | Not started | - |
| 52. Script ownership and a committed dist | 0/TBD | Not started | - |
| 53. Install through npx skills and the README | 0/TBD | Not started | - |
| 54. Owner-attended live checks and consent items | 0/TBD | Not started | - |

## Backlog

v2.0 requirements cover these entries (kept here until `/gsd-review-backlog` removes them): 999.1 (FEAT-01, Phase 30.1),
999.2 (HOOK-04), 999.5 (RUN-03), 999.7 (FEAT-02), 999.8 (JEV-05), 999.9 and 999.10 (JEV-01), 999.11 (DEF-04),
999.12 (RUN-04), 999.14 (DIST-02), 999.15 (RUN-01, RUN-07, RUN-08, EXE-07; no new skill), 999.16 (RULE-01), 999.17 (EXE-03, JEV-06). The Playwright MCP Chrome path row in 999.1 is the FEAT-06 owner decision. The whole-tree layering suite once named 999.3 is ARCH-01 (Phase 52).
999.13 is dropped as written (see REQUIREMENTS.md Out of Scope). 999.6 stays open (secondary runtime).

### Phase 999.1: Config Doctor reachable from the setup wizard (BACKLOG)

**Goal:** [Captured for future planning] Config Doctor (v1.0 Phase 4) is a
standalone `textual` TUI reached only through `setup.py --config-doctor`; the
setup wizard (`tools/wizard_app.py`: housekeeping, Choose, Arrange, Review,
Done) never offers it, and `make doctor` runs the different status-line
doctor. Make Config Doctor reachable from the wizard (for example an entry on
the Done step, or a dedicated step) reusing the existing stdlib-only engine
(`config_doctor_checks.py` / `config_doctor_readers.py` /
`config_doctor_appliers.py`) and `config_doctor_app.py` screen, with no second
implementation. Coordinate with v1.3 Phase 23 C2 (per-host
status-line step); `worktree-context-tools-manager-plan1` no longer lands (2026-10-14). Candidate rows to add later: the Playwright MCP Chrome path
on Bazzite. Rewritten 2026-10-13 from the former "shared core for a CLI
variant" note, whose goal (engine not coupled to the TUI) is already met.
**Requirements:** TBD
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

**Moved 2026-10-13:** the host-split status line (former 999.4) was promoted to
v1.3 Phase 23 on branch `gsd/v1.3-curated-config-v2`; former 999.3 was removed
(resolved by v1.2 Phase 12; see git history).

### Phase 999.2: Cursor hooks path ignores CURSOR_CONFIG_DIR (BACKLOG)

**Goal:** [Captured for future planning] `tools/setup.py`'s single `Paths.cursor_dir`
(`CURSOR_CONFIG_DIR` or `~/.cursor`) is used for Cursor hook wiring, but the Cursor CLI
(2026.10.01 bundle) always reads user hooks from `~/.cursor/hooks.json` and ignores both
`CURSOR_CONFIG_DIR` and `XDG_CONFIG_HOME`. When `CURSOR_CONFIG_DIR` is set, ai-kit writes hooks
where the CLI never looks. Resolve the hooks path separately from the config dir (Phase 23 D-21
adds the config-dir resolver for the status line), re-verify against current Cursor docs, and
check Phase 21's `cursor-agents` destination against the same split. Found by the Phase 23
assumptions analysis, 2026-10-14.
**Requirements:** TBD
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.5: Idle watchdog for the cross-AI runner (BACKLOG)

**Goal:** [Captured for future planning] The Phase 18 cross-AI runner
(`.planning/scripts/cross-ai.mjs`, rendered from the ai-kit-spec-review template) kills the
child's process group only at the overall deadline (outer `workflow.cross_ai_timeout` minus the
D-29 margin). A child that hangs without output burns the whole window. Add an opt-in idle
watchdog: kill the process group after N seconds with no stdout/stderr growth, then exit with the
existing status vocabulary (a `retry-later` or `fallback` action, never a new exit class). It needs
a self-test case and a default that is safe for slow, quiet models. Deferred by 18 D-43
(RUN-46, 2026-10-15): not required by SPEC R5/D-27, and the runner is the largest new code in
Phase 18.
**Requirements:** TBD
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.6: Codex interactive TUI confirmation (secondary runtime) (BACKLOG)

**Goal:** [Captured for future planning] Run `20-INTERACTIVE-CODEX.md` from a real codex TUI
session to confirm EVAL-04 (codex session env signal, smoke, snapshot) beyond the headless
`codex exec` evidence in `20-SMOKE-CODEX.md`, then promote or rename the "live-verified (Phase 20)
… TUI confirmation pending" labels in `detection.py`. Deferred 2026-10-18 by owner decision: the
primary runtimes are claude, opencode and pi; codex and cursor are secondary (their models remain
usable as reviewers and executors). The headless evidence and the pending label stay as they are.
**Requirements:** EVAL-04
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.7: Cursor project-level subagent linking (BACKLOG)

**Goal:** [Captured for future planning] ai-kit's pinned Cursor subagents (`cursor-agents/`,
shipped by Phase 21) reach the cursor CLI: they are linked per file into a project's
`.cursor/agents`, the only subagent root the CLI reads (Phase 21 D-01 spike, 2026-10-18), and a
live delegation shows each pinned model. Success criteria when promoted: (1) a tested ai-kit path
links `cursor-agents/*.md` per file (never a directory) into a chosen project's `.cursor/agents`,
mirrors `--skills` selection (`all|name1,name2`, unknown name exits 1 naming it), never overwrites
a non-ai-kit file and removes only its own links; (2) a headless delegation from a cursor parent
shows each pinned model in the Task call, and the user confirms one run as non-fast in the Cursor
usage dashboard; (3) docs say where the agents are linked and why `~/.cursor/agents` is not used.
Inputs: `21-SPIKE-D01.md`, 21-CONTEXT D-02..D-05. Moved out of the inserted Phase 21.1 on
2026-10-18 by owner decision (cursor is a secondary runtime; Phase 21 documents manual linking).
**Requirements:** AGT-02
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.8: Jev image and box questions (BACKLOG)

**Goal:** [Captured for future planning] The `jev-fast-decision` client builds image questions
(one image, and several compared) and `box` questions on every backend whose 21.1 capability
matrix cell is `verified-live` or `documented`, so a flow can ask Jev to judge a UI state against
a reference screenshot. Success criteria when promoted: (1) a spike against TypeSafe direct (key
and consent present) records the request shape, size limits (PNG/JPEG, 280-1568 px, 16 MiB per
file, 32 MiB per request) and the danger-zone header as live facts; (2) stub-tested request
builders for images and `box`, gated by the matrix; (3) the Laya and Zen cells are re-checked.
Deferred 2026-10-18 from Phase 21.1 (D-21): no in-scope caller sends images, and no TypeSafe key
or consent was available to verify the shapes live.
**Requirements:** (none yet)
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.9: jev-fast-decision backend detection and selection by host (BACKLOG)

**Goal:** [Captured for future planning; rewritten 2026-10-24 from "drop the OpenCode Zen backend"
after the owner's follow-up] The client picks a backend through explicit, host-aware detection
instead of a fixed Laya -> TypeSafe -> Zen ladder:
1. **Laya first:** the default Laya URL lives in ai-kit's config `.toml` as a knob (default
   `http://127.0.0.1:8010`). The client probes `/health` there. The first time no Laya answers, it
   asks the user once whether a Laya instance exists (and where) and stores the answer in the knob.
2. **TypeSafe second:** the key is resolved from the environment (`TYPESAFE_API_KEY`). If it is
   missing, the client tells the user it must be in the env, or that the user can pass it or save
   it in ai-kit's `.toml` (owner option). The transitional file fallback is backlog 999.10.
3. **OpenCode Zen third, only where it is legitimate:**
   - The free `jev-*-free` model is used only when the host harness IS opencode and an OpenCode
     Zen provider is configured. It never runs under OpenCode Go or any other host.
   - Under pi, Zen (non-free) may be used through the owner's linked subscription.
   - Under Claude Code or Cursor, Zen is used only with an explicit token and URL.
   - Otherwise the Zen rung is skipped with a reason.

Owner note (2026-10-24): undecided whether to keep Zen at all, which is why it is gated, not
deleted. **Current state (verified 2026-10-24, before this work):** the Laya URL is hard-coded
with env overrides (no `.toml` knob, no first-run question). The Zen rung exists with free-tier
first and has no host/provider gating. `consent grant opencode` exists. Success criteria when
promoted: (1) detection table per host (claude, cursor, pi, opencode) with tests on synthetic
configs; (2) the free model is never selected outside opencode-with-Zen; (3) the `.toml` knob and
first-run question are covered by tests in a scratch HOME; (4) the skill-judge gate passes with
the owner's judge set.
**Requirements:** (none yet)
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.10: TypeSafe key sources, the transitional ~/.mycreds fallback and env inheritance (BACKLOG)

**Goal:** [Captured for future planning; updated 2026-10-24] The TypeSafe key normally comes from
the environment (`TYPESAFE_API_KEY`, sourced by the owner's shell from `~/.mycreds`, 0600).
**Done on the v1.3 branch (9d9c181, not yet merged to main at capture time):**
- the client reads `~/.mycreds` as a transitional fallback (line parse, no `source`, no export to
  children, 0600 enforced);
- `--probe` reports `key_source` and an ordered `key_expected` list without values.

**Still open:**
- (a) make `~/.mycreds` strictly the last source (it currently sits before `state`);
- (b) document env inheritance: a long-lived terminal multiplexer server (herdr, observed
  2026-10-24) keeps the environment it started with, so panes it spawns lack a newly sourced
  variable until that server restarts, while a new Konsole/Kitty tab has it — no machine reboot
  needed;
- (c) remove the fallback once agents inherit the env;
- (d) the `.toml` storage option from 999.9 step 2, if the owner keeps it.

Success criteria when promoted: (a)-(c) done with tests on synthetic files; the probe names the
missing source and the inheritance hint without printing any value.
**Requirements:** (none yet)
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.11: ai-kit-gsd-spec-discuss polish after the Phase 24 close-out (BACKLOG)

**Goal:** [Captured for future planning] Resolve the Important findings left at the Phase 24
skill-judge r3 PASS (`24-SKILL-JUDGE.md`, digest 7fc3f03ffb2fb714): a forced local answer that
matches no decision-table row; "one commit per phase" vs the spec workflow's own commit; analyzer
start while the same phase's CONTEXT is written; `state.record-session` on an early stop; trigger
keywords late in the description; the agent's action on `no_client`/`incompatible_client`.
Success criteria when promoted: each fixed with a pinned doc-contract test, and the owner's judge
set (native Opus + my-referee-one + my-referee-two) scores no Important.
**Requirements:** (none yet)
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.12: Runner and adapter cleanup after the Phase 25 reviews (BACKLOG)

**Goal:** [Captured for future planning] Cut what the Phase 25 code and ponytail reviews
(`25-REVIEW.md`) found unneeded or duplicated, with no behavior change:
- one "confirmed router" rule shared by Python's catalog `fallback_quota` and curated-config's
  `is_router`/`router_confirmed`/execute;
- a `quota_cycle` class from superpowers' `classify_dispatch_failure`, instead of three shell
  JSON parses in its SKILL;
- `plan_io.py` calls gsd-core's `buildAgentSkillsBlock` instead of re-implementing its
  skill-resolution rules;
- dead `runCli` state, the live-detection plumbing and the clamp helpers (IN-01, IN-03);
- the runner's embedded self-test harness (about 3,300 lines) moves to a sibling file that
  rendered copies do not carry;
- the lower user `cross_ai_timeout` is restored on cleanup (WR-05).

Success criteria when promoted: each change keeps the runner self-test, `make test` and
`make validate` green, and the template still renders a pristine copy.
**Requirements:** (none yet)
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.13: Register workflow.cross_ai_retry with gsd-core so config-set accepts it (BACKLOG)

**Goal:** [Captured for future planning] Ship a gsd-core capability manifest that registers
`workflow.cross_ai_retry.*`, so `config-set workflow.cross_ai_retry.<key>` validates and writes the
key instead of the owner hand-editing `.planning/config.json` (Phase 25.1 D-02). Starting evidence
(25.1-RESEARCH.md Q2): gsd-core 1.17.0 composes federated capability config keys from
`capability.json` manifests under `$GSD_HOME/.gsd/capabilities/<id>/` (global) or
`<project>/.gsd/capabilities/<id>/` (project); a project-scope capability needs a consent record
keyed to the project's realpath and its bundle hash, or it stays discovered-but-inactive. Open:
the exact manifest fields, whether a list-typed key such as `hard_waits_s` is accepted, the
global versus project scope choice and the consent gate.
**Requirements:** (none yet)
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.14: Install ai-kit skills as real copies through the skills CLI, synced across hosts (BACKLOG)

**Priority:** major. This is the next feature to implement after v1.3.
**Goal:** [Captured for future planning] The setup installs each ai-kit skill into a host as a
symlink. Replace that with real (non-symlink) installs done through the existing `skills` CLI
(`npx --yes skills add <owner/repo or local path> --yes`; the exact subcommands, flags, target-host
selectors and non-interactive behavior are unverified and must be checked live before planning).
The same layer must install, remove and sync the skills in each supported host: pi, cursor,
copilot, codex, opencode and claude. Open: how a local path is copied instead of linked; how
sync detects drift (a removed skill, a changed `SKILL.md`, a renamed directory); how it migrates
existing symlinks without touching unrelated user skills; and how it relates to `tools/setup.py`
atomic writes and backups, the dry-run-first rule, and the scratch-HOME rule for tests and e2e.
**Requirements:** (none yet)
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.15: A cross-AI chain skill for execute and review runs (BACKLOG)

**Priority:** major. It builds on the todo "Unify the review/execute lane TOML".
**Goal:** [Captured for future planning] Turn the xai execute/review scripts used in v1.3 into a
portable Agent Skill (suggested name `ai-kit-cross-ai-chain`, beside the single-call
`ai-kit-cross-ai`) that bundles the script as an asset and carries the calling convention:
an explicit `--role execute|review` with per-role rails, confinement, timeouts and done
criteria; run in the background and wait for the notification; read the AIKIT-XAI status line;
the retry ladder (same-session resume x3, then a new session x3; never switch harness, provider
or model); coverage gates behind verify (tasks versus tagged commits, early exit, SUMMARY
admissions, forbidden-file diff); a start-of-chain tree baseline and a run lock; an append-only
run ledger; an informational-versus-blocking Issues taxonomy; a classifier for execute results
(done, partial, another round) and for review results (severity fit by problem kind, test tier,
reproducibility, end-user reach, MVP versus production; converge, continue or escalate). Runtime,
model, effort, timeout and polling rate are decided, not hard-coded, optionally through the
decision system behind the TOML knob (never a hard dependency). Evidence, incident catalogue and
the ten ranked recommendations: `.planning/phases/999.15-cross-ai-chain-skill-for-execute-and-review-runs/999.15-LESSONS.md`.
**Requirements:** (none yet)
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.16: Evaluate one event-keyed playbook skill for the ai-kit-project-rules-* family (BACKLOG)

**Priority:** major. Decide it together with the todo "Refactor execute-gsd and rules-agents (SJ-1, SJ-3)".
**Goal:** [Captured for future planning] Owner request (2026-10-30): evaluate whether the rules should
become a single skill with several event-keyed playbooks or runbooks, so AGENTS.md is not
overloaded and the agent knows what to do in each case. The events: a new project (create
Makefiles, pre-commit hooks, tests, verifications); a new worktree is created; a plan or phase
finishes in open-gsd; a worktree is closed; a subagent is delegated; quota errors appear.
**Problem:** AGENTS.md carries too many workflow rules. The family today is seven sibling checkers
(agents, makefile, precommit, arch, docker, cicd, plus `ai-kit-project-rules-all` as the wrapper),
and skill-judge kept finding new detail in the big skills (Phase 26: execute-gsd and
rules-agents were accepted as-is and deferred).
**First step (mandatory):** a feasibility check against the already confirmed architecture, before
anything is built. Questions: is one skill with event-keyed runbooks better than the siblings (what
does it gain and lose for routing, skill-judge size, host portability); what would the trigger be
for each event on each host (a skill description, a hook, a manual call; claude, opencode and pi
are primary, codex and cursor secondary); how does it relate to `ai-kit-session-wake` (quota
events) and the execute skills (`ai-kit-spec-execute-gsd`, `ai-kit-spec-execute-superpowers`: phase
finish, subagent delegation). Nothing is built before this check; its result may be to keep the
siblings.
**Requirements:** (none yet)
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)

### Phase 999.17: Lite or strong executor choice through jev-fast-decision (BACKLOG)

**Priority:** major. Depends on the todo "Refactor execute-gsd and rules-agents (SJ-1, SJ-3)" (same skills, resume paths).
**Goal:** [Captured for future planning] Let the executor of a plan be chosen between a lighter
local combo (`my-coding-lite`), `my-coding`, or a model the user names explicitly, in
`ai-kit-spec-execute` and its `-gsd` and `-superpowers` adapters, deciding by asking the
`jev-fast-decision` skill; and let `ai-kit-spec-review` adapt the writing-plans instructions to a
lighter executor (`EXECUTOR_PROFILE=lite`). Requested by the llm-env project.
**Hard rule (owner):** `jev-fast-decision` is a black box. ai-kit text says only: ask that skill,
follow its own `SKILL.md`, the answer is advisory, and `needs_fallback` or no answer means the
rule-based default decides. No text about how it picks local versus remote, consent, TypeSafe,
environment variables or probes; the call line is re-read from the jev skill's own `SKILL.md`
when built, never copied.
**Reference input (not to be applied blindly):** six patches against the old main (f669709), an
implementation plan and a JEV-NOTES file listing the jev wording to strip, kept in the llm-env
project (its `tmp/ai-kit-lite-executor-patches` folder and
`docs/superpowers/plans/2026-10-30-ai-kit-lite-executor-routing.md`).
**Timing:** after the v1.3 milestone is merged to main (the patches must be re-made against the
new main); build it on the refactored execute-gsd and execute-superpowers resume paths (see the
SJ-1/SJ-2/SJ-3 refactor todo).
**Gates:** skill-judge with the current percent-based judge (needs `README.md` and `evals/` in
each changed skill), arch and unit tests, and a GSD-first waiver note recorded by the owner.
**Requirements:** (none yet)
**Plans:** 0 plans

Plans:

- [ ] TBD (promote with /gsd-review-backlog when ready)
