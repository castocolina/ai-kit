# Skill evaluation: ai-kit-gsd-curated-config

**Score: 108/120 — A.** Strong Tool/Process skill with substantial GSD-specific knowledge, explicit approval boundaries, and useful recovery instructions. Estimated Expert:Activation:Redundant ratio: **85:10:5**.

Read the complete rubric, the 337-line `SKILL.md`, both referenced documents (`runner.md`, 64 lines; `v1-path.md`, 47 lines), and the entrypoint. No `scripts/` directory exists. Reviewed the requested diff and compared its resolution rules with the installed GSD implementation.

| Dimension | Score | Assessment |
|---|---:|---|
| D1: Knowledge Delta | 18/20 | Valuable resolver, migration, permission, and recovery details; some duplication. |
| D2: Mindset + Procedures | 14/15 | Strong trust-first reasoning and domain-specific sequencing. |
| D3: Anti-Pattern Quality | 15/15 | Concrete prohibitions explain data-loss and permission consequences. |
| D4: Specification Compliance | 15/15 | Valid metadata; description clearly supplies capabilities, scenarios, and keywords. |
| D5: Progressive Disclosure | 13/15 | Both references have explicit loading conditions; some repeated material remains in the body. |
| D6: Freedom Calibration | 12/15 | Appropriate approval gates, but the claimed resolver invariant exceeds its enforcement. |
| D7: Pattern Recognition | 9/10 | Clear Tool/Process structure with conditional reference routing. |
| D8: Practical Usability | 12/15 | Actionable common paths and recovery guidance; retained-reference validation has a gap. |
| **Total** | **108/120** | |

### Findings

Paths below are relative to `skills/ai-kit-gsd-curated-config/`.

1. **Important — Retained project references bypass the new “no skipped reference” check.**  
   **Evidence:** `ai_kit_gsd_curated_config/plan_io.py:598–604` checks every `set` item, but checks `keep` items only when they match bare `global:<name>`. `plan_edit.py:128–137` makes `plan-unset` retain the existing value through `op: keep`. Consequently, an existing `skills/escape` pointing outside the project—or a missing project skill—passes this check when retained. GSD explicitly skips those cases in installed `init.cjs:3740–3762`. This contradicts `SKILL.md:254–257`, which promises that edits and apply refuse skipped references.  
   **Concrete fix:** Validate retained project-relative references against GSD’s containment and existence rules, alongside retained global references. Add regression cases for `plan-unset`, dry-run, and apply retaining an escaping or missing project skill.

2. **Minor — Repeat explanations dilute an otherwise effective disclosure structure.**  
   **Evidence:** Trusted-root approval and refusal behavior appears in `SKILL.md:122–128` and again at `249–257`; `.new` handling appears at `232–235`, `312`, and in `references/runner.md:38–59`. These passages substantially repeat procedures rather than adding distinct decisions.  
   **Concrete fix:** Keep the actionable approval instructions at step 3, link to one authoritative trust-policy explanation, and leave detailed runner-upgrade behavior in `references/runner.md`.

**Resolver-change assessment:** The main correction is sound: unrelated escaping globals are excluded, ai-kit install roots require explicit approval, and apply checks the proposed effective roots before writing. The remaining retained-reference gap prevents the stronger universal guarantee.

No commands that modify files were run, and no credential files were read. Runtime tests were not executed; conclusions are based on source and diff inspection.

DIGEST fb2186c9cbe3f86b
CURRENT 108/120
CRITICAL 0 IMPORTANT 1
