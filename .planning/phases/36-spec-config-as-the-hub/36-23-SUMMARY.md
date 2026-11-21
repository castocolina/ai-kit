---
phase: 36-spec-config-as-the-hub
plan: 23
subsystem: spec-config
tags: [wizard-json-example, doc-writer-contract, herdr-identity]

requires: [36-13, 36-17, 36-20, 36-21]
provides:
  - "config-file.md: section `## Example: the JSON the wizard passes to render-toml` (one paragraph, one json block, four bullets), placed after `## Roles` and before `## Trust`; placeholders only"
  - "tests/test_spec_config_lane_json.py: TestWizardLaneJson (6 tests) renders exactly that block through config_io.cfg_render_lanes with no message, keeps every lane key in its role, per-role orders, every new lane key, no date or alias, every flag has a target"
  - "tests/test_config_herdr_identity.py: TestHerdrIdentity (4 tests): config-status, render-toml, propose-lanes and check-reviewer print and write identical bytes with and without HERDR_ENV=1 and a logging fake herdr on PATH, and the fake logs zero calls; herdr-names is excluded by name"

key-files:
  modified:
    - skills/ai-kit-spec-config/references/config-file.md
    - tests/test_spec_config_lane_json.py
    - tests/test_config_herdr_identity.py

requirements-completed: [HUB-05, HUB-07, HUB-10]

executor: "cross-AI lane: pi router-env/my-coding, AIKIT-XAI status=ok exit=0 cli_rc=0 elapsed=493s attempts=1 cycles=0; one commit"
---

# Phase 36 Plan 23: wizard write path pinned

One commit (pre-fold): `76f51ba test(36-23): pin wizard write path` (3 files, +289 -8, commit hook passed). No production code changed.

## Accomplishments

- The documented wizard JSON is exactly what the writer accepts and keeps (a key the writer drops or warns about fails the test).
- The executable part of the herdr rule is pinned: the four write-path commands never differ with a herdr signal and never call herdr. The question flow's text is plan 36-24's.

## Deviations and notes

- The herdr test uses `assertTrue(herdr_calls(self.log) == [])` where the plan says `assertEqual`-style wording is free (the acceptance text `herdr_calls(self.log) == []` is present). No file outside the plan's three paths changed. Shipped text edited: `skills/ai-kit-spec-config/references/config-file.md` (a reference, not a SKILL.md).

## Orchestrator verification (own runs, not the executor's claims)

- `python3 tools/run_unittest_parallel.py tests.test_spec_config_lane_json tests.test_config_herdr_identity tests.test_arch_hardcoded_models tests.test_skill_text_history tests.test_arch`: exit 0, 5/5 modules (6, 4, 23, 45 and 109 tests).
- `make ruff`, `make pyright`, `make vulture`, `make pylint`: Passed. Read the whole doc and test diff against the plan.

## Self-Check: PASSED
