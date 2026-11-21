---
phase: 36-spec-config-as-the-hub
plan: 21
subsystem: spec-config
tags: [effort-probe, check-reviewer, render-toml, effort-refusal]

requires: [36-05, 36-18]
provides:
  - "effort_probe.py (new): probe_effort runs one test call with the effort set (through spec_with_effort) and returns state accepted, rejected, inconclusive or ignored; the host's first error line is control-free and redacted; wrapper lines (cross-ai:, AIKIT-XAI, ai-kit-spec:) are never reported as the host's error; stores nothing"
  - "cli.py: check-reviewer --effort adds effort_probe to its JSON and refuses --catalog-path together with --effort or an effort key in --extra-json (exit 2, nothing probed or written); render-toml takes --catalog-path and --runtimes-json and refuses, before any migration, splice or write, a lane whose effort lane_effort.write_problems names (exit 1); an unreadable explicit evidence file exits 2"
  - "tests/test_effort_probe.py: TestProbeEffort (11), TestCheckReviewerEffort (5), TestRenderTomlEffort (5)"

key-files:
  created:
    - skills/ai-kit-spec-review/ai_kit_spec/effort_probe.py
  modified:
    - skills/ai-kit-spec-review/ai_kit_spec/cli.py
    - tests/test_effort_probe.py

requirements-completed: [HUB-05]

executor: "cross-AI lane: pi router-env/my-coding, AIKIT-XAI status=ok exit=0 cli_rc=0 elapsed=562s attempts=1 cycles=0; one commit"
---

# Phase 36 Plan 21: effort probe and render-toml effort refusal

One commit (pre-fold): `5f29ea9 feat(36-21): probe and validate lane effort` (3 files, +321 -7, commit hook passed).

## Accomplishments

- An unknown effort is learned by one call: an answered call is `accepted` with the label `accepted by a call on <YYYY-MM-DD>`; only `real_error` or `configuration` with a host line is `rejected`; every other stop or an unanswered call is `inconclusive`; an effort with no runner path makes no call (`ignored`).
- `render-toml` writes no lane whose effort the model does not list or the runner cannot pass; unknown support is never refused.

## Deviations and notes

- `effort_probe._host_error_line` and `_classify` run `secret_shapes.redact(line, "[redacted]")` before `usability.sanitize_error` (the plan names only `sanitize_error`); the extra pass catches a key glued to a control character (earlier lanes' lesson 3) and changes no other output.
- The lane's tests are lighter than the plan's behaviour lines in places (for example `test_accepted_labels_the_date` does not assert `error is None`, `test_effort_probe_in_output` does not assert the exact key set or the label pattern, the custom-lane case of the ignored test uses a runtime-less model-less lane). The code satisfies each omitted line (read against the plan); the code review of the phase can decide whether to tighten them. No file outside the plan's three paths changed.

## Orchestrator verification (own runs, not the executor's claims)

- `python3 tools/run_unittest_parallel.py tests.test_effort_probe tests.test_ai_kit_spec tests.test_config_layers tests.test_arch_hardcoded_models tests.test_lane_effort tests.test_arch`: exit 0, 6/6 modules (21, 694, 54, 23, 24 and 109 tests).
- `make ruff`, `make pyright`, `make vulture`, `make pylint`: Passed. Read the whole source and test diff against the plan.

## Self-Check: PASSED
