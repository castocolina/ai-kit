Nothing has been run. I only read the baseline `SKILL.md`. This is what I would do.

**How I read "use TypeSafe"**

Jev is TypeSafe AI's model, and this skill reaches it through OpenCode Zen. You said `TYPESAFE_API_KEY` is unset and Zen works, so I would use the Zen route. I would tell you it is Jev via Zen and not TypeSafe's direct API. The skill has no `TYPESAFE_API_KEY` path. Direct access would need `JEV_API_URL` plus `JEV_API_KEY`, and no such key exists. I would not look for, copy or invent a key to force the direct route. I would only use the direct API for images or `box` questions, where the skill says Zen pass-through is unverified.

**Steps**

1. **Settle what to ask.** You gave no question or evidence, so I would ask for it or take it from the surrounding task. I would write it as a short, self-contained summary with the material to judge in each item's `context`, or inline in `instructions`. I would not send raw files, diffs that may contain secrets, or environment dumps.

2. **Get your go-ahead before the first call.** "Disabled by default" is a kill switch, not consent, and "use TypeSafe" doesn't cover any particular text. I would show you the exact JSON I plan to send and ask for a yes. I would also remind you that the answer is advisory only.

3. **Read `reference.md` first if it applies.** I would read it with `Read` if I use a `score` item, build a request with more than a couple of items, or record an `ok` receipt in a durable artifact. A single quick shorthand `choice` call can skip it.

4. **Check the script exists, without printing any key.**
   ```bash
   test -f ~/.claude/skills/jev-fast-decision/scripts/jev_review.py && echo present
   ```
   I would not echo `OPENCODE_API_KEY` or `auth.json`. The script reads the `opencode` entry from `auth.json` itself and never prints it.

5. **Make one call after you approve.** I would use no `JEV_API_URL` (so the default Zen URL and the `auth.json` fallback apply), the required timeout, and a placeholder 40-hex `reviewed_head`, or the real HEAD from `git rev-parse HEAD`.
   ```bash
   GSD_PATH_JEV=1 GSD_PATH_JEV_TIMEOUT_SECONDS=20 \
   python3 -B ~/.claude/skills/jev-fast-decision/scripts/jev_review.py <<'JSON'
   {"reviewed_head": "<40-hex>", "items": [ <approved items, each with context> ]}
   JSON
   ```
   I would leave `User-Agent` in the script alone.

6. **Read the JSON `status` before anything else.**
   - `disabled`: the env var didn't take effect. I would carry on with my own reasoning.
   - `unavailable`: I would read `reason` and fix the cause. For `invalid_input`, I would fix the item named in `item`. I would not retry blindly. A 403 or auth error most likely means a Zen key or `auth.json` problem. I would report it to you rather than hunt for another credential.
   - `ok`: I would treat it as a hint. An answer below `JEV_MIN_CONFIDENCE` (0.7) carries `needs_fallback: true`, and I would reason it through myself. I would never auto-dismiss a finding on a single `unsupported` or low-confidence answer. I would never let it waive a criterion, pass a gate, pick a route or authorize anything. I would verify with my own tools.

**Not verified**

- That Zen actually works. I'm relying on your statement, and the first real call will confirm it.
- That `jev_review.py` is installed at `~/.claude/skills/jev-fast-decision/`. Step 4 checks it.
