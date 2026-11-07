---
phase: 28-fast-environment-proof-gates
plan: 02
subsystem: testing
tags: [cross-ai-runner, self-test, load-factor, process-groups, test-runner, stress]
requires: ["28-01", "28-03"]
provides:
  - "runner self-test ceilings scale with one load factor per run (1..4); floors and the 13 real limits stay fixed and are pinned"
  - "tools/run_unittest_parallel.py: per-module deadline, graceful process-group stop, interrupt-safe pool"
  - "all four test tiers green under the tripwire and the baseline env"
affects: [28-04, 28-06, 28-07, 28-09]
tech-stack:
  added: []
  patterns: ["one load reading shared by Python hang guard and Node ceilings via AIKIT_XAI_SELFTEST_LOAD", "SIGTERM-first group stop with forwarded SIGTERM to nested sessions", "file lock on setup.py around the uv cold start"]
key-files:
  created: []
  modified:
    - skills/ai-kit-spec-review/references/cross-ai.mjs
    - .planning/scripts/cross-ai.mjs
    - tools/run_unittest_parallel.py
    - tests/test_cross_ai_runner_e2e.py
    - tests/test_cross_ai_skill_text.py
    - tests/test_run_unittest_parallel.py
    - tests/test_arch.py
    - tests/test_wizard_pty.py
    - tests/test_config_doctor_pty.py
key-decisions:
  - "The Python hang guard and the Node ceilings share one reading (AIKIT_XAI_SELFTEST_LOAD); no margin, the printed factor is asserted equal"
  - "Interrupt path stops groups from the main thread without touching the workers' pipes; the deadline path reaps with closed pipes (bounded)"
  - "A uv cold start is serialized with flock on tools/setup.py rather than adding a sequential path to the runner"
status: complete
commits: 5
plan_head_before: 834ebfacf19d0e22e6b0f8e4d71f34457cc02dd2
plan_head_after: 025af74b50d0df9e14246977f6ef786884749d01
actuals:
  tokens: 14600
  tasks: 4
  commits: 5
requirements-completed: [GATE-04]
---

# Phase 28 Plan 02: Self-test load scaling, runner deadline and four-tier convergence Summary

The runner self-test now scales every time ceiling by one measured load factor (load per CPU, clamped 1..4) while floors and the 13 real run limits stay byte-identical; the test runner gives that module a 5400 s deadline, stops module process groups gracefully, and all four tiers pass.

## Commits

- `3f2d3ed` feat(28-02): per-case hard limit scaled by one load factor per run; injected readings (Task 1, tracer)
- `b0e03e9` feat(28-02): every other ceiling scaled; floors and real limits pinned; dogfood copy re-rendered (Task 2)
- `53ba2a1` feat(28-02): per-module deadline, graceful group stop, interrupt-safe pool (Task 3, committed before any long run)
- `50366f7` fix(28-02): early re-entry case accepts the remaining wait as a load-scaled range (Task 4 fix)
- `025af74` fix(28-02): serialize the cold start of setup.py's uv environment across the PTY modules (Task 4 fix)

## What changed

- `cross-ai.mjs` template (self-test harness only): `loadFactor`, `measuredLoadPerCpu`, `scaledMs`, `selfTestLoadFactor`, `SELF_TEST_SIGNAL_EXIT_MS = 2900`, pure case `load-factor-math`, stderr line `self-test load factor <f>`. Scaled: the per-case hard limit, both harness waits, the post-exit wait, `pidLingers`, the signal-to-exit ceiling, and all 16 elapsed ceilings (14 `elapsedMs >= N`, `elapsed >= 1000`, `elapsed >= 600`). The three 2500 ms floors are untouched. The template version is not bumped; `.planning/scripts/cross-ai.mjs` was re-rendered through `ensure-runner` (second run: `keep-pristine`; only `cross-ai.mjs` changed, no stray file).
- `tests/test_cross_ai_skill_text.py`: `SelfTestCeilingPins` (zero unscaled ceilings in `>` and `>=` form, three bare floors, zero `withinMs` literals, scaled waits, `REAL_LIMITS` with exactly 13 names, `budgetMs` byte for byte, `"outerTimeoutS": 1800`, non-vacuity case).
- `tests/test_cross_ai_runner_e2e.py`: `SelfTestLoadFactorTest` (7 injected readings plus the unset case), `GuardFactorTest` (uses the runner's `available_cpus()`; no `process_cpu_count` call), one shared reading for both full-run hang guards, `stop_group`, `_LIVE_GROUPS`, SIGTERM forwarding in `setUpModule`, `DeadlineCouplingTest.test_runner_deadline_covers_scaled_guards`, `StopGroupTest` (live `hang` case: no process left in the case runner's session, temp root removed, a sentinel outside it kept).
- `tools/run_unittest_parallel.py`: `SELF_TEST_MODULE_TIMEOUT_SECS = 5400`, `MODULE_TIMEOUT_OVERRIDES`, `module_timeout_secs` (global read at call time), `MODULE_STOP_GRACE_SECS = 15`, public `stop_process_group(proc, grace=None)`, a lock-guarded live registry with a stop flag, `install_signal_handlers`, `_run_all(modules, cwd)` and `main(argv, cwd)` with interrupt cleanup inside the pool block, exit 130, and the `not started: the run was interrupted` result line.
- `tests/test_run_unittest_parallel.py`: `ModuleDeadlineTest` (override and call-time global, grandchild, SIGTERM-ignoring module, nested sessions, queued-work interrupt with SIGINT and with SIGTERM).
- `tests/test_arch.py`: rule 11 allowlist gained `tools/run_unittest_parallel.py` (the runner starts module sessions; it supervises tests, not a cross-AI run).
- `tests/test_wizard_pty.py`, `tests/test_config_doctor_pty.py`: `warm_setup_env()` in `setUpModule` (see Deviations).

## Verification (exact commands, exit codes; all with `AI_KIT_REFUSE_REAL_HOME=1`, from the worktree root)

- Task 1: `uv run python tools/run_unittest_parallel.py tests.test_cross_ai_runner_e2e.SelfTestLoadFactorTest` exit 0, 2 tests.
- Task 2: `python3 tools/run_unittest_parallel.py tests.test_cross_ai_skill_text tests.test_curated_config_script` exit 0 (29 and 51 tests at that point); `uv run python tools/run_unittest_parallel.py tests.test_cross_ai_runner_e2e` exit 0, 22 tests in 351 s.
- Task 3: `python3 tools/run_unittest_parallel.py tests.test_run_unittest_parallel tests.test_arch` exit 0 (45 and 66 tests); `uv run ... tests.test_cross_ai_runner_e2e` exit 0, 24 tests in 352 s; `StopGroupTest` run verbose: `ok`, not skipped (0.2 s). `ruff`, `pylint` (10.00/10), `pyright` (0 errors), `vulture` clean on the touched files.
- Acceptance greps: no `elapsed\w*\s*>=?\s*[0-9]` match left (baseline 16); `elapsedMs < 2500` 3; `withinMs: 2900` 0; `process_cpu_count` absent from the e2e module.

### Stress run (Task 4 step 2): `bash tmp/p28/stress_selftest.sh`

stress-ng with 48 workers on 24 CPUs (2 per CPU), 120 s ramp, then `node cross-ai.mjs --self-test` in a hermetic env.

- Run 1: exit 126, no self-test ran (script defect: `node` here is a Volta shim that needs HOME; fixed by linking `process.execPath`, as `runner_env` does). Not counted.
- Run 2 (before the fix below): load before the self-test `42.75 25.12 13.15` (one-minute load per CPU 1.78), `self-test load factor 1.78125`, FAIL `router-quota-early-reentry` (`retry_after_s=599`), exit 1.
- Run 3 (after the fix): load before `42.24 33.31 25.73`, `self-test load factor 1.76`, `self-test ok`, **exit 0**; load after `51.29 46.65 34.93`.
- Cleanup: stress-ng pid and pgid recorded in `tmp/p28/stress_pids.txt` (`1565154 pgid=1565141` for the last run). The EXIT trap killed the workers every time; `pgrep -x stress-ng` printed nothing (rc 1) after each run and again at the end.

### wait_load lines

1. Before run 1: `load: 2.24 below 4 after 0 s`
2. Before run 2: `load: 3.04 below 4 after 150 s`
3. Before run 3: `load: 3.95 below 4 after 90 s`
4. Before the first tier pass: `load: 3.15 below 4 after 180 s`
5. Before the final tier pass: `load: 0.58 below 4 after 0 s`

The bound (600 s) was never reached; no tier ran at a load above 4 at its start.

### Four tiers

First pass (after the stress run): test-unit exit 0, arch-test exit 0, test-integration **exit 2**, e2e-test exit 0. Failure: `tests.test_config_doctor_pty` (uv cold-start race, below). A plain re-run passed, then the race was reproduced and fixed (2 commits before the final pass).

Final pass after every commit (`bash tmp/p28/tiers.sh c`; logs `tmp/p28/tier_*_c.log`):

- `make test-unit`: exit 0, 76/76 modules passed (unit) and 1/1 (unit-uv)
- `make arch-test`: exit 0, 1/1
- `make test-integration`: exit 0, 4/4
- `make e2e-test`: exit 0, 14/14 (includes `tests.test_cross_ai_runner_e2e` 24 tests in 355 s; `tests/test_install.sh` printed no FAIL)
- `tripwire:` blocks in any of the four logs: 0.

## Failure triage (Task 4 step 3)

- `tests.test_ai_kit_spec_goal_prompt_e2e`: already fixed in `efb8b57`, cause class host call; not re-fixed here (passes, 4 tests).
- `router-quota-early-reentry` (a self-test case in `cross-ai.mjs`, not a module): cause class **timing under load** (none of host call, host presence or baseline env). The re-entry reports what is left of the 600 s wait, so it is `599` once the gap between the two runs passes half a second; at factor 1.78 it did. Fixed in the case check (`50366f7`): accept `600 - ceil(scaledMs(10000)/1000) <= left <= 600`; a text pin in `SelfTestCeilingPins` keeps the exact-600 comparison out of that case. The same latent flake existed at factor 1.
- `tests.test_config_doctor_pty` (+ `tests.test_wizard_pty`): cause class **concurrency in the shared uv cache**. Both modules cold-start `uv run --script tools/setup.py` at once; uv failed with "failed to remove directory ... Directory not empty". The first run after a new checkout path hits it. Reproduced with a scratch `UV_CACHE_DIR` (`tmp/p28/pty_cold.sh`): 1 failure in 3 cold runs before, 0 in 6 after. Fix (`025af74`): `warm_setup_env()` in `setUpModule` of both modules, serialized by `flock` on `tools/setup.py`. `test_every_pty_env_isolates_host_roots` still passes (the warm-up env carries the host-root overrides).
- No module needed a host-call, host-presence or baseline-env fix in this plan.

## Deviations from Plan

**1. [Rule 1 - Bug] Latent timing flake in `router-quota-early-reentry`.** Found by the stress run (see triage). Commit `50366f7`.

**2. [Rule 1 - Bug] uv cold-start race between the two PTY modules.** Found by the first integration pass (see triage). Commit `025af74`. Files beyond the frontmatter list of the plan: `tests/test_wizard_pty.py`, `tests/test_config_doctor_pty.py`.

**3. [Rule 3 - Blocking] Arch rule 11 rejected `start_new_session=True` in the runner.** Added `tools/run_unittest_parallel.py` to `_START_NEW_SESSION_ALLOWED` with a comment (`tests/test_arch.py`, in `53ba2a1`).

**4. [Rule 3 - Blocking] Stress script used the Volta `node` shim.** Fixed in the gitignored script (links `process.execPath`).

**5. Minor, within the plan's intent.** The usage-comment acceptance count for `AIKIT_XAI_SELFTEST_LOAD` is 2 lines, not 3 (the env var name appears once on the read line, once in the usage comment); `main` and `_run_all` gained a `cwd` parameter (the plan asked for `_run_all`) so the SIGINT/SIGTERM tests exercise the real `main` path; `install_signal_handlers()` also sets SIGINT explicitly because a runner started from a background job inherits it ignored.

## Worktree-only skips (re-checked by the orchestrator's post-merge `make test` in the main checkout)

This worktree has no checkout-local `.claude/gsd-core`, so tests that run the real `gsd-tools.cjs` skip with a named reason (no failure, no code change, no link into the main checkout). Seen skipped (29 skips across the seven modules I ran verbose): `tests.test_ai_kit_project_rules_all_e2e` (TestAgentsProbe, TestTracer), `tests.test_ai_kit_gsd_curated_config_matrix`, `tests.test_curated_config_apply_e2e` (TestRealApply), `tests.test_curated_config_e2e` (TestGoldenTables, TestRealGsdLanes, TestRealGsdInventory, TestMergeModeEndToEnd, catalog test), and the `TestGsdHookE2E` class in `tests.test_cross_ai_runner_e2e`. One matrix class also skips for "no cached pi package". The tier exit codes above count these as passed; a pass is claimed only for what ran.

## Known limits

- `stop_process_group` does not guard a pid reused between the leader's exit and the SIGKILL; documented as a `shortcut:` in the docstring.
- On interrupt, a stray in a third session that holds a module's pipe delays the pool shutdown until it exits; modules forward SIGTERM to their sessions so none is left (documented `shortcut:`).
- A real hang of the self-test module can hold `make e2e-test` for up to 5400 s at the 4x cap (300 s and 900 s guards at idle); said in the constant's comment.
- Known stubs: none.

## Human verification

None required. No sudo, real login or real config write. Real-config audit (audit only): `~/.codex` last modified 2026-11-02, `~/.config/opencode` 2026-10-31, `~/.pi` 2026-07-26, `~/.cursor` 2026-11-03 16:29 (before this plan's runs started), `~/.gsd` absent. `~/.claude` cannot be separated from the running session itself; every run used scratch HOMEs and `AI_KIT_REFUSE_REAL_HOME=1`. The uv cache was used as the runner forwards it (cache, not config).

## Threat Flags

None. The only new surface is `AIKIT_XAI_SELFTEST_LOAD`, read only inside `--self-test` and clamped to 1..4 (T-28-04, T-28-05 mitigated and pinned); process-group handling is covered by `ModuleDeadlineTest` and `StopGroupTest` (T-28-22).

## Self-Check: PASSED

Commits found in HEAD ancestry: 3f2d3ed, b0e03e9, 53ba2a1, 50366f7, 025af74. Files found: tools/run_unittest_parallel.py, skills/ai-kit-spec-review/references/cross-ai.mjs, .planning/scripts/cross-ai.mjs, tests/test_cross_ai_runner_e2e.py, tests/test_cross_ai_skill_text.py, tests/test_run_unittest_parallel.py, tests/test_wizard_pty.py, tests/test_config_doctor_pty.py. `pgrep -x stress-ng` empty. Working tree clean before this file.
