---
phase: 27-one-shot-goal-and-loop-prompt-skill
plan: 09
subsystem: tooling
tags: [goal-prompt, cli, detect, render, golden, property-sweep, r18-r19, e2e, stdlib, tdd]
requires:
  - phase: 27-08
    provides: "gp_sections done/report/order/turn-cap variants and gp_render readiness warnings"
provides:
  - "goal_prompt.py: detect and render subcommands, CliSeams, real_seams, parse_work_set, build_detect, run_render, build_parser, main"
  - "--gsd-cmd captures: three read-only query calls as list argv, never through a shell (T-27-21)"
  - "Property sweep over 13 scenarios run through the real CLI layer (caps, headings, flags, jev, budgets, QUOTA, DONE WHEN, repo-relative paths, -2 re-render)"
  - "Golden file for the recommended OpenGSD case (UPDATE_GOLDEN=1 regenerates)"
  - "R18 and R19 parity: the generated QUOTA text is present for both rules through check_rules, and absent without the QUOTA section"
  - "E2E-tier real-CLI subprocess test and dogfood detect; module listed in E2E_MODULES"
  - "WINDOWS #2, #3 and #6 closed"
affects:
  - "27-10: SKILL.md and README row for the goal-prompt skill (WINDOWS #1 still open)"

# Actuals (#2632): chars/4 over the git diff 15155f0..HEAD (97916 bytes), the three task commits only
actuals:
  tokens: 24479
  tasks: 3
  commits: 3
  plan_head_before: 15155f0be33276a1553587e6a8ef984005b45392
  plan_head_after: 5f686c666826b0e7217f2606064206718dd6658a

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "The CLI layer is a thin shell over the sibling gp_ modules; each subcommand is built from small functions and the seams are one NamedTuple"
    - "Errors are JSON on stderr with exit 2; argparse usage errors are routed through the same path"
    - "Tests drive the CLI layer (build_detect, run_render) on temp git repositories with fake host seams; no test prompts or touches a real home"

key-files:
  created:
    - skills/ai-kit-spec-goal-prompt/scripts/goal_prompt.py
    - tests/test_ai_kit_spec_goal_prompt_cli.py
    - tests/test_ai_kit_spec_goal_prompt_golden.py
    - tests/test_ai_kit_spec_goal_prompt_e2e.py
    - tests/fixtures/goal_prompt/golden/opengsd-recommended.md
  modified:
    - tools/run_unittest_parallel.py
    - Makefile
    - .pre-commit-config.yaml
    - .planning/WINDOWS.md

key-decisions:
  - "detect takes no strategy request, so its dropped list is empty. render re-selects the strategies with the answers' explicit request and reports each drop in its own stdout dropped list."
  - "A requested autonomous on a superpowers or none scope has no matrix row; it is reported in dropped with a reason (WINDOWS #3 closed this way, not by a new matrix row)."
  - "detect restricts superpowers plans to the named files and recomputes their dependency order in the CLI (WINDOWS #2 closed; gp_scope.detect_scope is unchanged)."
  - "unattended is not asked, so derive() sees must_outlive from the item count alone (D-11 input not asked)."
  - "Missing GSD captures are checked before the flag values, so a bad --target-host without captures reports the capture error first. Both are exit 2 with a JSON error."
  - "Captured-JSON files and the --gsd-cmd query output are parsed as JSON only; a @file: indirection is not handled (not needed for the real gsd-tools queries observed here)."
  - "The runner command is blanked from detect output when any token is a machine path."
  - "answers.skills (optional, lower-case names) is merged into candidate_skills in render."

requirements-completed: [GPS-01, GPS-02, GPS-03, GPS-04]

# Metrics
duration: unmeasured (start time was not recorded)
completed: 2026-10-31
status: complete
---

# Phase 27 Plan 09: goal_prompt.py detect and render subcommands, property sweep, golden, R18/R19 parity and the e2e tier Summary

**`goal_prompt.py` runs `detect` (the contract object, read-only, GSD captured from files or a read-only `--gsd-cmd`) and `render` (one goal file, strategies re-selected from the explicit request, drops reported), proven by a 13-scenario property sweep, one golden, R18/R19 parity through `check_rules`, and an e2e-tier run of the real CLI on a temp repository plus a dogfood detect of this repository**

## Performance

- **Duration:** unmeasured (the start timestamp was not recorded)
- **Tasks:** 3 of 3 completed, one commit each
- **Commits:** `6000634` (Task 1), `d34fd91` (Task 2), `5f686c6` (Task 3)

## Accomplishments

- `detect` builds the contract object: host and primitives (labelled per host, non-current targets unverified), matrix source, unrecognized tools, scope (`opengsd`, `gsd-unproven`, `superpowers`, `both`, `none`), e2e commands, cross-AI readiness, jev usability, derived inputs, strategies, `needs`, `candidate_skills`, `wake` and `runner`. It writes nothing.
- `--work-set` accepts `phases:16-17` (inclusive range over the roadmap), `phases:16,16.1,17`, `plans:a.md,b.md` and `free:<text>`. Malformed ranges, unknown plans and bad kinds exit 2. `free:` and `plans:` make no GSD call.
- GSD captures come from `--roadmap`, `--identity`, `--phase-op` files, or from `--gsd-cmd` as three read-only `query` calls run as list argv (`shlex.split`, no shell). A phases work set on a `.planning/` project with neither source exits 2 naming both flags.
- `render` validates the answers file (types, work-set shape, `output_dir` not absolute and not containing `..`, `skills` names), writes exactly one file through `gp_render`, and prints the contract plus `dropped` and `warnings`. Bad input names the field and never echoes the value.
- The property sweep runs 13 scenarios (OpenGSD recommended, native, user goal, mockup, readiness failed, GSD unproven, superpowers chain, superpowers single plan, no e2e suite, host without goal or loop, codex target, free text with `tmp/` ignored, OpenGSD single phase). Every scenario passes every generated-text property, and the upstream `/gsd-autonomous` extraction is simulated with the workflow's own regexes.
- The golden file is the recommended OpenGSD case, 87 lines and 4,986 bytes. It is shorter than the 5,581-byte hand-written reference in `.planning/goals/`. I read it before committing.
- R18 and R19 are present in the generated QUOTA text through `check_rules`. Removing the QUOTA section makes both `missing` or `near_miss`.

## Verification run

- `python3 tools/run_unittest_parallel.py --group unit --group arch` (foreground, `timeout 900`): 73 of 73 modules passed, exit 0, 37 seconds.
- `python3 -m unittest tests.test_ai_kit_spec_goal_prompt_cli`: 33 tests OK. The golden module: 7 tests OK. The e2e module: 3 tests OK (about 57 seconds, see below).
- `python3 -m unittest tests.test_gate_scope`: OK after each listing regeneration.
- `ruff check` on `skills/ai-kit-spec-goal-prompt` and the three new test modules: all checks passed.
- `pylint skills/ai-kit-spec-goal-prompt/scripts`: 10.00/10.
- `pyright` on the goal-prompt skill and the new tests: `0 errors, 0 warnings, 0 informations`.
- `vulture` (repo config): no findings.

## Real CLI run (read-only, scratch HOME, `AI_KIT_REFUSE_REAL_HOME=1`)

- `detect --repo . --gsd-cmd "node .claude/gsd-core/bin/gsd-tools.cjs" --work-set phases:16-27 --tools CronCreate`: exit 0, 19 seconds. Printed `scope.kind` `opengsd`, identity `opengsd`, 18 phases (16 through 27, with the dotted 16.1, 18.1, 21.1 to 21.3, 25.1), `e2e.commands` `make e2e-test`, `make e2e-docker`, `python3 -m unittest tests.test_wizard_pty`, readiness `runner_ok` true, `cli_listed` true, `reviewers_ok` true, jev usable (local backend), `strategies` `[autonomous]` recommended, `dropped` `[]`, `needs` `[]`, no absolute path in the output.
- `render` of that detect into the git-ignored `tmp/p27/goals/` (`--out-dir`): exit 0, path `tmp/p27/goals/2026-10-31-phases-16-16-1-17-18-18-1-19-20-21-21-1.md`, 5,848 bytes, 89 lines, `warnings` `[]`, `dropped` `[]`, first fence line `/gsd-autonomous --from 16 --to 27 --converge`. The project tree gained no file.
- Error paths: `phases:27-16` with captures exits 2 with `no roadmap phase falls in the phase range`. An absolute `output_dir` exits 2 with `field output_dir holds a machine path`. A missing subcommand exits 2 with a JSON error.
- Probe timing: `ai-kit-spec.py detect-runtimes` takes about 16 seconds. Every other host probe is under 0.1 seconds. The sibling probe is the cause of the slow detect and of the e2e module's runtime.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `TestCli` shadowed `unittest.TestCase.run`.** The first draft assigned `self.run` as the fake host seam. Pyright flagged it, and the unittest runner calls `self.run`. Renamed the attribute to `self.host_run` before the Task 1 commit.

**2. [Rule 2 - Missing critical] Plan restriction and autonomous request were not wired.** WINDOWS #2 (plans work set not restricted) and #3 (requested autonomous silently ignored) both needed CLI wiring, not a matrix change. Implemented as `_restrict_plans` in detect and an autonomous entry in render's `dropped`.

**3. [Lint] Pylint, ruff and pyright findings in the new modules** (an over-long line, an unused unpack, an import order, an optional-narrowing gap). Fixed before each commit; no suppression comments added.

### Plan verify command defects

**4. [Plan defect] Task 1 pyright check cannot pass as written.** `uv run pyright ... | tail -n 3 | grep -q '0 errors'`: pyright's version banner occupies the last lines, so `tail` never shows the summary. The real result is `0 errors, 0 warnings, 0 informations` (run without `tail`). This is the same defect recorded in 27-06, 27-07 and 27-08.

**5. [Plan defect] Task 3 clean-tree check.** `test -z "$(git status --porcelain)"` includes `.planning/config.json`, which the orchestrator modifies on purpose. Checked as `git status --porcelain -- . ':!.planning/config.json'`: only my files were clean.

**6. [Protocol] The plan commit ledger (0c) was not written before the first commit.** The base was therefore measured from git: `15155f0` is the parent of the first task commit `6000634`, and `commits: 3` is `git rev-list --count 15155f0..HEAD`.

### Scope notes

- `pre-commit` stashes unstaged files around each commit and restores them. The orchestrator's `.planning/config.json` change was restored unchanged after each commit (checked with `git status`).
- The golden and e2e modules import helper names from `tests.test_ai_kit_spec_goal_prompt_cli` (`FakeRun`, `host_routes`, `MATRIX_ROWS`, `cli_seams` for the CLI module only). The shared fixtures module is outside this plan's file list; a follow-up can move them into `tests/goal_prompt_fixtures.py`.

## Auth Gates

None.

## Known Stubs

None in the CLI. The skill's `SKILL.md` is still the 27-06 stub (WINDOWS #1, owned by 27-10).

## Broken-windows ledger

- Closed: WINDOWS #2 (plans restriction, wired in `_restrict_plans`), #3 (requested autonomous on a non-GSD scope, reported in `dropped`), #6 (R18/R19 parity, `TestRuleParity`), via `gsd-tools windows fixed`.
- Still open: #1 (stub `SKILL.md`, 27-10), #7 (the autonomous block's unverified label is in its heading only, by D-12), #8 (a rule line over 200 characters refuses generation instead of wrapping; no wrapped-title test yet). #7 and #8 are in `gp_render`, outside this plan's file list.

## Unverified Items

- **No host has run a rendered block.** The `/goal`, loop and autonomous claims rest on fixtures and the readiness probes, not on a live session. The readiness label says "installed, not quota- or auth-verified".
- **The runner's `--print-argv` listing ran once, against this repository.** It reported one CLI. Whether that CLI can actually take a quota-checked task is unverified.
- **`--gsd-cmd` output is parsed as JSON only.** The three queries returned plain JSON here (roadmap 14,920 bytes). A `@file:` indirection on a larger roadmap is not handled and is unverified.
- **`unattended` is not asked.** `must_outlive` follows the item count alone, which matters only for the loop and plain rows of a non-OpenGSD scope.
- **The golden is a synthetic fixture,** not a real project. The real-repository render above is the only run against a real roadmap, and its goal file was not committed.
- **Dogfood `e2e` commands are as the detector reports them.** `python3 -m unittest tests.test_wizard_pty` was found as an e2e command; whether it is a real end-to-end gate for this repository was not checked.
- **Plan verify commands were run by hand, not as written** (defects 4 and 5 above).

## Threat Flags

None. The CLI reads user-named JSON files and runs the `--gsd-cmd` queries as list argv with no shell (T-27-21). Error messages name fields and flags and never echo a value (T-27-22). The tests use temporary homes and fake `node` (T-27-23). No network call and no new endpoint.

## Self-Check

- Created files exist: `skills/ai-kit-spec-goal-prompt/scripts/goal_prompt.py`, `tests/test_ai_kit_spec_goal_prompt_cli.py`, `tests/test_ai_kit_spec_goal_prompt_golden.py`, `tests/test_ai_kit_spec_goal_prompt_e2e.py`, `tests/fixtures/goal_prompt/golden/opengsd-recommended.md`.
- Commits `6000634`, `d34fd91` and `5f686c6` are ancestors of HEAD and carry `feat(27-09):` and `test(27-09):` subjects.
- `commits: 3` was measured as `git rev-list --count 15155f0..HEAD`.
- `.planning/config.json` was never staged.
