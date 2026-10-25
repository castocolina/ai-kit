# ai-kit-spec-execute-superpowers — skill-judge report (opencode router-env/my-referee-one, read-only review mode)

Round 5 (evidence round), skill digest `beff20e2e6df85d9`, judged at commit e2bb140. Rubric: the skill-judge skill (120 points).

## Round 5: BLOCKED (the runner stopped the lane; no score)

Runner evidence lines:

```text
cross-ai: report status=quota lane=opencode/router-env/my-referee-one route=router attempts=7 cycles=0 first_failure=2026-10-25T04:25:46.794Z last_failure=2026-10-25T04:41:49.507Z stopped=deadline
AIKIT-XAI status=quota cli=opencode model=router-env/my-referee-one exit=75 cli_rc=1 elapsed=963s out=5192 tree=clean action=stop route=router rule=text-pre-dispatch pattern=verified attempts=7 cycles=0 retry_after_s=600 cycle=0
```

Upstream messages (OmniRoute, verbatim, trimmed):

```text
Service temporarily unavailable: all targets were skipped by pre-dispatch filters (Session (5h) 100% conn:dd6b6ba2; Session (5h) 100% conn:f48bcb3c)
Service temporarily unavailable: all targets were skipped by pre-dispatch filters (Session (5h) 100% conn:f48bcb3c)
```

## Last completed report from this judge (round 4, an earlier digest; reference only, not this verdict's score)

## Skill evaluation: `ai-kit-spec-execute-superpowers`

**Score: 93/120 (C).** The skill captures substantial domain-specific knowledge and correctly points to the shared failure ladder. Its main weakness is that two execution paths do not fully honor or explain the Phase 25 stop contract.

| Dimension | Score | Max | Assessment |
|---|---:|---:|---|
| D1 Knowledge delta | 16 | 20 | Strong quota, exclusion, and resume edge cases; some repeated procedure |
| D2 Mindset and procedures | 12 | 15 | Explains why state and escalation choices matter |
| D3 Anti-patterns | 13 | 15 | Specific NEVER rules with consequences |
| D4 Specification and description | 14 | 15 | Valid, precise trigger description |
| D5 Progressive disclosure | 11 | 15 | Mandatory reference triggers, but a long main workflow |
| D6 Freedom calibration | 10 | 15 | Strict external-stop rule; less constrained native model choice |
| D7 Pattern | 8 | 10 | Clear process skill |
| D8 Practical usability | 9 | 15 | Good quota path; gaps in other stop and wake paths |

1. **Critical — Native fix rounds can change models without an owner choice.** `SKILL.md:205-212` leaves Claude Code’s round-4/5 model bump to the other skill’s “own judgment, with no ladder,” while `SKILL.md:405-410` says the owner decides and the skill never switches models on its own. **Fix:** require an explicit owner-approved model for that bump, or state and justify a narrowly defined exception to the no-autonomous-switch rule.

2. **Important — The non-quota stop lacks a resumable-state instruction.** `SKILL.md:394-400` relays evidence and stops on `"real_error"` but never writes or reports a resume path; the shared policy calls for resumable state where the skill writes it (`skills/ai-kit-spec-review/references/subprocess-quota-policy.md:80-91`). **Fix:** specify what state is saved for this branch and how the owner resumes without silently selecting another candidate.

3. **Important — The one-shot wake does not clearly rejoin task review.** The scheduled prompt ends at “Run Step 3 point 3 … and point 4” (`SKILL.md:369-382`). A successful dispatch says to continue with the implementer report (`SKILL.md:308-316`), but the wake also says not to read the plan. **Fix:** give the wake an explicit successful-completion handoff to the existing task-review controller, with the state needed to do it.

4. **Minor — The scheduler-free instruction promises a command but supplies a prompt.** `SKILL.md:49-53` says to print a “re-invoke command”; `SKILL.md:360-382` supplies a prompt template instead. **Fix:** either provide an executable re-invoke command or consistently call it an owner-run prompt.

This was a read-only review; I did not run the skill or its tests. The wake-path assessment is based on its written instructions.

DIGEST 23f9b4fbd9cdb4a6
CURRENT 93/120
CRITICAL 1 IMPORTANT 2
