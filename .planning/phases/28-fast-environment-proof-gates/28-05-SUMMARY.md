---
phase: 28-fast-environment-proof-gates
plan: 05
subsystem: testing
tags: [arch-test, ast-rule, fixtures, frozen-history, planning-reader, host-cli, tripwire]
requires: ["28-01", "28-04", "28-06"]
provides:
  - "tests/test_arch.py check_no_planning_reader, planning_reader_exception_problems, PLANNING_READER_EXCEPTIONS (empty) and test_no_test_reads_planning / test_planning_reader_exceptions_stay_empty"
  - "tests/test_arch.py check_no_host_cli_calls, SPAWN_PROGRAM_POSITION, _host_cli_names (ast read of tools/run_unittest_parallel.py HOST_CLI_NAMES) and test_no_test_calls_a_host_cli"
  - "tests/fixtures/archived/{26,22,21.3}/: frozen copies of the checkers and evidence the arch-era tests read, each with a frozen-history header"
  - "tests/fixtures/curated_config_v2/repo-config.json: committed config copy for the curated eval scratch project"
  - "tests/gsd_curated_eval.py snapshot --repo-root (the tests point it at a scratch repo)"
  - "tests/test_ai_kit_spec_goal_prompt_e2e.py: test_detect_on_a_copy_of_this_repo, source_files(repo), copy_checkout(dest), test_source_files_without_git"
affects: [28-07, 28-08, 28-09]
tech-stack:
  added: []
  patterns:
    - "AST rule over tests/*.py with three root scopes (module, function, class attribute) and a pinned empty exception list"
    - "frozen fixture copies: one header line naming the source path and copy date, rest byte-identical"
    - "host CLI names read from the runner with ast.literal_eval, never a second copy and never an import"
key-files:
  created:
    - tests/fixtures/archived/26/26-OWNER-CAPTURES.md
    - tests/fixtures/archived/26/skill-judge/check_verdicts.py.txt
    - tests/fixtures/archived/22/22-INTERACTIVE-PI.md
    - tests/fixtures/archived/22/22-SKILL-JUDGE.md
    - tests/fixtures/archived/22/22-SMOKE-PI.md
    - tests/fixtures/archived/22/22-SPIKE-PI-AGENTS.md
    - tests/fixtures/archived/22/live/check_pi_live.py.txt
    - tests/fixtures/archived/22/live/pi_mock_provider.py.txt
    - tests/fixtures/archived/22/live/trim_pi_capture.py.txt
    - tests/fixtures/archived/22/skill-judge/ (six reports: pre-/post-native-opus, pre-/post-opencode-plan-review, and their -r1 variants)
    - tests/fixtures/archived/21.3/21.3-LIVE.md
    - tests/fixtures/archived/21.3/live/check_live.py.txt
    - tests/fixtures/curated_config_v2/repo-config.json
  modified:
    - tests/test_arch.py
    - tests/test_phase26_owner_captures.py
    - tests/test_pi_live_tools.py
    - tests/test_tool_advisor_core.py
    - tests/gsd_curated_eval.py
    - tests/test_gsd_curated_eval.py
    - tests/test_ai_kit_spec_goal_prompt_e2e.py
decisions:
  - "The .planning/ rule is static and literal-form only; its run-time backstop is plan 28-08's long-path matrix clone (named in the rule's docstring)."
  - "The host-CLI static rule reports a host program only at a fixed program position or a literal executable= keyword; an argv or executable value built in a variable is the documented gap, covered at run time by the 28-01 tripwire."
  - "The goal-prompt dogfood copy drops every path under .planning/ and is built with git ls-files when the checkout has git, or a filtered walk when it does not."
  - "git_status and the copy helpers scrub GIT_* variables: a commit hook exports GIT_INDEX_FILE, which would point these git calls at the outer index."
metrics:
  duration: "not recorded"
  completed: 2026-11-04
commits: 3
plan_head_before: ccb65b0d8d6f8ad2172aab783b04b1a4934dd826
plan_head_after: 124ca2733225f62f83f0d4c7fb8aa703085722fe
actuals:
  tokens: 39014
  tasks: 3
  commits: 3
status: complete
---

# Phase 28 Plan 05: Frozen fixtures, the `.planning/` reader rule and the host-CLI rule Summary

Tests read frozen fixture copies and a config copy instead of the live `.planning/`; an AST rule holds that line with an empty, pinned exception list, and a second AST rule rejects a test that spawns a host CLI by name outside `tests/host_fakes.py`.

## What was built

- **Task 1 (`d0d2cd4`) tracer:** `check_no_planning_reader` in `tests/test_arch.py` tracks repo roots per module, per function and per class attribute (`cls.repo` set in `setUpClass`), with `__file__` and cwd calls (`Path.cwd()`, `pathlib.Path.cwd()`, `os.getcwd()`) as roots. It flags `/`, `os.path.join`, `Path`/`PurePath`, `.joinpath`, f-string and concatenation joins with `.planning`, and a relative `.planning` path passed to a filesystem call or Path method. The phase-26 owner-capture test reads `tests/fixtures/archived/26` (no skip).
- **Task 2 (`6ab8d14`):** phase-21.3 and phase-22 checkers and evidence copied to `tests/fixtures/archived/`; `test_pi_live_tools.py` and `test_tool_advisor_core.py` read them (the `.py.txt` checkers load through an explicit `SourceFileLoader`, run with `sys.executable -I`); the judged-archive unpack uses `tarfile` with `filter="data"`; `gsd_curated_eval._scratch_project` copies `repo-config.json`; `snapshot --repo-root` is honoured by `_cmd_snapshot`; the goal-prompt dogfood detects on a copy of the checkout without `.planning/`; `test_legacy_references_live_tree` skips `.planning/` before the open; `PLANNING_READER_EXCEPTIONS` is empty and pinned.
- **Task 3 (`124ca27`):** `check_no_host_cli_calls(tree, names)` with the `SPAWN_PROGRAM_POSITION` table (subprocess family, `os.exec*`, `os.posix_spawn*`, `asyncio.create_subprocess_exec`, `os.spawn*`, `os.system`/`os.popen`, `asyncio.create_subprocess_shell`), the literal `executable=` keyword, and `shutil.which` (including a bare `which` imported from `shutil`). `HOST_CLI_NAMES` is read from `tools/run_unittest_parallel.py` with `ast.literal_eval`. `test_no_test_calls_a_host_cli` walks `tests/*.py`, exempting only `tests/host_fakes.py`.

## Verification

| Command | Exit | Summary |
| --- | --- | --- |
| `python3 tools/run_unittest_parallel.py tests.test_arch tests.test_phase26_owner_captures tests.test_gate_scope` (Task 1) | 0 | 3/3 modules passed (test_arch 70 tests, phase26 1 test, not skipped) |
| `python3 tools/run_unittest_parallel.py tests.test_arch tests.test_pi_live_tools tests.test_tool_advisor_core tests.test_gsd_curated_eval tests.test_gate_scope` (Task 2) | 0 | 5/5 modules passed (re-run after commit: 5/5) |
| `uv run python tools/run_unittest_parallel.py tests.test_ai_kit_spec_goal_prompt_e2e` (Task 2) | 0 | 1/1 modules passed, 5 tests |
| `... tests.test_ai_kit_spec_goal_prompt_e2e.TestDogfood` (Task 2, by name) | 0 | 2 tests ran (copy-based detect, source_files without git) |
| `python3 tools/run_unittest_parallel.py tests.test_arch tests.test_phase26_owner_captures tests.test_pi_live_tools tests.test_tool_advisor_core tests.test_gsd_curated_eval` (Task 3) | 0 | 5/5 modules passed, no `tripwire:` block |
| Final check, all six modules plus the uv e2e module | 0 / 0 | 6/6 and 1/1 modules passed; no `tripwire:` line |
| `uv run ruff check` on every touched test file | 0 | All checks passed |
| `uv run pyright` on every touched test file | 0 | 0 errors |

Commit-stage evidence (`staged:` lines):
- `d0d2cd4` (Task 1): `staged: 4 files -> 7 modules`: test_ai_kit_project_rules_arch, test_arch, test_gate_scope, test_phase26_owner_captures, test_run_unittest_parallel, test_staged_commit_e2e (uv child, 8 cases), test_staged_mapper. No cross-AI e2e module. The first attempt was refused by ruff (see deviations) and was not committed.
- `6ab8d14` (Task 2): `staged: full unit+arch run: shared test helper or fixture: tests/fixtures/archived/22/22-INTERACTIVE-PI.md (3 modules)`, then 79/79 modules passed. The fail-safe full run is expected for a shared fixture under 28-06. No e2e module was selected.
- `124ca27` (Task 3): `staged: 1 files -> 6 modules`, 6/6 modules passed.

## Acceptance criteria

- Task 1: `check_no_planning_reader` and `test_no_test_reads_planning` exist; every join-form non-vacuity case fails its offender and the temp-project case passes. `rg -n "\.planning" tests/test_phase26_owner_captures.py` prints nothing. `tail -n +2` of the fixture cmp-equals the source (exit 0), and line 1 starts with `<!-- Frozen copy of`.
- Task 2: `PLANNING_READER_EXCEPTIONS` is empty; `test_planning_reader_exceptions_stay_empty` and its non-vacuity case pass. `rg -n "REPO_ROOT / \".planning\"" tests/gsd_curated_eval.py` prints nothing. `rg -n "/var/home|/home/[a-z]|/Users/" tests/fixtures/archived` prints nothing. `rg -n "\"tar\"" tests/test_pi_live_tools.py` prints nothing. Both dogfood tests pass. After the task commit and a fresh verify run, `git status --porcelain tests/fixtures/archived` is empty.
- Task 3: `check_no_host_cli_calls` and `test_no_test_calls_a_host_cli` exist and pass on the tree. `rg -n "HOST_CLI_NAMES" tests/test_arch.py` matches. `rg -n "spec_from_file_location\(.*run_unittest_parallel|import run_unittest_parallel" tests/test_arch.py` prints nothing. Each spawning family and form has a non-vacuity subtest; the clean forms return no violation.

## `.planning/` reader rule: first-run hits and outcomes

The first run of the new rule over `tests/*.py` found three direct readers, matching the plan's expected list:
- `tests/gsd_curated_eval.py:4168` `REPO_ROOT / ".planning" / "config.json"` (in `_scratch_project`): moved to the fixture copy.
- `tests/test_pi_live_tools.py:15` `ROOT / ".planning" / "milestones" / "v1.3-phases"`: moved to `tests/fixtures/archived/22`.
- `tests/test_tool_advisor_core.py:336` `os.path.join(_ROOT, ".planning", ...)`: moved to `tests/fixtures/archived/21.3`.

The re-run after Task 2 found 0 hits.

## Indirect-reader search (Task 2 step 6)

Pattern search `str\(REPO\)|str\(REPO_ROOT\)|_REPO_ROOT\b|snapshot\(REPO_ROOT|snapshot\(_REPO_ROOT|snapshot\(_abs\(REPO_ROOT` over `tests/*.py`:
- `tests/test_ai_kit_gsd_curated_config_matrix.py:93`: the repo root appears only in an output-path assertion. Not a reader.
- `tests/test_ai_kit_spec_goal_prompt_e2e.py:177`: dogfood `detect --repo`. Moved to a copy (Task 2 step 4).
- `tests/test_ai_kit_spec_goal_prompt_signals.py:259,270` `gp_e2e.detect_e2e(str(REPO))`: `gp_e2e` lists top-level names with `os.listdir`, probes `<browser>.config.*` with `isfile`, and reads only `tests/` and the target files it names. No `.planning` path. Not a reader.
- `tests/test_cross_ai_skill_text.py:268` `enumerate_entries(str(REPO))`: `tools/setup.py` enumerates `CATEGORIES = ("agents", "commands", "skills")`. Not a reader.
- `tests/test_precompact_shims_e2e.py:102,192` `cwd=REPO`: the harness runs the `tools/hooks/pi` and `opencode` shims. A grep of those folders and `tests/fixtures/precompact` finds no `.planning` path. Not a reader.
- `tests/test_curated_config_e2e.py`, `test_curated_config_apply_e2e.py`, `tests/gsd_curated_eval.py` (`RUNTIME_DIR` at 2642, 3008, 3022, 5073): `RUNTIME_DIR` is the checkout's gsd-core install (`.claude/gsd-core`), and every run uses a scratch project as cwd. Not a `.planning` reader.
- `tests/gsd_curated_eval.py:3273,3300` `git -C REPO show/rev-parse`: git history only, no working-tree read. `4597,5100` `"repo_root"` labels and `2120` output replacement: output normalisation, not reads. `725,737`: realpath comparison in a refusal guard.
- `tests/gsd_curated_eval.py:3875` `snapshot(_abs(REPO_ROOT), ...)` (owner `run --snapshot` path): the only test that reaches it, `tests/test_gsd_curated_eval.py:4771`, patches `ev.snapshot`, so the live checkout is not read. The owner path is unchanged.

## Whole-tree scan hits (`ls-files|os.walk(|rglob(`) and outcomes

- `tests/test_arch.py` `test_legacy_references_live_tree` (`git ls-files` then open every path): **fixed**. `.planning/` paths are skipped before the open. `check_legacy_references` lists `.planning/` among its history prefixes, so its result is unchanged.
- `tests/test_gate_scope.py:432` `ungated_python_assets(REPO_ROOT)`: its walk skips dot-directories, so `.planning` is never opened. Not a reader.
- `tests/test_ai_kit_spec_goal_prompt_e2e.py:63` `git_status` fallback walk: now runs only on the copy, skipping `.git`, `.venv`, `tmp`, `__pycache__`.
- `tests/gsd_curated_eval.py:265,450,1181,2239,3923,4106`: walk a skill folder, a run dir, a caller-given root, or a scratch project's `.planning` (4106). Not the live project.
- `tests/test_ai_kit_spec_runtimes_table.py:533` (`git ls-files skills tools README.md AGENTS.md`), `tests/test_run_unittest_parallel.py:421` (`tools`, `skills`), `tests/test_arch.py` walks (`skills`, `tools`), `tests/test_quota_policy_text.py:217` (`skills`), `tests/test_curated_config_golden.py:575` (`fixtures`), `tests/test_tool_substitution_hook.py:1301` (hooks dir): none reaches `.planning/`.
- Temp-tree walks (`test_setup.py`, `test_staged_mapper.py`, `test_ai_kit_spec_goal_prompt_scope.py`, `test_ai_kit_project_rules_agents.py`, `test_curated_config_inventory.py`, `test_ai_kit_spec_goal_prompt_evals.py` `repo`, the session-wake, cursor-quota and project-rules-makefile scratch walks): roots are temp trees made by the test. Not readers.

## Host-CLI scan (Task 3) and violations fixed

- The rule's live-tree scan over `tests/*.py` found **0 host-CLI hits** on the first run, with `tests/host_fakes.py` exempt. No test needed rerouting through the fakes, so none was changed.
- Scan size: 202 spawn calls resolved to a fixed program position (`git` 31, `node` 17, `bash` 5, `ps` 1, plus `subprocess`-family argv lists). 148 calls have a variable or non-constant program (for example `sys.executable`); the static rule cannot see those, and the run-time tripwire from plan 28-01 is their layer.
- The non-vacuity subtests each fail on their synthetic offender, and the clean forms (a data list, an `assertEqual` argument, a variable program, a non-constant `executable=`) pass.

## Key-looking strings in fixtures

A regex scan of `tests/fixtures/archived` and `tests/fixtures/curated_config_v2/repo-config.json` for `sk-…`, `ghp_…`, `AKIA…`, `xox…`, `Bearer …` and PEM headers finds **nothing**. The words that matched a looser scan are not values: `token` (a field name in a smoke-table row), `secret-scan` (a command name), and `apikey`, `bearer`, `authorization` as forbidden markers inside `trim_pi_capture.py`. The `repo-config.json` fixture was checked the same way and holds no key-like value.

## Header-strip files

None. No checker rejected the frozen-history header line, so no `strip_frozen_header` helper was added. Every frozen copy runs with its header in place (`.md` copies use an HTML comment, which keeps the markdown headings unchanged).

## Deviations from Plan

**1. [Rule 1 - Lint] Ruff refused the first Task 1 commit**
- **Found during:** Task 1 commit (pre-commit `ruff`)
- **Issue:** five findings: SIM102 (nested `if`) at four places and B905 (`zip()` without `strict=`).
- **Fix:** conditions combined or restructured with the same behaviour, `zip(..., strict=False)`, re-checked with ruff and pyright, then committed. The refused attempt was never committed.
- **Commit:** `d0d2cd4`

**2. [Rule 2 - Correctness] Git calls in the test scrub `GIT_*` variables**
- **Found during:** Task 2 step 4 (designing the copy)
- **Issue:** a commit hook exports `GIT_INDEX_FILE`. Without a scrub, `git -C <copy>` would read the outer repository's index, and `git_status` would be unreliable.
- **Fix:** `_clean_env()` drops `GIT_*` for `git_status`, `source_files` and the copy's init/add/commit.
- **Commit:** `6ab8d14`

**3. [Plan naming] The dogfood test name**
- The plan's rename, `test_detect_on_a_copy_of_this_repo`, is used. The old `test_detect_on_this_repo` is gone.

**4. [TDD sequence, Task 3] No failing run was captured before the rule**
- The tests and the rule were written in one editing pass: the non-vacuity and live-tree tests were added first, then the rule, then the suite was run. I did not capture a red run before the implementation, so the red step is not evidenced in the log.
- Non-vacuity coverage itself is complete: every spawning family and form has a subtest that fails on its offender.

## Known Stubs

None.

## Threat Flags

None new. The rule implements the T-28-28 mitigation (basename match at each program position and at a literal `executable=`). The fixtures carry no machine path and no key-like value (T-28-10).

## Self-Check: PASSED

- Created fixture files exist (`tests/fixtures/archived/26`, `22`, `21.3`, and `tests/fixtures/curated_config_v2/repo-config.json`).
- Task commits `d0d2cd4`, `6ab8d14` and `124ca27` are ancestors of HEAD.
- The working tree is clean after the final verify run; `tests/fixtures/archived` is unchanged.
- `STATE.md`, `ROADMAP.md` and `.planning/config.json` are untouched (none of them appears in the diff from the plan's base commit).
