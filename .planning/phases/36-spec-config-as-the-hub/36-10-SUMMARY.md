---
phase: 36-spec-config-as-the-hub
plan: 10
subsystem: spec-config
tags: [migration, keep-backup, probe-quota, review-routing]

requires: [36-03, 36-04]
provides:
  - "skills/ai-kit-spec-review/ai_kit_spec/config_migrate.py: KEEP_BACKUP_ENV, RETIRING_SUFFIX, keep_backup_from_env, migrate_layer(..., keep_backup=False); a verified migration deletes the old roster by default (link, verify, unlink) and keeps the `.migrated` rename only with the opt-in"
  - "render-toml --keep-backup (sets AI_KIT_KEEP_MIGRATION_BACKUP=1 in the env it passes to the migration)"
  - "probe-quota probes the review order (role_orders.role_order(config, 'review')); _route_reviewers routes the review lanes (_review_lanes)"

key-files:
  created: []
  modified:
    - skills/ai-kit-spec-review/ai_kit_spec/config_migrate.py
    - skills/ai-kit-spec-review/ai_kit_spec/config_io.py
    - skills/ai-kit-spec-review/ai_kit_spec/cli.py
    - tests/test_config_migrate.py
    - tests/test_config_layers.py
    - tests/test_ai_kit_spec_legacy_config.py

requirements-completed: []

executor: "cross-AI lane: pi router-env/my-coding, one run (962 s, AIKIT-XAI status=ok exit=0 attempts=1 cycles=0)"
---

# Phase 36 Plan 10: migration without a backup by default

One commit, `e06009b feat(36-10): delete verified migrated rosters by default` (pre-fold; 6 files, +338 -29); the commit hook ran 115/115 modules green. The lane also ran `make test` itself (exit 0: 163/163 unit, 3/3 unit-uv, 9/9 integration, 26/26 e2e, install 48 passed, 2/2 arch).

## Accomplishments

- After the existing value check, the old roster is hard-linked to a free `*.retiring` name, re-read, compared with the snapshot and unlinked only while it is still the same file; a changed or undeletable file stays (`deferred` or a named warning); a failed check deletes nothing. `AI_KIT_KEEP_MIGRATION_BACKUP=1` (read only by `keep_backup_from_env`, passed from `config_io._migrate`) and `render-toml --keep-backup` keep the old `.migrated` rename.
- `probe-quota` switches to the review order and `resolve-reviewers` routes a key shared by a review and an execute lane by its review lane (plan 36-22 later adds `--role`).
- Tests: `test_config_migrate` 56, `test_config_layers` 54 (four new cases, three existing ones now set the keep-backup variable), `test_ai_kit_spec_legacy_config` 24.

## Deviations and notes

- None against the plan. Known limit recorded in the plan and the lane report: a writer that swaps the path between the `samefile` check and the unlink is not caught.
- No file outside the plan's six paths changed.

## Orchestrator verification (own runs, not the executor's claims)

- `python3 tools/run_unittest_parallel.py tests.test_config_migrate tests.test_config_layers tests.test_ai_kit_spec_legacy_config tests.test_config_callers tests.test_config_status tests.test_ai_kit_spec_trust tests.test_ai_kit_spec_routing tests.test_ai_kit_spec tests.test_role_orders tests.test_arch`: exit 0, 10/10 modules (56, 54, 24, 10, 25, 29, 30, 693, 17 and 109 tests).
- `make ruff`, `make pyright`, `make vulture`: Passed; pylint on `config_migrate.py`, `config_io.py` and `cli.py`: Passed. Read the whole source diff against the plan; the acceptance greps hold (`KEEP_BACKUP_ENV` twice in `cli.py`, the four named tests present).
- Real-config audit (marker-c3-p36-w3): host files only (claude job state and plugin-store files, the ponytail mode files of this host session, codex daemon of another project) plus pi session logs.

## Self-Check: PASSED
