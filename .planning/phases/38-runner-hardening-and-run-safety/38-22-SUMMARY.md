# 38-22 Summary: `--describe` lists statuses, findings and supervision flags

Status: complete. One commit: 083317b (`feat(38-22): --describe lists statuses, findings and supervision flags, locked to the runner
source`, Tasks 1 and 2 in one cross-AI lane, pi router-env/my-coding, status=ok, 267 s).

## What changed

- skills/ai-kit-spec-review/references/cross-ai.mjs: `SUPERVISION_FLAGS` (`['--baseline', '--forbid', '--idle-timeout', '--plan-id',
  '--sweep']`, frozen) and `FINDING_RESULTS` (the four blocking codes: `no_commit`, `task_uncovered`, `admits_skipped` to `partial`,
  `forbidden_path` to `contract_violation`; no earlier plan had made one), placed directly above `planFindings`; `planFindings` computes
  `blocking` from `FINDING_RESULTS` (same behaviour: `contract_violation` wins over `partial`, informational codes never block), so the
  enforcement, `--describe`, the golden and the doc tests read one map; `describeJson` adds `statuses` (each `STATUS_TABLE` name to its
  default exit), `findings` (`{code, result}` in `FINDING_CODES` order, `info` for the five informational codes) and `supervision_flags`.
  `schema` stays 1 and every existing key is unchanged.
- tests/fixtures/runner_describe_golden.json: regenerated with `--write-golden`; the old keys compare equal to the previous golden.
- tests/test_runner_describe.py: helpers `BLOCKING`, `status_table`, `key_problems`; tests `test_new_keys_beside_the_existing_ones`,
  `test_statuses_equal_the_status_table`, `test_findings_follow_the_closed_list`, `test_supervision_flags_are_parsed_flags` (each flag is
  accepted by `parseArgs`, `--made-up-flag` is refused: non-vacuity), `test_source_lock_catches_a_drift` (extra status, swapped findings,
  missing flag), `test_python_reader_accepts_the_new_keys` (through `read_runner_describe` with its real `run_in_own_group`).

## Verification (run by the chunk agent)

- Acceptance greps: the `SUPERVISION_FLAGS` line, `supervision_flags: [...SUPERVISION_FLAGS]` and `^const FINDING_RESULTS` once each; the
  old `codes.includes('forbidden_path')` statement is gone; the golden holds `"supervision_flags"`, `"statuses"`, `"findings"` and
  `"schema": 1` once each; old keys unchanged against 10ee436.
- `node --check` passes; the six `pure-findings-*` cases plus `ok` and `nochange` print `self-test ok`; `--self-test-list` 777 lines (no new
  case); `--print-argv` of six calls byte-equal to 10ee436.
- `tests.test_runner_describe` (17 tests), `tests.test_runner_facts`, `tests.test_arch_hardcoded_models`, `tests.test_arch` pass; `make
  ruff`, `make pyright`, `make vulture`, `make pylint` passed in the lane; the commit hook ran 129/129 modules (the curated-config matrix
  deferred to push). `detection.py` and the model-literal baseline unchanged.

## Deviations

- One commit for both tasks (the plan names one per task).
- The plan's `pure.sh` and the golden-old copy were replaced by `tmp/run-2026-11-19/p38-22/selftest.py` (real node) and `same_keys.py`
  (compares against the golden of the previous commit).
- `key_problems` checks the sortedness of the source flag list it compares against (equal to the describe list whenever the lists match).
