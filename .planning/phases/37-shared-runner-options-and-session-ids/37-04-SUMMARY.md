# 37-04 Summary: the runner's settings planner, version 1

Status: complete after one retry and one fix-up lane (pi `router-env/my-coding`, same CLI and model throughout), verified by the orchestrator.

## Lanes

- Lane 1: `AIKIT-XAI status=no_change exit=1 elapsed=36s attempts=1 tree=clean`; the model read the phase docs and ended with "not implemented or committed".
- Lane r2 (plan kept, do-not-stop note): `status=ok exit=0 elapsed=99s`, but it stopped with Task 1 written and uncommitted, because `tests.test_cli_help_flags` failed (see Deviations).
- Fix-up lane (after one orchestrator line fix): `status=ok exit=0 elapsed=1551s attempts=1 cycles=0`, three commits.

## Commits

- 8da51b7 `feat(37-04): settings planner v1 with row effort forms and print-argv setting lines`
- f1f68e7 `feat(37-04): confirmReport, statusGroup and recorded-only escalation entries`
- 1b5c169 `test(37-04): CONFIG.effort beneath the call, fed, yielding and redacted`

Each holds only `skills/ai-kit-spec-review/references/cross-ai.mjs` and `tests/test_runner_settings_argv.py`; the staged-tests hook passed (129/129 modules per the lane).

## What was done

- Planner block: `SETTING_REASONS` (10), `SETTING_NAMES` (11), `SETTING_STATES` (3), `SETTING_HANDLERS` (model, provider, role, effort, escalate_runtime, escalate_model), `bracketValue`, `mergeBracket`, `cleanSettingValue`, `planSettings(row, role, call)`, `MODEL_SLOT_FLAGS`, `confirmReport`, `reportLines`, `statusGroup`.
- `forms.effort` and `forms.provider` with source labels on all six rows; pi, codex (`withCodexKnobs`), claude review (closure now `(m, c)`) and copilot formulas read `c.adds.effort`, with the old `piThinking`/`codexEffort` fallback for the run path (unchanged until 37-06).
- `--print-argv` prints the setting lines in `SETTING_NAMES` order and `cross-ai: model-id <id>` (control-stripped, key-shape-redacted), checked by `confirmReport` first.
- Four pure self-test cases `planner-effort-no-form`, `planner-confirm-report`, `planner-status-group`, `planner-report-lines`; `CONFIG.effort` doc comment updated.
- `tests/test_runner_settings_argv.py` replaces the 37-02 stub: `TestNoSettingArgv` (1), `TestEffortForms` (5), `TestSettingsReport` (3), `TestConfigEffort` (2).

## Evidence (orchestrator re-run, scratch HOME)

- Acceptance greps: the four constants, `planSettings`, six `    forms: {` lines, one `cross-ai: model-id `, three functions, four `planner-` cases, 11 tests, no stub text, no `sk-aaaa`, `settings report claims `, `has no proof`, `MODEL_SLOT_FLAGS`, `reason: 'recorded_only'` present; no grok line added; `Makefile` and `.pre-commit-config.yaml` untouched.
- `--self-test-list`: 519 cases, 472 logic. The four planner cases and the twelve existing effort and argv cases of Task 1's verify: `self-test ok`.
- No-setting stdout argv equals the 9b3ba32 template's for all eleven `(runtime, mode)` entries, plus codex `--codex-effort high` and pi `fake/ok:high`.
- Spot checks: cursor `fake-ok-cursor[context=1m]` with `--effort high` gives model-id `fake-ok-cursor[context=1m,effort=high]`; pi with `--escalate-model --escalate-runtime --effort low` prints the six lines in fixed order and adds only `--thinking low`; claude review with `--effort max` ends `--permission-mode plan --effort max`.
- Task 3 module list: 9/9 passed (`test_runner_settings_argv` 11 tests). Eight self-test shards plus `test_ai_kit_spec_exec_formula_e2e`: 9/9 passed. Lane-reported: `make ruff`, `make pyright`, `make vulture`, `make pylint` passed. `tmp/p37-04` is gone; tree clean.
- Real-config audit: only the orchestrating Claude session's files and the codex app-server daemon's files; nothing from the lane.

## Deviations

- Orchestrator fix (plan text vs the 37-02 test): the plan's opencode effort label quoted `"--model, -m string Model to use ..."` from `run --help`, but `tests/test_cli_help_flags.py` checks every row-block flag outside a `['run', ...]` array against opencode's main `help.txt`, which has no `--model`. The label now quotes `"Model to use in the format provider/model#variant"` (same text as the provider label). Later plans that write labels must not put a subcommand-only flag token in a row label.
- `planner-confirm-report`: the plan's case expects `{ slotPrefix: 'fake/' }` to fail against `['--model', 'other/fake/ok']` (the prefix in the middle of the id); the lane replaced it with `{ slotPrefix: 'fake/ok/' }` against `fake/other` to satisfy the hardcoding guard. `confirmReport` uses `startsWith` (checked), but the case no longer shows that a match in the middle of the id is refused. Open for code review (an invented id of the allowed forms that holds `fake/` after its start).
