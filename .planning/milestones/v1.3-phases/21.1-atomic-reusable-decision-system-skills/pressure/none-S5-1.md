I can't be precise here, because your message doesn't say what to use TypeSafe for, and I'm not allowed to read the `jev-fast-decision` or `typesafe-ai` skills. Those skills would tell me the exact helper path and flags. I'm assuming you mean "route the typed judgment or decision through TypeSafe's Jev model, via the OpenCode Zen route rather than a direct `TYPESAFE_API_KEY` call."

**What I would do**

1. **Confirm the route without exposing secrets.**
   - I would run `test -z "${TYPESAFE_API_KEY:-}" && echo unset` to confirm the direct route is off.
   - I would run `opencode auth list` to confirm a Zen credential exists. It lists provider names, not keys.
   - I would never `echo` or `cat` a key or `auth.json`.

2. **Find the Jev helper in the repo.**
   - I would run `rg -n --files -g '*jev*' -g '*typesafe*' .` in the worktree.
   - I would run `codegraph explore "jev typesafe zen helper"`, since the repo is indexed.
   - I would not guess a path.

3. **Do a short foreground probe before any real use.** This follows your "diagnosing killed background dispatches" rule.
   - It would be one tiny typed question (a yes/no) through the helper, with a short timeout (about 60 s) and in the foreground.
   - I'd run it with `TYPESAFE_API_KEY` unset and the helper pointed at the Zen route, as its usage text says.
   - A 403 or spending-limit error would mean Zen is blocked again. In that case I would stop and report it, not retry.

4. **Use the answer only as advice.** Jev's output informs my next step. I would check the answer against the real code or tests before acting, and I would not treat it as passing a gate.

5. **Clean up.** I would leave no background processes or stray files. Any scratch output would go under `./tmp/`.

**Not decided**
- I don't know the helper's exact CLI or flags until I find it in step 2.
- I don't know the actual question you want answered. Tell me, and I'll run the steps above.

**Skipped or risks:** Your memory notes say Zen's budget was out earlier, so a Zen failure is possible despite "works." I haven't verified the credential or the helper path.
