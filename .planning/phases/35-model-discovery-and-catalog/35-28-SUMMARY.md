---
phase: 35-model-discovery-and-catalog
plan: 28
subsystem: catalog
tags: [catalog-report, attribution, runtimes-snapshot, optional-names]

requires:
  - phase: 35-model-discovery-and-catalog
    provides: "35-11 optional names store, 35-18 attribution, 35-20 report rows, 35-22 catalog_cmds, 35-27 fetch-model-catalog"
provides:
  - "catalog_cmds.cmd_catalog_report: catalog-report --catalog-path P (--detect | --runtimes-json R) [--json] prints plan 20's sorted rows (with facts, the optional names of the store and the host rows) and then the Attribution lines from catalog_sources(entries)"
  - "--detect builds the runtimes snapshot in this process and passes fresh=True; a snapshot from --runtimes-json is passed with fresh=False, so absent ids read `not checked (cached <date>)`"
  - "tests/test_catalog_cmds.py: TestCatalogReportCommand, 8 tests"

key-files:
  modified:
    - skills/ai-kit-spec-review/ai_kit_spec/catalog_cmds.py
    - tests/test_catalog_cmds.py

requirements-completed: []

executor: "cross-AI lane: pi router-env/my-coding-lite, one run (520 s, AIKIT-XAI status=ok exit=0 attempts=1 cycles=0; an earlier launch lane-35-28 was stopped by me after 8 s with SIGTERM before it did anything, see the ledger)"
---

# Phase 35 Plan 28: catalog-report

One commit, `d725787 feat(35-28): add catalog report command` (pre-fold); the commit hook ran 98/98 modules green.

## Accomplishments

- `cmd_catalog_report` reads the catalog (an unreadable or empty file gives no rows), builds or reads the runtimes snapshot, prints the sorted rows and, only
  when the catalog holds source facts, a blank line, `Attribution:` and the credit lines (a failed refresh that kept cached facts is still credited,
  because the credit comes from `catalog_sources(entries)`).
- `--json` prints `{"rows": [...], "attribution": [...]}`; the optional store is read through `optional_sources.store_path`, a non-dict store reads as empty.
- `catalog-report` is registered in `register_parsers` and in `COMMANDS` (the `--detect` and `--runtimes-json` choices are a required mutually exclusive group).

## Notes for the code review

- `_optional_rows_input(env, entries)` keeps the plan's signature but does not use `entries` (vulture and pylint accept it).
- Only `catalog_cmds.py` and `tests/test_catalog_cmds.py` changed, as the plan lists; no formatting noise (`+185 -2`).
- The lane's report says the first targeted run exposed test-fixture problems and a pylint import-order finding, both fixed before the commit.

## Orchestrator verification (own runs, not the executor's claims)

- `python3 tools/run_unittest_parallel.py tests.test_catalog_cmds tests.test_catalog_stale tests.test_catalog_listing tests.test_arch_hardcoded_models
  tests.test_arch tests.test_skill_text_history tests.test_gate_scope tests.test_ai_kit_spec tests.test_catalog_attribution`: exit 0, 9/9 modules
  (18, 15, 24, 14, 109, 45, 62, 693 and 5 tests).
- `make ruff`, `make pyright`, `make vulture` rc 0; pre-commit pylint on `catalog_cmds.py` rc 0.
- Read the whole `catalog_cmds.py` diff; the eight report tests are named as the plan lists.
- Real-config audit (marker-c6-w10): only the host's own files and another agent's `.codex` logs and models cache; nothing from the lane.

## Self-Check: PASSED
