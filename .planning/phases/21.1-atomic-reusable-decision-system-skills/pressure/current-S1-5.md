I haven't run anything. I read `baseline-SKILL.md` (the `jev-fast-decision` skill) and this is what I would do under it.

**Gap:** your message doesn't contain the 4 findings. Before step 2 I would ask you for them, or look for them in the phase's review artifact, probably a `REVIEW.md` under `.planning/phases/21.1-*/`. Everything below assumes I have each finding's file, claim and evidence.

**1. Read `reference.md` first.**
- The skill makes it mandatory before interpreting a `score` answer, recording a receipt, or building a request with more than a couple of items.
- It is at `~/.claude/skills/jev-fast-decision/reference.md`.
- I'd read it anyway, because I'm sending 4 items and may record the outcome.

**2. Send one call per finding, not one batch.**
- The skill's Laya caveat says items with different `context` bleed into each other, because Laya reads the whole `state` for every question.
- Your 4 findings have different files and different evidence, so a batch would contaminate the answers.
- A single call is about 12 ms on Laya, so 4 calls is cheap.

**3. Consent check.**
- The skill forbids sending text off this machine without your go-ahead.
- Laya at `127.0.0.1:8010` is local, so nothing leaves the machine, and you named it explicitly.
- I'd still send only my own summary of each finding. I would not send raw source, diffs, credentials or environment dumps.

**4. Build each payload.**
- It is one shorthand item (`criterion` plus `evidence`) per finding, with `id` set to F1 to F4.
- `criterion` is "This finding is a real bug, not a false positive."
- `evidence` is a self-contained plain-text summary of that finding: the file, the claim and the proof, e.g. a grep result or a call-site fact.
- Empty evidence is not allowed, because it scores `unsupported` by design.
- `reviewed_head` is a real SHA, which I'd get with `git rev-parse HEAD`.

**5. Commands (read-only, nothing written).**

```bash
git rev-parse HEAD   # paste the 40-hex result into reviewed_head below

# Repeat once per finding F1..F4, each as its own call
GSD_PATH_JEV=1 GSD_PATH_JEV_TIMEOUT_SECONDS=20 \
JEV_API_URL=http://127.0.0.1:8010/v1/systemone \
JEV_MODEL=jev-1 JEV_RESPONSE_MODEL=laya-rl-agent \
python3 -B ~/.claude/skills/jev-fast-decision/scripts/jev_review.py <<'JSON'
{"reviewed_head": "<40-hex from rev-parse>",
 "items": [{"id": "F1",
   "criterion": "This finding is a real bug, not a false positive.",
   "evidence": "<my summary of finding 1: file, claim, proof>"}]}
JSON
```

- The `/v1/systemone` path comes from the skill's example, which uses port 8000. Only the port changes for Laya on 8010, and I haven't verified the path.
- If the first call returns `unavailable`, I'd check the path and port as the likely cause. I would not retry blindly.
- I would not set `OPENCODE_API_KEY` or `JEV_API_KEY`, since a key is optional with `JEV_API_URL` set, and I'd never print one.

**6. Read the JSON `status` before anything else.**
- `disabled` or `unavailable`: I proceed with my own reasoning, and I fix the cause before any retry.
- `ok`: I read each answer's `choice` and `confidence`.
- If the winning probability is below `JEV_MIN_CONFIDENCE` (0.7), the answer carries `needs_fallback: true`. I don't act on it and reason through that finding myself.

**7. Treat every answer as advisory.**
- Per the NEVER list, a Jev answer is a triage ordering and never a verdict.
- I would never dismiss a finding on a single `unsupported` or low-confidence answer. `unclear` and low confidence mean "investigate myself", not "no".
- For each finding I'd still check the cited file and line myself, using `codegraph_explore` first (the repo is indexed) and `rg` plus Read as a fallback.
- Likely-real findings get investigated first.
- Likely-noise findings get a quick check before I mark them as noise.

**8. Report.**
- Per finding, I'd give Jev's choice and confidence, my own verification result, and the final verdict. Jev's answer would be labelled advisory.
- I'd record a durable receipt only if you ask, and then in the exact format from `reference.md`.

**Skipped or unchecked:** I haven't verified that Laya is up, the endpoint path, or that the script exists at that path. I also haven't seen the findings. The main risk is that a confident Laya answer on thin evidence gets over-trusted, so my own check of each finding is what decides it.
