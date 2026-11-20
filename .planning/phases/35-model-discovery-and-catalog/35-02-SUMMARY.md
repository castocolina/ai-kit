---
phase: 35-model-discovery-and-catalog
plan: 02
subsystem: testing
tags: [arch-group, hardcoding-guard, baseline, ast-free-scan]

requires:
  - phase: 35-model-discovery-and-catalog
    provides: "35-01: tests.test_arch_hardcoded_models registered in ARCH_MODULES as a stub"
provides:
  - "tests/test_arch_hardcoded_models.py: position-based guard (scan_text, tracked_files, scan_tree, load_baseline, baseline_problems), TestHardcodedModels (2 tests) and TestHardcodedModelsNonVacuity (10 tests)"
  - "tests/fixtures/no_hardcoded_models_baseline.json: schema 2, 89 files, 1451 hit strings, shrink-only"

key-files:
  created:
    - tests/fixtures/no_hardcoded_models_baseline.json
  modified:
    - tests/test_arch_hardcoded_models.py

requirements-completed: [HUB-09]

executor: "cross-AI lane: pi router-env/my-coding-lite, one run (373 s)"
---

# Phase 35 Plan 02: the hardcoded-model guard and its baseline

One commit, `1de2582 test(35-02): add shrinking hardcoded-model guard`.

## Accomplishments

- The stub became the live arch-group guard: position rules (model-key values, `--model` argument, quoted provider/model literals,
  seed-row cells, multi-line seed rows by bracket balance), allowed forms (`router-env/<x>`, `placeholder-model-<n>`,
  `placeholder-alias-<n>`, `fake/<token>`, `fake-<token>`), a `model-example:` marker that exempts only comments, docstrings,
  doc lines and example fields and covers its own line and the next, NFKC normalisation, and a scan of tracked plus untracked files.
- `baseline_problems` fails on a new violating file, a new or second copy of a hit inside a baselined file, a vanished hit,
  a baselined path that is gone or fixed, a bad schema, an unsorted or duplicated baseline and a bad `cleaned_by`.
- Baseline generated once by the scratch script `tmp/p35/02/make_baseline.py`: 89 files, 1451 hits; `cleaned_by` counts:
  backlog 54, 36: 26, 35: 8 (detection.py among them), 37: 1 (cross-ai.mjs); no file that a Phase 35 plan creates is baselined.

## Deviations and notes for the code review

- The plan's step 1 says to keep the plan-01 import preamble (`sys.path` insert). The new module imports nothing from
  `ai_kit_spec`, so it dropped `os`, `sys` and the insert; no behaviour depends on them.
- `baseline_problems` keeps one unused local (`actual = _hit_strings(hits)` in the first loop) and `test_untracked_file_is_scanned`
  writes the literal text `pass\n` (backslash, n) instead of a newline; both are harmless and pass ruff and pyright.

## Orchestrator verification (own runs, not the executor's claims)

- `python3 tools/run_unittest_parallel.py --group arch` exit 0, 2/2 modules (`tests.test_arch` 109 tests, `tests.test_arch_hardcoded_models` 12 tests).
- `python3 tests/test_arch_hardcoded_models.py -v`: 12 tests `ok`, none skipped (`test_tree_matches_baseline` runs against the real tree).
- Baseline checks (`tmp/run-2026-11-19/check_baseline.py`): schema 2; paths sorted and unique; every entry has non-empty sorted hits;
  `cross-ai.mjs` has `cleaned_by` 37 and `detection.py` has 35; no baselined path starts with a Phase 35 new-file prefix; no grok path;
  the module has no `import tests.test_arch`, no `.planning` and no `tmp/` string.
- Real-config audit after the lane: no file changed under `~/.pi` (sessions only), `~/.config/opencode`, `~/.cursor`; the changed files under
  `~/.claude/plugins` and `~/.codex` belong to the Claude host and to a codex app server of another project.

## Self-Check: PASSED
