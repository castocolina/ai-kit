# ai-kit-spec-execute-superpowers — skill-judge report (native Opus subagent, clean context)

Round 5 (evidence round), skill digest `beff20e2e6df85d9`, judged at commit e2bb140. Rubric: the skill-judge skill (120 points).

# Skill evaluation: ai-kit-spec-execute-superpowers (Phase 25 state)

The skill scores 100/120 (grade B), with 0 Critical and 2 Important findings. Its pattern is a Process/Tool hybrid: a 457-line SKILL.md plus three references and the shared quota policy. I estimate the content mix at about 75% expert, 15% activation and 10% redundant.

**Phase 25 claims checked against the code, and they hold:**
- **One CLI per call, no fallback:** no stale "hourly" or "next ladder candidate" wording remains.
- **Where the router tokens live:** `classify_dispatch_failure` turns both exit 75 and exit 69 into `"quota"`. `retry_after_s` and `cycle` sit only inside `status`, the parsed `AIKIT-XAI` line (`execute_dispatch.py:144-152`, `runner_dispatch.py:241-247`).
- **"Confirmed only by the catalog":** true for this adapter's path. `dispatch-task` uses the package template, whose `routerBacked` is `{}`. The flag comes from `resolve_route` (`runner_dispatch.py:182-183, 216-226`; `tooling_guidance.py:23-27`).
- **The 1800 s budget:** it covers the whole call (`cross-ai.mjs:1727-1743, 1796-1808`).
- **The 4-hour cap:** a stop past it is exit 69 (`cross-ai.mjs:2411-2416, 2459-2468`). A re-entry before the due time comes back as exit 75 with the remaining seconds (`:2417-2424`).
- **Evidence lines:** they land in `$DISPATCH_BASE.err`, because the runner's stderr is relayed live.
- **The `<files>` rule:** the dirty-tree gate is implemented at `cross-ai.mjs:2697-2708`.
- **No switch after a failure:** both failure branches stop, and none re-resolves to another candidate.

| Dimension | Score | Max | Notes |
|---|---|---|---|
| D1 Knowledge Delta | 17 | 20 | Hard-won detail (the three exclusion sets, the escalation anchor, why the task digest needs a byte-identical objective). The routing and exec-confinement notes are repeated 2–3 times. |
| D2 Mindset + Procedures | 13 | 15 | A good "permanent or same-wave?" question to ask first, and exact procedures for fragile steps. |
| D3 Anti-Patterns | 14 | 15 | NEVER index with reasons, repeated where each rule applies. |
| D4 Spec / Description | 13 | 15 | WHAT and WHEN are clear; few trigger keywords (cross-AI, external CLI, quota). |
| D5 Progressive Disclosure | 12 | 15 | MANDATORY read triggers are placed in the workflow, and design-notes is load-on-demand. The body is still 457 lines and restates parts of the policy. |
| D6 Freedom Calibration | 13 | 15 | Low freedom for state and dispatch, which fits. One fragile step is left unguarded (finding 2). |
| D7 Pattern | 7 | 10 | Recognizable Process pattern, but about 1.5–2x the usual length. |
| D8 Usability | 11 | 15 | Thorough on edge cases, with gaps in error handling (2, 4, 5). One authorization claim overstates its source (1). |

## Findings

1. **Important. Pre-dispatch choice and the Rounds 4–5 escalation are called "settled" and "authorized", but the owner has not confirmed that.**
   - **Where:** `SKILL.md:411-417` ("Two rules, not open questions… authorized"), `references/design-notes.md:128-137` ("They are settled as rules"), `references/escalation.md:76`.
   - **The record says otherwise:** `.planning/phases/25-.../25-OWNER-CAPTURES.md:124` lists "Pre-dispatch candidate selection and rounds 4-5 escalation stay (A1)" as something still to confirm, and `:144` reads "C7: not run (owner)". `25-09-SUMMARY.md:46,139` says "A1 is recorded as pending, not settled".
   - **Why it matters:** the round-2 judge fix (`b0c4d1e`) turned "pending the owner's confirmation" into "settled". That breaks the AGENTS.md rule against claiming more certainty than the source supports. It matters most for escalation, which picks a different CLI and model by itself.
   - **Fix:** keep both as executable current behavior. Say they "stay pending owner confirmation (25-OWNER-CAPTURES C7, A1)". Keep "nothing after a failure is authorized" as the one settled owner rule.

2. **Important. `dispatch-task`'s own exit status is never checked.**
   - **Where:** `SKILL.md:273-289`. The second block runs `cat "$DISPATCH_BASE.json"` and feeds it to `classify-dispatch-failure` (`:305`) without reading `.exit`.
   - **How it fails:** `main` catches only `ConfigError` (`cli.py:476-484`). `dispatch_execute` raises `ValueError` when it refuses a candidate, for example a missing target dir or a refused CLI (`execute_dispatch.py:106-133`), and a missing prompt file also raises. In those cases the command exits non-zero with a traceback and an empty `.json`. `classify-dispatch-failure` then crashes on `json.loads('')`, and no ok/quota/real_error branch matches.
   - **Fix:** in the second block, read `$(cat "$DISPATCH_BASE.exit")`. If it is non-zero, or `.json` is empty, relay the tail of `.err` verbatim and STOP as a `real_error`, with no re-resolve.

3. **Minor. The quota-branch layout contradicts its own order.**
   - **Where:** the fold bash at `SKILL.md:322-330` comes before the text at `:332-337` that says "Relay the evidence lines first… then run the fold block above". An agent reading top-down runs the fold first.
   - **Fix:** move the fold block into list item 1, after the relay.

4. **Minor. The relay step assumes runner lines always exist.**
   - **Where:** `SKILL.md:335-337, 400-403`.
   - **The gap:** the Python fail-closed paths (no Node, no template, bad model id; `runner_dispatch.py:564-573`) and an ignored status line (`:549-550`) print only `ai-kit-spec:` lines. There is no `AIKIT-XAI` or `cross-ai: report` line to relay.
   - **Fix:** "If no `AIKIT-XAI` line is present, relay the `ai-kit-spec:` lines and state that the runner did not run."

5. **Minor. A scheduled stop gives the owner no fallback.**
   - **Where:** `SKILL.md:365` says the `CronCreate` job "lives only as long as the session". Yet `:369-370` reports `$RESUME_STATE_PATH` only for unscheduled stops.
   - **Fix:** on a scheduled stop, also print `retry_after_s`, the state path and the wake prompt, so the owner can re-run it if the session ends.

6. **Minor. "the ruled single re-invoke" reads as one wake in total.**
   - **Where:** `SKILL.md:41-45`. The real contract is one one-shot wake per confirmed-router exit 75, chained until exit 69 (policy `:86-88`; SKILL `:398`).
   - **Fix:** "one one-shot per confirmed-router exit 75; a wake may schedule the next, until exit 69."

7. **Minor. Duplication wastes tokens and copies policy rules.**
   - **Where:** the Step 3 intro (`SKILL.md:203`) repeats Step 2 (`:150-155`) and `design-notes.md:24-32`. "The one exception" (`:428-430`) repeats `:137-139`. "Exec confinement" (`:419-426`) repeats `design-notes.md:76-83`. `:356-370` restates the cap, exit codes and router-confirmation rule, while the policy says "A skill links here; it does not copy the rules" (`subprocess-quota-policy.md:4-5`).
   - **Fix:** cut these to pointers, saving roughly 40 lines. Keep only the mapping that is specific to this adapter: `RETURNCODE` 75 plus both tokens.

8. **Minor. The `<files>` guidance misses line-range suffixes.**
   - **Where:** `SKILL.md:254-256`. Superpowers plans write paths like `Modify: path.py:123-145`. The runner compares exact paths (`cross-ai.mjs:2667-2676, 2706-2708`), so a suffixed path never matches and the new-session retry (rung 2) is blocked.
   - **Fix:** "strip `:N`/`:N-M` suffixes; include the Create: and Test: paths."

Not checked: I did not run the runner self-test or the skill's tests, and did not trace the shared `resolve-injection` internals beyond the CLI layer.

DIGEST beff20e2e6df85d9
CURRENT 100/120
CRITICAL 0 IMPORTANT 2
