---
phase: 36-spec-config-as-the-hub
plan: 07
subsystem: spec-config
tags: [lane-price, lane-data-use, free-pool, data-use-record]

requires: [36-01, 36-02, 36-06]
provides:
  - "skills/ai-kit-spec-review/ai_kit_spec/lane_price.py: ZERO_LOCALITY, POOL_TIER, POOL_KEY_RX, Price, price_of, pool_key"
  - "skills/ai-kit-spec-review/ai_kit_spec/lane_data_use.py: DATA_USE_VALUES, DATA_USE_LABELS, DATA_USE_KEYS, LINE_MAX, SOURCE_MAX, clean_line, validate_note"

key-files:
  created:
    - skills/ai-kit-spec-review/ai_kit_spec/lane_price.py
    - skills/ai-kit-spec-review/ai_kit_spec/lane_data_use.py
  modified:
    - tests/test_lane_price.py
    - tests/test_lane_data_use.py

requirements-completed: [HUB-10]

executor: "cross-AI lane: pi router-env/my-coding, one run (623 s, AIKIT-XAI status=ok exit=0 attempts=1 cycles=0)"
---

# Phase 36 Plan 07: lane_price and lane_data_use

One commit, `44816e1 feat(36-07): add sourced lane pricing and data use validation` (pre-fold; 4 files, +396 -8); the commit hook ran 115/115 modules green.

## Accomplishments

- New pure module `lane_price.py`: a price is `zero`, `nonzero`, `unknown` or `conflict` from its sources only (the models.dev `free_or_local` band read through `checked_fact`, and the host listing's cost items from the runtimes snapshot); a zero and a nonzero reading give `conflict`; one zero figure beside a positive one is not zero; `pricing` alone is never a source; a bare or provider-prefixed model id gets the models.dev band, a row of another provider only its host reading; `pool_key` gives `<provider>:free` with the contract shape.
- New pure module `lane_data_use.py`: `clean_line` (control characters removed, key shapes redacted, at most 200 characters) and `validate_note` (five required keys plus `data_use_label` exactly when `data_use` is not `unknown`; consistency only, nothing defaulted).
- `tests/test_lane_price.py` (10 tests) and `tests/test_lane_data_use.py` (7 tests); the stubs are gone.

## Deviations and notes

- None. No file outside the plan's four paths changed. The lane fixed its own first ruff and pyright findings (line length, type narrowing) before the commit.

## Orchestrator verification (own runs, not the executor's claims)

- `python3 tools/run_unittest_parallel.py tests.test_lane_price tests.test_lane_data_use tests.test_arch_hardcoded_models tests.test_arch`: exit 0, 4/4 modules (10, 7, 14 and 109 tests).
- `make ruff`, `make pyright`, `make vulture`: Passed; pylint on both modules: Passed. Read both whole modules against the plan's rules.
- Real-config audit (marker-c3-p36-w3): host and other-agent files plus a pi session log only.

## Self-Check: PASSED
