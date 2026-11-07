---
phase: 30-phase-boundary-index-refresh-code-exploration-rules-and-lens
plan: 05
subsystem: tooling
tags: [advisor, codegraph, hooks, setup-dev, makefile, installer]
status: complete
requires:
  - phase: 30-01
    provides: post-checkout ai-kit-index hook in .pre-commit-config.yaml, scope.py rails
  - phase: 30-02
    provides: RULE_CLAUSES in skills/_shared/ai_kit_rules_common/code_exploration.py
  - phase: 30-03
    provides: tool-advisor hook row in tools/setup.py
provides:
  - codegraph-search advice id and CODEGRAPH_LINE in the tool advisor
  - indexed_checkout, _markdown_only, codegraph_advice in tools/hooks/advisor_core.py
  - tools/setup_dev.py guarded installer and `make setup-dev` target
affects: [30-06, hook-registry, setup-dev docs]
tech-stack:
  added: []
  patterns: [guarded installer steps with a fail-open exit, git common dir lock]
key-files:
  created:
    - tools/setup_dev.py
    - tests/test_setup_dev.py
  modified:
    - tools/hooks/advisor_core.py
    - tools/setup.py
    - tests/test_tool_advisor_core.py
    - tests/test_hook_registry.py
    - tests/test_hook_registry_e2e.py
    - Makefile
    - README.md
    - .pre-commit-config.yaml
decisions:
  - "setup-dev keeps no failure state: each run re-probes PATH and retries only the tools still missing (jev choice a, see jev log)"
  - "codegraph presence is read through installed_tools (PATH lookup only), so the advisor still starts no process"
  - "Markdown-only classification: positive filters decide when present, a negated glob never counts, path scopes decide otherwise"
metrics:
  duration: "about 1h (first run, wall clock); continuation duration not measured precisely"
  completed: 2026-11-05
  tasks: 2
  files: 12
commits: 1
plan_head_before: a0e7e3cc4aa7c8ddae6e6241ca097ecf62887970
plan_head_after: 010790f2b532c4858ca7c423fa78b1cabde47c88
actuals:
  tokens: 14103
  tasks: 2
  commits: 3
requirements-completed: [FLOW-06, FLOW-13]
---

# Phase 30 Plan 05: Codegraph search advice and `make setup-dev` Summary

Code searches in a codegraph-indexed checkout now get one rate-limited codegraph line from the tool advisor (Bash rg/grep/find, Claude Grep and Glob), and `make setup-dev` installs the missing flow tools and the hooks through guarded steps that always exit 0.

## Performance

- **Tasks:** 2 of 2 complete (first run); gap closure in the continuation run
- **Commits:** 3 in total across both runs (5561780, 6d018b3 from the first run; 010790f from the continuation). This continuation's count, measured with `git rev-list --count a0e7e3c..HEAD` before the SUMMARY commit, is 1.
- **Test run:** `scope.py test` (one `make test`) run in the continuation; result in Self-Check below.

## Accomplishments

- Advisor: `codegraph-search` advice for rg, grep and find over code, Claude Grep and Glob, when the checkout holds `.codegraph/` and the codegraph CLI is on PATH. Markdown-only searches, unindexed checkouts and nested unindexed worktrees get none. Reminder events never get it. Frequency is first, then every tenth, through the existing per-session state and call-key dedupe.
- Hook matcher widened to `Bash|Read|Grep|Glob` through setup's table; registry pins updated.
- `tools/setup_dev.py`: `uv sync`, then pre-commit, gh, gh-stack, codegraph and graphify (missing tools only, in dependency order), then `uv run pre-commit install`. Each step reports success, a skip, or a failure with its manual command. Timeouts and OSErrors are reported, not raised. One lock under the git common dir. Install argv are fixed lists; none uses sudo or a shell. Unverified commands are labelled `[unverified command]`.
- `Makefile` `setup-dev` target has no prerequisite and one recipe line. `dev` and `setup-env` are unchanged.
- README: `make setup-dev` line, and the tool-advisor row now names code searches.

## Gaps closed in the continuation (commit 010790f)

Each item below was listed under "Not done" in the first run's summary; the test names are in `tests/test_setup_dev.py` and `tests/test_tool_advisor_core.py`.

1. **Two `setup_dev.py` runs at once** (`TestSetupDevRealProcesses.test_two_runs_at_once_install_each_tool_once_under_one_lock`): two real `python3 tools/setup_dev.py` processes, both started with `Popen` and then waited, in one temp repo with fake `uv`, `brew` and `pnpm` executables on a scratch PATH. Each of the five installs appears once in the fake log in total, both runs exit 0, and `ai-kit-setup-dev.lock` exists in the repo's git common dir.
2. **Read-only git common dir** (`TestSetupDevGuardedSteps.test_unopenable_lock_is_noted_and_every_later_step_still_runs`): the `.git` directory is made `0o555`; the output holds exactly one `note: setup-dev lock unavailable (<reason>); running without it` line, every later step runs (`env: synced`, `hooks: installed`, tool installs), and the exit code is 0. The test skips only when run as root, since root bypasses the permission.
3. **2 x 20 threaded advise count** (`TestCodegraphSearchAdvice.test_two_threads_share_the_frequency_count`): two threads each call `advise` 20 times in one session; the number of shown results equals the count from 40 sequential calls in another session (4, on calls 1, 11, 21, 31).
4. **Real-subprocess run with fake gh/brew executables** (`TestSetupDevRealProcesses.test_fake_executables_install_gh_and_gh_stack_in_one_real_run`): `gh` is absent until the fake `brew install gh` copies a fake into the bin; the fake `gh extension install` records the extension so `gh extension list` reports `gh-stack`; the run reports `gh: installed (brew install gh) [unverified command]`, `gh-stack: installed`, and `setup-dev: 5 installed, 0 present, 0 need a manual step`.

No code fix was needed: all four new tests passed on their first run, so no `fix(30-05)` commit was made.

## Task Commits

1. **Task 1: codegraph search advice end to end through the hook** - `5561780` (feat)
2. **Task 2: `make setup-dev` guarded installs** - `6d018b3` (feat; its first attempt was blocked by ruff, pylint and the arch rule, fixed and re-run, no `--no-verify`)
3. **Gap tests (continuation)** - `010790f` (test; its first attempt was blocked by ruff B905 `zip()` without `strict=`, fixed and re-run, no `--no-verify`)

## Files Created/Modified

- `tools/hooks/advisor_core.py` - CODEGRAPH_LINE, `indexed_checkout`, `_search_scope`, `_markdown_only`, `codegraph_advice`, cwd/pattern/search path/glob/type mapping
- `tools/setup.py` - tool-advisor matcher
- `tools/setup_dev.py` - new installer
- `tests/test_tool_advisor_core.py` - `TestCodegraphSearchAdvice`, including the threaded count
- `tests/test_setup_dev.py` - new, fake installers only (injected runner and real processes with fake executables)
- `tests/test_hook_registry.py`, `tests/test_hook_registry_e2e.py` - matcher pins
- `Makefile`, `.pre-commit-config.yaml` (generated test listings), `README.md`

## Decisions Made

- No persisted failure state for setup-dev (jev choice a). A failed tool is retried on the next run because each run re-probes PATH.
- `codegraph_advice(event, installed)` takes the installed set rather than the plan's one-argument form. `installed_tools` adds `codegraph` when it is on PATH (a `shutil.which` check, no subprocess).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Narrowed the setup-dev safety net**
- **Found during:** Task 2 commit
- **Issue:** `main` caught `Exception`; `tests/test_arch.py` rule 9 allows broad excepts only in listed backstops.
- **Fix:** `main` catches `(OSError, ValueError, subprocess.SubprocessError)`. Every installer and probe step already converts its own failures to report lines inside `run`, so the exit-0 contract holds for the failure modes the plan lists.
- **Commit:** 6d018b3

**2. [Rule 3 - Blocking] Lint fixes in setup_dev.py**
- **Found during:** Task 2 commit (ruff E501, SIM115; pylint line-too-long, consider-using-with)
- **Fix:** shortened the gh manual string; the lock uses `os.open` with an explicit `os.close`.
- **Commit:** 6d018b3

**3. [Rule 3 - Blocking] Lint fix in the new concurrency test**
- **Found during:** Continuation commit 010790f (ruff B905)
- **Fix:** `zip(..., strict=True)` in `test_two_runs_at_once_install_each_tool_once_under_one_lock`.
- **Commit:** 010790f

### Gaps not closed (plan does not require them)

- Pi grep/glob mapping: `event_from_pi` keeps `cwd`, but pi grep/glob inputs are not mapped to search events, so pi gets no codegraph line for those tools. The plan's action list only maps `cwd` for pi, so this stays as built. reported (not this run): pi grep/glob search mapping.

## Issues Encountered

- First Task 2 commit attempt was blocked by lint (ruff, pylint) and the arch rule. Fixed in the working tree and retried; hooks ran in full each time. No `--no-verify`.
- First gap-test commit attempt was blocked by ruff B905. Fixed and retried; no `--no-verify`.

## Next Phase Readiness

- The owner check below is still open.

## jev call log

- First run: `jev-fast-decision` ladder, 1 call. Question: keep no failure state in setup-dev, or persist failed tools. Result: choice `a` (no failure state), decided by typesafe (top 1.0), laya fallback. Used as advice; the plan's design was kept.
- Continuation: 0 calls. The gap closure had no classify or decide step; every expected value came from the plan's behavior list.

## Owner check (not run)

`make setup-dev` was NOT run against this machine (it has all five tools). The install commands in `tools/setup_dev.py` TOOLS, to confirm before a fresh-machine run:

- `uv tool install pre-commit`
- `brew install gh` (unverified on this machine: gh is a user-local tarball here)
- `gh extension install github/gh-stack`
- `pnpm add -g @colbymchenry/codegraph` (unverified; `npm` is banned here)
- `uv tool install graphifyy`

## Self-Check

- Commits `5561780`, `6d018b3` (first run) and `010790f` (continuation) are on `worktree-agent-afd0cd8f020eec3fd`.
- `tools/setup_dev.py`, `tests/test_setup_dev.py`, and the advisor and README edits are in those commits; the continuation adds only the two test modules.
- Focused suites green in the continuation: `tests.test_setup_dev` (10 tests), `tests.test_tool_advisor_core` (23 tests), `tests.test_arch` (103 tests, staged-tests hook).
- `make pyright` passed in the continuation (run before the commit).
- Every "Gaps closed" item above has a named test that passes.
- `scope.py test` (one `make test`, continuation) exited 0: unit 94/94 modules, arch 1/1, wizard 6/6, e2e 25/25 (`tests.test_setup_dev` 10 tests, `tests.test_tool_advisor_core` 23 tests, `tests.test_flow_index_e2e` 4 tests included).

## Self-Check: PASSED

## Run-close reported lines (not this run)

Continuation `scope.py close` (printed `clean`; these are other sessions' processes, the main checkout and other worktrees, and one older run's temp dir):

- reported (not this run): process (other worktree): pid 6079 cwd /var/home/bazzite/git/personal/ai-kit: /home/linuxbrew/.linuxbrew/bin/zsh
- reported (not this run): process (other worktree): pid 6578 cwd /var/home/bazzite/git/personal/ai-kit: /home/linuxbrew/.linuxbrew/bin/zsh
- reported (not this run): process (other worktree): pid 1834804 cwd /var/home/bazzite/git/personal/ai-kit/.claude/worktrees/v13-curated-config-v2 (deleted): node -e process.stdout.write(process.execPath)
- reported (not this run): process (other worktree): pid 1922019 cwd /var/home/bazzite/git/personal/ai-kit: claude --dangerously-skip-permissions
- reported (not this run): process (other worktree): pid 1922292 cwd /var/home/bazzite/git/personal/ai-kit: /var/home/bazzite/.codegraph/versions/v1.6.2/node --liftoff-only --disable-warning=ExperimentalWarning /var/home/bazzite
- reported (not this run): process (other worktree): pid 2452893 cwd /var/home/bazzite/git/personal/ai-kit/tmp/wt-301: /var/home/bazzite/.codegraph/versions/v1.6.2/node --liftoff-only --disable-warning=ExperimentalWarning /var/home/bazzite
- reported (not this run): process (other worktree): pid 2522299 cwd /var/home/bazzite/git/personal/ai-kit: /bin/bash -c source /home/bazzite/.claude/shell-snapshots/snapshot-bash-1793659154621-wcxvtw.sh 2>/dev/null || true && e
- reported (not this run): process (other worktree): pid 2888315 cwd /var/home/bazzite/git/personal/ai-kit/tmp/wt-301: /var/home/bazzite/.codegraph/versions/v1.6.2/node --liftoff-only --disable-warning=ExperimentalWarning /var/home/bazzite
- reported (not this run): process (other worktree): pid 3121017 cwd /var/home/bazzite/git/personal/ai-kit: /home/linuxbrew/.linuxbrew/bin/zsh
- reported (not this run): process (other worktree): pid 3423848 cwd /var/home/bazzite/git/personal/ai-kit/tmp/compact-291: /bin/bash -c source /home/bazzite/.claude/shell-snapshots/snapshot-bash-1793659154621-wcxvtw.sh 2>/dev/null || true && s
- reported (not this run): process (other worktree): pid 3615075 cwd /var/home/bazzite/git/personal/ai-kit: /bin/bash -c source /home/bazzite/.claude/shell-snapshots/snapshot-bash-1793659154621-wcxvtw.sh 2>/dev/null || true && e
- reported (not this run): process (other worktree): pid 3615076 cwd /var/home/bazzite/git/personal/ai-kit: bash /var/home/bazzite/git/personal/ai-kit/tmp/phase30-exec/watch_commits.sh 30-04c:worktree-agent-a5613d5ffd519c5a7 30-
- reported (not this run): process (other worktree): pid 3772706 cwd /var/home/bazzite/git/personal/ai-kit: sleep 30
- reported (not this run): process (other worktree): pid 3774070 cwd /var/home/bazzite/git/personal/ai-kit: sleep 3
- reported (not this run): process (other worktree): pid 3774073 cwd /var/home/bazzite/git/personal/ai-kit/tmp/compact-291: sleep 3
- reported (not this run): process (other worktree): pid 3774292 cwd /var/home/bazzite/git/personal/ai-kit/.claude/worktrees/agent-a5613d5ffd519c5a7: /bin/bash -c source /home/bazzite/.claude/shell-snapshots/snapshot-bash-1793659154621-wcxvtw.sh 2>/dev/null || true && e
- reported (not this run): process (other worktree): pid 3774293 cwd /var/home/bazzite/git/personal/ai-kit/.claude/worktrees/agent-a5613d5ffd519c5a7: /var/home/bazzite/git/personal/ai-kit/.claude/worktrees/agent-a5613d5ffd519c5a7/.venv/bin/python /var/home/bazzite/git/p
- reported (not this run): process (other worktree): pid 3774332 cwd /var/home/bazzite/git/personal/ai-kit/.claude/worktrees/agent-afd0cd8f020eec3fd: /bin/bash -c source /home/bazzite/.claude/shell-snapshots/snapshot-bash-1793659154621-wcxvtw.sh 2>/dev/null || true && e (this run's own shell wrapper, used for close; not a leftover)
- reported (not this run): process (other worktree): pid 3774333 cwd /var/home/bazzite/git/personal/ai-kit/.claude/worktrees/agent-afd0cd8f020eec3fd: python3 /var/home/bazzite/git/personal/ai-kit/.claude/worktrees/agent-afd0cd8f020eec3fd/tmp/p30/05/scope.py close (this run's close process; not a leftover)
- reported (not this run): temp (other run): /tmp/ai-kit-p30-run-04-0b3d2bb6

These lines are from other sessions and worktrees. They are left alone, not counted as leftovers of this run:

- pid 3484859, 3484869, 3484892, 3487494 (agent-ad057836d2675491d: shell, commit, pre-commit hook, staged tests)
- pid 3558827, 3558830, 3558834, 3558835 (agent-ad057836d2675491d: unit runner)
- pid 3559076, 3559683 (`sleep` in the main checkout)
- pid 3559877 (`sleep` in tmp/compact-291)
- pi grep/glob search mapping is not in this plan's action list; left as built (see Gaps not closed).
