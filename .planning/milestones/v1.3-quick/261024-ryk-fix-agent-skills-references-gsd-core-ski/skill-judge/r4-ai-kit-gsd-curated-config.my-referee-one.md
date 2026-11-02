# Skill evaluation: ai-kit-gsd-curated-config

**106/120 — Grade B (88.3%).** Strong Tool/Process skill with domain-specific safeguards and actionable recovery guidance. The changes since `5b4ec21` substantially improve trust handling, but the new validator does not yet match gsd-core in every case.

Read the complete rubric, `SKILL.md` (354 lines), both references (`v1-path.md`, 47 lines; `runner.md`, 65 lines), and the requested diff. No `scripts/` directory exists. Estimated Expert:Activation:Redundant ratio: **85:10:5**.

| Dimension | Score | Assessment |
|---|---:|---|
| D1 Knowledge Delta | 18/20 | Valuable GSD-specific resolution, migration and permission knowledge; some repeated safeguards. |
| D2 Mindset + Procedures | 14/15 | Trust-first decisions and approval checkpoints precede fragile operations. |
| D3 Anti-Pattern Quality | 15/15 | Specific prohibitions explain consequences: sparse config, overwritten runners, unsafe execution and mistaken rollback. |
| D4 Specification Compliance | 15/15 | Valid frontmatter; description clearly supplies capabilities, scenarios and trigger phrases. |
| D5 Progressive Disclosure | 12/15 | References have explicit loading conditions, but detailed skill-validation mechanics enlarge the main workflow. |
| D6 Freedom Calibration | 13/15 | Appropriate low-freedom commands and approval gates; enforcement gaps weaken the promised boundary. |
| D7 Pattern Recognition | 9/10 | Clear Tool/Process structure; some troubleshooting repetition. |
| D8 Practical Usability | 10/15 | Strong common-case recovery, but the two resolver mismatches below remain. |
| **Total** | **106/120** | |

### Findings

Paths below are relative to `skills/ai-kit-gsd-curated-config/`, except the explicit gsd-core comparison.

1. **Important — Malformed kept namespaced references bypass the skip refusal.**  
   **Evidence:** `ai_kit_gsd_curated_config/plan_io.py:629–642` accepts every multi-colon `global:` reference on Claude without checking its grammar. Kept entries also bypass value validation at `plan_io.py:915–921`. Consequently, `global:plugin::skill` and `global:plugin:bad.name` return no problem, while checkout-local `.claude/gsd-core/bin/lib/init.cjs:3687–3691` explicitly skips them. This contradicts `SKILL.md:268–274`’s refusal guarantee.  
   **Fix:** Validate the complete global name against gsd-core’s segment grammar before either namespaced or filesystem handling. Add regressions for empty segments and invalid characters in kept references.

2. **Important — A valid symlinked trusted root can be classified as unwireable.**  
   **Evidence:** `ai_kit_gsd_curated_config/skills.py:186–201` compares roots lexically; `skills.py:271–275` turns a failed comparison into an unwired refusal. If `~/trusted-link` resolves to `~/store`, a skill resolving to `~/store/foo` is rejected despite that configured root covering it. Gsd-core canonicalizes configured roots in `.claude/gsd-core/bin/lib/security.cjs:207–230`. For non-ai-kit skills this is not merely duplicate approval: it prevents wiring. Kept references encounter the same early refusal at `plan_io.py:635–637`.  
   **Fix:** Canonicalize existing trusted roots before coverage comparisons, retaining gsd-core’s existence and broad-root exclusions. Test a differently named symlinked root covering a non-ai-kit skill.

3. **Minor — Detailed resolver troubleshooting weakens progressive disclosure.**  
   **Evidence:** `SKILL.md:258–275` embeds refusal-command reconstruction and reference round-trip cases in the main body, alongside the exit table and common-mistakes section.  
   **Fix:** Keep the trust-approval rule and snapshot limitation inline; move detailed refusal variants into a reference loaded explicitly when a skill-reference refusal occurs.

**Verification limits:** No files or credentials were changed or read, respectively. No CLI workflow or test suite was run; conclusions use source comparison and isolated, non-writing in-memory checks.

DIGEST 7d0b37f068c3f41b
CURRENT 106/120
CRITICAL 0 IMPORTANT 2
