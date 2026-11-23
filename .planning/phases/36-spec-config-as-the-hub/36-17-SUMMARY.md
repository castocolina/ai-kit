---
phase: 36-spec-config-as-the-hub
plan: 17
subsystem: spec-config
tags: [lane-settings, readers, usage-limit, fallback, escalation]

requires: [36-04, 36-11]
provides:
  - "lane_settings.py readers: LaneSettingError, UsageLimit, Escalation, FALLBACK_WARNING, lane_usage_limit, lane_escalation, escalation_target, lane_fallback (pool rule), selectable_lanes, fallback_warnings"
  - "config_io._combine_roles prints one no-fallback warning per role through lane_settings.fallback_warnings; nothing refuses or reorders; cfg_combine unchanged"
  - "tests/test_lane_settings.py part 2: TestLaneUsageLimit, TestLaneFallback, TestFallbackWarnings, TestLaneEscalation, TestEscalationTarget, TestNoFlagSetter (module runs 48 tests)"

key-files:
  created: []
  modified:
    - skills/ai-kit-spec-review/ai_kit_spec/lane_settings.py
    - skills/ai-kit-spec-review/ai_kit_spec/config_io.py
    - tests/test_lane_settings.py

requirements-completed: []

executor: "cross-AI lane: pi router-env/my-coding, one run (529 s, AIKIT-XAI status=ok exit=0 attempts=1 cycles=0)"
---

# Phase 36 Plan 17: lane setting readers

One commit (pre-fold): `c9cf243 feat(36-17): read lane settings and warn on missing fallback` (3 files, +380 -6; the lane folded the three tasks into one commit, hook 115/115).

## Accomplishments

- One place for consumers to read the usage-limit and escalation flags and the fallback (pool rule, role order, duplicate key keeps its first place); malformed collections never raise in the fallback and warning paths, while `lane_usage_limit` and `lane_escalation` stay strict.
- A hand-written file whose usage-limited lanes have no selectable fallback prints one warning per role through `cfg_resolve`; the roster is untouched.
- A guard test fails when any module other than `lane_settings.py` holds a flag literal or names a reader; both scanners have a planted non-vacuity case. No run reads the readers in this phase (Phases 37, 40 and 41 do).

## Deviations and notes

- The lane made one commit for the three tasks instead of one per task. No file outside the plan's three paths changed.

## Orchestrator verification (own runs, not the executor's claims)

- `python3 tools/run_unittest_parallel.py tests.test_lane_settings tests.test_config_layers tests.test_role_orders tests.test_ai_kit_spec tests.test_arch tests.test_arch_hardcoded_models`: exit 0, 6/6 modules (48, 54, 17, 694, 109 and 23 tests).
- `make ruff`, `make pyright`, `make vulture`, `make pylint`: Passed. Read the whole source diff against the plan.

## Self-Check: PASSED
