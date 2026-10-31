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
**Rounds:** at most three; the verdict is the last judged round whose digest equals the committed package.
**Pass rule:** `((Critical 0 and Important 0) or percent >= 80) and percent >= base`; Critical = findings with
severity `critical`, Important = severity `high`; base = lowest finished percent of round 1 (a new skill has no
earlier baseline). `skill-judge/check_verdicts.py` reproduces the verdict, the digest and the arithmetic from the
reports; `--gate` lists a non-PASS verdict as pending unless the owner accepted it.

## Rounds

- Start commit 35e1320. Round 1 (referee-two, 346 s): 113/125, 90.4%, grade A, 0 critical, 0 high, 5 medium and
  5 low findings; PASS, which also fixes the base percent at 90.4. Report commit 8bb2a40.
- Fix bbe21f3 (made by the coordinator after the PASS): D8-1 and D8-2 of round 1, the `tmp/` default output
  directory and the MANDATORY reads moved before the readback. The package changed, so the round 1 verdict went stale.
- Round 2 (referee-two, 481 s): 111/125, 88.8%, grade B, 0 critical, 1 high (D8-1), 5 medium and 3 low; UNRESOLVED
  (88.8% is above 80 but below the base 90.4). The high finding was checked against the code and was real:
  `run_render` re-selects strategies from the answers (scripts/goal_prompt.py:542), so detect's `reason` and
  `label` could describe a different set than the file, and render printed neither (scripts/gp_render.py:575).
  Fix 7d25266 (test first: the render and strategies tests failed before the change): render prints each
  strategy's `reason` and `label`; SKILL.md now says to explain the choice from render's list, names the
  1,800-character `/goal` budget next to the 4,000 code-point cap (scripts/gp_render.py:82), and makes
  `scope.ask` replace question 1. Report commit ce6c66e.
- Round 3, the last (referee-two, 351 s): 115/125, 92.0%, grade A, 0 critical, 0 high, 6 medium and 3 low;
  PASS (92.0 >= base 90.4). Its digest equals the committed package. Report commit 49f4178.
- `my-referee-three` was probed in rounds 1 and 2 and never answered (round 1: the full one-hour backoff;
  round 2: one probe): `route down`, no lane. `my-referee-one` was not probed; no Opus judge ran.

## Verdicts

Skill: ai-kit-spec-goal-prompt
Verdict: PASS
Round: 3
Reviewed-sha256: 06e5d77b6bf574ce0fafaa50622d466c753f68dd97e2fd5098f9cdf840e5e9dd
Base percent: 90.4
Base source: lowest finished percent of its first finished round (round 1, referee-two); a new skill has no earlier baseline
Score: 115/125
Percent: 92.0
Grade: A
Critical findings: 0
Important findings: 0
Rule: lowest percent 92.0 (referee-two 92.0); ((C0 and I0) -> True) or 92.0 >= 80 -> True; 92.0 >= 90.4 -> True.
Reports: skill-judge/r3/ai-kit-spec-goal-prompt-my-referee-two.md

## Refuted findings

none (the round had no critical or high finding to refute)

## Owner decision needed

none

## Owner decisions

none

## Pending acceptance

Open medium and low findings of round 3 (judged, not fixed; the phase stops at the cap of three rounds):

- ai-kit-spec-goal-prompt: PASS (D2-1, D3-1, D4-1, D7-1, D8-1, D8-2 medium: the `host.current` default cited before detect at SKILL.md:43, a NEVER line at SKILL.md:138, the description's non-uses at SKILL.md:3, the unseen smoke test at evals/evals.json:6, the e2e readback at SKILL.md:69, the exit-2 retry wording at SKILL.md:112; not triaged beyond the line check)
- ai-kit-spec-goal-prompt: PASS (D1-1, D5-1, D6-1 low: a bare hand-off bullet, the golden-file pointer, re-asking answered questions)

Fixed after judging: none. The judge is non-deterministic (88.8% to 92.0% on a package whose only change was one real fix),
so the verdict is that of the last judged round, whose digest equals the committed package.
