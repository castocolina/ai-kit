Judge: my-referee-one
Reviewed-sha256: 757174ac243c233f8f4c7866b8318f3a1f405c04f3b3cdf64a11c6076b7ae919
Lane: AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-one exit=0 cli_rc=0 elapsed=137s out=763693 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 100
Critical: 0
Important: 4

## Assessment

**100/120 — B (83.3%).** Strong **Process/Tool** skill with valuable exclusion-state, report-preservation and resume rules. Estimated knowledge ratio: **80% expert / 15% activation / 5% redundant**.

Read the complete supplied rubric, `SKILL.md`, all three references, the shim and relevant implementation paths, and the requested diff. Phase 25.1 correctly adds transient hard-tier handling, upstream-evidence relay and links to the canonical policy. Model grammars, profiles, catalog overlays and Copilot mechanics appropriately remain delegated rather than duplicated here.

| Dimension | Score | Assessment |
|---|---:|---|
| D1: Knowledge Delta | 18/20 | Substantial project-specific expertise; some repeated explanations. |
| D2: Mindset + Procedures | 13/15 | Strong state invariants and exact procedures; policy conflicts remain. |
| D3: Anti-Pattern Quality | 14/15 | Specific prohibitions explain real failure modes. |
| D4: Specification Compliance | 15/15 | Valid metadata with precise capabilities, triggers and exclusions. |
| D5: Progressive Disclosure | 11/15 | Good reference triggers, but canonical-policy loading is no longer required. |
| D6: Freedom Calibration | 10/15 | Tight dispatch controls undermined by autonomous escalation and altered waits. |
| D7: Pattern Recognition | 9/10 | Clear phased workflow with conditional references. |
| D8: Practical Usability | 10/15 | Detailed happy/recovery paths; failed-run persistence is incomplete. |
| **Total** | **100/120** | |

## Findings

Paths below are relative to `skills/ai-kit-spec-execute-superpowers/`.

1. **Important — Automatic capability escalation conflicts with the no-switch requirement.**  
   **Evidence:** `SKILL.md:200–208,436–448` and `references/escalation.md:20–25,71–78` authorize choosing another model—and potentially runtime/provider—after unsuccessful task-review rounds. `SKILL.md:409–415` calls this pre-dispatch selection while admitting owner confirmation remains pending. Moving the choice before the next dispatch does not itself establish owner authorization.  
   **Fix:** Preserve initial pair selection, but require an explicit owner-selected replacement before changing a task’s existing pair, including rounds 4–5 and native model bumps.

2. **Important — Non-quota failures do not persist the injection needed for safe resume.**  
   **Evidence:** `SKILL.md:351–355` persists `injection_json` only in the quota branch; `SKILL.md:398–404` stops on `real_error` without an equivalent state write. Yet `references/state-management.md:61–66` uses the presence of `injection_json` to distinguish pinned redispatch from Step 2 re-resolution. A first-dispatch crash, auth failure or terminal transient stop can therefore leave no pinned resume record.  
   **Fix:** Persist the current injection and task state for every failed external dispatch before stopping. Keep automatic scheduling restricted to qualifying exit-75 outcomes.

3. **Important — Scheduling changes the configured hard wait.**  
   **Evidence:** `SKILL.md:356–364` imposes a 60-second minimum and rounds to the next whole minute. The canonical contract requires exactly `retry_after_s` (`skills/ai-kit-cross-ai/SKILL.md:115–117`), and its policy permits configurable waits down to zero (`skills/ai-kit-cross-ai/references/subprocess-quota-policy.md:88–89`). Defaults conceal this mismatch; custom waits expose it.  
   **Fix:** Do not silently transform the interval. Use an exact-delay mechanism where supported; otherwise report the scheduler limitation and provide the unchanged delay and manual reinvocation.

4. **Important — The canonical policy is linked but has no mandatory loading trigger.**  
   **Evidence:** `SKILL.md:39–42,52–53` supplies links, while the diff removes the former mandatory read before dispatch and before acting on stops. Unlike the state and escalation references, nothing explicitly requires loading the new canonical skill. This matters because its upstream-data trust rule and stopped-record handling are not fully reproduced locally.  
   **Fix:** Require reading `../ai-kit-cross-ai/SKILL.md` before the first external dispatch and before handling a wait/stop. Follow its conditional references rather than maintaining a second policy here.

5. **Minor — Ownership language is contradictory.**  
   **Evidence:** `SKILL.md:8` says the skill “never dispatches a task itself,” but `SKILL.md:261–274` instructs it to invoke `dispatch-task`. `SKILL.md:413–414` also says the runner “owns the ladder,” obscuring the distinction between candidate selection, soft retries and caller-owned hard waits.  
   **Fix:** Say that the skill adapts the harness’s implementer dispatch without owning its review loop; consistently name the runner’s **soft retry series** and the caller’s **hard-tier wait**.

No files were changed or credentials read. Runtime tests were not run under the read-only constraint; the findings are based on source and documentation inspection.

DIGEST 757174ac243c233f
CURRENT 100/120
CRITICAL 0 IMPORTANT 4

## Runner evidence

```
AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-one exit=0 cli_rc=0 elapsed=137s out=763693 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
```
