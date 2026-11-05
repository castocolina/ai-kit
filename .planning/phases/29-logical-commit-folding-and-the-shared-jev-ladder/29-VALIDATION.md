---
phase: "29"
slug: "logical-commit-folding-and-the-shared-jev-ladder"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-11-04"
audited: "2026-11-05T00:45:00Z"
---

# Phase 29 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | stdlib unittest through tools/run_unittest_parallel.py |
| **Config file** | tools/run_unittest_parallel.py group sets; tests/test_gate_scope.py |
| **Quick run command** | `python3 tools/run_unittest_parallel.py <touched test modules>` |
| **Full suite command** | `make test` |
| **Estimated runtime** | ~29 seconds (phase modules); ~75 seconds (`make test`) |

---

## Sampling Rate

- **After every task commit:** the commit hook runs the covering modules (tools/staged_mapper.py)
- **After every plan wave:** Run `python3 tools/run_unittest_parallel.py --group unit --group arch`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 29 seconds

---

## Requirement Coverage (SPEC acceptance → tests)

| # | Requirement | Covering tests (module: test) | Status |
|---|-------------|-------------------------------|--------|
| 1 | One written folding policy (FLOW-01) | test_arch: `test_folding_policy_states_every_rule`, `test_policy_rule_removal_is_caught`, `test_agents_md_points_to_the_folding_policy`; test_ai_kit_commit_fold: `test_points_to_policy`, `test_does_not_restate_policy` | ✅ COVERED |
| 2 | Fold a finished GSD plan (FLOW-01) | test_ai_kit_commit_fold: `test_two_features_fold_into_two_commits`; test_ai_kit_commit_fold_adapters: `test_sequential_plan_folds_into_two_commits`, `test_worktree_plans_keep_each_segment_tree_and_the_tracking_commit`; test_ai_kit_commit_fold_e2e (GSD capability run) | ✅ COVERED |
| 3 | Fold a finished superpowers plan (FLOW-01) | test_ai_kit_commit_fold_adapters: `test_two_feature_plan_folds_and_keeps_the_pre_plan_commit`, `test_single_commit_after_base_is_nothing_to_fold`; test_ai_kit_spec_superpowers: `test_documented_block_folds_the_two_features_above_the_pre_plan_commit` | ✅ COVERED |
| 4 | Tree proof and backup before the swap (FLOW-01) | test_ai_kit_commit_fold: `test_one_byte_wrong_segment_refuses_with_tree_mismatch`, `test_branch_moved_before_the_swap_deletes_the_new_tag`, `test_reused_backup_tag_survives_a_moved_branch`; test_arch: `test_reset_hard_flags_each_form` | ✅ COVERED |
| 5 | Never rewrite main or merged work (FLOW-01) | test_ai_kit_commit_fold: `test_range_commit_on_local_base_branch_refuses`, `test_range_commit_on_remote_base_branch_refuses`, `test_range_commit_on_merged_branch_refuses`, `test_pushed_unmerged_range_folds`, `test_root_commit_in_the_range_refuses_instead_of_crashing` | ✅ COVERED |
| 6 | A five-line subagent report (FLOW-01) | test_ai_kit_commit_fold: `test_every_outcome_and_reason_renders_the_five_line_report`, `test_checker_rejects_a_six_line_report_and_colour_codes`, `test_dispatches_subagent_with_inline_fallback` | ✅ COVERED |
| 7 | Grouping proposed by jev, decided by the agent (FLOW-01, JEV-06) | test_ai_kit_commit_fold: `test_no_jev_installed_the_rules_decide`, `test_real_jev_without_a_backend_the_rules_decide`, `test_jev_answer_decides_the_grouping`, `test_wrong_split_is_rejected_and_the_rules_decide` | ✅ COVERED |
| 8 | The ladder lives in jev-fast-decision (JEV-06) | test_ai_kit_gsd_spec_discuss: `test_scripts_define_no_ladder_or_client_lookup`; test_jev_fast_decision: `test_ladder_example_runs_through_the_client`, `test_detect_reports_closed_status_and_this_skills_client`, the re-pointed ladder tests | ✅ COVERED |
| 9 | Every caller chains jev as a black box (JEV-06) | spec-discuss `test_phase_range_runs_with_no_jev_installed`; fold `test_no_jev_installed_the_rules_decide`; goal-prompt `test_missing_client_never_calls_a_subprocess`; precompact `test_presummarize_with_no_client_anywhere_returns_none`; decision probe `test_copied_probe_jev_absent_everywhere_gives_empty`; test_arch: `test_no_cross_skill_reach_outside_the_allowlist`, `test_cross_skill_rule_flags_each_form`, `test_cross_skill_allowlist_rejects_a_new_entry` | ✅ COVERED |
| 10 | Caller text treats jev as a black box (JEV-06) | test_ai_kit_caller_text: `test_every_caller_text_names_no_backend_consent_or_probe`, `test_every_caller_skill_states_the_default_decides`, `test_scanner_flags_each_forbidden_term`, `test_scanner_finds_the_terms_in_real_jev_text`; judge bar: 29-JUDGE.md (JDG-04 met) | ✅ COVERED |

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 29-01-01..02 | 01 | 1 | FLOW-01 | T-29-01, T-29-03 | tree proofs and compare-and-swap before any ref write | unit | `python3 tools/run_unittest_parallel.py tests.test_ai_kit_commit_fold` | ✅ | ✅ green |
| 29-02-01..02 | 02 | 1 | FLOW-01 | T-29-25 | each policy rule pinned; no `reset --hard` | arch | `python3 tools/run_unittest_parallel.py tests.test_arch tests.test_ai_kit_project_rules_agents` | ✅ | ✅ green |
| 29-03-01..02 | 03 | 1 | JEV-06 | T-29-04..06 | scrubbed child env; field validation | unit | `python3 tools/run_unittest_parallel.py tests.test_jev_fast_decision tests.test_ai_kit_gsd_spec_discuss` | ✅ | ✅ green |
| 29-04-01..02 | 04 | 1 | JEV-06 | T-29-07, T-29-08 | fail-open probe, jev absent gives empty | unit | `python3 tools/run_unittest_parallel.py tests.test_precompact_core tests.test_claude_precompact tests.test_decision_probe` | ✅ | ✅ green |
| 29-05-01..02 | 05 | 1 | FLOW-01, JEV-06 | T-29-09, T-29-10 | judge lane writes only under tmp | judge | `python3 .planning/phases/29-logical-commit-folding-and-the-shared-jev-ladder/judge/parse.py base <judge> <skills>` | ✅ | ✅ recorded |
| 29-06-01..02 | 06 | 2 | FLOW-01 | T-29-02, T-29-26 | main/merged refusal; foreign merge refusal | unit | `python3 tools/run_unittest_parallel.py tests.test_ai_kit_commit_fold tests.test_arch` | ✅ | ✅ green |
| 29-07-01..02 | 07 | 2 | JEV-06 | T-29-14 | detect output reduced to booleans | unit | `python3 tools/run_unittest_parallel.py tests.test_ai_kit_spec_goal_prompt_host tests.test_ai_kit_spec_goal_prompt_golden` | ✅ | ✅ green |
| 29-08-01..02 | 08 | 2 | JEV-06 | T-29-15 | consent asked before any remote grant | unit | `python3 tools/run_unittest_parallel.py tests.test_jev_fast_decision tests.test_skill_evals_shape` | ✅ | ✅ green |
| 29-09-01..02 | 09 | 3 | FLOW-01 | T-29-27 | foreign-plan commits refuse `plan_not_contiguous` | unit | `python3 tools/run_unittest_parallel.py tests.test_ai_kit_commit_fold_adapters` | ✅ | ✅ green |
| 29-10-01..02 | 10 | 3 | FLOW-01, JEV-06 | T-29-11..13 | jev answer validated; rules fallback | unit | `python3 tools/run_unittest_parallel.py tests.test_ai_kit_commit_fold` | ✅ | ✅ green |
| 29-11-01..02 | 11 | 3 | JEV-06 | T-29-19 | summaries only to jev | unit | `python3 tools/run_unittest_parallel.py tests.test_ai_kit_gsd_spec_discuss tests.test_jev_fast_decision` | ✅ | ✅ green |
| 29-12-01..02 | 12 | 4 | FLOW-01 | T-29-16..18 | fixed argv, temp HOME/GSD_HOME | e2e | `uv run python tools/run_unittest_parallel.py tests.test_ai_kit_commit_fold_e2e` | ✅ | ✅ green (make test) |
| 29-13-01..02 | 13 | 5 | FLOW-01 | T-29-20, T-29-21 | FOLD_BASE recorded; no finishing-step push | unit | `python3 tools/run_unittest_parallel.py tests.test_ai_kit_spec_superpowers tests.test_ai_kit_commit_fold_adapters` | ✅ | ✅ green |
| 29-14-01..02 | 14 | 5 | FLOW-01, JEV-06 | T-29-28 | synthetic eval inputs only | unit | `python3 tools/run_unittest_parallel.py tests.test_skill_evals_shape` | ✅ | ✅ green |
| 29-15-01..03 | 15 | 6 | JEV-06, FLOW-01 | T-29-22, T-29-23 | frozen allowlist; non-vacuity per form | arch | `python3 tools/run_unittest_parallel.py tests.test_arch tests.test_ai_kit_caller_text` | ✅ | ✅ green |
| 29-16-01..02 | 16 | 7 | FLOW-01, JEV-06 | T-29-24 | fixes keep behaviour and tests | judge | `python3 tools/run_unittest_parallel.py tests.test_ai_kit_caller_text tests.test_skill_evals_shape tests.test_jev_fast_decision` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

Evidence: `tmp/phase29-verify/val_run.sh` (12 covering modules) exit 0, "12/12 modules passed"; `make test` exit 0 at d2855bc (84/84, 1/1, 6/6, 24/24, 1/1 modules).

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

All phase behaviors have automated verification. The owner confirmation of the amended D-09 (tip-only build
proof) is a decision, not a behavior; it is tracked in 29-UAT.md.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 29s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-11-05

## Validation Audit 2026-11-05

| Metric | Count |
|---|---|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
