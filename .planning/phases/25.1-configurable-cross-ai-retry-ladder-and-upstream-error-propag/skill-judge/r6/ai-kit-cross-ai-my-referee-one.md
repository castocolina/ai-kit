Judge: my-referee-one
Reviewed-sha256: 17d7161a3b98c5573e3914240a8e0772571594c1e45996303013a032fb000bc3
Lane: AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-one exit=0 cli_rc=0 elapsed=196s out=611565 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 106
Critical: 0
Important: 2

## Skill evaluation: ai-kit-cross-ai

**106/120 — Grade B.** Clear Process/Tool pattern with substantial repository-specific knowledge (estimated Expert:Activation:Redundant ratio **85:12:3**). Reviewed the 191-line `SKILL.md`, both references (86 and 180 lines), the requested diff, and relevant runner implementation.

Phase 25.1’s central policy is represented correctly: one runtime per call, first-entry-only `--prefer`, configurable soft retries and resets, caller-owned hard waits, redacted upstream evidence, catalog overlays, script-owned grammars/profiles, and Copilot caveats. **No autonomous harness, provider, or model switch is prescribed.** Sibling skills point back to this canonical contract.

| Dimension | Score | Assessment |
|---|---:|---|
| D1 Knowledge Delta | 18/20 | High-value runner-specific guidance; some repeated warnings and examples. |
| D2 Mindset + Procedures | 14/15 | Strong ownership boundaries and result-driven workflow. |
| D3 Anti-Pattern Quality | 15/15 | Specific prohibitions with reasons: no switching, no upstream-directed waits, no premature chaining. |
| D4 Specification Compliance | 15/15 | Valid frontmatter; precise capabilities, triggers, and exclusions. |
| D5 Progressive Disclosure | 13/15 | Useful conditional references, but a required notice rule is hidden behind an optional read. |
| D6 Freedom Calibration | 12/15 | Appropriate constraints overall; host-specific instructions contradict capability-based routing. |
| D7 Pattern Recognition | 9/10 | Coherent Process/Tool structure; minor duplication. |
| D8 Practical Usability | 10/15 | Operational gaps in host selection, intermediate notices, and fallback examples. |
| **Total** | **106/120** | **Good, with actionable corrections.** |

### Findings

1. **Important — OpenCode host guidance disregards available background capabilities.**  
   **Evidence:** `skills/ai-kit-cross-ai/references/launch-and-wait.md:3–6` selects patterns by host capability, but `:55–58` assigns OpenCode a foreground wait, and `:75–78` categorically assigns every non-Claude host that path. This session’s shell tool supports background execution with completion notifications. CLI help is not evidence of the hosting agent’s tool capabilities.  
   **Fix:** Make capability detection authoritative. Separate background completion notifications from one-shot scheduling; use foreground execution only when the host actually lacks a background primitive.

2. **Important — Intermediate hard-tier stops lack a mandatory evidence-relay instruction on the normal loading path.**  
   **Evidence:** `skills/ai-kit-cross-ai/SKILL.md:19–21` says a plain launch/read need not load the policy reference. Its result step (`:75–101`) tells callers to read evidence, while explicit verbatim user relay appears only for terminal `hard-waits`/`cap` stops (`:141–156`). Conversely, `references/subprocess-quota-policy.md:163–169` requires evidence relay on a stop generally. An ordinary exit 75 can therefore reach scheduling or handoff without showing the upstream error.  
   **Fix:** In `SKILL.md` section 6, require relaying the report, available upstream lines, and final status line **before either scheduling or handing off every nonzero stop**.

3. **Minor — A `.new` file is incorrectly treated as sufficient evidence that the active runner is unusable.**  
   **Evidence:** `skills/ai-kit-cross-ai/SKILL.md:41–45` stops when a `.new` exists, independently of the active runner’s version. The linked upgrade documentation says readiness is not determined by `.new` existence (`skills/ai-kit-gsd-curated-config/references/runner.md:66–71`). A leftover `.new` can unnecessarily block a valid template-8 runner.  
   **Fix:** Gate on the active runner’s verified version/readiness; treat `.new` as an upgrade-review notice rather than an unconditional refusal.

4. **Minor — The documented template fallback is not carried through into launch examples.**  
   **Evidence:** `skills/ai-kit-cross-ai/SKILL.md:41–43` permits using the template when the project copy is absent, but its example (`:59–63`) and all reference examples (`references/launch-and-wait.md:26–29,82–85`) still invoke the absent project copy. The template path is also expressed relative to an ai-kit checkout, not an installed skill location.  
   **Fix:** Resolve one `RUNNER` path—project copy first, otherwise the sibling skill’s installed template—and use `node "$RUNNER"` consistently in launch and re-invoke examples.

No files changed or credentials read. Static review only: runner self-tests and live CLI/scheduler behavior were not executed.

DIGEST 17d7161a3b98c557
CURRENT 106/120
CRITICAL 0 IMPORTANT 2

## Runner evidence

```
AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-one exit=0 cli_rc=0 elapsed=196s out=611565 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
```
