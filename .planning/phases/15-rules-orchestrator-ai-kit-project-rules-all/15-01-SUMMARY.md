---
phase: 15-rules-orchestrator-ai-kit-project-rules-all
plan: 01
subsystem: testing
tags: [python, subprocess, cli, rules-orchestrator, cross-domain-merge]

# Dependency graph
requires:
  - phase: 09-agents-md-checker-prune-ai-kit-project-rules-agents
    provides: "ai-kit-project-rules-agents check/remediate CLI shape, the AGENTS.md workflow-domain checker this orchestrator dispatches to"
  - phase: 10-makefile-rules-checker-ai-kit-project-rules-makefile
    provides: "ai-kit-project-rules-makefile check/remediate CLI shape, the Makefile-domain checker"
  - phase: 11-pre-commit-rules-checker-ai-kit-project-rules-precommit
    provides: "ai-kit-project-rules-precommit check/remediate CLI shape, the pre-commit-domain checker"
  - phase: 12-architecture-rules-checker-ai-kit-project-rules-arch
    provides: "ai-kit-project-rules-arch check/remediate CLI shape, the architecture-domain checker"
  - phase: 13-docker-rules-checker-ai-kit-project-rules-docker
    provides: "ai-kit-project-rules-docker check/remediate CLI shape, the Docker-domain checker"
  - phase: 14-ci-cd-rules-checker-ai-kit-project-rules-cicd
    provides: "ai-kit-project-rules-cicd check/remediate CLI shape, the CI/CD-domain checker"
provides:
  - "ai-kit-project-rules-all's functional core: subprocess fan-out (dispatch.py), per-domain failure isolation (D-02/D-05), and a pure cross-domain criticality merge with AGENTS.md hand-off tagging (aggregate.py)"
  - "check/remediate CLI surface (cli.py) proven identical per D-04"
  - "13 unit/integration tests (TestTracer, TestFailureIsolation, TestAggregate, TestCLI) registered in make test-unit"
affects: ["15-02 (SKILL.md authoring and installer registration for this skill)"]

# Actuals (#2632)
actuals:
  tokens: 6301
  tasks: 3
  commits: 3
plan_head_before: 81e755666088b4e68718892333482e0e37bb1f29

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Subprocess fan-out via a fixed DOMAIN_ORDER tuple as the single source of truth for both dispatch iteration order and the aggregator's tie-break order (dispatch.py owns it, aggregate.py imports it)"
    - "D-05 failure-entry schema ({domain, status: failed, error, returncode}) as the universal degradation shape for non-zero exit, timeout, malformed JSON, and unresolvable entrypoint -- kept in a separate `failed` list, never folded into `remediate`/`blocked`"
    - "Module-level constant read live at call time (never bound as a function-default parameter) so tests can monkeypatch it effectively -- applied to both DOMAIN_TIMEOUT_SECONDS (dispatch.py) and the dispatch/aggregate module references in cli.py (qualified attribute access, never `from .x import y`)"
    - "Pure aggregation function with zero I/O imports, tested exclusively via hand-built fixture dicts -- proves cross-domain logic without re-exercising any sibling's real logic"

key-files:
  created:
    - skills/ai-kit-project-rules-all/ai-kit-project-rules-all.py
    - skills/ai-kit-project-rules-all/ai_kit_project_rules_all/__init__.py
    - skills/ai-kit-project-rules-all/ai_kit_project_rules_all/cli.py
    - skills/ai-kit-project-rules-all/ai_kit_project_rules_all/dispatch.py
    - skills/ai-kit-project-rules-all/ai_kit_project_rules_all/aggregate.py
    - tests/test_ai_kit_project_rules_all.py
  modified:
    - Makefile

key-decisions:
  - "D-04 (plan-authored): remediate(repo_root) == check(repo_root) -- every sibling's own remediate already runs check internally before build_remediation(), so there is no further per-orchestrator classification step"
  - "D-05 (plan-authored): failure entries use {domain, status: failed, error, returncode} in a separate failed list, distinguishable from a real payload by the presence of a status key"
  - "D-06 (plan-authored): dispatch_all() is sequential over the fixed DOMAIN_ORDER, never parallel -- accepted worst-case 180s ceiling (6 x 30s) in exchange for zero completion-order non-determinism"
  - "Task 1 shipped run_domain() as happy-path-only (no try/except); Task 2 added D-02 isolation wrapping in a separate commit -- matches the plan's explicit task split and was confirmed by pyright: 2 reportArgumentType/reportCallIssue errors after Task 1 (entrypoint typed str | None reaching subprocess.run) resolved to 0 after Task 2's None-check and try/except landed"

patterns-established:
  - "Pattern 1: D-05 failure-entry schema as the universal per-domain degradation shape across this whole skill family's future cross-domain consumers"
  - "Pattern 2: qualified module-attribute call access (`from . import x` then `x.y(...)`) wherever a test needs to monkeypatch a module-level function/constant that a caller invokes -- named-import binding silently defeats the patch"

requirements-completed: [REQ-rules-all]

coverage:
  - id: D1
    description: "check real-subprocess-invokes all 6 sibling checkers' remediate subcommand (D-04) in fixed DOMAIN_ORDER; the report's remediate+blocked+failed lists together account for every domain (SC1)"
    requirement: "REQ-rules-all"
    verification:
      - kind: integration
        ref: "tests/test_ai_kit_project_rules_all.py#TestTracer.test_dispatch_all_returns_all_six_real_domains"
        status: pass
      - kind: integration
        ref: "tests/test_ai_kit_project_rules_all.py#TestTracer.test_entry_script_subprocess_check_against_this_repo"
        status: pass
    human_judgment: false
  - id: D2
    description: "the combined remediate list is globally criticality-ordered across all 6 domains, not per-domain-grouped (SC2)"
    requirement: "REQ-rules-all"
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_project_rules_all.py#TestAggregate.test_cross_domain_ordering_is_one_global_sort"
        status: pass
      - kind: integration
        ref: "tests/test_ai_kit_project_rules_all.py#TestTracer.test_aggregate_of_real_dispatch_is_globally_sorted_with_no_failures"
        status: pass
    human_judgment: false
  - id: D3
    description: "workflow-kind entries alone carry hand_off: agent-md-refactor; no other entry does (SC3 data half)"
    requirement: "REQ-rules-all"
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_project_rules_all.py#TestAggregate.test_workflow_kind_alone_gets_hand_off_tag"
        status: pass
    human_judgment: false
  - id: D4
    description: "a sibling subprocess failure (non-zero exit, timeout, malformed JSON, unresolvable entrypoint) produces a D-05 failure entry without crashing the run, and does not affect the other 5 domains' real results (D-02)"
    requirement: "REQ-rules-all"
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_project_rules_all.py#TestFailureIsolation (4 cases)"
        status: pass
      - kind: unit
        ref: "tests/test_ai_kit_project_rules_all.py#TestAggregate.test_failed_domain_isolated_from_remediate_and_blocked"
        status: pass
    human_judgment: false
  - id: D5
    description: "aggregate() is a pure function -- never imports subprocess, never touches the filesystem -- so TestAggregate exercises SC1/SC2/SC3's cross-domain logic with hand-built fixtures, never invoking any real sibling checker (SC4)"
    requirement: "REQ-rules-all"
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_project_rules_all.py#TestAggregate (4 cases, zero subprocess/dispatch_all calls)"
        status: pass
      - kind: other
        ref: "skills/ai-kit-project-rules-all/ai_kit_project_rules_all/aggregate.py contains no `import subprocess` and no filesystem call (source inspection)"
        status: pass
    human_judgment: false
  - id: D6
    description: "no sibling's own remediation.py file is modified anywhere in this plan (SC5)"
    requirement: "REQ-rules-all"
    verification:
      - kind: other
        ref: "git diff --stat 81e7556..HEAD -- skills/ai-kit-project-rules-{agents,makefile,precommit,arch,docker,cicd}/**/remediation.py (empty output)"
        status: pass
    human_judgment: false
  - id: D7
    description: "remediate(repo_root) returns output byte-identical to check(repo_root) (D-04)"
    requirement: "REQ-rules-all"
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_project_rules_all.py#TestCLI.test_check_and_remediate_are_byte_identical_d04"
        status: pass
    human_judgment: false
  - id: D8
    description: "tests.test_ai_kit_project_rules_all is registered in Makefile's test-unit target and runs as part of make test-unit/make test"
    requirement: "REQ-rules-all"
    verification:
      - kind: other
        ref: "make test-unit (full run, 2484 tests, this module included with zero attributed failures)"
        status: pass
    human_judgment: false

duration: 10min
completed: 2026-09-15
status: complete
---

# Phase 15 Plan 01: Rules Orchestrator Functional Core Summary

**Subprocess fan-out + pure cross-domain criticality merge for `ai-kit-project-rules-all`, dogfooded live against this repo's own 6 shipped sibling checkers with zero failures.**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-09-15T01:32:54Z
- **Completed:** 2026-09-15T01:42:23Z
- **Tasks:** 3
- **Files modified:** 7 (6 created, 1 modified)

## Accomplishments
- `dispatch.py`: subprocess fan-out to all 6 sibling `ai-kit-project-rules-*` checkers via their `remediate` subcommand (D-04), host-neutral 5-candidate entrypoint resolution matching every sibling's own `SKILL.md`, sequential dispatch over a fixed `DOMAIN_ORDER` (D-06), and full D-02/D-05 failure isolation (non-zero exit, timeout, malformed JSON, unresolvable entrypoint all degrade to one shape without crashing the run)
- `aggregate.py`: pure cross-domain merge -- one global criticality sort spanning all 6 domains (SC2), `hand_off: agent-md-refactor` tagging scoped exclusively to `workflow`-kind (AGENTS.md-domain) entries (SC3), and a separate `failed` list so "checked, no findings" is never conflated with "couldn't check" (D-02/D-05)
- `cli.py` + entry script: `check`/`remediate` subcommands matching every sibling's exact CLI shape, with `remediate` proven byte-identical to `check` per D-04
- 13 tests across 4 classes: `TestTracer` (live dogfood against this repo's real 6 siblings, no mocks), `TestFailureIsolation` (4 fixture-script-driven degradation cases), `TestAggregate` (4 pure-function stub cases, SC4), `TestCLI` (2 cases)
- `Makefile`'s `test-unit` target gains this module -- confirmed via a full `make test-unit` run (2484 tests, zero failures attributed to this module)
- A real `check` run against this repo itself: 12 `remediate` entries, 3 `blocked`, 0 `failed`

## Task Commits

Each task was committed atomically:

1. **Task 1: Wire check/remediate end-to-end** - `fe707b9` (feat) -- entry script through `dispatch_all()`/`aggregate()`, `TestTracer`'s 3 cases against all 6 real siblings
2. **Task 2: D-02 failure isolation** - `5950dd6` (fix) -- non-zero exit/timeout/malformed-JSON/unresolvable-entrypoint all degrade to D-05's shape, `TestFailureIsolation`'s 4 fixture-backed cases
3. **Task 3: CLI remediate proof, TestAggregate/TestCLI, Makefile registration** - `864c237` (test) -- SC4's stub suite, D-04's check==remediate proof, Makefile wiring

_Note: this was a TDD plan (RED confirmed before each GREEN implementation), but each task's RED->GREEN cycle stayed within one commit per the plan's "One commit" instruction per task -- tests and implementation land together, not as separate commits._

## Files Created/Modified
- `skills/ai-kit-project-rules-all/ai-kit-project-rules-all.py` - 4-line entry script (`sys.exit(main(sys.argv[1:]))`)
- `skills/ai-kit-project-rules-all/ai_kit_project_rules_all/__init__.py` - package docstring only, no `_shared` import
- `skills/ai-kit-project-rules-all/ai_kit_project_rules_all/dispatch.py` - `DOMAIN_ORDER`, `SKILL_NAMES`, `DOMAIN_TIMEOUT_SECONDS`, `resolve_entrypoint()`, `run_domain()`, `dispatch_all()` -- the only module importing `subprocess`
- `skills/ai-kit-project-rules-all/ai_kit_project_rules_all/aggregate.py` - `aggregate()`, the pure cross-domain merge/sort/hand-off-tag function
- `skills/ai-kit-project-rules-all/ai_kit_project_rules_all/cli.py` - `check()`/`remediate()`/`main(argv)`, qualified `dispatch`/`aggregate` module access
- `tests/test_ai_kit_project_rules_all.py` - `TestTracer`, `TestFailureIsolation`, `TestAggregate`, `TestCLI` (13 cases total)
- `Makefile` - `test-unit` target gains `tests.test_ai_kit_project_rules_all`

No `SKILL.md` was created (intentional, per the plan's objective -- this code stays dev-only and un-installed until plan 15-02).

## Decisions Made
- D-04, D-05, D-06 were pre-authored in the plan itself (planner's authority, resolving `15-RESEARCH.md`'s two Open Questions) and implemented exactly as specified -- no deviation.
- Task 1's `run_domain()` was deliberately shipped happy-path-only (no try/except), with Task 2 adding D-02's isolation wrapping in a separate commit, matching the plan's explicit task split (`read_first` for Task 2 states "run_domain's current happy-path-only shape is what this task wraps in isolation"). This was independently confirmed correct by `pyright`: 2 type errors present after Task 1 (entrypoint typed `str | None` flowing into `subprocess.run`, which cannot yet be `None` at that point in the happy path) resolved to 0 errors after Task 2's `None`-check and exception handling landed.
- Task 3's sub-step (a) ("add the remediate branch to `main(argv)` ... if Task 1 did not already wire it") required no code changes -- Task 1's `cli.py` already implemented both `check`/`remediate` branches per its own `<action>` spec, confirmed by `TestCLI`'s Test 5/6 passing without modification. This matches the plan's own anticipation of this outcome.

## Deviations from Plan

None - plan executed exactly as written. D-04/D-05/D-06 are plan-authored decisions, not deviations; they were implemented literally as specified.

## Issues Encountered

- `pyproject.toml`'s ruff config flagged 2 style issues in the first test-file draft (`RUF100` unused `noqa: E402` -- the ignore is already blanket-applied to `tests/*` via `per-file-ignores`, so the inline `noqa` was redundant; `RUF005` list concatenation via `+` instead of unpacking). Both fixed inline before the Task 1 commit; not a deviation from the plan, just normal lint cleanup before committing.
- This session's worktree branch (`worktree-agent-a57bc11f14abcbd56`) was spawned from a base commit 182 commits behind `main` -- predating all of Phases 9-15's planning and implementation, including the 6 sibling checkers this plan's tracer task dogfoods against. Fast-forwarded the worktree branch to `main` (`81e7556`) before starting Task 1; the worktree branch carried zero unique commits of its own, so this was a clean, lossless fast-forward, not a merge or rebase.

## User Setup Required

None - no external service configuration required. This orchestrator is stdlib-only (confirmed via every sibling's own import block, per the plan's threat-model ASVS L1 assessment); no package install, no `[ASSUMED]` checkpoint needed.

## Next Phase Readiness

- The functional core (`dispatch.py`, `aggregate.py`, `cli.py`) is fully proven end-to-end against this repo's own 6 real sibling checkers, with 13 passing tests and zero scope leakage into any sibling's own files (`git diff --stat` confirms exactly the 7 files this plan's `files_modified` lists).
- Plan 15-02 (SKILL.md authoring and installer registration) can proceed directly against this stable `cli.py`/`dispatch.py`/`aggregate.py` surface -- no interface changes anticipated.
- `.pre-commit-config.yaml`'s `ruff`/`pylint`/`unittest` hooks' `files` regex lists do not yet include `skills/ai-kit-project-rules-all/.*` or `tests.test_ai_kit_project_rules_all` in their pre-push `unittest` module list -- this is out of scope for this plan (not in `files_modified`, and touching it would violate this plan's own `<verification>` diff-scope check) but is a likely candidate for plan 15-02's scope, matching the pattern every prior sibling phase (9-14) used to register itself into these hooks alongside its own `SKILL.md`.

---
*Phase: 15-rules-orchestrator-ai-kit-project-rules-all*
*Completed: 2026-09-15*

## Self-Check: PASSED

All 6 created files confirmed present on disk; all 3 task commit hashes (`fe707b9`, `5950dd6`, `864c237`) confirmed present in `git log --oneline --all`.
