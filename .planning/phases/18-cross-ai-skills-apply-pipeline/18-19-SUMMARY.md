---
phase: 18-cross-ai-skills-apply-pipeline
plan: 19
executor: cross-ai (pi router-env/my-coding)
requirements-completed: [APP-03]
duration_s: 626
orchestrator_verify: "VERIFY 18-19: 3/3 passed"
---

# Plan 18-19: Real apply proofs and write-path discipline

Proved failed real applies restore exact config/runner state, D-20 re-apply and backup behavior, absent-config reconcile, and pinned the config write prohibition with AST tests.

## Accomplishments

- Added six real-gsd-tools E2E cases: Nth-key and absent-config rollback, failed re-apply runner restore, keep-3 prune, D-20 re-apply no-op, and absent-config reconcile (model_policy leaves removed per L589).
- Added `TestCommitPointEdges` for post-commit paths (agent-skills failure, commit-record/marker-clear failures, marker acquire `OSError`) with `_RecordingRun` simulating on-disk config updates for dry-run recovery checks.
- Added `TestWritePathDiscipline` AST scan with non-vacuity fixtures for every SPEC write rule.

## Files Created/Modified

- `tests/test_curated_config_apply_e2e.py` — helpers and six E2E tests
- `tests/test_curated_config_apply.py` — `_RecordingRun` config simulation, `TestCommitPointEdges`, `TestWritePathDiscipline`

## Commits

- `4a7e23a` — test(18-19): real failed applies restore the exact config and runner
- `cb12abc` — test(18-19): real prune, re-apply no-op per D-20, absent-config reconcile
- `b2b84ac` — test(18-19): AST guard for the config write path
