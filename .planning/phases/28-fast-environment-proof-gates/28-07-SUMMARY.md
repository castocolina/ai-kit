---
phase: 28-fast-environment-proof-gates
plan: 07
subsystem: testing
tags: [staged-tests, pre-commit, pre-push, commit-budget, name-index, mapper, runner, gate-scope]
requires: ["28-05", "28-06"]
provides:
  - "COMMIT_E2E_BUDGET_SECS = 60 and E2E_RECORDED_SECS (one whole-second entry per e2e module, measured on the frozen tree): an e2e module over the budget or unrecorded is deferred at commit"
  - "runner --pushed mode and the pre-push deferred-e2e hook: runs the deferred covering e2e modules, narrowed to the pushed range only with the proof"
  - "staged_mapper: pushed_paths, outside_commits, commit_sha, --stats (unit_stats), path-decision CLI"
  - "tests/test_gate_scope.py pins: staged_hook_errors, deferred_hook_errors, shared_machinery_errors, recorded_secs_errors"
affects: [28-09]
tech-stack:
  added: []
  patterns: ["commit budget from a committed duration table, not run reports", "pushed-range narrowing only with a provable no-outside-commit proof, else every over-budget module", "per-unit tightened token forms only where a unit over-selects"]
key-files:
  created: []
  modified:
    - tools/run_unittest_parallel.py
    - tools/staged_mapper.py
    - tests/test_staged_mapper.py
    - tests/test_staged_commit_e2e.py
    - tests/test_gate_scope.py
    - tests/test_arch.py
    - .pre-commit-config.yaml
key-decisions:
  - "Decision carries the covering modules even on a full run; index_built False marks shared machinery with no index, so the runner falls back to every e2e module"
  - "The commit budget is 60 s (SPEC R3's push target); the recorded table is this machine's and not scaled by CPU count; the 2026-11-04 frozen-tree run puts only tests.test_cross_ai_runner_e2e (366 s) over it"
  - "--pushed narrows to the pre-commit range only when the checkout is the pushed commit and no commit held by a local branch or worktree HEAD lies outside it; local tags and the stash are left out (817 commits with tags counted, 0 without, on this checkout)"
  - "The spec-review skill folder is the one unit whose bare name over-selected (40 of 79 unit and arch modules, over half); only its path forms select it now (39 modules). Other folders keep the bare token: tightening all of them dropped real reads (the wizard symlink test, the jev skill install e2e)"
  - "A private helper attribute (`setup._name()`) selects its tool module; this closed the only uncovered unit found (tools/command_ownership.py)"
requirements-completed: [GATE-01]
status: complete
duration: ~4h (estimate; no start timestamp was recorded)
completed: 2026-11-04
commits: 6
plan_head_before: 4781bd67dd73ddbb4770e12e076901b15041cf60
plan_head_after: 8a156196c19b99f231bad1a9acbd10ee9c043eda
actuals:
  tokens: 66700   # chars/4 over the seven changed files at HEAD (266810 chars)
  tasks: 4
  commits: 6
---

# Phase 28 Plan 07: Commit budget, pushed-range proof and measured selectivity Summary

Covering e2e modules over a 60 s commit budget no longer hold up a commit. They run at push, from a pre-push hook that narrows to the pushed range only when a proof holds and otherwise runs every over-budget module. The durations behind the budget were measured on a frozen tree, and the mapper's selectivity was measured and tightened for the one unit the decision rule flagged.

## What was built

- **Commit budget (Task 1).** `COMMIT_E2E_BUDGET_SECS = 60`, `E2E_RECORDED_SECS`, `split_e2e`, `_deferral_line`, `_run_under_uv(modules, cwd, prefix)` and `_uv_missing`. Full runs and mapper errors split their e2e modules by the same budget. The deferral notice has the plan's exact format.
- **Pushed mode (Task 2).** `--pushed` in the runner: `_range_problem`, `_proof_refusal`, `_range_deferred`, `_fallback`, `_pushed_modules`, `_pushed_main`. The `deferred-e2e` pre-push hook after `check-dogfood`. Mapper: `commit_sha`, `pushed_paths` (`git diff --name-only -z --no-renames a...b`), `outside_commits` (`git rev-list --exclude=refs/stash --exclude=refs/tags/* --all --not --remotes <to>`), all argv lists, a ref starting with `-` refused before git runs.
- **Mapper stats and CLI (Task 3).** `staged_mapper --stats` (`unit_stats`, `units`, `tracked_paths`), positional paths for decisions without a test run, `main(argv)`. The mapper loads the runner's `E2E_MODULES` and `SHARED_MACHINERY` by file path, so it never imports the runner by name.
- **Gate-scope pins (Task 4).** `staged_hook_errors`, `deferred_hook_errors`, `shared_machinery_errors` (`REQUIRED_SHARED_MACHINERY`, the seven D-03 entries), `recorded_secs_errors`, with a non-vacuity case for each failing behaviour line. Runner docstring updated for `--staged`, `--pushed`, the budget and the mapper.

## Commits

| # | Hash | Subject | Hook `- duration:` |
|---|------|---------|--------------------|
| 1 | 1fa255e | feat(28-07): defer over-budget covering e2e modules from the commit stage | 67.29 s |
| 2 | b4f3e52 | feat(28-07): run deferred e2e modules at push, narrowed only with the proof | 64.53 s |
| 3 | b719620 | test(28-07): pin runner staged cases to a fixed e2e table | 8.39 s |
| 4 | e2f8f75 | chore(28-07): record frozen-tree e2e durations for the commit budget | 70.77 s |
| 5 | aea3db0 | feat(28-07): mapper --stats and path decisions; tighten the spec-review skill's forms | 67.03 s |
| 6 | 8a15619 | test(28-07): pin the commit and push hooks, the shared machinery and the budget table | 69.88 s |

Commit 4 is the table-only commit (Task 2 step 6). Commit 3 is a test-only pin that the table change required (see deviations).

## Task status and verify exit codes

| Task | Status | Verify |
|------|--------|--------|
| 1 Commit budget | done, `1fa255e` | `tests.test_staged_mapper tests.test_run_unittest_parallel tests.test_gate_scope`: 0; `uv run python tools/run_unittest_parallel.py tests.test_staged_commit_e2e`: 0 (9 tests, no skip) |
| 2 Pushed mode and frozen-tree measurement, `b4f3e52` then `e2f8f75` | done | unit modules: 0; `tests.test_staged_commit_e2e` under uv: 0 (13 tests, no skip); `python3 tmp/p28/proof_count.py`: 0 |
| 3 Mapper selectivity and commit-stage times, `aea3db0` | done | `tests.test_staged_mapper`: 0; `python3 tools/staged_mapper.py --stats`: 0; `bash tmp/p28/commit_stage_time.sh`: 0 |
| 4 Gate-scope pins and docstring, `8a15619` | done | `tests.test_gate_scope tests.test_run_unittest_parallel`: 0 (55 and 45 tests) |

## Task 1: commit-stage evidence

Commit `1fa255e` ran the hook with the new budget. The hook's own deferral lines (as printed):

```
staged: full unit+arch run: shared test machinery: tools/run_unittest_parallel.py
staged: deferred to push (over the 60 s commit budget): tests.test_cross_ai_runner_e2e (recorded 361 s); run now: uv run python tools/run_unittest_parallel.py tests.test_cross_ai_runner_e2e
staged: deferred to push (over the 60 s commit budget): tests.test_staged_commit_e2e (no recorded time); run now: uv run python tools/run_unittest_parallel.py tests.test_staged_commit_e2e
```

`- duration: 67.29s`, `79/79 modules passed`. Commit `8a15619` shows the same deferral for `tests.test_cross_ai_runner_e2e` with the table's 366 s.

## Task 2: proof and frozen-tree measurement

Proof on this checkout (`python3 tmp/p28/proof_count.py`, run after commit `b4f3e52`, exit 0):

```
proof: 0 unpushed commits outside HEAD (local tags left out); 817 with local tags counted
proof: fast path holds on this checkout now
```

Both counts match the planning-time probe (0 and 817). The fast path holds on this checkout now.

Frozen-tree measurement (step 6). `wait_load.py` printed `load: 2.06 below 4 after 0 s` for a first attempt and `load: 1.80 below 4 after 0 s` for the run whose output is recorded. The one-minute load at the start of the recorded run was 1.80 on 24 CPUs. No tracked file changed during the run: `git status --short` was empty before it started, and no edit was made until it exited. The gitignored `.claude/scripts` folder was copied in before this run (see deviations). Raw `=== <module>: ok in <s>` lines from `tmp/p28/e2e_times.txt`:

```
=== tests.test_ai_kit_gsd_spec_discuss_e2e: ok in 0.1s  Ran 1 test in 0.056s
=== tests.test_ai_kit_gsd_curated_config_matrix: ok in 0.2s  Ran 2 tests in 0.082s
=== tests.test_curated_config_apply_e2e: ok in 0.2s  Ran 7 tests in 0.110s
=== tests.test_jev_skill_install_e2e: ok in 0.6s  Ran 9 tests in 0.549s
=== tests.test_ai_kit_spec_e2e: ok in 0.9s  Ran 2 tests in 0.866s
=== tests.test_ai_kit_spec_goal_prompt_e2e: ok in 1.0s  Ran 5 tests in 0.899s
=== tests.test_worktree_e2e: ok in 0.2s  Ran 4 tests in 0.137s
=== tests.test_markdown_to_pdf_e2e: ok in 1.1s  Ran 1 test in 1.072s
=== tests.test_system_memory_e2e: ok in 0.6s  Ran 4 tests in 0.594s
=== tests.test_hook_registry_e2e: ok in 1.8s  Ran 16 tests in 1.774s
=== tests.test_staged_commit_e2e: ok in 3.4s  Ran 13 tests in 3.320s
=== tests.test_curated_config_e2e: ok in 5.3s  Ran 8 tests in 5.189s
=== tests.test_ai_kit_project_rules_all_e2e: ok in 25.6s  Ran 5 tests in 25.552s
=== tests.test_precompact_shims_e2e: ok in 57.3s  Ran 23 tests in 57.191s
=== tests.test_cross_ai_runner_e2e: ok in 365.9s  Ran 24 tests in 365.816s
15/15 modules passed
```

Rounded up into `E2E_RECORDED_SECS`: 1, 1, 26, 1, 1, 366, 1, 6, 2, 1, 2, 58, 4, 1, 1 (in table order). Modules over the 60 s budget: `tests.test_cross_ai_runner_e2e` only. `tests.test_precompact_shims_e2e` (58 s) is within it. The first attempt (`tmp/p28/e2e_times_run1.txt`, not in the repo) had 3 failures from the missing `.claude/scripts`; the second run is the measurement.

## Task 3: mapper selectivity

`python3 tools/staged_mapper.py --stats`, before the spec-review tightening (commit `aea3db0`'s parent state, measured in this run):

```
mapper: 64 units; covering modules per unit: median 3 (all units), median 3 (covered units), max 40 (skills/ai-kit-spec-review); 18 covering sets hold an e2e module
mapper: uncovered unit tools/command_ownership.py
mapper: data file Makefile: 25 modules
mapper: data file README.md: 25 modules
mapper: data file AGENTS.md: 16 modules
mapper: data file .pre-commit-config.yaml: 12 modules
mapper: data file pyproject.toml: 11 modules
```

After the tightening (committed state, `aea3db0`), exit 0:

```
mapper: 64 units; covering modules per unit: median 3 (all units), median 3 (covered units), max 39 (skills/ai-kit-spec-review); 18 covering sets hold an e2e module
mapper: data file Makefile: 25 modules
mapper: data file README.md: 25 modules
mapper: data file AGENTS.md: 16 modules
mapper: data file .pre-commit-config.yaml: 12 modules
mapper: data file pyproject.toml: 11 modules
```

Unit and arch modules: 79 (the full-run count the hook prints). Medians: 3 over all units, 3 over covered units. The rough 3.5 and 37 from the spec step are not reproduced; the measured 3 and 40 (before tightening) are the real numbers.

**Uncovered units and their decisions.**
- `tools/command_ownership.py`: test_setup reaches it through `setup._command_ownership()`, which the mapper did not match (a leading underscore before the stem). The dotted form now allows `._<stem>`, and a test covers it. No uncovered unit remains.

**Data files and the read-or-not note.** Read-looking counts are a heuristic (`read_text`, `open`, `read_bytes`, or the file name in a path read): Makefile 23 of 25 covering modules, README.md 22 of 25, AGENTS.md 13 of 16, `.pre-commit-config.yaml` 12 of 12, pyproject.toml 11 of 11. The covering modules that the heuristic does not mark as readers were not checked one by one; they name the file (fail-safe over-selection if they only mention it). None selects more than half of the 79 modules (the largest is 25), so none triggers the rule.

**Decision rule outcome.** Fired, then resolved. The all-units median is 3, which is not above 10. But `skills/ai-kit-spec-review` selected 40 of the 79 unit and arch modules, over half. Its over-selecting forms were the bare quoted name in value positions (for example `"candidate_skills": ["ai-kit-spec-review"]` and the session-wake name lists). Task 3 tightened that unit only: a path string `skills/<name>`, a path join `"skills", "<name>"` or `"skills" / "<name>"`, or `<name>/file` selects it. Re-measured: 39 modules (49 %). The one module dropped is `tests.test_ai_kit_spec_goal_prompt_strategies`, which names the skill only as a candidate-name fixture and does not read it.

**Commit-stage times** (`tmp/p28/commit_stage_time.sh`, exit 0; measurements on this machine, 24 CPUs; the one-minute load was not recorded for this script run; the 2 x 60 s check applies to the three selective sets only):

| Set | Wall time | Modules | e2e run under uv | e2e deferred | Check |
|-----|-----------|---------|------------------|--------------|-------|
| `skills/ai-kit-spec-review/references/cross-ai.mjs` | 61.6 s | 39 | 5 (`ai_kit_gsd_curated_config_matrix`, `ai_kit_spec_e2e`, `ai_kit_spec_goal_prompt_e2e`, `curated_config_apply_e2e`, `curated_config_e2e`) | `tests.test_cross_ai_runner_e2e` (366 s) | exit 0; deferral named; not run; within 2 x 60 s |
| `tools/hooks/detect.py` | 65.2 s | 15 | 2 (`ai_kit_spec_goal_prompt_e2e`, `precompact_shims_e2e`) | none | exit 0; within 2 x 60 s; `precompact_shims_e2e` selected |
| `skills/markdown-to-pdf/scripts/render_mermaid.py` | 23.8 s | 5 | 2 (`wizard_pty`, `markdown_to_pdf_e2e`) | none | exit 0; within 2 x 60 s |
| mapper-error worst case (no bound) | 120.4 s | 93 (79 unit and arch + 14 e2e within budget) | 14 | `tests.test_cross_ai_runner_e2e` | exit 0; `93/93 modules passed` |

The shared-machinery commit (a `tools/staged_mapper.py` change, full unit and arch run plus the within-budget covering e2e modules) took `- duration: 67.03s` for `aea3db0`. The other shared-machinery commits took 70.77 s (`e2f8f75`) and 69.88 s (`8a15619`). Commit `e2f8f75`'s hook ran `tests.test_staged_commit_e2e` under uv (within budget after the table, 3.2 s). These are measurements on this machine, not bounds.

## Task 4: gate-scope pins

`tests.test_gate_scope` runs 55 tests: `staged_hook_errors`, `deferred_hook_errors`, `shared_machinery_errors`, `recorded_secs_errors` with their real-config tests (`test_staged_hook_is_commit_stage`, `test_deferred_hook_is_push_stage`, `test_shared_machinery_is_pinned`, `test_commit_budget_is_pinned`), the extended `test_hook_order_and_serial_runs` (pylint < staged-tests < unittest), the mapper added to the worker-count scan, and non-vacuity cases for each failing behaviour line, including the omitted-stage ones. `test_core_hook_precedes_wizard_hook` and `test_hooks_cover_every_group_except_e2e` still pass.

Lint and types on the touched tool files: `ruff` clean, `pylint` 10.00, `pyright` 0 errors, `vulture` clean.

## Deviations from Plan

**1. [Rule 3 - Blocking, environment] Worktree missing the gitignored `.claude/scripts`.** The setup copied only `.claude/gsd-core`. The real gsd-core requires `.claude/scripts/fix-slash-commands.cjs` through `command-roster.cjs`. The first e2e run had 3 failures in `tests.test_ai_kit_spec_e2e`, `tests.test_curated_config_e2e` and `tests.test_cross_ai_runner_e2e` for that reason. I copied `.claude/scripts` from the main checkout (gitignored, never staged) and re-ran the whole group on the frozen tree; all 15 passed. Orchestrator note: worktree setup should copy `.claude/scripts` too. The first run's output is kept at `tmp/p28/e2e_times_run1.txt`.

**2. [Rule 3 - Blocking] A test pin commit before the table commit (`b719620`).** The runner-level `--staged` cases read the measured table, so they moved when it was refreshed. They now patch a fixed table with the two values they were written against. The table commit is `e2f8f75`.

**3. [Rule 2 - Missing critical] `tests/test_arch.py` broad-except allowlist (Task 2).** `_pushed_modules` has a broad except, which rule 9 rejects unless listed. Any proof or mapper failure must run every over-budget module, so the catch-all is the fail-safe. Added to the explicit allowlist with a comment (the 28-06 precedent). Not in the plan's file list.

**4. [Rule 1 - Bug] Private helper form (Task 3).** The mapper's dotted form did not match `setup._name()`, which left `tools/command_ownership.py` uncovered. The form now allows one leading underscore; a test pins it.

**5. [Plan deviation] Tightening scope (Task 3).** The first tightening applied the path-only forms to every skill folder. The probe showed it dropped real dependencies: `tests.test_wizard_pty` (asserts the fixer's symlink on install), `tests.test_jev_skill_install_e2e`, and cross-AI tests that read skills through install lists. Reverted; the tightening now applies only to `TIGHT_SKILL_FOLDERS = {"ai-kit-spec-review"}`, the unit the decision rule flagged, as the plan states. Known limit: a test that reads a tight skill through a variable holding only the bare name is not selected; the push stage's full suites cover it (a `shortcut:` line is in the mapper).

**6. [Plan deviation] Runner's last commit.** The Task 2 acceptance says `git log -1 -- tools/run_unittest_parallel.py` is the table-only commit. After it, Task 4 changed the runner's docstring only (`8a15619`), so the last commit touching the runner is `8a15619`. The table commit is `e2f8f75`. No behaviour of the runner changed after the measurement.

**7. [Plan deviation] Measurement and later changes.** Tasks 3 and 4 changed `tools/staged_mapper.py` and tests after the frozen run. `tests.test_staged_commit_e2e` (the only e2e module that runs the mapper) ran under uv inside the Task 3 and Task 4 commit hooks and passed (3.0 s and 3.2 s). The other e2e modules are unchanged in their inputs. The full e2e group was not re-run.

**8. [Time-box].** Planned for about 60 minutes; the run took several hours, mostly the e2e group (about 7 minutes per run, 366 s for `tests.test_cross_ai_runner_e2e` alone) and the commit hooks (64 to 70 s each).

## Verification (Task 1 to 4 acceptance, grep and command results)

- `rg -c 'COMMIT_E2E_BUDGET_SECS = 60' tools/run_unittest_parallel.py`: 1
- `rg -c 'def split_e2e|def _run_under_uv' tools/run_unittest_parallel.py`: 2
- `rg -c 'id: deferred-e2e' .pre-commit-config.yaml`: 1; the block is after `check-dogfood` and holds `stages: [pre-push]`
- `rg -c 'def outside_commits|def pushed_paths' tools/staged_mapper.py`: 2
- `rg -c -F -e '--exclude=refs/tags/*' tools/staged_mapper.py`: 1
- `rg -c 'shortcut: local tags are left out' tools/run_unittest_parallel.py`: 1
- `python3 tools/run_unittest_parallel.py --pushed --group unit`: exit 2
- `python3 tools/staged_mapper.py tools/hooks/detect.py`: exit 0, `modules:` line includes `tests.test_tool_substitution_hook`
- `python3 tools/staged_mapper.py tools/common_render.py`: exit 0, `modules:` line includes `tests.test_cursor_status_line`
- `E2E_RECORDED_SECS` keys equal `E2E_MODULES` (15 of 15), checked with the runner loaded by path

## Known Stubs

None.

## Threat Flags

None. The new subprocess calls use argv lists only, and refs starting with `-` are refused before git runs (T-28-26).

## Self-Check: FAILED

Acceptance criteria checked with the commands above. One item does not hold as written:

- Task 2 acceptance: `git log -1 --format=%s -- tools/run_unittest_parallel.py` is the table-only commit. It is `8a15619` (Task 4 docstring). The table-only commit is `e2f8f75`. The later change is docstring only (deviation 6).

All other acceptance criteria hold: Task 1 and Task 2 unit and e2e tests pass (including cases (i)-(n) and `TestDeferredPush`), the two `proof:` lines and the frozen-tree raw lines are recorded, the Task 3 stats and path decisions and the three selective commit-stage checks pass, and every Task 4 pin and its non-vacuity case passes. No STATE.md, ROADMAP.md or `.planning/config.json` change was made, and `.claude/` and `tmp/` are not committed.
