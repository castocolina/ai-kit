---
phase: 36-spec-config-as-the-hub
plan: 19
subsystem: spec-config
tags: [adapter-skill, no-config-check, session-model-mode, no-formula, doc-contract-tests]

requires: [36-16]
provides:
  - "ai-kit-spec-execute-superpowers references/config-check.md (new): the adapter variant of the No-config check (pinned against the review block except three lines), block 1 (check, `config-status --role execute`, resume guard through the `CONFIG_CHECK=` scalar and a validated resume state file), block 2 (record), block 3 (session-model injection)"
  - "adapter SKILL.md: Step 1 pointer (MANDATORY, before the start step), session-model mode at Step 2, rounds 4-5 sentence at Step 3, Step 5 repeats the `once` or `notice` line; 299 lines"
  - "adapter SKILL.md, escalation.md, design-notes.md and resolution-stops.md name route `no_formula`; no `review_only` or `review-only`"
  - "tests/test_spec_chain_text.py: TestAdapterChainBlock, TestAdapterConfigCheckBlock (blocks run for real against a stub tools script), TestAdapterNoFormulaWording (33 tests in the module)"

key-files:
  created:
    - skills/ai-kit-spec-execute-superpowers/references/config-check.md
  modified:
    - skills/ai-kit-spec-execute-superpowers/SKILL.md
    - skills/ai-kit-spec-execute-superpowers/references/escalation.md
    - skills/ai-kit-spec-execute-superpowers/references/design-notes.md
    - skills/ai-kit-spec-execute-superpowers/references/resolution-stops.md
    - tests/test_spec_chain_text.py

requirements-completed: []

executor: "cross-AI lane: pi router-env/my-coding; two plain lanes ended no_change (43 s and 22 s, no change, tree clean), the third lane (fix-up prompt, 316 s, AIKIT-XAI status=ok exit=0 attempts=1 cycles=0) did the work"
---

# Phase 36 Plan 19: adapter skill no-config chain

Three commits (pre-fold): `5ca5399 docs(36-19): no-config check for the superpowers adapter before the start step` (hook 16/16), `e69fe7f test(36-19): run the adapter's no-config blocks against a stub` (hook 3/3), `4f29ee8 docs(36-19): adapter texts name the no_formula route; step 5 repeats the no-config notice` (hook 16/16); 6 files, +373 -14 over the three.

## Accomplishments

- An execute run on a project with no lanes asks once before any commit moves; a resumed run of the same plan (valid resume state file plus a recorded `CONFIG_CHECK=`) never asks again, a fresh start checks again; answer (2) and the no-way-to-ask case dispatch every task natively on the session model (no `resolve-injection`, no rounds 4-5 escalation) and print the notice again after the final review.
- The adapter texts name route `no_formula` instead of the seed flag. The adapter SKILL.md is materially changed: it goes to plan 36-29's judge loop (not run here).

## Deviations and notes

- Executor escalation: the two plain lanes changed nothing. Cause (inferred; the runner keeps no answer text for a `no_change` lane): the plan's T1 text (the new reference file) contains a bash fence with a heredoc and command substitution, which the executor shell rules forbid in the model's own calls. The fix-up prompt (`tmp/run-2026-11-19/fixup-36-c4-19.md`) states that T1 is file content to write with the file-write tool and asks for a reason file when blocked; that lane completed all three tasks. No file outside the plan's six paths changed.

## Orchestrator verification (own runs, not the executor's claims)

- `python3 tools/run_unittest_parallel.py tests.test_spec_chain_text tests.test_ai_kit_spec_superpowers tests.test_ai_kit_spec_runtimes_table tests.test_quota_policy_text tests.test_cross_ai_skill_text tests.test_skill_text_history tests.test_arch_hardcoded_models tests.test_flow_docs tests.test_ai_kit_caller_text tests.test_arch`: exit 0, 10/10 modules (33, 170, 62, 19, 30, 45, 23, 25, 11 and 109 tests).
- `make ruff`, `make pyright`, `make vulture`, `make pylint`: Passed. Read the whole skill and reference diff against T1 to T9.

## Self-Check: PASSED
