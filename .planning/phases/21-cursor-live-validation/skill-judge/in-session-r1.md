# Skill Evaluation Report: ai-kit-gsd-curated-config (Phase 21, cursor label lift)

Judge: in-session `skill-judge` (Claude Opus 5.5, the orchestrator's live Claude Code session).
CURRENT only, at `skills/ai-kit-gsd-curated-config/SKILL.md` (315 lines) with `references/runner.md`
and `references/v1-path.md`. Digest judged: `b924ac84e1d6d3c9` (SKILL.md + references/).
Delta since the Phase 20 final (digest `ea3200ce9624de80`, 109/120): the resolution-order sentence
names cursor, the runner is template 5, runner.md documents the scan-all guarded `agent`, and the
limits table splits pi from a qualified cursor row.

## Summary
- **Total Score**: 109/120 (91%)
- **Grade**: A
- **Pattern**: Process, with Tool-pattern exit-code and subcommand tables
- **Verdict**: every changed claim holds against the code and evidence:
  `_HOST_FIRST_ROOT["cursor"] = ".cursor"` (`ai_kit_gsd_curated_config/host.py:22-28`);
  `TEMPLATE_VERSION = 5` (`cross_ai.py:46`); `pathHits` scan with the D-09 comment
  (`ai-kit-spec-review/references/cross-ai.mjs:413-432`); the cursor row's facts (local install,
  apply, resolve-model-only chain, 420-check matrix) match `21-SMOKE-CURSOR.md` steps 4-9 and its
  per-project lines. The lift is qualified ("validated headless … interactive confirmation
  **pending**"), never bare, so certainty is not overstated. No Critical or Important issue.

## Dimension Scores

| Dimension | Score | Max | Notes |
|-----------|-------|-----|-------|
| D1: Knowledge Delta | 18 | 20 | Unchanged; the cursor row adds expert, sourced limits |
| D2: Mindset + Procedures | 13 | 15 | Unchanged |
| D3: Anti-Pattern Quality | 14 | 15 | Unchanged |
| D4: Specification Compliance | 14 | 15 | No migration trigger in the description (carried) |
| D5: Progressive Disclosure | 13 | 15 | runner.md still has no "do not load" note (carried) |
| D6: Freedom Calibration | 14 | 15 | Unchanged |
| D7: Pattern Recognition | 9 | 10 | Unchanged |
| D8: Practical Usability | 14 | 15 | The cursor row's "resolve-model-only chain" is terse (Minor 1) |

## Critical Issues

None.

## Important Issues

None.

## Minor Findings

1. **Cursor row jargon (D8), SKILL.md line 252.** "resolve-model-only chain" is not explained in the
   skill; one clause would do: the cursor installer bakes no `model:` line, so per-agent models
   take effect only through gsd-core's `resolve-model`.
2. **Repo-only citations (D5), line 252.** The row cites `21-SMOKE-CURSOR.md` and
   `21-INTERACTIVE-CURSOR.md`, which ship only in this repo's planning tree; consistent with the
   existing "20 D-11" style, but opaque to a reader of the installed skill.
3. **Line wrap (cosmetic), lines 24-25.** The resolution-order sentence's second line runs past the
   file's wrap width.

CURRENT 109/120
CRITICAL 0
IMPORTANT 0
DIGEST b924ac84e1d6d3c9
