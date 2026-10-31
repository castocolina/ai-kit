# Phase 26 — skill-judge verdicts for the five changed skills

**Date:** 2026-10-30. **Judges** changed during the phase on the owner's instructions: rounds 1-2 ran a
clean-context native Opus subagent plus `router-env/my-referee-one` and `my-referee-two` through
opencode; round 3 ran Opus alone (the referee lanes were quota-blocked); from 2026-10-30 native Opus
stopped, referee-one was unavailable for days, and rounds 4-15 ran `my-referee-three` and/or
`my-referee-two` through pi (`--runtime pi --route-pi router --mode review --outer-timeout 3600`),
whichever answered a PONG probe. The final round 15 ran referee-two alone; referee-three's route
returned "Combo has no executable targets" (owner rule: one available judge is enough, two is ideal).
**Pass rule (AGENTS.md):** `((CRITICAL 0 and IMPORTANT 0) or score >= 96) and score >= base`.
Each verdict aggregates the finished lanes of the skill's latest judged round: the lowest score and the
highest Critical and Important counts. `skill-judge/check_verdicts.py` reproduces every verdict from the
reports; its `--gate` mode lists every non-PASS verdict as pending unless the owner accepted it.
The makefile skill's SKILL.md changed only a count string in this phase and is not judged.

## Rounds

Sixteen rounds ran; every fix is a `fix(26-11)` commit. Only rounds 1, 2, 15 and 16 keep their reports in
`skill-judge/` (the others live in the ignored scratch directory).

- Round 1 (Opus, referee-one, referee-two; 15 lanes): all five below the bar. Fixes 71a3db0, 16ddc7f, 4ece930, 8414319.
- Round 2 (same judges): session-wake 98, execute-gsd 97, execute-superpowers 97, rules-agents 100 (1 Critical), rules-all 96. Fixes 54e9556, dede6b3, e1300f9, c6aaa92.
- Round 3 (Opus alone): 98-102, 1-2 Important each. Fixes 974e645, 568bf4c, 680725c.
- Rounds 4-6 (referee-three): scores 92-104; rules-all and session-wake reached 0/0 in round 6. Fixes ca17d9f, 4a5eafd, 7904a05, 657ac78, 96d85fe.
- Rounds 7-11 (referee-two and/or referee-three): each round found new, mostly real details in the same packages; fixes 86af192, d288e31, 73ecc81, da88015, f126f18, 9a60f5a, ad03c23, 21601e8, 3905a50, bd8b951, c96bb20, 954f67a, cd83677, 6146ac5, 501e838, 350a9ef.
- Rounds 12-14 (referee-two): the judge now checks claims against the code; several Critical findings were real (a missing backup on the links-only path, an invented wake session id, the zero-plan scan) and were fixed; others were refuted with evidence in the fix logs (a quoted-glob loop that does expand, `RC=$?` after a command substitution, `check_tool_presence` running repo binaries). Fixes 58bec82, 69bccc0, 76d2a06, b560ddd, 93101a8, d9f7c5a, a8b2f79, 399ea68, 33cbc80, ecb715f, 66c6c79.
- Round 15 (referee-two alone): fixes 28a3c70, 36fec9c, aa81a27 precede it.
- Round 16 (referee-two, execute-superpowers only, requested by the owner for SJ-2): fix dd7b004 precedes it; the score rose from 94 to 98 and the verdict from FAIL to UNRESOLVED. The other four skills keep their round 15 verdicts.

The judge is not deterministic: the session-wake package, unchanged between rounds 13 and 14, went from
115 with 0 Important to 108 with 1 Important under the same judge. Iterating further does not converge,
so the phase stops here and carries the remaining findings forward.

## Verdicts

Skill: ai-kit-session-wake
Verdict: PASS
Round: 15
Reviewed-sha256: ff755e6e941bbca160be84bde69dafff453deefcd912422586aa38db87fd4ff2
Base score: 95
Base source: lowest finished score of its first finished round (round 1, Opus)
Score: 108
Critical findings: 0
Important findings: 0
Rule: lowest score 108 (referee-two 108); ((C0 and I0) -> True) or 108 >= 96 -> True; 108 >= 95 -> True.
Reports: skill-judge/r15/ai-kit-session-wake-my-referee-two.md

Skill: ai-kit-spec-execute-gsd
Verdict: UNRESOLVED
Round: 15
Reviewed-sha256: 087fb33173e1a99aa9009e1d2573ea6d90bc206f2c639b29ac81a01a62811b71
Base score: 105
Base source: 25.1-SKILL-JUDGE.md round 5
Score: 101
Critical findings: 0
Important findings: 2
Rule: lowest score 101 (referee-two 101); ((C0 and I2) -> False) or 101 >= 96 -> True; 101 >= 105 -> False.
Reports: skill-judge/r15/ai-kit-spec-execute-gsd-my-referee-two.md

Skill: ai-kit-spec-execute-superpowers
Verdict: UNRESOLVED
Round: 16
Reviewed-sha256: 683e3a0c9be177ab0ff81ec767451f1e17a1d6cb7e81730e143ef8ee71fd8e58
Base score: 110
Base source: 25.1-SKILL-JUDGE.md, carried from Phase 18.1
Score: 98
Critical findings: 0
Important findings: 4
Rule: lowest score 98 (referee-two 98); ((C0 and I4) -> False) or 98 >= 96 -> True; 98 >= 110 -> False.
Reports: skill-judge/r16/ai-kit-spec-execute-superpowers-my-referee-two.md

Skill: ai-kit-project-rules-agents
Verdict: FAIL
Round: 15
Reviewed-sha256: 60db9a1a8f05bffe2dafe21132a78e4812cf7f3e66a557df61682947ebc3f475
Base score: 99
Base source: 16.1-SKILL-JUDGE-independent.md
Score: 93
Critical findings: 1
Important findings: 2
Rule: lowest score 93 (referee-two 93); ((C1 and I2) -> False) or 93 >= 96 -> False; 93 >= 99 -> False.
Reports: skill-judge/r15/ai-kit-project-rules-agents-my-referee-two.md

Skill: ai-kit-project-rules-all
Verdict: PASS
Round: 15
Reviewed-sha256: 16918292c2cacdeb40792fbd1e44247c55668883d1e836e7c0521ad496ba6582
Base score: 95
Base source: 16.1-SKILL-JUDGE-independent.md
Score: 102
Critical findings: 0
Important findings: 1
Rule: lowest score 102 (referee-two 102); ((C0 and I1) -> False) or 102 >= 96 -> True; 102 >= 95 -> True.
Reports: skill-judge/r15/ai-kit-project-rules-all-my-referee-two.md

## Owner decision needed

Three skills do not pass: 3 verdicts are held pending below. Two questions for the owner:
whether a single non-deterministic judge's last-round result is the right bar for "no Critical or
Important" (it re-opens new details every round), and whether execute-gsd (101 vs base 105) and
execute-superpowers (94 vs base 110) keep their carried bases, the open Phase 25 decision (O9). The
rules-agents Critical in round 15 claims an unattended `git restore` can discard uncommitted edits; a
`clean` file is by definition tracked and unmodified at backup time, so there is nothing to discard
(the dirty files are backed up and restored from the backup), but the text can be made clearer.

## Owner decisions

(none given)

## Pending acceptance

- ai-kit-spec-execute-gsd: UNRESOLVED (score 101 >= 96 but below the base 105)
- ai-kit-spec-execute-superpowers: UNRESOLVED (score 98 >= 96 but below the base 110; 4 Important open)
- ai-kit-project-rules-agents: FAIL (score 93 < 96 with 1 Critical and 2 Important)
