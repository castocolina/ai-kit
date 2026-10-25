Judge: my-referee-one
Reviewed-sha256: 17fb505e590c611cce964ad027ce5e245a132d8a946bb0735ced163ef76155d8
Lane: AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-one exit=0 cli_rc=0 elapsed=165s out=554856 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 110
Critical: 0
Important: 0

## Skill evaluation: ai-kit-spec-execute-gsd

**110/120 — A (91.7%).** A strong **Process/Tool** skill with substantial repository-specific knowledge and explicit safeguards against silent fallback. Estimated knowledge ratio: **Expert 80% / Activation 15% / Redundant 5%**.

Reviewed the complete 488-line `SKILL.md`, the complete 67-line reference, the entrypoint shim, the requested Phase 25.1 diff, and relevant runner/policy implementation.

| Dimension | Score | Assessment |
|---|---:|---|
| D1: Knowledge Delta | 18/20 | Valuable GSD ownership, hook-expansion, trust and recovery details; some repetition. |
| D2: Mindset + Procedures | 14/15 | Explains why opt-in, fresh resolution and stale-hook cleanup matter. |
| D3: Anti-Pattern Quality | 15/15 | Specific prohibitions with concrete consequences, especially native fallback and re-resolution. |
| D4: Specification Compliance | 15/15 | Valid frontmatter; description clearly covers capabilities, scenarios and triggers. |
| D5: Progressive Disclosure | 12/15 | Conditional reference loading exists, but most operational detail remains in the large body. |
| D6: Freedom Calibration | 14/15 | Fragile writes are tightly prescribed; configurable waits have one mismatch. |
| D7: Pattern Recognition | 9/10 | Coherent phased workflow, somewhat burdened by embedded implementation. |
| D8: Practical Usability | 13/15 | Strong failure handling and recovery instructions; policy-loading and scheduling details could be clearer. |
| **Total** | **110/120** | |

### Phase 25.1 assessment

The integration correctly points to `ai-kit-cross-ai` as the caller contract and prohibits harness/provider/model switching. Generated hooks use one `--runtime`; model grammars remain implementation-owned. Copilot’s unverified error patterns, unrestricted tools and argv-visible prompt are disclosed. Stop handling now includes redacted upstream evidence and terminal hard-tier stops. The soft series, configurable hard waits and error-catalog overlay appropriately remain in the canonical policy rather than being independently specified here.

### Findings

1. **Minor — Make loading the canonical contract explicit.**  
   **Evidence:** `skills/ai-kit-spec-execute-gsd/SKILL.md:41–45` links the contract “including its policy reference,” but does not explicitly require reading either document before proceeding. The actionable stop recipe at `:453–482` can be followed without that read, missing such details as treating upstream text strictly as data.  
   **Fix:** Require reading `../ai-kit-cross-ai/SKILL.md` and its policy reference before the first cross-AI handoff; retain only GSD-specific adaptations locally.

2. **Minor — Scheduling silently changes configurable wait values.**  
   **Evidence:** `skills/ai-kit-spec-execute-gsd/SKILL.md:464–465` imposes a 60-second minimum and rounds upward to a whole minute. The canonical contract requires exactly `retry_after_s` (`skills/ai-kit-cross-ai/SKILL.md:120–122`), while its policy permits non-minute values, including zero (`skills/ai-kit-cross-ai/references/subprocess-quota-policy.md:89–90`).  
   **Fix:** Explicitly document the scheduler’s rounding limitation and actual scheduled delay. For values it cannot represent exactly, provide the owner-run path rather than presenting the schedule as an exact wait.

3. **Minor — Separate execution recipes from the decision spine.**  
   **Evidence:** `skills/ai-kit-spec-execute-gsd/SKILL.md:236–289` embeds runner setup orchestration, and `:372–422` embeds a complete marker-aware file-rewrite recipe. Together they make the main workflow harder to scan.  
   **Fix:** Move these verbatim recipes into a workflow reference with mandatory loading triggers at their respective steps; keep prerequisites, branch decisions and stop conditions in `SKILL.md`.

Static review only: no tests, runner invocations or scheduling were performed. Runtime behavior remains unverified by this review; no files were changed or credentials read.

DIGEST 17fb505e590c611c
CURRENT 110/120
CRITICAL 0 IMPORTANT 0

## Runner evidence

```
AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-one exit=0 cli_rc=0 elapsed=165s out=554856 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
```
