# ai-kit-spec-execute-gsd — skill-judge report (native Opus subagent, clean context)

Round 6, skill digest `5ec033df03ba8007`, judged at commit 12083a7. Rubric: the skill-judge skill (120 points).

## Skill-judge report: ai-kit-spec-execute-gsd

**Grade: B, 96/120.** I found no critical issues. The Phase 25 policy is mostly described correctly in the skill: one CLI per call, no automatic fallback, the ladder, router cycles under the 4-hour cap, and evidence lines on every stop. One sentence gets the retry rule wrong for direct-route quota stops, and the file sits at the 500-line ceiling.

- **Pattern:** a mix of Process and Tool.
- **Knowledge ratio:** about 70% expert, 15% activation, 15% redundant.
- **SKILL.md:** 499 lines.
- **References:** `references/dispatch-notes.md` (66 lines) and the linked policy (119 lines).

| Dimension | Score | Max | Notes |
|---|---|---|---|
| D1 Knowledge Delta | 15 | 20 | Project-specific expert content (hook word-splitting, ownership sidecar, exit 75/69 semantics). Diluted by stop rules repeated many times and internal function names. |
| D2 Mindset + Procedures | 12 | 15 | Good "before writing, ask yourself" bullets (SKILL.md:187-198) and procedures Claude wouldn't know. |
| D3 Anti-Patterns | 13 | 15 | Strong NEVER list with reasons (`skip` falls back to native, re-resolving can rewrite the hook, early retry is refused). |
| D4 Spec / Description | 13 | 15 | Valid frontmatter, 820 characters, says WHAT and WHEN. No phrases a user would actually say, and no mention of quota-stop handling. |
| D5 Progressive Disclosure | 11 | 15 | MANDATORY trigger for the policy (SKILL.md:454) and "read only if" pointers. But 499 lines with a 35-line inline script. |
| D6 Freedom Calibration | 13 | 15 | Low freedom for fragile config writes is right. Copying long inline scripts by hand is a risk. |
| D7 Pattern | 8 | 10 | Clear Step 0 to 3 process, overloaded with policy prose. |
| D8 Usability | 11 | 15 | Very thorough error and stop handling, but has the inaccuracies below. Prose is dense. |

### Verified against the code (no finding)

- The route flag: `build_cross_ai_command` → `resolve_route` → `runner_flags` emits `--route-<cli> router|unknown` only for a catalog-confirmed route (gsd_cross_ai.py:25-28, runner_dispatch.py:182-183, 213-226).
- An early re-entry is refused without a model call and returns exit 75 with `retry_after_s` (cross-ai.mjs:2443-2450).
- The `--min cross_ai_timeout=1800` behavior (cli.py `_cmd_write_workflow_keys`).
- GSD shows the runner's stderr and offers retry/skip/abort (`.claude/gsd-core/workflows/execute-phase/detail/elaboration.md:99-120`).
- The skill never tells the agent to switch CLI, provider or model (SKILL.md:20-24, 25, 451, 457).

### Findings

1. **Important.** SKILL.md:450-451 says the runner "retries a transient or quota failure in the same session, then in new sessions". That is wrong for direct and `router-inferred` lanes: a quota hit off a confirmed router lane stops at once with no rung (cross-ai.mjs:2599 and 2606 `!(hit === 'quota' && lane)` → `classStop()`; policy:56-61). It also contradicts the skill's own SKILL.md:491-493. **Fix:** "It retries a transient failure, and a quota failure only on a confirmed router lane, first in the same session and then in new sessions, on that same CLI and model."

2. **Important.** The file is at the 500-line cap and much of it repeats.
   - The "fallback_notice / runner failure stops, never continue to native" rule appears about 7 times (SKILL.md:29-30, 147-151, 173-178, 288-293, 329-332, 338-341, 365-367).
   - The plan opt-in rule appears 4 times (14-17, 191-195, 211-216, 325-328).
   - SKILL.md:182-185 is a generic reviewer/native paragraph that doesn't apply to this flow.
   - SKILL.md:421-431 narrates internal function names.

   **Fix:** state each rule once in NEVER, point to it from the steps, and drop the generic paragraph and the internals narration. That frees about 60-80 lines.

3. **Minor.** SKILL.md:452-453 says "Step 0 resolves `$REVIEW_SPEC_SKILL_DIR`", but Step 0 only prints `GSD_SHIM`, `TOOLS_PY` and `CURATED_PY` (SKILL.md:73). Under the skill's own fresh-shell rule (82-85) the value was never captured. **Fix:** add `REVIEW_SPEC_SKILL_DIR=%s` to Step 0's printf, or say "the directory of `$TOOLS_PY`".

4. **Minor.** SKILL.md:489-491 says that after a cap stop the runner "keeps refusing that lane with exit 69". In the code, the cap stop saves `due_at = at + cooldown` (cross-ai.mjs:2478-2500). The `first_seen + cap` check only fires once the cap has passed (2436). So a re-entry before the cap ends hits the `due_at` branch (2443-2450) and gets exit 75 with `retry_after_s=`, which by the skill's rules schedules a wake. **Fix:** either have the runner return 69 for a capped episode (persist `stopped: 'cap'`), or reword the skill to say "an exit 69 after the cap; an earlier re-entry may still see exit 75".

5. **Minor.** SKILL.md:491-493 lists the causes of a bare exit 75 but leaves out a router lane whose cycle state file can't be written (cross-ai.mjs:2474-2488, `retryAfterS` undefined when `!stateWritable`). **Fix:** add "or an unwritable cycle-state file" to that list.

6. **Minor.** SKILL.md:297-299 and 338: when a user's `cross_ai_timeout` is below 1800, Step 2 raises it and takes ownership. A later cleanup then deletes the key instead of restoring the user's value (`apply_changes` with `None`, gsd_config.py:142-147), so GSD falls back to 300 and the original survives only in another run's backup. **Fix:** restore the backed-up prior value on cleanup, or print the backup path in the cleanup output.

7. **Minor.** SKILL.md:384-418 is a 35-line inline Python script for editing the guidance markers, which the agent has to copy by hand. **Fix:** move it into a shim subcommand (for example `python3 $GSD_SHIM write-phase-guidance --file ... --guidance-file -`) and keep exit codes 2 and 3 as they are.

8. **Minor.** The resolve-time ladder walk (adapter.py:298-307) skips quota-exhausted candidates and moves to the next configured one. This is pre-handoff selection from the owner's ordered list, which sits next to the "never switch provider/model" rule without being explained. **Fix:** add one line in Step 1 saying this owner-ordered walk, before handoff, is the only selection, and nothing changes after a dispatch starts.

9. **Minor.** The description (SKILL.md:3) has no trigger phrases a user would type (for example "execute GSD phase N", "run phase with cross-AI executor") and doesn't mention resuming from a quota stop. **Fix:** add 2-3 such phrases and shorten the parenthetical config detail.

I didn't run any tests or the runner self-test, and didn't live-check whether the CronCreate wake fires while GSD's prompt is pending; the skill already flags that as unverified. Finding 4 is a runner edge case: a wasted wake, not data loss.

DIGEST 5ec033df03ba8007
CURRENT 96/120
CRITICAL 0 IMPORTANT 2
