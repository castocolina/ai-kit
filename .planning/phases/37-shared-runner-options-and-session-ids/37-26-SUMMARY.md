# 37-26 Summary: curated-config checks an effort level by the runner's token shape

Status: complete in one lane for all three tasks (pi `router-env/my-coding`), verified by the orchestrator.

## Lanes

- fix-a (Tasks 1, 2 and 3): `status=ok exit=0 elapsed=435s attempts=1`, commit 7ecdfa7 (hook 30/30).
- The prompt was built from the plan's own task blocks plus orchestrator anchor notes checked against e99bfa6 (the plan's cross_ai.py line numbers had moved).

## Commits

- 7ecdfa7 `feat(37-26): curated-config checks an effort level by the runner's token shape on every runner`

## What was done

- cross_ai.py: `EFFORT_LEVELS` deleted, `EFFORT_LEVEL_RE = re.compile(r"[a-z][a-z0-9_-]{0,15}")` added; `exec_effort(candidate)` clamps for every runner; `_pick_for_runner` and `plan_edit._plan_set_script_model` pass only the candidate.
- plan_io.py `_validate_effort`: a str matching the token shape on a runner with a model; the refusal names the field and the pattern, never the value; "cannot pin effort" gone. The `RUNNER_IDS` gates are unchanged.
- SKILL.md lines 132-133 replaced in place (line count 412 unchanged).
- Tests: `test_artifact_effort_is_a_token_on_a_runner_with_a_model`, `test_artifact_effort_outside_the_token_shape_is_refused`, `test_catalog_pick_pins_effort_on_every_runner`, `test_no_effort_without_modes_or_with_variant_id`, `TestEffortLevelToken` (template pin).

## Evidence (orchestrator re-run, `tmp/run-2026-11-19/c7-verify-37-26.sh e2cf850`)

- Acceptance greps: no `EFFORT_LEVELS` or `cannot pin effort` in skills/tools sources; RE + new `exec_effort` 2; no `exec_effort(runner_id`; new test names 2 and 3; `runner_id not in cross_ai.RUNNER_IDS` 1 in plan_io.py and 1 in plan_edit.py; old SKILL sentence gone, `reports it ignored` 1; grok counts 3 and 2 in the test files as before, 0 elsewhere; baseline json and detection.py unchanged; no file outside the plan.
- Non-test diff reviewed: verbatim the plan's code blocks.
- Modules 9/9 (curated_config_cross_ai, plan_edit, script, golden, recommend, ai_kit_gsd_curated_config, gsd_curated_eval, apply, arch_hardcoded_models). Lane-reported: `make ruff`, `make pyright`, `make vulture`, `make pylint` exit 0 (the wave gates re-run them).

## Deviations

- None in behaviour. The curated-config SKILL.md change is two lines; its skill-judge round is plan 37-24's changed-SKILL.md loop, as the plan records.
