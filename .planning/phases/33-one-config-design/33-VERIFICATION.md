---
phase: 33-one-config-design
verified: 2026-11-15T18:30:00Z
status: passed
score: 12/12 must-haves verified
covered_files: [".planning/judge/REJUDGE.md", ".planning/phases/33-one-config-design/33-01-PLAN.md", ".planning/phases/33-one-config-design/33-01-SUMMARY.md", ".planning/phases/33-one-config-design/33-02-PLAN.md", ".planning/phases/33-one-config-design/33-02-SUMMARY.md", ".planning/phases/33-one-config-design/33-03-PLAN.md", ".planning/phases/33-one-config-design/33-03-SUMMARY.md", ".planning/phases/33-one-config-design/33-04-PLAN.md", ".planning/phases/33-one-config-design/33-04-SUMMARY.md", ".planning/phases/33-one-config-design/33-05-PLAN.md", ".planning/phases/33-one-config-design/33-05-SUMMARY.md", ".planning/phases/33-one-config-design/33-06-PLAN.md", ".planning/phases/33-one-config-design/33-06-SUMMARY.md", ".planning/phases/33-one-config-design/33-07-PLAN.md", ".planning/phases/33-one-config-design/33-07-SUMMARY.md", ".planning/phases/33-one-config-design/33-08-PLAN.md", ".planning/phases/33-one-config-design/33-08-SUMMARY.md", ".planning/phases/33-one-config-design/33-09-PLAN.md", ".planning/phases/33-one-config-design/33-09-SUMMARY.md", ".planning/phases/33-one-config-design/33-10-PLAN.md", ".planning/phases/33-one-config-design/33-10-SUMMARY.md", ".planning/phases/33-one-config-design/33-11-PLAN.md", ".planning/phases/33-one-config-design/33-11-SUMMARY.md", ".planning/phases/33-one-config-design/33-12-PLAN.md", ".planning/phases/33-one-config-design/33-12-SUMMARY.md", ".planning/scripts/cross-ai.mjs", "README.md", "docs/config/design.md", "skills/ai-kit-cross-ai/SKILL.md", "skills/ai-kit-cross-ai/references/subprocess-quota-policy.md", "skills/ai-kit-gsd-curated-config/SKILL.md", "skills/ai-kit-gsd-curated-config/references/runner.md", "skills/ai-kit-spec-config/SKILL.md", "skills/ai-kit-spec-config/evals/evals.json", "skills/ai-kit-spec-config/evals/files/stale-opencode/config.toml", "skills/ai-kit-spec-config/evals/trigger-queries.json", "skills/ai-kit-spec-config/references/check-only.md", "skills/ai-kit-spec-config/references/cli-model-selection.md", "skills/ai-kit-spec-config/references/config-file.md", "skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/dispatch_injection.py", "skills/ai-kit-spec-execute-superpowers/references/resolution-stops.md", "skills/ai-kit-spec-review-checklist/evals/orchestrator-integration.md", "skills/ai-kit-spec-review/SKILL.md", "skills/ai-kit-spec-review/ai_kit_spec/cache.py", "skills/ai-kit-spec-review/ai_kit_spec/cli.py", "skills/ai-kit-spec-review/ai_kit_spec/config_io.py", "skills/ai-kit-spec-review/ai_kit_spec/config_migrate.py", "skills/ai-kit-spec-review/ai_kit_spec/local_secrets.py", "skills/ai-kit-spec-review/ai_kit_spec/provider_check.py", "skills/ai-kit-spec-review/ai_kit_spec/quota.py", "skills/ai-kit-spec-review/ai_kit_spec/toml_splice.py", "skills/ai-kit-spec-review/ai_kit_spec/trust.py", "skills/ai-kit-spec-review/evals/01-superpowers-plan-routes-writing-plans.md", "skills/ai-kit-spec-review/evals/02-gsd-plan-routes-native-cmd.md", "skills/ai-kit-spec-review/evals/03-generic-doc-direct-edit.md", "skills/ai-kit-spec-review/evals/04-ambiguous-detection-fallback.md", "skills/ai-kit-spec-review/references/cli-profiles/cursor.md", "skills/ai-kit-spec-review/references/cross-ai-dispatch.md", "skills/ai-kit-spec-review/references/cross-ai.mjs", "skills/jev-fast-decision/scripts/jev_review.py", "tests/fixtures/cross_ai_selftest_secs.json", "tests/gsd_curated_eval.py", "tests/test_ai_kit_spec.py", "tests/test_ai_kit_spec_check_providers.py", "tests/test_ai_kit_spec_legacy_config.py", "tests/test_ai_kit_spec_routing.py", "tests/test_ai_kit_spec_superpowers.py", "tests/test_ai_kit_spec_trust.py", "tests/test_config_callers.py", "tests/test_config_design_record.py", "tests/test_config_dir_parity.py", "tests/test_config_layers.py", "tests/test_config_migrate.py", "tests/test_cross_ai_skill_text.py", "tests/test_curated_config_recommend.py", "tests/test_external_segments.py", "tests/test_gsd_curated_eval.py", "tests/test_jev_fast_decision.py", "tests/test_setup.py", "tests/test_toml_splice.py", "tools/common_config.py", "tools/run_unittest_parallel.py", "tools/setup.py"]
covered_digest: "v4:sha256:885fde6f173fa9cde33afafa9b7fac39ab879ea81a496b498a3d61afbcd46380"
behavior_unverified: 0
overrides_applied: 0
---

# Phase 33: One config design Verification Report

**Phase Goal:** ai-kit keeps its settings in one neutral `config.toml` per layer (project `.aikit/config.toml` over
user `${XDG_CONFIG_HOME:-~/.config}/ai-kit/config.toml`), one table per concern, role-structured lanes; the roster
leaves `review-spec.toml` and the retry tuning leaves GSD's `config.json` / `cross-ai.json`, each migrating once with
nothing lost; no foreign-schema key; runs without GSD; every write atomic and lossless; named places for Phases 34,
35, 36, 38.1 and 49.
**Verified:** 2026-11-15 at HEAD 6ebd054 (branch gsd/phase-33-one-config-design, clean tree)
**Status:** passed
**Re-verification:** No (initial verification)

All commands below ran with `AI_KIT_REFUSE_REAL_HOME=1`; scratch scripts and logs are under
`tmp/auto/r325/verify33/`.

## Goal Achievement

### Observable Truths

| # | Truth (SPEC requirement / acceptance criterion) | Status | Evidence |
|---|---|---|---|
| 1 | R1 (CFG-01): committed inventory record, every row cites `file:line`; test fails when a settings file name is missing | VERIFIED | `docs/config/design.md` (21366 bytes; sections Decision, Tables, Roles, Trust, Resolver rule, Assignments, Inventory, Environment-only settings, Other tools' files, State and caches; 110 `file:line` cites). `tests.test_config_design_record` 11 tests ok, including `test_every_collected_location_has_one_assignment` and non-vacuity tests `test_a_missing_label_fails_the_assignment_check`, `test_a_label_in_two_rows_fails`, `test_an_empty_assignment_fails` |
| 2 | R2 (CFG-01): one neutral `config.toml` per layer, per-key precedence, state files apart with reasons, no skill/host name | VERIFIED | design.md Decision and Assignments (`.aikit/config.toml` project, `${XDG_CONFIG_HOME:-~/.config}/ai-kit/config.toml` user, line 125/134); tests `test_decision_names_both_paths_and_the_rule`, `test_new_names_carry_no_skill_or_host_name`, `test_neutral_names_pass_and_skill_or_host_names_fail` pass |
| 3 | R3 (CFG-05): tables `[models]`, `[lanes]` (+`[[lanes.review]]`/`[[lanes.execute]]`), `[runner.retry]`, `[jev]`, `[hooks]` documented with filling phase; unknown table kept byte-equal; roles distinct | VERIFIED | design.md:43-55 names each table and its phase (35, 36, 38.1, 34, 49). `tests.test_config_layers` (50 ok): `test_unknown_table_and_key_read_without_error`, `test_unknown_lanes_key_and_unknown_table_are_byte_equal`, `test_review_and_execute_lanes_load_under_their_roles`, `test_same_key_in_both_roles_stays_two_entries`; `tests.test_toml_splice` 51 ok |
| 4 | R4 (CFG-02): roster migrates on first read (local, global, both, local-only, comments+legacy, purpose execute/both, second run no byte change, old-and-new keeps new) | VERIFIED | `tests.test_config_migrate` 43 ok: TestTracer, TestLayers (`test_global_only_migrates_without_trust`, `test_local_and_global_migrate_independently`), TestShapes (`test_local_only_strategy_lands_under_lanes`, `test_legacy_fields_stay_as_written`, `test_both_purpose_appears_in_both_roles`, empty/comment-only), TestRepeat (`test_second_call_is_none_and_changes_no_byte_or_mtime`), TestInterruptions, TestConcurrency. Only `config_migrate.py` names `review-spec.toml` among runtime `.py`/`.mjs` files |
| 5 | R5: trust carried through migration, untrusted stays untrusted, unrelated edit keeps trust, command edit drops it | VERIFIED | `test_config_migrate`: `test_trusted_roster_carries_trust_to_the_new_digest`, `test_untrusted_roster_gets_no_record`; `test_config_layers`: `test_comment_and_unrelated_table_keep_trust`, `test_command_edit_drops_trust`, `test_command_lane_without_trust_is_ignored_with_a_warning`, `test_trusted_legacy_roster_resolves_its_command_after_migration`; `tests.test_ai_kit_spec_trust` 29 ok |
| 6 | R6 (CFG-02): only the migration code names `review-spec.toml`; docs mention it only as a migration source | VERIFIED | `grep -rln 'review-spec\.toml' skills tools --include=*.py --include=*.mjs` -> only `skills/ai-kit-spec-review/ai_kit_spec/config_migrate.py`. Remaining `.md` hits (README.md:63, spec-config SKILL.md, references/config-file.md:54-57, check-only.md:11) are migration-source wording, enforced by `tests.test_config_callers` `test_docs_name_the_old_roster_only_as_a_migration_source` (scope `skills/**`, README, `docs/config/**`). Roster tests on new paths: `test_ai_kit_spec` 693 ok, `test_ai_kit_spec_legacy_config` 24 ok, `test_ai_kit_spec_check_providers` 24 ok. See Info row on historical docs |
| 7 | R7 (CFG-03): runner reads `[runner.retry]` project > user > CONFIG.retry > defaults; GSD block and user JSON migrated once; subset reader fails closed | VERIFIED | `node .planning/scripts/cross-ai.mjs --self-test-list` rc 0, 478 cases; 60 retry/TOML/migration cases incl. `retry-migrate-project`, `-workstream`, `-user-json`, `-readded`, `-second-run`, `-keeps-bytes`, `retry-config-precedence`, `-per-key`, `-invalid-utf8`, `-out-of-subset`, `pure-toml-subset-*`, `no-planning-run`. All four logic shards ran through the runner: `test_cross_ai_selftest_logic_{1,2,3}_e2e` ok (23.2/23.4/23.3 s), `logic_4_e2e` ok (22.3 s) |
| 8 | R8 (CFG-06): no foreign key into another tool's config; ai-kit runs without `.planning/` | VERIFIED | `tests.test_config_callers` 10 ok: TestForeignKeys (`test_no_python_names_cross_ai_retry`, `test_runner_names_cross_ai_retry_only_in_the_migrator`, `test_gsd_config_writes_only_through_allowed_paths`, plus non-vacuity), TestNoPlanning (`test_three_commands_run_without_planning`, `test_second_round_changes_no_repository_byte`); runner case `no-planning-run`. `grep cross_ai_retry` in skills/tools hits only the runner's migrator/notice code (cross-ai.mjs:64, 3675-3970) |
| 9 | R9 (CFG-04): writes atomic and lossless; interrupted write keeps old file; status-line recovery not in place | VERIFIED | `test_toml_splice` `test_interrupted_before_rename_keeps_the_old_file`; `test_setup` (483 ok) `test_interrupted_replace_keeps_the_live_file`; `tools/setup.py:3471` `_recover_incompatible_config` copies `.bak` then publishes via temp file + `os.replace` (lines ~3500-3512); runner cases `retry-migrate-keeps-bytes`, `-interrupted` |
| 10 | R10: one resolver rule for the user config dir; parity test; both secrets readers read one file | VERIFIED | `tests.test_config_dir_parity` 9 ok: config_io, local_secrets, jev_review, common_config, setup.resolve_paths and the runner's `aiKitConfigDir` (run under node) on the same cases; `tests.test_jev_fast_decision` 225 ok |
| 11 | R11 (JDG-04): spec-config SKILL.md + README section updated; loop 33 judges exactly the materially changed SKILL.md files; bar met; `judge_loop.py check` exits 0 | VERIFIED | README.md:53 `## ai-kit configuration` (layers, tables, migration, trust, link to the record); spec-config SKILL.md names `config.toml` 9 times. `python3 tools/judge_loop.py check .planning/judge` rc 0; rows: spec-config `loop 33 round 3 ... worst 88.8 B; critical 0; high 2; bar met: grade B or better; lowest percent 83.2, loop 32 base 79.2; digest current`; curated-config `loop 33 round 1 ... worst 97.6 A; critical 0; high 0; bar met ...; digest current`. Loop 33 bar table below |
| 12 | Acceptance: `make test` passes | VERIFIED (orchestrator evidence) | Close-out part 1 ran `make test`, pyright, lint and check-dogfood with rc 0 (orchestrator fact, not re-run per instructions). This verifier re-ran `make check-dogfood`: `check-dogfood: ok`, rc 0 (no-write guard 3/3 executed; stale digests only for fact-only/carried skills) |

**Score:** 12/12 truths verified (0 present, behavior-unverified)

### Prohibitions (must-NOT)

| Prohibition | Tier | Status | Evidence |
|---|---|---|---|
| No secret value copied into any config file or the record | test | VERIFIED | `test_config_migrate` `test_no_environment_or_secrets_value_lands_in_any_file`; `test_config_design_record` `test_record_holds_no_secret_value` (both pass) |
| Untrusted roster's command entry not made runnable by migration | test | VERIFIED | `test_untrusted_roster_gets_no_record`, `test_command_lane_without_trust_is_ignored_with_a_warning` |
| Old roster not deleted/overwritten before the new config is written and re-read | test | VERIFIED | TestInterruptions: `test_rename_failure_keeps_every_value_in_one_of_the_files`, `test_old_file_changed_before_the_rename_is_kept` |
| No key outside another tool's schema written into its config | test | VERIFIED | TestForeignKeys (4 tests incl. non-vacuity); residual AR-33-05 (static scan cannot see a runtime-passed path) accepted in 33-SECURITY.md |
| `.planning/`/GSD not required to read settings | test | VERIFIED | TestNoPlanning; runner case `no-planning-run` |
| Do not judge commit-fold, a project-rules skill, or an unchanged SKILL.md | judgment | VERIFIED (deterministic evidence) | `.planning/judge/verdicts/33/` holds only `ai-kit-spec-config` (r1-r3) and `ai-kit-gsd-curated-config` (r1). `git diff --stat ab06802 HEAD -- skills/*/SKILL.md`: 4 files changed; ai-kit-cross-ai (1 line) and ai-kit-spec-review (2 lines) are name/path substitutions only (diff read), so fact-only; no commit-fold or project-rules SKILL.md in the set |

### Loop 33 bar results (R11 / JDG-04; facts copied from the orchestrator and 33-12-SUMMARY.md)

Judges: referee-one and referee-two only (referee-three probe timed out, exit 124, never needed; no native judge; no
substitute). Judged exactly the materially changed SKILL.md files.

| Skill | Round | HEAD / records | referee-one | referee-two | Bar | Lowest % vs base |
|---|---|---|---|---|---|---|
| ai-kit-gsd-curated-config | 1 | 0221f4f / 0baf499 | 97.6 A (0 crit, 0 high) | not in count (1 judge) | met: no critical or high | 97.6 vs loop 32.4 base 88.0 (+9.6) |
| ai-kit-spec-config | 1 | 0221f4f / 0baf499 | 89.6 B (1 high) | 83.2 B (1 high) | met: grade B or better | 83.2 vs 79.2 |
| ai-kit-spec-config | 2 | 715c230 / 7a599aa | 90.4 A (1 high, D8-1) | 85.6 B (0 high) | met | 85.6 vs 79.2 (+6.4) |
| ai-kit-spec-config | 3 (last, cap reached) | 2ce2c0b / b43ae32 | 88.8 B (0 crit, 2 high) | 83.2 B (0 crit, 0 high) | met: grade B or better | 83.2 vs loop 32 base 79.2 (+4.0); 1.6/2.4 under round 2, within judge variation |

Open round 3 highs (recorded, not gating): D8-1 `skills/ai-kit-spec-config/references/check-only.md:15` (the
write-risk check covers the raw target's entries but `probe-quota` probes the merged set); D8-2
`skills/ai-kit-spec-config/references/cli-model-selection.md:20` (`CATALOG_JSON` / `FILTERED_RUNTIMES_JSON` set in
one shell block and used in later ones).

Changed SKILL.md files and their loop 33 status:

| SKILL.md | Change | Loop 33 |
|---|---|---|
| ai-kit-spec-config | material (107 lines) | judged, round 3, bar met |
| ai-kit-gsd-curated-config | material (8 lines) | judged, round 1, bar met |
| ai-kit-cross-ai | fact-only (retry key name) | not judged, stale digest recorded |
| ai-kit-spec-review | fact-only (config file name) | not judged, stale digest recorded |
| ai-kit-spec-execute-superpowers | references/code only, SKILL.md unchanged | not judged, stale digest recorded |

Carried stale from before the loop: ai-kit-gsd-spec-discuss, ai-kit-session-wake, ai-kit-spec-review-checklist,
ai-kit-usage-metrics, jev-fast-decision. Not judged by rule: ai-kit-commit-fold, ai-kit-project-rules-*.

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `docs/config/design.md` | inventory + decision record | VERIFIED | all sections present; pinned by `test_config_design_record` |
| `skills/ai-kit-spec-review/ai_kit_spec/toml_splice.py` | comment-preserving atomic TOML writer | VERIFIED | 51 tests; used by config_io/config_migrate |
| `skills/ai-kit-spec-review/ai_kit_spec/config_migrate.py` | roster migration + trust carry | VERIFIED | 43 tests; sole runtime holder of `review-spec.toml` |
| `skills/ai-kit-spec-review/ai_kit_spec/config_io.py`, `trust.py`, `cli.py`, `provider_check.py`, `quota.py` | callers on new paths | VERIFIED | roster suites green (693 + 24 + 24 + 29) |
| `skills/ai-kit-spec-review/references/cross-ai.mjs` | TOML-subset reader, retry sources, migrations | VERIFIED | 60 relevant self-test cases; 4 logic shards green |
| `.planning/scripts/cross-ai.mjs` | pristine render of the template | VERIFIED | `make check-dogfood` ok (byte `cmp` differs by design: it is a render, not a copy) |
| `tools/setup.py` `_recover_incompatible_config` | atomic recovery | VERIFIED | temp + `os.replace`; interruption test |
| README `## ai-kit configuration` | general config section | VERIFIED | README.md:53-67 |

### Key Link Verification

| From | To | Via | Status |
|---|---|---|---|
| cfg_resolve / cfg_combine / trust-local / provider_check | `config.toml` (`[lanes]`) | config_io paths + first-read migration | WIRED (`test_config_callers`, roster suites) |
| `dispatch_injection.assemble_candidates` | new roster | config_io | WIRED (`test_ai_kit_spec_superpowers` in close-out make test; file in phase diff) |
| runner `resolveRetry` | project/user `config.toml` `[runner.retry]` | TOML-subset reader | WIRED (`retry-config-project`, `-user`, `-precedence`) |
| runner migrator | GSD `config.json` block removal | snapshot-checked atomic rewrite | WIRED (`retry-migrate-keeps-bytes`, `-last-key`, `-snapshot-changed`) |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|---|---|---|---|
| Per-requirement unit modules (VALIDATION map R1-R6, R8-R10) | `tools/run_unittest_parallel.py` with 12 modules (`run_units.sh`) | rc 0, `12/12 modules passed` (toml_splice 51, design_record 11, migrate 43, legacy_config 24, layers 50, trust 29, dir_parity 9, check_providers 24, callers 10, ai_kit_spec 693, setup 483, jev_fast_decision 225) | PASS |
| Judge records valid (R11) | `python3 tools/judge_loop.py check .planning/judge` | rc 0 | PASS |
| Runner self-test listing (R7) | `node .planning/scripts/cross-ai.mjs --self-test-list` | rc 0, 478 cases, 60 R7-relevant | PASS |
| Runner logic shards (R7) | `run_unittest_parallel.py tests.test_cross_ai_selftest_logic_{1..4}_e2e` | 4/4 ok (a first call also named a non-existent `logic_0`, ModuleNotFoundError, verifier typo; shards are numbered 1-4) | PASS |
| Live-project check | `make check-dogfood` | `check-dogfood: ok`, rc 0 | PASS |

### Probe Execution

Not applicable: no `scripts/*/tests/probe-*.sh` declared by the phase; the runner self-test shards play that role and
ran above.

### Requirements Coverage

| Requirement | Description | Status | Evidence |
|---|---|---|---|
| CFG-01 | recorded decision backed by an inventory | SATISFIED | truths 1, 2 |
| CFG-02 | `review-spec.toml` replaced with automatic migration | SATISFIED | truths 4, 5, 6 |
| CFG-03 | runner retry settings in ai-kit's config, GSD block migrated | SATISFIED | truth 7 |
| CFG-04 | every config write atomic and lossless | SATISFIED | truth 9 |
| CFG-05 | entries structured by concern and role | SATISFIED | truth 3 |
| CFG-06 | no foreign-schema key; runs without GSD | SATISFIED | truth 8 |
| JDG-04 | changed SKILL.md files meet the judge bar | SATISFIED | truth 11 |

Every ID is claimed by at least one plan's `requirements:` field; no orphaned requirement. The REQUIREMENTS.md
traceability table still reads "Pending" for these IDs (updated at phase close by the orchestrator, not a gap).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| phase diff (`git diff ab06802 HEAD -- skills tools docs README.md`) | - | added `TBD`/`FIXME`/`XXX` | none found | no debt-marker blocker |
| `docs/superpowers/**`, `docs/prds/ai-kit-opencode-provider-management-v1.0-prd.md` | various | name `review-spec.toml` | Info | dated historical plans/specs outside the R6 scan scope (`skills/**`, README, `docs/config/**`); rewriting them would falsify history. Not user-facing config docs |

### Open items with disposition (not gaps)

Security (`33-SECURITY.md`: status verified, threats_open 0, 50/50 closed). Accepted risks:
- AR-33-01: migration concurrency without a lock (T-33-13, T-33-15), owner D-25.
- AR-33-02: stop between retiring a source and recording `migrated_from` (T-33-11, C3-3).
- AR-33-03: trust hashes command-bearing lane entries only (T-33-19), owner D-11.
- AR-33-04: a project `[lanes]` without command entries applies without trust (IN-07), owner D-11.
- AR-33-05: static foreign-key scan cannot see a runtime-passed GSD path (T-33-28).
- AR-33-06: no package install in phase 33.

Code review (`33-REVIEW.md` status issues_found, iteration cap reached; `33-REVIEW-FIX.md`):
- WR-02 remainder: reordering lanes moves a section comment with its entry; a comment directly above `[lanes.policy]`
  goes with the table. Comment placement only, no data or trust effect; does not break R9 (no value lost, written-key
  diff tests pass).
- WR-51 code part: a multi-line nested array element alone on its line makes the runner skip the file; D-07
  (owner-locked) lists nested arrays as outside the subset, and the skip fails closed with a notice as R7 requires.
- IN-101, IN-102, IN-103: Info, no exploit; IN-102's guard already refuses the write.
- IN-01 (inline comment on a changed key line lost: outside D-08's promise), IN-02/03/04/08/09 skipped as Info.

Judge: round 3 open highs D8-1 and D8-2 on ai-kit-spec-config (listed above), recorded, not gating.

### Human / Post-ship Verification

These are read-only checks that run after the ship step (install from the phase branch tip), which has not run yet.
They do not set `human_needed` because every automatable truth passed:

1. **First post-install run migrates this machine's two rosters** (R4, R5; VALIDATION manual row): after install,
   read `.aikit/config.toml` and the user `config.toml`, confirm `review-spec.toml.migrated` exists beside each, and
   `trust-local --show` reports the expected state.
2. **The `33-11-SUMMARY.md` post-install live check list** (read-only re-checks of the installed skills and runner
   against the live config).

### Gaps Summary

None. Every SPEC requirement R1-R11 and acceptance criterion has passing test or command evidence gathered by this
verifier (12 unit modules, 4 runner logic shards, judge check, check-dogfood), with `make test` on the orchestrator's
close-out evidence. Remaining open items are owner-accepted risks, code-review remainders with recorded dispositions,
and two non-gating judge highs.

---

_Verified: 2026-11-15_
_Verifier: Claude (gsd-verifier)_
