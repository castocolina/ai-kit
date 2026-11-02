Judge: my-referee-one
Reviewed-sha256: 6efb7723c3ca635d131295da929abda0a3fdc89e12ab88b5d3fa1a25d2c3911a
Lane: AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-one exit=0 cli_rc=0 elapsed=339s out=1079926 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 82
Critical: 2
Important: 2

# Skill evaluation: `ai-kit-spec-review`

**82/120 (D).** The skill has strong framework-aware review guidance, but its pre-dispatch selection and hard-tier instructions do not consistently uphold the new cross-AI policy.

| Dimension | Score | Assessment |
|---|---:|---|
| D1 Knowledge delta | 16/20 | Worktree, lifecycle, and routing guidance is specific. |
| D2 Mindset and procedures | 12/15 | Good stage-aware decisions and dispatch sequence. |
| D3 Anti-patterns | 11/15 | Concrete safeguards, though some policy is duplicated. |
| D4 Specification | 14/15 | Valid frontmatter with clear triggers. |
| D5 Progressive disclosure | 10/15 | Mandatory references help, but the 480-line entry point is dense. |
| D6 Freedom calibration | 7/15 | Fragile retry decisions have conflicting instructions. |
| D7 Pattern | 7/10 | Recognizable process skill with some stale branches. |
| D8 Practical usability | 5/15 | The contradictions can change which reviewer runs or strand a pending lane. |
| **Total** | **82/120** | |

## Findings

1. **Critical — Automatic pre-dispatch provider/model switching remains.** `skills/ai-kit-spec-review/SKILL.md:157-166` instructs `probe-quota` to walk past a failed entry to another provider, then to the session default. This conflicts with the requested no-switch rule, even though the skill calls it “pre-dispatch.” **Fix:** on a failed selected probe, surface that entry’s result for the owner to decide; do not advance the roster automatically.

2. **Critical — The mandatory resume reference excludes transient hard-tier waits.** `skills/ai-kit-spec-review/references/cross-ai-dispatch.md:244-261` defines a pending lane only as `route=router`, and calls an exhausted transient ladder without `retry_after_s=`. Template 8 can issue `retry_after_s=` for a transient lane on any route; the main skill recognizes this at `SKILL.md:326-331`. **Fix:** make the pending/resume procedure depend on exit 75 **with `retry_after_s=`**, regardless of route, and update its headings, sibling handling, and Surface row (`SKILL.md:383,440`).

3. **Important — Multiline output can hide the matched upstream error.** `skills/ai-kit-spec-review/references/cross-ai.mjs:1803-1813,1844-1864` splits on literal `\\n` rather than a newline. A later event can consequently carry the entire output as its raw body and disappear under the 2,000-character display cap. **Fix:** split on `'\n'` and add a long preceding-event fixture.

4. **Important — Child output is retained without a capture limit.** `skills/ai-kit-spec-review/references/cross-ai.mjs:3232-3233,3258-3262,3289-3295` accumulates stdout and stderr until completion; the bounded diagnostic relay does not bound those arrays. A noisy CLI could exhaust memory before producing the promised status line. **Fix:** cap captured output, preserve a bounded diagnostic tail, and fail explicitly when the cap is reached.

5. **Minor — Reference wording still names template 7 and a router-only cooldown.** `skills/ai-kit-spec-review/references/cross-ai-dispatch.md:313,348,355` can lead readers back to the superseded policy despite its new canonical links. **Fix:** update these descriptions to template 8 and the route-independent hard tier.

Read-only source review; I did not run self-tests or live CLIs. Copilot’s real review-mode permissions remain unverified.

DIGEST 6efb7723c3ca635d
CURRENT 82/120
CRITICAL 2 IMPORTANT 2

## Runner evidence

```
AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-one exit=0 cli_rc=0 elapsed=339s out=1079926 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
```
