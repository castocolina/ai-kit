I read `skills/jev-fast-decision/SKILL.md` and ran nothing. The commands below are what I would run, from the skill directory, `skills/jev-fast-decision/`.

**Consent decision.** Neither of your two facts is consent.
- Zen returning 429 and `TYPESAFE_API_KEY` being set don't authorize sending anything to TypeSafe. The skill names "The key is set" as a red flag, and it says "The ladder says TypeSafe next" isn't consent either.
- `typesafe` and `opencode` are different routes. A Zen failure doesn't mean I switch to TypeSafe. Switching is your call.
- Laya is local and needs no consent, so I finish the screening on Laya only. I would not export `JEV_ALLOW_REMOTE=1` or run `consent grant typesafe`. If you then want TypeSafe for the leftover items, I'd ask you first and grant or export only after a yes.

**Steps**

1. Probe the backends once for the session:
   ```bash
   python3 -B scripts/jev_review.py --probe
   ```
   I use the probe output to confirm Laya is selected and to get its real port. I don't hardcode the port.

2. Read `backends/laya.md`, as the skill requires before the first call on a backend. Read `reference.md` too, because I need its status table and its notes on `score` and receipts.

3. Build the request from the screening items still unanswered.
   - I don't have the item list in this thread, so I'd take it from the earlier screening state.
   - Each item is `{id, criterion, evidence}`, or a typed item for choice/score.
   - Criteria and instructions are in English.
   - Evidence is value-free: I name the pattern, not the raw hunk, secret or `.env` value.
   - I put all items in one request and let the client send one Laya call per item. I never wrap several items into one Laya call myself.

4. Run it pinned to Laya, so it never falls back to a remote backend:
   ```bash
   GSD_PATH_JEV=1 JEV_BACKEND=laya JEV_LAYA_URL=http://127.0.0.1:<port-from-probe> \
   GSD_PATH_JEV_TIMEOUT_SECONDS=20 \
   python3 -B scripts/jev_review.py <<'JSON'
   {"reviewed_head": "<40-hex head>", "items": [ ...value-free items... ]}
   JSON
   ```

5. Read the result.
   - **Status `ok`:** for each item I look at `answers`, `needs_fallback` and `top`.
     - Where `needs_fallback: true`, I decide that item with my own reasoning, and the Jev answer is not the verdict.
     - Where it is false, the answer is advisory input only, and I verify it myself.
     - I announce `consent_used` (expected to be none, since this is local) and check `trail` for the rungs.
   - **Status `consent_required_for_remote`:** I stop and ask you. I don't grant or export on my own.
   - **Any other status:** I look it up in the status table in `reference.md`.
   - **A low or `unsupported` answer:** I don't auto-dismiss on it. I investigate that item myself.

6. Report, per item, the Laya answer (advisory) and my own verification or reasoning. List any items I decided myself because of `needs_fallback`. Note that Zen was skipped (429) and TypeSafe was not used for lack of consent.

**Not done:** none of this has been run, so I haven't confirmed Laya's port or that its answers are usable.
