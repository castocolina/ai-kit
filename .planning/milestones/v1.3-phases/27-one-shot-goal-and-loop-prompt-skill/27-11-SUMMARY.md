---
phase: 27-one-shot-goal-and-loop-prompt-skill
plan: 11
subsystem: docs-installer-tests
tags: [goal-prompt, readme, installer-smoke, headless, pty, pyright, ruff, gates, GPS-04]
requires:
  - phase: 27-10
    provides: "SKILL.md and the goal-prompt skill directory the README row links to"
provides:
  - "README skills-table row for ai-kit-spec-goal-prompt"
  - "Recorded headless install of the skill into a scratch HOME (dry run and real run, symlink and SKILL.md checked)"
  - "tests/test_setup.py cmd_install reconcile tests no longer close stdout (suite exits 0)"
  - "tests/test_ai_kit_spec_superpowers.py pyright-clean (two Optional regex matches asserted)"
  - "Phase 27 gate state: integration, unit and arch groups green under uv (78/78) and under system python3 (74/74)"
affects:
  - "27-12, 27-13, 27-14 (remaining phase 27 plans)"

# Actuals (#2632): chars/4 over the git diff of the three task commits (6790 bytes)
actuals:
  tokens: 1698
  tasks: 2
  commits: 3
  plan_head_before: a016ccc2db819c147b21f28f10d5af662b558924
  plan_head_after: dcb103ce3b591e7c52deb651ad2929136dfffcfd

status: complete
requirements-completed: [GPS-04]

key-files:
  created: []
  modified:
    - README.md
    - tests/test_setup.py
    - tests/test_ai_kit_spec_superpowers.py

key-decisions:
  - "PI_SKILLS (tools/setup.py:48) is NOT changed: the skill needs no pi link. The plan states pi has no goal primitive; that was not re-verified in this plan."
  - "_PTY_ROWS stays 160: the wizard PTY suite passed with one more skill, so no sizing change and no assertion change was needed."
  - "README row uses the skill's own frontmatter description, condensed to one row. The README has no skill-count statement to update."

patterns-established:
  - "Installer smoke into a scratch HOME needs AI_KIT_DIR set to the checkout: the headless installer enumerates AI_KIT_DIR, not the directory it was launched from."

metrics:
  duration: "not recorded (start timestamp was not captured in this run)"
  completed: 2026-10-31
  tasks_completed: 2
  task_commits: 3
---

# Phase 27 Plan 11: README row, installer smoke and phase gates Summary

README row for `ai-kit-spec-goal-prompt` plus a headless install into a scratch HOME that links the skill; the wizard PTY suite passes with the added skill, and two gate failures from earlier phases were fixed along the way.

## Task commits

1. **Task 1: README row** - `4099de7f9d633f03bcda4aff0426a4c9b8ef387c` `docs(27-11): README row for the goal-prompt skill` (README.md, one row)
2. **Task 2 (deviation, see below):** `e5c8a3a692e0a7835b0e409b1becff024fc26287` `test(27-11): give the cmd_install reconcile tests a fake settings path` (tests/test_setup.py)
3. **Task 2 (deviation, see below):** `dcb103ce3b591e7c52deb651ad2929136dfffcfd` `test(27-11): narrow two regex matches in the superpowers tests for pyright` (tests/test_ai_kit_spec_superpowers.py)

Task 2's planned commit (`test(27-11): size the wizard PTY for one more skill`) was not made: the PTY suite passed at `_PTY_ROWS = 160`, so the file was not changed.

## What was done

### Task 1: README row and installer smoke

The row sits after the `ai-kit-gsd-spec-discuss` row. It uses the skill's frontmatter description (builds a `/goal`, `/loop` or `/gsd-autonomous` prompt file for GSD phases or superpowers plans, with rails, quota directives and e2e-based done; detects host primitives labelled verified or unverified; picks one to three strategies; never runs the prompt). The row does not claim anything the smoke does not cover; the stdlib-only claim was left out.

Installer smoke. The scratch HOME was a fresh `mktemp -d` directory under the session scratchpad (outside the repo), with `mkdir -p "$H/.claude"`. Every command used `AI_KIT_REFUSE_REAL_HOME=1` and `HOME`/`XDG_CONFIG_HOME` pointing into `$H`. `AI_KIT_DIR` was set to the worktree root (`git rev-parse --show-toplevel`):

| Step | Result |
|------|--------|
| `python3 tools/setup.py install --headless --skills ai-kit-spec-goal-prompt --dry-run` | rc 0; `headless summary: 1 linked, 0 relinked, 0 foreign-skipped, 0 real-skipped`; `(dry-run — no changes were made)` |
| same command without `--dry-run` | rc 0; same summary |
| `test -L "$H/.claude/skills/ai-kit-spec-goal-prompt"` | pass |
| `test -f "$H/.claude/skills/ai-kit-spec-goal-prompt/SKILL.md"` | pass |
| `readlink` of the link | points at `<repo>/skills/ai-kit-spec-goal-prompt` |
| `rm -rf "$H"` | scratch directory removed |
| `git status` after the README commit | only the orchestrator's `.planning/config.json` modified |

The dry-run summary counts one link but does not print the skill's name. The symlink and `SKILL.md` checks are the proof that the skill was installed.

### Task 2: wizard PTY and setup tests, then static gates

Integration group (under `uv run`, after the README commit and before the test fix): 4/4 modules ok (`config_doctor` 83 tests, `config_doctor_pty` 4, `wizard_pty` 12, `wizard_app` 66). `_PTY_ROWS` stayed at 160.

Setup tests: `python3 -m unittest tests.test_setup tests.test_sibling_resolution tests.test_gate_scope` ran every test OK (465 tests, 32 skipped) but exited 120. The cause is in the test code (see deviation 2). After the fix the three modules exit 0.

Static gates on the phase's new files and the whole repo, as applicable:

| Gate | Result |
|------|--------|
| `uv run pre-commit run ruff --all-files` (the `make ruff` gate) | Passed |
| `uv run ruff check tools skills tests` (the gate's file scope) | All checks passed |
| `uv run ruff check .` (plan's literal command) | 296 findings, none in `skills/`, `tools/` or `tests/` (see Unverified) |
| `uv run pylint skills/ai-kit-spec-goal-prompt/scripts` | 10.00/10 |
| `uv run pyright` | 0 errors, 0 warnings (2 errors before, fixed in deviation 3) |
| `uv run vulture` | clean |
| `python3 -m py_compile` on the 21 tracked goal-prompt `.py` files, including the fixtures and test modules | ok |

Final verification:

- `timeout 900 uv run python tools/run_unittest_parallel.py --group unit --group arch --group integration`: **78/78 modules passed**, rc 0.
- `timeout 900 python3 tools/run_unittest_parallel.py --group unit --group arch` (system python3, as `make test-unit` and `arch-test` run): **74/74 modules passed**, rc 0.
- Every `tests.test_ai_kit_spec_goal_prompt_*` module passed in both runs (11 modules in the uv run).
- No `wizard_app.py` process was left running (`pgrep -f '[w]izard_app.py'` found none).

## Deviations from Plan

**1. [Rule 3 - Blocking] Installer smoke command did not install anything as written.**
- **Found during:** Task 1, first smoke run.
- **Issue:** The plan's command ran `setup.py install --headless --skills ai-kit-spec-goal-prompt` in a scratch HOME. It returned rc 0 with `warn: --skills named unknown skill ... skipping` and `nothing linked`. The headless installer enumerates `AI_KIT_DIR` (default `$XDG_DATA_HOME/ai-kit` or `~/.local/share/ai-kit`), which does not exist in a scratch HOME.
- **Fix:** Added `AI_KIT_DIR="$(git rev-parse --show-toplevel)"` to the smoke commands. Only a runtime environment value; nothing machine-specific is written into any file.
- **Files:** none (command only). The corrected command is recorded above.

**2. [Rule 1 - Bug] `tests/test_setup.py` closed stdout and exited 120.**
- **Found during:** Task 2, `python3 -m unittest tests.test_setup ...`.
- **Issue:** Three tests in `TestCmdInstallExternalReconcile` patch `resolve_paths` with a `MagicMock` that has no `settings` value. `paths.settings` is therefore a mock. `_read_json_checked` then calls `open()` on it; the mock converts to the integer 1, so the `with` block wraps and closes fd 1 (stdout). The process exits 120 with `OSError: [Errno 9] Bad file descriptor` at shutdown. The fd-1 probes showed that no other class does this.
- **Fix:** Each of the three mocks now sets `settings="/fake/.claude/settings.json"`, a path that does not exist. Assertions are unchanged.
- **Commit:** `e5c8a3a`.

**3. [Rule 1 - Bug, earlier-phase gate red] Two pyright errors in `tests/test_ai_kit_spec_superpowers.py`.**
- **Found during:** Task 2 static gates.
- **Issue:** Phase 26-11 commits (`8a1ec6f`, `36ee536`) call `re.search(...).group(1)` on an Optional match at two lines. pyright reports `reportOptionalMemberAccess`, so the planned `uv run pyright` gate is red. The file is outside this plan's `files_modified`.
- **Fix:** Each match is now assigned, asserted non-None with a message, and only then read. Assertions are unchanged. The superpowers module passes (152 tests) and ruff is clean on the file.
- **Commit:** `dcb103c`. Reported here because the file is outside the plan's file list.

**4. [Plan defect] Clean-tree check in the plan's verify commands.**
- The plan's `test -z "$(git status --porcelain)"` cannot pass while the orchestrator's `.planning/config.json` change is present. The corrected form `git status --porcelain -- . ':!.planning/config.json'` was used for every check. The orchestrator's change was never staged.

**5. [Protocol miss] Plan commit ledger (0c) was not written before the first task commit.**
- The ledger file `gsd-plan-head-before-27-11` was written at SUMMARY time with the recovered base `a016ccc2db819c147b21f28f10d5af662b558924`. That is the parent of the first task commit `4099de7`, and it was the branch HEAD immediately before the first commit. `commits: 3` is measured from that base.

**6. [Plan defect] Whole-repo `uv run ruff check .` is not a clean gate.** See Unverified.

**7. [Run error, corrected] First integration run used system `python3`.**
- The integration group was first run without uv and `tests.test_wizard_app` failed to import `rich`. The Makefile runs this group under `uv run`; the rerun under uv passed. No code change was involved.

## Auth gates

None.

## Known Stubs

None in this plan's changes.

## Threat Flags

None. The smoke writes only under a scratch HOME that was removed afterwards.

## Unverified and open

- **Whole-repo ruff (plan's literal command):** `uv run ruff check .` reports 296 findings, all in files outside this phase's code: `.planning/docs/system-one-decision-skill` (202), `.planning/phases` (79), `docs/wizard-redesign` (11), `.planning/spikes` (4). None are in `skills/`, `tools/` or `tests/`. The project's own ruff gate (`make ruff`, the pre-commit hook) passes. These findings were not fixed here; they belong to earlier planning and docs work and are outside this plan's files.
- **WINDOWS ledger:** entries #7 (`gp_render.py`: an autonomous block names an unverified primitive in its heading) and #8 (`gp_render.py`: a rule line over 200 characters refuses generation) remain open from 27-09. Entry #1 was already fixed by 27-10; the 27-09 summary text saying it is still open is stale. With `workflow.windows_enforce` enabled, `/gsd-ship` blocks while entries are open.
- **Not run:** the e2e tier (`make e2e-test`, including `tests.test_ai_kit_spec_goal_prompt_e2e`), `bash tests/test_install.sh`, and the full `make test` aggregate. These were outside the plan's stated verification.
- **Installer observations (not changed):** a headless `--skills` name that is unknown still exits 0, with only a warning. `tests/test_setup.py` `test_install_exits_nonzero_when_no_tty` sets `AI_KIT_REFUSE_REAL_HOME` to `"0"` inside `mock.patch.dict`; it exits at the tty check before any write, but it runs with the real-home guard off, so the owner may want that test reviewed.
- **Unverified:** the `pi` claim behind the `PI_SKILLS` decision (taken from the plan, not re-observed here). The owner may add the skill to `PI_SKILLS` later if pi should link it.

## Self-Check

- README row present: `grep -q 'skills/ai-kit-spec-goal-prompt/SKILL.md' README.md` passes.
- Commits present on the branch: `4099de7`, `e5c8a3a`, `dcb103c` (`git log a016ccc..HEAD` shows the three).
- Installed link and `SKILL.md` verified in the scratch HOME before its removal.
- Full unit, arch and integration run under uv: 78/78 modules passed.

## Self-Check: PASSED
