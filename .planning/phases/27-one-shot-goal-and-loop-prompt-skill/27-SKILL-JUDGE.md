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
**Round 6 judges (2026-11-02):** `router-env/my-referee-one` and `router-env/my-referee-three` through pi
(`--route-pi router --mode review`), one lane each. `my-referee-two` answered a PONG probe with `503 ... service_unavailable`
in each of four probes during the round and was replaced by referee-three (owner rule: referee-three only as a replacement).
The skill-judge files were read once from the installed skill into `tmp/` (nine files); the prompt names those copies and
the repository's `tests/test_ai_kit_spec_goal_prompt_*.py`. No native Opus judge ran.
**Rounds:** the original loop ran at most three; rounds 4 to 6 are the post-review confirmations allowed by the
orchestrator (round 4 after code review and a security audit changed the scripts, round 5 after the milestone audit
fix INT-1 changed the generated quota rule in scripts/gp_sections.py, round 6 after the pointer form of the `/goal`
block and the evidence reference; round 6 is the last, there is no round 7).
The verdict is the last judged round whose digest equals the committed package.

Post-review confirmation rounds: 4,5,6
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
- Post-review confirmation, round 6 (2026-11-02, start commit 1bbcc7d, two judges; the prompt adds a note on the pointer
  form of the `/goal` block in scripts/gp_render.py, the new eval `precise-long-goal-pointer`, the new
  `references/evidence.md` and the shorter `## Unverified`): referee-one 116/125, 92.8%, grade A, 0 critical, 3 high
  (D6-1, D8-1, D8-2), 2 medium and 0 low, 596 s; referee-three 114/125, 91.2%, grade A, 0 critical, 0 high, 3 medium and
  4 low, 140 s. Both digests equal the committed package. The three high findings of referee-one were triaged against
  the code: two are refuted (see Refuted findings) and one (D8-1) is real, older than this change and a deliberate
  design choice that the owner told this change to leave alone, so it is recorded under Pending acceptance and not
  fixed. No critical or high finding was a defect of this change, so no fix and no round 7 ran. Probes: referee-one and
  referee-three answered PONG; referee-two returned 503 each time. Verdict PASS: the lowest percent is 91.2 (referee-three),
  which is above 80 and above the base 90.4.

## Verdicts

Skill: ai-kit-spec-goal-prompt
Verdict: PASS
Round: 6
Round kind: post-review confirmation
Reviewed-sha256: c3f5572f493a3c01c69dfe2b3d497e95e86532adb70bbe2959e07711db894bde
Base percent: 90.4
Base source: lowest finished percent of its first finished round (round 1, referee-two); a new skill has no earlier baseline
Score: 114/125
Percent: 91.2
Grade: A
Critical findings: 0
Important findings: 3
Rule: lowest percent 91.2 (referee-one 92.8, referee-three 91.2); ((C0 and I3) -> False) or 91.2 >= 80 -> True; 91.2 >= 90.4 -> True.
Reports: skill-judge/r6/ai-kit-spec-goal-prompt-my-referee-one.md, skill-judge/r6/ai-kit-spec-goal-prompt-my-referee-three.md

## Refuted findings

Round 2's high finding was real and fixed. Round 6 (referee-one) reported three high findings:

- D6-1 (CLEANUP merges into the main checkout and removes worktrees without authorization): refuted as a defect. The cleanup is a locked owner decision (27-CONTEXT.md:229, "the branch merged into the main checkout (never pushed)") and the generated lines are scripts/gp_sections.py:356; the owner's rule also forbids a push in the same lines.
- D8-2 (`/loop` rendered for CronCreate and ScheduleWakeup rows): refuted as unlabelled. scripts/gp_sections.py:62 lists the primitives typed as a `/loop` command on purpose, and the heading and the paste text carry the label (`[unverified: ScheduleWakeup]` from scripts/gp_sections.py:273 and the sentence from scripts/gp_render.py:394).
The third, D8-1 (a long objective is cut to one capped rule line outside the `/goal` block), is not refuted: it is real. See Pending acceptance.

## Owner decision needed

none for the verdict (PASS). Context for the owner: the same skill scored 88.8, 92.0, 88.8 and 92.0 in rounds 2 to 5
(round 4 was UNRESOLVED against the 90.4 base), so one judge's result has about 3 points of noise. Round 6 had two
judges (referee-one 92.8, referee-three 91.2; referee-two returned 503) and the verdict takes the lower one, 91.2,
only 0.8 above the 90.4 base. One real high finding of referee-one is left open on purpose (see Pending acceptance).

## Owner decisions

none

## Pending acceptance

Open findings of round 6 (judged, not fixed; the owner told this change to leave the autonomous, loop and plain blocks
as they are, and only critical or high defects of the change itself get a fix):

- ai-kit-spec-goal-prompt: PASS (D8-1 high, referee-one: the OBJECTIVE rule line cut to one capped line in the
  autonomous, loop and plain blocks, scripts/gp_sections.py:168; deliberate since dbb32f9 and listed as owner_decision P4 in
  27-OWNER-CAPTURES.md; the `/goal` block no longer loses it because the pointer form keeps the full text)
- ai-kit-spec-goal-prompt: PASS (D4-1 medium both judges: the description's boundary against running the phases now, SKILL.md:3; D8-3 medium
  referee-one and D8-1 medium referee-three: `tmp/` is assumed to exist and be git-ignored, SKILL.md:52; D3-1 medium referee-three: the NEVER
  reason "the next render would overwrite it" is false because render writes a new `-2` file, SKILL.md:146)
- ai-kit-spec-goal-prompt: PASS (D1-1, D2-1, D5-1, D7-1 low, referee-three: the two Unverified-style sections repeat reference text, no
  fit check of the strategy against the user's intent, the e2e MANDATORY read comes after the first e2e readback, no eval with mockups
  or with `native_execution` true)

Fixed after the last round, unjudged: none. The judge is non-deterministic, so the verdict is that of the last judged round,
whose digest equals the committed package; earlier reports (r1-r5) are kept.
