---
phase: 33-one-config-design
plan: 09
subsystem: config
tags: [config-toml, lanes, render-toml, toml-splice, lossless-write, migration, tests]

# Dependency graph
requires:
  - phase: 33-01
    provides: toml_splice (set_table, set_array, remove_table, publish) used as the only roster writer
  - phase: 33-07
    provides: roster readers over config.toml [lanes] with migration and the D-11 trust rule
provides:
  - "cfg_render_lanes: the roster written into config.toml through the splicer (D-08, D-24)"
  - "render-toml guard: an existing [lanes] table or an old review-spec.toml beside the target is refused without --replace before anything is written (C1-17, C1-18)"
  - "render-toml migrates its target only after the guard passes; a broken or non-UTF-8 target is exit 2 with the file unchanged (C1-16)"
  - "roster test fixtures on config.toml with the [lanes] shape (SPEC R6); the four legacy-migration tests keep the old file and carry the marker"
affects: [33-10 (wizard detects an old roster and passes --replace on approval; skills/ai-kit-spec-config docs), 33-11 (naming audit: only the migration names review-spec.toml), 36 (callers of the flat reviewers view)]

# Actuals (#2632): chars/4 over the realized diff (base 240cd2c .. HEAD bd155aa)
actuals:
  tokens: 21910
  tasks: 3
  commits: 3

plan_head_before: 240cd2c0250bd9781290f7e97e5bad0d67918f56
plan_head_after: bd155aab6f4a9842f6c0692e08fb486a0f7ca3f8

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "The roster writer splices only the roster parts of [lanes] (strategy, [lanes.policy], [[lanes.review]], [[lanes.execute]]); other tables, unknown [lanes] keys and comments stay byte-equal"
    - "The generated '# Priority fallback order' comment above [lanes.policy] follows its ladder; a user's own comment there is kept"
    - "render-toml runs its guard (target read, [lanes] check, old-roster check) before the migration, so a refusal writes nothing at all"

key-files:
  created: []
  modified:
    - skills/ai-kit-spec-review/ai_kit_spec/config_io.py
    - skills/ai-kit-spec-review/ai_kit_spec/cli.py
    - skills/ai-kit-spec-review/ai_kit_spec/toml_splice.py
    - tests/test_config_layers.py
    - tests/test_toml_splice.py
    - tests/test_ai_kit_spec.py
    - tests/test_ai_kit_spec_legacy_config.py
    - tests/test_ai_kit_spec_routing.py
    - tests/test_ai_kit_spec_trust.py
    - tests/test_gsd_curated_eval.py
    - tests/gsd_curated_eval.py

key-decisions:
  - "cfg_render_lanes(config, existing_text) takes the JSON key `lanes`; a JSON still keyed `reviewers` raises ValueError with the rename message (exit 1 from render-toml)"
  - "cfg_write_toml reads and parses the target before publishing, so a broken target is a ConfigError and nothing is written"
  - "The ladder comment is refreshed through toml_splice.split_blocks: the contiguous comment lines above the [lanes.policy] block are replaced only when they are the generated block (first line '# Priority fallback order'); a user's own comment is left alone"
  - "The final roster check after the splices raises ConfigError('render-toml target', ...) when the written lanes differ from the intended ones; render-toml maps it to exit 2 (an internal consistency failure, not a bad input)"
  - "The render-toml guard refuses only an existing [lanes] table or an old roster beside the target; a file with other tables (for example [runner.retry]) is written without --replace"

patterns-established:
  - "Writer tests call cfg_render_lanes on text and compare difflib lines; the adjacency test asserts exactly one '-' and one '+' line"

requirements-completed: [CFG-02, CFG-04, CFG-05]

# Metrics
duration: unknown (plan start time was not recorded)
completed: 2026-11-15
status: complete
---

# Phase 33 Plan 09: render-toml writes the roster through the splicer and guards an existing one Summary

**render-toml writes the `[lanes]` roster into config.toml through the comment-keeping splicer (other tables, comments and unknown keys stay byte-equal), refuses to replace an existing roster without --replace before any write, and every roster test moved to config.toml**

## Performance

- **Duration:** unknown (plan start time was not recorded)
- **Tasks:** 3 (Task 1 tracer writer with TDD RED, Task 2 CLI guard and callers, Task 3 fixtures)
- **Commits:** 3 task commits; the SUMMARY commit follows
- **Files modified:** 11

## Accomplishments

- `cfg_render_lanes` writes `strategy`, `[lanes.policy]`, `[[lanes.review]]` and `[[lanes.execute]]` through `toml_splice`; a changed model is a one-line diff; entries file by `purpose` (D-24); a rejected entry is dropped from roster and ladder with the WARNING line.
- `render-toml --out` runs the guard first: a target that is unreadable or malformed is exit 2 with the file byte-equal; an existing `[lanes]` table or an old `review-spec.toml` beside the target is refused without `--replace` with "(nothing written)"; with `--replace` the old roster migrates, then the new roster is written.
- `cfg_render_toml`, `_cfg_render_policy_lines`, `_cfg_render_reviewer_lines` and `_toml_value` are gone; every caller (cli, the test modules named below, the routing module that imports the removed API) moved in the same commits.
- Roster test fixtures moved to `config.toml` with the `[lanes]` shape; the four legacy-migration tests (`test_tracer`, `test_one_note_per_file`, `test_mixed_file_names_only_old_entries`, `test_partial_override`) keep the old file and carry the marker `# legacy roster on purpose: migration`.
- `toml_splice` bug fixed at its root (see Deviations 1): a parent table edit no longer writes its array-of-tables children as inline keys.

## Task Commits

1. **Task 1: cfg_render_lanes writes the roster into a config.toml with a one-line diff** - `28a1a36` (feat; the commit hook ran 73 staged modules and 17 uv modules, all passed)
2. **Task 2: render-toml uses the splicer, migrates its target and guards an existing roster** - `31cace8` (feat; the hook ran the same 73 + 17, all passed)
3. **Task 3: remaining fixtures move to config.toml; full unit tier and static gates** - `bd155aa` (test; the hook ran the full unit and arch groups because a shared fixture changed: 121 of 121, plus 1 uv module)

## Files Created/Modified

- `skills/ai-kit-spec-review/ai_kit_spec/config_io.py` - `cfg_render_lanes`, `_refresh_ladder_comment`, `_splice_roster`, `_expected_lanes`, `cfg_migrate_target`; `cfg_write_toml` rewritten; the full-rewrite writer removed.
- `skills/ai-kit-spec-review/ai_kit_spec/cli.py` - `_cmd_render_toml` (checked target read, guard, migration, splice, publish), `_checked_target`, `_render_toml_refusal`; the build-command message.
- `skills/ai-kit-spec-review/ai_kit_spec/toml_splice.py` - `_splice_table` excludes every child key from the parent's new values (root-cause fix).
- `tests/test_config_layers.py` - new `TestLaneWriter` (10 tests) and `TestRenderTomlCli` (7 tests); module now 40 tests.
- `tests/test_toml_splice.py` - regression test for the parent-table bug.
- `tests/test_ai_kit_spec.py`, `tests/test_ai_kit_spec_legacy_config.py`, `tests/test_ai_kit_spec_routing.py`, `tests/test_ai_kit_spec_trust.py`, `tests/test_gsd_curated_eval.py`, `tests/gsd_curated_eval.py` - converted fixtures and callers (listed below).

## Changed Tests (named)

Converted in place (assertions kept unless stated):
- tests/test_ai_kit_spec.py `TestRenderAndWriteToml`: all 17 tests now call `cfg_render_lanes` with the `lanes` key and assert `[[lanes.review]]`, `[lanes.policy]` and `parsed["lanes"]...`; `test_write_toml_creates_parent_dirs`, `test_write_toml_replaces_atomically` and `test_render_toml_result_resolves_cleanly_through_cfg_resolve` use `config.toml` (the last reads the project's `config.toml` directly, no legacy path).
- tests/test_ai_kit_spec.py `TestPiHostEndToEnd.test_pi_host_renders_as_the_session_default` (`[[lanes.review]]`).
- tests/test_ai_kit_spec.py `TestMainCli`: `test_resolve_reviewers_uses_cfg_resolve_local_global_merge` (config.toml fixtures; trust via `cfg_trust_project`), `test_probe_quota_does_not_probe_a_host_selectable_alias`, `test_probe_quota_refreshes_stale_entries_and_writes_cache`, `test_probe_quota_reads_its_config_from_the_injected_env`, `test_render_toml_prints_only_without_out`, `test_render_toml_with_out_writes_via_cfg_write_toml`, `test_build_command_codex_prints_runner_argv` and `test_build_command_cursor_agent_passes_mode_flag` (message now `a config.toml lane stores runtime and model`).
- tests/test_ai_kit_spec.py `TestMainCli.test_render_toml_out_refuses_existing_file_without_replace`: **behaviour changed as the plan states**. It used to refuse any existing file; it now refuses an existing `[lanes]` table (with "(nothing written)") and writes a file with other tables without --replace. The test name is kept.
- tests/test_ai_kit_spec.py `TestResolveConfig`: `setUp` (global fixture at config.toml, `[lanes.policy]`, `[[lanes.review]]`); `_trust_local_file` is now argument-less and calls `cfg_trust_project`; `_trust_local` is deleted (its only caller was `_trust_local_file`); `test_local_only_strategy_ignores_global` and `test_global_merge_is_the_default_strategy` (local file at `cfg_local_path`).
- tests/test_ai_kit_spec.py `TestTimeoutTiers.test_resolve_timeout_tiers_cli_subcommand_uses_reviewer_override` (`.aikit/config.toml`, `[lanes.policy]`).
- tests/test_ai_kit_spec.py `TestFetchModelCatalogCli.test_single_provider_cli_candidate_pulled_from_review_spec_toml` (name kept; local fixture at `cfg_local_path`, `[[lanes.review]]`, trust via `cfg_trust_project`).
- tests/test_ai_kit_spec.py comment-only rewording (the old file name in comments): `TestLoadToml.test_malformed_toml_raises_config_error`, `TestMergeReviewers.test_entry_with_no_key_is_skipped_not_raised`, `TestExecuteCliRejection.test_grok_keeps_its_custom_entry_generator`, `TestFilterByPurpose.test_missing_purpose_key_entirely_treated_as_no_preference`, `TestTimeoutTiers.setUp` and `..._falls_back_to_policy_default`, `TestBuildModelCatalog.test_discovered_candidates_include_single_provider_and_extra_candidates`.
- tests/test_ai_kit_spec_legacy_config.py `TestLegacyTracer.test_old_file_normalizes_in_memory_with_one_safe_note` (config.toml with `[[lanes.review]]`; `cfg_load_toml(path)["lanes"]["review"]`), `TestLegacyLoad.test_local_only_never_reads_the_global_file` (broken file at config.toml), `TestLegacyLoad.test_order` (config.toml, `[lanes.policy]`, `[[lanes.review]]`), `TestSaveSide` (all five tests: `cfg_render_lanes`, `"lanes"` JSON key, `cfg_load_toml(path)["lanes"]["review"]`, file at config.toml).
- tests/test_ai_kit_spec_legacy_config.py marked (kept at the old file, marker added): `TestLegacyLoad.test_tracer`, `test_one_note_per_file`, `test_mixed_file_names_only_old_entries`, `test_partial_override`.
- tests/test_ai_kit_spec_routing.py `TestResolveRoutes._write_config` (config.toml, `lanes` key), `TestUnverifiedNote.test_unverified_line_once`, `TestRouteNeverStored.test_render_rejects_route` (`cfg_render_lanes`, assertions unchanged), `TestRouting.test_merged_custom_entry_routes_custom` and `TestRouteNeverStored.test_load_drops_route_with_a_note` (config.toml, `[[lanes.review]]`; `route` still checked as dropped).
- tests/test_ai_kit_spec_trust.py `test_render_toml_out_never_trusts_the_file_it_writes` (render writes `.aikit/config.toml`; `lanes` key; the comment reworded), `test_show_renders_local_fields_merged_into_a_global_command` and `test_global_only_reviewer_needs_no_trust` (global fixtures at config.toml, `[lanes.policy]`), `_write_global` and `test_review_spec_main_exits_2_on_malformed_global` (global file path in the assertion now config.toml). The deliberately malformed `[[reviewers` headers in the other trust tests were renamed to `[[lanes.review` and remain malformed.
- tests/test_gsd_curated_eval.py `TestFixture.test_ambient_review_config_cannot_affect_fetch` (the broken fixture is written to config.toml; still `[[[`).
- tests/gsd_curated_eval.py: a docstring line now names the `config.toml` roster.
- New: tests/test_config_layers.py `TestLaneWriter` (10) and `TestRenderTomlCli` (7); tests/test_toml_splice.py `TestSetTable.test_parent_table_beside_an_array_of_tables_child_changes_only_its_key`.

## Decisions Made

- `cfg_render_lanes` takes the JSON key `lanes`; a JSON still keyed `reviewers` is refused with the rename message (exit 1).
- The ladder comment is generated from the ladder that is written, after the rejected keys are dropped; it is refreshed only when the block above `[lanes.policy]` is the generated one (first line `# Priority fallback order`), inserted when there is none, and left alone when it is a user's comment.
- `_refresh_ladder_comment` uses `toml_splice.split_blocks` (the block's `lead` lines) rather than scanning text lines, so `[lanes.policy]` is found whatever its spacing.
- `cfg_migrate_target` decides the layer by comparing the target's folder with the user config folder (realpath): the user layer carries no trust, the project layer carries trust.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `toml_splice._splice_table` wrote array-of-tables children as inline keys**
- **Found during:** Task 1 (the strategy case of `TestLaneWriter`, reproduced with a pure text probe before the fix)
- **Issue:** `set_table(text, ("lanes",), {...})` on a `[lanes]` table that holds `[[lanes.review]]` raised SpliceError: the parent block's new keys included the review array (a list, not a dict), so `review = [...]` was emitted inline beside the array of tables. The old-side already excluded child keys; the new side did not.
- **Fix:** `new` excludes every child key, the same as `old`. The comment in the code says why.
- **Files modified:** `skills/ai-kit-spec-review/ai_kit_spec/toml_splice.py` (a Plan 01 module, not in this plan's `files_modified`), `tests/test_toml_splice.py` (regression test).
- **Verification:** the strategy test and the regression test pass; the full config modules pass.
- **Committed in:** `28a1a36`

**2. [Rule 3 - Blocking] The scope script the plan copies did not exist in this worktree**
- **Found during:** Task 1 start. The plan says to copy `tmp/p33/07/scope.py`, which is not on disk here.
- **Fix:** wrote `tmp/p33/09/scope.py` with the plan's three modes (`test`, `lint`, `all`) and the same output lines. Tests run only through `tools/run_unittest_parallel.py`; lint runs `make ruff|pylint|pyright|vulture`. Scratch, under `tmp/`, not committed.

**3. [Rule 2 - Plan acceptance] Fixture lines were counted in comments and docstrings too**
- **Found during:** Task 3. The plan estimated about 42 fixture lines; the lister found 64 at HEAD and 40 after Task 2.
- **Issue:** the acceptance says `fixture lines: 0`, so comment and docstring lines naming `review-spec.toml` had to change as well.
- **Fix:** reworded those comment lines (count in the Changed Tests list); no code change.

**4. [Coverage addition] `tests/test_ai_kit_spec_trust.py` roster fixtures**
- **Issue:** the plan's Task 3 list does not name this module, but the must-haves (SPEC R6) name it. Its valid global fixtures still used the old file and shape.
- **Fix:** converted those fixtures (listed above). The deliberately malformed `[[reviewers` headers were renamed and kept malformed, so they still test the error paths.

**Total deviations:** 4 (1 bug fix in toml_splice with a regression test, 1 process fix for the scope script, 1 acceptance count, 1 coverage addition). **Impact:** the writer behaves as the must-haves state; deviation 1 is a Plan 01 defect that this plan's strategy write exposed.

## TDD Gate Compliance

- Task 1 (`tdd="true"`): the tests were written before `cfg_render_lanes` existed. The RED run `python3 tmp/p33/09/scope.py test` gave `tests rc: 1`, with 10 ERROR lines in `TestLaneWriter` (each `AttributeError` on `cfg_render_lanes`) and `14/15 modules passed`. After the writer, the one remaining failure was the strategy case (the splicer bug, deviation 1); after the fix the run was green.
- Task 2 (`tdd="true"`): **not met in the strict sense.** The converted tests and the new `TestRenderTomlCli` tests were written together with the CLI change, so there is no separate RED run for them. The first run after the change failed on my own fixture (the new test counted the JSON input it wrote into the tree), which is a test mistake, not a behaviour RED. The behaviours are pinned by the 7 CLI tests, which pass against the committed code.
- Task 3 (fixtures): no TDD flag; the lister evidence is below.

## Issues Encountered

- **Requirement checkboxes are left to the orchestrator.** `REQUIREMENTS.md` is not changed by this executor; the `requirements-completed` list above is copied from the plan frontmatter.
- **Plan's test-count note:** the plan's "about 42" fixture lines counted code only; the lister counts comments too (deviation 3).
- `make test` tiers: see Verification.

## Verification

Every test run went through `tools/run_unittest_parallel.py` (via `tmp/p33/09/scope.py`, `make test-unit`, `make test-integration`, `make e2e-test`) with `AI_KIT_REFUSE_REAL_HOME=1`. Lint ran through `make ruff|pylint|pyright|vulture`.

| Command | Exit | Count line |
| --- | --- | --- |
| `python3 tmp/p33/09/scope.py test` (Task 1, before `cfg_render_lanes`, RED) | 1 | `14/15 modules passed`, 10 ERROR in `TestLaneWriter`, `tests rc: 1` |
| `python3 tmp/p33/09/scope.py test` (Task 1, writer in, before the splicer fix) | 1 | 1 ERROR (strategy case, SpliceError), `tests rc: 1` |
| `python3 tmp/p33/09/scope.py test` (Task 1, after the splicer fix) | 0 | `15/15 modules passed`, `tests rc: 0` |
| `python3 tmp/p33/09/scope.py all` (Task 1 final) | 0 | `tests rc: 0`; `lint ruff rc: 0`; `lint pylint rc: 0`; `lint pyright rc: 0`; `lint vulture rc: 0` |
| commit hook on `28a1a36` | 0 | `73/73 modules passed` (staged), `17/17 modules passed` (uv) |
| `python3 tmp/p33/09/scope.py test` (Task 2, first run after the CLI change) | 1 | 1 FAIL in my new `test_legacy_roster...` (the JSON input was counted in the tree), `tests rc: 1` |
| `python3 tmp/p33/09/scope.py test` (Task 2, after the test fix) | 0 | `15/15 modules passed`, `tests rc: 0` |
| `python3 tmp/p33/09/scope.py all` (Task 2, before the last docstring fix) | 0 for tests | `tests rc: 0`; `lint ruff rc: 2` (one docstring, fixed); `lint pylint rc: 0`; `lint pyright rc: 0`; `lint vulture rc: 0` |
| `make ruff` after the docstring fix | 0 | `ruff.....Passed` |
| commit hook on `31cace8` | 0 | `73/73 modules passed` (staged), `17/17 modules passed` (uv) |
| `python3 tmp/p33/09/fixtures.py` (Task 3, before) | 0 | `fixture lines: 64`, `marked lines: 0` |
| `python3 tmp/p33/09/fixtures.py` (Task 3, after) | 0 | `fixture lines: 0`, `marked lines: 9`, `marked tests: TestLegacyLoad.test_mixed_file_names_only_old_entries, TestLegacyLoad.test_one_note_per_file, TestLegacyLoad.test_partial_override, TestLegacyLoad.test_tracer` |
| `python3 tmp/p33/09/scope.py all` (Task 3 final, after the trust conversion) | 0 | `tests rc: 0`; `lint ruff rc: 0`; `lint pylint rc: 0`; `lint pyright rc: 0`; `lint vulture rc: 0` |
| commit hook on `bd155aa` (full unit + arch, shared fixture changed) | 0 | `121/121 modules passed`, `1/1 modules passed` (uv) |
| `AI_KIT_REFUSE_REAL_HOME=1 make test-unit` (before the trust conversion) | 0 | `119/119 modules passed`, `3/3 modules passed` |
| `AI_KIT_REFUSE_REAL_HOME=1 make test-unit` (final, committed tree) | 0 | `119/119 modules passed`, `3/3 modules passed` |
| `make test-integration` (log `tmp/p33/09/test-integration.log`) | 0 | `9/9 modules passed` |
| `make e2e-test` (log `tmp/p33/09/e2e-test.log`) | 0 | `25/25 modules passed`; `48 passed, 0 failed` |
| `git grep -n cfg_render_toml -- skills/ai-kit-spec-review tests` | 1 (no match) | none |
| `git grep -c review-spec.toml -- skills/ai-kit-spec-review/ai_kit_spec/cli.py` | 1 (no match) | none |
| `git grep -c "legacy roster on purpose: migration" -- tests` | 0 | 4 lines (one per marked test) |

**Isolation:** every test and every run kept away from the real roster files and `~/.config/ai-kit`: each test builds its own temp cwd, HOME and XDG folder (the `_LayerCase` base patches `os.environ`; the runner gives each module a temp HOME; `AI_KIT_REFUSE_REAL_HOME=1` is exported for each run). No ai-kit-spec CLI was run outside a test. The probe script (`tmp/p33/09/probe_splice.py`) called only pure `toml_splice` text functions in-process on a string. The main checkout was not used as cwd or output, and `tmp/` (gitignored) holds only scratch scripts and logs. The only `.aikit` read in the main checkout was the unit brief, read-only.

## Self-Check

- Created files exist: `.planning/phases/33-one-config-design/33-09-SUMMARY.md` (this file). No files were created by the code changes.
- Task commits are ancestors of HEAD: `28a1a36`, `31cace8`, `bd155aa`.
- Ledger base `240cd2c` is the parent of `28a1a36`; `commits: 3` was measured with `git rev-list --count 240cd2c..HEAD` before this SUMMARY commit.

## Self-Check: PASSED

---
*Phase: 33-one-config-design*
*Completed: 2026-11-15*
