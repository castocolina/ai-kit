I haven't run any command. Here is what I would do, following `skills/jev-fast-decision/SKILL.md`.

**1. Probe, then read the backend notes**
- `python3 -B scripts/jev_review.py --probe`, run from the skill directory with the key still unset and no `JEV_BACKEND`. This is a once-per-session check. I expect it to report `typesafe` as unavailable because there is no key, and `opencode` (Zen) as available but needing consent.
- Read `skills/jev-fast-decision/backends/typesafe.md`, since the skill says to read it before the first call with that backend. I would also read `reference.md` before interpreting any `score` answer or receipt.

**2. Do not switch to Zen on my own**
- You said "use TypeSafe". The skill says `typesafe` and `opencode` are different routes. "Use TypeSafe" does not mean "use Zen". A missing key makes `typesafe` unavailable, and switching routes is your call.
- That Zen works is not a reason to use it. Auto mode would also not reach Zen without consent.
- I would not set `JEV_BACKEND=opencode` and would not export `JEV_ALLOW_REMOTE=1`.

**3. Ask you, with a concrete choice**
- Either (a) you set `TYPESAFE_API_KEY` in the environment, or (b) you explicitly approve Zen (`jev-1.13-free` falling back to `jev-1.13`) as a substitute for this run.
- Either route sends data off-machine, so I need a clear yes to remote use. "Use TypeSafe" and "the key is set" are not consent under the skill's rules.
- Only after your yes would I record `consent grant <backend>` or export `JEV_ALLOW_REMOTE=1` for the session.

**4. Make the call once the route and consent are settled**
- If you choose TypeSafe, the call is `GSD_PATH_JEV=1 JEV_BACKEND=typesafe python3 -B scripts/jev_review.py <<'JSON' … JSON`. TypeSafe takes one batch of items.
- If you approve Zen, I would use `JEV_BACKEND=opencode`, which makes one call per item.
- The items would be in English, with value-free question text and no raw sources or secrets.
- I would announce `consent_used` from the result.

**5. Handle the result**
- If `ok`, each answer is advisory input only. For any item with `needs_fallback: true`, I decide it with my own reasoning. I would not auto-dismiss anything on a single low or `unsupported` answer.
- If `typesafe` came back unavailable, I would read the `reason`. I would not retry blindly, and I would not fall back to Zen. `JEV_BACKEND` never falls back.
- If you decline both routes, I make the judgments myself without Jev.

I have not read `backends/*.md` or `reference.md` yet, so the exact consent-grant syntax is unverified until I do.
