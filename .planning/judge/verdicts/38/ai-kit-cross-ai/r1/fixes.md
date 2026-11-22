# Loop 38 round 1 fixes: ai-kit-cross-ai

Fix rule (AGENTS.md): 3 critical, important or high findings across both judges, fixed in the
skill's own files with no further round; the skill's digest is stale by design until its next loop.

- referee-one D8-1 (SKILL.md:43, high): the preflight now says that for a runtime whose ids carry a variant suffix (opencode's `#<variant>`) it checks the id without the suffix and prints `cross-ai: <runtime> preflight checks <base id>; the suffix <suffix> is not validated` (runner `listed = plan.model.replace(c.rt.modelSuffix, '')`), and a passing preflight never validates the suffix. File: skills/ai-kit-cross-ai/SKILL.md.
- referee-one D8-2 (SKILL.md:138, high): the idle watchdog now ends an attempt, not the call; the final `AIKIT-XAI` line decides: `timeout` (124), a waitable `transient` (75 with `retry_after_s=`), a bare 75 when the cycle state cannot be written, or a 69 stop once the hard waits are spent. File: skills/ai-kit-cross-ai/SKILL.md.
- referee-two D8-1 (SKILL.md:275, high): the hard-tier wait now takes exactly one of the two forms, a confirmed one-shot job (then stop without also waiting in the session) or the print-and-stop handoff, never both. File: skills/ai-kit-cross-ai/SKILL.md.
