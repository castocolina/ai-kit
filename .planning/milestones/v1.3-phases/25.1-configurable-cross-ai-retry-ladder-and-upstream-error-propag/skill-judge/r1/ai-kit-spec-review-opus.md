Judge: opus
Reviewed-sha256: 6efb7723c3ca635d131295da929abda0a3fdc89e12ab88b5d3fa1a25d2c3911a
Lane: native subagent completed
Score: 98
Critical: 1
Important: 2

**Skill evaluation: `skills/ai-kit-spec-review/` (focus on the Phase 25.1 changes)**

The skill is a Process-pattern skill. SKILL.md is 480 lines, close to the 500-line ceiling, and the heavy detail sits in `references/`. The core review loop is strong and full of hard-won rules. But the 25.1 rewrite of Step 1 left the hard-tier handling contradicting itself between SKILL.md and `references/cross-ai-dispatch.md`, and it dropped the mandatory route into the pending-lane lifecycle. No passage permits switching harness, provider or model. The rule appears in SKILL.md:340 and in the Hard rules table at :465. The Step 0.7 probe walk (:157-166) is pre-dispatch selection, and the text says openly that the owner has not ruled on it yet.

| Dimension | Score | Max | Notes |
|---|---|---|---|
| D1 Knowledge Delta | 16 | 20 | Expert rules: worktree root, archetype ceiling, `.exit` as the completion signal, branching before deleting. `cross-ai-dispatch.md` point 0 has some verbose parentheticals. |
| D2 Mindset + Procedures | 13 | 15 | "Ask yourself" prompts at 0.5, 0.7, 3 and 5, plus domain procedures. |
| D3 Anti-Patterns | 13 | 15 | The NEVER list is short, but the Hard rules table gives reasons, and the never-switch rule is explicit. |
| D4 Spec / Description | 14 | 15 | WHAT, WHEN and keywords are all present. The description is long. |
| D5 Progressive Disclosure | 12 | 15 | Good MANDATORY and "Do NOT load" triggers. The trigger to read the canonical policy got weaker (finding 2). |
| D6 Freedom Calibration | 12 | 15 | Dispatch freedom is correctly low, but two contradictory low-freedom rules cover the same case. |
| D7 Pattern | 8 | 10 | Clear Process pattern, about twice the usual length. |
| D8 Practical Usability | 10 | 15 | A hard-tier lane outside a router gets contradictory instructions, two dangling "Step 1" references, and a stopped-lane refusal goes unhandled. |

**Findings**

1. **Critical: the hard-tier gate contradicts itself and the canonical policy.**
   - SKILL.md:326-328 says any exit 75 with `retry_after_s=` gets a one-shot re-invoke, "whether the runner classified it `transient` or `quota`".
   - `references/cross-ai-dispatch.md` says something narrower:
     - :244-249 keeps the report only when the last line has `route=router` and `retry_after_s=`.
     - :248-249 says "an exhausted transient ladder on any route" is a terminal bare 75.
     - :258-261 says "A `route=router-inferred` lane gets no cycles".
   - The canonical policy disagrees with that reference. `ai-kit-cross-ai/references/subprocess-quota-policy.md:48-49,96` gives both soft classes the hard tier on every route, and a deadline-cut series ends in the hard tier, "never a bare exit 75".
   - Result: a transient hard tier on `route=unknown` is deleted as a Failure by the reference, while SKILL.md says to re-invoke it.
   - Fix: change the gate in dispatch.md :244-249 and :258 to "exit 75 with `retry_after_s=` on the last `AIKIT-XAI` line, any route". Remove the "exhausted transient ladder" parenthetical. Rename the section to something like "Pending lane (hard tier) — lifecycle and resume". Keep only the true remaining case: an off-router quota stop is a bare 75.

2. **Important: Step 1 no longer routes to the pending-lane lifecycle, and two references now dangle.**
   - The 25.1 diff removed the "Pending router lane … MANDATORY: follow … pending router lane section" paragraph. That paragraph covered keeping the slot, merging the sibling as single mode, writing the resume files and running no fixer.
   - It also removed "MANDATORY before acting on any subprocess stop". Now SKILL.md:339-340 is just a bare link with no load trigger.
   - Two places still point at Step 1 content that no longer exists:
     - SKILL.md:372-373 refers to "the pending-lane note from Step 1".
     - SKILL.md:383 refers to "Step 1's pending router lane".
   - Without the resume files, a re-invoke after a context reset cannot work.
   - Fix: after SKILL.md:328, add "MANDATORY: follow cross-ai-dispatch.md's pending lane section (keep the slot, merge the sibling as single mode, write the resume files, no fixer)". Change :339 to "MANDATORY before acting on any exit 69/75: read ../ai-kit-cross-ai/SKILL.md sections 4, 6 and 8".

3. **Important: the refusal on a stopped lane is not handled, and the owner's reset path is lost.**
   - When a lane is already stopped, the runner refuses the next call with exit 69. It prints `cross-ai: lane stopped=<v> at <iso>; delete <path> to start a new episode` (cross-ai.mjs:3785-3786). Its `AIKIT-XAI` line has no `stopped=` token (self-test regex at cross-ai.mjs:6321-6322).
   - SKILL.md:329 keys the stop on `stopped=hard-waits`/`stopped=cap`.
   - SKILL.md:443-445 and dispatch.md:320 quote only the `report`, `upstream` and `AIKIT-XAI` lines. So the delete path, which is the owner's only reset, never reaches the user.
   - SKILL.md:329-332 also leaves unclear whether an exit 69 stop deletes `iter<N>-<key>.md` ("Every other nonzero exit…").
   - Fix: in Step 1 and the Step 5 Failure rule, also quote any `cross-ai: lane stopped=` and `cross-ai: state` line verbatim. State explicitly that an exit 69 stop deletes the report and is merged as failed.

4. **Minor: the Step 5 row name and its quoted lines are stale.**
   - SKILL.md:440 calls every hard-tier wait "Router quota cooldown", even a transient one on a non-router route.
   - dispatch.md:294-296 prints the argv path but not the `cross-ai: state <path>`. `ai-kit-cross-ai/SKILL.md:128-130` requires that path on hosts without `CronCreate`.
   - Fix: rename the row to "Hard-tier wait" and add the state-path line.

5. **Minor: the template labels and status table are stale.**
   - dispatch.md:348 and :355 still say "Template 7". The new template-8 tokens (`stopped=`, `upstream=`, `cycle`, `due_at`, `retry_after_s`) are not named in the pointer sentence.
   - The `idle_stall` row at :349 sits next to a canonical policy that says "There is no idle watchdog" (`ai-kit-cross-ai/SKILL.md:55`).
   - Fix: relabel the section as template 8, list the new tokens by name and link to the policy, and mark `idle_stall` as accepted only from older runners.

6. **Minor: the CLI profiles are stale for the new runtimes.**
   - SKILL.md:153 says to load `references/cli-profiles/` "when a named CLI's flags are in doubt".
   - No profile exists for `copilot` (new in detection.py:117) or `pi`.
   - The policy also now says the runner owns every runtime's flags and `--model` grammar (`subprocess-quota-policy.md:16-18`).
   - Fix: point that trigger at `node <runner> --self-test` or `ai-kit-cross-ai` section 1. Note that the profiles are historical notes and do not cover copilot or pi.

I did not run the runner's `--self-test` or any make target, and I only spot-checked cross-ai.mjs (9,985 lines) around the stopped-lane refusal. The risk the user must know about: finding 1 makes a non-router transient hard tier fail closed (it gets deleted as a Failure) instead of waiting.

DIGEST 6efb7723c3ca635d
CURRENT 98/120
CRITICAL 1 IMPORTANT 2
