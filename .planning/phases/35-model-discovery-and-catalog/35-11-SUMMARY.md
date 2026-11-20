---
phase: 35-model-discovery-and-catalog
plan: 11
subsystem: catalog
tags: [optional-sources, seed-rows, web-names, sanitizer, labels]

requires:
  - phase: 35-model-discovery-and-catalog
    provides: "35-01 stub test modules; 35-02 hardcoding guard"
provides:
  - "optional_sources.py: SeedRow, SEED_ROWS, seed_provider, seed_candidates, MODEL_ID_RX, sanitize_name, WEB_QUERY_TEMPLATE, web_query, ingest_web_file, STORE_NAME, store_path, SOURCE_LABELS, record_names, LABEL_ORDER, strongest, optional_candidates"
  - "tests/test_catalog_optional_sources.py: 13 tests (TestSeedAndWeb and the hostile-text, query, label-order and refusal tests)"

key-files:
  created:
    - skills/ai-kit-spec-review/ai_kit_spec/optional_sources.py
  modified:
    - tests/test_catalog_optional_sources.py

requirements-completed: []

executor: "cross-AI lane: pi router-env/my-coding-lite, one run (569 s, status=ok exit=0)"
---

# Phase 35 Plan 11: optional model-name sources

One commit, `ae16fbf feat(35-11): add labeled optional model sources` (the commit hook passed on the executor's run).

## Accomplishments

- Seed rows (`claude`, `copilot`) are data with a `seed, unverified` label under a `model-example:` marker. `seed_provider` returns the claude
  row's provider when it is a key of the models.dev data, and for copilot the single provider key holding the token `copilot` (zero or several
  keys give None).
- `sanitize_name` strips ANSI escapes and control characters and keeps only names that fit `MODEL_ID_RX`; an instruction sentence or a
  non-string is dropped.
- `web_query` builds the one fixed query for a runtime in `KNOWN_CLIS` only; `ingest_web_file` accepts an agent-written JSON file only when
  the query equals that template, the url is https and the date is `YYYY-MM-DD`; names are labeled `web, unverified`.
- `record_names` refuses any `verified` label, unknown source or spoofed label, writes nothing on refusal and writes atomically through
  `cache_write_json`; `strongest` ranks labels verified, host listing, interactive view, web, seed; `optional_candidates` merges one name from
  several sources into one candidate that keeps every source record (the contract of plans 20 and 23).

## Deviations and notes for the code review

- The claude seed row's provider cell holds a literal provider id, the one exception the plan allows (it moves the value of
  `catalog_build._FIRST_PARTY_PROVIDER_BY_CLI["claude"]` into labeled seed data); the guard module passes. The plan said the row copies that
  value; the two copies are not tied by a test, so a later change of one does not change the other.
- The module docstring names pane names as a source but `optional_sources.py` has no reader for them (plan 17's herdr reader is the user).
- No file outside the plan's `files_modified` was touched.

## Orchestrator verification (own runs, not the executor's claims)

- `python3 tools/run_unittest_parallel.py tests.test_catalog_optional_sources tests.test_arch_hardcoded_models tests.test_arch`: exit 0, 3/3
  modules (13, 12 and 109 tests).
- `make ruff`, `make pyright`, `make vulture` and `uv run pre-commit run pylint --files skills/ai-kit-spec-review/ai_kit_spec/optional_sources.py`:
  all Passed (evidence under `tmp/run-2026-11-19/chk-35-11/`).
- I read the whole new module: `record_names` validates before any write, `web_query` refuses ids outside `KNOWN_CLIS`, `strongest` keeps the
  first of equal labels.
- Real-config audit (`audit_c2.py` against the wave marker): nothing unexpected; only pi session logs are newer.

## Self-Check: PASSED
