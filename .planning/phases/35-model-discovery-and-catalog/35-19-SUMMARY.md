---
phase: 35-model-discovery-and-catalog
plan: 19
subsystem: catalog
tags: [fetch, freshness, fetch-meta, raw-source-cache]

requires:
  - phase: 35-model-discovery-and-catalog
    provides: "35-04 models_config (KNOWN_SOURCES, SOURCE_KEYS, ModelsSettings), 35-14 CatalogSources.arena_data/arena_ok"
provides:
  - "catalog_fetch.py: FUTURE_SLACK_S, PlanFlags, read_fetch_meta, source_plan, raw_cache_path, read_raw_source, FetchedRaw, fetch_sources, updated_fetch_meta"
  - "tests/test_catalog_fetch.py: 10 tests (TestSourcePlan 5, TestFetchSources 5)"

key-files:
  created:
    - skills/ai-kit-spec-review/ai_kit_spec/catalog_fetch.py
  modified:
    - tests/test_catalog_fetch.py

requirements-completed: []

executor: "cross-AI lane: pi router-env/my-coding-lite, one run (560 s, status=ok exit=0, attempts=1, cycles=0)"
---

# Phase 35 Plan 19: per-source fetch freshness

One commit, `fa2aabb feat(35-19): add per-source catalog fetch freshness` (pre-fold); the commit hook ran 98/98 modules green.

## Accomplishments

- `read_fetch_meta` keeps only valid per-source records (finite number not below 0 and not more than 300 s in the future, bool `ok`, known
  sidecar key); an absent file, a legacy single-`last_fetched` sidecar and a non-dict `sources` read as `{}`.
- `source_plan` decides per source in the plan's order (disabled, no Artificial Analysis key, cached by its own `cache_days`, else fetch) with a
  visible reason for every skip; `schema_current` False or a record with `ok` False always fetches.
- `fetch_sources` fetches planned sources through injected fakes, writes the raw cache (`<catalog dir>/sources/<key>.json`) for models.dev and
  Arena only, reuses it for a fresh source with its own time in `source_at`, reports `raw data not cached` (source not answered, cached facts
  kept) when a fresh source has no readable raw cache, and never raw-caches Artificial Analysis.
- `updated_fetch_meta` keeps a failed source's previous `last_fetched` with `ok` False, sets a fetched-ok source to now and leaves cached ones.

## Deviations and notes for the code review

- No deviation from the plan; no file outside `files_modified` was touched. A failed raw-cache write (`cache_write_json`) is not reported in the
  source's result (the fetch still counts as ok); the next stale run simply finds no raw cache for that source.
- The Arena fetch passes `progress=lambda line: print(line, file=sys.stderr)` as the plan says; the tests' fake accepts it.

## Orchestrator verification (own runs, not the executor's claims)

- `python3 tools/run_unittest_parallel.py tests.test_catalog_fetch tests.test_arch_hardcoded_models tests.test_skill_text_history tests.test_arch tests.test_gate_scope`:
  exit 0, 5/5 modules (10, 14, 45, 109 and 62 tests).
- `make ruff`, `make pyright`, `make vulture`, `make pylint`: all rc 0.
- I read `catalog_fetch.py` whole against the plan text.
- Real-config audit (`audit_c2.py` against the wave 7 marker): a pi session log and the Claude host's own `history.jsonl` (this agent's session);
  nothing from the lane.

## Self-Check: PASSED
