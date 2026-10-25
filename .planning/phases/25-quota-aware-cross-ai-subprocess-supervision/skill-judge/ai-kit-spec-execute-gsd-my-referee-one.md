# ai-kit-spec-execute-gsd — skill-judge report (opencode router-env/my-referee-one, read-only review mode)

Round 5 (evidence round), skill digest `0a5d05b298c07ee8`, judged at commit e2bb140. Rubric: the skill-judge skill (120 points).

## Round 5: BLOCKED (the runner stopped the lane; no score)

Runner evidence lines:

```text
cross-ai: report status=quota lane=opencode/router-env/my-referee-one route=router attempts=7 cycles=0 first_failure=2026-10-25T04:25:46.793Z last_failure=2026-10-25T04:41:34.235Z stopped=deadline
AIKIT-XAI status=quota cli=opencode model=router-env/my-referee-one exit=75 cli_rc=1 elapsed=948s out=5192 tree=clean action=stop route=router rule=text-pre-dispatch pattern=verified attempts=7 cycles=0 retry_after_s=600 cycle=0
```

Upstream messages (OmniRoute, verbatim, trimmed):

```text
Service temporarily unavailable: all targets were skipped by pre-dispatch filters (Session (5h) 100% conn:dd6b6ba2; Session (5h) 100% conn:f48bcb3c)
Service temporarily unavailable: all targets were skipped by pre-dispatch filters (Session (5h) 100% conn:f48bcb3c)
```

## Last completed report from this judge (round 4, an earlier digest; reference only, not this verdict's score)

## Skill evaluation: `ai-kit-spec-execute-gsd`

**105/120 — Grade B (87.5%).** A strong **Process/Tool** skill with substantial repository-specific knowledge. Estimated Expert:Activation:Redundant ratio: **80:15:5**.

Read all 494 lines of `SKILL.md`, the sole local reference (`dispatch-notes.md`, 66 lines), the linked shared quota policy (116 lines), and the requested Phase 25 diff. No local `scripts/` files were found.

**Phase 25 assessment:** The skill correctly links the authoritative policy, prohibits candidate re-resolution and native `skip`, preserves the hook during recovery, requires verbatim stop evidence, and limits scheduled re-entry to confirmed-router quota stops. No Critical finding; some summaries and emitted instructions remain inconsistent.

| Dimension | Score | Rationale |
|---|---:|---|
| D1: Knowledge Delta | 18/20 | High-value GSD ownership, hook-expansion, trust and recovery knowledge; some duplication. |
| D2: Mindset + Procedures | 14/15 | Strong opt-in, stale-hook and dispatch-boundary reasoning with actionable procedures. |
| D3: Anti-Pattern Quality | 14/15 | Specific, consequential prohibitions with explanations, particularly against silent fallback. |
| D4: Specification Compliance | 15/15 | Valid frontmatter; description clearly supplies capabilities, scenarios and trigger terms. |
| D5: Progressive Disclosure | 11/15 | Mandatory policy-loading trigger is good; lengthy inline implementation crowds the main workflow. |
| D6: Freedom Calibration | 13/15 | Appropriately constrained recovery, but one retry summary overgeneralizes quota handling. |
| D7: Pattern Recognition | 9/10 | Clear staged Process/Tool design; operational detail sometimes obscures branch decisions. |
| D8: Practical Usability | 11/15 | Extensive failure handling, weakened by misleading fallback output and a resume-output mismatch. |
| **Total** | **105/120** | |

### Findings

1. **Important — Fallback output still promises automatic native execution.**  
   **Evidence:** `skills/ai-kit-spec-execute-gsd/SKILL.md:177–182` instructs printing the fallback message and stopping without native execution. However, `skills/ai-kit-spec-execute-gsd/ai_kit_spec_gsd/adapter.py:117–129` constructs that message with **“GSD's own currently-active default … will run instead.”** This contradicts the Phase 25 owner-controlled stop and can mislead the owner about whether execution continues.  
   **Concrete fix:** Change the emitted fallback message to state that execution stopped and native execution requires an explicit owner decision.

2. **Important — The promised resumable-state output is never emitted.**  
   **Evidence:** `skills/ai-kit-spec-execute-gsd/SKILL.md:154–157` promises a printed `RESUME_STATE_PATH=…` line, and `:483–484` relies on that line for scheduler-less recovery. The block at `:165–175` assigns the variable but never prints it. The invoked implementation at `skills/ai-kit-spec-execute-gsd/ai_kit_spec_gsd/cli.py:389–393` emits JSON containing `written` and `path`, not that assignment.  
   **Concrete fix:** Explicitly print `RESUME_STATE_PATH=%s` after a successful state write, and require checking the write’s status before scheduling. Alternatively, consistently document capturing the JSON `path`.

3. **Minor — The ladder summary incorrectly generalizes quota retries.**  
   **Evidence:** `skills/ai-kit-spec-execute-gsd/SKILL.md:452–453` says a “transient or quota failure” receives same-session and then new-session retries. The mandatory policy at `skills/ai-kit-spec-review/references/subprocess-quota-policy.md:54–59` explicitly excludes off-router and `router-inferred` quota stops from both rungs and cycles.  
   **Concrete fix:** Say **“transient failures, and quota failures on confirmed-router lanes”**, with a brief qualification that session support and safety gates can prevent a rung.

4. **Minor — Main-file implementation detail weakens progressive disclosure.**  
   **Evidence:** `skills/ai-kit-spec-execute-gsd/SKILL.md:238–291` embeds runner-setup shell implementation, while `:372–422` embeds an atomic file-rewrite implementation. Combined with repeated guard explanations, the main file reaches 494 lines despite having references.  
   **Concrete fix:** Move these executable recipes into bundled scripts or mandatory branch-specific references; retain inputs, exit contracts and stop decisions in `SKILL.md`.

No files changed or credential files read. Execution tests and live quota/scheduler behavior were not checked; runtime correctness remains unverified.

DIGEST 6c26070e06867feb
CURRENT 105/120
CRITICAL 0 IMPORTANT 2
