# 39-09 Summary: curated-config `skill_roles`, the derived lens visibility and the propose-and-confirm step

Status: complete. Commits 34b73a7 (`feat(39-09): derive the ponytail visibility from the shared skill table and inventory
skill_roles`, Task 1), f286be4 (`test(39-09): inventory without skill_table or with a broken roles config, and the plan gates`,
Task 2) and af1078f (`feat(39-09): curated-config classify-skills and confirm-skill-role through the review package handlers`,
Task 3). Executed through three cross-AI lanes (pi router-env/my-coding), one per task, each status=ok on its first run (242 s,
236 s, 344 s).

## What changed

- `skill_scan.py`: `PONYTAIL_SKILLS` removed; `ponytail_visibility(skills_roots, home, table=None)` lists the ponytail family
  (`ponytail` or `ponytail-*`) from the shared table's `root_rows` over gsd-core's roots and five hosts, with this skill's own listing
  as the fallback when the table is unavailable; output byte-equal to the old function on the frozen fixture.
- `inventory.py`: `_skill_roles` loads `skill_table` once through `gsd_catalog.load_ai_kit_spec_module`; the inventory gains the
  optional `skill_roles` key (39-04's scan, copilot and agents included); a missing module gives `_SKILL_TABLE_MISSING_WARN`, each scan
  note becomes a `skill_roles: <note>` warning; never an inventory failure.
- `cli.py` (curated-config, orchestrator decision D8 for D-09): `classify-skills` and `confirm-skill-role` register the review
  package's own parsers and run its `COMMANDS` handlers with this CLI's seams; a missing `skill_classify` prints the missing-sibling note
  and exits 2; a ConfigError exits 2.
- `SKILL.md` (curated-config): one bullet naming `skill_roles`, `classify-skills` (advisory) and `confirm-skill-role` (only for a sort
  the user accepts). This file now joins 39-18's judge loop.
- `tests/test_curated_config_skills.py`: `FROZEN_VISIBILITY` and the tests the plan names (102 tests in the module).

## Verification (run by the chunk agent)

- Acceptance greps: `PONYTAIL_SKILLS` 0, the loader call 1, direct `ai_kit_spec` imports 0, the five named tests 5, the validator 1,
  the two handler entries 2, a second sorter copy 0; `plan_io.py` and `tests/test_arch.py` unchanged.
- Before the lane ran I printed the old function's output on the plan's fixture myself: equal to the plan's literal.
- tests.test_curated_config_skills (102), test_curated_config_inventory (116), test_curated_config_recommend (139),
  test_curated_config_apply (119), test_curated_config_golden (15), test_arch (118), test_skill_table (61),
  test_arch_hardcoded_models (23): pass with `report check: ok`. Lanes: ruff, pyright, vulture, pylint exit 0.
- The deferred modules (curated-config matrix, curated-config e2e and apply e2e, test_ai_kit_gsd_curated_config, test_config_*) ran
  at the wave gate (see the ledger).

## Deviations

- pylint statement limit in `_build_parser`: the existing `ensure-project` parser and its one argument became one statement.
- `test_table_unavailable_keeps_five_hosts` passes `cast(dict, None)` for the roots (pyright; the product annotation is unchanged).
- The visibility docstring is shorter than the plan's text (same meaning).
- Known behaviour change (planned, D-15): a future `ponytail-<x>` skill is listed; the listing now comes from `root_rows`, which does
  not apply the old `scan_root` checks beyond the SKILL.md presence (a review item for 39-18).
- `test_classify_skills_same_output_as_review_package` pins jev discovery to a synthetic client (`mock.patch` of
  `ai_kit_spec.jev_names.find_jev`), so the skills installed for the checkout cannot change its result; the plan did not
  name the pin (added by the 39 code review, 39-REVIEW.md INFO-3).
