# Skill evaluation: ai-kit-gsd-curated-config

**107/120 — B (Good).** Clear Tool/Process pattern with substantial GSD-specific knowledge; estimated Expert:Activation:Redundant ratio **85:12:3**.

Read the complete rubric, all 342 lines of `SKILL.md`, both references (`runner.md`: 64 lines; `v1-path.md`: 47 lines), and the requested diff. No `scripts/` directory exists. Inspected the changed implementation and tests, and compared containment rules with checkout-local gsd-core.

| Dimension | Score | Assessment |
|---|---:|---|
| D1: Knowledge Delta | 19/20 | Strong runtime, trust, migration and rollback knowledge; slight repetition. |
| D2: Mindset + Procedures | 14/15 | Good trust-first reasoning and approval sequence; somewhat procedure-heavy. |
| D3: Anti-Pattern Quality | 15/15 | Specific prohibitions explain concrete failures and consequences. |
| D4: Specification Compliance | 15/15 | Valid frontmatter; explicit capabilities, triggers and keywords. |
| D5: Progressive Disclosure | 14/15 | Conditional references and v1-only loading guidance; minor duplication remains. |
| D6: Freedom Calibration | 12/15 | Strong approval controls, weakened by unsafe printed recovery commands. |
| D7: Pattern Recognition | 9/10 | Coherent Tool/Process structure with clear checkpoints. |
| D8: Practical Usability | 9/15 | Common paths are actionable; two correctness gaps undermine the new guarantees. |
| **Total** | **107/120** | |

### Findings

Paths below are relative to `skills/ai-kit-gsd-curated-config/`.

1. **Important — Recovery commands can drop unrelated, working skills.**  
   **Evidence:** `ai_kit_gsd_curated_config/plan_io.py:626–641` excludes *every* colon-containing reference from the replacement list, not just skipped references. `SKILL.md:255–258` tells the agent to rerun the printed commands. A read-only synthetic check with `global:blocked`, healthy `global:healthy`, and `global:plugin:other` produced:
   ```text
   plan-set agent_skills.gsd-executor '[]'
   ```
   Following that fix removes both healthy skills too. The accompanying “re-resolves by name” note does not disclose that they were omitted entirely.  
   **Concrete fix:** Preserve healthy bare-global references by converting them to bare names. For namespaced references that cannot safely round-trip through bare names, require an explicit replacement decision instead of printing a destructive command as the fix. Add a mixed-reference regression test.

2. **Important — Apply’s global-reference guarantee relies on stale inventory facts.**  
   **Evidence:** `ai_kit_gsd_curated_config/skills.py:212–236` trusts recorded `escapes_root` and resolved paths; `ai_kit_gsd_curated_config/apply.py:896–917` checks those snapshot facts without refreshing global skill containment. In contrast, kept project references receive live filesystem checks at `skills.py:270–285`. Thus, a global skill removed or retargeted outside trusted roots after inventory can pass apply and subsequently be skipped by gsd-core, contrary to `SKILL.md:259–263`.  
   **Concrete fix:** Revalidate global skill existence and canonical containment against the effective trusted roots before either dry-run or real apply proceeds. Add tests that remove or retarget a global skill after inventory. Until implemented, qualify the documentation as snapshot-based validation.

3. **Minor — Repeated operational safeguards add avoidable reading overhead.**  
   **Evidence:** `SKILL.md:144–152` and `330` repeat the full-key dry-run approval rule; `232–235`, `317`, and `references/runner.md:56–63` repeat `.new` activation guidance.  
   **Concrete fix:** Keep the authoritative instructions at their workflow decision points and shorten later repetitions to cross-references.

No files were changed or credential files read. Tests and live apply were not run; runtime conclusions are based on source inspection and a no-write synthetic check.

DIGEST a7baccdc7bd3a6f1
CURRENT 107/120
CRITICAL 0 IMPORTANT 2
