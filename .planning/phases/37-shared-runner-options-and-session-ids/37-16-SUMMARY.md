# 37-16 Summary: the runner owns the model id floor; the Python grammar mirror is gone

Status: complete in one lane for all three tasks (pi `router-env/my-coding`), verified by the orchestrator.

## Lanes

- fix-a (Tasks 1, 2 and 3): `status=ok exit=0 elapsed=678s attempts=1`, commit 5e61a0b (hook 133/133).
- The prompt was built from the plan's own task blocks plus orchestrator anchor notes checked against a450a8d (37-14 had already changed runner_dispatch.py; the plan's line numbers were stale).

## Commits

- 5e61a0b `feat(37-16): the runner owns the model id floor; Python grammar mirror deleted`

## What was done

- curated-config `cross_ai.py`: `RUNNER_MODEL_FLOOR_RE` (the template's `MODEL_ID_FLOOR` without anchors, pinned by a test that reads the template) and `runner_floor_problem(label, value)`; `MODEL_ID_RE` and `model_id_problem` unchanged for review keys.
- `cli._model_refusal`: hook-token check first (`unsafe_hook_token`), then the floor (`unsupported_model_id`); `plan_edit._plan_set_script_model`, `plan_io._model_row_problem` and `cross_ai_script._drop_refused_models` use the floor; `cross_ai_build.runner_model_problem` and its `model_id_ok` import deleted; `cross_ai_build` dropped from three import lines that no longer use it.
- `runner_dispatch.py`: `MODEL_ID_SRC`, `CURSOR_MODEL_ID_SRC`, `PI_MODEL_ID_SRC`, `OPENCODE_MODEL_ID_SRC`, `_MODEL_ID_SRC`, `model_id_ok`, `model_id_src`, the `SUPPORTED_EXECUTE_CLIS` import and gate, and the `run_runner` id refusal deleted; `project_runner_command` checks `HOOK_TOKEN_RE` only (a claude hook is built now).
- Tests: `TestRunnerFloor` (2), `test_unsafe_hook_token_comes_first`, `test_upgrade_keeps_an_unusual_shape` and renamed floor tests in tests/test_curated_config_script.py; renamed floor tests in tests/test_curated_config_plan_edit.py; `TestRunnerOwnsTheModelFloor` (4) and two renamed `TestProjectRunnerCommand` tests in tests/test_ai_kit_spec_runner_dispatch.py; `test_claude_maps_to_the_runner_command`; `GRAMMAR_MIRROR_RX`, `grammar_lines`, `TestNoGrammarMirror` (2) in tests/test_no_seed_refusal.py. Five fixed baseline hits removed (shrink-only).

## Evidence (orchestrator re-run, `tmp/run-2026-11-19/c6-verify-37-16.sh a450a8d`)

- Acceptance greps: no `runner_model_problem` or `model_id_ok` under curated-config; `runner_floor_problem` in curated cli.py 1; floor definitions 2; `grammar` 0 in both curated test files; mirror names and `is not a valid` 0 in runner_dispatch.py; `TestRunnerOwnsTheModelFloor` present, `TestModelIdCharsetParity` gone; `TestNoGrammarMirror` and `GRAMMAR_MIRROR_RX` present, grok 0; no mirror name left in any skills/tools Python file.
- Behaviour: the floor pattern equals the template's; `runner_floor_problem` passes `placeholder-model-1`, `fake/placeholder-model-1:high`, `placeholder-model-1[effort=high]` and refuses `-placeholder-model-1`, `a b`, `a[x=1][y=2]`, `""` with the plan's text; `project_runner_command` builds hooks for claude, placeholder-cli-1, pi and opencode (`--role execute --host auto`) and returns None for a cursor bracket id and `has space`.
- Modules 11/11 (no_seed_refusal, ai_kit_gsd_curated_config, curated_config_script, curated_config_plan_edit, curated_config_apply, gsd_curated_eval, arch_hardcoded_models, runner_flags, ai_kit_spec, lane_effort, runner_dispatch). Baseline json: 5 lines removed, none added; detection.py and the template unchanged. Lane-reported: `make ruff`, `make pyright`, `make vulture`, `make pylint` exit 0.

## Deviations

- tests/test_curated_config_plan_edit.py `_run_plan_set` now passes `--` before the key and value, so argparse accepts the leading-dash value `-placeholder-model-1`; every caller of the helper still passes (89 tests).
- The unforced `plan set script:cross-ai.model.pi placeholder-model-1` case needed that model added to the test's synthetic inventory (and the plan saved against it) before the set is accepted.
- The floor comment is wrapped over two lines (line-length limit); `runner_floor_problem` has no docstring, as in the plan text.
