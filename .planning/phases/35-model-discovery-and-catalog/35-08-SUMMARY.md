---
phase: 35-model-discovery-and-catalog
plan: 08
subsystem: catalog
tags: [bands, tiers, cost-bands, class-rule, strengths, pure]

requires:
  - phase: 35-model-discovery-and-catalog
    provides: "35-01 stub test modules; 35-02 hardcoding guard"
provides:
  - "skills/ai-kit-spec-review/ai_kit_spec/catalog_bands.py: TIERS, COST_BANDS, CLASSES, STRENGTH_CATEGORIES, quartile_cuts, tier_for, price_per_million, cost_cuts, cost_band, ClassInputs, class_for, delta_cuts, strengths_for"
  - "tests/test_catalog_bands.py: TestTiersAndCost (7) and TestClassAndStrengths (8)"

key-files:
  created:
    - skills/ai-kit-spec-review/ai_kit_spec/catalog_bands.py
  modified:
    - tests/test_catalog_bands.py

requirements-completed: [HUB-02]

executor: "cross-AI lane: pi router-env/my-coding-lite, one run (587 s, status=ok exit=0)"
---

# Phase 35 Plan 08: the pure banding rules

One commit, `2c7093e feat(35-08): add pure catalog banding rules` (staged-tests hook: 97/97 modules, per the executor's report).

## Accomplishments

- `quartile_cuts` takes only finite numbers (NaN, infinity and booleans never enter a cut), needs at least four values and returns the cuts at
  `int(n * 0.25)`, `int(n * 0.5)` and `int(n * 0.75)` of the sorted values; `tier_for` and `cost_band` put a value on a cut into the higher band;
  no cuts or no number gives `unknown`.
- `price_per_million` is input plus output (free when both are 0, `None` for missing, non-numeric, negative or non-finite prices); `cost_cuts`
  groups prices by `canonical_model_id` (else bare id), takes the median per group and returns the quartile cuts of the medians.
- `class_for(ClassInputs)` is one ordered rule (router, unknown, flagship, coding, fast, small, else general) over tier, cost band, coding edge and
  tokens per second; context is not an input and nothing is labelled review.
- `delta_cuts` and `strengths_for` give the Arena categories whose rating minus the overall rating reaches that category's own p75 delta.

## Deviations and notes for the code review

- The executor replaced test fixture keys that the hardcoding guard flagged with neutral placeholders (reported by the lane; the guard passes).
- No file outside the plan's `files_modified` was touched.

## Orchestrator verification (own runs, not the executor's claims)

- `python3 tools/run_unittest_parallel.py tests.test_catalog_bands tests.test_arch_hardcoded_models`: exit 0, 2/2 modules (15 and 12 tests).
- `rg` on `catalog_bands.py`: `_CLASS_RULES = (` and `math.isfinite` present; imports are `math`, `statistics`, `typing` only; no `context` or `ctx`.
- `make ruff`, `make pyright`, `make vulture` and `uv run pre-commit run pylint --files .../catalog_bands.py`: all Passed.
- Real-config audit after the lane (`tmp/run-2026-11-19/audit_c2.py`): nothing unexpected; only pi session logs and files of the Claude host and of
  another project's codex daemon changed.

## Self-Check: PASSED
