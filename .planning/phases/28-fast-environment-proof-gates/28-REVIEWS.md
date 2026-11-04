---
phase: 28
cycle: 3
reviewers: [referee-one, referee-two, referee-three]
reviewed_at: 2026-11-03T20:21:21-03:00
plans_reviewed: [28-01-PLAN.md, 28-02-PLAN.md, 28-03-PLAN.md, 28-04-PLAN.md, 28-05-PLAN.md, 28-06-PLAN.md, 28-07-PLAN.md, 28-08-PLAN.md, 28-09-PLAN.md]
models:
  referee-one: "router-env/my-referee-one"
  referee-two: "router-env/my-referee-two"
  referee-three: "router-env/my-referee-three"
model_sources:
  referee-one: "pinned"
  referee-two: "pinned"
  referee-three: "pinned"
---

# Cross-AI Plan Review — Phase 28

<!-- gsd:plan-revision-conflicts:begin -->
## Plan-Revision Conflicts
<!-- gsd:plan-revision-conflicts:end -->

> Note: referee-one, referee-two and referee-three share the opencode adapter; their consensus is cross-model, not cross-tool.

## Review conditions

Cycle 3 (the last), over the nine plans at `59087b2` (revised at `e06127c` and `59087b2` after cycle 2's
REVIEWS.md at `3bcb78b`). `/gsd-review --phase 28` ran the three configured reviewer instances
(`review.default_reviewers`) through the opencode lane concurrently (`review.parallel_lanes: true`), 20:19 to
20:21 local time. The prompt (427 KB) inlined PROJECT.md (first 80 lines), the ROADMAP Phase 28 section,
GATE-01..05, 28-CONTEXT.md, 28-RESEARCH.md and all nine plans (each with its Round 1 and Round 2
`## Review Dispositions Ledger`), with the source-grounding instructions and the plan coverage manifest; the
reviewers were told the review is read-only.

- **referee-one** (`router-env/my-referee-one`): **failed.** The lane returned the empty-output stub after 5 s
  (opencode exit 1). Four direct probes (20:20, 20:22, 20:24, 20:26) print
  `Error: Combo has no executable targets`: the router combo has no target available, a route-quota condition,
  not a CLI fault. Per the owner rule no other model was substituted.
- **referee-two** (`router-env/my-referee-two`): **failed again**, as in its probe and cycles 1 and 2. Empty-output
  stub after 90 s; a direct probe prints `Error: Model grok-cli/grok-4.7-xhigh is unavailable`. No substitute.
- **referee-three** (`router-env/my-referee-three`): ran, 100 s, full review of all nine plan ids, with `file:line`
  evidence and one live `git rev-list` probe. Its section does not open with a discount marker. One zero-width
  joiner (U+200D) inside a file name in its text was removed when this file was assembled; nothing else changed.

Only one reviewer produced a review, so the consensus gate does not apply this cycle: every HIGH it raises counts.
The orchestrator checked every existence claim it makes against the source (marked below).

## OpenCode Review (referee-one)

opencode review failed or returned empty output. stderr:

Raw response body:
OpenCode review returned no assistant text (#1936: agent ended its turn with no final message).
Diagnostic: stop reason=?, output tokens=?
Diagnosis: opencode ran with no effort argument, so the reviewer CLI's own configuration applied and exited with status 1.

---

## OpenCode Review (referee-two)

opencode review failed or returned empty output. stderr:

Raw response body:
OpenCode review returned no assistant text (#1936: agent ended its turn with no final message).
Diagnostic: stop reason=?, output tokens=?
Diagnosis: opencode ran with no effort argument, so the reviewer CLI's own configuration applied and exited with status 1.

---

## OpenCode Review (referee-three)

I'll check the key claims against the source, then give one section per plan.
### Cross-AI plan review: Phase 28 (fast, environment-proof gates)

I read the repo directly. I checked these claims against source: `tools/run_unittest_parallel.py`, `.pre-commit-config.yaml`, `detection.py`, `gp_host.py`, `tests/gsd_curated_eval.py`, the matrix module, `cross-ai.mjs`, pre-commit's `hook_impl.py`, `tests/test_cursor_status_line.py`, and this checkout's git refs. Most of the plans' code facts hold up. I found one new **HIGH** issue: the fast path of 28-07's push-range proof can never be taken in this checkout (see 28-07).

#### 28-01

**Summary.** This plan adds a tripwire folder of host-CLI stubs and a baseline environment for every test module. The design fits the runner well:
- `run_module` already makes a per-module temp folder and sets TMPDIR in its env copy (`tools/run_unittest_parallel.py:145-159`), so both changes slot in there.
- The fakes target the real callers (`gp_host.py:112-115,153-156` look hosts up with `seams.which`).
- The plan notices that the stubs make every host look installed to `shutil.which`, so detection results change (case f).

**Strengths**
- The log path is written into each stub when it is created, so a test that rebuilds its env from scratch can't lose it (case d).
- The output is capped at 20 lines.
- `HOST_SIGNAL_ENV_VARS` really is the composed frozenset at `detection.py:224-228`. Copying it and adding a drift test is the correct choice, because the runner should not import a skill module.
- `tool_cache_forwards` is one public helper that 28-08 and 28-09 reuse. This removes the earlier divergence between three copies.

**Concerns**
- **MEDIUM:** The DriftTest scanner reads every `_KEY/_TOKEN/_URL/...` string constant in `tools/` and `skills/`. On first run it will likely produce many hits that are not env vars (dict keys, JSON field names), each needing a hand decision. The work is real but unbounded in the estimate.
- **MEDIUM:** Case (f) changes what modules see: any test that today asserts "host absent" without setting its own PATH will now fail with no `tripwire:` block. The plan defers finding these to 28-02 Task 3. That is fine, but 28-01's own verify list never runs the detection-heavy modules (`test_ai_kit_spec*`, `test_ai_kit_session_wake*`), so this breakage surfaces only in wave 2.
- **LOW:** A `GIT_CEILING_DIRECTORIES` set to the parent of `temp_dir` blocks discovery above that point. Any test that does `git init` deeper inside `temp_dir` is unaffected; this is fine as designed.

**Suggestions**
- Have Task 2 print the scan hits in a stable sorted list in the summary, so the reviewer can audit each kept/dropped decision quickly.
- Add one or two detection-heavy modules to the Task 1 verify command, so host-presence breakage shows up early.

**Risk:** MEDIUM. The approach is correct; the unknown is how many modules the baseline breaks, which 28-02 Task 3 absorbs.

#### 28-02

**Summary.** This plan load-scales the self-test ceilings, sizes the Python guards from one shared reading, gives the self-test module a longer runner deadline, and makes process-group stops graceful.
- The counts in the plan match the source: `rg -ci "elapsed\w*\s*>=?\s*\d"` gives **16** and `withinMs: 2900` gives **5**.
- Case runners are spawned `detached: true` (`cross-ai.mjs:5275`) and reaped only by `selfTestAbort` (`:5466`), which runs on SIGTERM, SIGINT and SIGHUP (`:3676`). So the "SIGTERM first, then SIGKILL" design is genuinely needed.

**Strengths**
- The guard's load reading is passed to Node through `AIKIT_XAI_SELFTEST_LOAD`, and the test asserts the factor Node prints. This removes the sampling race between the two languages properly.
- The 13 real limits are pinned by name rather than by a broad regex.
- The interrupt path stops new spawns under the same lock that registers a started process. This closes the window between `Popen` and registration.

**Concerns**
- **MEDIUM:** `run_module` switches from `subprocess.run(timeout=)` to `Popen`/`communicate`. That changes how output is captured and joined (`run_module` currently returns stdout and stderr joined). The existing `test_a_hung_module_fails_with_a_timeout_line` covers only the timeout branch, so output ordering is unpinned. Add one assertion on the joined-output shape.
- **MEDIUM:** Task 3 bundles the deadline/process-group refactor, the stress run and the four-tier convergence with all its fix-ups into one task. If convergence uncovers many baseline-env failures, this task balloons (estimate confidence is already "low"). Consider making the convergence its own task so the deadline code commits independently.
- **LOW:** The SIGTERM handler is installed "only when the runner runs as a script in the main thread". The `uv run` child that 28-06 starts is also a script, so it gets the handler too. That is good; it's worth saying explicitly.
- **LOW:** A 5400 s worst-case hold on `make e2e-test` is acknowledged in the plan. This is acceptable.

**Suggestions**
- Split Task 3 into "deadline and process groups" and "stress run plus convergence".
- In `stop_process_group`, log which signal finished the group. That makes later forensics on hung modules cheap.

**Risk:** MEDIUM. The engineering is sound, but there is a lot of process-lifecycle code concentrated in one task.

#### 28-03

**Summary.** Three targeted fixes for tests that depend on the environment. Each one is fixed at its cause:
- the no-git e2e case gets a git ceiling;
- the compose test patches `detect.__file__`;
- the precompact tests get a frozen clock plus in-process fakes, so the 0.2 s budget never reaches a real process.

**Strengths**
- Cloning committed history for the long-path check isolates this plan from 28-01's uncommitted edits in the same wave.
- The frozen clock sits at 0.0, which fixes the float problem (`(1000.0 + 0.2) - 1000.0 = 0.20000000000004547`), and the hung-stub bound (83 s) is stated.

**Concerns**
- **LOW:** Running the frozen-clock mixin on all of `TestCoreEdges` relies on per-test patches overriding the class patch. `mock.patch.object` stacks correctly, so this works; it's fine.
- **LOW:** The Task 1 verify uses `mkdir -p ... &&`, which the plans' own run rules discourage. It is cosmetic.

**Risk:** LOW.

#### 28-04

**Summary.** This plan adds `make check-dogfood`, which reruns the guard tests between fingerprints of the live files. The matrix-module facts in the plan are accurate:
- `tests/test_ai_kit_gsd_curated_config_matrix.py:12,31,33,95,98` import `_REPO_CONFIG` and `_REPO_RUNNER` and call `snapshot(REPO_ROOT…)`.
- `_tree_sha` hashes only the link string for a symlinked root (`tests/gsd_curated_eval.py:258-259`).

So switching to an explicit `_tree_sha(core_root.resolve())` is the right fix.

**Strengths**
- The verdict counts attempted, executed and skipped tests separately, and prints a warning when the apply guard did not run. This avoids claiming coverage that didn't happen, which matches the project's core value.
- `--root` without `--skip-no-write` is refused, so the tool can't fingerprint one checkout while the guard child writes in another.

**Concerns**
- **MEDIUM:** Every push runs real gsd-core node flows, adding wall time. That time is measured in 28-09 (`dogfood=`), but there is no ceiling: a slow gsd-core can quietly make every push longer. Consider a soft notice above some threshold.
- **MEDIUM:** As documented in the plan, the apply guard skips on gsd-core 1.18.0, so in practice `check-dogfood` guards only ensure-project and apply-profile. That gap is honestly stated, but the deferral means it stays open for the whole phase. It belongs in the backlog with a goal statement, not only in the summary.
- **LOW:** `parse_verbose` depends on the unittest verbose format, which differs slightly across 3.12 and 3.14 (for example, docstring first lines appear on their own line). Test both forms.

**Risk:** MEDIUM. The design is correct; the coverage gap is acknowledged.

#### 28-05

**Summary.** This plan moves archived data into frozen fixtures and adds two AST rules: no test builds a path into the repo's `.planning/`, and no test names a host binary as a command. The table of program positions per spawning API is correct, and the `executable=` check closes a real bypass.

**Strengths**
- The first run of the `.planning/` rule is treated as the authoritative list, and the exception dict must end empty.
- Fixtures are stored as `.py.txt` with a header line, so the frozen history passes ruff without being edited.

**Concerns**
- **MEDIUM:** The rule tracks repo-root names by data flow across module, function and class-attribute scopes, plus cwd calls. That is the most complex static rule in the repo, and it will be brittle at the edges, for example tuple unpacking (`ROOT, X = ...`) or roots passed into helpers. The run-time backstop does not exist for this rule: unlike host calls, there is no tripwire for `.planning/` reads. Consider a cheap run-time layer as well: the runner could set cwd to a copy without `.planning/`, or the matrix could run a clone with `.planning/` removed. The plan already deletes `.planning/` in 28-05's dogfood copy, so the pattern exists.
- **LOW:** A `strip_frozen_header` helper "only if needed" leaves the outcome open. That's fine.

**Suggestions**
- Add a run-time guard for `.planning/` reads, as above. In the long-path environment of 28-08, cloning without `.planning/` would turn any reader that escapes the AST rule into a matrix difference.

**Risk:** MEDIUM.

#### 28-06

**Summary.** This plan adds the staged-file to test-module name index, the `--staged` runner mode and the `staged-tests` commit hook. The import-form fix is verified: `tests/test_cursor_status_line.py:35` reaches `common_render` only through `from common_render import ...`. The stage claim is also right: `.pre-commit-config.yaml` sets no `default_stages`, and the existing hooks list `stages` explicitly (lines 37, 43, 63, 72), so an explicit `stages: [pre-commit]` is required.

**Strengths**
- Every failure mode falls back to running more tests, never fewer, including an import error in the mapper itself.
- The staged list is read from `git diff --cached` (with `pass_filenames: false`), so deletions are included and pre-commit can't split the list across processes.
- A real-hook e2e test runs in a temp repo.

**Concerns**
- **MEDIUM:** The e2e test copies the runner, the mapper and the real hook block into a temp repo. After 28-07, the copied runner reaches the uv call and depends on `E2E_RECORDED_SECS` and other tables. Every new constant the runner later validates against the tree (as `stale_machinery_names` already does) means `build_repo` must create more stub files. This scaffolding will churn; centralize it in `build_repo` (28-07 does this).
- **MEDIUM:** The accepted cost is real: each of this plan's two runner commits runs the full unit and arch groups plus roughly 6 minutes of `test_cross_ai_runner_e2e`. That's tolerable, but an executor model may treat a 7-minute pre-commit as a hang. The instruction "run it in the background" needs to sit in the task action, not only in `<context>`.

**Risk:** MEDIUM.

#### 28-07

**Summary.** This plan adds the commit budget, the pre-push `deferred-e2e` hook with its narrowing proof, mapper statistics, and gate-scope pins. The multi-ref analysis is right: `_pre_push_ns` returns on the first ref it can handle (`.venv/.../pre_commit/commands/hook_impl.py:128-140`).

**Concerns**
- **HIGH: the narrowing proof is never satisfied in this checkout.** I ran the proof's own command, `git rev-list --exclude=refs/stash --all --not --remotes HEAD`, here and it prints **817 commits**. They are reachable from local tags that were never pushed (`refs/tags/archive/*`, `backup/*`, `backup-pre-*`, `precompact-*`, …). So on the owner's real repo, `deferred-e2e` always takes the fallback and runs every over-budget e2e module, roughly 360 s of `test_cross_ai_runner_e2e`, on every push.
  - The correctness claim survives: the fallback still fails safe.
  - The performance story does not. AGENTS.md (28-09) would describe a fast single-branch path the owner never gets.
  - The 28-07 truth that git "updating remote-tracking refs after each successful push … takes the fast path" is false for this repo.
  - Case (n) passes only because the temp repo has no such tags.
  - **Fix options:** exclude `refs/tags` from the proof. Tags are pushed only explicitly; they are pushed with `--tags` or `--follow-tags`, so add `--exclude=refs/tags/*` and document that limit as a `shortcut:` line. Alternatively, restrict the proof to `--branches` plus worktree HEADs. Either way, add an e2e case with an unpushed local tag.
- **MEDIUM:** `E2E_RECORDED_SECS` is measured once, at a load below 4, on 24 CPUs. Seeding unrecorded modules as "deferred" is safe, but the 57.7 s module sits 2.3 s under the 60 s budget, so a slightly loaded run will move it across the line. Consider a margin rule, such as deferring modules recorded above 0.8 × the budget.
- **MEDIUM:** Task 1 is very large: the budget split, the full-run and mapper-error e2e handling, `pushed_paths`, `outside_commits`, the `--pushed` mode, the hook, a fake uv, six new e2e cases and a frozen-tree measurement. For a "cheap cross-AI executor" (an AGENTS.md requirement), this should be split.
- **LOW:** The "five tracked data files" stats include root `README.md` and `AGENTS.md` matched by basename. 28-09 relies on `--staged AGENTS.md README.md` selecting real readers, so a good match here matters, and 28-09's verify checks it.

**Suggestions**
- Fix the tag exclusion, run the proof command live on this checkout as part of the Task 1 verify, and record its output.
- Split Task 1 into "commit budget" and "pushed mode plus proof".

**Risk:** HIGH, until the tag issue is fixed. After that, MEDIUM.

#### 28-08

**Summary.** This plan adds per-module JSON reports and `make test-env-matrix`, a six-environment proof. The safeguards are thorough:
- the baseline itself must be green, with exactly one report per expected module;
- `AI_KIT_TEST_REPORT_DIR` is dropped from module envs, so nested runners can't publish into the matrix;
- reports are created exclusively and duplicates are flagged;
- the inner make is serial;
- `UV_NO_SYNC` stops uv from touching the owner's venv.

**Concerns**
- **MEDIUM:** Running `make test` six times takes roughly an hour or more, and the fix-and-rerun loop in Task 3 multiplies that. There is no stated cap or escape for an executor. Allow `--only` for the reruns during the fix loop, and require the full run only for the final proof.
- **MEDIUM:** The long-path clone shares `.venv` through `UV_PROJECT_ENVIRONMENT`. That venv's `.pth` files and editable paths point at the source checkout, not the clone. `pyproject.toml` has `package = false`, so the risk is low, but any test that imports from `sys.path` derived from the venv would silently test the source tree. A quick probe in the clone (`python -c "import tools; print(tools.__file__)"` or similar) would settle it.
- **LOW:** The plan says plainly that three of the six environments are neutralized by the runner baseline. That honesty is good.

**Risk:** MEDIUM. The main cost is wall time.

#### 28-09

**Summary.** This plan adds push timing with a verdict that reads the per-module reports, updates the docs before the final measurement, and writes only the measured figures afterward. The ordering is correct.

**Concerns**
- **HIGH (inherited from 28-07):** `push-worst` will include about 360 s of `deferred-e2e` on every real push from this checkout (see the 28-07 tag issue). The docs would then claim a 60 s push alongside a worst case that is actually the typical case. Either fix 28-07, or have the docs state that the fast path needs no unpushed local tags or branches.
- **MEDIUM:** Task 3 waits for a one-minute load below 4 after the matrix run. On a shared desktop this may never happen, and there is no timeout or fallback. Add a bounded wait, and record the load if the bound is reached.
- **MEDIUM:** The 60 s target depends on assumption A5: fakes alone get there, with `test_precompact_core` at about 30 s and `test_wizard_app` at about 21 s. These run in separate hooks back to back, so their sum is near 51 s plus the other modules. The fallback for a fail verdict ("fix the slowest module") is open-ended. That is acceptable, but flag it as the likely remaining effort.
- **LOW:** `ALL_SKIP_OK` will probably stay empty, which is fine.

**Risk:** MEDIUM.

#### Overall risk assessment

**Overall: MEDIUM-HIGH, driven by one concrete defect.**
- The plans are carefully reconciled with the source; nearly every code fact I checked was accurate.
- They lean toward safety: the fail-safe fallbacks, the non-vacuity cases, and honest labels on evidence and gaps.
- The new HIGH: 28-07's `outside_commits` proof is defeated by the many unpushed local tags in this checkout (817 commits outside `--remotes`). So `deferred-e2e` always takes the full fallback (about 360 s per push), and the docs in 28-09 would overstate the push experience.
- The secondary risks are task size (28-02 Task 3, 28-07 Task 1) for a cheap executor model, and the hour-plus matrix loop in 28-08.

---
This review is read-only. I didn't run any test suite. I checked the plans' factual claims with targeted greps and the live `git rev-list` probe, not by executing them, so the commit-time and push-time figures in the plans remain unverified.

---

## Consensus Summary

One grounded review ran (referee-three); referee-one (router combo with no target) and referee-two (model
unavailable) returned no output and contribute nothing, so there is no cross-reviewer consensus this cycle.
Referee-three rates the phase MEDIUM-HIGH, "driven by one concrete defect", and says the cycle-2 fixes hold:
the 16 elapsed ceilings, the detached case runners and `selfTestAbort` on SIGTERM, the `_tree_sha` symlink fix,
the `from common_render import` form, and `_pre_push_ns`'s first-ref return all match the source. The
orchestrator re-checked each existence claim and every symbol in the text changed since `3bcb78b`.

### Cycle-2 HIGH resolution

All 10 cycle-2 HIGHs have a Round 2 row in a plan's `## Review Dispositions Ledger`, and the plan text holds
the change. The source-grounding pass confirms each:

- **Fully resolved (10):** only the first pushed ref reaches `--pushed` (28-07 Task 1 step 3: narrow only with
  the HEAD-is-TO and `outside_commits` proof, otherwise run every over-budget module; correct and fail-safe, but
  see the new HIGH below for its fast path); the commit-budget amendment's owner status (orchestrator gray-area
  ruling recorded in SPEC R1, GATE-01, ROADMAP criterion 1, 28-06 and 28-07; decided for this run, the owner may
  revert); e2e durations measured while edited (28-07 Task 1 steps 6-7: commit, then a frozen-tree foreground
  run); interrupt cleanup with queued work (28-02 Task 3 step 3: stop flag under the registry lock,
  `cancel_futures=True`, a three-modules-one-worker test); the self-test's detached sessions (28-02 Task 3 steps
  2 and 4: SIGTERM first, forwarded by the e2e module so `selfTestAbort()` runs, then SIGKILL); the matrix
  snapshot hashing a symlink (28-04 Task 2 step 5: `_tree_sha(Path(core_root).resolve())`, `TestCoreTreeHash`);
  the literal `executable=` override (28-05 Task 3 step 1, three non-vacuity cases); `from <stem> import` in the
  mapper (28-06, with the real `tests/test_cursor_status_line.py:35` regression); the scratch HOME losing the
  toolchain (one public `tool_cache_forwards`, used by 28-01, 28-08 and 28-09); the tripwire making hosts look
  installed (28-01 case (f), the docstring, and the host-presence class in 28-02 Task 3 step 7).

### Agreed Strengths

Single reviewer; no agreement possible. Its main strengths, confirmed by the orchestrator: one shared load
reading passed to Node removes the cross-language sampling race (28-02); the check-dogfood counts and the
apply-skip warning do not claim coverage that did not happen (28-04); every mapper failure falls back to more
tests, never fewer (28-06).

### Agreed Concerns

None (single reviewer). Its HIGH is confirmed by the orchestrator and counts.

### Divergent Views

None this cycle. The cycle-2 divergence on the `.planning/` rule's breadth was settled in 28-05's Round 2 row
(the rule widens).

## Current HIGH Concerns

Gate: only referee-three ran, so the consensus gate is skipped and its HIGH counts.

1. **28-07 (and the 28-09 docs): the `--pushed` narrowing proof never holds in this checkout** (referee-three;
   confirmed by the orchestrator). `git rev-list --exclude=refs/stash --all --not --remotes HEAD` prints 817
   commits here, all reachable only from the 27 local tags (`archive/*`, `backup/*`, `precompact-*`, `v1.2`,
   `v1.3`, ...): `--tags --not --remotes HEAD` gives 817, `--branches --not --remotes HEAD` gives 0, and the same
   command with `--exclude='refs/tags/*'` added gives 0. So every real push takes the fallback and runs every
   over-budget e2e module (about 360 s of `tests.test_cross_ai_runner_e2e`). Correctness holds (the fallback is
   fail-safe); the 28-07 `<context>` line "a solo developer's single-branch push takes the fast path" is false
   for this repo, case (n) passes only because the temp repo has no tags, and 28-09's AGENTS.md/README push
   figures would describe a path the owner never gets. Needed: leave unpushed tags out of the proof
   (`--exclude='refs/tags/*'` before `--all`, or `--branches` plus each worktree's HEAD), with a `shortcut:`
   line naming the gap (a tag pushed by name, `--tags` or `--follow-tags` that points outside TO); an e2e case
   with an unpushed local tag that still narrows; a Task 1 verify that runs the proof command on this checkout
   and records its count; and 28-09's docs stating when the fast path applies.

## Current Actionable Non-HIGH Concerns

- 28-02 (referee-three M): Task 3 holds the deadline and process-group code, the stress run and the four-tier
  convergence with its fix-ups; split it so the runner code commits on its own before the convergence.
- 28-07 (referee-three M): Task 1 holds the budget split, the full-run and mapper-error e2e handling,
  `pushed_paths`, `outside_commits`, `--pushed`, the hook, the fake uv, the new e2e cases and the frozen-tree
  measurement; split it (commit budget, then pushed mode and proof) for a cheap executor.
- 28-04 (referee-three M): the apply no-write guard skips on gsd-core 1.18.0 and the deferral keeps it in the
  summary only; add a `.planning/ROADMAP.md` §Backlog item with a goal statement (widen `GSD_CORE_PREFIXES` with
  its table-parity check so the apply guard runs), per AGENTS.md's backlog rule.
- 28-05 (referee-three M): the `.planning/` rule is static only and tracks root names across scopes; either add
  a cheap run-time layer (for example, 28-08's long-path clone without `.planning/`, so an escaping reader shows
  as a matrix difference) or reject it explicitly in the ledger with the D-13 reason.
- 28-06 (referee-three M): "let such a commit run to the end in the background" is only in `<context>`; put it,
  with the expected ~6 minutes, in the task actions of the two runner commits so an executor does not read the
  hook as hung.
- 28-08 (referee-three M): Task 3 re-runs the full six-environment matrix after every fix; let the fix loop
  re-run `--only <the differing environments>` (plain first) and require the full `make test-env-matrix` only
  for the final proof.
- 28-02 Task 3 step 7, 28-07 Task 1 step 7 and 28-09 Task 3 (referee-three M): each waits for a one-minute load
  below 4 with no bound; give the wait a bound and record the load when it is reached.

Raised and not counted, with the reason:

- 28-01: the drift scan's hits are bounded (47 unique upper-case `_HOME/_DIR/.../_SECRET` constants in `tools/`
  and `skills/`), and step 6 already prints and decides each; case (f) breakage surfacing in wave 2 is the
  designed triage of 28-02 Task 3 step 7; the `GIT_CEILING_DIRECTORIES` LOW is self-declared fine.
- 28-02: the joined-output shape is already pinned (`tests/test_run_unittest_parallel.py:150` asserts unittest's
  stderr text `NO TESTS RAN` in the joined output); the uv child's SIGTERM handling is stated in 28-06 Task 1
  step 2; the 5400 s hold is accepted in the plan.
- 28-03: both LOWs are self-declared fine or cosmetic (the run rules forbid `cd <repo> &&`, not `mkdir -p &&`).
- 28-04: the dogfood time is measured by 28-09 (Round 2 row "already measured"); `parse_verbose` across 3.12
  and 3.14: the existing guard tests have no docstrings and the `<method> (<id>) ... <status>` form is the same.
- 28-06: the e2e scaffolding churn is already centralized in 28-07's `build_repo`.
- 28-07: a margin under the 60 s budget: the plan decides by the measured table and checks the 120 s bound
  (`<context>`, deliberate-simplicity rationale); the data-file stats LOW is covered by 28-09's verify.
- 28-08: the shared `.venv` in the long-path clone: the only `.pth` is `_virtualenv.pth`, none points at the
  checkout, and `pyproject.toml:13` sets `package = false` (rejected by the source check).
- 28-09: the A5 dependency is acknowledged as the likely remaining effort; `ALL_SKIP_OK` staying empty is fine.

## Verification coverage

### Source-grounding pass

`plan_review.source_grounding` is on; effective authority `grep` (`drift-guard authority`), so MISSING gives
`needs-acknowledgement`, AMBIGUOUS gives MEDIUM and UNCHECKABLE gives INFO; nothing hard-blocks. A read-only
pass resolved, with `rg` and `sed`, every existing symbol cited in the plan text changed since `3bcb78b`
(448 added lines across the nine plans, SPEC, REQUIREMENTS and ROADMAP), plus every existence claim of
referee-three. Paths and symbols the phase creates were excluded after checking they are absent at HEAD
(`tool_cache_forwards`, `CREDENTIAL_ENV_VARS`, `stop_process_group`, `MODULE_STOP_GRACE_SECS`,
`SELF_TEST_MODULE_TIMEOUT_SECS`, `AIKIT_XAI_SELFTEST_LOAD`, `scaledMs`, `outside_commits`, `pushed_paths`,
`COMMIT_E2E_BUDGET_SECS`, `E2E_RECORDED_SECS`, `stale_machinery_names`, `test_parent_project_config_is_never_touched`,
`TestCoreTreeHash`, `TestDeferredPush`, and the new tools, tests and hooks listed in cycle 2).

- **VERIFIED:** about 70 symbols in the changed text, among them: `shutil.which` defaults in
  `detection.py:182,205` and `seams.which` at `gp_host.py:115,156`; the plan's credential scan returns exactly
  the ten `CREDENTIAL_ENV_VARS` names; `ConfigSpec.provider_env` is field 8 (`tools/common_types.py:43-51`), with
  `AI_KIT_SEGMENT_` (`tools/claude_host.py:96`) and `AI_KIT_CURSOR_PROVIDER_` (under `AI_KIT_CURSOR_`);
  `CACHE_ROOT` in `stack_cache.__all__`; `RUNBOOK_RELATIVE_PATH`; 16 elapsed ceilings with `elapsed >= 1000`
  at `cross-ai.mjs:2564` and `elapsed >= 600` at `:2638`; `caseRunners`, `runCaseProcess` and `detached: true`
  (`:5267-5277`), `selfTestAbort` (`:5466`), the SIGTERM/SIGINT/SIGHUP loop (`:3676`), the `hang` case,
  `AIKIT_XAI_SELFTEST_CASES` (`:10114`); `MODULE_TIMEOUT_SECS = 900`, `_run_all`'s pool, `available_cpus`,
  `worker_count`; `load_runner`, `test_module_temp_directories_are_removed`, the 0.01 patch at
  `tests/test_run_unittest_parallel.py:161`; `run_group`'s new session (`tests/test_cross_ai_runner_e2e.py:101-115`);
  Python 3.12.12 under uv without `os.process_cpu_count`; the symlink-home test
  (`tests/test_tool_substitution_hook.py:1198-1206`); `TestCoreEdges`, `test_chunk_max_chunks_dropped_counted`
  (`:310`), `test_classify_stops_below_ten_ms` (`:327`); both matrix snapshot calls (`:33`, `:98`),
  `cls.core_root`, `live_tables`, `run_matrix`; `_tree_sha`'s symlink branch (`tests/gsd_curated_eval.py:253-259`);
  `check_pi_live.py`'s `parents[5]` root; `from tools import wizard_app as wa` (`tests/test_wizard_app.py:27`);
  pre-commit 4.6.0's `_pre_push_ns` (`hook_impl.py:120-175`), `run.py:385-392` and `git.py:158-165`; both
  doc readers named by 28-09 read AGENTS.md or README.md.
- **MISSING:** none.
- **CONTRADICTED:** the 28-07 `<context>` claim that a single-branch push takes the fast path (HIGH 1).
- **AMBIGUOUS:** none new. Two Round 1 / iteration-2 ledger rows in 28-06 (`:237`) and 28-07 (`:275`) still read
  "owner confirmation pending" and "bounds every timed selective commit"; the Round 2 rows say they supersede
  them, so this is not a finding.

**UNCHECKABLE (INFO), with reason:**

- Measurements: the 360.5 s and 57.7 s e2e times, the stress-run factor, the 120 s commit-stage check, the
  push-time figures. They need runs.
- External behaviour: the volta shim under a temp HOME, Puppeteer under the pinned HOME, `git rev-list --all`
  including other worktrees' HEADs (one worktree here).
- Run-only outcomes: the four-tier convergence, the six-environment matrix, the two-ref push to a bare remote.
- Signatures: not assertable under `grep`.

### Cross-artifact fact-drift pass

- **Phase status** (`drift-guard phase-status --phase 28`): `lag`. STATE.md "Ready to execute", ROADMAP "Not
  started", one step apart. Not a finding.
- **Requirement IDs:** GATE-01..05 all claimed by the plans; the GATE-01 and SPEC R1 commit-budget wording in
  REQUIREMENTS.md and ROADMAP criterion 1 now carries the same orchestrator-ruling text as 28-06 and 28-07. No
  contradiction.
- **Success criteria vs `must_haves.truths`:** criteria 1-5 each have matching truths. SPEC R1's Target adds the
  narrowing proof and the multi-ref acceptance, which ROADMAP criterion 1 states at a coarser level ("run by a
  pre-push hook for the pushed commits"); a level-of-detail difference, not a contradiction.
- **CONTEXT decisions vs plan usage:** D-01..D-14 re-checked against the changed text. D-02 (the two existing
  pre-push hooks stay as they are) still holds with `check-dogfood` and `deferred-e2e` added; D-13 (a static
  `.planning/` rule) matches 28-05. Advisory only.
- Skipped: nothing. STATE.md and CONTEXT.md are both present.
