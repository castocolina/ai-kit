---
phase: 36-spec-config-as-the-hub
plan: 27
subsystem: spec-review
tags: [evals, fixtures, no-config-chain, chain-evals-test]

requires: [36-16, 36-19]
provides:
  - "skills/ai-kit-spec-review/evals/evals.json (new, 13 cases) and trigger-queries.json (new, 20 queries, 10 true): every no-config situation with each of the three answers, --no-cross-ai, the missing-helper notice, execute-only roster, and the four converted routing scenarios"
  - "nine review fixture files under skills/ai-kit-spec-review/evals/files/ (project layout; aikit/ stands for .aikit/, planning/ for .planning/)"
  - "skills/ai-kit-spec-execute-superpowers/evals: seven appended cases (14 in all), two trigger queries (22: 10 true, 12 false), fixtures active-execute and review-only; no --no-cross-ai case"
  - "tests/test_spec_chain_text.py: TestChainEvals (6 tests; module now 39 tests)"
  - "removed from the tree: the four skills/ai-kit-spec-review/evals/0N-*.md scenarios (history keeps them)"

key-files:
  created:
    - skills/ai-kit-spec-review/evals/evals.json
    - skills/ai-kit-spec-review/evals/trigger-queries.json
    - skills/ai-kit-spec-execute-superpowers/evals/files/active-execute/project/aikit/config.toml
    - skills/ai-kit-spec-execute-superpowers/evals/files/review-only/project/aikit/config.toml
  modified:
    - skills/ai-kit-spec-execute-superpowers/evals/evals.json
    - skills/ai-kit-spec-execute-superpowers/evals/trigger-queries.json
    - tests/test_spec_chain_text.py
  deleted:
    - skills/ai-kit-spec-review/evals/01-superpowers-plan-routes-writing-plans.md
    - skills/ai-kit-spec-review/evals/02-gsd-plan-routes-native-cmd.md
    - skills/ai-kit-spec-review/evals/03-generic-doc-direct-edit.md
    - skills/ai-kit-spec-review/evals/04-ambiguous-detection-fallback.md

requirements-completed: [HUB-01]

executor: "cross-AI lane: pi router-env/my-coding, AIKIT-XAI status=ok exit=0 cli_rc=0 elapsed=463s attempts=1 cycles=0; one commit"
---

# Phase 36 Plan 27: review and adapter evals for the no-config chain

One commit (pre-fold): `e4b965e test(36-27): review and adapter evals for the no-config chain` (20 files, +453 -125, commit hook passed).

## Accomplishments

- Both chain skills have evals for every no-config situation and answer on real fixture files; every quoted notice line matches the pinned `BLOCK`, `ADAPTER_BLOCK` and `TOOLS_PY_NOTICE`; the adapter has no `--no-cross-ai` case.

## Deviation: four assertions added to keep old coverage (orchestrator decision)

The four old Markdown scenarios held five pass criteria that the plan's new cases did not state: the absolute `SEEDS_DIR` (scenario 01 and 02), the approval surface message naming the file (01 and 03), the `gsd-plan-checker` validate step after a successful `/gsd-plan-phase ... --reviews` (02 step 9, still in `references/routing-table.md` and the GSD framework profile), and "no native-skill or slash-command routing, review still completes" (04). Before the files were moved, the lane prompt (`tmp/run-2026-11-19/extra-36-c6-27.md`) added exactly four assertions, one string at the end of the `assertions` list of each converted case in `skills/ai-kit-spec-review/evals/evals.json` (lines 13, 24, 35, 47): `casual-superpowers-plan-routes-writing-plans`, `precise-gsd-plan-routes-native-cmd`, `edge-generic-doc-direct-edit`, `edge-ambiguous-framework-fallback`. `tmp/run-2026-11-19/cmp-36-27.py` parses plan blocks E1, E2, A1, A2 and the committed JSON: apart from these four extra assertions every id, prompt, expected_output, files list and assertion is identical to the plan, the trigger queries are identical and the adapter holds 14 cases.

## Deviations and notes

- Residual (not asserted by a separate string): old scenario 02's "reviewer prompt contains only the file path" is asserted by the superpowers case of the same orchestrator step, and "archetype plan, framework gsd" sits in the GSD case's `expected_output` only.
- The lane removed its own scratch folder `tmp/p36-27/` (the plan asked to keep the moved bytes in `tmp/p36-27/old-evals/`); the four files stay recoverable from git history (`git show e4b965e^:skills/ai-kit-spec-review/evals/<name>.md`). Nothing outside `tmp/` or the repository was deleted.
- No file outside the plan's paths changed.

## Orchestrator verification (own runs, not the executor's claims)

- `python3 tools/run_unittest_parallel.py tests.test_skill_evals_shape tests.test_spec_chain_text tests.test_arch_hardcoded_models tests.test_config_callers tests.test_ai_kit_spec_superpowers`: exit 0, 5/5 modules (6, 39, 23, 10 and 170 tests).
- `make ruff`, `make pyright`, `make vulture`, `make pylint`: rc 0.

## Self-Check: PASSED
