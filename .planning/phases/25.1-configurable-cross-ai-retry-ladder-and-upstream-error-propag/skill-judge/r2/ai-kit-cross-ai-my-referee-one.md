Judge: my-referee-one
Reviewed-sha256: fc34de9e11130d7844424142c0b8fa1e5801368f34b94b8889f7006d2c52e94e
Lane: AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-one exit=0 cli_rc=0 elapsed=178s out=664914 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 101
Critical: 0
Important: 4

## Skill evaluation: ai-kit-cross-ai

**101/120 — B.** Strong **Tool/Process** skill with mostly project-specific knowledge (estimated E:A:R **85:12:3**). The Phase 25.1 policy correctly covers single-runtime dispatch, configurable soft retries and resets, caller-owned hard waits, redacted upstream evidence, catalog overlays, script-owned model/tool rules, and Copilot’s unverified error patterns. The related skills point to this canonical contract, and the no-switch rule is explicit.

The remaining weaknesses concern applying that policy reliably across hosts.

| Dimension | Score | Rationale |
|---|---:|---|
| D1: Knowledge delta | 18/20 | Valuable runner-specific contracts; some repeated warnings and policy summaries. |
| D2: Mindset + procedures | 13/15 | Clear ownership boundaries and result handling; GSD retry branching needs qualification. |
| D3: Anti-pattern quality | 14/15 | Strong prohibitions against switching, upstream instruction-following, premature chaining, and unsafe process termination. |
| D4: Specification compliance | 15/15 | Valid frontmatter; description provides capabilities, triggers, keywords, and exclusions. |
| D5: Progressive disclosure | 11/15 | Compact 168-line entry point and two focused references; policy-loading conditions remain implicit. |
| D6: Freedom calibration | 11/15 | Appropriately strict dispatch rules, but host/runtime coupling and scheduling instructions overconstrain incorrectly. |
| D7: Pattern recognition | 9/10 | Recognizable, well-organized Tool/Process pattern. |
| D8: Practical usability | 10/15 | Useful evidence examples and exit table; installation-path and scheduling gaps hinder execution. |
| **Total** | **101/120** | **Good foundation; operational corrections needed.** |

### Findings

1. **Important — Host guidance conflates the calling host with the selected runtime.**  
   **Evidence:** `skills/ai-kit-cross-ai/references/launch-and-wait.md:48–73` directs each host to use its matching `--runtime` (`pi`, `opencode`, `cursor`, etc.). This conflicts with the owner-selected runtime/model contract at `skills/ai-kit-cross-ai/SKILL.md:28–35`. An OpenCode caller dispatching an owner-selected pi lane should change only its launch mechanism, not dispatch to OpenCode.  
   **Fix:** Make every host section preserve the selected `$RUNTIME` and `$MODEL`; vary only background, foreground, and notification handling.

2. **Important — GSD’s retry instruction is not gated on a retry hint.**  
   **Evidence:** `skills/ai-kit-cross-ai/SKILL.md:139–142` says to wait `retry_after_s` and answer retry whenever GSD presents retry/skip/abort. It only explicitly aborts for `hard-waits` or `cap`, although `:97–102` also identifies authentication, permission, bare-75, and other terminal outcomes. Those outcomes may have no `retry_after_s`.  
   **Fix:** Say: **only exit 75 with `retry_after_s` permits waiting and retrying the unchanged lane; every terminal outcome gets its notice and abort; never skip.**

3. **Important — Exact-second hard waits are not translated into an actionable scheduler call.**  
   **Evidence:** `skills/ai-kit-cross-ai/SKILL.md:120–122,133–135` requires waiting “exactly” the supplied seconds and scheduling `CronCreate` at that interval. Configuration permits zero-second waits (`references/subprocess-quota-policy.md:88–89`), while the existing review integration explicitly rounds scheduling up to a whole minute with a 60-second minimum (`skills/ai-kit-spec-review/references/cross-ai-dispatch.md:293–298`). The canonical guide neither reconciles this discrepancy nor specifies the non-recurring tool setting.  
   **Fix:** Define the hint as an earliest retry time, provide the scheduler-compatible conversion and explicit one-shot setting, and retain manual re-invocation when scheduling is unavailable.

4. **Important — The no-project-runner fallback is repository-relative rather than installation-relative.**  
   **Evidence:** `skills/ai-kit-cross-ai/SKILL.md:39–40` tells projects without a runner to use `skills/ai-kit-spec-review/references/cross-ai.mjs`. That path works in this repository, but generally not from another project using installed skills. All launch examples still assume `.planning/scripts/cross-ai.mjs` exists (`:50–54`; `references/launch-and-wait.md:82–86`).  
   **Fix:** Resolve the template relative to the loaded skill’s directory and its sibling `ai-kit-spec-review`, then use one resolved runner path in the examples. Do not require copying files merely to launch.

5. **Minor — The detailed policy lacks explicit loading triggers.**  
   **Evidence:** `skills/ai-kit-cross-ai/SKILL.md:16–18,163–168` lists the policy reference, while only the launch reference receives a mandatory workflow trigger (`:46–48`). The detailed configuration precedence, route qualification, state lifecycle, and overlay rules can therefore remain unread when needed.  
   **Fix:** Add conditional mandatory reads for retry/configuration questions, route classification, and state/catalog diagnosis; explicitly say ordinary successful-result handling does not require loading those details.

**Scope:** Read-only inspection; no credential files read, files changed, or runner/self-tests executed. Scheduling behavior remains unverified live.

DIGEST fc34de9e11130d78
CURRENT 101/120
CRITICAL 0 IMPORTANT 4

## Runner evidence

```
AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-one exit=0 cli_rc=0 elapsed=178s out=664914 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
```
