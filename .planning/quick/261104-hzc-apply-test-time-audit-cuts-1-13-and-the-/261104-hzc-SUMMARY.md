---
quick_id: 261104-hzc
status: complete
date: 2026-11-04
commits: 05c84f7..429bc0d (16)
---

# Quick 261104-hzc: test-time audit cuts 1-13 and the data-file mapper rule

Applied `tmp/test-audit/REPORT.md` findings 1-13 (finding 14, the claude_precompact real
budget, skipped as decided). Executed by three sequential haiku executors in a linked worktree,
merged fast-forward onto the phase-29 branch.

## Per finding (module wall before -> after, seconds)

1. precompact_shims_e2e 57.4 -> 12.1. Hang tests merged; `run_shim.mjs` scales setTimeout via
   `AI_KIT_SHIM_TIME_SCALE`; `TestShimDeadlinePins` pins TIMEOUT_MS 10000 (both precompact
   shims) and 2000 (pi tool-advisor, tool-reminder) and keeps the knob out of every shim.
2. project_rules_all_e2e 25.6 -> 0.9. Changed: forwarding `tool_cache_forwards` was measured
   not to help (the identity probe passes node only PATH and HOME), so the scratch PATH links
   the real node binary. The test now asserts the probe's answer (R18/R19 `missing`, no
   `unverified`).
3. run_unittest_parallel 25.5 -> 6.9. One-test arch group in a temp folder; 1.0 s deadlines,
   0.5 s grace; MODULE_STOP_GRACE_SECS 15 pinned. Longest-first start order kept.
4. claude_session_wake_hook 16.9 -> 2.9. Driver sets a 1 s deadline; AST pin of 8.0/1.0/5.0
   and 8 s < the registered 10 s timeout.
5. cursor_quota 11.4 -> 5.3 (cursor_fakes 2.7 -> 1.3). poll_interval 0.05.
6. wizard_pty 16.7 -> 7.0. Settle-on-quiet and file-state waits; flake check 2/2 plus the hook.
7. session_wake_fire 17.8 -> 9.5. Lock hold 0.5 s, fake host sleep 1.5 s.
8. precompact_core 13.2 -> 7.1. 10 trials, coverage of every error count asserted; the
   40-chunk deterministic test kept.
9. spec_runner_dispatch 13.2 -> 7.1. `_TERM_GRACE_S`/`_DRAIN_S` patched; (4, 2) pinned.
10. wizard_app 21.4 -> 4.4 / 7.4 / 9.2 in three parallel modules (66 tests kept); groups
    regenerated.
11. arch 6.4 -> 6.3. Parse cache added plus a teardown that frees it (freeing at exit cost
    3 s); the saving is within noise, not the projected 4 s.
12. jev_fast_decision 18.0 -> 15.7. Retry sleep patched.
13. Mapper: a data file outside the unit folders matches only in test code. `--staged
    AGENTS.md` 16 modules / 11.3 s -> 13 modules / 4.8 s.
14 (user item). E2E_RECORDED_SECS refreshed; push-time numbers in README/AGENTS refreshed.

## Gate (worktree, head 7b4db41 before rebase)

- `make test` rc 0, 66.2 s: unit 21.7 s (80/80), unit-uv 0.1 s (1/1), integration 8.9 s
  (6/6), e2e 28.6 s (23/23) + test_install.sh 0.6 s (45 passed), arch 6.3 s (1/1).
- Tier walls before (REPORT.md): unit 34.3, integration 20.9, e2e 57.4, arch 6.5.
- e2e stays above 20 s: the eight cross-ai self-test shards take 21-24 s each (out of scope).
- `time_prepush.py` rc 0: test hooks 30.7 s (was 55.4 s), push-worst 42.7 s, verdict pass.
- `staged_mapper.py --stats` rc 0; env matrix custom-tmpdir + long-path rc 0, identical.

## Deviations

- Item 2 implemented by linking real node instead of forwarding tool caches (measured).
- Extra commit `18b4290` (arch cache teardown) fixes a 3 s exit regression from `70e114f`.
- `staged_mapper.py tools/command_ownership.py` also selects test_staged_mapper (its new test
  names the path in code); kept as safe over-selection.
