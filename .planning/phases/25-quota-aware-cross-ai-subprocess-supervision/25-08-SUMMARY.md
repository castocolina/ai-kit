---
phase: 25-quota-aware-cross-ai-subprocess-supervision
plan: 08
subsystem: infra
tags: [cross-ai, runner, model-catalog, route-flag, plan-set]

requires:
  - phase: 25-03
    provides: the runner's --route-<cli> router|unknown flag and the router-inferred label
  - phase: 25-07
    provides: the dogfood runner on template 7, which this plan does not edit
provides:
  - resolve_route, which turns a user-confirmed catalog fallback_quota into router or unknown
  - --route-<runtime> on every Python-dispatched runner argv, and nowhere else
  - plan-set router_backed written only from that same confirmed boolean
affects: [25-09, 25-10]

actuals:
  tokens: 4500
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns: [a confirmed catalog boolean is the only route a Python caller may assert]

key-files:
  created: []
  modified:
    - skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py
    - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/plan_edit.py
    - tests/test_ai_kit_spec_runner_dispatch.py
    - tests/test_curated_config_plan_edit.py
    - tests/test_cross_ai_runner_e2e.py
    - tests/test_ai_kit_spec_env_scrub.py
    - tests/test_ai_kit_spec.py

key-decisions:
  - "An unconfirmed catalog value stays unset, so the runner's own heuristic decides and labels it router-inferred or unknown"
  - "A variant is compared after strip_model_suffix, so a confirmed answer on the base model covers its cursor, pi and opencode forms"
  - "project_runner_command and runner_flags stay unchanged: the GSD hook string never carries a route flag"

patterns-established:
  - "RunnerSeams.route_fn is the cache seam: a spawn-path test on a non-scratch environment stubs it"
  - "router_backed is true only when fallback_quota is a bool and fallback_quota is in heuristic_confirmed"

requirements-completed: [QTA-01, QTA-03]

coverage:
  - id: D1
    description: "A user-confirmed fallback_quota becomes --route-<runtime> router or unknown, including a variant of the confirmed base model"
    requirement: QTA-03
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_spec_runner_dispatch.py#TestResolveRoute"
        status: pass
    human_judgment: false
  - id: D2
    description: "A missing, unreadable or malformed catalog, and an unconfirmed entry, pass no flag"
    requirement: QTA-03
    verification:
      - kind: unit
        ref: "tests/test_ai_kit_spec_runner_dispatch.py#TestResolveRoute.test_unconfirmed_and_malformed_yield_none"
        status: pass
    human_judgment: false
  - id: D3
    description: "plan-set writes router_backed true only from a confirmed fallback_quota"
    requirement: QTA-03
    verification:
      - kind: unit
        ref: "tests/test_curated_config_plan_edit.py#TestScriptRouterBacked"
        status: pass
    human_judgment: false
  - id: D4
    description: "The real runner reports route=router and status=quota for a confirmed catalog, and route=unknown with no flag when the catalog is absent"
    requirement: QTA-01
    verification:
      - kind: e2e
        ref: "tests/test_cross_ai_runner_e2e.py#TestRouteFlagE2E"
        status: pass
    human_judgment: false

duration: 40min
completed: 2026-10-24
status: complete
orchestrator_verify: "VERIFY 25-08: 2/2 passed"
---

# Phase 25 Plan 08: Catalog Route on Python Dispatch Summary

**A Python-dispatched runner call carries the user's confirmed router answer as `--route-<runtime>`, and otherwise defers to the runner's labelled heuristic; plan-set uses the same confirmed boolean.**

## Performance

- **Duration:** 40 min
- **Started:** 2026-10-24T00:00:00Z
- **Completed:** 2026-10-24T00:40:00Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- `resolve_route` reads the model catalog through `cache_read_json` and `split_catalog_meta` and returns `router` or `unknown` only for a boolean `fallback_quota` listed in `heuristic_confirmed`, after `strip_model_suffix`.
- `run_runner` fills a blank `RunnerSpec.route` through `RunnerSeams.route_fn` and `build_runner_argv` appends the flag; `runner_flags` and `project_runner_command` do not.
- `plan_edit._plan_set_script_model` writes `router_backed` true only from that confirmed boolean, so an inferred router row and a confirmed false both render as not router-backed.
- The real unrendered template, driven with a fake opencode and a scratch catalog, reports `route=router` and relays one `cross-ai: report` line.

## Task Commits

Each task was committed atomically:

1. **Task 1: Catalog route into the runner argv, end to end through run_runner** - `66906ed` (feat)
2. **Task 2: Real-runner proof and hermetic seams across the test suite** - (this commit) (test)

## Files Created/Modified

- `skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py` - `resolve_route`, `RunnerSpec.route`, `RunnerSeams.route_fn`, the `--route-<runtime>` argv flag
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/plan_edit.py` - `router_backed` from a confirmed `fallback_quota` only
- `tests/test_ai_kit_spec_runner_dispatch.py` - confirmed, variant, malformed and argv cases; `_seams` stubs `route_fn`
- `tests/test_curated_config_plan_edit.py` - inferred, confirmed-false and confirmed-true `router_backed` cases
- `tests/test_cross_ai_runner_e2e.py` - `TestRouteFlagE2E` against the real runner
- `tests/test_ai_kit_spec_env_scrub.py` - `route_fn` stub on the two real-env spawn seams
- `tests/test_ai_kit_spec.py` - `route_fn` stub on the execute-dispatch spawn seam

## RunnerSeams audit

Sites that got a `route_fn=lambda *_a: None` stub, because they reach the spawn path with a default or non-scratch environment:

- `tests/test_ai_kit_spec_runner_dispatch.py` `_seams`: the shared fake-spawn helper; its `env_fn` is a scratch dict, and the stub keeps a later edit from reading a real cache.
- `tests/test_ai_kit_spec_env_scrub.py` the `run_runner` block: the parent environment is the real one and node plus the template are found.
- `tests/test_ai_kit_spec_env_scrub.py` the `dispatch_execute` block: `ExecuteSeams` with a real parent environment and a `which_fn` that finds node.
- `tests/test_ai_kit_spec.py` `TestDispatchExecuteArgv`: the same execute-dispatch spawn capture against the real parent environment.

Sites that did not need one:

- `tests/test_cross_ai_runner_e2e.py` (`TestRunnerDispatchE2E`, `TestReviewStatusesE2E`, `TestExecStatusesE2E`, `TestGsdHookE2E`): each passes `env_fn` returning `runner_env(tmp)`, whose `HOME` and `XDG_CONFIG_HOME` are scratch, so the default cache path stays inside the temp dir. `TestRouteFlagE2E` is the one that must read a catalog, and it points `XDG_CACHE_HOME` at its own scratch cache.
- `tests/test_cross_ai_runner_e2e.py` `TestRunnerDispatchNoNode`: `which_fn` returns None, so `run_runner` returns before `route_fn`.
- `tests/test_ai_kit_spec_runner_dispatch.py` `TestSpawnCleanup.test_wedged_runner_recorded_group_killed`: the only other `run_runner` with a default `env_fn`, but its `which_fn` resolves node to `sys.executable` and its `runner_path_fn` points at a Python script, so a catalog read would spawn Python rather than node. It runs inside the suite and does not touch `~/.cache/ai-kit`.
- `tests/test_ai_kit_spec_runner_dispatch.py` `test_escaped_grandchild_is_abandoned`, `test_recorded_group_validation`, `TestRunCustomCommand`: custom-command and group-reaping paths; `run_custom_command` never calls `route_fn`.
- `tests/test_ai_kit_spec_env_scrub.py` `run_custom_command` and `dispatch_reviewer`: custom entries, no runner argv and no catalog read.
- `reviewer_dispatch.py` `ReviewerSeams()` and `execute_dispatch.py` `ExecuteSeams()`: production defaults, and the right ones — a real review or execute lane must read the user's catalog. Every test that builds either class either replaces `runner_fn`/`runner_tiers_fn` (no `run_runner` call) or passes a scratch `env_fn` through `runner_seams`. No test constructs the bare default and reaches the spawn path.
- `quota.py` `_collecting_seams`: production probe path, same reason; its tests inject `runner_fn` and never spawn.

## Decisions Made

- Followed the plan: only a user-confirmed boolean becomes a flag, and the comparison uses the same `strip_model_suffix` normalization the routing path uses before its own catalog lookup.
- A non-dict entry, a non-dict `runtimes` value and a non-dict runtime row all yield None and never raise.

## Deviations from Plan

None - plan executed exactly as written.

## Deleted tests

None.

## Pre-existing failures

None.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Review and execute lanes hand the runner the confirmed route; 25-09 can describe that policy without changing the dispatch.
- The project-wide `make test` / `make validate` barrier is the orchestrator's, after this commit.

---
*Phase: 25-quota-aware-cross-ai-subprocess-supervision*
*Completed: 2026-10-24*
