# Phase 27 - skill-judge verdict for the goal-prompt skill

**Date:** 2026-10-31. **Judge:** the new `skill-judge` (percent grading, agentskills.io-aligned rubric,
125 points), prompt built from the installed skill-judge's own nine files.

Rubric: version 4, spec_sha 69ef37e9424c0a7ea9dd2293b559e43ec8176379

**Judges and why:** `router-env/my-referee-two` through pi (`--route-pi router --mode review`).
`my-referee-three` was probed with PONG over the full one-hour backoff (waits 0, 60, 120, 300, 600, 600, 600 s)
and never answered: `route down`, no lane. `my-referee-one` was reported down by the owner on 2026-10-31 and was
not probed because referee-two answered. No native Opus judge ran. One finished judge is enough (owner rule).
**Inputs the judge saw:** the skill directory as shipped (`SKILL.md`, `README.md`, `assets/`, `references/`,
`scripts/`, `evals/` with `evals/files/`) plus a note listing `tests/test_ai_kit_spec_goal_prompt_*.py`; the
rubric looks for script tests in `tests/skills/<name>/`, so the D7 finding states that limit and the smoke test it
could not see was not deducted.
**Pass rule:** `((Critical 0 and Important 0) or percent >= 80) and percent >= base`; Critical = findings with
severity `critical`, Important = severity `high`; base = lowest finished percent of round 1 (a new skill has no
earlier baseline). `skill-judge/check_verdicts.py` reproduces the verdict, the digest and the arithmetic from the
reports; `--gate` lists a non-PASS verdict as pending unless the owner accepted it.

## Rounds

- Start commit 35e1320 (package digest below). Round 1 (referee-two, 346 s, one lane, no retry): 113/125,
  90.4%, grade A, 0 critical, 0 high, 5 medium and 5 low findings. The verdict is PASS, so the loop stopped
  at round 1; no fix commit was made, because a fix would change the package digest and force a re-judge.
  Round 1 report commit: 8bb2a40.

## Verdicts

Skill: ai-kit-spec-goal-prompt
Verdict: PASS
Round: 1
Reviewed-sha256: cc485218ce28befa39d97b9e7b7684e76addc42c8428935c18e999379ecf536a
Base percent: 90.4
Base source: lowest finished percent of its first finished round (round 1, referee-two); a new skill has no earlier baseline
Score: 113/125
Percent: 90.4
Grade: A
Critical findings: 0
Important findings: 0
Rule: lowest percent 90.4 (referee-two 90.4); ((C0 and I0) -> True) or 90.4 >= 80 -> True; 90.4 >= 90.4 -> True.
Reports: skill-judge/r1/ai-kit-spec-goal-prompt-my-referee-two.md

## Refuted findings

none (the round had no critical or high finding to refute)

## Owner decision needed

none

## Owner decisions

none

## Pending acceptance

Medium and low findings of round 1, open (not fixed, not judged again):

- ai-kit-spec-goal-prompt: PASS (D8-1 medium, checked against the code and real: SKILL.md:98 names only `.planning/goals` and `docs/superpowers/goals` as the default `output_dir`, while `choose_path` in scripts/gp_render.py:395 also writes to `tmp/` for a free-text work set)
- ai-kit-spec-goal-prompt: PASS (D2-1, D4-1, D8-2, D8-3 medium: a thinking check before the readback, a description that names its non-uses, the two MANDATORY reads placed after the readback at SKILL.md:64, and `scope.ask` handling at SKILL.md:73; not triaged beyond the line check)
- ai-kit-spec-goal-prompt: PASS (D1-1, D3-1, D5-1, D6-1, D7-1 low: bare hand-off bullets, a generic hook warning, a conditional worked-example load, re-asking answered questions, three missing evals)

The judge is non-deterministic and the phase stops at the cap of three rounds; a fix made now would change the
package digest and is not judged.
