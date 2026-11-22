---
phase: 38-runner-hardening-and-run-safety
reviewed: 2026-11-22T10:05:00Z
reviewed_head: 0e21f5a
diff_range: "42bad13..0e21f5a (excluding .planning, tests/fixtures/cli_help, tests/fixtures/cross_ai_selftest_secs.json)"
depth: standard (deep on the phase-38 runner blocks and the curated-config skill check; the moved self-test harness read only for its new cases)
files_reviewed: 75
findings:
  critical: 0
  high: 0
  medium: 12
  low: 16
  info: 10
  total: 38
fixed: 20
deferred: 7
kept: 1
status: fixed_or_tracked
---

# Phase 38 code review

Two passes over `42bad13..0e21f5a`: a `gsd-code-reviewer` pass over the whole phase diff (the phase-38 runner blocks read
around every change, Python as diffs, docs against code, added-line scans), and the review list carried by the run ledger
and the plan summaries, each item checked in the code by the review executor. The reviewer's time box left out the
`tests/test_arch.py`, `tests/test_cross_ai_render_sync.py`, `tests/test_curated_config_e2e.py` and
`tests/test_curated_config_plan_edit.py` hunks and the curated-config SKILL.md, `references/runner.md` and superpowers
SKILL.md hunks; the executor read them afterwards: the new arch rules carry non-vacuity cases, the plan-edit refusal tests
moved to the "runs at apply" note as 38-27 locked (apply-level refusal tests remain in `tests/test_curated_config_apply.py`
and the real gsd-core cases in `tests/test_curated_config_e2e.py`), and the doc hunks match the code except the items
below. The restored gsd-core line references were checked against `.claude/gsd-core/bin/lib/gate-evaluation-scope.cjs`
(113-119, 126-134, 145-148, 760-768, 787-803). Fixes went in as neutral-scope `fix(38)`
commits with their tests (hooks ran on each, never skipped); the eight new harness cases went through the cross-AI lane
(pi, router-env/my-coding, one lane, `8f5ae00`). The shas below are pre-fold; the review checkpoint folds them into one
commit. Deferred items are tracked in `.planning/todos/pending/2026-11-22-review-notes-left-open-by-phase-38.md`.

Two judged skills changed after loop 38 round 1 (`ai-kit-cross-ai`, `ai-kit-gsd-curated-config`): each change is recorded
in that skill's `fixes.md` beside loop 38 round 1, and both digests stay stale by design until their next loop. The template
changes made the live runner copy stale; it was re-rendered through `ensure-runner` (dry run first) in `03e32b4`, and
`make check-dogfood` ends `check-dogfood: ok`. `--print-argv` for six lanes (pi exec/review, opencode exec, codex exec with
the sandbox flag, claude review, pi with `--idle-timeout 30`) is byte-equal to `0e21f5a`.

Tests run on the fixes: each commit's hook (132/132, 31/31, 143/143, 132/132 in the lane, 139/139, 195/195 with the full
unit and arch groups, 194/194 full); then, one module at a time under the guard, the deferred e2e set at `03e32b4`: runner
e2e 28, render sync 11, describe 17, host protocol 13, runner dispatch 80, skill text 30, docs text 17, settings text 23,
skill text history 45, staged mapper 74, the 12 self-test shards (logic 31-32 s, runtime 37-38 s), curated-config e2e 21,
apply e2e 8 and the curated-config matrix 34 (240 s), all ok; unit-uv 3/3 and integration 9/9; `make ruff pylint pyright
vulture` clean.

## Medium

### MEDIUM-1: the automatic sweep deleted the pid file of a live launcher its runner never adopted (fixed, 569a4ed)

A runner killed after its launcher wrote `pid` but before the first poll recorded `launcher_pgid` left a record with a null
group. The next execute run's sweep (before the lock) claimed that directory, removed `pid` and closed the tab, so the lock
then read the run as stale while the `setsid` launcher kept editing. The sweep now counts such a run as `live launcher` when
its `pid` file names a live process leading its own group (the test `hostedLaunchAlive` already used, now one helper
`pidFileLauncherAlive`). New case `sweep-pid-file-live`.

### MEDIUM-2: `CONFIG.forbiddenPaths` and `CONFIG.admissionPhrases` were unchecked and documented as shipped keys (fixed, 569a4ed, 25a9229)

A string or number there threw after the lane had committed (a finished run ended `crash`), and the docs said both keys
sit in the shipped CONFIG with defaults. `configList` now uses a CONFIG value only as a list of strings and otherwise prints
`cross-ai: note: CONFIG.<key> is not a list of strings; the seed list is used`; ai-kit-cross-ai SKILL.md and curated-config
`references/runner.md` say both keys are optional and absent from the shipped block. New case `plan-config-seed-bad`
(both notes once, the seed's forbidden path still gives `contract_violation`).

### MEDIUM-3: a host failure that reran headless left the hosted fields in the lock record (fixed, 569a4ed)

After `tab create` the lock record carried `token`, `tab_id` and `host_ms`; a definite `pane run` failure reran the lane
headless with those fields kept, so a refusal could print the hosted line for a headless lane. The rerun now clears them
(only when `rerun` is true; an unclear start keeps them). New case `host-rerun-lock-fields`.

### MEDIUM-4: the `no_tree_change` finding and the failed-read note were recorded once per attempt (fixed, 569a4ed)

Both flags lived in the per-attempt poll state, so a ladder retry could print the finding twice. They are now once per run
(`noTreeChangeNoted`, `pollFailNoted`). New case `poll-notes-once-per-run` (two attempts, a notice per attempt, one finding).

### MEDIUM-5: the fail-closed branch of the execute check had no test (fixed, 8f5ae00)

The harness git wrapper could fail only `write-tree`. It now fails any verb named by a `.fake-git-fail-<verb>` file in the
case HOME (skipping a leading `-c` pair), with the exit code the file holds. New cases `plan-git-log-fails`,
`plan-git-show-fails`, `plan-git-diff-tree-fails`: each ends `git_error` with `cross-ai: git <verb> failed reading the work
tree (fail closed)`, no finding line and empty stdout.

### MEDIUM-6: no test covered a baseline record kept when git cannot check it (fixed, 8f5ae00)

New cases `baseline-kept-unchecked` (`cat-file` exits 2) and `baseline-kept-ancestry` (`merge-base` exits 2 after HEAD
moved): one note each, no `baseline_replaced`, and the record survives the ok run byte-for-byte.

### MEDIUM-7: the model-literal guard was not selected at commit for a self-test-only change (fixed, 94753d9)

The 38-13 fold alone failed `tests.test_arch_hardcoded_models` (green from 9a64d4b) because the guard walks the tree and
an `.mjs`-only commit set no arch flag. The staged mapper now lists the guard in `SKILLS_TREE_WALKERS`, so any staged file
under skills/ selects it; `tests/test_staged_mapper.py` pins it for the harness file.

### MEDIUM-8: a gsd-core warning that sanitized to nothing read as "resolves" (fixed, a933d91)

`_parse_verdicts` returned `""` for such a warning, which callers read as a resolved skill. An empty sanitized cause is now
`skipped`; `test_cause_empty_after_sanitizing_is_still_skipped` covers an empty string, control characters only and a bare
gsd-core wrapper.

### MEDIUM-9: `hostPairReset` ran `git checkout -- .` and `git clean -f` with no path guard (fixed, 569a4ed)

The reset now calls `assertScratchRepo(tmp, c.repo)`: the repository must sit strictly under the self-test root and hold its
own `.git` (a custom TMPDIR inside a repository cannot let git walk up). New pure case `pure-scratch-repo-guard`.

### MEDIUM-10: curated-config said `plan-unset` refuses a declined root (fixed, 25a9229)

Since 38-27 `plan-unset` only prints a note; `apply` and `apply --dry-run` refuse. Fixed in the "Refusal → action" bullet
and in the trusted-roots step (SKILL.md:144, the same stale claim, found by the review).

### MEDIUM-11: the idle watchdog's list of call endings was incomplete (fixed, 25a9229)

Traced: a timed-out attempt is a soft transient (`ladderClass`), so the ladder ends in the hard handler (75 with
`retry_after_s=`, a bare 75 when the state is unwritable, or 69), or `timeout` 124 with no budget; but an execute lane whose
fresh retry meets a changed tree stops with a bare 75 (`why=dirty-tree`), and an unreadable tree there gives
`git_error`/`git_timeout`. The SKILL sentence now names both.

### MEDIUM-12: `workspace-write` was described as a fixed allowlist (fixed, 569a4ed, 25a9229, 03e32b4)

It is Codex's sandbox mode: by default the target dir plus `/tmp` and `$TMPDIR`, and the owner's Codex config can add or
exclude writable roots. Fixed in the runner header and the `codexExecArgv` comment (the second site, found by the review),
`references/cli-profiles/codex.md` and superpowers `references/design-notes.md`; the live copy was re-rendered.

## Low

Fixed:
- LOW-1 (5db3e4e): a failed cut of a hosted output file reset the offset anyway, so every poll re-read and re-relayed the
  file and the hosted idle clock could never fire. A failed cut now keeps the offset and is not retried. No harness case: an
  `ftruncate` failure on the runner's own descriptor cannot be produced by the fakes.
- LOW-2 (569a4ed): the seed and port comments shortened by lanes are restored to the plans' source labels (the D-14
  document path and its 2026-11-16 verification date, the D-13 provenance, the gsd-core `gate-evaluation-scope.cjs` line
  references for `planSubjectRe`, `parseCommitLog` and `commitPaths`, checked against `.claude/gsd-core`).
- LOW-3 (569a4ed): `parseCommitLog` sits at its sorted place in the export list and the harness import.
- LOW-4 (25a9229): the 38-24 doc test reads every file with `encoding="utf-8"`.
- LOW-5 (94753d9): the `cross_ai_selftest.py` comment said a shard takes about 25 s; it now says 35 to 45 s (38-25).
- LOW-6 (5db3e4e): ai-kit-cross-ai SKILL.md Pitfalls now say an uncreatable lock record does not stop the run
  (`cross-ai: run lock not taken (<code>); running without a lock`).
- LOW-7 (5db3e4e): superpowers `references/dispatch-external-cli.md` now says a 69/75 with no token or one token is the
  `quota` owner stop, as `dispatch_classification` does.
- LOW-11 (77ebda5, after the phase verification): the state-home exclusion was computed against the cwd, so a runner
  started in a subdirectory snapshotted a state home elsewhere in the checkout. `stateExclude` now resolves it against the
  checkout top (the lock's root) and passes `:(top,exclude,literal)<path>` to `git add`; new self-test cases start in a
  subdirectory (no-op, planned execute, idle watchdog, hosted pair) and fail on the previous template.

Deferred (todo file):
- LOW-8: curated-config `apply` does not compare its writes with the approved preview. Binding them needs a stored digest
  of the planned writes in the plan, a plan-format design decision outside 38-06's design (the gsd-core skill check); the
  skill already tells the agent to rerun the dry run first.
- LOW-9: `router_statement` confirms on an owner-confirmed `is_router` with an unconfirmed `fallback_quota` heuristic; D-17
  keys the rule on `fallback_quota` with its label. Owner decision before any change.
- LOW-10: `parseTasks` counts every non-checkpoint type (a planning decision); SPEC R5/D-12 name absent, `auto`, `tdd` and
  `tracer`. Amend the SPEC or narrow the code.
- LOW-12: after three lost lock rounds the refusal names `pid -`.
- LOW-13: `lockVerdict`'s `own` branch is unreachable.
- LOW-14: the admission seed phrase `remaining work` also matches "no remaining work".
- LOW-15: the staged mapper still misses a staged non-Python file under tools/, tests/ or docs/ that the model-literal
  guard scans (push stage covers it).

Kept:
- LOW-16: the curated-config and superpowers SKILL.md lines past 100 columns (superpowers :263, three 38-24 lines): both
  files have no wrap rule and dozens of longer lines; tracked in the todo with that reason.

## Info (checked, no change)

- `hostPairCheck` normalises only the measured seconds of a `no_tree_change` detail, for every hosted pair: the finding's
  presence and text are still compared, and the seconds are wall-clock like `elapsed=`, so no pair loses a real assertion.
- The e500022 HOME handling holds: the skill check runs under the inventory's HOME, and gsd-core's global skills dir is
  compared with the one inventory recorded (`expect`), so a custom `CLAUDE_CONFIG_DIR` that differs between inventory and
  apply gives a named note, never a verdict from another home; an inventory without `home` keeps apply's env, still guarded
  by `expect` for `global:` references.
- `--baseline` takes `<sha>^{commit}` and `^{tree}` before the lock (a bad value is a usage error with no lock); every tree
  read uses a private `GIT_INDEX_FILE` in a temp dir, so the user's `.git/index` is never written (`baseline-owner-dirty`
  compares its bytes).
- Lock, baseline and run records are written with `wx` or a temp file and rename, mode 0600 in a 0700 directory; every
  printed record value goes through `redactSecrets` and control-character removal.
- The sweep signals no process at all: it removes a dead run's directory and closes only a tab whose id and complete label
  match; a live launcher (now also one known only by its pid file) is kept.
- `RUN-13` stays complete: its SPEC acceptance text (R12, lines 517-529) is a list of fake-herdr tests, and each clause maps
  to a case (`sweep-sigkill-e2e`, `sweep-foreign-safe`, `sweep-down`, `sweep-host-none`, `sweep-live-untouched`,
  `sweep-race`, `sweep-unreadable`, `host-idle-silent`, `host-idle-busy`, `host-idle-commits`, `host-state-in-checkout`,
  `host-cap`, `host-key-scan`, `host-findings-partial`, `host-lock-live-group`, `runner_describe`, `host-no-herdr`); the
  SPEC keeps a live probe out of the test suite. The live real-herdr sweep of 38-26 part (1) stays an owner item.
- Node: no phase-38 product spawn of a PATH `node` (the skill check goes through `detection.bounded_run`, which is
  `run_in_own_group`); the phase-38 tests take node from `_real_node_executable()`.
- Generic: no added line names grok (`scan: ok`), no machine path in source or tests, runtime Python adds stdlib imports
  only, no new config writer, no secret printed; README/SKILL/reference text for `--idle-timeout`, `--baseline`,
  `--plan-id`, `--forbid`, `--sweep`, `locked`, `partial` and the finding codes matches the code after MEDIUM-2, -10, -11.
- `STATE.md` shows "Plan: 28 of 28" (stale counter, note only).
- The fold subject `fix(38-26): 38-26` and the two unfolded neutral commits under 38-25 are history wording for the later
  compaction step.

---

_Reviewed: 2026-11-22_
_Reviewers: Claude (gsd-code-reviewer) and the phase 38 review executor_
