---
phase: 35-model-discovery-and-catalog
plan: 10
subsystem: detection
tags: [opencode, api-model, records, retry-503]

requires:
  - phase: 35-model-discovery-and-catalog
    provides: "35-01 stub test modules and the per-key merge seam; 35-02 hardcoding guard; 35-03 runner fixes"
provides:
  - "detection.py: parse_opencode_api_records, parse_opencode_api_payload, probe_opencode_api (images and records from one server start), a 503 retry inside the 15 s probe deadline, _opencode_fields"
  - "snapshot key clis.opencode.model_records = {providerID/id: {efforts, limit {context, input, output}, enabled, status, cost}}"
  - "tests/fixtures/opencode_api_model_v2.json (opencode 2.3.2 /api/model shape, invented router-env ids)"
  - "tests/test_catalog_listing.py: TestOpencodeApiRecords (3 tests) and TestOpencodeRecordEdges (9 tests)"

key-files:
  created:
    - tests/fixtures/opencode_api_model_v2.json
  modified:
    - skills/ai-kit-spec-review/ai_kit_spec/detection.py
    - tests/test_catalog_listing.py
    - tests/test_ai_kit_spec.py

requirements-completed: []

executor: "cross-AI lane: pi router-env/my-coding-lite, one run (1016 s, status=ok exit=0)"
---

# Phase 35 Plan 10: opencode model records and the 503 retry

One commit, `50912dc feat(35-10): capture opencode model records` (the executor reported that its first focused run failed on test fake
signatures and that later lint runs flagged formatting and typing; both were fixed before the commit, and the commit hook passed).

## Accomplishments

- `GET /api/model` answering HTTP 503 (opencode 2.3.2 while its plugins start) is retried up to 6 tries with a 2 s pause. Every request timeout
  is capped by the time left on one 15 s deadline that starts at the server timer, so the banner read counts against it; any other HTTP error,
  or a 503 on the last try, gives the existing `{}` failure result.
- `parse_opencode_api_records` keeps per `providerID/id`: effort ids exactly as listed (`none` and `thinking` included), limits as exact positive
  integers or None, `enabled` (bool or None), `status` (str or None) and `cost` (the list). It never raises on malformed items.
- `probe_opencode_api` returns `{image, records}` from one server start; `probe_opencode_api_image_input` stays as the image-only wrapper.
  `build_runtimes_snapshot` stores `model_records` when records exist, via the new `_opencode_fields` helper (a None major version takes the
  1.x verbose path).

## Deviations and notes for the code review

- The docstring of `probe_opencode_api_image_input` is now one line ("Image-only wrapper for older callers. Thin wrapper of probe_opencode_api
  (35)."); the plan said to keep the old docstring and add the wrapper sentence. The full original text moved to `probe_opencode_api`.
- `requirements-completed` is empty: HUB-02 and HUB-08 are still declared by plans without a summary (shared-ID gate), so nothing is marked.
- No file outside the plan's `files_modified` was touched.

## Orchestrator verification (own runs, not the executor's claims)

- `python3 tools/run_unittest_parallel.py tests.test_catalog_listing tests.test_ai_kit_spec tests.test_arch_hardcoded_models`: exit 0, 3/3 modules
  (12, 693 and 12 tests).
- `make ruff`, `make pyright`, `make vulture` and `uv run pre-commit run pylint --files skills/ai-kit-spec-review/ai_kit_spec/detection.py`:
  all Passed (evidence under `tmp/run-2026-11-19/chk-35-10/`).
- I read the `detection.py` and `test_ai_kit_spec.py` diffs: the clock starts before `timer.start()`, the loop honors the remaining time, only 503
  retries, and the single touched test function uses `router-env/placeholder-model-1`.
- Real-config audit (`audit_c2.py` against the wave marker): nothing unexpected; only a pi session log is newer.

## Self-Check: PASSED
