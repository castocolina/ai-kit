---
phase: 36-spec-config-as-the-hub
plan: 16
subsystem: spec-config
tags: [review-skill, no-config-check, no-formula, doc-contract-tests]

requires: [36-03, 36-12]
provides:
  - "ai-kit-spec-review SKILL.md Step 0.7: the shared No-config check block (13 lines, ASCII, pinned verbatim as BLOCK in tests/test_spec_chain_text.py), run as `config-status --role review`"
  - "references/cross-ai-dispatch.md: point 3 = No-config check then the snapshot refresh (the old missing-snapshot hint is gone); point 2 prints the pinned TOOLS_PY-missing notice (never for --no-cross-ai)"
  - "review SKILL.md, cross-ai-dispatch.md and cli-profiles/claude.md name route `no_formula` and the runner-formula fact; no `review_only` or `review-only`"
  - "tests/test_spec_chain_text.py: TestReviewChainBlock, TestConfigStatusFixture, TestDispatchPointThree, TestReviewNoFormulaWording (15 tests)"

key-files:
  created: []
  modified:
    - skills/ai-kit-spec-review/SKILL.md
    - skills/ai-kit-spec-review/references/cross-ai-dispatch.md
    - skills/ai-kit-spec-review/references/cli-profiles/claude.md
    - tests/test_spec_chain_text.py
    - tests/test_ai_kit_spec_runtimes_table.py

requirements-completed: []

executor: "cross-AI lane: pi router-env/my-coding, one run (1153 s, AIKIT-XAI status=ok exit=0 attempts=1 cycles=0)"
---

# Phase 36 Plan 16: review skill no-config chain

Three commits (pre-fold): `26582c5 docs(36-16): no-config check block in the review skill's Step 0.7` (hook 115/115), `4b7024c docs(36-16): dispatch point 3 runs config-status before the snapshot refresh` (hook 115/115), `55489ed docs(36-16): review texts name the no_formula route instead of the seed flag` (hook 116/116); 5 files, +222 -39 over the three.

## Accomplishments

- A review on a project with no lanes asks once (run ai-kit-spec-config now, run once on the session model, stop); `--no-cross-ai` never runs the check; a missing review helper prints a named notice instead of degrading silently.
- A fixture project with no config prints `none` from `config-status --role review`, an active review roster prints `active`, a malformed file exits 2 with `ai-kit-spec: config error:`, and an execute-only roster still reaches the check.
- The review texts name route `no_formula`; `test_review_only_label` became `test_no_formula_wording`; the probe-quota sentence names the review order.
- The review SKILL.md is materially changed: it goes to plan 36-29's judge loop (not run here).

## Deviations and notes

- None. No file outside the plan's five paths changed.

## Orchestrator verification (own runs, not the executor's claims)

- `python3 tools/run_unittest_parallel.py tests.test_spec_chain_text tests.test_ai_kit_spec_runtimes_table tests.test_skill_text_history tests.test_arch_hardcoded_models tests.test_ai_kit_spec_review_checklist tests.test_ai_kit_spec_review_fixer tests.test_cross_ai_skill_text tests.test_quota_policy_text tests.test_arch`: exit 0, 9/9 modules (15, 62, 45, 14, 13, 9, 30, 19 and 109 tests).
- `make ruff`, `make pyright`, `make vulture`, `make pylint`: Passed. Read the whole skill and reference diff against the plan texts T1 to T5.

## Self-Check: PASSED
