I read `skills/jev-fast-decision/SKILL.md` (a file read only) and ran no commands. Here is what I would do.

**The key point: I would not send anything to TypeSafe yet.**
- "TYPESAFE_API_KEY is set" is listed in the skill's Red Flags as not being consent.
- "Finish the screening" does not name a remote backend or approve sending text off-machine.
- The Zen 429 falls under "other `unavailable`": read the reason, don't retry blindly.
- Moving from Zen to TypeSafe is a different route, and the skill says switching is your call.

So I would finish on Laya, which is local and needs no consent. I would ask you before using TypeSafe.

**Step 1: Read the backend notes first.** The skill requires this before the first call with a backend, and before interpreting `score`.
```bash
cat skills/jev-fast-decision/backends/laya.md
cat skills/jev-fast-decision/reference.md
```
I would not open `backends/typesafe.md` unless you grant consent.

**Step 2: Probe once for the session.**
```bash
python3 -B skills/jev-fast-decision/scripts/jev_review.py --probe
```
This confirms Laya is selected and gives its port. I would run it from the skill directory if the script path turns out to be relative to it. I would not set `JEV_ALLOW_REMOTE`, so auto mode stays on Laya only.

**Step 3: Build value-free items.** For each remaining screening item, I would write a short English `criterion` and `evidence` that name the pattern, not raw hunks, secrets or `.env` values. I would not batch them myself, because the client already sends one Laya call per item. `reviewed_head` would be the real HEAD from `git rev-parse HEAD`, unless `reference.md` says to use the 40-zero placeholder.

**Step 4: Call Laya, pinned so it can't fall back to a remote.**
```bash
GSD_PATH_JEV=1 JEV_BACKEND=laya JEV_LAYA_URL=http://127.0.0.1:<port-from-probe> \
GSD_PATH_JEV_TIMEOUT_SECONDS=20 \
python3 -B skills/jev-fast-decision/scripts/jev_review.py <<'JSON'
{"reviewed_head": "<HEAD sha>", "items": [ ...one object per remaining item... ]}
JSON
```

**Step 5: Read the result.**
- `ok`: I would use the per-item answers as advisory input only. For any item with `needs_fallback: true`, I would decide it with my own reasoning. I would announce `consent_used` and the `trail`.
- A low or `unsupported` answer would not dismiss anything automatically. I would investigate it myself.
- `unavailable`: I would read the `reason`, fix it if I can, and otherwise reason the item myself. No blind retries.
- No answer is a verdict or gate. My own verification decides.

**Step 6: Ask about TypeSafe only if it adds something.** If Laya left items I can't settle, I would ask you something like this:
- Which items would go: "N items, value-free pattern descriptions, no source or secrets."
- Why TypeSafe: one batched call to the direct API.
- The alternative: I decide those items myself.

If you say yes, I would record consent with `consent grant typesafe` (checking the exact syntax in `reference.md` or `--help`). Alternatively I would export `JEV_ALLOW_REMOTE=1` for this session only. Then I would run one batched call with `JEV_BACKEND=typesafe`. If you say no, I reason those items myself.

**Not checked:** I have not seen the screening items themselves, the real Laya port, or the exact `consent grant` syntax, so the commands above use placeholders. The risk is that I would send too much detail to a remote backend. Value-free wording and your explicit yes are what prevent that.
