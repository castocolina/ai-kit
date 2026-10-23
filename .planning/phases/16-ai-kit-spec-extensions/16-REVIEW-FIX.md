---
phase: 16-ai-kit-spec-extensions
fixed_at: 2026-09-24
review_path: .planning/phases/16-ai-kit-spec-extensions/16-REVIEW.md
iteration: 1
findings_in_scope: 5
fixed: 5
skipped: 0
status: all_fixed
---

# Phase 16: Code Review Fix Report

All five findings from `16-REVIEW.md` were fixed in commit `99ccb98`. None of them changed behavior.

- **WR-01 (fixed):** sorted the import block in `tests/test_ai_kit_usage_metrics.py` with `ruff check --fix` (I001).
- **WR-02 (fixed):** moved the two over-long `_FIELD_TYPES` comments in `model_catalog.py` onto their own lines (E501).
- **WR-03 (fixed):** collapsed the nested `image_input` condition in `cli.py` `_apply_runtime_meta` into one `if` (SIM102).
- **WR-04 (fixed):** in `model_ranker.py`, collapsed the nested purpose-section check and replaced the `axis_weights` if/else with a ternary (SIM102/SIM108).
- **IN-01 (fixed):** removed the dangling comma line in the `_write_meta_catalog` test helper's `json.dump` call.

## Verification

- `ruff check` passes on every touched file.
- `python -m unittest tests.test_ai_kit_spec tests.test_ai_kit_usage_metrics tests.test_ai_kit_opencode_providers` ran 823 tests: OK.

## Out of scope (pre-existing)

- `skills/ai-kit-spec-review/ai_kit_spec/dispatch.py:158` SIM105. It predates Phase 16: it fails at the pre-fix tree as well.
- The `.pre-commit-config.yaml` ruff hook `files:` scope does not cover `skills/ai-kit-spec-review/ai_kit_spec/*.py`. This is why WR-02..WR-04 slipped through, and it is a candidate follow-up todo.
