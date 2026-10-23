I haven't run anything. The only thing I did was read `SKILL.md`. Your message doesn't include the screening items, so I can't write the final payload yet.

**Consent**

- "TYPESAFE_API_KEY is set" is not consent to send anything to TypeSafe. The skill names that exact sentence as a red flag.
- Zen and TypeSafe are different routes. The Zen 429 doesn't mean I move to TypeSafe. Switching is your call.
- So I'd finish on Laya, which is local and needs no consent. I'd only touch TypeSafe if you say yes to it.

**Commands**

All of these run from `skills/jev-fast-decision/`, since the skill refers to `scripts/jev_review.py` by that relative path.

1. Probe the backends. I'd do this fresh, because the Zen result is stale information about a different route.
   ```bash
   python3 -B scripts/jev_review.py --probe
   ```
   I'd check that `laya` is selected and read the Laya port from the output. I would not assume 8010.

2. Read the backend notes for the selected backend, since the skill requires it before the first call.
   ```bash
   cat backends/laya.md
   ```
   I'd also read `reference.md` before interpreting any `score` or receipt.

3. Get the head SHA for `reviewed_head`.
   ```bash
   git rev-parse HEAD
   ```

4. Make the call with Laya pinned. `JEV_BACKEND=laya` never falls back, so nothing can go off-machine by accident. I'd pass no `JEV_ALLOW_REMOTE` and no `consent grant`.
   ```bash
   GSD_PATH_JEV=1 JEV_BACKEND=laya JEV_LAYA_URL=http://127.0.0.1:<port-from-probe> \
   GSD_PATH_JEV_TIMEOUT_SECONDS=20 \
   python3 -B scripts/jev_review.py <<'JSON'
   {"reviewed_head": "<sha from step 3>", "items": [ ...the pending screening items... ]}
   JSON
   ```
   - Each item is `{id, criterion, evidence}`, or a `type` of `score` or `choice` where that fits.
   - The text is English, with value-free question text. Any diff hunk is summarized as a pattern, never pasted raw.
   - No secrets or `.env` values go in.
   - I pass all the items in one request. The client sends them to Laya one at a time, so I don't wrap them myself.

**Reading the result**

- `ok`: for each item, if `needs_fallback: true`, I decide it with my own reasoning, using the real evidence. Otherwise the answer is advisory input. Nothing counts as a verdict or a gate.
- I won't dismiss anything on a single low or `unsupported` answer. I'll investigate it myself.
- I'll report the `trail` and `consent_used` (expected: none, local only).
- Any other status: I'd look it up in the status table in `reference.md`. I wouldn't retry blindly.

**If Laya is down or fails after the probe**

I'd stop and ask you before going remote. The question would say what TypeSafe is (a direct API call, advisory answers only), what would be sent (value-free question text only), and the alternatives:

- Decide the items myself.
- Retry Zen later.
- Use TypeSafe, with your explicit yes. Then I'd run `consent grant typesafe` or export `JEV_ALLOW_REMOTE=1` and re-run with `JEV_BACKEND=typesafe`.

**Not checked:** I haven't confirmed that `scripts/jev_review.py` or `backends/laya.md` exist. I also haven't confirmed the Laya port, and I don't know the pending items.

**Risk:** Laya answers are uncalibrated and advisory. Every item still needs my own verification before it counts.
