---
phase: 41-superpowers-adapter-refactor-with-spec-config-handoff
verified: 2026-11-26T20:38:44Z
status: passed
score: 6/6 must-haves verified
covered_files: [".planning/REQUIREMENTS.md", ".planning/ROADMAP.md", ".planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-01-PLAN.md", ".planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-01-SUMMARY.md", ".planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-02-PLAN.md", ".planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-02-SUMMARY.md", ".planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-03-PLAN.md", ".planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-03-SUMMARY.md", ".planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-04-PLAN.md", ".planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-04-SUMMARY.md", ".planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-05-PLAN.md", ".planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-05-SUMMARY.md", ".planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-06-PLAN.md", ".planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-06-SUMMARY.md", ".planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-07-PLAN.md", ".planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-07-SUMMARY.md", ".planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-08-PLAN.md", ".planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-08-SUMMARY.md", ".planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-09-PLAN.md", ".planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-09-SUMMARY.md", ".planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-10-PLAN.md", ".planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-10-SUMMARY.md", ".planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-11-PLAN.md", ".planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-11-SUMMARY.md", ".planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-12-PLAN.md", ".planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-12-SUMMARY.md", ".planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-13-PLAN.md", ".planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-13-SUMMARY.md", ".planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-14-PLAN.md", ".planning/phases/41-superpowers-adapter-refactor-with-spec-config-handoff/41-14-SUMMARY.md", ".planning/scripts/cross-ai.mjs", ".pre-commit-config.yaml", "Makefile", "README.md", "skills/ai-kit-cross-ai/SKILL.md", "skills/ai-kit-cross-ai/references/execute-checks.md", "skills/ai-kit-cross-ai/references/setting-reasons.md", "skills/ai-kit-gsd-curated-config/SKILL.md", "skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai.py", "skills/ai-kit-gsd-curated-config/references/runner.md", "skills/ai-kit-spec-config/SKILL.md", "skills/ai-kit-spec-config/evals/evals.json", "skills/ai-kit-spec-config/references/check-only.md", "skills/ai-kit-spec-config/references/config-file.md", "skills/ai-kit-spec-config/references/free-lanes.md", "skills/ai-kit-spec-config/references/headless.md", "skills/ai-kit-spec-config/references/test-call.md", "skills/ai-kit-spec-config/references/wizard-flow.md", "skills/ai-kit-spec-config/references/write-confirmation.md", "skills/ai-kit-spec-execute-superpowers/SKILL.md", "skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/cli.py", "skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/dispatch_injection.py", "skills/ai-kit-spec-execute-superpowers/evals/evals.json", "skills/ai-kit-spec-execute-superpowers/evals/files/escalation-off/project/aikit/config.toml", "skills/ai-kit-spec-execute-superpowers/evals/files/flagged-quota/project/aikit/config.toml", "skills/ai-kit-spec-execute-superpowers/evals/files/session-fallback/project/aikit/config.toml", "skills/ai-kit-spec-execute-superpowers/references/config-check.md", "skills/ai-kit-spec-execute-superpowers/references/design-notes.md", "skills/ai-kit-spec-execute-superpowers/references/dispatch-external-cli.md", "skills/ai-kit-spec-execute-superpowers/references/escalation.md", "skills/ai-kit-spec-execute-superpowers/references/fold-step.md", "skills/ai-kit-spec-execute-superpowers/references/quota-wake.md", "skills/ai-kit-spec-execute-superpowers/references/resolution-stops.md", "skills/ai-kit-spec-execute-superpowers/references/session-wake.md", "skills/ai-kit-spec-execute-superpowers/references/start-step.md", "skills/ai-kit-spec-execute-superpowers/references/state-management.md", "skills/ai-kit-spec-review/ai_kit_spec/config_io.py", "skills/ai-kit-spec-review/ai_kit_spec/dispatch_guidance.py", "skills/ai-kit-spec-review/ai_kit_spec/execute_dispatch.py", "skills/ai-kit-spec-review/ai_kit_spec/host_config.py", "skills/ai-kit-spec-review/ai_kit_spec/lane_settings.py", "skills/ai-kit-spec-review/ai_kit_spec/lane_switch.py", "skills/ai-kit-spec-review/references/cross-ai-selftest.mjs", "skills/ai-kit-spec-review/references/cross-ai.mjs", "tests/fixtures/cross_ai_selftest_secs.json", "tests/fixtures/curated_config_v2/golden/claude-mvp-adaptive.json", "tests/fixtures/curated_config_v2/golden/claude-rigorous-adaptive.json", "tests/fixtures/curated_config_v2/golden/claude-standard-adaptive.json", "tests/fixtures/curated_config_v2/golden/codex-mvp-adaptive.json", "tests/fixtures/curated_config_v2/golden/codex-mvp-budget.json", "tests/fixtures/curated_config_v2/golden/codex-rigorous-adaptive.json", "tests/fixtures/curated_config_v2/golden/codex-standard-adaptive.json", "tests/fixtures/runner_describe_golden.json", "tests/test_adapter_escalation_flags.py", "tests/test_adapter_executor_switch.py", "tests/test_adapter_session_fallback.py", "tests/test_adapter_single_definitions.py", "tests/test_ai_kit_spec_check_providers.py", "tests/test_ai_kit_spec_superpowers.py", "tests/test_curated_config_script.py", "tests/test_dispatch_guidance_gates.py", "tests/test_host_config_audit.py", "tests/test_lane_failure_text.py", "tests/test_lane_settings.py", "tests/test_spec_chain_text.py", "tests/test_spec_config_flow_text.py", "tools/run_unittest_parallel.py"]
covered_digest: "v4:sha256:fad8f68bf0f5f33ece546ae66b126caf47170094050ed8a4db22d13a746e657d"
behavior_unverified: 0
overrides_applied: 0
human_verification: []
---

# Phase 41: Superpowers adapter refactor with spec-config handoff Verification Report

**Phase Goal:** The superpowers execute adapter has one resume path and one stop path, hands off to spec-config when unconfigured, and every executor brief carries the gates.
**Verified:** 2026-11-26T20:38:44Z, branch `gsd/phase-41-superpowers-adapter-refactor-with-spec-config-handoff`, HEAD f843b5e, tree clean
**Status:** passed
**Re-verification:** No (initial verification)

The closing-gate suites of 41-14 ran at dcea116. `git diff --name-only dcea116 HEAD` lists only `.planning/REQUIREMENTS.md`,
`.planning/ROADMAP.md`, `.planning/STATE.md`, `.planning/state.json` and `41-14-SUMMARY.md`. So that run's `make test` (exit
0; unit 203/203, unit-uv 3/3, integration 9/9, e2e 29/29, installer 48/0, arch 3/3), `make e2e-docker` PASS, `check-dogfood:
ok`, the installer dry run and the live re-check all apply to HEAD's code. The verifier did not re-run them. It did run the
focused modules and runner self-test cases listed under Behavioral Spot-Checks.

Owner decisions applied as given, not re-opened:
- EXE-09 is confirmed for execute lanes (2026-11-25).
- `EXEC_PREAMBLE` stays unchanged (2026-11-25; `cross-ai.mjs` diff touches only the guard and the template number).
- spec-config grade B is accepted for phase 41 (2026-11-26, backlog 999.35).
- referee-two is out of judge loops from loop 41.1 on.
- Orchestrator decisions (41-REVIEW Resolution): the round 4-5 switch stays inside the gate, and the session fallback does
  not run on a narrowed-empty candidate list.

## Goal Achievement

### Observable Truths (ROADMAP Phase 41 success criteria; SPEC R1-R10 and the plan truths as sub-evidence)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | SC1 / R1, R2: one pinned-resume path and one owner-stop path; the no-config handoff to spec-config is kept; escalation flags gate rounds 4 and 5 | ✓ VERIFIED | Single homes: `## Pinned resume` in `references/state-management.md`, `## Owner stop` in `references/resolution-stops.md`. SKILL.md links both anchors (`SKILL.md:33,152,154,178,198,209,211,220,239,248,266,288`). `tests/test_adapter_single_definitions.py` (11 pass) counts each marker once, keeps 15 rule phrases only in their home, resolves every anchor link, and fails on a planted second copy or a removed pointer (`:165,190,212`). `test_no_config_check_comes_first` and `test_kept_handoff_text` pin that the config-check block runs before the start step (`SKILL.md:101`). SKILL.md is 293 lines (cap 300). Flags: `lane_settings.escalation_candidates` (`lane_settings.py:202-216`) reads `lane_escalation` from the anchor and uses `_kind_matches` over the keys above it. `dispatch_injection.escalation_gate` (`:254-269`) returns `escalate` false with reason `off`/`no-target`, or the allowed keys. `cli._cmd_escalation_gate` (`cli.py:598-621`) writes both gate files atomically and prints the stays-on notice. Tests (32 pass): `test_model_flag_moves_only_to_same_runtime`, `test_runtime_flag_moves_only_to_another_runtime`, `test_both_flags_keep_todays_floor`, `test_both_off_keep_the_lane`, `test_flag_with_no_target_keeps_the_lane` (backstop), `test_non_boolean_flag_exits_2_with_the_key`, `test_anchor_dropped_from_the_roster_exits_3` (WR-04), `test_allowed_check_stops_on_a_key_outside_the_list` (runs the `escalation.md` block). The "14 existing evals still pass" clause is a human item (byte-unchanged and shape-valid only). |
| 2 | SC2 / R3: with no configured executor available and the fallback flag on, the task runs on the session model, with jev picking haiku or sonnet; with the flag off the error names spec-config | ✓ VERIFIED | Flag reader `lane_session_fallback` (`lane_settings.py:112-118`, `_bool_setting`, non-boolean raises with `policy.execute` named). Writer `config_io._execute_extra` (`config_io.py:1040-1048`): keeps true, drops false, refuses other values. spec-config asks the question in `references/wizard-flow.md:73`, default no, written only on a yes (NEVER rule `SKILL.md:32`). Adapter `cli._emit_or_fallback` (`cli.py:271-296`) runs only on `QuotaExhaustedError` or an empty candidate list (`:332-337,348-351`), never on `no_candidate` (`:338-341`, IN-06 decision), and never at fix round >= 4, with escalation keys or with `--no-fallback`. The picker `pick_session_model` (`dispatch_injection.py:216-238`) asks jev only on a Claude host, sends the summary only, and accepts `haiku`/`sonnet` only at or above `STABLE_TOP`. Flag off prints `_FALLBACK_OFF` naming ai-kit-spec-config (`cli.py:87`). Tests (27 + 58 pass): `test_flag_on_and_every_lane_out_runs_native`, `test_sole_quota_out_lane_triggers_the_fallback`, `test_available_lane_is_never_replaced`, `test_real_narrowing_to_no_candidate_is_never_replaced`, `test_flag_off_names_spec_config`, `test_confident_pick_sets_the_model`, `test_low_answer_keeps_the_session_model`, `test_needs_fallback_keeps_the_session_model`, `test_choice_outside_the_picks_is_discarded`, `test_payload_holds_only_the_summary`, `test_brief_text_never_reaches_jev`, `test_lane_settings.py:485 test_true_round_trips`. Sole blocked-pool lane: `test_adapter_executor_switch.py:285`. |
| 3 | SC3 / R4, R5: every executor brief (ai-kit's `dispatch_guidance.py`, per amendment 1) lists the unit and arch gates and the commit guard. Banner-safe verify lines, clean-tree exclusion of the owner config, `coverage=n/a` by design, one guard block on every path | ✓ VERIFIED | `build_gates_guidance` / `build_commit_guard_guidance` (`dispatch_guidance.py:77-123`) are caller-fed and return "" with no input. They are composed after failure reporting and before the output format (`:126-153`). (a) `GATES_FRAME` (`:21-25`) judges a gate by exit code alone. `test_tail_grep_line_is_framed_not_rewritten` (backstop). (b) The guard names `.aikit/config.toml` as a top-anchored literal pathspec (WR-01, 16114c4). A real-git test runs it from the root and from a subdirectory. Path validation sits beside the builder (`:84-101`, IN-02). (c) `test_compose_holds_no_task_block` (`test_dispatch_guidance_gates.py:393`); `dispatch-external-cli.md:59` states `coverage=n/a`. (d)/(e) No agent-branch regex in ai-kit code (`rg` over `skills/**/*.py,*.mjs`: none). `test_every_path_composes_the_native_print` (`:641`), `test_unpinned_resume_passes_the_recorded_files_to_the_dispatch` (`:664`), `test_pinned_resume_keeps_the_task_scalar` (`:683`) and `test_native_block_fails_when_print_fails` (`:690`) cover the first, fix-round, resumed and native paths. External path: `ExecuteDispatchSpec.gates_text/guard_text/owner_config_paths` reach `build_execute_guidance` (`execute_dispatch.py:77-94`). Native path: `print-guidance` (`cli.py:472-484`, `SKILL.md:250-255`). (f) Gate text source: `state-management.md#gates-and-guard-inputs`. Named tests: `test_braces_and_markup_stay_verbatim` (R4 encoding backstop), `test_supported_path_excludes_only_that_file` (WR-01, runs the printed command with real git from the root and from `sub/`), `test_order_is_fixed`, `test_default_composition_is_unchanged`, `test_dispatch_task_composes_both_blocks_once_in_order`, `test_fresh_start_clears_the_task_scalar` (WR-03). 32 + 182 tests pass. Limit: these path tests seed `gates.txt` and `guard.txt` themselves; writing them from the project's gate commands is controller prose (`SKILL.md:239`), see coincidental_reliance_items. `EXEC_PREAMBLE` is unchanged by owner decision. |
| 4 | SC4 / R6, R7: in an ai-kit checkout every executor lane runs with `AI_KIT_REFUSE_REAL_HOME=1`, and a lane that touches a host config is reported from before-and-after modification times | ✓ VERIFIED | Runner: `aiKitCheckout` (`cross-ai.mjs:5321-5331`) stops at the first `.git` and needs both markers. It is applied only for `mode === 'exec'` and overrides an inherited value (`:5764`). The template is bumped to 14. The live copy `.planning/scripts/cross-ai.mjs` holds template=14 and the guard (`check-dogfood: ok` at dcea116: pristine render). The verifier ran self-test cases `realhome-exec-checkout-root`, `-checkout-subdir`, `-inherited-zero`, `-linked-worktree`, `-plain-repo` (nested plain repo: unset), `-hosted` (herdr path, IN-05) and `realhome-review-checkout` (review mode: unset): `self-test ok`. A native subagent is reported as not applicable (`SKILL.md:248`, D-05). Audit: `host_config.py` lists the ten amendment-8 files, uses stat only, and is resolved against HOME. `dispatch_superpowers_task` snapshots around the external lane in a `finally` block, prints `OBSERVATION` lines and adds `host_config_changed`. It never changes the return code (`dispatch_injection.py:470-501`). The native path uses `host-config-audit --snapshot/--compare`, which always exits 0 (`cli.py:523-546`, `SKILL.md:248`). Tests (15 pass): `test_a_lane_that_touches_a_config_file_is_reported`, `test_a_lane_that_touches_nothing_reports_nothing`, `test_two_touched_files_are_reported_in_list_order`, `test_a_path_with_spaces_and_non_ascii_is_verbatim`, `test_a_listed_folder_is_never_read`, `test_a_failing_lane_keeps_its_return_code`, plus the CLI cases. |
| 5 | SC5 / R10: every SKILL.md this phase adds or materially changes meets the judge bar (JDG-04) | ✓ VERIFIED | Changed SKILL.md files: ai-kit-spec-execute-superpowers, ai-kit-spec-config, ai-kit-cross-ai (section 8 exception widened, amendment 9), and ai-kit-gsd-curated-config (one line, `template 13` -> `template 14`, not material). `python3 tools/judge_loop.py check .planning/judge` results: superpowers loop 41 r2 worst 88.0 B, lowest 84.0 vs loop 36 base 87.2; spec-config loop 41.1 r1 worst 86.4 B, lowest 86.4 vs loop 41 base 88.8; cross-ai loop 41 r1 worst 85.6 B vs loop 40 base 84.8. All three print `bar met: grade B or better`. The regression limit is 7.0 points (`judge_loop.py:1616-1634`); 3.2 and 2.4 are within it. Stale digests are by design: the last fix commits 2a914c7, 7e49979 and e00735a are ancestors of HEAD, `git log <fix>..HEAD -- skills/<skill>/` is empty for each, and each round folder holds `fixes.md`. Grade A for spec-config was the run's target, not the bar (owner accepted B, backlog 999.35). evals.json gains the four evals R10 names (`precise-session-fallback-runs-native`, `edge-escalation-flags-off-keeps-lane`, `edge-flagged-lane-quota-switch`, `precise-host-config-audit-observation`). They are transcript-assessed, not executed (human item). |
| 6 | SC6 / R8: a flagged execute lane on quota moves at once to a fallback of another pool; a blocked pool is skipped at selection and tried once after its time; an unflagged lane stops and reports; each case has a fake-lane fixture | ✓ VERIFIED | `lane_switch.fallback_outcome` (`lane_switch.py:204-216`) needs runner-proven quota (`quota_evidence`, `dispatch_injection.py:576`), a known execute lane and the `usage_limited` flag, then calls `next_lane` with role `execute`. `cli._cmd_executor_fallback` (`cli.py:642-660`) narrows to the task's `ladder_keys` and the repeatable exclude files. Blocked pool: `_blocked_pool_quota` (`cli.py:299-315`) through `lane_switch.blocked_cache_entries`, read only via `--blocked-status`. `--pool` reaches the runner for a flagged lane (`execute_dispatch.py:110-115`). Round 4-5 decision (CR-01, 981fab5): the gate's exclude file is a second exclude; with no gate file there is no switch (`dispatch-external-cli.md:177-190`). Tests (24 pass): `test_real_quota_69_and_75_move_a_flagged_lane`, `test_transient_69_and_75_never_switch`, `test_unflagged_lane_on_quota_stops_and_reports`, `test_no_eligible_fallback_reports_without_dispatch`, `test_flagged_lane_moves_to_the_first_unflagged_lane_of_another_pool`, `test_two_eligible_fallbacks_take_the_earlier_in_order`, `test_blocked_pool_lane_is_skipped`, `test_expired_pool_is_tried_once_by_the_first_eligible_lane`, `test_missing_node_or_bad_record_blocks_nothing`, `test_rounds_four_five_switch_stays_inside_the_gate`, `test_both_flags_off_switch_never_moves_the_stuck_lane`. The doc block itself runs under fakes in `test_ai_kit_spec_superpowers.py:3530-3647` (validated move, failed move keeps the original, round 4 with and without the gate file, stale answer removed). The owner's exception sentence is widened in ai-kit-cross-ai section 8 (diff read: it now names ai-kit-spec-review and ai-kit-spec-execute-superpowers, and section 6 points to it). |

**Score:** 6/6 truths verified (0 present, behavior-unverified; 0 uncertain)

**Plan truths and backstops.** Every `must_haves.truths` entry of 41-01 to 41-14 folds into one of the six criteria. Each
`verification: backstop` truth has a named test that passed in this run:
- R2 boundary: `test_flag_with_no_target_keeps_the_lane`, `test_no_target_prints_its_notice`.
- R3 boundary, empty, encoding and precision: `test_sole_quota_out_lane_triggers_the_fallback`,
  `test_flag_off_and_empty_config_ask_nothing`, `test_choice_outside_the_picks_is_discarded`,
  `test_needs_fallback_keeps_the_session_model`.
- R4 encoding and R5 precision: `test_braces_and_markup_stay_verbatim`, `test_tail_grep_line_is_framed_not_rewritten`.
- R6 adjacency and empty: self-test `realhome-exec-checkout-subdir`, `-linked-worktree`, `-inherited-zero`.
- R7 adjacency and encoding: `test_two_touched_files_are_reported_in_list_order`,
  `test_a_path_with_spaces_and_non_ascii_is_verbatim`.
- R8 adjacency and ordering: `test_flagged_lane_moves_to_the_first_unflagged_lane_of_another_pool`,
  `test_two_eligible_fallbacks_take_the_earlier_in_order`.
- 41-08 ordering: template=14 in both copies, and `check-dogfood` pristine render.

### Prohibitions

| Prohibition | Tier | Disposition | Enforcement evidence |
|-------------|------|-------------|----------------------|
| MUST NOT run the session-model fallback when its flag is off | test | enforced | `test_flag_off_names_spec_config`, `test_flag_off_and_empty_config_ask_nothing` |
| MUST NOT send code, diffs, file contents, config values or secrets to jev | test | enforced | `test_payload_holds_only_the_summary`, `test_brief_text_never_reaches_jev` |
| MUST NOT change today's behavior when jev is absent, errors or answers low | test | enforced | `test_jev_absent`, `test_failed_run_keeps_the_session_model`, `test_low_answer_keeps_the_session_model` |
| MUST NOT edit another framework's own prose or files | test | flagged: no wired check (fail-closed); one-off evidence clean | `git diff --name-only b7ff220d001c HEAD -- .claude docs/superpowers` prints nothing (run here); 41-14 scope check `scope: ok 129 files` |
| MUST NOT touch a real host config in any test; MUST NOT fail a lane on the audit alone | test | enforced | runner tripwire and baseline env (scratch HOME, `AI_KIT_REFUSE_REAL_HOME=1`); `test_a_failing_lane_keeps_its_return_code`; `host-config-audit` always exits 0 (`cli.py:523-546`) |
| MUST NOT hand-edit `.planning/scripts/cross-ai.mjs` or the goldens | test | enforced | `check-dogfood` pristine-render check, ok at dcea116 (runner copy unchanged since) |
| MUST NOT switch an unflagged lane | test | enforced | `test_unflagged_lane_on_quota_stops_and_reports`, `test_unflagged_lane_reads_no_record` |
| MUST NOT judge a project-rules skill, ai-kit-spec-execute, or a skill whose SKILL.md this phase did not change (41-13) | judgment | flagged: unverified-prohibition, human review recommended | Non-authoritative reading: not violated. Loop 41/41.1 records exist only for ai-kit-cross-ai, ai-kit-spec-config and ai-kit-spec-execute-superpowers, all with materially changed SKILL.md. ai-kit-gsd-curated-config's one-line template-number change was not judged. |

### Required Artifacts

`verify.artifacts` per plan: 41-01 to 41-03 and 41-05 to 41-13 all passed (exit 0); 41-14 declares none (exit 66, not
applicable); 41-04 exit 1 on one artifact, explained below.

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `ai_kit_spec/dispatch_guidance.py` | gates and guard builders | ✓ VERIFIED | used by `execute_dispatch.build_execute_guidance` and `cli._cmd_print_guidance` |
| `ai_kit_spec/host_config.py` | audit list, snapshot, compare | ✓ VERIFIED | used by `dispatch_superpowers_task` and `host-config-audit` |
| `ai_kit_spec/lane_settings.py` | `lane_session_fallback`, `escalation_candidates`, `_kind_matches` | ✓ VERIFIED | imported by `dispatch_injection.py:27` |
| `ai_kit_spec/lane_switch.py` | role-aware `next_lane`, `fallback_outcome` | ✓ VERIFIED | used by `cli._cmd_executor_fallback`, `_blocked_pool_quota` |
| `ai_kit_spec_superpowers/cli.py` | escalation-gate, executor-fallback, print-guidance, host-config-audit, fallback wrapper | ✓ VERIFIED | all registered in `_COMMANDS` (`cli.py:817-828`) and called from SKILL.md / references |
| `ai_kit_spec_superpowers/session_pick.py` (41-04) | jev session pick | ✓ VERIFIED (relocated) | Deleted by review fix WR-02 (91fbc53). `SESSION_PICKS`, `PICK_QUESTION` and `pick_session_model` now live in `dispatch_injection.py:208-238` and are called at `:247`. `rg session_pick skills tests` finds no stale import. |
| `references/cross-ai.mjs` + live copy | real-home guard, template 14 | ✓ VERIFIED | both copies carry `aiKitCheckout` |

### Key Link Verification

`verify.key-links`: all verified except four, each checked by hand.

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| dispatch_injection.py | lane_settings.py | escalation flags / fallback flag (41-02, 41-04) | ✓ WIRED | Pattern used look-around (not RE2). Manual check: `from ai_kit_spec.lane_settings import escalation_candidates, lane_session_fallback` (`:27`), used at `:245,262` |
| cli.py | dispatch_injection.py | session fallback (41-04) | ✓ WIRED | Pattern not RE2. Manual check: `session_fallback_injection` imported (`cli.py:73`), called at `:284` |
| .planning/scripts/cross-ai.mjs | references/cross-ai.mjs | `ensure-runner` re-render (41-08) | ✓ WIRED | The via text is a process name, not source. Copy header `template=14 sha256=46dcc357...`; guard present; `check-dogfood` pristine render ok |
| all other plan key links | | | ✓ WIRED | gsd-tools "Pattern found in source" |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| guidance text in a dispatch | `gates_text`, `guard_text`, `owner_config_paths` | `$RUN_DIR/gates.txt`, `guard.txt` -> `--gates-file/--guard-file/--owner-config` -> `_guidance_inputs` -> `SuperpowersDispatchGuidance` -> `ExecuteDispatchSpec` -> `build_dispatch_reinforcement_guidance` | yes | ✓ FLOWING |
| session-fallback injection | `session_fallback` flag | `.aikit/config.toml` via `cfg_resolve_quiet` -> `lane_session_fallback` | yes | ✓ FLOWING |
| executor switch | `usage_limited`, blocked-until record | roster via `cfg_resolve_quiet`; record via `cross-ai.mjs --blocked-status` | yes | ✓ FLOWING |
| audit report | `st_mtime_ns` per listed file | `os.stat` under HOME | yes | ✓ FLOWING |

### Behavioral Spot-Checks (run by this verifier)

All modules were run with `env TMPDIR=<repo>/tmp/run-2026-11-23/tmpdir python3 tools/run_unittest_parallel.py <two modules>`:

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| escalation gate, session fallback | `tests.test_adapter_escalation_flags tests.test_adapter_session_fallback` | 32 + 27 ran, 2/2 passed | ✓ PASS |
| executor switch, single definitions | `tests.test_adapter_executor_switch tests.test_adapter_single_definitions` | 24 + 11 ran, 2/2 passed | ✓ PASS |
| guidance, audit | `tests.test_dispatch_guidance_gates tests.test_host_config_audit` | 32 + 15 ran, 2/2 passed | ✓ PASS |
| adapter doc blocks, lane settings | `tests.test_ai_kit_spec_superpowers tests.test_lane_settings` | 182 + 58 ran, 2/2 passed | ✓ PASS |
| lane switch, spec-config text | `tests.test_lane_switch tests.test_spec_config_flow_text` | 30 + 41 ran, 2/2 passed | ✓ PASS |
| runner e2e, lane failure text | `tests.test_cross_ai_runner_e2e tests.test_lane_failure_text` | 28 + 32 ran, 2/2 passed | ✓ PASS |
| real-home guard | `AIKIT_XAI_SELFTEST_CASES=realhome-exec-checkout-root,...-checkout-subdir,...-inherited-zero,...-linked-worktree,...-plain-repo,...-hosted,realhome-review-checkout node skills/ai-kit-spec-review/references/cross-ai.mjs --self-test` | `self-test ok` | ✓ PASS |
| judge records | `python3 tools/judge_loop.py check .planning/judge` | three phase-41 skills `bar met: grade B or better`; stale digests only | ✓ PASS |

### Probe Execution

Step 7c: not applicable. No plan or SUMMARY declares a `scripts/*/tests/probe-*.sh` probe. The runner self-test cases above
are the runnable checks this phase declares.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| EXE-01 | 41-01, 41-02, 41-12 | one pinned-resume and one owner-stop path; spec-config handoff kept; flags gate rounds 4-5 | ✓ SATISFIED | Truth 1 |
| EXE-04 | 41-03, 41-04 | opt-in session-model fallback with jev pick; flag off names spec-config | ✓ SATISFIED | Truth 2 |
| EXE-05 | 41-05, 41-06 | brief lists gates and commit guard; banner, clean-tree, counter and allow-list items | ✓ SATISFIED | Truth 3 (meaning per SPEC amendments 1 and 6) |
| EXE-08 | 41-07, 41-08, 41-09 | real-home guard on every executor lane in a checkout; host-config audit | ✓ SATISFIED | Truth 4 |
| EXE-09 | 41-10, 41-11 | flagged executor lane on quota moves to another-pool fallback | ✓ SATISFIED | Truth 6 |
| JDG-04 | 41-13 | changed SKILL.md files meet the judge bar | ✓ SATISFIED | Truth 5 |

No orphaned requirement: REQUIREMENTS.md maps EXE-01, EXE-04, EXE-05, EXE-08 and EXE-09 to Phase 41 (`:1119-1127`). Every
one of them is claimed by a plan.

### Anti-Patterns Found

The scan for `TBD|FIXME|XXX` across the phase's changed skill, tool and test files (fixtures excluded) found nothing.

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `skills/ai-kit-spec-review/ai_kit_spec/dispatch_guidance.py` | 2-13, 54-56 | the module docstrings name GSD and superpowers as examples of caller-supplied text | ℹ️ Info | SPEC R4's acceptance says "no framework name appears in the module". `test_new_frames_name_no_framework` checks only the emitted frames, and the text sent to an implementer holds none. These docstrings predate the phase and are not guidance wording. |
| `skills/ai-kit-spec-config/evals/evals.json` | n/a | no eval for the new `session_fallback` question (`references/wizard-flow.md:73`) | ℹ️ Info | R10's eval list names only adapter evals; the question is pinned by `tests/test_spec_config_flow_text.py` |
| `skills/ai-kit-spec-review/ai_kit_spec/dispatch_guidance.py` | 115-122 | the owner-config "never stage" rule is an instruction only | ℹ️ Info | By design (SPEC amendment 6(b); `dispatch-external-cli.md:57` says nothing enforces it); the runner's informational `uncommitted_edits` finding is unchanged |

### Human Verification Required

No `<verify><human-check>` block exists in any of the 14 PLAN files (`rg human-check` over the phase folder: no match), so nothing was harvested from the plans.

#### 1. The 14 pre-existing adapter evals still pass

**Test:** Execute `casual-run-superpowers-plan`, `precise-external-cli-pair`, `precise-fold-after-review`,
`precise-start-before-first-task`, `edge-plan-without-fold-step`, `edge-fold-refused`, `edge-executing-plans-out-of-scope`,
`precise-no-config-chains-spec-config`, `precise-config-active-never-asks`, `edge-spec-config-missing-stops`,
`edge-no-way-to-ask-notice`, `edge-no-config-stop-answer`, `precise-no-config-once-native` and
`edge-review-only-roster-still-asks` (`skills/ai-kit-spec-execute-superpowers/evals/evals.json`).

How to run: no documented eval procedure was found (searched `docs/`, `README.md`, `AGENTS.md` and `tools/`; `tests/test_skill_evals_shape.py` checks shape only). Suggested procedure, not a project rule: run each eval in a fresh subagent
with the skill loaded:
1. Apply the eval's Setup in a scratch project.
2. Fake the host CLIs as scripted.
3. Use a scratch HOME with `AI_KIT_REFUSE_REAL_HOME=1`.
4. Grade the run against the eval's assertions.

**Expected:** every assertion holds.
**Why human:** SPEC R1 says these "pass unchanged". The verifier could only confirm that the entries are byte-unchanged and
shape-valid.

#### 2. The four new adapter evals

**Test:** Execute `precise-session-fallback-runs-native`, `edge-escalation-flags-off-keeps-lane`,
`edge-flagged-lane-quota-switch` and `precise-host-config-audit-observation`, the same way as item 1.
**Expected:** every assertion holds.
**Why human:** the tests prove the subcommands' choices and run the doc bash blocks under fakes. Only an eval run shows a
controller agent following the SKILL.md order end to end.

#### 3. The changed spec-config eval

**Test:** Execute `precise-escalation-only-with-two-lanes` (`skills/ai-kit-spec-config/evals/evals.json`), the same way.
**Expected:** the escalation question is asked only for the two-lane execute role, worded as a rounds 4-5 move above the
stuck lane; a flag is written only on an explicit yes.
**Why human:** this is eval behavior of a SKILL.md.

#### 4. The framework-files prohibition (test tier, flagged)

**Test:** Confirm that no file under `.claude/` (GSD agents, workflows, commands) or superpowers' own scripts changed in the phase range.
**Expected:** `git diff --name-only b7ff220d001c HEAD -- .claude docs/superpowers` prints nothing (it printed nothing in this run).
**Why human:** no wired repo check enforces this prohibition, so the fail-closed rule flags it.

#### 5. The judgment-tier prohibition of 41-13

**Test:** Confirm the reading in the Prohibitions table.
**Expected:** not violated.
**Why human:** the verifier's reading of a judgment-tier prohibition is advisory only.

### Resolution (orchestrator, 2026-11-26)

1. **The 14 existing adapter evals (R1), the four new adapter evals and the changed spec-config eval: executed.** Each ran
   in a scratch world with a scratch HOME and fake host CLIs, a fresh executor subagent and a fresh grader subagent
   (`tmp/evals-41/RESULTS.md`): 19/19 evals pass, 54 assertions PASS, 0 FAIL, 0 N/A. Two older prompts lacked the setup
   answer `references/config-check.md` asks for; their prompts now state it with the assertions unchanged (commit
   24b65d8), and both re-ran green. Two evals were re-run with a review that repeats its finding through round 5, so the
   rounds 4-5 path phase 41 changed was reached; both pass.
2. **No edits to another framework's files: satisfied.** `git diff --name-only 1420a53 HEAD -- .claude docs/superpowers`
   is empty.
3. **Judged-skill rule of 41-13: satisfied.** Loop 41 judged exactly the three skills whose SKILL.md changed
   (ai-kit-spec-execute-superpowers, ai-kit-spec-config, ai-kit-cross-ai); ai-kit-gsd-curated-config changed only its
   template number and was recorded `not judged`. Loop 41.1 judged ai-kit-spec-config alone at the owner's request.
4. **Advisory, framework names in `dispatch_guidance.py`: fixed.** The module docstrings name no framework, pinned by
   `test_module_source_names_no_framework`.
5. **Owner decisions recorded:** EXEC_PREAMBLE unchanged (2026-11-25); spec-config grade B accepted for phase 41
   (2026-11-26, backlog 999.35); referee-two out of judge loops from loop 41.1 on (2026-11-26).

### Gaps Summary

No gap found. Every ROADMAP criterion and SPEC requirement holds in code, with passing tests that exercise the behavior.
These tests cover the subcommand choices, and the executed doc bash blocks under fakes cover the state transitions.

What remains is eval execution:
- the "14 existing evals still pass" clause of R1;
- the four new adapter evals and the changed spec-config eval, which are transcript-assessed only;
- one judgment-tier prohibition and one unwired test-tier prohibition that need the owner's confirmation.

One advisory (fixture-only reliance) is recorded: the gates and guard files are seeded by the tests and written by controller prose in a real run.

These items are resolved below (Resolution), so the status is `passed`.

Review findings CR-01, WR-01 to WR-04 and IN-01 to IN-07 were each checked in the code or tests at HEAD and are fixed (IN-01 `dispatch_injection.py:494-496`; IN-02 `dispatch_guidance.py:84-107`; IN-03 `cli.py:574-595`; IN-05 self-test `realhome-exec-hosted` run here; IN-06 `cli.py:338-341`; IN-07 spec-config `SKILL.md:225`; WR-03 `config-check.md` block 1 and `test_fresh_start_clears_the_task_scalar`; IN-04 the real-git test and the renamed resume test):
- CR-01: the round 4-5 switch stays inside the gate, `test_rounds_four_five_switch_stays_inside_the_gate`.
- WR-01: a top-anchored literal pathspec, tested with real git.
- WR-02: `session_pick.py` folded into `dispatch_injection.py`, with no frozen-list rows added.
- WR-04: exit 3, `test_anchor_dropped_from_the_roster_exits_3`.

---

_Verified: 2026-11-26T20:38:44Z_
_Verifier: Claude (gsd-verifier)_
