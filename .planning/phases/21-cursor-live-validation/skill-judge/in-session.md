# Skill Evaluation Report: ai-kit-gsd-curated-config (Phase 21, after fix rounds 1-2)

Judge: in-session `skill-judge` (Claude Opus 5.5, the orchestrator's live session). CURRENT only,
`skills/ai-kit-gsd-curated-config/SKILL.md` with `references/`. Digest judged: `85da5a6682d937c5`.
Delta since the round-1 in-session report (`b924ac84e1d6d3c9`, 109/120): inventory now stops and
asks on an offline or no-write request (pi Important 1, round 1); `--project-dir "<target>"` and
`--path "<detected path>"` are quoted in every command (SKILL.md and v1-path.md); the two adjacent
dry-run/full-key mistake rows are merged and point at step 4; runner.md no longer presents three
flags as the whole interface.

## Summary
- **Total Score**: 110/120 (92%)
- **Grade**: A
- **Verdict**: the round-1 claims still hold (host roots, template 5, scan-all `agent`, the qualified
  cursor row). The new stop-and-ask branch is a real safety gain (an explicit refusal path where
  there was only disclosure); the quoting fixes a copy-paste hazard; the merged row removes a
  repeat. No Critical or Important issue.

## Dimension Scores

| Dimension | Score | Max | Notes |
|-----------|-------|-----|-------|
| D1: Knowledge Delta | 18 | 20 | Unchanged |
| D2: Mindset + Procedures | 13 | 15 | Unchanged |
| D3: Anti-Pattern Quality | 14 | 15 | Unchanged |
| D4: Specification Compliance | 14 | 15 | No migration trigger in the description (carried) |
| D5: Progressive Disclosure | 13 | 15 | runner.md has no "do not load" note (carried) |
| D6: Freedom Calibration | 15 | 15 | Offline/no-write now a hard stop with a question, matching its fragility |
| D7: Pattern Recognition | 9 | 10 | Unchanged |
| D8: Practical Usability | 14 | 15 | "resolve-model-only chain" still terse on the cursor row |

## Critical Issues

None.

## Important Issues

None.

## Minor Findings

1. **Cursor row jargon (D8).** "resolve-model-only chain" stays unexplained (carried from round 1).
2. **Profile choice (D2/D8).** No guidance on balanced versus adaptive (pi Minor 2, round 2); it
   needs verified gsd-core behavior, so it was not invented here.
3. **Repo-only citations (D5).** The cursor row cites planning files that do not ship with the skill.

CURRENT 110/120
CRITICAL 0
IMPORTANT 0
DIGEST 85da5a6682d937c5
