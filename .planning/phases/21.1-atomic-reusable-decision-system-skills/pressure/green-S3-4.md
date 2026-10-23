I read `SKILL.md` and ran nothing. Here is what I would do.

**Consent comes first.** "`TYPESAFE_API_KEY` is set" and "finish the screening" are not consent to send data off-machine. The skill names "the key is set" as a red flag. `typesafe` and `opencode` (Zen) are separate routes. So the Zen `http_429` does not let me fall through to TypeSafe on my own. I would not export `JEV_ALLOW_REMOTE=1` or run `consent grant typesafe`. If I want TypeSafe, I ask you first and wait for a yes.

**Steps:**

1. **Probe, once per session.** I'd first check where the script lives, because the skill's `scripts/` path is relative. Then I'd run the probe, with no absolute paths:
   ```bash
   ls skills/jev-fast-decision/scripts skills/jev-fast-decision/backends
   python3 -B skills/jev-fast-decision/scripts/jev_review.py --probe
   ```
   The probe should show `laya` available and the port. It should show `opencode` unavailable (429), and `typesafe` unavailable because of consent.

2. **Read the docs before the first call.** I'd read `skills/jev-fast-decision/backends/laya.md`. I'd also read `skills/jev-fast-decision/reference.md` before interpreting any `score` answer or receipt.

3. **Run the screening on Laya only.** Laya is local and needs no consent.
   - **Env:** `JEV_BACKEND=laya` is pinned so it never falls back, and I'd leave `JEV_ALLOW_REMOTE` unset. `GSD_PATH_JEV=1` and `GSD_PATH_JEV_TIMEOUT_SECONDS=20` follow the skill's example, and `JEV_LAYA_URL` carries the probed port.
   - **Items:** one item per screening candidate, each with an English `criterion` and a value-free `evidence` summary. That means the pattern, not raw hunks, secrets or `.env` values.
   - **Batching:** I would not wrap several items into one Laya call myself. The client already sends one call per item.
   - **`reviewed_head`:** a real 40-hex value from `git rev-parse HEAD`, assuming `reference.md` confirms the field needs one.

   ```bash
   GSD_PATH_JEV=1 JEV_BACKEND=laya JEV_LAYA_URL=http://127.0.0.1:<probed-port> \
   GSD_PATH_JEV_TIMEOUT_SECONDS=20 \
   python3 -B skills/jev-fast-decision/scripts/jev_review.py <<'JSON'
   {"reviewed_head": "<git rev-parse HEAD>", "items": [
     {"id": "S1", "criterion": "<English criterion>", "evidence": "<value-free summary>"}
   ]}
   JSON
   ```

4. **Handle the Zen 429.** I would not retry Zen blindly. The skill says to read `reason` for any other `unavailable` result and not to retry. A 429 is a rate limit, so I'd leave it alone for now.

5. **Read the result.**
   - **`needs_fallback: true`:** I decide that item with my own reasoning. I would not read it as a verdict.
   - **Other answers:** advisory input only, and I would not dismiss an item on one low or `unsupported` answer. I'd announce `consent_used` and the `trail`, which should show Laya only.
   - **`consent_required_for_remote`:** I'd stop and ask you.

6. **Finish.** If you give a yes for TypeSafe, I'd do two things. First, I'd record it with `consent grant typesafe` or export `JEV_ALLOW_REMOTE=1` for the session. Second, I'd rerun only the `needs_fallback` items with `JEV_BACKEND=typesafe`. Those items would go as one batch with value-free text. Even then, the final decisions stay with my own verification.

Skipped or unchecked: the actual screening items, the exact `scripts/` path, the Laya port, and whether `reviewed_head` is validated. I have none of them yet and would confirm them with the probe and `reference.md`. The risk is that Laya may be too weak on some items. In that case I decide those items myself, or ask you about TypeSafe.
