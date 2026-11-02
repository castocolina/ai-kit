Judge: my-referee-one
Reviewed-sha256: 29ec2a75169bb7038d204870f064fb339adf0c02441032341c64806e07067892
Lane: AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-one exit=0 cli_rc=0 elapsed=82s out=589524 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 112
Critical: 0
Important: 0

## Skill evaluation: ai-kit-gsd-curated-config

**112/120 — A (93.3%).** Strong Process/Tool skill with mostly repository-specific knowledge (estimated Expert:Activation:Redundant **85:10:5**).

Read the complete rubric, all 406 lines of `SKILL.md`, both reference files, the entrypoint, the requested diff, and the linked canonical policy. **No Critical or Important findings.**

| Dimension | Score | Assessment |
|---|---:|---|
| D1 Knowledge Delta | 19/20 | Valuable trust, migration, rollback and runtime-specific knowledge; slight repetition. |
| D2 Mindset + Procedures | 14/15 | Strong approval boundaries and non-obvious sequencing; a few ambiguous instructions. |
| D3 Anti-Pattern Quality | 15/15 | Specific prohibitions explain data-loss, trust and unauthorized-switch risks. |
| D4 Specification Compliance | 15/15 | Valid metadata; description clearly covers capabilities, scenarios and trigger terms. |
| D5 Progressive Disclosure | 13/15 | Both references have conditional loading guidance; retry tuning needs a more precise onward link. |
| D6 Freedom Calibration | 14/15 | Appropriately constrained writes and owner choices; local retry shorthand is broader than canonical policy. |
| D7 Pattern Recognition | 9/10 | Clear Process/Tool structure, with some repeated runner-upgrade guidance. |
| D8 Practical Usability | 13/15 | Detailed failure handling and actionable commands; minor dispatch and configuration-navigation ambiguity. |
| **Total** | **112/120** | |

### Phase 25.1 assessment

The skill correctly describes template 8’s single-runtime behavior, refuses autonomous harness/provider/model switching, preserves upstream evidence as data, and delegates stop handling to `ai-kit-cross-ai`. It distinguishes curated runners from Copilot-capable hooks and explains older-template readiness. The canonical policy covers the `--prefer` alias, retry schema and `hard_waits_s`, redaction, catalog overlay, model grammars and tool profiles; duplicating those details here is unnecessary.

### Findings

1. **Minor — Retry tuning does not explicitly load the configuration policy.**  
   **Evidence:** `skills/ai-kit-gsd-curated-config/SKILL.md:269–273` routes tuning to `runner.md`; `skills/ai-kit-gsd-curated-config/references/runner.md:42–49` names configuration sources but points onward only “for caller actions on any non-ok status.” The schema, bounds and precedence are in `skills/ai-kit-cross-ai/references/subprocess-quota-policy.md:52–93`.  
   **Fix:** Add a conditional mandatory link to that canonical reference for retry tuning. Do not copy its schema here.

2. **Minor — Local hard-tier shorthand omits the scheduler limitation.**  
   **Evidence:** `skills/ai-kit-gsd-curated-config/SKILL.md:244–246` says a requested dispatch “gets one wait and the same lane again,” whereas `skills/ai-kit-cross-ai/SKILL.md:149–154` requires a notice and stop without an available scheduler. The mandatory canonical read mitigates this discrepancy.  
   **Fix:** Replace the shorthand with “follow section 6’s scheduler-or-handoff rule; any re-entry uses the same lane.”

3. **Minor — Dispatch ownership is phrased inconsistently.**  
   **Evidence:** `skills/ai-kit-gsd-curated-config/SKILL.md:238–240` says this skill “never dispatches a model call,” immediately followed by allowance for a user-requested live dispatch; lines 244–245 also describe handling one.  
   **Fix:** State that configuration and verification never dispatch, and explicitly hand user-requested live calls to `ai-kit-cross-ai`.

No files or credentials were changed or read, respectively. Runtime calls and tests were not run; this is a static skill assessment, not live verification.

DIGEST 29ec2a75169bb703
CURRENT 112/120
CRITICAL 0 IMPORTANT 0

## Runner evidence

```
AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-one exit=0 cli_rc=0 elapsed=82s out=589524 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
```
