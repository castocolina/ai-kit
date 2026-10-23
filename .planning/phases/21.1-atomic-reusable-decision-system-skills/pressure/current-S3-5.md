I read `baseline-SKILL.md` (a read, no commands run). It is the `jev-fast-decision` skill text. Everything below is what I would do, with nothing executed yet.

**What the skill says about your situation**
- `unavailable` means I must not retry blindly. A Zen `http_429` is a rate limit, so I would not loop on Zen. I would switch route to Laya, which is a different backend.
- Laya is local (127.0.0.1), so no text leaves the machine. I would take your message as the go-ahead for Laya. TypeSafe direct is off-machine, so I would use it only as a fallback, and only with summarized question text. No raw files, diffs or secrets.
- Laya carries one caveat. It reads the whole `state` for every question, so items with different `context` must go in separate calls, one item per call. I would not batch them.
- Every answer is advisory. Items with `needs_fallback: true` (winning probability below `JEV_MIN_CONFIDENCE`, default 0.7), or `unclear`/low-confidence answers, mean I reason it through myself. They never count as a negative or a dismissal.

**Gaps in what I know**
- The baseline file doesn't say which items make up "the screening". I'd find them first (step 1).
- The skill's example Laya URL uses port 8000, but my notes say 8010. I would check the live listener instead of trusting either.

**Steps and commands**

1. Find the pending screening items and the script (read-only):
   ```
   ls .planning/phases/21.1-atomic-reusable-decision-system-skills/pressure/
   ls skills/jev-fast-decision/scripts/ ~/.claude/skills/jev-fast-decision/scripts/
   ```
   I'd then read `reference.md` (mandatory before multi-item requests and before recording receipts). I'd also read the pressure-dir files that list the cases and note which ones already got an answer before the 429.

2. Confirm Laya's port and URL path, and how the script handles `JEV_API_URL`:
   ```
   ss -ltn | rg ':8010|:8000'
   rg -n "JEV_API_URL|JEV_MODEL|JEV_RESPONSE_MODEL|User-Agent" skills/jev-fast-decision/scripts/jev_review.py
   ```

3. Run one foreground probe against Laya with a trivial `noul` item. If it returns `ok`, continue. If it returns `unavailable`, I'd read the `reason`, fix that, and not retry.
   ```
   GSD_PATH_JEV=1 GSD_PATH_JEV_TIMEOUT_SECONDS=20 \
   JEV_API_URL=http://127.0.0.1:8010/v1/systemone JEV_MODEL=jev-1 JEV_RESPONSE_MODEL=laya-rl-agent \
   python3 -B skills/jev-fast-decision/scripts/jev_review.py < tmp/jev-probe.json
   ```
   I'd write the probe and the item JSON files under `./tmp/`, which is gitignored. Each item gets its own `context` holding the material to judge, and `reviewed_head` is the current commit SHA. No API key is needed for Laya, and I would never print a key.

4. Run the remaining items one call per item, using the same env as step 3. The loop would look like this:
   ```
   for f in tmp/jev-item-*.json; do ...same env... python3 -B <script> < "$f" > "${f%.json}.out.json"; done
   ```

5. Only if an item is still `unavailable` on Laya, or needs something Laya lacks, I'd make a TypeSafe-direct call. I'd read my backends note and the script's URL handling first. `TYPESAFE_API_KEY` goes in as `JEV_API_KEY`, passed from the environment and never echoed. I'd use the exact URL and model from the script or notes rather than guess them.

6. Interpret the results:
   - I'd read the `status` field first.
   - For `score` answers I'd follow `reference.md`'s confidence guidance.
   - Any `needs_fallback: true` item gets my own reasoning.
   - Nothing is auto-dismissed on a single low-confidence answer.
   - I'd record receipts in the exact `reference.md` format, in English. Each receipt would note the backend (Laya or TypeSafe) and that Zen was skipped because of the 429.
   - I would not commit anything unless the plan says to, and I would delete nothing besides my own `tmp/` scratch files.

I did not check where the screening items live, whether Laya is actually listening, or the TypeSafe direct URL. The risk is that Laya's probabilities are not calibrated and differ from Zen's Jev, so any receipt must say which backend produced it.
