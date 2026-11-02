---
phase: 18-cross-ai-skills-apply-pipeline
plan: 16
executor: cross-ai (pi router-env/my-coding)
requirements-completed: [APP-03]
duration_s: 176
orchestrator_verify: "VERIFY 18-16: 3/3 passed"
---

# Plan 18-16: Config backup and apply marker I/O

Delivered dated config backups, keep-3 pruning, verbatim restore, exclusive apply markers, runner snapshots, and promoted `read_json_object` to `plan_io`.

## Accomplishments

- Added `config_backup.py`: exclusive backup claim via `tempfile.mkstemp` + `os.link`, byte-and-mode reuse (D-20), keep-3 pruning (D-06), atomic restore through `cache_write_bytes` (D-21), apply marker acquire/update/read/clear (D-40), runner snapshot helpers, and branch-complete `recovery_text`.
- Promoted `_read_json_object` from `inventory.py` to `plan_io.read_json_object`; inventory and tests call the public helper only.
- Added `tests/test_curated_config_apply.py` (26 tests): backup/restore tracer, naming collisions, reuse, prune, marker exclusivity (8-thread race), snapshots, and recovery-text branches.
- Regenerated test groups (`Makefile`, `.pre-commit-config.yaml`); `make test-unit` passes.

## Files Created/Modified

- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/config_backup.py` (new, extended across tasks)
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/plan_io.py`
- `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/inventory.py`
- `tests/test_curated_config_apply.py` (new)
- `tests/test_curated_config_inventory.py`
- `Makefile`, `.pre-commit-config.yaml`

## Commits

- `c14da42` — feat(18-16): config backups with verbatim atomic restore
- `2886e6d` — test(18-16): backup collisions, reuse and keep-3 prune
- `e143b33` — feat(18-16): exclusive apply marker and runner snapshots

## Issues Encountered

- `make pyright` still fails on pre-existing errors in `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/skills.py` (lines 100–101, 158); that file was not modified in this plan. Task 3 hooks (ruff, pylint, py-compile) passed on staged files; `make test-unit` exited 0.
