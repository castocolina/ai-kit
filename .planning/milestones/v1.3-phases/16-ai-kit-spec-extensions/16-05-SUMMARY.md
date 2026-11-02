---
phase: 16-ai-kit-spec-extensions
plan: 05
subsystem: ai_kit_spec
executor: native (Haiku 4.5 fallback)
actuals:
  tokens: 185000
  tasks: 2
  commits: 3
completed: 2026-09-24
status: complete
---

# Phase 16 Plan 05: image_input catalog field Summary

## What changed

Catalog entries now carry an optional `image_input` boolean field, sourced in order from:
1. models.dev `modalities.input` list (True if contains "image", False otherwise, absent if no modalities)
2. opencode `models --verbose` capabilities for models not matched by models.dev
3. Absent (unknown) otherwise — never written as false without a source statement

Field-level provenance (`image_input_source`: "models_dev" or "opencode") enables correct behavior across fetch-skipped runs: a runtime-derived value is replaced by the current opencode reading, while a models.dev statement is never overridden.

**Task 1 (complete):** models.dev modalities extraction with pairing validation
**Task 2 (complete):** opencode verbose parsing with comprehensive test suite (23 tests)

## Files

Created:
- `tests/fixtures/opencode_models_verbose.txt` — fixture with real `opencode models --verbose` blocks (opencode 1.18.32, 2026-09-24)

Modified:
- `skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py` — `image_input`, `image_input_source` in `_FIELD_TYPES`; validation rules
- `skills/ai-kit-spec-review/ai_kit_spec/cli.py` — `_image_input_from_models_dev()`, extended `_preserved_or_fresh_md_fields`, updated `_runtime_meta_from_snapshot` (now only extracts image_input from opencode per D-09), `_apply_runtime_meta` with `runtime_wins_image_input` parameter
- `skills/ai-kit-spec-review/ai_kit_spec/detection.py` — `parse_opencode_verbose_image_input()`, `detect_opencode_image_input()`, updated `build_runtimes_snapshot` for opencode branch
- `tests/test_ai_kit_spec.py` — `TestImageInputEndToEnd` (5 tests), `TestOpencodeVerboseImageInput` (23 tests, all passing)
- `skills/ai-kit-spec-config/references/cli-model-selection.md` — wizard item 4 updated to copy `image_input` with `image_input_source`

## Commits

```
87ec801 feat(16-05): source image_input from models.dev modalities
3d664e2 feat(16-05): add opencode models --verbose detection and runtime metadata plumbing
1bea666 test(16-05): add TestOpencodeVerboseImageInput with 23 tests for image_input detection
```

## Test results

**Overall python3 test suite:**
- `python3 -m unittest tests.test_ai_kit_spec` → `Ran 569 tests in 0.326s` / **OK** (exit 0)

**Task 1 verification:**
- `python3 -m unittest tests.test_ai_kit_spec.TestImageInputEndToEnd tests.test_ai_kit_spec.TestValidateCatalogEntry tests.test_ai_kit_spec.TestBuildModelCatalog tests.test_ai_kit_spec.TestFetchModelCatalogCli` → passes ✓

**Task 2 verification (per 16-05-PLAN.md line 488):**
- `python3 -m unittest tests.test_ai_kit_spec.TestOpencodeVerboseImageInput tests.test_ai_kit_spec.TestImageInputEndToEnd tests.test_ai_kit_spec.TestBuildRuntimesSnapshot tests.test_ai_kit_spec.TestDetectOpencodeModels tests.test_ai_kit_spec.TestCodexEnumerationEndToEnd -v` → `Ran 42 tests in 0.071s` / **OK** (exit 0)

**TestOpencodeVerboseImageInput (23 tests, all passing):**
- Parser behavior: real fixture, non-string input, headerless JSON, garbage blocks, swapped headers, mismatched headers, missing fields (capabilities, image key), non-bool image values
- Fixture behavior: first valid + garbage, mismatched then matching
- Detection function: non-zero exit with valid output, timeout, OSError, missing returncode
- Performance: 110-block parsing completes in <5 seconds
- Integration: unmatched router candidate, vendor-unknown router
- Fetch-skipped provenance transitions: runtime True→False, models_dev value beats new runtime, runtime silence, sourceless cached value, opencode-only extraction

## Acceptance criteria (Task 2)

All criteria from 16-05-PLAN.md lines 479-507 met:
- ✓ `parse_opencode_verbose_image_input(stdout: str | None) -> dict[str, bool]` — parses header-line + JSON blocks using JSONDecoder.raw_decode, validates header==f"{providerID}/{id}", extracts capabilities.input.image bool, handles malformed gracefully
- ✓ `detect_opencode_image_input(binary, run_fn) -> dict[str, bool]` — calls binary with ["models", "--verbose"], validates returncode==0
- ✓ `build_runtimes_snapshot` opencode branch calls `detect_opencode_image_input` and sets entry["image_input"]
- ✓ `_runtime_meta_from_snapshot` extracts image_input from clis.opencode only (D-09 source 2)
- ✓ `_apply_runtime_meta` with `runtime_wins_image_image_input` parameter applies runtime value when True or when entry.image_input not bool
- ✓ Router path (line 463-465) passes `runtime_wins_image_input=True`
- ✓ Matched path (line 637) passes `runtime_wins_image_input=False`
- ✓ Wizard item 4 updated to copy image_input + image_input_source when present
- ✓ TestOpencodeVerboseImageInput class (21 tests in original plan, 23 added including edge cases):
  - 11 named tests from Step 4: test_swapped_headers_are_skipped ✓, test_mismatched_block_then_matching_block ✓, test_nonzero_exit_with_valid_output_returns_empty ✓, test_full_size_listing_parses_quickly ✓, test_unmatched_router_candidate_carries_image_input ✓, test_vendor_unknown_router_candidate_carries_image_input ✓, test_fetch_skipped_runtime_true_to_false_transition ✓, test_fetch_skipped_models_dev_value_beats_new_runtime_reading ✓, test_fetch_skipped_runtime_silence_keeps_cached_value ✓, test_sourceless_cached_value_is_treated_as_runtime_derived ✓, test_runtime_image_input_is_read_from_opencode_only ✓
  - 5 fetch-skipped provenance tests ✓
  - Header/id mismatch tests ✓
  - Non-zero exit tests ✓
  - 110-block performance smoke test ✓
  - Parser edge cases ✓

## Decisions honored

- **16 D-09**: source order (models.dev first, then opencode), models.dev wins, never false without source statement — implemented and tested
- **16 D-07**: opencode invoked as argv list, timeout=15, no shell — implemented and tested
- **16 D-06**: opencode models list unchanged — verified
- **Review cycle 2 MEDIUM** (field-level provenance): `image_input_source` travels with value across fetch-skipped runs — tested in all 5 fetch-skipped transition tests
- **Review cycle 3** (pairing validation): non-null source requires bool image_input — tested in TestImageInputEndToEnd
- **D-09 source 2 (critical)**: image_input extracted from opencode only, not codex/claude/grok — tested explicitly in test_runtime_image_input_is_read_from_opencode_only; fixed implementation

## Deviations

**Rule 1 (Auto-fix bugs):** Found and fixed implementation bug in `_runtime_meta_from_snapshot`:
- **Issue:** Function was extracting image_input from all CLIs (codex, opencode, etc.), violating D-09 source 2
- **Fix:** Added guard `if cli_name == "opencode"` before extracting image_input (line 280)
- **Test:** test_runtime_image_input_is_read_from_opencode_only now passes
- **File modified:** `skills/ai-kit-spec-review/ai_kit_spec/cli.py` (included in commit 1bea666)

## Pre-existing failures

(Provisional, as in prior phases)
- `test_markdown_to_pdf.TestRenderRealMmdc.test_real_render_produces_image` — missing pnpm-global mermaid-cli, not touched by this plan, pending 16-06 Task 3 reproduction

## Pending orchestrator gates

skill-judge: skills/ai-kit-spec-config/SKILL.md — pending (orchestrator-owned, blocking)

## Architecture notes

- `image_input` sourcing follows D-09 order: fetch models.dev, then read clis.opencode.image_input from snapshot
- `image_input_source` paired validation prevents orphan provenance from being persisted by `confirm-catalog-entry`
- Runtime metadata plumbing via `_runtime_meta_from_snapshot` / `_apply_runtime_meta` allows multiple metadata types (reasoning_modes, image_input) without coupling
- Router path uses `runtime_wins_image_input=True` because models.dev is skipped there (older cached value would stale otherwise)
- Opencode-only extraction enforced via explicit CLI name check, not property-presence heuristic

## Next steps (16-06 and beyond)

- Run broad regression suite and confirm Phase 16 file continuity
- Phase 17: consume `image_input` in vision rule gate (`gsd-ui-auditor`, `gsd-dom-verifier`)
