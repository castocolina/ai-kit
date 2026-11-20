---
phase: 35-model-discovery-and-catalog
plan: 16
subsystem: catalog
tags: [tiers, classes, strengths, arena, artificial-analysis, jev-judges]

requires:
  - phase: 35-model-discovery-and-catalog
    provides: "35-05 model_names, 35-06 jev seams, 35-07 arena data shape, 35-08 catalog_bands, 35-14 catalog_facts.apply_facts"
provides:
  - "catalog_tiers.py: source_enabled, arena_index, arena_matches, aa_cuts, tier_fact, class_fact, strengths_fact, tier_facts"
  - "catalog_facts.apply_facts: second pass that merges the derived tier, class and strengths per entry, once per refresh"
  - "tests/test_catalog_tiers.py: 19 tests (TestTiers 14, TestTiersOutageAndCuts 5)"

key-files:
  created:
    - skills/ai-kit-spec-review/ai_kit_spec/catalog_tiers.py
  modified:
    - skills/ai-kit-spec-review/ai_kit_spec/catalog_facts.py
    - tests/test_catalog_tiers.py

requirements-completed: []

executor: "cross-AI lane: pi router-env/my-coding-lite, same CLI, provider and model for both runs: run 1 (lane-35-16, 1224 s, status=ok exit=0, attempts=1) wrote the plan; after my review found defects, run 2 (lane-35-16-fix, 556 s, status=ok exit=0, attempts=1) fixed them from a written fix-up prompt (tmp/run-2026-11-19/fixup-35-c4-c.md)"
---

# Phase 35 Plan 16: labeled tiers, classes and strengths

Two commits, `f052a03 feat(35-16): derive labeled catalog tiers and classes` (the plan) and
`cee9eef feat(35-16): keep cached facts through a source outage and cut Arena tiers on overall ratings` (the fix-up), both pre-fold; each commit hook ran 98/98
modules green.

## Accomplishments

- Tier: Artificial Analysis decides when the entry has `scores.intelligence_index` and AA answered; else Arena `overall` (effort rows give
  `by_effort`, otherwise the note `effort not distinguished`). Cuts are quartiles over that source's rows of this refresh; every tier fact is
  stamped with its deciding source's own time (`source_at`), labeled judged with confidence rule.
- Names reach Arena through `model_names.resolve_many`; the name judge sees one batch of non-router entries; a judged match adds `match`
  and `match_confidence` to the tier fact; no judge or no answer leaves the entry without Arena facts.
- Class: `catalog_bands.class_for` over the tier, the coding edge (Arena coding minus overall, else the AA coding minus intelligence index),
  the cost band and AA tokens per second; its `inputs` list every source that fed it (tier source, edge source, cost band source, AA for tokens
  per second). An `unknown` class with no measured field goes to the class judge in one call. Router entries are skipped; strengths come
  from Arena only.
- Source rules in `apply_facts`: a disabled source removes its facts and every fact whose `inputs` hold it; a derived fact is not written while the
  existing fact of that name depends on a source that is enabled but did not answer (tier, class and strengths stay).

## Deviations and notes for the code review

- My review of run 1 (probes `tmp/run-2026-11-19/probe-tiers-cuts.py` and `probe-tiers-outage.py`) found six defects, all fixed in run 2 with tests:
  Arena cuts were computed over every category instead of `overall` (a model set tiered light x4, capable x4 instead of light, light, capable,
  capable, strong, strong, frontier, frontier); an Arena-decided tier of an entry with cached AA scores carried the AA time; an Arena outage
  overwrote the cached class (flagship became general); class `inputs` missed the tier source when no coding edge existed; router entries went
  through name matching; and a module-wide pylint disable of too-many-locals, branches and statements (plus an unused import) hid a 125-line
  `tier_facts`. The outage rule in `apply_facts` is one rule over `source` and `inputs` and replaces two ad-hoc filters.
- `tests.test_catalog_tiers` has 19 tests, not the 14 of the plan's acceptance line: the five new ones are `test_arena_cuts_use_overall_ratings_only`,
  `test_arena_outage_keeps_class_tier_and_strengths`, `test_tier_time_is_the_deciding_sources_time`, `test_class_inputs_name_the_tier_source` and
  `test_router_entries_are_not_matched`.
- Open design question for the orchestrator (not in the plan): when the rule gives `unknown` and no class judge answers this run, a cached
  jev-judged class of the entry is overwritten by `unknown`, because jev is not one of the three sources of the outage rule.
  - Resolved: owner-orchestrator decision (plan 35-03, verified records are kept) and fix-up commit `922c475 fix(35-16): keep a cached jev class when no class judge answers`: `tier_facts` drops the derived class for such an entry, so the cached class stays unchanged (the schema has no stale marker); `test_cached_judged_class_survives_a_refresh_without_a_judge_answer` covers absent and invalid judge answers.
- `_aa_edge` and `_edge` narrow with `assert ... is not None` after a numeric check (the rule of this wave's gate notes allows it; an explicit check
  would be cleaner). The only remaining pylint disable is `protected-access` for the plan-named `catalog_bands._num`.
- Both runs of this plan carried a time-budget note in the prompt (plan 15's first run, which hit the 1800 s deadline in its commit hook, had none).
- No file outside the plan's `files_modified` was touched.

## Orchestrator verification (own runs, not the executor's claims)

- After the fix-up: `python3 tools/run_unittest_parallel.py tests.test_catalog_tiers tests.test_catalog_build_sources tests.test_ai_kit_spec tests.test_arch_hardcoded_models tests.test_skill_text_history tests.test_arch tests.test_catalog_bands tests.test_catalog_names tests.test_catalog_jev_names`:
  exit 0, 9/9 modules (19, 18, 693, 14, 45, 109, 15, 17 and 13 tests).
- `make ruff`, `make pyright`, `make vulture`, and pylint over `catalog_tiers.py` and `catalog_facts.py`: all Passed.
- Both probes now agree with the plan (tiers from overall cuts; cached flagship class, tier and strengths kept through an Arena outage).
- I read `catalog_tiers.py` whole (before and after the fix-up) and both `catalog_facts.py` diffs.
- Real-config audit (`audit_c2.py` against the wave 6 marker): only pi session logs and the Claude host's own plugin files
  (`.ponytail-active`, `ponytail-modes`, `daemon.status.json`); nothing from the lane.

## Self-Check: PASSED
