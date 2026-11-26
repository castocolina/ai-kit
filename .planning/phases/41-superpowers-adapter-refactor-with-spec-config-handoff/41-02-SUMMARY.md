---
phase: 41-superpowers-adapter-refactor-with-spec-config-handoff
plan: 02
subsystem: ai-kit-spec-execute-superpowers (rounds 4-5 escalation gate), ai-kit-spec-config (escalation question)
tags: [superpowers, escalation, lane-flags, spec-config]
requires: [41-01]
provides:
  - "lane_settings.escalation_candidates(role_lanes, anchor_key, above_keys) -> list[str] | None: keys above the anchor its flags allow (both on = every key above, one flag = escalation_target's kind rule nearest first, both off = None)"
  - "dispatch_injection.escalation_gate(execute_lanes, anchor_key, ladder_keys) -> {escalate, allowed, exclude, reason}; exclude = live execute roster keys plus saved ladder keys minus allowed; reason off / no-target / flags"
  - "CLI `escalation-gate --cwd --anchor-key --injection-file --out-dir`: exit 0 writes ESCALATION_EXCLUDE_JSON.json and ESCALATION_ALLOWED_JSON.json through temporary names; 2 for a non-boolean flag, an unreadable injection file or an unwritable folder; 3 with the STOP line for an empty or unknown anchor; stderr notice when the round stays on its lane"
  - "escalation.md runs the gate in place of the inline floor script and checks the re-resolved key against the allowed list (automatic round only); owner-directed paths drop a stale allowed file and check the owner's key"
  - "resolution-stops.md `### Rounds 4–5 re-resolution`: An unavailable kept lane, A re-resolved key the gate did not allow"
  - "spec-config wizard step 10, config-file.md and eval precise-escalation-only-with-two-lanes describe the flags as the fix-round 4-5 move the execute adapter reads (review lanes: recorded only)"
affects: [41-04, 41-14]
key-files:
  created:
    - tests/test_adapter_escalation_flags.py
  modified:
    - skills/ai-kit-spec-review/ai_kit_spec/lane_settings.py
    - skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/dispatch_injection.py
    - skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/cli.py
    - skills/ai-kit-spec-execute-superpowers/references/escalation.md
    - skills/ai-kit-spec-execute-superpowers/references/resolution-stops.md
    - skills/ai-kit-spec-execute-superpowers/references/state-management.md
    - skills/ai-kit-spec-execute-superpowers/SKILL.md
    - skills/ai-kit-spec-config/references/wizard-flow.md
    - skills/ai-kit-spec-config/references/config-file.md
    - skills/ai-kit-spec-config/evals/evals.json
    - tests/test_lane_settings.py
    - tests/test_ai_kit_spec_superpowers.py
    - tests/test_spec_config_flow_text.py
    - tests/test_ai_kit_spec_check_providers.py
    - Makefile
    - .pre-commit-config.yaml
decisions:
  - "test_unavailable_anchor_is_a_quota_stop puts lane-new in the roster as well: its fake resolver candidates hold lane-new, and a candidate missing from the live roster cannot be excluded by the gate (in a real run the resolver's candidates come from that roster); the case still proves quota_exhausted with both flags off"
  - "escalation.md's persistence sentence named the removed `$LADDER_KEYS_JSON`; a follow-up commit names `escalation-gate` and the saved `ladder_keys` instead"
metrics:
  tasks: 3
  commits: 4
---

# Phase 41 Plan 02: rounds 4-5 escalate only along the stuck lane's flags Summary

Fix rounds 4 and 5 now run `escalation-gate`, which reads the stuck (anchor) lane's `escalate_runtime` / `escalate_model` flags from
the live roster: with both on the round may take any key ranked above the anchor (the old capability floor); with one flag only keys
above it of that kind (another runtime, or the same runtime with another model), nearest first; with both off, or no matching key
above, the round stays on the anchor's own lane (a same-lane fix round, not a bump) and stderr says so. The gate's exclusion covers
every live roster key and every saved ladder key except the allowed ones, so a lane added since the ladder was saved is never picked,
and the escalation reference checks the re-resolved key against `ESCALATION_ALLOWED_JSON.json` before dispatching (owner-directed
picks drop a stale allowed file and check the owner's key instead). spec-config's escalation question and its config-file and eval
text now describe that fix-round move instead of calling the flags informational.

## Commits

| Task | Commit | Subject |
|------|--------|---------|
| 1 | 68f24da | feat(41-02): gate fix rounds 4 and 5 by the stuck lane's escalation flags |
| 2 | fd5d614 | docs(41-02): run the escalation gate at fix rounds 4 and 5 |
| 3 | f8f7de8 | docs(41-02): spec-config asks and says how the execute adapter reads the escalation flags |
| follow-up | 7c066a5 | docs(41-02): name the gate as the source of the escalation floor |

Cross-AI lanes (pi, router-env/my-coding), one per task from the start, each AIKIT-XAI `status=ok attempts=1`: Task 1 542 s,
Task 2 123 s, Task 3 63 s; one follow-up lane (42 s) for the stale variable name found in the diff review.

## Verification (chunk executor, own runs)

- Acceptance: `def escalation_candidates` 1, `def escalation_gate` 1, `"escalation-gate"` 2 and `"--injection-file"` 1 in cli.py,
  the `ALLOWED_READERS` row 1, `class TestGateFeedsTheResolver` 1, `def invoke_gate` 1; no flag string typed in
  dispatch_injection.py or cli.py; `escalation-gate --cwd` 1 and `ladder.index(stuck)` 0 in escalation.md;
  `ESCALATION_ALLOWED_JSON.json` 1 in resolution-stops.md and 1 in state-management.md; the two renamed or new tests present;
  "stored and informational" and "next lane of another runtime" gone from spec-config; wizard question, adapter sentence and
  review-lane sentence 1 each; eval phrase 2; evals.json valid JSON; SKILL.md stays at 279 lines; no `LADDER_KEYS_JSON` left;
  the model-literal baseline unchanged; scope check from the plan base 7012ccb lists only `files_modified` paths.
- `tests.test_adapter_escalation_flags` (28), `tests.test_lane_settings` (50), `tests.test_ai_kit_spec_superpowers` (175),
  `tests.test_adapter_single_definitions` (9), `tests.test_quota_policy_text` (20), `tests.test_spec_config_flow_text` (40),
  `tests.test_ai_kit_spec_check_providers` (32), `tests.test_skill_evals_shape` (6), `tests.test_skill_text_history` (45),
  `tests.test_gate_scope` (62), `tests.test_arch` (118), `tests.test_arch_hardcoded_models` (23): each `1/1 modules passed`.
- The commit-deferred `tests.test_ai_kit_gsd_curated_config_matrix` 35 tests ok (151.4 s, under the watchdog).
- Gates after the plan: unit + arch groups under the watchdog `202/202 modules passed` (peak 6 runner processes, not killed);
  `make ruff`, `make pyright`, `make vulture`, `make pylint`, `make check-dogfood` exit 0 each.

## Deviations

- Task 1 test fixture: `test_unavailable_anchor_is_a_quota_stop` roster includes `lane-new` (see decisions).
- The lanes wrapped `_GATE_STOP`, the parser help and `SUPER_DIR` to the 100-column limit and used `[*lanes(...), NEW]` for
  ruff RUF005; behaviour as planned.
- Follow-up commit 7c066a5 (one line in escalation.md, outside the plan's task text but inside its file list).
