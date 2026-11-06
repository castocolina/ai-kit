---
phase: 30-phase-boundary-index-refresh-code-exploration-rules-and-lens
plan: 02
subsystem: docs
tags: [agents-md, house-rules, graphify, codegraph, design-rule, doc-contract]
requires: []
provides:
  - "One code-exploration rule text (RULE_CLAUSES) carried by AGENTS.md, house rules R07/R08"
  - "docs/run-book/graphify.md: Build, Refresh, Check freshness, Query"
  - "AGENTS.md Design rule bullet and make setup-dev Commands line"
affects: [30-05, 30-06, 30-07]
key-files:
  created:
    - skills/_shared/ai_kit_rules_common/code_exploration.py
    - docs/run-book/graphify.md
    - tests/test_rules_docs.py
  modified:
    - AGENTS.md
    - skills/ai-kit-project-rules-agents/ai_kit_project_rules_agents/rules.py
    - tests/test_ai_kit_rules_common.py
    - Makefile
    - .pre-commit-config.yaml
decisions:
  - "R08 summary index set is (2, 6, 7), not the plan's (2, 6): clauses 2 and 6 name no graph.json or graphify-out, and the plan's own test requires the R08 summary to name both. Chosen via jev (typesafe) and confirmed by the passing tests."
  - "The R07/R08 summary test lives in tests/test_rules_docs.py, not tests/test_ai_kit_project_rules_agents.py."
metrics:
  duration: "about 8 min of execution (10:43 to 10:51 local), plus the make test run"
  completed: "2026-11-05"
  tasks: 2
  files: 8
status: complete
actuals:
  tokens: 9485
  tasks: 2
  commits: 2
commits: 2
plan_head_before: 9cf58016578c7435caef6d00ca6f67185bcf3cce
plan_head_after: fea5967a77f1066c0951a6658be38c2e51111f10
---

# Phase 30 Plan 02: One code-exploration rule, graphify runbook, design rule Summary

One 13-clause code-exploration rule in `RULE_CLAUSES` now feeds AGENTS.md and house rules R07/R08, with the graphify runbook, the design rule bullet and the `make setup-dev` Commands line, each pinned by doc-contract tests.

## Performance

- **Tasks:** 2 of 2 complete
- **Commits:** 2 logical commits (`21dc09e`, `fea5967`)
- **make test:** exit 0; every runner group reported all modules passed (89/89, 1/1, 6/6, 24/24, 1/1; log at `tmp/p30/02/test-run.log`, lines 91, 94, 102, 128, 179)
- **make pyright:** passed

## Accomplishments

- `RULE_CLAUSES` (13 sentences) is the single source; AGENTS.md `## Code Exploration` carries each clause verbatim as a bullet; R07 and R08 `summary` read `R07_SUMMARY` / `R08_SUMMARY`.
- `docs/run-book/graphify.md` has the four ordered sections, timings labelled "measured on 2026-11-03 on this machine", GSD thresholds attributed to gsd-core 1.20.0, and the lock and location facts.
- AGENTS.md Non-Negotiable Rules gained the `**Design rule**` bullet (owner-written part, first bullet); Commands gained `make setup-dev` beside `setup-env` and `dev`.
- `tests/test_rules_docs.py` pins the clauses, design clauses, runbook headings and phrases, and Commands lines, each with a remove-one non-vacuity test; `tests/test_ai_kit_rules_common.py` checks each clause is one sentence and none repeats.

## Task Commits

1. **Task 1: one code-exploration rule in AGENTS.md and house rules R07/R08** - `21dc09e` (feat)
2. **Task 2: graphify runbook, design rule and setup-dev command** - `fea5967` (docs)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] R08 index set contradicted its own test**
- **Found during:** Task 1
- **Issue:** The plan fixes `R08_CLAUSES = (2, 6)` but requires the R08 summary to contain `graph.json` and `graphify-out`. Clauses 2 and 6 contain neither.
- **Fix:** `R08_CLAUSES = (2, 6, 7)`; clause 7 names `graphify-out/graph.json`. R08 signals in `rules.py` unchanged.
- **Files modified:** `skills/_shared/ai_kit_rules_common/code_exploration.py`
- **Commit:** `21dc09e`

**2. [Rule 3 - Blocking] Lint failures**
- **Found during:** Task 1 and Task 2
- **Issue:** Ruff E501 on long clause strings; RUF100 on unused `noqa` markers in the new test module.
- **Fix:** Clause strings split by implicit concatenation (text unchanged, verified by the rules-common and doc-contract tests); unused `noqa` removed.
- **Commit:** `21dc09e`

**3. [Placement] Summary-to-dict test location**
- **Issue:** The plan puts the R07/R08 dict test in `tests/test_ai_kit_project_rules_agents.py`. I put it in `tests/test_rules_docs.py` (`TestHouseRulesCarryTheSharedSummaries`) to keep the doc-contract tests together. Same assertions.
- **Commit:** `21dc09e`

## Known Gaps (not fixed in this plan)

- **`make setup-dev` does not exist yet.** The Makefile has only `setup-env` and `dev`. The AGENTS.md Commands line names `make setup-dev` as the plan asks; that target lands with plan 05. Until then, the Commands line documents a target this worktree cannot run.
- **`fold.py boundary --next --point plan` does not exist in this worktree yet.** Clauses 11 and 12 point at it; plan 04 adds it. The route is documented but not runnable here.
- **Required reading only partly done.** Read in full: the plan, plan 01's rails and scope.py spec, `AGENTS.md`, the jev brief, the jev skill's request section. Not read in full before the deadline: `30-SPEC.md`, `30-CONTEXT.md`, `30-RESEARCH.md`, `30-PATTERNS.md`, `30-VALIDATION.md`, `30-REVIEWS.md` (the plan's embedded ledger was used instead), `.planning/PROJECT.md`, `.planning/STATE.md`, `.planning/config.json`, and the `execute-plan.md` workflow. Task work followed the plan text; a reviewer should check it against those documents.
- **Commit trailer.** Commit `21dc09e` carries an `Ai-Kit-Phase: 30` trailer I added; the plan did not ask for it.

## User-owned items

- The owner confirms the superpowers before-planning route in clause 12 (`python3 <fold skill>/scripts/fold.py boundary --next --point plan`, handing `.aikit/brief/SKILL.md` to the plan writer). Recorded here as a user-owned item, not a stop. Target projects receive the route through Phase 45.1's generated rules block (RULE-03), outside this phase.

## Decisions Made

- R08 index set `(2, 6, 7)`. Recorded in Deviations #1.
- The R07/R08 summary test lives in `tests/test_rules_docs.py`. Recorded in Deviations #3.

## jev Call Log

- Call 1 (`ladder`, R08 index set): rejected with `invalid_input` for a missing subcommand (I first ran the script without `ladder`); no backend ran.
- Call 2: rejected with `invalid_input` / `empty_context`; I added a `context` field.
- Call 3 (`ladder`, item `c1`): answer `b` (add clause 7 to the R08 index set), decided by typesafe, top 0.83, not a fallback. laya answered `a` with `fallback: true`. I decided `b` on my own reasoning too. Verified by the passing doc-contract tests with `R08_CLAUSES = (2, 6, 7)`.

## Verification Results

- **D-05 grep** (`Phase 30 now indexes automatically` in the 2026-10-24 session-hooks todo): `1`. The todo is not edited.
- **Acceptance greps:** runbook `## ` headings `4`; `**Design rule**` `1`; `ponytail yields` `1`; `make setup-dev` in AGENTS.md `1`; `R07_SUMMARY|R08_SUMMARY` in rules.py `3`.
- **Focused tests:** `tests.test_rules_docs` 16 ok; `tests.test_ai_kit_rules_common` 205 ok; `tests.test_flow_docs` ok; `tests.test_ai_kit_project_rules_agents` ok; `tests.test_gate_scope` ok.
- **Commit-stage and push-stage hooks:** ran on both commits (ruff, pylint, py-compile, staged tests, pyright via `make pyright`).

## Self-Check

- `skills/_shared/ai_kit_rules_common/code_exploration.py`: FOUND
- `docs/run-book/graphify.md`: FOUND
- `tests/test_rules_docs.py`: FOUND
- Commit `21dc09e` (feat): FOUND
- Commit `fea5967` (docs): FOUND
- No changes to `.planning/STATE.md` or `.planning/ROADMAP.md`: confirmed
- Working tree after the last commit: clean (`git status --short` empty)
- **Self-Check: PASSED**

## scope.py close output

Run after the last task commit (`fea5967`), before this SUMMARY was written. The `reported` lines are other plans' processes and temp directories (plan 30-03 in `agent-ac88e8e3336766d66`, plan 30-01 and the 30.1 worktree); none belong to this run.

```
reported (not this run):
  pid 3761563 cwd /var/home/bazzite/git/personal/ai-kit: /bin/bash -c source /home/bazzite/.claude/shell-snapshots/snapshot-bash-1793659154621-wcxvtw.sh 2>/dev/null || true && e
  pid 3761564 cwd /var/home/bazzite/git/personal/ai-kit: bash /var/home/bazzite/git/personal/ai-kit/tmp/phase30-exec/watch_wave.sh 1 aaf7474cba24ee858=30-01 a66943886f3b570b5=30
  pid 3763913 cwd /var/home/bazzite/git/personal/ai-kit: /bin/bash -c source /home/bazzite/.claude/shell-snapshots/snapshot-bash-1793659154621-wcxvtw.sh 2>/dev/null || true && e
  pid 3763921 cwd /var/home/bazzite/git/personal/ai-kit: sleep 600
  pid 3766497 cwd /var/home/bazzite/git/personal/ai-kit: /bin/bash -c source /home/bazzite/.claude/shell-snapshots/snapshot-bash-1793659154621-wcxvtw.sh 2>/dev/null || true && e
  pid 3766498 cwd /var/home/bazzite/git/personal/ai-kit: bash /var/home/bazzite/git/personal/ai-kit/tmp/phase30-exec/wait_any.sh 580 30-01:worktree-agent-aaf7474cba24ee858 30-02
  pid 3796417 cwd /var/home/bazzite/git/personal/ai-kit/tmp/wt-301/.planning/phases/30.1-setup-wizard-component-cards-and-host-status-line-panes-inse: /bin/bash -c source /home/bazzite/.claude/shell-snapshots/snapshot-bash-1793659154621-wcxvtw.sh 2>/dev/null || true && e
  pid 3813697 cwd /var/home/bazzite/git/personal/ai-kit/tmp/wt-301/.planning/phases/30.1-setup-wizard-component-cards-and-host-status-line-panes-inse: /bin/bash -c source /home/bazzite/.claude/shell-snapshots/snapshot-bash-1793659154621-wcxvtw.sh 2>/dev/null || true && e
  pid 4086808 cwd /var/home/bazzite/git/personal/ai-kit/.claude/worktrees/agent-ac88e8e3336766d66: /bin/bash -c source /home/bazzite/.claude/shell-snapshots/snapshot-bash-1793659154621-wcxvtw.sh 2>/dev/null || true && e
  pid 4086811 cwd /var/home/bazzite/git/personal/ai-kit/.claude/worktrees/agent-ac88e8e3336766d66: git commit -q -m feat(30-03): setup rewrites codegraph's global sentence headless, with backups -m - marked_block: byte-
  pid 4086827 cwd /var/home/bazzite/git/personal/ai-kit/.claude/worktrees/agent-ac88e8e3336766d66: /var/home/bazzite/git/personal/ai-kit/.venv/bin/python -mpre_commit hook-impl --config=.pre-commit-config.yaml --hook-ty
  pid 4100714 cwd /var/home/bazzite/git/personal/ai-kit/.claude/worktrees/agent-ac88e8e3336766d66: /home/linuxbrew/.linuxbrew/bin/python3 tools/run_unittest_parallel.py --staged
  pid 4122819 cwd /var/home/bazzite/git/personal/ai-kit: sleep 20
  pid 4124865 cwd /var/home/bazzite/git/personal/ai-kit/.claude/worktrees/agent-ac88e8e3336766d66: /home/linuxbrew/.linuxbrew/bin/python3 -m unittest tests.test_flow_contract
  pid 4125151 cwd /var/home/bazzite/git/personal/ai-kit/.claude/worktrees/agent-ac88e8e3336766d66: /home/linuxbrew/.linuxbrew/bin/python3 -m unittest tests.test_flow_stack
  pid 4130358 cwd /var/home/bazzite/git/personal/ai-kit/.claude/worktrees/agent-ac88e8e3336766d66: /home/linuxbrew/.linuxbrew/bin/python3 -m unittest tests.test_jev_fast_decision
  pid 4157000 cwd /var/home/bazzite/git/personal/ai-kit: sleep 60
  pid 4157131 cwd /var/home/bazzite/git/personal/ai-kit/tmp/compact-291: sleep 3
  pid 4158052 cwd /var/home/bazzite/git/personal/ai-kit/tmp/wt-301/.planning/phases/30.1-setup-wizard-component-cards-and-host-status-line-panes-inse: sleep 2
  pid 4159132 cwd /var/home/bazzite/git/personal/ai-kit/tmp/wt-301/.planning/phases/30.1-setup-wizard-component-cards-and-host-status-line-panes-inse: sleep 2
  pid 4159861 cwd /var/home/bazzite/git/personal/ai-kit/.claude/worktrees/agent-ac88e8e3336766d66: /home/linuxbrew/.linuxbrew/bin/python3 /var/home/bazzite/git/personal/ai-kit/.claude/worktrees/agent-ac88e8e3336766d66/s
  pid 4159890 cwd /var/home/bazzite/git/personal/ai-kit/.claude/worktrees/agent-ac88e8e3336766d66: /home/linuxbrew/.linuxbrew/bin/python3 /var/home/bazzite/git/personal/ai-kit/.claude/worktrees/agent-ac88e8e3336766d66/s
  temp: /tmp/ai-kit-p30-run-01-eadb1abc
  temp: /tmp/ai-kit-p30-run-03-e78f2ad4
clean
```

## Next Phase Readiness

- Plan 05 must add `make setup-dev` (guarded steps) to match the AGENTS.md Commands line.
- Plan 04 must add `fold.py boundary --next --point plan`, the route clauses 11 and 12 name.
- Plans 05-07 can cite `RULE_CLAUSES` and `docs/run-book/graphify.md` by path.

## Threat Flags

None. No new network, auth or file-access surface; the rule text and runbook are documentation.
