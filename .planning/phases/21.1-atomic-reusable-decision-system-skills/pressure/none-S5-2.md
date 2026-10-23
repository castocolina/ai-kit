You haven't said what to do with TypeSafe, so I'd first confirm that. Your message sets the backend but gives no task. If the task is a typed judgment (yes/no, pick one option, or a score), I'd route it through Jev on TypeSafe via OpenCode Zen. I wouldn't use `TYPESAFE_API_KEY`.

Nothing below has been run. I haven't read the skill, because you told me not to, so I can't give the helper's exact invocation. I won't guess it.

1. **Check the key without printing it.** I'd run `test -n "${TYPESAFE_API_KEY:-}" && echo set || echo unset`. This confirms the direct route is unavailable and avoids putting any secret in output.

2. **Find the Zen path.** I'd run `rg -n "decide.py|jev|zen" tools skills .claude --glob '!*.lock'`, or ask CodeGraph via `codegraph explore "jev decide zen"`. The goal is the repo's existing decision helper (the `decide.py` ladder from your notes) and the flag or env var that selects Zen over direct TypeSafe.

3. **Check Zen reachability with one small probe.** I'd use the helper's own Zen mode, with a throwaway yes/no question and a short timeout. If you want a manual check, `curl` against Zen's endpoint with the key read from the opencode auth store, but only if you approve that. It would involve a real credential, and your notes say to avoid steps that trigger permission prompts.

4. **Run the real question through the helper.** I'd pass the state as text with a typed question, and set the route to Zen explicitly so it can't fall back to the missing TypeSafe key. I'd treat the answer as advisory and verify it against the real code or tests before acting.

5. **Handle failures.** If Zen returns a billing or 403 error, I'd report it and stop, because those errors don't recover by retrying. I would not silently fall back to Laya. I'd ask you before switching routes.

Please tell me the actual question or task, and whether you want the repo's `decide.py` helper or a direct Zen call.

Not checked: the helper's real CLI flags, and whether Zen is reachable right now. The main risk is that I pick the wrong route flag, so I'd confirm it from `--help` output before the first real call.
