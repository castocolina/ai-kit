# 38-06 Summary: apply asks gsd-core which skills it skips, after binding

Status: complete. Commits ceb65db (`feat(38-06): ask gsd-core which skill references it skips`) and 2bbbf8e (`feat(38-06): apply checks skipped skills through gsd-core after binding`). Executed through two per-task cross-AI lanes (pi router-env/my-coding), each status=ok on its first run (232 s, 418 s).

## What changed

- `plan_io.py`: `SkillCheck` (node, project-local gsd-tools.cjs, apply's env, project, bounded runner); `_GSD_SKILL_SCRIPT` (one `node -e` child calling gsd-core's `buildAgentSkillsBlock` once per reference: an empty block means skipped, the first warning is the cause), `_GSD_SKILL_TIMEOUT_S = 30`, `_NOTE_FAILED`, `_cause_text` (prefix/suffix removed, control characters removed, 300 characters), `_run_skill_child`, `_parse_verdicts`, `gsd_skill_verdicts`; `_candidate_refs`, `_skill_base` (runtime only when the plan writes one), `_skip_text` (extracted from `_skip_message`, text unchanged), `gsd_skipped_skill_problem`.
- `apply.py`: `_skill_check(target, inputs, deps)` (notes for a pi host, a non-local gsd-core, a missing sibling); `prepare` runs the skipped-skill check only after `resolve_target` bound the destination.
- Tests: `TestGsdSkillVerdicts` (5 cases against the real checkout-local gsd-core: missing project skill, symlinked global outside the skills dir, trusted root accepts, `/` and `~` roots never accept, malformed name and absolute path); `TestGsdSkillVerdictNotes` (4 fake-child cases); `fake_skill_child` and five new `TestApplyRefusals` methods (no child before binding, child after binding, entry order, global core note, runtime only when written); the four existing refusal methods run through the fake child.

## Verification (run by the chunk agent)

- Acceptance greps all at their expected counts; no grok text; baseline, goldens and detection.py untouched; apply.py diff reviewed (the old pre-binding call is gone).
- `tmp/run-2026-11-19/p38-06/e2e-verbose.sh`: 5 `TestGsdSkillVerdicts` tests ok against the real gsd-core.
- tests.test_curated_config_apply (120), test_curated_config_plan_edit (90), test_curated_config_skills (90), test_curated_config_inventory (116), test_curated_config_e2e (19): all pass. Lanes ran make ruff, pyright, vulture, pylint (exit 0); hooks passed 31/31 covering modules each.

## Deviations

- The inventory probe also runs `node -e`, so `fake_skill_child` and the new order tests identify the skill child by its script (`plan_io._GSD_SKILL_SCRIPT`), not by `-e` alone; an existing dry-run call-count assertion was raised by one for the added child (a stronger, not weaker, expectation of the new call).
- `Callable` comes from `collections.abc` (ruff UP035) instead of `typing`.
- Open for code review: a gsd-core warning that sanitizes to an empty string would read as "resolves" (`verdicts.get(r)` is falsy); plan edit keeps the old check until 38-27; curated-config SKILL.md:307-318 still describes the old snapshot-only check (no 38 plan owns it).
