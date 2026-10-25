# ai-kit-spec-execute-gsd — skill-judge report (opencode router-env/my-referee-one, read-only review mode)

Round 6, skill digest `5ec033df03ba8007`, judged at commit 12083a7. Rubric: the skill-judge skill (120 points).

Runner status: `AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-one exit=0 cli_rc=0 elapsed=166s out=554348 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0`

## Skill evaluation: ai-kit-spec-execute-gsd

**105/120 — B (87.5%).** Clear **Process/Tool** pattern; estimated Expert:Activation:Redundant ratio **80:15:5**.

Phase 25’s stop-handling correctly prohibits candidate re-resolution and native fallback, requires verbatim evidence lines, and limits scheduled re-entry to confirmed-router quota stops with the hook unchanged (`SKILL.md:20–30,450–493`). The shared policy is correctly located and mandatory on cross-AI stops. Two operational inconsistencies remain.

| Dimension | Score | Assessment |
|---|---:|---|
| D1: Knowledge Delta | 17/20 | Strong GSD-specific knowledge; repeated explanations dilute it. |
| D2: Mindset + Procedures | 14/15 | Good ownership, opt-in and stale-hook reasoning alongside executable procedures. |
| D3: Anti-Pattern Quality | 14/15 | Specific prohibitions explain dangerous implicit fallback paths. |
| D4: Specification Compliance | 15/15 | Valid frontmatter; description supplies capabilities, scenarios and trigger terms. |
| D5: Progressive Disclosure | 12/15 | Explicit reference triggers, but the 499-line entrypoint carries duplicated mechanics. |
| D6: Freedom Calibration | 13/15 | Appropriate constraints around dispatch; quota summary needs qualification. |
| D7: Pattern Recognition | 9/10 | Coherent staged workflow, somewhat obscured by length. |
| D8: Practical Usability | 11/15 | Detailed failure handling, undermined by contradictory fallback output and incomplete resumability. |
| **Total** | **105/120** | |

## Findings

1. **Important — Fallback messages still promise automatic native execution.**  
   **Evidence:** `skills/ai-kit-spec-execute-gsd/ai_kit_spec_gsd/adapter.py:117–129` emits “GSD’s own currently-active default … will run instead.” Meanwhile, `skills/ai-kit-spec-execute-gsd/SKILL.md:173–178,329–340` requires printing that message, cleaning up and **stopping** until the owner explicitly chooses native execution. The agent can follow the new policy correctly while telling the owner the opposite.  
   **Fix:** Change the shared notice to say execution stopped and native execution requires an explicit owner decision; update message assertions accordingly.

2. **Important — Durable resumable state is missing for ordinary cross-AI stops.**  
   **Evidence:** `skills/ai-kit-spec-review/references/subprocess-quota-policy.md:83–94` requires resumable state on a stop. The adapter’s explicit write instructions cover probe-time quota exhaustion (`skills/ai-kit-spec-execute-gsd/SKILL.md:147–170`) and confirmed-router delayed re-entry (`:466–469`), but not auth, billing, bad-model, transient-exhaustion or other owner-controlled stops (`:456–458,483–493`).  
   **Fix:** Require the existing state-writing block for every cross-AI failure stop, using `RESUME_VIA=gsd-execute-phase`. Schedule nothing unless the confirmed-router retry contract is present.

3. **Minor — The ladder summary overstates which quota failures receive retries.**  
   **Evidence:** `skills/ai-kit-spec-execute-gsd/SKILL.md:450–451` says the runner retries “a transient or quota failure” through sessions without qualification. The authoritative policy explicitly excludes off-router quota failures from **both rungs and cycles** (`skills/ai-kit-spec-review/references/subprocess-quota-policy.md:58–61`).  
   **Fix:** Say “eligible transient failures and confirmed-router quota failures,” noting that session support and safety/deadline gates constrain the ladder.

4. **Minor — Repeated mechanics weaken progressive disclosure.**  
   **Evidence:** `skills/ai-kit-spec-execute-gsd/SKILL.md:243–253,342–352` duplicates cleanup logic; `:211–216,325–328` repeats opt-in handling; `:302–307` repeats runner-setup explanation. The optional rationale reference is only 66 lines.  
   **Fix:** Keep the core mode/stop decisions in `SKILL.md`; consolidate cleanup into one referenced procedure with an explicit loading trigger, and remove repeated explanatory paragraphs.

**Limits:** Static review only; no scripts, tests or live scheduler checks were run. No files were changed or credential files read.

DIGEST 5ec033df03ba8007
CURRENT 105/120
CRITICAL 0 IMPORTANT 2
