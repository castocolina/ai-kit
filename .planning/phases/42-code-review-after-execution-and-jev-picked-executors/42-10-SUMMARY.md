---
phase: 42-code-review-after-execution-and-jev-picked-executors
plan: 10
subsystem: ai-kit-spec-execute-superpowers (references, evals), README
tags: [docs, evals, executor-pick, code-review, lite-block, transport]
requires: [42-09]
provides:
  - "dispatch-external-cli.md `## Executor pick`: the one home of the executor pick rules and its stderr line"
  - "tests/test_adapter_single_definitions.py pins `## Executor pick`, the lite-block marker, the SKILL.md code review heading, the code-review.md and lite-block.md links and the pick-line rule, with no skip branch"
  - "README row names the code review (at most three rounds, CRITICAL or HIGH blocks) and the jev executor pick"
  - "four new evals with named worlds (code review cap, executor pick line, lite block, transport subprocess without a verified resume) and eleven fixtures; the fold and no-config evals pass the code review step first; 22 evals"
affects: [42-11, 42-12]
key-files:
  created:
    - skills/ai-kit-spec-execute-superpowers/evals/files/code-review/review-round-high.md
    - skills/ai-kit-spec-execute-superpowers/evals/files/code-review/round-outcomes.md
    - skills/ai-kit-spec-execute-superpowers/evals/files/executor-pick/project/aikit/config.toml
    - skills/ai-kit-spec-execute-superpowers/evals/files/executor-pick/jev-answer.json
    - skills/ai-kit-spec-execute-superpowers/evals/files/lite-small/project/aikit/config.toml
    - skills/ai-kit-spec-execute-superpowers/evals/files/lite-small/model-catalog.json
    - skills/ai-kit-spec-execute-superpowers/evals/files/lite-small/jev-answer.json
    - skills/ai-kit-spec-execute-superpowers/evals/files/lite-small/runtimes.json
    - skills/ai-kit-spec-execute-superpowers/evals/files/transport/transport.json
    - skills/ai-kit-spec-execute-superpowers/evals/files/transport/runtimes.json
    - skills/ai-kit-spec-execute-superpowers/evals/files/transport/injection.json
  modified:
    - skills/ai-kit-spec-execute-superpowers/references/dispatch-external-cli.md
    - skills/ai-kit-spec-execute-superpowers/evals/evals.json
    - tests/test_adapter_single_definitions.py
    - README.md
decisions:
  - "Eval fixtures use fake/placeholder-alias-<n> where the plan wrote router-env/placeholder-alias-<n>: an unmarked router-env alias outside tests/ is a referee hit of tests/test_arch_hardcoded_models.py"
metrics:
  tasks: 2
  commits: 2
---

# Phase 42 Plan 10: adapter docs and evals close-out Summary

The executor pick now has one doc section in `dispatch-external-cli.md` (labels-only jev ask on a plain first
resolution, the dispatched-key stderr line, the `pick` field, the cases that never ask), and the single-home test pins
it beside the lite-block marker, the SKILL.md code review heading and both new reference links without a skip branch.
The README row names the code review and the pick. The adapter carries 22 evals: four new ones whose worlds are stated
and whose fixtures are listed (a code review that caps at three rounds and stops for the owner, the executor pick line,
the lite block for a small pick, a transport round with no verified resume that resets the record to one round), and
the fold, start and no-config evals now pass the code review step before the fold. No SKILL.md changed; the eval run
itself is the orchestrator's, after verification.

## Commits

- `b3f9bbb` docs(42-10): executor pick section, single-home pins and the README row (Task 1)
- `746e3ef` test(42-10): eval worlds for the code review cap, executor pick, lite block and transport (Task 2)

## Lane history

Both lanes pi `router-env/my-coding` through the project runner, per-task fix-up prompts, `status=ok`, coverage 1/1,
first attempt: `42-10-fix-a` 290 s (hook 60/60 + 2/2 uv, lane-reported); `42-10-fix-b` 260 s (hook counts not
quoted). No lane reported an e2e deferral.

## Checks (own runs)

- Acceptance greps all met: `## Executor pick` 1, the lite-marker pin 1, the rule pin 1, the pick phrase in the doc 1,
  the README phrase 1; eval ids 22, `the code review step passed` 1, the pick line 2, no machine path under `evals/`,
  evals.json valid JSON.
- Plan verification modules: adapter_single_definitions 11, ai_kit_spec_superpowers 210, skill_evals_shape 6,
  arch_hardcoded_models 23, skill_text_history 45; also spec_chain_text 40: all ok.
- Gates at `746e3ef`: unit+arch `211/211 modules passed` (guard peak 7, no kill); `make ruff`, `make pyright`,
  `make vulture`, `make pylint`, `make check-dogfood` exit 0 (advisory stale-digest and facts-drift lines only).
- Scope from `aa48550`: exactly the fifteen `files_modified` paths. Added shipped lines carry no phase, decision or
  requirement id, date or `.planning` path; the hardcoded-model baseline is unchanged; no SKILL.md changed (the adapter
  SKILL.md stays at 297 lines).

## Deviations

- Fixture model literals: `fake/placeholder-alias-1` (executor-pick roster) and `fake/placeholder-alias-2`
  (round-outcomes) replace the plan's `router-env/placeholder-alias-<n>` (see decisions).
- `precise-executor-pick-logs-why`, `edge-lite-block-only-for-lite-pick` and
  `edge-transport-subprocess-without-verified-resume` gained the setup sentence (copy the `project` folder to a scratch
  root, rename `aikit/` to `.aikit/`, run from that root) that `tests/test_spec_chain_text.py`
  `test_review_fixtures_use_a_project_folder` requires for every eval listing a `/project/` fixture, as the existing
  evals carry.
