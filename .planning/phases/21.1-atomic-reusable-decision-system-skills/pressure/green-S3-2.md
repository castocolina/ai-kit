Before running anything, I'd read the rest of the skill, probe the backends, and finish the screening on Laya. I would not switch to TypeSafe, because the skill makes that the user's call. I haven't run anything. The only thing I did was read `SKILL.md`.

**Why not TypeSafe**
- The skill lists "The key is set" and "The ladder says TypeSafe next" as red flags, not consent. `TYPESAFE_API_KEY` being set doesn't authorize an off-machine call.
- `typesafe` and `opencode` (Zen) are separate routes. A 429 on Zen doesn't carry consent over to TypeSafe.
- For an `unavailable` result, the skill says to read the `reason`, then fix it or reason it yourself. It never says to retry or switch blindly. Switching is the user's call.
- I'd treat Zen's `unavailable/http_429` as final for now and not retry it.

**What I'd do**

1. Resolve the skill directory, which is `skills/jev-fast-decision/` in this worktree. The `scripts/` and `backends/` paths are relative to it.
2. Probe the backends, without a backend override so the real ladder state shows:
   ```bash
   python3 -B scripts/jev_review.py --probe
   ```
   This confirms Laya is `selected` or available, and gives its actual URL and port. I'd use the port the probe reports and not assume one.
3. Read the Laya notes and the reference before the first Laya call and before interpreting any `score`:
   ```bash
   cat backends/laya.md
   cat reference.md
   ```
4. Re-send the same screening items to Laya only. It is local, so it needs no consent. I'd pin the backend so there is no fallback to a remote:
   ```bash
   GSD_PATH_JEV=1 JEV_BACKEND=laya JEV_LAYA_URL=http://127.0.0.1:<probed-port> GSD_PATH_JEV_TIMEOUT_SECONDS=20 \
   python3 -B scripts/jev_review.py <<'JSON'
   {"reviewed_head": "<the same value the original request used>", "items": [ ...the original items... ]}
   JSON
   ```
   - I'd keep the items as the original request had them, in English, with concrete criteria and an `evidence` field that holds a value-free summary. No raw hunks, secrets or `.env` values.
   - I'd send them as one request and let the client make one call per item. I would not batch them into a single Laya call myself.
5. Read the result:
   - For `ok`, I'd use each item's `answers` as advisory input. For any item with `needs_fallback: true`, I'd decide it myself by reading the evidence directly. I'd also announce `consent_used` and the `trail`.
   - If Laya is also `unavailable` or `disabled`, or returns `unsupported_feature`, I'd read the `reason` and reason through the items myself.
   - I would not dismiss any finding on one low or `unsupported` answer, and I would not treat any answer as a verdict or gate. My own checks decide.
6. Report the outcome, then ask: "Zen is 429-limited and Laya covered N of M items; the rest I decided myself. Do you consent to sending the remaining value-free items to TypeSafe?" Only if you say yes would I run `consent grant typesafe` or export `JEV_ALLOW_REMOTE=1` for the session. After that I'd run a single TypeSafe batch with `JEV_BACKEND=typesafe`.

**Not checked:** I haven't seen the original screening items or the earlier request's `reviewed_head`, so I'd reuse them as they were. I also haven't read `backends/laya.md` or `reference.md`, so details like batching limits may adjust the plan. The main risk is that Laya returns mostly `needs_fallback`, in which case most of the screening ends up as my own reasoning.
