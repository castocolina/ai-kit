# 38-02 Summary: runner dead code and the temp-folder proof

Status: complete. Commits a68ebe7 (`refactor(38-02): drop unused watchChunk parameters and the redundant dropState term`) and 87e9fec (`test(38-02): prove ok, failure, signal and timeout runs leave no runner temp folder`); both touch only `skills/ai-kit-spec-review/references/cross-ai.mjs`. Executed through two per-task cross-AI lanes (pi router-env/my-coding), each status=ok on its first run (215 s, 264 s).

## What changed

- `watchChunk(relay, chunk)` (three unused parameters gone, both callers in `runOnce` updated).
- `dropState` tests `!QUOTA_KEEP.has(status)`; the set constant that fed only its redundant first term is deleted (logically equal: `quota` is in `QUOTA_KEEP`, none of the five deleted members is).
- One comment above the per-attempt cap names the kept live helpers: `clampAttemptTimeout`, `clampCapS` (4-hour bound, T-25-13), `liveMatch`, `armLimit`.
- New runtime self-test case `temp-dirs-gone`: an ok, an auth failure (69), a SIGTERM (143) and a timeout (124) run each leave no `cross-ai-*` or `xai-idx-*` entry in the case TMPDIR; status lines and the fake lane's `gc.pid` are checked so the signal and timeout paths ran with a live lane.

## Verification (run by the chunk agent, not taken from the lane reports)

- Acceptance greps all at their expected counts; `node --check` ok.
- `--self-test-list`: `temp-dirs-gone	runtime`, one more case than at the plan's base.
- Cases ok, auth, hang, sigterm-hang, pure-ladder-clamps, pure-ladder-cap-clamp, reap-after-failure, temp-dirs-gone: `self-test ok`.
- `--print-argv` for pi exec and review, opencode exec, claude review, cursor exec: byte-equal to the base template (random session ids normalised).
- tests.test_arch, tests.test_arch_hardcoded_models, tests.test_runner_describe, tests.test_cross_ai_render_sync pass; the commit hooks passed (128/128 covering modules each, self-test shards included). The lane ran the eight shard modules (8/8) and the four gates.

## Deviations

- None in code. The live copy `.planning/scripts/cross-ai.mjs` is not re-rendered (plan 38-25 does it).
