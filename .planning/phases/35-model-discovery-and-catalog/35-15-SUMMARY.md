---
phase: 35-model-discovery-and-catalog
plan: 15
subsystem: catalog
tags: [runtimes-snapshot, listing-provenance, detect-runtimes, schema-8]

requires:
  - phase: 35-model-discovery-and-catalog
    provides: "35-10 opencode model_records, 35-12 usability, 35-14 catalog_facts (last_seen reads listing and listed_from)"
provides:
  - "detection.py: RUNTIMES_SCHEMA_VERSION = 8, _RecordingRun, _host_version, detect_unlisted_runtimes, codex context_window and max_context_window maps"
  - "cli.py: detect-runtimes --runtime ID (dest extra_runtime)"
  - "tests/test_catalog_listing.py: TestListingProvenance, 12 tests"

key-files:
  modified:
    - skills/ai-kit-spec-review/ai_kit_spec/detection.py
    - skills/ai-kit-spec-review/ai_kit_spec/cli.py
    - tests/test_catalog_listing.py
    - tests/test_ai_kit_spec.py
    - tests/test_ai_kit_spec_runtimes_table.py
    - tests/test_ai_kit_spec_routing.py
    - tests/fixtures/curated_config_v2/runtimes.json

requirements-completed: []

executor: "cross-AI lane: pi router-env/my-coding-lite; run 1 (lane-35-15) wrote all code and tests and was in the commit hook when the 1800 s deadline hit (status=timeout exit=124 elapsed=1710 s, nothing committed, 7 files staged); run 2 (lane-35-15-r2, 370 s, status=ok exit=0, same CLI, provider and model) only re-ran the verify commands and committed"
---

# Phase 35 Plan 15: where each runtime listing came from, and how it went

One commit, `988b626 feat(35-15): record where each runtime listing came from and how it went` (pre-fold); its commit hook ran 165/165 modules
green (17/17 under uv).

## Accomplishments

- Every installed runtime row says `listing`: `ok`, `failed` or `none`. A listing that ran carries `listed_from {command, version, at}`
  (command as run, the host's `--version` first line control-free, redacted and cut to 80 characters, the UTC run time); pi's command ends with
  `(rpc get_available_models)`. A failed listing records `listing_error` (`exit <rc>: <first stderr line>`, control characters removed, key shapes
  redacted, 200 characters) and writes no `models`. A listing that succeeds with no models is `ok` with `models: []`. claude and copilot are
  `none`, so a catalog-backed claude list is never listing proof.
- codex rows carry `context_window` and `max_context_window` maps (exact integers only, ids with a value only).
- `detect-runtimes --runtime ID` (repeatable) shows a runtime missing from the table as `{installed, path, listing: none, note: installed, no listing}`
  (an id must match `[a-z][a-z0-9-]{0,30}`; the binary is only located, never run); a named runtime skips the `--if-stale` early return.
- `RUNTIMES_SCHEMA_VERSION` is 8, so every cached snapshot re-detects once; the seeded curated-config fixture moves to 8.

## Deviations and notes for the code review

- `tests/test_ai_kit_spec_routing.py` is outside the plan's `files_modified`: the fake run of
  `TestOpencodePrivateDirUsesTheGivenEnv` reads `kwargs["cwd"]` on every call, and the new `--version` probe passes no `cwd`; the fake now
  answers that probe first (two lines added).
- `tests/test_ai_kit_spec.py` changes beyond the plan text: `test_version_predicate_rejects_non_int_values` now treats 8 and 9 as good (7 is no
  longer current); schema 7 itself is not added to its `bad` list, so "a v7 cache is stale now" has no direct assertion there (the
  `TestRuntimesSchemaVersion` cache tests cover the re-detect path).
- The code review may also look at `_RecordingRun.__call__`, which catches `Exception` only to remember it and re-raise.
- Run 1 timed out because the code, the tests and the checks used about 25 minutes and the commit hook needed more than the rest of the 1800 s;
  the staged tree was verified by me before run 2 (below), and run 2 changed no file.

## Orchestrator verification (own runs, not the executor's claims)

- On the staged tree after run 1, identical to commit `988b626` (same seven paths, 297 insertions and 40 deletions):
  `python3 tools/run_unittest_parallel.py tests.test_catalog_listing tests.test_ai_kit_spec tests.test_ai_kit_spec_runtimes_table tests.test_ai_kit_spec_routing tests.test_arch_hardcoded_models tests.test_gsd_curated_eval tests.test_ai_kit_spec_goal_prompt_host tests.test_skill_text_history tests.test_arch`:
  exit 0, 9/9 modules (24, 693, 58, 30, 14, 321, 75, 45 and 109 tests).
- `make ruff`, `make pyright`, `make vulture`, and pylint over `detection.py` and `cli.py`: all Passed.
- I read the whole source diff (`detection.py`, `cli.py`), the new test class and the `test_ai_kit_spec.py` diff.
- Real-config audit (`audit_c2.py` against the wave 6 marker): nothing unexpected.

## Self-Check: PASSED
