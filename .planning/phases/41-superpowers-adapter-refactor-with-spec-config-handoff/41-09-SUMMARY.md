---
phase: 41-superpowers-adapter-refactor-with-spec-config-handoff
plan: 09
subsystem: superpowers adapter (host-config audit around executor lanes)
tags: [superpowers, dispatch, host-config, observation]
requires: [41-08]
provides:
  - "ai_kit_spec/host_config.py: HOST_CONFIG_FILES (ten HOME-relative files), OBSERVATION, NOT_CHECKED, UNAVAILABLE, UNAVAILABLE_FOR, home, snapshot (stat only, never opens or lists), changed, unavailable, observation_lines"
  - "dispatch_superpowers_task: before/after snapshot in a try/finally, best-effort stderr lines, result key host_config_changed; SuperpowersDispatchSeams.env_fn"
  - "adapter subcommand host-config-audit --snapshot <file> / --compare <file> (every failure is an exit-0 observation)"
  - "references/dispatch-external-cli.md `## Host-config audit`; one SKILL.md native line with the recipe"
affects: [41-10, 41-14]
key-files:
  created:
    - skills/ai-kit-spec-review/ai_kit_spec/host_config.py
    - tests/test_host_config_audit.py
  modified:
    - skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/dispatch_injection.py
    - skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/cli.py
    - skills/ai-kit-spec-execute-superpowers/references/dispatch-external-cli.md
    - skills/ai-kit-spec-execute-superpowers/SKILL.md
    - tests/test_ai_kit_spec_superpowers.py
    - tests/test_dispatch_guidance_gates.py
    - Makefile
    - .pre-commit-config.yaml
decisions:
  - "The audit is an observation only: it never changes a return code, a classification or a dispatch exception, never reads a host config's contents and never lists a folder."
metrics:
  tasks: 3
  commits: 3
---

# Phase 41 Plan 09: host-config audit around executor lanes Summary

Before and after each external executor lane, `dispatch_superpowers_task` records the modification times of ten real host-config
files under the lane's HOME and reports each changed file as an observation (stderr line plus `host_config_changed` in the
result), with a closing line that config folders moved by environment variables are not checked. A stat error is reported as
`audit unavailable`, never as a change. A native dispatch runs the same audit through `host-config-audit --snapshot/--compare`,
described once in the external-CLI reference and in one SKILL.md native line.

## Commits

| Task | Commit | Subject |
|------|--------|---------|
| 1 | c0f1ebb | feat(41-09): report real host-config changes made during an executor lane |
| 2 | 4dd08dc | feat(41-09): host-config-audit snapshot and compare for a native dispatch |
| 3 | 0ec35ba | docs(41-09): describe the host-config audit once and point the native branch at it |

Cross-AI lanes (pi, router-env/my-coding), one per task from per-task prompts with checked anchors
(`tmp/run-2026-11-23/anchors-41-09.md`), each AIKIT-XAI `status=ok attempts=1`: Task 1 438 s (hook full unit+arch 228/228 +
uv 23/23, Makefile staged), Task 2 130 s (hook 25/25 + uv 1/1), Task 3 80 s (hook 25/25 + uv 1/1). Task 1's hook deferred
`tests.test_ai_kit_gsd_curated_config_matrix` to push.

## Verification (chunk executor, own runs)

- Task 1: five `def` lines in host_config.py; `contextlib.suppress(OSError)` 1 and `host_config.snapshot` 2 in dispatch_injection.py;
  no `listdir`/`os.walk`/`scandir` and no `open(`/`read` in host_config.py (stat only); Makefile names the new module;
  `seams_check.py`: `seams check: ok 5`.
- Task 2: `"host-config-audit"` 2 and `host-config audit unavailable` 1 in cli.py; 12 tests after Task 2, 14 after Task 3.
- Task 3: `## Host-config audit` 1 in the reference; snapshot command 1 and the reference link 1 in SKILL.md, on the docs-tested
  line; no listed path in SKILL.md; SKILL.md numstat 1/1 (no new line).
- Modules: host_config_audit 14, ai_kit_spec_superpowers 175, dispatch_guidance_gates 30, gate_scope 62, skill_text_history 45,
  adapter_single_definitions 9, arch 118, arch_hardcoded_models 23, lane_settings 58: all ok.
- Gates after the plan: unit + arch groups under the watchdog `205/205 modules passed` (peak 7, not killed); `make ruff`,
  `make pyright`, `make vulture`, `make pylint`, `make check-dogfood` exit 0 each (`check-dogfood: ok`; judge stale-digest and
  facts-drift notes only).
- Deferred e2e: `tests.test_ai_kit_gsd_curated_config_matrix` under the watchdog, 35 tests ok in 300.2 s, `1/1 modules passed`
  (guard exit 0, not killed; slower than its recorded 146 s, the module is over the commit budget either way).
- SKILL.md (ai-kit-spec-execute-superpowers) body: 3679 -> 3763 words, 290 -> 290 lines.

## Deviations

- Task 1: `assert result is not None` before `return result` in `dispatch_superpowers_task` (pyright narrowing of the
  `result = None` start value; `dispatch_execute` always returns a dict, and a dispatch exception propagates before the assert).
- Task 1: the two `dispatch_superpowers_task(request, guidance, seams)` calls in tests/test_dispatch_guidance_gates.py pass
  `seams=seams` as a keyword so the plan's seams check sees them (same behaviour; anchor note).
- Task 2: the snapshot-shape check lives in two small helpers, `_is_audit_value` and `_is_audit_snapshot` (same behaviour as
  the plan's inline check).
- The plan put SKILL.md at about 298 lines; it was 290 and stays 290.
