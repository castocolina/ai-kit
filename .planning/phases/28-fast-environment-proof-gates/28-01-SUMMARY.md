---
phase: 28-fast-environment-proof-gates
plan: 01
subsystem: testing
tags: [test-runner, tripwire, baseline-env, host-fakes, mermaid-e2e]
requires: []
provides:
  - "tripwire stubs: a real host CLI call through PATH fails the calling module"
  - "baseline_env and tool_cache_forwards in tools/run_unittest_parallel.py"
  - "tests/host_fakes.py shared fake helper"
  - "tests/test_markdown_to_pdf_e2e.py real render with named skips"
affects: [28-02, 28-05, 28-08, 28-09]
tech-stack:
  added: []
  patterns: ["tripwire first on PATH, log path baked into stubs", "pure baseline_env over a source mapping", "drift tests pin every copied list"]
key-files:
  created: [tests/host_fakes.py, tests/test_markdown_to_pdf_e2e.py]
  modified: [tools/run_unittest_parallel.py, tests/test_run_unittest_parallel.py, tests/test_ai_kit_spec_goal_prompt_evals.py, tests/gsd_curated_eval.py, tests/test_gsd_curated_eval.py, tests/test_arch.py, tests/test_markdown_to_pdf.py, Makefile, .pre-commit-config.yaml]
key-decisions:
  - "Dropped-versus-kept is decided by baseline_env's own output, so a later plan's dropped name needs no drift-test edit"
  - "tool_cache_forwards is public so plans 28-08 and 28-09 compute the same forwards before replacing HOME"
  - "BROWSER_MISSING built from the two texts Puppeteer printed on this machine"
status: complete
commits: 4
plan_head_before: 7b0ce148ef16a75c341a721d8a6ca4a5093baeee
plan_head_after: 3e1e7fc1a5df354bc1d39cdea48530dbc0434693
actuals:
  tokens: 11400
  tasks: 3
  commits: 4
---

# Phase 28 Plan 01: Tripwire, baseline environment and Mermaid e2e Summary

Every test module now runs with a host-CLI tripwire first on PATH and a pinned baseline environment (temporary HOME, no host signals, no inherited git state, no config or credential overrides); the goal-prompt eval module runs on fakes in 4.6 s instead of 162 s.

## Commits

- `0841bb1` feat(28-01): tripwire fails any module that calls a real host CLI (Task 1)
- `b9216fb` test(28-01): add failing tests for the baseline module environment (Task 2, RED)
- `64da75e` feat(28-01): run every test module under a pinned baseline environment (Task 2, GREEN)
- `3e1e7fc` feat(28-01): move the real Mermaid render to the e2e tier with named skips (Task 3)

## What changed

- `tools/run_unittest_parallel.py`: `HOST_CLI_NAMES`, `write_tripwire`, `_tripwire_report` (20 lines plus `... and <n> more calls`), `HOST_SIGNAL_VARS`, `HOME_OVERRIDE_VARS`, `CREDENTIAL_ENV_VARS`, `HOST_CONFIG_ENV_PREFIXES`, `GIT_KEPT_VARS`, `tool_cache_forwards`, `baseline_env`; `run_module` keeps its 4-tuple. Docstring states the PATH-only reach, the `shutil.which` effect and the baseline env.
- `tests/host_fakes.py`: `HOST_NAMES`, `CLAUDE_ANSWERS`, `write_host_fakes`, `host_path`, `fake_calls`.
- Goal-prompt eval `eval_env` puts the fakes first on PATH. `tests/test_gsd_curated_eval.py` puts the fakes behind its decoys (the python dir on this machine is `~/.linuxbrew/bin`, which holds a real `copilot`). `tests/gsd_curated_eval.py` `_cmd_run` uses the bare-name constant `LIVE_CLAUDE_BIN`.
- Arch rule 10 allowlist gained `tools/run_unittest_parallel.py`.
- Mermaid real render moved to `tests/test_markdown_to_pdf_e2e.py` (in `E2E_MODULES`, generated listings regenerated).

## TDD record (Task 2)

RED (`b9216fb`): `BaselineEnvTest` and `DriftTest` failed with `AttributeError` on `baseline_env`, `tool_cache_forwards` and `HOST_CONFIG_ENV_PREFIXES` (12 errors), and `test_synthetic_module_never_sees_the_callers_state` failed on its assertion (the sentinel `CC_AI_KIT_CONFIG_FILE` path reached `cfg_config_path`: `CFG=/sentinel/owner-state/cfg.toml`). Semantic assessment: the named target tests ran and failed for the planned reason (missing behaviour); no syntax, collection or fixture fault. `gsd_run check tdd-red-evidence` was not run (the plan is `type: execute`, not `type: tdd`). GREEN (`64da75e`): 39 tests pass. No separate refactor commit.

## Step-6 scan hits (drift test decisions)

The scan over `tools/` and `skills/` found 52 names. Dropped by the baseline: 33 in `HOME_OVERRIDE_VARS` (all listed by the plan) and 10 in `CREDENTIAL_ENV_VARS`. Nine are kept: `AI_KIT_REFUSE_REAL_HOME` and `GIT_EXEC_PATH` (set by the baseline), `CACHE_ROOT`, `CONFIG_FILE`, `RUNBOOK_RELATIVE_PATH` (not env vars), and the runner's own forwards `PUPPETEER_CACHE_DIR`, `UV_CACHE_DIR`, `UV_PYTHON_INSTALL_DIR`, `VOLTA_HOME` (approved forwards, pinned in `BaselineEnvTest`). No source name beyond the plan's lists turned up, so no name was added to the sets. `ConfigSpec` prefixes found: `CC_AI_KIT_`, `AI_KIT_SEGMENT_` (kept, written only into provider children), `AI_KIT_CURSOR_`, `AI_KIT_CURSOR_PROVIDER_` (covered by `AI_KIT_CURSOR_`).

## Mermaid probes (Task 3 step 1, scratch HOME, mmdc from linuxbrew, mermaid-cli 11.17.0)

- (a) caller's real Puppeteer cache via `PUPPETEER_CACHE_DIR`: rc 0, `Generating single mermaid chart`. Puppeteer honours the variable.
- (b) empty folder: rc 1, `Error: Could not find chrome-headless-shell (ver. 152.0.7977.54).`
- (c) partial cache (empty `chrome-headless-shell/` and `chrome/`): rc 1, same text.
- (d) `PUPPETEER_EXECUTABLE_PATH` at a missing file: rc 1, `Error: Tried to find the browser at the configured path (...), but no executable was found.`

`BROWSER_MISSING` matches `Could not find (Chrome|chrome-headless-shell)` and `Tried to find the browser at the configured path`. The plan's example text `Browser was not found at the configured executablePath` was not observed and is not used.

`uv run python tmp/p28/mermaid_e2e_check.py render` (exit 0):
```
expected: current cache: rc=0 OK
actual:   current cache: rc=0 OK
expected: empty cache: rc=0 OK (skipped=1)
actual:   empty cache: rc=0 OK (skipped=1)
expected: partial cache: rc=0 OK (skipped=1)
actual:   partial cache: rc=0 OK (skipped=1)
```
Also seen directly: with `PATH=/usr/bin` the module skips with `mmdc not installed`.

## Verification (exact commands, exit codes)

All with `AI_KIT_REFUSE_REAL_HOME=1`, from the worktree root:

- `python3 tools/run_unittest_parallel.py tests.test_run_unittest_parallel tests.test_ai_kit_spec_goal_prompt_evals tests.test_gsd_curated_eval tests.test_arch tests.test_markdown_to_pdf tests.test_gate_scope tests.test_status_line tests.test_cursor_status_line` -> 8/8 passed, exit 0, no `tripwire:` block. Eval module 4.6 s (spec: 162.4 s); `test_long_goal_eval_renders_the_pointer_form` passes.
- `python3 tools/run_unittest_parallel.py tests.test_markdown_to_pdf tests.test_gate_scope tests.test_run_unittest_parallel tests.test_markdown_to_pdf_e2e` -> 4/4, exit 0.
- `uv run ruff check tools tests`, `uv run pylint tools/run_unittest_parallel.py` (10.00/10), `uv run pyright` on touched files (0 errors), `uv run vulture` (exit 0); pre-commit hooks (ruff, pylint, py-compile) passed on all four commits.
- No all-tier run (plan 28-02 Task 4 owns it). `wait_load.py` was not needed: no stress or whole-tier run in this plan.
- Real-config audit: `ls -la --time-style=full-iso ~/.claude ~/.codex ~/.config/opencode` shows `~/.claude` entries modified at 20:58, which is the running Claude Code session itself, so the audit cannot separate this plan's runs from it; every run used the runner's temporary HOME and `AI_KIT_REFUSE_REAL_HOME=1`, and nothing was written there by this plan.

## Deviations from Plan

**1. [Rule 1 - Bug] `test_label_path_placeholders` broke under the pinned HOME**
- Found during: Task 2 verify (`tests.test_gsd_curated_eval`).
- Issue: the test asserted that `Path.home()` labels as `<home>`; the baseline HOME sits inside the temp dir, which `label_path` reads as scratch (`<scratch>/home`).
- Fix: the test sets HOME to a path outside the temp dir for that assertion.
- Files: `tests/test_gsd_curated_eval.py`. Commit: `64da75e`.

**2. Step 5 trace differed from the spec.** The spec's `pi --mode rpc` and `codex debug models` calls did not appear in the tripwire log of `tests.test_gsd_curated_eval` on this machine. The only test that rebuilds PATH from `dirname(sys.executable)` is the launcher/decoy test; on this machine that directory (`~/.linuxbrew/bin`) holds a real `copilot`, and the spec's run likely had a python dir next to `pi` and `codex`. The fix is still the one the plan asks for: fakes from `host_fakes` behind the decoys in that test. No `tests/gsd_curated_eval.py` seam was needed beyond the `_cmd_run` constant.

Otherwise the plan ran as written.

## Known limits

- The tripwire sees PATH lookups only (stated in the runner docstring); the arch rule of plan 28-05 covers literal commands.
- Inside a module `shutil.which(<host>)` resolves into the tripwire folder (pinned by `TripwireTest` case (f)); plan 28-02 triages tests that need a host absent.
- Known stubs: none.

## Threat Flags

None. The tripwire and baseline reduce surface; no new network endpoint, auth path or schema.

## Self-Check: PASSED

Files found: tools/run_unittest_parallel.py, tests/host_fakes.py, tests/test_markdown_to_pdf_e2e.py, tests/test_run_unittest_parallel.py. Commits found in HEAD ancestry: 0841bb1, b9216fb, 64da75e, 3e1e7fc.
