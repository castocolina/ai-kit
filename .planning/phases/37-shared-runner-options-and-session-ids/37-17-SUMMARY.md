# 37-17 Summary: the runner's read-only `--describe`

Status: complete in two per-task lanes (pi `router-env/my-coding`), verified by the orchestrator.

## Lanes

- fix-a (Task 1): `status=ok exit=0 elapsed=465s attempts=1`, commit 2f441c0 (hook 129/129).
- fix-b (Tasks 2 and 3): `status=ok exit=0 elapsed=571s attempts=1`, commit e2cf850 (hook 129/129).
- Prompts were built from the plan's own task blocks plus orchestrator anchor notes checked against e99bfa6 (no plan-as-written lane: runner-heavy plan).

## Commits

- 2f441c0 `feat(37-17): --describe prints the closed setting lists as one sorted JSON object`
- e2cf850 `feat(37-17): --describe rows with formulas, labels and forms, host availability and a golden file`

## What was done

- cross-ai.mjs: `ownTemplateVersion()`, `describeValue(value)` (sorted keys at every depth), `describeJson(env)`, the `o.describe` branch of `main` before the overlay load (no stdin read, one `AIKIT-XAI status=ok ... exit=0` line); `HERDR_BIN` and `hostAvailable(env, whichFn = which)` after `runChild`; `FORMULA_LABELS` after `RUNTIMES`. Rows are described sorted by id with `formulas`, `formula_labels`, `listing`, `listing_label`, `source` (`unverified`: no row has a source) and every `forms` key copied generically; no `classes` key.
- tests/test_runner_describe.py (replaces the 37-02 stub): 11 tests, the helpers the plan names and the `--write-golden` entry. tests/fixtures/runner_describe_golden.json generated (580 lines, `"available": false`, no absolute path).

## Evidence (orchestrator re-run, `tmp/run-2026-11-19/c7-verify-37-17.sh e99bfa6`)

- Acceptance greps: `describeJson`, `describeValue`, `ownTemplateVersion`, `if (o.describe)`, `HERDR_BIN`, `hostAvailable` once each; 11 test methods; grok lines added 0; baseline json and detection.py unchanged; no file outside the plan.
- `--describe` exits 0, top-level keys `host, reasons, runtimes, schema, settings, states, template_version`, runtimes `claude, codex, copilot, cursor, opencode, pi`; copilot `resume` false; claude and copilot listing null. With `HERDR_ENV=1` and a fake herdr on PATH `host.available` is true and the fake was never run.
- `--self-test-list` 606 cases, no missing-kind line; `--print-argv` byte-equal to e99bfa6 for 14 calls.
- Modules 6/6 (runner_describe, arch_hardcoded_models, arch, cli_help_flags, runner_flags, runner_settings_argv); self-test shards + runner_e2e + exec_formula 10/10; verbose run 11 tests ok, none skipped.

## Deviations

- Node resolution: the plan's `NODE = shutil.which("node")` fails here (the Volta shim cannot run under the test's scratch HOME); the module uses the existing `tests.cross_ai_selftest._real_node_executable()` with the repo root on `sys.path`, so `--write-golden` also works when run directly.
- `SETTING_STATES` already existed (plain array), so Task 1 step 1 was a no-op; the flag doc comment already had a `--describe` line from 37-03, so Task 3 step 1 added none (the orchestrator's anchor note wrongly said none existed; the lane checked and followed the plan's condition).
- `FORMULA_LABELS` is built with `Object.fromEntries` from one row per runtime (id, recorded version, date, facts) instead of a literal object, so the acceptance grep `const FORMULA_LABELS = {` matches 0 times; the behaviour is the plan's (one data constant, labels decide nothing, `test_formula_and_listing_labels_follow_recorded_help` recomputes every label from `--print-argv` and the fixtures). Every current label is `verified`, so `test_label_check_is_not_vacuous` first plants a synthetic `unverified` label before turning it into a wrong `verified` one.
- The module docstring keeps the plan's exact text with `# noqa: E501`.
