# 38-25 Summary: template 10, live runner re-rendered, self-test re-recorded and re-sharded

Status: Tasks 1 to 3 complete. Run by the chunk executor itself (no lane: every step is a deterministic command, the 37-23 shape).

## Commits

- d554534 `chore(38-25): template version 10 for the phase 38 runner` (15 paths: the plan's eight plus seven curated-config plan goldens, see Deviations)
- 1f1c656 `chore(38-25): re-render the live runner copy from the template` (only `.planning/scripts/cross-ai.mjs`)
- 9204dbb `test(38): split the runner self-test into 5 logic and 7 runtime shards so each stays near 40 s` (neutral scope, see Deviations)
- 037c25e `test(38-25): re-record the runner self-test shard times and the e2e module times` (`tests/fixtures/cross_ai_selftest_secs.json`, `tools/run_unittest_parallel.py`)

## Task 1: template version 10

- Pin check (`rg` of the plan's pattern): only the expected hits (the texts the plan edits plus the floor statements it keeps).
- Header `template=10`, comment `(template v10)`, `TEMPLATE_VERSION = 10`; `_READY_TEMPLATE = 9` unchanged. Golden regenerated with `--write-golden` (diff: `"template_version": 9` to `10` only). cross-ai SKILL.md `template=10` or later; curated-config SKILL.md `the bundled template 10.`; runner.md title and the shipped-10 / floor-9 sentence; README `template-10`; the script test asserts `shipped == 10`, `_READY_TEMPLATE == 9` and floor at or below shipped.
- Verify: the seven modules pass (runner_describe 17, cross_ai_skill_text 30, cross_ai_settings_text 23, cross_ai_docs_text 17, curated_config_script 50, ai_kit_gsd_curated_config 104, skill_text_history 45). Commit hook 150/150 (matrix deferred to push).

## Task 2: live runner copy

- `render.py` copied byte for byte to `tmp/run-2026-11-19/p38-25/`. `dry`: `{"ready": true, "runner": "change", "notes": []}`, `render: migration idleTimeoutS` (the template's value 0, expected), `render: dry ok 170a4791a9dd2bd53210bb4c0cd0077ad0da6852f5540ea37b38f71280a165db`. `live`: same JSON, `render: check ok`, `render: live ok`; the repeat `check` printed `render: check ok`. Live line 2 names `template=10`. The 37-23 `dry.sha256` is untouched.
- `make check-dogfood` ran with the caller's HOME (the named exception: it reads the real consent record) and only `AI_KIT_REFUSE_REAL_HOME=1` exported: hook Passed, `no-write guard: 3 attempted, 3 executed, 0 skipped`, last line `check-dogfood: ok`. The other lines are judge-record stale-digest and facts-drift notes (ten skills; ai-kit-cross-ai and ai-kit-gsd-curated-config among them until 38-26).

## Task 3: times, shards, e2e module times, scan, gates

- Preflight: `/tmp` 36 %, `/var/home` 67 %; quiet check 08:41: one-minute load 3.10 (limit 12.0 on 24 CPUs), MemAvailable 14968 MB, `quiet: yes`.
- `record.sh` (the 37-23 script with `p37-23` replaced by `p38-25`) under the run's guard: `recorded 777 cases`; guard exit 0, peak 1, nothing killed; the trap removed `record-tmp` and `record-home`. `check_times.py`: `times self-check: ok`, `times: 777 cases, 464.2 s`.
- Predicted shard seconds from the new times (sum of case seconds): logic at 4 shards 51.5 s, runtime at 4 shards 64.7 s (the hook had measured 56.8 to 68.3 s for the runtime shards, over the 60 s budget). Logic at 5 predicts 41.2 s, runtime at 7 predicts 37.0 s.
- The 13 modules once, in one parallel run (guard exit 0, peak 10, nothing killed), all ok:

```
=== tests.test_cross_ai_selftest_logic_1_e2e: ok in 36.6s
=== tests.test_cross_ai_selftest_logic_2_e2e: ok in 36.1s
=== tests.test_cross_ai_selftest_logic_3_e2e: ok in 36.1s
=== tests.test_cross_ai_selftest_logic_4_e2e: ok in 36.1s
=== tests.test_cross_ai_selftest_logic_5_e2e: ok in 34.4s
=== tests.test_cross_ai_selftest_runtime_1_e2e: ok in 37.1s
=== tests.test_cross_ai_selftest_runtime_2_e2e: ok in 36.9s
=== tests.test_cross_ai_selftest_runtime_3_e2e: ok in 36.5s
=== tests.test_cross_ai_selftest_runtime_4_e2e: ok in 37.2s
=== tests.test_cross_ai_selftest_runtime_5_e2e: ok in 36.3s
=== tests.test_cross_ai_selftest_runtime_6_e2e: ok in 36.1s
=== tests.test_cross_ai_selftest_runtime_7_e2e: ok in 36.3s
=== tests.test_cross_ai_runner_e2e: ok in 16.9s
```

- `E2E_RECORDED_SECS` holds those values rounded up (logic 37/37/37/37/35, runtime 38/37/37/38/37/37/37, runner e2e 17). The two hook runs that followed (9204dbb, 037c25e) measured the shards at 31.6 to 40.8 s: 198/198 and 196/196 modules.
- `make ruff`, `make pyright`, `make vulture`, `make pylint`: exit 0 each.
- Added-line scan (`tmp/run-2026-11-19/p38-25/added_line_scan.py`, the 37-23 scan adapted: base is the merge base with the phase 37 branch, everything outside `.planning/` and the verbatim `tests/fixtures/cli_help` captures, no expected-message allowance): `scan: ok (no new line naming grok)`.
- `detection.py` and `tests/fixtures/no_hardcoded_models_baseline.json` are not touched by this plan.

## Deviations

- The plan's Task 1 named eight paths but missed the seven curated-config plan goldens (`tests/fixtures/curated_config_v2/golden/`: the claude and codex `*-adaptive.json` files and `codex-mvp-budget.json`) that carry the template version: the first commit was refused by the hook (`tests.test_curated_config_golden`, 7 failures). They were regenerated with `UPDATE_GOLDEN=1` under a scratch HOME (diff: `"version": 9` to `10` only) and committed with Task 1.
- Shard budget, resolved at the root (orchestrator instruction; the plan says a shard over budget stops the plan): `SHARD_COUNTS` goes from logic 4 / runtime 4 to logic 5 / runtime 7, with the matching shard modules, `E2E_MODULES`, the regenerated test-group listings (`Makefile`, `.pre-commit-config.yaml`: comment listing lines only) and the four new `E2E_RECORDED_SECS` entries, in the neutral commit 9204dbb. The plan's "eight shard modules / nine modules" is now twelve shard modules / thirteen modules; the measuring scripts take the module list from `SHARD_COUNTS`. AGENTS.md names no shard count, so it is unchanged. The case list did not change after the record, so no second record was needed (the times file is per case).
- No lane was used: every step is an installer, recorder or test command, run and checked by the executor.
