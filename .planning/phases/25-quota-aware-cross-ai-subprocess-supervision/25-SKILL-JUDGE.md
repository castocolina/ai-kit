# Phase 25 — skill-judge verdicts for the four changed skills

**Date:** 2026-10-25. **Phase base:** 11ac3eb (the commit before 25-01).
**Judges** (owner set since 2026-10-24): a clean-context native Opus subagent, and opencode
`router-env/my-referee-one` and `router-env/my-referee-two` through
`node .planning/scripts/cross-ai.mjs --prefer opencode --model-opencode <lane> --route-opencode router --mode review`.
**Pass rule (AGENTS.md):** `((CRITICAL 0 and IMPORTANT 0) or score >= 96) and score >= base score`.
**Recorded score:** the native Opus score of the evidence round (round 5). It is the only judge
that completed that round; the referee lanes stopped (below), so every verdict is `BLOCKED`.

## Why the referee lanes are blocked

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

## Findings fixed after round 5 (not re-judged)

ed63b5e fixes the round-5 Importants:
- execute-gsd prints `RESUME_STATE_PATH=` and records `resume_via`, and its Step 2 exit-0
  sentence is scoped to `cross_ai_hook`;
- superpowers stops on a `dispatch-task` failure that left no JSON, and no longer calls the
  pre-dispatch rules owner-settled (A1 is still open in C7);
- spec-review keeps one resume file per pending lane with a merge lock, and names the
  session-default end of the probe walk;
- curated-config never dispatches a model call to verify a runner.

The Phase 25 code review re-runs all three judges on these four skills once the referee lanes
recover.

## Verdicts

Skill: ai-kit-spec-review
Verdict: BLOCKED
Base score: 97
Score: 100
Critical findings: 0
Important findings: 2
Rule: (C0 and I2 → false) or 100 >= 96 → true; 100 >= 97 → true. The numbers pass, but two of the three judge lanes did not complete.
Reports: skill-judge/ai-kit-spec-review-opus.md, skill-judge/ai-kit-spec-review-my-referee-one.md, skill-judge/ai-kit-spec-review-my-referee-two.md

Skill: ai-kit-spec-execute-gsd
Verdict: BLOCKED
Base score: 104
Score: 96
Critical findings: 0
Important findings: 3
Rule: (C0 and I3 → false) or 96 >= 96 → true; 96 >= 104 → false. Below the base score, so `UNRESOLVED` on the numbers; also blocked on the referee lanes.
Reports: skill-judge/ai-kit-spec-execute-gsd-opus.md, skill-judge/ai-kit-spec-execute-gsd-my-referee-one.md, skill-judge/ai-kit-spec-execute-gsd-my-referee-two.md

Skill: ai-kit-spec-execute-superpowers
Verdict: BLOCKED
Base score: 110
Score: 100
Critical findings: 0
Important findings: 2
Rule: (C0 and I2 → false) or 100 >= 96 → true; 100 >= 110 → false. Below the base score, so `UNRESOLVED` on the numbers; also blocked on the referee lanes.
Reports: skill-judge/ai-kit-spec-execute-superpowers-opus.md, skill-judge/ai-kit-spec-execute-superpowers-my-referee-one.md, skill-judge/ai-kit-spec-execute-superpowers-my-referee-two.md

Skill: ai-kit-gsd-curated-config
Verdict: BLOCKED
Base score: 106
Score: 104
Critical findings: 0
Important findings: 1
Rule: (C0 and I1 → false) or 104 >= 96 → true; 104 >= 106 → false. Below the base score, so `UNRESOLVED` on the numbers; also blocked on the referee lanes.
Reports: skill-judge/ai-kit-gsd-curated-config-opus.md, skill-judge/ai-kit-gsd-curated-config-my-referee-one.md, skill-judge/ai-kit-gsd-curated-config-my-referee-two.md

## Owner decision needed

1. Re-run the referee lanes when they recover: my-referee-one after its 5-hour session resets
   (about 06:00 -03 on 2026-10-25), and my-referee-two once its combo has an executable target.
2. Decide whether the no-regression bases for execute-gsd (104) and execute-superpowers (110),
   which were judged on much shorter skills, stay the bar for skills that now carry the Phase 25
   policy.
