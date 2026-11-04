---
phase: 28-fast-environment-proof-gates
plan: 06
subsystem: testing
tags: [staged-tests, pre-commit, name-index, fail-safe, runner]
requires: ["28-01", "28-04"]
provides:
  - "tools/staged_mapper.py: MapperError, Index, Decision, build_index, unit_tokens, covering_modules, decide, staged_paths (stdlib, read-only, rebuilt on every call)"
  - "runner --staged [PATH ...] mode, SHARED_MACHINERY, stale_machinery_names, _load_mapper; unit+arch in-process, unit-uv/integration/e2e in one uv child"
  - "pre-commit hook staged-tests (stages: [pre-commit], verbose, always_run) running python3 tools/run_unittest_parallel.py --staged"
  - "tests/test_staged_mapper.py (unit) and tests/test_staged_commit_e2e.py (e2e, real commits through the real hook)"
affects: [28-05, 28-07, 28-09]
tech-stack:
  added: []
  patterns: ["name index over tests/*.py sources with transitive helper reach", "any mapper failure falls back to the full unit+arch groups, never zero", "decision made over the sorted de-duplicated path list, so staging order cannot matter"]
key-files:
  created:
    - tools/staged_mapper.py
    - tests/test_staged_mapper.py
    - tests/test_staged_commit_e2e.py
  modified:
    - tools/run_unittest_parallel.py
    - .pre-commit-config.yaml
    - Makefile
    - tests/test_arch.py
    - tests/test_tool_substitution_hook.py
key-decisions:
  - "unit_tokens returns regex strings (any one selects a module); the fixture 'every folder' alternative is one anchored lookahead regex, so the OR-of-ANDs fits a flat tuple"
  - "decide runs the shared-machinery pass before the index is built; a shared path therefore reports shared machinery even when the index would fail"
  - "the arch group joins via Decision.arch (a staged .py under skills/, tools/ or tests/); the runner adds ARCH_MODULES, so the mapper knows no runner sets"
  - "stale_machinery_names and stale_exception_names check the runner's own REPO_ROOT, not the cwd passed to main, so a synthetic cwd in tests (and the copied runner in the e2e temp repo) stay consistent"
requirements-completed: [GATE-01]
status: complete
duration: ~95 min
completed: 2026-11-04
commits: 2
plan_head_before: 9a2837ac5de25c4fe88670079154dea77a3f1914
plan_head_after: dd4283d7e288e08bdeb7d71a4b3626135215f1ff
actuals:
  tokens: 18000
  tasks: 2
  commits: 2
---

# Phase 28 Plan 06: Staged-file mapper and the commit-stage hook Summary

The commit stage now runs only the test modules that cover the staged files, refuses the commit when one fails, and fails safe: shared test machinery, a shared helper or fixture, an empty answer or any mapper failure runs the full unit and arch groups, never zero.

## What was built

- **`tools/staged_mapper.py`** (stdlib only, writes nothing): `build_index` reads every `tests/*.py` (unreadable or undecodable raises `MapperError`) and builds each test module's reach text (own source plus, transitively, the helpers it names). `unit_tokens` maps a path to whole-token regexes: skill folder name; tool stems only in code forms (`<stem>.py`, quoted, `import`, `from <stem> import`, `from tools[.hooks] import` lists incl. parenthesised and `as`, dotted `.<stem>`); tests helper, fixture and test-module rules; `.planning/**` selects nothing; any other file selects by basename. `decide` returns the sorted covering modules or a full-run reason (`shared test machinery: <path>`, `shared test helper or fixture: <path> (<n> modules)`, `empty answer for covered file <path>`). `staged_paths` runs `git diff --cached --name-only -z --no-renames` as an argv list.
- **Runner `--staged`**: excludes `--group` and module names (exit 2). No paths means the staged list from git. Zero files prints `staged: no staged files; 0 modules` and exits 0. Mapper import/`decide`/`staged_paths` failures (broad `except`) print `staged: full unit+arch run: mapper error: <type>: <msg>` and run every unit and arch module. Unit+arch run through `_run_all` only when non-empty; unit-uv/integration/e2e run as one `uv run python <runner> <modules>` child (own session, registered for interrupt, never `--staged`); uv missing with any of them chosen prints the `make setup-env` pointer and returns 1. `SHARED_MACHINERY` and `stale_machinery_names` (exit 2 on a stale entry) added.
- **Hook** `staged-tests` between `py-compile` and `unittest`: `stages: [pre-commit]`, `verbose: true`, `always_run`, `pass_filenames: false`.
- **Tests**: 43 unit tests (`test_staged_mapper`) and 8 e2e cases (a-h) in a temp repo with the real hook block, including refusal on failure with HEAD unchanged, planning-only, shared machinery, unreadable test source (mapper error -> full run -> refused), empty commit, and no hook at the pre-push stage.

## Commit-stage evidence

- Task 1 commit (`68181fc`): the hook selected 7 staged files -> 28 modules, including `tests.test_cross_ai_runner_e2e` (356.8 s) under the uv child; `- duration: 398.74s`. A first attempt was refused with 27/28 passed (see deviation 2) after `- duration: 401.52s`.
- Task 2 commit (`dd4283d`): `staged: full unit+arch run: shared test machinery: .pre-commit-config.yaml`, 79/79 modules passed, `- duration: 51.4s`.

## Deviations from Plan

**1. [Rule 3 - Blocking] tests/test_arch.py rule 9 allowlist**
- Found during: Task 1. The runner's staged backstop (`# pylint: disable=broad-exception-caught` in `_staged_selection`) tripped `test_rule9_broad_except_only_in_listed_backstops`.
- Fix: listed `("tools/run_unittest_parallel.py", "_staged_selection")` with a comment (extends the rule, no bypass).
- Commit: 68181fc

**2. [Rule 1 - Bug] tests/test_tool_substitution_hook.py depended on the checkout path**
- Found during: Task 1 commit. `test_compose_names_only_installed` matched modern tool names by substring over the whole message, whose usage suffix holds the checkout path; this worktree's id (`...d33bfd729...`) contains `fd`, so the test failed in it (fails standalone at base too, only in a path containing `fd`/`bat`). The new hook correctly refused the commit.
- Fix: check names only in the part before ` Usage:`.
- Commit: 68181fc

**3. TDD red state not committed.** Task 2 was written test-first and run red locally (6 failures, 2 errors on the planned fail-safe branches; the Task 1 behaviours already passed), then green. The plan prescribes one commit per task, and the new commit-stage hook would refuse a deliberately failing test commit (no `--no-verify`), so no separate `test(...)` commit exists.

**4. Task 1 kept the runner's shared set out.** Per the plan's commit-cost note, Task 1's `decide` ignored `shared` and the runner had no `SHARED_MACHINERY` until Task 2.

## Known Stubs

None.

## Threat Flags

None. T-28-13 (argv lists only, staged names matched as text, uv receives discovered module names) and T-28-14 (every failure path runs more tests or exits 2) are implemented and pinned by tests.

## Verification

- `python3 tools/run_unittest_parallel.py tests.test_staged_mapper tests.test_run_unittest_parallel tests.test_gate_scope`: exit 0
- `uv run python tools/run_unittest_parallel.py tests.test_staged_commit_e2e`: exit 0, 8 tests, none skipped
- `make test-unit`: exit 0 (78/78 and 1/1); `make arch-test`: exit 0
- `--staged .planning/STATE.md`: `staged: 1 files -> 0 modules`, exit 0; `--staged --group unit`: exit 2
- ruff, pylint, pyright, vulture clean on the touched files

## Self-Check: PASSED

- FOUND: tools/staged_mapper.py, tests/test_staged_mapper.py, tests/test_staged_commit_e2e.py
- FOUND: commits 68181fc, dd4283d (ancestors of HEAD)
