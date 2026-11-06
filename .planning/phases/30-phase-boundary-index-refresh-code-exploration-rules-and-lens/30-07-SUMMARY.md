---
phase: 30-phase-boundary-index-refresh-code-exploration-rules-and-lens
plan: 07
subsystem: unit-flow
tags: [superpowers, boundary, unit-brief, start-block, skill-text]

requires:
  - phase: 30-04
    provides: "fold.py boundary (the three unit points) and start running the boundary"
provides:
  - "superpowers start block also runs the wave-point boundary before the first task"
  - "every superpowers implementer objective points at .aikit/brief/SKILL.md"
  - "SKILL.md states how the plan writer is briefed before the plan exists"
affects: [30-JUDGE, 45.1]

actuals:
  tokens: 2599
  tasks: 2
  commits: 2
plan_head_before: 12078bd74c72e8018310df01d7d95ccb7ddd2bff
plan_head_after: 55917cc26e591f90c3a74b2b2fcf2571d240cef2

tech-stack:
  added: []
  patterns:
    - "start block runs the boundary with `|| true`: a boundary problem never stops the plan"

key-files:
  created:
    - .planning/phases/30-phase-boundary-index-refresh-code-exploration-rules-and-lens/30-07-SUMMARY.md
  modified:
    - skills/ai-kit-spec-execute-superpowers/SKILL.md
    - skills/ai-kit-spec-execute-superpowers/references/start-step.md
    - skills/ai-kit-spec-execute-superpowers/references/dispatch-external-cli.md
    - tests/test_ai_kit_spec_superpowers.py

key-decisions:
  - "The plan writer is briefed by the instruction-file rule (AGENTS.md clause), not by an ai-kit dispatch: superpowers writes the plan before this skill runs and this adapter never dispatches it"
  - "The main-branch check in the start-step test asserts `main^` equals the value captured before the run: the test's own plan commit moves main, and the boundary must add nothing after it"

patterns-established:
  - "Pinned skill text: each adapter string has a remove-each check, so a deleted string fails its own test"

requirements-completed: [FLOW-04, JDG-04]

duration: 15min
completed: 2026-11-05
status: complete
---

# Phase 30 Plan 07: superpowers boundary and unit brief Summary

**The superpowers start block runs the wave-point boundary, every implementer brief points at the unit brief, and the plan-writer route is stated in SKILL.md**

## Performance

- **Duration:** about 15 min
- **Started:** 2026-11-05T02:29Z
- **Completed:** see the commit time of this file
- **Tasks:** 2
- **Files modified:** 4 (plus this SUMMARY)

## Accomplishments

- `references/start-step.md`: the start block runs `fold.py boundary --plan "$PLAN_FILE" --point wave --repo "$CWD" || true` right after `start`. Prose says `start` already runs the boundary for the unit's start, that this second run is the one before the first task, and that a boundary problem never stops the plan.
- `references/dispatch-external-cli.md` `## Compose`: the objective carries the `Unit brief:` line pointing at `.aikit/brief/SKILL.md`, to read after the plan and spec, and to note and continue when it is missing, says no brief, or names another unit.
- `SKILL.md`: Step 1 says superpowers writes the plan before this skill runs, so the plan writer is briefed by `python3 <fold skill>/scripts/fold.py boundary --next --point plan` (fold skill found as in `start-step.md`), then handed `.aikit/brief/SKILL.md`. Step 3's native paragraph says the native brief carries the same unit-brief line.
- Tests: `TestUnitBriefDelivery` (text pins, a remove-each non-vacuity check, boundary-after-start order) and `TestStartStep.test_start_block_writes_the_wave_point_brief` (the block runs as written in a superpowers fixture: exit 0, the brief holds `point: wave`, no `.planning/` folder, codegraph and graphify run in the repo, the plan commit is the only commit main gains).

## Task Commits

1. **Task 1: start block runs the wave boundary; implementers get the unit brief** - `b1bb77f` (feat)
2. **Task 2: the start block, run as written in a fixture, writes the wave-point brief** - `55917cc` (test)

Plan head before: `12078bd74c72e8018310df01d7d95ccb7ddd2bff` (the worktree base recorded by the branch check). Plan head after: `55917cc` plus this SUMMARY's own commit.

## Files Created/Modified

- `skills/ai-kit-spec-execute-superpowers/SKILL.md` - Step 1 plan-writer sentence; Step 3 native line
- `skills/ai-kit-spec-execute-superpowers/references/start-step.md` - wave-point boundary line and prose
- `skills/ai-kit-spec-execute-superpowers/references/dispatch-external-cli.md` - unit-brief line in `## Compose`
- `tests/test_ai_kit_spec_superpowers.py` - `TestUnitBriefDelivery`, `TestStartStep.test_start_block_writes_the_wave_point_brief`

## Decisions Made

- The plan writer is briefed through the instruction-file rule (AGENTS.md's clause from plan 02), not through an ai-kit dispatch. superpowers writes the plan before this skill runs, and the adapter never dispatches the plan writer. The fixture test cannot observe superpowers' own planning skill, so the deferred review concern about a boundary-to-plan-writer fixture stays deferred (see the plan's review ledger).
- The test asserts `main^` against the value captured before the run. The helper `_run()` commits the plan on main first, so main moves by exactly that commit; the boundary adds nothing after it.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test main-branch check compared the wrong commit**
- **Found during:** Task 2
- **Issue:** The draft compared `main` before and after `_run()`; `_run()` commits the plan on main, so the check failed on the plan's own commit.
- **Fix:** Compare `main^` after the run with `main` captured before `_run()`.
- **Files modified:** tests/test_ai_kit_spec_superpowers.py
- **Verification:** `tests.test_ai_kit_spec_superpowers` ok, 167 tests.
- **Committed in:** 55917cc (Task 2 commit, same change before the commit)

**2. [Rule 3 - Blocking] Two E501 line-length findings in the new test class**
- **Found during:** Task 1 commit (ruff hook)
- **Fix:** Wrapped the two long constants. **Committed in:** b1bb77f (Task 1 commit, fixed before the commit).

**Total deviations:** 2 auto-fixed (1 bug in the test draft, 1 lint wrap). **Impact on plan:** none to scope.

## Jev Calls

- `c1` (choice, the test's main-branch assertion): jev typesafe chose `b` (top 0.94); laya fell back (`needs_fallback` true) and also chose `b` (top 0.51). Decided `b`; one cheap check: the test passes with `main^`.

## User-owned items

- The owner confirms the superpowers before-planning route (`python3 <fold skill>/scripts/fold.py boundary --next --point plan` written into AGENTS.md and the superpowers SKILL.md). This is a recorded user-owned item and does not stop execution. Target projects get the route with Phase 45.1's generated rules block (RULE-03), outside this phase.

## Judge

- `skills/ai-kit-spec-execute-superpowers/SKILL.md` is in plan 06's `30-JUDGE.md` set. The orchestrator runs the judge; this executor did not run it.

## Verification

- `scope.py selftest`: `selftest ok`
- `tests.test_ai_kit_spec_superpowers` and `tests.test_flow_docs`: ok (Task 1 and Task 2 commit hooks ran the staged covering modules, all ok)
- `make pyright`: passed
- `scope.py test` (`make test` under this run's temp dir): exit 0. Unit 95/95 and unit-uv 1/1, integration 6/6, e2e 25/25 with `tests/test_install.sh` 45 passed, arch 1/1 (`tests.test_flow_index_e2e` ok in this run).
- `scope.py close`: run after this file's commit as the plan's last step; its last line is in the executor's final return, not here (the file cannot record its own commit).

## Reported (not this run)

Lines `scope.py close` printed as `reported (not this run):` at the pre-commit close check (other plans' and agents' processes and temp entries, none created by this run):

- process in other worktree: pid 204290 cwd /var/home/bazzite/git/personal/ai-kit: /home/linuxbrew/.linuxbrew/bin/python3 tools/env_matrix.py --only custom-tmpdir --only long-path
- process in other worktree: pid 523434 cwd /var/home/bazzite/git/personal/ai-kit/.claude/worktrees/agent-a7f663df983c8d3a2: /bin/bash -c source /home/bazzite/.claude/shell-snapshots/snapshot-bash-1793659154621-wcxvtw.sh 2>/dev/null || true && e
- process in other worktree: pid 523435 cwd /var/home/bazzite/git/personal/ai-kit/.claude/worktrees/agent-a7f663df983c8d3a2: python3 /var/home/bazzite/git/personal/ai-kit/.claude/worktrees/agent-a7f663df983c8d3a2/tmp/p30/04/scope.py test
- process in other worktree: pid 523471 cwd /var/home/bazzite/git/personal/ai-kit/.claude/worktrees/agent-a7f663df983c8d3a2: make test
- process in other worktree: pid 532686 cwd /var/home/bazzite/git/personal/ai-kit: make -j1 -k -C /var/home/bazzite/git/personal/ai-kit test
- process in other worktree: pid 532689 cwd /var/home/bazzite/git/personal/ai-kit: python3 tools/run_unittest_parallel.py --group unit
- process in other worktree: pid 562316 cwd /var/home/bazzite/git/personal/ai-kit: /home/linuxbrew/.linuxbrew/bin/python3 -m unittest -v tests.test_flow_stack
- process in other worktree: pid 657007 cwd /var/home/bazzite/git/personal/ai-kit: sleep 30
- process in other worktree: pid 686177 cwd /var/home/bazzite/git/personal/ai-kit/.claude/worktrees/agent-a7f663df983c8d3a2: uv run python tools/run_unittest_parallel.py --group integration
- process in other worktree: pid 686190 cwd /var/home/bazzite/git/personal/ai-kit/.claude/worktrees/agent-a7f663df983c8d3a2: /var/home/bazzite/git/personal/ai-kit/.claude/worktrees/agent-a7f663df983c8d3a2/.venv/bin/python3 tools/run_unittest_par
- process in other worktree: pid 686222 cwd /var/home/bazzite/git/personal/ai-kit/.claude/worktrees/agent-a7f663df983c8d3a2: /var/home/bazzite/git/personal/ai-kit/.claude/worktrees/agent-a7f663df983c8d3a2/.venv/bin/python3 -m unittest tests.test
- process in other worktree: pid 686224 cwd /var/home/bazzite/git/personal/ai-kit/.claude/worktrees/agent-a7f663df983c8d3a2: /var/home/bazzite/git/personal/ai-kit/.claude/worktrees/agent-a7f663df983c8d3a2/.venv/bin/python3 -m unittest tests.test
- process in other worktree: pid 686225 cwd /var/home/bazzite/git/personal/ai-kit/.claude/worktrees/agent-a7f663df983c8d3a2: /var/home/bazzite/git/personal/ai-kit/.claude/worktrees/agent-a7f663df983c8d3a2/.venv/bin/python3 -m unittest tests.test
- process in other worktree: pid 686227 cwd /var/home/bazzite/git/personal/ai-kit/.claude/worktrees/agent-a7f663df983c8d3a2: /var/home/bazzite/git/personal/ai-kit/.claude/worktrees/agent-a7f663df983c8d3a2/.venv/bin/python3 -m unittest tests.test
- process in other worktree: pid 687733 cwd /var/home/bazzite/git/personal/ai-kit/.claude/worktrees/agent-a7f663df983c8d3a2: /home/bazzite/.local/bin/uv run --script /var/home/bazzite/git/personal/ai-kit/.claude/worktrees/agent-a7f663df983c8d3a2
- process in other worktree: pid 687737 cwd /var/home/bazzite/git/personal/ai-kit/.claude/worktrees/agent-a7f663df983c8d3a2: /home/bazzite/.cache/uv/environments-v2/setup-4c6453ed998c6862/bin/python3 /var/home/bazzite/git/personal/ai-kit/.claude
- process in other worktree: pid 687949 cwd /var/home/bazzite/git/personal/ai-kit: /home/linuxbrew/.linuxbrew/bin/python3 /var/home/bazzite/git/personal/ai-kit/skills/ai-kit-commit-fold/scripts/fold.py s
- temp entry not this run: /tmp/ai-kit-p30-run-04-a627d339
- temp entry not this run: /tmp/ai-kit-p30-run-06-e2963785
- temp entry not this run: /tmp/ai-kit-p30-gate-bpfsz0ed

## Issues Encountered

- The ledger file that protocol 0c writes before the first commit was not written before Task 1's commit. `commits:` is measured from the base recorded by the branch check (`12078bd`), so the count stays measured, not narrated.

## Known Stubs

None.

## Deferred Issues

None from this plan's scope.

## Next Phase Readiness

- The superpowers adapter now runs the wave boundary and hands the unit brief to every implementer. Plan 06's judge set includes SKILL.md; the orchestrator runs the judge.

---
*Phase: 30-phase-boundary-index-refresh-code-exploration-rules-and-lens*
*Completed: 2026-11-05*
