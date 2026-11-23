---
phase: 36-spec-config-as-the-hub
plan: 01
subsystem: test-layout
tags: [test-stubs, e2e-group, generated-listings]

requires: []
provides:
  - "17 skipped stub test modules for phase 36 (each with the repo-root sys.path preamble), so later plans only fill stub bodies"
  - "tests.test_ai_kit_spec_exec_formula_e2e registered in E2E_MODULES with a recorded time of 1 s in E2E_RECORDED_SECS"
  - "Makefile and .pre-commit-config.yaml listings regenerated once by tools/gen_test_groups.py"

key-files:
  created:
    - tests/test_config_status.py
    - tests/test_role_orders.py
    - tests/test_lane_effort.py
    - tests/test_lane_pool.py
    - tests/test_lane_price.py
    - tests/test_lane_data_use.py
    - tests/test_ai_kit_spec_exec_formula_e2e.py
    - tests/test_lane_order.py
    - tests/test_lane_settings.py
    - tests/test_propose_cmds.py
    - tests/test_no_seed_refusal.py
    - tests/test_spec_chain_text.py
    - tests/test_config_role_write.py
    - tests/test_effort_probe.py
    - tests/test_spec_config_lane_json.py
    - tests/test_config_herdr_identity.py
    - tests/test_spec_config_flow_text.py
  modified:
    - tools/run_unittest_parallel.py
    - Makefile
    - .pre-commit-config.yaml

requirements-completed: []

executor: "cross-AI lane: pi router-env/my-coding, one run (559 s, AIKIT-XAI status=ok exit=0 attempts=1 cycles=0); the 1800 s lane timeout was not reached (the commit hook ran the full groups inside the lane)"
---

# Phase 36 Plan 01: test layout

One commit, `3b96713 test(36-01): stub every phase 36 test module and register the exec-formula e2e module` (pre-fold; 20 files, +297 -5); the hook ran
180/180 modules green (15/15 under uv).

## Accomplishments

- 17 stub modules (one skipped `test_stub` each), the e2e registration (2 lines in `E2E_MODULES`, 1 in `E2E_RECORDED_SECS`), regenerated listings.
- `tools/gen_test_groups.py` leaves `Makefile` and `.pre-commit-config.yaml` unchanged after the commit; `tests.test_gate_scope` is green.

## Deviations and notes

- None. No file outside the plan's 20 paths changed; the diff has no formatting noise (the runner file shows exactly the 3 planned lines).

## Orchestrator verification (own runs, not the executor's claims)

- `python3 tools/run_unittest_parallel.py tests.test_gate_scope tests.test_run_unittest_parallel tests.test_staged_mapper tests.test_config_status
  tests.test_spec_chain_text tests.test_ai_kit_spec_exec_formula_e2e`: exit 0, 6/6 modules (62, 58, 73 and 1 + 1 + 1 tests).
- `make ruff pyright vulture`: all Passed. Read the `tools/run_unittest_parallel.py` diff and one stub.
- Real-config audit (marker-c1-p36-w1): host and other-agent files plus pi session logs only.

## Self-Check: PASSED
