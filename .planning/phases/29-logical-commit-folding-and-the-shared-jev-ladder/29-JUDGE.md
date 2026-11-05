# Phase 29 judge record

## Procedure

- Base commit: `10d4d153d327f4ab74fc159ca05b1f089ead5cef` (the commit that added plan 29-01; `judge/prepare.sh` resolves it and writes `tmp/p29/judge/base.sha`).
- Rubric: skill-judge rubric version 4, spec_sha `69ef37e9424c0a7ea9dd2293b559e43ec8176379` (from the verdicts).
- Skills judged at their unchanged base text: `jev-fast-decision`, `ai-kit-gsd-spec-discuss`, `ai-kit-spec-execute-superpowers`, `ai-kit-spec-goal-prompt`.
- Lane command shape (`judge/run_lane.sh <referee> <round>`): `gsd-tools run-with-timeout 3600 -- node .planning/scripts/cross-ai.mjs --runtime pi --model router-env/<referee> --route-pi router --mode review --outer-timeout 3600`, prompt from `judge/prompt-<round>.txt`, outputs in `tmp/p29/judge/<round>-<referee>.{prompt,out,err}` (gitignored).
- Verdict parsing: `judge/parse.py <round> <referee> <skill>...` prints one row per skill and the lane's last `AIKIT-XAI` status line; it exits 1 when a listed skill has no valid verdict.
- The bar for each judged edit: no critical or high finding, grade B or better, and no regression beyond judge variation, taken as 7 percentage points for the same judge (measured noise of about 8 points on the old /120 scale; the old scores are not comparable to the percent bands of rubric v4).
- Lanes: router-env `my-referee-one` and `my-referee-two` through pi; `my-referee-three` only replaces a lane that fails (quota or auth stops that lane and is recorded).

## Baselines (base commit 10d4d153d327f4ab74fc159ca05b1f089ead5cef)

| Skill | Judge | Score | Percent | Grade | Critical | High |
| --- | --- | --- | --- | --- | --- | --- |
| jev-fast-decision | my-referee-one | 115/125 | 92.0 | A | 0 | 0 |
| ai-kit-gsd-spec-discuss | my-referee-one | 112/125 | 89.6 | B | 0 | 0 |
| ai-kit-spec-execute-superpowers | my-referee-one | 112/125 | 89.6 | B | 0 | 0 |
| ai-kit-spec-goal-prompt | my-referee-one | 112/125 | 89.6 | B | 0 | 2 |

Referee-one high findings on the unchanged `ai-kit-spec-goal-prompt` text (baseline facts, to be re-checked by plan 29-16):
- D6-1: every rendered work family tells the agent to merge the working branch and to archive and remove intermediate worktrees, with no ownership, clean-tree or authorization gate (`scripts/gp_sections.py` line 369).
- D8-2: `loop_block()` emits `/loop` syntax for the CronCreate and ScheduleWakeup strategies too, so the emitted syntax can be unverified while the label names the scheduling tool (`scripts/gp_sections.py` line 279).

## Lane status

- `my-referee-one`, round `base`: `AIKIT-XAI status=ok cli=pi model=router-env/my-referee-one exit=0 cli_rc=0 elapsed=1476s out=11549 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0`; run count 1; all four verdicts parsed.
- `my-referee-two`, round `base`: run 1 `AIKIT-XAI status=transient cli=pi model=router-env/my-referee-two exit=75 cli_rc=1 elapsed=200s out=0 tree=clean action=stop route=router rule=omniroute-model-unavailable pattern=verified attempts=12 cycles=0 retry_after_s=600 cycle=0`, `lane-exit=75`; the runner's message: `503: {"message":"Model anthropic/claude-opus-5-5-xhigh is unavailable","type":"server_error","code":"service_unavailable"}`. Run count 1. A queued run 2 (after the advised 600 s wait) was cancelled before it started, on the orchestrator's ruling that this is the referee-two outage, not a transient failure; no verdicts. Run 1 outputs kept as `tmp/p29/judge/base-my-referee-two.run1.{out,err}`.
- `my-referee-three`, round `base` (replacement for referee-two, probed once): `AIKIT-XAI status=transient cli=pi model=router-env/my-referee-three exit=75 cli_rc=1 elapsed=202s out=0 tree=clean action=stop route=router rule=omniroute-model-unavailable pattern=verified attempts=12 cycles=0 retry_after_s=600 cycle=0`, `lane-exit=75`; the runner's message: `503: {"message":"Model anthropic/claude-opus-5-5-xhigh is unavailable","type":"server_error","code":"service_unavailable"}`. Run count 1. Not retried; no verdicts.

## Pending

Human verification item: take this baseline before plan 29-16 judges the new text.

- Skill `jev-fast-decision`, lane `my-referee-two` (and replacement `my-referee-three`): last status `AIKIT-XAI status=transient ... rule=omniroute-model-unavailable ... exit=75`.
- Skill `ai-kit-gsd-spec-discuss`, lane `my-referee-two` (and replacement `my-referee-three`): same last status.
- Skill `ai-kit-spec-execute-superpowers`, lane `my-referee-two` (and replacement `my-referee-three`): same last status.
- Skill `ai-kit-spec-goal-prompt`, lane `my-referee-two` (and replacement `my-referee-three`): same last status.

The second-judge baselines are blocked by a router-side model outage on both referee-two and referee-three; no other model or native judging was used. The first-judge baselines (referee-one, table above) are complete.

## Final round 1

Plan 29-16 Task 1, on the final texts in the working tree (`judge/prompt-final1.txt`, tracked). Lanes launched in the background: `run_lane.sh my-referee-one final1` and `run_lane.sh my-referee-two final1` together, each probed once. Referee-three replaced the failed referee-two and was probed once. Owner rules applied: a quota failure stops that lane and is recorded, with no retry and no replacement; `omniroute-model-unavailable` is the known outage, recorded verbatim, with no 600 s retry.

Lane status (last `AIKIT-XAI` line of each run, verbatim from `tmp/p29/judge/final1-<referee>.err`; `attempts=12` on each run, `cycles=0`, `tree=clean`, `action=stop`):

- `my-referee-one`: `AIKIT-XAI status=quota cli=pi model=router-env/my-referee-one exit=75 cli_rc=1 elapsed=203s out=0 tree=clean action=stop route=router rule=omniroute-all-targets-skipped pattern=verified attempts=12 cycles=0 retry_after_s=600 cycle=0`; runner message `503: {"message":"Service temporarily unavailable: all targets were skipped by pre-dispatch filters (session 99% <redacted>)","type":"service_unavailable","code":"ALL_TARGETS_SKIPPED"}`. Not replaced: the quota failure stops the lane.
- `my-referee-two`: `AIKIT-XAI status=transient cli=pi model=router-env/my-referee-two exit=75 cli_rc=1 elapsed=201s out=0 tree=clean action=stop route=router rule=omniroute-model-unavailable pattern=verified attempts=12 cycles=0 retry_after_s=600 cycle=0`; runner message `503: {"message":"Model grok-cli/grok-4.7-xhigh is unavailable","type":"server_error","code":"service_unavailable"}`. Replaced by `my-referee-three`.
- `my-referee-three` (replacement for referee-two): `AIKIT-XAI status=transient cli=pi model=router-env/my-referee-three exit=75 cli_rc=1 elapsed=190s out=0 tree=clean action=stop route=router rule=omniroute-model-unavailable pattern=verified attempts=12 cycles=0 retry_after_s=600 cycle=0`; runner message `503: {"message":"Model anthropic/claude-opus-5-5-xhigh is unavailable","type":"server_error","code":"service_unavailable"}`.

Result: no valid verdict from any lane, so no score, percent, grade, critical or high count, and no delta exists for any row. `judge/compare.py final1 ...` printed ten `pending` rows and computed no pass or fail. Each row names its lane status and the replacement, as Task 1 requires.

| Skill | Judge | Score | Percent | Grade | Critical | High | Delta | Bar |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ai-kit-commit-fold | my-referee-one | - | - | - | - | - | none | pending: quota, lane stopped, no replacement |
| ai-kit-commit-fold | my-referee-two (replacement my-referee-three) | - | - | - | - | - | none | pending: model-unavailable on both |
| jev-fast-decision | my-referee-one | - | - | - | - | - | - | pending: quota, lane stopped, no replacement |
| jev-fast-decision | my-referee-two (replacement my-referee-three) | - | - | - | - | - | - | pending: model-unavailable on both |
| ai-kit-gsd-spec-discuss | my-referee-one | - | - | - | - | - | - | pending: quota, lane stopped, no replacement |
| ai-kit-gsd-spec-discuss | my-referee-two (replacement my-referee-three) | - | - | - | - | - | - | pending: model-unavailable on both |
| ai-kit-spec-execute-superpowers | my-referee-one | - | - | - | - | - | - | pending: quota, lane stopped, no replacement |
| ai-kit-spec-execute-superpowers | my-referee-two (replacement my-referee-three) | - | - | - | - | - | - | pending: model-unavailable on both |
| ai-kit-spec-goal-prompt | my-referee-one | - | - | - | - | - | - | pending: quota, lane stopped, no replacement |
| ai-kit-spec-goal-prompt | my-referee-two (replacement my-referee-three) | - | - | - | - | - | - | pending: model-unavailable on both |

Task 2 had no verdict findings to fix, so no round-2 or round-3 re-judge ran and no SKILL.md, `references/` or `evals/` file changed. Orchestrator direction (received mid-run): the native-opus-xhigh fallback is run by the orchestrator, not by this session; this session runs no native or haiku judging.

## Verdict

JDG-04 for the five skills is open: no judge produced a verdict in this run. Every skill is pending the native-opus-xhigh fallback, which the orchestrator runs. The orchestrator also decides the regression check, since a baseline from another judge is not comparable.

- ai-kit-commit-fold: pending: native-opus-xhigh fallback, run by the orchestrator (referee-one quota; referee-two and referee-three model-unavailable). No baseline exists for this skill.
- jev-fast-decision: pending: native-opus-xhigh fallback, run by the orchestrator (referee-one quota; referee-two and referee-three model-unavailable). Baseline: referee-one 92.0 (A), not comparable to a native-opus-xhigh judge.
- ai-kit-gsd-spec-discuss: pending: native-opus-xhigh fallback, run by the orchestrator (referee-one quota; referee-two and referee-three model-unavailable). Baseline: referee-one 89.6 (B), not comparable to a native-opus-xhigh judge.
- ai-kit-spec-execute-superpowers: pending: native-opus-xhigh fallback, run by the orchestrator (referee-one quota; referee-two and referee-three model-unavailable). Baseline: referee-one 89.6 (B), not comparable to a native-opus-xhigh judge.
- ai-kit-spec-goal-prompt: pending: native-opus-xhigh fallback, run by the orchestrator (referee-one quota; referee-two and referee-three model-unavailable). Baseline: referee-one 89.6 (B) with two high findings (D6-1, D8-2), not comparable to a native-opus-xhigh judge.

Human verification item (phase verification, JDG-04): run the native-opus-xhigh judge on the five final SKILL.md files, then record its verdicts here.

## Fallback verdicts (native-opus-xhigh, 2026-11-04)

Judge: `native-opus-xhigh`, the owner's standing fallback when the referees are down (rule of 2026-11-02).
Fallback reason: referee-one quota stop (503, all targets skipped, session 99%); referee-two
`grok-cli/grok-4.7-xhigh` unavailable; referee-three `anthropic/claude-opus-5-5-xhigh` unavailable.
Rubric version 4, spec_sha `69ef37e9424c0a7ea9dd2293b559e43ec8176379`. Raw verdicts: `tmp/judge-fallback-29/`
(round 1 at 3410359) and `tmp/judge-fallback-29/round2/` (round 2 at d2855bc), gitignored.

Referee-one baselines are from another judge and are not compared; round 2 deltas are against round 1 of
the same judge.

| Skill | Round 1 | Round 2 | Delta | Critical / high | Bar |
|---|---|---|---|---|---|
| ai-kit-commit-fold | 104/125, 83.2 B | 103/125, 82.4 B | -1 | 0 / 0 | pass |
| jev-fast-decision | 107/125, 85.6 B | not re-judged (unchanged) | - | 0 / 0 | pass |
| ai-kit-gsd-spec-discuss | 111/125, 88.8 B | not re-judged (unchanged) | - | 0 / 0 | pass |
| ai-kit-spec-execute-superpowers | 104/125, 83.2 B | not re-judged (unchanged) | - | 0 / 0 | pass |
| ai-kit-spec-goal-prompt | 107/125, 85.6 B, 2 high | 111/125, 88.8 B | +4 | 0 / 0 | pass |

Round 1 high findings on ai-kit-spec-goal-prompt, both resolved in round 2: D6-1 cleanup acted on any
worktree (fixed 21a908d); D8-2 `/loop` labelled with a schedule tool's availability (fixed 844286f).

Open medium findings (non-blocking, follow-up):
- goal-prompt D6-2: "directories of work items finished in this run" and "remove this worktree last" are
  still loosely scoped.
- goal-prompt D8-3: no rule tells the run to write the run ledger it relies on, or names its file.
- commit-fold D8-3: "check the PR yourself" is reachable only from a refusal row the gsd and superpowers
  forms never produce; D8-4 (low): a root commit is refused as `foreign_merge`, which the table describes
  as a merge.

JDG-04 verdict: met for all five skills (no critical or high finding, grade B or better, no regression
beyond 7 points for the same judge).
