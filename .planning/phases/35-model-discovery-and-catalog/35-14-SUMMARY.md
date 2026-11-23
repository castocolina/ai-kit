---
phase: 35-model-discovery-and-catalog
plan: 14
subsystem: catalog
tags: [catalog-facts, router-alias, models-dev, name-resolution]

requires:
  - phase: 35-model-discovery-and-catalog
    provides: "35-03 labels (fact), 35-05 model_names (split_effort, resolve_many, known_ids_from_models_dev), 35-08 catalog_bands, 35-10 model_records"
provides:
  - "catalog_facts.py: ROUTER_PREFIX, ROUTER_SOURCE, FactsInputs, router_alias_key, router_alias_entry, md_facts, runtime_updates, apply_facts, resolve_candidates"
  - "catalog_build.py: CatalogSources.arena_data and arena_ok, router-env first branch, build_model_catalog(..., facts_inputs=None), match_name and unresolved handling"
  - "tests/test_catalog_build_sources.py: 18 tests (TestFactsCore 4, TestFactsRuntimeRows 10, TestNameResolution 4)"

key-files:
  created:
    - skills/ai-kit-spec-review/ai_kit_spec/catalog_facts.py
  modified:
    - skills/ai-kit-spec-review/ai_kit_spec/catalog_build.py
    - tests/test_catalog_build_sources.py
    - tests/test_ai_kit_spec.py

requirements-completed: []

executor: "cross-AI lane: pi router-env/my-coding-lite, one run (1310 s, status=ok exit=0, attempts=1, cycles=0)"
---

# Phase 35 Plan 14: labeled catalog facts and host-name resolution

One commit, `93c964a feat(35-14): apply labeled catalog facts` (pre-fold). The executor's first commit-hook attempt failed on ruff's
`Callable` import rule (now `collections.abc.Callable`); one test run hit a disk-quota error and passed again with the repository's
`tmp/` as TMPDIR; the final hook ran 98/98 modules green.

## Accomplishments

- `router-env/` ids become assumed router entries with no models.dev or Artificial Analysis lookup (D-15): key `router-env/<base>` through
  `split_effort`, so `#high` or `:high` variants share one identity; the class fact is written in `apply_facts` with `inputs.now`;
  a heuristic field listed in `heuristic_confirmed` keeps the user's value.
- `md_facts` writes modalities, reasoning and status as measured facts from models.dev and the cost band as a judged fact with confidence
  `rule` (one priced model gives `unknown`); `identity` carries models.dev's `canonical_model_id` without changing the cache key (Amend-2).
- `runtime_updates` gives each runtime row its `efforts` (name-parsed plus the listing's levels, sorted) and `last_seen` (the listing's own
  `listed_from.at`, only when `listing == "ok"` and the model is in the listed `models`), and the `match` fact for judged or unmatched names.
- `resolve_candidates` sends host names through `model_names.resolve_many` before the models.dev match: an exact bare id, or one judged by
  jev, becomes the candidate's `match_name`; an unmatched name is marked `unresolved` and `_fetch_source_matches` returns no match for it
  (the legacy fuzzy matcher never decides it). Ambiguous bare ids stay out of the pool.
- An enabled-but-down source keeps its cached facts; a source missing from `[models] sources` has its models.dev facts removed.

## Deviations and notes for the code review

- Existing tests changed to the D-15 contract, as plan step 9 allows:
  `test_unmatched_candidate_carries_heuristic_fields_for_wizard_confirmation` (a router-env alias is no longer "unmatched": it is an entry
  with is_router and fallback_quota), `test_heuristic_correction_survives_a_later_catalog_rebuild` (the seeded entry gains
  `heuristic_confirmed: ["is_router"]`) and `test_unmatched_router_candidate_carries_image_input` (reads the catalog entry instead of an
  unmatched record).
- Beyond the plan text, `_fetch_source_matches` also passes the resolved `match_name` to `match_artificial_analysis` (the plan names only
  `match_models_dev`); the two matchers now see the same name for a candidate.
- `apply_facts` is only called from `build_model_catalog` when `facts_inputs` is given; `rg facts_inputs skills tools` finds only
  `catalog_build.py` and `catalog_facts.py`, so no production caller passes it yet (later plans wire it) and this plan changes no live build.
- No file outside the plan's `files_modified` was touched.

## Orchestrator verification (own runs, not the executor's claims)

- `python3 tools/run_unittest_parallel.py tests.test_catalog_build_sources tests.test_ai_kit_spec tests.test_catalog_names tests.test_arch_hardcoded_models tests.test_arch tests.test_skill_text_history`:
  exit 0, 6/6 modules (18, 693, 17, 14, 109 and 45 tests).
- `make ruff`, `make pyright`, `make vulture`, and pylint over `catalog_facts.py` and `catalog_build.py`: all Passed.
- I read `catalog_facts.py` whole, the `catalog_build.py` and `tests/test_ai_kit_spec.py` diffs and the first test classes.
- Real-config audit (`audit_c2.py` against the wave marker): one pi session log; the only unexpected files were the Claude host's own
  `.credentials.json` (13:01), `daemon.log` and `history.jsonl` (the orchestrating Claude sessions: token refresh, daemon, prompt history; the
  lane is a pi run with `AI_KIT_REFUSE_REAL_HOME=1` and has no reason to touch them; contents not read).

## Self-Check: PASSED
