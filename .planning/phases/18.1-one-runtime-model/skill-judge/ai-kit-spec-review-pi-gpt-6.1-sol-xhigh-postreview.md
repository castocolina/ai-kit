## Assessment

**CURRENT is materially better, but mixed-handler revisions still have two Important defects.** It improves host portability, fixes native-only initialization, extracts reviewer prompts, and replaces report-size polling with explicit process completion.

This is a static, read-only assessment; no CLIs or tests were run.

Paths below:
- **B**: `tmp/judge/baseline/skills/ai-kit-spec-review/`
- **C**: `skills/ai-kit-spec-review/`

Both use a **Process + Tool** pattern. `SKILL.md` shrinks from **533 to 467 lines**. Estimated Expert:Activation:Redundant content ratios are **75:15:10** for BASELINE and **80:15:5** for CURRENT.

## Dimension scores

| Dimension | BASELINE | CURRENT | Evidence and justification |
|---|---:|---:|---|
| **D1: Knowledge Delta** | **16/20** | **17/20** | Strong package-specific knowledge: worktree ownership, archetype ceilings, routing, trust gates, and report persistence. CURRENT reduces repeated prompt and cleanup prose, but the merge explanation remains unnecessarily repetitive (`C/SKILL.md:327–370`). |
| **D2: Mindset + Appropriate Procedures** | **13/15** | **14/15** | Both teach useful thinking: “archetype is a ceiling” (`SKILL.md:78`) and separate grounding from review scope. CURRENT adds explicit host-capability decisions (`C/SKILL.md:240–253`). Mixed-route sequencing remains inconsistent. |
| **D3: Anti-Pattern Quality** | **14/15** | **15/15** | Specific prohibitions explain real failure mechanisms: contaminated reviewer context, wrong-checkout grounding, missing report files, and concurrent edits. CURRENT additionally forbids inline fallback and premature subprocess completion (`C/SKILL.md:244–253,312–321`). |
| **D4: Specification Compliance** | **15/15** | **15/15** | Both have valid frontmatter, a compliant name, and a description covering WHAT, WHEN, frameworks, flags, and searchable trigger phrases (`SKILL.md:1–4`). |
| **D5: Progressive Disclosure** | **10/15** | **13/15** | BASELINE exceeds 500 lines and embeds both reviewer prompts. CURRENT extracts them behind a mandatory workflow trigger (`C/SKILL.md:255–256`), with optional diagram and routing references. Requiring the entire cross-AI reference even for native-only runs still loads avoidable material. |
| **D6: Freedom Calibration** | **11/15** | **13/15** | Exact prompts, dispatch commands, and fail-closed status handling appropriately constrain fragile orchestration. CURRENT labels Claude-specific behavior and unsupported-host fallbacks. However, fixer scope is not constrained to the findings assigned to its route. |
| **D7: Pattern Recognition** | **8/10** | **9/10** | Both have a recognizable staged orchestration process with decision tables and checkpoints. CURRENT separates templates more effectively; its core remains longer and more fragmented than necessary. |
| **D8: Practical Usability** | **8/15** | **10/15** | BASELINE contains conflicting no-path behavior, an obsolete fixer invocation (`B/references/apply-findings.md:38`), an unprinted temp-path capture, and unsafe completion polling. CURRENT repairs these and supplies useful fallbacks, but mixed-handler execution still requires the agent to reconcile contradictory instructions. |
| **Total** | **95/120** | **106/120** | BASELINE: **C, 79.2%**. CURRENT: **B, 88.3%**. |

## CURRENT findings

### Critical

None.

### Important

1. **Mixed-route fixers receive unrestricted work.**  
   **Lines:** `skills/ai-kit-spec-review/references/apply-findings.md:45–54`  
   Line 22 assigns direct-edit and native-owned findings to different handlers, but the generic fixer receives the complete `DOC_PATHS` and `EFFECTIVE_REPORT_PATH`, with no allowed-finding or archetype restriction. Its loaded skill requires addressing every CRITICAL/HIGH finding, so it can edit native-owned sections before their designated handler runs. Pass and enforce an explicit finding allowlist, or route a fused document wholly through its owning handler.

2. **Mixed-handler sequencing conflicts with the generic-fixer return path.**  
   **Lines:** `skills/ai-kit-spec-review/references/apply-findings.md:59`, conflicting with line 22 and `skills/ai-kit-spec-review/SKILL.md:413`  
   Line 22 requires generic fixing followed by native revision within one iteration, then one re-review. But Step 3a immediately sends control to Step 4, whose `Edits Applied` branch increments the iteration and jumps directly to Step 1. Following that branch skips the pending native handler and consumes review budget prematurely. Return handler results to a Step 3 coordinator; increment and re-review only after all scheduled handlers finish.

### Minor

3. **Persistence-table success branches point past required initialization.**  
   **Lines:** `skills/ai-kit-spec-review/SKILL.md:31–32`  
   “Continue to Step 1” conflicts with the intervening root, framework, lifecycle, and reviewer-resolution steps. Change these destinations to Step 0.1.

4. **Native-only loading remains unnecessarily expensive.**  
   **Line:** `skills/ai-kit-spec-review/SKILL.md:163`  
   Requiring initialization on every run is correct, but requiring the entire cross-AI reference also loads quota resolution, subprocess rationale, and status mappings for `--no-cross-ai`. Separate the mandatory bootstrap from conditional cross-AI details, with explicit “do not load” guidance.

5. **The stage-gap message claims a review that the guard never performed.**  
   **Line:** `skills/ai-kit-spec-review/SKILL.md:434`  
   The message says “Reviewed `<existing>`,” while Step 0.6’s guard at lines 139–143 stops and offers to review those documents. Use “I can review…” unless an actual reviewer dispatch occurred.

The two Important findings are retained defects present in both versions, not new CURRENT regressions.

BASELINE 95/120
CURRENT 106/120
CRITICAL 0
IMPORTANT 2
