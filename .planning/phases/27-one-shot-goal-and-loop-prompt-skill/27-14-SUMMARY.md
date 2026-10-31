---
phase: 27-one-shot-goal-and-loop-prompt-skill
plan: 14
subsystem: goal-prompt-skill-evals
tags: [goal-prompt, evals, trigger-queries, readme, fixtures, cli-smoke, D7]
requires:
  - phase: 27-09
    provides: "goal_prompt.py detect and render: flags, JSON contract, exit codes 0 and 2"
  - phase: 27-10
    provides: "SKILL.md whose promises the evals and the README must match"
  - phase: 27-11
    provides: "README row and headless installer smoke for the skill"
provides:
  - "README.md: five sections, install and usage commands, links that resolve (TestReadme)"
  - "evals/trigger-queries.json: 20 queries, 10 should trigger, 10 near-miss negatives (TestTriggerQueries)"
  - "evals/evals.json: nine output evals (casual, precise, seven edge cases), each with four or more concrete assertions (TestEvals)"
  - "evals/files/: synthetic fixtures for five project kinds (OpenGSD mixed state with captured gsd-tools JSON, superpowers chain, no e2e, empty, both frameworks), each proven through the real detect CLI (TestFixtureDetect)"
  - "tests/test_ai_kit_spec_goal_prompt_evals.py: 34 tests in five classes, joins the unit group"
  - "goal_prompt.py --help: root epilog states the exit codes; every detect and render option has help text"
  - "goal_prompt.py detect: a project with .planning/ and superpowers plans and no --work-set now exits 0 with scope kind both and an ask, as the contract states"
affects:
  - "27-12 (skill-judge round): reads evals/, README and the test module; the judge note points at tests/test_ai_kit_spec_goal_prompt_evals.py"

# Actuals (#2632): chars/4 over the git diff 16d744a..HEAD (74455 bytes)
actuals:
  tokens: 18614
  tasks: 3
  commits: 5
  plan_head_before: 16d744a88f34e5f79a2455a4b2eb7e3ccd6b485f
  plan_head_after: 871b7c3b29abc9401cbdcb9a700395a009eb4986

status: complete
requirements-completed: []

key-files:
  created:
    - skills/ai-kit-spec-goal-prompt/README.md
    - skills/ai-kit-spec-goal-prompt/evals/evals.json
    - skills/ai-kit-spec-goal-prompt/evals/trigger-queries.json
    - skills/ai-kit-spec-goal-prompt/evals/files/ (20 synthetic fixture files)
    - tests/test_ai_kit_spec_goal_prompt_evals.py
  modified:
    - skills/ai-kit-spec-goal-prompt/scripts/goal_prompt.py
    - tests/test_ai_kit_spec_goal_prompt_cli.py
    - Makefile
    - .pre-commit-config.yaml

key-decisions:
  - "A roadmap is needed only for a phases work set. With no work set a missing roadmap is no longer fatal (27-09 root bug, see deviation 2)."
  - "Commit order is trigger queries, CLI fix, evals and fixtures, README. The README links the evals files, so it can only be green after them (deviation 1)."
  - "Fixtures store the planning folder as planning/ and tests copy it to .planning/ in a temp dir; the captured JSON carries @REPO@ in place of the repository root."
  - "GPS-04 is not marked complete here. Its gate is the skill-judge round in 27-12."

patterns-established:
  - "Fixture tests stage a copy of evals/files/<kind> into a TemporaryDirectory and run the real CLI with a fake HOME and AI_KIT_REFUSE_REAL_HOME=1; nothing is written to the staged repo."

metrics:
  duration: "not recorded (start timestamp was not captured in this run)"
  completed: 2026-10-31
  tasks_completed: 3
  task_commits: 5
---

# Phase 27 Plan 14: README, trigger queries and evals with fixtures Summary

Shipped the D7 package for the goal-prompt skill (README, nine evals, twenty trigger queries, synthetic fixtures) and a test module that keeps them valid and proves each fixture kind through the real `detect` CLI. Writing the fixture tests exposed one contract mismatch in 27-09's code, which is fixed at the root.

## Task commits

1. **Task 2 (committed first): trigger queries** - `361eeec` `test(27-14): trigger queries for the goal-prompt skill` (evals/trigger-queries.json, test module with TestTriggerQueries, regenerated listings)
2. **Fix (deviation 2):** `08f60d2` `fix(27-14): detect asks for a both-framework project without captures` (scripts/goal_prompt.py, tests/test_ai_kit_spec_goal_prompt_cli.py)
3. **Task 3: evals, fixtures, script smoke** - `b42faaf` `test(27-14): evals, fixtures proven by the CLI and the script smoke` (evals/evals.json, evals/files/, goal_prompt.py help text and epilog, test module)
4. **Task 1 (committed last): README** - `3111065` `docs(27-14): README for the goal-prompt skill` (README.md, TestReadme)
5. **Lint fix (deviation 4):** `871b7c3` `test(27-14): record the seam's timeout and cwd in FakeRun` (tests/test_ai_kit_spec_goal_prompt_cli.py)

## What was done

### Task 2: trigger queries

Twenty queries in the plan's order. The ten negatives are near misses (summary of phases, run a phase now, `/loop` pacing, plan review, plan authoring, `/goal` explanation, prompt rewriting, cron schedule, superpowers execution). TestTriggerQueries pins shape, counts, uniqueness, near-miss count (>= 8 of 10 negatives carry a skill word), variety and hygiene. Six tests, all green.

### Task 3: evals, fixtures and script smoke

- Fixtures under `evals/files/`: `opengsd-mixed` (project tree with `planning/`, three SPEC files, captured `identity.json`, `roadmap.json`, `phase-op/16-18.json`), `superpowers-chain` (alpha, beta with `**Depends on:** \`alpha.md\``, gamma, Makefile with `e2e-test`), `no-e2e`, `empty-project`, `both-frameworks`. Twenty files; the evals list every one, and an orphan test enforces that.
- `TestEvals` (11 tests): structure, id pattern, required keys, mix of casual, precise and edge ids, input paths exist, no orphan fixtures, prompt paths exist, assertions concrete (>= 40 characters, no vague word, unique, >= 3 with a backticked literal), a non-vacuity case, no machine path or secret, no live `.planning` or `__pycache__` in fixtures and no ignored fixture file.
- `TestFixtureDetect` (7 tests): each fixture kind through the real `detect` CLI, asserting the scope kind, phase numbers and plan counts, order, e2e command, unverified primitives for codex, and the ask cases.
- `TestScriptCli` (6 tests): `--help` exits 0 with `usage:` on stdout and empty stderr for root, `detect` and `render`; the documented flags are listed; the root help has an `Exit codes` line naming 0 and 2; every option has help text (checked on the parser object); `detect` prints one JSON object with `schema_version` 1 and an empty stderr; `render` with `{}` answers exits 2 with JSON stderr and leaves the staged repo unchanged.
- goal_prompt.py: `RawDescriptionHelpFormatter` and the epilog `Exit codes: 0 ok; 2 bad input or a guard failure ...` exactly as the plan states, plus one `help=` line per option of `detect` and `render`.

### Task 1: README

Five sections (`What it is`, `When to use`, `Install`, `Usage`, `Links`), 47 lines, plan text kept byte for byte apart from the removed indentation. TestReadme (4 tests) checks the shape, every relative link, the commands and the `unverified` label.

## Deviations from plan

**1. [Plan ordering] Commit order 2, fix, 3, 1.** The README links `evals/evals.json` and `evals/trigger-queries.json`, and TestReadme requires them to exist, so the Task 1 verify (whole module green at Task 1) cannot hold before Task 3. Each commit staged the test module version that was green at that point (the README class was added in the last commit). The working tree followed the plan's order.

**2. [Rule 1 - Bug in 27-09 code, contract mismatch] `detect` without `--work-set` on a both-framework project.** The plan's interface contract says such a project gives scope kind `both` with an ask and exit 0. The real CLI exited 2 with `a GSD work set needs --roadmap or --gsd-cmd`. Root cause: `_roadmap` raised whenever no roadmap source was given, even with no work set. Fix: with no work set, return no roadmap (a phases work set still needs one, so `phases:16-18` without captures still exits 2, covered by the existing test). Failing test first (rc 2 vs 0), fix, then commit `08f60d2`. The fixture was correct; only the CLI was wrong.

**3. [Plan-directed] Help text in goal_prompt.py.** Added in the Task 3 commit, as the plan says: epilog, formatter, and `help=` on all 15 options of `detect` (11) and `render` (4). No import was added.

**4. [Lint, earlier-plan test file] vulture on `FakeRun`.** Vulture (pre-push gate, `tests` in scope, 100% confidence) flagged the unused `timeout` and `cwd` parameters of `FakeRun.__call__` in `tests/test_ai_kit_spec_goal_prompt_cli.py`. The finding already existed at the base commit, from 27-09. Fixed by recording both values per call (`871b7c3`); the vulture config was not changed.

**5. [Lint, own module]** ruff import-sort (I001) fixed on the new module; the unused imports were added back when the tests that use them were written.

**6. [Protocol miss] Plan commit ledger (0c).** The ledger file was not written before the first commit. The base is the branch HEAD before the first commit, `16d744a`; it was recovered and written at SUMMARY time, the same miss 27-11 recorded. `commits: 5` is measured from it.

**7. [Plan defect] Clean-tree check.** `git status --porcelain` cannot pass while `.planning/config.json` is dirty. Every check used `-- . ':!.planning/config.json'`. Intermediate states also had the README untracked until its own commit.

**8. [Assertions read against SKILL.md and the real renderer]** No assertion was changed. Facts checked with real `detect` and `render` runs in a scratch dir:
- OpenGSD range: block first line `/gsd-autonomous --from 16 --to 18 --converge`, matches the eval's regex; file under `.planning/goals/` named `2026-10-31-phases-16-17-18.md`; warnings relayed (readiness: script missing, convergence off, reviewer CLI not installed).
- OpenGSD single phase 17: `/gsd-autonomous --only 17 --converge`.
- Superpowers chain: file under `docs/superpowers/goals/`, ORDER section, four-backtick fences, no `/gsd-autonomous` line.
- No-e2e single plan: no ORDER section; the DONE WHEN section starts with "No e2e suite exists. The first task ... creates one"; the unit sentence is present.
- Absolute `output_dir`: exit 2, `field output_dir holds a machine path`, the home value not echoed.

**9. [Trigger queries] No query reworded.** Two positives may not route on the current description: query 5 ("make a goal file ... phase 27") says "goal file", not "goal prompt"; query 7 ("something to paste into claude ...") has no "prompt" word. Neither is clearly unroutable, so both stay; flagged for the 27-12 judge.

**10. [State pointer] STATE.md left at "Plan: 12 of 13".** `state.advance-plan` was not run: 27-12 and 27-13 have no SUMMARY, so advancing would misstate progress. The pointer is the orchestrator's; `state.update-progress`, `roadmap.update-plan-progress` and `state.record-session` were run from disk.

## Commands run and results

| Command | Result |
|---|---|
| `python3 -m unittest tests.test_ai_kit_spec_goal_prompt_evals` (full module, before README split) | 34 tests OK, rc 0 |
| `python3 tools/run_unittest_parallel.py --group unit --group arch` under `timeout 900` (before the FakeRun commit) | 75/75 modules, rc 0 |
| same, final (after `871b7c3`) | 75/75 modules, rc 0 (`evals` module 34 tests in 131 s) |
| `uv run ruff check` on changed files and `skills/ai-kit-spec-goal-prompt`, `tools`, `skills`, `tests` | All checks passed |
| `uv run pylint skills/ai-kit-spec-goal-prompt/scripts` | 10.00/10 |
| `uv run pyright` on the three changed Python files | 0 errors, 0 warnings |
| `uv run vulture tests skills tools --min-confidence 80` | rc 0 (the same run before `871b7c3` reported two findings in `FakeRun`) |
| `python3 -m unittest tests.test_gate_scope` | OK (after the listing regeneration) |
| `python3 tools/gen_test_groups.py` | listings changed only by the new module name in Makefile and `.pre-commit-config.yaml` |
| hygiene scan of all changed files (machine paths, key shapes) | only the module's own `MACHINE_PATH_RE` pattern and a pre-existing Makefile comment matched; no secret shape |

Help output (first lines of each, run with `AI_KIT_REFUSE_REAL_HOME=1`):

```
$ python3 skills/ai-kit-spec-goal-prompt/scripts/goal_prompt.py --help
usage: goal_prompt.py [-h] {detect,render} ...

Goal-prompt generator: detect, render.

$ python3 skills/ai-kit-spec-goal-prompt/scripts/goal_prompt.py detect --help
usage: goal_prompt.py detect [-h] [--repo REPO] [--target-host TARGET_HOST]
                             [--tools TOOLS] [--roadmap ROADMAP]

$ python3 skills/ai-kit-spec-goal-prompt/scripts/goal_prompt.py render --help
usage: goal_prompt.py render [-h] [--repo REPO] --detect DETECT
                             --answers ANSWERS [--out-dir OUT_DIR]
```

Each prints exit code 0. The root help ends with `Exit codes: 0 ok; 2 bad input or a guard failure (a JSON error is printed on stderr). Output is JSON on stdout. The tool never prompts.`

## Auth gates

None.

## Known Stubs

None in this plan's changes.

## Threat Flags

None. The CLI change is internal (no new input surface); the fixtures carry no secret and no machine path.

## Unverified and open

- **Hand-off assertions.** Several eval assertions describe the agent's final reply (labels repeated, "does not run the prompt", "no claim that /goal exists on codex"). No test can check a reply; no model was called. These are for the 27-12 judge and the owner.
- **Host claims.** Only the CLI's own labels were exercised (the current host and codex). Nothing was observed live on any host, so no `/goal` or `/loop` availability is claimed.
- **Not run:** the e2e tier (`make e2e-test`, which includes `tests.test_ai_kit_spec_goal_prompt_e2e`), `bash tests/test_install.sh`, the integration group, and the full `make validate` aggregate. Per-commit hooks (ruff, pylint, py-compile) passed; pyright and vulture were run directly on the changed files.
- **GPS-04** is not marked complete here; its gate is the skill-judge round in 27-12.
- **Runtime.** The evals module takes about 130 s because each `detect` probes the sibling CLIs read-only; the unit group takes a few minutes. No timing change was attempted.
- **WINDOWS ledger.** No entry appended; the test-skip and unrun-verify items above are the ones a future ship gate would care about.

## Self-Check

- Created files present: `README.md`, `evals/evals.json`, `evals/trigger-queries.json`, `evals/files/**` (20 files), `tests/test_ai_kit_spec_goal_prompt_evals.py`.
- Commits present on the branch: `361eeec`, `08f60d2`, `b42faaf`, `3111065`, `871b7c3` (`git rev-list --count 16d744a..HEAD` = 5).
- Module green (34/34) and unit plus arch groups green (75/75) on the final commit.
- Fixture paths contain no `.planning` or `__pycache__`; `tests/test_ai_kit_spec_goal_prompt_evals.py::TestEvals::test_fixtures_hold_no_live_planning_dir` enforces it.

## Self-Check: PASSED
