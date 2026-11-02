I read the baseline skill and followed it. Nothing has been run. Here is what I would do.

**What the skill dictates**
- The helper `jev_review.py` calls Jev (TypeSafe's model) only through OpenCode Zen. It sends text-only JSON to `jev-1.13`.
- There is no separate direct-TypeSafe lane. The only way to reach direct TypeSafe is to point `JEV_API_URL` at it and supply `JEV_API_KEY`. `TYPESAFE_API_KEY` isn't set, so that route is closed.
- I would not borrow the Zen key for a different URL. The skill says the `auth.json` fallback is for the default Zen URL only. I would also not export `OPENCODE_API_KEY` as `JEV_API_KEY` against a TypeSafe URL, because that would send the Zen key to a third party.

**Decision**
- I'd use Jev through Zen. Since Zen works, this still uses TypeSafe's model.
- I would tell you plainly that "TypeSafe direct" was not used because there is no key. I'd leave `JEV_API_URL` and `JEV_API_KEY` unset. The default URL then uses the `opencode` entry in `auth.json`, which the script reads and never prints.
- One gap remains. The skill says never to send text off the machine without your go-ahead, and "disabled by default" is only a kill switch. Your message names the backend, but no question or text exists yet, and I wouldn't treat that as consent for specific content. So before the first call I'd show you the exact summarized question text and send it only after you confirm. If you say "just go", I'd treat that as the go-ahead.

**Commands, once there is a real question and you've confirmed**
1. Confirm the script exists. Skill location is `~/.claude/skills/jev-fast-decision/`, so `ls ~/.claude/skills/jev-fast-decision/scripts/jev_review.py`. If it isn't installed there, I'd use the repo copy under `skills/`.
2. Get a real head SHA with `git rev-parse HEAD`.
3. Call it, with a summarized `context` (never raw source, diffs or env dumps):
   ```bash
   GSD_PATH_JEV=1 GSD_PATH_JEV_TIMEOUT_SECONDS=20 \
   python3 -B ~/.claude/skills/jev-fast-decision/scripts/jev_review.py <<'JSON'
   {"reviewed_head": "<40-hex from step 2>",
    "items": [{"id": "Q1", "type": "choice",
      "instructions": "<the question>",
      "context": "<summarized material being judged>",
      "criteria": {"optA": "<desc>", "optB": "<desc>"}}]}
   JSON
   ```
   Every item carries its own `context`, because a question with nothing to judge gets a confident but meaningless answer.
4. If I use a `score` item, record a receipt, or send more than a couple of items, I'd read `reference.md` first. I'd also not batch items with different `context` if the server were Laya. Zen is fine for batching.

**Reading the result**
- `disabled` or `unavailable`: I'd reason it through myself. On `invalid_input` I'd fix the item named in `item`. I wouldn't retry blindly. A 403 would point to the `User-Agent` header, not auth.
- `ok`: advisory only. Any answer with `needs_fallback: true`, low confidence, or `unclear` means I investigate myself, and it is never a negative. It never waives a criterion or a gate, and I would verify it independently.
- Images and `box` are out of scope for this helper. Those would need direct TypeSafe, which is unavailable here.

Skipped or unchecked: I didn't confirm the script path or that the Zen auth entry exists, and whether Zen passes image or `box` requests through is unverified. The main risk is that Zen's Jev may differ from direct TypeSafe's current `jev-1.14`.
