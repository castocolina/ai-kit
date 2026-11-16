---
phase: 33-one-config-design
plan: 07
subsystem: config
tags: [config-toml, lanes, migration, trust, d-11, check-providers, trust-local, probe-quota]

# Dependency graph
requires:
  - "33-03: one user-dir rule (cfg_config_base) that every path here uses"
  - "33-05: config_migrate.migrate_layer, read_legacy, pending, legacy_path, legacy_trust_dir, revoke_legacy_trust; trust.command_lanes_bytes"
provides:
  - "cfg_resolve reads .aikit/config.toml and the user config.toml [lanes] per role, migrating an old review-spec.toml first (migrate=False reads it read-only)"
  - "D-11 trust gate: a project [lanes] needs trust only when it has a command-bearing entry; the digest is the canonical command-lane bytes"
  - "cfg_resolve returns review and execute lists beside the flat reviewers view (D-24)"
  - "trust-local: --show and trust record the canonical digest; --revoke revokes both identities before any migration (C2-3)"
  - "probe-quota --no-migrate; check-providers reports a pending old roster and writes nothing"
  - "tests/test_config_layers.py: layered reader, role lanes, trust rule, migration through resolve, read-only mode, revoke-before-migration"
affects: [33-09 (render-toml writer still writes the old shape at the old path; Plan 09 moves it), 36 (callers still read the flat reviewers view)]

# Actuals (#2632): chars/4 over the realized diff (base a55e6af .. HEAD)
actuals:
  tokens: 29260
  tasks: 3
  commits: 2
plan_head_before: a55e6af9cca83b527427cda79ed6580cf5c892aa
plan_head_after: f6acd89fbb2482c56dfff0a458cf29596a88a05c

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Every roster read migrates the project layer first, then the user layer before it is read (never for local-only)"
    - "Trust gates the whole project [lanes] table, keyed by the canonical bytes of its command-bearing entries and the user's command keys"
    - "Read-only mode (migrate=False) reports a pending old roster in memory and writes nothing"

key-files:
  created:
    - tests/test_config_layers.py
  modified:
    - skills/ai-kit-spec-review/ai_kit_spec/config_io.py
    - skills/ai-kit-spec-review/ai_kit_spec/cli.py
    - skills/ai-kit-spec-review/ai_kit_spec/provider_check.py
    - skills/ai-kit-spec-review/ai_kit_spec/quota.py
    - skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/dispatch_injection.py
    - tests/test_ai_kit_spec.py
    - tests/test_ai_kit_spec_trust.py
    - tests/test_ai_kit_spec_check_providers.py
    - tests/test_ai_kit_spec_superpowers.py
    - tests/test_ai_kit_spec_legacy_config.py
    - tests/test_ai_kit_spec_routing.py
    - Makefile
    - .pre-commit-config.yaml

key-decisions:
  - "cfg_combine takes a lanes table and returns the flat reviewers view plus review and execute lists; a role never merges with the other role (D-24)"
  - "A project [lanes] without a command-bearing entry needs no trust (D-11); a command-bearing one is used only when its canonical bytes are trusted, else the whole table is ignored with the existing untrusted warning"
  - "trust-local --revoke runs before cfg_migrate_project and revokes the config.toml records and the old roster's records (C2-3)"
  - "migrate=False in read-only paths: a pending old roster is used when it needs no trust (D-11) or its old file is trusted under the old raw-byte rule"
  - "The user layer's command keys join the digest of a project lane whose key overrides a user command (C1-12, T-33-19)"

patterns-established:
  - "The trust test helper canonical_of(raw) computes the D-11 bytes a record pins (tests/test_ai_kit_spec_trust.py)"

requirements-completed: []  # Orchestrator decides. CFG-05 (reader side) and CFG-06 (no .planning read) are in place; CFG-02 needs Plan 09 (render-toml writes the new shape). Not marked here.

# Metrics
duration: unknown (plan start time was not recorded)
completed: 2026-11-15
status: complete
---

# Phase 33 Plan 07: Roster readers read config.toml lanes through migration and the D-11 trust rule Summary

**Every roster reader resolves `[lanes]` from `.aikit/config.toml` and the user `config.toml` per role, migrating an old `review-spec.toml` first; trust pins the canonical digest of the command-bearing lanes, so an unrelated edit keeps trust and a command edit drops it**

## Performance

- **Duration:** unknown (the plan start time was not recorded)
- **Tasks:** 3 (Task 1 tracer switch, Task 2 layered-reader and trust-rule tests, Task 3 static gates)
- **Commits:** 2 task commits (Task 3 needed no commit: its gates passed on the Task 2 tree)

## Accomplishments

- `cfg_resolve(cwd, env, warn_fn, migrate=True)` migrates the project roster, reads its `[lanes]` (trusted or command-free), and merges the user `[lanes]` per role; `migrate=False` reads a pending old roster in memory and writes nothing.
- `cfg_combine(local_lanes, env, ..., migrate=True)` returns `policy`, the flat `reviewers`, `review` and `execute`; `strategy = "local-only"` never reads the user file.
- `cfg_project_trust_bytes` is the D-11 digest: command-bearing entries, plus entries whose key matches a user command key or a command entry of the same file in any role (C1-12).
- `cfg_trust_project` records trust for the canonical bytes; `trust-local` prints `nothing to trust:` when no lane needs trust.
- `trust-local --revoke` revokes the config.toml records and the old roster's records before any migration (C2-3); the next read then migrates the roster untrusted.
- `probe-quota --no-migrate` reads both layers read-only and reports `migration pending`; `check-providers` reports a pending roster as `scanned (migration pending: <old path>)`.
- Helpers added and used: `cfg_lanes_table`, `cfg_lanes_view`, `cfg_user_command_keys`, `cfg_migrate_project`, `cfg_migrate_user`, `cfg_load_layers`, `cfg_layered_table`.

## Task Commits

1. **Task 1: roster readers read config.toml lanes through migration and the D-11 trust rule** - `9d8625a` (feat; the commit hook ran the 72 covering modules, all passed)
2. **Task 2: layered reader, role lanes and trust-rule tests; caller text** - `f6acd89` (test; the commit hook ran the full unit and arch groups because the Makefile changed, 139 of 139 modules passed)
3. **Task 3: static gates** - no commit; `scope.py all` and `make test-unit` passed on the Task 2 tree

## Files Created/Modified

- `skills/ai-kit-spec-review/ai_kit_spec/config_io.py` - paths, the lanes readers, migration calls, D-11 digest, `cfg_resolve` and `cfg_combine` with the role lists; the write side (`cfg_render_toml`, `cfg_write_toml`) is unchanged for Plan 09.
- `skills/ai-kit-spec-review/ai_kit_spec/cli.py` - imports, help strings, `--no-migrate`, `_trust_local_argv_lines(lanes, env)`, `_cmd_trust_local`.
- `skills/ai-kit-spec-review/ai_kit_spec/provider_check.py` - rewritten around `scan_config`, `lanes_strategy`, the pending-roster report; read-only.
- `skills/ai-kit-spec-review/ai_kit_spec/quota.py`, `skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/dispatch_injection.py` - docstring and warning text only.
- `tests/test_config_layers.py` - new, 23 tests in TestLayeredTable, TestEmpty, TestLaneRoles, TestTrustRule, TestMigrationThroughResolve, TestReadOnlyMode, TestTrustLocalNothingToTrust, TestTrustLocalRevokeLegacy.
- `tests/test_ai_kit_spec_trust.py` - converted whole (rules 1-8).
- `tests/test_ai_kit_spec_check_providers.py` - converted whole (rules 1-8) plus two new tests.
- `tests/test_ai_kit_spec.py`, `tests/test_ai_kit_spec_superpowers.py`, `tests/test_ai_kit_spec_legacy_config.py`, `tests/test_ai_kit_spec_routing.py` - only the per-test list of the plan changed.
- `Makefile`, `.pre-commit-config.yaml` - regenerated test-group blocks (`tools/gen_test_groups.py`), with `tests.test_config_layers` added.

## Changed Test Expectations (named)

tests/test_ai_kit_spec_trust.py (whole module, rules 1-8):
- `_local_spec` returns the `[lanes]` shape (`[[lanes.review]]`, `[lanes.policy]`); `write_local` writes `.aikit/config.toml`.
- Show-test fixtures (`test_show_lists_runtime_and_custom_entries`, `test_show_renders_a_pair_with_its_top_level_knobs`, `test_show_renders_placeholder_hidden_flag_and_executable`, `test_show_renders_local_fields_merged_into_a_global_command`) moved to `[lanes]`; their argv and trust assertions are unchanged. The global fixture of the last one stays at the old path (rule 4).
- `test_trust_local_records_and_probe_then_runs`: record `sha256` equals the digest of the canonical bytes (rule 6).
- `test_edit_after_trust_reblocks`: now edits the command value (rule 6); the old test appended a comment, which keeps trust under D-11.
- `test_crlf_only_edit_needs_new_trust` renamed to `test_crlf_only_edit_keeps_trust`: expectation is now trusted, one probe call (rule 6, D-11).
- `test_non_object_trust_record_reads_untrusted_and_revoke_skips_it`: record keyed on the canonical bytes.
- `test_concurrent_trust_records_stay_valid`: records the canonical bytes.
- `test_render_toml_out_never_trusts_the_file_it_writes`: `--out` is the legacy path (rule 8, C1-13); the other assertions unchanged.
- `TestLoudConfigErrors` fixtures move through `write_local`; expectations unchanged.

tests/test_ai_kit_spec_check_providers.py (whole module, rules 1-8):
- Paths are `.aikit/config.toml` and `<xdg>/ai-kit/config.toml`; `_trust` calls `cfg_trust_project`; fixtures use `[[lanes.review]]`.
- `test_trusted_local_only_marks_global_inactive`: fixture `[lanes] strategy`; reason text is `project config.toml sets strategy = "local-only"` (rule 1-type text update).
- `test_untrusted_local_does_not_deactivate_global` (rule 5 applied differently, see Deviations): the local lane gets a `command`, so it stays an untrusted command-bearing lane; expectations unchanged except the reason text `project config.toml is not trusted`.
- New `test_command_free_local_only_deactivates_global_without_trust` (rule 5 outcome: D-11 applies a command-free local-only project without trust).
- New `test_pending_legacy_roster_is_reported_and_nothing_is_written`.

tests/test_ai_kit_spec.py (per-test list):
- `TestConfigPaths.test_local_path_under_cwd_aikit` expects `/repo/.aikit/config.toml`.
- `TestConfigPaths.test_global_path_uses_xdg_config_home` expects `/x/config/ai-kit/config.toml`.
- `TestConfigPaths.test_global_path_falls_back_to_home_dot_config` expects `/home/u/.config/ai-kit/config.toml`.
- `TestRenderAndWriteToml.test_render_toml_result_resolves_cleanly_through_cfg_resolve`: the writer's fixture path is `config_migrate.legacy_path(config_io.cfg_local_path(d))`; `config_migrate` added to the imports.
- `TestFetchModelCatalogCli.test_custom_grok_entry_model_is_discovered_through_its_command`: fixture at `config.toml` with `[[lanes.review]]`; trust via `cfg_trust_project(d, {"HOME": d})`; assertions unchanged.

tests/test_ai_kit_spec_superpowers.py:
- `TestUntrustedLocalExecuteEntry.test_untrusted_local_execute_entry_absent_until_trusted`: fixture `[lanes]` plus `[[lanes.execute]]` at `config.toml`; trust via `cfg_trust_project(cwd, env)`; both assertions unchanged.

tests/test_ai_kit_spec_legacy_config.py:
- `TestLegacyLoad.test_tracer`: the final re-read of the old user file becomes `assertFalse(exists(old))`, the `.migrated` bytes equal `before`, `config.toml` exists, and the notice `migrated <old> to` is printed.
- `TestLegacyLoad.test_local_only_never_reads_the_global_file`: local key `review`.
- `TestLegacyLoad.test_one_note_per_file`: 2 warnings (the migration notice, then the legacy note that names `config.toml`).
- `TestLegacyLoad.test_mixed_file_names_only_old_entries`: 2 warnings; `old` in warnings[1], `new` not.
- `TestLegacyLoad.test_load_never_writes`: fixture `[[lanes.review]]` (the old `[[reviewers]]` is an unknown key in config.toml, so it would load nothing).
- `TestLegacyLoad.test_partial_override`: local key `review`.
- `TestLegacyLoad.test_variant_merge`: both fixtures at `config.toml` with `[[lanes.review]]`; locals key `review`.
- `TestSaveSide.test_variant_merge_saves`: fixtures at `config.toml` with `[[lanes.review]]`; locals key `review`.

tests/test_ai_kit_spec_routing.py:
- `TestRouting.test_merged_custom_entry_routes_custom`: local key `review`; the user fixture stays at the old path.
- `TestRouteNeverStored.test_resolve_output_has_route_but_the_file_never_gains_it`: the file is `config.toml` with a plain `[lanes.policy]` / `[[lanes.review]]` write; byte-equality assertion unchanged.

## Deviations from Plan

**1. [Rule 1 - Lint] Commit hook line length and pylint (fixed before commit 9d8625a)**
- **Found during:** `scope.py lint` before Task 1's commit
- **Issue:** 17 ruff E501 lines (config_io, cli, provider_check, one test comment); pylint `too-many-locals` (16/15) in `cfg_combine`
- **Fix:** docstrings and one f-string rewrapped; `cfg_combine` calls `cfg_global_path(env)` in its note calls instead of holding a `global_path` local. Behaviour unchanged.
- **Committed in:** `9d8625a`

**2. [Rule 2 - D-11 consistency] Read-only pending roster trust follows D-11, not only the old raw-byte rule**
- **Plan text:** `cfg_resolve(migrate=False)` and `check-providers` use a pending roster "only when trusted under the old rule"
- **Issue:** a pending roster with no command-bearing entry needs no trust under D-11 (the plan's own must-have). With the old rule only, the read-only report would ignore a roster that the migrating read applies without trust, so the two paths would disagree.
- **Fix:** `config_io._pending_project_lanes` and `provider_check._scan_pending` use the roster when its canonical digest is None, else when the old file is trusted under the old raw-byte rule (exactly what migration carries).
- **Files:** `skills/ai-kit-spec-review/ai_kit_spec/config_io.py`, `skills/ai-kit-spec-review/ai_kit_spec/provider_check.py`
- **Committed in:** `9d8625a`. The owner may want to confirm this reading; the difference only shows for a pending roster with no command entry.

**3. [Rule 1 - Test fixture, rule 5] `test_untrusted_local_does_not_deactivate_global` keeps its meaning**
- **Plan text (rule 5):** change the expectation to the D-11 outcome for a file with no command-bearing entry.
- **Action:** the test's fixture is a command-bearing untrusted lane (a `command` line added), so its expectations stay as they were (untrusted, global still active). The command-free outcome is pinned by the new `test_command_free_local_only_deactivates_global_without_trust`.
- **Committed in:** `9d8625a`

**4. [Rule 3 - Blocking] `_trust` helper and `trust` import in check-providers tests**
- `_trust` calls `config_io.cfg_trust_project(self.proj, self.env)`, so the `trust` import is unused and was dropped.
- **Committed in:** `9d8625a`

**5. [Rule 1 - Test fixture] `test_local_only_override_needs_no_trust` (new test, Task 2)**
- The first run of `tests/test_config_layers.py` had 1 failure (22 passed): its project lane had no `runtime`, and the existing legacy inference cleared the model to the session default. The fixture gained `runtime = "codex"`. No source change.
- **Committed in:** `f6acd89`

**6. [Coverage addition] `TestTrustLocalRevokeLegacy` and `TestMigrationThroughResolve` use a legacy `command` the plan named only generally**
- The fixture command is `<sys.executable> -c pass {model}` (the trust module's PROBE_CMD shape), written with `json.dumps` so the TOML string escapes correctly.
- **Committed in:** `f6acd89`

**Total deviations:** 6 (1 lint fix before commit, 1 D-11 consistency reading for the read-only path, 1 fixture-level rule 5 handling, 1 blocking import cleanup, 1 fixture fix in a new test, 1 coverage addition). **Impact:** the switch behaves as the plan's must-haves state; deviation 2 is the only behaviour reading the owner should confirm.

## TDD Gate Compliance

- Task 1 is `type="tracer"` (no TDD flag); its tests were converted with the source and passed in the same commit.
- Task 2 is `tdd="true"`. **Violation, same as Plan 05:** `tests/test_config_layers.py` was written after the Task 1 implementation, so no `test(33-07)` RED commit precedes the GREEN code. The first run of the module was not a behaviour RED: its single failure was a fixture error (deviation 5). No `tdd-red-evidence` classifier was run.
- The behaviours are pinned by 23 tests in `tests/test_config_layers.py`, which pass against the committed code.

## Known Stubs

None.

## Threat Flags

None beyond the plan's threat model. The D-11 narrowing of the trust digest (T-33-19) is recorded in the plan and is flagged for `/gsd-secure-phase` review as the plan states. No new network endpoint, auth path or file-access pattern was added.

## Verification (run in this worktree)

Every test run went through `tools/run_unittest_parallel.py` (via `tmp/p33/07/scope.py` or `make test-unit`) with `AI_KIT_REFUSE_REAL_HOME=1`.

| Command | Exit | Count line |
| --- | --- | --- |
| `python3 tmp/p33/07/scope.py test` (Task 1 scope, 11 modules, before the new module existed) | 0 | `11/11 modules passed`, `tests rc: 0` |
| `python3 tmp/p33/07/scope.py all` (Task 1 final tree, before commit) | 0 | `11/11 modules passed`, `tests rc: 0`; `lint ruff rc: 0`, `lint pyright rc: 0`, `lint pylint rc: 0`, `lint vulture rc: 0` |
| `python3 tmp/p33/07/scope.py test` (first run after `test_config_layers.py` was added) | 1 | `FAILED (failures=1)` on `test_local_only_override_needs_no_trust` (deviation 5), `tests rc: 1` |
| `python3 tmp/p33/07/scope.py test` (after the fixture fix, 12 modules) | 0 | `12/12 modules passed`, `tests rc: 0`; `tests.test_config_layers` 23 tests ok |
| `python3 tmp/p33/07/scope.py lint` (Task 2 tree) | 0 | `lint ruff rc: 0`, `lint pyright rc: 0`, `lint pylint rc: 0`, `lint vulture rc: 0` |
| `AI_KIT_REFUSE_REAL_HOME=1 make test-unit` | no `make` error printed; the exit status was not captured separately | `119/119 modules passed` (unit), `3/3 modules passed` (unit-uv) |
| Commit hook on `9d8625a` | 0 | `staged: 9 files -> 72 modules`, `72/72 modules passed`; ruff, pylint, py-compile passed |
| Commit hook on `f6acd89` | 0 | full unit and arch run (`.pre-commit-config.yaml` changed), `139/139 modules passed` |
| `rg -n "review-spec" skills/ai-kit-spec-review/ai_kit_spec/config_io.py skills/ai-kit-spec-review/ai_kit_spec/provider_check.py` | 1 (no match) | none |
| `rg -n "review-spec\.toml\|review-spec-trust" skills/ai-kit-spec-review/ai_kit_spec/cli.py` | 0 | one line: line 894, `build-command: review-spec.toml stores ...` (Plan 09 rewrites it) |
| `rg -n "review-spec\.toml" skills/ai-kit-spec-review/ai_kit_spec/quota.py skills/ai-kit-spec-execute-superpowers/ai_kit_spec_superpowers/dispatch_injection.py` | 1 (no match) | none |
| `python3 tools/gen_test_groups.py` | 0 (no output) | `Makefile` and `.pre-commit-config.yaml` regenerated |

**Isolation:** every test and every run kept away from the real roster files and `~/.config/ai-kit`: each test builds its own temp cwd, HOME and XDG folder and patches `os.environ` to them; `scope.py` and `make test-unit` export `AI_KIT_REFUSE_REAL_HOME=1`; no ai-kit-spec CLI was run outside a test; the only read of the main checkout's `.aikit/` was the unit brief named by the plan's agent-skill list (`.aikit/brief/SKILL.md`, read-only; it names this unit).

## Self-Check

- Created files exist: `tests/test_config_layers.py`, `.planning/phases/33-one-config-design/33-07-SUMMARY.md`.
- Task commits are ancestors of HEAD: `9d8625a` (feat), `f6acd89` (test).
- Ledger base `a55e6af` is the parent of `9d8625a`.

## Self-Check: PASSED

---
*Phase: 33-one-config-design*
*Completed: 2026-11-15*
