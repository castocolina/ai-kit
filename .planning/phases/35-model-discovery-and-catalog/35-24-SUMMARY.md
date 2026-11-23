---
phase: 35-model-discovery-and-catalog
plan: 24
subsystem: catalog
tags: [hardcoding-guard, baseline, seed-rows, provider-hint]

requires:
  - phase: 35-model-discovery-and-catalog
    provides: "35-02 guard and baseline, 35-10 and 35-11 seed rows, 35-13 docs, 35-14 build, 35-15 detection"
provides:
  - "catalog_build._fixed_seed_provider: provider hint read from optional_sources.SEED_ROWS (the private _FIRST_PARTY_PROVIDER_BY_CLI dict is gone)"
  - "baseline: catalog_build.py, model_catalog.py and model_matcher.py entries removed; detection.py kept as cleaned_by 36 with only its deciding-list hits"
  - "tests/test_catalog_build_sources.py: TestSeedHint (1 test, 19 tests in the module)"

key-files:
  modified:
    - skills/ai-kit-spec-review/ai_kit_spec/detection.py
    - skills/ai-kit-spec-review/ai_kit_spec/catalog_build.py
    - skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py
    - skills/ai-kit-spec-review/ai_kit_spec/model_matcher.py
    - tests/fixtures/no_hardcoded_models_baseline.json
    - tests/test_catalog_build_sources.py

requirements-completed: []

executor: "cross-AI lane: pi router-env/my-coding-lite, one run (727 s, status=ok exit=0, attempts=1, cycles=0)"
---

# Phase 35 Plan 24: clean the rewritten code files of hardcoded names

One commit, `38058df refactor(35-24): source provider hints from seed rows` (pre-fold); the commit hook ran 98/98 modules green. The executor's first
`make pyright` failed on optional narrowing in the new test; it fixed that before committing.

## Accomplishments

- Docstring and comment examples in the four files use `fake/placeholder-model-1`, `placeholder-model-1` or generic words; no value changed.
  detection.py gained the plan's comment above `RUNTIMES`; the claude `native_selectors` and `CLAUDE_FALLBACK_MODEL_IDS` values are unchanged.
- `_fixed_seed_provider(runtime)` returns the `models_dev_provider` of the runtime's `SEED_ROWS` row (claude has one; copilot's is None; no
  row gives None), so matching is unchanged; `_anthropic_model_ids` and `_fetch_source_matches` use it.
- The baseline lost the three cleaned files; detection.py stays with `cleaned_by` 36 and eight deciding-list hit strings (four selectors, four
  fallback ids).
- Executor's scratch runs: `hits.py` printed the 8 deciding-list hits only; `names_check.py` printed the four fallback ids only.

## Deviations and notes for the code review

- No file outside `files_modified` was touched; the grok row, `build_grok_command` and the grok-worker agent were not touched.
- `_anthropic_model_ids` keeps its old name although it now reads the fixed seed provider of claude (a rename is Phase 36's, with the gating work).
- Some reworded docstrings lost real context (for example "`model_creator.name` (OpenAI, xAI)" became "its creator name"); the meaning holds.

## Orchestrator verification (own runs, not the executor's claims)

- `python3 tools/run_unittest_parallel.py tests.test_arch_hardcoded_models tests.test_catalog_build_sources tests.test_ai_kit_spec tests.test_catalog_listing tests.test_ai_kit_spec_runtimes_table tests.test_runtime_list_drift tests.test_skill_text_history tests.test_arch tests.test_cross_ai_skill_text`:
  exit 0, 9/9 modules (14, 19, 693, 24, 58, 10, 45, 109 and 30 tests).
- `python3 tmp/p35/24/names_check.py` prints only the four fallback ids of `detection.py:144-145`.
- `make ruff`, `make pyright`, `make vulture`, `make pylint`: all rc 0.
- I read the diff of the four code files and the baseline whole; `SEED_ROWS` holds fixed providers for claude only (copilot None).
- Real-config audit (`audit_c2.py` against the wave 7 marker): three pi session logs; the Claude host's own `history.jsonl` and `jobs/*`
  (this agent's session); nothing from the lane.

## Self-Check: PASSED
