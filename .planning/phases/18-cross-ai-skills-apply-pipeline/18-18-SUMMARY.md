---
phase: 18-cross-ai-skills-apply-pipeline
plan: 18
executor: cross-ai (pi router-env/my-coding)
requirements-completed: [APP-03, SKL-02]
duration_s: 729
orchestrator_verify: "VERIFY 18-18: 2/2 passed"
---

# Plan 18-18: Apply write path and golden E2E

Implemented the D-22 apply write path (marker, backup, config creation/reconcile, runner snapshot, ordered `config-set`, post-commit cleanup, agent-skills check) with a real gsd-tools golden E2E test and unit coverage for marker, ordering, skips, rollback, and cleanup edge cases.

## Accomplishments

- **`run_apply`** implements the full D-22 sequence: exclusive marker, backup reuse, optional `config-new-project` + reconcile, runner render with snapshot, strict writes, commit point, and `_cleanup_committed` (committed flag, skill check, marker/snapshot/prune with warnings-only failures).
- **CLI** non-dry-run branch calls `run_apply` and prints the JSON report.
- **E2E** `TestRealApply.test_apply_golden_plan` applies a decided claude plan against checkout-local gsd-core 1.16.x and verifies agent skills with no warnings.
- **Unit** `TestApplyWritePath` (11 cases) covers held marker, write order, skips, rollback paths, pi skip, forced warning, absent config, `GSD_RUNTIME` on agent-skills, and clear-marker failure after commit.

## Files Created/Modified

- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/apply.py` — write path
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cli.py` — apply branch
- `tests/test_curated_config_apply_e2e.py` — new E2E module
- `tests/test_curated_config_apply.py` — `_decide_all_choices` trusted-root fix + `TestApplyWritePath`
- `tools/run_unittest_parallel.py`, `Makefile`, `.pre-commit-config.yaml` — E2E registration

## Commits

- `2b9ddba` — feat(18-18): apply writes through gsd-tools and verifies agent skills
- `70d7012` — test(18-18): apply order, skips, marker, rollback and failed restore

## Issues Encountered

Several Task 2 behaviors called out in the plan (re-apply runner rollback, edited-runner `.new`, render failure before writes, fresh-project `.planning` removal on failed write, prune/discard snapshot fault cases) are not yet covered by unit tests; they remain for 18-19 or a follow-up test commit. Verification run: `make test-unit`, full apply/gate unittests, and `make e2e-test` passed; repo `.planning/config.json` and `cross-ai.mjs` unchanged.


## Gap-fill run (orchestrator re-dispatch)

# 18-18 Gap-Fill: Apply Unit Test Coverage

Added the missing Task 2 `TestApplyWritePath` behavior cases; all plan verify commands pass with no implementation changes.

## Accomplishments

- Added `_setup_reapply_change` helper and eight unit tests: re-apply runner snapshot rollback/success discard, edited-runner `.new` (success and failed write), render failure before any `config-set`, fresh-project rollback removing `.planning`, and post-commit `prune_backups` / `discard_snapshot` faults (exit 0, warnings, no `_rollback`).
- Verified `python3 -m unittest tests.test_curated_config_apply_e2e tests.test_curated_config_apply tests.test_gate_scope` — OK (103 tests).
- Verified `PATH="$HOME/.local/bin:$PATH" UV_NO_SYNC=1 UV_OFFLINE=1 make test-unit e2e-test` — OK.
- Confirmed `.planning/config.json` and `.planning/scripts/cross-ai.mjs` unchanged in this checkout.

## Files Created/Modified

- `tests/test_curated_config_apply.py` — imports, `_setup_reapply_change`, eight new tests in `TestApplyWritePath`.

## Commits

- `0c03b50` — `test(18-18): gap-fill apply rollback, render and cleanup cases`
- (Prior plan work unchanged: `70d7012`, `2b9ddba`)
