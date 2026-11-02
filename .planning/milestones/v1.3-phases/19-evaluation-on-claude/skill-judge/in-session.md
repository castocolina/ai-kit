# Skill Evaluation Report: ai-kit-gsd-curated-config

Judge: in-session `skill-judge` (Claude Opus 5.5, live Claude Code session). CURRENT only, at
`skills/ai-kit-gsd-curated-config/SKILL.md` (306 lines) with `references/runner.md` (53) and
`references/v1-path.md` (40). Digest judged: `f29ad8427446ce45`.

## Summary
- **Total Score**: 108/120 (90%)
- **Grade**: A
- **Pattern**: Process (a six-step pipeline with checkpoints), with Tool-pattern exit-code and subcommand tables
- **Knowledge Ratio**: E:A:R ≈ 85:13:2
- **Verdict**: a product-specific, low-freedom procedure whose value is facts Claude cannot know: pseudo-keys, refusal semantics, key-family removal, fingerprinted follow-ups and permission differences between flows. The remaining issues are wording and consistency, not missing knowledge.

## Dimension Scores

| Dimension | Score | Max | Notes |
|-----------|-------|-----|-------|
| D1: Knowledge Delta | 18 | 20 | Almost every paragraph is product knowledge. Some sentences pack three facts and read slowly (step 1 inventory, Removals) |
| D2: Mindset + Procedures | 13 | 15 | The "ask yourself" block before the first command (trust, v1-written config, scratch location) plus a non-obvious ordering (dry run, show rows, end the turn, apply) |
| D3: Anti-Pattern Quality | 14 | 15 | The NEVER list gives a non-obvious reason for each item (`--force` bypassing the full-permission guard, v1 `apply-execution` dropping the v2 prefer order). The Common mistakes table records failures seen in pressure tests |
| D4: Specification Compliance | 14 | 15 | Valid frontmatter. The description covers WHAT, WHEN and keywords, and says it is not a gsd-settings replacement. Migrating a v1-configured project is not a listed trigger |
| D5: Progressive Disclosure | 13 | 15 | Both references have conditional triggers ("only when running it", "Read … when a runner upgrade, a `.new` merge … comes up"). There is no explicit "do not load" line, and the runner facts are partly duplicated between SKILL.md and runner.md |
| D6: Freedom Calibration | 14 | 15 | Low freedom where config writes are fragile (exact commands, `approve_with` passed unchanged, no hand edits). Medium freedom in reporting. Appropriate |
| D7: Pattern Recognition | 9 | 10 | A clear Process pattern. The Limits and Subcommand tables follow the Tool pattern and fit |
| D8: Practical Usability | 13 | 15 | Exit-code table, failure states, refusal-recovery paths and fallbacks for a missing `followups` block. Two consistency gaps (below) |

## Critical Issues

None.

## Important Issues

None.

## Minor Findings

1. **Reporting rule vs step 4 (D8), SKILL.md lines 297-306 vs 134-142.** The Reporting rule asks for
   "a short structured summary", and its verbatim list does not name the dry-run rows. Step 4 asks
   for every row, one line per full dotted key. An agent that reads the Reporting rule last can lean
   toward brevity. Fix: add "every dry-run row (step 4)" to the verbatim list.
2. **Step 4 wording (D1/D8), lines 135-142.** One paragraph carries the full-key rule, the
   no-grouping rule, end-the-turn and the earlier-"go ahead" rule, with a hard line break mid-sentence
   ("given before those rows were / shown"). It is correct but dense. Fix: reflow it, and split the
   approval sentence into its own line.
3. **Description trigger (D4), line 3.** The description has no trigger for moving a project already
   configured by the v1 flow (or by hand) onto v2, which is the riskiest case the skill handles
   (key-family removal). Fix: add "or migrate an existing GSD config to the curated v2 flow".
4. **Duplicated runner facts (D5), lines 196-218 vs runner.md 21-25.** The codex sandbox and
   full-permission facts appear in both places. runner.md says it never weakens them, so the
   duplication is deliberate, but it costs tokens on every load. Fix: keep only the one-line
   permission summary per flow in SKILL.md (acceptable as is).
5. **Step 1 density (D1), lines 69-74.** One paragraph mixes cache refresh, offline disclosure,
   scratch-dir creation and `--host`/`--refresh`. Fix: put the disclosure sentence first and split
   it from the `$WORK` instruction.

## Top 3 Improvements
1. Name the dry-run rows in the Reporting rule's verbatim list (finding 1).
2. Add the v1-to-v2 migration trigger to the description (finding 3).
3. Reflow step 4 so each rule is one sentence (finding 2).

CURRENT 108/120
CRITICAL 0
IMPORTANT 0
