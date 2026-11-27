---
phase: 42-code-review-after-execution-and-jev-picked-executors
plan: 03
subsystem: ai-kit-spec-execute-superpowers (plan-writer brief)
tags: [lite-block, executor-pick, plan-writer, rail]
requires: [42-02]
provides:
  - "references/lite-block.md: the lite block once between `<!-- lite-block:start -->` and `<!-- lite-block:end -->`, with Selector, Command, Rail sentence and Limits sections"
  - "executor_pick.LITE_CLASSES = (\"small\", \"fast\") and is_lite(entries, candidate)"
  - "adapter shim `lite-block --cwd <dir>`: executor pick with the task label `plan` over the dispatchable execute lanes (read-only resolver, cached runtimes snapshot only); writes `.aikit/brief/lite-executor.md` for a small or fast pick, removes a stale one otherwise; stdout `{lite, key, decided_by, path, removed_stale}`; exit 2 on a config error, a brief folder outside the project or a write failure"
  - "AGENTS.md rail line and the matching RULE_CLAUSES clause hand `.aikit/brief/lite-executor.md` to the plan writer only after an exit 0 with `\"lite\": true`"
affects: [42-10, 42-11, 42-12]
key-files:
  created:
    - skills/ai-kit-spec-execute-superpowers/references/lite-block.md
    - tests/test_lite_block.py
  modified:
    - skills/ai-kit-spec-review/ai_kit_spec/executor_pick.py
    - skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/cli.py
    - skills/ai-kit-spec-execute-superpowers/SKILL.md
    - AGENTS.md
    - skills/_shared/ai_kit_rules_common/code_exploration.py
    - Makefile
    - .pre-commit-config.yaml
decisions:
  - "The adapter cli.py `from ai_kit_spec import ...` line became a parenthesized multi-line import: adding `routing` passes the 100-character limit"
  - "A router alias reads class `router` and gets no lite block (owner's confirmed scope reading; stated in the reference's Limits)"
metrics:
  tasks: 2
  commits: 2
---

# Phase 42 Plan 03: lite executor block Summary

`lite-block --cwd <project>` on the adapter shim runs the executor pick over the execute roster with the task label
`plan`, reading the roster through the read-only resolver (a pending old roster stays pending) and routing from the
cached runtimes snapshot only (no host probe, no cache write); lanes on a skip route are never offered. When the
picked model's catalog class is `small` or `fast` it writes `.aikit/brief/lite-executor.md` holding only the block
(labeled unverified); a strong pick, no pick or a missing or `router`/`unknown` class writes nothing and removes a
stale file. A `.aikit` or `brief` folder resolving outside the project exits 2 before any write or removal. The
brief `.aikit/brief/SKILL.md` keeps its bytes. AGENTS.md (and its shared rule clause) runs the command after the
brief step and hands the file over only on exit 0 with `"lite": true`; the adapter SKILL.md points at the reference.

## Commits

- `5975b11` feat(42-03): write the lite executor block beside the plan-writer brief (Task 1)
- `39e1611` docs(42-03): hand the lite block to the plan writer from the project rail (Task 2)

## Lane history

- Task 1: per-task fix-up lane `42-03-fix-a` (pi router-env/my-coding), status ok, 696 s, one commit; first commit
  attempt refused by the ruff hook (RUF005 in the new test), fixed by the lane; hook 231/231 modules plus 23/23 under uv.
- Task 2: per-task fix-up lane `42-03-fix-b`, status ok, 495 s, one commit; hook 35/35 covering modules plus 2/2 under
  uv; the hook deferred `tests.test_ai_kit_gsd_curated_config_matrix` to push.

## Checks (orchestrator chunk, own runs)

- Acceptance greps of both tasks: every EXPECT value met; SKILL.md 293 lines; scope check from the plan base
  b3aa451 lists exactly the plan's nine paths (nothing under skills/ai-kit-commit-fold/ or a superpowers plugin path).
- Makefile and `.pre-commit-config.yaml` add only `tests.test_lite_block`; added shipped lines carry no phase,
  decision or requirement id and no date; `tests/fixtures/no_hardcoded_models_baseline.json` unchanged.
- Modules: `tests.test_lite_block` (15 tests), `test_executor_pick`, `test_ai_kit_spec_superpowers`, `test_gate_scope`,
  `test_skill_text_history`, `test_arch_hardcoded_models`, `test_rules_docs`, `test_ai_kit_rules_common`,
  `test_tool_advisor_core`, `test_agents_md_links`, `test_arch`: all ok.
- Real-command smoke test (scratch HOME, `AI_KIT_REFUSE_REAL_HOME=1`, temporary project with no roster): exit 0,
  `{"lite": false, "key": null, "decided_by": "default", ...}`, no new file, brief bytes kept; with `.aikit` symlinked
  outside the project: exit 2 with `ai-kit-spec: lite-block: brief folder outside the project`, the outside file kept.
- Deferred e2e `tests.test_ai_kit_gsd_curated_config_matrix` run under the guard after each task: 35 tests ok.
- SKILL.md body words 3842 before, 3857 after.

## Deviations

- Multi-line `from ai_kit_spec import (...)` in the adapter cli.py (line length).
- The pinned block-text list in `TestLiteBlockDocs` splits one long element into two adjacent literals (line length);
  a two-line `_flat` helper does the whitespace flattening.
- The clause's last part keeps the opening backtick of `` `"lite": true` `` so the joined clause equals the AGENTS.md
  line exactly (the plan's part list was quoting-ambiguous; `tests.test_rules_docs` pins equality).
