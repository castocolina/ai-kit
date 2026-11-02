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
**Round 6 and 7 judges (2026-11-02):** `router-env/my-referee-one` and `router-env/my-referee-three` through pi
(`--route-pi router --mode review`), one lane each in both rounds. `my-referee-two` answered every PONG probe (four in round 6,
one in round 7) with `503 ... service_unavailable` and was replaced by referee-three (owner rule: referee-three only as a replacement).
The skill-judge files were read once from the installed skill into `tmp/` (nine files); the prompt names those copies and
the repository's `tests/test_ai_kit_spec_goal_prompt_*.py`. No native Opus judge ran.
**Rounds:** the original loop ran at most three; rounds 4 to 7 are the post-review confirmations allowed by the
orchestrator (round 4 after code review and a security audit changed the scripts, round 5 after the milestone audit
fix INT-1 changed the generated quota rule in scripts/gp_sections.py, round 6 after the pointer form of the `/goal`
block and the evidence reference, round 7 after the `## Full objective` section and the corrected SKILL.md statements;
round 8 would run only after a real critical or high finding was fixed).
The verdict is the last judged round whose digest equals the committed package.

Post-review confirmation rounds: 4,5,6,7
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
  fixed then. The owner afterwards told this change to fix it (see round 7). Probes: referee-one and
  referee-three answered PONG; referee-two returned 503 each time. Verdict PASS: the lowest percent is 91.2 (referee-three),
  which is above 80 and above the base 90.4. That digest is now stale.
- Post-review confirmation, round 7 (2026-11-02, start commit 65aa32f plus commits 7b61f3c, bb364f7, 3577128 and
  the checker commit; two judges; the prompt adds a note on the `## Full objective` section, the corrected `tmp/` and re-render
  statements and the moved e2e read): referee-one 118/125, 94.4%, grade A, 0 critical, 2 high (D6-1 and D8-2, the same two
  findings refuted in round 6), 1 medium and 0 low, 458 s; referee-three 109/125, 87.2%, grade B, 0 critical, 0 high, 3
  medium and 7 low, 103 s. Both digests equal the committed package. The objective-loss finding (high in round 6) and the false
  re-render sentence did not come back. No new critical or high finding, so no round 8 ran. Probes: referee-one and
  referee-three answered PONG; referee-two returned 503. The lowest percent is 87.2 (referee-three): above 80 but below the
  base 90.4, so the verdict is UNRESOLVED, as in round 4. referee-three moved from 91.2 to 87.2 between rounds 6 and 7 with
  only medium and low findings, within the noise recorded below.

## Verdicts

Skill: ai-kit-spec-goal-prompt
Verdict: UNRESOLVED
Round: 7
Round kind: post-review confirmation
Reviewed-sha256: 1651b906d996fcfbec97e2bd17b4a0a089ce55d835a23ecbbd0a32ba885e7a72
Base percent: 90.4
Base source: lowest finished percent of its first finished round (round 1, referee-two); a new skill has no earlier baseline
Score: 109/125
Percent: 87.2
Grade: B
Critical findings: 0
Important findings: 2
Rule: lowest percent 87.2 (referee-one 94.4, referee-three 87.2); ((C0 and I2) -> False) or 87.2 >= 80 -> True; 87.2 >= 90.4 -> False.
Reports: skill-judge/r7/ai-kit-spec-goal-prompt-my-referee-one.md, skill-judge/r7/ai-kit-spec-goal-prompt-my-referee-three.md

## Refuted findings

Round 2's high finding was real and fixed. Round 6 (referee-one) reported three high findings:

- D6-1 (CLEANUP merges into the main checkout and removes worktrees without authorization): refuted as a defect. The cleanup is a locked owner decision (27-CONTEXT.md:229, "the branch merged into the main checkout (never pushed)") and the generated lines are scripts/gp_sections.py:369; the owner's rule also forbids a push in the same lines.
- D8-2 (`/loop` rendered for CronCreate and ScheduleWakeup rows): refuted as unlabelled. scripts/gp_sections.py:64 lists the primitives typed as a `/loop` command on purpose, and the heading and the paste text carry the label (`[unverified: ScheduleWakeup]` from scripts/gp_sections.py:286 and the sentence from scripts/gp_render.py:404). Round 7 (referee-one) repeated both findings
  (D6-1 at scripts/gp_sections.py:369, D8-2 at scripts/gp_sections.py:283); the refutations stand..
The third, D8-1 (a long objective is cut to one capped rule line outside the `/goal` block), was real and is fixed since: the
line now ends with a pointer and the file keeps the whole text in `## Full objective` (scripts/gp_sections.py:171).

## Owner decision needed

The verdict is UNRESOLVED (87.2 is above 80 but below the 90.4 base); the checker's `--gate` lists it as pending until an
owner decision exists. Context for the owner: the same skill scored 88.8, 92.0, 88.8 and 92.0 in rounds 2 to 5 with one
judge, and in rounds 6 and 7 two judges gave 92.8 and 91.2, then 94.4 and 87.2, so one judge's result has about 4 points of
noise. The package improved since round 6 (a real information-loss defect and a false sentence were fixed) and referee-one
scored it higher (94.4), while referee-three scored it lower with medium and low findings only. No Owner-decision line was written.

## Owner decisions

none

## Pending acceptance

Open findings of round 7 (judged, not fixed; no critical or high finding of the change is open):

- ai-kit-spec-goal-prompt: UNRESOLVED (D8-1 medium, referee-one: a plan work set names plans by title only, so a single plan
  without a dependency has no file name in the prompt, scripts/gp_render.py:571)
- ai-kit-spec-goal-prompt: UNRESOLVED (D2-1 and D4-1 medium, referee-three: the mindset paragraph gives no fit check of the strategy
  against the user's intent, SKILL.md:13; the description has no boundary against running the phases now, SKILL.md:3)
- ai-kit-spec-goal-prompt: UNRESOLVED (D1-1, D1-2, D3-1, D5-1, D6-1, D7-1, D8-1, D8-2, low or medium, referee-three: Unverified section
  repeats reference text, a generic NEVER line, no Gotchas section, the worked-example pointer, the `--tools` step, no eval for a
  free-text work set or the `tmp/` refusal, the hand-edit sentence, the stop-run wording)

Fixed after round 6 and judged in round 7: the objective cut (a `## Full objective` section), the false re-render sentence, the
`tmp/` statements, the e2e read order. Fixed after round 7: none. The judge is non-deterministic, so the verdict is that of the
last judged round, whose digest equals the committed package; earlier reports (r1-r6) are kept.
