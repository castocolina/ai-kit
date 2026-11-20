---
phase: 35-model-discovery-and-catalog
plan: 23
subsystem: catalog
tags: [web-query, record-web-names, herdr-names, optional-candidates, listed-from]

requires:
  - phase: 35-model-discovery-and-catalog
    provides: "35-11 optional names store, 35-17 herdr reader, 35-19 raw source cache, 35-22 catalog_cmds, 35-24 seed rows, 35-27 fetch-model-catalog, 35-28 catalog-report"
provides:
  - "catalog_cmds.py: cmd_web_query, cmd_record_web_names, cmd_herdr_names (commands web-query, record-web-names, herdr-names), optional_fetch_candidates, builder_candidates, attach_listed_from"
  - "cli.py: _run_fetch_catalog_build adds the stored optional names and seed rows of installed no-listing runtimes as discovered candidates (builder sees each pair once), then attaches every source record as listed_from on the matched runtime rows"
  - "cli.py: _claude_seed_provider() reads the claude provider from optional_sources.SEED_ROWS instead of a literal"
  - "tests/test_catalog_cmds.py: TestOptionalSourceCommands (3) and TestOptionalFetchCandidates (6)"

key-files:
  modified:
    - skills/ai-kit-spec-review/ai_kit_spec/catalog_cmds.py
    - skills/ai-kit-spec-review/ai_kit_spec/cli.py
    - tests/test_catalog_cmds.py

requirements-completed: []

executor: "cross-AI lane: pi router-env/my-coding-lite, one run (731 s, AIKIT-XAI status=ok exit=0 attempts=1 cycles=0)"
---

# Phase 35 Plan 23: optional names as commands and fetch candidates

One commit, `a8f5819 feat(35-23): ingest optional model candidates` (pre-fold); the commit hook ran 98/98 modules green.

## Accomplishments

- `web-query` prints the fixed query (an unknown runtime exits 2), `record-web-names` validates the agent-written file and stores its names labeled
  `web, unverified`, `herdr-names` runs the herdr reader only through `herdr_source.read_interactive_names` and records nothing when herdr is absent.
- `optional_fetch_candidates` yields, for every installed runtime whose listing is `none`, the stored names and (not for claude) the seed rows, each with
  the full `sources` list as `listed_from`; `builder_candidates` hands the builder each pair once; `attach_listed_from` puts every record on the
  catalog row after the build, so a duplicate pair keeps its records.
- `_claude_seed_provider()` replaces the `"anthropic"` literal in the two `canonical_key` calls of `_finalize_fetch_catalog_meta`.

## Notes for the code review

- `optional_fetch_candidates` dedupes with a dict keyed by (runtime, model_id): when the same pair appears twice the last record wins, but
  `optional_candidates` already merges its sources per name, so a duplicate can only come from the seed list; unmatched names are not catalog entries and
  stay in the store (catalog-report shows them).
- `_claude_seed_provider` uses `assert row.models_dev_provider is not None` to narrow the type for pyright.
- The `_optional_candidates_for_fetch` helper (a new cli.py function, not named in the plan) exists only to keep `_run_fetch_catalog_build` under
  pylint's max-locals; the plan's wiring is unchanged.
- The lane's report: an initial run failed on the fake pane's newline encoding and a hardcoding-guard match, pylint on too many locals in `cli.py` and ruff
  on import order; all fixed before the commit. No formatter was run (diff `+304 -4`).

## Orchestrator verification (own runs, not the executor's claims)

- `python3 tools/run_unittest_parallel.py tests.test_catalog_cmds tests.test_catalog_fetch tests.test_ai_kit_spec tests.test_catalog_optional_sources
  tests.test_catalog_herdr tests.test_arch_hardcoded_models tests.test_arch tests.test_skill_text_history tests.test_gate_scope tests.test_catalog_build_sources
  tests.test_curated_config_inventory tests.test_gsd_curated_eval`: exit 0, 12/12 modules (27, 17, 693, 13, 11, 14, 109, 45, 62, 19, 112 and 321 tests).
- `make ruff`, `make pyright`, `make vulture` rc 0; pre-commit pylint on `catalog_cmds.py` and `cli.py` rc 0.
- Read the whole diff of `catalog_cmds.py` and `cli.py`; the nine tests are named as the plan lists; acceptance names (`optional_fetch_candidates(`,
  `builder_candidates(`, `attach_listed_from(`, `_claude_seed_provider`) are in cli.py.
- Real-config audit (marker-c6-w11): only the host's own files and another agent's `.codex` logs and models cache; nothing from the lane.

## Self-Check: PASSED
