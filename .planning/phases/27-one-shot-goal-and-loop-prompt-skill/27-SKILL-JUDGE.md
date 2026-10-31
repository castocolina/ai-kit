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
**Rounds:** the original loop ran at most three; rounds 4 and 5 are the post-review confirmations allowed by the
orchestrator (round 4 after code review and a security audit changed the scripts, round 5 after the milestone audit
fix INT-1 changed the generated quota rule in scripts/gp_sections.py; no round 6).
The verdict is the last judged round whose digest equals the committed package.

Post-review confirmation rounds: 4,5
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
- Post-review confirmation, round 5 (referee-two, 368 s; the prompt adds a note on the INT-1 quota-rule change in
  scripts/gp_sections.py, fix 6cd87b7, and on the history compaction that made the committed package differ from
  round 4's): 115/125, 92.0%, grade A, 0 critical, 0 high, 3 medium and 5 low findings. PASS (92.0 >= base 90.4).
  Its digest equals the committed package. Nothing needed a fix. The r4 UNRESOLVED stays on record in its report.
- `my-referee-three` was probed in rounds 1, 2, 4 and 5 and never answered (round 1: the full one-hour backoff;
  rounds 2, 4 and 5: one probe each): `route down`, no lane. `my-referee-one` was not probed; no Opus judge ran.

## Verdicts

Skill: ai-kit-spec-goal-prompt
Verdict: PASS
Round: 5
Round kind: post-review confirmation
Reviewed-sha256: 500cc4187664bc6c50f7787a787f7795660fe3b799e31cbbde96df5a204dc95e
Base percent: 90.4
Base source: lowest finished percent of its first finished round (round 1, referee-two); a new skill has no earlier baseline
Score: 115/125
Percent: 92.0
Grade: A
Critical findings: 0
Important findings: 0
Rule: lowest percent 92.0 (referee-two 92.0); ((C0 and I0) -> True) or 92.0 >= 80 -> True; 92.0 >= 90.4 -> True.
Reports: skill-judge/r5/ai-kit-spec-goal-prompt-my-referee-two.md

## Refuted findings

none (no round after round 2 had a critical or high finding; round 2's was real and fixed)

## Owner decision needed

none for the verdict (PASS). Context for the owner: the same skill scored 88.8, 92.0, 88.8 and 92.0 in rounds 2 to 5
(round 4 was UNRESOLVED against the 90.4 base), so one judge's result has about 3 points of noise; the PASS is
referee-two only (referee-three down, no second judge).

## Owner decisions

none

## Pending acceptance

Open medium and low findings of round 5 (judged, not fixed):

- ai-kit-spec-goal-prompt: PASS (D4-1, D7-1, D8-1 medium: the description's non-uses at SKILL.md:3, the script docstring's exit-code wording at scripts/goal_prompt.py:93, the render re-selection note at SKILL.md:110; not triaged beyond a line check)
- ai-kit-spec-goal-prompt: PASS (D1-1, D2-1, D3-1, D5-1, D8-2 low: generic NEVER lines, the mindset sentence, the golden-file pointer, the worked-example provenance wording)

Fixed after the last round, unjudged: none. The judge is non-deterministic, so the verdict is that of the last judged round,
whose digest equals the committed package; earlier reports (r1-r4) are kept.
