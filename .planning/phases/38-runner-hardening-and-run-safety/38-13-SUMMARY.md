# 38-13 Summary: per-checkout run lock (part 1)

Status: complete. Two commits through two cross-AI lanes (pi router-env/my-coding), both status=ok on their first run:
57716aa (`feat(38-13): Tracer: the run lock file, the locked status and its release`, Task 1, 430 s) and 2e3d907
(`feat(38-13): lock record child group, two runs at once, review note and root walk`, Tasks 2 and 3, 340 s).

## What changed

- skills/ai-kit-spec-review/references/cross-ai.mjs: `STATUS_TABLE` row `locked` (exit 75, never `retry_after_s`); module state `liveLock`,
  `lockUpdateFailed` (reset in `main`); the lock block before `stateSig` (`LOCK_RECORD_VERSION`, `lockPath`, `checkoutRoot` (filesystem walk to
  the nearest `.git`, no git spawn; `GIT_DIR` and `GIT_CEILING_DIRECTORIES` give the cwd's real path), `lockText`, `lockHeldLine`,
  `acquireLock` (`wx` 0600 in a 0700 folder; `EEXIST` gives the held line; any other error runs without a lock with one line),
  `lockUpdate(fields, lock = liveLock)` (temp file and rename, one note on failure), `releaseLock` (only this run's `run_id`), `lockSeen`);
  release in `finish`, `exitFlushed` and a new `process.on('exit')` backstop; `runChild` calls `opts.onSpawn`, which only `runOnce` passes
  (child group and start into the record). In `main` the review-argv check and `planSettings` with its usage return now come before the lock
  and the first snapshot (same text); the lock block sits between them and `const before`. Export list gains `checkoutRoot`, `lockPath`,
  `lockUpdate`.
- skills/ai-kit-spec-review/references/cross-ai-selftest.mjs: fake pi modes `lockpeek` and `lockhold` (in `STICKY_FAKE`); helpers
  `plantLock(c, overrides = {})`, `plantLiveLock(c)`, `plantedUnchanged(c)`; `host-overlap` runs its background run on a second checkout;
  twelve cases: `lock-two-at-once`, `lock-gone-after-signal` (runtime) and `lock-held-refuses`, `lock-held-redacts`, `lock-not-taken`,
  `lock-late-usage-no-lock`, `lock-gone-after-failure`, `lock-record-fields`, `lock-none-usage`, `lock-review-note`, `pure-lock-update-note`,
  `pure-lock-root` (logic).

## Verification (run by the chunk agent)

- Acceptance greps: every named line once, `releaseLock();` 3, `onSpawn` 2, the twelve case names, `function plantLiveLock(c)` and
  `lockpeek: () => {` once each; `node --check` on both files.
- The moved review-argv and `planSettings` block of 7926475 (22 lines) appears byte-identical once, after the `no_model` return and before the
  lock block and `const before`.
- Sixteen cases (the twelve new ones, `host-overlap`, `ok`, `hang`, `session-chosen-pi`) print `self-test ok`; `--self-test-list` 657 lines with
  the twelve new cases at the planned kinds.
- `--print-argv` of six calls byte-equal to 7926475 (no lock on that path); detection.py and the model-literal baseline unchanged; runner and
  sibling diffs reviewed against the plan. Shards and wave gates: see the ledger (c38-4, waves 8-9).

## Deviations

- Task 3's action text (`fake/slowok`, one `Promise.all`, `pi slowok` count) contradicts its own behavior line; the behavior line was followed
  (`fake/lockhold`, `Promise.race`, the `lock-release` file, `pi lockhold` / `pi rpc` counts): the winner cannot end before the release, so the
  loser provably met a held lock (SPEC R3 concurrency edge).
- Task 2's acceptance grep `function lockUpdate(fields)` cannot match the signature the task defines; the two-parameter signature
  `function lockUpdate(fields, lock = liveLock)` was kept and grepped.
- The plan's `selftest.sh` (bare `node` under a scratch HOME, the Volta-shim fork hazard) was replaced by `tmp/run-2026-11-19/p38-13/selftest.py`
  (the real node executable).
- One commit for Tasks 2 and 3 (the chunk's lane prompt) instead of one per task.
- `acquireLock` opens the `wx` file itself instead of calling `writePrivate`, so it removes a half-written file only when this call created it.
- `plantLiveLock(c)` returns null and keeps the path on `c.lockFile`: a truthy `setup` return fails a case in this harness.
- The existing case `session-chosen-pi` started two execute runs on one checkout at once; its second concurrent run now uses a second
  checkout (same session id, same assertion), like `host-overlap`.
