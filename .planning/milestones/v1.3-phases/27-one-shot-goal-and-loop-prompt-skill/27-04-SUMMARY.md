---
phase: 27-one-shot-goal-and-loop-prompt-skill
plan: 04
subsystem: tooling
tags: [goal-prompt, e2e, detection, makefile, package-json, playwright, cypress, pty, zero-test, stdlib]
requires:
  - phase: 27-01
    provides: "gp_common make_targets, read_package_scripts and package_runner (copies, parity-tested); fixture builders"
provides:
  - "gp_e2e.detect_e2e(repo) -> E2EResult: commands (make, package, playwright/cypress, pty), gates, none"
  - "gp_e2e.ZERO_TEST_MARKERS: labelled zero-test marker table (four verified rows, six unverified)"
  - "gp_e2e.markers_for_text(command): marker rows whose runner appears in a command string"
affects: [27-09 detect CLI, done-check rendering plans]

key-files:
  created:
    - skills/ai-kit-spec-goal-prompt/scripts/gp_e2e.py
    - tests/test_ai_kit_spec_goal_prompt_signals.py
  modified:
    - Makefile
    - .pre-commit-config.yaml

key-decisions:
  - "A PTY driver is mapped only to an e2e Makefile target whose recipe names it; a driver named only by a non-e2e target, or by none, is listed as inferred."
  - "Package script names must match `[A-Za-z0-9_.:/@-]+`; any other name is skipped, because the name is copied into a command meant to be pasted."
  - "Package `test`/`lint` become gates only when the Makefile has no gate target; Makefile gates always win."
  - "The shell-harness row carries no exit code (the table gives only the count line); its marker is `0 passed`."
  - "Driver scanning skips symlinks, files over 200 KB and anything past the first 80 lines."

patterns-established:
  - "Negative guard tests are checked for non-vacuity: each guard was disabled in a scratch run and its test's expectation then fails."

requirements-completed: []  # GPS-03 detection logic is delivered; the detect CLI that exposes it lands later (same precedent as 27-01 and 27-03).

# Actuals (#2632): chars/4 over the realized diff (39056 bytes for the four files changed)
actuals:
  tokens: 9764
  tasks: 2
  commits: 2
  plan_head_before: 477fb45a4e52e6561b91a02deccfd3892ab2a716
  plan_head_after: 6272d70602bd21e3387fda2c69a44cbf3799fd20

# Metrics
duration: unmeasured (start time was not recorded)
completed: 2026-10-31
status: complete
---

# Phase 27 Plan 04: E2E command detection, gate commands and the zero-test marker table Summary

**Read-only, stdlib-only detection of the project's e2e commands (Makefile, package scripts, Playwright/Cypress configs, PTY drivers) with the gate commands that run before them, plus a labelled zero-test marker table**

## Performance

- **Duration:** unmeasured (the start timestamp was not recorded)
- **Tasks:** 2 of 2 completed
- **Files created:** 2; **files modified:** 2 (test-group listings only)

## Accomplishments
- `detect_e2e` finds every Makefile target named `e2e`, `e2e-*`, `e2e_*` or `e2e.*` in declaration order. `end2end`, `my-e2e-test` and `e2elike` are not e2e.
- Package scripts named `e2e`, `e2e:*` or `*:e2e`, or whose body runs playwright or cypress, become `<runner> run <name>` commands with the runner taken from the lockfile. The script body is never copied.
- Playwright and Cypress configs add `npx`/`pnpm exec`/`yarn`/`bunx` commands; a config adds nothing when a package script already runs that browser.
- `gates` lists `make test`, `make lint`, `make validate`, `make test-unit` in that fixed order when present, else package `test`/`lint`. No e2e target is ever a gate.
- `none` is `True` only when no e2e command exists.
- PTY drivers under `tests/` (pty, pexpect, ptyprocess, node-pty imports; Textual-pilot files excluded) map to the e2e target whose recipe names them, else are `inferred`.
- `ZERO_TEST_MARKERS` labels unittest, `node --test`, `go test` and the shell harness `verified: True`; pytest, jest, vitest, Playwright, Cypress and cargo are `verified: False`.
- Dogfood on this repository: `make e2e-test` and `make e2e-docker` are detected as `detected`; `tests.test_wizard_pty` is listed as `inferred` (integration tier).

## Task Commits

1. **Task 1: Makefile, package-script and config-file e2e signals plus gate commands** - `3dc3e26` (feat)
2. **Task 2: PTY drivers, the zero-test marker table, and the dogfood detection** - `6272d70` (feat)

**Plan metadata:** recorded in the docs commit that adds this file (see the completion report).

## Files Created/Modified
- `skills/ai-kit-spec-goal-prompt/scripts/gp_e2e.py` - detection, PTY mapping, marker table (stdlib only; imports `gp_common`)
- `tests/test_ai_kit_spec_goal_prompt_signals.py` - 30 tests: `TestSignals` (15) and `TestPtyAndMarkers` (15), temp projects only plus the dogfood read of this repo
- `Makefile`, `.pre-commit-config.yaml` - test-group listings regenerated with `tools/gen_test_groups.py` (the new module added to the unit group)

## Decisions Made
See `key-decisions` in the frontmatter. The two that change behaviour beyond the plan text are the safe-name check on script names (T-27-09) and the symlink skip in the driver scan.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Lint] Over-long docstring line (ruff E501, pylint C0301)**
- **Found during:** Task 1, before its commit
- **Fix:** shortened the `_make_signals` docstring; behaviour unchanged.
- **Commit:** `3dc3e26`

**2. [Rule 1 - Type] `detect_e2e` returned `dict[str, object]`, so tests could not iterate its values (pyright "object is not iterable")**
- **Found during:** Task 2, before its commit
- **Fix:** added `E2EResult(TypedDict)` as the return type, plus a return annotation on `_owner`.
- **Commit:** `6272d70`

### Plan-shape notes

**3. Gate fallback wording.** The plan's "else package scripts `test`/`lint`" is implemented as a whole-set fallback: package gates appear only when the Makefile has none of the four gate targets. Mixing the two sources was not specified.

**4. PTY mapping scope.** The plan says "the Makefile target whose recipe names its file or module". Implemented as: only e2e-named Makefile targets can own a driver. A driver named by `test-integration` (or by nothing) stays `inferred`. When two drivers name one target, the first sets `driver` and the second is treated as mapped, with no duplicate entry.

**5. Negative guard tests passed before the scanner existed.** The size, 80-line, symlink and Textual-pilot tests assert an empty result, so they were green before the scanner was written; that is expected for guards. Their non-vacuity was then checked directly: a scratch script (`tmp/p27/mutate_check.py`, git-ignored) disabled the size cap, the line cap and the pilot exclusion one at a time, and each made the driver appear in the result, so the matching test's expectation would fail.

### Process notes

**6. Plan verification command.** The Task 2 pyright check in the plan (`... | tail -n 3 | grep -q '0 errors'`) fails as written, because pyright prints a version-update warning after its summary line. Run without the tail, pyright reports `0 errors, 0 warnings`. The code is clean; the command is not.

**7. Pre-commit stash.** Each hook run stashes the unstaged files and restores them. The orchestrator's `.planning/config.json` and another session's `27-14-PLAN.md` edit were still modified and unstaged after both commits. Neither was staged or committed by this plan.

**8. Requirements.** GPS-03 is listed in the plan's frontmatter, but this plan delivers only the detection module. The `detect` CLI and the done checks land in later plans, so `requirements-completed` is empty (same precedent as 27-01 and 27-03).

## Known Stubs

None. `gp_e2e.py` has no placeholder values and no unwired data source.

## Threat Flags

None beyond the plan's register. Detection is read-only and executes nothing from the scanned project; the threat-register mitigations are implemented as written (T-27-09 fixed templates plus a safe name check; T-27-10 the 200 KB, 80-line and `node_modules`/`.git` limits; T-27-11 `verified` on every marker row).

## Deferred Issues

**Architecture rule 10 fails on this branch, caused by plan 27-03 (not fixed here).** `tests/test_arch.py::TestArchitecture::test_rule10_retired_literals_only_in_allowlist` reports `skills/ai-kit-spec-goal-prompt/scripts/gp_host.py:26: retired literal 'cursor-agent'`. Rule 10 allows that literal only in `skills/ai-kit-spec-review/ai_kit_spec/detection.py`. The line was introduced by 27-03 (commit `ef3684f`) and is present at the pre-task HEAD `477fb45`, so it is not caused by this plan. `gp_host.py` belongs to 27-03, and this plan's file scope excludes it, so it was not edited. The owner of 27-03 should build the literal by concatenation (as `tests/test_arch.py` does for its own constants) or move the name into the allowlisted module. Until then `make test` (arch-test) is red on this branch.

## Unverified Items

- The `verified: False` rows (pytest, jest, vitest, Playwright, Cypress, cargo) are labelled from research only; no runner was run here.
- The shell-harness row (`0 passed`) rests on reading `tests/test_install.sh` in research; it was not re-run.
- Detection was checked on the test fixtures and on this repository only; no other real project was scanned.
- The PTY scan reads 80 lines per file, so a driver whose import sits on line 81 or later is missed (an accepted cap, T-27-10).
- `make test`, `make validate` and `make e2e-test` were not run as whole targets. Run here: the goal-prompt unit modules, `tests.test_gate_scope`, `tests.test_arch` (one failure, above), ruff, pylint (10.00), pyright (0 errors) and vulture at 80% confidence on the touched files.
- The dogfood listing `python3 -m unittest tests.test_wizard_pty` is `inferred`. Later plans must treat `inferred` entries as non-gating, as the spec requires.

## Self-Check

- Created files exist: `skills/ai-kit-spec-goal-prompt/scripts/gp_e2e.py`, `tests/test_ai_kit_spec_goal_prompt_signals.py`.
- Commits `3dc3e26` and `6272d70` are on the branch with `feat(27-04):` subjects.
- `commits: 2` was measured as `git rev-list --count 477fb45...HEAD` (ledger base) before this docs commit.
