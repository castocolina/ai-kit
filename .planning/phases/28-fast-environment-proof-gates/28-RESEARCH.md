# Phase 28: Fast, environment-proof gates - Research

**Researched:** 2026-11-03
**Domain:** Python stdlib test-runner/gate engineering (pre-commit hooks, unittest runner, AST structural tests), one Node self-test harness
**Confidence:** HIGH for repo facts (read this session), MEDIUM for the mapper's real hit-rate (not yet measured by the real mapper)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
D-01 Mapper is a name index rebuilt at every commit, never cached. A test module covers a code unit (a `skills/<name>/` folder, a `tools/*.py` file, a `tools/hooks/*.py` file) when the module's source, or the source of a `tests/` helper it uses by name, names that unit; it covers a data file it names exactly. A staged test module always covers itself. Over-approximation is intended. Stdlib-only, system python3, in `tools/` (runner or a sibling module; planner's choice).
D-02 One pre-commit-stage hook calls the runner with the staged file list. Runner splits chosen modules by group: `unit-uv` and `integration` through `uv run`; `unit` and `arch` under the hook's python3. Wizard module chosen and uv missing: commit refused with a message pointing to `make setup-env`. Existing two pre-push hooks stay (`stages: [pre-push]`); `tests/test_gate_scope.py` gains rules for the new hook (stage, runner entry, no hardcoded worker count).
D-03 Shared test machinery list is an explicit set in `tools/run_unittest_parallel.py` next to the group sets, pinned by `tests/test_gate_scope.py`. A staged file in it, or any mapper error/crash/unreadable input, runs full `unit` and `arch` groups. Empty mapper answer for a file the index says is covered = failure. Stale names fail the gate like `stale_exception_names`.
D-04 Runner puts a tripwire folder first on every module's PATH with one stub per host CLI name: every binary of the runtime table (`detection.py`) plus goal-prompt `HOST_BINARY` (`gp_host.py`, includes `agent`), and `cursor-agent`. A stub logs argv to a per-module log and exits 127 naming the binary. Tests needing host behaviour put fakes in front through one shared fake helper under `tests/` (reuse `tests/cursor_fakes.py`, `tests/session_wake_fakes.py` patterns).
D-05 Two enforcement layers: AST rule in `tests/test_arch.py` flagging a test or `tests/` helper that names a host binary in a subprocess argv, a command string or a `shutil.which` lookup outside the shared fake helper, with a `TestArchNonVacuity` case per form (synthetic `claude --version`); at run time the runner fails any module whose tripwire log is non-empty and prints the calls.
D-06 Runner gives every module a baseline env: host signal vars removed (`HOST_SIGNAL_ENV_VARS`; a copied list needs a drift test if arch rules forbid the import), tripwire PATH, own TMPDIR. A test needing a host signal sets it itself.
D-07 Six-environment proof is a separate `make test-env-matrix` target (not in `make test`, `validate`, or any hook), run during verification, documented in AGENTS.md Testing and README. All four tiers in: plain terminal, host session, no host CLI on PATH, checkout path >= 200 chars, custom TMPDIR (one with a space), cwd outside any git repo; compares pass/fail per module and skip reasons.
D-08 Wall-clock-budget code tests fix the clock or budget; product budget stays. Precompact header-count tests patch `core._monotonic` or `core.CLASSIFY_SECONDS`; product 8 s `CLASSIFY_SECONDS` unchanged.
D-09 `test_real_render_produces_image` leaves `tests/test_markdown_to_pdf.py` for a new e2e module in `E2E_MODULES`, skipping with a named reason when `mmdc` or headless Chrome is missing. Rest stays in `unit`.
D-10 Self-test factor = one-minute `os.loadavg()` / `os.availableParallelism()`, clamped 1..4, read once per self-test run. Every ceiling (30 s case limit in `runCaseProcess`, 10 s `waitFor` waits, 2.9 s signal-to-exit, per-case elapsed ceilings) multiplied and rounded up to whole ms; floors (e.g. "killed live" < 2.5 s) never multiplied. Injected reading (env var) honoured only under `--self-test`. `budgetMs` and real run limits unchanged. Missing/zero reading = factor 1. Template `skills/ai-kit-spec-review/references/cross-ai.mjs`; rendered copies follow via the existing render path (dogfood `.planning/scripts/cross-ai.mjs` re-rendered, not hand-edited).
D-11 `make check-dogfood` replaces tests that read the live project: stdlib script under `tools/` checks `.planning/scripts/cross-ai.mjs` is a pristine render of the template (today's `TestDogfoodCopy`) and runs the curated-config no-write guards against the real config and runner; also a pre-push hook. Tests run against temp copies. `tests/gsd_curated_eval.py` reads a fixture, not the real config.
D-12 Archived-phase checkers copied with data into `tests/fixtures/archived/<phase>/`, each copied file starting with a one-line frozen-history header (source path, copy date). Applies to `test_phase26_owner_captures.py`, `test_pi_live_tools.py`, `test_tool_advisor_core.py`.
D-13 `.planning/` structural rule beside `tests/test_gate_scope.py` or in `tests/test_arch.py` (planner's choice), empty pinned exception list; flags a path built from repo root and `.planning` in any join form; a temp project's own `.planning/` stays allowed.
D-14 Before time = 2026-11-03 measurement (core 162.9 s, wizard 21.0 s, total 183.9 s; 24 CPUs, 9 workers, load 1.86). After time measured the same way; script shape committed under `tools/` or kept in the verification record (planner's choice); both go into verification record and AGENTS.md Testing.

### Claude's Discretion
Mapper layout inside `tools/`, tripwire log format and env var names; new e2e file vs split class for the Mermaid render; order of plans, provided push timing is measured last.

### Deferred Ideas (OUT OF SCOPE)
Concurrency test suite for shared state; real-host smoke checks of goal-prompt/curated-config host detection (Phase 54). Also out: per-phase branch flow (Phase 29), pyright/vulture/ruff/pylint hook scope, real cross-AI run limits, whole-tree arch suite (999.3).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| GATE-01 | Commit runs covering tests, refuses on failure | Mapper design, pre-commit hook shape (serial, always_run), runner `--staged` mode |
| GATE-02 | Fail-safe fallback | Shared-machinery set, error-path-runs-full rule, tests via synthetic repo |
| GATE-03 | Push in 60 s | Tripwire/fakes remove the 162 s eval pole; remaining poles listed |
| GATE-04 | No host CLI calls + structural test | Tripwire PATH, AST rule, fake helper, non-vacuity forms |
| GATE-05 | Same result in six envs, load-scaled self-test, no `.planning/` readers, live check | Baseline env, matrix target, cross-ai.mjs scaling sites, fixtures, check-dogfood |
</phase_requirements>

## Summary

All work is stdlib Python plus one Node file. The runner (`tools/run_unittest_parallel.py`, 241 lines, read in full) already isolates each module in a subprocess with its own TMPDIR; every new behaviour (baseline env, tripwire PATH, staged-file mode) extends `run_module`'s env copy and `main`. The slow push is dominated by one module (`test_ai_kit_spec_goal_prompt_evals`, 162.4 s) that shells out to real host CLIs through the product CLI it runs; hiding host CLIs alone brought both hooks to 48 s in the spec step, so the 60 s target is mostly a fakes problem, not a parallelism problem.

The biggest planning risks are hidden environment inheritance, not the mapper: a commit hook runs with `GIT_INDEX_FILE` and other `GIT_*` variables set, which leak into every test that runs `git` in a temp repo. The baseline env must scrub them, otherwise the new commit-stage tests behave differently from push-stage tests (the exact environment dependence this phase removes).

**Primary recommendation:** Build in this order: (1) baseline env + tripwire in `run_module` (fixes the pole, enables everything else), (2) fakes/eval-module rework and AST rule, (3) fixtures + `.planning/` rule + check-dogfood, (4) env pinning fixes + e2e Mermaid split, (5) cross-ai.mjs scaling, (6) mapper + commit hook, (7) matrix target, docs, then push timing last.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary | Rationale |
|------------|-------------|-----------|-----------|
| Staged-file mapping | `tools/` stdlib module | runner | Must run under system python3 at commit |
| Per-module env/PATH pinning | runner (`run_module`) | tests (opt-in host signal) | One place gives every tier the same baseline |
| Host-CLI ban | runner tripwire (runtime) | `tests/test_arch.py` (static) | Static misses dynamic argv; runtime misses unexecuted paths |
| `.planning/` reader ban | structural test | fixtures | Static AST is sufficient |
| Live-project check | `tools/` script + Makefile + pre-push hook | none | Not a test; reads the live tree by design |
| Self-test load scaling | `cross-ai.mjs` template | render path | Copies must be re-rendered |

## Standard Stack

Stdlib only (runtime and runner rules, AGENTS.md). Existing dev env: `ruff~=0.14`, `pylint~=4.0`, `pyright~=1.1`, `vulture~=2.14`, `pre-commit` (4.6.2 on this machine, `uv` 0.11.28, `nproc` 24) [VERIFIED: ran `pre-commit --version`, `uv --version`, `nproc`]. No new packages are needed, so no Package Legitimacy Audit applies. Do not add a dev dependency.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| name-index mapper | `coverage.py` per-test coverage map | New dependency, cached state, stale; rejected by D-01 |
| tripwire PATH | `unittest.mock` patching everywhere | Misses real subprocesses the product CLI spawns (the 80 calls) |

## Architecture Patterns

### Data flow
```
git commit -> pre-commit (staged files, serial) -> tools mapper
   mapper: staged files -> [shared machinery? / error?] -> full unit+arch
                        -> [index: name -> covering modules] -> module set (deduped, order-independent)
   runner: module set -> split by group -> unit/arch under python3 | unit-uv/integration under `uv run`
        -> per module: subprocess(env = baseline: no host signals, GIT_* scrubbed, tripwire PATH first, own TMPDIR)
        -> tripwire log non-empty => module FAILED + calls printed
   exit != 0 => commit refused
```

### Hook shape (pre-commit)
New hook: `language: system`, `entry: python3 tools/run_unittest_parallel.py --staged` (name is planner's), `pass_filenames: true`, `require_serial: true` (pre-commit splits long file lists across several parallel processes otherwise, and each would map only its slice - and a fail-safe full run could then run several times) [CITED: pre-commit docs, `require_serial`; ASSUMED for the batching size], `always_run: true` not needed for staged-file hooks, but the zero-file case must still exit 0 in the runner. Stage defaults to pre-commit; place it after `pylint` and before `unittest` so `test_hook_order_and_serial_runs` (asserts ruff < pylint < unittest < unittest-wizard; read at `tests/test_gate_scope.py:422-428`) keeps holding; extend that test with the new id.

`tests/test_gate_scope.py:319-324` asserts hook entries start with exact strings and that every hook entry names each module from `hook_groups()` after `--`. The new hook must not carry a module list (it lists none), so `gen_test_groups.refresh_hook_entries` (only rewrites ids in `hook_listings`) is unaffected [VERIFIED: tools/gen_test_groups.py:52-65]. `test_hooks_cover_every_group_except_e2e` (`:336`) computes group names from all hook entries; the new hook uses `--staged` not `--group`, so confirm `hook_group_names` ignores it (read it before editing).

`tests/test_run_unittest_parallel.py` has `test_mixing_group_and_module_names_is_usage_error` (`:113`) - a `--staged` mode must keep module/group mixing an error.

### Mapper design notes (D-01)
- Index units: `skills/<name>/`, `tools/*.py`, `tools/hooks/*.py`; match on whole-token names (e.g. `precompact_core`, `ai-kit-spec-review`) in module source and in `tests/` helper source the module names (helpers: `cursor_fakes.py`, `session_wake_fakes.py`, `goal_prompt_fixtures.py`, `gsd_curated_eval.py`). Use word-boundary regex, not substring (`tools/setup.py` vs `setup`-prefixed words).
- Data files: exact path or basename named in module source; `tests/fixtures/**` mapped by the same rule, but a fixture named by more than one module is shared machinery -> full run (SPEC R2).
- Staged deletions/renames: map both old and new paths (`git diff --cached --name-status`), pre-commit passes only existing files by default; deleted files are not passed. A deleted code unit's tests should still run -> either read the staged list via `git diff --cached --name-only --diff-filter=ACMRD` inside the mapper or document the gap. Recommend the former (fail-safe direction).
- Order independence and dedupe: sort + set; tested by permutation test.
- Empty-answer rule: a file the index lists as covered but mapping returns nothing -> full run.
- Measured earlier (spec step, rough regex): median 3.5 modules/unit, max 37 for `ai-kit-spec-review` [CITED: 28-CONTEXT.md D-01]; the real mapper must re-measure and the verification record should store it.

### Tripwire / baseline env (D-04, D-06)
- Create the stub folder per module inside the module's own TemporaryDirectory so logs are per module and cleaned with it; stubs are tiny `#!/bin/sh` scripts (log argv, print message, `exit 127`) - `/bin/sh` is allowed, no new binary dependency.
- Binary names [VERIFIED: skills/ai-kit-spec-review/ai_kit_spec/detection.py:79-125]: `pi`, `opencode`, `cursor-agent`, `agent`, `codex`, `claude`, `copilot`, `grok`. Goal-prompt map [VERIFIED: gp_host.py:21-27]: `claude`, `codex`, `pi`, `opencode`, `agent`. Derive the list from `RUNTIMES[...]` binaries at runner start via a tiny import or a copied tuple with a drift test (the runner must stay stdlib-only and must not import host families; `tests/test_arch.py` enforces host-family isolation for status-line modules only - check whether `tools/run_unittest_parallel.py` is covered before choosing import vs copy; a copy plus a drift test against `RUNTIMES` is the safe default).
- `HOST_SIGNAL_ENV_VARS` [VERIFIED: detection.py:224-228] is a frozenset built from `_RUNTIME_ENV_SIGNALS`, `scrub_signals` and `_GENERIC_HOST_MARKERS = ("AI_AGENT",)`; values seen in the table: `PI_CODING_AGENT`, `OPENCODE`, `CURSOR_AGENT`, `CODEX_THREAD_ID`, `CODEX_VERSION`, `CODEX_SANDBOX`, `CLAUDECODE`, `CLAUDE_CODE_ENTRYPOINT`, `CLAUDE_CODE_SSE_PORT`, `GROK_AGENT`, `AI_AGENT`.
- **Scrub `GIT_*` too.** Live probe: a pre-commit git hook in a scratch repo sees `GIT_INDEX_FILE`, `GIT_AUTHOR_DATE`, `GIT_EXEC_PATH`, `GIT_AUTHOR_EMAIL`, `GIT_PREFIX`, `GIT_EDITOR`, `GIT_AUTHOR_NAME` [VERIFIED: ran scratch script under a throwaway HOME]. Tests that `git init`/`git commit` in temp dirs (worktree e2e, goal-prompt e2e, curated-config) inherit these when run from the commit hook. Remove `GIT_INDEX_FILE`, `GIT_DIR`, `GIT_WORK_TREE`, `GIT_PREFIX`, `GIT_COMMON_DIR`, `GIT_OBJECT_DIRECTORY`; keep `GIT_EXEC_PATH` (git needs it). Pin `GIT_CONFIG_GLOBAL`/author identity inside the tests that commit, or set `GIT_CONFIG_NOSYSTEM=1` plus fixed author vars in the baseline.
- Also pin `HOME` (temp, with `AI_KIT_REFUSE_REAL_HOME=1`) in the baseline; today only TMPDIR/TEMP/TMP are set [VERIFIED: tools/run_unittest_parallel.py:149]. This is what makes the Mermaid unit tests Chrome-independent. Caveat: some modules (uv env) need `HOME` for uv cache -> for `uv run` the runner process already carries the env; the subprocess is `sys.executable -m unittest`, which does not call uv, so a temp HOME is safe. Verify with `make test-integration`.
- PATH ordering: tripwire first, then the caller's PATH. Note `git`, `node`, `python3` must stay reachable; a no-host-CLI matrix case should filter PATH, not blank it.
- Tests that spawn the product CLI and legitimately expect "host present" must put a fake in front of the tripwire via the shared helper; the helper writes executables into a temp dir and prepends it (pattern in `tests/cursor_fakes.py`, `tests/session_wake_fakes.py` - read both before writing the helper).

### The eval module (the 162 s pole)
`tests/test_ai_kit_spec_goal_prompt_evals.py` `eval_env` removes `HOST_SIGNAL_ENV_VARS`, sets `CLAUDECODE=1`, a fake HOME and `AI_KIT_REFUSE_REAL_HOME=1`, but leaves PATH [VERIFIED: tests/test_ai_kit_spec_goal_prompt_evals.py:159-180]. The fix is to give `eval_env` a PATH of fakes for `claude` (and the other names `gp_host.host_version`/`help_mentions` probe with `--version`/`--help`), driven from the shared fake helper; `test_long_goal_eval_renders_the_pointer_form` currently fails with no host CLI present, so the fake must produce the version/help text it needs (read the test before building the fake). 80 calls per run means the fake should be a single script keyed on argv, not 80 files.

### Anti-patterns
- Caching the mapper index (D-01 forbids; stale index = silent skipped tests).
- Returning 0 modules when the mapper throws: wrap `main --staged` in a broad `try`, and on any exception run the full groups (SPEC R2, must-NOT).
- Hand-editing `.planning/scripts/cross-ai.mjs`.
- Mocking `subprocess.run` only: the real calls were made by a child process.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Atomic file writes in new tools | custom writes | `_atomic_write` pattern in `tools/gen_test_groups.py:84` | AGENTS.md rule; mapper itself writes nothing |
| Parallel execution/CPU share | new pool | existing `worker_count`, `available_cpus`, `ThreadPoolExecutor` in runner | 40 % cap and `AI_KIT_TEST_CPU_SHARE` semantics already tested |
| Stale-name detection | new check | model on `stale_exception_names` | Same failure style the gate already uses |
| Fake CLIs | per-test ad hoc scripts | one shared helper, patterned on `tests/cursor_fakes.py` | D-04 single helper; the AST rule exempts only it |
| Staged file list | parsing `git status` | pre-commit's passed filenames plus `git diff --cached --name-status` | Handles renames/deletes |
| Wall-clock testing | sleeps | `core._monotonic` seam (`precompact_core.py:74`) | Existing seam |

## Runtime State Inventory

Not a rename phase, but two state items matter:
- Stored data: none (mapper uncached by decision).
- Live service config: none.
- OS-registered state: installed git hooks in `.git/hooks` come from `pre-commit install`; a new commit-stage test hook only fires after `make dev` re-run is NOT needed because `default_install_hook_types: [pre-commit, pre-push]` already installs both [VERIFIED: .pre-commit-config.yaml:8]. The hook script itself reads the config at run time. Verify `.git/hooks/pre-commit` exists in this checkout before the e2e commit test.
- Secrets/env: none new; `AI_KIT_REFUSE_REAL_HOME` and `AI_KIT_TEST_CPU_SHARE` exist.
- Build artifacts: the dogfood copy `.planning/scripts/cross-ai.mjs` is stale after the template edit and must be re-rendered (D-10/D-11). Rendered copies in other repos are out of reach.

## Common Pitfalls

1. **GIT_* leakage into tests at commit time** (see above). Warning sign: worktree/e2e tests pass at push, fail only inside `git commit`. Test it by running the new hook from a real fixture commit in a temp repo.
2. **pre-commit file batching**: without `require_serial` a large commit is split across processes. Use `require_serial: true`.
3. **Stash/unstaged changes**: pre-commit stashes unstaged changes during commit-stage hooks, so tests see the staged tree - desired. But untracked files remain; the mapper must index from the working tree as stashed (it will be the staged state).
4. **uv missing**: refuse with a pointer to `make setup-env` only when a wizard-group module is chosen (D-02). Detect with `shutil.which("uv")`.
5. **Dedup via two groups**: a module belongs to exactly one group (`test_every_module_in_exactly_one_group`); the Mermaid split must add the new e2e module to `E2E_MODULES` and regenerate listings with `python3 tools/gen_test_groups.py` or `test_generated_listings_name_every_discovered_module` fails.
6. **Dogfood runner copy**: the template edit makes `TestDogfoodCopy` (moving to check-dogfood) fail until the copy is re-rendered; do the re-render in the same plan. Find the render entry in `skills/ai-kit-gsd-curated-config` (not read this session) before planning that step.
7. **Self-test factor placement**: the file is 10424 lines [VERIFIED: wc -l]. Scale at three harness sites (`runCaseProcess` hard timeout at line 5290 `30000`; `waitFor` calls at 5297 and 5299 `10000`; `withinMs ?? 2900` at 5348 plus literal `withinMs: 2900` at 7179, 7199, 7496, 7504, 7513) and the 14+ per-case `elapsedMs >=` ceilings (5000, 10000, 15000, 30000, 80000 at lines 6306, 6510, 7106, 7117, 7252, 7418, 7448, 7539, 7553, 7560, 7589, 7776, 7820, 9721) [VERIFIED: grep]. Floors: `elapsedMs < 2500` at 7152, 7428, 7471 stay unscaled. Prefer one helper (`ceil(ms * LOAD_FACTOR)`) and a grep-based test that no unscaled `elapsedMs >=` ceiling remains (with a non-vacuity case), because a missed literal silently stays flaky. The 3 `withinMs: 2900` literals and the 5348 default should share one constant.
8. **`pre-push` check-dogfood hook** must obey the same rules as the other pre-push test hooks in `test_gate_scope.py` (id ordering, no hardcoded workers).
9. **AST rule false positives**: test files legitimately contain strings like `"claude"` as data (model names, labels, `HOST_BINARY` keys). Flag only: argv list element 0 (or any element) passed to `subprocess.*`/`Popen`/`os.exec*`/`os.system`, a command string whose first shlex token is a host name, and `shutil.which("<host>")` calls; exempt the shared fake helper and require non-vacuity per form (SPEC edge R5 encoding). Tests of detection code that pass host names to injected `which_fn`/`run_fn` fakes are not real calls: the rule must not flag a name passed to a fake seam, which an AST rule cannot prove, so scope it to the three syntactic forms and keep the run-time tripwire as the real backstop.
10. **`.planning/` AST rule scope**: 43 test files mention `.planning`; most build paths under a temp project (allowed). The flagged form is a path expression rooted in a repo-root name (`REPO_ROOT`, `ROOT`, `_ROOT`, `_REPO_ROOT`, `Path(__file__)...parents`) joined with `".planning"` in `/`, `os.path.join`, `Path(...)`, and f-strings. Known real offenders [VERIFIED: grep]: `tests/test_tool_advisor_core.py:336`, `tests/test_pi_live_tools.py:15`, `tests/test_phase26_owner_captures.py:8`, `tests/test_curated_config_e2e.py:131`, `tests/test_curated_config_apply_e2e.py:54-55`, `tests/test_curated_config_script.py:850`; plus `tests/gsd_curated_eval.py` and a seventh in the spec's count that must be located by running the new rule (the rule's first run is the authoritative list).

## Code Examples

### Runner env extension (shape; extend `run_module`, `tools/run_unittest_parallel.py:145-159`)
```python
env = {k: v for k, v in os.environ.items()
       if k not in HOST_SIGNALS and not k.startswith(GIT_SCRUB)}
env.update(TMPDIR=temp_dir, TEMP=temp_dir, TMP=temp_dir, HOME=home,
           AI_KIT_REFUSE_REAL_HOME="1",
           PATH=os.pathsep.join([trip_dir, env.get("PATH", "")]),
           AI_KIT_TRIPWIRE_LOG=log_path)
# after run: if Path(log_path).read_text(): rc = 1; append the logged calls to output
```

### Stub (tiny, one per host name)
```sh
#!/bin/sh
printf '%s %s\n' "$(basename "$0")" "$*" >> "$AI_KIT_TRIPWIRE_LOG"
echo "ai-kit tripwire: real host CLI $(basename "$0") called from a test" >&2
exit 127
```

### Load factor in cross-ai.mjs (D-10)
```js
// shortcut: loadavg is a 1-minute average; fine for ceilings, not floors.
const LOAD_FACTOR = (() => {
  const injected = o.selfTest && process.env.AIKIT_SELFTEST_LOAD; // name is planner's
  const load = injected !== undefined ? Number(injected) : os.loadavg()[0] / os.availableParallelism();
  return Number.isFinite(load) && load > 0 ? Math.min(4, Math.max(1, load)) : 1;
})();
const scaled = (ms) => Math.ceil(ms * LOAD_FACTOR);
```
(Injection must live under `--self-test` only; read once per run - module-level constant evaluated when self-test starts, not at import, if the env var must be gated by the flag.) `os.availableParallelism` needs Node >= 18.14 [CITED: nodejs.org API docs, ASSUMED version]; check `node --version` on the machine and fall back to `os.cpus().length`.

## State of the Art

Not applicable beyond: pre-commit `require_serial` and `pass_filenames` are the documented way to batch-control hooks [CITED: pre-commit.com]. Python 3.13 `os.process_cpu_count` is already used by the runner with fallbacks.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | pre-commit splits file lists across parallel processes unless `require_serial: true` | Hook shape | Low; serial is harmless either way |
| A2 | `os.availableParallelism` requires Node >= 18.14 | Code Examples | Low; a fallback is specified |
| A3 | Mapper median covering-modules per unit stays near 3.5 and the max near 37 | Mapper | Medium; if far higher, commit-stage speed gain shrinks (still correct) |
| A4 | A temp `HOME` in the runner baseline breaks no module | Baseline env | Medium; verify by full `make test` before and after |
| A5 | The 60 s push target holds from fakes alone (spec saw 48 s with host CLIs hidden under shared load) | GATE-03 | Medium; next poles are `test_precompact_core` 30 s and `test_wizard_app` 21 s - the wizard hook runs after the core hook, so the sum must be measured |
| A6 | Which goal-prompt test is path-length dependent and which `test_worktree_e2e` case is the no-git case | Environment pinning | Medium; neither was reproduced (SPEC says so). The matrix run with a 200+ char path and a cwd outside git is how they are found; `test_worktree_e2e.py` already creates an "outside" dir at tmp/outside (`:59-61`) so the failure is TMPDIR-inside-a-repo, fix by pinning TMPDIR out of any repo or `GIT_CEILING_DIRECTORIES` |

## Open Questions

1. Which exact goal-prompt test couples to the tool-substitution hook by path length? Not identified this session. Recommendation: run the matrix with the long path first; fix the coupling at its cause (assert on relative content or derive limits from the path length).
2. Where does the curated-config render entry point live (for re-rendering the dogfood copy)? Recommendation: plan reads `skills/ai-kit-gsd-curated-config` scripts and `tests/test_curated_config_script.py` `TestDogfoodCopy` (line ~850) first.
3. Does `tools/run_unittest_parallel.py` fall under any `tests/test_arch.py` import-direction rule? Recommendation: check before importing `detection.py` from the runner; default to a copied tuple plus drift test.
4. Can the tripwire catch calls made via absolute paths (`/usr/bin/claude`)? No; the AST rule plus `resolve_runtime_binary`'s `shutil.which` use cover the product's own flows. State this limit in the docs.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| python3 | all | yes | system | - |
| uv | wizard/integration groups, check-dogfood | yes | 0.11.28 | refuse with `make setup-env` hint |
| pre-commit | hook tests | yes | 4.6.2 | - |
| node | cross-ai.mjs self-test | yes (checkout-local use) | not probed; run `node --version` | - |
| stress-ng | one real-stress self-test run | probed in spec step | not re-probed | a Python/`yes >/dev/null` CPU burner |
| mmdc / headless Chrome | e2e Mermaid real render | machine-dependent | - | named skip |
| CPUs | worker count | 24 (so 9 workers) | [VERIFIED: nproc] | - |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | stdlib `unittest`, run through `tools/run_unittest_parallel.py` |
| Config file | none (groups in the runner; hooks in `.pre-commit-config.yaml`) |
| Quick run command | `python3 tools/run_unittest_parallel.py tests.test_run_unittest_parallel tests.test_gate_scope tests.test_arch` |
| Full suite command | `make test` (then `make test-env-matrix`, `make check-dogfood`) |

Group counts now [VERIFIED: `--list-groups`]: unit 76, arch 1, unit-uv 1, integration 4, e2e 13; hook unittest 77, hook unittest-wizard 5.

### Phase Requirements -> Test Map
| Req | Behavior | Test Type | Automated Command | File Exists? |
|-----|----------|-----------|-------------------|-------------|
| GATE-01 | staged file -> covering modules; fixture commit refused on failure; data-only file maps; dedupe; order-independent; empty list passes | unit + e2e (temp repo with real pre-commit hook) | `python3 tools/run_unittest_parallel.py tests.test_staged_mapper` | no, Wave 0 |
| GATE-02 | planning-only = 0 modules; runner/helper/fixture/hook-config = full unit+arch; forced mapper failure = full, never 0; empty answer for covered file = full | unit | same module | no, Wave 0 |
| GATE-03 | before/after timings recorded; 60.0 passes / 60.1 fails; failed hook not counted | manual timing script + a unit test of the arithmetic | `bash tools/time_prepush.sh` (name planner's) | no, Wave 0 |
| GATE-04 | tripwire log empty across tiers; AST rule passes tree, fails synthetic `claude --version` in argv, string and `shutil.which` forms; runtime tripwire fails a module that calls a host | unit (arch) + unit (runner) | `python3 tools/run_unittest_parallel.py tests.test_arch tests.test_run_unittest_parallel` | partial; add cases |
| GATE-05 | 6-env matrix identical; precompact test with injected clock; Mermaid split; load factor 1/proportional/4 + floors fixed + limits byte-identical; `.planning/` rule empty list + synthetic offender; check-dogfood exit 0 / non-zero after edit | unit, e2e, make targets | `make test-env-matrix`, `make check-dogfood`, `node skills/ai-kit-spec-review/references/cross-ai.mjs --self-test` (HOME and `AI_KIT_REFUSE_REAL_HOME` set) | no, Wave 0 |

### Sampling Rate
- Per task commit: quick run command above plus the module touched.
- Per wave merge: `make test-unit arch-test`.
- Phase gate: `make test`, `make validate`, `make test-env-matrix`, `make check-dogfood`, then timing last.

### Wave 0 Gaps
- [ ] `tests/test_staged_mapper.py` (or in `test_run_unittest_parallel.py`) - GATE-01/02 including the temp-repo real-hook commit
- [ ] Shared host fake helper under `tests/` and its tests
- [ ] AST rules + non-vacuity cases in `tests/test_arch.py` / `tests/test_gate_scope.py` (host CLI, `.planning/`)
- [ ] `tests/fixtures/archived/<phase>/` copies with headers
- [ ] e2e module for real Mermaid render, added to `E2E_MODULES`, listings regenerated
- [ ] `tools/check_dogfood.py` (name planner's), Makefile `check-dogfood` and `test-env-matrix` in `.PHONY`
- [ ] Node self-test cases for the load factor (injected readings 0, 0.5, 2, 4, 10, missing) and a floor/limit byte check

## Security Domain

`security_enforcement` not probed in config this session (treated as enabled).

| ASVS Category | Applies | Control |
|---------------|---------|---------|
| V5 Input validation | yes | Mapper treats staged paths as data (no shell interpolation; pass argv lists to subprocess) |
| V12 Files/resources | yes | Temp dirs only; never real `~/.claude` etc.; `AI_KIT_REFUSE_REAL_HOME=1` |
| V2/V3/V4/V6 | no | - |

| Threat | STRIDE | Mitigation |
|--------|--------|------------|
| Tripwire stub path injection via filenames | Tampering | Fixed stub names from a constant list, written inside a runner-owned temp dir |
| Env-var injected load reading changing real run limits | Tampering | Honoured only under `--self-test`; real limits unchanged (byte-identity test) |
| Tests reaching real host config | Info disclosure | Baseline HOME + refuse flag; audit real-config mtimes after runs |

## Sources

### Primary (HIGH)
- Read this session: `tools/run_unittest_parallel.py`, `tools/gen_test_groups.py`, `.pre-commit-config.yaml`, `Makefile`, `tests/test_gate_scope.py` (hooks/order sections), `tests/test_ai_kit_spec_goal_prompt_evals.py:159-199`, `detection.py:75-245`, `gp_host.py:21-31,110-161`, `cross-ai.mjs:5250-5360` plus grep of ceilings, `tests/test_precompact_core.py:173-193`, `tests/test_markdown_to_pdf.py:75-83`, 28-CONTEXT.md, 28-SPEC.md.
- Live probes: `--list-groups` counts, `nproc`, `pre-commit --version`, `uv --version`, git-hook env probe.

### Secondary / Tertiary
- Spec-step timing and trace figures are cited from 28-CONTEXT.md/28-SPEC.md (measured 2026-11-03 by the spec step; not re-measured here, so the 184 s, 48 s and 80-call figures are [CITED], not re-observed).
- pre-commit batching/`require_serial` semantics [ASSUMED] from training knowledge.

## Metadata

**Confidence:** stack HIGH (stdlib, existing code read); architecture HIGH; pitfalls MEDIUM-HIGH (GIT_* leak observed; path-length/no-git tests not reproduced).
**Research date:** 2026-11-03. **Valid until:** about 30 days or the next edit to the runner/hooks.
