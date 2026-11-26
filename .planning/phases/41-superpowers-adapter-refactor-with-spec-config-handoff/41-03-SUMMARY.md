---
phase: 41-superpowers-adapter-refactor-with-spec-config-handoff
plan: 03
subsystem: ai-kit-spec-review (lane settings, config writer), ai-kit-spec-config (fallback question)
tags: [session-fallback, lane-settings, spec-config]
requires: [41-02]
provides:
  - "lane_settings.SESSION_FALLBACK_KEY = \"session_fallback\" (role-table flag of [lanes.policy.execute], kept out of LANE_FLAG_KEYS)"
  - "lane_settings.lane_session_fallback(config) -> bool: False when the execute table or key is absent; a non-boolean raises LaneSettingError `policy.execute: 'session_fallback' must be a boolean` (label set last)"
  - "config_io._execute_extra(extra, rejections): true kept, false dropped silently, anything else refused with `policy.execute.session_fallback: must be true or false; not written`"
  - "spec-config wizard step 9 asks the fallback question once (default no, only when the execute role holds a lane, kept across an order retry); config-file.md execute row with the revocation and layer sentence; SKILL.md NEVER bullet and Step 3 JSON shape with the yes-only qualification; headless.md item 7"
affects: [41-04]
key-files:
  modified:
    - skills/ai-kit-spec-review/ai_kit_spec/lane_settings.py
    - skills/ai-kit-spec-review/ai_kit_spec/config_io.py
    - tests/test_lane_settings.py
    - skills/ai-kit-spec-config/references/wizard-flow.md
    - skills/ai-kit-spec-config/references/config-file.md
    - skills/ai-kit-spec-config/SKILL.md
    - skills/ai-kit-spec-config/references/headless.md
    - tests/test_spec_config_flow_text.py
decisions:
  - "Follow-up ef20cd7: the NEVER bullet's reason said each flag records an owner decision 'about that lane'; session_fallback is a role-table flag, so the reason now says 'about that lane or role' (the bold part the test pins is unchanged)"
metrics:
  tasks: 2
  commits: 3
---

# Phase 41 Plan 03: session_fallback flag, reader, write rule and spec-config question Summary

The owner's opt-in to run a task on the session model when no execute lane is available is now one boolean,
`session_fallback = true` under `[lanes.policy.execute]`. One reader (`lane_settings.lane_session_fallback`) reads it through the
existing boolean rule (absent = off; a hand-written non-boolean raises with `policy.execute` named). The writer keeps only a
literal true, drops false and refuses anything else with the key named; a same-target `--replace` without the key revokes it, and a
project execute table replaces the user's. spec-config asks the question once at the end of wizard step 9, default no, and
documents the key in config-file.md, the NEVER line, the Step 3 JSON shape (with "only a yes adds `session_fallback`") and the
headless question list.

## Commits

| Task | Commit | Subject |
|------|--------|---------|
| 1 | dd4c5e0 | feat(41-03): add the session-model fallback flag, its reader and its write rule |
| 2 | f564549 | docs(41-03): spec-config asks for the session-model fallback and documents it |
| follow-up | ef20cd7 | docs(41-03): say the owner-flag rule covers the execute role's fallback flag |

Cross-AI lanes (pi, router-env/my-coding), one per task from the start, each AIKIT-XAI `status=ok attempts=1`: Task 1 215 s,
Task 2 63 s, follow-up 23 s.

## Verification (chunk executor, own runs)

- Acceptance: every grep of both tasks printed 1 (constant, reader, `_execute_extra`, `TestSessionFallback`, the replace and
  project-layer tests, the label-last dict, the wizard question, the NEVER phrase, the JSON shape, the config-file row and its
  revocation sentence, "only a yes adds", the headless phrase); both commit subjects as planned; plan base 4dc2201 recorded as a
  full sha; scope check from the plan base lists only `files_modified` paths; `session_fallback` typed in runtime code only in
  lane_settings.py; the model-literal baseline unchanged; `test_project_table_replaces_the_users` asserts True then False as planned.
- Every module that names spec-config files, two per call: test_spec_config_flow_text (40), test_ai_kit_spec_check_providers (32),
  test_role_orders (29), test_cross_ai_docs_text (40), test_ai_kit_spec_runtimes_table (63), test_cross_ai_skill_text (40),
  test_spec_chain_text (40), test_spec_config_catalog_text (6), test_spec_config_lane_json (6), test_skill_text_history (45), plus
  test_lane_settings (58), test_config_role_write (18), test_arch (118), test_ai_kit_spec_superpowers (175): each pair `2/2 modules passed`.
- The commit-deferred `tests.test_ai_kit_gsd_curated_config_matrix`: 35 tests ok in 156.0 s under the watchdog (not killed).
- Gates after the plan: unit + arch groups under the watchdog `202/202 modules passed` (peak 6, not killed); `make ruff`,
  `make pyright`, `make vulture`, `make pylint`, `make check-dogfood` exit 0 each (at f564549).
- ai-kit-spec-config SKILL.md body 6453 -> 6476 words after the follow-up (428 lines, unchanged count).

## Deviations

- Follow-up ef20cd7 (one sentence in SKILL.md, inside the plan's file list; see decisions).
