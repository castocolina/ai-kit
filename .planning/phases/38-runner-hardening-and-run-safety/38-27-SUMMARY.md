# 38-27 Summary: plan edit defers the skipped-skill check; the re-implemented resolution is deleted

Status: complete. Two commits through cross-AI lanes (pi router-env/my-coding), each status=ok on its first run: d6d0180
(`refactor(38-27): plan edit defers the skipped-skill check to apply`, 234 s) and 9a54451
(`refactor(38-27): delete the re-implemented skill resolution`, 264 s).

## What changed

- `plan_edit._skipped_skills_refusal` no longer refuses: for an `agent_skills.*` key and for
  `agent_skills_security.trusted_global_roots` it prints
  `ai-kit-gsd-curated-config: note: the skipped-skill check runs at apply (plan-set has no project root)` to stderr; apply's gsd-core
  check (38-06) owns the refusal. Plan edit starts no child process.
- Seven plan-edit tests migrated: the edit succeeds with the note; fix-text assertions call `plan_io._skip_text` directly with the same
  expected text. Four renamed (`test_decline_trusted_roots_defers_to_apply`, `test_unset_keeping_skipped_project_skill_defers_to_apply`,
  `test_unset_agent_skills_holding_skipped_global_ref_defers_to_apply`, `test_trusted_roots_without_needed_root_defers_to_apply_even_forced`).
- Deleted: `skipped_skill_problem`, `_skip_message`, `_skipped_items`, `_kept_skip`, `_kept_global_skip`, `_project_ref_skip_reason`,
  `_project_root_of`, `_live_global_problem`, `_root_covers`, `_GLOBAL_NAME_RE` (plan_io.py), `global_ref_skip_reason`, `host_skills_dir`
  (skills.py); `TestLiveRootCoverage` and the apply test methods that pinned the deleted helpers (covered by 38-06's `TestGsdSkillVerdicts`
  in tests/test_curated_config_e2e.py, named in the commit body). Kept: `_kept_names`, `_round_trip_name`, `_plan_set_command`,
  `_skip_text` and their two tests.

## Verification (run by the chunk agent)

- No deleted name remains in skills/, tests/ or tools/ (rg -w per name: 0 files each); the four kept helpers are still defined; the full
  note text occurs once in plan_edit.py.
- Lanes: test_curated_config_plan_edit + test_curated_config_apply, test_curated_config_skills + test_curated_config_inventory pass; make
  ruff/pyright/vulture/pylint exit 0; hooks 31/31 each. Wave 3 gates and the deferred e2e modules: see the ledger (c38-2).

## Deviations

- Orchestrator decision: the note prints for the trusted-roots key too (the old check covered every agent_skills entry for it), so the
  note replaces the whole old check, not only `agent_skills.*` keys.
- Task 1 split the note string mid-sentence for ruff, which hid it from the plan's acceptance grep; Task 2's commit re-splits it so the
  phrase `the skipped-skill check runs at apply (plan-set has no project root)` is one literal.
- The kept apply classes' docstrings were shortened to what they still test.
