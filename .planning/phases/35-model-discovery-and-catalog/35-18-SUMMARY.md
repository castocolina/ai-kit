---
phase: 35-model-discovery-and-catalog
plan: 18
subsystem: catalog
tags: [attribution, artificial-analysis, arch-guard]

requires:
  - phase: 35-model-discovery-and-catalog
    provides: "35-02 hardcoding guard module (tracked_files, SCAN_ROOTS); 35-03 marked AA-shaped test lines"
provides:
  - "catalog_attribution.py: SOURCE_ORDER, ATTRIBUTION, AA_DERIVED_LINE, AA_TERMS_LINE, attribution_lines, catalog_sources"
  - "tests/test_arch_hardcoded_models.py: AA_SHAPE_RX, AA_MARKER, AA_SHAPE_KNOWN, aa_text_problem, aa_shape_problems, TestAaShapes"
  - "tests/test_catalog_attribution.py: 5 tests (TestAttribution)"

key-files:
  created:
    - skills/ai-kit-spec-review/ai_kit_spec/catalog_attribution.py
  modified:
    - tests/test_arch_hardcoded_models.py
    - tests/test_catalog_attribution.py

requirements-completed: []

executor: "cross-AI lane: pi router-env/my-coding-lite, one run (1358 s, status=ok exit=0, attempts=1) after the router outage; runs 1 and 2 of 2026-11-20 06:23 and 06:42 never got an answer (ECONNRESET, no work)"
---

# Phase 35 Plan 18: credit lines and the Artificial Analysis shape rule

One commit, `88c4608 feat(35-18): add catalog attribution and AA shape guard`. The executor's first commit-hook attempt failed on
ruff long lines and a later one on disk-quota errors in parallel e2e tests; it fixed the lint findings and the final hook passed.

## Accomplishments

- `attribution_lines(used)` returns the credit lines in the fixed order models.dev, artificial-analysis, arena; Artificial Analysis adds
  the derived-data line and the Amend-5 redistribution-terms line. No source gives `[]`; an unknown name raises `ValueError("unknown source: <name>")`.
- `catalog_sources(catalog)` reads `source` and `inputs` of every fact in `facts` and in each runtime row's `context` and `match`
  (`_meta` and non-dicts skipped), so cached Artificial Analysis facts still earn their credit after a failed refresh.
- Guard module: `aa_text_problem` flags an `artificial_analysis_*_index` key with a number unless the marker line covers it (its own line
  or the marker directly above the run of matching lines, never a whole file); `aa_shape_problems` skips the three historic docs in
  `AA_SHAPE_KNOWN` and reports one that no longer matches. The scratch scan listed only those three docs and `tests/test_ai_kit_spec.py`
  (`marker=True`).

## Deviations and notes for the code review

- `catalog_attribution.py` line 1 carries `# pylint: disable=line-too-long` although the executor wrapped the module docstring to two
  lines, so the suppression is probably not needed any more (the plan's one-line docstring was the reason for it).
- No file outside the plan's `files_modified` was touched.

## Orchestrator verification (own runs, not the executor's claims)

- `python3 tools/run_unittest_parallel.py tests.test_catalog_attribution tests.test_arch_hardcoded_models tests.test_skill_text_history`:
  exit 0, 3/3 modules (5, 14 and 45 tests).
- `make ruff`, `make pyright`, `make vulture`: all Passed.
- I read `catalog_attribution.py` whole and the guard-module diff.
- Real-config audit (`audit_c2.py` against the wave marker): only the Claude host's own plugin and history files and one pi session log
  changed; nothing from the lane.

## Self-Check: PASSED
