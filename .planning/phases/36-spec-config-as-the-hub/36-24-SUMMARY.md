---
phase: 36-spec-config-as-the-hub
plan: 24
subsystem: spec-config
tags: [wizard-flow, free-lanes, catalog-inputs, doc-contract-tests]

requires: [36-13, 36-20, 36-21]
provides:
  - "references/wizard-flow.md (new, 74 lines): the one question order, steps 1 to 11, with four `- Run:` commands (propose-lanes per purpose, check-reviewer --effort, check-code-index-alternative)"
  - "references/free-lanes.md (new, 43 lines): sections a to f, data-use note first with no data-use command, pool warning, owner-only usage flag, fallback rule, alternative lane (one `- Run:` line), who asks"
  - "references/cli-model-selection.md rewritten as `# Catalog inputs before the proposal` (items 1 to 7): no per-runtime ranking script, no review_only or no_exec filter; hands off to propose-lanes"
  - "tests/test_spec_config_flow_text.py: TestWizardFlowText (12 tests) and TestFreeLanesText (8 tests); every documented command is parsed with the real parser"

key-files:
  created:
    - skills/ai-kit-spec-config/references/wizard-flow.md
    - skills/ai-kit-spec-config/references/free-lanes.md
  modified:
    - skills/ai-kit-spec-config/references/cli-model-selection.md
    - tests/test_spec_config_flow_text.py

requirements-completed: [HUB-05, HUB-07, HUB-10]

executor: "cross-AI lane: pi router-env/my-coding, AIKIT-XAI status=ok exit=0 cli_rc=0 elapsed=175s attempts=1 cycles=0; one commit"
---

# Phase 36 Plan 24: spec-config question flow, free lanes and catalog inputs

One commit (pre-fold): `9bde53c docs(36-24): spec-config question flow, free lanes and catalog inputs` (4 files, +343 -147, commit hook passed).

## Accomplishments

- An agent running spec-config asks the owner the right questions in order through documented commands only; zero-price lanes get the data-use note first, the pool warning, the owner-only usage flag, the fallback rule and the alternative-lane step, all pinned by doc-contract tests.
- `cli-model-selection.md` no longer ranks by a table flag (SPEC R7 text).

## Deviations and notes

- None in the files: a script (`tmp/run-2026-11-19/cmp-36-24.py`) compared both new references byte for byte with the plan's text blocks (identical), found every constant line of the plan in the test module, and found blocks A1 to A6 in `cli-model-selection.md`. No file outside the plan's four paths changed. No SKILL.md changed (the skeleton that points at these files is plan 36-25).
- Existing text still names grok in `cli-model-selection.md` item 6 (`today: grok`) and item 2; the plan says to leave existing grok sentences alone (open item for the owner).

## Orchestrator verification (own runs, not the executor's claims)

- `python3 tools/run_unittest_parallel.py tests.test_spec_config_flow_text tests.test_ai_kit_spec_check_providers tests.test_ai_kit_spec_runtimes_table tests.test_spec_config_catalog_text tests.test_skill_text_history tests.test_arch_hardcoded_models tests.test_spec_config_lane_json tests.test_arch`: exit 0, 8/8 modules (20, 29, 62, 6, 45, 23, 6 and 109 tests).
- `make ruff`, `make pyright`, `make vulture`, `make pylint`: Passed.

## Self-Check: PASSED
