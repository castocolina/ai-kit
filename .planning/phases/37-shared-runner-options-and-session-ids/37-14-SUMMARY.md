# 37-14 Summary: the runner preview replaces the Python effort composers

Status: complete in two per-task lanes (pi `router-env/my-coding`), verified by the orchestrator.

## Lanes

- fix-a (Task 1): `status=ok exit=0 elapsed=656s attempts=1`, commit a67a999 (hook 130/130).
- fix-b (Tasks 2 and 3): `status=ok exit=0 elapsed=610s attempts=1`, commit f9f51ea (hook 129/129).
- No plan-as-written lane (the plan is flagged heavy): prompts were built from the plan's own task blocks plus orchestrator anchor notes checked against ccf67be.

## Commits

- a67a999 `feat(37-14): build-model-id prints the id the runner composes`
- f9f51ea `feat(37-14): bare model plus --effort for every runtime; Python effort composers and closed sets deleted`

## What was done

- `runner_dispatch.py`: `PREVIEW_TIMEOUT_S`, `MODEL_ID_PREFIX`, `SETTING_LINE_RE`, `print_argv_lines` (the runner's own `--print-argv` in `spec.cwd`, trusted only on exit 0), `preview_model_id`, `preview_setting`; `spec_with_effort` passes the bare model and `--effort` for every runtime (37-12's `context=None, session_id=None` kept); `RunnerSpec.ignored` and the `run_runner` ignored line deleted.
- `cli.py`: `build-model-id` reads the runner's `cross-ai: model-id` line (setting lines echoed on stderr), `_with_fast` keeps cursor's `fast` bracket key, named failures for a missing preview or a missing model-id line; `_EFFORT_HELP` rewritten; the `_preview_notes` and `build-command` ignored lines deleted.
- Deleted: `commands.build_reviewer_model_id`, `commands.build_cursor_agent_model_id`, and in `lane_effort.py` the closed sets `RUNNER_CODEX_EFFORTS`, `RUNNER_PI_LEVELS`, `EFFORT_PATH_RUNTIMES`, `_SUFFIX_RX`, `EffortForm`, `has_effort_path`, the per-runtime form helpers and `effort_form`. `effort_problem`, `offered_levels` and `write_problems` keep the shape and name-word checks only.
- `effort_probe.py`: `NO_PREVIEW_REASON`, `NO_SETTING_REASON`, `CARRIED_REASON`, `_preview_outcome` (preview in a private temporary cwd), `probe_effort(..., preview_fn=None)`.
- `tests/test_runner_preview.py` (37-02 stub, filled in place): `TestPreviewReaders` (3), `TestBuildModelIdReadsTheRunner` (4), `TestNoPythonEffortComposer` (2).

## Evidence (orchestrator re-run, `tmp/run-2026-11-19/c5-verify-37-14.sh ccf67be`)

- Acceptance greps: no `build_reviewer_model_id`; composer names only in tests/test_runner_settings_argv.py (`class TestEffortForms`, `test_effort_form_per_runtime`: the runner's own forms, not a Python composer); no `.ignored` or `ignored: str` in runner_dispatch.py or cli.py; `def print_argv_lines(` 1, `MODEL_ID_PREFIX` 1, `def preview_setting(` 1, `def _preview_outcome(` 1, `CARRIED_REASON` 1; 9 tests in test_runner_preview.py, grok 0.
- `build-model-id` through the real template (scratch HOME): cursor `--effort high --context 1m --fast true` prints `placeholder-model-1[fast=true,effort=high,context=1m]`; codex `--effort high` prints the bare id with `setting effort=high applied` on stderr; codex `--fast true` prints the cursor-only note; pi prints `fake/placeholder-model-1`.
- Modules 12/12 (runner_preview, lane_effort, effort_probe, runner_dispatch, ai_kit_spec, runtimes_table, propose_cmds, trust, arch_hardcoded_models, no_seed_refusal, runner_flags, runner_settings_argv); verbose: all 9 preview tests `ok`, none skipped.
- Baseline json, detection.py and the template unchanged. Lane-reported: `make ruff`, `make pyright`, `make vulture`, `make pylint` exit 0.
- Real-config audit (marker at plan start): Claude host-session files (jobs, plugin store, synced skills) and the codex daemon's logs and model cache; no opencode or pi config file changed.

## Deviations

- tests/test_propose_cmds.py (not in the plan's file list, but in its verify list): `test_effort_levels_per_row` asserted the old closed-set refusal of codex `max`; updated to the plan's rule (lesson 4).
- `TestEffortWiring.test_effort_help_names_the_ignored_line` now asserts `reports it ignored with a reason` (the new `_EFFORT_HELP`); test name kept.
- `_with_fast`'s comment is split over two lines (line-length limit); module and function docstrings of lane_effort.py are close to, not word for word, the plan text.
- Open for review: no test pins `review_spec(rt, base, {"effort": 3}, 30).effort == "3"` or the absence of a `RunnerSpec.ignored` field (the code does both); the baseline needed no change.
