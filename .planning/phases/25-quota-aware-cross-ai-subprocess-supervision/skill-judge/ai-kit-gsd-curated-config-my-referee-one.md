# ai-kit-gsd-curated-config — skill-judge report (opencode router-env/my-referee-one, read-only review mode)

Round 5 (evidence round), skill digest `089d13c6a215b519`, judged at commit e2bb140. Rubric: the skill-judge skill (120 points).

## Round 5: BLOCKED (the runner stopped the lane; no score)

Runner evidence lines:

```text
cross-ai: report status=quota lane=opencode/router-env/my-referee-one route=router attempts=7 cycles=0 first_failure=2026-10-25T04:25:46.794Z last_failure=2026-10-25T04:39:58.645Z stopped=deadline
AIKIT-XAI status=quota cli=opencode model=router-env/my-referee-one exit=75 cli_rc=1 elapsed=852s out=5192 tree=clean action=stop route=router rule=text-pre-dispatch pattern=verified attempts=7 cycles=0 retry_after_s=600 cycle=0
```

Upstream messages (OmniRoute, verbatim, trimmed):

```text
Service temporarily unavailable: all targets were skipped by pre-dispatch filters (Session (5h) 100% conn:dd6b6ba2; Session (5h) 100% conn:f48bcb3c)
Service temporarily unavailable: all targets were skipped by pre-dispatch filters (Session (5h) 100% conn:f48bcb3c)
[429]: The usage limit has been reached (reset after 4h 16m 3s)
```

## Last completed report from this judge (round 4, an earlier digest; reference only, not this verdict's score)

## Skill evaluation: `ai-kit-gsd-curated-config`

**102/120 (B).** The skill gives usable approval and recovery procedures. Phase 25 correctly points to the shared quota policy, treats `prefer` as an owner-controlled menu, and forbids the agent from switching CLI, harness, provider, or model after a stop. Knowledge mix is roughly **80% expert / 15% activation / 5% redundant**. Reviewed `SKILL.md`, both local references, the linked quota policy, and the relevant runner source and diff; no runtime checks were run.

| Dimension | Score | Reason |
|---|---:|---|
| D1 Knowledge delta | 17/20 | Strong GSD-specific safeguards; some repetition |
| D2 Mindset and procedures | 13/15 | Clear approval and refusal decisions |
| D3 Anti-patterns | 14/15 | Specific prohibitions with consequences |
| D4 Specification | 15/15 | Valid, searchable WHAT/WHEN description |
| D5 Progressive disclosure | 12/15 | Useful conditional references; long core file |
| D6 Freedom calibration | 12/15 | Tight controls, but edited-runner assurance is too broad |
| D7 Pattern recognition | 8/10 | Sound process/navigation hybrid |
| D8 Practical usability | 11/15 | Stop handling is clear once the policy is loaded |
| **Total** | **102/120** | |

### Findings

1. **Important — An edited template-7 header is not proof of the no-fallback policy.** `SKILL.md:260-265` says an edited current-template runner stays ready and directs readers to its line-2 version header; `references/runner.md:54-59` says only an active template-7 copy carries the ladder. But readiness checks the version without requiring a pristine body (`ai_kit_gsd_curated_config/cross_ai_script.py:300-304`). **Fix:** distinguish tool-reported readiness from policy verification. For an edited active runner, require inspection of its changes before asserting that it still runs one CLI with the Phase 25 ladder.

2. **Important — The four-hour, cross-call behavior is absent from the approval path.** `SKILL.md:105-112` asks users to review `router_backed`, while `SKILL.md:215-224` names the ladder but requires reading its policy only *after* a non-`ok` dispatch. The linked policy specifies same-session then new-session attempts, cooldown cycles, a four-hour cap, and host-dependent re-entry (`subprocess-quota-policy.md:26-51,80-94`). **Fix:** add a brief pre-dispatch summary of those consequences where the runner choice is approved; retain the policy link for exact stop handling.

3. **Minor — Repeated guidance costs core-context space.** The `.new`/template-header rule appears at `SKILL.md:260-267`, `SKILL.md:346`, and `SKILL.md:367-369`. **Fix:** keep the decision rule in the cross-AI section and let the command table and NEVER list point back to it.

DIGEST bf2a458d046ad20c
CURRENT 102/120
CRITICAL 0 IMPORTANT 2
