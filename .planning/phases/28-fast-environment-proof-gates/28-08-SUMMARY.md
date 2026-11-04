---
phase: 28-fast-environment-proof-gates
plan: 08
subsystem: testing
tags: [test-env-matrix, environments, tmpdir, long-path, host-cli, reports, make, pyright]
requires: ["28-02", "28-03", "28-05", "28-07"]
provides:
  - "make test-env-matrix: all four tiers (make -j1 -k -C <checkout> test) in six environments (plain, host-session, no-host-cli, long-path, custom-tmpdir, outside-git), run one after another, compared module by module (pass/fail and skip reasons) against plain"
  - "tools/run_unittest_parallel.py writes one JSON report per module when AI_KIT_TEST_REPORT_DIR is set (module, rc, skips, ran); baseline_env drops the variable so nested runners publish nothing; reports are created exclusively and duplicates are flagged"
  - "baseline_problems: the plain run must be green and complete (make rc 0, exactly one report per expected module) or the matrix stops with env plain: baseline not green"
  - "make_long_checkout (a 210-character clone with the working-tree state, no .planning/) and the custom TMPDIR case (a space in the path, inside a git repo)"
affects: [28-09]
tech-stack:
  added: []
  patterns: ["one serial make per environment with MAKEFLAGS, MFLAGS and MAKELEVEL removed", "scratch HOME per environment with AI_KIT_REFUSE_REAL_HOME=1 and toolchain caches forwarded from the caller env once", "outer logging shims on PATH record host CLI calls", "shell words and quoted paths in test fixtures (shlex.quote), so a TMPDIR with a space changes nothing"]
key-files:
  created:
    - tools/env_matrix.py
    - tests/test_env_matrix.py
  modified:
    - tools/run_unittest_parallel.py
    - tests/test_run_unittest_parallel.py
    - Makefile
    - .pre-commit-config.yaml
    - tests/test_gate_scope.py
    - tests/test_staged_mapper.py
    - tests/test_setup.py
    - tools/setup.py
    - tests/test_gsd_curated_eval.py
    - tests/gsd_curated_eval.py
    - tests/test_ai_kit_session_wake.py
    - tests/test_ai_kit_project_rules_all.py
    - tests/test_ai_kit_project_rules_all_e2e.py
    - tests/test_ai_kit_spec_goal_prompt_e2e.py
    - tests/test_hook_registry.py
key-decisions:
  - "The six environments run strictly sequentially in a plain loop, plain first; the printed estimate after plain is about six times its duration"
  - "The matrix verdict needs a green, complete plain baseline; two identical failing runs cannot read as identical"
  - "Only top-level runners write reports (baseline_env drops AI_KIT_TEST_REPORT_DIR), so a nested runner's intentional failure cannot reach the matrix"
  - "Long-path clone: git clone --local --no-hardlinks (approved by the orchestrator; see Deviations)"
  - "A quoting defect in the product (tools/setup.py wire_statusline) was real: an install path with a space split into two shell words. Fixed in the product, not only in the test"
  - "Test fixes never add a skip: the session-wake missing-interpreter test was redesigned to hold in every TMPDIR"
requirements-completed: [GATE-02, GATE-03]
status: complete
duration: not measured (no start timestamp was recorded; see Deviations); the commit span alone is 2 h 26 min
completed: 2026-11-04
commits: 8
plan_head_before: 29d31c05c78d070ef091f8669843fd163eee4b22
plan_head_after: 8f8e996f7c395e9397c9242ef994fe6e5da272af
actuals:
  tokens: 28705   # chars/4 over the realized diff 29d31c0..HEAD (114819 bytes, 17 files)
  tasks: 3
  commits: 8
---

# Phase 28 Plan 08: Six-environment matrix, reports and host-CLI proof Summary

`make test-env-matrix` runs every test tier in six environments and compares each module's pass/fail and skip reasons against the plain run. The final run on `8f8e996` reports `matrix: identical in 6 environments` with no host CLI call recorded.

## What was built

- **Runner reports (Task 1).** `REPORT_DIR_ENV`, `parse_skips`, `report_text`, `publish_report`; `baseline_env` drops the variable; `ReportTest` (six cases, including the nested-runner and duplicate cases).
- **Matrix tool (Tasks 1 and 2).** `tools/env_matrix.py`: `ENV_NAMES`, `Report`, `load_reports`, `expected_modules`, `inventory_problems`, `baseline_problems`, `compare_reports`, `host_free_path`, `long_checkout_path`, `make_long_checkout`, `run_environment`, `main` with `--only`. Scratch root via `tempfile.mkdtemp(prefix="aikit-matrix-")`, refused inside a git work tree, removed in a `finally`.
- **Make target (Task 1).** `test-env-matrix` in `.PHONY`, outside `test` and `validate`; pinned by `test_env_matrix_stays_out_of_gates` with a non-vacuity case. Test-group listing regenerated with `tools/gen_test_groups.py`.
- **Unit tests.** `tests/test_env_matrix.py`: `TestCompareReports`, `TestBaselineProblems`, `TestLoadReports`, `TestEnvironmentBuilders`, `TestMatrixRuns`, `TestLongCheckoutPath`, `TestHostFreePath`, `TestLongCheckoutClone` (staged, unstaged, deleted, renamed, untracked, ignored, symlink, dangling and type-swap states; no write through a symlink; the source-as-target refusal), `TestTheOtherFourEnvironments`, `test_environments_run_one_after_another`, `test_the_inner_make_is_serial_and_inherits_no_make_state`, `test_the_toolchain_forwards_survive_the_scratch_home` (the plan's `test_environments_run_sequentially`, `test_inner_make_is_serial` and `test_forwards_survive_the_scratch_home`, under longer names).
- **Environment faithfulness fixes (found by the matrix).** Shell and path fixtures quoted where a TMPDIR with a space reached them; `_clean_env` keeps `GIT_CEILING_DIRECTORIES` so a temp repo under a TMPDIR inside a repo does not see the outer repo; the agents probe runs in a scratch repo with its own `.planning/` marker; the claude status-line writer quotes its path; the session-wake test no longer depends on TMPDIR.

## Matrix runs

Environment: `AI_KIT_REFUSE_REAL_HOME=1`, `make test-env-matrix` run from the worktree, plain run first.

- Final full run on `8f8e996` (`tmp/p28/matrix-final.log`), command `AI_KIT_REFUSE_REAL_HOME=1 make test-env-matrix`:
  - `matrix: plain took 452s; expect about 2714s for six environments`
  - `env plain: identical (100 modules, make rc 0, 452s)`
  - `env host-session: identical (100 modules, make rc 0, 454s)`
  - `env no-host-cli: identical (100 modules, make rc 0, 457s)`
  - `env long-path: checkout path is 210 characters`, then `env long-path: identical (100 modules, make rc 0, 446s)`
  - `env custom-tmpdir: identical (100 modules, make rc 0, 448s)`
  - `env outside-git: identical (100 modules, make rc 0, 448s)`
  - `matrix: identical in 6 environments`, exit 0. Zero `host CLI calls:` lines.
- Full run on `eac38d5` (`tmp/p28/matrix-final-eac38d5.log`), same command: `matrix: identical in 6 environments`, exit 0, before the two pyright commits. The two later commits change type annotations only, so the full run was repeated on `8f8e996`.

Re-runs and first runs, in order (logs under `tmp/p28/`):

1. `AI_KIT_REFUSE_REAL_HOME=1 python3 tools/env_matrix.py --only plain` (`matrix-plain.log`): `env plain: identical (100 modules, make rc 0, 459s)`, `matrix: identical in 1 environments`. Duration 459 s, estimate 2751 s.
2. `AI_KIT_REFUSE_REAL_HOME=1 python3 tools/env_matrix.py --only host-session` (`matrix-host-session.log`): `env host-session: identical (100 modules, make rc 0, 467s)`, `matrix: identical in 2 environments`.
3. `AI_KIT_REFUSE_REAL_HOME=1 make test-env-matrix` (`matrix-1.log`, first full run): `env long-path: 2 differences`, `env custom-tmpdir: 10 differences`, `matrix: differences found`.
4. `AI_KIT_REFUSE_REAL_HOME=1 python3 tools/env_matrix.py --only custom-tmpdir` (`matrix-2.log`): `env custom-tmpdir: 6 differences`, `matrix: differences found`.
5. `AI_KIT_REFUSE_REAL_HOME=1 python3 tools/env_matrix.py --only custom-tmpdir` (`matrix-custom.log`, after the fixes): `env custom-tmpdir: identical (100 modules, make rc 0, 449s)`, `matrix: identical in 2 environments`.
6. `AI_KIT_REFUSE_REAL_HOME=1 make test-env-matrix` (`matrix-final-eac38d5.log`): `matrix: identical in 6 environments`, exit 0.
7. `AI_KIT_REFUSE_REAL_HOME=1 make test-env-matrix` (`matrix-final.log`, final HEAD): `matrix: identical in 6 environments`, exit 0.

Each environment ran `make -j1 -k -C <checkout> test` with `MAKEFLAGS`, `MFLAGS` and `MAKELEVEL` removed. Environments ran one after another; no two overlapped.

## Other checks on the final tree

- `AI_KIT_REFUSE_REAL_HOME=1 make validate`: exit 0 (`tmp/p28/validate.log`). It first failed with four pyright errors (fixed in `8f8e996`). `check-dogfood` printed an informational warning: the apply no-write guard did not run because the checkout-local gsd-core is 1.18.0 (needs 1.16 or 1.17); it is not a failure and is left as is.
- `ruff check` on every file this plan touched: `All checks passed!`.
- Session-wake module: `tests.test_ai_kit_session_wake` 56 tests, exit 0 plain and under a spaced TMPDIR.
- gsd harness module: `tests.test_gsd_curated_eval` 316 tests, exit 0 plain and under a spaced TMPDIR (`tmp/p28/gsd-plain.txt`, `tmp/phase28-w7/gsd-custom-3.txt`).
- `tests.test_gate_scope` and `tests.test_staged_mapper`: 2 modules passed, exit 0.

## Evidence reach

The runner baseline already neutralizes host signals, puts the tripwire stubs first on PATH and fixes each module's cwd for runner modules, so for those modules the host-session, no-host-cli and outside-git environments mainly exercise make, uv and `tests/test_install.sh`. `outside-git` proves a start from a cwd outside git (the recipes still run in the checkout), and `no-host-cli` proves the host executables are off PATH, not uninstalled. The module-level evidence comes mainly from the long-path and custom-tmpdir environments.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Claude status-line command not quoted (product)**
- **Found during:** Task 3 (custom-tmpdir environment)
- **Issue:** `wire_statusline` wrote `python3 -S <path>` unquoted, so an install path with a space became two shell words.
- **Fix:** `shlex.quote` on the path (the cursor writer already quoted), matching fixtures in `tests/test_setup.py`, plus `test_a_status_line_path_with_a_space_is_written_as_one_argument`.
- **Files modified:** `tools/setup.py`, `tests/test_setup.py`
- **Commit:** 710d9e1

**2. [Rule 1 - Bug] gsd harness split commands on whitespace; reap label truncated after cutting**
- **Found during:** Task 3 (custom-tmpdir environment)
- **Issue:** `_shadow_failures` split Bash commands with `str.split()`, so `E='<path with space>'` became fragments; `_reap_strays` truncated the command before labelling it.
- **Fix:** shell-word tokenizer (`_command_tokens`, `_last_absolute_cd`); the label is written before truncation; the placeholder test expectation corrected to `<worktree>/home-inside/z`; the shadow test's `cd` fixture quoted.
- **Commit:** 6d47968

**3. [Rule 1 - Bug] Session-wake missing-interpreter test depended on TMPDIR**
- **Found during:** Task 3 (custom-tmpdir environment)
- **Issue:** the kernel reads a shebang only to the first space, so an interpreter under a TMPDIR with a space tested a different path.
- **Fix:** the test uses a fixed, space-free absent path and asserts it is absent first. No skip was added (the orchestrator's directive).
- **Commit:** e7ad6bf

**4. [Rule 1 - Bug] pyright errors blocked `make validate`**
- **Found during:** final validation
- **Issue:** `tests/test_gate_scope.py` (line 782-783: `hook_block()` returns `None` when absent) and `tests/test_staged_mapper.py` (line 762: mixed value types in the stub cases) had four pyright errors. Both lines predate this plan (from earlier phases, now in the base), but `make validate` must pass.
- **Fix:** an `assert block is not None`; `cases` annotated as `dict[str, Any]` entries. No test logic changed.
- **Commit:** 8f8e996

**5. [Rule 1 - Bug] Matrix found long-path and custom-tmpdir differences (earlier runs)**
- **Found during:** Task 3, runs 3 and 4 above
- **Issue:** long-path: the agents probe needed the repo's `.planning/` marker and asserted a realpath after cleanup; custom-tmpdir: `_clean_env` stripped `GIT_CEILING_DIRECTORIES` (an outer repo became visible), and several unquoted shell and path fixtures broke under a spaced TMPDIR.
- **Fix:** the probe runs in a scratch repo with its own marker, and its assertion sits inside the `with` block; the ceiling is kept; fixtures quoted with `shlex.quote` (a no-op for a plain path, so the plain environment is unchanged).
- **Commit:** ebfb25b (partial), then 710d9e1, 6d47968, e7ad6bf

### Deviations from the plan text

**1. Long-path clone uses `--no-hardlinks` (orchestrator-approved).** `git clone --local` failed with "Invalid cross-device link": `/tmp` is tmpfs (device 58) and `/var/home` is btrfs (device 60), so hard links cannot be created across them. The clone is `git clone --quiet --local --no-hardlinks`, with a one-line code comment; the scratch root is still removed in `finally`.

**2. The overlay also copies `.claude/scripts`.** The plan names `.claude/gsd-core`. `.claude/scripts` is gitignored local tooling (`.gitignore`: `.claude/`), so the clone copies it with symlinks kept for parity with the checkout. No test in the tree reads `.claude/scripts` by path (grep), so this is a parity choice, not a fix for a measured difference.

**3. No separate RED commit for Task 2 (tdd="true").** Phase 28 runs with TDD mode off (orchestrator direction), so Task 2's tests and code landed in one commit (`24262e0`).

**4. Plan-start ledger missing; duration not measured.** The plan-start ledger file was never written (lost at a context compaction), and no start timestamp was recorded. `plan_head_before` is the worktree's recorded base, `29d31c0`. The commit span 02:40 to 05:06 (-03:00) is 2 h 26 min; the real duration is at least that. The `commits: 8` figure is `git rev-list --count 29d31c0..HEAD`.

**5. Estimate versus actual.** The plan estimated 95000 tokens (confidence low). The realized diff measures 28705 tokens on the same chars/4 scale (114819 bytes over 17 files). The estimate was high by about 3.3 times.

## Out-of-plan files

Files changed beyond this plan's `files_modified`, each with its cause:

- `tools/setup.py`: quoted claude status-line path (Deviation 1 above).
- `tests/test_setup.py`: status-line fixtures quoted; one new test.
- `tests/gsd_curated_eval.py`: shell-word tokenizer and reap-label fix (Deviation 2).
- `tests/test_gsd_curated_eval.py`: quoted fixtures; corrected placeholder expectation; outside-workdir tests build their directory beside the checkout and clean it up.
- `tests/test_ai_kit_session_wake.py`: missing-interpreter test redesigned (Deviation 3).
- `tests/test_ai_kit_project_rules_all.py`: `shlex.quote` on the `<AGENTS_ENTRYPOINT>` and `<repo_root>` substitutions under a spaced TMPDIR.
- `tests/test_ai_kit_project_rules_all_e2e.py`: agents probe in a scratch repo with its own `.planning/` marker (Deviation 5).
- `tests/test_ai_kit_spec_goal_prompt_e2e.py`: `_clean_env` keeps `GIT_CEILING_DIRECTORIES`.
- `tests/test_hook_registry.py`: hook command fixture quoted.
- `tests/test_staged_mapper.py`: pyright type fix (Deviation 4); the errors predate this plan.

Files in the plan's list that changed: `tools/run_unittest_parallel.py`, `tests/test_run_unittest_parallel.py`, `tools/env_matrix.py`, `tests/test_env_matrix.py`, `Makefile`, `.pre-commit-config.yaml` (regenerated listing), `tests/test_gate_scope.py`.

## Commits

- `347c03e` feat(28-08): six-environment matrix: runner reports, compare tool, make target
- `24262e0` feat(28-08): build the other four matrix environments
- `ebfb25b` test(28-08): env-proof fixes the TMPDIR-with-space matrix run exposed (partial)
- `710d9e1` fix(setup): quote the claude status-line command so a path with a space stays one argument
- `6d47968` test(28-08): parse quoted Bash commands in the gsd harness and quote its shell fixtures
- `e7ad6bf` test(28-08): hold the missing-shebang-interpreter test in every TMPDIR
- `eac38d5` docs(28-08): state the no-.planning rule the long-path environment checks
- `8f8e996` test: satisfy pyright in the gate-scope and staged-mapper tests

## Known Stubs

None.

## Threat Flags

None. The matrix introduces no new network endpoint, auth path or trust boundary beyond the plan's threat model (T-28-17 to T-28-25).

## Deferred Items

- `check-dogfood` warning: the apply no-write guard does not run with the checkout-local gsd-core 1.18.0 (it needs 1.16 or 1.17). Informational; out of this plan's scope.

## Self-Check: PASSED

Checked: all 17 files named above exist; all 8 plan commits (`347c03e` to `8f8e996`) are ancestors of HEAD.
