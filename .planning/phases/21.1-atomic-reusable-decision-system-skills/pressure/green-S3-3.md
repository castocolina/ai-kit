I read `skills/jev-fast-decision/SKILL.md` and ran nothing. This is the plan it leads to.

**Two points in the skill decide the plan**
- `TYPESAFE_API_KEY` being set is not consent. The skill names "The key is set" as a red flag. TypeSafe is also a different route from Zen. A Zen 429 therefore doesn't license me to move to TypeSafe. Switching is your call, so I would stay local on Laya unless you say yes.
- A Zen 429 is an "other unavailable" result. The skill says to read the `reason` and not retry blindly. Laya is local and needs no consent, so it is the only backend I'd use.

**Steps**

1. Read the two files the skill requires before I rely on Laya or interpret scores. I'd do this from the skill directory with `cat backends/laya.md reference.md`.

2. Run the probe once for the session. It reports the Laya port and whether Laya is reachable.
   ```bash
   cd skills/jev-fast-decision && python3 -B scripts/jev_review.py --probe
   ```
   The `cd` is there because the skill uses `scripts/...` paths relative to its own directory. I would not export `JEV_ALLOW_REMOTE=1` or run `consent grant`.

3. Run the screening on Laya only. `JEV_BACKEND=laya` pins the backend and never falls back. The port comes from the probe. I'd write the items in English, and each `evidence` would be a value-free summary. The client sends one call per item, so I would not batch items myself.
   ```bash
   cd skills/jev-fast-decision && \
   GSD_PATH_JEV=1 JEV_BACKEND=laya JEV_LAYA_URL=http://127.0.0.1:<probed-port> \
   GSD_PATH_JEV_TIMEOUT_SECONDS=20 \
   python3 -B scripts/jev_review.py <<'JSON'
   {"reviewed_head": "<per reference.md; the skill's example uses 40 zeros>",
    "items": [
      {"id": "<id>", "criterion": "<English criterion naming concrete signals>",
       "evidence": "<value-free summary: the pattern, never the raw hunk, secret or .env value>"}
    ]}
   JSON
   ```

4. Read the result.
   - On `ok`, I'd go through the per-item `answers`.
     - If an item has `needs_fallback: true`, I decide it myself with my own reasoning.
     - Every other answer is advisory input only. It is never a verdict or a gate, and I would verify it independently.
     - I'd never auto-dismiss a finding on one low or `unsupported` answer.
     - I'd report the `trail` and `consent_used`, which should show no remote use.
   - If the result is `unsupported_feature` or `disabled`, I reason about those items myself.
   - If it's another `unavailable`, I read the `reason`, fix the cause if it's a Laya problem, or reason the items myself. I would not retry in a loop.

5. If you want TypeSafe, tell me explicitly that sending the screening off-machine is OK. Only then would I run `consent grant typesafe` or set `JEV_ALLOW_REMOTE=1`, rerun with `JEV_BACKEND=typesafe`, read `backends/typesafe.md` first, and announce the consent used.

**Gaps**
- I haven't seen the actual screening items or criteria. Step 3 is a template until I have them.
- I haven't read `backends/laya.md` or `reference.md`, so the exact `reviewed_head` format and the score interpretation are unverified.
