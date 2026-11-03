# Phase 28: Fast, environment-proof gates — Specification

**Created:** 2026-11-03
**Ambiguity score:** 0.14 (gate: ≤ 0.20)
**Requirements:** 10 locked

## Goal

The owner's commit runs only the test modules that cover the staged files, and the owner's push runs the full
unit, arch and wizard suites in 60 s or less instead of the 184 s measured on 2026-11-03, with every test tier
giving the same pass or fail in every caller environment and no test calling a real host CLI.

## Background

Live-verified on 2026-11-03 in the ai-kit checkout (24 CPUs, so 9 workers at the 40 % share; scratch HOME,
`AI_KIT_REFUSE_REAL_HOME=1`; scripts and logs under the gitignored `tmp/p28/`):

- **The commit stage runs no tests.** `.pre-commit-config.yaml` runs ruff, pylint, shellcheck and py-compile at
  commit; both test hooks (`unittest` for the `unit` and `arch` groups under system python3, `unittest-wizard`
  for `unit-uv` and `integration` under uv) carry `stages: [pre-push]`. The runner
  (`tools/run_unittest_parallel.py`) runs whole groups or a module list; it has no notion of staged files.
- **The push wait is 184 s**: the core hook 162.9 s and the wizard hook 21.0 s (load average 1.9 at start).
  The roadmap's 2.5 minutes from 2026-11-02 is the same order. The long pole is
  `tests.test_ai_kit_spec_goal_prompt_evals` at 162.4 s; the next modules are `test_precompact_core` 30.2 s,
  `test_wizard_app` 21.0 s, `test_jev_fast_decision` and `test_ai_kit_session_wake_fire` 17.7 s each. With every
  host CLI hidden from PATH the same two hooks finished in 48 s while a second suite shared the machine, and the
  eval module took 4.1 s.
- **Real host CLI calls.** A PATH of logging shims recorded every host call during both hooks. Only two modules
  call host CLIs, and only through the real CLIs they run as subprocesses:
  `tests.test_ai_kit_spec_goal_prompt_evals` (80 calls: `claude --version`/`--help`, `opencode --version`,
  `opencode models`, `opencode serve --hostname 127.0.0.1 --port 0`, `codex debug models`, `pi --mode rpc …`,
  `cursor-agent models`) and `tests.test_gsd_curated_eval` (one `pi --mode rpc` and one `codex debug models`,
  through `tests/gsd_curated_eval.py`). With the host CLIs absent from PATH,
  `test_long_goal_eval_renders_the_pointer_form` fails.
- **Other environment dependence seen.** `tests.test_markdown_to_pdf.test_real_render_produces_image` runs the
  real `mmdc` and fails under a clean HOME ("Could not find chrome-headless-shell"), because Chrome lives in the
  caller's HOME cache. `tests.test_precompact_core.test_header_counts_property` failed once (18 unclassified
  chunks, 2 expected) while two full suites shared the machine; the code under test classifies 40 chunks, each a
  subprocess, inside a fixed 8 s wall-clock budget (`CLASSIFY_SECONDS`, `tools/hooks/precompact_core.py`).
  Reproduction: the failure did not recur in 9 further runs (3 idle; 3 under `stress-ng --cpu 24`, load 22-30,
  84-88 s per run; 2 under `--cpu 48`, load 46-53; 2 beside a full core suite; 1 under `--cpu 24 --fork 16`,
  113 s), so plain CPU load alone does not trigger it. The mechanism is proven instead: with the budget shortened
  in-process to 0.5 s the same test fails the same way (3 unclassified, 2 expected), and at 0.2 s 25 against 2.
  The test's result therefore depends on how fast the machine spawns 40 processes, which is environment
  dependence.
  The todo and the milestone inputs record two more: a goal-prompt test that passes only from a short checkout
  path (coupled to a tool-substitution-hook test), and the no-git e2e case in `tests/test_worktree_e2e.py` that
  fails when its temporary directory sits inside a git repository. Neither was reproduced in this spec step.
- **How tests reach code.** 81 of the 95 `tests/test_*.py` modules reach the code under test through path
  strings, `sys.path` inserts, `importlib` or subprocesses rather than plain imports, and many read `SKILL.md`
  files and other docs as data. A plain import graph alone cannot map a staged file to its tests.
- **Tests that read the real `.planning/`.** `tests/test_phase26_owner_captures.py`,
  `tests/test_pi_live_tools.py` and `tests/test_tool_advisor_core.py` load checkers and data from archived v1.3
  phase folders; `tests/test_curated_config_script.py` (`TestDogfoodCopy`) checks that the project's own
  `.planning/scripts/cross-ai.mjs` is a pristine render of the template; `tests/test_curated_config_e2e.py` and
  `tests/test_curated_config_apply_e2e.py` hash the real `.planning/config.json` (and runner) before and after a
  run as no-write guards; `tests/gsd_curated_eval.py` reads `.planning/config.json`.
- **Runner self-test budgets.** `skills/ai-kit-spec-review/references/cross-ai.mjs --self-test` runs in the e2e
  tier (`tests/test_cross_ai_runner_e2e.py`). Each case has a hard 30 s limit (`runCaseProcess`), signal waits of
  10 s and a 2.9 s signal-to-exit ceiling, plus per-case elapsed ceilings (5, 10, 15, 30 and 80 s) and floors
  (for example "killed live" under 2.5 s). Nothing reads host load. The real run limits (the 30-minute outer
  limit, `budgetMs`) are separate.
- **Structural tests today.** `tests/test_gate_scope.py` pins the groups, hooks and generated listings;
  `tests/test_arch.py` holds the AST rules with a non-vacuity class. No rule looks at host CLI calls or
  `.planning/` reads.

## Requirements

1. **Commit runs the covering tests**: A commit runs, in parallel at the runner's CPU share, only the test modules that cover the staged files, and the commit is refused when any of them fails.
   - Current: the commit stage runs no tests; tests run only at push.
   - Target: a pre-commit-stage test step maps each staged file to the test modules that cover it (through imports, the path strings and `sys.path` inserts tests use to reach code, files tests read as data, and the runner's group lists) and runs exactly those modules, each module under the interpreter its group needs (system python3, or uv for the wizard groups).
   - Acceptance: a fixture commit touching one module runs only the modules the mapper lists for it, in parallel, and exits non-zero (commit refused) when one of them fails; a change to a file read only as data by one test module runs that module.

2. **Commit fallback is fail-safe**: A staged file that no test covers runs no tests, while a change to shared test machinery or any mapper failure runs the full unit and arch suites.
   - Current: no mapping exists.
   - Target: staged files with no covering module add nothing; staged files under the shared test machinery (the runner, `tests/` helpers and fixtures shared by more than one module, the hook config, the generated listings' source) or a mapper error, crash or unreadable input run the full `unit` and `arch` groups.
   - Acceptance: fixtures prove the three cases: a planning-only commit runs zero modules and passes; a commit touching `tools/run_unittest_parallel.py` runs every `unit` and `arch` module; a mapper forced to fail runs every `unit` and `arch` module and never zero.

3. **Push suites finish in 60 s**: The two pre-push test hooks together finish in 60 s or less on the owner's machine, with the before and after times recorded.
   - Current: 184 s (core 162.9 s, wizard 21.0 s) on 2026-11-03, 24 CPUs, load average 1.9 at start.
   - Target: the `unittest` and `unittest-wizard` hooks run back to back in 60 s or less of wall time on the same machine at the same 40 % CPU share.
   - Acceptance: the phase records the before time and the after time of both hooks, each with the CPU count, the worker count and the load average at start, and the after time is 60 s or less.

4. **No test calls a host CLI**: No test in any tier (unit, arch, wizard, e2e) runs a real host CLI; host behaviour comes from fakes only.
   - Current: the goal-prompt eval module makes 80 real host calls per run and the curated-config eval helper makes 2.
   - Target: host CLIs (every binary the runtime table in `skills/ai-kit-spec-review/ai_kit_spec/detection.py` names, plus the goal-prompt host map) are replaced by fakes on a test-controlled PATH; `git`, `node` (the checkout-local gsd-core) and `python` stay allowed.
   - Acceptance: a run of all four tiers with logging shims for every host CLI name on PATH records zero calls.

5. **A structural test bans host CLI calls**: A structural test fails when a test module, or a test helper it loads, can run a real host CLI, and its non-vacuity counterpart proves it catches one.
   - Current: no rule exists.
   - Target: a structural test beside `tests/test_gate_scope.py` or in `tests/test_arch.py` flags a test that runs a host CLI name or resolves one from the caller's PATH without a fake in front.
   - Acceptance: the test passes on the tree after this phase, and a synthetic module that runs `claude --version` makes it fail.

6. **Outside tools run only in e2e**: Tests that need an outside tool other than git, node and python run only in the e2e tier and skip with a stated reason when the tool is missing.
   - Current: the real Mermaid render test runs `mmdc` with headless Chrome in the unit tier and errors under a clean HOME.
   - Target: such tests live in the e2e group; when the tool or its runtime (such as Chrome) is missing they skip with a named reason.
   - Acceptance: `tests.test_markdown_to_pdf` passes in the unit tier under a clean HOME, and the real-render test is in the e2e group and reports a named skip when `mmdc` or Chrome is absent.

7. **Every tier gives the same result in six environments**: All four tiers give the same pass or fail in a plain terminal, inside a host session, with no host CLI on PATH, from a long checkout path, with a custom TMPDIR and from outside a git repository, and a skip happens only with a named reason that is the same everywhere.
   - Current: the goal-prompt eval module, the Mermaid render test, the precompact header-count test, the short-path goal-prompt test and the no-git e2e test depend on the caller's environment.
   - Target: host signals, PATH, checkout path length, TMPDIR, HOME and whether the cwd is inside a git repository are pinned per test; code under test with wall-clock budgets is tested with an injected clock or budget, not the machine's speed.
   - Acceptance: a matrix run of all four tiers in the six environments gives identical pass/fail per module and identical skip reasons.

8. **Self-test budgets scale with load**: The runner self-test's time ceilings scale with the measured load per CPU, capped at four times, while its floors and the real run limits stay unchanged.
   - Current: fixed ceilings (30 s per case, 10 s waits, 2.9 s signal exit, 5-80 s per-case elapsed checks); nothing reads load.
   - Target: each self-test ceiling is multiplied by a factor from the measured load per CPU, never below 1 and never above 4; floors (minimum elapsed checks) do not scale; `budgetMs` and the real run limits do not change.
   - Acceptance: an injected load reading proves factor 1 at idle, a proportional factor in between and 4 at and above the cap; one self-test run under real CPU stress passes; the real run limits are byte-identical in the template before and after.

9. **No test reads `.planning/`**: No test module reads, opens, globs or loads a path under the repo's `.planning/`, and a structural test with no exceptions fails when one does.
   - Current: seven test files read the real `.planning/` (archived phase checkers and data, the runner copy, the real config).
   - Target: the data each test needs is copied into `tests/fixtures/`; a structural test with a non-vacuity counterpart flags a test that builds a path under the repo's `.planning/`; tests that create their own `.planning/` inside a temporary project stay allowed.
   - Acceptance: the structural test passes on the tree after this phase with an empty exception list, and a synthetic module that opens `REPO_ROOT / ".planning" / "STATE.md"` makes it fail.

10. **Live-project checks move out of the tests**: The runner-copy check and the two curated-config no-write guards run as a `make` check or a doctor step instead of as tests.
    - Current: `TestDogfoodCopy` and the no-write hashes in two e2e modules read the real `.planning/`.
    - Target: one documented command (a `make` target or a doctor step) checks that the project's runner copy is a pristine render of the template and that the curated-config runs leave the real config and runner untouched; the tests run against temporary copies.
    - Acceptance: the command exits 0 on a clean checkout, exits non-zero when the runner copy is edited, and AGENTS.md Testing and the README testing section name it alongside the commit and push stages.

## Boundaries

**In scope:**
- A pre-commit-stage test step and a staged-file to test-module mapper, with the fail-safe fallback.
- Fakes in place of every real host CLI call in the test suite, and the host-CLI structural test.
- Moving outside-tool tests to e2e with named skips.
- Pinning the caller's environment per test across all four tiers, including the precompact budget test, the
  short-path goal-prompt test and the no-git e2e test.
- Load-scaled self-test ceilings in `cross-ai.mjs` (template and its rendered copies through the existing render
  path).
- Copying `.planning/` test data into `tests/fixtures/`, the `.planning/` structural test, and the live-project
  check command.
- Recording the before and after push times, and updating AGENTS.md Testing, the README testing section and the
  runner's docstring.

**Out of scope:**
- A concurrency test suite for shared state (status-line caches, wake schedule, jev answer log, two setup runs) —
  optional for a desktop and CLI tool; the run lock (Phase 38) and the wake grid (Phase 50) keep their own.
- The per-phase branch, logical-commit and chained-PR flow — Phase 29; this phase runs on main.
- Live checks against real host CLIs — owner-attended, Phase 54.
- Changing pyright, vulture, ruff or pylint hook scope or stages — the requirement covers the test hooks only.
- Changing the real run limits of the cross-AI runner — the requirement keeps them unchanged.
- The whole-tree architecture-layer suite — backlog 999.3.

## Constraints

- The runner and the mapper stay stdlib-only and run under system python3; uv is reached only for the groups that
  already need it.
- Parallelism stays a CPU share capped at 40 % (`worker_count`); `AI_KIT_TEST_CPU_SHARE` may only lower it; no
  hardcoded worker or core count.
- No `--no-verify`; the commit refusal comes from the hook's exit code.
- Every new structural rule gets a non-vacuity counterpart (`TestArchNonVacuity` pattern).
- No test touches the owner's real config files; tests use temporary directories and synthetic content.
- No absolute machine path in source, tests or fixtures.

## Acceptance Criteria

- [ ] A fixture commit touching one module runs only its covering modules, in parallel, and is refused when one fails.
- [ ] A change to a file read only as data by one test module runs that module at commit.
- [ ] A planning-only commit runs zero test modules and passes.
- [ ] A commit touching the runner, a shared `tests/` helper or fixture, or the hook config runs the full `unit` and `arch` groups.
- [ ] A forced mapper failure runs the full `unit` and `arch` groups, never zero modules.
- [ ] The two pre-push test hooks together finish in 60 s or less; before and after times are recorded with CPU count, worker count and load average.
- [ ] A four-tier run with logging shims for every host CLI name records zero host calls.
- [ ] The host-CLI structural test passes on the tree and fails on a synthetic `claude --version` caller.
- [ ] `tests.test_markdown_to_pdf` passes in the unit tier under a clean HOME; the real-render test is in e2e and skips with a named reason without `mmdc` or Chrome.
- [ ] A six-environment matrix run of all four tiers gives identical pass/fail per module and identical skip reasons.
- [ ] Injected load readings give factor 1 at idle, a proportional factor between, and 4 at the cap; floors are unchanged.
- [ ] One runner self-test run under real CPU stress passes; the real run limits are unchanged in the template.
- [ ] The `.planning/` structural test passes with an empty exception list and fails on a synthetic `REPO_ROOT / ".planning"` reader.
- [ ] The live-project check command exits 0 on a clean checkout and non-zero when the runner copy is edited.
- [ ] AGENTS.md Testing and the README testing section describe the commit stage, the push stage and the live-project check.

## Edge Coverage

**Coverage:** 40/40 applicable edges resolved · 0 unresolved

| Category | Requirement | Status | Resolution / Reason |
|----------|-------------|--------|---------------------|
| adjacency | R1 | ✅ covered | Two staged files covered by the same module run that module once |
| empty | R1 | ✅ covered | A commit with no staged files (amend of the message only) runs zero modules and passes |
| ordering | R1 | 🧪 backstop | The selected module set does not depend on the order files are staged (held-out edge test) |
| concurrency | R1 | 🧪 backstop | Selected modules run through the existing one-subprocess-per-module runner, each with its own TMPDIR |
| adjacency | R2 | ✅ covered | A commit mixing an uncovered file and a shared-machinery file runs the full `unit` and `arch` groups |
| empty | R2 | ✅ covered | A mapper that returns an empty answer for a covered file is treated as a failure and runs the full groups |
| ordering | R2 | 🧪 backstop | The fallback decision is the same whichever staged file triggers it first (held-out edge test) |
| concurrency | R2 | 🧪 backstop | The mapper reads the tree and the staged list only; it writes nothing, so parallel commits in two worktrees cannot interfere |
| boundary | R3 | ✅ covered | 60.0 s passes and 60.1 s fails the target; the time is wall time of both hooks back to back |
| adjacency | R3 | ✅ covered | The core and wizard hooks are timed separately and summed; neither hook's time hides the other |
| empty | R3 | ✅ covered | A run where a hook fails or skips modules does not count as an after time |
| ordering | R3 | 🧪 backstop | The core hook still runs before the wizard hook (`test_core_hook_precedes_wizard_hook` keeps holding) |
| precision | R3 | ✅ covered | Times are recorded to 0.1 s with the CPU count, worker count and one-minute load average at start |
| adjacency | R4 | ✅ covered | A test that needs a host's output gets it from a fake on a test-controlled PATH, never from the real binary next to it on PATH |
| empty | R4 | ✅ covered | With no host CLI installed at all, every tier still passes (same as with them installed) |
| encoding | R4 | 🧪 backstop | Host names are matched as whole binary names from the runtime table and the goal-prompt host map (`agent` and `cursor-agent` included) |
| ordering | R4 | 🧪 backstop | A fake earlier on PATH wins over a real binary later on PATH; the shim log run proves it |
| empty | R5 | ✅ covered | A test tree with no host-CLI caller passes the structural test; the synthetic caller fails it |
| encoding | R5 | 🧪 backstop | The rule catches a host name passed as a list element, a string command and a `shutil.which` lookup (non-vacuity cases) |
| adjacency | R6 | ✅ covered | The Mermaid unit tests that use a fake renderer stay in the unit tier beside the moved real-render test |
| empty | R6 | ✅ covered | With `mmdc` or Chrome absent the e2e test reports a named skip, not an error |
| ordering | R6 | 🧪 backstop | The group move keeps every module in exactly one group (`test_every_module_in_exactly_one_group`) |
| boundary | R7 | ✅ covered | The long checkout path case uses a path of at least 200 characters; the plain case uses the normal checkout |
| adjacency | R7 | ✅ covered | The short-path goal-prompt test and the tool-substitution hook test pass together from both path lengths |
| empty | R7 | ✅ covered | The no-host-CLI case runs with an empty host set on PATH and gives the same results |
| encoding | R7 | 🧪 backstop | A TMPDIR containing a space is one of the custom TMPDIR cases (held-out edge test) |
| ordering | R7 | 🧪 backstop | Results do not depend on module order or on which modules share the machine at the same time |
| precision | R7 | ✅ covered | Code with wall-clock budgets (the precompact classify budget) is tested with an injected clock or budget, so machine speed cannot change the count |
| boundary | R8 | ✅ covered | Load per CPU at or below 1 gives factor 1; at or above the cap point the factor is exactly 4 |
| adjacency | R8 | ✅ covered | Floors such as "killed live under 2.5 s" stay fixed even when the ceiling next to them scales |
| empty | R8 | ✅ covered | When no load reading is available (no `os.loadavg` value) the factor is 1 |
| ordering | R8 | 🧪 backstop | The factor is read once per self-test run, so cases in one run share the same factor |
| precision | R8 | 🧪 backstop | The scaled ceiling is rounded up to whole milliseconds, never down |
| adjacency | R9 | ✅ covered | A temporary project's own `.planning/` built by a test stays allowed; only the repo's `.planning/` is flagged |
| empty | R9 | ✅ covered | The exception list is empty and the structural test rejects a non-empty one |
| ordering | R9 | 🧪 backstop | The rule catches the path built in any order of joins (`ROOT / ".planning"`, `os.path.join(ROOT, ".planning", …)`) |
| idempotency | R9 | 🧪 backstop | Copied fixtures are checked in; re-running the tests never rewrites them |
| concurrency | R9 | 🧪 backstop | Tests read fixtures read-only, so parallel modules cannot race on them |
| empty | R10 | ✅ covered | On a checkout with no runner copy the command reports the copy as absent and exits non-zero only when it should exist |
| encoding | R10 | 🧪 backstop | The runner-copy comparison is byte-exact on the template body outside the rendered config block |

## Prohibitions (must-NOT)

**Coverage:** 3/3 applicable prohibitions resolved · 0 unresolved

| Prohibition (must-NOT statement) | Requirement | Status | Verification / Reason |
|----------------------------------|-------------|--------|------------------------|
| The commit step MUST NOT pass a commit with zero tests run when the mapper failed | R2 | resolved | verification: test (forced mapper failure runs the full `unit` and `arch` groups) |
| Load scaling MUST NOT lengthen the real cross-AI run limits or shorten any floor | R8 | resolved | verification: test (template limits byte-identical; floor checks unchanged) |
| A test MUST NOT reach the owner's real host configuration or real host CLI to make a result pass | R4, R7 | resolved | verification: test (host-call shim log empty; scratch-HOME matrix run) |

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes                                                  |
|--------------------|-------|------|--------|--------------------------------------------------------|
| Goal Clarity       | 0.90  | 0.75 | ✓      | 60 s push target, covering-tests commit                |
| Boundary Clarity   | 0.85  | 0.70 | ✓      | tiers, allowed tools, out-of-scope list explicit        |
| Constraint Clarity | 0.80  | 0.65 | ✓      | CPU share, stdlib, load cap 4x, floors fixed            |
| Acceptance Criteria| 0.85  | 0.70 | ✓      | fixture commits, shim log, six-environment matrix       |
| **Ambiguity**      | 0.14  | ≤0.20| ✓      | 1 − (0.315 + 0.2125 + 0.16 + 0.17)                      |

Status: ✓ = met minimum, ⚠ = below minimum (planner treats as assumption)

## Interview Log

Interactive, 2 rounds (both batches answered by the owner through the orchestrator). The decision ladder was not
used: in the interactive path it screens only items the owner asks to screen, and none were. Rule: `mvp-mode`
inactive, the best design wins over the smallest diff (DESIGN-01: simple is not easy, no half-done feature).

| Round | Perspective | Question summary | Decision locked |
|-------|-------------|------------------|-----------------|
| 1 | Researcher | The push-time target as a number | Both test hooks together in 60 s or less on this machine; before and after recorded with CPU count and load (R3) |
| 1 | Researcher + Simplifier | Which outside programs tests may run | Host CLIs never, in any tier; git, node (checkout-local gsd-core) and python allowed; other tools only in e2e, named skip when missing (R4, R6) |
| 1 | Simplifier | What the commit step does for an uncovered file | Uncovered file runs nothing; shared test machinery change or mapper failure runs the full `unit` and `arch` groups (R2) |
| 2 | Boundary Keeper | Which tiers must be environment-proof | All four tiers; same pass/fail in six environments; skips only with a named reason, the same everywhere (R7) |
| 2 | Failure Analyst | How far self-test ceilings may stretch | Scale with load per CPU up to 4x; floors never scale; injected reading plus one real stress run; real limits unchanged (R8) |
| 2 | Failure Analyst | The tests that read the real `.planning/` | Data copied into `tests/fixtures`; runner-copy check and the two no-write guards move to a make check or doctor step; no exceptions (R9, R10) |
| 2 | Seed Closer (orchestrator note) | The precompact wrong result under shared load | Environment dependence, in this phase; reproduced before any claim (Background, R7) |
| after 2 | Edge and prohibition probes | The engine's 40 edge rows and the must-NOT pass | Resolved by the orchestrating agent (23 covered, 17 backstop, none dismissed) and 3 prohibitions kept; not shown to the owner row by row, open to change in discuss |
