Judge: my-referee-one
Reviewed-sha256: 81ba60cd25342e7aec8d9f47ce81a9a00d606a7368cec6fe570a688701372eef
Lane: AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-one exit=0 cli_rc=0 elapsed=112s out=633510 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 100
Critical: 0
Important: 3

## Skill evaluation: ai-kit-spec-config

**Score: 100/120 — B (83.3%).** A strong **Process/Tool** skill with substantial repository-specific knowledge (estimated Expert:Activation:Redundant ratio **85:10:5**). Its write safeguards and model-selection workflow are thorough, but the Phase 25.1 addition does not fully reconcile older fallback guidance or the probe’s error-reporting limitations.

Reviewed the complete 493-line `SKILL.md`, the complete 344-line reference, the requested diff, and relevant linked policy/implementation source. The diff correctly links the canonical `ai-kit-cross-ai` skill and delegates model grammar to the runner. It need not duplicate the retry series, hard-tier configuration, catalog overlay, or tool profiles.

| Dimension | Score | Rationale |
|---|---:|---|
| D1: Knowledge Delta | 17/20 | Valuable routing, catalog, trust and serialization knowledge; repeated explanations dilute it. |
| D2: Mindset + Procedures | 13/15 | Good user-agency and provenance decisions, with precise procedures; failure-handling boundary remains unclear. |
| D3: Anti-Pattern Quality | 13/15 | Specific, justified prohibitions; missing an explicit no-switch guard at the probe/failure boundary. |
| D4: Specification Compliance | 15/15 | Valid metadata with clear capabilities, triggers and flags. |
| D5: Progressive Disclosure | 13/15 | Excellent conditional reference/profile loading, but the main workflow remains dense and repetitive. |
| D6: Freedom Calibration | 11/15 | Strong replacement and trust gates; weaker constraints around policy loading and unverified runtimes. |
| D7: Pattern Recognition | 9/10 | Coherent Process/Tool hybrid with clear checkpoints. |
| D8: Practical Usability | 9/15 | Actionable common paths, but truncated evidence and incomplete Copilot guidance undermine edge cases. |
| **Total** | **100/120** | **Important corrections needed despite the numerical B grade.** |

### Findings

1. **Important — Legacy fallback wording is not bounded by the canonical no-switch policy.**  
   **Evidence:** `skills/ai-kit-spec-config/SKILL.md:241–243` merely points to the policy, while `:335–345` promotes session-default entries as fallback and states that “quota/availability failures decide fallback.” `:364–368` describes reviewers being tried in order. The canonical `skills/ai-kit-cross-ai/SKILL.md:139–143` forbids callers from switching harness, provider or model after failure.  
   **Impact:** An agent can interpret the older wording as permission to advance the ladder or use the native session after a failed lane. The distinction between initial roster selection and recovery of an already-started lane is not explicit.  
   **Fix:** Require loading `ai-kit-cross-ai` before live probe/dispatch operations. State that roster selection occurs before a lane starts; once selected, failures follow the canonical same-lane wait/notify/stop policy, never automatic ladder advancement or native substitution.

2. **Important — The promised upstream error evidence is actually a truncated prefix.**  
   **Evidence:** `skills/ai-kit-spec-config/SKILL.md:293–298` tells the agent that `detail` is the CLI’s real error text and to show it verbatim. However, `skills/ai-kit-spec-review/ai_kit_spec/quota.py:215–220` returns only `detail[:300]`; `:256–265` constructs that detail from collected runner stderr. The canonical policy requires the report, redacted upstream lines and final status trailer (`skills/ai-kit-cross-ai/references/subprocess-quota-policy.md:116–130`).  
   **Impact:** Initial runner messages can consume the prefix before the upstream body or final status appears. Showing this field verbatim does not satisfy the advertised error pass-through or establish a hard-tier outcome.  
   **Fix:** Expose the complete redacted evidence trailer through the probe interface, then have Step 2.5 inspect it under the canonical policy. Until then, explicitly label `detail` as truncated diagnostic output, not the complete upstream error.

3. **Important — Copilot falls through without the required uncertainty and permission disclosure.**  
   **Evidence:** `skills/ai-kit-spec-config/references/cli-model-selection.md:25–27` claims every runtime except Grok lists models, despite Copilot having no listing configured in `skills/ai-kit-spec-review/ai_kit_spec/detection.py:117–118`. `skills/ai-kit-spec-config/SKILL.md:232–234` allows missing profiles, but the permission warning at `:300` requires a profile’s `read_only: unconfirmed` field. No Copilot profile exists. The canonical policy labels every Copilot error pattern unverified (`skills/ai-kit-cross-ai/references/subprocess-quota-policy.md:145–146`).  
   **Impact:** Copilot is selectable, but its missing profile bypasses the warning mechanism and its verification limits are not surfaced.  
   **Fix:** Derive listing availability from the actual snapshot instead of the exhaustive prose claim. For selected runtimes without a profile, explicitly disclose that read-only enforcement is unconfirmed; identify Copilot’s unverified status without inventing guarantees.

4. **Minor — Repeated rationale adds avoidable loading cost.**  
   **Evidence:** Explicit-purpose handling is repeated in `skills/ai-kit-spec-config/SKILL.md:311–313`, `:352–359`, `:398–402`, and `references/cli-model-selection.md:295–305`.  
   **Fix:** Keep the full invariant once at the write boundary; elsewhere retain only where the value is captured and carried forward. This preserves the safeguard without repeatedly explaining the legacy default.

Read-only review only: no files changed, credentials read, or live probes/tests run. Runtime behavior was checked against source, not exercised.

DIGEST 81ba60cd25342e7a
CURRENT 100/120
CRITICAL 0 IMPORTANT 3

## Runner evidence

```
AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-one exit=0 cli_rc=0 elapsed=112s out=633510 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
```
