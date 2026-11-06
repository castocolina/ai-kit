# Phase 30 skill judge set (plan 30-06)

Judge: `native-opus-xhigh`, run by the orchestrator. The referees were down at plan time (2026-11-05).
The executor of plan 30-06 prepared this file and did not run the judge.

Procedure: the orchestrator runs the native opus xhigh judge on each file below after plan 30-07 lands,
with the skill-judge rubric (percent bands, grade, critical and high findings), and writes the verdict
into its row. A file passes the bar when it has no critical or high finding and grades B or better on
the skill's own percent bands, with no regression against its baseline beyond the judge's run-to-run
variation (AGENTS.md, Non-Negotiable Rules). The phase holds until each row meets the bar.

Baselines come from the native-opus-xhigh rounds in
`.planning/phases/29.1-stacked-phase-branches-chained-prs-and-the-merge-chain-inserted/29.1-JUDGE.md`.

| File | Baseline | Verdict |
|---|---|---|
| `skills/ai-kit-commit-fold/SKILL.md` | 105/125, 84.0 B (native-opus-xhigh round 2, 29.1-JUDGE.md) | round 1 103/125, 82.4 B; round 2 105/125, 84.0 B; round 3 105/125, 84.0 B, 0 critical / 0 high / 3 medium; pass |
| `skills/ai-kit-spec-execute-superpowers/SKILL.md` | 104/125, 83.2 B (same source; plan 30-07 edits it) | round 1 102/125, 81.6 B, 1 high (fixed); round 2 103/125, 82.4 B, 1 high (fixed in 76fa531); round 3 104/125, 83.2 B, 0 critical / 0 high / 6 medium; pass |
| `.planning/lens-brief/SKILL.md` | none (new in this phase) | round 1 75/125, 60.0 D, 3 high (fixed); round 2 103/125, 82.4 B, 1 high (fixed in 1329c6b); round 3 106/125, 84.8 B, 0 critical / 0 high / 1 medium; pass |

Not judged: `skills/ai-kit-project-rules-agents/SKILL.md` (unchanged in this phase, so it has no judge row).

## Native-opus-xhigh verdicts (2026-11-06)

Judge: `native-opus-xhigh`, one fresh judge per file per round. Raw verdicts: `tmp/judge-30/` (round 1 at
0214ccb) and `tmp/judge-30/round2/` (round 2 at 9dca258), gitignored. Fix commits between rounds: 217807f
(lens brief), 48b02b5 (superpowers), 7037be9 (commit-fold).

- Round 1 highs, all fixed in round 2: lens-brief name not matching its folder, no evals, and an always-true
  "brief not loaded" check; superpowers running `boundary --next` during a run, which rewrote the unit's brief.
- Lens-brief round 2 high (the host rule marked an `@` lens as not loaded on non-Claude hosts): fixed in
  1329c6b after round 2 with three of its mediums; not re-judged.
- Superpowers round 2 high, open and pre-existing (since 4c3c890, missed by the baseline and round 1): `start`
  carries only commits that touch the plan file, so a separately committed spec is dropped, while
  SKILL.md:104, `references/start-step.md` and commit-fold's `references/adapter-guide.md` claim spec and plan
  commits are carried. Root fix is in `fold.py`/`flow_unit._carry` (carry the plan's `**Spec:**` file too, or
  stop when it is missing). Left for a follow-up after the phase's one fix cycle.
- Commit-fold round 2: the three mediums 7037be9 targeted are fixed (description covers the boundary;
  `.graphifyignore` commit before the next checkpoint; `.aikit/` exclude reported). Open: 3 carried mediums.

Bar (AGENTS.md: no critical or high finding, or grade B or better, no drop beyond run-to-run variation): met
for all three. Deltas vs baseline: commit-fold 0, superpowers -1 point.

## Round 3 (2026-11-06, phase close)

Judge: `native-opus-xhigh`, one fresh judge for all three files at 76fa531, skill-judge rubric v4. Raw
verdicts: `tmp/judge-30/round3/` (gitignored). Bar for this round: no critical or high finding, grade B or
better, and no drop of more than 7 points against round 2.

- lens-brief: 106/125, 84.8 B (+3). The round-2 high is fixed: an `@` lens counts as loaded on any host.
  Both round-2 mediums are fixed. Open: the evals medium (no case covers the host rule) and 6 lows.
- commit-fold: 105/125, 84.0 B (0). The spec-carry fix (76fa531) agrees across the code, `adapter-guide.md`
  and `unit-contract.md`. Open: the 3 carried mediums and 12 lows (one new low: `adapter-guide.md:14` calls
  the unit id "the phase number"; the code uses `phase-<NN>`).
- superpowers: 104/125, 83.2 B (+1). Superpowers round-2 high D8-5 is fixed. `start --plan` carries the
  commits that touch the spec on the plan's `**Spec:**` line. Fixture probes passed for a bare path, a
  plan-relative link, backticks, a plan revision, no `**Spec:**` line (plan only) and an outside path
  (ignored). Open: the `.graphifyignore` commit rule in the start step (medium), the second index refresh
  in the start block (medium), and 4 more mediums.

Result: pass for all three.
