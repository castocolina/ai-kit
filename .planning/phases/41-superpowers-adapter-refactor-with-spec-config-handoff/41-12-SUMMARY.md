---
phase: 41-superpowers-adapter-refactor-with-spec-config-handoff
plan: 12
subsystem: superpowers adapter (evals, single-home pins, README)
tags: [superpowers, evals, doc-contract, readme]
requires: [41-11]
provides:
  - "evals.json: 18 evals; new precise-session-fallback-runs-native, edge-escalation-flags-off-keeps-lane, edge-flagged-lane-quota-switch, precise-host-config-audit-observation"
  - "eval rosters evals/files/session-fallback/, escalation-off/, flagged-quota/ (each project/aikit/config.toml, placeholder models)"
  - "tests/test_adapter_single_definitions.py: MARKERS +## Host-config audit, RULES +6 single-home fragments, LINKS +escalation.md and dispatch-external-cli.md#host-config-audit, HOMES +dispatch-external-cli.md, class TestNewTopicHomes"
  - "README row of ai-kit-spec-execute-superpowers names the flag-gated escalation, session-model fallback, gates and commit guard, real-home guard limits, host-config audit and flagged-lane switch"
affects: [41-13, 41-14]
key-files:
  created:
    - skills/ai-kit-spec-execute-superpowers/evals/files/session-fallback/project/aikit/config.toml
    - skills/ai-kit-spec-execute-superpowers/evals/files/escalation-off/project/aikit/config.toml
    - skills/ai-kit-spec-execute-superpowers/evals/files/flagged-quota/project/aikit/config.toml
  modified:
    - skills/ai-kit-spec-execute-superpowers/evals/evals.json
    - tests/test_adapter_single_definitions.py
    - README.md
decisions:
  - "The gates-and-guard recipe pin is the recipe's own sentence (write `$RUN_DIR/gates.txt` with the project's gate commands -> SKILL.md), not `the one input recipe`: that label also sits in dispatch-external-cli.md's pointer, so the planned pin could never be single-home."
  - "Eval scripted outputs follow the code at HEAD: escalation-gate prints escalate, allowed, exclude and reason; external_cli injections carry effort, service_tier and pool; the session-fallback injection is session_fallback_injection's dict with fallback_note `host takes no model` (the alignment step plan 41-04 owed to this plan)."
metrics:
  tasks: 3
  commits: 3
---

# Phase 41 Plan 12: evals, single-home pins and README Summary

The adapter now ships four transcript-assessed evals for its new behaviour: the opt-in session-model fallback on a non-Claude
host, the fix round that stays on its lane when both escalation flags are off, the flagged-lane switch after a proven quota stop,
and the relay of host-config audit observations. Each scenario names the calls it fakes and their scripted output, taken from the
code and reference text at HEAD; three new eval rosters load and decide as scripted (checked with the real lane_settings and
escalation_gate functions). The single-definitions test pins one reference home for each new topic, with a non-vacuity case
that plants a second copy, and the README row describes the new behaviour with its limits.

## Commits

| Task | Commit | Subject |
|------|--------|---------|
| 1 | b0dd423 | test(41-12): evals for the session fallback, flag-gated escalation, flagged-lane switch and host-config audit |
| 2 | ccb264a | test(41-12): pin one reference home for each new adapter topic |
| 3 | 50d51c9 | docs(41-12): describe the adapter's flags, fallback, guard, audit and switch in the README |

Cross-AI lanes (pi, router-env/my-coding), one per task from the start with exact texts in `anchors-41-12.md`, each AIKIT-XAI
`status=ok attempts=1`: Task 1 71 s (hook 27/27), Task 2 65 s (hook 4/4), Task 3 49 s (hook 42/42).

## Verification (chunk executor, own runs)

- Acceptance: ids 18, the four new ids 4, `class TestNewTopicHomes` 1, the Host-config audit MARKERS row 1, module `^def ` 7
  (unchanged), README sentence 1, all three subjects as planned. Plan scope 23a9291..50d51c9 = the six `files_modified` paths;
  no phase, plan, decision or requirement id, date or PROVISIONAL in added lines; model-literal baseline unchanged; EXEC_PREAMBLE
  untouched; no SKILL.md or reference changed (adapter SKILL.md body 3789 words, 290 lines, before and after).
- Evals: the first 14 entries equal 23a9291's as objects, the last four equal the checked block; the audit eval quotes host_config.py's
  `OBSERVATION` and `NOT_CHECKED` texts and the fallback eval cli.py's `_FALLBACK_ON` text verbatim; every `/project/` eval carries the
  Setup step; each new roster is named by exactly one eval.
- Preflight (`tmp/run-2026-11-23/p41-12/preflight.py`, the test's own scanner): each of the six fragments gives exactly `[home]` and sits
  after its named section; SKILL.md holds none of `.copilot/mcp-config.json`, `SWITCH_INJECTION_JSON`, `## Host-config audit` and links
  all three homes.
- Modules, two per call, each `2/2 modules passed`: test_skill_evals_shape (6), test_arch_hardcoded_models (23),
  test_skill_text_history (45), test_spec_chain_text (40), test_adapter_single_definitions (11), test_ai_kit_spec_superpowers (180),
  test_cross_ai_docs_text (40), test_quota_policy_text (20), test_arch_no_grok_runtime (11), test_no_seed_refusal (12),
  test_spec_config_flow_text (41), test_skill_table (61).
- No e2e module was deferred: the staged mapper over the plan's paths selects only test_ai_kit_spec_goal_prompt_e2e among e2e
  modules, which is within the commit budget; the curated-config matrix is not selected.
- Gates after the plan (at 50d51c9): unit + arch groups under the watchdog `206/206 modules passed` (peak 8, not killed);
  `make ruff`, `make pyright`, `make vulture`, `make pylint`, `make check-dogfood` exit 0 each (`check-dogfood: ok`; the adapter's
  facts-drift note is expected until its judge loop).

## Deviations

- See decisions: the recipe pin and the code-matched scripted outputs.
- Lane a said the anchors file put an invisible character into `opencode`; the only non-ASCII character in that file is an em dash in a
  quoted heading, and the shipped TOML files are plain ASCII.
