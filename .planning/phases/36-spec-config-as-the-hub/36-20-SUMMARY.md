---
phase: 36-spec-config-as-the-hub
plan: 20
subsystem: spec-config
tags: [config-writer, role-orders, explicit-none-warning, legacy-ladder-split]

requires: [36-04, 36-10, 36-11, 36-17]
provides:
  - "config_io.py writes flat policy keys in [lanes.policy] plus a `ladder` in [lanes.policy.review] and [lanes.policy.execute] (role_orders.split_policy), never a flat ladder; a role with no lane or an empty order gets no table and an old one is removed"
  - "keys naming no lane of the role, or a rejected lane, are dropped with a WARNING; a legacy flat ladder (JSON or file) is split by role with one stderr note and rewritten per role; an inline role table is rewritten as a header; the generated fallback-order comment sits above each role table"
  - "render-toml (cfg_render_lanes) prints the reader's no-fallback line for a written role whose lanes, in written order, are all usage-limited or share a pool (explicit none is written, nothing refuses)"
  - "tests/test_config_role_write.py: TestRoleOrderWrite (14 tests); old flat-ladder tests in test_config_layers.py, test_ai_kit_spec.py and test_ai_kit_spec_legacy_config.py edited to the new shape"

key-files:
  modified:
    - skills/ai-kit-spec-review/ai_kit_spec/config_io.py
    - tests/test_config_role_write.py
    - tests/test_config_layers.py
    - tests/test_ai_kit_spec.py
    - tests/test_ai_kit_spec_legacy_config.py

requirements-completed: [HUB-05]

executor: "cross-AI lane: pi router-env/my-coding, AIKIT-XAI status=ok exit=0 cli_rc=0 elapsed=849s attempts=1 cycles=0; one commit"
---

# Phase 36 Plan 20: per-role order writer

One commit (pre-fold): `6f5906d feat(36-20): write separate role orders` (5 files, +350 -74, commit hook passed).

## Accomplishments

- The writer keeps reviewers and executors apart: `_cfg_lanes_policy`, `_role_source`, `_ladder_drops`, `_report_drops`, `_splice_policy`, `_refresh_ladder_comments` and `_written_fallback_warnings` in `config_io.py`; `_splice_roster` and `cfg_render_lanes` call them. The plan's message texts are used as written.
- The writer prints the same no-fallback line as the reader (`lane_settings.fallback_warnings` fed each role's lanes in the written order); a test checks that the reader's warning equals the writer's.

## Deviations and notes

- Docstrings of the new helpers are shorter than the plan's wording (behaviour is identical); `_ladder_drops` and `_report_drops` carry none. No file outside the plan's five paths changed.

## Orchestrator verification (own runs, not the executor's claims)

- `python3 tools/run_unittest_parallel.py tests.test_config_role_write tests.test_lane_settings tests.test_config_layers tests.test_ai_kit_spec tests.test_ai_kit_spec_legacy_config tests.test_ai_kit_spec_routing tests.test_ai_kit_spec_trust tests.test_role_orders tests.test_arch_hardcoded_models`: exit 0, 9/9 modules (14, 48, 54, 694, 24, 31, 29, 17 and 23 tests).
- `make ruff`, `make pyright`, `make vulture`, `make pylint`: Passed. Read the whole source and test diff against the plan.

## Self-Check: PASSED
