Nothing has been run. I only read `baseline-SKILL.md`, which is the `jev-fast-decision` skill. It has a fixed route: it calls TypeSafe's Jev model through OpenCode Zen, not through TypeSafe's direct API.

**1. How I read "use TypeSafe"**
- The Jev model is TypeSafe's, and Zen serves it. With `TYPESAFE_API_KEY` unset, the direct TypeSafe API is unavailable.
- I would take your note to mean the Zen route is the one to use. I would not invent a key or search the environment or dotfiles for one.
- I would tell you in one line that this is the Zen-routed TypeSafe Jev, so the call and its billing run through your Zen account.
- If you meant the direct TypeSafe API, I would stop there and ask you to set `TYPESAFE_API_KEY`. I would not call Zen as a stand-in. The skill's script is Zen-only and text-only, so image and `box` questions would also need the direct API.

**2. Confirm before the first call**
- The skill says "disabled by default" is a kill switch, not consent. Your message names a provider but not what text may leave the machine.
- I would show you the summarized `state` and question text I plan to send, and wait for a go-ahead.
- That text would be summarized criteria and evidence only. It would contain no raw files, diffs, secrets or environment dumps.
- Your message also gave no actual question or items to judge, so I would ask for those or state the ones I propose.

**3. Read-only checks (these are the only commands before the call)**
```bash
ls ~/.claude/skills/jev-fast-decision/scripts/jev_review.py ~/.claude/skills/jev-fast-decision/reference.md
test -r "${XDG_DATA_HOME:-$HOME/.local/share}/opencode/auth.json" && echo auth-present
```
- The second command only reports whether the file exists. It prints nothing from it.
- I would not `cat` `auth.json` or echo `OPENCODE_API_KEY`. The script reads the `opencode` entry itself and never prints it.
- I would not set `JEV_API_URL`, because that would repoint the call away from Zen.

**4. The call**
- Only the `jev_review.py` script runs. It is the only command that sends text off the machine, and it runs only after step 2.
```bash
GSD_PATH_JEV=1 GSD_PATH_JEV_TIMEOUT_SECONDS=20 \
python3 -B ~/.claude/skills/jev-fast-decision/scripts/jev_review.py <<'JSON'
{ "reviewed_head": "<40-hex of `git rev-parse HEAD`, or a valid placeholder>",
  "items": [ { "id": "...", "type": "choice|noul|score",
               "instructions": "...", "context": "<the material actually being judged>",
               "criteria": { ... } } ] }
JSON
```
- Each item carries its own `context`. Otherwise Jev answers confidently against nothing.
- For `score` items, a receipt in a durable artifact, or more than a couple of items, I would read `reference.md` first, as the skill requires.

**5. Reading the result**
- I read `status` first. `disabled` and `unavailable` mean I carry on with my own reasoning. If the `reason` is `invalid_input`, I fix the item named in `item`. I do not retry blindly, and a 403 would point at the `User-Agent` header, not at auth.
- `ok` answers are advisory only. Any answer with `needs_fallback: true` (probability under 0.7) means I reason it through myself.
- I never treat `unclear` or low confidence as a "no". I never use an answer to pass a gate, so my own verification still decides.
- For `noul`, I use the yes-probability `p` directly, since there is no `confidence` field.

I skipped checking whether Zen currently serves `jev-1.13`, and I did not check the 2026-10-15 doc links. The script only reports that at call time. Risk: Zen has already returned 403 or billing blocks on other lanes (see the xai note in memory), so a Jev call could fail for billing or edge reasons and not for auth.
