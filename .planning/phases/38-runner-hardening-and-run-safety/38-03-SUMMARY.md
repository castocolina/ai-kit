# 38-03 Summary: visible timeout raise and the restore-claim doc scan

Status: complete. Commit 555a775 (`feat(38-03): show the current cross_ai_timeout the plan replaces and scan docs for a restore claim`). Executed through one cross-AI lane (pi router-env/my-coding) covering both tasks, status=ok on its first run (360 s).

## What changed

- `cross_ai.py`: `timeout_problem(label, value)` moved here from `plan_io.py` (text unchanged); new `timeout_why(key, existing)`: the plain reason for an unset or valid current value, plus `; replaced by 1800: <timeout_problem text>` for an invalid number or boolean, or `; replaced by 1800: <key> holds a <type>, not an integer >= 1800` for a string or container (never echoed).
- `plan_io.py`: `timeout_problem = cross_ai.timeout_problem` (every caller unchanged).
- `recommend.py`: the workflow timeout entry reads the current value once (`timeout_now`) and its reason comes from `cross_ai.timeout_why`; the artifact timeout is untouched.
- `tests/test_curated_config_cross_ai.py`: `TestTimeoutPlanEntry` (1799 raised and named, 1800/3600 kept, absent and explicit null, second apply, apply diff change-then-keep, True/"3600"/2400.5 kept raw and named, the alias) and `TestTimeoutDocClaims` (matcher proven on planted sentences; the scan over skills, docs and READMEs finds no restore or never-touches claim).

## Verification (run by the chunk agent)

- Acceptance greps all at their expected counts; no golden fixture changed; no grok text; baseline and detection.py untouched.
- tests.test_curated_config_cross_ai (55 tests), tests.test_curated_config_plan_edit (90), tests.test_curated_config_recommend (139): all pass. The lane ran make ruff, pyright, vulture, pylint (exit 0); the commit hook passed 31/31 covering modules.

## Deviations

- One commit for both tasks instead of one per task (the chunk's lane prompt asked for one; the wave fold makes one commit per plan anyway).
- The test import `apply as apply_mod` sits on its own `from ai_kit_gsd_curated_config import apply as apply_mod` line above the existing import block, because ruff's isort rule does not combine an aliased name into that block.
