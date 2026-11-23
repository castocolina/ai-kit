---
phase: 36-spec-config-as-the-hub
plan: 03
subsystem: spec-config
tags: [config-status, read-only, trust, migration]

requires: [36-01]
provides:
  - "ai-kit-spec.py config-status --cwd <root> [--role review|execute]: first line active, pending or none, then `checked project <path> <status>` and `checked user <path> <status>`; exit 0"
  - "skills/ai-kit-spec-review/ai_kit_spec/config_status.py: config_status(cwd, env, role=None), cmd_config_status, register_parsers, COMMANDS"

key-files:
  created:
    - skills/ai-kit-spec-review/ai_kit_spec/config_status.py
  modified:
    - skills/ai-kit-spec-review/ai_kit_spec/cli.py
    - tests/test_config_status.py

requirements-completed: [HUB-01]

executor: "cross-AI lane: pi router-env/my-coding, one run (919 s, AIKIT-XAI status=ok exit=0 attempts=1 cycles=0)"
---

# Phase 36 Plan 03: config-status

One commit, `bfe3f87 feat(36-03): report lane configuration status` (pre-fold; 3 files, +322 -4); the commit hook ran 115/115 modules green.

## Accomplishments

- New read-only module `config_status.py` and the `config-status` subcommand (three wiring lines in `cli.py`): `pending` wins over `active`; an untrusted command-bearing project roster and an old roster in a layer with no `[lanes]` table are `pending`; a local-only project skips the user layer; a malformed project file, user file or old roster is a ConfigError (exit 2).
- `tests/test_config_status.py`: 25 tests (tracer 3, states 8, errors 3, read-only 1, combinations 6, role 4), the stub is gone.

## Deviations and notes

- None. No file outside the plan's three paths changed.

## Orchestrator verification (own runs, not the executor's claims)

- `python3 tools/run_unittest_parallel.py tests.test_config_status tests.test_config_layers tests.test_ai_kit_spec_check_providers tests.test_arch_hardcoded_models`: exit 0, 4/4 modules (25, 50, 29 and 14 tests).
- `make ruff`, `make pyright`, `make vulture`: Passed; pylint on `config_status.py` and `cli.py`: Passed. Read the whole `config_status.py` and the `cli.py` diff against the plan's steps.
- Real-config audit (marker-c2-p36-w2): host and other-agent files only (claude jobs, plugin store, synced skills, codex logs and models cache) plus session logs.

## Self-Check: PASSED
