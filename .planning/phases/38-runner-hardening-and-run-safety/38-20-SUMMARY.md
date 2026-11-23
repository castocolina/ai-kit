# 38-20 Summary: the sweep of what hard-killed hosted runs leave behind

Status: complete. Two commits through two cross-AI lanes (pi router-env/my-coding), each status=ok on its first run, and one orchestrator
test fix: 5adf7e7 (`feat(38-20): Tracer: sweepRuns, --sweep and the automatic sweep close one dead run end to end`, Task 1, 476 s), b5cecf8
(`feat(38-20): what the sweep never closes, keeps or touches, sweep races, a hung herdr and the SIGKILL end-to-end case`, Tasks 2 and 3,
397 s), and the `test(38-20)` fix of `sweep-empty` (below).

## What changed

- skills/ai-kit-spec-review/references/cross-ai.mjs: `SWEEP_HERDR_TIMEOUT_MS` (2000, exported), `SWEEP_BUDGET_MS` (4000, one budget per
  sweep), `SWEEP_REREAD_MS`, `RUN_RECORD_MAX_BYTES`, `SWEEP_DIR_RX`, `SWEEP_REASONS` (`unreadable`, `other host`, `live launcher`,
  `hosting off`, `herdr unreachable`, `tab unproven`, `close failed`, `cleanup failed`); `runnerAlive(rec)` and `launcherGroupAlive(rec)`
  (exported) on 38-14's `lockPidAlive`/`lockStartTime`/`lockGroupAlive` (unknown counts alive); fail-closed `readRunRecord(dir, token)` (lstat,
  regular file, size cap, one fd, the full record grammar); `sweepRuns({ explicit, hostingOff })` (exported): live claims skipped, the 2 s
  monotonic re-read, deadness before the claim rename `<token>.sweep-<pid>-<start>`, secrets and every other file but `run.json` removed
  first, one `tab list` per sweep, a close only by id and complete label, keep reasons counted and the record renamed back, the report line
  through control-character removal and redaction; `herdrCall` spawns with `killSignal: 'SIGKILL'`; flag `--sweep` (usage line, parse line
  after `--describe`, usage error with `--print-argv` or `--classify-only`); in `main` the explicit sweep after the describe branch and the
  automatic sweep directly before the lock block (after the print-argv and classify-only returns).
- skills/ai-kit-spec-review/references/cross-ai-selftest.mjs: helpers `plantRun`, `plantTabs`, `stateKeyLeft`, `sweepLine`, `hostDirNames`,
  `callsJson`; fake herdr switches `close-notfound`, `close-hang`, `list-slow`; the usage row `vocab-sweep-print-argv`; twenty `sweep-` cases:
  sixteen logic (`sweep-dead-closes`, `sweep-auto-run`, `sweep-foreign-safe`, `sweep-null-id`, `sweep-zero-tabs`, `sweep-down`,
  `sweep-host-none`, `sweep-env-none`, `sweep-live-untouched`, `sweep-unreadable`, `sweep-other-host`, `sweep-notfound`, `sweep-empty`,
  `sweep-claim-takeover`, `sweep-bad-record`, `sweep-race`) and four runtime (`sweep-herdr-hang`, `sweep-fresh-unreadable`,
  `sweep-sigkill-e2e`, `sweep-close-hang`).

## Verification (run by the chunk agent)

- Acceptance greps (with review amendment 8): every named function and constant once, two `await sweepRuns(`, one `herdrCall('tab list'`,
  `spawnSync(HERDR_BIN` still once; `node --check` on both files.
- The twenty `sweep-` cases plus `vocab-sweep-print-argv`, `host-ok`, `host-dead-launcher`, `host-create-lost`, `host-overlap`, `host-cap`
  and `ok` print `self-test ok`; `--self-test-list` 766 lines, 20 `sweep-` lines at the planned kinds.
- `--print-argv` of six calls byte-equal to the 38-19 tip; `tests.test_arch`, `tests.test_runner_host_protocol`, `tests.test_runner_describe`,
  `tests.test_arch_hardcoded_models` pass; detection.py and the model-literal baseline unchanged; the fix commit's hook ran 128/128 modules
  including the eight shards. Shards and wave gates: see the ledger (c38-6).

## Deviations

- `sweep-empty`: the lane gave its second run `--host none`, which turns the automatic sweep's herdr path off and so cannot show that an
  empty state home calls no herdr; the orchestrator's `test(38-20)` commit runs it with the default hosting setting (the plan's args) and keeps
  the no-`herdr.log` check.
- The 38-20 verification text's "17 cases" predates the review rows; 20 `sweep-` cases exist (the acceptance count).
- The plan's `selftest.sh` was replaced by `tmp/run-2026-11-19/p38-20/selftest.py` (real node); one commit for Tasks 2 and 3.
- The plan's explanatory comments above the sweep constants are shorter in the code (open for code review).
