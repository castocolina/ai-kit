Judge: my-referee-one
Reviewed-sha256: 2aed7941ce4547821e04d7ec86d5741ad40e979393a065827aabf25e6688c3d8
Lane: AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-one exit=0 cli_rc=0 elapsed=154s out=533531 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 104
Critical: 0
Important: 2

## Skill evaluation: ai-kit-spec-execute-superpowers

**104/120 — B (86.7%)**. Strong **Process/Tool** skill with substantial repository-specific knowledge (estimated Expert/Activation/Redundant ratio: **80/15/5**). Reviewed the complete 460-line `SKILL.md`, all three references, the requested Phase 25.1 diff, and relevant dispatch code. No `scripts/` files exist in this skill.

The Phase 25.1 updates correctly link the canonical `ai-kit-cross-ai` policy, preserve the injection across hard-tier wakes, relay upstream evidence, forbid post-failure candidate switching, and disclose Copilot’s permission and argv risks. They appropriately delegate retry configuration, the error catalog/overlay, and runtime flag ownership instead of duplicating those implementations.

| Dimension | Score | Assessment |
|---|---:|---|
| D1: Knowledge Delta | 18/20 | Valuable exclusion, report-memory and escalation edge cases; some repeated policy prose. |
| D2: Mindset + Procedures | 14/15 | Explains permanent versus temporary exclusions and selection versus recovery well. |
| D3: Anti-Pattern Quality | 14/15 | Specific NEVER rules supported by concrete failure histories. |
| D4: Specification Compliance | 15/15 | Valid metadata; precise capabilities, activation conditions and exclusions. |
| D5: Progressive Disclosure | 12/15 | Strong mandatory reference triggers, but the main document retains substantial duplicated policy. |
| D6: Freedom Calibration | 12/15 | Tight dispatch constraints; conflicting host-launch requirements weaken portability. |
| D7: Pattern Recognition | 9/10 | Clear phased Process/Tool structure, somewhat oversized. |
| D8: Practical Usability | 10/15 | Detailed executable guidance, but non-quota failure recovery lacks a complete pinned-state handoff. |
| **Total** | **104/120** | **Two Important findings remain.** |

### Findings

1. **Important — Non-quota failures do not persist the injection needed for safe resume.**  
   **Evidence:** `skills/ai-kit-spec-execute-superpowers/SKILL.md:353–357` persists `injection_json` only in the `"quota"` branch; `SKILL.md:402–408` stops on `"real_error"` without writing resumable state. Meanwhile, `references/state-management.md:61–66` prevents re-resolution only when that state contains `injection_json`. An auth, configuration or crash stop therefore lacks the same durable pinning guarantee, and an existing state file could describe an older dispatch.  
   **Fix:** Persist the current injection and task state for every failed external dispatch before handing control to the owner. Document the same pinned-resume path for `"real_error"`, with no automatic wake.

2. **Important — The mandatory background-only launch contradicts the canonical host contract.**  
   **Evidence:** `skills/ai-kit-spec-execute-superpowers/SKILL.md:264–265` requires background execution and forbids foreground execution without a host qualification. The mandatory linked policy instead prescribes foreground waiting for hosts without a background primitive: `skills/ai-kit-cross-ai/references/launch-and-wait.md:75–85`.  
   **Fix:** Apply the background requirement only where supported; otherwise follow the canonical foreground pattern with a sufficient tool deadline. Keep the `.exit` evidence file in both cases.

3. **Minor — “Unverified” routing is described as bypassing all model checks.**  
   **Evidence:** `skills/ai-kit-spec-execute-superpowers/SKILL.md:148–150` and `references/design-notes.md:27–28` say neither side checks the model when inventory is unavailable. However, `skills/ai-kit-spec-review/ai_kit_spec/runner_dispatch.py:595–600` still validates the runtime-specific model grammar.  
   **Fix:** Say that *inventory membership* is unverified while model-id grammar validation remains enforced.

4. **Minor — Repeated recovery policy dilutes otherwise useful progressive disclosure.**  
   **Evidence:** `skills/ai-kit-spec-execute-superpowers/SKILL.md:39–53`, `337–373`, `398–418`, and `references/design-notes.md:120–139` repeatedly state the same no-switch/pinned-retry policy.  
   **Fix:** Retain the short invariant and adapter-specific wake instructions; replace repeated policy explanations with links to the canonical sections.

No files were changed or credentials read; tests and live CLI/scheduler behavior were not exercised. Runtime conclusions are based on static inspection.

DIGEST 2aed7941ce454782
CURRENT 104/120
CRITICAL 0 IMPORTANT 2

## Runner evidence

```
AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-one exit=0 cli_rc=0 elapsed=154s out=533531 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
```
