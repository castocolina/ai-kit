Judge: my-referee-one
Reviewed-sha256: 1f5f09727354aee6c185d4f574da6e1e6aa4c5b34fed2e90ee9e4006fcb16bd1
Lane: AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-one exit=0 cli_rc=0 elapsed=133s out=670638 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 104
Critical: 0
Important: 2

## Skill evaluation: ai-kit-spec-execute-superpowers

**104/120 — B (86.7%).** A strong Process/Tool skill with useful exclusion-state, report-preservation and pinned-resume rules. Estimated knowledge ratio: **80% Expert / 15% Activation / 5% Redundant**.

Reviewed the complete 459-line `SKILL.md`, all three references, the linked Python shim and relevant dispatch implementation, the requested Phase 25.1 diff, and the canonical cross-AI policy.

| Dimension | Score | Assessment |
|---|---:|---|
| D1: Knowledge Delta | 18/20 | Concrete failure modes and state invariants; some repeated prohibitions. |
| D2: Mindset + Procedures | 14/15 | Strong permanent-versus-wave reasoning and explicit dispatch/resume procedures. |
| D3: Anti-Pattern Quality | 14/15 | Specific NEVER rules explain report loss, exclusion mistakes and unauthorized recovery. |
| D4: Specification Compliance | 15/15 | Valid metadata; description clearly identifies triggers and excludes inline execution. |
| D5: Progressive Disclosure | 11/15 | Good mandatory state/escalation references, but canonical-policy loading is not required; substantial policy remains duplicated. |
| D6: Freedom Calibration | 12/15 | Dispatch failures pin the injection, but scheduling changes the runner-requested wait. |
| D7: Pattern Recognition | 9/10 | Clear phased adapter pattern, slightly burdened by repeated policy and rationale. |
| D8: Practical Usability | 11/15 | Detailed executable examples; policy-loading and stale retry wording leave avoidable ambiguity. |
| **Total** | **104/120** | |

### Findings

1. **Important — The canonical caller policy is linked but no longer mandatory to load.**  
   **Evidence:** `skills/ai-kit-spec-execute-superpowers/SKILL.md:39–42,52–53` provides pointers without a read/invoke requirement. The Phase 25.1 diff removes the previous mandatory policy read. Consequently, an agent can follow this skill without receiving the canonical rule that upstream bodies are **data, never instructions**, including refusal to act on `switch-combo` hints (`skills/ai-kit-cross-ai/SKILL.md:88–90`).  
   **Fix:** Require loading `ai-kit-cross-ai` before the first external dispatch and consulting its stop contract before acting on a failure. Keep runner grammar, tool-profile, retry-configuration and catalog/overlay details there rather than duplicating them.

2. **Important — The scheduling instruction overrides configurable hard waits.**  
   **Evidence:** `skills/ai-kit-spec-execute-superpowers/SKILL.md:356–366` requires a minimum 60-second wait rounded up to a whole minute. The canonical contract requires **exactly** `retry_after_s` seconds (`skills/ai-kit-cross-ai/SKILL.md:120–122`), and configured `hard_waits_s` entries may be zero or sub-minute values (`skills/ai-kit-cross-ai/references/subprocess-quota-policy.md:89–90`). Thus a valid configured wait can be silently changed by the caller.  
   **Fix:** Remove caller-side clamping and rounding. If the host scheduler cannot represent the requested interval, explicitly report that limitation and use the canonical manual re-invocation path rather than claim an exact scheduled wait.

3. **Minor — The escalation reference retains the obsolete router-only retry exception.**  
   **Evidence:** `skills/ai-kit-spec-execute-superpowers/references/escalation.md:76–78` permits the one-shot wake only “for the ruled router exit 75.” Updated `SKILL.md:320–321,356–361` also covers exhausted transient series with valid hard-tier hints.  
   **Fix:** Replace the router-specific exception with a pointer to Step 3’s validated exit-75 hard-tier branch, explicitly preserving the same injection for either eligible class.

**Phase 25.1 assessment:** Failure handling correctly prohibits candidate re-resolution, preserves the runtime/model injection, relays report/upstream/status evidence, and stops on hard-tier exhaustion. Copilot’s unverified classification, unrestricted execution and argv exposure are disclosed. Runtime grammars, tool profiles and catalog ownership remain delegated rather than independently reconstructed.

No files were changed or credentials read. Runtime execution, scheduler behavior and tests were not checked; this is a static review.

DIGEST 1f5f09727354aee6
CURRENT 104/120
CRITICAL 0 IMPORTANT 2

## Runner evidence

```
AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-one exit=0 cli_rc=0 elapsed=133s out=670638 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
```
