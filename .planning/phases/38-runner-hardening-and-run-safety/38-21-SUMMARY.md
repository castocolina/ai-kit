# 38-21 Summary: the lock, the execute checks and the state home for a hosted lane

Status: complete. Two commits: 400c5d0 (`feat(38-21): Tracer: the runner's own state is excluded from the tree snapshot when it lies inside
the checkout`, Task 1, one cross-AI lane, pi router-env/my-coding, status=ok, 238 s) and f3589e4 (`feat(38-21): the lock record and liveness
of a hosted lane, and hosted equals headless on findings with no key left`, Tasks 2 and 3: the lane, 167 s, wrote the code and the cases but
stopped uncommitted on `host-ok: finding lines differ`; the chunk agent fixed the pair harness, verified and committed).

## What changed

- skills/ai-kit-spec-review/references/cross-ai.mjs: `stateExcludeRel(cwd)` (the deepest existing ancestor of `<state home>/ai-kit/spec` is
  resolved, so a state folder not made yet still compares; only that subtree, never the whole tree); `treeState` adds
  `-- :(exclude,literal)<rel>` to `add -A` only when it is set (the plain `['add', '-A']` argv otherwise) and drops the subtree from the
  ignored-file signature; `lockHostedLine(rec)` (`cross-ai: lock: held by a hosted lane, launcher group <pgid or ->, herdr tab <tab or ->`);
  `hostedLaunchAlive(rec)` (the launcher group by `lockGroupAlive`; with only a token, a live group leader in the run directory's `pid`, or no
  `pid` yet within `HOST_PID_GRACE_MS` of `host_ms`); `lockProbe().launcherAlive` and the `orphan` branch of `lockVerdict`; `acquireLock`
  returns `hosted` beside `held`, a hosted orphan prints the one hosted line, and a cleared stale lock with a token runs
  `sweepRuns({ ..., onlyToken })` (new optional parameter); `main` passes `hostingOff` to `acquireLock` and logs `got.hosted`; `hostedChild`
  publishes `token`, `tab_id`, `host_ms` to the lock before `pane run` and the launcher fields when the pid is first read.
- skills/ai-kit-spec-review/references/cross-ai-selftest.mjs: pi fake modes `hstate`, `hstateloop` (sticky), `hscan`; `statusFields` compares
  `coverage` and `findings`; `hostPairCheck` compares the `cross-ai: finding ` lines; `runTwice` runs an optional `between(c)` before the
  second run and `hostPair` uses `hostPairReset` (restores tracked files and removes untracked top-level files, commits stay); helper
  `killedHostedRun(c, { keepLauncher })` (kills only `pidsUnder(c.repo)` pids with a readable start time, the launcher group only after its
  start time matches); eleven cases: `state-inside-nochange`, `state-root-nochange`, `state-inside-edit`, `state-inside-ignored` (logic),
  `host-state-in-checkout`, `host-state-is-root`, `state-idle-expires`, `host-lock-stale-swept`, `host-lock-live-group`,
  `host-findings-partial`, `host-key-scan` (runtime).

## Verification (run by the chunk agent)

- Acceptance greps (with review amendment 5b): `stateExcludeRel`, `lockHostedLine`, `hostedLaunchAlive`, the hosted line text, the `host_ms`
  publish, `onlyToken: seen.rec.token`, `launcherAlive: (rec) => hostedLaunchAlive(rec)`, `if (got.hosted) log(got.hosted);` once each;
  `lockUpdate({ token: made.record.token,` twice (publish and launcher); one `:(exclude,literal)`; the plain `['add', '-A']` still once;
  sibling `unknown escalate coverage findings'` and `return 'finding lines differ';` once.
- The eleven cases plus the hosted pairs, `sweep-sigkill-e2e`, `pure-lock-verdict`, `nochange`, `ok` print `self-test ok`; all 88 `host-`,
  `lock-`, `pure-lock`, `sweep-`, `state-` and `baseline-` cases in one run print `self-test ok`; `--self-test-list` 777 lines, kinds as
  planned.
- `--print-argv` of six calls byte-equal to the 38-20 tip; `tests.test_arch`, `tests.test_runner_host_protocol`, `tests.test_runner_describe`,
  `tests.test_arch_hardcoded_models`, `tests.test_cross_ai_render_sync` pass; `make ruff`, `make pyright`, `make vulture` exit 0; the commit
  hook ran 128/128 modules including the eight shards.

## Deviations

- Comparing finding lines between the hosted and the headless run of a pair (Task 3 step 2) cannot pass as written: both runs share one
  checkout, so the first run's uncommitted edit (`a.txt`) is already dirty at the second run's baseline and only the first reports
  `uncommitted_edits`. The pair now restores the starting work tree before its second run (`hostPairReset` through the new `between` hook of
  `runTwice`); commits are kept, so `host-idle-commits` still counts both runs' commits. The comparison itself is unchanged.
- The acceptance line `launcherAlive: (rec) => launcherGroupAlive(rec)` predates amendment 5b; the member is `hostedLaunchAlive(rec)`.
- `host-findings-partial` replaces `host-findings-nochange` (amendment 3b).
- The plan's `selftest.sh` was replaced by `tmp/run-2026-11-19/p38-21/selftest.py` (real node); one commit for Tasks 2 and 3.
