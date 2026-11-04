---
phase: quick-261104-cxr
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - skills/ai-kit-spec-review/references/cross-ai.mjs
  - .planning/scripts/cross-ai.mjs
  - tests/cross_ai_selftest.py
  - tests/test_cross_ai_selftest_logic_1_e2e.py
  - tests/test_cross_ai_selftest_logic_2_e2e.py
  - tests/test_cross_ai_selftest_logic_3_e2e.py
  - tests/test_cross_ai_selftest_logic_4_e2e.py
  - tests/test_cross_ai_selftest_runtime_1_e2e.py
  - tests/test_cross_ai_selftest_runtime_2_e2e.py
  - tests/test_cross_ai_selftest_runtime_3_e2e.py
  - tests/test_cross_ai_selftest_runtime_4_e2e.py
  - tests/fixtures/cross_ai_selftest_secs.json
  - tests/test_cross_ai_runner_e2e.py
  - tools/run_unittest_parallel.py
  - tests/test_run_unittest_parallel.py
  - tests/test_staged_commit_e2e.py
  - tests/test_staged_mapper.py
  - Makefile
  - .pre-commit-config.yaml
  - AGENTS.md
  - README.md
autonomous: true
requirements: [quick-261104-cxr]

estimate:
  tokens: 120000
  raw_tokens: 120000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "`cross-ai.mjs --self-test-list` prints 438 `name<TAB>kind` lines, 392 `logic` and 46 `runtime`, identical to tmp/quick-xai-split/kinds.tsv; a case without a kind or a duplicate name makes the self-test exit 2"
    - "The eight shard modules run every listed case exactly once, through `--self-test` with real clocks, one kind per module, split longest-first by the generated timing fixture (ShardCoverageTest)"
    - "tests.test_cross_ai_runner_e2e no longer runs the full self-test: it smoke-runs a rendered copy (5 named cases) and keeps the interrupt, load-factor, stop, dispatch and classify tests"
    - "After the E2E_RECORDED_SECS refresh no cross-AI e2e module is recorded above the 60 s commit budget, so a template change runs its covering shards at commit"
    - "The parallel runner submits modules longest-recorded first and every module has the one 900 s deadline (the self-test override is gone)"
    - "tests.test_staged_commit_e2e keeps one deferred module in its copied runner whatever the real table holds"
    - "AGENTS.md and README.md carry the new push-timing figures and AGENTS.md describes the shards, `--self-test-list` and the fixture refresh command"
  artifacts:
    - path: tests/cross_ai_selftest.py
      provides: "Shared harness: hermetic env, load-scaled guards, SIGTERM forwarding, list_cases, split_cases, run_cases, shard_case, record_times"
      contains: "def split_cases("
    - path: tests/fixtures/cross_ai_selftest_secs.json
      provides: "Generated per-case seconds that balance the shards"
    - path: tests/test_cross_ai_selftest_logic_1_e2e.py
      provides: "One of eight shard modules"
      contains: "shard_case(\"logic\", 1)"
    - path: skills/ai-kit-spec-review/references/cross-ai.mjs
      provides: "Per-case kind tags, --self-test-list, kind and name validation"
      contains: "--self-test-list"
    - path: tools/run_unittest_parallel.py
      provides: "Shard modules in E2E_MODULES, refreshed E2E_RECORDED_SECS, longest-first submit order"
      contains: "ordered = sorted(modules"
  key_links:
    - from: tests/test_cross_ai_selftest_*_e2e.py
      to: tests/cross_ai_selftest.py
      via: "shard_case(kind, index) -> shard_names -> list_cases + split_cases"
      pattern: "shard_case\\("
    - from: tests/cross_ai_selftest.py
      to: skills/ai-kit-spec-review/references/cross-ai.mjs
      via: "`--self-test-list` for membership, AIKIT_XAI_SELFTEST_CASES for the run"
      pattern: "--self-test-list"
    - from: tools/staged_mapper.py
      to: tests/cross_ai_selftest.py
      via: "the helper names the path form \"skills\", \"ai-kit-spec-review\", so every shard covers the template"
      pattern: "\"skills\", \"ai-kit-spec-review\""
    - from: tools/run_unittest_parallel.py
      to: tests/test_cross_ai_selftest_*_e2e.py
      via: "E2E_MODULES membership and E2E_RECORDED_SECS times"
      pattern: "tests.test_cross_ai_selftest_"
---

<objective>
Split the runner template's self-test (438 cases, today run twice by
`tests/test_cross_ai_runner_e2e.py`, recorded 366 s) into four logic and four runtime shard
modules of about 20-25 s each, so no new e2e module takes more than about 30 s and the e2e tier
can finish under 60 s. Nothing is removed or weakened: every case keeps its real clocks and runs
in exactly one shard; membership comes from the template's own listing, never a hand list.

Purpose: a template change runs its covering e2e modules at commit instead of deferring a 6-minute
module to push.
Output: two commits (template listing; shards, harness, runner, docs) and a SUMMARY.
</objective>

<execution_context>
@.claude/gsd-core/workflows/execute-plan.md
@.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@AGENTS.md

Facts already established by the orchestrator (live-verified 2026-11-04; do not re-derive, do not
re-run the per-case timing pass):
- Kinds: `tmp/quick-xai-split/kinds.tsv` (name, kind, seconds, reason): 392 logic, 46 runtime.
  `tmp/quick-xai-split/insert_kinds.py` writes them into the template (`--check` dry-runs).
- Simulated split (planner dry run on a scratch copy): logic shards 97/97/99/99 cases at 22.1 s
  each alone, runtime 10/11/11/14 cases at about 23.2 s; one logic shard ran in 19.2 s and one
  runtime shard in 23.0 s at idle.
- The planner wrote every script and code file below and dry-ran the whole of Tasks 1 and 2 plus
  the Task 3 edits on a scratch copy of HEAD: ruff, vulture, pyright and pylint passed, and
  `tests.test_run_unittest_parallel`, `tests.test_gate_scope`, `tests.test_staged_mapper` and
  `tests.test_arch` passed. The scripts and code files already sit in the main checkout's
  `tmp/quick-xai-split/` and reach the worktree in Task 1 step 0. The listings at the end of this
  plan are their exact contents, for review. A script that cannot find its exact anchor stops
  before writing and names the snippet. Then STOP and report: the tree differs from the one the
  plan was dry-run against. Do not hand-edit around it.

Executor environment and rules (owner rules; follow every one):
- You run in an agent git worktree that lacks the gitignored `.claude/gsd-core`, `.claude/scripts`
  and `tmp/`. Task 1 step 0 copies them from the main checkout. The main checkout is the parent
  directory of `git rev-parse --path-format=absolute --git-common-dir`. Never commit them.
- Every command runs from the worktree root. Export `AI_KIT_REFUSE_REAL_HOME=1` for every test
  command and every `git commit` (the hooks run tests).
- Multi-step shell lives in the copied `.sh`/`.py` files; one-line commands are fine. No heredocs,
  no `cd <repo> &&` chains.
- Re-run only the affected modules while iterating. Do NOT run `make test` or `make validate`: the
  orchestrator runs `make test`, `make check-dogfood` and the env matrix after merging.
- Stage files by name only (never `git add -A` / `git add .`), never `--no-verify`. Never stage
  `.planning/config.json`, `.claude/gsd-core`, `.claude/scripts` or anything under `tmp/`. Do not
  commit SUMMARY, STATE or PLAN files (the orchestrator does). After a commit hook fails: fix the
  cause, re-run only that check's Makefile target (for example `make ruff`), then commit again.
- Never touch the real `~/.claude`, `~/.cursor`, `~/.config/opencode`, `~/.codex`, `~/.pi` or
  `~/.gsd`; never print secrets; never push; never `git reset --hard`, `git clean -f`,
  `git checkout .` or `git restore .`. Leave no stray process or `/tmp` litter.
- On the same failure 3 times without progress, stop and report. If a step's wall time passes
  twice its estimate, stop that step and report.
- jev: only for a new gray decision (a failure that might be environment noise, a deviation that
  might need the owner). Follow the main checkout's `tmp/auto/jev-brief.md`; its answers are
  advisory; log each call in one SUMMARY line (id, answer, confidence, what you did).
- English only in every file and commit message.
</context>

<tasks>

<task type="tracer">
  <name>Task 1: Tag every self-test case logic or runtime, add --self-test-list, re-render, commit 1</name>
  <precondition>The main checkout (parent of `git rev-parse --path-format=absolute --git-common-dir`) holds tmp/quick-xai-split/kinds.tsv, insert_kinds.py and edit_template.py.</precondition>
  <files>skills/ai-kit-spec-review/references/cross-ai.mjs, .planning/scripts/cross-ai.mjs</files>
  <action>
Thinnest end-to-end path first: a tagged case, listed by the template, selected by name and run by
the rendered runner copy. The Python shards in Task 2 consume exactly this contract.

Step 0 (environment, one-line commands, from the worktree root):
- `MAIN="$(dirname "$(git rev-parse --path-format=absolute --git-common-dir)")"; echo "$MAIN"`
  must print the main checkout path (it contains `.planning/` and `tmp/quick-xai-split/`). The
  shell does not keep variables between calls, so repeat the `MAIN=...;` prefix in every
  command that needs it.
- `MAIN="$(dirname "$(git rev-parse --path-format=absolute --git-common-dir)")"; mkdir -p tmp .claude; [ -d tmp/quick-xai-split ] || cp -a "$MAIN/tmp/quick-xai-split" tmp/; [ -d .claude/gsd-core ] || cp -a "$MAIN/.claude/gsd-core" .claude/; [ -d .claude/scripts ] || cp -a "$MAIN/.claude/scripts" .claude/`
- `ls tmp/quick-xai-split/edit_template.py tmp/quick-xai-split/check_listing.py tmp/quick-xai-split/cross_ai_selftest.py tmp/quick-xai-split/assemble.py tmp/quick-xai-split/edit_task3.py tmp/quick-xai-split/edit_docs.py .claude/gsd-core/bin/gsd-tools.cjs`
  lists every file. `git status --short` shows nothing new under `tmp/` or `.claude/` (both are
  gitignored).

Step 1: `python3 tmp/quick-xai-split/insert_kinds.py --check` prints `covered 438 of 438 cases`;
then `python3 tmp/quick-xai-split/insert_kinds.py` writes the `kind:` lines (it prints the same
line). It refuses a template that already has kinds: if it says so, Step 1 already happened.

Step 2: `python3 tmp/quick-xai-split/edit_template.py` (listing L1). It prints
`applied 6 edits to skills/ai-kit-spec-review/references/cross-ai.mjs`. The six edits are:
- the usage header gets a `--self-test-list` entry;
- parseArgs gets the `selfTestList: false` default and the
  `else if (a === '--self-test-list') { o.selfTest = true; o.selfTestList = true; }` branch;
- `blackBoxSelfTest(listOnly = false)` is called as `blackBoxSelfTest(o.selfTestList)` from main;
- right before the AIKIT_XAI_SELFTEST_CASES filter, a validation block runs on every self-test
  run. A case whose kind is neither `logic` nor `runtime` prints
  `self-test: case without a logic or runtime kind: <names>` and returns 2. A repeated name
  prints `self-test: duplicate case name: <names>` and returns 2. In list mode the block then
  prints `name\tkind` per case and returns 0.
There is no template version bump.

Step 3: `node --check skills/ai-kit-spec-review/references/cross-ai.mjs` exits 0.

Step 4: re-render the dogfood copy through the tool, never by hand:
`python3 skills/ai-kit-gsd-curated-config/ai-kit-gsd-curated-config.py ensure-runner --cwd .`
twice. The second run's output contains `keep-pristine`.
`git status --short .planning/scripts/` shows only ` M .planning/scripts/cross-ai.mjs`. Then:
`diff <(git diff -U0 skills/ai-kit-spec-review/references/cross-ai.mjs | grep '^[+-] ') <(git diff -U0 .planning/scripts/cross-ai.mjs | grep '^[+-] ') && echo mirrored`
prints `mirrored`, and `git diff --stat skills/ai-kit-spec-review/references/cross-ai.mjs .planning/scripts/cross-ai.mjs`
lists both files (so the comparison is not of two empty diffs). The rendered copy changed
exactly like the template, and no config line moved. If it does not print `mirrored`, stop and
report the diff.

Step 5: end-to-end check of both files (listing L2, about 10 s each):
`python3 tmp/quick-xai-split/check_listing.py skills/ai-kit-spec-review/references/cross-ai.mjs`
and `python3 tmp/quick-xai-split/check_listing.py .planning/scripts/cross-ai.mjs`. Each prints
`listed 438 {'logic': 392, 'runtime': 46}` then `subset ok`. Then `make check-dogfood` passes.

Step 6 (commit 1): `git add skills/ai-kit-spec-review/references/cross-ai.mjs .planning/scripts/cross-ai.mjs`.
`git diff --cached --stat` must list exactly those two files. Run
`AI_KIT_REFUSE_REAL_HOME=1 git commit -F tmp/quick-xai-split/commit1.txt` in the background and
wait for it to exit (the staged-tests hook runs the covering unit, uv and in-budget e2e modules,
about 1-3 minutes; `tests.test_cross_ai_runner_e2e` is still recorded at 366 s, so it is deferred,
which is expected). `git log -1 --format=%s` prints
`feat(cross-ai): tag self-test cases logic or runtime and list them`.
  </action>
  <verify>
    <automated>python3 tmp/quick-xai-split/check_listing.py skills/ai-kit-spec-review/references/cross-ai.mjs && python3 tmp/quick-xai-split/check_listing.py .planning/scripts/cross-ai.mjs && test "$(git log -1 --format=%s)" = 'feat(cross-ai): tag self-test cases logic or runtime and list them'</automated>
  </verify>
  <done>Both runner files list 438 cases with the kinds of kinds.tsv and run a subset; the second ensure-runner run says keep-pristine; commit 1 holds exactly the two .mjs files.</done>
</task>

<task type="auto">
  <name>Task 2: Shared harness, timing fixture, eight shard modules, slimmed e2e module</name>
  <files>tests/cross_ai_selftest.py, tests/fixtures/cross_ai_selftest_secs.json, tests/test_cross_ai_selftest_{logic,runtime}_{1..4}_e2e.py, tests/test_cross_ai_runner_e2e.py, tools/run_unittest_parallel.py, Makefile, .pre-commit-config.yaml</files>
  <action>
Step 1: `cp tmp/quick-xai-split/cross_ai_selftest.py tests/cross_ai_selftest.py` (listing L3). The
harness moves out of `tests/test_cross_ai_runner_e2e.py` verbatim: `_real_node_executable`,
`TEMPLATE`, `runner_env`, `MAX_LOAD_FACTOR`, `_load_runner`, `load_reading`, `load_factor`,
`guard_secs`, `assert_factor_printed`, `STOP_GRACE_SECS`, `_LIVE_GROUPS`, `stop_group`,
`_forward_sigterm`, `setUpModule`, `start_group`, `run_group`. The two full-run guard constants
are replaced by `SHARD_GUARD_SECS = 120`: 4 x 120 + 300 = 780 s, under the runner's 900 s module
deadline. New code: `SHARD_COUNTS`, `LIST_TIMEOUT_SECS`, `TIMES_FIXTURE`, `SHARD_MODULE`,
`list_cases`, `recorded_secs`, `split_cases` (greedy longest first, ties by name, lightest shard
with the lowest index wins, an unrecorded name weighs the median), `shard_names`, `run_cases`,
`shard_case`, `record_times`, and the `--record-times` main guard (the last statement). It keeps
only the spec-review `sys.path` insert. That insert carries the path form
`"skills", "ai-kit-spec-review"` that makes tools/staged_mapper.py map the template to every
shard.

Step 2 (about 4 minutes, run in the background and wait for it to exit; stop and report past
8 minutes): `AI_KIT_REFUSE_REAL_HOME=1 python3 tests/cross_ai_selftest.py --record-times`. The
last line printed is `recorded 438 cases in <path>/tests/fixtures/cross_ai_selftest_secs.json`.
Any failing case aborts with its name and stderr: treat that as a real failure (fix or report),
never skip it.

Step 3: `python3 tmp/quick-xai-split/write_shards.py` (listing L4) writes the eight
`tests/test_cross_ai_selftest_<kind>_<i>_e2e.py` files. Each holds only a docstring,
`import unittest`, `from tests.cross_ai_selftest import shard_case`,
`<Kind>Shard<i>Test = shard_case("<kind>", <i>)` and the `__main__` guard as the last statement
(test_arch rule 12). The class keeps the helper as its `__module__`, so unittest calls the
helper's `setUpModule` (SIGTERM forwarding) in every shard process. ruff does not select pep8
naming, so the CamelCase name passes.

Step 4: `python3 tmp/quick-xai-split/assemble.py tests/test_cross_ai_runner_e2e.py` (listing L7,
which reads L5 `e2e_head.txt` and L6 `e2e_shard_classes.txt`). It prints `assembled ...`. It
makes these changes:
- the module header becomes L5: a new docstring, and the harness imported from
  `tests.cross_ai_selftest`, with `setUpModule` imported under `# noqa: F401`. The module keeps
  its own `REPO_ROOT` and both `sys.path` inserts because its `ai_kit_*` imports need them.
  `importlib.util`, `math` and `resolve_cross_ai_template_path` are dropped.
- `test_self_test` is deleted.
- GuardFactorTest patches `"tests.cross_ai_selftest._load_runner"` (3 places).
- DeadlineCouplingTest asserts `runner.MODULE_TIMEOUT_SECS >= MAX_LOAD_FACTOR * SHARD_GUARD_SECS + 300`
  and keeps the stop-grace check.
- `test_render_and_self_test` keeps the pristine check. Instead of the full self-test, it runs
  `run_cases(SMOKE_CASES, template=script_path, cwd=tmp)` and asserts rc 0, `self-test ok` and
  the printed factor, with `SMOKE_CASES = ("ok", "quota", "argv-exec-pi", "hang", "load-factor-math")`.
- `ShardCoverageTest` is added (skips without node or git). One test checks unique names, that
  the kinds are exactly the SHARD_COUNTS keys, and that every name lands in exactly one
  non-empty shard. The non-vacuity test copies the template with its first `kind: 'logic',`
  line removed: `--self-test-list` exits 2 with the kind message and prints nothing.
- `ShardSplitTest` is added (pure). It checks the split cases `[["a","c"],["b","d"]]`, the
  median weight case `[["a","b"],["c","x"]]` and that every name lands once. It also checks
  that the `tests/test_cross_ai_selftest_*_e2e.py` files on disk are exactly the SHARD_COUNTS
  set, each in E2E_MODULES and each holding `shard_case("<kind>", <i>)`.
The interrupted, load-factor and stop_group tests stay; they use AIKIT_XAI_SELFTEST_CASES with
`sigterm-hang`, `load-factor-math` and `hang`.

Step 5: `python3 tmp/quick-xai-split/edit_runner_modules.py` (listing L8). It adds the eight
shard modules to E2E_MODULES right after `"tests.test_cross_ai_runner_e2e",`, under one comment
line. Then `python3 tools/gen_test_groups.py` refreshes the generated listings in `Makefile` and
`.pre-commit-config.yaml`. `git diff --stat Makefile .pre-commit-config.yaml` shows both files
changed.

Step 6 (checks):
- `uv run ruff check tests/cross_ai_selftest.py tests/test_cross_ai_runner_e2e.py tests/test_cross_ai_selftest_logic_1_e2e.py tests/test_cross_ai_selftest_logic_2_e2e.py tests/test_cross_ai_selftest_logic_3_e2e.py tests/test_cross_ai_selftest_logic_4_e2e.py tests/test_cross_ai_selftest_runtime_1_e2e.py tests/test_cross_ai_selftest_runtime_2_e2e.py tests/test_cross_ai_selftest_runtime_3_e2e.py tests/test_cross_ai_selftest_runtime_4_e2e.py tools/run_unittest_parallel.py`
  passes. If only I001 (import order) fails, run the same command with `--select I --fix`
  once, then re-check.
- `AI_KIT_REFUSE_REAL_HOME=1 uv run python tools/run_unittest_parallel.py tests.test_cross_ai_runner_e2e tests.test_cross_ai_selftest_logic_1_e2e tests.test_cross_ai_selftest_logic_2_e2e tests.test_cross_ai_selftest_logic_3_e2e tests.test_cross_ai_selftest_logic_4_e2e tests.test_cross_ai_selftest_runtime_1_e2e tests.test_cross_ai_selftest_runtime_2_e2e tests.test_cross_ai_selftest_runtime_3_e2e tests.test_cross_ai_selftest_runtime_4_e2e`
  prints `=== <module>: ok` for all nine (about 1 minute).
- `AI_KIT_REFUSE_REAL_HOME=1 python3 tools/run_unittest_parallel.py tests.test_gate_scope tests.test_arch tests.test_staged_mapper`
  prints ok for all three.
No commit in this task. Task 3 makes commit 2.
  </action>
  <verify>
    <automated>AI_KIT_REFUSE_REAL_HOME=1 uv run python tools/run_unittest_parallel.py tests.test_cross_ai_runner_e2e tests.test_cross_ai_selftest_logic_1_e2e tests.test_cross_ai_selftest_logic_2_e2e tests.test_cross_ai_selftest_logic_3_e2e tests.test_cross_ai_selftest_logic_4_e2e tests.test_cross_ai_selftest_runtime_1_e2e tests.test_cross_ai_selftest_runtime_2_e2e tests.test_cross_ai_selftest_runtime_3_e2e tests.test_cross_ai_selftest_runtime_4_e2e && AI_KIT_REFUSE_REAL_HOME=1 python3 tools/run_unittest_parallel.py tests.test_gate_scope tests.test_arch tests.test_staged_mapper</automated>
  </verify>
  <done>The fixture lists 438 cases. The eight shards and the slimmed module pass. ShardCoverageTest and ShardSplitTest pass. The gate-scope listings are current.</done>
</task>

<task type="auto">
  <name>Task 3: One deadline, longest-first submit, refreshed timings and docs, commit 2</name>
  <files>tools/run_unittest_parallel.py, tests/test_run_unittest_parallel.py, tests/test_staged_commit_e2e.py, tests/test_staged_mapper.py, AGENTS.md, README.md</files>
  <action>
Step 1: `python3 tmp/quick-xai-split/edit_task3.py` (listing L9) prints four `edited ...` lines.
It checks every anchor before it writes. It edits four files:
- tools/run_unittest_parallel.py: the self-test deadline override, its 5400 s constant and its
  comment are deleted. The per-module deadline lookup function is deleted, and its two callers
  use `MODULE_TIMEOUT_SECS` and `MODULE_TIMEOUT_SECS * len(modules)`. Nothing else used the
  override mechanism (checked by grep). The MappingProxyType import goes. The docstring now
  names MODULE_TIMEOUT_SECS and `tests/cross_ai_selftest.py` as the SIGTERM forwarder.
  `_run_all` submits `sorted(modules, key=lambda m: -E2E_RECORDED_SECS.get(m, 0))`, a stable
  sort, so non-e2e order is unchanged. Without this, the nine cross-AI modules would sort
  alphabetically ahead of the 57 s precompact module and the tier would end near 80 s.
- tests/test_run_unittest_parallel.py: the long-deadline test becomes
  `test_every_module_gets_the_one_global_deadline` (pins 900). The new
  `RunAllOrderTest.test_the_longest_recorded_module_is_submitted_first` patches `run_module`,
  `worker_count` -> 1 and the table, and expects order c, b, a, d.
- tests/test_staged_commit_e2e.py: the new `defer_one(path)` drops the largest recorded entry
  from the copied runner, and `build_repo` calls it right after copying the runner. After the
  split every real e2e module may fit the budget, and `pick_e2e` would then raise IndexError on
  an empty over-budget list.
- tests/test_staged_mapper.py: the two PushedModeTest comments say "patched to ... below" instead
  of claiming real recorded times. The logic is unchanged.

Step 2 (checks):
- `AI_KIT_REFUSE_REAL_HOME=1 python3 tools/run_unittest_parallel.py tests.test_run_unittest_parallel tests.test_gate_scope tests.test_staged_mapper tests.test_arch`
  shows four ok.
- `AI_KIT_REFUSE_REAL_HOME=1 uv run python tools/run_unittest_parallel.py tests.test_staged_commit_e2e`
  shows ok.
- `make ruff`, `make pyright` and `make vulture` pass, and so does
  `uv run pylint tools/run_unittest_parallel.py`.

Step 3 (measure; about 1.5 minutes; stop past 3 minutes):
`sh tmp/quick-xai-split/run_e2e_group.sh tmp/quick-xai-split/e2e_group.txt` (listing L10) runs
in the background; wait for it to exit 0. Then
`python3 tmp/quick-xai-split/refresh_recorded.py tmp/quick-xai-split/e2e_group.txt`
(listing L11). It rewrites E2E_RECORDED_SECS: every E2E_MODULES entry, rounded up, the 366
entry gone, the comment's date/CPUs/load updated. It prints one `module: secs` line per module.
It refuses a log with a FAILED module: fix that module first, never refresh around a failure.
Then confirm with a second run under the new submit order:
`sh tmp/quick-xai-split/run_e2e_group.sh tmp/quick-xai-split/e2e_group_ordered.txt`. Record its
`wall N s` line in the SUMMARY. If any cross-AI module is recorded above 60 s, or the second wall
time is above 60 s, do not loop: report it as a deviation with the numbers.
`tests.test_precompact_shims_e2e` (about 57 s) is out of this task's scope; just report its time.

Step 4 (mapper coverage):
`python3 tools/staged_mapper.py skills/ai-kit-spec-review/references/cross-ai.mjs | python3 -c "import sys; m = sys.stdin.read().split(); s = [x for x in m if x.startswith('tests.test_cross_ai_selftest_')]; assert len(s) == 8 and 'tests.test_cross_ai_runner_e2e' in m, m; print('mapper ok')"`
prints `mapper ok`: all eight shards plus tests.test_cross_ai_runner_e2e cover the template. At
HEAD it fails (no shard modules yet).

Step 5 (push timing; about 2 minutes; stop past 6):
`AI_KIT_REFUSE_REAL_HOME=1 python3 tools/time_prepush.py > tmp/quick-xai-split/prepush.txt 2>&1`
runs in the background. Wait, then `grep '^push-timing ' tmp/quick-xai-split/prepush.txt`
shows one line ending `verdict=pass`. Then
`python3 tmp/quick-xai-split/edit_docs.py tmp/quick-xai-split/prepush.txt` (listing L12). It
rewrites AGENTS.md's Push timing bullet from that one record: the 183.9 s before-figure is kept,
and the after-figures, pyright, vulture, check-dogfood, deferred-e2e and push-worst are replaced.
It adds the "Runner self-test shards" bullet after it (`--self-test-list`, the kinds, the
helper, the shard modules, the generated fixture and its refresh command). It also rewrites
README.md's matching sentence. A verdict other than pass, or a hook with a non-zero rc, makes
the script stop: report the line instead.
Review `git diff AGENTS.md README.md`: English only, no stale 352.4 s or 420.2 s figure left.

Step 6 (commit 2): stage by name:
`git add tests/cross_ai_selftest.py tests/fixtures/cross_ai_selftest_secs.json tests/test_cross_ai_selftest_logic_1_e2e.py tests/test_cross_ai_selftest_logic_2_e2e.py tests/test_cross_ai_selftest_logic_3_e2e.py tests/test_cross_ai_selftest_logic_4_e2e.py tests/test_cross_ai_selftest_runtime_1_e2e.py tests/test_cross_ai_selftest_runtime_2_e2e.py tests/test_cross_ai_selftest_runtime_3_e2e.py tests/test_cross_ai_selftest_runtime_4_e2e.py tests/test_cross_ai_runner_e2e.py tools/run_unittest_parallel.py tests/test_run_unittest_parallel.py tests/test_staged_commit_e2e.py tests/test_staged_mapper.py Makefile .pre-commit-config.yaml AGENTS.md README.md`.
`git diff --cached --stat` lists exactly these 19 files, and `git status --short` shows nothing
else modified or untracked outside `tmp/`/`.claude/`. Then run
`AI_KIT_REFUSE_REAL_HOME=1 git commit -F tmp/quick-xai-split/commit2.txt` in the background and
wait (shared machinery is staged, so the hook runs the full unit and arch groups plus the
covering e2e modules: about 3-5 minutes; stop and report past 10).
`git log -1 --format=%s` prints
`test(cross-ai): split the runner self-test into timed logic and runtime shards`.

Step 7 (SUMMARY, not committed): write
`.planning/quick/261104-cxr-split-cross-ai-runner-e2e-self-test-into/261104-cxr-SUMMARY.md`
with frontmatter `status: complete`. Include: the kind counts (392 logic, 46 runtime); each shard
module with its measured time from e2e_group.txt; tests.test_cross_ai_runner_e2e's new time;
the precompact time; both wall times; the push-timing line; both commit hashes and subjects;
deviations; jev calls (or "none").
  </action>
  <verify>
    <automated>AI_KIT_REFUSE_REAL_HOME=1 python3 tools/run_unittest_parallel.py tests.test_run_unittest_parallel tests.test_gate_scope tests.test_staged_mapper tests.test_arch && python3 tools/staged_mapper.py skills/ai-kit-spec-review/references/cross-ai.mjs | python3 -c "import sys; m = sys.stdin.read().split(); s = [x for x in m if x.startswith('tests.test_cross_ai_selftest_')]; assert len(s) == 8 and 'tests.test_cross_ai_runner_e2e' in m, m" && test "$(git log -1 --format=%s)" = 'test(cross-ai): split the runner self-test into timed logic and runtime shards'</automated>
  </verify>
  <done>Every module gets the one 900 s deadline, and the pool starts the longest-recorded module first. E2E_RECORDED_SECS comes from a full e2e run. The docs carry the new record and the shard bullet. Commit 2 holds the 19 files. The SUMMARY is written with status complete.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| test harness -> node child processes | the self-test runs fake CLIs; the harness gives them a temp HOME and a fake-bin PATH |
| executor -> owner checkout and config | the worktree copies gitignored tooling from the main checkout; the owner's uncommitted `.planning/config.json` must stay untouched |
| test gate -> commit | the shard split decides which cases run; a dropped case would silently weaken the gate |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-261104-01 | Tampering | tests/cross_ai_selftest.py runner_env | medium | mitigate | runner_env gives every node child a temp HOME, XDG_CONFIG_HOME and a fake-bin PATH; AI_KIT_REFUSE_REAL_HOME=1 on every test command and commit; the runner's baseline env and tripwire stay in force |
| T-261104-02 | Denial of service | shard runs | medium | mitigate | each shard is guarded by SHARD_GUARD_SECS x the load factor (at most 480 s); run_group stops the whole session (SIGTERM, then SIGKILL); DeadlineCouplingTest pins 4 x 120 + 300 <= the 900 s module deadline; setUpModule forwards SIGTERM to live groups |
| T-261104-03 | Repudiation | shard membership | high | mitigate | membership comes only from `--self-test-list`. The template refuses an unkinded or duplicate case (exit 2). ShardCoverageTest proves every case lands in exactly one shard, and its non-vacuity test proves the refusal fires. ShardSplitTest pins the shard files to SHARD_COUNTS and E2E_MODULES |
| T-261104-04 | Tampering | tests/fixtures/cross_ai_selftest_secs.json | low | mitigate | record_times writes through tempfile.mkstemp in the fixture folder plus os.replace; a stale or partial table only unbalances shards, never drops a case (median weight) |
| T-261104-05 | Information disclosure | commits | medium | mitigate | stage by name only; `git diff --cached --stat` must list exactly the planned files; `.planning/config.json`, `.claude/` and `tmp/` are never staged; no secret is printed |
| T-261104-SC | Tampering | npm/pip/cargo installs | low | accept | this plan installs no package; `uv run` only syncs the existing uv.lock |
</threat_model>

<verification>
- Task 1: `check_listing.py` passes on the template and on the re-rendered copy; ensure-runner's
  second run says keep-pristine; the rendered diff mirrors the template diff.
- Task 2: the nine cross-AI e2e modules pass; gate scope, arch and mapper tests pass.
- Task 3: runner, gate-scope, mapper, arch and staged-commit e2e tests pass. The mapper selects 8
  shards plus tests.test_cross_ai_runner_e2e for the template. Two timed `--group e2e` runs are
  recorded. time_prepush gives verdict pass, and both commits exist.
- The orchestrator afterwards runs `make test`, `make check-dogfood` and the env matrix.
</verification>

<success_criteria>
- No cross-AI e2e module is recorded above 60 s, and each shard is at most about 30 s in the
  e2e group run.
- Every one of the 438 cases runs in exactly one shard with its real clocks (ShardCoverageTest
  green).
- tests.test_staged_commit_e2e passes whatever the real E2E_RECORDED_SECS holds.
- Two logical commits, nothing else modified or untracked outside the gitignored `tmp/` and
  `.claude/`.
</success_criteria>

<output>
Create `.planning/quick/261104-cxr-split-cross-ai-runner-e2e-self-test-into/261104-cxr-SUMMARY.md`
(status: complete), and do not commit it.
</output>

<listings>

The files below already exist in the main checkout's `tmp/quick-xai-split/` (copied into the
worktree in Task 1 step 0). L3 is the code that lands as `tests/cross_ai_selftest.py`. If a file is
missing after the copy, write it from its listing with the Write tool, byte for byte.

#### file: tmp/quick-xai-split/edit_template.py (L1)

```python
"""Apply the quick 261104-cxr listing edits to the runner template. Run from the checkout root.

python3 tmp/quick-xai-split/edit_template.py
Each edit replaces one exact, unique snippet; the script stops on the first one it cannot find.
"""
import sys

PATH = "skills/ai-kit-spec-review/references/cross-ai.mjs"

HEADER_OLD = (
    " *                                            with load per CPU up to 4x,"
    " AIKIT_XAI_SELFTEST_LOAD overrides the reading\n"
)
HEADER_NEW = HEADER_OLD + (
    " *   --self-test-list                         print each self-test case as name<TAB>kind"
    " (logic or runtime);\n"
    " *                                            AIKIT_XAI_SELFTEST_CASES=a,b runs only the"
    " named cases\n"
)
VALIDATE = """\
    const unkinded = cases.filter((c) => c.kind !== 'logic' && c.kind !== 'runtime').map((c) => c.name);
    if (unkinded.length) {
      process.stderr.write(`self-test: case without a logic or runtime kind: ${unkinded.join(',')}\\n`);
      return 2;
    }
    const dupes = cases.map((c) => c.name).filter((n, i, all) => all.indexOf(n) !== i);
    if (dupes.length) {
      process.stderr.write(`self-test: duplicate case name: ${[...new Set(dupes)].join(',')}\\n`);
      return 2;
    }
    if (listOnly) {
      for (const c of cases) process.stdout.write(`${c.name}\\t${c.kind}\\n`);
      return 0;
    }
"""
ONLY = "    const only = (process.env.AIKIT_XAI_SELFTEST_CASES || '').split(',').filter(Boolean);\n"

EDITS = [
    (HEADER_OLD, HEADER_NEW),
    ("    printArgv: false, preamble: true, selfTest: false, classifyOnly: null,\n",
     "    printArgv: false, preamble: true, selfTest: false, selfTestList: false,"
     " classifyOnly: null,\n"),
    ("    } else if (a === '--self-test') o.selfTest = true;\n",
     "    } else if (a === '--self-test') o.selfTest = true;\n"
     "    else if (a === '--self-test-list') { o.selfTest = true; o.selfTestList = true; }\n"),
    ("async function blackBoxSelfTest() {\n", "async function blackBoxSelfTest(listOnly = false) {\n"),
    ("  if (o.selfTest) return blackBoxSelfTest();\n",
     "  if (o.selfTest) return blackBoxSelfTest(o.selfTestList);\n"),
    (ONLY, VALIDATE + ONLY),
]

with open(PATH, encoding="utf-8") as handle:
    text = handle.read()
if "--self-test-list" in text:
    sys.exit("the template already has --self-test-list")
for old, new in EDITS:
    if text.count(old) != 1:
        sys.exit(f"expected exactly one match for: {old!r}")
    text = text.replace(old, new)
with open(PATH, "w", encoding="utf-8") as handle:
    handle.write(text)
print(f"applied {len(EDITS)} edits to {PATH}")
```

#### file: tmp/quick-xai-split/check_listing.py (L2)

```python
"""Quick 261104-cxr Task 1 check, run from the checkout root.

python3 tmp/quick-xai-split/check_listing.py TEMPLATE
Lists TEMPLATE's self-test cases in a hermetic env, compares every (name, kind) with
tmp/quick-xai-split/kinds.tsv, then runs three cases through --self-test.
"""
import collections
import os
import shutil
import subprocess
import sys
import tempfile

TEMPLATE = sys.argv[1]
NODE = subprocess.run(["node", "-e", "process.stdout.write(process.execPath)"],
                      capture_output=True, text=True, check=True).stdout


def run(args, extra):
    with tempfile.TemporaryDirectory() as tmp:
        bin_dir = os.path.join(tmp, "bin")
        os.mkdir(bin_dir)
        os.symlink(NODE, os.path.join(bin_dir, "node"))
        for tool in ("git", "mkfifo"):
            found = shutil.which(tool)
            if found:
                os.symlink(found, os.path.join(bin_dir, tool))
        env = {"PATH": bin_dir, "HOME": tmp, "LANG": "C", "GIT_CONFIG_GLOBAL": os.devnull,
               "GIT_CONFIG_NOSYSTEM": "1", **extra}
        return subprocess.run([NODE, TEMPLATE, *args], env=env, capture_output=True, text=True,
                              timeout=120, check=False)


want = {}
with open("tmp/quick-xai-split/kinds.tsv", encoding="utf-8") as handle:
    for line in handle:
        if line.strip():
            name, kind = line.rstrip("\n").split("\t")[:2]
            want[name] = kind
proc = run(["--self-test-list"], {})
if proc.returncode != 0:
    sys.exit(f"listing failed rc={proc.returncode}: {proc.stderr}")
rows = [line.split("\t") for line in proc.stdout.splitlines()]
names = [row[0] for row in rows]
if len(names) != len(set(names)):
    sys.exit("duplicate names in the listing")
got = {row[0]: row[1] for row in rows}
if got != want:
    sys.exit(f"listing differs from kinds.tsv: {sorted(set(got.items()) ^ set(want.items()))[:10]}")
print("listed", len(rows), dict(collections.Counter(got.values())))
proc = run(["--self-test"], {"AIKIT_XAI_SELFTEST_CASES": "ok,hang,load-factor-math"})
if proc.returncode != 0 or "self-test ok" not in proc.stdout:
    sys.exit(f"subset run failed rc={proc.returncode}: {proc.stderr}")
print("subset ok")
```

#### file: tmp/quick-xai-split/cross_ai_selftest.py (L3, copied to tests/cross_ai_selftest.py)

```python
"""Shared harness for the cross-AI runner template's self-test e2e modules.

The full self-test takes minutes, so it runs as logic and runtime shard modules
(tests/test_cross_ai_selftest_<kind>_<i>_e2e.py), each well inside the commit e2e budget.
Membership is never a hand list: the template lists its cases with their kind
(`cross-ai.mjs --self-test-list`), and split_cases deals each kind into SHARD_COUNTS[kind]
shards, heaviest first, by the per-case seconds in tests/fixtures/cross_ai_selftest_secs.json.
That file is generated: `python3 tests/cross_ai_selftest.py --record-times` (see record_times).

Every session started here is registered for SIGTERM forwarding (setUpModule), so a stopped
module reaps the self-test's detached case runners. tests/test_cross_ai_runner_e2e.py uses the
same harness.
"""

from __future__ import annotations

import contextlib
import importlib.util
import json
import math
import os
import re
import shutil
import signal
import statistics
import subprocess
import sys
import tempfile
import time
import unittest
from collections.abc import Mapping, Sequence

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "skills", "ai-kit-spec-review"))

from ai_kit_spec.tooling_guidance import resolve_cross_ai_template_path


def _real_node_executable() -> str | None:
    if shutil.which("node") is None:
        return None
    try:
        proc = subprocess.run(
            ["node", "-e", "process.stdout.write(process.execPath)"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return proc.stdout if proc.returncode == 0 and os.path.isfile(proc.stdout) else None


_RESOLVED_TEMPLATE = resolve_cross_ai_template_path()
assert _RESOLVED_TEMPLATE is not None, "the shipped runner template is missing"
TEMPLATE = _RESOLVED_TEMPLATE


def runner_env(tmp: str) -> dict[str, str]:
    """Hermetic env matching cross-ai.mjs --self-test (fakes + node + git + mkfifo only)."""
    bin_dir = os.path.join(tmp, "bin")
    os.makedirs(bin_dir, exist_ok=True)
    node_bin = _real_node_executable()
    git_bin = shutil.which("git")
    # the FIFO cases (overlay-fifo-refused, retry-config-fifo) create their FIFO with mkfifo
    mkfifo_bin = shutil.which("mkfifo")
    if mkfifo_bin:
        link = os.path.join(bin_dir, "mkfifo")
        if not os.path.lexists(link):
            os.symlink(mkfifo_bin, link)
    if node_bin:
        link = os.path.join(bin_dir, "node")
        if not os.path.lexists(link):
            os.symlink(node_bin, link)
    if git_bin:
        link = os.path.join(bin_dir, "git")
        if not os.path.lexists(link):
            os.symlink(git_bin, link)
    # the fake bin stays first; the real node dir is added so a seam whose which_fn reads PATH
    # (the default) still resolves node, while the child itself only ever sees bin_dir
    path = bin_dir
    if node_bin:
        path = bin_dir + os.pathsep + os.path.dirname(node_bin)
    home = os.path.join(tmp, "home")
    os.makedirs(home, exist_ok=True)
    return {
        "PATH": path,
        "HOME": home,
        "XDG_CONFIG_HOME": os.path.join(home, ".config"),
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "xai-selftest",
        "GIT_COMMITTER_NAME": "xai-selftest",
        "GIT_AUTHOR_EMAIL": "xai-selftest@example.invalid",
        "GIT_COMMITTER_EMAIL": "xai-selftest@example.invalid",
        "LANG": "C",
    }


# Each shard run is guarded by a hard limit. The guard and the ceilings it guards are sized from
# ONE load reading (`load_reading`, passed to Node as AIKIT_XAI_SELFTEST_LOAD): a second,
# independently sampled reading (or Python's CPU count against Node's availableParallelism under
# an affinity mask) could differ, so the guard could fire before the ceilings it guards. One shard
# takes about 25 s at idle; 4 x 120 s plus 300 s for the rest of a module stays under the
# runner's 900 s module deadline (DeadlineCouplingTest pins it).
SHARD_GUARD_SECS = 120
MAX_LOAD_FACTOR = 4
SHARD_COUNTS = {"logic": 4, "runtime": 4}
LIST_TIMEOUT_SECS = 60
TIMES_FIXTURE = os.path.join(REPO_ROOT, "tests", "fixtures", "cross_ai_selftest_secs.json")
SHARD_MODULE = "tests.test_cross_ai_selftest_{kind}_{index}_e2e"
_RUNNER_PATH = os.path.join(REPO_ROOT, "tools", "run_unittest_parallel.py")


def _load_runner():
    spec = importlib.util.spec_from_file_location("run_unittest_parallel", _RUNNER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_reading() -> float:
    """One-minute load per CPU over the runner's own CPU count; 0.0 when unreadable."""
    cpus = _load_runner().available_cpus()
    try:
        load = os.getloadavg()[0]
    except OSError:
        return 0.0
    return load / cpus if cpus else 0.0


def load_factor(reading: float) -> float:
    """The reading clamped to 1..MAX_LOAD_FACTOR; 1 for a non-finite or non-positive reading."""
    if not math.isfinite(reading) or reading <= 0:
        return 1.0
    return min(float(MAX_LOAD_FACTOR), max(1.0, reading))


def guard_secs(base: int, factor: float) -> int:
    return math.ceil(base * factor)


def assert_factor_printed(case: unittest.TestCase, stderr: str, reading: float) -> None:
    match = re.search(r"self-test load factor (\S+)\n", stderr)
    assert match is not None, stderr
    case.assertAlmostEqual(float(match.group(1)), load_factor(reading), delta=1e-9)


# The runner stops this module with SIGTERM to its process group (MODULE_STOP_GRACE_SECS = 15 s).
# Each session started here is stopped the same way, so the self-test's selfTestAbort() reaps its
# detached case runners before any hard kill. STOP_GRACE_SECS must stay below the runner's grace.
STOP_GRACE_SECS = 10
_LIVE_GROUPS: set[subprocess.Popen] = set()


def stop_group(proc: subprocess.Popen, grace: float) -> None:
    """SIGTERM to the group of `proc`, up to `grace` seconds to exit, then SIGKILL to the group."""
    with contextlib.suppress(ProcessLookupError):
        os.killpg(proc.pid, signal.SIGTERM)
    with contextlib.suppress(subprocess.TimeoutExpired):
        proc.wait(timeout=grace)
    with contextlib.suppress(ProcessLookupError):
        os.killpg(proc.pid, signal.SIGKILL)


def _forward_sigterm(_signum, _frame) -> None:
    for proc in list(_LIVE_GROUPS):
        stop_group(proc, STOP_GRACE_SECS)
    os._exit(128 + signal.SIGTERM)


def setUpModule() -> None:
    signal.signal(signal.SIGTERM, _forward_sigterm)


def start_group(argv: list[str], **kwargs) -> subprocess.Popen:
    """Start `argv` in a new session and register it for SIGTERM forwarding."""
    proc = subprocess.Popen(
        argv,
        start_new_session=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        **kwargs,
    )
    _LIVE_GROUPS.add(proc)
    return proc


def run_group(argv: list[str], timeout: int, **kwargs) -> subprocess.CompletedProcess:
    """`subprocess.run` in a new session; a timeout stops the whole group (SIGTERM, then SIGKILL),
    not just the leader, so no fake CLI outlives the test."""
    proc = start_group(argv, **kwargs)
    try:
        with proc:
            try:
                out, err = proc.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                stop_group(proc, STOP_GRACE_SECS)
                out, err = proc.communicate()
                raise
            return subprocess.CompletedProcess(argv, proc.returncode, out, err)
    finally:
        _LIVE_GROUPS.discard(proc)


def list_cases(template: str = TEMPLATE) -> list[tuple[str, str]]:
    """(name, kind) of every self-test case, in the template's order (`--self-test-list`)."""
    node_bin = _real_node_executable()
    assert node_bin is not None
    with tempfile.TemporaryDirectory() as tmp:
        proc = subprocess.run(
            [node_bin, template, "--self-test-list"],
            cwd=REPO_ROOT,
            env=runner_env(tmp),
            capture_output=True,
            text=True,
            timeout=LIST_TIMEOUT_SECS,
            check=False,
        )
    if proc.returncode != 0:
        raise AssertionError(f"--self-test-list exited {proc.returncode}: {proc.stderr}")
    cases = []
    for line in proc.stdout.splitlines():
        name, kind = line.split("\t")
        cases.append((name, kind))
    return cases


def recorded_secs() -> dict[str, float]:
    """Per-case seconds from TIMES_FIXTURE (written by record_times)."""
    with open(TIMES_FIXTURE, encoding="utf-8") as handle:
        return json.load(handle)


def split_cases(names: Sequence[str], count: int, secs: Mapping[str, float]) -> list[list[str]]:
    """Deal `names` into `count` shards: heaviest first (ties by name) onto the lightest shard
    (lowest index on a tie); each shard's names sorted.

    A name missing from `secs` weighs the median of the known weights among `names` (1.0 when
    none is known). The table only affects balance, never membership: every name lands in exactly
    one shard.
    """
    known = [secs[name] for name in names if name in secs]
    default = statistics.median(known) if known else 1.0
    weight = {name: secs.get(name, default) for name in names}
    shards: list[list[str]] = [[] for _ in range(count)]
    loads = [0.0] * count
    for name in sorted(weight, key=lambda n: (-weight[n], n)):
        index = loads.index(min(loads))
        shards[index].append(name)
        loads[index] += weight[name]
    return [sorted(shard) for shard in shards]


def shard_names(kind: str, index: int) -> list[str]:
    """The case names of shard `index` (1-based) of `kind`."""
    names = [name for name, case_kind in list_cases() if case_kind == kind]
    return split_cases(names, SHARD_COUNTS[kind], recorded_secs())[index - 1]


def run_cases(
    names: Sequence[str],
    template: str = TEMPLATE,
    cwd: str = REPO_ROOT,
    guard_base: int = SHARD_GUARD_SECS,
) -> tuple[subprocess.CompletedProcess, float]:
    """Run the named cases through `--self-test` in one session; (result, the load reading)."""
    node_bin = _real_node_executable()
    assert node_bin is not None
    reading = load_reading()
    with tempfile.TemporaryDirectory() as tmp:
        env = {
            **runner_env(tmp),
            "AIKIT_XAI_SELFTEST_LOAD": repr(reading),
            "AIKIT_XAI_SELFTEST_CASES": ",".join(names),
        }
        proc = run_group(
            [node_bin, template, "--self-test"],
            guard_secs(guard_base, load_factor(reading)),
            cwd=cwd,
            env=env,
        )
    return proc, reading


def shard_case(kind: str, index: int) -> type[unittest.TestCase]:
    """The TestCase that runs shard `index` (1-based) of `kind`, named like LogicShard1Test."""

    class ShardTest(unittest.TestCase):
        @classmethod
        def setUpClass(cls):
            cls._skip = None
            if _real_node_executable() is None:
                cls._skip = "no node executable"
            elif shutil.which("git") is None:
                cls._skip = "git not on PATH"

        def setUp(self):
            if self._skip:
                self.skipTest(self._skip)

        def test_shard(self):
            names = shard_names(kind, index)
            self.assertTrue(names, f"{kind} shard {index} is empty")
            proc, reading = run_cases(names)
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)
            self.assertIn("self-test ok", proc.stdout)
            assert_factor_printed(self, proc.stderr, reading)

    ShardTest.__name__ = ShardTest.__qualname__ = f"{kind.title()}Shard{index}Test"
    return ShardTest


def record_times() -> int:
    """Run every case alone and rewrite TIMES_FIXTURE with its seconds (about 4 minutes).

    Refresh it on a quiet machine after adding a case or making one slower:
    `python3 tests/cross_ai_selftest.py --record-times`. A stale table only unbalances the
    shards; it never drops or duplicates a case.
    """
    secs: dict[str, float] = {}
    for name, _kind in list_cases():
        start = time.monotonic()
        proc, _reading = run_cases([name])
        if proc.returncode != 0:
            raise SystemExit(f"case {name} failed (rc {proc.returncode}):\n{proc.stderr}")
        secs[name] = round(time.monotonic() - start, 2)
    fd, tmp_path = tempfile.mkstemp(
        dir=os.path.dirname(TIMES_FIXTURE), prefix=".cross_ai_selftest_secs-", suffix=".json"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(secs, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(tmp_path, TIMES_FIXTURE)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        raise
    print(f"recorded {len(secs)} cases in {TIMES_FIXTURE}")
    return 0


if __name__ == "__main__":
    if sys.argv[1:] != ["--record-times"]:
        sys.exit("usage: python3 tests/cross_ai_selftest.py --record-times")
    setUpModule()
    sys.exit(record_times())
```

#### file: tmp/quick-xai-split/write_shards.py (L4)

```python
"""Write the eight self-test shard modules (quick 261104-cxr). Run from the checkout root."""

BODY = '''"""E2E tier: {kind} shard {index} of 4 of the runner self-test (tests/cross_ai_selftest.py)."""

import unittest

from tests.cross_ai_selftest import shard_case

{title}Shard{index}Test = shard_case("{kind}", {index})

if __name__ == "__main__":
    unittest.main()
'''

for kind in ("logic", "runtime"):
    for index in range(1, 5):
        path = f"tests/test_cross_ai_selftest_{kind}_{index}_e2e.py"
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(BODY.format(kind=kind, index=index, title=kind.title()))
        print("wrote", path)
```

#### file: tmp/quick-xai-split/e2e_head.txt (L5)

```python
"""E2E tier: real node and git, hermetic env for the cross-AI runner template.

The template's full self-test runs in the logic and runtime shard modules
(tests/test_cross_ai_selftest_<kind>_<i>_e2e.py) through the harness in tests/cross_ai_selftest.py.
This module keeps a smoke run of a rendered copy, the interrupt, load-factor and stop checks, the
dispatch e2e tests, and the checks that every case runs in exactly one shard.
"""

from __future__ import annotations

import contextlib
import glob
import io
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "skills", "ai-kit-gsd-curated-config"))
sys.path.insert(0, os.path.join(REPO_ROOT, "skills", "ai-kit-spec-review"))

from ai_kit_gsd_curated_config import cross_ai_script
from ai_kit_spec.detection import HOST_SIGNAL_ENV_VARS
from ai_kit_spec.execute_dispatch import (
    ExecuteDispatchSpec,
    ExecuteSeams,
    dispatch_execute,
)
from ai_kit_spec.reviewer_dispatch import (
    ReviewerDispatchSpec,
    ReviewerSeams,
    dispatch_reviewer,
)
from ai_kit_spec.runner_dispatch import RunnerSeams, RunnerSpec, run_runner

from tests.cross_ai_selftest import (
    _LIVE_GROUPS,
    LIST_TIMEOUT_SECS,
    MAX_LOAD_FACTOR,
    SHARD_COUNTS,
    SHARD_GUARD_SECS,
    SHARD_MODULE,
    STOP_GRACE_SECS,
    TEMPLATE,
    _load_runner,
    _real_node_executable,
    assert_factor_printed,
    guard_secs,
    list_cases,
    load_factor,
    load_reading,
    recorded_secs,
    run_cases,
    run_group,
    runner_env,
    setUpModule,  # noqa: F401  (unittest's module fixture: SIGTERM forwarding)
    split_cases,
    start_group,
    stop_group,
)
```

#### file: tmp/quick-xai-split/e2e_shard_classes.txt (L6)

```python
class ShardCoverageTest(unittest.TestCase):
    """Every listed self-test case has a kind and runs in exactly one shard (quick 261104-cxr)."""

    @classmethod
    def setUpClass(cls):
        cls._skip = None
        if _real_node_executable() is None:
            cls._skip = "no node executable"
        elif shutil.which("git") is None:
            cls._skip = "git not on PATH"

    def setUp(self):
        if self._skip:
            self.skipTest(self._skip)

    def test_every_case_runs_in_exactly_one_shard(self):
        listed = list_cases()
        names = [name for name, _kind in listed]
        self.assertEqual(len(names), len(set(names)), "duplicate case names")
        self.assertEqual({kind for _name, kind in listed}, set(SHARD_COUNTS))
        secs = recorded_secs()
        placed: list[str] = []
        for kind, count in SHARD_COUNTS.items():
            of_kind = [name for name, case_kind in listed if case_kind == kind]
            shards = split_cases(of_kind, count, secs)
            self.assertEqual(len(shards), count)
            self.assertTrue(all(shards), f"an empty {kind} shard: {shards}")
            placed += [name for shard in shards for name in shard]
        self.assertEqual(sorted(placed), sorted(names))

    def test_a_case_without_a_kind_fails_the_listing(self):
        node_bin = _real_node_executable()
        assert node_bin is not None
        with open(TEMPLATE, encoding="utf-8") as handle:
            text = handle.read()
        broken, count = re.subn(r"^[ ]*kind: 'logic',\n", "", text, count=1, flags=re.MULTILINE)
        self.assertEqual(count, 1)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "cross-ai.mjs")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(broken)
            proc = subprocess.run(
                [node_bin, path, "--self-test-list"],
                cwd=tmp,
                env=runner_env(tmp),
                capture_output=True,
                text=True,
                timeout=LIST_TIMEOUT_SECS,
                check=False,
            )
        self.assertEqual(proc.returncode, 2, msg=proc.stderr)
        self.assertIn("self-test: case without a logic or runtime kind: ", proc.stderr)
        self.assertEqual(proc.stdout, "")


class ShardSplitTest(unittest.TestCase):
    """The split is deterministic and the shard modules on disk match SHARD_COUNTS."""

    def test_split_is_greedy_longest_first(self):
        secs = {"a": 10, "b": 10, "c": 1, "d": 1}
        self.assertEqual(split_cases(["a", "b", "c", "d"], 2, secs), [["a", "c"], ["b", "d"]])

    def test_an_unrecorded_case_weighs_the_median(self):
        # x weighs 3 (the median of 4, 1, 3); at 1 or 0 it would land beside a, at 4 beside b
        secs = {"a": 4, "b": 1, "c": 3}
        self.assertEqual(split_cases(["a", "b", "c", "x"], 2, secs), [["a", "b"], ["c", "x"]])

    def test_every_name_lands_once(self):
        names = [f"n{i}" for i in range(10)]
        shards = split_cases(names, 3, {})
        self.assertEqual(len(shards), 3)
        self.assertEqual(sorted(name for shard in shards for name in shard), sorted(names))

    def test_shard_modules_match_the_counts(self):
        expected = {
            SHARD_MODULE.format(kind=kind, index=index): (kind, index)
            for kind, count in SHARD_COUNTS.items()
            for index in range(1, count + 1)
        }
        pattern = os.path.join(REPO_ROOT, "tests", "test_cross_ai_selftest_*_e2e.py")
        on_disk = {"tests." + os.path.basename(path)[:-3] for path in glob.glob(pattern)}
        self.assertEqual(on_disk, set(expected))
        e2e_modules = _load_runner().E2E_MODULES
        for module, (kind, index) in expected.items():
            self.assertIn(module, e2e_modules)
            with open(os.path.join(REPO_ROOT, *module.split(".")) + ".py", encoding="utf-8") as f:
                self.assertIn(f'shard_case("{kind}", {index})', f.read())
```

#### file: tmp/quick-xai-split/assemble.py (L7)

```python
"""Quick 261104-cxr Task 2: move tests/test_cross_ai_runner_e2e.py onto the shared harness.

python3 tmp/quick-xai-split/assemble.py tests/test_cross_ai_runner_e2e.py   (from the checkout root)
Reads e2e_head.txt and e2e_shard_classes.txt beside this script. Each edit replaces one exact,
unique snippet; the script stops before writing anything when one is missing.
"""
import pathlib
import sys

HERE = pathlib.Path(__file__).parent
TARGET = pathlib.Path(sys.argv[1])


def swap(text, old, new, count=1):
    if text.count(old) != count:
        sys.exit(f"expected {count} match(es) for: {old[:120]!r}")
    return text.replace(old, new)


src = TARGET.read_text(encoding="utf-8")
if "from tests.cross_ai_selftest import" in src:
    sys.exit("already assembled")
head = (HERE / "e2e_head.txt").read_text(encoding="utf-8").rstrip("\n") + "\n\n"
classes = (HERE / "e2e_shard_classes.txt").read_text(encoding="utf-8").rstrip("\n") + "\n\n\n"
text = head + src[src.index('_FAKE_OPENCODE = """'):]

text = swap(text, '''    def test_self_test(self):
        node_bin = _real_node_executable()
        assert node_bin is not None
        reading = load_reading()
        with tempfile.TemporaryDirectory() as tmp:
            env = {**runner_env(tmp), "AIKIT_XAI_SELFTEST_LOAD": repr(reading)}
            proc = run_group(
                [node_bin, TEMPLATE, "--self-test"],
                guard_secs(SELF_TEST_GUARD_SECS, load_factor(reading)),
                cwd=REPO_ROOT,
                env=env,
            )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertIn("self-test ok", proc.stdout)
        assert_factor_printed(self, proc.stderr, reading)

''', "")

text = swap(text, 'f"{__name__}._load_runner"', '"tests.cross_ai_selftest._load_runner"', count=3)

text = swap(text, '''class DeadlineCouplingTest(unittest.TestCase):
    """The runner's deadline for this module covers the load-scaled guards (D-10)."""

    def test_runner_deadline_covers_scaled_guards(self):
        runner = _load_runner()
        need = MAX_LOAD_FACTOR * (SELF_TEST_GUARD_SECS + RENDER_SELF_TEST_GUARD_SECS) + 600
        self.assertGreaterEqual(runner.module_timeout_secs(__name__), need)
        self.assertGreater(runner.MODULE_STOP_GRACE_SECS, STOP_GRACE_SECS)
''', '''class DeadlineCouplingTest(unittest.TestCase):
    """The runner's one module deadline covers a load-scaled shard guard (D-10)."""

    def test_runner_deadline_covers_scaled_guards(self):
        runner = _load_runner()
        need = MAX_LOAD_FACTOR * SHARD_GUARD_SECS + 300
        self.assertGreaterEqual(runner.MODULE_TIMEOUT_SECS, need)
        self.assertGreater(runner.MODULE_STOP_GRACE_SECS, STOP_GRACE_SECS)
''')

text = swap(text, '''    def test_render_and_self_test(self):
        node_bin = _real_node_executable()
        assert node_bin is not None
        with tempfile.TemporaryDirectory() as tmp:
''', '''    def test_render_and_self_test(self):
        with tempfile.TemporaryDirectory() as tmp:
''')

text = swap(text, '''            self.assertEqual(cross_ai_script.script_state(written), "pristine")
            # The self-test alone takes about 175 s and about 480 s beside the other e2e modules
            # on a host under memory pressure; 300 s timed out there (27-13 gate runs).
            reading = load_reading()
            proc = run_group(
                [node_bin, script_path, "--self-test"],
                guard_secs(RENDER_SELF_TEST_GUARD_SECS, load_factor(reading)),
                cwd=tmp,
                env={**runner_env(tmp), "AIKIT_XAI_SELFTEST_LOAD": repr(reading)},
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)
            assert_factor_printed(self, proc.stderr, reading)
''', '''            self.assertEqual(cross_ai_script.script_state(written), "pristine")
            # The full self-test runs in the shard modules; the rendered copy runs a smoke set.
            proc, reading = run_cases(SMOKE_CASES, template=script_path, cwd=tmp)
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)
            self.assertIn("self-test ok", proc.stdout)
            assert_factor_printed(self, proc.stderr, reading)
''')

smoke = (
    "# One case per area the rendered copy could break: a pi run, quota, an exec argv, a hang\n"
    "# (real clock) and the load-factor math.\n"
    'SMOKE_CASES = ("ok", "quota", "argv-exec-pi", "hang", "load-factor-math")\n\n\n'
)
anchor = "class TestRenderedRunner(unittest.TestCase):\n"
text = swap(text, anchor, classes + smoke + anchor)

TARGET.write_text(text, encoding="utf-8")
print("assembled", TARGET)
```

#### file: tmp/quick-xai-split/edit_runner_modules.py (L8)

```python
"""Quick 261104-cxr Task 2: add the eight shard modules to E2E_MODULES. Run from the checkout root."""
import sys

PATH = "tools/run_unittest_parallel.py"
OLD = '    "tests.test_cross_ai_runner_e2e",\n'
NEW = OLD + "    # the runner template's self-test, split by kind into timed shards (quick 261104-cxr)\n" + "".join(
    f'    "tests.test_cross_ai_selftest_{kind}_{index}_e2e",\n'
    for kind in ("logic", "runtime")
    for index in range(1, 5)
)

with open(PATH, encoding="utf-8") as handle:
    text = handle.read()
if "tests.test_cross_ai_selftest_logic_1_e2e" in text:
    sys.exit("the shard modules are already listed")
if text.count(OLD) != 1:
    sys.exit(f"expected exactly one match for: {OLD!r}")
with open(PATH, "w", encoding="utf-8") as handle:
    handle.write(text.replace(OLD, NEW))
print(f"added 8 shard modules to E2E_MODULES in {PATH}")
```

#### file: tmp/quick-xai-split/edit_task3.py (L9)

```python
"""Quick 261104-cxr Task 3: the runner's one deadline and submit order, plus the test edits.

python3 tmp/quick-xai-split/edit_task3.py   (run from the checkout root)
Each edit replaces one exact, unique snippet; the script stops before writing anything when one
is missing, so a partial run never happens.
"""
import sys

RUNNER = "tools/run_unittest_parallel.py"
RUNNER_TEST = "tests/test_run_unittest_parallel.py"
STAGED_E2E = "tests/test_staged_commit_e2e.py"
MAPPER_TEST = "tests/test_staged_mapper.py"

EDITS = {
    RUNNER: [
        ("deadline (module_timeout_secs); exits 130 when",
         "deadline (MODULE_TIMEOUT_SECS); exits 130 when"),
        ("forward SIGTERM to it (tests/test_cross_ai_runner_e2e.py\ndoes).",
         "forward SIGTERM to it (tests/cross_ai_selftest.py\ndoes)."),
        ("from types import FrameType, MappingProxyType, ModuleType\n",
         "from types import FrameType, ModuleType\n"),
        ("# A hung module fails the gate instead of hanging it; generous for slow machines.\n"
         "MODULE_TIMEOUT_SECS = 900\n"
         "# The self-test module runs the full runner self-test twice, each guarded by a hang guard"
         " sized\n"
         "# from one load reading (300 s and 900 s at idle, times the 1..4 load factor):"
         " 4 x (300 + 900) s\n"
         "# plus 600 s for the rest of the module. Its own guards fire first. A real hang of this"
         " module can\n"
         "# therefore hold `make e2e-test` for up to 5400 s at the 4x cap (1200 s plus the rest at"
         " idle).\n"
         "SELF_TEST_MODULE_TIMEOUT_SECS = 5400\n"
         "MODULE_TIMEOUT_OVERRIDES = MappingProxyType({\n"
         '    "tests.test_cross_ai_runner_e2e": SELF_TEST_MODULE_TIMEOUT_SECS,\n'
         "})\n",
         "# A hung module fails the gate instead of hanging it; generous for slow machines. It is the"
         " one\n"
         "# deadline for every module; the runner self-test shards size their guards under it.\n"
         "MODULE_TIMEOUT_SECS = 900\n"),
        ("def module_timeout_secs(module: str) -> int:\n"
         '    """The deadline of `module`; the global is read at call time so a test can patch'
         ' it."""\n'
         "    return MODULE_TIMEOUT_OVERRIDES.get(module, MODULE_TIMEOUT_SECS)\n\n\n",
         ""),
        ("rc, output = _communicate(proc, module_timeout_secs(module))",
         "rc, output = _communicate(proc, MODULE_TIMEOUT_SECS)"),
        ("rc, output = _communicate(proc, sum(module_timeout_secs(m) for m in modules))",
         "rc, output = _communicate(proc, MODULE_TIMEOUT_SECS * len(modules))"),
        ("    with ThreadPoolExecutor(max_workers=workers) as pool:\n"
         "        futures = [pool.submit(run_module, m, cwd) for m in modules]\n",
         "    # Longest recorded e2e module first, so a slow one never starts last (a stable sort).\n"
         "    ordered = sorted(modules, key=lambda m: -E2E_RECORDED_SECS.get(m, 0))\n"
         "    with ThreadPoolExecutor(max_workers=workers) as pool:\n"
         "        futures = [pool.submit(run_module, m, cwd) for m in ordered]\n"),
    ],
    RUNNER_TEST: [
        ("    def test_self_test_module_gets_the_long_deadline_others_the_global(self) -> None:\n"
         "        r = self.runner\n"
         "        self.assertEqual(r.SELF_TEST_MODULE_TIMEOUT_SECS, 5400)\n"
         "        self.assertEqual(\n"
         '            r.module_timeout_secs("tests.test_cross_ai_runner_e2e"),'
         " r.SELF_TEST_MODULE_TIMEOUT_SECS\n"
         "        )\n"
         '        self.assertEqual(r.module_timeout_secs("tests.test_arch"), r.MODULE_TIMEOUT_SECS)\n'
         '        with unittest.mock.patch.object(r, "MODULE_TIMEOUT_SECS", 0.01):\n'
         '            self.assertEqual(r.module_timeout_secs("tests.test_arch"), 0.01)\n',
         "    def test_every_module_gets_the_one_global_deadline(self) -> None:\n"
         "        # The self-test shards size their hang guards under this one deadline\n"
         "        # (DeadlineCouplingTest in tests/test_cross_ai_runner_e2e.py); no module has its"
         " own.\n"
         "        self.assertEqual(self.runner.MODULE_TIMEOUT_SECS, 900)\n"),
        ("class ModuleDeadlineTest(unittest.TestCase):\n",
         "class RunAllOrderTest(unittest.TestCase):\n"
         '    """The pool starts the longest recorded e2e module first; the others keep their'
         ' order."""\n'
         "\n"
         "    def test_the_longest_recorded_module_is_submitted_first(self) -> None:\n"
         "        runner = load_runner()\n"
         "        seen: list[str] = []\n"
         "\n"
         "        def fake_run(module, _cwd):\n"
         "            seen.append(module)\n"
         '            return module, 0, "", 0.0\n'
         "\n"
         '        table = {"tests.b": 5, "tests.c": 50}\n'
         "        with (\n"
         '            unittest.mock.patch.object(runner, "run_module", fake_run),\n'
         '            unittest.mock.patch.object(runner, "worker_count", return_value=1),\n'
         '            unittest.mock.patch.object(runner, "E2E_RECORDED_SECS", table),\n'
         "            contextlib.redirect_stdout(io.StringIO()),\n"
         "        ):\n"
         '            failed = runner._run_all(["tests.a", "tests.b", "tests.c", "tests.d"])\n'
         "        self.assertEqual(failed, [])\n"
         '        self.assertEqual(seen, ["tests.c", "tests.b", "tests.a", "tests.d"])\n'
         "\n"
         "\n"
         "class ModuleDeadlineTest(unittest.TestCase):\n"),
    ],
    STAGED_E2E: [
        ("def build_repo(root: pathlib.Path) -> Repo:\n",
         "def defer_one(path: pathlib.Path) -> None:\n"
         '    """Drop the largest recorded time from the copied runner at `path`: the copy then'
         " always\n"
         '    defers one e2e module to push, whatever the real table holds."""\n'
         "    table = load_by_path(path).E2E_RECORDED_SECS\n"
         "    module = max(sorted(table), key=table.__getitem__)\n"
         "    line = f'    \"{module}\": {table[module]},\\n'\n"
         '    text = path.read_text(encoding="utf-8")\n'
         "    assert text.count(line) == 1, line\n"
         '    path.write_text(text.replace(line, ""), encoding="utf-8")\n'
         "\n"
         "\n"
         "def build_repo(root: pathlib.Path) -> Repo:\n"),
        ("    shutil.copy(RUNNER, root / \"tools\" / RUNNER.name)\n"
         "    shutil.copy(MAPPER, root / \"tools\" / MAPPER.name)\n",
         "    shutil.copy(RUNNER, root / \"tools\" / RUNNER.name)\n"
         "    defer_one(root / \"tools\" / RUNNER.name)\n"
         "    shutil.copy(MAPPER, root / \"tools\" / MAPPER.name)\n"),
    ],
    MAPPER_TEST: [
        ('WITHIN = "tests.test_precompact_shims_e2e"  # recorded at 58 s: within the budget',
         'WITHIN = "tests.test_precompact_shims_e2e"  # patched to 58 s below: within the budget'),
        ('OVER = "tests.test_cross_ai_runner_e2e"  # recorded at 361 s: over it',
         'OVER = "tests.test_cross_ai_runner_e2e"  # patched to 361 s below: over it'),
    ],
}

texts = {}
for path, edits in EDITS.items():
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    for old, new in edits:
        if text.count(old) != 1:
            sys.exit(f"{path}: expected exactly one match for: {old!r}")
        text = text.replace(old, new)
    texts[path] = text
for path, text in texts.items():
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    print(f"edited {path} ({len(EDITS[path])} edits)")
```

#### file: tmp/quick-xai-split/run_e2e_group.sh (L10)

```sh
#!/bin/sh
# Quick 261104-cxr: one timed `--group e2e` run from the checkout root.
# Usage: sh tmp/quick-xai-split/run_e2e_group.sh OUTFILE
out="$1"
export AI_KIT_REFUSE_REAL_HOME=1
echo "meta date=$(date +%F) cpus=$(nproc) load1=$(cut -d' ' -f1 /proc/loadavg)" > "$out"
start=$(date +%s)
uv run python tools/run_unittest_parallel.py --group e2e >> "$out" 2>&1
rc=$?
echo "wall $(( $(date +%s) - start )) s rc $rc" >> "$out"
exit "$rc"
```

#### file: tmp/quick-xai-split/refresh_recorded.py (L11)

```python
"""Rewrite E2E_RECORDED_SECS in tools/run_unittest_parallel.py from one timed e2e log.

python3 tmp/quick-xai-split/refresh_recorded.py tmp/quick-xai-split/e2e_group.txt
Run from the checkout root. Values are whole seconds rounded up (at least 1); the table
comment's parenthetical gets the date, CPU count and start load from the log's `meta` line.
"""
import importlib.util
import math
import re
import sys

RUNNER = "tools/run_unittest_parallel.py"
with open(sys.argv[1], encoding="utf-8") as handle:
    log = handle.read()
if re.search(r"^=== \S+: FAILED", log, re.MULTILINE):
    sys.exit("the e2e run has a failed module: fix it before refreshing the table")
times = {module: max(1, math.ceil(float(secs))) for module, secs in
         re.findall(r"^=== (tests\.\S+): ok in ([\d.]+)s", log, re.MULTILINE)}
meta = re.search(r"^meta date=(\S+) cpus=(\d+) load1=([\d.]+)$", log, re.MULTILINE)
if meta is None:
    sys.exit("the log has no meta line")
spec = importlib.util.spec_from_file_location("rup", RUNNER)
assert spec is not None and spec.loader is not None
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
if set(times) != set(runner.E2E_MODULES):
    sys.exit(f"modules differ: missing {sorted(set(runner.E2E_MODULES) - set(times))}, "
             f"extra {sorted(set(times) - set(runner.E2E_MODULES))}")
with open(RUNNER, encoding="utf-8") as handle:
    source = handle.read()
block = ("E2E_RECORDED_SECS = {\n"
         + "".join(f'    "{module}": {times[module]},\n' for module in sorted(times)) + "}\n")
source, tables = re.subn(r"^E2E_RECORDED_SECS = \{\n(?:    .*\n)*?\}\n", block, source,
                         count=1, flags=re.MULTILINE)
date, cpus, load1 = meta.groups()
source, notes = re.subn(r"\(\d{4}-\d{2}-\d{2}, \d+ CPUs, one-minute load [\d.]+ at start\)",
                        f"({date}, {cpus} CPUs, one-minute load {float(load1):.2f} at start)",
                        source, count=1)
if (tables, notes) != (1, 1):
    sys.exit(f"replaced {tables} tables and {notes} notes, expected 1 and 1")
with open(RUNNER, "w", encoding="utf-8") as handle:
    handle.write(source)
for module in sorted(times):
    print(f"{module}: {times[module]}")
```

#### file: tmp/quick-xai-split/edit_docs.py (L12)

```python
"""Quick 261104-cxr: put the new push-timing record and the shard note into AGENTS.md and README.md.

python3 tmp/quick-xai-split/edit_docs.py tmp/quick-xai-split/prepush.txt   (from the checkout root)
Reads the last `push-timing` line, rewrites AGENTS.md's Push timing bullet (and adds the shard
bullet after it) and README.md's push paragraph. Stops before writing when a field or an anchor
is missing.
"""
import re
import sys
import textwrap

with open(sys.argv[1], encoding="utf-8") as handle:
    lines = [line for line in handle if line.startswith("push-timing ")]
if not lines:
    sys.exit("no push-timing line")
rec = lines[-1]
PATTERN = (r"date=(?P<date>\S+) cpus=(?P<cpus>\d+) load1=(?P<load1>[\d.]+) share=(?P<share>[\d.]+)"
           r" core=(?P<core>[\d.]+)s\(rc=0, [^)]*workers=(?P<w1>\d+)\)"
           r" wizard=(?P<wizard>[\d.]+)s\(rc=0, [^)]*workers=(?P<w2>\d+)\)"
           r" test-hooks=(?P<total>[\d.]+)s limit=[\d.]+s"
           r" pyright=(?P<pyright>[\d.]+)s\(rc=0\) vulture=(?P<vulture>[\d.]+)s\(rc=0\)"
           r" dogfood=(?P<dogfood>[\d.]+)s\(rc=0\)"
           r" deferred-e2e=(?P<deferred>[\d.]+)s\(rc=0, (?P<ran>\d+)/(?P<of>\d+), no range\)"
           r" push-worst=(?P<worst>[\d.]+)s verdict=(?P<verdict>\S+)")
match = re.search(PATTERN, rec)
if match is None:
    sys.exit(f"cannot parse (a hook failed, or the format changed): {rec}")
f = match.groupdict()
if f["verdict"] != "pass":
    sys.exit(f"verdict {f['verdict']}: report it instead of documenting it")
none_deferred = f["of"] == "0"
deferred_note = "no push range; no e2e module is over the commit budget" if none_deferred \
    else "no push range"


def wrap(text, width, first, rest):
    # \x00 keeps a number and its " s" unit on one line; it turns back into a space after fill
    glued = re.sub(r"(\d) s\b", "\\1\x00s", text)
    filled = textwrap.fill(glued, width=width, initial_indent=first, subsequent_indent=rest,
                           break_on_hyphens=False, break_long_words=False)
    return filled.replace("\x00", " ") + "\n"


AGENTS_OLD_START = "- Push timing: the 60 s target covers the two test hooks only, their subtotal,\n"
AGENTS_OLD_END = "  push: 420.2 s.\n"
agents_new = wrap(
    "Push timing: the 60 s target covers the two test hooks only, their subtotal, measured back "
    "to back by `python3 tools/time_prepush.py` at the default 40 % share. Before this phase they "
    "took 183.9 s (2026-11-03: 24 CPUs, 9 workers, one-minute load 1.86 at start); after this "
    f"phase and the runner self-test split they took {f['total']} s ({f['date']}: {f['cpus']} "
    f"CPUs, {f['w1']} and {f['w2']} workers, share {f['share']}, one-minute load {f['load1']} at "
    f"start; unit and arch {f['core']} s, wizard {f['wizard']} s). The pyright "
    f"({f['pyright']} s), vulture ({f['vulture']} s), check-dogfood ({f['dogfood']} s) and "
    f"deferred-e2e ({f['deferred']} s, {deferred_note}) times are recorded beside the subtotal, "
    "never inside the 60 s figure, with `push-worst` (all six pre-push hooks timed alone, "
    "deferred-e2e at its no-range worst case) as the worst-case whole push: "
    f"{f['worst']} s.", 82, "- ", "  ") + wrap(
    "Runner self-test shards: `cross-ai.mjs --self-test-list` prints every self-test case as "
    "`name<TAB>kind`, `logic` or `runtime` (a case that waits on or measures a real clock is "
    "`runtime`). `tests/cross_ai_selftest.py` deals each kind, longest first by the generated "
    "`tests/fixtures/cross_ai_selftest_secs.json`, into the "
    "`tests/test_cross_ai_selftest_<kind>_<i>_e2e.py` shard modules, so each fits the commit "
    "budget and a template change runs its shards at commit. Refresh that file with "
    "`python3 tests/cross_ai_selftest.py --record-times` on a quiet machine after adding or "
    "slowing a case.", 82, "- ", "  ")

README_OLD = (
    "`python3 tools/time_prepush.py`): before this phase they took 183.9 s (2026-11-03),\n"
    "after it 55.5 s (2026-11-04). pyright (9.9 s), vulture (1.9 s), check-dogfood (0.5 s)\n"
    "and deferred-e2e (352.4 s, no push range) are recorded beside that subtotal, and the\n"
    "worst-case whole push (`push-worst`, every pre-push hook timed alone) is 420.2 s.\n"
)
readme_new = wrap(
    "`python3 tools/time_prepush.py`): before this phase they took 183.9 s (2026-11-03), after "
    f"it {f['total']} s ({f['date']}). pyright ({f['pyright']} s), vulture ({f['vulture']} s), "
    f"check-dogfood ({f['dogfood']} s) and deferred-e2e ({f['deferred']} s, {deferred_note}) are "
    "recorded beside that subtotal, and the worst-case whole push (`push-worst`, every pre-push "
    f"hook timed alone) is {f['worst']} s.", 84, "", "")

with open("AGENTS.md", encoding="utf-8") as handle:
    agents = handle.read()
start = agents.find(AGENTS_OLD_START)
end = agents.find(AGENTS_OLD_END, start)
if start < 0 or end < 0 or agents.count(AGENTS_OLD_START) != 1:
    sys.exit("AGENTS.md: the Push timing bullet anchors are missing")
agents = agents[:start] + agents_new + agents[end + len(AGENTS_OLD_END):]
with open("README.md", encoding="utf-8") as handle:
    readme = handle.read()
if readme.count(README_OLD) != 1:
    sys.exit("README.md: the push timing sentence is missing")
readme = readme.replace(README_OLD, readme_new)
with open("AGENTS.md", "w", encoding="utf-8") as handle:
    handle.write(agents)
with open("README.md", "w", encoding="utf-8") as handle:
    handle.write(readme)
print("AGENTS.md and README.md updated from:", rec.strip())
```

#### file: tmp/quick-xai-split/commit1.txt (L13)

```text
feat(cross-ai): tag self-test cases logic or runtime and list them

Every runner self-test case now carries kind 'logic' or 'runtime' (a case that waits on or
measures a real clock is runtime). --self-test-list prints name<TAB>kind; the self-test exits 2
on a case without a kind or a duplicate name. .planning/scripts/cross-ai.mjs is re-rendered
through ensure-runner.
```

#### file: tmp/quick-xai-split/commit2.txt (L14)

```text
test(cross-ai): split the runner self-test into timed logic and runtime shards

tests.test_cross_ai_runner_e2e ran the full self-test twice (366 s), so every template change
deferred it to push. tests/cross_ai_selftest.py now deals each kind from --self-test-list into
four shard modules, longest first by a generated timing fixture; the module keeps a smoke run
of a rendered copy. The runner submits e2e modules longest-recorded first and drops the
self-test deadline override; the staged-commit e2e copy defers one module itself.
```

</listings>
