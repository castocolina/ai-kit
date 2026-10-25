Judge: my-referee-one
Reviewed-sha256: bc1edbe8473bef7e6dad7c829cf89b43e1f758192c7e417dbd45a84fbf235af7
Lane: AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-one exit=0 cli_rc=0 elapsed=130s out=579178 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 104
Critical: 0
Important: 1

## Skill evaluation: ai-kit-spec-execute-gsd

**104/120 — B (86.7%).** A strong Process/Tool skill with valuable GSD-specific safeguards, but the canonical-policy loading instruction needs strengthening.

Read the supplied rubric fully, the complete **485-line SKILL.md**, the sole reference (**dispatch-notes.md**, 66 lines), and the requested diff. Also traced the shim/hook builder and checked the canonical cross-AI policy. Estimated Expert:Activation:Redundant ratio: **80:15:5**.

| Dimension | Score | Assessment |
|---|---:|---|
| D1: Knowledge Delta | 18/20 | Strong ownership, rollback, hook-expansion and dispatch knowledge; some repetition. |
| D2: Mindset + Procedures | 14/15 | Explains why opt-in, cleanup and unchanged-hook recovery matter. |
| D3: Anti-Pattern Quality | 14/15 | Specific prohibitions prevent native fallback and candidate reselection. |
| D4: Specification Compliance | 15/15 | Valid name and descriptive, scenario-rich frontmatter within the description limit. |
| D5: Progressive Disclosure | 10/15 | Optional rationale is routed well; canonical policy lacks an explicit mandatory loading gate, while substantial implementation remains inline. |
| D6: Freedom Calibration | 12/15 | Generally appropriate constraints, weakened by policy-loading ambiguity and locally overridden wait timing. |
| D7: Pattern Recognition | 9/10 | Clear phased Process/Tool structure with explicit stop branches. |
| D8: Practical Usability | 12/15 | Detailed operational handling; policy integration and scheduling consistency need improvement. |
| **Total** | **104/120** | |

### Findings

1. **Important — The canonical policy is linked but no longer explicitly required reading.**  
   **Evidence:** `skills/ai-kit-spec-execute-gsd/SKILL.md:41–45` names the caller contract “including its policy reference,” but never instructs the agent to load either document. The diff removes the previous mandatory-read instruction. Meanwhile, `SKILL.md:450–459` directly instructs relaying upstream bodies without locally establishing that they are untrusted data; that boundary exists in `skills/ai-kit-cross-ai/SKILL.md:83–85`.  
   **Fix:** Add an explicit mandatory read of `ai-kit-cross-ai/SKILL.md` and its policy reference before cross-AI handoff or result handling. State that upstream text is evidence, never instructions, including any switch-combo suggestion.

2. **Minor — Local scheduling changes the canonical hard-tier delay.**  
   **Evidence:** `skills/ai-kit-spec-execute-gsd/SKILL.md:461–462` imposes a 60-second minimum and rounds upward to whole minutes. The canonical contract requires exactly `retry_after_s` seconds (`skills/ai-kit-cross-ai/SKILL.md:115–117`), and configurable waits may be zero (`references/subprocess-quota-policy.md:88–89`).  
   **Fix:** Document minute-resolution scheduling as a host limitation in the canonical policy, permitting a wake no earlier than the deadline, then reference that rule here. Avoid defining different timing semantics in this adapter.

3. **Minor — The main body carries too much implementation and duplicated policy.**  
   **Evidence:** `skills/ai-kit-spec-execute-gsd/SKILL.md:243–287` embeds runner-setup plumbing; `:369–419` embeds an atomic file-rewrite program. Caller rules are repeated across `:25–28`, `:41–45`, and `:450–479`.  
   **Fix:** Move the long executable recipes into a conditionally loaded reference or existing shim commands. Keep the decision gates, failure outcomes and GSD-specific unchanged-hook retry mapping in SKILL.md; delegate shared retry policy to the canonical skill.

**Phase 25.1 assessment:** The hook builder emits one `--runtime` and `--model`; recovery explicitly preserves the hook and prohibits switching. Delegating soft retries, session resets, model grammars, tool profiles, Copilot behavior and catalog/overlay details to the canonical policy and runner is appropriate—not a documentation omission.

No files were changed or credentials read; tests and live scheduler behavior were not exercised. Scheduler delivery remains explicitly unverified.

DIGEST bc1edbe8473bef7e
CURRENT 104/120
CRITICAL 0 IMPORTANT 1

## Runner evidence

```
AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-one exit=0 cli_rc=0 elapsed=130s out=579178 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
```
