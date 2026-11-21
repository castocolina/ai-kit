---
phase: 36-spec-config-as-the-hub
plan: 11
subsystem: spec-config
tags: [lane-settings, writer-validation, model-bound-merge, free-lane-write-check]

requires: [36-04, 36-05, 36-07]
provides:
  - "skills/ai-kit-spec-review/ai_kit_spec/lane_settings.py: LANE_FLAG_KEYS, MODEL_BOUND, NOTE_MAX, POOL_RX, FREE_LANE_REFUSAL, clean_note, normalise_lane_settings, validate_lane_settings, write_problem"
  - "config_io.py hooks: validate_reviewer_fields chains lane_effort.effort_problem, lane_settings.validate_lane_settings and _validate_pair_fields; _cfg_partition_reviewers adds the write-only free-lane check; _cfg_render_reviewers cleans the two display lines; cfg_merge_reviewers drops model-bound settings when the pair changes (_drop_model_bound)"

key-files:
  created:
    - skills/ai-kit-spec-review/ai_kit_spec/lane_settings.py
  modified:
    - skills/ai-kit-spec-review/ai_kit_spec/config_io.py
    - tests/test_lane_settings.py
    - tests/test_config_layers.py

requirements-completed: []

executor: "cross-AI lane: pi router-env/my-coding, one run (501 s, AIKIT-XAI status=ok exit=0 attempts=1 cycles=0); the lane staged the work, ran 114/115 in the hook and made no commit (see deviation); the orchestrator made the one-line test fix and the commit"
---

# Phase 36 Plan 11: lane settings (write side)

One commit, `e208cee feat(36-11): validate and clean the new lane settings` (pre-fold; 4 files, +310 -12), made by the orchestrator from the lane's staged work plus one test line; the commit hook ran green.

## Accomplishments

- New module `lane_settings.py`: the escalation flags and `usage_limited` must be booleans (`<key>: '<name>' must be a boolean`), `usage_limit_note` is a string that needs `usage_limited = true`, `pool` must look like `<provider>:free`, the six data-use keys go through `lane_data_use.validate_note`; `normalise_lane_settings` drops false flags and cleans the two display lines before validation; `write_problem` refuses a lane carrying `pool` without a complete confirmed data-use record on the write path only (a hand-written lane still loads).
- `config_io.py`: the four hooks above; `MODEL_BOUND` settings of a lane are dropped in the layered merge when a project entry restates `runtime`, `command` or a different `model` (a flag, pool, effort or data-use confirmation given for one model never rides along to another).
- `tests/test_lane_settings.py`: 22 tests (validate 7, normalise 2, writer 5, free-lane write check 3, model-bound merge 5).

## Deviations and notes

- LIVE FACT, plan contradicts earlier code: the existing `tests/test_config_layers.py::TestLaneRoles::test_execute_lane_merges_project_over_user_within_execute_only` (user lane `e` with model `u` and `effort = "low"`, project lane `e` with model `p`) asserted that the effort of model `u` survives onto model `p`. That is exactly what the locked contract (36-RESEARCH section 0 item 6, `MODEL_BOUND`) forbids. The lane stopped without a commit rather than change the merge rule. Smallest fix following the locked text: the assertion now reads `assertNotIn("effort", entry)` with a one-line comment (one-line trivial test fix made by the orchestrator, ledger). `tests/test_config_layers.py` is outside the plan's `files_modified`; recorded here and in the ledger.
- No other file outside the plan's paths changed.

## Orchestrator verification (own runs, not the executor's claims)

- `python3 tools/run_unittest_parallel.py tests.test_lane_settings tests.test_lane_data_use tests.test_config_layers tests.test_ai_kit_spec tests.test_ai_kit_spec_legacy_config tests.test_ai_kit_spec_trust tests.test_config_callers tests.test_config_migrate tests.test_role_orders tests.test_arch tests.test_arch_hardcoded_models`: exit 0, 11/11 modules (22, 7, 54, 693, 24, 29, 10, 56, 17, 109 and 14 tests).
- `make ruff`, `make pyright`, `make vulture`: Passed; pylint on `lane_settings.py` and `config_io.py`: Passed. Read the whole `lane_settings.py` and the `config_io.py` diff against the plan.
- Real-config audit (marker-c3-p36-w4): host files only (claude job state, plugin store, codex daemon of another project) plus a pi session log.

## Self-Check: PASSED
