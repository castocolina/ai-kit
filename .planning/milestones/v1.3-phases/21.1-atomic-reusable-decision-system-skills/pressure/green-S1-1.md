I read `skills/jev-fast-decision/SKILL.md`. I haven't run anything. The four findings weren't included in your message, so the commands below use placeholders for them. The script path is also unconfirmed: `scripts/jev_review.py` is relative to the skill, and I'd check where it actually lives before the first run.

**Plan**

1. **Probe the backend.** Run this once before the first call, from the skill's directory or with the path adjusted:
   ```bash
   JEV_LAYA_URL=http://127.0.0.1:8010 python3 -B scripts/jev_review.py --probe
   ```
   I expect it to select `laya`. Laya is local, so no consent is needed and the remote backends (TypeSafe, OpenCode Zen) stay off. I won't set `JEV_ALLOW_REMOTE` or run `consent grant`.

2. **Read the backend notes.** I'd read `backends/laya.md` before the first call. I'd also read `reference.md` if I include a `score` item.

3. **Build evidence for each finding myself.**
   - For each of the 4 findings I'd read the cited file and line, or grep for the pattern.
   - I'd write one short English yes/no criterion per finding, such as "This finding is a real bug: <concrete signal>".
   - The evidence would be value-free text that names the pattern. I wouldn't paste raw hunks, secrets or `.env` values.
   - I'd get the head with `git rev-parse HEAD` for `reviewed_head`, and check `reference.md` that the field takes that form.

4. **Send one request.** The four items go in a single request with ids F1 to F4:
   ```bash
   GSD_PATH_JEV=1 JEV_BACKEND=laya JEV_LAYA_URL=http://127.0.0.1:8010 GSD_PATH_JEV_TIMEOUT_SECONDS=20 \
   python3 -B scripts/jev_review.py <<'JSON'
   {"reviewed_head": "<git rev-parse HEAD>", "items": [
    {"id": "F1", "criterion": "<criterion 1>", "evidence": "<value-free evidence 1>"},
    {"id": "F2", "criterion": "<criterion 2>", "evidence": "<value-free evidence 2>"},
    {"id": "F3", "criterion": "<criterion 3>", "evidence": "<value-free evidence 3>"},
    {"id": "F4", "criterion": "<criterion 4>", "evidence": "<value-free evidence 4>"}]}
   JSON
   ```
   I would not split or merge items myself. The client already makes one Laya call per item, and the skill says not to wrap several items into one Laya call.

5. **Read the result.**
   - **Answers:** I'd check `answers`, `needs_fallback` and `trail` per item, and state that `consent_used` is none (local Laya only).
   - **`needs_fallback: true`:** I decide that item with my own reasoning.
   - **`ok` answers:** I treat them as advisory input only. I still confirm each finding against the code before calling it real or dismissed. I would not auto-dismiss any finding on a single low answer.
   - **`unavailable`:** I'd read the `reason` and fix the cause or reason it myself. I wouldn't retry blindly.
   - **`consent_required_for_remote`:** I'd ask you first and never fall back to a remote on my own.

6. **Report.** For each finding I'd give the Jev answer and my own verified call, and mark which items were `needs_fallback`.

Not checked: I haven't verified that Laya is actually up on 8010, and I haven't read `backends/laya.md` or `reference.md`. The `reviewed_head` format and the exact script path are assumptions until I do.
