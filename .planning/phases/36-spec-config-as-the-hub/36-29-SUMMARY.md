---
phase: 36-spec-config-as-the-hub
plan: 29
subsystem: judge
tags: [skill-judge, loop-36, jdg-04, referee-one, referee-two]

requires: [36-01, 36-02, 36-03, 36-04, 36-05, 36-06, 36-07, 36-08, 36-09, 36-10, 36-11, 36-12, 36-13, 36-14, 36-15, 36-16, 36-17, 36-18, 36-19, 36-20, 36-21, 36-22, 36-23, 36-24, 36-25, 36-26, 36-27, 36-28]
provides:
  - "Loop 36 records for ai-kit-spec-config (round 1), ai-kit-spec-execute-superpowers (round 1) and ai-kit-spec-review (rounds 1 and 2), judged by referee-one and referee-two only; REJUDGE.md regenerated"
  - "All three skills meet the bar with no regression; ai-kit-spec-review reaches it for the first time (prior base 75.2, grade C), and its inputs.json `deferred` entry is removed"
  - "Four fix commits under the fix rule (1 to 3 findings per skill), each with its fixes.md"

key-files:
  modified:
    - .planning/judge/REJUDGE.md
    - .planning/judge/facts.json
    - .planning/judge/inputs.json
    - .planning/judge/loops/36.json
    - .planning/judge/verdicts/36/
    - skills/ai-kit-spec-config/SKILL.md
    - skills/ai-kit-spec-config/references/check-only.md
    - skills/ai-kit-spec-config/references/wizard-flow.md
    - skills/ai-kit-spec-execute-superpowers/SKILL.md
    - skills/ai-kit-spec-execute-superpowers/references/design-notes.md
    - skills/ai-kit-spec-review/SKILL.md
    - skills/ai-kit-spec-review/references/cross-ai-dispatch.md
    - skills/ai-kit-spec-review/references/loop-diagram.md
    - skills/ai-kit-spec-review/evals/evals.json
    - tests/test_spec_chain_text.py

requirements-completed: [HUB-01, HUB-05, HUB-07, HUB-10]

executor: "orchestrator action in the main checkout (cross_ai false); judge lanes opencode router-env/my-referee-one and router-env/my-referee-two through the project runner, review mode"
---

# Phase 36 Plan 29: Loop 36 skill-judge loop

Commits (pre-fold): round 1 records `26690ab`; round 1 fixes `81ae282` (ai-kit-spec-config), `4a968ed` (ai-kit-spec-execute-superpowers), `346ed13` (ai-kit-spec-review, before round 2); round 2 records `37cc58a`; round 2 fix `7e2539d` (ai-kit-spec-review).

Judged set from git (`tmp/judge-36/judged.py`): base `88440fc^`, changed and judged ai-kit-spec-config, ai-kit-spec-execute-superpowers, ai-kit-spec-review; no fact-only skill. Pool: referee-one and referee-two (opencode), no native judge, no referee-three; count 2 per skill; pool check before and after ok in both rounds.

## Loop 36 bar results

| Skill | Round | Worst percent (report column) | Grade | Bar | Findings (crit+imp+high) | decide.py row |
|---|---|---|---|---|---|---|
| ai-kit-spec-config | 1 | 88.8 | B | met | 3 | fix -> 81ae282 |
| ai-kit-spec-execute-superpowers | 1 | 87.2 | B | met | 3 | fix -> 4a968ed |
| ai-kit-spec-review | 1 | 92.0 | A | met | 4 | next-round (met, n > 3, r = 1); fixed before round 2 in 346ed13 |
| ai-kit-spec-review | 2 | 92.8 | A | met | 3 | fix -> 7e2539d |

The report's worst column holds the higher percent for ai-kit-spec-review; the lowest valid percent is in the `regression.py` lines.

`regression.py` results (round 1 values as recorded in the round 1 notes; the round 2 line quoted):

- round 1: ai-kit-spec-config lowest 88.8, loop 35 base 88.0, delta +0.8, regression: no
- round 1: ai-kit-spec-execute-superpowers lowest 87.2, loop 32 base 86.4, delta +0.8, regression: no
- round 1: ai-kit-spec-review lowest 90.4, loop 32 base 75.2, delta +15.2, regression: no
- round 2: `ai-kit-spec-review: lowest 83.2 (2 valid, 0 invalid), loop 32 r1 base 75.2, delta +8.0, regression: no`

The bases match the expected ones (88.0 loop 35, 86.4 loop 32, 75.2 loop 32). Note for the owner: ai-kit-spec-review's round 2 lowest (83.2, referee-two) is 7.2 points under its round 1 lowest (90.4); the regression rule compares against the prior loop, not the prior round, so it is not a regression by the rule.

Round 1 findings fixed (one fixes.md per skill and round under `.planning/judge/verdicts/36/<skill>/r<N>/`):

- ai-kit-spec-config (81ae282): probe cwd claim, load condition for `references/cli-model-selection.md`, two-call effort probe vs usability record.
- ai-kit-spec-execute-superpowers (4a968ed): codex confinement claim qualified, FOLD_BASE and UNIT_FLOW cleared once the fold finishes, FIX_ROUND increment guarded as new-round-only.
- ai-kit-spec-review (346ed13, before round 2, the orchestrator's choice instead of a gap plan): D5-1 SKILL.md 511 -> 479 lines (duplicated or branch-only detail kept only in its existing reference); D8-1 revisions run only when the request authorizes them, otherwise findings are surfaced and the user is asked first (pinned in `tests/test_spec_chain_text.py`); D8-2 the outside-a-repository branch asks for a grounding directory or stops, and says the read-only contract is unverified outside git; D8-3 the single-reviewer message names no report path on approval.

Round 2 findings fixed (7e2539d): D8-1 every document's toplevel is resolved and compared; D8-2 the pending-lane resume file records and restores `revisions_authorized`; D8-3 `detect-tools` runs only when `ai-kit-spec.py` exists.

## Loop 36 facts for the verifier

- Judges: referee-one `opencode:router-env/my-referee-one` configured; referee-two `opencode:router-env/my-referee-two` configured. Probes both usable (`AIKIT-XAI status=ok ... exit=0`, 11 s and 19 s).
- Round 1 lanes (6): all `AIKIT-XAI status=ok cli=opencode exit=0 cli_rc=0 tree=clean attempts=1 cycles=0`; spec-config 91 s / 71 s, spec-review 42 s / 79 s, spec-execute-superpowers 65 s / 86 s (referee-one / referee-two).
- Round 2 lanes: referee-one `AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-one exit=0 elapsed=40s tree=clean`. referee-two first run `AIKIT-XAI status=ok ... exit=0 elapsed=90s tree=clean`, verdict rejected by ingest (`D1 is below its max but has no finding`, record verdict null; ledger line in `tmp/judge-36/ledger.md`). Orchestrator decision: re-run only that lane, same CLI, provider and model, new session, up to 3 fresh attempts. Fresh attempt 1 (rejected record and lane outputs moved to `tmp/judge-36/rejected/r2-attempt1/`, worker started through lanes.py's own spawn by `tmp/judge-36/relaunch_one.py`): `AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 elapsed=98s out=317484 tree=clean attempts=1 cycles=0`, dict verdict 83.2 B. No substitute judge was started.
- `verdict_facts.py` verdicts: spec-config r1 91.2 A (2 high) and 88.8 B (1 high); spec-execute-superpowers r1 93.6 A (2 high) and 87.2 B (1 high); spec-review r1 92.0 A (4 high) and 90.4 A (0); spec-review r2 92.8 A (3 high) and 83.2 B (0); no critical, no substitute.
- `check.py` (`--require-current`) exit 0 before any fix commit in both rounds.
- Closing `AI_KIT_REFUSE_REAL_HOME=1 python3 tools/judge_loop.py check .planning/judge`: exit 0 after round 1 and again after the round 2 fix commit; each of the three skills has its `: loop 36` line (spec-config round 1, spec-execute-superpowers round 1, spec-review round 2, all `bar met`); notes: `stale digest` for the three judged skills by design after their fix commits, plus the seven skills stale before the loop; no facts-drift line. `stale_after.py` re-run after the final fix commit exits 1 naming ai-kit-spec-review as judged and stale, which is that fix commit's intended effect (the plan runs it only before a fix commit, where it printed `stale ok`).
- `make check-dogfood`: `check-dogfood: ok` (rounds 1 and 2, before each records commit).
- `stale_after.py`: `stale ok` (rounds 1 and 2, before the fix commits).
- `evals_gate.py`: `evals gate: ok` (each skill has an evals.json case; the scratch skill without evals fails as designed).
- `clear_deferred.py`: round 1 `deferred cleared` (ai-kit-spec-review's latest bar met; report and check.py re-run, exit 0); round 2 `deferred already absent`.
- `decide.py --self-check`: `decide self-check: ok`.

## Stale-digest notes

- Stale before the loop (carried, not judged here): ai-kit-cross-ai, ai-kit-gsd-curated-config, ai-kit-gsd-spec-discuss, ai-kit-session-wake, ai-kit-spec-review-checklist, ai-kit-usage-metrics, jev-fast-decision (the stale-before set also named the three judged skills, which the loop re-judged).
- Stale by design after their fix commits (`tmp/judge-36/intentional-stale.txt`): ai-kit-spec-config, ai-kit-spec-execute-superpowers, ai-kit-spec-review. `report` was not re-run after a fix commit; the stale-digest and facts-drift notes stay until each skill's next loop.

`bar-results.json`:

- `bar ai-kit-spec-config: met (round 1)`
- `bar ai-kit-spec-execute-superpowers: met (round 1)`
- `bar ai-kit-spec-review: met (round 2)`

## Mtime check of the listed paths

`mtime check of the listed paths: unchanged` (round 1 after its lanes; round 2 after its lanes and again after the referee-two re-run; snapshot of 5 present files taken in round 1).

## Deviations and notes

- The ai-kit-spec-review round 1 fix ran before round 2 as one fix commit decided by the orchestrator, not through a separate gap plan; it holds only the skill's files, the pinning test and `r1/fixes.md`.
- The D8-1 fix also changed the loop diagram (which resolved referee-two's medium round 1 finding on a false edge) and two eval prompts that did not ask for a fix; medium and low findings were otherwise not changed.
- The rejected referee-two lane of round 2 was re-run under the orchestrator's decision (same judge, new session); lanes.py has no single-lane relaunch, so `relaunch_one.py` moved the rejected staged record aside and started that judge's worker only.
- Processes: probe pgids 4110510 and 4110522, lane pgids 4114465, 4114467 (round 1), 170912, 170913 (round 2) and 185203 (referee-two re-run), all ended (`tmp/run-2026-11-19/pgids.txt`).
