---
phase: 29-logical-commit-folding-and-the-shared-jev-ladder
plan: 05
subsystem: testing
tags: [skill-judge, judge-baseline, pi, router-env, judge-lanes]

requires:
  - phase: 29-logical-commit-folding-and-the-shared-jev-ladder
    provides: plan 29-01 start snapshot and close check (the scope.py spec this run follows)
provides:
  - Referee-one new-rubric baselines for the four SKILL.md files this phase changes, on their unchanged base text
  - Tracked judge procedure (prepare.sh, run_lane.sh, parse.py, prompt-base.txt) that plan 29-16 reruns
  - Lane record: referee-two and referee-three both blocked by a router-side model outage, recorded as a human verification item
affects: [29-16]

actuals:
  tokens: 3046   # chars/4 over the 5 files changed (12183 chars)
  tasks: 2
  commits: 2     # measured: git rev-list --count 358113ad..HEAD before this summary commit

tech-stack:
  added: []
  patterns:
    - "judge lanes run through pi and the project cross-AI runner, outputs under gitignored tmp/p29/judge/"
    - "verdicts parsed by a stdlib script; a lane with no valid verdict is recorded, never skipped"

key-files:
  created:
    - .planning/phases/29-logical-commit-folding-and-the-shared-jev-ladder/29-JUDGE.md
    - .planning/phases/29-logical-commit-folding-and-the-shared-jev-ladder/judge/prepare.sh
    - .planning/phases/29-logical-commit-folding-and-the-shared-jev-ladder/judge/run_lane.sh
    - .planning/phases/29-logical-commit-folding-and-the-shared-jev-ladder/judge/parse.py
    - .planning/phases/29-logical-commit-folding-and-the-shared-jev-ladder/judge/prompt-base.txt
  modified: []

key-decisions:
  - "Baseline base commit is 10d4d153 (the commit that added plan 29-01); the four skills are judged at that text, not at HEAD"
  - "Referee-two's transient-looking failure was not retried past run 1: the orchestrator ruled it the known outage; the queued run 2 was cancelled"
  - "Referee-three probed once as the replacement lane; it failed with the same outage, so no second-judge rows exist"

patterns-established:
  - "Judge scripts and prompt are tracked; only run outputs go to tmp/p29/judge/"

requirements-completed: [FLOW-01, JEV-06]

coverage: []

duration: not measured
completed: 2026-11-04
status: complete
---

# Phase 29 Plan 05: Judge baselines for the four changed skills (referee-one only)

**Referee-one new-rubric baselines (rubric v4) for jev-fast-decision, ai-kit-gsd-spec-discuss, ai-kit-spec-execute-superpowers and ai-kit-spec-goal-prompt on their unchanged base text; the second-judge baselines are blocked by a router-side model outage and recorded as a human verification item**

## Performance

- **Tasks:** 2 of 2 executed
- **Commits:** 2 (plus this summary commit)
- **Files:** 5 created, 0 modified (plus this summary)

## Accomplishments

- Extracted the unchanged base text of the four skills and the named tests from base commit `10d4d153d327f4ab74fc159ca05b1f089ead5cef` into gitignored `tmp/p29/judge/base/`, and copied the installed skill-judge read-only.
- Ran the referee-one lane once (status ok, 1476 s): four verdicts parsed. Scores: jev-fast-decision 115/125 (92.0, A, 0 critical, 0 high); ai-kit-gsd-spec-discuss 112/125 (89.6, B, 0, 0); ai-kit-spec-execute-superpowers 112/125 (89.6, B, 0, 0); ai-kit-spec-goal-prompt 112/125 (89.6, B, 0 critical, 2 high).
- Recorded the procedure, the tracked scripts and the lane status in `29-JUDGE.md`.
- Referee-two failed on its first run and was cancelled before any retry (see Deviations). Referee-three, the plan's replacement lane, also failed on its one probe. Both lanes returned the same router-side 503 (`Model anthropic/claude-opus-5-5-xhigh is unavailable`).

## Task Commits

1. **Task 1: referee-one baselines, procedure and scripts** - `70e9259` (docs)
2. **Task 2: referee-two lane record and Pending section** - `c27bc18` (docs)

## Files Created/Modified

- `.planning/phases/29-logical-commit-folding-and-the-shared-jev-ladder/29-JUDGE.md` - procedure, base sha, referee-one baseline rows, lane status, Pending section
- `.planning/phases/29-logical-commit-folding-and-the-shared-jev-ladder/judge/prepare.sh` - extracts base text and copies skill-judge
- `.planning/phases/29-logical-commit-folding-and-the-shared-jev-ladder/judge/run_lane.sh` - one judge lane through pi and cross-ai.mjs
- `.planning/phases/29-logical-commit-folding-and-the-shared-jev-ladder/judge/parse.py` - verdict parser and Markdown rows
- `.planning/phases/29-logical-commit-folding-and-the-shared-jev-ladder/judge/prompt-base.txt` - judge prompt for the baseline round

## Decisions Made

- The base commit is the one that added plan 29-01 (`10d4d153`), so the baseline is the unchanged text even though other wave-1 plans may have edited the SKILL.md files on the branch.
- The referee-one baseline is the only judge row set; no other model or native judging was used.

## Deviations from Plan

### Lane-level deviations

**1. [Lane outage - referee-two and referee-three] Second-judge baselines not obtained**
- **Found during:** Task 2
- **Issue:** Referee-two run 1 returned `status=transient ... rule=omniroute-model-unavailable ... exit=75 ... retry_after_s=600`. Referee-three's single probe returned the same status.
- **Fix:** Referee-two's queued run 2 (after the advised 600 s wait) was cancelled on the orchestrator's ruling that this is the known outage, not a transient blip; the job's process group was terminated. Referee-three was probed once as the replacement. No other model was used. The missing rows are under `## Pending` in `29-JUDGE.md`.
- **Files modified:** `29-JUDGE.md`
- **Verification:** lane status lines and the runner's 503 message recorded verbatim in `29-JUDGE.md`; run outputs kept in `tmp/p29/judge/`.
- **Committed in:** `c27bc18`

**Total deviations:** 1 lane-level (second-judge baselines blocked). Impact: 4 of 8 planned baseline rows exist; plan 29-16 must take the referee-two or referee-three baselines before judging the new text (human verification item).

## Auto-fixed Issues

None.

## Issues Encountered

- Several compound git and python invocations were refused by the worktree guard (the command named git or a runtime-computed `$HOME` in a form it could not verify). Each check was split into a plain command.
- The first referee-two run wrote its runner message only to stderr; the status line is the last stderr line, as parse expects.

## Judge Calls (jev-fast-decision)

- **c1** (choice, transient referee-two failure): answer `a` (wait about 600 s, rerun the same command), confidence 0.61, `needs_fallback: true`, backend typesafe (laya trail answered `b`, confidence 0.07). Action: I decided option a, then the orchestrator's ruling overrode the rerun (outage, not transient) and I cancelled run 2 and probed referee-three once.
- **f1** (yes/no, failure is transient, not quota or auth): answer `supported`, confidence 0.63, `needs_fallback: true`, backend typesafe (laya answered `partial`, confidence 0.02). Action: I classified it as transient at first, then the orchestrator's outage ruling superseded that classification.
- Both answers were advisory with `needs_fallback: true`; I decided on the lane rules and the orchestrator's ruling, not on the jev answers.

## Self-Check

- Commits present: `70e9259` (Task 1), `c27bc18` (Task 2): FOUND both.
- Files present: `29-JUDGE.md` and the four `judge/` files: FOUND.
- Baseline rows in `29-JUDGE.md`: 4 (one per skill, referee-one): FOUND.
- `make test` (via `tmp/p29/05/scope.py test`): exit 0, no `failed:` lines.
- `scope.py close`: run after this summary's commit (the plan's `<verification>` step); its result is in the completion reply.

## Self-Check: PASSED

## Next Phase Readiness

- Plan 29-16 must take a second-judge baseline (referee-two or referee-three) for the four skills before it judges the changed text; the `## Pending` section of `29-JUDGE.md` names the rows and the human verification item.
- The judge scripts are tracked and reproducible in any checkout: `bash .planning/phases/29-logical-commit-folding-and-the-shared-jev-ladder/judge/prepare.sh`, then `run_lane.sh <referee> base`, then `parse.py base <referee> <skills>`.

---
*Phase: 29 plan 05*
*Completed: 2026-11-04*
