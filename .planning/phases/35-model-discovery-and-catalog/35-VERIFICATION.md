---
phase: 35-model-discovery-and-catalog
verified: 2026-11-20T23:30:00Z
status: passed
score: 12/12 requirements, 8/8 roadmap criteria, 7/7 prohibitions verified in code with tests
covered_files:
  - ".planning/phases/35-model-discovery-and-catalog/35-01-PLAN.md"
  - ".planning/phases/35-model-discovery-and-catalog/35-01-SUMMARY.md"
  - ".planning/phases/35-model-discovery-and-catalog/35-02-PLAN.md"
  - ".planning/phases/35-model-discovery-and-catalog/35-02-SUMMARY.md"
  - ".planning/phases/35-model-discovery-and-catalog/35-03-PLAN.md"
  - ".planning/phases/35-model-discovery-and-catalog/35-03-SUMMARY.md"
  - ".planning/phases/35-model-discovery-and-catalog/35-04-PLAN.md"
  - ".planning/phases/35-model-discovery-and-catalog/35-04-SUMMARY.md"
  - ".planning/phases/35-model-discovery-and-catalog/35-05-PLAN.md"
  - ".planning/phases/35-model-discovery-and-catalog/35-05-SUMMARY.md"
  - ".planning/phases/35-model-discovery-and-catalog/35-06-PLAN.md"
  - ".planning/phases/35-model-discovery-and-catalog/35-06-SUMMARY.md"
  - ".planning/phases/35-model-discovery-and-catalog/35-07-PLAN.md"
  - ".planning/phases/35-model-discovery-and-catalog/35-07-SUMMARY.md"
  - ".planning/phases/35-model-discovery-and-catalog/35-08-PLAN.md"
  - ".planning/phases/35-model-discovery-and-catalog/35-08-SUMMARY.md"
  - ".planning/phases/35-model-discovery-and-catalog/35-09-PLAN.md"
  - ".planning/phases/35-model-discovery-and-catalog/35-09-SUMMARY.md"
  - ".planning/phases/35-model-discovery-and-catalog/35-10-PLAN.md"
  - ".planning/phases/35-model-discovery-and-catalog/35-10-SUMMARY.md"
  - ".planning/phases/35-model-discovery-and-catalog/35-11-PLAN.md"
  - ".planning/phases/35-model-discovery-and-catalog/35-11-SUMMARY.md"
  - ".planning/phases/35-model-discovery-and-catalog/35-12-PLAN.md"
  - ".planning/phases/35-model-discovery-and-catalog/35-12-SUMMARY.md"
  - ".planning/phases/35-model-discovery-and-catalog/35-13-PLAN.md"
  - ".planning/phases/35-model-discovery-and-catalog/35-13-SUMMARY.md"
  - ".planning/phases/35-model-discovery-and-catalog/35-14-PLAN.md"
  - ".planning/phases/35-model-discovery-and-catalog/35-14-SUMMARY.md"
  - ".planning/phases/35-model-discovery-and-catalog/35-15-PLAN.md"
  - ".planning/phases/35-model-discovery-and-catalog/35-15-SUMMARY.md"
  - ".planning/phases/35-model-discovery-and-catalog/35-16-PLAN.md"
  - ".planning/phases/35-model-discovery-and-catalog/35-16-SUMMARY.md"
  - ".planning/phases/35-model-discovery-and-catalog/35-17-PLAN.md"
  - ".planning/phases/35-model-discovery-and-catalog/35-17-SUMMARY.md"
  - ".planning/phases/35-model-discovery-and-catalog/35-18-PLAN.md"
  - ".planning/phases/35-model-discovery-and-catalog/35-18-SUMMARY.md"
  - ".planning/phases/35-model-discovery-and-catalog/35-19-PLAN.md"
  - ".planning/phases/35-model-discovery-and-catalog/35-19-SUMMARY.md"
  - ".planning/phases/35-model-discovery-and-catalog/35-20-PLAN.md"
  - ".planning/phases/35-model-discovery-and-catalog/35-20-SUMMARY.md"
  - ".planning/phases/35-model-discovery-and-catalog/35-21-PLAN.md"
  - ".planning/phases/35-model-discovery-and-catalog/35-21-SUMMARY.md"
  - ".planning/phases/35-model-discovery-and-catalog/35-22-PLAN.md"
  - ".planning/phases/35-model-discovery-and-catalog/35-22-SUMMARY.md"
  - ".planning/phases/35-model-discovery-and-catalog/35-23-PLAN.md"
  - ".planning/phases/35-model-discovery-and-catalog/35-23-SUMMARY.md"
  - ".planning/phases/35-model-discovery-and-catalog/35-24-PLAN.md"
  - ".planning/phases/35-model-discovery-and-catalog/35-24-SUMMARY.md"
  - ".planning/phases/35-model-discovery-and-catalog/35-25-PLAN.md"
  - ".planning/phases/35-model-discovery-and-catalog/35-25-SUMMARY.md"
  - ".planning/phases/35-model-discovery-and-catalog/35-26-PLAN.md"
  - ".planning/phases/35-model-discovery-and-catalog/35-26-SUMMARY.md"
  - ".planning/phases/35-model-discovery-and-catalog/35-27-PLAN.md"
  - ".planning/phases/35-model-discovery-and-catalog/35-27-SUMMARY.md"
  - ".planning/phases/35-model-discovery-and-catalog/35-28-PLAN.md"
  - ".planning/phases/35-model-discovery-and-catalog/35-28-SUMMARY.md"
  - "skills/ai-kit-spec-config/SKILL.md"
  - "skills/ai-kit-spec-review/ai_kit_spec/catalog_cmds.py"
  - "skills/ai-kit-spec-review/ai_kit_spec/catalog_report.py"
  - "skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py"
  - "skills/ai-kit-spec-review/ai_kit_spec/usability.py"
  - "tests/test_arch_hardcoded_models.py"
covered_digest: "v4:sha256:60a726c8645a3e069b87ada5d8fbd5589d1f509d631e59207063e4d944e10e5a"
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "Live install from the unit tip to the real machine, then re-check"
    expected: "install.sh from the checkout links the skills; spec-config catalog flow runs on the real hosts"
    why_human: "run rails forbid touching the real home; AGENTS.md Workflow ships after gates (scratch-HOME dry run and install are done, see gates)"
  - test: "ai-kit-fold ready and un-draft the stacked PRs"
    expected: "draft PRs marked ready by the owner-started flow"
    why_human: "needs the owner; the draft PRs stay drafts"
  - test: "Read Artificial Analysis term 2.5 (model-selection products offered to third parties)"
    expected: "owner decides whether ai-kit's use fits; reported in 35-CONTEXT.md Amend-5, not decided"
    why_human: "legal reading, owner decision"
  - test: "Triage the 23 deferred MEDIUM plan-review concerns in each plan's Review Dispositions Ledger"
    expected: "owner accepts or schedules each"
    why_human: "deferred by the review rules, recorded per plan"
  - test: "Rerun python3 tools/judge_loop.py report .planning/judge and a new ai-kit-spec-config judge loop"
    expected: "digest refreshed; check-dogfood prints no facts-drift note"
    why_human: "digest is stale by design after the review's SKILL.md fix (eb4ab23); the loop-35 round-1 verdicts stand"
  - test: "Note the executor model change my-coding-lite to my-coding after plan 28"
    expected: "recorded on owner instruction 2026-11-20"
    why_human: "informational; plans 01-28 ran on my-coding-lite"
  - test: "Spike herdr against copilot's interactive /model view"
    expected: "names read reliably; until then the output stays labeled 'interactive view, unverified'"
    why_human: "Amend-11: not run in planning; needs a real copilot session"
---

# Phase 35: Model discovery and catalog Verification Report

**Phase Goal:** spec-config shows every model the machine can reach, with where it was listed from, whether it is usable, and catalog facts labeled by how sure they are.
**Verified:** 2026-11-20 against branch tip 0cf96e7
**Status:** passed (no gap; seven human-verification items below do not block)
**Re-verification:** No, initial verification

## Requirement-to-evidence (SPEC R1-R12; HUB-02, HUB-03, HUB-06, HUB-08, HUB-09)

Plan frontmatter `requirements:` across the 28 plans lists exactly HUB-02, HUB-03, HUB-06, HUB-08, HUB-09: all five appear in REQUIREMENTS.md (rows 212-255, traceability rows 1090-1097) and map to Phase 35. No orphaned id.

| Req | Code | Test that fails if the behaviour is missing | Status |
| --- | ---- | ------------------------------------------- | ------ |
| R1 listing per host with `listed_from`, failed listing leaves cache, unlisted runtime | `detection.py` (opencode `/api/model`, pi RPC, codex, cursor, copilot no listing), `catalog_facts.py` | `tests/test_catalog_listing.py`: `test_cursor_listing_ok:245`, `test_failed_listing_error:260`, `test_empty_listing_ok:271`, `test_copilot_has_no_listing:279`, `test_unlisted_runtime_found:307`, `test_retry_after_503:55`; `test_catalog_schema4.test_unreadable_catalog_is_not_overwritten:194` | VERIFIED |
| R2 usability apart from listing; only real answer marks verified | `usability.py:27-42` (`record_for`: verified only when `answered is True`; rejected carries `sanitize_error`, first line, control chars removed, redacted, 200 cap); `model_catalog.py:59` states; `catalog_report.py:126` "listed disabled by host" | `tests/test_catalog_usability.py`: `test_verified_written:78`, `test_rejected_error_sanitized:102`, `test_error_capped:120`, `test_answer_with_reason_is_unverified:127`, `test_state_is_per_runtime:152`; `test_catalog_stale.test_usability_display:83` | VERIFIED |
| R3 seed, web, herdr, labeled and optional | `optional_sources.py`, `herdr_source.py`, `catalog_cmds.py:303-343` (`web-query`, `record-web-names`, `herdr-names`) | `test_catalog_optional_sources.py`: `test_hostile_names_dropped:87`, `test_query_holds_no_local_detail:99`, `test_absent_sources:175`, `test_verified_and_spoofed_refused:140`, `test_label_order:134`; `test_catalog_herdr.py`: `test_absent_env:81`, `test_absent_cli:89`, `test_hostile_pane_text:103`, `test_records_never_verified:143`. Live: hostile web string dropped, escape bytes stripped, stored as "web, unverified"; a query off the fixed template refused | VERIFIED (herdr on real copilot is a spike, human item 7) |
| R4 name matching, effort parsing, jev seam | `model_names.py`, `jev_names.py`, `catalog_facts.py` | `test_catalog_names.py`: `test_known_id_kept_whole:65`, `test_blank_name_refused:71`, `test_tie_is_unmatched_with_both:86`, `test_confident_judge:93`, `test_no_answer:110`, `test_low_answers_unmatched:119`, `test_cursor_styles:31`, `test_pi_style:20`; `test_catalog_jev_names.py`: `test_confident_name_answer:38`, `test_item_holds_names_only:50`, `test_absent_jev:70` | VERIFIED |
| R5 tier, class, cost, modalities, strengths with labels and times; Arena merged when enabled; router alias assumed | `catalog_bands.py`, `catalog_tiers.py`, `arena_source.py`, `catalog_labels.py`, `catalog_build.py` | `test_catalog_bands.py`: `test_tier_edges:30`, `test_equal_scores_share_tier:40`, `test_cost_band:49`, `test_router:126`; `test_catalog_tiers.py`: `test_aa_decides_when_present:88`, `test_neither_source:112`, `test_aa_outage_keeps_tier:175`, `test_arena_disabled_removes_facts:201`, `test_class_judge:135`, `test_router_untouched:235`, `test_source_time_kept:104`; `test_catalog_arena.py` (14 tests). Live: router alias shows `class: router (assumed, router-env alias naming, <time>)` | VERIFIED |
| R6 context per (runtime, model) | `catalog_context.py` (precedence override, host, models.dev, unknown; integers only) | `test_catalog_context.py`: `test_two_runtimes_two_windows:44`, `test_report_line_per_runtime:70`, `test_host_beats_models_dev:87`, `test_override_beats_all:97`, `test_unknown_stays_unknown:172`, `test_no_guess_from_name:182`, `test_invalid_values_ignored:110` | VERIFIED |
| R7 attribution, no AA data tracked | `catalog_attribution.py:9-20` (AA credit, Arena CC BY 4.0, models.dev, AA redistribution "not granted"); `catalog_cmds.py` report | `test_catalog_attribution.py`: `test_aa_lines:28`, `test_none_and_unknown:34`, `test_fixed_order:22`; `test_catalog_cmds.test_text_output_facts_and_attribution:200`, `test_empty_catalog_no_attribution:248`; `test_arch_hardcoded_models.test_tree_has_no_unmarked_aa_shape:328`, `test_aa_rule_non_vacuity:331` | VERIFIED |
| R8 stale on proof only | `catalog_report.py:81-93` (`stale_state`: any listing not `ok` gives "not checked"; cached listing gives "not checked (cached ...)"), `stale_providers:96` | `test_catalog_stale.py`: `test_removed_after_good_listing_and_failed_listing:44`, `test_reappearing_model_not_stale:70`, `test_stale_provider:112`, `test_marked_by_source:123`; `test_catalog_cmds.test_detect_is_run_local_proof:285`; `test_ai_kit_spec_check_providers.py` (absent). Live: `check-providers` prints "absent" for missing files; a saved snapshot shows "not checked" for every row | VERIFIED |
| R9 opencode profile and comments match recorded help | `tests/fixtures/cli_help/opencode/` (meta: version 2.3.2, recorded 2026-11-20), `tools/record_cli_help.py`, rewritten `cli-profiles/opencode.md`, `cross-ai.mjs` comments; no stale `2.0.29` citation left in `skills/` (only a parse example in `detection.py:756`) | `test_opencode_help_flags.py`: `test_fixture_records_version:81`, `test_profile_flags_in_help:99`, `test_runner_flags_in_help:104`, `test_planted_stale_flag_fails:113`, `test_whole_token:116`, `test_empty_profile_passes:122`; `test_record_cli_help.py` (6 tests) | VERIFIED |
| R10 `[models]`, schema 4, confirm subcommand | `models_config.py`, `model_catalog.py:22` (`CATALOG_SCHEMA_VERSION = 4`), `catalog_cmds.py` (`confirm-model`, `models-config`) | `test_models_config.py`: `test_project_over_user:49`, `test_unknown_source_named:101`, `test_write_keeps_other_bytes:36`, `test_key_never_written:94`, `test_two_writers_keep_one_value:167`; `test_catalog_schema4.test_v3_cache_keeps_confirmed_and_verified:137`; `test_catalog_cmds.test_survives_refresh:96`, `test_confirm_heuristic_field:80`. Live: unknown source gives a named error (rc 2); write kept `[models]` only | VERIFIED |
| R11 hardcoding guard with shrinking baseline | `tests/test_arch_hardcoded_models.py` (position-based), `tests/fixtures/no_hardcoded_models_baseline.json` (each file names `cleaned_by`) | `test_tree_matches_baseline:378`, `test_baseline_is_sorted_and_unique:384`, `test_each_rule_catches_its_form:396`, `test_allowed_forms_pass:408`, `test_marker_never_exempts_code:427`, `test_untracked_file_is_scanned:461`, `test_baseline_problems_each_fire:477`, `test_nfkc_lookalike_caught:455`; group `arch`, 14 tests ok | VERIFIED |
| R12 skill text, docs, judge bar | `skills/ai-kit-spec-config/SKILL.md` Step 1.5, `references/catalog.md`, `references/cli-model-selection.md`, 12 evals | `test_spec_config_catalog_text.py`: `test_step_order:47`, `test_commands_named:56`, `test_documented_commands_parse:72`, `test_herdr_notice_before_run:77`. Judge loop 35 round 1 (`.planning/judge/verdicts/35/ai-kit-spec-config/r1`): referee-one 88.8 B (111/125), referee-two 88.0 B (110/125), no critical finding; three high findings fixed in place under the 3-or-fewer rule (`fixes.md`); previous recorded result 77.6, so no regression | VERIFIED |

## Roadmap success criteria

All eight map to the rows above: SC1 to R1+R2; SC2 to R5+R7; SC3 to R8; SC4 to R9; SC5 to R6; SC6 to R12; SC7 to R11; SC8 to R3. Eight of eight verified.

## Prohibitions (SPEC)

| Must-NOT | Evidence | Status |
| -------- | -------- | ------ |
| verified from listing, seed, web or view alone | `usability.py:37` only `answered is True`; `test_verified_and_spoofed_refused`, `test_records_never_verified`, `test_answer_with_reason_is_unverified` | verified |
| ship AA data or print/store a key | `test_tree_has_no_unmarked_aa_shape`, `test_key_never_written`; scan of added lines found no key shape | verified |
| project/user/machine detail in web query; fetched text as instruction | fixed template, live refusal of off-template file, `test_query_holds_no_local_detail`, `test_hostile_names_dropped`, `test_hostile_pane_text` | verified |
| guess context from a name | `test_no_guess_from_name`, `test_unknown_stays_unknown` | verified |
| stale after failed or skipped listing | `catalog_report.py:82-83`, first stale test | verified |
| table row decides / hardcoded names | guard tests above | verified |
| real user config, host or network in tests | module tripwire, `AI_KIT_REFUSE_REAL_HOME`; gates all green | verified |

## Gate summary (logs in `tmp/run-2026-11-19/gates-35/`, read by the verifier)

| Command | Exit | Evidence |
| ------- | ---- | -------- |
| `make test-unit` | 0 | `3/3 modules passed` |
| `make test` (arch tail) | 0 | `2/2 modules passed` (arch: 109 + 14 tests) |
| `make lint` | 0 | shellcheck and py-compile passed |
| `make validate` | 0 | `check-dogfood: ok`, no-write guard 3 executed |
| `make e2e-test` | 0 | `48 passed, 0 failed` |
| wizard PTY (`tests.test_wizard_pty`) | 0 | 14 tests ok |
| e2e-docker via podman | 0 | `ai-kit clean-room E2E: PASS` |
| `make check-dogfood` | 0 | ok; prints judge-records facts drift (human item 5) |
| ship check (`ship2.log`) | 0 | scratch-HOME `install --headless --dry-run` rc 0 (23 linked), real scratch install rc 0; catalog commands in `ship.log` rc 0 (refusal of an unknown key rc 1 as intended) |
| Verifier run: `run_unittest_parallel.py --group unit --group arch` | 0 | `149/149 modules passed` (includes 21 new `test_catalog_*`, `test_models_config`, `test_opencode_help_flags`, `test_record_cli_help`, `test_arch_hardcoded_models`) |

The wizard-less first dry run in `ship.log` (rc 2: "no interactive terminal") is the interactive wizard path; the headless dry run in `ship2.log` is the valid proof. `install.sh check` in `ship2.log` returned rc 1 only for a missing `claude-statusline.toml` in the empty scratch HOME (unrelated to this phase).

## Verifier's own live checks (scratch HOME under `tmp/verify-35/`, no network, no real host)

`check-providers` absent wording; `models-config` unknown-source error, write and show with comment-free minimal `[models]`; `web-query` (known runtime only, bad id refused); `record-web-names` with a hostile string and an escape sequence (hostile name dropped, escape stripped, label "web, unverified"); `catalog-report` on a snapshot (every row "not checked", never stale without a run-local listing).

## Anti-patterns and constraints

No absolute path, key shape, debt marker (TBD/FIXME/XXX) or non-router model literal in added source lines (scan of `git diff main...HEAD`). One added line, `tests/test_ai_kit_spec.py` `written["openai/gpt-5.6-sol"]`, sits in a file already in the guard baseline (`cleaned_by: backlog`); the guard passes. Info only: low-severity review note on `catalog_facts._merge_derived` and `_apply_entry` for a hand-edited malformed fact (35-REVIEW.md); stale-flag listing is proven by unit tests, not by a live `--detect` on a real host (the verifier did not call real hosts).

## Human verification

Seven items, listed in the frontmatter (live install, `ai-kit-fold ready` and draft PRs, AA term 2.5, the 23 deferred MEDIUM plan-review concerns, stale judge digest, executor model change, herdr copilot spike). None blocks the phase: each is an owner action or a recorded limit, none is a missing requirement.

## Gaps

None.

---

_Verified: 2026-11-20_
_Verifier: Claude (gsd-verifier)_
