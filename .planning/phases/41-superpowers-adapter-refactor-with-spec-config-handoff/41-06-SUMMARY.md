---
phase: 41-superpowers-adapter-refactor-with-spec-config-handoff
plan: 06
subsystem: ai-kit-spec-execute-superpowers (one gates and guard recipe for both dispatch branches, coverage=n/a)
tags: [superpowers, dispatch-guidance, gates, commit-guard, coverage]
requires: [41-05]
provides:
  - "SKILL.md Step 3 `**Gates and commit guard (both branches; the one input recipe).**` line: gates.txt and guard.txt written at a task's first actual dispatch, keyed on the loaded scalar GUIDANCE_READY not being $TASK_N; reused unchanged by fix rounds, quota wakes and pinned re-dispatches; file flags only for existing files and --owner-config .aikit/config.toml always; the native branch (session fallback included) launches only when the print-guidance block exits 0, else the owner stop"
  - "SKILL.md native bash block: GUIDE_ARGS array and `python3 \"$SHIM\" print-guidance \"${GUIDE_ARGS[@]}\" > \"$RUN_DIR/guidance.txt\"`"
  - "dispatch-external-cli.md: Compose pointer to the recipe (owner-config line is an instruction, not enforcement) and the coverage=n/a note (caller text holding a task tag would be counted); Dispatch block passes \"${GUIDE_ARGS[@]}\""
  - "tests/test_dispatch_guidance_gates.py: TestGuidanceDocs (5 tests), TestGuidanceUniformity (5 tests: record-then-replay of the documented native, Dispatch and Restore blocks through a stub shim)"
affects: [41-12, 41-14]
key-files:
  modified:
    - skills/ai-kit-spec-execute-superpowers/SKILL.md
    - skills/ai-kit-spec-execute-superpowers/references/dispatch-external-cli.md
    - tests/test_dispatch_guidance_gates.py
decisions:
  - "Owner answered 2026-11-25: leave EXEC_PREAMBLE unchanged (the runner's execute preamble is not one of the briefs this plan edits; cross-ai.mjs untouched)."
metrics:
  tasks: 2
  commits: 2
---

# Phase 41 Plan 06: one gates and guard recipe for every dispatch path Summary

SKILL.md Step 3 now holds one input recipe for both branches: at a task's first actual dispatch the controller writes
`$RUN_DIR/gates.txt` (the instruction file's gate lines, else the plan's verify lines, else none) and `$RUN_DIR/guard.txt` (the
caller's guard text, else none) and records `GUIDANCE_READY=$TASK_N`; every later dispatch of the task reuses them unchanged.
The native branch runs a documented `print-guidance` block and launches only when it exits 0; the external Dispatch block
passes the same arguments, always with `--owner-config .aikit/config.toml`. dispatch-external-cli.md explains that the runner
reports `coverage=n/a` by design because ai-kit's own composed text adds no task block. A test runs the documented blocks against
a recording stub shim and replays each external call through the real dispatch layers: the first dispatch, an append fix round
and a pinned resume after the real Restore block all carry the native print verbatim, with each frame once and no task tag.

## Commits

| Task | Commit | Subject |
|------|--------|---------|
| 1 | b6a9e1b | docs(41-06): one gates and guard recipe for both dispatch branches; explain coverage=n/a |
| 2 | 9d2852e | test(41-06): pin identical gate and guard blocks on every documented dispatch path |

Cross-AI lanes (pi, router-env/my-coding), one per task from the start, each AIKIT-XAI `status=ok attempts=1`: Task 1 123 s,
Task 2 96 s.

## Verification (chunk executor, own runs)

- Acceptance: Task 1 `the one input recipe` 1, `print-guidance "${GUIDE_ARGS[@]}"` 1, `GUIDANCE_READY` 1, `launches only when
  that block exits 0` 1, `coverage=n/a` 1, `GUIDE_ARGS=(--owner-config .aikit/config.toml)` 1, SKILL.md 290 lines, no `<task`
  in dispatch-external-cli.md, plan base 9bd21a9 recorded as a full sha; Task 2 `TestGuidanceUniformity` 1, `state file does not
  match` 1, `AI_KIT_FAKE_SHIM_LOG` 2, the three names 3, `AI_KIT_FAKE_SHIM_EXIT` 2; both subjects as planned. Scope check from the
  plan base: exactly the three `files_modified` paths.
- Modules, two per call: test_dispatch_guidance_gates (30), test_ai_kit_spec_superpowers (175), test_arch (118),
  test_arch_hardcoded_models (23), test_adapter_single_definitions (9), test_skill_text_history (45), test_skill_evals_shape (6),
  test_gate_scope (62), test_ai_kit_caller_text (11), test_spec_chain_text (40), test_quota_policy_text (20),
  test_banned_tool_mentions (11): each pair `2/2 modules passed`. The staged mapper over the three paths selects no e2e module.
- Gates after the plan: unit + arch groups under the watchdog `204/204 modules passed` (peak 9, not killed); `make ruff`,
  `make pyright`, `make vulture`, `make pylint`, `make check-dogfood` exit 0 each (at 9d2852e).
- ai-kit-spec-execute-superpowers SKILL.md body 3426 -> 3679 words (281 -> 290 lines).

## Deviations

- None in the code. Open for code review: the unpinned-resume test writes `"injection_json": null` rather than leaving the key
  out; the Restore block treats both as no pinned injection (the test asserts no INJECTION_JSON.json is written).
