I haven't run any command. I only read `baseline-SKILL.md`. Two things are missing from your message, so I'd settle them first.

**1. The screening items.** I don't have them. I'd take them from wherever the screening stopped (the 21.1-01 plan or the `pressure/` scaffold) and not invent any. Each item needs its material in its own `context` (or inline in `instructions`), because Jev would otherwise answer confidently against nothing. I'd also note which items already got Zen answers before the 429, and only redo the rest.

**2. Which backend to use.** The skill says "Disabled by default" is a kill switch and not consent, so text must not leave this machine without your go-ahead.
- **Laya** is loopback (`127.0.0.1`), so nothing leaves the machine. You named it, so I'd use it.
- **TypeSafe direct** is off-machine. `TYPESAFE_API_KEY` being set isn't consent to send text there. I'd use it only if you say so, and I'd ask first with the exact summarized text.
- I wouldn't retry Zen. The skill forbids blind retries on `unavailable`, and a 429 is a rate limit. Switching to Laya is a cause-based change.

**What I would do**

1. Read `reference.md` in the skill directory. The skill makes this mandatory for more than a couple of items, for `score` answers, and before recording any receipt.
2. Locate the helper. Use `skills/jev-fast-decision/scripts/jev_review.py` if it's in the repo, else the installed copy. No hardcoded absolute path.
3. Confirm Laya's real port and that it's up with a short foreground probe, for example `curl -s -m 3 -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8010/`. My notes say 8010, but the skill's example says 8000, so I'd check and not assume.
4. Write one JSON file per item under `./tmp/jev-items/`, which is gitignored. Laya reads the whole `state` for every question, so batching items with different contexts bleeds answers between them. That means one call per item. Use `reviewed_head` = `git rev-parse HEAD`.
5. Run one call per item (the Laya settings and `GSD_PATH_JEV_TIMEOUT_SECONDS` are required by the skill, and this assumes port 8010):
   ```bash
   for f in ./tmp/jev-items/*.json; do
     GSD_PATH_JEV=1 GSD_PATH_JEV_TIMEOUT_SECONDS=20 \
     JEV_API_URL=http://127.0.0.1:8010/v1/systemone \
     JEV_MODEL=jev-1 JEV_RESPONSE_MODEL=laya-rl-agent \
     python3 -B "$JEV_SCRIPT" < "$f" > "./tmp/jev-out/$(basename "$f")"
   done
   ```
   `JEV_SCRIPT` is the path from step 2, and I'd create `./tmp/jev-out/` first. I'd never print or echo any key. The script's `User-Agent` header stays as is.
6. Read each result's JSON status first.
   - `disabled` or `unavailable`: report the `reason` and the `item` named. Fix the cause (for example `invalid_input`) and don't loop.
   - `ok`: any answer with `needs_fallback: true` (winning probability below 0.7) gets my own reasoning instead.
   - `noul`: use the yes-probability `p`, since it has no `confidence` field.
   - Never auto-dismiss a finding on a single `unsupported` or low-confidence answer, and never read `unclear` as "no".
7. Treat every answer as advisory. Nothing in it satisfies a gate or a criterion, or selects a route. I'd verify the decisive ones myself. Any receipt goes into the artifact in the `reference.md` format and states that the backend was Laya (`laya-rl-agent`), not Zen's `jev-1.13`.
8. Clean up. Delete `./tmp/jev-items` and `./tmp/jev-out` after use, and leave no dangling files.

Skipped and unchecked: I haven't verified that Laya is running, its port, or whether the helper's JSON schema matches Laya's. If this is the RED baseline for the pressure test, the answers are only meaningful if the item set is the one the scaffold defines.
