# 37-20 Summary: hosted lane through herdr, equal to headless, with the off switches

Status: complete in two per-task lanes (pi `router-env/my-coding`), verified by the orchestrator.

## Lanes

- fix-a (Task 1): `status=ok exit=0 elapsed=528s attempts=1`, commit eb399d1 (hook 128/128).
- fix-b (Tasks 2 and 3 in one lane): `status=ok exit=0 elapsed=513s attempts=1`, commit d386f75 (hook 128/128).
- Prompts were built from the plan's own task blocks plus anchor notes checked against f6b8a6f (`tmp/run-2026-11-19/c8-notes-37-20.md`).

## Commits

- eb399d1 `feat(37-20): hosted lane through herdr with the same result as headless (tracer host-ok)`
- d386f75 `feat(37-20): hosted equals headless for auth, empty and timeout; AIKIT_HOST precedence and off switches`

## What was done

- cross-ai.mjs runtime: `openTabs` (Map), `HOST_POLL_MS` 250, `HOST_ID_RX`, `HOST_ADMIT_GRACE_MS` 1000, `HOST_PID_GRACE_MS` 5000; `closeTab`, `dropSecrets`, `keepRecordOnly`, `waitDead`, `waitForFile`, `launcherVerified`, `hostedChild` (startup finalizer, `tab create` / `pane run` admission rules, 250 ms polling of out/err/pid/rc into the runChild capture buffers, verified-group signalling, tab closed before the run directory goes, run.json rewritten at tab create and at the first pid read), `hostFailedNote`, `hostSettingValue`; the `runOnce` host switch (`childOpts`), `host` and `promptArg` passed through `runCli`; `exitFlushed` retries `openTabs`; the `host` handler of `SETTING_HANDLERS`; `hostSetting` in `callOf`; `hostEntry` / `hostPlan` in `main`; the unknown `AIKIT_HOST` note.
- Self-test harness: `writeFakeHerdr` (verbs tab create, pane run, tab close; foreign tab t0; `FAKE_HERDR_PRECLOSED`), the `bin-herdr` folder and `hostedPath`, helpers `hostedUsable`, `hostFailedOnly`, `statusFields`, `hostLogProblem`, `hostPairCheck`, `hostPair`; seven cases `host-ok`, `host-auth`, `host-empty`, `host-timeout` (runtime) and `host-env-none`, `host-no-herdr`, `host-print-argv` (logic).

## Evidence

Orchestrator re-run, `tmp/run-2026-11-19/c9-verify-37-20.sh f6b8a6f 3`:

- `node --check` exit 0; every acceptance grep at count 1 (`spawnSync(HERDR_BIN` still 1; `hostPair('host-` 4).
- `--self-test-list` 615 cases, the seven host cases with the planned kinds.
- `AIKIT_XAI_SELFTEST_CASES=host-ok,host-auth,host-empty,host-timeout,host-env-none,host-no-herdr,host-print-argv,ok,hang,vocab-host-bad,vocab-stored-only ... --self-test`: `self-test ok`.
- `--print-argv` output equal to f6b8a6f for 14 calls (no host flag: no host line, argv unchanged); `--host none` prints `cross-ai: setting host=none applied`, `--host auto` without herdr prints `cross-ai: setting host=auto ignored reason=no_herdr`.
- Modules: runner_host_protocol, runner_describe, arch, arch_hardcoded_models, cli_help_flags, runner_flags 6/6; the eight self-test shards plus runner_e2e 9/9.
- No grok line added; tests/fixtures/no_hardcoded_models_baseline.json and detection.py unchanged; only cross-ai.mjs changed.

## Deviations

- Plan gap: the plan says `confirmReport` accepts entries without `proof`, but it throws `settings report entry <name> has no proof` for an applied entry. The two applied host entries (`none`, `herdr`) carry `proof: { unprovable: 'transport (D-28)' }`; the ignored `no_herdr` entry carries none.
- `hostSettingValue` redacts the `AIKIT_HOST` value before and after stripping control characters (the earlier-lane lesson on keys glued to control characters).
- The 37-20 functions sit at the end of the host block, after `writeRunDir` (the plan says "after herdrCall"; same block, read at call time only).
