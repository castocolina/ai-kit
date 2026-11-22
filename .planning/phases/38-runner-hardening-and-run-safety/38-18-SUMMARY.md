# 38-18 Summary: the execute check in the run and the `partial` status

Status: complete. One commit through one cross-AI lane (pi router-env/my-coding), status=ok on its first run: 0c6ee7f
(`feat(38-18): wire the execute check into the run: commits, changed paths, findings and the partial status`, Tasks 1 to 3, 650 s).

## What changed

- skills/ai-kit-spec-review/references/cross-ai.mjs: `STATUS_TABLE` gains `partial: { exit: 1 }`; `runChild`'s result carries `stdoutDropped`;
  `diffNames(a, b, cwd, limit = runDeadline)` (`-c core.quotepath=off diff-tree -r --no-renames --name-only -z`, null and `gitFailed` on a
  failure, a timeout or a capped capture; `changedPaths` now delegates to it); `parseCommitLog` (port of gsd-core's record parser, exported);
  `commitPaths` (gsd-core's commitFiles rule: a non-merge with `--first-parent`, a two-parent merge with `--remerge-diff`, an octopus merge
  nothing); `commitsSince` (`git log --format=%H%x1f%P%x1f%s%x1e <baseline head>..<end head>`); `executeFindings(prompt, r, end, cwd, o, noTree)`
  (commits, changed paths between the baseline tree and the end tree, uncommitted paths that were clean at the baseline, the caller's `raw`
  text and the answer into 38-17's `planFindings`; every finding through `addFinding`, the coverage into `liveCheck.coverage`; `{ gitFailed: true }`
  when git evidence is missing; a non-git cwd checks the answer only); in `main` the `checked` step after the end snapshot of a spawned execute
  run, an `aborting` re-check after it, and in the `r.ok` branch after `no_change`: git evidence missing -> `gitFailStatus()`, then
  `contract_violation`, then `partial`, none writing the answer to stdout.
- skills/ai-kit-spec-review/references/cross-ai-selftest.mjs: fake pi mode `plan-commit` (reads `FAKE_PLAN`), helpers `planPrompt`, `all3`,
  `planCase`; nineteen logic cases: `pure-commit-log` and the eighteen `plan-*` spawn cases; two existing assertions updated for the new
  output: `status-group-before-retry` now expects `coverage=n/a` (a spawned execute run that fails is still checked, D-15) and `baseline-rebased`
  finds `baseline_replaced` anywhere in the findings group (the run also carries `uncommitted_edits`).

## Verification (run by the chunk agent)

- Acceptance greps: every named function and line once, the `partial` return before the single `process.stdout.write(r.text);`, 17
  `planCase('plan-` calls; `node --check` on both files.
- The nineteen cases plus `ok`, `nochange`, `ladder-dirty-inside`, `finding-lines-through-finish` and `check-group-no-spawn` print
  `self-test ok`; `--self-test-list` 739 lines, the nineteen names all `logic`.
- `--print-argv` of six calls byte-equal to the 38-17 tip; `tests.test_arch_hardcoded_models`, `tests.test_runner_describe`,
  `tests.test_ai_kit_spec_runtimes_table` and `tests.test_runner_status_group` pass; detection.py, error_classifier.py and the model-literal baseline
  unchanged; runner and sibling diffs reviewed against the plan. Shards and wave gates: see the ledger (c38-5, waves 11-13).

## Deviations

- `executeFindings` takes six parameters (action step 4 and the Artifacts); the acceptance grep's five-parameter text matches as a prefix.
- `parseCommitLog` sits at the head of the runner's export list and the sibling's import instead of its sorted place (cosmetic, open for code
  review).
- The plan's `selftest.sh` (bare `node` under a scratch HOME, the Volta-shim fork hazard) was replaced by `tmp/run-2026-11-19/p38-18/selftest.py`.
- One commit for all three tasks (the chunk's lane prompt) instead of one per task.
