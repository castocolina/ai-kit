Judge: my-referee-one
Reviewed-sha256: 4c59f5c4841437e80d5f593ecdf95ef8d2cee6209aa8005901a69ff1db1a2697
Lane: AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-one exit=0 cli_rc=0 elapsed=173s out=587200 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 104
Critical: 0
Important: 3

## Skill evaluation: ai-kit-cross-ai

**104/120 — B (86.7%).** A strong Process/Tool skill with mostly project-specific knowledge (approximately **80:18:2 Expert:Activation:Redundant**). Reviewed the complete 168-line `SKILL.md`, both references (86 and 180 lines), the requested diff, and relevant runner implementation.

The Phase 25.1 policy is largely captured correctly: one runtime per call, first-entry-only `--prefer`, configurable soft retries and session resets, caller-owned hard waits, redacted upstream evidence, catalog overlays, script-owned model grammars/tool profiles, and appropriately unverified Copilot behavior. The no-switch rule is explicit and includes upstream hints and GSD’s native-executor fallback.

| Dimension | Score | Assessment |
|---|---:|---|
| D1: Knowledge Delta | 19/20 | High-value runner contracts; modest repetition across body and references. |
| D2: Mindset + Procedures | 13/15 | Good ownership and evidence principles; invocation prerequisites need tightening. |
| D3: Anti-Pattern Quality | 15/15 | Specific prohibitions with consequences: native fallback, premature chaining, argv exposure. |
| D4: Specification Compliance | 15/15 | Valid frontmatter; description clearly identifies capabilities, triggers, and exclusions. |
| D5: Progressive Disclosure | 12/15 | Compact body and mandatory launch reference, but the policy reference lacks a conditional loading requirement. |
| D6: Freedom Calibration | 11/15 | Strong no-switch constraints weakened by host/target conflation and unconditional GSD retry wording. |
| D7: Pattern Recognition | 9/10 | Clear Process/Tool structure; some duplicated policy prose. |
| D8: Practical Usability | 10/15 | Useful examples and exit table, but older runners and terminal GSD failures lack safe routing. |
| **Total** | **104/120** | |

### Findings

1. **Important — No template-8 prerequisite before launching an existing project runner.**  
   **Evidence:** `skills/ai-kit-cross-ai/SKILL.md:39-40` selects the project copy solely by existence, then `:52` invokes `--runtime`. Yet `skills/ai-kit-gsd-curated-config/references/runner.md:65-68` documents that template 7 rejects that flag and templates 3–6 can fall back to another CLI. Existence does not establish the policy this skill promises.  
   **Fix:** Require checking the **active** runner’s template header before launch. Below template 8, stop and route to `ensure-runner`; require resolution of an edited runner’s `.new` upgrade before proceeding.

2. **Important — GSD retry guidance is unconditional, unlike the exit-code contract.**  
   **Evidence:** `skills/ai-kit-cross-ai/SKILL.md:139-142` says to wait `retry_after_s` and answer retry whenever GSD offers retry/skip/abort. But `:97-100` distinguishes invocation errors, terminal owner stops, and bare exit 75—all potentially lacking that field. Section 7 also does not preserve the non-scheduling-host handoff at `:133-135`.  
   **Fix:** Permit retry **only** for exit 75 carrying `retry_after_s`. For terminal failures, notify and abort; for invocation errors, stop for correction. Without a scheduling primitive, print the handoff details and leave retry to the owner.

3. **Important — Host-specific instructions can override the owner-selected target runtime.**  
   **Evidence:** `skills/ai-kit-cross-ai/references/launch-and-wait.md:3-5` defines these as **host** patterns, but `:50-57` directs pi and OpenCode hosts to use `--runtime pi` and `--runtime opencode`. That conflicts with owner selection in `skills/ai-kit-cross-ai/SKILL.md:33-35`. Also, `SKILL.md:133-135` categorically denies other hosts a scheduling primitive, while the reference labels its host claims unverified.  
   **Fix:** Keep `$RUNTIME` and `$MODEL` unchanged across every host example. Select background/foreground and wake behavior by available host capabilities—not by the target runtime—and qualify unverified capability claims consistently.

4. **Minor — The canonical policy reference has no required loading trigger.**  
   **Evidence:** `skills/ai-kit-cross-ai/SKILL.md:16-18,165-166` lists the policy reference, whereas `:46-48` explicitly requires reading the launch reference. Retry configuration, route confirmation, catalog overlays, and session-reset exceptions can therefore remain unloaded.  
   **Fix:** Add a conditional requirement to read the policy before configuring/classifying failures, interpreting route-dependent retries, or changing retry/catalog settings; say it need not be loaded for an ordinary successful result.

**Limits:** Static review only; no runner, self-tests, or live CLI calls executed. No files changed or credentials read. Host wake behavior remains unverified.

DIGEST 4c59f5c4841437e8
CURRENT 104/120
CRITICAL 0 IMPORTANT 3

## Runner evidence

```
AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-one exit=0 cli_rc=0 elapsed=173s out=587200 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
```
