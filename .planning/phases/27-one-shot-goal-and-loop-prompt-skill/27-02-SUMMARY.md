---
phase: 27-one-shot-goal-and-loop-prompt-skill
plan: 02
subsystem: tooling
tags: [goal-prompt, scope, opengsd, superpowers, depends-on, stdlib, tdd]

# Dependency graph
requires:
  - phase: 27-01
    provides: "gp_common.phase_key; tests/goal_prompt_fixtures.py builders for OpenGSD, original GSD, superpowers and empty projects"
provides:
  - "gp_scope.load_phases: GSD phase state from roadmap JSON, a *-SPEC.md glob and phase-op JSON, in numeric order; repo-relative dirs"
  - "gp_scope.opengsd_identity: exact packageName == @opengsd/gsd-core, anything else unverified"
  - "gp_scope.load_plans and Plan: superpowers plans with exact backticked Depends-on edges and one free-text entry"
  - "gp_scope.execution_order and dependents: stable Kahn order, a dependency-cycle error, transitive failure scope"
  - "gp_scope.scope_kind and detect_scope: the contract scope object for opengsd, gsd-unproven, superpowers, both and none"
affects: [27-03 host and readiness, 27-05 strategy matrix, 27-09 CLI detect]

# Actuals (#2632): chars/4 over the realized diff (git diff b1bdb47..HEAD = 45757 bytes)
actuals:
  tokens: 11439
  tasks: 4
  commits: 4
  plan_head_before: b1bdb47
  plan_head_after: 440bf60

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pure detection over injected JSON plus read-only repo reads; no subprocess, no network"
    - "Exact-match trust gates: identity by packageName equality, dependency edges by exact filename"

key-files:
  created:
    - skills/ai-kit-spec-goal-prompt/scripts/gp_scope.py
    - tests/test_ai_kit_spec_goal_prompt_scope.py
  modified:
    - Makefile
    - .pre-commit-config.yaml

key-decisions:
  - "Plans are identified by filename; a Depends-on edge needs an exact backticked filename of a loaded plan (27 D-08)."
  - "The rest of a Depends-on line is one free-text entry, so the work-set question shows a sentence rather than fragments."
  - "has_context comes from roadmap analyze (D-24); has_spec from the *-SPEC.md glob."
  - "detect_scope loads phases only when a roadmap JSON is supplied."

patterns-established:
  - "Test names for plans use full filenames (a.md) where the plan's shorthand said a."

requirements-completed: []  # GPS-01 and GPS-02 have pure detection and ordering here; the user-facing detect CLI and its wiring land in later plans (see Deviations).

# Metrics
duration: unmeasured (start time was not recorded)
completed: 2026-10-31
status: complete
---

# Phase 27 Plan 02: Scope detection (phases, OpenGSD identity, superpowers order and failure scope) Summary

**Pure scope detection: GSD phase state with exact OpenGSD identity, superpowers plans with exact Depends-on edges, a stable execution order with transitive failure scope, and the contract scope object for all five kinds**

## Performance

- **Duration:** unmeasured (the start timestamp was not recorded)
- **Tasks:** 3 of 3 completed, plus one Rule 1 fix commit
- **Files created:** 2; **files modified:** 2

## Accomplishments
- `load_phases` merges the three phase sources in numeric order (16 < 16.1 < 17); a requested phase missing from the roadmap raises, and `dir`, the only path field, is repo-relative.
- `opengsd_identity` accepts only the exact `@opengsd/gsd-core` package name; near-miss names, missing, malformed and non-object documents are `unverified`.
- `load_plans` parses `**Depends on:**`: an exact backticked filename of a loaded plan becomes an edge, anything else is free text, `none` and a missing line are independent.
- `execution_order` is a Kahn order that always takes the smallest ready filename; a cycle raises `ValueError("dependency cycle ...")`. `dependents` returns the transitive dependents in that order.
- `scope_kind` and `detect_scope` return the contract `scope` object; `both` and `none` carry an `ask`; detection is read-only (a test compares the tree before and after).

## Task Commits

1. **Task 1: phase state and OpenGSD identity** - `7f40635` (feat)
2. **Task 2: superpowers plans, Depends-on edges, order and failure scope** - `63d54d5` (feat)
3. **Task 3: scope kind and detect_scope** - `40107ba` (feat)
4. **Rule 1 fix: Depends-on free text kept as one entry** - `440bf60` (fix)

**Plan metadata:** recorded in the docs commit that adds this file (see the completion report).

## Files Created/Modified
- `skills/ai-kit-spec-goal-prompt/scripts/gp_scope.py` - the detection functions and the `Phase`, `Plan`, `ScopeInputs` records (stdlib only; imports `gp_common.phase_key`)
- `tests/test_ai_kit_spec_goal_prompt_scope.py` - 39 tests: TestPhases (10), TestIdentity (4), TestPlans (16), TestScopeKind (9)
- `Makefile`, `.pre-commit-config.yaml` - regenerated test-group listings via `tools/gen_test_groups.py`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Depends-on free text split into fragments**
- **Found during:** a live check, after Task 3, that ran the parser over this repo's 38 superpowers plans (3 have a Depends-on line, as D-08 predicted).
- **Issue:** free text was split on commas and backticks, so the work-set question would have shown fragments such as `/` and `E5a (`. The edges were correct; the user-facing text was not.
- **Fix:** the rest of the line is one free-text entry (linked names removed, other backticks unwrapped). A test pins a mixed line.
- **Files modified:** `gp_scope.py`, `tests/test_ai_kit_spec_goal_prompt_scope.py`
- **Commit:** `440bf60`

### Scope notes (not auto-fixed; carried forward)

**2. [Scope gap] A requested plans work set is not applied in detect_scope.** The contract says work sets are restricted "when given". `ScopeInputs` has no file list, and `numbers` restricts phases only. The caller restricts plans until the CLI plan wires the answers. Recorded as an open deviation in `.planning/WINDOWS.md` so the ship gate sees it.

**3. [Scope note] Requirements GPS-01 and GPS-02 are not marked complete.** This plan delivers the pure detection and ordering. The `detect` command and its wiring land in later plans. This follows the 27-01 precedent.

**4. [Scope note] TDD red for Task 1 was an ImportError** (the module did not exist yet), not an assertion failure. Each later red was a real failing assertion or missing attribute.

## Known Stubs

None in the files this plan created or modified. The 27-01 stub `skills/ai-kit-spec-goal-prompt/SKILL.md` remains open until plan 27-10, as recorded in `.planning/WINDOWS.md`.

## Threat Flags

None. No network endpoint, subprocess, auth path or schema change was added. `gp_scope.py` imports no subprocess or network module (checked by grep and by the file's imports).

## Unverified Items

- **Live checks run on this checkout (read-only):** `query roadmap.analyze` (18 phases, fields `has_context`, `plan_count`, `disk_status` present), `query init.phase-op 27` (`has_reviews` and `has_verification` are booleans; `phase_dir` and `state_path` present and never read), and `runtime-identity` (`packageName` `@opengsd/gsd-core`). `detect_scope` on this checkout gave kind `opengsd`, identity `opengsd`, phase 27 with `cross_ai_plans` 13, and no absolute path in the output. This was not run through a CLI, which does not exist yet.
- **Not live-checked:** decimal phases such as `16.1` on the real roadmap (only the fixtures cover them), and a `.planning/` project without a roadmap argument.
- **Superpowers parser, live:** all 38 plans in `docs/superpowers/plans` parse and order (`execution_order` returns 38). Only the three Depends-on lines were exercised, and only one of them links a plan (`2026-06-19-e4c-external-segments-core.md`).
- **Test runs:** the unit group ran through `tools/run_unittest_parallel.py --group unit` (64/64 modules passed) after the final code change. Also passed: `tests.test_gate_scope`, ruff, pylint (10.00), pyright (0 errors), and vulture on the touched paths. `make validate` and `make test` were not run as whole targets; the pre-commit hooks ran on each commit.
- **gsd-tools progress:** `state update-progress` reported 0% while the STATE frontmatter progress stayed at 6%. I did not hand-edit the frontmatter. This looks like a pre-existing mismatch in the tool, not something this plan changed.

## Self-Check

- Created files exist: `skills/ai-kit-spec-goal-prompt/scripts/gp_scope.py`, `tests/test_ai_kit_spec_goal_prompt_scope.py`.
- Commits `7f40635`, `63d54d5`, `40107ba`, `440bf60` are on the branch with `feat(27-02):` and `fix(27-02):` subjects.
- `commits: 4` was measured as `git rev-list --count b1bdb47..HEAD` at the time of writing.

## Self-Check: PASSED
