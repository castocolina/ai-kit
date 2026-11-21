# 37-19 Summary: hosted-lane protocol pieces (run directory, launcher, readers, herdrCall) and the herdr/jev arch rules

Status: complete in two per-task lanes (pi `router-env/my-coding`), verified by the orchestrator.

## Lanes

- fix-a (Task 1): `status=ok exit=0 elapsed=474s attempts=1`, commit d032673 (hook 129/129).
- fix-b (Tasks 2 and 3 in one lane): `status=ok exit=0 elapsed=1188s attempts=1`, commit a05fe19 (hook 132/132; the lane also ran `make test` green).
- Prompts were built from the plan's own task blocks plus orchestrator anchor notes checked against db99848 (`tmp/run-2026-11-19/c8-notes-37-19.md`).

## Commits

- d032673 `feat(37-19): host protocol run directory and launcher, run for real under /bin/sh`
- a05fe19 `feat(37-19): quoting, NUL refusal, rc and start-time readers, herdrCall, protocol fixture lock and arch rules`

## What was done

- cross-ai.mjs host block: `HOST_LABEL_PREFIX`, `HOST_PATH_SAFE`, `HOST_FILES`, `HOST_TOOLS`, `HOST_SETSID`, `RUN_RECORD_VERSION`, `HERDR_VERBS`, `HERDR_TIMEOUT_MS`; `shQuote`, `hostToken`, `hostLabel`, `hostRunDir`, `writePrivate`, `procStartTime`, `procGroup`, `hostTypedLine`, `hostEnvText`, `buildLauncher`, `writeRunDir`, `parseRc`, `hostStartProblem`, `herdrCall` (the one `spawnSync(HERDR_BIN` site); `pidAlive` moved unchanged from the self-test helpers into the host block.
- `run.json` fields exactly as planned: `version`, `token`, `runner_pid`, `runner_start`, `host_name`, `checkout_root`, `role`, `runtime`, `label`, `tab_id`, `pane_id`, `launcher_pid`, `launcher_pgid`, `launcher_start`, `created_ms` (run.json written first by `writeCycleState`, then env, prompt, launch.sh, out, err; 0700 directory, 0600 files).
- runCli refuses an argv element holding a NUL byte (`cross-ai: argv for <runtime> holds a NUL byte; refused`, status `usage`, exit 2, no spawn); self-test case `argv-nul-refused` (logic).
- tests/test_runner_host_protocol.py (replaces the 37-02 stub): 13 tests run the built launcher for real under `/bin/sh` (no herdr; the herdr test writes its own fake script).
- tests/fixtures/runner_host_protocol.json: the D-27 protocol fixture (12 keys).
- tests/test_arch.py: `js_code_lines`, `runner_jev_hits`, `runner_herdr_problems` with two live rules and two non-vacuity tests.

## Evidence

Orchestrator re-run, `tmp/run-2026-11-19/c8-verify-37-19.sh db99848 3`:

- `node --check` exit 0; every acceptance grep of Tasks 1-3 at its expected count (`^function pidAlive|^const HOST_FILES` 2, HOST_FILES before pidAlive; `spawnSync(HERDR_BIN` 1; 13 test methods, no stub skip; fixture 12 sorted keys, 15 record fields; 4 arch tests).
- `AIKIT_XAI_SELFTEST_CASES=argv-nul-refused,copilot-argv-review ... --self-test`: `self-test ok`; `--self-test-list` 608 cases with `argv-nul-refused<TAB>logic`.
- `--print-argv` output equal to db99848 for 14 calls (pi, opencode, cursor, codex, claude, copilot in both modes, effort and session variants).
- Modules: runner_host_protocol, runner_describe, arch, arch_hardcoded_models, cli_help_flags, runner_flags 6/6; the eight self-test shards plus runner_e2e 9/9; verbose test_runner_host_protocol 13 ok (the process-group test ran, not skipped); the four new arch tests ok.
- No grok line added; tests/fixtures/no_hardcoded_models_baseline.json and detection.py unchanged; files changed are exactly the plan's four.

## Deviations

- Task 3 plan contradiction: for "GOOD plus `spawn(HERDR_BIN, ['tab', 'list']);`" the plan's own algorithm also reports line 5 as a spawn outside the herdrCall body; the algorithm was kept as written and that case expects `["5: herdr spawn outside herdrCall", "2 herdr spawn sites (one expected, in herdrCall)"]` (every other case keeps the plan's list).
- The test module takes node from `tests.cross_ai_selftest._real_node_executable()` (as tests/test_runner_describe.py does) instead of `shutil.which("node")`: the Volta shim fails under the runner's scratch HOME and run_node's bare env.
- `buildLauncher` quotes every argv element before substituting `"$aikit_prompt"`, so a NUL in the argv-prompt element is refused too (stricter, same output otherwise).
- `herdrCall`, `parseRc` and `hostStartProblem` sit just before the HOST_* constants in the same host block (they read them only at call time); the module docstring is wrapped over two lines for ruff.
