---
phase: 36-spec-config-as-the-hub
plan: 04
subsystem: spec-config
tags: [role-orders, policy, review, execute]

requires: [36-01]
provides:
  - "skills/ai-kit-spec-review/ai_kit_spec/role_orders.py: ROLES, role_orders, role_order, ordered_lanes, split_policy"
  - "config_io.cfg_combine returns `orders` (per-role priority order) beside the unchanged raw `policy`; _combine_roles helper"
  - "quota.resolve_reviewers walks the review order over the review lanes; dispatch_injection.assemble_candidates takes the execute lanes and the execute order"

key-files:
  created:
    - skills/ai-kit-spec-review/ai_kit_spec/role_orders.py
  modified:
    - skills/ai-kit-spec-review/ai_kit_spec/config_io.py
    - skills/ai-kit-spec-review/ai_kit_spec/quota.py
    - skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/dispatch_injection.py
    - tests/test_role_orders.py

requirements-completed: [HUB-05]

executor: "cross-AI lane: pi router-env/my-coding, one run (571 s, AIKIT-XAI status=ok exit=0 attempts=1 cycles=0)"
---

# Phase 36 Plan 04: per-role orders (read side)

One commit, `b922be1 feat(36-04): read separate role orders` (pre-fold; 5 files, +350 -20); the commit hook ran 119/119 modules green.

## Accomplishments

- New pure module `role_orders.py`: each role's order from `[lanes.policy.review]` or `[lanes.policy.execute]`; a legacy shared `ladder` loads as each role's order filtered to that role's lanes with one note; dangling keys dropped with a named warning; duplicates keep their first place; inline-table or array entries are never hashed.
- `cfg_combine` adds `orders` through the new 5-argument `_combine_roles`; the review run reads the review order over the review lanes and the execute adapter reads the execute lanes and the execute order, each falling back to the flat view only for hand-built configs.
- `tests/test_role_orders.py`: 17 tests (tracer 3, rules 10, layers 3, execute adapter 1); no existing test changed.

## Deviations and notes

- None. No file outside the plan's five paths changed.

## Orchestrator verification (own runs, not the executor's claims)

- `python3 tools/run_unittest_parallel.py tests.test_role_orders tests.test_ai_kit_spec_superpowers tests.test_ai_kit_spec_legacy_config tests.test_ai_kit_spec_routing tests.test_ai_kit_spec_check_providers tests.test_ai_kit_spec_trust tests.test_config_callers tests.test_config_layers tests.test_ai_kit_spec tests.test_arch`: exit 0, 10/10 modules (17, 170, 24, 30, 29, 29, 10, 50, 693 and 109 tests).
- `make ruff`, `make pyright`, `make vulture`: Passed; pylint on the four changed source files: Passed. Read the whole `role_orders.py` and the diffs of `config_io.py`, `quota.py` and `dispatch_injection.py` against the plan's rules.
- Real-config audit (marker-c2-p36-w2): host and other-agent files only plus session logs.

## Self-Check: PASSED
