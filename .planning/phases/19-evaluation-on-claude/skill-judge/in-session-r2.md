# Skill Evaluation Report: ai-kit-gsd-curated-config (round r2)

Judge: in-session `skill-judge` (Claude Opus 5.5, live Claude Code session). CURRENT only, at
`skills/ai-kit-gsd-curated-config/SKILL.md` (307 lines) with `references/runner.md` (53) and
`references/v1-path.md` (45). Digest judged: `9cddf0a5892fba97` (fix round 2, 86ad793).

## Summary
- **Total Score**: 109/120 (91%)
- **Grade**: A
- **Pattern**: Process, with Tool-pattern exit-code and subcommand tables
- **Knowledge Ratio**: E:A:R ≈ 85:13:2
- **Verdict**: the v1 approval rule is now executable. It asks for the command and its passed values,
  names the commands whose preset writes v1 cannot preview (checked against `cli.py`: only
  `apply-profile` and `apply-claude-md-path` write exactly their flag), and routes a full preview
  to the v2 dry run. No Critical or Important issue remains.

## Dimension Scores

| Dimension | Score | Max | Notes |
|-----------|-------|-----|-------|
| D1: Knowledge Delta | 18 | 20 | Unchanged; step 1 and step 4 are still dense |
| D2: Mindset + Procedures | 13 | 15 | Unchanged |
| D3: Anti-Pattern Quality | 14 | 15 | Unchanged; scoped NEVER rule |
| D4: Specification Compliance | 14 | 15 | No migration trigger in the description |
| D5: Progressive Disclosure | 13 | 15 | Unchanged |
| D6: Freedom Calibration | 14 | 15 | v1 now has an approval point an agent can actually satisfy |
| D7: Pattern Recognition | 9 | 10 | Unchanged |
| D8: Practical Usability | 14 | 15 | The Reporting rule's verbatim list still omits the dry-run rows |

## Critical Issues

None.

## Important Issues

None.

## Minor Findings

1. **Reporting rule vs step 4 (D8).** The Reporting rule's verbatim list does not name the dry-run rows.
2. **v1 lead-in (D8), v1-path.md line 8.** "each `apply-*` call writes at once" leaves out `ensure-project`,
   which also writes. The next sentence, "Before each write", covers it.
3. **Description trigger (D4).** Migrating an existing GSD config to v2 is not a listed trigger.
4. **Step 4 density (D1).** Four rules in one paragraph, with a hard wrap mid-sentence.
5. **Duplicated runner facts (D5).** SKILL.md and runner.md both carry the permission facts (deliberate).

CURRENT 109/120
CRITICAL 0
IMPORTANT 0
