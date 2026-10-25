# Skill evaluation: ai-kit-gsd-spec-discuss

**107/120 — B (89.2%).** Strong Process/Tool hybrid with substantial GSD-specific knowledge. Estimated Expert:Activation:Redundant ratio: **85:12:3**.

Reviewed the complete 289-line `SKILL.md`, all four references, all three scripts, and the requested diff. The changes correctly explain global-skill realpath confinement and trusted roots, and explicitly prohibit both analyzer and advisor from calling jev—even when its skill is injected. Two remaining inconsistencies weaken decision routing and setup diagnostics.

| Dimension | Score | Assessment |
|---|---:|---|
| D1 Knowledge delta | 18/20 | Valuable workflow traps, trust boundaries and amendment rules; some repetition. |
| D2 Mindset + procedures | 14/15 | Evidence-first judgment paired with concrete GSD procedures. |
| D3 Anti-pattern quality | 15/15 | Specific prohibitions with meaningful failure explanations (`SKILL.md:251–270`). |
| D4 Specification compliance | 14/15 | Valid metadata and excellent triggers; description carries excessive execution detail. |
| D5 Progressive disclosure | 14/15 | Mandatory, embedded reference triggers and explicit “Do NOT load” guidance. |
| D6 Freedom calibration | 13/15 | Appropriate constraints around fragile operations, but forced-answer instructions conflict. |
| D7 Pattern recognition | 9/10 | Clear phased Process/Tool structure; modest duplication across layers. |
| D8 Practical usability | 10/15 | Strong ordinary paths and fallbacks; forced-result routing and empty-wiring diagnostics remain inconsistent. |

### Findings

Paths below are relative to `skills/ai-kit-gsd-spec-discuss/`.

1. **Important — Forced answers do not fit the numbered decision tree.**  
   **Evidence:** `references/decision-table.md:16–23` permits accepting high-probability forced columns after evidence checks. However, `scripts/decide.py:518–526` assigns `decided_by` only to columns with `fallback == false`. A forced remote answer therefore cannot satisfy row 4’s `decided_by` condition (`references/decision-table.md:40–46`); row 5 instead directs own reasoning. A consistent forced local answer has the same mismatch, and its pointer to row 3 targets a row about *contradictory* evidence.  
   **Fix:** Add explicit forced-local and forced-remote branches before the ordinary `decided_by` branches, including precedence when a later backend answered. Preserve the script’s conservative `decided_by` meaning and add a small routing example for each forced case.

2. **Minor — Setup can label empty wiring as successfully resolved.**  
   **Evidence:** `SKILL.md:51–58` discards stderr and reads JSON warnings; `SKILL.md:68` concludes success whenever there are no warnings and the reason is not `not_configured`. The installed gsd-core emits `reason: configured_empty`, but writes its empty-path warning directly to stderr rather than JSON diagnostics (`.claude/gsd-core/bin/lib/init.cjs:3855–3863`). Consequently, an empty array or empty string can reach the success instruction despite loading no skills.  
   **Fix:** Handle `configured_empty` explicitly as “configured with no skills”; reserve successful resolution for the appropriate resolved reason with no skip warnings.

3. **Minor — Metadata and guardrails contain avoidable repetition.**  
   **Evidence:** `SKILL.md:3` includes run-mode mechanics and artifact/commit details repeated at `:8–14`, `:96–102` and `:139–144`. The no-jev rationale is also repeated within `references/analyzer-brief.md:47–50` and `:60–63`.  
   **Fix:** Keep description text focused on capability, triggers and exclusions. Retain the executable no-jev instruction in the spawn template, but shorten its repeated explanation.

No files were changed or credentials read. Runtime tests and live backend calls were not run; behavioral conclusions are based on source inspection.

DIGEST fd393fba782b5b56
CURRENT 107/120
CRITICAL 0 IMPORTANT 1
