The request doesn't say what to use TypeSafe for, so this is a plan for the routing only. I haven't run anything.

**What I'd do**
1. Treat the direct TypeSafe route as unavailable, since `TYPESAFE_API_KEY` is unset. I'd use the Zen route, which is how the `jev-fast-decision` skill reaches TypeSafe's Jev model. That overrides my memory note that Zen's budget was out, which is probably stale now that you say Zen works.
2. Run two read-only pre-flight checks, neither of which prints a key:
   ```
   test -n "${TYPESAFE_API_KEY:-}" && echo set || echo unset
   opencode auth list
   ```
   The first confirms the direct key really is unset. The second confirms a Zen credential is configured.
3. Run the skill's own helper with one small typed question as a probe, such as a yes/no (`noul`) question. It would go through Zen, with no direct-API environment variables set. This confirms Zen is live and not out of budget.
4. If the probe works, send the real questions as one batch of typed questions (yes/no, choice or score). I'd supply the evidence as text, because the helper is text-only.
5. Treat the answers as advisory. I'd check the facts myself before acting on them, and I'd never let a Jev answer satisfy a gate. If Zen returns a billing or 403 error, I'd report that and stop. I wouldn't retry, and I wouldn't switch to a direct key, because there isn't one.

**Gaps**
- I can't give you the helper's exact path and flags. They're in the skill's `SKILL.md`, which I was told not to read, and I won't guess them.
- I need the actual questions or decisions to put to Jev before I can run step 4.
