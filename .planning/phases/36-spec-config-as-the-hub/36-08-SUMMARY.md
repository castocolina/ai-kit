---
phase: 36-spec-config-as-the-hub
plan: 08
subsystem: spec-config
tags: [exec-formula, runtime-table, drift-test, advice]

requires: [36-01, 36-04]
provides:
  - "skills/ai-kit-spec-review/ai_kit_spec/detection.py: ExecFormula, Advice, Runtime.exec_formula and Runtime.advice, has_exec_formula, exec_formula_source, NO_RUNNER_ENTRY, advice_line (additive; review_only untouched)"
  - "tests/test_ai_kit_spec_exec_formula_e2e.py: formula_problems and the offline --print-argv drift check for every runner row, plus four non-vacuity tests"

key-files:
  created: []
  modified:
    - skills/ai-kit-spec-review/ai_kit_spec/detection.py
    - tests/test_ai_kit_spec_exec_formula_e2e.py
    - tests/test_ai_kit_spec_runtimes_table.py
    - tests/test_ai_kit_gsd_curated_config.py

requirements-completed: []

executor: "cross-AI lane: pi router-env/my-coding, one run (933 s, AIKIT-XAI status=ok exit=0 attempts=1 cycles=0)"
---

# Phase 36 Plan 08: exec formula mirror

Two commits (pre-fold): `441bd8d feat(36-08): mirror the runner's exec formula per runtime with a drift test` (task 1, hook 115/115) and `ed1c317 feat(36-08): add exec formula readers with unit pins and record the drift test time` (task 2, hook 116/116); 4 files, +191 -8 over the two.

## Accomplishments

- Every runner row of the table carries the runner's exec head with a source label (pi, opencode, cursor, codex, copilot; claude has a null head and the seed advice "usually the main agent in this host [seed row, unverified]"); `has_exec_formula` is the one predicate for plan 36-12. The grok row is byte-identical to HEAD, `review_only` is untouched.
- The drift test runs the real runner template with `--print-argv --mode exec` for each runner row (no model call) and fails on a changed head, a missing formula or a changed null entry; four non-vacuity tests prove each rule fires without node.
- Two refusal assertions are wording-neutral (`test_ai_kit_spec_runtimes_table`, `test_ai_kit_gsd_curated_config`) so plan 36-14 can reword the refusal in one test.

## Deviations and notes

- `E2E_RECORDED_SECS["tests.test_ai_kit_spec_exec_formula_e2e"]` already read 1 (plan 36-01) and the measured run took 0.3 s, so `tools/run_unittest_parallel.py` did not change (the plan says to edit only when the rounded value differs; the second commit therefore did not stage it).
- No file outside the plan's paths changed.

## Orchestrator verification (own runs, not the executor's claims)

- `python3 tools/run_unittest_parallel.py tests.test_ai_kit_spec_exec_formula_e2e tests.test_ai_kit_spec_runtimes_table tests.test_ai_kit_spec_routing tests.test_ai_kit_spec tests.test_ai_kit_gsd_curated_config tests.test_gate_scope tests.test_arch_hardcoded_models tests.test_arch`: exit 0, 8/8 modules (5, 62, 30, 693, 104, 62, 14 and 109 tests); the e2e module ran 5 tests against a real node.
- `make ruff`, `make pyright`, `make vulture`: Passed; pylint on `detection.py`: Passed. Read the whole `detection.py` diff (grok row untouched).
- Real-config audit (marker-c3-p36-w3): host and other-agent files plus pi session logs only.

## Self-Check: PASSED
