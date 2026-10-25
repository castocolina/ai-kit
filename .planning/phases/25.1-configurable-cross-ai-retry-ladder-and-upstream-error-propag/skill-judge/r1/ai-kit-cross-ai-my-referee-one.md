Judge: my-referee-one
Reviewed-sha256: 5d18a6276c145c97dbc38991579989c8c093267004f9a4428d4de651c5e0bd1e
Lane: AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-one exit=0 cli_rc=0 elapsed=135s out=703981 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 92
Critical: 0
Important: 3

## Skill evaluation: `ai-kit-cross-ai`

**92/120 (C).** The skill captures the one-runtime rule, soft retries, caller-owned hard waits, upstream evidence, and no-switch policy. Its main weakness is operational: the launch examples do not reliably preserve the exit code that the skill tells callers to read.

| Dimension | Score | Reason |
|---|---:|---|
| D1 Knowledge delta | 17/20 | Specific runner policy and failure distinctions |
| D2 Mindset and procedures | 12/15 | Clear ownership boundary; some workflow gaps |
| D3 Anti-patterns | 13/15 | Strong, reasoned no-switch and no-skip rules |
| D4 Specification | 15/15 | Valid frontmatter with precise activation triggers |
| D5 Progressive disclosure | 10/15 | Useful references, but no mandatory loading points |
| D6 Freedom calibration | 10/15 | Fragile wait and exit handling needs tighter examples |
| D7 Pattern | 8/10 | Coherent process-and-reference structure |
| D8 Practical usability | 7/15 | Exit-code capture and dependent guidance need repair |
| **Total** | **92/120** | |

1. **Important — Exit codes are promised but not captured.** `skills/ai-kit-cross-ai/SKILL.md:64-67` says the exit code is in a status file; its launch command at `:46-49` creates none. The background examples in `references/launch-and-wait.md:17-21,43-48` save a PID but neither save the exit code nor instruct the caller to capture `wait`’s result. **Fix:** give each lane an explicit exit-status artifact or a same-shell `wait` pattern that records `$?`, and make the read instructions match it.

2. **Important — Runtime changes are not explicitly owner-controlled.** `skills/ai-kit-cross-ai/SKILL.md:33-34` permits a config edit “done by the agent,” while `:139-143` forbids a caller from switching on failure. **Fix:** state that only an explicit owner decision may authorize a new runtime/model configuration; a failed lane must stop without the agent editing its way to another combination.

3. **Important — A linked dependent guide contradicts the canonical hard-tier rule.** `skills/ai-kit-cross-ai/references/subprocess-quota-policy.md:160-164` applies hinted exit 75 to both soft classes. But `skills/ai-kit-spec-review/references/cross-ai-dispatch.md:244-250,256-261` treats only confirmed-router hints as pending and calls exhausted transient exit 75 terminal. **Fix:** update that dispatch guide to branch on `retry_after_s=` regardless of transient versus quota, while retaining its lane-specific review bookkeeping.

4. **Minor — Reference loading is too implicit.** `skills/ai-kit-cross-ai/SKILL.md:16-18,158-163` lists the policy and host guide but never requires the relevant file to be read before a hard-tier or host-specific decision. **Fix:** put conditional “read the full reference” triggers at those workflow steps.

5. **Minor — A machine-specific test path appears in reusable guidance.** `skills/ai-kit-cross-ai/SKILL.md:125` reproduces an absolute `/tmp/...` state path. **Fix:** replace it with `<state-file-path>` while preserving the refusal format.

Read-only review; no tests or runner self-test were run. The linked dispatch-guide conflict remains a risk until corrected.

DIGEST 5d18a6276c145c97
CURRENT 92/120
CRITICAL 0 IMPORTANT 3

## Runner evidence

```
AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-one exit=0 cli_rc=0 elapsed=135s out=703981 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
```
