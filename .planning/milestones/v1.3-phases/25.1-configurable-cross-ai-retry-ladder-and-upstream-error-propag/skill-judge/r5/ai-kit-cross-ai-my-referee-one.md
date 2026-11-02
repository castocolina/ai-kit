Judge: my-referee-one
Reviewed-sha256: 89f7ffad31da99f1bde4987beee6c7fe4f6a325b6e13137bdd1801e7b6200d79
Lane: AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-one exit=0 cli_rc=0 elapsed=163s out=706424 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 101
Critical: 0
Important: 3

## ai-kit-cross-ai skill review

**Score: 101/120 (B).** The skill captures the Phase 25.1 policy well: one runtime and model per call, a runner-owned soft retry series, caller-owned hard waits, and no automatic switch of harness, provider, or model. Its main gaps are in the instructions an agent would copy to launch or report a lane.

| Dimension | Score | Reason |
|---|---:|---|
| D1 Knowledge delta | 18/20 | Strong runner-specific decisions; little generic advice. |
| D2 Mindset and procedures | 13/15 | Clear division between runner, caller, and owner. |
| D3 Anti-patterns | 13/15 | Specific prohibitions against switching and treating upstream text as instructions. |
| D4 Specification | 15/15 | Valid frontmatter and precise activation triggers. |
| D5 Progressive disclosure | 13/15 | Both references have useful loading triggers. |
| D6 Freedom calibration | 12/15 | Precise policy, but the copied launch command defaults to exec. |
| D7 Pattern | 9/10 | Effective process-and-navigation structure. |
| D8 Practical usability | 8/15 | Template discovery and hard-tier notice need clearer instructions. |

1. **Important — Template fallback is not portable.** `skills/ai-kit-cross-ai/SKILL.md:41-45` says a project without a runner can use `skills/ai-kit-spec-review/references/cross-ai.mjs`, but that path is relative to the *project*, not an installed skill. The command at `:59-63` still invokes the absent `.planning/scripts` copy. **Fix:** explain how to resolve the installed sibling template, check that active file’s header, and use the resolved path in the launch command.

2. **Important — Review callers can copy an exec invocation.** `skills/ai-kit-cross-ai/SKILL.md:59-63` and `references/launch-and-wait.md:26-30,82-86` show only `--mode exec`, although the skill explicitly covers reviews. Copying those examples for a review requests the execution contract and tool profile. **Fix:** show a review invocation or make the mode an explicitly selected value, with a warning not to use exec for reviews.

3. **Important — The hard-tier notice does not consistently relay the error evidence.** `skills/ai-kit-cross-ai/SKILL.md:139-154` requires the report and redacted upstream lines verbatim for terminal `hard-waits`/`cap` stops, but the no-scheduler exit-75 path asks only for the wait, state path, and command. The policy reference calls for those evidence lines on a stop (`references/subprocess-quota-policy.md:163-169`). **Fix:** require the report, upstream lines, and final status line in every hard-tier owner notice, including an exit 75 handed off without a scheduler.

Skipped: no runner self-test or live CLI call; this was a read-only documentation and source review, so host-specific scheduling remains unverified.
DIGEST 89f7ffad31da99f1
CURRENT 101/120
CRITICAL 0 IMPORTANT 3

## Runner evidence

```
AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-one exit=0 cli_rc=0 elapsed=163s out=706424 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
```
