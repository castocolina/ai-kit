---
phase: 32-re-judge-baseline
plan: 08
subsystem: testing
tags: [skill-judge, judge-loop, cross-ai, baseline, native-judge]

# Dependency graph
requires:
  - phase: 32-re-judge-baseline
    provides: tools/judge_loop.py (prompt, pool, count, ingest, check), the 15-skill inputs, the frozen tree at c5c77d3
provides:
  - Round-1 staging records for the 15 judged skills (tmp/p32/judge/, scratch, not tracked)
  - Judge pool referee-two and referee-three with probe results, and 5 native substitutes
affects: [32-09 (REJUDGE.md report written from these records)]

# Actuals (#2632)
actuals:
  tokens: 0        # no tracked file changed; scratch outputs are not a diff
  tasks: 3
  commits: 0       # MEASURED: git rev-list --count c5c77d3..HEAD before this SUMMARY commit

tech-stack:
  added: []
  patterns: [sentinel probe before a judge counts, detached lane workers with per-attempt ingest, one native substitute per failed lane]

key-files:
  created: []
  modified: []

key-decisions:
  - "Judge pool: referee-two and referee-three (both probes matched exactly). referee-one left out, owner-stated unavailable."
  - "Count kept deterministic (1) for ai-kit-gsd-spec-discuss and ai-kit-spec-goal-prompt: jev returned needs_fallback."
  - "Each of the five failed external lanes got a native ai-kit-judge substitute with substitute.json. No skill is marked second judge unavailable."

patterns-established:
  - "A judge counts only after its sentinel probe matches the token file exactly (judge_loop.py pool)."

requirements-completed: [JDG-06]

# Metrics
duration: 36min (lane window 15:15-15:51 local, from the orchestrator ledger)
completed: 2026-11-07
status: complete
plan_head_before: c5c77d31f6001ffd119193e720c895342cce9484
plan_head_after: c5c77d31f6001ffd119193e720c895342cce9484
---

# Phase 32 Plan 08: Baseline Judge Run Summary

**Round-1 baseline over the 15 judged skills with referee-two, referee-three and five native substitutes: all 15 digests current, 8 skills meet the bar, 7 do not.**

## Performance

- **Tasks:** 3 (Task 3 is the orchestrator checkpoint, resumed with "lanes done")
- **Lane window:** external lanes ended 15:44, native substitutes ingested by 15:51 (local)
- **Tracked files changed:** none. HEAD c5c77d3 before and after the run.

## Judges

- Built from `.planning/config.json` `review.reviewer_instances` in the rails' order: `opencode:router-env/my-referee-two`, then `opencode:router-env/my-referee-three` (`tmp/p32/judge-run/judges.json`).
- referee-one is left out: owner-stated unavailable.
- Native id: `native:opus-xhigh`.

## Probes

Sentinel probe (`judge_loop.py prompt --probe`, full package, through `cross-ai.mjs --mode review`):

- referee-two: `status=ok exit=0 cli_rc=0 elapsed=10s out=689 tree=clean`. Answer matched the `token` file exactly. Usable.
- referee-three: `status=ok exit=0 cli_rc=0 elapsed=7s out=689 tree=clean`. Answer matched exactly. Usable.
- Pool: both judges. No pool-level substitute was needed.

## Effort environment (names only, recorded before the native lanes ran)

- `CLAUDE_CODE_EFFORT_LEVEL`: unset
- `CLAUDE_CODE_SUBAGENT_EFFORT`: unset
- `CLAUDE_CODE_AUTO_COMPACT_WINDOW`: unset

## Judge count (jev on)

- 13 skills, count 2, deterministic:
  - no rubric-v4 verdict (8): ai-kit-spec-review-fixer, ai-kit-usage-metrics, cst-refactor, markdown-to-pdf, ai-kit-spec-review, ai-kit-spec-review-checklist, ai-kit-cross-ai, ai-kit-session-wake
  - last percent within 7.0 of the 80 pass mark (5): jev-fast-decision (85.6), ai-kit-spec-config (77.6), ai-kit-spec-execute (80.8, one high), ai-kit-spec-execute-superpowers (83.2), ai-kit-gsd-curated-config (84.0, one high)
- 2 skills, count 1:
  - ai-kit-gsd-spec-discuss (last 88.0, no critical or high): no deterministic trigger, jev asked, `needs_fallback`, deterministic count kept.
  - ai-kit-spec-goal-prompt (last 88.8, no critical or high): same.

**jev calls in this plan:** 2 (one judge-count score item each, for ai-kit-gsd-spec-discuss and ai-kit-spec-goal-prompt). Both returned `needs_fallback`, so the deterministic count was kept. No other skill asked jev.

## Lanes (final state: 28 external, 5 native)

External: 23 ok, 5 failed.

- ai-kit-spec-review-fixer (2): referee-two ok, referee-three ok
- ai-kit-usage-metrics (2): ok, ok
- cst-refactor (2): ok, ok
- jev-fast-decision (2): ok, ok
- markdown-to-pdf (2): referee-two ok; referee-three failed (ingest refused), native substitute
- ai-kit-spec-config (2): ok, ok
- ai-kit-spec-execute (2): ok, ok
- ai-kit-spec-review (2): ok, ok
- ai-kit-spec-review-checklist (2): referee-two failed (ingest refused), native substitute; referee-three ok
- ai-kit-cross-ai (2): ok, ok
- ai-kit-session-wake (2): referee-two ok; referee-three failed (ingest refused), native substitute
- ai-kit-spec-execute-superpowers (2): referee-two failed (ingest refused), native substitute; referee-three ok
- ai-kit-gsd-curated-config (2): ok, ok
- ai-kit-gsd-spec-discuss (1): referee-two failed (ingest refused), native substitute
- ai-kit-spec-goal-prompt (1): referee-two ok

Failure reasons, as recorded:

- The two referee-three lanes (markdown-to-pdf, ai-kit-session-wake) wrote a verdict whose judge id carried a U+200D zero-width joiner (`o\u200dpencode:...`). Ingest refused it. The joiner appears in `lane.out` of those two lanes only; no `prompt.md` contains it. Refused verdicts leave no record, so the failure lives in the lane `state`.
- The three referee-two lanes passed the runner (`status=ok`, `tree=clean`) but ingest recorded the attempt without a verdict: ai-kit-spec-review-checklist ("finding D5-1 line 156 is beyond the file's 150 lines"), ai-kit-spec-execute-superpowers and ai-kit-gsd-spec-discuss ("D3 is below its max but has no finding"). The reasons are in each record's `attempts[].error`.

## Native substitutes (5)

Each has `substitute.json` (`replaces`, `reason`) and a verdict ingested with the note `native, xhigh (frontmatter, documented; not observed)`. The `reason` field holds the lane state text: the ingest error for the two ZWJ lanes, the status line for the three validation lanes.

- markdown-to-pdf replaces referee-three (ZWJ refusal). Native 71.2 C, two high.
- ai-kit-session-wake replaces referee-three (ZWJ refusal). Native 81.6 B.
- ai-kit-spec-review-checklist replaces referee-two (line beyond file). Native 74.4 C, no high.
- ai-kit-spec-execute-superpowers replaces referee-two (D3 with no finding). Native 86.4 B.
- ai-kit-gsd-spec-discuss replaces referee-two (D3 with no finding). Native 84.8 B.

Skills marked `second judge unavailable`: none. The marker string appears only in `lanes.py` source, not in any record or log.

## Check (`tools/judge_loop.py check`, judges referee-two, referee-three, native)

Run through `tmp/auto/p32-exec/check-staging.sh`:

```
ai-kit-spec-review-fixer: loop 32 round 1 (rounds 1); judges opencode:router-env/my-referee-two, opencode:router-env/my-referee-three; worst 75.2 C; critical 0; high 1; bar not met; digest current
ai-kit-usage-metrics: loop 32 round 1 (rounds 1); judges opencode:router-env/my-referee-two, opencode:router-env/my-referee-three; worst 72.0 C; critical 0; high 1; bar not met; digest current
cst-refactor: loop 32 round 1 (rounds 1); judges opencode:router-env/my-referee-two, opencode:router-env/my-referee-three; worst 72.8 C; critical 0; high 1; bar not met; digest current
jev-fast-decision: loop 32 round 1 (rounds 1); judges opencode:router-env/my-referee-two, opencode:router-env/my-referee-three; worst 87.2 B; critical 0; high 0; bar met: no critical or high finding; digest current
markdown-to-pdf: loop 32 round 1 (rounds 1); judges opencode:router-env/my-referee-two, native:opus-xhigh; worst 71.2 C; critical 0; high 2; bar not met; digest current
ai-kit-spec-config: loop 32 round 1 (rounds 1); judges opencode:router-env/my-referee-two, opencode:router-env/my-referee-three; worst 79.2 C; critical 0; high 0; bar met: no critical or high finding; digest current
ai-kit-spec-execute: loop 32 round 1 (rounds 1); judges opencode:router-env/my-referee-two, opencode:router-env/my-referee-three; worst 85.6 B; critical 0; high 1; bar met: grade B or better; digest current
ai-kit-spec-review: loop 32 round 1 (rounds 1); judges opencode:router-env/my-referee-two, opencode:router-env/my-referee-three; worst 75.2 C; critical 0; high 2; bar not met; digest current
ai-kit-spec-review-checklist: loop 32 round 1 (rounds 1); judges opencode:router-env/my-referee-three, native:opus-xhigh; worst 75.2 C; critical 0; high 2; bar not met; digest current
ai-kit-cross-ai: loop 32 round 1 (rounds 1); judges opencode:router-env/my-referee-two, opencode:router-env/my-referee-three; worst 76.8 C; critical 0; high 1; bar not met; digest current
ai-kit-session-wake: loop 32 round 1 (rounds 1); judges opencode:router-env/my-referee-two, native:opus-xhigh; worst 87.2 B; critical 0; high 1; bar met: grade B or better; digest current
ai-kit-spec-execute-superpowers: loop 32 round 1 (rounds 1); judges opencode:router-env/my-referee-three, native:opus-xhigh; worst 86.4 B; critical 0; high 0; bar met: no critical or high finding; digest current
ai-kit-gsd-curated-config: loop 32 round 1 (rounds 1); judges opencode:router-env/my-referee-two, opencode:router-env/my-referee-three; worst 82.4 B; critical 0; high 0; bar met: no critical or high finding; digest current
ai-kit-gsd-spec-discuss: loop 32 round 1 (rounds 1); judges native:opus-xhigh; worst 84.8 B; critical 0; high 0; bar met: no critical or high finding; digest current
ai-kit-spec-goal-prompt: loop 32 round 1 (rounds 1); judges opencode:router-env/my-referee-two; worst 92.8 A; critical 0; high 0; bar met: no critical or high finding; digest current
judge-loop: REJUDGE.md not found; run: python3 tools/judge_loop.py report <records>
check exit=1
```

- Digests: 15 of 15 current.
- Bar: 8 met (jev-fast-decision, ai-kit-spec-config, ai-kit-spec-execute, ai-kit-session-wake, ai-kit-spec-execute-superpowers, ai-kit-gsd-curated-config, ai-kit-gsd-spec-discuss, ai-kit-spec-goal-prompt); 7 not met (ai-kit-spec-review-fixer, ai-kit-usage-metrics, cst-refactor, markdown-to-pdf, ai-kit-spec-review, ai-kit-spec-review-checklist, ai-kit-cross-ai).
- Exit 1 is expected: the only problem is the missing `REJUDGE.md`, which 32-09 writes.
- Reading the `worst` figure: the check picks the lowest bar rank first, then the lowest percent. So ai-kit-spec-review-checklist shows referee-three (75.2, not met, two high) over the native verdict (74.4, no high). ai-kit-session-wake shows referee-two (87.2, one high) over the native verdict (81.6, no high).

## Verification

- `lanes.py status`: last line `all lanes ended`. Summary lines: `external lanes: 23 ok, 5 failed, 0 pending`, `native lanes: 0 waiting, 5 ingested`. Both workers (pids 3601346, 3601347) are dead.
- `git status --porcelain --untracked-files=no`: empty. `git rev-parse HEAD` equals `tmp/p32/judge-run/head.txt` (c5c77d3).
- Records read for all 15 skills: `verdicts/32/<skill>/r1/` holds one record per external lane that ingested, and one per native lane.
- `scope.py close`: NOT clean (exit 1). Leftovers, none started by the judge workers:
  - pid 4045227, `bash tmp/auto/p32-exec/wait-file.sh`, the orchestrator's file waiter, with its `sleep 10` children (latest pid 4067299);
  - pid 4068485, `sleep 3` with cwd `tmp/compact-291`, another session's process;
  - pid 4045224, a bash wrapper with cwd in the checkout.
  Not killed: these belong to the orchestrator and another session. `close` also stopped before removing its run directory under `tmp/p32/08/`. Reported, not removed.
- `scope.py close`, re-run by the orchestrator after its waiters ended: still exit 1, with two leftovers that this run did not start. The first is pid 3593974, `codegraph serve --mcp`, cwd the checkout, started 15:20:10. It is a child of the long-running `opencode serve --service` (pid 1323552, started 2026-10-28), which spawned it when the referee lanes ran through that service; an earlier run left the same kind of child (pid 2888315, reported). The second is a `sleep 3` from another session's loop in `tmp/compact-291`. Decision (jev typesafe `a`, 1.0; ledger): leave both running and record the check as not clean, because neither process belongs to this run. The judge workers have exited, which is what the check is meant to prove.
- Root pin: `root pin ok` before the first write and again before the commit.

## Deviations from Plan

1. **Task 3 step 1 (native reply save):** the orchestrator saved each native reply with `tmp/auto/p32-exec/extract-reply.py` (the agent's last assistant message from its host transcript), not with the Write tool. The notification view escapes `<` as `&lt;`, and the replies contain `<`. All five `lane.out` files are non-empty and were ingested.
2. **Task 2 (`assign.json`):** written in batch order without key sorting. Fixed before `assign` ran.
3. **Ordering:** `natives` ran while external lanes were still running. It touches only native lane dirs, so the native lanes started earlier.
4. **`state.begin-phase`:** not re-run at dispatch. A STATE write would break the clean-tree precondition and D-09.

## Requirements

- **JDG-06:** met for this run. The count is recorded per skill from the recorded inputs before any lane prompt was built, with jev asked where the deterministic rule was silent.
- **JDG-01:** not marked. Its report (`REJUDGE.md`) is written by 32-09. The judges, probes and verdicts it needs are in place.

## Self-Check: PASSED

- All 15 skills have verdict records; `check` reads 15 digests as current.
- HEAD and the tracked tree are unchanged since the run started.
