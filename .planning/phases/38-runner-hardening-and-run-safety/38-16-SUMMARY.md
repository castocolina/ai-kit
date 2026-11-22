# 38-16 Summary: tree polling and the heartbeat suffix

Status: complete. Two commits through two cross-AI lanes (pi router-env/my-coding), both status=ok on their first run:
6dd2fd4 (`feat(38-16): Tracer: background tree reads reset the idle clock of an execute lane`, Task 1, 342 s) and d50bdfd
(`test(38-16): poll cases for silent, chatty, editing, review, failed and hung reads`, Tasks 2 and 3, 594 s).

## What changed

- skills/ai-kit-spec-review/references/cross-ai.mjs: `runChild` option `bg` (a background child never sets `current`/`currentFinalize`; its
  `finalize` sits in `bg.stops` while it runs); `treeState(cwd, limit, depth = 0, bg = null)` with a `bg.cancelled` check after each of its five
  git steps and `bg` passed to the recursion; module state `treePollNoted`; `pollTreeRead(cwd, limit, baseHead, bg)` (treeState plus
  `rev-list --count <baseline head>..<head>`, not exported); in `runOnce`: the poller (one read in flight, a read after a check interval without
  output, one read per idle period while output flows), the change test against the previous read (the first one is 38-15's baseline), the
  `printed output but changed nothing` notice once per idle period with the `no_tree_change` finding once per run, the failed-read line once per
  run, the idle gate on 38-11's `onIdle` (an idle end waits for a read in flight or takes one fresh read), the consumer of 38-11's
  `idleResetter` pair, the end-of-lane cancel and join of an in-flight read, the heartbeat suffix `, commits +<n> since the baseline, tree
  changed|unchanged`; `idlePlan` passed from `main` through `runCli` to `runOnce`.
- skills/ai-kit-spec-review/references/cross-ai-selftest.mjs: fake pi modes `quiet-commit`, `quiet-idle`, `chatty-nochange`, `quiet-edit`,
  `review-slow`, `quiet-headonly`, `change-then-stall`, `quiet-gitfail`, `quiet-githang`, `githang-silent` (all in `STICKY_FAKE`); the git
  wrapper logs `write-tree` to `$HOME/git-calls.log` and `hang <pid>` / `fail <pid>` to `$HOME/git-switch.log`; eleven cases: `poll-quiet-commit`,
  `poll-quiet-idle`, `poll-chatty-nochange`, `poll-quiet-edit`, `poll-review-none`, `poll-head-only`, `poll-change-then-stall`,
  `poll-git-fail-once`, `poll-git-hang-stopped`, `poll-git-hang-capped` (runtime) and `poll-non-git-note` (logic).

## Verification (run by the chunk agent)

- Acceptance greps: every named signature and line once, five `if (bg?.cancelled) return null;`, `pollTreeRead` not exported; `node --check` on
  both files.
- The eleven `poll-` cases with `non-git-exec`, `git-hang`, `ok`, `git-after-fail` and `ladder-dirty-inside` print `self-test ok`; the eight
  38-11 idle cases and `lock-gone-after-signal` print `self-test ok` (lane); `--self-test-list` 691 lines, ten `poll-` runtime and one logic.
- `--print-argv` of six calls byte-equal to the 38-15 tip; `tests.test_arch_hardcoded_models` and `tests.test_runner_describe` pass;
  detection.py and the model-literal baseline unchanged; runner and sibling diffs reviewed against the plan. Shards and wave gates: see the
  ledger (c38-5).

## Deviations

- The deferred-idle flag `poll.allowIdle` is kept until the gate consumes it and is cleared by new child output: the plan set it back to false
  synchronously around `recheck()`, before 38-11's `setImmediate` consults the gate, so it never took effect.
- The plan's `selftest.sh` (bare `node` under a scratch HOME, the Volta-shim fork hazard) was replaced by `tmp/run-2026-11-19/p38-16/selftest.py`.
- One commit for Tasks 2 and 3 (the chunk's lane prompt) instead of one per task; code comments are shorter than the plan's quoted ones.
