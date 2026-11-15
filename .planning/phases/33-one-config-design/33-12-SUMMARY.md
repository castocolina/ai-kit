---
phase: 33-one-config-design
plan: 12
subsystem: docs
tags: [judge-loop, skill-judge, jdg-04, loop-33, rejudge]

# Dependency graph
requires:
  - phase: 33-10
    provides: "ai-kit-spec-config SKILL.md, config-file reference and evals naming config.toml"
  - phase: 33-06
    provides: "ai-kit-gsd-curated-config docs naming [runner.retry]"
  - phase: 33-11
    provides: "decision record, caller scans and README; last code plan before the judge loop"
provides:
  - ".planning/judge/loops/33.json: loop 33 pool, probes and judge counts"
  - ".planning/judge/verdicts/33/: three referee verdicts for round 1"
  - ".planning/judge/REJUDGE.md and facts.json regenerated with loop 33 rows"
affects: [33-VERIFICATION (copies the bar results and facts below)]

# Actuals (#2632): chars/4 over the realized diff of the round 1 records commit
actuals:
  tokens: 10396
  tasks: 3
  commits: 2
plan_head_before: 0221f4fac4f2da68f6a08fbc173afaa7d1935579

tech-stack:
  added: []
  patterns:
    - "Loop drivers copied from tmp/judge-32.4 with exact single-match edits: three referee instances, no native pool"

key-files:
  created:
    - .planning/judge/loops/33.json
    - .planning/judge/verdicts/33/ai-kit-gsd-curated-config/r1/opencode_router-env_my-referee-one.json
    - .planning/judge/verdicts/33/ai-kit-spec-config/r1/opencode_router-env_my-referee-one.json
    - .planning/judge/verdicts/33/ai-kit-spec-config/r1/opencode_router-env_my-referee-two.json
  modified:
    - .planning/judge/REJUDGE.md
    - .planning/judge/facts.json

key-decisions:
  - "Judged set from judged.py (diff against ab06802): ai-kit-gsd-curated-config and ai-kit-spec-config; fact-only: ai-kit-cross-ai, ai-kit-spec-execute-superpowers, ai-kit-spec-review"
  - "Pool is referee-one and referee-two (both probes usable); referee-three's probe timed out (exit 124) and was not needed"
  - "Judge counts come from judge_loop.py count: ai-kit-spec-config 2 (last percent 79.2 within 7.0 of 80), ai-kit-gsd-curated-config 1 (no deterministic trigger; jev needs_fallback, tool's own reasoning)"
  - "Both skills meet the bar in round 1; no fix round (tmp/judge-33/unmet.txt is empty)"

patterns-established: []

requirements-completed: [JDG-04]

duration: 19min
completed: 2026-11-15
status: complete
---

# Phase 33 Plan 12: Loop 33 judge records Summary

**Loop 33 round 1 judged ai-kit-spec-config (worst 83.2 B, lowest 83.2 vs loop 32 base 79.2) and ai-kit-gsd-curated-config (97.6 A, lowest 97.6 vs loop 32.4 base 88.0) with referee-one and referee-two; both meet the bar, no substitutes, no fix round.**

## Performance

- **Duration:** about 19 min
- **Started:** 2026-11-15T12:18:18-03:00
- **Completed:** 2026-11-15T12:37:00-03:00
- **Tasks:** 3 (Task 2's checkpoint was run by this executor on the orchestrator's delegation)
- **Files modified:** 6 (all under `.planning/judge/`)

## Accomplishments

- Loop 33 pool, probes and counts recorded; three referee lanes ran detached on a frozen tree (HEAD `0221f4f` throughout, no tracked change) and were ingested into the staging copy.
- Records published byte for byte, report regenerated, `check.py` (require-current), `make check-dogfood` and both closing checks exit 0.
- Bar met for both judged skills against their prior loops; stale digests after the loop are only the fact-only skills and those already stale before it.

## Task Commits

1. **Task 1: drivers, judged set, staging, probes, pool, counts, lanes launched** - scratch only under `tmp/judge-33/` (no commit)
2. **Task 2: lanes waited, no failed lane, no substitute** - scratch only (no commit)
3. **Task 3: records published, report regenerated, checks green** - `0baf499` (docs(33-12): loop 33 round 1 re-judge records and report)

**Plan metadata:** this SUMMARY's commit.

## Loop 33 bar results

Round 1. Output of `python3 tmp/judge-33/bar_table.py`:

```
regex self-check: ok
| Skill | Round | Worst percent | Grade | Bar | Lowest percent | Prior loop base | Delta |
|---|---|---|---|---|---|---|---|
| ai-kit-gsd-curated-config | 1 | 97.6 | A | met | 97.6 | 88.0 | +9.6 |
| ai-kit-spec-config | 1 | 83.2 | B | met | 83.2 | 79.2 | +4.0 |
judge-loop: ai-kit-gsd-curated-config: loop 33 round 1 (rounds 1); judges opencode:router-env/my-referee-one; worst 97.6 A; critical 0; high 0; bar met: no critical or high finding; lowest percent 97.6, loop 32.4 base 88.0; digest current
judge-loop: ai-kit-spec-config: loop 33 round 1 (rounds 1); judges opencode:router-env/my-referee-one, opencode:router-env/my-referee-two; worst 83.2 B; critical 0; high 1; bar met: grade B or better; lowest percent 83.2, loop 32 base 79.2; digest current
unmet.txt: 0 skill(s) not met
```

Per judge (all configured referees; no referee-three substitute):

| Skill | Judge | Role | Percent | Grade | Critical | High | Bar clause |
|---|---|---|---|---|---|---|---|
| ai-kit-gsd-curated-config | opencode:router-env/my-referee-one | configured referee | 97.6 | A | 0 | 0 | no critical or high finding |
| ai-kit-spec-config | opencode:router-env/my-referee-one | configured referee | 89.6 | B | 0 | 1 | grade B or better |
| ai-kit-spec-config | opencode:router-env/my-referee-two | configured referee | 83.2 | B | 0 | 1 | grade B or better |

Regression clause (enforced by `bar_with_base`): the lowest valid percent may sit at most 7.0 points under the prior-loop base. ai-kit-spec-config: 83.2 against the loop 32 base 79.2 (+4.0). ai-kit-gsd-curated-config: 97.6 against the loop 32.4 base 88.0 (+9.6).

High findings still open on ai-kit-spec-config (the bar is met by the grade clause; recorded for a later pass):
- referee-one, D6, `skills/ai-kit-spec-config/SKILL.md`: the `read_only: unconfirmed` warning comes only before writing the entry, after Step 2.5's `check-reviewer` already made one real call; fix: read the profile's permission guarantees and ask consent before the probe.
- referee-two, D8, `skills/ai-kit-spec-config/SKILL.md`: SKILL.md and `references/config-file.md` define "command-bearing" differently; fix: one definition, plus the branch for a runtime lane that overrides a user command entry.

## Loop 33 facts for the verifier

Output of `python3 tmp/judge-33/verdict_facts.py` (exit 0):

```
## Probes and pool

- judge opencode:router-env/my-referee-one; usable True; reason ; status_line AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-one exit=0 cli_rc=0 elapsed=12s out=689 tree=clean action=stop route=unknown rule=- pattern=none attempts=1 cycles=0
- judge opencode:router-env/my-referee-two; usable True; reason ; status_line AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=10s out=689 tree=clean action=stop route=unknown rule=- pattern=none attempts=1 cycles=0
- judge opencode:router-env/my-referee-three; usable False; reason status timeout exit 124 tree clean; status_line AIKIT-XAI status=timeout cli=opencode model=router-env/my-referee-three exit=124 cli_rc=130 elapsed=510s out=566 tree=clean action=stop route=unknown rule=- pattern=none attempts=1 cycles=0
- members: ["opencode:router-env/my-referee-one","opencode:router-env/my-referee-two"]
- native: null
- substitutes: none

## Verdicts

| Skill | Round | Judge | Percent | Grade | Critical | High | Substitute |
|---|---|---|---|---|---|---|---|
| ai-kit-gsd-curated-config | 1 | opencode:router-env/my-referee-one | 97.6 | A | 0 | 0 | none |
| ai-kit-spec-config | 1 | opencode:router-env/my-referee-one | 89.6 | B | 0 | 1 | none |
| ai-kit-spec-config | 1 | opencode:router-env/my-referee-two | 83.2 | B | 0 | 1 | none |
```

Judge counts (`lanes.py count`): ai-kit-spec-config 2 (last percent 79.2 is within 7.0 points of 80); ai-kit-gsd-curated-config 1 (no deterministic trigger; jev needs_fallback (own reasoning)).

Lane status lines (last AIKIT-XAI line of each lane):
- ai-kit-gsd-curated-config, referee-one: `AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-one exit=0 cli_rc=0 elapsed=229s out=509829 tree=clean action=stop route=unknown rule=- pattern=none attempts=1 cycles=0`
- ai-kit-spec-config, referee-one: `AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-one exit=0 cli_rc=0 elapsed=149s out=219471 tree=clean action=stop route=unknown rule=- pattern=none attempts=1 cycles=0`
- ai-kit-spec-config, referee-two: `AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=44s out=261097 tree=clean action=stop route=unknown rule=- pattern=none attempts=1 cycles=0`

Substitutions: none (no lane failed; `substitute.py` was not run).

Stale check (`python3 tmp/judge-33/stale_after.py`):

```
stale after: ai-kit-cross-ai ai-kit-gsd-spec-discuss ai-kit-session-wake ai-kit-spec-execute-superpowers ai-kit-spec-review ai-kit-spec-review-checklist ai-kit-usage-metrics jev-fast-decision
stale ok
```

Closing checks:
- `AI_KIT_REFUSE_REAL_HOME=1 python3 tools/judge_loop.py check .planning/judge`: exit 0 (loop 33 rows for both judged skills, `digest current`).
- `AI_KIT_REFUSE_REAL_HOME=1 python3 tools/judge_loop.py check .planning/judge --skills ai-kit-gsd-curated-config ai-kit-spec-config --require-current --gate`: exit 0.
- `AI_KIT_REFUSE_REAL_HOME=1 make check-dogfood`: `check-dogfood: ok`, exit 0.

## Stale-digest notes (D-21)

Fact-only skills (name and path updates only in this phase, never judged): `ai-kit-cross-ai`, `ai-kit-spec-review`, `ai-kit-spec-execute-superpowers`.

Carried from before loop 33 (stale at HEAD `0221f4f` before the loop, not changed materially by this phase's SKILL.md text): `ai-kit-gsd-spec-discuss`, `ai-kit-session-wake`, `ai-kit-spec-review-checklist`, `ai-kit-usage-metrics`, `jev-fast-decision` (Python-only changes, such as `jev-fast-decision`'s resolver copy in Plan 03, are not judged). `ai-kit-spec-config` and `ai-kit-gsd-curated-config` were stale before the loop and are current after it.

## Files Created/Modified

- `.planning/judge/loops/33.json` - loop 33 pool, probes and counts
- `.planning/judge/verdicts/33/<skill>/r1/<judge>.json` - three referee verdicts
- `.planning/judge/REJUDGE.md`, `.planning/judge/facts.json` - regenerated report

## Decisions Made

None beyond the plan: the judged set, pool and counts are the tool outputs listed above.

## Deviations from Plan

- `judged.py` excludes an `evals/` folder at any depth under the skill (the plan's wording) rather than only as the first path part (the 32.4 driver). Same result for this tree.
- Task 2 (orchestrator checkpoint) ran inside this executor on the orchestrator's delegation; no session wake was armed because every lane ended within about 4 minutes.

**Total deviations:** 2 minor, no effect on the records.

## Issues Encountered

referee-three's probe timed out (exit 124, 510 s, tree clean). It was only the replacement judge and no lane failed, so it was not needed.

## User Setup Required

None.

## Next Phase Readiness

Loop 33 closes with the bar met for both judged skills; 33-VERIFICATION.md can copy the bar results and facts above. The two open high findings on ai-kit-spec-config are recorded, not gating.

---
*Phase: 33-one-config-design*
