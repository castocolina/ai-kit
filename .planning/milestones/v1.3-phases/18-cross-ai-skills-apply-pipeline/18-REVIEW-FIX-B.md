---
phase: 18
fixed_at: 2026-10-15
review_path: .planning/phases/18-cross-ai-skills-apply-pipeline/18-REVIEW.md
scope: "Batch B (CR, WR, IN) + cross-batch C-W1, C-W7, C-W8 (validator side), C-W9 + ponytail PT-01..07, PT-11, PT-12"
iteration: 1
findings_in_scope: 29
fixed: 29
skipped: 0
status: all_fixed
---
# Phase 18 Batch B: Code Review Fix Report

**Source review:** `18-REVIEW.md`, section "# Batch B", plus the cross-batch and ponytail items assigned to batch-B files.
**Commit range:** `9b8c4cf..e4b1166` (27 commits on `gsd/v1.3-curated-config-v2`, after `9159270`).
**Where verification ran:** in this checkout (`.claude/worktrees/v13-curated-config-v2`). No separate review-fix worktree was used.

**Verification:**
- `make test-unit`: 37/37 modules plus 1/1 uv module pass.
- `python3 -m unittest tests.test_curated_config_apply_e2e`: OK.
- The `e2e` group (`run_unittest_parallel.py --group e2e`): 7/7 modules pass.
- `make ruff pylint pyright vulture`: all pass.

Every behavior change got a failing test before the fix. Each test was confirmed red against the unfixed source.

Some fixes change logic and should get a human read, not only the tests. These are marked "requires human verification" below: CR-01, WR-04/C-W8 and IN-07.

## Fixed

### B-CR-01: exceptions in the pre-commit window bypassed rollback
**Fixed in** `9b8c4cf` (requires human verification).
- `_execute_apply` now runs D-22 steps 4-6 inside one `try` (`_pre_commit`). An `OSError`, `ValueError` or `SubprocessError` restores through `_rollback`, like a returned failure.
- A failed snapshot discard inside `_rollback` no longer raises.
- New tests cover these failures:
  - a `config-new-project` timeout on a fresh project;
  - a runner-marker `OSError` on a fresh project;
  - a snapshot `OSError` on an existing config;
  - the CLI path.
- Each test asserts:
  - exit 1;
  - no config left, or the bytes restored;
  - no marker;
  - no created `.planning/`;
  - a JSON report instead of a traceback.

### B-WR-01: `TimeoutExpired` escaped the skill check and the follow-ups
**Fixed in** `e3bbcf6`.
- `verify_skills`, `effort_dry_run_count` and `_run_one` now catch `SubprocessError` and reject a JSON body that is not an object.
- The post-commit skill check and the follow-up listing are warn-only backstops (SPEC R13). They are allowlisted in `tests/test_arch.py` rule 9.

### B-WR-02 / C-W7: `plan-set` crashed with a traceback on a bare value
**Fixed in** `8fb6bdd`.
- `_parse_string_list` and `_parse_json_type` raise `PlanEditError`, which exits 2. The message gives an example of the expected shape (`'["name"]'`).
- Covered for every list-key family and for object keys.
- Not done: changing the `skills.py` proposal text (C-W7, batch C) to show the JSON form. The refusal message now shows the expected shape.

### B-WR-03: the plan host was not bound to the inventory host
**Fixed in** `0f2a9b0`.
- `check_plan_inventory` refuses a mismatch. This covers apply, followups, `plan-set` and `plan-unset`.

### B-WR-04 / C-W8 (validator side): trusted roots
**Fixed in** `bbe91d5` (requires human verification).
- `plan_io.home_relative_root` normalizes `~/` roots and rejects `~/..`, `~/../..`, `~/a/../../b`, `~/` and `~//x`. It is the only shape rule: `plan_edit` no longer repeats it (part of PT-07).
- C-W8 design choice: refuse rather than merge. Merging would silently change what the user typed, and trusted roots are a security control.
  - `plan-set` refuses a list that omits an already-configured root. The refusal prints the merged list as a ready-to-run, shell-quoted command.
  - `--force` drops the root, prints a warning and marks the entry `forced`.
  - `validate_plan` rejects a dropping list that is not marked `forced`, which also catches hand edits.
- `--force` never bypasses the `~/` shape rule.

### B-WR-05: `--force` admitted the host slug as a review lane
**Fixed in** `1193049`.
- `_reviewers_refusal` refuses the host slug with or without `--force`.
- `validate_plan` rejects a `set` entry for `review.default_reviewers` that contains the plan host.

### B-WR-06: the dry run hid the reconcile removals on a fresh project
**Fixed in** `bc8bb73`.
- On an absent config, the dry run adds `remove` rows marked `"predicted": true`. They are derived from the inventory's `global_defaults.values`.
- A warning says that the copy `config-new-project` makes is unverified until apply runs.

### B-WR-07: the installer version was not validated
**Fixed in** `5018086`.
- Only an exact semver (an optional prerelease is allowed) reaches `npx -y @opengsd/gsd-core@<v>`.
- `latest`, `file:`, `git+` and two-part versions fall back to the existing pin-by-hand note.

### B-WR-08: `followups --approve` ran while an apply marker was held
**Fixed in** `f6b0ebd`; the refusal helper was merged in `75670f9`.
- `--approve` refuses with apply's recovery text while a marker is held.
- The read-only listing still works.

### C-W1: `cli.py` dropped the injected `connect_fn`
**Fixed in** `a2604bd`.
- `connect_fn` is now passed into `InventoryDeps`.
- `test_key_value_never_in_output` asserts that the fake recorded the probe, so the unit test no longer makes a real network call.

### C-W9: the approval command was not shell-quoted
**Fixed in** `7198f17`. This touches `skills.py`, a batch C file, because the user listed C-W9 for this batch.
- The command now uses `shlex.quote`.
- Ordinary payloads render byte-identically, so the golden fixtures are unchanged.

### B-IN-01: a stale `forced` flag stayed on the canonical command
**Fixed in** `9c06dc3`.

### B-IN-02: the recovery text named the backup by basename
**Fixed in** `81e07de`.
- The text now gives an absolute path. The marker keeps the basename.

### B-IN-03: the snapshot was discarded before the marker update
**Fixed in** `0edf392`.
- The marker is updated first, then the snapshot is discarded.

### B-IN-04: a missing `existing_config.path` raised `KeyError`
**Fixed in** `4ac6d05`.
- The run now stops with the clean "rerun inventory" message.

### B-IN-05: a rolled-back apply left its `.new` render
**Fixed in** `3d09f39`.
- `_rollback` removes a `.new` that this apply created.
- Not done: refusing (or suffixing) when a `.new` already exists. That conflicts with the locked 18-CONTEXT rule "a stale `.new` is overwritten" (also SPEC R4, concurrency row). A `.new` that predates the apply is still overwritten, and it is kept on rollback.

### B-IN-06: the failing key was missing from the error, and an empty error read as success
**Fixed in** `5a87241`.
- The error reads `config-set <key> failed: <output or 'no output'>`.
- `_apply_script_step` returns an explicit success flag.
- Runner render and write failures now carry a context prefix.

### B-IN-07: `0 == False` counted as "already applied"
**Fixed in** `475c317` (requires human verification).
- `plan_io.same_value` compares JSON encodings. Both the single diff rule and the plan-set keep decision use it.

### B-IN-08: the approval was not bound to the block the user saw, and CLI helpers were duplicated
**Fixed in** `75670f9` (fingerprint) and `7f8793e` (helpers).
- `approve_with` carries `--fingerprint`, a sha256 of the required rows' id, argv and cwd. `--approve` refuses when the rebuilt rows differ.
- The flag is optional, so the commands documented in SKILL.md still parse.

### PT-01: apply re-implemented `ensure_config_exists`
**Fixed in** `4efae26`.
- `ensure_config_exists` (in `ai_kit_spec/gsd_tools.py`) gains `env` and `timeout` keywords. It returns `False` on a spawn error or timeout. `env` is passed only when given.
- `_new_project` is deleted.

### PT-02: three copies of the no-op rule
**Fixed in** `d7ffc76`.
- The writes and the skipped count are now derived from `diff_entries`.
- `pending_writes`, `_count_skipped`, the dead `host_name` parameter, the inner sort and the third live-config read are deleted.

### PT-03: apply copied inventory's table probe
**Fixed in** `d56c29c`.
- `inventory.probe_gsd_tables` is now public, a one-line call-site change in `inventory.py` (batch C).
- `Target` carries the `GsdCore`.

### PT-04 / PT-05: plan and inventory loading written twice, and near-copy plan-edit handlers
**Fixed in** `7f8793e`.
- New `plan_io.load_plan_and_inventory` and `cli._run_plan_edit`.

### PT-06: the dry run re-sequenced apply's pre-flight
**Fixed in** `93c7391`.
- New `apply.prepare`, used by both `run_apply` and the dry run.

### PT-07: the timeout rule existed five times
**Fixed in** `b87516f`.
- New `plan_io.timeout_problem`, covering four of the five sites.
- Not done: `cross_ai.timeout_value`, which is in `cross_ai.py`, a batch A file.

### PT-11: repeated umask trick and atomic file copy
**Fixed in** `634622b`.
- New `ai_kit_spec.cache.umask_file_mode` and `config_backup._atomic_copy`.
- Not done: the copy in `cross_ai_script.py`, a batch A file.

### PT-12: JSON-file loading boilerplate copied three times
**Fixed in** `e4b1166`.
- `plan_io._load_doc` serves the plan, the inventory and the affinity file. It also turns a `RecursionError` into "invalid JSON".
- Not done: `skill_scan._read_json`, which is in a batch C file.

## Files outside batch B touched
- `skills/ai-kit-spec-review/ai_kit_spec/gsd_tools.py`, for PT-01 (`ensure_config_exists`).
- `skills/ai-kit-spec-review/ai_kit_spec/cache.py`, for PT-11 (`umask_file_mode`).
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/inventory.py`, for PT-03 (the `probe_gsd_tables` rename).
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/skills.py`, for C-W9 (`shlex.quote`).
- `tests/test_arch.py`, for WR-01 (two documented broad-except backstops added to the rule 9 allowlist).

No batch A file was touched: `references/cross-ai.mjs`, `cross_ai.py`, `cross_ai_script.py` and `ai_kit_spec/detection.py` are unchanged.

## Handed to other batches
- **Batch C, SKILL.md:** document three changes.
  - The `predicted` diff rows (WR-06).
  - The `--fingerprint` in `approve_with` (IN-08).
  - The trusted-roots drop refusal and its `--force` path (C-W8).
- **Batch C, proposals:**
  - C-W7: proposal text that shows the JSON list form.
  - C-W8: proposal side that stores the merged list as the single candidate value.
- **Batch A:** the PT-07 and PT-11 call sites in `cross_ai.py` and `cross_ai_script.py`.

---

_Fixed: 2026-10-15_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
