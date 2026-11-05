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
