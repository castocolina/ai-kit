---
phase: quick-261104-hzc
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - tests/test_run_unittest_parallel.py
  - tests/test_claude_session_wake_hook.py
  - tests/cursor_fakes.py
  - tests/test_ai_kit_session_wake_fire.py
  - tests/test_precompact_core.py
  - tests/test_ai_kit_spec_runner_dispatch.py
  - tests/test_arch.py
  - tests/test_jev_fast_decision.py
  - tests/fixtures/precompact/run_shim.mjs
  - tests/test_precompact_shims_e2e.py
  - tests/test_ai_kit_project_rules_all_e2e.py
  - tests/test_wizard_pty.py
  - tests/test_wizard_app.py
  - tests/test_wizard_app_1.py
  - tests/test_wizard_app_2.py
  - tests/test_wizard_app_3.py
  - tests/wizard_app_common.py
  - tests/test_system_memory_e2e.py
  - tests/test_staged_mapper.py
  - tools/run_unittest_parallel.py
  - tools/staged_mapper.py
  - Makefile
  - .pre-commit-config.yaml
  - AGENTS.md
autonomous: true
requirements: [quick-261104-hzc]

estimate:
  tokens: 150000
  raw_tokens: 150000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "Every touched module passes when run alone through tools/run_unittest_parallel.py. No test is dropped except test_opencode_messages_hang_finishes_within_11s, whose hang run duplicated the hang case of test_opencode_messages_failure_untouched (merged into it)"
    - "Every scaled production timer has a static pin that fails when the real constant changes: shims TIMEOUT_MS 10000 (pi, opencode precompact) and 2000 (pi tool-advisor, tool-reminder) with the scale knob absent from every shim; wake hook HOOK_DEADLINE_S 8.0, HOOK_MIN_CHILD_S 1.0, _STDIN_TOTAL_SECONDS 5.0, 8 - 5 >= 1 and 8 < the registered 10 s; runner MODULE_STOP_GRACE_SECS 15 (900 s deadline already pinned); runner_dispatch _TERM_GRACE_S 4 and _DRAIN_S 2"
    - "tests.test_ai_kit_project_rules_all_e2e links the real node binary and asserts the identity probe answered (R18 and R19 status `missing`, no `unverified` key); no test waits a 5 s probe timeout"
    - "tests/test_wizard_app.py is replaced by tests/test_wizard_app_1.py, _2.py, _3.py (22 tests each, 66 in total) that share tests/wizard_app_common.py; INTEGRATION_MODULES and the regenerated Makefile and .pre-commit-config.yaml listings name the three, and no file under tools/ or tests/, the Makefile, the hook config, AGENTS.md or README.md names the old module"
    - "Staging AGENTS.md selects 13 modules instead of 16 (no longer tests.test_wizard_pty, tests.test_ai_kit_project_rules_all_e2e or tests.test_ai_kit_spec); staging tools/command_ownership.py still selects tests.test_setup"
    - "E2E_RECORDED_SECS holds the times of one --group e2e run made after the cuts, every value at most 60; tmp/quick-test-cuts/timings-task1.txt, -task2.txt and -task3.txt hold before and after walls for every touched module and the docs-only `--staged AGENTS.md` wall"
  artifacts:
    - path: tests/fixtures/precompact/run_shim.mjs
      provides: "AI_KIT_SHIM_TIME_SCALE wraps setTimeout before the shim loads (tests only)"
      contains: "AI_KIT_SHIM_TIME_SCALE"
    - path: tests/test_precompact_shims_e2e.py
      provides: "Scaled hang tests and TestShimDeadlinePins"
      contains: "class TestShimDeadlinePins"
    - path: tests/test_claude_session_wake_hook.py
      provides: "_DRIVER with a 1 s deadline and TestHookDeadlinePins"
      contains: "class TestHookDeadlinePins"
    - path: tests/wizard_app_common.py
      provides: "HAVE_TEXTUAL and query_static for the three wizard parts"
      contains: "def query_static"
    - path: tools/staged_mapper.py
      provides: "DATA_SUFFIXES, code_text and data-file covering in code only"
      contains: "def code_text"
    - path: tools/run_unittest_parallel.py
      provides: "The three wizard parts in INTEGRATION_MODULES and the refreshed E2E_RECORDED_SECS"
      contains: "tests.test_wizard_app_3"
  key_links:
    - from: tests/test_precompact_shims_e2e.py
      to: tests/fixtures/precompact/run_shim.mjs
      via: "SCALE_ENV passes AI_KIT_SHIM_TIME_SCALE to the harness env"
      pattern: "SCALE_ENV"
    - from: tests/test_claude_session_wake_hook.py
      to: tools/hooks/claude_session_wake.py
      via: "_DRIVER imports the copied hook and overrides its module constants"
      pattern: "hook.HOOK_DEADLINE_S"
    - from: tools/staged_mapper.py
      to: tools/run_unittest_parallel.py
      via: "the runner's --staged mode loads the mapper by path and calls decide()"
      pattern: "def covering_modules"
    - from: tests/test_wizard_app_1.py
      to: tests/wizard_app_common.py
      via: "from tests.wizard_app_common import HAVE_TEXTUAL, query_static"
      pattern: "wizard_app_common"
---

<objective>
Apply the owner-approved test-time cuts (owner items 1-13, 2026-11-04) from
`tmp/test-audit/REPORT.md`, refresh the e2e commit budget table and update the docs.
Report finding 14 (claude_precompact real budget) is not applied. Every scaled timer keeps a
static pin of its production constant. No real behavior loses its only coverage.

Purpose: shorter tier walls and cheaper docs-only commits, with no claim weakened.
Output: 14 commits on branch `quick/261104-hzc` (Task 1: 8, Task 2: 4, Task 3: 2) and timing logs
under `tmp/quick-test-cuts/`. The orchestrator writes SUMMARY.md and STATE.md.
</objective>

<execution_context>
@.claude/gsd-core/workflows/execute-plan.md
@.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@AGENTS.md

Owner items (this plan's numbering) and the REPORT.md findings they come from:
1 shims e2e (finding 1), 2 project_rules_all e2e (2), 3 runner tests (4), 4 wake hook (5),
5 cursor fake dashboard (6), 6 wizard PTY (7), 7 wake fire (8), 8 precompact property (9),
9 spec dispatch (10), 10 wizard_app split (11), 11 arch cache (12), 12 jev matrix (13),
13 mapper data-file rule (the commit-time section), 14 budget table, pins and docs.
REPORT finding 3 (longest module first) is already in `_run_all` in
tools/run_unittest_parallel.py. Keep it and do not re-implement it.

Execution environment (every task; owner rules):
- You run in the git worktree `tmp/quick-test-cuts/wt` of the main checkout, on branch
  `quick/261104-hzc`, with cwd at the worktree root. Every path in this plan is relative to the
  repo root. The main checkout is the parent of
  `git rev-parse --path-format=absolute --git-common-dir`.
- Prefix every test, script and `git commit` command with `AI_KIT_REFUSE_REAL_HOME=1 ` (the
  shell keeps no variables between calls, and the commit hooks run tests).
- Multi-step shell lives in the `.py` files under `tmp/quick-test-cuts/` (inside the worktree).
  One-line commands are fine. No heredocs, no `cd <repo> &&` chains.
- The scripts are in the Appendix of this plan. Each one was dry-run, in task order, on a scratch
  copy of HEAD 01922d6, together with the module runs and lint below. Write each one with the
  Write tool, byte for byte, to the path its heading names. An `edits_task<N>.py` script applies
  exact (old, new, count) replacements. When an anchor count is wrong it writes nothing to that
  file, exits 1 and names the edit. If that happens, run `git diff -- <file>`. If the edits are
  already there, that step was done before: move on. Otherwise STOP and report: the tree differs
  from the one the plan was dry-run against. Do not hand-edit around it.
- Re-run only the affected modules (the commands given). Do NOT run `make test` or
  `make validate`. The orchestrator runs `make test`, `tools/time_prepush.py`,
  `tools/staged_mapper.py --stats` and the env matrix after merging.
- Stage files by explicit path only. Never use `git add -A` or `git add .`. Never use
  `--no-verify`. Never stage `.claude/` or `tmp/`. Do not commit SUMMARY.md, STATE.md or PLAN.md.
  If a commit hook fails: read which hook failed, fix the cause, re-run only that check's
  Makefile target (for example `make ruff`, `make pylint`, `make pyright`), then run the same
  `git commit` again.
- Never `git reset --hard`, `git clean -f`, `git checkout .`, `git restore .`; never push. Never
  touch the real `~/.claude`, `~/.cursor`, `~/.config/opencode`, `~/.codex` or `~/.pi`. Leave no
  stray process.
- The same failure 3 times without progress: stop and report. A step that takes more than
  twice its estimate: stop that step and report.
- jev: before you spend reasoning on a classify or decide question (a failure that may be
  environment noise, a deviation that may need the owner), follow the main checkout's
  `tmp/auto/jev-brief.md`. Answers are advisory. Verify each with one cheap check, then act. Put
  one line per call in your report: id, answer, confidence, what you did.
- English only in every file and commit message. Commit subjects are conventional, concise; a
  one-line body says why.

Facts established at planning time (live-verified 2026-11-04; do not re-derive):
- Runner CLI: `python3 tools/run_unittest_parallel.py MODULE [MODULE ...]` runs the named
  modules (unit and arch under system python3; integration and e2e under
  `uv run python tools/run_unittest_parallel.py MODULE ...`). Each module prints
  `=== <module>: ok in <s>s  Ran <n> tests ...` and the run ends with `<k>/<k> modules passed`.
  `--staged PATH ...` runs the commit hook's selection for those paths.
  `python3 tools/gen_test_groups.py` regenerates the Makefile and .pre-commit-config.yaml
  listings.
- Item 2 deviates from the owner's wording. jev c1 chose option b (0.99, TypeSafe, consent on
  record 2026-10-14). Measured: forwarding `tool_cache_forwards(os.environ)` into the cleared
  env changes nothing. The identity probe (`skills/_shared/ai_kit_rules_common/gsd_identity.py`,
  `_PROBE_ENV_KEYS`) passes node only PATH and HOME. The scratch HOME hides the Volta shim's
  toolchain, so the probe still timed out after 5 s. Linking the real node binary, resolved
  under the caller's env the way tests/test_precompact_shims_e2e.py `_node_bin()` already does,
  makes the probe answer in 0.1 s: `("ok", "runtime-identity names @opengsd/gsd-core", ...)`. With
  that answer, the scratch repo's R18 and R19 rows have status `missing`. With the timeout they
  were `not_applicable` with `unverified: true`. The new assertion checks exactly that.
- gsd-tools needs both `.claude/gsd-core` and `.claude/scripts`. Both are gitignored, so Step 0
  of every task copies them from the main checkout. Without them, the
  project_rules_all e2e classes skip and the probe fails with exit 1.
- Item 11: the parse cache saves about 0.8 s of arch test time (6.35 s to 5.58 s alone). That is
  less than REPORT.md's 4 s estimate, because tokenize and AST walks dominate. It is applied as
  asked.
- Item 13: the mapper decision for AGENTS.md goes from 0.6 s to 1.0 s (tokenizing only the
  modules whose full text names the file). `--stats` already takes about 30 s at HEAD, with or
  without this change. The data-file suffixes are `.md .json .jsonc .yaml .yml .toml .txt`, for
  paths whose first folder is not in the mapper's `UNIT_DIRS` (skills, tools, tests, .planning),
  the same split `--stats` already uses for its "data file" lines. Code files outside the unit
  folders (docs/wizard-redesign/prototypes/*.py, examples/segments/system_memory) keep today's
  matching.
- Dry run on a scratch copy of HEAD with other runs in parallel (so the times are loaded). Each
  line gives seconds before (REPORT.md) and after, and the test count after:
  run_unittest_parallel 25.5 -> 7.5 (53); claude_session_wake_hook 17.0 -> 3.3 (8);
  cursor_quota 11.4 -> 5.5 (37); session_wake_fire 18.9 -> 11.4 (45);
  precompact_core 13.2 -> 9.0 (52); spec_runner_dispatch 13.1 -> 7.4 (71);
  arch 6.5 -> about 5.6 alone (76); jev_fast_decision 17.7 -> 16.3 (156);
  precompact_shims_e2e 57.3 -> 12.4 (24); project_rules_all_e2e 25.7 -> 1.1 (5);
  wizard_pty 16.2 -> 7.6 (12); wizard_app 20.8 -> 4.9 / 8.0 / 9.7 for the three parts (22 each);
  `--staged AGENTS.md` 16 modules / 11.5 s -> 13 modules / 5.0 s.
  The e2e table refresh gave precompact_shims_e2e 13 and project_rules_all_e2e 1. ruff passed
  on tools, tests and skills. pylint on tools/staged_mapper.py: 10.00. pyright reported 0 errors
  on the changed files.
- Scratch-copy noise to expect: on a fresh `git init` copy, tests.test_pi_live_tools fails its
  digest check, because it reads git history. It passes at HEAD in the real checkout. In the
  worktree it should pass. If it fails there, classify it with jev, then run it in the main
  checkout to compare.
</context>

<tasks>

<task type="tracer">
  <name>Task 1: Unit-tier timing cuts (owner items 3, 4, 5, 7, 8, 9, 11, 12), 8 commits</name>
  <precondition>The worktree is on branch quick/261104-hzc at a commit that holds 01922d6, and `git status --short` prints nothing.</precondition>
  <files>tests/test_run_unittest_parallel.py, tests/test_claude_session_wake_hook.py, tests/cursor_fakes.py, tests/test_ai_kit_session_wake_fire.py, tests/test_precompact_core.py, tests/test_ai_kit_spec_runner_dispatch.py, tests/test_arch.py, tests/test_jev_fast_decision.py</files>
  <action>
The tracer is Step 3: the thinnest full path through this plan's loop. It covers the timing
log, one scripted edit, the per-module re-run, and a commit through the real pre-commit hook.
Tasks 2 and 3 repeat the same loop.

Step 0 (environment; one-line commands from the worktree root):
- `MAIN="$(dirname "$(git rev-parse --path-format=absolute --git-common-dir)")"; echo "$MAIN"; ls "$MAIN/tmp/auto/jev-brief.md"`
  prints the main checkout path and the jev brief path.
- `MAIN="$(dirname "$(git rev-parse --path-format=absolute --git-common-dir)")"; mkdir -p tmp/quick-test-cuts .claude; [ -d .claude/gsd-core ] || cp -a "$MAIN/.claude/gsd-core" .claude/; [ -d .claude/scripts ] || cp -a "$MAIN/.claude/scripts" .claude/`
- `git branch --show-current` prints `quick/261104-hzc`; `git status --short` prints nothing.

Step 1: with the Write tool, write `tmp/quick-test-cuts/time_modules.py` (Appendix A) and
`tmp/quick-test-cuts/edits_task1.py` (Appendix B). `python3 tmp/quick-test-cuts/edits_task1.py`
prints `files:` and the 8 file names, then exits 2.

Step 2 (before timings, about 2.5 min):
`AI_KIT_REFUSE_REAL_HOME=1 python3 tmp/quick-test-cuts/time_modules.py 1 before tests.test_run_unittest_parallel tests.test_claude_session_wake_hook tests.test_cursor_quota tests.test_cursor_status_line tests.test_cursor_fakes tests.test_ai_kit_session_wake_fire tests.test_precompact_core tests.test_ai_kit_spec_runner_dispatch tests.test_arch tests.test_jev_fast_decision`
prints 10 `before ... ok` lines and exits 0. If a module is not ok at this point, STOP and report:
the tree is red before any change.

Step 3 (tracer, item 3: runner tests). Run `python3 tmp/quick-test-cuts/edits_task1.py tests/test_run_unittest_parallel.py`.
It prints `applied 5 edits`. The edits:
- test_arch_group_passes runs `runner.main(["--group", "arch"], tmp)` on a one-test
  tests/test_arch.py in a temp folder, not the full arch module.
- The three stop tests use a 1.0 s deadline and a 0.5 s grace. The grandchild test now asserts
  `timed out after 1.0s`.
- A new pin test asserts `MODULE_STOP_GRACE_SECS == 15`.
- `_run_all`'s longest-first order is untouched.
Then:
`AI_KIT_REFUSE_REAL_HOME=1 python3 tools/run_unittest_parallel.py tests.test_run_unittest_parallel`
must print `1/1 modules passed` and `Ran 53 tests`. Commit:
`git add tests/test_run_unittest_parallel.py` then
`AI_KIT_REFUSE_REAL_HOME=1 git commit -m "test(runner): one-test arch group and second-scale stop deadlines" -m "The arch tier already runs the real module; the stop tests keep their claims at a 1 s deadline and 0.5 s grace, and the real 15 s grace is pinned."`

Steps 4-10. Do the same three moves for each row: apply with
`python3 tmp/quick-test-cuts/edits_task1.py <file>`, re-run with
`AI_KIT_REFUSE_REAL_HOME=1 python3 tools/run_unittest_parallel.py <modules>`, then stage the
file by path and commit with the subject given.
- Item 4, tests/test_claude_session_wake_hook.py (applied 6 edits). Re-run
  tests.test_claude_session_wake_hook: Ran 8 tests (7 plus the pin). The edits:
  - The deadline tests run `drive_hook.py` (`_DRIVER`). It imports the copied hook and sets
    HOOK_DEADLINE_S 1.0, HOOK_MIN_CHILD_S 0.2 and `_session_start._STDIN_TOTAL_SECONDS` 0.3.
  - The trickle drips every 0.1 s.
  - The walls are asserted below 2.0 s.
  - TestHookDeadlinePins reads the real constants with ast, because importing the hook would
    replace this process's excepthook. It asserts 8.0, 1.0 and 5.0, that 8 - 5 >= 1, and that
    8 < the `session-wake` row timeout loaded from tools/setup.py.
  Subject: `test(session-wake): drive the StopFailure hook with a 1 s deadline; pin the real 8 s`.
- Item 5, tests/cursor_fakes.py (applied 1 edits). `serve_forever` gets
  `kwargs={"poll_interval": 0.05}`, as tests/test_jev_fast_decision.py already does. Re-run
  tests.test_cursor_quota tests.test_cursor_status_line tests.test_cursor_fakes: 3/3 modules
  passed, with Ran 37, 13 and 6 tests. Subject:
  `test(cursor): poll the fake dashboard every 0.05 s`. This is a shared helper, so the commit
  hook runs the full unit and arch groups (about 1 min).
- Item 7, tests/test_ai_kit_session_wake_fire.py (applied 3 edits; the hold change replaces 3
  lines). FAKE_HOST_SLEEP goes from 5 to 1.5 and the three lock holds from 2.0 to 0.5. The
  disarm wait asserts elapsed >= 0.4, which stays below the 0.5 s hold. Re-run
  tests.test_ai_kit_session_wake_fire: Ran 45 tests. Subject:
  `test(session-wake): shorter lock holds and fake host sleep in the fire tests`.
- Item 8, tests/test_precompact_core.py (applied 3 edits). The property test runs 10 trials
  instead of 50. It now also asserts that the seeded draws hit every error count 0-3 and all
  three labels. test_header_counts_match_stub_labels keeps the deterministic 40-chunk case.
  Re-run tests.test_precompact_core: Ran 52 tests. Subject:
  `test(precompact): ten property trials that still cover every error count`.
- Item 9, tests/test_ai_kit_spec_runner_dispatch.py (applied 4 edits). It patches `_DRAIN_S`
  0.5 in the escaped-grandchild test and `_TERM_GRACE_S` 0.5 in the sigterm-ignored and wedged
  tests, the way the wedged test already patches it. The new TestGracePins asserts (4, 2) and a
  grace above 2.5. Re-run tests.test_ai_kit_spec_runner_dispatch: Ran 71 tests (70 plus the pin).
  Subject: `test(spec-review): patch the term and drain graces in the slow dispatch tests`.
- Item 11, tests/test_arch.py (applied 7 edits). `_read_tree(path)` is wrapped in
  `functools.cache`. `_parse`, `_parse_path`, `_host_cli_names` and the six inline loops read
  through it. The non-vacuity tests still call `ast.parse` on their own snippets and never touch
  the cache. Re-run tests.test_arch: Ran 76 tests. Also
  `grep -c "ast.parse(handle.read()" tests/test_arch.py` prints 0 (it prints 8 at HEAD).
  Subject: `test(arch): parse each source file once per run`.
- Item 12, tests/test_jev_fast_decision.py (applied 1 edits). test_matrix_auto_skips_rung
  patches `JR._sleep`, as lines 633-660 already do. Re-run tests.test_jev_fast_decision: Ran 156
  tests. Subject: `test(jev): patch the retry sleep in the matrix rung test`.

Static pins in this task:
- Item 3 pins MODULE_STOP_GRACE_SECS 15 (900 s was already pinned).
- Item 4 pins the hook's 8.0 / 1.0 / 5.0 and the registered 10 s.
- Item 9 pins `_TERM_GRACE_S` 4 and `_DRAIN_S` 2.
- Items 5, 7, 8, 11 and 12 scale only test machinery (a server poll interval, a lock-holder
  helper, a fake host sleep, a trial count, a parse cache, a patched sleep), so they need no pin.

Step 11 (after timings): the Step 2 command with label `after` instead of `before`. Every line
must be ok. Then `git status --short` prints nothing, and `git log --oneline -8` shows the 8
commits.
  </action>
  <verify>
    <automated>AI_KIT_REFUSE_REAL_HOME=1 python3 tools/run_unittest_parallel.py tests.test_run_unittest_parallel tests.test_claude_session_wake_hook tests.test_cursor_quota tests.test_cursor_status_line tests.test_cursor_fakes tests.test_ai_kit_session_wake_fire tests.test_precompact_core tests.test_ai_kit_spec_runner_dispatch tests.test_arch tests.test_jev_fast_decision</automated>
  </verify>
  <done>The run prints `10/10 modules passed`. tmp/quick-test-cuts/timings-task1.txt holds 10 `before` and 10 `after` lines, all ok. `git log` shows the 8 Task 1 commits. Each commit passed the pre-commit hook without `--no-verify`.</done>
</task>

<task type="auto">
  <name>Task 2: E2e and integration cuts (owner items 1, 2, 6, 10), 4 commits</name>
  <precondition>Task 1's 8 commits are on the branch, `git status --short` prints nothing, and `uv run python -c "import textual"` exits 0.</precondition>
  <files>tests/fixtures/precompact/run_shim.mjs, tests/test_precompact_shims_e2e.py, tests/test_ai_kit_project_rules_all_e2e.py, tests/test_wizard_pty.py, tests/test_wizard_app.py, tests/test_wizard_app_1.py, tests/test_wizard_app_2.py, tests/test_wizard_app_3.py, tests/wizard_app_common.py, tests/test_system_memory_e2e.py, tests/test_staged_mapper.py, tools/run_unittest_parallel.py, Makefile, .pre-commit-config.yaml</files>
  <action>
Step 0: the Task 1 Step 0 commands (main checkout path, then copy `.claude/gsd-core` and
`.claude/scripts` if missing). Then `ls .claude/gsd-core/bin/gsd-tools.cjs .claude/scripts`
lists both. Without them the project_rules_all e2e classes skip, and Step 4 would prove nothing.

Step 1: with the Write tool, write `tmp/quick-test-cuts/edits_task2.py` (Appendix C) and
`tmp/quick-test-cuts/split_wizard_app.py` (Appendix D). Also write
`tmp/quick-test-cuts/time_modules.py` (Appendix A) if it is missing.
`python3 tmp/quick-test-cuts/edits_task2.py` lists 7 files and exits 2.

Step 2 (before timings, about 2.5 min):
`AI_KIT_REFUSE_REAL_HOME=1 python3 tmp/quick-test-cuts/time_modules.py 2 before --uv tests.test_precompact_shims_e2e tests.test_ai_kit_project_rules_all_e2e tests.test_wizard_pty tests.test_wizard_app`
prints 4 ok lines, about 57, 26, 16 and 21 s.

Step 3 (item 1, the shims). Run
`python3 tmp/quick-test-cuts/edits_task2.py tests/fixtures/precompact/run_shim.mjs tests/test_precompact_shims_e2e.py`.
It prints 1 and 7 edits. The edits:
- run_shim.mjs reads `AI_KIT_SHIM_TIME_SCALE`. When it is set and not 1, it wraps
  `globalThis.setTimeout` before the shim loads, multiplying every delay by it. The opencode
  `remaining` deadline reaches `setTimeout(kill, remaining)` and is scaled too.
- The production `const TIMEOUT_MS = 10000;` in tools/hooks/pi/ai-kit-precompact.ts and
  tools/hooks/opencode/ai-kit-precompact.ts is never edited. Neither is the 2000 in the pi
  tool-advisor and tool-reminder.
- The hang tests pass `SCALE_ENV` (TIME_SCALE 0.2) and assert scaled bounds.
- test_opencode_messages_hang_finishes_within_11s is merged into
  test_opencode_messages_failure_untouched: its hang subtest now also asserts elapsed under the
  scaled deadline plus 1 s.
- TestShimDeadlinePins asserts the four TIMEOUT_MS values, that no shim names the knob, and
  that the harness reads it.
Re-run
`AI_KIT_REFUSE_REAL_HOME=1 uv run python tools/run_unittest_parallel.py tests.test_precompact_shims_e2e`:
Ran 24 tests (23, minus the merged one, plus 2 pins), about 12 s. Stage both files by path.
Subject: `test(precompact): scale shim hang timers in the harness; pin the real deadlines`.

Step 4 (item 2, the probe). Run
`python3 tmp/quick-test-cuts/edits_task2.py tests/test_ai_kit_project_rules_all_e2e.py`
(4 edits). The edits:
- `_real_node()` resolves `process.execPath` under the caller's env, and the scratch PATH links
  that binary as `node`.
- The probe test asserts R18 and R19 have status `missing` and no `unverified` key.
- The module docstring says why.
Re-run with uv: Ran 5 tests, about 1 s. Subject:
`test(project-rules): link the real node binary so the identity probe answers`.

Step 5 (item 6, PTY drains). Run
`python3 tmp/quick-test-cuts/edits_task2.py tests/test_wizard_pty.py` (4 edits; the third
replaces 6 lines). The edits:
- New helpers `_settle(fd, deadline, quiet=0.3)` and `_drain_until(fd, done, deadline)`.
  `_settle` returns once the PTY has been quiet for 0.3 s, so it never waits longer than the
  fixed drain it replaces. `_drain_until` keeps reading until `done()` holds, with a bounded
  deadline.
- The six fixed 1.0 s drains and the 3.0 s board drain become `_settle`.
- The replace-gate's 2.0 s apply drain waits for `os.path.islink(real_skill)` (file state),
  then settles.
- The final drains that read to EOF are unchanged.
Re-run with uv twice, as a flake check: Ran 12 tests both times, about 7-8 s. Subject:
`test(wizard): wait for render quiet or file state instead of fixed PTY drains`.

Step 6 (item 10, the split). In order:
- `python3 tmp/quick-test-cuts/split_wizard_app.py` prints `part 1: 22 tests`,
  `part 2: 22 tests`, `part 3: 22 tests` and `wrote 4 files; 66 of 66 tests`.
- `git rm -q tests/test_wizard_app.py`
- `python3 tmp/quick-test-cuts/edits_task2.py tools/run_unittest_parallel.py tests/test_staged_mapper.py tests/test_system_memory_e2e.py`
  applies 1 edit to each file:
  - In INTEGRATION_MODULES, the three parts replace `tests.test_wizard_app`.
  - The 10 runner stand-in names in test_staged_mapper become `tests.test_wizard_app_1`.
  - A docstring pointer moves to `tests/test_wizard_app_2.py` (where TestReviewDone now lives).
- `python3 tools/gen_test_groups.py` regenerates the Makefile and .pre-commit-config.yaml
  listings.
- `grep -c "tests.test_wizard_app_1 tests.test_wizard_app_2 tests.test_wizard_app_3" Makefile .pre-commit-config.yaml`
  prints `Makefile:1` and `.pre-commit-config.yaml:2`.
- `grep -rnIE "test_wizard_app([^_0-9]|$)" tools tests Makefile .pre-commit-config.yaml AGENTS.md README.md`
  prints nothing. At HEAD it matches 15 lines. Do not touch docs/superpowers/: those are
  historical plans.
- `AI_KIT_REFUSE_REAL_HOME=1 uv run python tools/run_unittest_parallel.py tests.test_wizard_app_1 tests.test_wizard_app_2 tests.test_wizard_app_3`
  prints `3/3 modules passed`, each with Ran 22 tests.
- `AI_KIT_REFUSE_REAL_HOME=1 python3 tools/run_unittest_parallel.py tests.test_gate_scope tests.test_staged_mapper tests.test_run_unittest_parallel tests.test_arch`
  prints `4/4 modules passed`.
- `git add tests/test_wizard_app_1.py tests/test_wizard_app_2.py tests/test_wizard_app_3.py tests/wizard_app_common.py tools/run_unittest_parallel.py tests/test_staged_mapper.py tests/test_system_memory_e2e.py Makefile .pre-commit-config.yaml`
  (`git rm` already staged the deletion). Subject:
  `test(wizard): split the wizard view tests into three parallel modules`.
The runner is shared machinery, so this commit's hook runs the full unit and arch groups plus
the covering uv modules (a few minutes).

Static pins in this task: item 1 pins TIMEOUT_MS 10000 and 2000 and keeps the scale knob out of
every shim. Items 2, 6 and 10 scale no production timer. Item 2 fixes the env. Item 6 replaces
fixed test sleeps with bounded waits. Item 10 moves tests between files.

Step 7 (after timings):
`AI_KIT_REFUSE_REAL_HOME=1 python3 tmp/quick-test-cuts/time_modules.py 2 after --uv tests.test_precompact_shims_e2e tests.test_ai_kit_project_rules_all_e2e tests.test_wizard_pty tests.test_wizard_app_1 tests.test_wizard_app_2 tests.test_wizard_app_3`
prints 6 ok lines. Then `git status --short` prints nothing.
  </action>
  <verify>
    <automated>AI_KIT_REFUSE_REAL_HOME=1 uv run python tools/run_unittest_parallel.py tests.test_precompact_shims_e2e tests.test_ai_kit_project_rules_all_e2e tests.test_wizard_pty tests.test_wizard_app_1 tests.test_wizard_app_2 tests.test_wizard_app_3</automated>
  </verify>
  <done>The run prints `6/6 modules passed`. tests/test_wizard_app.py is deleted and the three parts hold 66 tests in total. The old-name grep prints nothing. timings-task2.txt holds 4 `before` and 6 `after` lines. `git log` shows the 4 Task 2 commits.</done>
</task>

<task type="auto">
  <name>Task 3: Mapper data-file rule (owner item 13), budget table refresh, pins and docs (owner item 14), 2 commits</name>
  <precondition>Tasks 1 and 2 (12 commits) are on the branch, and `git status --short` prints nothing.</precondition>
  <files>tools/staged_mapper.py, tests/test_staged_mapper.py, AGENTS.md, tools/run_unittest_parallel.py</files>
  <action>
Step 0: the Task 1 Step 0 commands. Then `ls .claude/gsd-core/bin/gsd-tools.cjs .claude/scripts`
lists both. The e2e refresh in Step 5 needs them, or modules skip and record short times.

Step 1: with the Write tool, write `tmp/quick-test-cuts/edits_task3.py` (Appendix E),
`tmp/quick-test-cuts/refresh_e2e_secs.py` (Appendix F) and `tmp/quick-test-cuts/time_staged.py`
(Appendix G). Also write `tmp/quick-test-cuts/time_modules.py` (Appendix A) if it is missing.

Step 2 (docs-only commit cost, before). Measure it as follows:
- `time_staged.py` gets the module count from `python3 tools/staged_mapper.py AGENTS.md` (no
  test runs).
- It times `python3 tools/run_unittest_parallel.py --staged AGENTS.md`, the commit hook's own
  command, with the staged list given as a path. That is exactly what a commit staging only
  AGENTS.md runs.
Run `AI_KIT_REFUSE_REAL_HOME=1 python3 tmp/quick-test-cuts/time_staged.py before AGENTS.md`.
It prints `before staged:AGENTS.md modules=16 wall=<s> rc=0` (rc 0 expected in the worktree).
Then run
`AI_KIT_REFUSE_REAL_HOME=1 python3 tmp/quick-test-cuts/time_modules.py 3 before tests.test_staged_mapper`.

Step 3 (item 13). Run
`python3 tmp/quick-test-cuts/edits_task3.py tools/staged_mapper.py tests/test_staged_mapper.py AGENTS.md`.
It prints 7, 1 and 1 edits. The edits:
- `Index` gains `sources` (stem to source).
- `code_text(source)` is cached with `functools.cache`. It drops comments and bare string
  statements (docstrings) with stdlib `tokenize`. A source tokenize cannot read is returned
  whole, so it selects more.
- `covering_modules` and `_named_in_corpus` use code text only for a data file: a path outside
  UNIT_DIRS with a DATA_SUFFIXES suffix. Only modules whose full reach text names the file get
  tokenized.
- Code files keep today's matching.
- DataFileTest adds 6 tests: comment and docstring select nothing; prose naming a data file is
  not an empty answer that forces a full run; a helper's code still carries a data file; a
  code file named only in a comment still selects; code_text itself; and the real checkout
  (AGENTS.md selects test_ai_kit_spec_runtimes_table but not test_wizard_pty or
  test_ai_kit_project_rules_all_e2e, and tools/command_ownership.py selects test_setup).
- AGENTS.md's commit-stage bullet gains the data-file sentence.
Checks:
- `python3 tools/staged_mapper.py AGENTS.md` prints 13 modules, without tests.test_wizard_pty,
  tests.test_ai_kit_project_rules_all_e2e or tests.test_ai_kit_spec.
- `python3 tools/staged_mapper.py tools/command_ownership.py` prints
  `modules: tests.test_setup`.
- `AI_KIT_REFUSE_REAL_HOME=1 python3 tools/run_unittest_parallel.py tests.test_staged_mapper tests.test_run_unittest_parallel tests.test_gate_scope`
  prints `3/3 modules passed`, with Ran 71 tests for the mapper.
Stage the three files by path. Subject: `feat(mapper): match a data file's name only in test code`.
Body: `Comments and docstrings name a file without reading it; a docs-only AGENTS.md commit selected 16 modules, now 13. Code files keep matching anywhere.`

Step 4 (after): `AI_KIT_REFUSE_REAL_HOME=1 python3 tmp/quick-test-cuts/time_staged.py after AGENTS.md`
prints `modules=13`. Then run
`AI_KIT_REFUSE_REAL_HOME=1 python3 tmp/quick-test-cuts/time_modules.py 3 after tests.test_staged_mapper`.

Step 5 (item 14, the budget table). Run
`AI_KIT_REFUSE_REAL_HOME=1 python3 tmp/quick-test-cuts/refresh_e2e_secs.py`. It makes one
`--group e2e` run (about 1.5-2 min). That is the table's documented refresh method, not
`make test`. The script prints 23 table lines and `refreshed 23 entries`. Expect about 13 for
tests.test_precompact_shims_e2e (was 58) and about 1 for
tests.test_ai_kit_project_rules_all_e2e (was 26). If any value is above 60, or the script says
`not refreshed`, STOP and report the printed modules.
`git diff --stat` shows only tools/run_unittest_parallel.py changed (the table values and the
load figure in its comment). Re-run
`AI_KIT_REFUSE_REAL_HOME=1 python3 tools/run_unittest_parallel.py tests.test_gate_scope tests.test_staged_mapper tests.test_run_unittest_parallel`:
`3/3 modules passed`. Stage the file. Subject:
`test(runner): refresh the e2e commit-budget times after the cuts`.

Step 6 (pins and docs check; no commit unless a check fails):
- `grep -rnIE "test_wizard_app([^_0-9]|$)" AGENTS.md README.md tests/test_gate_scope.py tools`
  prints nothing.
- tests/test_gate_scope.py needs no pin change. Its `recorded_secs_errors` checks the table's
  shape, and its listing test checks the regenerated listings. Both passed in Step 5.
- README.md's push-time numbers (55.4 s and the others) come from `tools/time_prepush.py`. The
  orchestrator refreshes them after merging. Do not edit them here.
- Then `git status --short` prints nothing, and `git log --oneline -14` shows all 14 plan
  commits.
  </action>
  <verify>
    <automated>AI_KIT_REFUSE_REAL_HOME=1 python3 tools/run_unittest_parallel.py tests.test_staged_mapper tests.test_gate_scope tests.test_run_unittest_parallel</automated>
  </verify>
  <done>The run prints `3/3 modules passed`. `python3 tools/staged_mapper.py AGENTS.md` lists 13 modules and `python3 tools/staged_mapper.py tools/command_ownership.py` lists tests.test_setup. E2E_RECORDED_SECS holds this run's times, all at most 60. timings-task3.txt holds the `before` and `after` `staged:AGENTS.md` lines, the e2e-group lines and the mapper module's before and after lines. `git log` shows the 2 Task 3 commits.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| test process to owner HOME | The tests spawn real children (node, the hook driver, PTY wizard, gsd-tools). A wrong env could reach the owner's real host config. |
| staged mapper to commit gate | The mapper decides which tests a commit runs. Under-selection lets a broken change through the commit stage. |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-hzc-01 | Tampering | tests/test_ai_kit_project_rules_all_e2e.py real node link | medium | mitigate | Only the binary path is resolved from the caller's env. The env stays cleared to a scratch HOME and PATH, and the probe still passes node only PATH and HOME. AI_KIT_REFUSE_REAL_HOME=1 is set on every command. |
| T-hzc-02 | Repudiation | Scaled timers (shims, wake hook, runner, dispatch) | medium | mitigate | Each scaled timing has a static pin of its production constant (TestShimDeadlinePins, TestHookDeadlinePins, test_the_production_stop_grace_is_pinned, TestGracePins). The scale knob is pinned absent from every shim. |
| T-hzc-03 | Denial of Service | tools/staged_mapper.py data-file rule | medium | mitigate | Only data files outside UNIT_DIRS change behavior. Code files keep full-text matching (pinned by tests). A source tokenize cannot read is matched whole. The push stage still runs the full suites. |
| T-hzc-04 | Denial of Service | Shorter waits (lock holds, PTY settle, 1 s deadlines) | low | accept | A wait that is too short fails a test; it never passes a broken claim. The owner accepted the low flake risk. Each step re-runs the module, and Task 2 runs wizard_pty twice. |
| T-hzc-SC | Tampering | npm/pip/cargo installs | high | accept | This plan installs no package; the reserved row stays per the template. |
</threat_model>

<verification>
- Each task's `<verify>` command passes, and its timings file holds before and after lines.
- `git log --oneline -14` shows 8 + 4 + 2 commits. Every commit went through the pre-commit
  hook.
- The orchestrator then runs `make test`, `python3 tools/time_prepush.py`,
  `python3 tools/staged_mapper.py --stats` and the env matrix (not the executor).
</verification>

<success_criteria>
- Every must_haves truth holds.
- No test removed except the merged duplicate hang test. Every scaled production timer is pinned.
- `--staged AGENTS.md` selects 13 modules (was 16), and the timings file records its wall before
  and after.
- E2E_RECORDED_SECS reflects one post-cut `--group e2e` run, every value at most 60.
</success_criteria>

<output>
Do not write SUMMARY.md. The orchestrator writes
`.planning/quick/261104-hzc-apply-test-time-audit-cuts-1-13-and-the-/261104-hzc-SUMMARY.md`
from your report. Report each task's commits, the timings file contents and every jev call
(id, answer, confidence, what you did).
</output>

## Appendix: scripts (write each one byte for byte to the path in its heading)

### Appendix A: tmp/quick-test-cuts/time_modules.py (per-module before/after walls (Tasks 1-3))

````python
"""Time test modules one at a time through the runner; append one line per module.

Usage (from the worktree root):
    python3 tmp/quick-test-cuts/time_modules.py TASK LABEL [--uv] MODULE [MODULE ...]
Each line `LABEL MODULE SECONDS STATUS` goes to tmp/quick-test-cuts/timings-task<TASK>.txt and
to stdout. --uv runs the runner under `uv run python` (integration and e2e modules). Exit 1 when
any module failed or printed no result line.
"""
import pathlib
import re
import subprocess
import sys


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__, file=sys.stderr)
        return 2
    task, label, rest = argv[0], argv[1], argv[2:]
    prefix = ["uv", "run", "python"] if "--uv" in rest else [sys.executable]
    modules = [name for name in rest if name != "--uv"]
    out = pathlib.Path("tmp/quick-test-cuts") / f"timings-task{task}.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    bad = 0
    for module in modules:
        proc = subprocess.run([*prefix, "tools/run_unittest_parallel.py", module],
                              capture_output=True, text=True, check=False)
        found = re.search(rf"^=== {re.escape(module)}: (ok|FAILED \(rc=-?\d+\)) in ([0-9.]+)s",
                          proc.stdout, re.MULTILINE)
        if found:
            status, secs = found.group(1).replace(" ", "_"), found.group(2)
        else:
            status, secs = "NO_RESULT", "-"
        bad += status != "ok"
        line = f"{label} {module} {secs} {status}"
        print(line)
        with out.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
````

### Appendix B: tmp/quick-test-cuts/edits_task1.py (Task 1 edits)

````python
"""Task 1 edits for quick 261104-hzc: exact (old, new, count) replacements per file.

Unit-tier timing cuts (owner items 3, 4, 5, 7, 8, 9, 11, 12).
Usage (from the worktree root): python3 tmp/quick-test-cuts/edits_task1.py FILE [FILE ...]
Each old text must occur exactly `count` times, or that file is left unwritten and
the script exits 1 naming the edit. No FILE lists the files it knows.
"""
import pathlib
import sys

E = {}

E["tests/test_run_unittest_parallel.py"] = [
('''class GroupModeTest(unittest.TestCase):
    def test_arch_group_passes(self) -> None:
        proc = run("--group", "arch")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("1/1 modules passed", proc.stdout)
''',
'''class GroupModeTest(unittest.TestCase):
    def test_arch_group_passes(self) -> None:
        # A one-test tests.test_arch in a foreign folder: --group arch picks the module and runs
        # it there. The arch tier runs the real module; running it here too only cost time.
        runner = load_runner()
        with tempfile.TemporaryDirectory() as tmp:
            tests_dir = pathlib.Path(tmp) / "tests"
            tests_dir.mkdir()
            (tests_dir / "__init__.py").write_text("")
            (tests_dir / "test_arch.py").write_text(_PASSING.format(body="        pass"))
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                rc = runner.main(["--group", "arch"], pathlib.Path(tmp))
        self.assertEqual(rc, 0, out.getvalue())
        self.assertIn("=== tests.test_arch: ok", out.getvalue())
        self.assertIn("1/1 modules passed", out.getvalue())
''', 1),
('''        self.assertEqual(self.runner.MODULE_TIMEOUT_SECS, 900)

''',
'''        self.assertEqual(self.runner.MODULE_TIMEOUT_SECS, 900)

    def test_the_production_stop_grace_is_pinned(self) -> None:
        # The stop tests below scale the deadline and the grace down; this pins the real grace.
        self.assertEqual(self.runner.MODULE_STOP_GRACE_SECS, 15)

''', 1),
('''        _, rc, output, _ = self.run_stopped(module, 3)
        self.assertEqual(rc, 124, output)
        self.assertIn("timed out after 3s", output)
''',
'''        _, rc, output, _ = self.run_stopped(module, 1.0, grace=0.5)
        self.assertEqual(rc, 124, output)
        self.assertIn("timed out after 1.0s", output)
''', 1),
('''        _, rc, _, secs = self.run_stopped(module, 3, grace=1)
''',
'''        _, rc, _, secs = self.run_stopped(module, 1.0, grace=0.5)
''', 1),
('''        _, rc, _, _ = self.run_stopped(module, 4, grace=5)
''',
'''        _, rc, _, _ = self.run_stopped(module, 1.0, grace=0.5)
''', 1),
]

E["tests/test_claude_session_wake_hook.py"] = [
("import contextlib\nimport io\nimport json\n",
 "import ast\nimport contextlib\nimport importlib.util\nimport io\nimport json\n", 1),
('''os.replace(tmp, PIDS)
time.sleep(60)
"""


class TestHookDeadline(_HookScratch):
    """One 8 s monotonic deadline over the stdin read and the arm child, so the
    hook exits by itself before the row's 10 s timeout (review round 1)."""
''',
'''os.replace(tmp, PIDS)
time.sleep(60)
"""
# The deadline tests run the real hook through this driver with its timers scaled down;
# TestHookDeadlinePins pins the real 8 s deadline, 1 s child minimum and 5 s read cap.
_SCALED_DEADLINE_S = 1.0
_SCALED_MIN_CHILD_S = 0.2
_SCALED_READ_CAP_S = 0.3
_DRIVER = f"""import importlib, os, sys
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
hook = importlib.import_module("claude_session_wake")
hook.HOOK_DEADLINE_S = {_SCALED_DEADLINE_S!r}
hook.HOOK_MIN_CHILD_S = {_SCALED_MIN_CHILD_S!r}
hook._session_start._STDIN_TOTAL_SECONDS = {_SCALED_READ_CAP_S!r}
raise SystemExit(hook.main())
"""


def _assigned_numbers(path) -> dict[str, float]:
    """Module-level `NAME = <number>` assignments of a source file, read with ast: importing
    the hook would replace this process's excepthook."""
    with open(path, encoding="utf-8") as handle:
        tree = ast.parse(handle.read())
    numbers = {}
    for node in tree.body:
        if not (isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant)):
            continue
        value = node.value.value
        if isinstance(value, (int, float)):
            numbers.update({t.id: float(value) for t in node.targets if isinstance(t, ast.Name)})
    return numbers


class TestHookDeadlinePins(unittest.TestCase):
    """Static pins of the real timers that TestHookDeadline scales through _DRIVER."""

    def test_real_deadline_fits_the_read_cap_and_the_registered_timeout(self):
        hook = _assigned_numbers(_HOOK)
        start = _assigned_numbers(os.path.join(_REPO, "tools", "hooks", "claude_session_start.py"))
        self.assertEqual(
            (hook["HOOK_DEADLINE_S"], hook["HOOK_MIN_CHILD_S"], start["_STDIN_TOTAL_SECONDS"]),
            (8.0, 1.0, 5.0),
        )
        # a read that runs to its cap still leaves the arm child its minimum
        self.assertGreaterEqual(
            hook["HOOK_DEADLINE_S"] - start["_STDIN_TOTAL_SECONDS"], hook["HOOK_MIN_CHILD_S"]
        )
        spec = importlib.util.spec_from_file_location(
            "setup_wake_pin", os.path.join(_REPO, "tools", "setup.py"))
        assert spec is not None and spec.loader is not None
        setup = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(setup)
        row = next(row for row in setup.HOOK_REGISTRY if row.id == "session-wake")
        self.assertLess(hook["HOOK_DEADLINE_S"], row.timeout)


class TestHookDeadline(_HookScratch):
    """The real hook under _DRIVER: one deadline (8 s, scaled to 1 s here) over the stdin read
    and the arm child, so the hook exits by itself before the row's 10 s timeout."""
''', 1),
('''        self.hook = os.path.join(hooks_dir, "claude_session_wake.py")
        self.pids_file = os.path.join(self.root, "pids.txt")
''',
'''        self.hook = os.path.join(hooks_dir, "drive_hook.py")
        with open(self.hook, "w", encoding="utf-8") as handle:
            handle.write(_DRIVER)
        self.pids_file = os.path.join(self.root, "pids.txt")
''', 1),
("        self.assertLess(wall, 9.0)\n",
 "        self.assertLess(wall, _SCALED_DEADLINE_S + 1.0)\n", 2),
('''            # a complete payload, then one space every 0.3 s: the read keeps the
            # stream open until its own 5 s cap; trailing whitespace stays valid JSON
''',
'''            # a complete payload, then one space every 0.1 s: the read keeps the
            # stream open until its own (scaled) cap; trailing whitespace stays valid JSON
''', 1),
("                time.sleep(0.3)\n", "                time.sleep(0.1)\n", 1),
]

E["tests/cursor_fakes.py"] = [
('''        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
''',
'''        # A 0.05 s poll: the default 0.5 s makes every shutdown() wait up to half a second.
        self._thread = threading.Thread(target=self._server.serve_forever,
                                        kwargs={"poll_interval": 0.05}, daemon=True)
''', 1),
]

E["tests/test_ai_kit_session_wake_fire.py"] = [
('''        fire_env = {**self.env, "FAKE_HOST_SLEEP": "5"}
''',
'''        # The first resume holds the lock 1.5 s: the second fire starts once the resume is
        # logged and needs well under that to reach the lock.
        fire_env = {**self.env, "FAKE_HOST_SLEEP": "1.5"}
''', 1),
('''        helper = fakes.hold_lock(paths.lock, 2.0)
''',
'''        helper = fakes.hold_lock(paths.lock, 0.5)
''', 3),
('''        self.assertGreaterEqual(elapsed, 1.5)  # it finished only after the release
''',
'''        self.assertGreaterEqual(elapsed, 0.4)  # it finished only after the 0.5 s release
''', 1),
]

E["tests/test_precompact_core.py"] = [
('''        # Twelve chunks per trial: every trial still spans the three labels and 0-3 errors, and
        # each stub call is a process start, so 40 chunks x 50 trials cost 24 s for no new case.
        # The 40-chunk path is covered by test_header_counts_match_stub_labels.
''',
'''        # Twelve chunks per trial, ten trials: each stub call is a process start, and the seeded
        # draws still span the three labels and every error count 0-3 (asserted below). The
        # 40-chunk path is covered by test_header_counts_match_stub_labels.
''', 1),
('''        for _trial in range(50):
            mapping = {identifier: rng.choice(self.CYCLE) for identifier in ids}
            errored = set(rng.sample(ids, rng.randrange(0, 4)))
''',
'''        error_counts, labels = set(), set()
        for _trial in range(10):
            mapping = {identifier: rng.choice(self.CYCLE) for identifier in ids}
            errored = set(rng.sample(ids, rng.randrange(0, 4)))
            error_counts.add(len(errored))
            labels.update(mapping.values())
''', 1),
('''                self.assertEqual(counts[label], expected, (label, mapping, errored))
''',
'''                self.assertEqual(counts[label], expected, (label, mapping, errored))
        self.assertEqual(error_counts, {0, 1, 2, 3})
        self.assertEqual(labels, set(self.CYCLE))
''', 1),
]

E["tests/test_ai_kit_spec_runner_dispatch.py"] = [
('''            started = time.monotonic()
            run_custom_command(
                CustomSpec("k", [sys.executable, script, marker], [5]), "hi", seams
            )
            self.assertLess(time.monotonic() - started, rd._DRAIN_S + 5)
''',
'''            started = time.monotonic()
            with mock.patch.object(rd, "_DRAIN_S", 0.5):
                run_custom_command(
                    CustomSpec("k", [sys.executable, script, marker], [5]), "hi", seams
                )
            self.assertLess(time.monotonic() - started, 0.5 + 5)
''', 1),
('''                mock.patch.object(rd, "_TERM_GRACE_S", 1),
''',
'''                mock.patch.object(rd, "_TERM_GRACE_S", 0.5),
''', 1),
('''        marker = _marker()
        result = run_custom_command(CustomSpec("k", [
            sys.executable, "-c",
            "import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(60)",
            marker,
        ], [1]), "hi")
''',
'''        marker = _marker()
        with mock.patch.object(rd, "_TERM_GRACE_S", 0.5):
            result = run_custom_command(CustomSpec("k", [
                sys.executable, "-c",
                "import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); "
                "time.sleep(60)",
                marker,
            ], [1]), "hi")
''', 1),
('''class TestRunCustomCommand(_ChildTracker):
''',
'''class TestGracePins(unittest.TestCase):
    """The slow-stop tests patch these graces down; the production values stay pinned here."""

    def test_production_graces(self):
        self.assertEqual((rd._TERM_GRACE_S, rd._DRAIN_S), (4, 2))
        self.assertGreater(rd._TERM_GRACE_S, 2.5)  # above the runner's 2.5 s signal budget


class TestRunCustomCommand(_ChildTracker):
''', 1),
]

E["tests/test_arch.py"] = [
("import ast\nimport hashlib\n", "import ast\nimport functools\nimport hashlib\n", 1),
('''def _parse(name):
    """Parse a tools/ module into an AST, attaching its banner block map.

    Returns ``(tree, source)`` so callers can inspect both the parse tree and
    the raw text (the banner blocks are comments and thus not in the AST).
    """
    path = os.path.join(_TOOLS, name)
    with open(path, encoding="utf-8") as handle:
        source = handle.read()
    return ast.parse(source, filename=name), source
''',
'''@functools.cache
def _read_tree(path):
    """``(tree, source)`` of one repo file, read and parsed once per run. Rules only read the
    tree; the non-vacuity snippets call ast.parse themselves and never come through here."""
    with open(path, encoding="utf-8") as handle:
        source = handle.read()
    return ast.parse(source, filename=path), source


def _parse(name):
    """Parse a tools/ module into an AST, attaching its banner block map.

    Returns ``(tree, source)`` so callers can inspect both the parse tree and
    the raw text (the banner blocks are comments and thus not in the AST).
    """
    return _read_tree(os.path.join(_TOOLS, name))
''', 1),
('''    with open(_RUNNER_PATH, encoding="utf-8") as handle:
        tree = ast.parse(handle.read(), filename=_RUNNER_PATH)
''',
'''    tree = _read_tree(_RUNNER_PATH)[0]
''', 1),
('''    with open(path, encoding="utf-8") as handle:
        return ast.parse(handle.read(), filename=path)
''',
'''    return _read_tree(path)[0]
''', 1),
('''                    with open(path, encoding="utf-8") as handle:
                        tree = ast.parse(handle.read(), filename=path)
''',
'''                    tree = _read_tree(path)[0]
''', 3),
('''            with open(os.path.join(tests_root, filename), encoding="utf-8") as handle:
                tree = ast.parse(handle.read(), filename=filename)
''',
'''            tree = _read_tree(os.path.join(tests_root, filename))[0]
''', 3),
('''                    with open(path, encoding="utf-8") as handle:
                        src = handle.read()
''',
'''                    src = _read_tree(path)[1]
''', 1),
]

E["tests/test_jev_fast_decision.py"] = [
('''        zen = JevStub(model="jev-1.14.0")
        with typesafe, zen:
''',
'''        zen = JevStub(model="jev-1.14.0")
        with typesafe, zen, mock.patch.object(JR, "_sleep", side_effect=lambda _seconds: None):
''', 1),
]


def main(argv: list[str]) -> int:
    if not argv:
        print("files: " + " ".join(E))
        return 2
    for rel in argv:
        if rel not in E:
            sys.exit(f"no edits for {rel}")
        path = pathlib.Path(rel)
        text = path.read_text(encoding="utf-8")
        for number, (old, new, count) in enumerate(E[rel], 1):
            found = text.count(old)
            if found != count:
                sys.exit(f"{rel} edit {number}: anchor found {found} times, expected {count}; "
                         "nothing written to this file")
            text = text.replace(old, new)
        path.write_text(text, encoding="utf-8")
        print(f"{rel}: applied {len(E[rel])} edits")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
````

### Appendix C: tmp/quick-test-cuts/edits_task2.py (Task 2 edits)

````python
"""Task 2 edits for quick 261104-hzc: exact (old, new, count) replacements per file.

E2e and integration cuts (owner items 1, 2, 6 and the registration half of 10).
Usage (from the worktree root): python3 tmp/quick-test-cuts/edits_task2.py FILE [FILE ...]
Each old text must occur exactly `count` times, or that file is left unwritten and
the script exits 1 naming the edit. No FILE lists the files it knows.
"""
import pathlib
import sys

E = {}

E["tests/fixtures/precompact/run_shim.mjs"] = [
('''// No test starts a real pi or opencode process.
import { readFileSync } from "node:fs";
import { pathToFileURL } from "node:url";
''',
'''// AI_KIT_SHIM_TIME_SCALE=<factor> (hang tests only) multiplies every setTimeout delay, so a
// hang waits a fraction of a shim's real deadline. It wraps setTimeout before the shim loads;
// no shim reads it (TestShimDeadlinePins in tests/test_precompact_shims_e2e.py).
// No test starts a real pi or opencode process.
import { readFileSync } from "node:fs";
import { pathToFileURL } from "node:url";

const timeScale = Number(process.env.AI_KIT_SHIM_TIME_SCALE ?? "1");
if (Number.isFinite(timeScale) && timeScale > 0 && timeScale !== 1) {
  const realSetTimeout = globalThis.setTimeout;
  globalThis.setTimeout = (callback, delay = 0, ...args) =>
    realSetTimeout(callback, delay * timeScale, ...args);
}
''', 1),
]

E["tests/test_precompact_shims_e2e.py"] = [
('''HEADER_FIRST_LINE = "<!-- ai-kit precompact v1 -->"
''',
'''HEADER_FIRST_LINE = "<!-- ai-kit precompact v1 -->"
# The hang tests scale the shims' timers through run_shim.mjs; TestShimDeadlinePins pins the
# production deadlines they stand in for.
TIME_SCALE = 0.2
PRECOMPACT_DEADLINE_S = 10.0  # TIMEOUT_MS of both precompact shims
TOOL_DEADLINE_S = 2.0  # TIMEOUT_MS of the pi tool-advisor and tool-reminder shims
SCALE_ENV = {"AI_KIT_SHIM_TIME_SCALE": str(TIME_SCALE)}
''', 1),
('''                env = self._harness_env(base, {"AI_KIT_PYTHON": script})
''',
'''                env = self._harness_env(base, {"AI_KIT_PYTHON": script, **SCALE_ENV})
''', 1),
('''                    self.assertGreaterEqual(elapsed, 9.5)
                    self.assertLessEqual(elapsed, 11.0)
''',
'''                    self.assertGreaterEqual(elapsed, PRECOMPACT_DEADLINE_S * TIME_SCALE * 0.95)
                    self.assertLessEqual(elapsed, PRECOMPACT_DEADLINE_S * TIME_SCALE + 1.0)
''', 1),
('''                                             extra={"PATH": self._rg_path(base),
                                                    "AI_KIT_PYTHON": script}, timeout=8)
''',
'''                                             extra={"PATH": self._rg_path(base),
                                                    "AI_KIT_PYTHON": script, **SCALE_ENV},
                                             timeout=8)
''', 1),
('''                    self.assertGreaterEqual(elapsed, 1.8)
                    self.assertLess(elapsed, 4)
''',
'''                    self.assertGreaterEqual(elapsed, TOOL_DEADLINE_S * TIME_SCALE * 0.9)
                    self.assertLess(elapsed, TOOL_DEADLINE_S * TIME_SCALE + 2.0)
''', 1),
('''    def test_opencode_messages_failure_untouched(self):
        base = self._make_base()
        for mode in ("throw", "hang", "array"):
            with self.subTest(mode=mode):
                proc, _env = self._run_harness("opencode", OC_SHIM, OC_FIXTURE, base,
                                               mode=mode,
                                               timeout=12 if mode == "hang" else 60)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                result = json.loads(proc.stdout)
                self.assertFalse(result["promptSet"])
                expected = 2 if mode == "array" else 1
                self.assertEqual(len(result["output"]["context"]), expected)
                self.assertEqual(result["output"]["context"][:1], ["prior plugin context"])

    def test_opencode_messages_hang_finishes_within_11s(self):
        base = self._make_base()
        started = time.monotonic()
        proc, _env = self._run_harness("opencode", OC_SHIM, OC_FIXTURE, base,
                                       mode="hang", timeout=15)
        elapsed = time.monotonic() - started
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertLess(elapsed, 11.0)
''',
'''    def test_opencode_messages_failure_untouched(self):
        # The hang case also proves the hook finishes within its deadline plus 1 s (the
        # production 10 s, scaled by TIME_SCALE).
        base = self._make_base()
        for mode in ("throw", "hang", "array"):
            with self.subTest(mode=mode):
                started = time.monotonic()
                proc, _env = self._run_harness("opencode", OC_SHIM, OC_FIXTURE, base,
                                               mode=mode, extra=SCALE_ENV, timeout=30)
                elapsed = time.monotonic() - started
                self.assertEqual(proc.returncode, 0, proc.stderr)
                result = json.loads(proc.stdout)
                self.assertFalse(result["promptSet"])
                expected = 2 if mode == "array" else 1
                self.assertEqual(len(result["output"]["context"]), expected)
                self.assertEqual(result["output"]["context"][:1], ["prior plugin context"])
                if mode == "hang":
                    self.assertLess(elapsed, PRECOMPACT_DEADLINE_S * TIME_SCALE + 1.0)
''', 1),
('''def header_of(document):
''',
'''class TestShimDeadlinePins(unittest.TestCase):
    """Static pins of the production deadlines the scaled hang tests stand in for; the scale
    knob lives only in the harness."""

    SHIMS = ((PI_SHIM, PRECOMPACT_DEADLINE_S), (OC_SHIM, PRECOMPACT_DEADLINE_S),
             (PI_ADVISOR_SHIM, TOOL_DEADLINE_S), (PI_REMINDER_SHIM, TOOL_DEADLINE_S))

    def test_production_deadlines_are_pinned(self):
        for shim, deadline_s in self.SHIMS:
            with self.subTest(shim=str(shim.relative_to(REPO))):
                text = shim.read_text(encoding="utf-8")
                self.assertEqual(re.findall(r"^const TIMEOUT_MS = (\\d+);$", text, re.MULTILINE),
                                 [str(int(deadline_s * 1000))])
                self.assertNotIn("AI_KIT_SHIM_TIME_SCALE", text)

    def test_only_the_harness_reads_the_scale(self):
        self.assertIn("process.env.AI_KIT_SHIM_TIME_SCALE", HARNESS.read_text(encoding="utf-8"))


def header_of(document):
''', 1),
]

E["tests/test_ai_kit_project_rules_all_e2e.py"] = [
('''The environment is cleared to a scratch HOME/XDG and a PATH of `node` and `git` symlinks: the
gsd-tools resolver reads `RUNTIME_DIR` and every host-home override, and `.claude/` is
gitignored, so an inherited env could reach a gsd-tools under the real home. Each class skips
with a reason when the checkout-local gsd-tools or `node` is absent.
''',
'''The environment is cleared to a scratch HOME/XDG and a PATH of `node` and `git` symlinks: the
gsd-tools resolver reads `RUNTIME_DIR` and every host-home override, and `.claude/` is
gitignored, so an inherited env could reach a gsd-tools under the real home. The `node` link is
the real binary behind a version-manager shim: the identity probe passes node only PATH and the
scratch HOME, where a Volta shim cannot find its toolchain. Each class skips with a reason when
the checkout-local gsd-tools or `node` is absent.
''', 1),
('''def _scoped_env_setup(case: unittest.TestCase) -> str:
''',
'''def _real_node(node):
    """The node binary a version-manager shim (Volta, asdf) runs, resolved under the caller's
    env; `node` itself when it is not a shim or the lookup fails."""
    if node is None:
        return None
    real = subprocess.run([node, "-e", "process.stdout.write(process.execPath)"],
                          capture_output=True, text=True, check=False, timeout=30)
    return real.stdout.strip() if real.returncode == 0 and real.stdout.strip() else node


_REAL_NODE = _real_node(_NODE)


def _scoped_env_setup(case: unittest.TestCase) -> str:
''', 1),
('''    for name in ("node", "git"):
        found = shutil.which(name)
        if found:
            os.symlink(found, os.path.join(bin_dir, name))
''',
'''    for name, found in (("node", _REAL_NODE), ("git", shutil.which("git"))):
        if found:
            os.symlink(found, os.path.join(bin_dir, name))
''', 1),
('''            self.assertEqual(
                os.path.realpath(probed), os.path.realpath(_CHECKOUT_GSD_TOOLS)
            )
''',
'''            self.assertEqual(
                os.path.realpath(probed), os.path.realpath(_CHECKOUT_GSD_TOOLS)
            )
            # The probe answered `ok`, so the opengsd rules apply; the scratch repo has no
            # AGENTS.md, so both are missing. A probe that timed out marks them unverified.
            rows = {row["id"]: row for row in json.loads(result.stdout)["workflow"]}
            for rule in ("R18", "R19"):
                self.assertEqual(rows[rule]["status"], "missing", msg=rows[rule])
                self.assertNotIn("unverified", rows[rule], msg=rows[rule])
''', 1),
]

E["tests/test_wizard_pty.py"] = [
('''class TestPhase1E2E(unittest.TestCase):
''',
'''def _settle(fd, deadline, quiet=0.3):
    """Read ``fd`` until it has been quiet for ``quiet`` seconds, EOF, or ``deadline`` (epoch
    secs); the bytes read. A frame still flushing keeps it reading, so a key sent next lands on
    a finished render; it never waits longer than the fixed drain it replaces."""
    chunks = []
    while time.time() < deadline:
        try:
            rlist, _, _ = select.select([fd], [], [], min(quiet, max(0.0, deadline - time.time())))
        except (OSError, ValueError):
            break
        if not rlist:
            break
        try:
            data = os.read(fd, 4096)
        except OSError:
            break
        if not data:
            break
        chunks.append(data)
    return b"".join(chunks)


def _drain_until(fd, done, deadline):
    """Read ``fd`` (so the child never blocks on a full PTY) until ``done()`` holds; raise
    ``AssertionError`` at ``deadline`` (epoch secs). The bytes read."""
    chunks = []
    while not done():
        if time.time() >= deadline:
            raise AssertionError("_drain_until: the condition never held before the deadline")
        chunks.append(_settle(fd, min(deadline, time.time() + 0.1), quiet=0.05))
    return b"".join(chunks)


class TestPhase1E2E(unittest.TestCase):
''', 1),
('''            _drain(master_fd, time.time() + 2.0)   # let the apply worker finish
''',
'''            # the apply worker has replaced the skill, then its render settles
            _drain_until(master_fd, lambda: os.path.islink(real_skill),
                         time.time() + _STEP_DEADLINE)
            _settle(master_fd, time.time() + 2.0)
''', 1),
("            _drain(master_fd, time.time() + 1.0)\n",
 "            _settle(master_fd, time.time() + 1.0)\n", 6),
("            tail_board = _drain(master_fd, time.time() + 3.0)\n",
 "            tail_board = _settle(master_fd, time.time() + 3.0)\n", 1),
]

E["tools/run_unittest_parallel.py"] = [
('''    "tests.test_wizard_app",
''',
'''    # the wizard view tests, split in three so they run in parallel (quick 261104-hzc)
    "tests.test_wizard_app_1",
    "tests.test_wizard_app_2",
    "tests.test_wizard_app_3",
''', 1),
]

E["tests/test_staged_mapper.py"] = [
("tests.test_wizard_app", "tests.test_wizard_app_1", 10),
]

E["tests/test_system_memory_e2e.py"] = [
("exactly the sequence `tests/test_wizard_app.py`'s",
 "exactly the sequence `tests/test_wizard_app_2.py`'s", 1),
]


def main(argv: list[str]) -> int:
    if not argv:
        print("files: " + " ".join(E))
        return 2
    for rel in argv:
        if rel not in E:
            sys.exit(f"no edits for {rel}")
        path = pathlib.Path(rel)
        text = path.read_text(encoding="utf-8")
        for number, (old, new, count) in enumerate(E[rel], 1):
            found = text.count(old)
            if found != count:
                sys.exit(f"{rel} edit {number}: anchor found {found} times, expected {count}; "
                         "nothing written to this file")
            text = text.replace(old, new)
        path.write_text(text, encoding="utf-8")
        print(f"{rel}: applied {len(E[rel])} edits")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
````

### Appendix D: tmp/quick-test-cuts/split_wizard_app.py (Task 2 Step 6 split)

````python
"""Split tests/test_wizard_app.py into three modules at class boundaries (quick 261104-hzc).

Run from the worktree root: python3 tmp/quick-test-cuts/split_wizard_app.py
Writes tests/test_wizard_app_1.py, _2.py, _3.py and tests/wizard_app_common.py, prints each
part's test count, and exits 1 (writing nothing) when an anchor is missing or the counts do
not add up. It never deletes the source: `git rm tests/test_wizard_app.py` does that.
"""
import pathlib
import re
import sys

SRC = pathlib.Path("tests/test_wizard_app.py")
GUARD = '@unittest.skipUnless(HAVE_TEXTUAL, "textual not installed (run under uv)")\n'
MAIN_GUARD = '\n\nif __name__ == "__main__":  # pragma: no cover\n'
PARTS = (
    ("1", "TestStructuralFidelity", "TestExternal",
     "structural fidelity, Choose, the adoption gate and Arrange moves"),
    ("2", "TestExternal", "TestHousekeepingGate",
     "external segments, writeback, Review and Done, the in-UI commit and the chrome"),
    ("3", "TestHousekeepingGate", None, "the housekeeping gate and host traversal"),
)
FIDELITY = """

TestStructuralFidelity is the anti-divergence net: it encodes the locked
Global Constraints (three separate lane panels, two-list ON/OFF model, every
chip carries its icon, Choose shows components only) as machine checks.  If a
structural test fails, the PORT is wrong — fix the view, never the test."""
COMMON = '''"""Shared guard and helper for the tests/test_wizard_app_*.py modules (tools/wizard_app.py).

The Textual runtime requires ``uv run``; plain ``python3`` will not have it, so every test
class in those modules is guarded by ``@skipUnless(HAVE_TEXTUAL, ...)``.
"""
import importlib.util

HAVE_TEXTUAL = importlib.util.find_spec("textual") is not None


def query_static(app, selector: str):
    """The Static at ``selector``; its text is ``str(widget.content)`` (Textual 8.2.7)."""
    from textual.widgets import Static

    return app.query_one(selector, Static)
'''
HEADER = '''"""Install wizard view tests (tools/wizard_app.py), part {num} of 3.

Covers {topic}.

The wizard is a faithful port of docs/wizard-redesign/prototypes/mockup-textual.py. The three
parts run in parallel; the Textual guard and the Static helper live in
tests/wizard_app_common.py.{fidelity}
"""
{threading}import unittest

from tests.wizard_app_common import HAVE_TEXTUAL, query_static
from tools import wizard_app as wa

if HAVE_TEXTUAL:
    from tests.wizard_fixtures import make_ctx


'''
TEST_RE = re.compile(r"^    (?:async )?def test_", re.MULTILINE)


def anchor(text: str, name: str) -> int:
    marker = GUARD + f"class {name}("
    if text.count(marker) != 1:
        sys.exit(f"anchor for {name} found {text.count(marker)} times; nothing written")
    return text.index(marker)


def main() -> int:
    text = SRC.read_text(encoding="utf-8")
    if text.count(MAIN_GUARD) != 1:
        sys.exit("main guard anchor missing; nothing written")
    end_of_tests = text.index(MAIN_GUARD)
    total = len(TEST_RE.findall(text))
    outputs = {pathlib.Path("tests/wizard_app_common.py"): COMMON}
    counted = 0
    for num, first, nxt, topic in PARTS:
        start = anchor(text, first)
        stop = anchor(text, nxt) if nxt else end_of_tests
        body = text[start:stop].rstrip() + "\n"
        body = body.replace("_query_static(", "query_static(")
        head = HEADER.format(num=num, topic=topic, fidelity=FIDELITY if num == "1" else "",
                             threading="import threading\n" if "threading." in body else "")
        source = head + body + MAIN_GUARD + "    unittest.main()\n"
        tests = len(TEST_RE.findall(body))
        counted += tests
        outputs[pathlib.Path(f"tests/test_wizard_app_{num}.py")] = source
        print(f"part {num}: {tests} tests")
    if counted != total:
        sys.exit(f"parts hold {counted} tests, the source {total}; nothing written")
    for path, source in outputs.items():
        path.write_text(source, encoding="utf-8")
    print(f"wrote {len(outputs)} files; {counted} of {total} tests")
    return 0


if __name__ == "__main__":
    sys.exit(main())
````

### Appendix E: tmp/quick-test-cuts/edits_task3.py (Task 3 edits)

````python
"""Task 3 edits for quick 261104-hzc: exact (old, new, count) replacements per file.

Data-file matching in the staged mapper (owner item 13), its tests and the AGENTS.md text.
Usage (from the worktree root): python3 tmp/quick-test-cuts/edits_task3.py FILE [FILE ...]
Each old text must occur exactly `count` times, or that file is left unwritten and
the script exits 1 naming the edit. No FILE lists the files it knows.
"""
import pathlib
import sys

E = {}

E["tools/staged_mapper.py"] = [
(r'''amended, which ran at their own commit.

shortcut:''',
r'''amended, which ran at their own commit.

A data file outside the unit folders (DATA_SUFFIXES: docs, configs) is matched only in test code:
comments and bare string statements (docstrings) are stripped with tokenize first, since they
name a file without reading it. A code file keeps matching anywhere in a test's source: a comment
naming a tool is often the only link to the test that covers it.

shortcut:''', 1),
(r'''import argparse
import importlib.util
import os
''',
r'''import argparse
import functools
import importlib.util
import io
import os
''', 1),
(r'''import sys
from collections.abc''',
r'''import sys
import tokenize
from collections.abc''', 1),
(r'''    corpus: str  # every tests/*.py source, concatenated
''',
r'''    corpus: str  # every tests/*.py source, concatenated
    sources: Mapping[str, str]  # stem -> source of every tests/*.py file
''', 1),
(r'''        corpus="\n".join(sources.values()),
''',
r'''        corpus="\n".join(sources.values()),
        sources=sources,
''', 1),
(r'''def covering_modules(index: Index, path: str) -> frozenset[str]:
    """The test modules whose reach text names the unit of `path`; a staged test module
    that still exists covers itself."""
    patterns = [re.compile(token) for token in unit_tokens(path)]
    found = {
        module for module, text in index.reach.items()
        if any(pattern.search(text) for pattern in patterns)
    }
''',
r'''# A staged path outside UNIT_DIRS with one of these suffixes is a data file: only test code that
# names it selects a module (test-time audit, 2026-11-04).
DATA_SUFFIXES = frozenset({".md", ".json", ".jsonc", ".yaml", ".yml", ".toml", ".txt"})
_LAYOUT_TOKENS = frozenset({tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT, tokenize.ENDMARKER})
_DROPPED_TOKENS = frozenset({tokenize.COMMENT, tokenize.NL, tokenize.ENCODING})


def _is_data_file(path: str) -> bool:
    pure = PurePosixPath(path)
    return bool(pure.parts) and pure.parts[0] not in UNIT_DIRS and pure.suffix in DATA_SUFFIXES


@functools.cache
def code_text(source: str) -> str:
    """`source` without its comments and bare string statements (docstrings), the remaining
    tokens joined by spaces. A source tokenize cannot read comes back whole, so it selects more."""
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (SyntaxError, tokenize.TokenError):
        return source
    kept: list[str] = []
    line: list[tokenize.TokenInfo] = []
    for tok in tokens:
        if tok.type in _DROPPED_TOKENS:
            continue
        line.append(tok)
        if tok.type in (tokenize.NEWLINE, tokenize.ENDMARKER):
            body = [t for t in line if t.type not in _LAYOUT_TOKENS]
            if not (body and all(t.type == tokenize.STRING for t in body)):
                kept.extend(t.string for t in line)
            line = []
    return " ".join(kept)


def _data_covering(index: Index, patterns: list[re.Pattern[str]]) -> set[str]:
    """The modules whose code names a data file: their own source and each helper they reach,
    both through code_text. Only a module whose full reach text matches is tokenized."""
    helpers = {stem: text for stem, text in index.sources.items() if not stem.startswith("test_")}
    found = set()
    for module, reach in index.reach.items():
        if not any(pattern.search(reach) for pattern in patterns):
            continue
        named = {stem: code_text(body) for stem, body in helpers.items()
                 if re.search(_token(stem), reach)}
        own = code_text(index.sources[module.removeprefix("tests.")])
        if any(pattern.search(_reach(own, named)) for pattern in patterns):
            found.add(module)
    return found


def covering_modules(index: Index, path: str) -> frozenset[str]:
    """The test modules whose reach text names the unit of `path` (for a data file, their code
    only); a staged test module that still exists covers itself."""
    patterns = [re.compile(token) for token in unit_tokens(path)]
    if _is_data_file(path):
        found = _data_covering(index, patterns)
    else:
        found = {
            module for module, text in index.reach.items()
            if any(pattern.search(text) for pattern in patterns)
        }
''', 1),
(r'''def _named_in_corpus(index: Index, path: str) -> bool:
    return any(re.search(token, index.corpus) for token in unit_tokens(path))
''',
r'''def _named_in_corpus(index: Index, path: str) -> bool:
    """Whether any tests/*.py source names the unit of `path` (for a data file, in code)."""
    tokens = unit_tokens(path)
    if not _is_data_file(path):
        return any(re.search(token, index.corpus) for token in tokens)
    texts = [text for text in index.sources.values() if any(re.search(t, text) for t in tokens)]
    return any(re.search(token, code_text(text)) for text in texts for token in tokens)
''', 1),
]

E["tests/test_staged_mapper.py"] = [
(r'''

if __name__ == "__main__":
    unittest.main()
''',
r'''

class DataFileTest(MapperCase):
    """A data file outside the unit folders is selected by test code only; a comment or docstring
    naming it selects nothing. A code file keeps matching anywhere in the source."""

    def test_a_data_file_named_only_in_a_comment_or_docstring_selects_nothing(self) -> None:
        make_tree(self.root, {
            "tests/test_reads.py": "DOC = 'NOTES.md'\n",
            "tests/test_comment.py": "# see NOTES.md\nX = 1\n",
            "tests/test_docstring.py": (
                '"""Mirrors NOTES.md."""\n\n\ndef f():\n    """Also NOTES.md."""\n    return 1\n'
            ),
        })
        index = self.mapper.build_index(self.root)
        self.assertEqual(self.mapper.covering_modules(index, "NOTES.md"),
                         frozenset({"tests.test_reads"}))

    def test_a_data_file_named_only_in_prose_is_not_an_empty_answer(self) -> None:
        make_tree(self.root, {"tests/test_comment.py": "# see GUIDE.md\nX = 1\n"})
        decision = self.decide(["GUIDE.md"])
        self.assertEqual((decision.modules, decision.full_reason), ((), None))

    def test_a_helper_names_a_data_file_in_code_only(self) -> None:
        # test_alpha and test_zeta reach tests/util.py through `import util`.
        make_tree(self.root, {"tests/util.py": "SHARED = 'shared.md'\n# also notes.md\n"})
        index = self.mapper.build_index(self.root)
        self.assertEqual(self.mapper.covering_modules(index, "shared.md"),
                         frozenset({"tests.test_alpha", "tests.test_zeta"}))
        self.assertEqual(self.mapper.covering_modules(index, "notes.md"), frozenset())

    def test_a_code_file_named_only_in_a_comment_still_selects(self) -> None:
        # TREE's test_alpha names tools/alpha.py only in its `# covers tools/alpha.py` comment.
        self.assertEqual(self.decide(["tools/alpha.py"]).modules, ("tests.test_alpha",))

    def test_code_text_drops_comments_and_docstrings_only(self) -> None:
        source = ('"""Doc A.md."""\nX = "B.md"  # C.md\n\n\n'
                  'def f():\n    """D.md."""\n    return 1\n')
        text = self.mapper.code_text(source)
        self.assertIn('"B.md"', text)
        for gone in ("A.md", "C.md", "D.md"):
            self.assertNotIn(gone, text)
        self.assertEqual(self.mapper.code_text("x = (\n"), "x = (\n")  # unreadable: kept whole

    def test_real_checkout_data_and_code_files(self) -> None:
        index = self.mapper.build_index(REPO_ROOT)
        agents = self.mapper.covering_modules(index, "AGENTS.md")
        self.assertIn("tests.test_ai_kit_spec_runtimes_table", agents)  # it reads the real file
        for module in ("tests.test_wizard_pty", "tests.test_ai_kit_project_rules_all_e2e"):
            self.assertNotIn(module, agents)
        self.assertIn("tests.test_setup",
                      self.mapper.covering_modules(index, "tools/command_ownership.py"))


if __name__ == "__main__":
    unittest.main()
''', 1),
]

E["AGENTS.md"] = [
(r'''  every commit; `python3 tools/staged_mapper.py --stats` shows its selectivity.
  Unit and arch modules run under python3; the modules that need uv (unit-uv,
''',
r'''  every commit; `python3 tools/staged_mapper.py --stats` shows its selectivity.
  A staged data file outside the unit folders (`.md`, `.json`, `.jsonc`, `.yaml`,
  `.yml`, `.toml`, `.txt`) selects only the modules whose code names it: a comment
  or docstring that names it selects nothing. Code files match anywhere.
  Unit and arch modules run under python3; the modules that need uv (unit-uv,
''', 1),
]


def main(argv: list[str]) -> int:
    if not argv:
        print("files: " + " ".join(E))
        return 2
    for rel in argv:
        if rel not in E:
            sys.exit(f"no edits for {rel}")
        path = pathlib.Path(rel)
        text = path.read_text(encoding="utf-8")
        for number, (old, new, count) in enumerate(E[rel], 1):
            found = text.count(old)
            if found != count:
                sys.exit(f"{rel} edit {number}: anchor found {found} times, expected {count}; "
                         "nothing written to this file")
            text = text.replace(old, new)
        path.write_text(text, encoding="utf-8")
        print(f"{rel}: applied {len(E[rel])} edits")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
````

### Appendix F: tmp/quick-test-cuts/refresh_e2e_secs.py (Task 3 Step 5 table refresh)

````python
"""Refresh E2E_RECORDED_SECS in tools/run_unittest_parallel.py from one `--group e2e` run.

Usage (from the worktree root): python3 tmp/quick-test-cuts/refresh_e2e_secs.py
Runs `uv run python tools/run_unittest_parallel.py --group e2e` once, rounds each module's
`=== <module>: ok in <s>s` time up to whole seconds (at least 1), rewrites the table body and the
load figure in its comment, and appends the run to tmp/quick-test-cuts/timings-task3.txt. It
writes nothing when any module failed, a table module did not report, or an anchor is missing.
"""
import math
import os
import pathlib
import re
import subprocess
import sys

RUNNER = pathlib.Path("tools/run_unittest_parallel.py")
LOG = pathlib.Path("tmp/quick-test-cuts/timings-task3.txt")
TABLE_RE = re.compile(r"^E2E_RECORDED_SECS = \{\n(.*?)^\}\n", re.MULTILINE | re.DOTALL)
LOAD_RE = re.compile(r"(\(2026-11-04, )\d+( CPUs, one-minute load )[0-9.]+( at start\))")
LINE_RE = re.compile(r"^=== (tests\.\S+): (ok|FAILED \(rc=-?\d+\)) in ([0-9.]+)s", re.MULTILINE)


def main() -> int:
    text = RUNNER.read_text(encoding="utf-8")
    table = TABLE_RE.search(text)
    if table is None or len(LOAD_RE.findall(text)) != 1:
        sys.exit("anchor missing in tools/run_unittest_parallel.py; nothing written")
    load = os.getloadavg()[0]
    cpus = os.process_cpu_count() or os.cpu_count() or 0
    proc = subprocess.run(["uv", "run", "python", str(RUNNER), "--group", "e2e"],
                          capture_output=True, text=True, check=False)
    results = {m.group(1): (m.group(2), float(m.group(3))) for m in LINE_RE.finditer(proc.stdout)}
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(f"e2e-group load={load:.2f} cpus={cpus} rc={proc.returncode}\n")
        for module, (status, secs) in sorted(results.items()):
            handle.write(f"e2e-group {module} {secs} {status.replace(' ', '_')}\n")
    failed = sorted(m for m, (status, _secs) in results.items() if status != "ok")
    listed = re.findall(r'"(tests\.[^"]+)"', table.group(1))
    missing = sorted(set(listed) - set(results))
    if proc.returncode != 0 or failed or missing:
        print(proc.stdout[-4000:])
        sys.exit(f"not refreshed: rc={proc.returncode} failed={failed} missing={missing}")
    body = "".join(f'    "{module}": {max(1, math.ceil(results[module][1]))},\n'
                   for module in sorted(listed))
    text = text[:table.start(1)] + body + text[table.end(1):]
    text = LOAD_RE.sub(lambda m: f"{m.group(1)}{cpus}{m.group(2)}{load:.2f}{m.group(3)}", text)
    RUNNER.write_text(text, encoding="utf-8")
    print(body, end="")
    print(f"refreshed {len(listed)} entries (load {load:.2f} at start, {cpus} CPUs)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
````

### Appendix G: tmp/quick-test-cuts/time_staged.py (Task 3 docs-only commit cost)

````python
"""Measure what a docs-only commit costs: the --staged selection for the given paths.

Usage (from the worktree root): python3 tmp/quick-test-cuts/time_staged.py LABEL PATH [PATH ...]
Prints and appends to tmp/quick-test-cuts/timings-task3.txt one line
`LABEL staged:<paths> modules=<count> wall=<seconds> rc=<exit>`: the module count comes from
`python3 tools/staged_mapper.py PATH ...` (no test runs), the wall time from timing
`python3 tools/run_unittest_parallel.py --staged PATH ...`, the commit hook's own command.
"""
import pathlib
import subprocess
import sys
import time


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    label, paths = argv[0], argv[1:]
    decided = subprocess.run([sys.executable, "tools/staged_mapper.py", *paths],
                             capture_output=True, text=True, check=False)
    line = next((ln for ln in decided.stdout.splitlines() if ln.startswith("modules:")), "")
    count = len(line.split()[1:])
    started = time.monotonic()
    proc = subprocess.run([sys.executable, "tools/run_unittest_parallel.py", "--staged", *paths],
                          capture_output=True, text=True, check=False)
    wall = time.monotonic() - started
    record = (f"{label} staged:{','.join(paths)} modules={count} wall={wall:.1f} "
              f"rc={proc.returncode}")
    print(record)
    out = pathlib.Path("tmp/quick-test-cuts/timings-task3.txt")
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a", encoding="utf-8") as handle:
        handle.write(record + "\n")
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
````
