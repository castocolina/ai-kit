# 38-19 Summary: the hosted lane obeys the idle clock and the output bound; `tab list` joins the herdr verbs

Status: complete. Two commits through two cross-AI lanes (pi router-env/my-coding), each status=ok on its first run:
e9d2777 (`feat(38-19): Tracer: tab list in the herdr verb set, the fake's list and error shapes, tab_not_found counted as gone`, Task 1,
298 s) and 4809596 (`feat(38-19): hosted idle clock through finalize('idle'), byte-exact capture retention and the 2x-cap cut of hosted
output files`, Tasks 2 and 3, 364 s).

## What changed

- skills/ai-kit-spec-review/references/cross-ai.mjs: `HERDR_VERBS` = `['tab create', 'pane run', 'tab close', 'tab list']`; `herdrCall`
  returns `code` (the JSON `error.code` of a failed call, else null); `closeTab` counts `tab_not_found` as gone; `captureMaxBytes(text)`
  (exported) and `LANE_CAPTURE_MAX_BYTES` from the lower-only knob `AIKIT_XAI_CAPTURE_MAX_BYTES` (65536 to 32 MiB), passed only to lane
  captures through `childOpts.captureMax` (`CAPTURE_MAX_BYTES` stays 32 MiB for git and listing reads); `pushCapped` keeps exactly the newest
  bytes (slices the oldest chunk) on both transports; `hostedChild` opens `out`/`err` with `r+`, cuts a file past twice the cap with
  `ftruncateSync` inside `readNew` and reads on from offset 0, and gains the idle hook (monotonic clock reset by bytes read, the expiry-time
  `tick()` sample, `onIdle` deferral, the `{ reset, recheck }` pair for 38-16's tree poll, `finalize('idle')` through the verified group,
  `idle` in the result).
- skills/ai-kit-spec-review/references/cross-ai-selftest.mjs: fake herdr `tab list`, `tab_not_found` on a close of an unknown or closed tab,
  `FAKE_HERDR_DOWN=1` (`server_not_running` on every verb), `FAKE_HERDR_FAIL=list-hang|list-fail`, second foreign tab `tx`; `hostLogProblem` and
  `hostSafety` refuse both foreign tabs; pi fake modes `hdrip`, `hcommit`, `hflood` (sticky); `hostPairCheck` members `present`, `absent`,
  `after`; `hostPair` also checks the hosted run's status line; cases `host-fake-shapes`, `pure-capture-max-bytes` (logic), `host-cap`,
  `host-idle-silent`, `host-idle-busy`, `host-idle-commits` (runtime).
- tests/test_arch.py (`HERDR_VERBS_ALLOWED` with `tab list`, the `dropped` non-vacuity row, the test renamed to `..._through_listed_verbs`),
  tests/fixtures/runner_host_protocol.json (`herdr_verbs`), tests/test_runner_host_protocol.py (refusal text names `tab list`).

## Verification (run by the chunk agent)

- Acceptance greps as amended by review c1: verb set, arch tuple and fixture once each; `spawnSync(HERDR_BIN` still once; the idle-clock
  comment once, `opts.idleResetter?.({ reset:` twice, the `idle` resolve once; `captureMaxBytes`, `LANE_CAPTURE_MAX_BYTES`, `captureMax:`,
  `ftruncateSync(fds[key], 0)` and the `r+` open once; no `fs.truncateSync(made.files`; no new `Date.now()`.
- The six cases plus `pure-capture-cap`, `host-ok`, `host-auth`, `host-empty`, `host-timeout`, `host-group-left`, `host-overlap`,
  `host-dead-launcher`, `host-create-lost`, `host-failed-run`, `host-signal` print `self-test ok`; `--self-test-list` 745 lines, kinds as planned.
- `--print-argv` of six calls byte-equal to 90f7802; `tests.test_arch`, `tests.test_runner_host_protocol`, `tests.test_runner_describe`,
  `tests.test_arch_hardcoded_models` pass; detection.py and the model-literal baseline unchanged. Shards and wave gates: see the ledger (c38-6).

## Deviations

- Task 3's case name `pure-capture-cap` collides with the existing `pushCapped` case of that name (the one that keeps `bbbbcccc`); the new
  `captureMaxBytes` case is `pure-capture-max-bytes` with the plan's rows.
- Task 3's acceptance greps (`CAPTURE_MAX_BYTES = captureMaxBytes(...)`, `fs.truncateSync(made.files[key], 0)`) predate the binding review
  amendment 4b; the code follows 4b (scoped knob, `r+` fds, `ftruncateSync` in the read loop).
- `hflood` waits for the runner's cut only when its stdout is a file (hosted); headless it waits 700 ms like the other steps.
- The plan's `selftest.sh` (bare `node` under a scratch HOME, the Volta-shim fork hazard) was replaced by `tmp/run-2026-11-19/p38-19/selftest.py`.
- One commit for Tasks 2 and 3 instead of one per task.
- Retention change: no test pinned the old kept-newest count (only the `bbbbcccc` pure case, which still holds); no fake mode exceeds 32 MiB.
