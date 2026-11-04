---
phase: 28-fast-environment-proof-gates
plan: 04
subsystem: testing
tags: [check-dogfood, pre-push, no-write-guard, curated-config, live-project]
requires: ["28-01", "28-02"]
provides:
  - "make check-dogfood: the one sanctioned reader of the live .planning/ (runner copy pristine; curated-config write flows leave config.json* and cross-ai.mjs* untouched)"
  - "pre-push hook check-dogfood (verbose) and a make validate prerequisite, pinned by tests/test_gate_scope.py"
  - "the curated-config script, e2e, apply e2e and resolve-model matrix tests no longer read the live project"
affects: [28-06, 28-09]
tech-stack:
  added: []
  patterns: ["guard child = GUARD_TESTS in one `unittest -v` process under the runner's baseline_env and tripwire, bracketed by fingerprints", "counts kept apart: attempted / executed / skipped (a skip is never coverage)"]
key-files:
  created:
    - tools/check_dogfood.py
    - tests/test_check_dogfood.py
  modified:
    - Makefile
    - .pre-commit-config.yaml
    - tests/test_gate_scope.py
    - tests/test_curated_config_script.py
    - tests/test_curated_config_e2e.py
    - tests/test_curated_config_apply_e2e.py
    - tests/test_ai_kit_gsd_curated_config_matrix.py
    - tests/test_arch.py
    - tests/test_gsd_curated_eval.py
key-decisions:
  - "The guard reuses the three existing write-flow tests as its child instead of a second copy of the flows in tools/; their own assertions make a do-nothing run fail"
  - "The matrix hashes the resolved gsd-core folder by content; _tree_sha keeps its no-follow default (pinned by TestCoreTreeHash)"
  - "A class-level skip (setUpClass) is attributed to the class's guard tests, so it can never read as a missing result or as coverage"
requirements-completed: [GATE-05]
status: complete
duration: ~45 min
completed: 2026-11-03
commits: 3
plan_head_before: 4bcb37c982d5e4e3ac7068758f11a58e05171812
plan_head_after: 1f12c82c5b4223c8632667ee58f2705cb39862f1
actuals:
  tokens: 15150
  tasks: 3
  commits: 3
---

# Phase 28 Plan 04: check-dogfood Summary

`make check-dogfood` (also a verbose pre-push hook and a `make validate` prerequisite) checks the live runner copy byte-for-byte against the template and runs the three curated-config write-flow guard tests in one child, bracketed by fingerprints of the live `config.json*` and `cross-ai.mjs*` files; no test reads the live project any more.

## Commits

- `9c881d7` feat(28-04): check-dogfood checks the live runner copy as a command; TestDogfoodCopy removed (Task 1, tracer)
- `47e0e32` feat(28-04): check-dogfood runs the curated-config no-write guards against the live files; e2e modules stop reading the live project (Task 2)
- `1f12c82` feat(28-04): check-dogfood gates a push: pre-push hook, make delegate, validate prerequisite, gate-scope pin (Task 3)

## What changed

- `tools/check_dogfood.py` (stdlib, skill module imported lazily): `check_runner_copy` (version, `script_state`, bytes outside `// <config>`..`// </config>`; absent copy is a note, a problem only when `workflow.cross_ai_command` names it), `GUARD_TESTS`, `parse_verbose` (ok/FAIL/ERROR/skipped in both quote forms, docstring lines, class-level `setUpClass` skips), `check_no_write(root, run=None)`, `_run_guard_tests` (runner's `baseline_env` + `write_tripwire`, cwd = the checkout, own session, 600 s, `stop_process_group` on expiry), `main` with `--root`, `--template`, `--skip-no-write` and the exit-2 refusal for a foreign `--root`.
- `tests/test_check_dogfood.py`: `TestRunnerCopy` (4), `TestParseVerbose`, `TestNoWrite` (changed/added/removed file, FAIL/ERROR, child rc, timeout, missing id, tripwire calls, skip counts and warning, class-level skip, `--root` refusal with no guard child started), `TestGuardTestsExist` (AST check plus a bogus-id non-vacuity case).
- `TestDogfoodCopy` deleted. `test_this_repos_own_config_is_never_touched` replaced by `test_parent_project_config_is_never_touched` (child `parent/project` holds its own `.planning/`). The golden-plan apply hashes a temporary parent's config and runner. The matrix drops the live-path imports and `test_repo_config_untouched`, snapshots an empty temp `snap_root`, hashes `Path(core_root).resolve()` before and after (`core_sha_before`), and gains `TestCoreTreeHash` (pure, runs on 1.18.0).
- Hook `check-dogfood` after `unittest-wizard` (pre-push, `pass_filenames: false`, `always_run: true`, `verbose: true`); Makefile target is the thin delegate and is in `.PHONY` and `validate`. `tests/test_gate_scope.py`: `hook_block`, `hook_stage`, `dogfood_hook_errors`, `test_check_dogfood_hook_gates_push`, `test_validate_runs_check_dogfood`, two non-vacuity cases.

## `make check-dogfood` on this checkout (gsd-core 1.18.0, 2026-11-03)

```
check-dogfood: no-write guard skipped: tests.test_curated_config_apply_e2e.TestRealApply.test_apply_golden_plan: checkout-local gsd-core is 1.18.0; need one of 1.16., 1.17.
check-dogfood: no-write guard: 3 attempted, 2 executed, 1 skipped
check-dogfood: warning: the apply no-write guard did not run (checkout-local gsd-core is 1.18.0; need one of 1.16., 1.17.); apply writes to the live project are unguarded until it runs
check-dogfood: ok
```

The runner copy was already pristine (plan 28-02 re-rendered it); no re-render was needed. Hook run time about 0.4 s of the hook itself (verbose pre-commit line).

**Open gap (recorded, not hidden):** the `apply` write path to the live project is unguarded while the checkout-local gsd-core is outside `GSD_CORE_PREFIXES`; it closes when ROADMAP backlog 999.18 widens the prefixes with the table-parity check. To confirm the edited golden-plan and matrix code anyway, I ran them once with `GSD_CORE_PREFIXES` widened to include 1.18 through a scratch script under `tmp/` (not committed): `test_apply_golden_plan` passed (3.6 s) and the Claude matrix plus `TestCoreTreeHash` passed (9 tests, 70 s).

## Verification (all with `AI_KIT_REFUSE_REAL_HOME=1`, from the worktree root)

- `python3 tools/run_unittest_parallel.py tests.test_check_dogfood tests.test_curated_config_script tests.test_gate_scope`: exit 0 (20, 50, 38 tests).
- `uv run python tools/run_unittest_parallel.py tests.test_curated_config_e2e tests.test_curated_config_apply_e2e tests.test_ai_kit_gsd_curated_config_matrix`: exit 0 (8, 7, 2 tests; `test_parent_project_config_is_never_touched` ran, not skipped).
- `make check-dogfood`: exit 0, lines above.
- `make arch-test`: exit 0 (66). `tests.test_gsd_curated_eval` 316 ok, `tests.test_run_unittest_parallel` 45 ok, `tests.test_ai_kit_project_rules_precommit` 99, `tests.test_tool_substitution_hook` 73, `tests.test_ai_kit_project_rules_makefile` 72 ok. `uv run pyright` 0 errors, `uv run vulture` clean, ruff and pylint passed in the commit hooks.
- Acceptance greps: no `_REPO_CONFIG|_REPO_RUNNER|REPO_ROOT / ".planning"` or `snapshot(REPO_ROOT` left in the three modules; `core_sha_before` present; `tests/gsd_curated_eval.py` untouched (no `_tree_sha` change).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `tests/test_arch.py` rule 11 flagged `start_new_session=True` in `tools/check_dogfood.py`**
- **Found during:** Task 2 (arch run)
- **Issue:** the guard child must run in its own session (plan text); rule 11 allows that only for listed files.
- **Fix:** added `tools/check_dogfood.py` to `_START_NEW_SESSION_ALLOWED` with a comment (the 28-02 precedent for `tools/run_unittest_parallel.py`).
- **Commit:** 47e0e32

**2. [Rule 1 - Bug] `tests/test_gsd_curated_eval.py` pinned the matrix module's collected classes and test count (47)**
- **Found during:** Task 2 (`tests.test_gsd_curated_eval`)
- **Issue:** removing `test_repo_config_untouched` from five classes and adding `TestCoreTreeHash` changes the collection to 43 tests and one extra class; the plan did not list this file.
- **Fix:** list gains `TestCoreTreeHash`, count 43, and the test is renamed `test_matrix_module_collects_the_host_classes_and_the_hash_case_only` (the old "six host classes" name was no longer true).
- **Commit:** 47e0e32

**3. [Rule 3 - Blocking] pylint `import-error` / `wrong-import-position` on the skill import**
- **Fix:** `check_dogfood.py` imports the skill module lazily (`importlib.import_module` after inserting the skill folder into `sys.path`, `functools.cache`), the `cursor_quota.py` precedent. The first Task 1 commit attempt was rejected by the hook before this was fixed; no commit existed until it passed.
- **Commit:** 9c881d7

**4. [Rule 1 - Bug] first `parse_verbose` regex let one result swallow the next line**
- **Found during:** Task 2 unit run (11 failures). The optional docstring group consumed the rest of a line plus the next line. Fixed to allow the docstring form only as an explicit `\n<docstring> ... status` alternative; covered by `TestParseVerbose`.
- **Commit:** 47e0e32

### Environment note (not a code deviation)

The worktree had no `.claude/` (gitignored), so the real-gsd tests could not resolve gsd-core. I copied the main checkout's `.claude/gsd-core` and `.claude/scripts` (gsd-core requires `../../../scripts/fix-slash-commands.cjs`) into the worktree's ignored `.claude/` for verification; nothing under `.claude/` is tracked or committed. Without the `scripts` folder `ensure-project` returned `{"ensured": false}` and the three real-gsd tests failed; with it they pass.

Judgment calls: `check_runner_copy` reports an unparseable `config.json` as a problem only when the runner copy is absent (it cannot then judge whether the copy is required); a timed-out child is reported as `rc is None` rather than a magic exit code.

## Known Stubs

None.

## Threat Flags

None beyond the plan's register (T-28-08, T-28-09, T-28-23 mitigated as written: fixed argv, fixed ids pinned to existing methods, own session, 600 s limit, baseline env with tripwire first on PATH, output limited to relative paths, ids and short reasons).

## Self-Check: PASSED

- FOUND: tools/check_dogfood.py, tests/test_check_dogfood.py
- FOUND commits: 9c881d7, 47e0e32, 1f12c82 (ancestors of HEAD)
- `.planning/config.json`, STATE.md, ROADMAP.md untouched.
