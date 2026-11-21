# 37-10 Summary: claude execute and resume formulas, labelled unverified

Status: complete in one lane (plan as written; pi `router-env/my-coding`), verified by the orchestrator.

## Lanes

- Lane 1 (plan as written): `status=ok exit=0 elapsed=1020s attempts=1`, commit 2617c12. The lane also ran `make test` (unit 177/177, unit-uv 3/3, integration 9/9, e2e 26/26, installer 48 passed, arch 2/2, per its report).

## Commits

- 2617c12 `feat(37-10): add unverified claude execute and resume` (cross-ai.mjs, cli-profiles/claude.md, tests/test_ai_kit_spec_exec_formula_e2e.py, tests/test_runner_claude_exec.py, tests/test_runner_settings_argv.py); staged-tests hook 129/129 per the lane.

## What was done

- Permission tokens: `['--permission-mode', 'bypassPermissions']`, because 37-SPIKE.md records claude Q3(b) as not probed (no ledger consent line; 0c default). `CLAUDE_EXEC_PROBE_RECORD` and `CLAUDE_EXEC_FORMULA_RECORD` are both `null` (no probe of the flag, the exact formula or its resume).
- claude row: `exec` (`-p --model <m> --output-format json --permission-mode bypassPermissions` plus the effort spread the review formula has), `resume` (`--resume <id>` after the role's formula), `permissionLabel` and `execLabel` (unverified while null); the session label drops `; no resume formula in this row yet`. `logExecLabel` prints `cross-ai: note: claude execute formula is unverified (no live probe record)` after the settings lines in `--print-argv` and on the run path for an execute call; `evidenceOf` reports `pattern=unverified` on execute calls while `execLabel` is unverified (review evidence unchanged).
- Fake claude: an execute call appends `a.txt`, commits `fake claude execute` and answers `## Summary\nok`; model `fake-auth` answers 401 and exits 1.
- Cases: `claude-exec-commit` (replaces `claude-exec-usage`), `prefer-first-claude-exec-runs` (replaces `review-only-first-refused`), `claude-exec-resume`, `claude-exec-pattern-unverified`, `claude-exec-no-model`; `review-only-later-menu-ok` comment reworded. `--self-test-list` 602.
- `RUNNER_AHEAD_OF_MIRROR` names claude in the exec-formula drift test, with a non-vacuity test (cursor with a null head still fails); detection.py unchanged. claude.md states both formulas and keeps `no_formula` once. `test_minted_without_resume_formula` became `test_claude_review_resumes` (applied, `--resume s-1`). `tests/test_runner_claude_exec.py` (plan 37-02's stub) now holds `TestClaudeArgv` (four tests) and `TestClaudeExecLabel` (two tests).

## Evidence (orchestrator re-run, scratch HOME, `tmp/run-2026-11-19/c4-verify-37-10.sh`)

- Every acceptance grep at its expected count: new test name 1 and old 0; both record constants (`null`), `permissionLabel`, `resume`, `execLabel`, `logExecLabel` 1 each; old claude-only case names 0; `review-only` in claude.md 0 and `no_formula` 1; `RUNNER_AHEAD_OF_MIRROR` and its test present; detection.py diff empty; six `def test_` in the new module, no stub text, no grok; grok lines in the template 1 (none added); Makefile, `.pre-commit-config.yaml` and generated listings untouched; `router-env/` literals 2; baseline JSON unchanged.
- The five claude cases listed as `logic`; them plus `review-only-later-menu-ok`, `claude-review-ok`, `pure-review-extras`, `pure-profiles-read-only`, `model-unusual-shape-spawns`, `model-cli-flag-floor`, `session-host-id-unshown`, `gate-runtime-no-formula`, `argv-file-refuse-known-runtime`: `self-test ok`.
- `--print-argv` execute: argv `["-p","--model","fake-ok","--output-format","json","--permission-mode","bypassPermissions"]`, the note, rung1 with `--resume <sid>`; review: the byte-equal review argv and no note. Stdout argv equals the f579899 template for twelve calls including claude review with and without `--effort high`.
- Modules 11/11 (runner_claude_exec, exec_formula_e2e, runner_status_group, spec_chain_text, runtimes_table, arch_hardcoded_models, runner_settings_argv, no_seed_refusal, routing, runner_dispatch, arch); eight shards plus `test_cross_ai_runner_e2e` 9/9. Lane-reported: `make ruff`, `make pyright`, `make vulture`, `make pylint` exit 0. Tree clean.
- Real-config audit (marker before the lane): Claude host-session files (jobs, plugin stores, skill sync), the codex daemon's logs, state and model cache, the lane's pi session; none attributable to this plan.

## Deviations

- None in behaviour. The `RUNNER_AHEAD_OF_MIRROR` line carries `# noqa: E501` (the plan's exact one-line dict exceeds 100 characters). The plan's scratch scripts `tmp/run-2026-11-19/p37-exec/37-10-t1.sh` and `37-10-t2.sh` remain under the ignored `tmp/` (their own `st-37-10-t*` folders are removed).
