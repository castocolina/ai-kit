# Skill Evaluation Report: ai-kit-gsd-curated-config (Phase 20, post-code-review round)

Judge: in-session `skill-judge` (Claude Opus 5.5, live Claude Code session, Skill tool loaded).
CURRENT only, at `skills/ai-kit-gsd-curated-config/SKILL.md` (314 lines) with
`references/runner.md` and `references/v1-path.md`. Digest judged: `ea3200ce9624de80` (after the code-review fixes; only runner.md changed since 2663ee4bf6433cc1).

## Summary
- **Total Score**: 109/120 (91%)
- **Grade**: A
- **Pattern**: Process, with Tool-pattern exit-code and subcommand tables
- **Knowledge Ratio**: E:A:R ≈ 85:13:2
- **Verdict**: the Phase 20 changes are certainty updates that hold against the code: the host is
  never a review lane (checked against `cross_ai.eligible_lanes` and `plan_io._host_reviewer_problem`),
  installer follow-ups report gitignore prefixes without editing `.gitignore`, and runner.md now
  matches template 4 (`--standalone` on opencode, the template-3 readiness floor in
  `cross_ai_script._READY_TEMPLATE`, the `liveOuterTimeoutS` ladder and its 300 s default).
  The host-lane guarantee is now scoped to v2, and v1-path.md says `detect-review-candidate` can
  name the host (checked against `preference_match.best_review_candidate` and
  `cli._apply_review_writes`, which add the slug with no host check). The code-review fix narrowed runner.md's `--standalone`
  sentence to what was observed (flag accepted by opencode v2.0.31, no port conflict; private-server
  isolation is the flag's stated purpose). No Critical or Important issue.

## Dimension Scores

| Dimension | Score | Max | Notes |
|-----------|-------|-----|-------|
| D1: Knowledge Delta | 18 | 20 | Expert content throughout; step 1 and step 4 are still dense |
| D2: Mindset + Procedures | 13 | 15 | Pre-flight questions plus a non-obvious ordered pipeline |
| D3: Anti-Pattern Quality | 14 | 15 | Scoped NEVER list with reasons; host-lane rule adds a concrete refusal |
| D4: Specification Compliance | 14 | 15 | No migration trigger in the description |
| D5: Progressive Disclosure | 13 | 15 | Conditional triggers for both references; no "do not load" for runner.md |
| D6: Freedom Calibration | 14 | 15 | Low freedom on writes and approvals, judgment on choices |
| D7: Pattern Recognition | 9 | 10 | Clear Process pattern |
| D8: Practical Usability | 14 | 15 | Failure states, exit codes and the v1 same-host case covered; Reporting rule omits the dry-run rows |

## Critical Issues

None.

## Important Issues

None.

## Minor Findings

1. **Reporting rule (D8), SKILL.md lines 306-313.** The verbatim list does not name the dry-run rows,
   which step 4 makes the approval surface.
2. **Description trigger (D4), line 3.** Migrating an existing (v1) GSD config to v2 is not a listed trigger.
3. **Repeated dry-run rule (D1), lines 134-143, 272-275, 300-301.** Step 4, the NEVER list and two
   adjacent common-mistake rows restate the full-key/separate-turn rule.
4. **Run-flow pre-flight (D8), lines 60-63.** The v1-runner parenthetical inside the second question is
   hard to parse; the question is "was this config written by v1?".
5. **runner.md loading (D5).** The trigger names when to read it but not when to skip it (a plain v2
   apply on a fresh project).

CURRENT 109/120
CRITICAL 0
IMPORTANT 0
