---
phase: 36-spec-config-as-the-hub
plan: 18
subsystem: spec-config
tags: [effort, runner-dispatch, previews, ignored-line]

requires: [36-05, 36-12, 36-13]
provides:
  - "runner_dispatch.spec_with_effort(runtime, model, mode, timeout_s, knobs): the one RunnerSpec constructor (composes the effort through lane_effort.effort_form before the spec exists); RunnerSpec.ignored; run_runner prints `ai-kit-spec: <ignored line>` first, before the node check"
  - "review_spec, execute_dispatch._runner_spec and cli build-command go through spec_with_effort; build-command and render-command print the ignored line on stderr; render-command prints `render-command: advice for <runtime>: <line>` when detection.advice_line returns one"
  - "the --effort help of build-command and dispatch-execute no longer promises a silent drop (_EFFORT_HELP)"
  - "tests/test_ai_kit_spec_runner_dispatch.py: TestEffortWiring (12 tests; the module runs 82)"

key-files:
  created: []
  modified:
    - skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py
    - skills/ai-kit-spec-review/ai_kit_spec/execute_dispatch.py
    - skills/ai-kit-spec-review/ai_kit_spec/cli.py
    - tests/test_ai_kit_spec_runner_dispatch.py
    - tests/fixtures/no_hardcoded_models_baseline.json

requirements-completed: []

executor: "cross-AI lane: pi router-env/my-coding, one run (506 s, AIKIT-XAI status=ok exit=0 attempts=1 cycles=0); the lane staged its work and stopped on a hook failure, the orchestrator finished the commit"
---

# Phase 36 Plan 18: effort wiring

One commit (pre-fold): `59995a1 feat(36-18): wire the effort into every runner path` (5 files, +237 -27, hook ok). The lane made no commit: its hook run failed 114/115 on `tests.test_arch_hardcoded_models` (`fixed, remove from baseline: tests/test_ai_kit_spec_runner_dispatch.py keyval x/y`).

## Accomplishments

- A set effort reaches each runtime in its own form (codex flag; pi, cursor and opencode in the model id) or prints an `ignored:` line, on review dispatch, execute dispatch, the probe, `build-command` and `render-command`; a lane with no effort passes nothing and prints nothing.
- `cross-ai.mjs` is not edited.

## Deviations and notes

- Plan and baseline contradict: the plan replaces the literal `x/y` in an existing test (placeholder rule), which removes one `keyval x/y` hit, and the guard's shrink-only rule then demands the matching baseline line be removed, but `tests/fixtures/no_hardcoded_models_baseline.json` is not in the plan's `files_modified`. The orchestrator removed exactly one `"keyval x/y"` line from that file (five hits to four) and committed it with the plan's four files; `tests.test_arch_hardcoded_models` is green (23 tests).

## Orchestrator verification (own runs, not the executor's claims)

- `python3 tools/run_unittest_parallel.py tests.test_ai_kit_spec_runner_dispatch tests.test_ai_kit_spec tests.test_ai_kit_spec_superpowers tests.test_arch_hardcoded_models tests.test_arch`: exit 0, 5/5 modules (82, 694, 170, 23 and 109 tests).
- `make ruff`, `make pyright`, `make vulture`, `make pylint`: Passed. Read the whole source diff against the plan.

## Self-Check: PASSED
