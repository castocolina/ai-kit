# 39-17 Summary: template 12, live runner re-rendered, self-test times re-recorded

Status: Tasks 1 to 3 complete. Run by the chunk executor itself (no lane: every step is a fixed installer, recorder or test
command, the 38.1-12 shape).

## Commits

- c152042 `chore(39-17): template version 12 for the phase 39 runner` (the fifteen planned paths, the seven curated-config plan
  goldens included)
- 8e5d36e `chore(39-17): re-render the live runner copy from the template` (only `.planning/scripts/cross-ai.mjs`, +72/-6)
- 81560f7 `test(39-17): re-record the runner self-test shard times and the e2e module times`
  (`tests/fixtures/cross_ai_selftest_secs.json`, `tools/run_unittest_parallel.py`)

## Task 1: template version 12

- Pin search before the edits: the 17 expected hits only; after: none.
- Header `template=12`, comment `(template v12)`, `TEMPLATE_VERSION = 12`; `_READY_TEMPLATE = 9` unchanged. The describe golden
  (`--write-golden`, real node from `_real_node_executable`, so the Volta guard line was left out as planned) and the seven plan
  goldens (`UPDATE_GOLDEN=1`) were regenerated under a scratch HOME and TMPDIR; the diff of the eight goldens is one
  `"template_version": 11` to `12` and seven `"version": 11,` to `12,` lines only. cross-ai SKILL.md `template=12` or later, and its two
  `--print-argv` sentences (lines 59 and 229) now name the `cross-ai: capabilities <JSON>` line (keys `write`, `shell`, `skills`, `mcp`
  as `{value, label}` and `prompt` `{channel, max_bytes}`, checked against `laneCapabilities` in the template); curated-config SKILL.md
  `the bundled template 12.`; runner.md title and the shipped-12 sentence naming the capabilities line (floor stays template 9);
  README `template-12`; the script test asserts `shipped == 12`.
- Verify (`tests.sh`, scratch HOME, real node): runner_describe 20, cross_ai_skill_text 40, cross_ai_settings_text 23,
  cross_ai_docs_text 38, curated_config_script 50, curated_config_golden 15, ai_kit_gsd_curated_config 104, skill_text_history 45,
  quota_policy_text 20, runner_skills_argv 14: 10/10 ok. Commit hook 207/207 modules.

## Task 2: live runner copy

- Pre-render HEAD c152042, live sha256 `733bb448...` pinned; no `.new` file, `.planning/scripts` clean.
- `render.py` (copied byte for byte from p381-12) `dry`: `{"ready": true, "runner": "change", "notes": []}`, no migration line,
  `render: dry ok be6cb492580fbe5a5c0a349fcc80bb592116a98304cee326cc31d400e8aad3fb` (run twice, same digest); the live sha256 was
  unchanged directly before `live`. `live`: same JSON, `render: check ok`, `render: live ok`; no `.new` file; the repeat `check` printed
  `render: check ok`. Live line 2 names `template=12`. No rollback needed. Commit hook: 0 modules.
- The approval line `p39-17 live render: approved head=... live=... dry=...` in the run ledger was written by the chunk executor on the
  authority of the orchestrator's chunk prompt ("The live runner copy `.planning/scripts/cross-ai.mjs` is re-rendered here"), after its
  own dry run (38.1-12 precedent); the ledger also holds `p39-17 dogfood: ok 8e5d36e...`.
- `make check-dogfood` ran with the caller's HOME (the named exception: it reads the real consent record) and only
  `AI_KIT_REFUSE_REAL_HOME=1` exported, at 8e5d36e: hook Passed, `no-write guard: 3 attempted, 3 executed, 0 skipped`, last line
  `check-dogfood: ok`; the other lines are judge-record stale-digest and facts-drift notes (ai-kit-cross-ai and
  ai-kit-gsd-curated-config among them, expected until 39-18).
- Accepted limit: the gap between the live-copy digest check and ensure-runner's own read and re-read (cross_ai_script.py:265-289, :358-388) is not closed by this plan; the orchestrator's maintenance window covered it during the live render.

## Task 3: times, shards, e2e module times

- Preflight: `/tmp` 51 to 53 %, `/var/home` 64 %. Quiet check 13:12: load 2.43 (limit 12.0), MemAvailable 8332 MB, `quiet: yes`.
- `record.sh` (real node first on PATH, scratch HOME and TMPDIR) under the run's guard: `recorded 916 cases` (guard exit 0, peak 1,
  nothing killed; the trap removed `record-tmp` and `record-home`). `check_times.py`: `times self-check: ok`, `times: 916 cases, 520.62 s`.
- The shard measurement waited: a second quiet check (13:22 to 13:27) failed only on its memory line (MemAvailable 7808 to 8127 MB,
  load 0.3 to 2.4), and five one-minute retries read 7306 to 7871 MB. The orchestrator then set this chunk's floor to 6 GiB (the 8 GiB
  floor was its own precondition; the memory was held by another project's process). The 13 modules ran once, in one parallel run, at
  13:35 with load 0.87 and about 7.9 GB available (guard exit 0, peak 9, nothing killed), so these times are an upper bound of what a
  quieter machine gives; against the 38.1 run (904 cases) the logic shards are about 1.5 s slower (eight more logic cases each, on average) and the
  runtime shards are within 0.5 s. `check_log.py`: `shards log: ok`;
  `check_reports.py`: `reports self-check: ok`, `shard reports: ok 13`:

```
=== tests.test_cross_ai_selftest_logic_1_e2e: ok in 42.4s
=== tests.test_cross_ai_selftest_logic_2_e2e: ok in 42.5s
=== tests.test_cross_ai_selftest_logic_3_e2e: ok in 42.4s
=== tests.test_cross_ai_selftest_logic_4_e2e: ok in 42.6s
=== tests.test_cross_ai_selftest_logic_5_e2e: ok in 39.1s
=== tests.test_cross_ai_selftest_runtime_1_e2e: ok in 39.2s
=== tests.test_cross_ai_selftest_runtime_2_e2e: ok in 39.7s
=== tests.test_cross_ai_selftest_runtime_3_e2e: ok in 39.5s
=== tests.test_cross_ai_selftest_runtime_4_e2e: ok in 39.2s
=== tests.test_cross_ai_selftest_runtime_5_e2e: ok in 39.2s
=== tests.test_cross_ai_selftest_runtime_6_e2e: ok in 38.8s
=== tests.test_cross_ai_selftest_runtime_7_e2e: ok in 38.5s
=== tests.test_cross_ai_runner_e2e: ok in 17.2s
```

- Slowest shard 42.6 s: 17.4 s inside the 60 s commit budget; `SHARD_COUNTS` stays logic 5 / runtime 7.
- `E2E_RECORDED_SECS` holds those values rounded up (logic 43/43/43/43/40, runtime 40/40/40/40/40/39/39, runner e2e 18); no other
  line changed (the matrix entry and the table comment are untouched, as the plan says).
- `make ruff`, `make pyright`, `make vulture`, `make pylint` (`lint.sh`, offline): Passed each. Commit hook 81560f7: 203/203 modules.
- `detection.py` and `tests/fixtures/no_hardcoded_models_baseline.json` are not touched by this plan.

## Deviations

- The shard times were measured below the plan's quiet-check memory line (about 7.9 GB available instead of above 8 GiB), on the
  orchestrator's decision; the quiet check's load line was met.
- The four Task 3 helpers were copied from p381-12 with one `cp` call instead of one per file (byte-equal copies, no `p381-12` text).
- No lane was used; no test was added, merged, renamed or weakened, so there are no test-name mappings or synthetic pins in this plan.
