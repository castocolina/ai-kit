---
phase: 42-code-review-after-execution-and-jev-picked-executors
plan: 08
subsystem: ai-kit-spec-review (herdr_pane, runner_dispatch)
tags: [transport, pane, herdr, sweep, runner-boundary]
requires: [42-07]
provides:
  - "herdr_pane.py: a client of the runner's hosted-lane protocol (open_pane, close_pane, pane_spawn, pid_alive, PaneSeams); run_round, read_verdict and PaneRound stay internal"
  - "close_pane proves ownership (run_dir_for path, lstat directory, run.json token, label and host, herdr tab list) before it retires the launcher group or closes a tab"
  - "a timed-out or gone round retires the verified launcher group (SIGTERM, then SIGKILL after KILL_GRACE_S) and marks the pane closed"
  - "runner_dispatch.RunnerSeams.spawn_fn (default None) and reap_recorded_groups; herdr_pane.pane_spawn(pane) is the spawn seam run_runner calls for a pane round"
  - "runner_dispatch.run_sweep and SWEEP_TIMEOUT_S: the runner's own --sweep, once"
  - "tests/test_arch.py check_pane_round_boundary with its non-vacuity test"
affects: [42-09]
key-files:
  created:
    - skills/ai-kit-spec-review/ai_kit_spec/herdr_pane.py
    - tests/test_herdr_pane.py
    - tests/test_herdr_pane_sweep_e2e.py
  modified:
    - skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py
    - tests/test_runner_preview.py
    - tests/test_ai_kit_spec_runner_dispatch.py
    - tests/test_arch.py
    - tools/run_unittest_parallel.py
    - Makefile
    - .pre-commit-config.yaml
decisions:
  - "Task 2 ran as two lanes (module changes with their tests, then the remaining edge tests and the protocol mirror) to stay inside the 1800 s lane limit; the second commit uses the test(42-08) type"
metrics:
  tasks: 4
  commits: 5
---

# Phase 42 Plan 08: herdr pane transport on the runner's protocol Summary

An owner-marked interactive lane can now run its headless runner command in one reused herdr pane. `herdr_pane.py`
writes the runner's own run record, launcher and round files (names, label and token grammar, modes and rc grammar
pinned to the runner's protocol fixture), so the runner's start-of-run sweep reads and closes a pane leftover; an e2e
test proves that with the real runner and a fake herdr binary. A pane round is one `runner_dispatch.run_runner` call
with `herdr_pane.pane_spawn(pane)` as its spawn seam, so argv, pgid file, deadline, env, stderr relay, trailer check
and reason stay run_runner's; an arch rule fails on any other module that names a pane round. A timed-out or gone round
retires the verified launcher group and marks the pane closed; close proves ownership before touching anything.
Nothing chooses a pane yet: the pane label stays unverified and the wiring is the next plan.

## Commits

- `db7bf4a` feat(42-08): herdr pane transport on the runner's hosted-lane protocol (Task 1)
- `cdd8b35` feat(42-08): retire pane launchers, prove ownership before close, keep the stderr tail (Task 2, first half)
- `06d2923` test(42-08): pin pane refusals, open failures, round edges and the protocol mirror (Task 2, second half)
- `999e051` feat(42-08): run the runner's own sweep once and prove it closes a pane leftover (Task 3)
- `32fe209` feat(42-08): run pane rounds behind the runner boundary (Task 4)

## Lane history

- Task 1: lane `42-08-fix-a` timed out at 1710 s inside its commit hook (files staged, pylint R1711 open); finish-up lane
  `42-08-fix-a2` removed the useless return and committed, ok, 530 s (hook attempt 1 failed on
  tests.test_cursor_status_line, two `OSError: [Errno 39] Directory not empty` in TemporaryDirectory cleanup under load;
  attempt 2 233/233 + 22/22 uv). Not in this plan's files; an open item.
- Task 2: split into `42-08-fix-b1` (ok, 827 s, hook 165/165 + 21/21 uv) and `42-08-fix-b2` (runner status `partial`
  700 s with `task_uncovered` and `outside_plan_files`: the fix-up prompt's `<files>` line carried a parenthetical, so
  the runner's comma-split file list held no clean path and the one changed file read as outside it; the commit exists
  and every check below passed; the lane's final reply was not captured, so its hook counts are not known).
- Task 3: `42-08-fix-c`, ok, 1198 s, hook 234/234 + 23/23 uv (full unit and arch: the listings were staged).
- Task 4: `42-08-fix-d`, ok, 900 s, hook 167/167 + 21/21 uv.
- Hooks deferred `tests.test_ai_kit_gsd_curated_config_matrix` (over the commit budget) and the new
  `tests.test_herdr_pane_sweep_e2e` (no recorded time) to push. I ran the sweep e2e under the guard at the clean HEAD
  `999e051` (1 test ok) and both at the clean plan HEAD `32fe209`: matrix 35 tests ok in 153.2 s, sweep 1 test ok,
  2/2 modules passed (guard peak 0, no kill).

## Checks (own runs)

- Acceptance greps of all four tasks met: Task 1's function set (13 defs at db7bf4a), `_retire` 1, `"tab list"` 2, no second pgid file, margin or
  trailer rule in herdr_pane.py; four test classes plus `TestPaneBoundary`, fixture and `write_herdr_fake` references;
  `run_sweep` 1, `"--sweep"` 1, `test_run_sweep_seams` 1, listing entry 1, `_write_record(` in the e2e 1; `spawn_fn`
  field 1, `(active.spawn_fn or _spawn_supervised)(` 1 (only inside `run_runner`; `run_custom` keeps its direct call),
  `herdr_pane` in runner_dispatch.py only in the seam comment, `pane_spawn` 1, no argv, `run_runner(` or trailer code in
  herdr_pane.py, three arch names 3. cross-ai.mjs and the protocol fixture are untouched.
- The sweep e2e takes node from `tests.cross_ai_selftest._real_node_executable`, never `shutil.which`. A verbose run
  under a scratch HOME shows no skips: `test_herdr_pane` 41 of 41 ok, `test_herdr_pane_sweep_e2e` 1 of 1 ok.
- Hook counts in the lane history are the lanes' own reports.
- The plan's verification command (eight modules: herdr_pane, lane_transport, lane_settings, runner_preview,
  runner_dispatch, runner_host_protocol, gate_scope, arch) printed `8/8 modules passed` at `46a4595`.
- Modules: `test_herdr_pane` (41 tests), `test_ai_kit_spec_runner_dispatch` (81), `test_runner_preview` (20),
  `test_arch` (120), `test_lane_transport` (20), `test_arch_hardcoded_models` (23), `test_gate_scope` (62): all ok.
- Gates at `32fe209`: unit+arch `211/211 modules passed` (guard peak 7, no kill); `make ruff`, `make pyright`,
  `make vulture`, `make pylint`, `make check-dogfood` exit 0.
- Diff review against the plan: run.json is read with `O_NOFOLLOW`, a regular-file check and the runner's 64 KiB cap;
  only a verified group leader that is not this process's group, with a matching start time, is signalled; an rc counts
  only after the launcher consumed `round.sh`; `read_verdict` keeps the raw last trailer and the stderr tail, and
  run_runner applies the one trailer rule; pane_spawn reaps run_runner's pgid file on every exit path.
- Scope from the plan base `b887f30`: exactly the ten `files_modified` paths. Added shipped lines carry no phase,
  decision or requirement id, date or `.planning` path; `tests/fixtures/no_hardcoded_models_baseline.json` unchanged. No
  SKILL.md changed.

## Deviations

- Task 2 split into two lanes and two commits (see decisions); the plan named one commit.
- `_retire` checks `isinstance(pgid, int)` beside `pgid != pid` (pyright narrowing; same behaviour); `_owned_record`
  merges the token and path checks into one guard (max-returns 6).
- Test details: subtests remove the run dir before each new open (open_pane refuses an existing run dir); the sweep e2e
  passes `stdin=DEVNULL` and also asserts the runner's sweep counts line; `test_run_sweep_seams` imports
  `_NO_NODE_LINE` and `_NO_TEMPLATE_LINE`.
- Task 4: the shared fake setup is `_PaneFakeHarness(unittest.TestCase)` with no test methods (pyright rejects
  TestCase methods on a plain mixin; the repo's `_ChildTracker` uses the same shape); `TestPaneBoundary` declares
  `pgid_file` as a class attribute for pyright.
