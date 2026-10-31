Judge: my-referee-one
Reviewed-sha256: a28223d21d64c262e99b7c9a3c004c8bbf89381ba6819f6d1f38f2b3fd4c0823
Lane: AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-one exit=0 cli_rc=0 elapsed=215s out=53833 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 104
Critical: 0
Important: 2

## Dimension scores

| Dimension | Score | Assessment |
|---|---:|---|
| **D1: Knowledge Delta** | 18/20 | High-value, repository-specific knowledge: wake ownership, exact-session identity, executor interaction, reset handling and process-survival limits. Minor repetition around child/subagent prohibitions. |
| **D2: Mindset + Procedures** | 13/15 | Strong principles—preserve identity, distinguish surviving timers from companions, report evidence honestly—paired with actionable procedures. Failure handling needs a consistent fail-open rule. |
| **D3: Anti-Pattern Quality** | 14/15 | Specific prohibitions address meaningful hazards, with useful explanations of locking, identity and subagent limitations. |
| **D4: Specification Compliance** | 15/15 | Valid frontmatter and name. Description clearly supplies WHAT, WHEN, trigger vocabulary and exclusions. |
| **D5: Progressive Disclosure** | 14/15 | At 174 lines, the package remains compact and appropriately self-contained. Important verification caveats could appear nearer the initial capability claims. |
| **D6: Freedom Calibration** | 11/15 | Appropriate precision for session identity and lifecycle operations, but contradictory stop guidance and overconfident refusal reporting weaken two fragile branches. |
| **D7: Pattern Recognition** | 9/10 | Clear **Tool** pattern: command resolution, lifecycle operations, output interpretation and limitations. |
| **D8: Practical Usability** | 10/15 | Common paths are actionable. Missing-shim handling and failed refreshes need correction before an agent can reliably report and manage the wake lifecycle. |
| **Total** | **104/120** | **Grade B — good, with two operational defects.** |

Estimated knowledge ratio: **Expert 85% / Activation 13% / Redundant 2%**.

## Findings

1. **Important — Missing-shim handling contradicts the fail-open contract.**  
   **Package:** `skills/ai-kit-session-wake/SKILL.md:44`  
   The resolver prints **“STOP and tell the user”** and exits 1, whereas lines 13–14 require every missing primitive to be reported while the underlying run continues without a wake. An agent following the local error instruction can stop the work that the skill explicitly says must continue.

   **Fix:** Replace the diagnostic with an explicit instruction to report the missing shim and continue without a wake. Clarify that the failed resolver ends only wake setup, not the orchestrated task.

2. **Important — A refused refresh does not establish that no wake exists.**  
   **Package:** `skills/ai-kit-session-wake/SKILL.md:90–91`  
   The unconditional outcome **“2: refused, no wake”** conflates failure to establish or refresh a wake with absence of a previously armed wake. Refreshing an existing wake is explicitly supported at lines 53–55 and 74–75.

   **Repository evidence:** `skills/ai-kit-session-wake/ai-kit-session-wake.py:21–28` catches an import failure and exits 2 before calling the CLI entrypoint. That path performs no timer or state cleanup. If a wake already exists when the dependency becomes unavailable, this refusal does not remove it. Reporting “no wake” would therefore misstate its lifecycle.

   **Fix:** Describe exit 2 as **“arm/refresh refused; no new wake established.”** For refresh failures, preserve uncertainty about the existing wake, inspect `status` where possible, and report its state as unknown if inspection is unavailable.

## Repository checks

- **Sibling dependency and missing-dependency exit:** Supported by `skills/ai-kit-session-wake/ai-kit-session-wake.py:18–28`; resolution uses the shim’s real path and reports the sibling dependency on import failure.
- **Separation from cross-AI retry policy:** Consistent with `skills/ai-kit-cross-ai/SKILL.md:137–156`, which requires the same lane/runtime/model, runner-counted cycles and a one-shot wait rather than a repeated job. This supports the policy relationship, not an end-to-end wake-resumption guarantee.

Not checked: imported implementation, executor integration, hook wiring or live timer behavior; no commands were executed or files changed.  
Risk: actual unattended resumption remains unverified, as the package itself acknowledges.
