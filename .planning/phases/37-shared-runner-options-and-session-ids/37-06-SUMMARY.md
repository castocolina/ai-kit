# 37-06 Summary: the run path plans and prints the settings; the status line's settings group

Status: complete after three no-change lanes and two focused fix-up lanes (pi `router-env/my-coding`, same CLI and model throughout), verified by the orchestrator.

## Lanes

- Lane 1: `status=no_change exit=1 elapsed=45s tree=clean`; the model stopped because step 6's `confirmReport(plan.report, firstArgv, '')` omits the `builtMode` argument the `role` entry's `{ mode }` proof needs.
- Lane r2 (plan kept, resolution + do-not-stop note): `status=no_change exit=1 elapsed=90s`; its one batched edit failed ("Found 2 occurrences", the pi exec and review spreads) and it stopped.
- Lane r3 (plus an edit-tool-error rule): `status=no_change exit=1 elapsed=69s`; read three ranges and stopped without an edit.
- Fix-up a (XAI_FIXUP, Task 1 only, ordered edit checklist): `status=ok exit=0 elapsed=810s attempts=1`, commit af1ab13.
- Fix-up b (XAI_FIXUP, Tasks 2 and 3): `status=ok exit=0 elapsed=875s attempts=1`, commits 398a40c and b91d846.

## Commits

- af1ab13 `feat(37-06): run path plans and prints the settings, status group` (cross-ai.mjs, tests/test_lane_effort.py, ai_kit_spec/lane_effort.py)
- 398a40c `test(37-06): run-path report, CONFIG.effort, called model, escalation and group cases` (cross-ai.mjs)
- b91d846 `test(37-06): status group parses with runner_dispatch readers` (tests/test_runner_status_group.py)

The staged-tests hooks passed (129/129, 128/128 and 3/3 modules per the lanes).

## What was done

- `liveSettings` module state, reset in `main`; `finish` appends `session= applied= ignored= unknown= escalate=` through `statusGroup` with the fallback text; `STATUS_HEAD_RE` gains the group capture between the attempts and retry groups; `statusTail` reads `parts[2..5]` and returns the five new keys.
- `callOf(o, name, model, newSessionId)` (CONFIG.effort for every runtime); the print-argv branch uses it and fills `liveSettings`.
- Run path: one `planSettings` call with a generated session id, `confirmReport` over the first argv it will spawn, setting lines printed after the review-argv check and before the listing preflight; preflight checks `plan.model`; the status `model=` stays the model as called.
- `runCli` takes `adds`, `sessionId`, `resume`, `callSessionId`; a chosen row runs with the planned id, a minted row with an applied id starts with `sameSessionArgv(..., prompt)`; the `last_sid` re-entry is skipped when the call names `--session-id`.
- Removed `knobs`, `CODEX_EFFORTS`, `PI_THINKING`, `piThinkingArgs`, the `ctx.codexEffort` fallback and the `codexEffort`/`piThinking` ctx fields; `o.codexEffort` stays (parseArgs still uses it, per the plan's own condition).
- Ten self-test cases (`settings-run-lines` and the nine of Task 2), all `logic`; `--self-test-list` 529.
- `tests/test_lane_effort.py`: `test_runner_has_no_closed_effort_set`; `lane_effort.py` comment updated. `tests/test_runner_status_group.py`: `GROUP_KEYS`, `last_status`, `TestStatusGroup` (3 tests).

## Evidence (orchestrator re-run, scratch HOME)

- Acceptance greps: `let liveSettings = {`, the `statusGroup(liveSettings...)` call, the regex group present; `piThinking|PI_THINKING|CODEX_EFFORTS|knobs\.` 0; `reportLines(report)` in main (line 13359) before `await listModels(c.rt` (13363); runner_dispatch.py unchanged; 3 tests, no stub text, no grok line, Makefile and `.pre-commit-config.yaml` untouched.
- All ten new cases listed as `logic`; the ten plus `ok`, `copilot-no-token-auth`, `hard-tier-other-task-fresh-session`, `claude-review-ok`, `model-flag-cursor-bracket` and six effort/argv cases: `self-test ok`.
- A parse error prints exactly one status line ending `attempts=0 cycles=0 session=- applied=- ignored=- unknown=- escalate=-`.
- `--print-argv` stdout argv equals the 4e0da8f template for sixteen calls (all eleven runtime/mode entries plus effort, suffix, context and session variants).
- Modules 8/8 (runner_status_group 3, runner_dispatch 83, lane_effort 24, runner_settings_argv 21, ...); eight shards plus `test_cross_ai_runner_e2e` and `test_ai_kit_spec_exec_formula_e2e` 10/10. Lane-reported: `make ruff`, `make pyright`, `make vulture`, `make pylint` exit 0; `make test` exit 0. Scratch `st-37-06-*` gone; tree clean.
- Real-config audit: Claude host-session files, the codex app-server daemon's auto-update, the lanes' pi sessions, and `~/.cursor/cli-config.json` at 09:50:09 (during lane 1, whose pi session shows only reads and no cursor-agent call; same pattern as 37-03's run at 08:38, not from this plan's lanes).

## Deviations

- Plan text vs code: the run path calls `confirmReport(plan.report, firstArgv, '', o.mode)` (the plan omitted `o.mode`; the `role` proof needs it, as the print-argv branch already passes it).
- Step 10 (header comment) needed no edit: plan 37-04 had already replaced it with `CONFIG.effort.<runtime> is the baked default effort beneath the call's --effort, for every runtime; ...` (same meaning, different wording).
- The `status-group-before-retry` case uses `status=transient` (the plan named only exit 75); the test module's docstring line carries `# noqa: E501` because the plan fixes its text.
- Executed as two fix-up lanes with the plan's steps restated, after three no-change lanes.
