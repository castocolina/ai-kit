# 39-16 Summary: skill sorting step, config keys, README rows and the dated notes

Status: complete. Commits 2124176 (`docs(39-16): skill sorting step, config keys and README rows`, Task 1) and d534165 (`docs(39-16):
dated 2026-11-23 notes for REV-03 to REV-05 and roadmap phase 39`, Task 2). Executed through two cross-AI lanes (pi
router-env/my-coding), each status=ok on its first run (362 s with findings=outside_plan_files, 110 s; the Task 1 lane's first commit
attempt failed the hook on an exact eval-id list, its second passed).

## What changed

- `skills/ai-kit-spec-config/SKILL.md`: NEVER bullet `**Never write a skill role the owner did not confirm**`; new `### Step 1.6 — Sort
  unknown skills (optional)` (`classify-skills --cwd`, both jev paths, the advisory proposal, `confirm-skill-role` only after Step 2.1
  announced the target, `--cwd <project root>` or `--global`); Step 2.5 shows a review lane's `capability` string from the review-role dry
  run; Step 4 runs `config-status --cwd <project root>` and shows each `capability <runtime>/<model> <role>: <summary>` line (none for a
  `pending` or `none` roster), plus the roles Step 1.6 wrote, failed confirms and skills left unsorted.
- `skills/ai-kit-spec-config/evals/evals.json`: `edge-sort-skills-jev-absent`, `edge-sort-proposal-is-advisory` (21 cases).
- `docs/config/design.md`: the `[models]` bullet names `[[models.context]]` as the lane's known window (refusal, exit 65); new bullets
  `[skills.roles]` and `[review]` (`edit_lens_pass`).
- `README.md`: the `ai-kit-spec-review` row (capability block, lens skills, pre-spawn refusal, opt-in after-approval pass) and the
  `ai-kit-spec-config` row (the optional sorting step with `classify-skills` and `confirm-skill-role`).
- `tests/test_cross_ai_docs_text.py`: constant `DESIGN`, class `SpecConfigAndConfigDocs` (7 tests).
- `tests/test_ai_kit_spec_check_providers.py`: the exact spec-config eval-id list gains the two new ids (see Deviations).
- `.planning/REQUIREMENTS.md` (REV-03, REV-04, REV-05) and `.planning/ROADMAP.md` (Phase 39 criterion 3): one dated 2026-11-23 note line
  each, citing 39-SPEC "Live facts added 2026-11-23".

## Verification (run by the chunk agent)

- Acceptance: `^### Step 1.6 — Sort unknown skills \(optional\)$` 1; `[skills.roles]` in design.md 1; both eval ids 2; `json.tool` exit 0;
  `def test_` 31 -> 38 (+7, every plan-named test exists under its plan name, 7 of 7), no `unittest.skip`; the four `rg -n -F` note checks
  print one line each, each note is a whole line directly after its anchor line, `git show --numstat` 3/0 REQUIREMENTS.md and 1/0
  ROADMAP.md; no grok text added; the Step 1.6 block 19/21 lines verbatim (the two other lines carry the correction under Deviations).
- Modules: test_cross_ai_docs_text (38), test_spec_config_flow_text (40), test_skill_text_history (45), test_ai_kit_spec_runtimes_table
  (63), test_skill_evals_shape (6), test_ai_kit_spec_check_providers (30), test_spec_chain_text (40) pass. Lanes: ruff, pyright, vulture,
  pylint exit 0; hooks pass (Task 1: 58/58).
- The `--help` of `classify-skills`, `confirm-skill-role` and `config-status` lists every flag the text names (checked before the lane).

## Deviations

- Step 1.6 text corrected to the shipped command: the plan said an unaddressable skill "is not listed"; `skill_classify.cmd_classify_skills`
  prints `not offered <name> hosts=<hosts> reason=<reason>` for it and proposes nothing, so the sentence now says so.
- The design.md `[review]` bullet adds "(at present only codex lanes report one)" after the write condition (orchestrator decision; shipped
  `edit_pass.pick_lane` picks only a lane whose `write` is `workspace` or `full`).
- Changed test outside the plan's file list: `tests/test_ai_kit_spec_check_providers.py`'s `test_skill_evals_have_the_nineteen_cases`
  pinned the exact 19 eval ids and blocked the commit; it is renamed `test_skill_evals_have_the_twenty_one_cases` and its list extended by
  the two new ids (the pin stays exact; nothing is weakened). Task 1's commit holds six files, not five.
- The two `test_new_text_names_no_model` methods (39-15's in `LaneCapabilitySkillTables`, this plan's in `SpecConfigAndConfigDocs`) share
  a name in different classes, as both plans name them.
- No synthetic pins (doc tests only; no patch or mock).
- Task 2's verify list repeats the four lint gates for a `.planning/`-only commit; the lane ran the four `rg` checks and the two doc
  modules, and the commit hook ran the rest.
