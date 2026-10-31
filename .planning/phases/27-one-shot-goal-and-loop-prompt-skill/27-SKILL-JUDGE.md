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
**Rounds:** the original loop ran at most three; round 4 is one post-review confirmation allowed by the
orchestrator after code review and a security audit changed the scripts (round 5 only if that round led to a fix).
The verdict is the last judged round whose digest equals the committed package.

Post-review confirmation rounds: 4
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
- - Post-review confirmation, round 4 (referee-two, 351 s; the prompt adds a note that scripts changed after a code
  review and a security audit): 111/125, 88.8%, grade B, 0 critical, 0 high, 4 medium and 5 low findings. No
  critical or high finding, so nothing needed a fix and no round 5 ran. Verdict UNRESOLVED: 88.8 is above 80 and
  the severity counts are 0/0, but it is below the base 90.4 (and below round 3's 92.0). Its digest equals the
  committed package. The package digest of round 3 is stale because of the review and security commits.
- `my-referee-three` was probed in rounds 1, 2 and 4 and never answered (round 1: the full one-hour backoff;
  rounds 2 and 4: one probe each): `route down`, no lane. `my-referee-one` was not probed; no Opus judge ran.

## Verdicts

Skill: ai-kit-spec-goal-prompt
Verdict: UNRESOLVED
Round: 4
Round kind: post-review confirmation
Reviewed-sha256: 4fbeef2e43137b38aa6bd4398d91e89f2e837efd3bde00b2ae93b8f9adc18878
Base percent: 90.4
Base source: lowest finished percent of its first finished round (round 1, referee-two); a new skill has no earlier baseline
Score: 111/125
Percent: 88.8
Grade: B
Critical findings: 0
Important findings: 0
Rule: lowest percent 88.8 (referee-two 88.8); ((C0 and I0) -> True) or 88.8 >= 80 -> True; 88.8 >= 90.4 -> False.
Reports: skill-judge/r4/ai-kit-spec-goal-prompt-my-referee-two.md

## Refuted findings

none (no round after round 2 had a critical or high finding; round 2's was real and fixed)

## Owner decision needed

Round 4 (the post-review confirmation) is UNRESOLVED only because 88.8% is under the round-1 base of 90.4%; it has
no critical and no high finding and it is a B above the 80% line. The base came from one lucky first judging of a
non-deterministic judge (the same skill scored 88.8, 92.0 and 88.8 across rounds 2 to 4). Does the owner accept
UNRESOLVED for this skill (an `Owner-decision:` line), or want the base lowered to the 80% line? An agent message is
not owner consent; no such line is written here.

## Owner decisions

none

## Pending acceptance

- ai-kit-spec-goal-prompt: UNRESOLVED (88.8% in the post-review confirmation round is below the round-1 base 90.4%; 0 critical, 0 high)
- ai-kit-spec-goal-prompt: UNRESOLVED (D2-1, D3-1, D4-1, D8-1 medium in round 4: the detect command template versus its omit notes at SKILL.md:55, the e2e readback at SKILL.md:69, the description's non-uses at SKILL.md:3, the scope.ask line at SKILL.md:76; not triaged beyond a line check)
- ai-kit-spec-goal-prompt: UNRESOLVED (D1-1, D5-1, D6-1, D7-1, D8-2 low: hand-off bullets, the worked-example pointer, re-asking answered questions, the script docstring, the default output dir wording)

Fixed after judging: none. The judge is non-deterministic (scores 88.8, 92.0, 88.8 on near-identical packages), so the verdict is that
of the last judged round, whose digest equals the committed package; earlier reports are kept.
