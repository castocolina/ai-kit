---
phase: 35-model-discovery-and-catalog
plan: 04
subsystem: config
tags: [models-config, layered-reader, toml-splice, context-overrides]

requires:
  - phase: 35-model-discovery-and-catalog
    provides: "35-01 stub test modules; 35-02 hardcoding guard"
provides:
  - "skills/ai-kit-spec-review/ai_kit_spec/models_config.py: KNOWN_SOURCES, SOURCE_KEYS, DEFAULT_CACHE_DAYS, ContextOverride, ModelsSettings, read_models_settings, write_models_settings"
  - "tests/test_models_config.py: TestModelsConfig (14 tests)"
  - "docs/config/design.md: the [models] keys and the stable schema-4 catalog keys"

key-files:
  created:
    - skills/ai-kit-spec-review/ai_kit_spec/models_config.py
  modified:
    - tests/test_models_config.py
    - docs/config/design.md

requirements-completed: [HUB-03]

executor: "cross-AI lane: pi router-env/my-coding-lite, one run (1023 s, status=ok exit=0)"
---

# Phase 35 Plan 04: the [models] table of config.toml

One commit, `c7e8c80 feat(35-04): add layered model config settings`.

## Accomplishments

- `read_models_settings(cwd, env)` reads `[models]` through `config_io.cfg_layered_table` (project over user, per key) and returns
  `ModelsSettings(sources, cache_days, context)`; absent or empty gives the three sources and 7 days each.
- Named `ConfigError`s for an unknown source (with the known set), a bad `cache_days` key or value, a bad `[[models.context]]` entry
  (by index) and an unknown `[models]` key. A project `[[models.context]]` array replaces the user array, also when the project
  states an empty one (`context = []` written under `[models]`).
- `write_models_settings` validates first, splices only `[models]` keys through `toml_splice` (comments and other tables kept), creates
  the file on a first write, publishes atomically and has no key parameter: the Artificial Analysis key never reaches `config.toml`.
- `docs/config/design.md` replaces the "Not read in Phase 33" line of `[models]` and lists the schema-4 catalog keys.

## Deviations and notes for the code review

- The plan text says `tests.test_models_config` holds "13 test names"; its two tasks list 6 plus 8, and the module has 14 tests.
- The doc line says `[models]` is "written by `models-config`"; that command is a later plan's (the CLI for these settings).
- No file outside the plan's `files_modified` was touched.

## Orchestrator verification (own runs, not the executor's claims)

- `python3 tools/run_unittest_parallel.py tests.test_models_config tests.test_config_design_record tests.test_arch_hardcoded_models`:
  exit 0, 3/3 modules (14, 11 and 12 tests).
- `rg -c "Not read in Phase 33" docs/config/design.md` prints 1; `rg -n "ARTIFICIAL_ANALYSIS_API_KEY|open\(" models_config.py` prints nothing.
- `make ruff`, `make pyright`, `make vulture` and `uv run pre-commit run pylint --files .../models_config.py`: all Passed.
- Real-config audit after the lane: no file changed under `~/.pi` (session logs only), `~/.config/opencode` or `~/.cursor`; the other changes
  belong to the Claude host (plugin store, skills sync) and to a codex app-server daemon of another project.

## Self-Check: PASSED
