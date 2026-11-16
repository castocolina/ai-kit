---
phase: 34-jev-backends-by-host-and-laya-calibration
verified: 2026-11-16T00:00:00Z
status: passed
score: 19/19 must-haves verified (9 SPEC requirements, 10 acceptance criteria; ROADMAP criteria 1-9 map onto them)
covered_files: [".planning/phases/34-jev-backends-by-host-and-laya-calibration/34-01-PLAN.md", ".planning/phases/34-jev-backends-by-host-and-laya-calibration/34-01-SUMMARY.md", ".planning/phases/34-jev-backends-by-host-and-laya-calibration/34-02-PLAN.md", ".planning/phases/34-jev-backends-by-host-and-laya-calibration/34-02-SUMMARY.md", ".planning/phases/34-jev-backends-by-host-and-laya-calibration/34-03-PLAN.md", ".planning/phases/34-jev-backends-by-host-and-laya-calibration/34-03-SUMMARY.md", ".planning/phases/34-jev-backends-by-host-and-laya-calibration/34-04-PLAN.md", ".planning/phases/34-jev-backends-by-host-and-laya-calibration/34-04-SUMMARY.md", ".planning/phases/34-jev-backends-by-host-and-laya-calibration/34-05-PLAN.md", ".planning/phases/34-jev-backends-by-host-and-laya-calibration/34-05-SUMMARY.md", ".planning/phases/34-jev-backends-by-host-and-laya-calibration/34-06-PLAN.md", ".planning/phases/34-jev-backends-by-host-and-laya-calibration/34-06-SUMMARY.md", ".planning/phases/34-jev-backends-by-host-and-laya-calibration/34-07-PLAN.md", ".planning/phases/34-jev-backends-by-host-and-laya-calibration/34-07-SUMMARY.md", ".planning/phases/34-jev-backends-by-host-and-laya-calibration/34-08-PLAN.md", ".planning/phases/34-jev-backends-by-host-and-laya-calibration/34-08-SUMMARY.md", ".planning/phases/34-jev-backends-by-host-and-laya-calibration/34-09-PLAN.md", ".planning/phases/34-jev-backends-by-host-and-laya-calibration/34-09-SUMMARY.md", ".planning/phases/34-jev-backends-by-host-and-laya-calibration/34-10-PLAN.md", ".planning/phases/34-jev-backends-by-host-and-laya-calibration/34-10-SUMMARY.md", "skills/jev-fast-decision/SKILL.md", "skills/jev-fast-decision/backends/laya.md", "skills/jev-fast-decision/backends/typesafe.md", "skills/jev-fast-decision/reference.md", "skills/jev-fast-decision/scripts/eval_cases.py", "skills/jev-fast-decision/scripts/jev_config.py", "skills/jev-fast-decision/scripts/jev_ladder.py", "skills/jev-fast-decision/scripts/jev_learn.py", "skills/jev-fast-decision/scripts/jev_review.py", "tests/test_config_dir_parity.py", "tests/test_jev_config.py", "tests/test_jev_config_parity.py", "tests/test_jev_fast_decision.py", "tests/test_jev_fast_decision_guard.py", "tests/test_jev_learn.py", "tests/test_jev_typesafe_models.py", "tests/test_precompact_core.py", "tools/hooks/precompact_core.py", "tools/judge_loop.py"]
covered_digest: "v4:sha256:73819f291d79e43082c2359580613f7a5093111d320a488e23200dd350dd5f6b"
behavior_unverified: 0
overrides_applied: 0
advisory:
  - finding: "Judge loop 34 round 3 open high D8-1: SKILL.md:25-27 ladder example item has no `context`; the client answers it invalid_input / empty_context"
    category: other
    reason: "Reproduced here (tmp/auto/r325/c34/r3-d81-probe.py, rc 0, items.c1 = {decided_by: own_reasoning, error: invalid_input, reason: empty_context}). Round 3 is the last under the three-round cap and the bar is met (grade B or better), so it goes to the owner and does not gate. Fix: add a `context` to the example item."
    evidence_status: "reproduced; not a SPEC requirement"
  - finding: "Judge loop 34 round 3 open high D8-2: reference.md:36-38 screen example uses a relative `scripts/jev_review.py` path and a `<git rev-parse HEAD>` placeholder"
    category: other
    reason: "Owner decision under the judge cap; not a SPEC requirement. Fix: use the `<skill-dir>` form from SKILL.md and say how to fill reviewed_head."
    evidence_status: "read at reference.md:35-43; not executed"
---

# Phase 34: jev backends by host and Laya calibration Verification Report

**Phase Goal:** jev picks its backend per host from ai-kit's config, with the home-file key strictly last, and Laya's
accuracy is measured against its floor (SPEC goal adds: version and capabilities learned once per Laya version, TypeSafe
model awareness, a knob for every skill, no Zen, no delegation).
**Verified:** 2026-11-16 at HEAD `479ca2c` on `gsd/phase-34-jev-backends-by-host-and-laya-calibration` (working tree clean)
**Status:** passed
**Re-verification:** No (initial verification)

## Goal Achievement

### SPEC requirements

| # | Requirement | Status | Evidence |
| --- | --- | --- | --- |
| R1 | Backend per host from `[jev] laya_url`, env overrides, first-run question, key order (JEV-01) | VERIFIED | `jev_config.laya_url_setting`/`knob` (`jev_config.py:714-752`), `jev_review._laya_url_source`/`_laya_url` (`jev_review.py:620-656`): env, project, user, legacy loopback `JEV_API_URL`, default. `_laya_learn` sets `needs_answer: ["laya_url"]` only when source is `default` and Laya does not answer (`jev_review.py:734-741`). Key hint names the multiplexer (`jev_review.py:1100-1102`); home-file `~/.mycreds` kept last with recorded reason (`reference.md:172`, `jev_review.py:919`). Tests pass: `test_url_order_env_project_user_default`, `test_env_override_beats_config`, `test_first_run_question_answered_and_declined`, `test_configured_default_counts_as_configured`, `test_two_writers_keep_one_answer`, `test_malformed_url_is_a_probe_error`, `test_probe_key_hint_without_env_key`, `test_probe_labels_key_sources_and_never_prints_a_value`, off-loopback consent tests (`tests/test_jev_config.py`, `tests/test_jev_fast_decision.py`). |
| R2 | Laya version at the configured address and server fingerprint (JEV-10) | VERIFIED | `_laya_learn` reads `/health` and `/openapi.json` (`jev_review.py:751-759`) into `jev_learn.learn_laya`. Tests: `test_version_source_order` (server 0.5.0 / config 0.4.27 / `not_exposed` + `fp:` key), `test_route_or_revision_change_is_a_new_fingerprint`, `test_same_version_new_fingerprint_is_changed`, `test_unreachable_laya_reports_no_version`, `test_openapi_unreadable_while_health_answers_has_no_fingerprint`, idle-reuse cases (`tests/test_jev_learn.py:166-360`, `662-683`). Live: calibration record server block `version_source: not_exposed`, fingerprint `f46ef21b10a1` (`tmp/p34/09/calibration-record.json`). |
| R3 | Capability record keyed by version or fingerprint, fetched once when unknown (JEV-10) | VERIFIED | `_public_get` keyless, https/loopback only, 5 s, 1 MiB, no redirect (`jev_review.py:695-723`). Tests: `test_unknown_version_fetches_once_and_records`, `test_known_key_never_fetches`, `test_failed_fetch_keeps_records_and_says_so`, `test_no_published_notes`, `test_invalid_utf8_is_replaced_and_stored_as_text`, `test_parallel_writers_leave_one_entry`, `test_verified_features_are_never_reported_new`, `test_new_upstream_feature_keeps_the_cell`, `test_check_updates_refreshes_the_known_key`, `test_probe_under_a_deadline_never_fetches`, `test_answer_path_never_fetches`, `test_probe_and_fetch_carry_no_key`. |
| R4 | TypeSafe model id / unknown feature triggers one doc-flow fetch (JEV-12) | VERIFIED | `jev_learn.py:47-49` doc URLs (llms.txt, changelog.md, models.md); answer path writes only a local pending note (`_typesafe_note_model`, `_note_models`). Tests (`tests/test_jev_typesafe_models.py`): `test_new_model_id_is_noted_then_read_once`, `test_known_alias_and_missing_ids_record_nothing`, `test_failed_fetch_keeps_ids_pending`, `test_unknown_primitive_or_option_triggers_one_doc_read`, `test_answer_notes_a_new_model_id_without_fetching`, `test_typesafe_docs_fetch_carries_no_key`. Doc contract: `test_doc_pointer_both_branches` pins SKILL.md:58. Installed-skill pointer is agent-facing per D-09 (SKILL.md:58), not fetched by code. |
| R5 | Laya calibration on the owner's version, how-to, opencode lane re-judged (JEV-03) | VERIFIED | `backends/laya.md:59-73` record: date 2026-11-15, host 127.0.0.1, version not exposed, fp `f46ef21b10a1`, revision english `55cf4c4e...`, n 32, accuracy 0.56, confident 50%, fallback 0.69, min_confidence 0.7 kept, proposal null, no upgrade step. Raw files match (`tmp/p34/09/calibration-record.json`: n 32, accuracy 0.5556, accuracy_when_not_fallback 0.5, fallback_rate 0.6875; `calibrate-stdout.txt`: `{"JEV_MIN_CONFIDENCE": {"laya": null}}`; mtimes 2026-11-15 21:02). How-to `reference.md:141-148`, linked from `laya.md:53`. Opencode judge lane re-judged: loop 34 judges are `opencode:router-env/my-referee-one` and `-two`. Commit 9a1f654 exists. Test `test_doc_calibration_record` passes. |
| R6 | SKILL.md and laya.md state the confident-answer limit with numbers and date (JEV-03) | VERIFIED | `SKILL.md:40` ("32 cases ... 50%"), date in trailing `SKILL.md:62` (`## Evidence`, per the repo rule that the main flow holds no date, enforced by `tests/test_skill_text_history.py`); `laya.md:53` with date 2026-11-15. Test `test_doc_limit_sentence_in_skill_and_laya_backend` passes. |
| R7 | `[jev] enabled` knob for every skill, asked once when absent (JEV-07) | VERIFIED | `jev_config.knob` (`jev_config.py:714-733`): env both ways, project over user, absent on + `needs_answer`, broken file fails closed. Callers no longer force `GSD_PATH_JEV=1`: `jev_ladder.py:441-451` and `precompact_core.client_env` (`tools/hooks/precompact_core.py:158-178`) forward only the user's switch or `0` from `knob_off`. Tests: `test_knob_*` (5), `test_knob_off_in_config_disables_probe_and_screen`, `test_knob_absent_is_on_and_asked_once`, `test_ladder_knob_off_is_own_reasoning`, `test_ask_jev_knob_off_returns_own_reasoning` (judge_loop), `test_user_config_knob_off_reaches_the_hook_child`, `test_session_switch_off_turns_the_hook_off`, `test_check_updates_is_disabled_with_the_knob_off`. |
| R8 | MCP decision record and shared-state spike record (JEV-11) | VERIFIED | `laya.md:55-57` names all five bypassed safeguards; `reference.md:150-156` dated spike (merged 8/8 mean top 0.95, shared 8/8 mean top 0.87, jev-1.14.0) matches `tmp/p34/09/spike.json`. Tests `test_doc_mcp_decision`, `test_doc_spike_record` pass. |
| R9 | No Zen, no delegation guard; judge bar (JEV-13, JDG-04 part) | VERIFIED | `tests/test_jev_fast_decision_guard.py` scans every .py/.md/.json/.jsonl in the skill for Zen, opencode-as-backend, tools-installer, delegation sentences, and package/container tool strings in code; 7 tests pass incl. non-vacuity (`test_guard_flags_each_violation`, `test_empty_tree_passes`). Judge: `judge_loop.py check ... --gate` rc 0: "loop 34 round 3 (rounds 3); judges opencode:router-env/my-referee-one, opencode:router-env/my-referee-two; worst 92.0 A; critical 0; high 2; bar met: grade B or better; lowest percent 88.8, loop 32.1 base 86.4; digest current". |

### Acceptance criteria

| # | Criterion | Status | Evidence |
| --- | --- | --- | --- |
| AC1 | Probe picks Laya from `[jev] laya_url` at any address, then TypeSafe, then home-file key; first-run question works | VERIFIED | R1 evidence; `test_consented_off_loopback_laya_answers`, `test_config_set_then_probe_finds_laya_there`. |
| AC2 | Probe shows Laya version (exposed, configured, not exposed) and fingerprint | VERIFIED | R2 evidence; `test_probe_records_the_configured_version_once`. |
| AC3 | Unknown version or fingerprint triggers one public fetch and a record; known never fetches | VERIFIED | R3 evidence. |
| AC4 | New TypeSafe model id triggers one doc-flow fetch and a record | VERIFIED | R4 evidence; `test_probe_reads_the_docs_once_for_a_pending_id`. |
| AC5 | Calibration record carries version or fingerprint and revision; how-to; no upgrade step | VERIFIED | R5 evidence. |
| AC6 | SKILL.md and laya.md state the limit with the calibration's numbers | VERIFIED | R6 evidence. |
| AC7 | Knob on, off, absent behave as specified | VERIFIED | R7 evidence. |
| AC8 | MCP record and spike record exist | VERIFIED | R8 evidence. |
| AC9 | Guard passes; loop 34 meets the bar for jev-fast-decision | VERIFIED | R9 evidence. |
| AC10 | `make test` passes | VERIFIED | Caller's last full run (close-out part 1) rc 0 before d14b5e4/fdfe5e5. Those two commits touched only `tools/hooks/precompact_core.py`, `SKILL.md` and `tests/test_jev_fast_decision.py`; every covering module was re-run here at HEAD and passed (test_precompact_core, test_claude_precompact, test_precompact_shims_e2e, test_hook_registry_e2e, test_jev_fast_decision, test_jev_skill_install_e2e, test_skill_text_history, test_arch). A full `make test` at HEAD was not re-run (brief: caller runs it). |

**Score:** 19/19 truths verified (0 present, behavior-unverified)

### Prohibitions (all `verification: test`, all with wired enforcement)

| Prohibition | Enforcement | Status |
| --- | --- | --- |
| No key printed or sent with a capability fetch | `test_probe_and_fetch_carry_no_key`, `test_typesafe_docs_fetch_carries_no_key`, `test_probe_labels_key_sources_and_never_prints_a_value`; `_public_get` sends only User-Agent (`jev_review.py:705`) | VERIFIED |
| No capability cell turned verified from upstream text | `test_new_upstream_feature_keeps_the_cell`, `test_verified_features_are_never_reported_new` | VERIFIED |
| No upgrade, install or restart of Laya; no install of the official skill | guard `code_problems`/`text_problems` (`test_skill_tree_passes_the_guard`) | VERIFIED |
| No fetch on the per-item answer path | `test_answer_path_never_fetches` (fetch side effect raises), `test_answer_notes_a_new_model_id_without_fetching` | VERIFIED |

### Required Artifacts

| Artifact | Status | Details |
| --- | --- | --- |
| `skills/jev-fast-decision/scripts/jev_config.py` | VERIFIED | 752 lines; parity copy of Phase 33 reader (`test_jev_config_parity`: 54 copied definitions match); loaded by `jev_review.py:74` and `precompact_core._config_module`. |
| `skills/jev-fast-decision/scripts/jev_learn.py` | VERIFIED | 772 lines; loaded by `jev_review.py:75`, called from `_laya_learn` and `_typesafe_learn`. |
| `skills/jev-fast-decision/scripts/jev_review.py` | VERIFIED | probe, config set, check-updates, answer-path note wired. |
| `skills/jev-fast-decision/backends/laya.md`, `reference.md`, `SKILL.md` | VERIFIED | records, how-to, settings, limit sentence, MCP record, spike. |
| `tests/test_jev_fast_decision_guard.py` | VERIFIED | guard with non-vacuity cases. |

### Key Link Verification

| From | To | Via | Status |
| --- | --- | --- | --- |
| `jev_review.py` | `jev_config.py` | `_load_sibling` (line 74), `laya_url_setting`, `knob`, `jev_table` | WIRED |
| `jev_review.py` | `jev_learn.py` | `_load_sibling` (line 75), `learn_laya` at line 759 | WIRED |
| `precompact_core.py` | client's `jev_config.py` | `_config_module` + `knob_off` -> `client_env` GSD_PATH_JEV=0 | WIRED (tested) |
| `jev_ladder.py` | client | forwards only the user's `GSD_PATH_JEV` (lines 441-451) | WIRED |
| `laya.md` | `reference.md ## Calibration how-to` | link at laya.md:53 | WIRED |

### Data-Flow Trace (Level 4)

| Artifact | Data | Source | Real data | Status |
| --- | --- | --- | --- | --- |
| laya.md calibration record | n, accuracy, fp, revision | `tmp/p34/09/calibration-record.json` from a live `eval_cases.py --record` on 2026-11-15 | Yes (32 per-case results with `top` values) | FLOWING |
| reference.md spike record | merged/shared scores | `tmp/p34/09/spike.json` | Yes | FLOWING |

Note: the 2026-11-15 numbers equal the 2026-10-23 run to every digit (0.5556 / 0.5 / 0.6875). Plausible: the checkpoint is deterministic (`repeat_max_prob_diff` 0.0 in the old run) and the same 32 cases were used; the raw file carries fresh 2026-11-15 per-case results and the server fingerprint, so it is a new run, not a copy. Recorded as information.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| Phase test modules | `bash tmp/auto/r325/c34/verify/run_tests.sh` (11 modules: jev_config, jev_config_parity, jev_fast_decision, jev_fast_decision_guard, jev_learn, jev_typesafe_models, config_dir_parity, precompact_core, judge_loop, secret_shapes_copy_install, claude_precompact) | 11/11 passed (243 + 152 + 65 + 43 + 35 + 24 + 23 + 10 + 8 + 7 + 4 tests), rc 0 | PASS |
| Callers, doc rules, arch | `bash tmp/auto/r325/c34/verify/run_tests2.sh` (decision_probe, skill_text_history, skill_evals_shape, skill_frontmatter, arch, ai_kit_gsd_curated_config, banned_tool_mentions, ai_kit_caller_text) | 8/8 passed, rc 0; `git status --porcelain` empty | PASS |
| e2e for files changed after the last make test | `bash tmp/auto/r325/c34/verify/run_tests3.sh` (precompact_shims_e2e, jev_skill_install_e2e, hook_registry_e2e) | 3/3 passed, rc 0 | PASS |
| Judge gate | `bash tmp/auto/r325/c34/verify/judge_check.sh` | rc 0, bar met | PASS |
| D8-1 reproduction | `python3 tmp/auto/r325/c34/r3-d81-probe.py` (scratch HOME, closed port) | rc 0; c1 invalid_input / empty_context | reproduced (advisory) |
| Commits cited | `gsd-tools query verify.commits` (12 hashes) | all_valid true | PASS |

### Probe Execution

No `scripts/*/tests/probe-*.sh` declared by this phase. Live `jev_review.py --probe` was not run (brief: it would write the real jev state). Step 7c: not applicable.

### Requirements Coverage

| Requirement | Description | Status | Evidence |
| --- | --- | --- | --- |
| JEV-01 | backend per host, home-file key last, key hint, recorded reason | SATISFIED | R1 |
| JEV-03 | calibration on the running version, opencode lane re-judged, how-to, limit sentence | SATISFIED | R5, R6 |
| JEV-07 | `[jev] enabled` knob, asked once, off = not installed | SATISFIED | R7 |
| JEV-10 | version, fingerprint, fetch-once records, `--check-updates`, deadline probes never fetch | SATISFIED | R2, R3 |
| JEV-11 | MCP record and shared-state spike | SATISFIED | R8 |
| JEV-12 | TypeSafe model-id / feature doc flow once, off the answer path | SATISFIED | R4 |
| JEV-13 | no-Zen, no-delegation guard | SATISFIED | R9 |
| JDG-04 (phase 34 part) | loop 34 for `jev-fast-decision` | SATISFIED for loop 34 (round 3 at fdfe5e5: 92.0 A / 88.8 B, bar met, lowest 88.8 vs base 86.4; rounds 1 and 2 recorded in 0814ef2 and d9bad05). JDG-04 stays Pending (milestone-wide). | R9 |

No orphaned requirements: ROADMAP phase 34 lists exactly JEV-01, 03, 07, 10, 11, 12, 13.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| --- | --- | --- | --- | --- |
| (skill tree, precompact_core.py, judge_loop.py, phase test files) | - | TBD / FIXME / XXX | none found | - |
| (skill tree, phase test files) | - | machine-specific absolute paths | none found | - |
| `skills/jev-fast-decision/SKILL.md` | 25-27 | caller example item without `context` is refused (D8-1) | Warning (advisory, owner) | a caller copying the example gets `invalid_input` instead of an answer |
| `skills/jev-fast-decision/reference.md` | 36-38 | relative script path and `<git rev-parse HEAD>` placeholder (D8-2) | Warning (advisory, owner) | example needs adapting before use |

### Open items (owner, non-gating)

1. D8-1 (`SKILL.md:25`): add a `context` to the ladder example item. Reproduced above.
2. D8-2 (`reference.md:37`): screen example path and `reviewed_head` placeholder.
3. Accepted risks stand as recorded: `34-SECURITY.md` threats_open 0 (11 accepted); `34-REVIEW-FIX.md` 41 in scope, 35 fixed, 6 skipped with reasons.

### Test isolation (brief check)

`_ClientCase.setUp` patches `JR._public_get` to raise `OSError("network is off in unit tests")` and clears the env to a temp HOME/XDG with `JEV_LAYA_URL` on a closed port (`tests/test_jev_fast_decision.py:335-361`); tests that need upstream pages use in-process `JevStub` servers on loopback.

### Human Verification Required

None required by the SPEC. The two judge findings above are owner decisions under the three-round cap and do not gate.

### Gaps Summary

No gaps. Every SPEC requirement, acceptance criterion and prohibition has code, a passing test or a live record behind it. Not re-run here: a full `make test` at HEAD (covering modules for the two later commits were run instead), and a live per-host probe (forbidden against the real home).

---

_Verified: 2026-11-16_
_Verifier: Claude (gsd-verifier)_
