---
phase: 41-superpowers-adapter-refactor-with-spec-config-handoff
plan: 05
subsystem: shared dispatch guidance (gates and commit-guard builders), superpowers adapter CLI (dispatch-task flags, print-guidance)
tags: [dispatch-guidance, gates, commit-guard, owner-config, superpowers]
requires: [41-04]
provides:
  - "dispatch_guidance.py: GATES_FRAME, GUARD_FRAME, build_gates_guidance(gates_text), build_commit_guard_guidance(guard_text, owner_config_paths=()); composer build_dispatch_reinforcement_guidance(resolved_label, format_block, gates_text=None, guard_text=None, owner_config_paths=()) in the order override, progress, failure reporting, gates, guard, format; default output unchanged"
  - "ExecuteDispatchSpec and SuperpowersDispatchGuidance: trailing gates_text, guard_text, owner_config_paths; build_execute_guidance passes them positionally"
  - "cli.py: dispatch-task --gates-file --guard-file --owner-config (repeatable); _read_optional, _unsupported_owner_config, _owner_config_paths, _guidance_inputs; stderr `ai-kit-spec: <flag>: unreadable file <path>` / `ai-kit-spec: --owner-config: unsupported path <path>`, exit 2, before any dispatch; print-guidance subcommand printing the same two blocks"
  - "tests/test_dispatch_guidance_gates.py: TestGateAndGuardBuilders, TestDispatchPath (CLI tracer through the real dispatch layers), TestGuidanceEdges, TestPrintGuidance; BAD_OWNER_CONFIGS, isolated_dispatch_env(test, root)"
affects: [41-06]
key-files:
  created:
    - tests/test_dispatch_guidance_gates.py
  modified:
    - skills/ai-kit-spec-review/ai_kit_spec/dispatch_guidance.py
    - skills/ai-kit-spec-review/ai_kit_spec/execute_dispatch.py
    - skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/dispatch_injection.py
    - skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/cli.py
    - Makefile
    - .pre-commit-config.yaml
decisions:
  - "Review hardening (orchestrator, recorded deviation): the owner-config check also rejects a first character other than a letter, digit or `.`, a backslash and any non-printable character. Probed with real git: `git status --porcelain -- . ':!_x.toml'` dies with `Unimplemented pathspec magic '_'` (also '-', '@', '~', '%', '='). BAD_OWNER_CONFIGS gains `_x.toml`, `@x/y.toml`, `a\\b.toml`, `a<newline>b.toml`; the exit-2 tests compare the whole stderr text. The plan text already covered the apostrophe, the leading colon, glob characters and unreadable or non-UTF-8 gates and guard files (exit 2 with a named line, no traceback). `--owner-config` paths are never opened, so for them 'missing or unreadable' is answered by the validation alone."
  - "build_commit_guard_guidance narrows guard_text with an assert for pyright (lane)."
metrics:
  tasks: 2
  commits: 2
---

# Phase 41 Plan 05: caller-fed gates and commit guard in the dispatch guidance Summary

The shared dispatch guidance now frames the caller's gate commands once, under one sentence that says a gate is judged by its exit
code alone, and a commit guard that keeps the owner's config files out of every commit and clean-tree check
(`git status --porcelain -- . ':!<path>'`). Both sit after failure reporting and before the output format, which stays last; with
neither input the composed text is byte-identical to before. The superpowers `dispatch-task` carries them through
`--gates-file`, `--guard-file` and `--owner-config`, and the new `print-guidance` prints the same two blocks for a native dispatch.
An unreadable or non-UTF-8 file and an unsupported owner-config path stop with a named stderr line and exit 2 before any dispatch.

## Commits

| Task | Commit | Subject |
|------|--------|---------|
| 1 | 96f93f4 | feat(41-05): pass caller-fed gates and a commit guard in the dispatch guidance |
| 2 | 864871f | feat(41-05): print the gates and guard blocks for a native dispatch |

Neutral commit before the plan: dbbdd2d docs(41) archives the 39.1 and 39.2 metric rows (STATE.md 293 -> 270 lines).
Cross-AI lanes (pi, router-env/my-coding), one per task from the start, each AIKIT-XAI `status=ok attempts=1`: Task 1 547 s (its
hook ran the full unit and arch groups because Makefile and .pre-commit-config.yaml were staged: 23/23 and 227/227; one ruff retry
for four E501 lines), Task 2 116 s (hook 24/24).

## Verification (chunk executor, own runs)

- Acceptance: Task 1 builders 2, frames 2, `owner_config_paths: tuple = ()` 1 in each of the two files, `"--owner-config"` 1,
  `unreadable file` 1, test names 2, `isolated_dispatch_env`/`BAD_OWNER_CONFIGS` 2, `os.path.isabs(` 1, `tail -n 3 | grep` 1,
  plan base dbbdd2d recorded as a full sha; Task 2 `"print-guidance"` 2, `TestPrintGuidance` 1; both subjects as planned. Scope
  check from the plan base: exactly the seven `files_modified` paths. Model-literal baseline unchanged.
- Modules, two per call: test_dispatch_guidance_gates (16 after Task 1; 20 after Task 2 in the lane), test_compose_for_lane (28),
  test_capability_entry_points (10), test_ai_kit_spec_env_scrub (3), test_arch (118), test_arch_hardcoded_models (23),
  test_skill_text_history (45), test_gate_scope (62), test_ai_kit_spec (705), test_ai_kit_spec_superpowers (175): each pair
  `2/2 modules passed`.
- Deferred e2e (the commit hook deferred it to push): test_ai_kit_gsd_curated_config_matrix run under the watchdog, 35 tests,
  `1/1 modules passed` (153.2 s, peak 0, not killed).
- Gates after the plan: unit + arch groups under the watchdog `204/204 modules passed` (peak 8, not killed); `make ruff`,
  `make pyright`, `make vulture`, `make pylint`, `make check-dogfood` exit 0 each (at 864871f).
- No SKILL.md changed in this plan.

## Deviations

- The owner-config hardening above (orchestrator decision from the plan review's open concerns), with its tests.
- Lane: the pyright narrowing assert in build_commit_guard_guidance.
