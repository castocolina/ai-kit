---
phase: 34-jev-backends-by-host-and-laya-calibration
plan: 10
subsystem: docs
tags: [judge-loop, skill-judge, jdg-04, jev-13, loop-34, rejudge]

# Dependency graph
requires:
  - phase: 34-01..34-09
    provides: "jev-fast-decision SKILL.md, reference.md, backends/ and evals (settings, probe, records); the curated-config jev session gate sentence (Plan 08)"
provides:
  - ".planning/judge/loops/34.json: loop 34 pool, probes and judge counts"
  - ".planning/judge/verdicts/34/jev-fast-decision/r1/: two referee verdicts"
  - ".planning/judge/REJUDGE.md and facts.json regenerated with the loop 34 row"
affects: [34-VERIFICATION (copies the bar results and facts below)]

actuals:
  tasks: 3
  commits: 2
plan_head_before: b8d01e02f91023235199ff061defaa1bffecede0

tech-stack:
  added: []
  patterns:
    - "Loop drivers copied from tmp/judge-33 with 33 -> 34 (no other edit needed)"

key-files:
  created:
    - .planning/judge/loops/34.json
    - .planning/judge/verdicts/34/jev-fast-decision/r1/opencode_router-env_my-referee-one.json
    - .planning/judge/verdicts/34/jev-fast-decision/r1/opencode_router-env_my-referee-two.json
  modified:
    - .planning/judge/REJUDGE.md
    - .planning/judge/facts.json

key-decisions:
  - "Judged set from judged.py (diff against 76269a2): jev-fast-decision; fact-only: ai-kit-gsd-curated-config"
  - "Pool is referee-one and referee-two (all three probes usable on the second attempt); referee-three not needed"
  - "Judge count from judge_loop.py count: jev-fast-decision 2 (last percent 86.4 is within 7.0 points of 80)"
  - "Bar met in round 1 by grade B or better; no fix round (tmp/judge-34/unmet.txt is empty)"

patterns-established: []

requirements-completed: [JEV-13, JDG-04]

duration: 25min
completed: 2026-11-15
status: complete
---

# Phase 34 Plan 10: Loop 34 judge records Summary

**Loop 34 round 1 judged jev-fast-decision with referee-one (94.4 A, high 1) and referee-two (89.6 B, high 0): the bar is met by grade B or better, and the lowest valid percent 89.6 sits 3.2 points above the loop 32.1 base 86.4. No substitutes and no fix round.**

## Performance

- **Duration:** about 25 min of loop work (the first probe attempt's root-cause work is described under Issues)
- **Started:** 2026-11-15T21:22:00-03:00
- **Completed:** 2026-11-15T21:47:14-03:00
- **Tasks:** 3. The orchestrator delegated Task 2's checkpoint to this executor.
- **Files modified:** 5 (all under `.planning/judge/`)

## Accomplishments

- Loop 34 pool, probes and count recorded. Two referee lanes ran detached on a frozen tree: HEAD stayed at `62c7f7d` throughout and no tracked file changed. Both lanes were ingested into the staging copy.
- Records published byte for byte (`published 3 files`) and the report regenerated. `check.py` (require-current), `make check-dogfood` and both closing checks exit 0.
- jev-fast-decision meets the bar against loop 32.1. After the loop, the only stale digests are the fact-only skill and skills that were already stale before it.

## Task Commits

1. **Task 1: drivers, judged set, staging, probes, pool, count, lanes launched.** Scratch only under `tmp/judge-34/` (no commit).
2. **Task 2: lanes waited; none failed, so no substitute.** Scratch only (no commit).
3. **Task 3: records published, report regenerated, checks green.** `0814ef2` (docs(34-10): loop 34 round 1 re-judge records and report)

**Plan metadata:** this SUMMARY's commit.

## Loop 34 bar results

Round 1. Output of `python3 tmp/judge-34/bar_table.py`:

```
regex self-check: ok
| Skill | Round | Worst percent | Grade | Bar | Lowest percent | Prior loop base | Delta |
|---|---|---|---|---|---|---|---|
| jev-fast-decision | 1 | 94.4 | A | met | 89.6 | 86.4 | +3.2 |
judge-loop: jev-fast-decision: loop 34 round 1 (rounds 1); judges opencode:router-env/my-referee-one, opencode:router-env/my-referee-two; worst 94.4 A; critical 0; high 1; bar met: grade B or better; lowest percent 89.6, loop 32.1 base 86.4; digest current
unmet.txt: 0 skill(s) not met
```

Per judge (both are configured referees; no referee-three substitute):

| Skill | Judge | Role | Percent | Grade | Critical | High | Bar clause |
|---|---|---|---|---|---|---|---|
| jev-fast-decision | opencode:router-env/my-referee-one | configured referee | 94.4 | A | 0 | 1 | grade B or better |
| jev-fast-decision | opencode:router-env/my-referee-two | configured referee | 89.6 | B | 0 | 0 | grade B or better |

Regression clause (enforced by `bar_with_base`): the lowest valid percent may sit at most 7.0 points under the prior-loop base. jev-fast-decision scores 89.6 against the loop 32.1 base 86.4, which is +3.2.

JEV-03's re-judged judge lane: the two configured referee lanes of this loop are that re-judge. Both run CLI `opencode`, one with model `router-env/my-referee-one` and one with `router-env/my-referee-two`, as their AIKIT-XAI status lines below show.

One high finding is still open. The bar is met by the grade clause, so it is recorded for a later pass and does not gate:
- referee-one D8-1 (high), `skills/jev-fast-decision/SKILL.md:40`. Problem: "`ok` → match ids to `answers` or `errors`. `needs_fallback: true` → you decide that item" does not separate a direct screen response from the ladder response. Fix: for ladder, read `items[id]`, each backend column's `fallback` or `error`, and `decided_by`, and use own reasoning when `decided_by` is `own_reasoning`.

Medium findings: referee-one D8-2 (`reference.md:38`, the `reviewed_head` placeholder inside a single-quoted heredoc) and D7-1 (`evals/evals.json:47`, the one-item-per-ladder and three-option assertions). referee-two D5-1 (`reference.md:150`, the dated spike and changelog have no load condition), D6-1 (`SKILL.md:24`, which call default a caller should use), D7-1 (`evals/trigger-queries.json:12`, every should-trigger query names jev, Laya, TypeSafe or the ladder) and D8-1 (`SKILL.md:36`, the bare screen example against the ladder rule).

## Loop 34 facts for the verifier

Output of `python3 tmp/judge-34/verdict_facts.py` (exit 0):

```
## Probes and pool

- judge opencode:router-env/my-referee-one; usable True; reason ; status_line AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-one exit=0 cli_rc=0 elapsed=9s out=2214 tree=clean action=stop route=unknown rule=- pattern=none attempts=1 cycles=0
- judge opencode:router-env/my-referee-two; usable True; reason ; status_line AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=16s out=2224 tree=clean action=stop route=unknown rule=- pattern=none attempts=1 cycles=0
- judge opencode:router-env/my-referee-three; usable True; reason ; status_line AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-three exit=0 cli_rc=0 elapsed=8s out=2206 tree=clean action=stop route=unknown rule=- pattern=none attempts=1 cycles=0
- members: ["opencode:router-env/my-referee-one","opencode:router-env/my-referee-two"]
- native: null
- substitutes: none

## Verdicts

| Skill | Round | Judge | Percent | Grade | Critical | High | Substitute |
|---|---|---|---|---|---|---|---|
| jev-fast-decision | 1 | opencode:router-env/my-referee-one | 94.4 | A | 0 | 1 | none |
| jev-fast-decision | 1 | opencode:router-env/my-referee-two | 89.6 | B | 0 | 0 | none |
```

Judge count (`lanes.py count`): jev-fast-decision 2 (last percent 86.4 is within 7.0 points of 80).

Lane status lines (last AIKIT-XAI line of each lane):
- jev-fast-decision, referee-one: `AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-one exit=0 cli_rc=0 elapsed=55s out=376269 tree=clean action=stop route=unknown rule=- pattern=none attempts=1 cycles=0`
- jev-fast-decision, referee-two: `AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=52s out=240413 tree=clean action=stop route=unknown rule=- pattern=none attempts=1 cycles=0`

Substitutions: none. No lane failed, so `substitute.py` was not run.

Stale check (`python3 tmp/judge-34/stale_after.py`):

```
stale after: ai-kit-cross-ai ai-kit-gsd-curated-config ai-kit-gsd-spec-discuss ai-kit-session-wake ai-kit-spec-execute-superpowers ai-kit-spec-review ai-kit-spec-review-checklist ai-kit-usage-metrics
stale ok
```

Closing checks:
- `AI_KIT_REFUSE_REAL_HOME=1 python3 tools/judge_loop.py check .planning/judge`: exit 0. The loop 34 row for jev-fast-decision reads `digest current`.
- `AI_KIT_REFUSE_REAL_HOME=1 python3 tools/judge_loop.py check .planning/judge --skills jev-fast-decision --require-current --gate`: exit 0.
- `python3 tmp/judge-34/check.py`: exit 0.
- `AI_KIT_REFUSE_REAL_HOME=1 make check-dogfood`: `check-dogfood: ok`, exit 0 (run before the records commit).

## Stale-digest notes (D-14)

Fact-only, never judged: `ai-kit-gsd-curated-config`. Plan 08 adds one fact sentence to its SKILL.md about the jev session gate.

Carried from before loop 34 (stale at HEAD `b8d01e0` before the loop, and this phase does not change their SKILL.md text materially): `ai-kit-cross-ai`, `ai-kit-gsd-spec-discuss`, `ai-kit-session-wake`, `ai-kit-spec-execute-superpowers`, `ai-kit-spec-review`, `ai-kit-spec-review-checklist`, `ai-kit-usage-metrics`. jev-fast-decision was stale before the loop and is current after it.

## Files Created/Modified

- `.planning/judge/loops/34.json`: loop 34 pool, probes and count
- `.planning/judge/verdicts/34/jev-fast-decision/r1/<judge>.json`: two referee verdicts
- `.planning/judge/REJUDGE.md`, `.planning/judge/facts.json`: regenerated report

## Decisions Made

None beyond the plan. The judged set, the pool and the count are the tool outputs listed above.

## Deviations from Plan

- The first probe attempt at HEAD `b8d01e0` failed for all three referees, so there was no pool. Every runner call exited 0 with `tree=clean`, but no answer held the sentinel. Cause: opencode 2.3.0, installed on 2026-11-15 at 13:22 local, makes the plan agent add a synthetic plan-mode `<system-reminder>` after the first answer. The model answers it a second time, and the runner kept only the last assistant message. The orchestrator fixed the runner in `62c7f7d`. The run then resumed from Task 1 step 6: `head.txt` set to `62c7f7d`, `stage.py` re-run, and the old probe directory moved to `tmp/judge-34/probe.old-1` so its `done` markers could not end the probe wait early. Evidence from the first attempt is in `tmp/judge-34/task1-r1.log` and `tmp/judge-34/diag/`.
- The orchestrator delegated Task 2 (its checkpoint) to this executor. No session wake was armed because both lanes ended within about one minute.

**Total deviations:** 2. Neither has any effect on the records.

## Issues Encountered

The first probe failure is described above. Nothing failed after the runner fix.

## User Setup Required

None.

## Next Phase Readiness

Loop 34 closes in round 1 with the bar met for jev-fast-decision. 34-VERIFICATION.md can copy the bar results and facts above. The open high finding (referee-one D8-1) is recorded and does not gate.

## Round 2 (close-out part 1, 2026-11-15)

Why: the round 1 high finding D8-1 (SKILL.md read every result as a screen call) was fixed in 148b3de
(`## Read the result`: a screen call's `answers`/`errors`/`needs_fallback` apart from a ladder's
`items[<id>]`, `decided_by` and each column's `fallback`/`error`; two evals; a pinning doc test), and the
code-review fixes changed reference.md, the backends and the evals. Round 2 ran at HEAD `9b9eeac` on a frozen
tree with the same pool (referee-one, referee-two; no probe re-run, no substitute). Records: `d9bad05`
(`docs(34-10): loop 34 round 2 re-judge records and report`).

```
regex self-check: ok
| Skill | Round | Worst percent | Grade | Bar | Lowest percent | Prior loop base | Delta |
|---|---|---|---|---|---|---|---|
| jev-fast-decision | 2 | 94.4 | A | met | 84.0 | 86.4 | -2.4 |
judge-loop: jev-fast-decision: loop 34 round 2 (rounds 2); judges opencode:router-env/my-referee-one, opencode:router-env/my-referee-two; worst 94.4 A; critical 0; high 1; bar met: grade B or better; lowest percent 84.0, loop 32.1 base 86.4; digest current
unmet.txt: 0 skill(s) not met
```

| Skill | Round | Judge | Role | Percent | Grade | Critical | High |
|---|---|---|---|---|---|---|---|
| jev-fast-decision | 2 | opencode:router-env/my-referee-one | configured referee | 94.4 | A | 0 | 1 |
| jev-fast-decision | 2 | opencode:router-env/my-referee-two | configured referee | 84.0 | B | 0 | 0 |

The regression clause holds: the lowest valid percent 84.0 sits 2.4 points under the loop 32.1 base 86.4,
inside the 7.0-point allowance `bar_with_base` enforces. Lane status lines:
- referee-one: `AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-one exit=0 cli_rc=0 elapsed=46s out=451058 tree=clean action=stop route=unknown rule=- pattern=none attempts=1 cycles=0`
- referee-two: `AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=52s out=232753 tree=clean action=stop route=unknown rule=- pattern=none attempts=1 cycles=0`

Round 1's D8-1 is not repeated. One high finding is open and does not gate (bar met by grade): referee-one
D8-1 (r2), `SKILL.md:10`: "From this skill's directory, run ... `--probe`" moves the working directory away
from the project, so the client's project layer (`./.aikit/config.toml`, read from the cwd) is not the
project's. Fix: run the client by its resolved skill path from the project's directory. Medium findings:
referee-one D7-1 (`evals.json:22`, exactly three options vs the no-match advice), D8-2 (`reference.md:38`,
the `<git rev-parse HEAD>` placeholder); referee-two D5-1 (`reference.md` one 245-line file), D7-1
(`eval_cases.py` has no `--help` or usage test), D8-1 (`SKILL.md:38`, name the nesting of `answers`/`errors`).

Closing checks: `check.py` exit 0; `judge_loop.py check .planning/judge` exit 0; `--skills jev-fast-decision
--require-current --gate` exit 0; `make check-dogfood` exit 0 (`check-dogfood: ok`); `stale_after.py`:
`stale ok` (the same eight carried names as round 1).

## Round 3 (close-out part 2, 2026-11-16; the last round under the three-round cap)

Why: the round 2 high finding D8-1 (`SKILL.md:10`, the probe run from the skill's folder loses the project
layer) was fixed in fdfe5e5 (the probe and `config set` run as `<skill-dir>/scripts/...` from the project root,
never after `cd` into the skill; a doc test and a client test with a temp project's `[jev] enabled = false`).
Round 3 ran at HEAD `fdfe5e5` on a frozen tree with the same pool (referee-one, referee-two; no substitute).

```
| Skill | Round | Worst percent | Grade | Bar | Lowest percent | Prior loop base | Delta |
|---|---|---|---|---|---|---|---|
| jev-fast-decision | 3 | 92.0 | A | met | 88.8 | 86.4 | +2.4 |
judge-loop: jev-fast-decision: loop 34 round 3 (rounds 3); judges opencode:router-env/my-referee-one, opencode:router-env/my-referee-two; worst 92.0 A; critical 0; high 2; bar met: grade B or better; lowest percent 88.8, loop 32.1 base 86.4; digest current
unmet.txt: 0 skill(s) not met
```

| Skill | Round | Judge | Role | Percent | Grade | Critical | High |
|---|---|---|---|---|---|---|---|
| jev-fast-decision | 3 | opencode:router-env/my-referee-one | configured referee | 92.0 | A | 0 | 2 |
| jev-fast-decision | 3 | opencode:router-env/my-referee-two | configured referee | 88.8 | B | 0 | 0 |

Lane status lines:
- referee-one: `AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-one exit=0 cli_rc=0 elapsed=45s out=490842 tree=clean action=stop route=unknown rule=- pattern=none attempts=1 cycles=0`
- referee-two: `AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=87s out=154379 tree=clean action=stop route=unknown rule=- pattern=none attempts=1 cycles=0`

Round 2's D8-1 is not repeated. Two high findings are open and do not gate (bar met by grade); the loop stops
here and they go to the owner: referee-one D8-1 (r3), `SKILL.md:25`: the ladder example's item has no
`context`, and the client rejects it (`items.c1`: `error: invalid_input`, `reason: empty_context`, reproduced in
a scratch HOME with Laya on a closed port); D8-2 (r3), `reference.md:37`: the screen example runs
`scripts/jev_review.py` by a relative path and carries the `<git rev-parse HEAD>` placeholder inside a quoted
heredoc. Medium findings: referee-one D8-3 (`SKILL.md:13`, the TypeSafe key named as environment only), D7-1
(`evals.json:22`, the choice eval does not require `context`), D7-2 (`eval_cases.py:257`, no `--help`);
referee-two D5-1 (`reference.md` one file), D6-1 and D8-1 (`SKILL.md:10`/`:34`, screen statuses only in the
reference), D7-1 (`evals.json:9`, `evidence` vs `context`).

Closing checks: `check.py` exit 0; `judge_loop.py check .planning/judge` exit 0; `--skills jev-fast-decision
--require-current --gate` exit 0; `make check-dogfood` exit 0 (`check-dogfood: ok`); `stale_after.py`:
`stale ok` (the same eight carried names as round 1). Hard-stop snapshot over the run: 0 changes.

---
*Phase: 34-jev-backends-by-host-and-laya-calibration*
