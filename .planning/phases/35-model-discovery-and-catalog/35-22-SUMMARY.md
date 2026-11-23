---
phase: 35-model-discovery-and-catalog
plan: 22
subsystem: catalog
tags: [confirm-model, models-config, catalog-cmds, provenance, catalog-lock]

requires:
  - phase: 35-model-discovery-and-catalog
    provides: "35-01 locked_catalog_update and rebase_on_current, 35-03 schema, 35-04 models settings, 35-08 bands, 35-21 facts keep_user_stated, 35-27 fetch-model-catalog"
provides:
  - "catalog_cmds.py: CONFIRMABLE, Refused, cmd_confirm_model, cmd_models_config, register_parsers, COMMANDS (cli.py registers it; the module never imports cli)"
  - "confirm-model: one correction with provenance confirmed_fields[F] = {by, at, note}, heuristic fields through apply_heuristic_corrections, class as a user-stated fact, unknown key exits 1 with a nearest list, bad value exits 2, written under locked_catalog_update"
  - "models-config: writes [models] (project file or --global), --show prints the resolved settings, bad --cache-days or --context tokens exit 2 with a named message"
  - "cli.py: the two older correction writers (confirm-catalog-entry, apply-heuristic-correction) run under the catalog lock"
  - "tests/test_catalog_cmds.py: 10 tests (TestConfirmModel 7, TestModelsConfigCommand 3; the plan's `test_bad_context_tokens` is in the latter)"

key-files:
  created:
    - skills/ai-kit-spec-review/ai_kit_spec/catalog_cmds.py
  modified:
    - skills/ai-kit-spec-review/ai_kit_spec/cli.py
    - skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py
    - tests/test_catalog_cmds.py

requirements-completed: []

executor: "cross-AI lane: pi router-env/my-coding-lite, one run (842 s, AIKIT-XAI status=ok exit=0 attempts=1 cycles=0)"
---

# Phase 35 Plan 22: confirm-model and models-config

One commit, `2e081e8 feat(35-22): add confirm-model and models-config catalog commands` (pre-fold); the commit hook ran 98/98 modules green.

## Accomplishments

- `confirm-model` corrects one catalog field with provenance; the read-modify-write runs inside `locked_catalog_update`, every helper result is assigned
  explicitly, and earlier `confirmed_fields` entries are kept. A confirmed `class` is a `user-stated` fact and survives a rebuild
  (`test_confirmed_class_survives_rebuild` proves the competing computed class first).
- `models-config` writes `[models]` through `write_models_settings` and shows the resolved settings; the Artificial Analysis key has no option.
- `cli.py` registers the commands (two lines) and moves `_cmd_confirm_catalog_entry` and `_cmd_apply_heuristic_correction` under the lock.

## Deviations and notes for the code review

- `model_catalog.py` was modified though the plan did not list it: `locked_catalog_update` gained a keyword-only `replace_unreadable` flag. Plan 27's
  `_write_fetch_catalog_result` reset a corrupt catalog to `{}` before the locked write; the lane moved that recovery into the lock
  (`replace_unreadable=True`) and removed the pre-reset. Behaviour is kept (`test_garbage_catalog_file_is_replaced_by_a_valid_fetch` passes); the
  reset no longer happens outside the lock. This is the 35-27 note in the review list, now implemented inside the lock.
- The exception is public `Refused` (not `_Refused`) so cli.py can use it without pylint's protected-access finding.
- Acceptance grep `rg "cache_write_json\(args.catalog_path"` still matches one line in `cli.py`: the `.fetch-meta.json` sidecar write, not a catalog write.
- The plan named nine tests; the lane wrote ten (an extra `test_confirmed_class_survives_rebuild` the behaviour list required).
- `cmd_models_config` lets `config_io.ConfigError` propagate (cli.main maps it to exit 2) as the plan says.

## Orchestrator verification (own runs, not the executor's claims)

- `python3 tools/run_unittest_parallel.py tests.test_catalog_cmds tests.test_ai_kit_spec tests.test_models_config tests.test_arch_hardcoded_models
  tests.test_arch tests.test_skill_text_history tests.test_gate_scope tests.test_catalog_fetch`: 8/8 modules ok (10, 693, 14, 14, 109, 45, 62, 17 tests).
- `make ruff`, `make pyright`, `make vulture` rc 0; pre-commit pylint on `catalog_cmds.py`, `cli.py`, `model_catalog.py` rc 0.
- Read `catalog_cmds.py` whole and the `cli.py` and `model_catalog.py` diffs; `git diff --stat 827c326 2e081e8`: 4 files, 420 insertions, 24 deletions
  (no formatting noise).
- Real-config audit (marker-c6-w9): only host and other-agent files (Claude jobs, plugin store, skills sync, `.codex` logs and models cache written by
  another agent's codex process); nothing from the lane (pi session log only).

## Self-Check: PASSED
