# Phase 28: Fast, environment-proof gates - Context

**Gathered:** 2026-11-03 (interactive, standard discuss mode `--analyze --all --batch`, after 28-SPEC.md; best over easy, DESIGN-01)
**Status:** Ready for planning

<domain>
## Phase Boundary

The commit stage runs only the test modules that cover the staged files; the push stage runs the full unit,
arch and wizard suites in 60 s or less with fakes only; every test tier gives the same result in six caller
environments; the runner self-test's ceilings scale with load; no test reads the repo's `.planning/`. Runs on
main, before Phase 29's per-phase branch flow exists.
</domain>

<spec_lock>
## Requirements (locked via SPEC.md)

**10 requirements are locked.** See `28-SPEC.md` for full requirements, boundaries, and acceptance criteria.

Downstream agents MUST read `28-SPEC.md` before planning or implementing. Requirements are not duplicated here.

**In scope (from SPEC.md):**
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

**Out of scope (from SPEC.md):**
- A concurrency test suite for shared state — optional for a desktop and CLI tool.
- The per-phase branch, logical-commit and chained-PR flow — Phase 29.
- Live checks against real host CLIs — owner-attended, Phase 54.
- Changing pyright, vulture, ruff or pylint hook scope or stages.
- Changing the real run limits of the cross-AI runner.
- The whole-tree architecture-layer suite — backlog 999.3.
</spec_lock>

<decisions>
## Implementation Decisions

### Commit stage: choosing the tests (SPEC R1, R2)

- **D-01: The mapper is a name index rebuilt at every commit, never cached.** A test module covers a code unit
  (a `skills/<name>/` folder, a `tools/*.py` file, a `tools/hooks/*.py` file) when the module's source, or the
  source of a `tests/` helper it uses by name, names that unit; it covers a data file it names exactly. A staged
  test module always covers itself. Over-approximation is the intended direction.
  - Live: 81 of 95 modules reach code through path strings, `sys.path` inserts, `importlib` or subprocesses,
    so an import graph alone misses most of the suite (`tmp/p28/refs.py`). A rough regex pass over 52 units gave
    a median of 3.5 covering modules per unit and a maximum of 37 (`ai-kit-spec-review`); the real mapper must
    re-measure this.
  - Stdlib-only, under system python3, in `tools/` (the runner or a sibling module it imports; planner's choice).
  - Owner choice (recommended option).
- **D-02: One pre-commit-stage hook calls the runner with the staged file list.** The runner splits the chosen
  modules by group and runs the `unit-uv` and `integration` modules through `uv run`; the `unit` and `arch`
  modules run under the hook's python3. When a wizard module is chosen and uv is missing, the commit is refused
  with a message that points to `make setup-env`. The commit refusal is the hook's non-zero exit.
  - The two existing pre-push hooks stay as they are (`stages: [pre-push]`); `tests/test_gate_scope.py` gains
    rules for the new hook (stage, runner entry, no hardcoded worker count).
  - Owner choice (recommended option).
- **D-03: The shared test machinery list is an explicit set in `tools/run_unittest_parallel.py`, next to the
  group sets, pinned by `tests/test_gate_scope.py`.** A staged file in it, or any mapper error, crash or
  unreadable input, runs the full `unit` and `arch` groups (SPEC R2). An empty mapper answer for a file the index
  says is covered counts as a failure (SPEC edge R2 empty). Stale names in the set fail the gate the way
  `stale_exception_names` does today.
  - Owner choice (recommended option).

### Host CLIs: fakes and enforcement (SPEC R4, R5)

- **D-04: The runner puts a tripwire folder first on every module's PATH.** It holds one stub per host CLI name:
  every binary of the runtime table (`skills/ai-kit-spec-review/ai_kit_spec/detection.py`) plus the goal-prompt
  host map (`HOST_BINARY`, `skills/ai-kit-spec-goal-prompt/scripts/gp_host.py`, which includes `agent`), and
  `cursor-agent`. A stub logs its argv to a per-module log and exits 127 with a message naming the binary.
  Tests that need host behaviour put fakes in front of it through one shared fake helper under `tests/`
  (reuse `tests/cursor_fakes.py` and `tests/session_wake_fakes.py` patterns where they fit).
  - Live: the only real callers are `tests.test_ai_kit_spec_goal_prompt_evals` (80 calls per run, all made by
    the product CLI it runs as a subprocess) and `tests/gsd_curated_eval.py` (2 calls); recorded with a
    logging-shim PATH (`tmp/p28/host_trace.sh`).
  - Owner choice (recommended option).
- **D-05: Two enforcement layers.** An AST rule in `tests/test_arch.py` flags a test or `tests/` helper that names
  a host binary in a subprocess argv, a command string or a `shutil.which` lookup outside the shared fake
  helper, with a `TestArchNonVacuity` case (a synthetic `claude --version` caller) for each form. At run time
  the runner fails any module whose tripwire log is non-empty and prints the logged calls.
  - Owner choice (recommended option).

### Environment baseline and the six-environment proof (SPEC R6, R7)

- **D-06: The runner gives every module a baseline env:** the host signal variables removed
  (`HOST_SIGNAL_ENV_VARS` in `detection.py`, read without importing host families into the runner if the arch
  rules forbid it; a copied list then needs a drift test), the tripwire PATH (D-04), and its own TMPDIR (exists
  in `run_module`). A test that needs a host signal sets it itself (the goal-prompt evals already set
  `CLAUDECODE=1` in `eval_env`).
- **D-07: The six-environment proof is a separate `make test-env-matrix` target**, run during this phase's
  verification and documented in AGENTS.md Testing and the README; it is not part of `make test`, `validate`
  or any hook. It runs all four tiers in: a plain terminal, a host session (host signals set), no host CLI on
  PATH, a checkout path of at least 200 characters, a custom TMPDIR (one case with a space), and a cwd outside
  any git repository; it compares pass/fail per module and the skip reasons.
  - Owner choice (recommended option) for D-06 and D-07.
- **D-08: Tests of code with a wall-clock budget fix the clock or the budget; the product budget stays.** The
  precompact header-count tests patch `core._monotonic` (the existing seam) or `core.CLASSIFY_SECONDS`; the
  product's 8 s `CLASSIFY_SECONDS` in `tools/hooks/precompact_core.py` is unchanged.
  - Live: shortening the budget in-process to 0.5 s and 0.2 s reproduced the observed failure shape
    (`tmp/p28/precompact_budget.py`); 9 loaded runs at the real budget passed.
  - Owner choice (recommended option).
- **D-09: Outside tools beyond git, node and python move to e2e** (SPEC R6): `test_real_render_produces_image`
  leaves `tests/test_markdown_to_pdf.py` for an e2e module (new, listed in `E2E_MODULES`), which skips with a
  named reason when `mmdc` or headless Chrome is missing. The rest of `test_markdown_to_pdf` stays in `unit`.
  - Follows SPEC R6 directly; the module split is the planner's to finalize.

### Runner self-test load scaling (SPEC R8)

- **D-10: The factor is the one-minute `os.loadavg()` value divided by `os.availableParallelism()`, clamped to
  between 1 and 4, read once per self-test run.** Every self-test ceiling (the 30 s case limit in
  `runCaseProcess`, the 10 s `waitFor` waits, the 2.9 s signal-to-exit ceiling, the per-case elapsed ceilings)
  is multiplied by it and rounded up to whole milliseconds; floors (for example "killed live" under 2.5 s) are
  never multiplied. An injected reading (an env var) is honoured only under `--self-test`. `budgetMs` and the
  real run limits do not change. A missing or zero reading gives factor 1.
  - The template is `skills/ai-kit-spec-review/references/cross-ai.mjs`; rendered copies follow through the
    existing render path (the dogfood copy `.planning/scripts/cross-ai.mjs` is re-rendered, not hand-edited).
  - Owner choice (recommended option).

### `.planning/` readers and the live-project check (SPEC R9, R10)

- **D-11: `make check-dogfood` replaces the tests that read the live project.** A stdlib script under `tools/`
  checks that `.planning/scripts/cross-ai.mjs` is a pristine render of the template (today's `TestDogfoodCopy`
  logic in `tests/test_curated_config_script.py`) and runs the curated-config no-write guards (today's hashes in
  `tests/test_curated_config_e2e.py` and `tests/test_curated_config_apply_e2e.py`) against the real config and
  runner. It is also wired as a pre-push hook so it still gates a push. The tests themselves run against
  temporary copies. `tests/gsd_curated_eval.py` stops reading the real `.planning/config.json` (it reads a fixture).
  - Owner choice (recommended option).
- **D-12: Archived-phase checkers are copied with their data into `tests/fixtures/archived/<phase>/`**, each
  copied file starting with a one-line frozen-history header (source path and copy date). Applies to
  `tests/test_phase26_owner_captures.py` (Phase 26 `skill-judge/check_verdicts.py` and `26-OWNER-CAPTURES.md`),
  `tests/test_pi_live_tools.py` (Phase 22 `live/trim_pi_capture.py` and its data) and
  `tests/test_tool_advisor_core.py` (Phase 21.3 `live/check_live.py` and `21.3-LIVE.md`).
  - Owner choice (recommended option).
- **D-13: The `.planning/` structural rule lives beside `tests/test_gate_scope.py` or in `tests/test_arch.py`
  (planner's choice), with an empty exception list it pins.** It flags a path built from the repo root and
  `.planning` in any join form; a temporary project's own `.planning/` stays allowed (SPEC edge R9 adjacency).

### Push timing (SPEC R3)

- **D-14: The before time is the 2026-11-03 measurement** (core 162.9 s, wizard 21.0 s, total 183.9 s; 24 CPUs, 9
  workers, load average 1.86 at start; `tmp/p28/time_prepush.sh`). The after time is measured the same way, with
  the same script shape committed under `tools/` or kept in the verification record (planner's choice), and both
  go into the phase's verification record and the AGENTS.md Testing note.

### Claude's Discretion

- The mapper's module layout inside `tools/`, the tripwire log format and the env var names.
- Whether the new e2e module for the real Mermaid render is a new file or a split class.
- The order of plans, as long as the push timing is measured last.

### Folded Todos

None. The two test fixes from `.planning/todos/pending/2026-11-02-tooling-defects-and-skill-writing-principle-found-at-the-v1.md`
(the short-path goal-prompt test and the no-git e2e test) are already in SPEC R7.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.planning/phases/28-fast-environment-proof-gates/28-SPEC.md` — Locked requirements — MUST read before planning
- `.planning/REQUIREMENTS.md` — GATE-01..05; DESIGN-01 (simple is not easy)
- `.planning/ROADMAP.md` — Phase 28 goal, success criteria and code anchors
- `.planning/milestones/NEXT-MILESTONE-INPUTS.md` — Round 9 (commits, push and tests; self-test budgets)
- `AGENTS.md` — Testing (tiers, runner groups, CPU share), Non-Negotiable Rules (stdlib runtime, no real configs)
- `.pre-commit-config.yaml` — `unittest` and `unittest-wizard` hooks, generated listings
- `tools/run_unittest_parallel.py` — `group_modules`, `hook_groups`, `worker_count`, `run_module`, `main`
- `tools/gen_test_groups.py` — generated listings in the Makefile and hook config
- `Makefile` — tier targets, `validate`
- `tests/test_gate_scope.py`, `tests/test_arch.py` — structural rules and their non-vacuity classes
- `skills/ai-kit-spec-review/ai_kit_spec/detection.py` — runtime table, `HOST_SIGNAL_ENV_VARS`
- `skills/ai-kit-spec-goal-prompt/scripts/gp_host.py` — `HOST_BINARY`, `host_version`, `help_mentions`
- `tests/test_ai_kit_spec_goal_prompt_evals.py` (`eval_env`, `run_cli`), `tests/gsd_curated_eval.py` — real host callers
- `tools/hooks/precompact_core.py` (`CLASSIFY_SECONDS`, `_monotonic`, `classify_all`), `tests/test_precompact_core.py`
- `skills/ai-kit-spec-review/references/cross-ai.mjs` — self-test (`runCaseProcess`, `waitFor`, per-case checks), `budgetMs`
- `tests/test_cross_ai_runner_e2e.py` — self-test callers
- `tests/test_markdown_to_pdf.py` — `test_real_render_produces_image`
- `tests/test_worktree_e2e.py` — the no-git case
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `run_module` already gives each module its own TMPDIR; the baseline env (D-06) and tripwire PATH (D-04) extend
  the same env copy.
- `stale_exception_names` is the pattern for pinning the shared-machinery set (D-03).
- `gen_test_groups.py` regenerates hook listings from discovery; a new hook entry follows the same `-- <names>`
  convention only if it lists modules.
- `tests/cursor_fakes.py`, `tests/session_wake_fakes.py`, `tests/goal_prompt_fixtures.py` already hold fake
  patterns; the shared host fake helper should reuse their shape.
- `core._monotonic` in the precompact core is an existing clock seam (D-08).

### Established Patterns
- One subprocess per module, CPU share capped at 40 %, `AI_KIT_TEST_CPU_SHARE` only lowers it.
- Every structural rule has a non-vacuity counterpart.
- Rendered runner copies are produced by the render path, never hand-edited.

### Integration Points
- `.pre-commit-config.yaml` gains a pre-commit-stage test hook and a pre-push `check-dogfood` hook;
  `tests/test_gate_scope.py` rules (`test_hooks_name_runner_groups`, `test_hook_order_and_serial_runs`) must be
  extended, not bypassed.
- `Makefile` gains `test-env-matrix` and `check-dogfood`, both added to `.PHONY`.
</code_context>

<specifics>
## Specific Ideas

- The measurement and trace scripts used in the spec step live in the gitignored `tmp/p28/`
  (`time_prepush.sh`, `host_trace.sh`, `precompact_budget.py`); they show the method but are not deliverables.
- With all host CLIs hidden, both pre-push hooks ran in 48 s even while a second suite shared the machine, so the
  60 s target is expected to hold from the fakes alone; the next long poles are `test_precompact_core` (30 s) and
  `test_wizard_app` (21 s).
</specifics>

<deferred>
## Deferred Ideas

- A concurrency test suite for shared state (status-line caches, wake schedule, jev answer log, two setup runs) —
  optional per the owner; not scheduled.
- Real-host smoke checks of the goal-prompt and curated-config host detection, which the fakes replace here —
  handed to Phase 54's discuss (its agent-run live checks are the natural home; its criteria do not name this
  check today).
</deferred>
