# ai-kit-spec-review — skill-judge report (opencode router-env/my-referee-one, read-only review mode)

Round 6, skill digest `e85ac2aec5c16f61`, judged at commit 12083a7. Rubric: the skill-judge skill (120 points).

Runner status: `AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-one exit=0 cli_rc=0 elapsed=178s out=1395374 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0`

## Skill evaluation: `ai-kit-spec-review`

**104/120 — Grade B.** Strong **Process/Tool** skill with substantial project-specific knowledge (estimated E:A:R **80:15:5**). Reviewed the complete `SKILL.md`, all 14 reference files, and the requested Phase 25 diff; no `scripts/` files were present.

Phase 25’s runner correctly selects only the first CLI, keeps retries on the same CLI/model, persists confirmed-router quota cycles under the four-hour cap, and emits stop evidence. The skill mandates reading the policy and prohibits post-dispatch fallback. Two orchestration gaps remain.

| Dimension | Score | Assessment |
|---|---:|---|
| D1: Knowledge Delta | 18/20 | Valuable worktree, lifecycle, routing and recovery knowledge; some repeated rationale. |
| D2: Mindset + Procedures | 14/15 | Good decision framing and concrete dispatch procedures; resume completion needs tightening. |
| D3: Anti-Pattern Quality | 14/15 | Specific prohibitions with meaningful reasons; pre-dispatch exception weakens owner control. |
| D4: Specification Compliance | 15/15 | Valid metadata; description clearly supplies capabilities, scenarios and trigger terms. |
| D5: Progressive Disclosure | 12/15 | Strong mandatory/conditional loading guidance, but excessive unconditional reading. |
| D6: Freedom Calibration | 12/15 | Appropriately constrained dispatch; autonomous preselection and ambiguous resume waiting remain. |
| D7: Pattern Recognition | 9/10 | Clear Process/Tool structure, somewhat oversized. |
| D8: Practical Usability | 10/15 | Common paths are actionable; resume signaling and evidence accounting need fixes. |
| **Total** | **104/120** | **Good, but not fully aligned with the requested owner-controlled policy.** |

### Findings

1. **Important — Pre-dispatch probing still permits autonomous provider/model/native fallback.**  
   **Evidence:** `skills/ai-kit-spec-review/SKILL.md:157–165` explicitly allows a failed probe—including timeout—to select another provider, ultimately the native session default, while admitting the owner has not ruled on this behavior. These are real subprocess calls: `skills/ai-kit-spec-review/ai_kit_spec/quota.py:268–283` executes the probe and marks any failure unavailable.  
   **Fix:** On an unavailable probe, surface the reason and require owner selection before choosing another harness, provider, model or native reviewer. Preserve an explicit no-config session-default path, but do not treat failed configured probes as authorization to switch.

2. **Important — Resume completion signaling contradicts the normal dispatch contract.**  
   **Evidence:** `skills/ai-kit-spec-review/references/cross-ai-dispatch.md:301–308` creates `.exit` containing `running` before launching the background process, then says to wait for that file. However, `skills/ai-kit-spec-review/SKILL.md:319–322` defines file existence as completion. Applying that rule during resume can immediately reach the terminal branch at `cross-ai-dispatch.md:316–317`, deleting a report while its process remains active.  
   **Fix:** Explicitly wait until `.exit` contains a completed numeric exit code, not `running`; update both contracts consistently. Alternatively, use a separate running marker and atomically publish the completion file.

3. **Minor — An empty-answer stop undercounts attempts and omits the promised attempt evidence.**  
   **Evidence:** `skills/ai-kit-spec-review/references/subprocess-quota-policy.md:65` promises one evidence line per failed attempt. In `skills/ai-kit-spec-review/references/cross-ai.mjs:2600–2604`, an empty answer returns before the increment and `logAttempt` at `2611–2616`. A first-call empty answer therefore reports zero attempts despite having run a CLI.  
   **Fix:** Count and log the empty-answer attempt before returning; add a focused assertion for its attempt line and trailer count.

4. **Minor — Native-only runs must load substantial irrelevant recovery detail.**  
   **Evidence:** `skills/ai-kit-spec-review/SKILL.md:153` requires reading all 384 lines of `cross-ai-dispatch.md` even with `--no-cross-ai`, although that reference’s `110–122` skips directly to native dispatch.  
   **Fix:** Separate common setup from external dispatch/recovery, and load recovery instructions only for external lanes or resume entry.

No files were changed and no credential files were read. Tests and live CLI/scheduler behavior were not run; runtime conclusions are based on source inspection.

DIGEST e85ac2aec5c16f61
CURRENT 104/120
CRITICAL 0 IMPORTANT 2
