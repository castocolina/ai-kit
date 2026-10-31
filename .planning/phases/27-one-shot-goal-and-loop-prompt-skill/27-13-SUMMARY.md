---
phase: 27-one-shot-goal-and-loop-prompt-skill
plan: 13
subsystem: phase-gate-and-owner-captures
tags: [gates, owner-captures, validation-map, amendments, e2e-docker, GPS-01, GPS-02, GPS-03, GPS-04]
requires:
  - phase: 27-12
    provides: "skill-judge verdict PASS (92.0%) and check_verdicts.py"
  - phase: 27-14
    provides: "README, evals and trigger queries"
provides:
  - "make test validate e2e-docker green at the phase tip"
  - "27-OWNER-CAPTURES.md: 8 human_verification items and 6 owner_decision proposals"
  - "27-VALIDATION.md: 36 task rows green, nyquist_compliant and wave_0_complete true"
  - "Dated amendments in 27-SPEC.md (versions, 1,800 budget) and ROADMAP.md (Plans line)"
affects:
  - "Orchestrator step after this plan: merge to local main, install, re-check live (push needs consent)"

# Actuals (#2632): chars/4 over the git diff 8394b95..HEAD (documents and two test fixes)
actuals:
  tokens: 12000
  tasks: 3
  commits: 8
  plan_head_before: 8394b95
  plan_head_after: see git log

status: complete
requirements-completed: []

key-files:
  created:
    - .planning/phases/27-one-shot-goal-and-loop-prompt-skill/27-12-SUMMARY.md
    - .planning/phases/27-one-shot-goal-and-loop-prompt-skill/27-OWNER-CAPTURES.md
  modified:
    - .planning/phases/27-one-shot-goal-and-loop-prompt-skill/27-VALIDATION.md
    - .planning/phases/27-one-shot-goal-and-loop-prompt-skill/27-SPEC.md
    - .planning/ROADMAP.md
    - tests/test_ai_kit_spec_goal_prompt_e2e.py
    - tests/test_cross_ai_runner_e2e.py

key-decisions:
  - "Acceptance is reported because check_verdicts.py --gate prints gate ok; the nine open round-3 findings stay an owner capture (item 7)."
  - "REQUIREMENTS.md was not amended: no fact contradicted GPS-01..GPS-04, and their status is the verifier's."
  - "The percent-based skill-judge rule for AGENTS.md and the older skills' markdown evals are proposals only; nothing was applied."

metrics:
  duration: "not recorded (start timestamp was not captured in this run)"
  completed: 2026-10-31
  tasks_completed: 3
---

# Phase 27 Plan 13: phase gate, owner captures and amendments Summary

The phase tip is green on every gate, the real CLI behaves on this repository without touching the real home, and everything that could not be verified here is an owner capture with exact steps.

## Commits

- `a847c91` `docs(27-12): complete the skill-judge plan` (27-12 SUMMARY, first request of this run)
- `3cd8d69` `fix(27-13): dogfood e2e snapshots the checkout when it has no .git (clean-room image)`
- `d17174a` `docs(27-13): owner captures and the filled validation map`
- `743d5ab` `docs(27-13): amend REQUIREMENTS, ROADMAP and SPEC with the phase 27 facts` (REQUIREMENTS untouched, see decisions)
- `cced6d1` `fix(27-13): give the rendered runner self-test a 900 s budget under load`
- the closing `docs(27-13)` commit with the gate results and this SUMMARY

## Task 1: gates and live checks

Guard `test "${CLAUDECODE:-}" = 1` held; `pgrep -f '[s]cripts/cross-ai.mjs'` printed nothing; the tree was clean.

Gate run at the tip (`AI_KIT_REFUSE_REAL_HOME=1`, log `tmp/p27/13/gates.log`, 14 minutes, podman as the container engine):

- `make test validate e2e-docker`: exit 0. Unit 74/74, uv 1/1, integration 4/4, e2e 13/13 + 45 installer checks, arch 1/1; ruff, pylint, pyright, vulture, shellcheck, py-compile, unittest (core) and (wizard) Passed; `ai-kit clean-room E2E: PASS`.

Failures found and fixed at their cause:

1. **Clean-room dogfood test** (`tests.test_ai_kit_spec_goal_prompt_e2e.TestDogfood`, a 27-09 test): `git status` exited 128 in the container because `tests/e2e/docker/.dockerignore` excludes `.git`. `git_status` now falls back to a file snapshot when git cannot read the tree; a new test covers the fallback (`3cd8d69`). Also run on a `.git`-less copy outside any repository: 4/4 OK.
2. **Rendered runner self-test budget** (`tests.test_cross_ai_runner_e2e`, a Phase 25.1 test): the `--self-test` call had a 300 s budget, it needs about 175 s alone and 360 to 480 s beside the other e2e modules; one run died with `TimeoutExpired` (`cced6d1`, budget 900 s).
3. **Timing failures with no single cause found:** four runs of the e2e tier failed in four different steps (`parser-cursor` exit 1, `model-opencode-two-variants` exit null, the 300 s budget, `test_five_combinations_two_paths` with one `resolve-model` call read as an empty model, which the helper does by design for a failed call). The host was swapping (17 GB of swap in use, peaks of 68 MB/s swap-in and 223 MB/s swap-out during the tier, `vmstat`). Two reruns with temporary logging in the helper and the runner passed and logged no failure, so which step stalled is **unverified**; both temporary edits were reverted (`git restore` of those two files only). Not claimed as fixed beyond the budget change; the fixed 60 s and 30 s budgets remain a risk on a stalled host.

Live checks from the branch (nothing written outside `tmp/`, tree clean afterwards):

- `goal_prompt.py detect --repo . --work-set phases:27 --gsd-cmd "node .claude/gsd-core/bin/gsd-tools.cjs" --tools ""` exit 0: `scope.kind` `opengsd`; `e2e.commands` `make e2e-test`, `make e2e-docker`, `python3 -m unittest tests.test_wizard_pty`; `readiness` `runner_ok` true, `cli_listed` true, `clis` `["pi"]`, label `installed, not quota- or auth-verified`; `host.current` `claude` 2.1.314; no value starts with a machine path (grep for `"/home`, `"/var`, `"/tmp`, `"/usr` found 0; the only `/`-leading strings are `/goal` and `/loop`).
- `render` with `work_set` `phases:27`, `output_dir` `tmp/p27/13/goals`: wrote `tmp/p27/13/goals/2026-10-31-phases-27.md`; strategy `autonomous` (recommended, "OpenGSD scope: /gsd-autonomous with --from/--to/--only and --converge"); sections OBJECTIVE to REPORT; `paste_chars` 5035; `rails_lines` 52 (limit 60); no warnings, nothing dropped.
- The first fenced block's first line is `/gsd-autonomous --only 27 --converge`. The upstream `grep` lines of `autonomous.md` on the block text: `--only` gives `27`; `--from`/`--to` match 0; `--converge` matches once; `--cross-ai`/`--interactive` match 0.
- Package: `git ls-files --error-unmatch` succeeds for `README.md`, `evals/evals.json` (9 evals) and `evals/trigger-queries.json` (20 queries); `python3 -m unittest tests.test_ai_kit_spec_goal_prompt_evals` ran 34 tests OK; `goal_prompt.py --help` exit 0.
- `check_verdicts.py` prints `verdicts ok`; `--gate` prints `gate ok` (`tmp/p27/13/gate.log`). The phase is reported accepted by the gate; the open findings are item 7 of the captures.

## Task 2: owner captures and validation map

`27-OWNER-CAPTURES.md`: gates, skill-judge state, 8 `human_verification` items (A3 4,000-code-point `/goal`; A2 pasted `/gsd-autonomous` block; A4 codex `/goal` and non-Claude primitives; A1 original GSD; A5 zero-test markers; the `PI_SKILLS` decision; the pending skill-judge findings; the remaining 27-10 unverified items), and an `## Owner decisions proposed` section with 6 `owner_decision` items, none applied: P1 the percent-based pass rule for `AGENTS.md` (proposal text and exact change), P2 the older skills' markdown evals as refactor debt (24 skills without `evals/evals.json` listed), P3 the WINDOWS #7 decision (still `open`; it blocks `/gsd-ship` under `windows_enforce`), P4 the remaining refusal paths (work-item lists and commands over the 200-character line cap), P5 plan defects (the `tail -n 3` pyright check, unexcluded clean-tree checks, the smoke install needing `AI_KIT_DIR`, the `state.update-progress` percent mismatch and STATE totals), P6 executor oddities (branch allow-list obeyed differently, the 27-03 miss of `tests.test_arch` fixed in `380e016`, a plan file changing during a run).

`27-VALIDATION.md`: 36 task rows (plans 27-01..27-14) set to `green`, file exists `yes`; `nyquist_compliant` and `wave_0_complete` true; the Wave 0 boxes ticked; sign-off ticked except the 60 s feedback latency, left unticked because the evals module needs 130 s and the real-CLI e2e module 49 s on this host; `status` left for validate-phase. No row is `pending (owner)`, because the gate is `gate ok`; the manual-only table points at the captures.

## Task 3: amendments

Dated notes (this run's date) in `27-SPEC.md` (host versions Claude Code 2.1.314 and OpenGSD 1.17.0 versus 2.1.299 and 1.16.0; R3 boundary row: render also refuses over the 1,800-character budget) and in `ROADMAP.md` (Plans line). Candidates checked and left alone: SPEC R2/A1 (matches the matrix, no change), SPEC R1 `both` scope asks (27-14 made the code match the spec), `REQUIREMENTS.md` (no contradicting fact; statuses are the verifier's; GPS-01..GPS-04 already read complete from an earlier plan's tooling).

## Deviations from Plan

- The plan's verify chain was run piecewise, not as one command; the evals test alone took 130 s under load.
- Task 1 allowed only root-cause fixes; two test fixes were made (above). Neither touched runtime code.
- The tip differs from the gate run by documentation commits only.

## Unverified

Everything in `27-OWNER-CAPTURES.md` items 1 to 8. Also unverified: why the four e2e runs failed in four different steps (host swap is the evidence, not a proven cause).
