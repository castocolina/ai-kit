---
phase: 41-superpowers-adapter-refactor-with-spec-config-handoff
plan: 08
subsystem: runner template version 14 and the live runner copy
tags: [cross-ai, runner, template-version, render, self-test-times]
requires: [41-07]
provides:
  - "tests/fixtures/cross_ai_selftest_secs.json re-recorded: 922 cases (916 + the six realhome cases)"
  - "tools/run_unittest_parallel.py E2E_RECORDED_SECS: nine entries updated to the measured whole seconds"
  - "template version 14: cross-ai.mjs header and comment, TEMPLATE_VERSION = 14, describe golden, seven curated-config plan goldens, cross-ai SKILL.md floor `template=14`, curated-config SKILL.md, runner.md title and shipped-template sentence, README, test_curated_config_script"
  - "cross-ai SKILL.md Pitfalls: the runner sets AI_KIT_REFUSE_REAL_HOME=1 for every exec lane inside an ai-kit checkout"
  - ".planning/scripts/cross-ai.mjs re-rendered by ensure-runner (template 14, CONFIG kept, pristine)"
affects: [41-13, 41-14]
key-files:
  modified:
    - tests/fixtures/cross_ai_selftest_secs.json
    - tools/run_unittest_parallel.py
    - skills/ai-kit-spec-review/references/cross-ai.mjs
    - skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai.py
    - tests/fixtures/runner_describe_golden.json
    - tests/fixtures/curated_config_v2/golden/ (seven plan goldens)
    - skills/ai-kit-cross-ai/SKILL.md
    - skills/ai-kit-gsd-curated-config/SKILL.md
    - skills/ai-kit-gsd-curated-config/references/runner.md
    - README.md
    - tests/test_curated_config_script.py
    - .planning/scripts/cross-ai.mjs
decisions:
  - "The readiness floor stays template 9; no builder flag added."
  - "The curated-config SKILL.md change is a version-number substitution only; the cross-ai SKILL.md change (floor and guard sentence) is for the skill judge loop."
metrics:
  tasks: 3
  commits: 2
---

# Phase 41 Plan 08: template version 14 and the re-rendered live runner Summary

Run natively by the chunk executor as the orchestrator's delegate (plan is `cross_ai: false`), in one window with 41-07: the
runner self-test case times were re-recorded for the six new realhome cases, the template version went 13 -> 14 with every pin,
the cross-AI caller contract gained the guard sentence, and the project's live runner copy was re-rendered through
`ensure-runner` and committed together with the bump. `make check-dogfood` is green again.

## Commits

| Task | Commit | Subject |
|------|--------|---------|
| 1 | 2bf454f | test(41-08): re-record the runner self-test case times |
| 2+3 | 4c72343 | chore(41-08): template version 14 and the re-rendered live runner with the real-home guard |

## Task 1: shard times

- Quiet check: load1 45.56 at 09:31 (another project's process, not this run's) falling to 9.27 at 09:35:35, limit 12.0 ->
  `quiet: yes`; record start load 6.23 26.08 25.10, end 1.55 13.67 21.89.
- `record.sh`: `recorded 922 cases` (916 before 41-07, plus 6); `times.sh`: `times self-check: ok`, `times: 922 cases, 796.98 s`.
- `shards.py` under the watchdog (exit 0, peak 12, not killed); `check_reports.py`: `reports self-check: ok`, `shard reports: ok 13`;
  `check_log.py`: `shards log: ok`. The 13 lines:
  - `=== tests.test_cross_ai_selftest_logic_1_e2e: ok in 42.9s`, `logic_2 ok in 44.2s`, `logic_3 ok in 42.6s`, `logic_4 ok in 44.3s`,
    `logic_5 ok in 45.2s`
  - `=== tests.test_cross_ai_selftest_runtime_1_e2e: ok in 40.4s`, `runtime_2 ok in 40.4s`, `runtime_3 ok in 39.3s`,
    `runtime_4 ok in 38.4s`, `runtime_5 ok in 40.4s`, `runtime_6 ok in 34.7s`, `runtime_7 ok in 40.0s`
  - `=== tests.test_cross_ai_runner_e2e: ok in 17.0s`
- Load skew in the recording (open item for the orchestrator): over the 916 cases shared with the previous table the sum went
  518.77 -> 794.41 s; new/old ratio p10 1.00, median 1.00, p90 3.96, max 4.64. About a tenth of the cases ran while the earlier
  load was still decaying and are recorded up to 4.6 times slower. That only unbalances the shards; all 13 modules stayed under
  60 s at record time and in both commit hooks. A re-record on a fully quiet machine is the orchestrator's call.
- Recorded changes applied to `E2E_RECORDED_SECS`: runner_e2e 18 -> 17, logic_2 43 -> 45, logic_4 43 -> 45, logic_5 43 -> 46,
  runtime_1 40 -> 41, runtime_2 40 -> 41, runtime_5 39 -> 41, runtime_6 39 -> 35, runtime_7 39 -> 40. All modules stay under 60 s.
- Commit 2bf454f under the watchdog (exit 0, peak 9): hook full unit + arch `221/221 modules passed`, uv `17/17` (all 12 shards
  and the runner e2e); nothing deferred.
- `make check-dogfood` after Task 1: exactly the one expected problem line
  `check-dogfood: .planning/scripts/cross-ai.mjs differs from the template outside the config block`.

## Task 2: version 14 staged

- Pin search: 17 hits before (the plan's list), none after.
- `golden.sh` and `plan-golden.sh`: the eight-golden diff is one `"template_version": 13 -> 14` and seven `"version": 13, -> 14,`.
- Verify (`tests.sh`, scratch HOME, real node): runner_describe 20, cross_ai_skill_text 40, cross_ai_settings_text 25,
  cross_ai_docs_text 40, curated_config_script 50, curated_config_golden 15, ai_kit_gsd_curated_config 106, skill_text_history 45,
  quota_policy_text 20, runner_skills_argv 14, lane_failure_text 31: `11/11 modules passed`. `lint.sh`: ruff, pyright, vulture,
  pylint Passed.
- SKILL.md bodies: ai-kit-cross-ai 6322 -> 6354 words (403 lines); ai-kit-gsd-curated-config 4665 words unchanged (420 lines).

## Task 3: live re-render

- Pre-render HEAD 2bf454f4811d3bc3669806709f2dd80dc993a18b, live sha256 9cc5fff4ea2cbccae6b87c04e87b4f56a5feaf5b75ba4b5d2dbba0bf8442baf2.
- `render.py dry`: `{"ready": true, "runner": "change", "notes": []}`, no migration or CONFIG-key line,
  `render: dry ok db122a924ae08e570a4e970c390b04cf04486b61a33cb390716af6e459f92dbb`. Dry vs live diff: header version and stamp,
  the comment's v14, the marker walk block and the exec env line; nothing else. Approval line in the run ledger.
- `render.py live`: `render: check ok`, `render: live ok`; no `.new`; line 2 `template=14`; `AI_KIT_REFUSE_REAL_HOME` once in the
  live copy. `--print-argv` (template exec and review, live exec) identical to before 41-07 after uuid normalization.
- Commit 4c72343 under the watchdog (exit 0, peak 9): 16 paths (the 15 staged plus the live copy); hook full unit + arch
  `225/225 modules passed`, uv `21/21` (12 shards, runner e2e, curated-config e2e and apply e2e); deferred
  `tests.test_ai_kit_gsd_curated_config_matrix` (run after the commit, below).
- `dry/` and `home/` removed. `render.py check`: `render: check ok`. `make check-dogfood`: exit 0, `check-dogfood: ok`.

## Gates after the plan

- Unit + arch groups under the watchdog: `204/204 modules passed` (exit 0, peak 8, not killed).
- `make ruff`, `make pyright`, `make vulture`, `make pylint`: exit 0 each; `make check-dogfood`: exit 0, `check-dogfood: ok`
  (judge stale-digest and facts-drift lines are notes; `no-write guard: 3 attempted, 3 executed, 0 skipped`).
- Deferred e2e: `tests.test_ai_kit_gsd_curated_config_matrix` under the watchdog, `ok in 162.3s  Ran 35 tests`, `1/1 modules
  passed`. The runner self-test shards and the runner e2e ran in both commit hooks (uv 17/17 and 21/21) and in Task 1's own run.

## Deviations

- None against the plan text. The render approval line was written by the chunk executor as the orchestrator's delegate (the
  orchestrator's brief runs this plan natively), after its own dry run.

## Open items

- Fold: 41-07's runner commits with this plan's bump and re-render into one logical commit, then the local pre-push history
  gate of 41-14, before any checkpoint, consent or push.
