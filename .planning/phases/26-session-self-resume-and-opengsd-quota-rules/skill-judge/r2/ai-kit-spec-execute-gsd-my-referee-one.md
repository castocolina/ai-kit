Judge: my-referee-one
Reviewed-sha256: 8cef3656bbba9bfa154bbdb15d0361b359afc2e99b349e069b4e8405506056b2
Lane: AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-one exit=0 cli_rc=0 elapsed=1017s out=734918 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 101
Critical: 0
Important: 3

## Dimension scores

| Dimension | Score | Assessment |
|---|---:|---|
| **D1: Knowledge Delta** | **17/20** | Strong project-specific knowledge: ownership-aware cleanup, hook-token restrictions, native-tier exceptions, and retry semantics. Repeated stop instructions dilute it slightly. |
| **D2: Mindset + Procedures** | **14/15** | Explains why fresh resolution and stale-hook cleanup matter (`SKILL.md:200–206`), then supplies concrete procedures. |
| **D3: Anti-Pattern Quality** | **15/15** | Excellent, consequential prohibitions: no implicit native fallback, no redispatch to another candidate, and no `skip` answer (`SKILL.md:10–30`). |
| **D4: Specification Compliance** | **14/15** | Valid name and frontmatter; description covers WHAT, WHEN, and searchable triggers. Its 820 characters include implementation detail better left in the body. |
| **D5: Progressive Disclosure** | **12/15** | Mandatory hook-setup loading and optional rationale loading are explicit. Nevertheless, the 459-line, approximately 30.8 KB core retains substantial branch-specific recovery detail. |
| **D6: Freedom Calibration** | **12/15** | Appropriately restrictive around configuration, trust, and dispatch. Shell-state and terminal-cleanup gaps undermine otherwise precise instructions. |
| **D7: Pattern Recognition** | **9/10** | Clear Tool/Process hybrid: executable blocks, dispatch branches, checkpoints, and failure handling. |
| **D8: Practical Usability** | **8/15** | Common paths are actionable, but the successful hook-setup output is defective, native-guidance delivery is not guaranteed, and one terminal path lacks explicit wake cleanup. |
| **Total** | **101/120** | **Grade B — strong domain knowledge, with correctness and usability fixes needed.** |

**Knowledge mix:** approximately **80% Expert / 10% Activation / 10% Redundant**.

**Package sizes:** `SKILL.md`: 459 lines; `references/cross-ai-hook-setup.md`: 77 lines; `references/dispatch-notes.md`: 63 lines.

## Findings

1. **Important — Successful hook setup prints an empty dispatch mode.**  
   **Location:** `skills/ai-kit-spec-execute-gsd/references/cross-ai-hook-setup.md:35–54`

   The successful branch never assigns `RESULT_MODE`, but line 54 prints it. The reference’s input-variable list at lines 4–6 also omits it. Since `SKILL.md:86–89` explicitly requires fresh shells, the successful call cannot rely on Step 1’s shell variable surviving.

   An in-memory simulation with successful producer, runner, and write stubs returned:
   ```text
   exit=0
   RESULT_MODE=
   ```
   This contradicts the documented `RESULT_MODE=cross_ai_hook` success outcome at lines 70–77 and leaves the agent without the promised authoritative mode for subsequent steps.

   **Fix:** Initialize `RESULT_MODE=cross_ai_hook` inside this block, or assign it explicitly after a successful write. Distinguish fixed input substitutions from mutable block-local variables so fallback assignments remain effective.

2. **Important — The native-tooling guidance is not guaranteed to reach native executors.**  
   **Location:** `skills/ai-kit-spec-execute-gsd/SKILL.md:321–342`

   The procedure modifies only `$PHASE_PROMPT_FILE`, which the skill permits to be a phase **prompt/context file** (`SKILL.md:91–103`), then states that the block reaches GSD’s native executor.

   The repository does not support that unconditional claim. Native executor required reading includes each executor’s own PLAN.md at `.claude/gsd-core/workflows/execute-phase.md:704–711`. Phase CONTEXT.md and RESEARCH.md are included conditionally, only when `CONTEXT_WINDOW >= 500000`, at lines 712–716. Consequently:
   - Appending to a context file does not guarantee delivery at smaller context-window settings.
   - Appending to one plan does not deliver the guidance to executors reading other plans in the phase.

   **Fix:** Put the guidance in each relevant native executor’s actual plan file, or use another verified, universally included handoff artifact. Narrow the claim until delivery is guaranteed.

3. **Important — Skill-resolution failure does not explicitly close an already-owned session wake.**  
   **Location:** `skills/ai-kit-spec-execute-gsd/SKILL.md:443–450`

   The wake is armed before GSD skill resolution (`SKILL.md:346–395`). If resolution subsequently fails, lines 443–447 direct the agent to **STOP, do not retry**, without routing through wake cleanup. The close instructions name phase completion and stops answered `abort`, neither of which describes this environment-error branch.

   This matters because the sibling contract describes a surviving systemd timer that resumes the session (`skills/ai-kit-session-wake/SKILL.md:8–14`); `done` removes it or arranges removal after an active resume (`skills/ai-kit-session-wake/SKILL.md:123–136`). Leaving it armed can repeatedly resume a run explicitly told not to retry.

   **Fix:** Route every terminal exit after arming—including missing or unreadable GSD definitions—through the owned-wake close step. Keep the delayed-retry branch as the explicit exception.

4. **Minor — Repeated recovery policy increases the mandatory reading burden.**  
   **Location:** `skills/ai-kit-spec-execute-gsd/SKILL.md:20–30`, `158–163`, and `399–441`

   The same no-reselection, unchanged-hook, retry-only-after-delay, and owner-resume rules appear repeatedly, alongside a mandatory sibling contract covering the same policy. The repetition adds maintenance points and makes branch differences harder to spot.

   **Fix:** Keep a short invariant list in the core and one authoritative recovery decision table. Preserve the explicit loading triggers; those are already effective.

**Verification limits:** No workflow, test suite, scheduler, or live AI dispatch was run. Runtime claims were checked statically where accessible; the hook-mode defect was also reproduced with an in-memory, stubbed shell simulation.
