# Skill evaluation: `ai-kit-gsd-spec-discuss`

**104/120 (B).** A strong Process skill with specific safeguards and well-timed references. The changes since `5b4ec21` correctly explain why gsd-core skips some global skills and explicitly keep jev calls with the orchestrator, not the analyzer. No files were changed.

| Dimension | Score | Evidence |
|---|---:|---|
| D1 Knowledge Delta | 18/20 | GSD routing, consent, and evidence-led decisions are specific and useful. |
| D2 Mindset + Procedures | 13/15 | “You are the decider” is backed by a workable phase sequence. |
| D3 Anti-Patterns | 14/15 | The NEVER rules name concrete failure modes and consequences. |
| D4 Specification | 15/15 | Valid frontmatter; description states what, when, and trigger terms. |
| D5 Progressive Disclosure | 13/15 | Four references have explicit loading triggers; some guidance repeats. |
| D6 Freedom Calibration | 12/15 | Firm constraints suit fragile operations, but one confidence rule is miscalibrated. |
| D7 Pattern Recognition | 9/10 | Clear Process pattern. |
| D8 Practical Usability | 10/15 | Usable overall; the forced-fallback decision path needs correction. |

1. **Important — Forced fallbacks can be treated as confident decisions.** `references/decision-table.md:16-20` says a `fallback: true` answer above threshold counts as high, including for an override. But the client sets `needs_fallback` for truncation or excess state regardless of probability (`skills/jev-fast-decision/scripts/jev_review.py:1565-1577`), and `scripts/decide.py:524-525` does not mark that rung as the decider. **Fix:** treat every forced fallback as advisory requiring evidence-based reasoning; distinguish it from an ordinary below-threshold answer in the table and log format.

2. **Minor — The new wiring check cannot distinguish “no skips” from “nothing configured.”** `SKILL.md:46-59` filters stderr warnings for two agents, while gsd-core can return an empty block with no warning when an agent has no `agent_skills` entry (`.claude/gsd-core/bin/lib/init.cjs:3835-3844`). **Fix:** inspect each agent’s JSON `configured`, `reason`, and `warnings` fields; report an unconfigured agent separately from skipped entries.

Skipped: no tests or skill scripts were run, so runtime behavior beyond the inspected source remains unverified.
DIGEST 4c33bda55ff6ed04
CURRENT 104/120
CRITICAL 0 IMPORTANT 1
