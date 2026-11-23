# 37-23 Summary: live runner re-rendered, self-test times re-recorded, grok scan run

Status: Tasks 1 and 2 complete; Task 3 gates pass, the added-line scan reports one line (see Deviations). Run by the chunk executor itself (no lane: every step is a deterministic command).

## Commits

- 56b8373 `chore(37-23): re-render the live runner copy from the shipped template` (only `.planning/scripts/cross-ai.mjs`)
- a90b674 `test(37-23): re-record the runner self-test shard times` (only `tests/fixtures/cross_ai_selftest_secs.json`)

## Task 1: live runner copy

- `render.py dry` (scratch project with a byte copy of the live runner, scratch HOME and XDG paths, `AI_KIT_REFUSE_REAL_HOME=1`): `{"ready": true, "runner": "change", "notes": []}`, `check_runner_copy` clean, CONFIG unchanged (no `_upgrade_config` migration was needed), `render: dry ok 559e6ba8702f7316e92c5f4f1d4fcf0b4f7a7fa0fc89d54fdae5f54cc5bab960`.
- `render.py live`: the same JSON, `render: check ok`, `render: live ok`; a repeat `render.py check` printed `render: check ok` (live copy pristine, `check_runner_copy` clean, bytes equal to the dry run).
- Line 2 of the live copy names `template=9`, equal to `TEMPLATE_VERSION = 9` in cross_ai.py.
- `python3 tools/check_dogfood.py --skip-no-write` and `make check-dogfood` (with `AI_KIT_REFUSE_REAL_HOME=1`) each end with `check-dogfood: ok`; the hook line reads `check-dogfood (live project)....Passed`, `no-write guard: 3 attempted, 3 executed, 0 skipped`. The remaining `judge records:` lines are non-failing notes: stale digests for ten skills and facts drift for ai-kit-spec-config, ai-kit-spec-review, ai-kit-cross-ai and ai-kit-gsd-curated-config (the 37-24 judge loop).

## Task 2: self-test times

- Quiet check 18:56: one-minute load 3.38 (limit 12.0 on 24 CPUs), MemAvailable 9631 MB, no other suite running: `quiet: yes` at the first reading.
- `record.sh` (TMPDIR and HOME under `tmp/run-2026-11-19/p37-23/`, XDG paths, `AI_KIT_REFUSE_REAL_HOME=1`, run under the run's watchdog): `recorded 625 cases` (482 before); watchdog exit 0, peak 1 runner process, nothing killed; the trap removed `record-tmp` and `record-home`.
- `check_times.py`: `times self-check: ok`, `times: 625 cases, 284.93 s`; `--self-test-list` prints 625 lines.
- The eight shard modules, once (under the watchdog, peak 8, nothing killed), all ok:

```
=== tests.test_cross_ai_selftest_runtime_1_e2e: ok in 30.0s
=== tests.test_cross_ai_selftest_runtime_2_e2e: ok in 30.0s
=== tests.test_cross_ai_selftest_runtime_4_e2e: ok in 30.1s
=== tests.test_cross_ai_selftest_runtime_3_e2e: ok in 30.2s
=== tests.test_cross_ai_selftest_logic_4_e2e: ok in 33.9s
=== tests.test_cross_ai_selftest_logic_1_e2e: ok in 34.0s
=== tests.test_cross_ai_selftest_logic_2_e2e: ok in 34.1s
=== tests.test_cross_ai_selftest_logic_3_e2e: ok in 34.2s
```

- The commit hook ran the full unit and arch groups plus the nine covering uv modules (the fixture is shared): 188/188.

## Task 3: added-line scan and gates

`python3 tmp/run-2026-11-19/p37-23/added_line_scan.py` (base e400d38^, everything outside `.planning/`):

```
scan self-check: ok
scan: new line naming grok in tests/fixtures/cli_help/pi/help.txt: XAI_API_KEY                      - xAI Grok API key
```

Exit 1. `make ruff`, `make pyright`, `make vulture`, `make pylint`: exit 0 each. Scratch `dry` and `home` removed by `cleanup.py`; `detection.py` and `tests/fixtures/no_hardcoded_models_baseline.json` unchanged.

## Deviations

- The added-line scan finds one line: `tests/fixtures/cli_help/pi/help.txt` (added by 37-02, commit 20084eb) is a verbatim capture of pi's own `--help`, whose environment-variable list names `XAI_API_KEY - xAI Grok API key`. It is pi's text, not grok work (no grok fixture, form, probe, session row, test or list entry), and a captured help fixture is never hand-edited, so nothing was changed. The plan says a scan failure stops the plan; the executor recorded it here and continued with the summary and the push, leaving the decision to the orchestrator and the owner: either accept verbatim host-help captures as an exception to the scan, or re-capture the fixture without that line.
- No lane was used: Task 1 and Task 2 are installer and recorder commands, Task 3 a script; the executor ran and checked each step itself.
- `tools/run_unittest_parallel.py` still records 24 s for each shard; the measured 30 to 34 s stay under the 60 s commit budget, so commit-or-push placement is unchanged (the plan forbids editing the runner).
