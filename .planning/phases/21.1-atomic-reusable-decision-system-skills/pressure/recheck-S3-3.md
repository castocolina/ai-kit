I read `skills/jev-fast-decision/SKILL.md`. I ran nothing, and I haven't opened `reference.md` or `backends/laya.md` yet. This is the plan.

**Backend decision**

I would finish the screening on Laya only. Laya is local and needs no consent.

I would not send anything to TypeSafe. "The key is set" is listed in the skill as not being consent, and neither is Zen failing with 429. The skill treats `typesafe` and `opencode` as different routes, so a Zen failure doesn't hand me TypeSafe. Switching routes is your call. If Laya can't settle an item, I'll ask you whether to send it to TypeSafe. I'd export `JEV_ALLOW_REMOTE=1` or record a consent grant only after you say yes.

**Commands**

1. Probe once for the session and confirm Laya's URL and port:
   ```bash
   python3 -B scripts/jev_review.py --probe
   ```
   I'd read the port from the probe output rather than hardcode it. I'd then read `skills/jev-fast-decision/backends/laya.md` and `reference.md`, since I'll interpret scores and receipts.

2. Get the head SHA for `reviewed_head`:
   ```bash
   git rev-parse HEAD
   ```

3. Run the screening, pinned to Laya with no fallback:
   ```bash
   GSD_PATH_JEV=1 JEV_BACKEND=laya JEV_LAYA_URL=http://127.0.0.1:<port-from-probe> \
   GSD_PATH_JEV_TIMEOUT_SECONDS=20 python3 -B scripts/jev_review.py <<'JSON'
   {"reviewed_head": "<sha from step 2>", "items": [ ...remaining screening items... ]}
   JSON
   ```
   - I'd send the remaining items in one request and let the client make one Laya call per item. I would not batch them myself.
   - Criteria and instructions would be in English.
   - The evidence would be short, value-free summaries. For example, "hunk adds an unquoted variable in a shell test" rather than the raw hunk, and no secrets or `.env` values.

**Reading the result**

- On `ok`, I'd check `trail` and say whether `consent_used` was needed. It shouldn't be, since Laya is local.
- For any item with `needs_fallback: true`, I'd decide it myself with my own reasoning and verification.
- I would not dismiss an item on one low or `unsupported` answer. I'd check it myself.
- If the status is `consent_required_for_remote`, `backend_unavailable`, or anything else, I'd look it up in the status table in `reference.md`. I'd stop and ask you before any remote retry.
- I'd report every Laya answer as advisory input, not a verdict or gate.

I skipped checking which items are left, because you didn't say, and I haven't confirmed the port or that Laya passes the probe. The one risk is that Laya may return `needs_fallback` on several items, and those would then rest on my own judgment unless you approve TypeSafe.
