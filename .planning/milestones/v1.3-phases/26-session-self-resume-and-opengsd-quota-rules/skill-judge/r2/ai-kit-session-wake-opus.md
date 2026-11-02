Judge: opus
Reviewed-sha256: a28223d21d64c262e99b7c9a3c004c8bbf89381ba6819f6d1f38f2b3fd4c0823
Lane: native subagent completed
Score: 98
Critical: 0
Important: 5

# Skill Evaluation Report: ai-kit-session-wake

## Summary
- **Total Score**: 98/120 (82%)
- **Grade**: B
- **Pattern**: Tool, with some Process elements (subcommand contract, exit-code outcomes, relay rules)
- **Knowledge Ratio**: E:A:R = about 80:15:5
- **Verdict**: A dense, honest skill specific to this project, with good certainty labelling. Several of its stated outcomes for `done`, exit 2, `--permission-mode` and wake lifetime do not match the shim's actual behaviour, so in edge cases an agent would relay wrong facts.

Line numbers are those of `skills/ai-kit-session-wake/SKILL.md`. The package text matches the repository file exactly, apart from the opening `---` line.

## Dimension Scores

- **D1 Knowledge Delta: 16/20.** Almost all of it is knowledge Claude cannot have: session-id sources per host, wake ownership through `refreshed`, the companion one-shot ("spike 004"), the lock semantics, and the unverified list. Small redundancy: the "six subcommands" section (142-144) and a restated subagent rule (138).
- **D2 Mindset + Procedures: 12/15.** It has real domain procedures: shim resolution, arm flags and relay lines. It has ownership thinking ("A manual arm makes you own its `done`", 53-55). It does not frame decisions for a resumed session, or for when to arm by hand versus via an executor.
- **D3 Anti-Pattern Quality: 13/15.** The NEVER list is specific, with reasons: no "most recent" resume, no guessed session id or pid, no hand edits because of the session lock. The residual risk of a subagent running `done` is named honestly. It lacks a "never `done` when nothing is armed" item; see finding 1.
- **D4 Specification Compliance: 14/15.** Frontmatter is valid. The description gives WHAT, WHEN and keywords (rate limit, usage-limit reset, AGENTS.md rule) plus a "Not for" boundary. It is slightly long.
- **D5 Progressive Disclosure: 12/15.** 174 lines, self-contained, no references needed. A few sections could be cut.
- **D6 Freedom Calibration: 13/15.** Freedom is low where it should be: an exact shim loop, exact relay lines, one outcome per exit code. One mismatch: the shim-not-found branch says STOP while the headline rule says to carry on (finding 5).
- **D7 Pattern Recognition: 8/10.** A clear Tool pattern with decision lists. Section order is a little scattered: "The six subcommands" sits after Done.
- **D8 Practical Usability: 10/15.** Good coverage of the common paths. Several outcomes the agent is told to relay are inaccurate in realistic edge cases (findings 1-4).

## Findings

1. **Important. SKILL.md:123 and 131-133.** The text says `done` "with no resume running ... removes the wake at once; while a resume runs it prints `a wake resume is running...`". In the code:
   - `done` first creates the `.done` marker (fire.py:236).
   - It then takes the lock with `lock_session(..., blocking=False)`. That returns `None` when the lock file does not exist (state.py:262-263).
   - So `done` on a session that is not armed, or was already closed (for example after an executor's own close step), wrongly prints "a wake resume is running" and leaves a stale `.done` behind (fire.py:240-243).
   - `arm` never clears `.done` (arm.py has no reference to it). A later `arm` of the same session id therefore prints `armed`, and its first fire takes the `done` branch and deletes the wake without resuming (fire.py:458-459, 429-432).

   Fix: in the code, make `done` print "nothing armed" and skip the marker when no lock or state exists, and have `arm` remove a stale `.done`. In the skill, add "run `done` only for a wake you own and that is still armed (`status` first)".

2. **Important. SKILL.md:8-10 and 86-93 (the cap is never mentioned).** Every hourly fire counts toward `WAKE_CAP = 24` (state.py:22), including fires where the host is still alive. The count happens before the liveness check (fire.py:463-474, then 402-404 and 433-441). At 24 the wake gives up and removes itself; this is pinned by tests/test_ai_kit_session_wake_fire.py:814 ("host alive; log only (wake 24/24)", "gave up"). A refresh keeps the old count (arm.py:374, 439). So a "long unattended run" past about 24 hours silently loses its wake, while the skill implies the wake lasts.

   Fix: state the cap, that live-host fires consume it, that re-arming does not reset it, and that `status` shows `wakes: n/cap`. Better still, change the code to count only fires that actually resume.

3. **Important. SKILL.md:90-91.** "2: refused, no wake" is wrong in two cases:
   - A failed refresh returns 2 with "previous wake restored", so a wake still exists (arm.py:682-683).
   - An invalid state returns 2 with "run disarm first" (arm.py:546-547, 297). The right action there is `disarm` and then `arm`, not "Retry only with a value the host or owner gave".

   Fix: split exit 2 into "no wake" (no session id, cross-AI child, `pass --pid`, session not found, interpreter not on the wake's PATH) and "existing wake kept or broken" (refresh failure, or invalid state, which needs `disarm`).

4. **Important. SKILL.md:72-74.** `--permission-mode` is documented as if it applies to every host. On pi, opencode and codex, `arm` reports "(not applied: no verified permission flag for <host>)" (arm.py:493-509). But `resume_argv` adds `--permission-mode <mode>` for every host (hosts.py:115-117). An agent that passes the flag on a non-claude host therefore gets a resume command with an unverified flag, while being told the flag was not applied.

   Fix: document the flag as claude-only ("do not pass it on pi, opencode or codex"), and gate it by host in `resume_argv`.

5. **Important. SKILL.md:44 versus 13-14.** The shim loop prints "shim not found; STOP and tell the user" and runs `exit 1`. The headline rule says "Never fail the run on the wake ... the run goes on without a wake". The executors print "not installed; no session wake" and continue. In an unattended run, "STOP" can halt the whole run.

   Fix: print "ai-kit-session-wake: shim not found; no wake, continue the run" and relay that.

6. **Minor. SKILL.md:101-103.** The companion prompt says to stop "when no wake is recorded". But `status --host X --session-id Y` on a session that is not armed prints the path and then `invalid state: missing`, not `nothing armed` (cli.py:176-177 and 145-146). Name the exact line to stop on.

7. **Minor. SKILL.md:35.** "The same order the executor skills use" is not accurate:
   - The executors locate the wake shim as a sibling of their own directory (ai-kit-spec-execute-gsd/SKILL.md:359, ai-kit-spec-execute-superpowers/SKILL.md:117).
   - Their own loops include git-toplevel and cwd candidates (superpowers SKILL.md:63-64), which this loop lacks.
   - This loop adds `PI_CODING_AGENT_DIR`, which theirs lack.

8. **Minor. SKILL.md:111 and 113.** `--reset-at` is called "an explicit time", but the next line says "Every reset time is inferred". The code labels both as `reset_inferred` (arm.py:345), so say "both are recorded as inferred".

9. **Minor. SKILL.md:172-174.** The rule "never restarts the wait at cycle 0" is credited to `ai-kit-cross-ai/SKILL.md`. That file says only "The runner counts the cycles" (section 6). The rule's actual source is the resume prompt (fire.py:33-34).

10. **Minor. SKILL.md:53-55.** The resume prompt tells the resumed agent to "Re-run ... arm to refresh" (fire.py:34-35). The skill's "arm by hand only when no executor arms for you" does not cover the resumed session, so it leaves unclear who owns the `done` after a resume.

11. **Minor. SKILL.md:140-144.** The "six subcommands" section mostly repeats what the earlier sections already show. Fold the `fire` note into NEVER.

## Top 3 Improvements
1. Fix `done` on a session with no wake: print "nothing armed", leave no stale `.done`, and have `arm` clear a stale marker. Document "only `done` a wake you own".
2. Document the 24-wake cap, including that live-host fires use it up and a refresh does not reset it, or change the code to count only fires that resume.
3. Correct the exit-code table and the host scope of `--permission-mode`, and make the shim-not-found branch continue the run.

I did not run the shim or its tests; I worked out findings 1, 2 and 4 by reading the code, and checked finding 2 against an existing test. The `CLAUDE_CODE_SESSION_ID`/`CLAUDE_PID` host behaviour is unverified here (the repository cites only "spike 001").
