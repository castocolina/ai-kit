---
phase: 35-model-discovery-and-catalog
plan: 12
subsystem: catalog
tags: [usability, check-reviewer, catalog-path, redaction]

requires:
  - phase: 35-model-discovery-and-catalog
    provides: "35-01 per-key merge seam and stub test modules; 35-02 hardcoding guard; 35-03 runner fixes"
provides:
  - "usability.py: ERROR_MAX, sanitize_error, record_for, find_runtime_key, record_usability (read-merge-write under model_catalog.locked_catalog_update)"
  - "cli.py: check-reviewer --catalog-path; the printed detail and reason are redacted with secret_shapes.redact on every call"
  - "quota.py: every probe result carries an `answered` key (true only when the runner's stdout held text)"
  - "tests/test_catalog_usability.py: 13 tests (TestUsabilityRecord, TestUsabilityStates)"

key-files:
  created:
    - skills/ai-kit-spec-review/ai_kit_spec/usability.py
  modified:
    - skills/ai-kit-spec-review/ai_kit_spec/cli.py
    - skills/ai-kit-spec-review/ai_kit_spec/quota.py
    - tests/test_catalog_usability.py

requirements-completed: []

executor: "cross-AI lane: pi router-env/my-coding-lite, one run (1160 s, status=ok exit=0)"
---

# Phase 35 Plan 12: usability records from check-reviewer

One commit, `5661c10 feat(35-12): record reviewer usability in catalog` (the executor also ran `make test` before committing and reported it
green; its first lint and type runs flagged issues that it fixed).

## Accomplishments

- `check-reviewer --runtime R --model M --catalog-path P` records `runtimes[R].usability {state, at, via, error}` on the catalog entry whose
  `runtimes[R].model_id` equals M, through `merge_catalog_entry` inside `locked_catalog_update`. A pair missing from the catalog prints
  `usability.recorded` false with a `not in catalog:` problem and writes nothing; an unreadable catalog writes nothing either.
- Only a call that answered (`answered` true, available, no reason) is `verified`; an available call without answer text or with a reason is
  `unverified`; a failed call is `rejected` with its sanitized first error line (control characters removed, key shapes redacted, at most 200
  characters). A native or custom entry (no runtime) records nothing.
- The record is written under the probed runtime only, so another runtime of the same entry keeps its own state.

## Deviations and notes for the code review

- `usability.py` does not import `cache_read_json` and `cache_write_json` (the plan's import line listed them); the locked update owns the
  read and write, and the unused imports would fail ruff and vulture.
- `answered` is set on the native-entry branch of `probe_reviewer_quota` too (false), as the plan says.
- No file outside the plan's `files_modified` was touched.

## Orchestrator verification (own runs, not the executor's claims)

- `python3 tools/run_unittest_parallel.py tests.test_catalog_usability tests.test_ai_kit_spec tests.test_arch_hardcoded_models
  tests.test_secret_shapes tests.test_ai_kit_spec_env_scrub`: exit 0, 5/5 modules (13, 693, 12, 27 and 3 tests).
- `make ruff`, `make pyright`, `make vulture` and `uv run pre-commit run pylint --files` over `usability.py`, `cli.py` and `quota.py`: all
  Passed (evidence under `tmp/run-2026-11-19/chk-35-12/`).
- I read `usability.py` whole and the `cli.py` and `quota.py` diffs: the lookup happens inside the lock on the re-read catalog, the redaction
  loop runs with and without `--catalog-path`, and `_probe_entry` keeps its other keys.
- Real-config audit (`audit_c2.py` against the wave marker): nothing unexpected; only pi session logs are newer.

## Self-Check: PASSED
