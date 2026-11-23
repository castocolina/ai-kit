---
created: 2026-11-21T00:00:00.000Z
title: Review notes left open by phase 36
area: tooling
severity: minor
files:
  - .planning/phases/36-spec-config-as-the-hub/36-REVIEW.md
  - tests/fixtures/no_hardcoded_models_baseline.json
  - skills/ai-kit-spec-review/ai_kit_spec/lane_effort.py
  - skills/ai-kit-spec-review/ai_kit_spec/lane_settings.py
  - skills/ai-kit-spec-review/ai_kit_spec/role_orders.py
---

## Problem

The phase 36 code review left these items open by decision. None loses data or refuses a lane.

## Notes

- Baseline labels: 26 entries of `tests/fixtures/no_hardcoded_models_baseline.json` carry `"cleaned_by": "36"` for
  curated-config fixtures and tests (`tests/fixtures/curated_config_v2/**`, `tests/test_curated_config_*.py`,
  `tests/gsd_curated_eval.py`, `tests/test_gsd_curated_eval.py`) that phase 36 never touched. SPEC R8 makes a phase clean
  only the files it rewrites and puts the others out of scope, so the label names no real owner. The 27th entry,
  `ai_kit_spec/detection.py`, stays by contract (its hits are the native-selector seed list R7 keeps). Relabel the 26 to
  the phase that rewrites the curated-config fixtures, or to `backlog`, when that guard is next touched.
- pi listed ids: `lane_effort.offered_levels` treats a complete listed pi id that ends in `:<level>` as a name and offers
  levels, while `effort_form` at preview, probe and dispatch is called without `known_ids` and reads the suffix as a
  carried effort. Pass the listed ids through `spec_with_effort` and `probe_effort`, or stop offering levels for such an
  id. Phase 37 reworks the runner's effort path; fix it there.
- Duplicates: the control-character class is defined in `lane_settings`, `lane_data_use`, `lane_effort` and `usability`;
  the pool key pattern in `lane_settings.POOL_RX` and `lane_price`; `lane_order.JEV_ERROR` repeats
  `_ANSWER_REASONS["error"]`; `propose-lanes` rows carry both `class` and `class_label`; cursor bracket parsing exists in
  `lane_effort._carried` and `model_names._cursor_parts`. Merge them when those modules are next changed.
- `role_orders.ordered_lanes` (named by the phase contract) has no runtime caller; `quota.py`, `cli.py` and the execute
  adapter each filter `role_order` themselves. Use it there or remove it.
- `DEFAULT_POLICY` still holds `"ladder": []`, and `role_orders.role_order` falls back to an unfiltered flat ladder for a
  config without `orders` (hand-built test configs only).
