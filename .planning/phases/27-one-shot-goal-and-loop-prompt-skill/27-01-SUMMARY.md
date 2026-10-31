---
phase: 27-one-shot-goal-and-loop-prompt-skill
plan: 01
subsystem: tooling
tags: [goal-prompt, stdlib, parity-tests, fixtures, pyright, test-groups]

# Dependency graph
requires: []
provides:
  - "gp_common.py stdlib helpers: phase_key, make_targets, read_package_scripts, package_runner (copies, parity-tested)"
  - "gp_common.py guards and file helpers: is_machine_path, scan_text (never flags a leading slash), slugify, unique_path, strip_ansi, GuardError"
  - "tests/goal_prompt_fixtures.py: temp-root builders for OpenGSD, original-GSD, superpowers and empty projects, plus e2e Makefile/package/Playwright/Cypress/PTY variants"
  - "Stub skills/ai-kit-spec-goal-prompt/SKILL.md (real skill written by plan 27-10)"
  - "pyproject.toml pyright extraPaths for the skill and its scripts directory"
  - "Regenerated test-group listings in Makefile and .pre-commit-config.yaml for the new test module"
affects: [27-02 through 27-13 (every later goal-prompt plan imports gp_common and the fixtures)]

# Actuals (#2632): chars/4 over the realized diff (git diff 36ee536..HEAD = 40887 bytes)
actuals:
  tokens: 10222
  tasks: 2
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Copy-with-parity (D-03): a helper copied from a sibling is tested against the original loaded by file path"
    - "Fixture builders write only under a caller-owned TemporaryDirectory"

key-files:
  created:
    - skills/ai-kit-spec-goal-prompt/SKILL.md
    - skills/ai-kit-spec-goal-prompt/scripts/gp_common.py
    - tests/test_ai_kit_spec_goal_prompt_common.py
    - tests/goal_prompt_fixtures.py
  modified:
    - pyproject.toml
    - Makefile
    - .pre-commit-config.yaml

key-decisions:
  - "Helpers are copied from their three originals, not imported, so the skill has no cross-skill dependency; each copy has a parity test that loads the original by path."
  - "scan_text checks only the home string (at least 2 characters), non-empty secrets and the sk-/ghp_ key shapes; problem strings name the kind of problem and never echo the match."
  - "Original-GSD fixtures reuse opengsd_project plus identity_json(False) instead of a separate builder."

patterns-established:
  - "Parity test: load the original file with importlib.util.spec_from_file_location and compare outputs over a table."
  - "Guard test: a fake home literal (FAKE_HOME) and a sentinel key; nothing is created on disk."

requirements-completed: []  # GPS-02 and GPS-04 are listed in this plan's frontmatter, but this plan only delivers their foundations; see Deviations.

# Metrics
duration: unmeasured (start time was not recorded)
completed: 2026-10-31
status: complete
---

# Phase 27 Plan 01: Shared goal-prompt helpers, parity tests, fixtures and the skill stub Summary

**Stdlib-only goal-prompt helpers copied from three siblings with parity tests against the originals, plus temp-root fixture builders and the gate registration for the new scripts directory**

## Performance

- **Duration:** unmeasured (the start timestamp was not recorded)
- **Tasks:** 2 of 2 completed
- **Files created:** 4; **files modified:** 3

## Accomplishments
- `gp_common.py` holds the three copied helpers (`phase_key`, `make_targets`, the package-script reader and lockfile runner) and each has a parity test that loads the original file by path and compares outputs over a table.
- `is_machine_path`, `scan_text`, `slugify`, `unique_path` and `strip_ansi` exist and are tested; `scan_text` does not flag `/goal` or `/gsd-autonomous ...` lines.
- `tests/goal_prompt_fixtures.py` builds the four project kinds and the e2e variants in a caller-owned temp root, with smoke tests for each builder.
- The pyright `extraPaths` includes the skill and its scripts directory; the generated test-group listings were refreshed and `tests.test_gate_scope` is green.

## Task Commits

1. **Task 1: gp_common.py with parity tests, and the stub SKILL.md** - `344ef2a` (feat)
2. **Task 2: Fixture project builders and the pyright path** - `f74e626` (test)

**Plan metadata:** recorded in the docs commit that adds this file (see the completion report).

## Files Created/Modified
- `skills/ai-kit-spec-goal-prompt/scripts/gp_common.py` - shared stdlib helpers, copies named with their source file and line
- `skills/ai-kit-spec-goal-prompt/SKILL.md` - stub frontmatter (`name:` plus one description line) and a work-in-progress line
- `tests/test_ai_kit_spec_goal_prompt_common.py` - 27 tests: parity, guards, slug/unique, ANSI, stdlib-only AST check, fixture smoke tests
- `tests/goal_prompt_fixtures.py` - fixture builders (not a test module)
- `pyproject.toml` - pyright `extraPaths` entries for the skill and its scripts dir
- `Makefile`, `.pre-commit-config.yaml` - regenerated test-group listings via `tools/gen_test_groups.py`

## Decisions Made
- Copy-with-parity instead of importing the sibling helpers (D-03), so the skill has no cross-skill import.
- `scan_text` problem strings name the kind of problem only, so a leaked secret or home path is never echoed in an error.

## Deviations from Plan

### Notes on scope

**1. Task 2 edited the test module created in Task 1.** The plan's Task 2 action adds the `TestFixtures` class to `tests/test_ai_kit_spec_goal_prompt_common.py`, so that file is in the Task 2 commit as well.

**2. [Scope note] Requirements GPS-02 and GPS-04 were not marked complete.** The plan lists them in its `requirements` frontmatter, but this plan only delivers the shared foundations; the requirement behaviour lands in later plans. I did not run `requirements mark-complete`, and `requirements-completed` is empty so the SUMMARY does not claim more than was delivered. The phase verifier should mark them once the later plans land.

**3. [Scope note] STATE/ROADMAP.** See the Self-Check and state-update notes below.

## Known Stubs

| File | Line | Reason |
|------|------|--------|
| skills/ai-kit-spec-goal-prompt/SKILL.md | 1-6 | Intentional stub; plan 27-10 writes the real skill. Recorded in `.planning/WINDOWS.md` so the ship gate sees it until 27-10 closes it. |

## Threat Flags

None. No network endpoint, auth path, or schema change at a trust boundary was added.

## Unverified Items

- The parity tests compare copies against their originals on the listed tables only. They do not prove equality on every input the originals accept.
- `scan_text` covers the two key shapes named in the plan (`sk-` and `ghp_`) and the given home and sentinel. Other secret formats are not covered.
- `make validate` and `make test` were not run as whole targets. I ran the pre-commit hooks that gate each commit (ruff, pylint, py-compile), pyright and vulture on the touched paths, the new test module and `tests.test_gate_scope` directly, and the unit and arch groups through `tools/run_unittest_parallel.py` (64/64 modules reported passed).

## Self-Check

- Created files exist: `skills/ai-kit-spec-goal-prompt/SKILL.md`, `skills/ai-kit-spec-goal-prompt/scripts/gp_common.py`, `tests/test_ai_kit_spec_goal_prompt_common.py`, `tests/goal_prompt_fixtures.py`.
- Commits `344ef2a` and `f74e626` are on the branch and follow the `feat(27-01):` and `test(27-01):` subjects.
- `commits: 2` was measured as `git rev-list --count 36ee536..HEAD` at the time of writing.

## Self-Check: PASSED
