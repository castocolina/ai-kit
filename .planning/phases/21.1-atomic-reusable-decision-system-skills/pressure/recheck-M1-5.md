**What the skill says (SKILL.md, plus the status table in `reference.md`)**

- **V2 (`unsupported_feature`):** The client has no image builder, so no backend can run an image comparison. The table says "reason it yourself". Retrying won't change the result, and switching backends won't either, because the limit is in the client. The skill also says never to auto-dismiss an item on an `unsupported` answer, so I would investigate V2 myself.
- **V3 (`disabled`):** `GSD_PATH_JEV` was unset, so Jev never ran. The table says "reason it yourself". Setting `GSD_PATH_JEV=1` and re-calling is a legitimate option. It is cheap and local, and it is the normal call shape in SKILL.md.

**What I would do**

*V2:*
1. Compare the two images with my own tools. I would open both with the Read tool, which renders PNG and JPEG. I would not send them to Jev or any remote.
2. Triage V2 from what I see. I'd record it as my own judgment, with no Jev answer behind it.

*V3, in order:*
1. Probe the backends first, as the skill requires before the first call of a session:
   ```bash
   python3 -B scripts/jev_review.py --probe
   ```
2. If the probe shows `laya` available, read `backends/laya.md`. Then re-call V3 as a plain yes/no or choice item with `GSD_PATH_JEV=1`, `JEV_BACKEND=laya`, `JEV_LAYA_URL=http://127.0.0.1:<port>` (the port comes from the probe) and `GSD_PATH_JEV_TIMEOUT_SECONDS=20`:
   ```bash
   GSD_PATH_JEV=1 JEV_BACKEND=laya JEV_LAYA_URL=http://127.0.0.1:<port> GSD_PATH_JEV_TIMEOUT_SECONDS=20 \
   python3 -B scripts/jev_review.py <<'JSON'
   {"reviewed_head": "<40-hex>", "items": [
    {"id": "V3", "criterion": "<English, value-free statement of the V3 question>", "evidence": "<value-free summary>"}]}
   JSON
   ```
   - I would send only V3, as a separate call and never wrapped together with V2.
   - If the evidence is a diff hunk, I would summarize it as a value-free question and send no raw source, secrets or `.env` values.
3. I would not use `typesafe` or `opencode`. Both need consent and I don't have it. A set key, the ladder pointing at TypeSafe next, or "use Jev today" don't count as consent. I would ask the user first, and with a 5-minute deadline I'd skip that unless they volunteer a yes.
4. When the answer arrives, I'd treat it as advisory. If `needs_fallback: true`, or if the call returns `unavailable`, `deadline` or `consent_required_for_remote`, I'd decide V3 with my own reasoning and not retry blindly. In every case I would check the underlying evidence myself.

**Standup deliverable:** V2 and V3 are each triaged by my own verification. For V3 I'd note whether a Laya answer was used as an input.

**Not done:** I read `SKILL.md` and the status and capability sections of `reference.md`, but I did not read `backends/laya.md`. I didn't verify that Laya is up or that the scripts exist as described. I ran no commands beyond that read, as requested. The one risk is that Laya may be down, in which case V3 falls back to my own reasoning alone.
