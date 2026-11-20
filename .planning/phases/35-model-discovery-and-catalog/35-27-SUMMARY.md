---
phase: 35-model-discovery-and-catalog
plan: 27
subsystem: catalog
tags: [fetch-model-catalog, per-source-fetch, arena, jev, attribution, publication-order]

requires:
  - phase: 35-model-discovery-and-catalog
    provides: "35-01 locked_catalog_update and rebase_on_current, 35-04 models settings, 35-06 jev judges, 35-14 facts inputs, 35-16 tiers, 35-18 attribution, 35-19 catalog_fetch"
provides:
  - "cli.py: fetch-model-catalog plans each source through catalog_fetch, fetches Arena through CliDeps.fetch_arena_fn, passes FactsInputs (source times, jev judges with --jev) to the build, stamps the schema after every build, publishes under the catalog lock with rebase_on_current, writes the per-source sidecar only after the catalog, prints arena_ok, sources and attribution"
  - "catalog_facts.resolve_candidates: a bare id that several providers list resolves to the runtime's seed provider (claude: 16 D-04 tie-break) instead of staying unmatched"
  - "tests/test_catalog_fetch.py: 17 tests (TestFetchCommand 7)"

key-files:
  modified:
    - skills/ai-kit-spec-review/ai_kit_spec/cli.py
    - skills/ai-kit-spec-review/ai_kit_spec/catalog_facts.py
    - tests/test_catalog_fetch.py
    - tests/test_ai_kit_spec.py
    - tests/gsd_curated_eval.py

requirements-completed: []

executor: "cross-AI lane: pi router-env/my-coding-lite, same CLI, provider and model for all six runs (272 s, 518 s, 349 s, 506 s, 180 s, 419 s; every run status=ok exit=0, attempts=1): run 1 wired the plan and stopped on the plan's own stop rule, runs 2 to 6 finished it from prompts with the orchestrator's diagnosis (tmp/run-2026-11-19/fixup-35-c5-c.md, extra-35-27-r4.md, fixup-35-c5-d.md, -e.md, -f.md)"
---

# Phase 35 Plan 27: fetch-model-catalog on per-source ages

One commit, `2c4648a feat(35-27): fetch-model-catalog by per-source age with Arena, jev and attribution` (pre-fold); the commit hook ran 165/165
modules green. The plan needed six lane runs; the cause of each is below because several are plan or tooling lessons for the code review.

## Accomplishments

- `_fetch_catalog_external_sources` reads `[models]` (`read_models_settings`), plans with `catalog_fetch.source_plan`, fetches or reuses the
  raw caches through `fetch_sources`, and returns `FetchedSources`; the sidecar is written only after the locked catalog update succeeded.
- `FactsInputs` carries the snapshot, settings, `now_iso()`, `source_at` and, with `--jev` only, the `jev_names` name and class judges.
- The output JSON keeps its keys and adds `arena_ok`, `sources` (a `{fetched, ok, reason}` record per source) and `attribution`
  (`attribution_lines(catalog_sources(<written catalog>))`); `fetch_skipped` is true only when no source was fetched.
- `tests/gsd_curated_eval.py` seeds the per-source sidecar, so the seeded fixed point still fetches nothing; `tests/test_ai_kit_spec.py` gets a
  no-network Arena fake at 31 `fetch_models_dev_fn=` call sites and `_fresh_meta()` for every old-shape sidecar seed.

## Deviations and notes for the code review

- Defects the plan text did not foresee, found by my own runs and fixed in this commit:
  - With `facts_inputs` passed, `resolve_candidates` left a bare id that models.dev lists under several providers out of its pool, so the claude
    candidates for such ids ended unmatched and the 16 D-04 anthropic tie-break was lost (3 existing tests failed). `_seed_provider_key` (the
    `SEED_ROWS` provider of the runtime, when its models.dev rows hold the id) now resolves them. The fix is in `catalog_facts.py`, which the
    plan did not list.
  - `locked_catalog_update` refuses an unreadable catalog; the old command replaced a corrupt file with the fresh build and
    `test_garbage_catalog_file_is_replaced_by_a_valid_fetch` pins that, so `_write_fetch_catalog_result` rewrites a non-dict file to `{}` first.
    This is a design choice (recovery over refusal) for the owner to confirm; a directory as catalog path still fails before the sidecar.
- Existing tests updated because their premise changed (plan Task 2 step 2 allows it; each named): `test_if_stale_skip_never_touches_the_fetch_freshness_marker`
  (plan-directed), `test_a_real_fetch_updates_the_freshness_marker_only_when_a_source_answered` (per-source sidecar record),
  `test_legacy_catalog_with_fresh_fetch_meta_is_refetched_and_stamped` (the entry is kept and enriched with facts, so the legacy fields are
  compared instead of the whole entry), `test_models_dev_down_stamps_schema_and_records_failure_so_next_run_refetches` (renamed; the schema is
  stamped after every build and a failed models.dev fetch is recorded ok false), `test_fetch_skipped_runtime_silence_keeps_cached_value` (the raw
  models.dev cache of run 1 is removed so the fresh source reaches run 2 as not answered, per 35-19) and
  `test_real_refresh_order_makes_a_non_fallback_id_scoreable_without_ttl_wait` (its Arena fake answers ok so step 2 leaves Arena fresh).
- The legacy-entry test shows a consequence of plan 35-21 worth a look: a refresh with an answering models.dev clears `ctx_window` of a runtime
  row whose window no source states (SPEC R6 wording), including a window that was cached from an older source.
- Process lessons: run 3 ran a formatter over `cli.py` and `tests/test_ai_kit_spec.py` (about 1900 lines of noise); I restored those two files
  and restarted with a formatter ban and a diff-size check (final diff: cli.py 102 lines, test_ai_kit_spec.py 96). A model-name literal I asked
  for in one test edit added a hit to the hardcoded-model baseline, which run 6 removed. Plan 27's own stop rule ended run 1 with the tree
  uncommitted and unlinted; the plan's verify list never named `tests.test_ai_kit_spec` before its Task 2.

## Orchestrator verification (own runs, not the executor's claims)

- `python3 tools/run_unittest_parallel.py tests.test_ai_kit_spec tests.test_curated_config_inventory tests.test_gsd_curated_eval tests.test_catalog_fetch tests.test_arch_hardcoded_models tests.test_catalog_build_sources tests.test_catalog_tiers tests.test_catalog_context tests.test_catalog_stale tests.test_skill_text_history tests.test_arch tests.test_gate_scope`:
  exit 0, 12/12 modules (693, 112, 321, 17, 14, 19, 20, 14, 15, 45, 109 and 62 tests).
- `make ruff`, `make pyright`, `make vulture`, `make pylint`: all rc 0.
- I read the `cli.py` and `catalog_facts.py` diffs and the `test_ai_kit_spec.py` diff whole; probes `tmp/run-2026-11-19/debug-claude-fetch.py` and
  `debug-narrowed.py` (my checks, not product code) showed the claude tie-break regression and that the original assertions still hold.
- Real-config audit (`audit_c2.py` against the wave 8 marker): eight pi session logs and the Claude host's own files (`.ponytail-active`, `daemon*`,
  `jobs/*`, `ponytail-modes`); nothing from the lanes.

## Self-Check: PASSED
