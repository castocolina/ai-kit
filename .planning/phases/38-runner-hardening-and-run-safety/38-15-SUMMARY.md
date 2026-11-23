# 38-15 Summary: start-of-run baseline

Status: complete. Two commits through two cross-AI lanes (pi router-env/my-coding), both status=ok on their first run:
ec31c53 (`feat(38-15): Tracer: the fresh baseline in the lock record and the task record, deleted on ok`, Task 1, 253 s) and 6bb7507
(`feat(38-15): baseline reuse or replacement, --baseline, unborn HEAD, unwritable state and the owner's dirty file`, Tasks 2 and 3, 347 s).

## What changed

- skills/ai-kit-spec-review/references/cross-ai.mjs: module state `liveBaseline` (`{ head, tree, at, role, cli, model, source }`),
  `baselineFile`, `baselineNoted` (reset in `main`); the baseline block after the lock block: `BASELINE_RECORD_VERSION`, `BASELINE_SHA_RE`,
  `baselineVerdict` (invalid, future, expired at `age >= capS * 1000`, rebased), `baselineGit` (`yes`/`no`/`unknown`), `headDescends` (equality
  and an unborn base short-circuit with no git call), `baselineObjectsExist` (`git cat-file -e`), `baselinePath`, `baselineNote` (one note per
  call), `resolveBaseline` (flag, then a valid task record, then the fresh start snapshot, which is stored as the task record; a failed probe
  keeps the record untouched with one note; replacement adds the `baseline_replaced` finding with its reason; the six data fields go into the
  lock record through `lockUpdate`); `finish` deletes the task record on `ok`; `--baseline <sha>` (7 to 64 hex, `o.baseline`) checked with
  `git rev-parse --verify -q <sha>^{commit}` and `<head>^{tree}` before the lock (a bad value is a usage error and takes no lock; review runs
  ignore it with a note); `resolveBaseline` runs after the start snapshot for git execute runs, keyed by the caller's stdin text. Export list
  gains `baselinePath`, `baselineVerdict`.
- skills/ai-kit-spec-review/references/cross-ai-selftest.mjs: `BASELINE_TASK`, helper `plantBaseline`, fake pi mode `commitcrash`, `lockpeek`
  also reports the task record; `lock-record-fields` now expects a baseline object with exactly `head tree at role cli model`; twelve logic
  cases: `baseline-fresh-recorded`, `pure-baseline-verdict`, `baseline-reused`, `baseline-reused-equal`, `baseline-rebased`, `baseline-expired`,
  `pure-baseline-flag-parse`, `baseline-flag-wins`, `baseline-flag-bad`, `baseline-unborn`, `baseline-unwritable`, `baseline-owner-dirty`.

## Verification (run by the chunk agent)

- Acceptance greps: every named function, constant and message once, the Task 2 marker comment gone, `let baselineHead = null;` once, the
  twelve case names and `commitcrash: () => {` once; `node --check` on both files.
- Seventeen cases (the twelve new ones plus `lock-record-fields`, `lock-not-taken`, `lock-two-at-once`, `lock-stale-race`, `ok`) print
  `self-test ok`; `--self-test-list` 680 lines, 12 `baseline-`/`pure-baseline-` lines, all `logic`.
- `--print-argv` of six calls byte-equal to the 38-14 tip; `tests.test_arch_hardcoded_models` and `tests.test_runner_describe` pass;
  detection.py and the model-literal baseline unchanged; runner and sibling diffs reviewed against the plan. Shards and wave gates: see the
  ledger (c38-4, wave 10).

## Deviations

- `plantBaseline(c, overrides = {})` stores the record on `c` and returns null instead of `{ file, rec }`: a truthy `setup` return fails a case in
  this harness.
- When a probe fails and the record is kept untouched (orchestrator decision 6), `resolveBaseline` also clears `baselineFile`, so an `ok` run
  does not delete the record it could not check (the plan's delete-on-ok line would otherwise remove it).
- The plan's `selftest.sh` (bare `node` under a scratch HOME, the Volta-shim fork hazard) was replaced by `tmp/run-2026-11-19/p38-15/selftest.py`.
- One commit for Tasks 2 and 3 (the chunk's lane prompt) instead of one per task.
