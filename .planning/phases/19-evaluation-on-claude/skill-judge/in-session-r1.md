# Skill Evaluation Report: ai-kit-gsd-curated-config (round r1)

Judge: in-session `skill-judge` (Claude Opus 5.5, live Claude Code session). CURRENT only, at
`skills/ai-kit-gsd-curated-config/SKILL.md` (307 lines) with `references/runner.md` (53) and
`references/v1-path.md` (42). Digest judged: `235e930d29d7d34c` (fix round 1, f88594a).

## Summary
- **Total Score**: 109/120 (91%)
- **Grade**: A
- **Pattern**: Process, with Tool-pattern exit-code and subcommand tables
- **Knowledge Ratio**: E:A:R ≈ 85:13:2
- **Verdict**: round 1 scopes the never-skip rule to v2 and gives v1 its own rule to ask before each write
  rule, which removes the one cross-path contradiction. The remaining issues are Minor.

## Dimension Scores

| Dimension | Score | Max | Notes |
|-----------|-------|-----|-------|
| D1: Knowledge Delta | 18 | 20 | Unchanged: dense, product-specific knowledge. Step 1 and step 4 paragraphs still pack several facts each |
| D2: Mindset + Procedures | 13 | 15 | Unchanged: preflight questions plus the dry-run, show, end-turn, apply ordering |
| D3: Anti-Pattern Quality | 14 | 15 | The NEVER rule now names its scope (v2) and points to the v1 rule; the reasons stay concrete |
| D4: Specification Compliance | 14 | 15 | Unchanged. The description still has no trigger for migrating an existing config to v2 |
| D5: Progressive Disclosure | 13 | 15 | The NEVER pointer to `references/v1-path.md` is a conditional route. There is still no explicit "do not load" line |
| D6: Freedom Calibration | 14 | 15 | Both paths now have a stated approval point before writes |
| D7: Pattern Recognition | 9 | 10 | Unchanged |
| D8: Practical Usability | 14 | 15 | The v1/v2 conflict is gone. Remaining gap: the Reporting rule's verbatim list does not name the dry-run rows |

## Critical Issues

None.

## Important Issues

None.

## Minor Findings

1. **Reporting rule vs step 4 (D8).** The verbatim list in `## Reporting rule` still omits "every
   dry-run row (step 4)", so the instruction toward a short summary competes with the full-key rule.
2. **v1 approval wording (D8), v1-path.md lines 8-10.** "each `apply-*` call writes at once" is
   narrower than the next sentence, "Before each write", because `ensure-project` also writes. The
   rule itself covers it; only the lead-in is narrow.
3. **Description trigger (D4).** Migrating an existing GSD config to v2 is still not a listed trigger.
4. **Step 4 density (D1).** One paragraph, with a mid-sentence hard wrap, still carries four rules.
5. **Duplicated runner facts (D5).** Permission facts appear in both SKILL.md and runner.md (deliberate).

CURRENT 109/120
CRITICAL 0
IMPORTANT 0
