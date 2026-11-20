---
phase: 35-model-discovery-and-catalog
plan: 03
subsystem: catalog
tags: [catalog-labels, schema-4, validators, fixtures]

requires:
  - phase: 35-model-discovery-and-catalog
    provides: "35-01 deep-merge seam and stub test modules; 35-02 hardcoding guard"
provides:
  - "skills/ai-kit-spec-review/ai_kit_spec/catalog_labels.py: LABELS, UNKNOWN, now_iso, fact, fact_problem, show"
  - "model_catalog.py: CATALOG_SCHEMA_VERSION = 4, USABILITY_STATES, _validate_facts, _validate_runtime_records (+ _usability_problem, _context_problem)"
  - "tests: TestCatalogLabels (4), TestSchemaFourFields and TestSchemaFourUpgrade in tests/test_catalog_schema4.py (14 tests in the module)"

key-files:
  created:
    - skills/ai-kit-spec-review/ai_kit_spec/catalog_labels.py
  modified:
    - skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py
    - tests/test_catalog_labels.py
    - tests/test_catalog_schema4.py
    - tests/test_ai_kit_spec.py
    - tests/test_ai_kit_spec_runtimes_table.py
    - tests/test_ai_kit_spec_runner_dispatch.py
    - tests/test_cross_ai_runner_e2e.py
    - tests/fixtures/curated_config_v2/model-catalog.json
    - tests/fixtures/model_catalog_null_index.json

requirements-completed: [HUB-03, HUB-02]

executor: "cross-AI lane: pi router-env/my-coding-lite, one run (1635 s, status=ok exit=0)"
---

# Phase 35 Plan 03: label vocabulary and schema 4

One commit, `c1e240e feat(35-03): add labeled facts and schema 4`. Per the executor's report, the hook refused the first two commit
attempts (ruff, then a staged test) and the third passed with 165/165 modules.

## Accomplishments

- `catalog_labels.py`: one label vocabulary (measured, judged, assumed, user-stated), `fact` builder, `fact_problem` validator
  (judged needs `confidence` of `"rule"` or a number from 0 to 1) and `show` (`unknown` for a missing value).
- `model_catalog.py`: schema 4. Top-level `facts`, `identity`, `confirmed_fields` and per-runtime `usability`, `context`, `efforts`,
  `last_seen`, `listed_from`, `ctx_note`, `match` are validated; usability accepts only the four states; a context value must be
  an int above zero or None; a confirmed field needs `by`, `at`, `note`.
- A v3 cache is stale (`catalog_schema_is_current` accepts 4 and 5, refuses 3) and its confirmed fields and verified records
  survive both `split_catalog_meta` and a fresh merge (`TestSchemaFourUpgrade`).
- Schema-3 expectations follow the constant: tests import `CATALOG_SCHEMA_VERSION`, the two JSON fixtures say 4,
  `test_current_schema_is_returned_unrenamed` replaces `test_schema_3_is_returned_unrenamed`; the 18 Artificial Analysis-shaped runs
  in `tests/test_ai_kit_spec.py` carry the `# synthetic: Artificial Analysis shapes, invented values` marker line.

## Deviations and notes for the code review

- `_usability_problem` and `_context_problem` return a bool (the plan's wording left the return type open); the messages are
  built in `_validate_runtime_records`, as the plan states them.
- `_context_problem` narrows with `assert isinstance(context, dict)` after `fact_problem` returned None (pyright).
- No file outside the plan's `files_modified` was touched.

## Orchestrator verification (own runs, not the executor's claims)

- `python3 tools/run_unittest_parallel.py tests.test_catalog_labels tests.test_catalog_schema4 tests.test_ai_kit_spec
  tests.test_ai_kit_spec_runtimes_table tests.test_ai_kit_spec_runner_dispatch tests.test_gsd_curated_eval tests.test_arch_hardcoded_models`:
  exit 0, 7/7 modules (4, 14, 693, 58, 70, 321 and 12 tests).
- `uv run python tools/run_unittest_parallel.py tests.test_cross_ai_runner_e2e`: exit 0, 28 tests.
- `python3 tools/run_unittest_parallel.py --group arch`: exit 0, 2/2 modules (109 and 12 tests).
- `make ruff`, `make pyright`, `make vulture`: all Passed; `uv run pre-commit run pylint --files` over both modules: Passed.
- `rg -c "synthetic: Artificial Analysis shapes" tests/test_ai_kit_spec.py` prints 18. The six `schema_version 3` literals left in
  `tests/` are intended: two runtimes-snapshot cases (`test_ai_kit_spec.py` 2807, 2810; `RUNTIMES_SCHEMA_VERSION` is 7 and untouched),
  the new bad-list line (8917), the v3 cache and refusal cases in `test_catalog_schema4.py` (140, 161) and an unrelated curated-config
  plan message (`test_curated_config_plan_edit.py` 190).
- Real-config audit after the lane: no file changed under `~/.pi` (one session log), `~/.config/opencode` or `~/.cursor`; the changed
  files under `~/.claude/plugins`, `~/.claude/skills/synced` and `~/.codex` belong to the Claude host and to a codex app server of
  another project.

## Self-Check: PASSED
