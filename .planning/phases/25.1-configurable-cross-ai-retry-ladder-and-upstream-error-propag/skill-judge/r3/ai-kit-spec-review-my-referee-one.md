Judge: my-referee-one
Reviewed-sha256: ee1794d8f5e1b061433573bd295203633909ba9675b7da446cfd4a399675f4dd
Lane: AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-one exit=0 cli_rc=0 elapsed=405s out=988770 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 102
Critical: 0
Important: 3

## Skill evaluation: ai-kit-spec-review

**102/120 — Grade B.** Strong **Process/Tool** skill with substantial project-specific knowledge (estimated Expert:Activation:Redundant ratio **80:15:5**). Reviewed `SKILL.md`, all 14 reference files—including the complete runner and its embedded tests—and the requested Phase 25.1 diff. No `scripts/` files were referenced.

Phase 25.1 mostly aligns correctly: dispatch uses `--runtime`/`--model`; the runner selects only one runtime; soft retries, session resets and caller-owned hard waits are implemented; upstream evidence is redacted and treated as data; catalog overlays, model grammars, tool profiles and Copilot are covered. The canonical `ai-kit-cross-ai` links resolve correctly. The main policy gap remains automatic selection after unsuccessful probes.

| Dimension | Score | Rationale |
|---|---:|---|
| D1 — Knowledge Delta | 17/20 | Valuable worktree, lifecycle, routing and recovery knowledge; some duplicated rationale. |
| D2 — Mindset + Procedures | 14/15 | Strong archetype ceilings, clean-context reasoning and explicit dispatch procedures. |
| D3 — Anti-Pattern Quality | 14/15 | Concrete landmines with reasons, including contamination and unauthorized lane changes. |
| D4 — Specification Compliance | 15/15 | Valid frontmatter; description supplies capabilities, scenarios and trigger terms. |
| D5 — Progressive Disclosure | 12/15 | Mandatory and “Do NOT load” triggers are good; the 492-line entry point repeats reference detail. |
| D6 — Freedom Calibration | 11/15 | Fragile operations are tightly scripted, but probe fallback and fresh-session gating weaken constraints. |
| D7 — Pattern Recognition | 9/10 | Coherent Process/Tool structure with clear branching and checkpoints. |
| D8 — Practical Usability | 10/15 | Actionable common paths, but policy and edge-case inconsistencies remain. |
| **Total** | **102/120** | **Good, with important corrections needed.** |

## Findings

Paths below are relative to `skills/ai-kit-spec-review/`.

1. **Important — Unapproved probe fallbacks still select another provider or the native session.**  
   **Evidence:** `SKILL.md:157–170` explicitly permits walking past probes that fail for any reason and an implicit session-default fallback, while acknowledging that these extensions lack an owner ruling. Calling this “pre-dispatch selection” does not authorize those extensions to the owner’s quota-only ladder.  
   **Fix:** Continue automatically only under the explicitly configured, owner-approved selection conditions. Stop and ask on non-quota probe failures or when native fallback is not explicitly configured; align the resolver accordingly.

2. **Important — Later fresh sessions can bypass the dirty-tree gate.**  
   **Evidence:** `references/cross-ai.mjs:4124–4127` suppresses gating after the first no-resume retry through `gated`, and suppresses subsequent resets after persisted-session re-entry through `continued` (`3955–3966`). Thus a later failed attempt can introduce an out-of-scope edit before another fresh session starts. This conflicts with the canonical policy’s fresh-session gate.  
   **Fix:** Gate every fresh-session transition, including no-resume retries and resets after persisted-session re-entry. Add regression cases where the second failure introduces an unlisted edit.

3. **Important — Retry-config reads can block before the runner establishes its deadline.**  
   **Evidence:** `references/cross-ai.mjs:2847–2855` reads existing paths synchronously without checking their type; `3010` applies this to the user retry config. A FIFO without a writer blocks indefinitely. The overlay loader already rejects non-regular and oversized files at `2871–2882`.  
   **Fix:** Apply equivalent regular-file and bounded-size validation to retry-config reads, then fall through to the next source on refusal. Add a FIFO regression case.

4. **Minor — Saved-capture classification overstates Copilot evidence confidence.**  
   **Evidence:** Live runs force Copilot patterns to `unverified` at `references/cross-ai.mjs:3991–3996`, but `--classify-only` emits `cls.label` directly at `4382–4387`. A Copilot capture matching a verified wildcard row therefore reports `verified`, contrary to the canonical policy.  
   **Fix:** Apply the runtime’s `errorsUnverified` rule in saved-capture output too; add a Copilot classification fixture.

5. **Minor — The entry point duplicates recovery detail already maintained elsewhere.**  
   **Evidence:** `SKILL.md:330–348` repeats exit branching and evidence rules from `references/cross-ai-dispatch.md:240–258`, despite declaring the canonical caller contract at `SKILL.md:350–352`.  
   **Fix:** Keep the pending-lane decision and mandatory loading trigger in `SKILL.md`; maintain detailed exit handling in one referenced location.

No scripts, tests or live CLIs were executed; no project files were changed or credentials read. Runtime behavior remains statically assessed, not execution-verified.

DIGEST ee1794d8f5e1b061
CURRENT 102/120
CRITICAL 0 IMPORTANT 3

## Runner evidence

```
AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-one exit=0 cli_rc=0 elapsed=405s out=988770 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
```
