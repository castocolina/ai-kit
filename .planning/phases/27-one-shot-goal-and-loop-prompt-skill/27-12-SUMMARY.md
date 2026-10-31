---
phase: 27-one-shot-goal-and-loop-prompt-skill
plan: 12
subsystem: goal-prompt-skill-judge
tags: [skill-judge, goal-prompt, percent-grading, rubric-v4, GPS-04]
requires:
  - phase: 27-10
    provides: "SKILL.md judged by the new skill-judge"
  - phase: 27-11
    provides: "README row and installer smoke"
  - phase: 27-14
    provides: "README, evals and trigger queries (judge dimension D7)"
provides:
  - "27-SKILL-JUDGE.md: three judged rounds, verdict block PASS (92.0%, grade A), pending acceptance list"
  - "skill-judge/r1..r3: the committed referee-two reports"
  - "skill-judge/check_verdicts.py: reproduces the verdict, the package digest and the gate from the reports"
  - "Two real fixes found by the judge (D8 round 1 findings; D8-1 high of round 2)"
affects:
  - "27-13 (phase gate): runs check_verdicts.py --gate and stages the pending items as owner captures"

# Actuals (#2632): chars/4 over the git diff 35e1320..8394b95 (57203 bytes)
actuals:
  tokens: 14301
  tasks: 3
  commits: 7
  plan_head_before: 35e1320
  plan_head_after: 8394b95

status: complete
requirements-completed: []

key-files:
  created:
    - .planning/phases/27-one-shot-goal-and-loop-prompt-skill/27-SKILL-JUDGE.md
    - .planning/phases/27-one-shot-goal-and-loop-prompt-skill/skill-judge/check_verdicts.py
    - .planning/phases/27-one-shot-goal-and-loop-prompt-skill/skill-judge/r1/ai-kit-spec-goal-prompt-my-referee-two.md
    - .planning/phases/27-one-shot-goal-and-loop-prompt-skill/skill-judge/r2/ai-kit-spec-goal-prompt-my-referee-two.md
    - .planning/phases/27-one-shot-goal-and-loop-prompt-skill/skill-judge/r3/ai-kit-spec-goal-prompt-my-referee-two.md
  modified:
    - skills/ai-kit-spec-goal-prompt/SKILL.md
    - skills/ai-kit-spec-goal-prompt/scripts/gp_render.py
    - tests/test_ai_kit_spec_goal_prompt_render.py
    - tests/test_ai_kit_spec_goal_prompt_strategies.py

key-decisions:
  - "The verdict is that of the last judged round whose digest equals the committed package (round 3); the judge is non-deterministic, so no fourth round was run."
  - "Acceptance is reported only because check_verdicts.py --gate prints gate ok; the open medium and low findings stay under Pending acceptance for the owner."

patterns-established:
  - "A judge verdict is bound to a package digest; any fix after a judged round makes that verdict stale and needs a new round or a Pending acceptance entry."

metrics:
  duration: "not recorded (start timestamp was not captured in this run)"
  completed: 2026-10-31
  tasks_completed: 3
  task_commits: 7
---

# Phase 27 Plan 12: skill-judge loop for the goal-prompt skill Summary

The new `skill-judge` (rubric v4, 125 points, percent grading) judged `ai-kit-spec-goal-prompt` in three rounds; the final verdict is PASS at 115/125 (92.0%, grade A, 0 critical, 0 high), and `check_verdicts.py --gate` prints `gate ok`.

## Task commits

1. `8bb2a40` `docs(27-12): skill-judge round 1 and fixes` (round 1 report)
2. `6ebdbdc` `docs(27-12): skill-judge verdict and pending acceptance for the goal-prompt skill` (`27-SKILL-JUDGE.md`, `check_verdicts.py`)
3. `bbe21f3` `fix(27-12): name the tmp default output dir and read the references before the readback` (SKILL.md, round 1 D8-1 and D8-2)
4. `7d25266` `fix(27-12): render prints each strategy's reason and label, document the 1,800 budget` (gp_render.py, SKILL.md and two tests; the real High of round 2)
5. `ce6c66e` `docs(27-12): skill-judge round 2 and fixes` (round 2 report)
6. `49f4178` `docs(27-12): skill-judge round 3` (round 3 report)
7. `8394b95` `docs(27-12): skill-judge round 2 verdict` (final verdict block)

## Rounds

- **Round 1**: 113/125, 90.4%, grade A, 0 critical, 0 high, 5 medium, 5 low. PASS; it fixed the base percent at 90.4.
- **Round 2** (after fix `bbe21f3`, which made the round 1 verdict stale): 111/125, 88.8%, grade B, 0 critical, 1 high (D8-1). UNRESOLVED (88.8 is above 80 but below the base 90.4). The high finding was checked against the code and was real: `run_render` re-selects strategies from the answers (`scripts/goal_prompt.py:542`), so detect's `reason` and `label` could describe a different set than the file, and render printed neither (`scripts/gp_render.py:575`). Fix `7d25266`, test first (the render and strategies tests failed before the change): render prints each strategy's reason and label; SKILL.md says to explain the choice from render's list, names the 1,800-character `/goal` budget next to the 4,000 code-point cap (`scripts/gp_render.py:82`) and makes `scope.ask` replace question 1.
- **Round 3** (the last allowed): 115/125, 92.0%, grade A, 0 critical, 0 high, 6 medium, 3 low. PASS (92.0 >= base 90.4). Its digest `06e5d77b...e5e9dd` equals the committed package.

Verdict reproduced at the tip: `check_verdicts.py` prints `verdicts ok`; with `--gate` it prints `gate ok`.

## Judges

Only `router-env/my-referee-two` (through pi, `--route-pi router --mode review`) ran. `my-referee-three` never answered a PONG probe (round 1: the full one-hour backoff, waits 0, 60, 120, 300, 600, 600, 600 s; round 2: one probe): `route down`, no lane. `my-referee-one` was reported down by the owner on 2026-10-31 and was not probed. No native Opus judge ran. One finished judge is enough under the owner rule; no second opinion exists, so the 92.0% rests on a single non-deterministic judge (88.8% to 92.0% on a package whose only change was one real fix).

## Pending acceptance

Open findings of round 3, judged and not fixed (cap of three rounds reached); each becomes an owner capture in 27-13:

- Medium: D2-1 (the `host.current` default cited before detect, `SKILL.md:43`), D3-1 (a NEVER line, `SKILL.md:138`), D4-1 (the description's non-uses, `SKILL.md:3`), D7-1 (the smoke test the judge could not see, `evals/evals.json:6`), D8-1 (the e2e readback, `SKILL.md:69`), D8-2 (the exit-2 retry wording, `SKILL.md:112`). Not triaged beyond the line check.
- Low: D1-1 (a bare hand-off bullet), D5-1 (the golden-file pointer), D6-1 (re-asking answered questions).

Because the verdict is PASS, the gate does not list these as blocking; they are recorded for the owner as informational acceptance items.

## Deviations from Plan

1. **Single judge.** The plan wanted two judges where possible; referee-three was down and referee-one was reported down, so one lane judged all three rounds.
2. **Fix before a re-judge, made by the coordinator after a PASS.** Round 1 passed; the coordinator then fixed D8-1 and D8-2 (`bbe21f3`). That invalidated the round 1 verdict by digest, so round 2 was run. It scored lower (88.8%) and exposed one real High.
3. **Tests not visible to the judge.** The rubric looks for script tests in `tests/skills/<name>/`; this repository keeps `tests/test_ai_kit_spec_goal_prompt_*.py`. The D7 finding states the limit; the unseen smoke test was not deducted.
4. **Round 2 UNRESOLVED was not a PASS-by-percent.** The base rule (`percent >= base`) made 88.8% a non-pass although it exceeds 80.

## Self-Check

- Commits 8bb2a40, 6ebdbdc, bbe21f3, 7d25266, ce6c66e, 49f4178, 8394b95 exist in `git log`.
- `check_verdicts.py` prints `verdicts ok` and `gate ok` at the tip.
- Not verified: a second judge's opinion; any rating by an Opus judge.
