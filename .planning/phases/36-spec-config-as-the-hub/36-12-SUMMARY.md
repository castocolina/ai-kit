---
phase: 36-spec-config-as-the-hub
plan: 12
subsystem: spec-config
tags: [routing, no-formula, review-only-removed, exec-formula]

requires: [36-04, 36-08]
provides:
  - "routing.py: route `no_formula` replaces `review_only` (SKIP_ROUTES, _route_shape for a custom lane in exec mode, route() for a runner row with no exec formula), no_formula_detail, skip_note(subject, decision, runtime=None)"
  - "detection.Runtime no longer has `review_only`; commands.SUPPORTED_EXECUTE_CLIS derives from has_exec_formula (codex, copilot, cursor, opencode, pi)"

key-files:
  created: []
  modified:
    - skills/ai-kit-spec-review/ai_kit_spec/routing.py
    - skills/ai-kit-spec-review/ai_kit_spec/detection.py
    - skills/ai-kit-spec-review/ai_kit_spec/commands.py
    - skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/dispatch_injection.py
    - skills/ai-kit-spec-config/references/cli-model-selection.md
    - tests/test_ai_kit_spec_routing.py
    - tests/test_ai_kit_spec_superpowers.py

requirements-completed: []

executor: "cross-AI lane: pi router-env/my-coding, one run (771 s, AIKIT-XAI status=ok exit=0 attempts=1 cycles=0)"
---

# Phase 36 Plan 12: route no_formula

Two commits (pre-fold): `caf494b feat(36-12): route no_formula in place of the review-only flag` (task 1, hook 119/119) and `2b40a44 refactor(36-12): drop the review_only field; the execute set reads the exec formula` (task 2, hook 115/115); 7 files, +68 -35 over the two.

## Accomplishments

- A claude lane in exec mode on a non-Claude host, and a custom `command` lane in exec mode, route `no_formula`; the skip line names the fact (`the runner has no exec formula for <runtime> (<source>)`, or `a custom command lane runs in review mode only`); every other route's line is unchanged. A claude alias on a Claude Code host still routes `native` (new table row); a runner-less row keeps its inventory route (no grok test added; two existing expected strings changed from `review_only` to `no_formula`).
- `review_only` is gone from `detection.Runtime` and the claude row; the execute set and the inline selection snippet in `cli-model-selection.md` read `has_exec_formula`. No Python file under `skills/` names `review_only` any more (skill texts, the other reference files and `docs` that still name the old route belong to plans 36-16, 36-19, 36-24 and 36-28).
- `cli.py` is unchanged on purpose (plan live fact: `_route_reviewers` routes in review mode only, where `no_formula` cannot occur).

## Deviations and notes

- None. No file outside the plan's seven paths changed.

## Orchestrator verification (own runs, not the executor's claims)

- `python3 tools/run_unittest_parallel.py tests.test_ai_kit_spec tests.test_ai_kit_spec_runtimes_table tests.test_ai_kit_spec_routing tests.test_ai_kit_spec_superpowers tests.test_ai_kit_spec_check_providers tests.test_ai_kit_gsd_curated_config tests.test_ai_kit_spec_exec_formula_e2e tests.test_arch_hardcoded_models tests.test_arch tests.test_config_layers tests.test_ai_kit_spec_legacy_config`: exit 0, 11/11 modules (693, 62, 31, 170, 29, 104, 5, 14, 109, 54 and 24 tests).
- `make ruff`, `make pyright`, `make vulture`: Passed; pylint on the four source files: Passed. Read the whole source diff and the routing test diff against the plan.
- Real-config audit (marker-c3-p36-w4): host files only (claude job state, plugin store, codex daemon of another project) plus pi session logs.

## Self-Check: PASSED
