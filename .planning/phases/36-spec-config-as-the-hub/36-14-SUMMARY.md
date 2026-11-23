---
phase: 36-spec-config-as-the-hub
plan: 14
subsystem: spec-config
tags: [refusals, no-formula, custom-lane, guard-test]

requires: [36-11, 36-12]
provides:
  - "commands.execute_cli_error(cli): None for a runtime with an exec formula; `'<cli>' has no exec formula in the runner (route no_formula): <source>` for a table row without one; `'<cli>' is not a runtime in the table; store it as a custom `command` lane (custom lanes run in review mode only)` otherwise"
  - "execute_selection.screen_execute_clis refuses only a runtime outside the table or a row with runner False"
  - "config_io save error names the custom `command` lane instead of the table"
  - "tests/test_no_seed_refusal.py: python_sources, flag_lines, OLD_FLAG_RX, TestNoSeedFlagReader (3), TestClaudeExecuteLane (1), TestOutOfTableRuntime (2)"

key-files:
  created: []
  modified:
    - skills/ai-kit-spec-review/ai_kit_spec/commands.py
    - skills/ai-kit-spec-review/ai_kit_spec/execute_selection.py
    - skills/ai-kit-spec-review/ai_kit_spec/config_io.py
    - tests/test_no_seed_refusal.py
    - tests/test_ai_kit_spec.py
    - tests/test_ai_kit_spec_superpowers.py
    - tests/test_ai_kit_spec_legacy_config.py

requirements-completed: []

executor: "cross-AI lane: pi router-env/my-coding, one run (454 s, AIKIT-XAI status=ok exit=0 attempts=1 cycles=0)"
---

# Phase 36 Plan 14: refusals name a fact

One commit (pre-fold): `3d1e60a feat(36-14): name execution refusal facts and custom lanes` (7 files, +155 -63; the lane folded the two tasks into one commit, hook 115/115).

## Accomplishments

- A claude execute lane passes config validation and execute selection and is skipped by the route walk as `no_formula`; a runtime outside the table is pointed at the custom `command` lane; dispatch-execute keeps exit 2 with the new reasons.
- `tests/test_no_seed_refusal.py` fails when any Python file under `skills/` or `tools/` names `review_only` (6 tests, with a planted non-vacuity case). Existing grok tests changed only in their expected text; no grok case added.

## Deviations and notes

- The lane made one commit for the two tasks instead of one per task. No file outside the plan's seven paths changed.

## Orchestrator verification (own runs, not the executor's claims)

- `python3 tools/run_unittest_parallel.py tests.test_no_seed_refusal tests.test_ai_kit_spec_legacy_config tests.test_ai_kit_spec tests.test_ai_kit_spec_superpowers tests.test_ai_kit_spec_runtimes_table tests.test_ai_kit_gsd_curated_config tests.test_arch_hardcoded_models tests.test_arch`: exit 0, 8/8 modules (6, 24, 694, 170, 62, 104, 14 and 109 tests).
- `make ruff`, `make pyright`, `make vulture`, `make pylint`: Passed. Read the whole source diff and the new test module against the plan.

## Self-Check: PASSED
