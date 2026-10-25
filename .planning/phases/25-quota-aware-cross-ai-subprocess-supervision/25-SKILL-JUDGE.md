# Phase 25 — skill-judge verdicts for the four changed skills

**Date:** 2026-10-25. **Phase base:** 11ac3eb (the commit before 25-01).
**Judges** (owner set since 2026-10-24): a clean-context native Opus subagent, and opencode
`router-env/my-referee-one` and `router-env/my-referee-two` through
`node .planning/scripts/cross-ai.mjs --prefer opencode --model-opencode <lane> --route-opencode router --mode review`.
**Pass rule (AGENTS.md):** `((CRITICAL 0 and IMPORTANT 0) or score >= 96) and score >= base score`.
**Recorded score:** round 6, the first round since round 2 in which all three judges completed.
Each verdict records the lowest of the three scores and the highest Critical and Important counts.

## Why the referee lanes were blocked in rounds 3 to 5 (recovered for round 6)

The runner stopped both referee lanes and switched nothing (owner rule). It ran one CLI per
call, relayed its evidence lines and exited:
- **my-referee-two, rounds 3 to 5:** every run crashed within 3 s. OmniRoute answered 404 `Combo has no executable targets`
  (`model_not_found`, pool size 0, `terminalReason no_executable_targets`). The runner matched no
  pattern for it (`status=crash`, `stopped=class`), so this upstream class is a candidate row for
  Phase 25.1's error catalog.
- **my-referee-one, rounds 1, 2 and 5:** each run hit `quota` exit 75 after 7 attempts with
  `retry_after_s=600`. OmniRoute answered `all targets were skipped by pre-dispatch filters (Session (5h) 100%)`
  and a member answered `[429] usage limit reached (reset after 4h 15m)`. That reset is past the
  4-hour cap, so re-invoking every 10 minutes cannot recover the lane in this run. Its rounds 3
  and 4 completed and are listed below.

## Rounds

Each cell gives the score, then `C<n>/I<n>` (Critical/Important); "quota" and "crash" mark a
runner stop with no score.

| Round | Fixes before it | Skill | Opus | referee-one | referee-two |
|---|---|---|---|---|---|
| r0 | 25-01..25-10 | spec-review | 98 C0/I4 | 89 C1 | 108 |
| r0 | | execute-gsd | 95 C0/I2 | 90 C1 | 107 |
| r0 | | execute-superpowers | 97 C1 | 104 | 110 |
| r0 | | curated-config | 99 C0/I5 | 99 | 111 |
| r1 | 1faaded, 6807c7a, ebbad9d, 7e88b4c, e2bb663 | spec-review | 99 C0/I5 | quota | 109 |
| r1 | | execute-gsd | 98 C0/I3 | quota | 106 |
| r1 | | execute-superpowers | 95 C1 | quota | 105 C1 |
| r1 | | curated-config | 101 C0/I3 | quota | 111 |
| r2 | b0c4d1e, bcfbf96, bc6fd4a, 77e343c | spec-review | 101 C0/I2 | quota | 110 C0/I1 |
| r2 | | execute-gsd | 96 C0/I3 | quota | 109 C0/I1 |
| r2 | | execute-superpowers | 104 C0/I3 | quota | 112 C0/I1 |
| r2 | | curated-config | 106 C0/I0 | quota | 109 C0/I2 |
| r3 | 5fdf76a, fba30c7, e026d59, 1a20c14 | spec-review | 102 C0/I4 | 103 C0/I3 | crash |
| r3 | | execute-gsd | 100 C0/I2 | 105 C0/I1 | crash |
| r3 | | execute-superpowers | 103 C0/I4 | 91 C0/I2 | crash |
| r3 | | curated-config | 104 C0/I3 | 94 C1/I1 | crash |
| r4 | 41dbc4b, bddc455, 4a893a1, d7f5d96 | spec-review | 103 C0/I3 | 94 C2/I3 | crash |
| r4 | | execute-gsd | 99 C0/I2 | 105 C0/I2 | crash |
| r4 | | execute-superpowers | 102 C0/I2 | 93 C1/I2 | crash |
| r4 | | curated-config | 105 C0/I2 | 102 C0/I2 | crash |
| r5 | fdd16bc, b7b0b11, 9dc8983, e2bb140 | spec-review | 100 C0/I2 | quota | crash |
| r5 | | execute-gsd | 96 C0/I3 | quota | crash |
| r5 | | execute-superpowers | 100 C0/I2 | quota | crash |
| r5 | | curated-config | 104 C0/I1 | quota | crash |
| r6 | ed63b5e, 8c3dbfa, 5b28f21, dff71c4 | spec-review | 102 C0/I1 | 104 C0/I2 | 111 C0/I1 |
| r6 | | execute-gsd | 96 C0/I2 | 105 C0/I2 | 109 C0/I0 |
| r6 | | execute-superpowers | 101 C0/I3 | 84 C2/I1 | 111 C0/I0 |
| r6 | | curated-config | 103 C0/I3 | 112 C0/I0 | 115 C0/I1 |

The judges kept finding new edge cases each round, and most of those were real defects that got
fixed in code with tests:
- the runner removed a self-test marker from the caller's home;
- an unconfirmed route inherited router cycle state;
- a deadline stop could offer a cooldown past the cap;
- an edited template 3-6 runner counted as ready;
- the GSD hook halved the 1800 s timeout floor;
- the hook did not pin its model's confirmed route;
- a pristine runner never took a same-version fix.

Opus scores stayed between 95 and 106 across the rounds. The base scores for execute-gsd (104)
and execute-superpowers (110) come from Phase 18.1's independent judging of much shorter skills.

## Findings fixed after round 5 (judged in round 6)

ed63b5e fixed the round-5 Importants. The code-review and ponytail fixes (8c3dbfa, 5b28f21, dff71c4)
also changed the runner and the policy before round 6.

## Findings fixed after round 6 (not re-judged)

- e3f00fb, superpowers (both referee-one Criticals): an owner's plain resume of a failed dispatch
  re-dispatches the pinned injection, and Step 2 re-resolves only with a pair the owner names. An
  external `BLOCKED` never takes the more-capable-model route on its own.
- 2d85d2d, execute-gsd: the fallback notice says execution stops for the owner instead of
  promising a native run (code and test). The skill states the quota retry only on a confirmed
  router lane and writes the resumable state on every stop.
- 6ae617c: spec-review gets a `.running` marker instead of writing into `.exit`, and a rule that
  two lanes pending at dispatch merge nothing; it also states the probe walk's router-lane
  consequence. curated-config gets `ensure-runner`'s real report fields and names who owns the
  re-entry and the below-template-7 choice.

Phase 25.1 edits these four SKILL.md files again (pointers to the new `ai-kit-cross-ai` skill), and
its closing plan re-runs all three judges on them.

## Verdicts

Skill: ai-kit-spec-review
Verdict: PASS
Base score: 97
Score: 102
Critical findings: 0
Important findings: 2
Rule: lowest score 102 (Opus 102, referee-one 104, referee-two 111); (C0 and I2 → false) or 102 >= 96 → true; 102 >= 97 → true.
Reports: skill-judge/ai-kit-spec-review-opus.md, skill-judge/ai-kit-spec-review-my-referee-one.md, skill-judge/ai-kit-spec-review-my-referee-two.md

Skill: ai-kit-spec-execute-gsd
Verdict: UNRESOLVED
Base score: 104
Score: 96
Critical findings: 0
Important findings: 2
Rule: lowest score 96 (Opus 96, referee-one 105, referee-two 109); (C0 and I2 → false) or 96 >= 96 → true; 96 >= 104 → false. Below the Phase 18.1 base.
Reports: skill-judge/ai-kit-spec-execute-gsd-opus.md, skill-judge/ai-kit-spec-execute-gsd-my-referee-one.md, skill-judge/ai-kit-spec-execute-gsd-my-referee-two.md

Skill: ai-kit-spec-execute-superpowers
Verdict: UNRESOLVED
Base score: 110
Score: 84
Critical findings: 2
Important findings: 3
Rule: lowest score 84 (Opus 101, referee-one 84 with C2, referee-two 111); (C2 → false) or 84 >= 96 → false. Both Criticals are fixed in e3f00fb and not re-judged; even at Opus's 101 it stays below the base of 110.
Reports: skill-judge/ai-kit-spec-execute-superpowers-opus.md, skill-judge/ai-kit-spec-execute-superpowers-my-referee-one.md, skill-judge/ai-kit-spec-execute-superpowers-my-referee-two.md

Skill: ai-kit-gsd-curated-config
Verdict: UNRESOLVED
Base score: 106
Score: 103
Critical findings: 0
Important findings: 3
Rule: lowest score 103 (Opus 103, referee-one 112, referee-two 115, the last read from its dimension table: the report omitted the score line); (C0 and I3 → false) or 103 >= 96 → true; 103 >= 106 → false. Below the Phase 22 base.
Reports: skill-judge/ai-kit-gsd-curated-config-opus.md, skill-judge/ai-kit-gsd-curated-config-my-referee-one.md, skill-judge/ai-kit-gsd-curated-config-my-referee-two.md

## Owner decision needed

The three UNRESOLVED skills fail only the no-regression bar. Their bases come from earlier, much
shorter versions: execute-gsd and execute-superpowers from Phase 18.1, curated-config from Phase 22.
Every round-6 judge scored them at 96 or more, except referee-one on superpowers (84, two Criticals
now fixed). Decide whether those bases stay the bar for skills that now carry the Phase 25 policy,
or whether the Phase 25.1 closing round sets new ones.
