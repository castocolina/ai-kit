---
phase: 35-model-discovery-and-catalog
plan: 09
subsystem: testing
tags: [opencode, recorded-help, flag-guard, maintainer-command]

requires:
  - phase: 35-model-discovery-and-catalog
    provides: "35-01 stub test modules; 35-02 hardcoding guard (skips tests/fixtures/cli_help/)"
provides:
  - "tools/record_cli_help.py: maintainer command (main(argv), child_env, --home DIR) that records opencode's own help"
  - "tests/fixtures/cli_help/opencode/: version.txt, help.txt, run-help.txt, models-help.txt, meta.json (version 2.3.2, recorded 2026-11-20)"
  - "tests/test_opencode_help_flags.py: FLAG_RX, extract_flags, recorded_flags, runner_opencode_text, missing_flags; TestOpencodeHelpFlags (7 tests)"

key-files:
  created:
    - tools/record_cli_help.py
    - tests/fixtures/cli_help/opencode/version.txt
    - tests/fixtures/cli_help/opencode/help.txt
    - tests/fixtures/cli_help/opencode/run-help.txt
    - tests/fixtures/cli_help/opencode/models-help.txt
    - tests/fixtures/cli_help/opencode/meta.json
  modified:
    - tests/test_opencode_help_flags.py

requirements-completed: [HUB-08]

executor: "cross-AI lane: pi router-env/my-coding-lite, one run (403 s, status=ok exit=0)"
---

# Phase 35 Plan 09: opencode's recorded help and the flag guard

One commit, `e50d797 test(35-09): record opencode help and guard flags` (per the executor's report the first commit attempt found lint issues and
the retry passed the hook).

## Accomplishments

- `tools/record_cli_help.py --home <scratch dir>` runs the installed opencode (`--version`, `--help`, `run --help`, `models --help`) once with a
  scratch HOME and XDG folders, an environment stripped of every `OPENCODE_*` variable, auto-update and project config off, and cwd in the scratch
  folder; it writes the four text fixtures and `meta.json` atomically. No test runs or imports it.
- Recorded opencode 2.3.2 help is committed byte for byte; it holds the flags the plan names (`--standalone`, `--server`, `--auto`, `--continue`,
  `--session`, `--model`, `--agent`, `--format`, `--help`, `--version`).
- `tests/test_opencode_help_flags.py` extracts every `--flag` of `cli-profiles/opencode.md` and of the runner's `  opencode: {` block (its comment
  lines and argv formulas) as whole tokens and fails naming any flag the recorded help lacks; a planted stale flag fails, a flag that prefixes
  another is never counted as it, a profile with no flag passes. The current profile and runner pass.

## Deviations and notes for the code review

- `meta.json` carries `recorded` 2026-11-20 (the day of the recording); the plan text said "2.3.2 on 2026-11-19", the date of the research.
- No file outside the plan's `files_modified` was touched. The scratch folder is `tmp/p35/09/` (ignored).

## Orchestrator verification (own runs, not the executor's claims)

- `python3 tools/run_unittest_parallel.py tests.test_opencode_help_flags tests.test_arch_hardcoded_models tests.test_arch`: exit 0, 3/3 modules
  (7, 12 and 109 tests).
- `python3 tmp/p35/09/check_fixtures.py` prints `fixtures ok 2.3.2`; `rg -n "record_cli_help" tests/` prints nothing; I read the four text fixtures
  and `meta.json` myself: no account name, e-mail address, home path or key-shaped string.
- `make ruff`, `make pyright`, `make vulture` and `uv run pre-commit run pylint --files tools/record_cli_help.py`: all Passed.
- Real-config audit after the lane: `find` over `~/.config/opencode`, `~/.local/share/opencode`, `~/.cache/opencode`, `~/.local/state/opencode` and
  `~/.opencode` for files newer than the lane's start marker prints nothing (the recorder ran against the scratch HOME); `audit_c2.py` shows nothing
  unexpected for `~/.pi`, `~/.cursor`, `~/.claude` settings and `~/.gsd`.

## Self-Check: PASSED
