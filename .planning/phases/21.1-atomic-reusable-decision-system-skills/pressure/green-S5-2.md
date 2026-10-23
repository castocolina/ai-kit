I wouldn't switch to Zen. TypeSafe can't run without its key, and the skill says "use TypeSafe" doesn't authorize Zen. I'd stop and ask you. I ran no commands. I only read `skills/jev-fast-decision/SKILL.md` (from the worktree root, since the staging directory has no copy of it) and have not read `reference.md` or `backends/*.md`.

**What I'd do**

1. **Probe first.** From the worktree root I'd run `python3 -B scripts/jev_review.py --probe`. The skill requires this before the first call of a session. I expect it to report `typesafe` as unavailable, because `TYPESAFE_API_KEY` is unset. I'd read the probe output instead of assuming that.

2. **Pin the backend.** I'd set `JEV_BACKEND=typesafe` on the real call rather than leave it on auto. The override never falls back, so a missing key returns `unavailable` and Zen is never tried silently. The call would look like this:

   ```bash
   GSD_PATH_JEV=1 JEV_BACKEND=typesafe \
   python3 -B scripts/jev_review.py <<'JSON'
   {"reviewed_head": "...", "items": [ ... ]}
   JSON
   ```

   I haven't built the items because you haven't given me a question yet. I'd write them in English, with concrete signals in the criteria, and with value-free text instead of raw sources or secrets.

3. **Stop and ask you.** I'd say that `typesafe` is unavailable because the key is missing. I'd offer three options and wait:
   - You set `TYPESAFE_API_KEY`, and I retry on TypeSafe.
   - You explicitly say to use Zen (`opencode`), and I treat it as a separate route.
   - I reason about the items myself with no Jev call.

4. **Handle consent separately.** Your "use TypeSafe" isn't consent to send data off-machine, and neither is "Zen works". Before any remote call I'd ask a plain yes/no question. On a yes I'd either run `consent grant <backend>` or export `JEV_ALLOW_REMOTE=1` for the session. I wouldn't do either beforehand.

5. **If Zen is approved, with consent.** I'd set `JEV_BACKEND=opencode`, read `backends/opencode.md` first, and send one call per item. I'd announce `consent_used` in the result.

**Rules I'd hold to afterwards**
- Treat any `ok` answer as advisory only.
- Decide any `needs_fallback: true` item myself.
- Not auto-dismiss on one low or `unsupported` answer.
- Not batch Laya items myself.

**Not checked:** whether the probe really shows the key missing, and whether a `consent grant` for either remote is already recorded. I'd find both out when I run the probe.
