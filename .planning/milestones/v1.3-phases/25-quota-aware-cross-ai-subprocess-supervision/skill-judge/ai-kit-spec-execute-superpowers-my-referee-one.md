# ai-kit-spec-execute-superpowers — skill-judge report (opencode router-env/my-referee-one, read-only review mode)

Round 6, skill digest `9fa91a3b0024ebf5`, judged at commit 12083a7. Rubric: the skill-judge skill (120 points).

Runner status: `AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-one exit=0 cli_rc=0 elapsed=272s out=824420 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0`

# Skill evaluation: `ai-kit-spec-execute-superpowers`

**84/120 (C).** The skill points to the Phase 25 subprocess policy and correctly describes the runner’s one-CLI-per-call ladder, router-only quota cycles, and evidence lines. Its remaining gaps are at the adapter boundary: a resume or an implementer status can still lead to a different model without an explicit owner choice.

| Dimension | Score | Max | Assessment |
|---|---:|---:|---|
| D1 Knowledge delta | 15 | 20 | Valuable failure and state rules; substantial repetition |
| D2 Mindset and procedures | 11 | 15 | Strong distinction between dispatch failure and fix rounds |
| D3 Anti-patterns | 12 | 15 | Specific, reasoned NEVER rules |
| D4 Specification compliance | 14 | 15 | Valid, precise activation description |
| D5 Progressive disclosure | 10 | 15 | References have triggers, but the 461-line body repeats policy |
| D6 Freedom calibration | 8 | 15 | Fragile owner-choice boundary is insufficiently constrained |
| D7 Pattern recognition | 8 | 10 | Clear process pattern |
| D8 Practical usability | 6 | 15 | Resume and stop paths can contradict the stated rule |

## Findings

1. **Critical — A post-failure resume can select another candidate.** `references/state-management.md:51-66` sends an owner-controlled resume back through Step 2; `SKILL.md:400-403` confirms that Step 2 resolves again. Re-invoking the task is not an explicit choice of a new harness, provider, or model, yet that resolution may pick one. **Fix:** keep the failed injection pinned on resume unless the owner explicitly names a replacement pair; distinguish that choice from a request merely to resume.

2. **Critical — An unusable zero-exit run can enter automatic model escalation.** `SKILL.md:306-320` sends an `"ok"` dispatch with `BLOCKED` status to subagent-driven-development’s report handler. That handler permits re-dispatch on a more capable model (`subagent-driven-development/SKILL.md:294-302`), while this skill’s no-switch rule at `SKILL.md:415-420` covers failed or *unusable* runs. **Fix:** explicitly stop external-CLI `BLOCKED` outcomes for an owner decision before following the handler’s model-change route.

3. **Important — The no-scheduler path promises a command it does not supply.** `SKILL.md:49-53` says to print a re-invoke command, but `SKILL.md:367-392` supplies a prose wake prompt and instructs hosts without `CronCreate` to print that prompt. **Fix:** provide a concrete, host-appropriate re-invoke command or state plainly that the owner must invoke the skill manually with the state path; do not label a prompt as a command.

4. **Minor — The no-JSON stop does not guarantee verbatim evidence relay.** `SKILL.md:284-288` says to relay stderr on refusal, but the displayed block only prints `dispatch-task exit …, no result`. **Fix:** make the stop instruction require printing the available `cross-ai: report` and `AIKIT-XAI` lines from `$DISPATCH_BASE.err` before the error summary.

This was a read-only review; I did not run dispatches or tests, and I did not inspect credential files.

DIGEST 9fa91a3b0024ebf5
CURRENT 84/120
CRITICAL 2 IMPORTANT 1
