---
phase: 36-spec-config-as-the-hub
plan: 26
subsystem: spec-config
tags: [evals, trigger-queries, hardcoded-models-baseline, drift-test]

requires: [36-25, 36-15]
provides:
  - "skills/ai-kit-spec-config/evals/evals.json: 19 cases (seven new, three reworded: per-role orders, no-way-to-ask stop, claude effort not asked, escalation only with two lanes, zero-price data use with yes and with decline, migration deleted unless --keep-backup)"
  - "skills/ai-kit-spec-config/evals/trigger-queries.json: 20 queries (10 true, 10 false)"
  - "skills/ai-kit-spec-config/evals/files/router-alias/lanes.md: the owner alias as a marked `model-example:` input; the evals.json entry of the hardcoded-models baseline is removed in the same commit"
  - "tests/test_ai_kit_spec_check_providers.py: `test_skill_evals_have_the_nineteen_cases` (renamed) and `test_new_flow_evals_quote_the_skill_text` (NEW_FLOW_PHRASES)"

key-files:
  created:
    - skills/ai-kit-spec-config/evals/files/router-alias/lanes.md
  modified:
    - skills/ai-kit-spec-config/evals/evals.json
    - skills/ai-kit-spec-config/evals/trigger-queries.json
    - tests/test_ai_kit_spec_check_providers.py
    - tests/fixtures/no_hardcoded_models_baseline.json

requirements-completed: [HUB-01, HUB-05, HUB-07, HUB-10]

executor: "cross-AI lane: pi router-env/my-coding, AIKIT-XAI status=ok exit=0 cli_rc=0 elapsed=111s attempts=1 cycles=0; one commit"
---

# Phase 36 Plan 26: spec-config evals for the new flow

One commit (pre-fold): `9c773cb test(36-26): spec-config evals for the new flow, alias as a marked example` (5 files, +130 -18, commit hook passed).

## Accomplishments

- The judge loop (plan 36-29) grades spec-config against evals that describe what the skill does now; every new eval quotes a phrase the skill text really holds.
- The router alias left evals.json for a marked example input and its baseline entry (`cleaned_by` 36, `skills/ai-kit-spec-config/evals/evals.json`) was removed in the same commit (seven lines deleted, nothing else changed in the baseline file).

## Spec statements without a plan task (SPEC R13, D-23)

- Per-model page rule: stated by plan 36-25 at `skills/ai-kit-spec-config/SKILL.md:164`.
- Doc-contract pins: `tests/test_spec_config_flow_text.py:279` (plan 36-25) and, added by this lane as a second pin, `tests/test_ai_kit_spec_check_providers.py:404` (`assertIn("once per chosen model", text)` over the skill text and every reference, inside `test_new_flow_evals_quote_the_skill_text`).
- R13 concurrency: recorded in `36-25-SUMMARY.md` under the heading "R13 concurrency" (the wizard composes the note and confirmation in memory and writes them through the same atomic splicing writer; last writer wins, nothing else is shared; no code).

## Deviations and notes

- None of substance. The JSON `files` list of `edge-router-alias-assumed` is written on three lines (json layout), same value as the plan block.
- No file outside the plan's five paths changed.

## Orchestrator verification (own runs, not the executor's claims)

- `python3 tools/run_unittest_parallel.py tests.test_skill_evals_shape tests.test_ai_kit_spec_check_providers tests.test_arch_hardcoded_models tests.test_config_callers tests.test_skill_text_history`: exit 0, 5/5 modules (6, 30, 23, 10 and 45 tests).
- `make ruff`, `make pyright`, `make vulture`, `make pylint`: rc 0.

## Self-Check: PASSED
