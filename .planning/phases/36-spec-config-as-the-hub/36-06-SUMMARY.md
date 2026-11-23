---
phase: 36-spec-config-as-the-hub
plan: 06
subsystem: spec-config
tags: [lane-pool, catalog-rows, drop-filters]

requires: [36-01, 36-02]
provides:
  - "skills/ai-kit-spec-review/ai_kit_spec/lane_pool.py: POOL_CLASSES, ALIAS_LABEL, DROP_REASONS, Row, PoolSplit, snapshot_cli, checked_fact, fact_value, build_rows, is_unknown, drop_reason, split_pools"

key-files:
  created:
    - skills/ai-kit-spec-review/ai_kit_spec/lane_pool.py
  modified:
    - tests/test_lane_pool.py

requirements-completed: [HUB-07]

executor: "cross-AI lane: pi router-env/my-coding, one run (906 s, AIKIT-XAI status=ok exit=0 attempts=1 cycles=0)"
---

# Phase 36 Plan 06: lane_pool

One commit, `7f90f97 feat(36-06): build lane candidate pools` (pre-fold; 2 files, +344 -4); the commit hook ran 115/115 modules green.

## Accomplishments

- New pure module `lane_pool.py`: one row per (catalog key, runtime) sorted by (key, runtime) with closed-list facts read only through `checked_fact`, the drop filters (rejected, listed disabled by host, stale, stale provider, unmatched) and `split_pools` into the purpose pool, the unknown group, the wider group and the router-env alias group; it imports nothing from `cli`, `config_io` or `detection`.
- `tests/test_lane_pool.py`: 18 tests (TestRows 4, TestDrops 7, TestGroups 7), including an AST import fence and a no-mutation check.

## Deviations and notes

- None. No file outside the plan's two paths changed.

## Orchestrator verification (own runs, not the executor's claims)

- `python3 tools/run_unittest_parallel.py tests.test_lane_pool tests.test_arch_hardcoded_models tests.test_arch`: exit 0, 3/3 modules (18, 14 and 109 tests).
- `make ruff`, `make pyright`, `make vulture`: Passed; pylint on `lane_pool.py`: Passed. Read the whole `lane_pool.py` against the plan's rules.
- Real-config audit (marker-c2-p36-w2): host and other-agent files only plus session logs.

## Self-Check: PASSED
