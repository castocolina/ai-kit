I read the skill, and I haven't run anything. You didn't paste the four findings, so step 1 is getting them.

## Rules from the skill that shape the plan

- **One call per finding, no batching.** The skill's Laya caveat says Laya reads the whole `state` for every question, so one item's context bleeds into the others. Your four findings come from different files with different evidence, so they go in four separate calls (about 12 ms each).
- **Consent.** The skill says to confirm before sending text off the machine. `127.0.0.1:8010` is local, and you asked for this triage, so I'd treat your request as the go-ahead. I'd say so in my reply and send only summarized text.
- **Jev is advisory only.** Its answers never decide a finding. I verify each one myself.
- **Nothing to judge means a meaningless answer.** The material being judged has to be in each item's `evidence`, or Jev answers confidently against nothing.

## Steps

**1. Get the findings.** I'd list the phase dir for a `*REVIEW*.md`, and read it with Read or `sed -n` if present. If the four aren't there, I'd ask you for them. I'd then read the cited lines in each file myself, which is my own verification and also the source of the evidence text.

**2. Preflight (read-only).**
- Check the script exists: `ls ~/.claude/skills/jev-fast-decision/scripts/jev_review.py`.
- Get a real SHA: `git rev-parse HEAD`.
- I'd set no env persistently and use no API key. The env goes inline on each call.

**3. Write one summarized evidence paragraph per finding.** It would contain:
- The claim.
- The relevant code behaviour in my own words.
- What I saw when reading the file.

It would contain no raw diffs, no secrets, and no env dumps.

**4. Make the four calls, in parallel, as four separate Bash calls.** Each call looks like this, with `<SHA>`, `F1` and the texts filled in:

```bash
GSD_PATH_JEV=1 GSD_PATH_JEV_TIMEOUT_SECONDS=20 \
JEV_API_URL=http://127.0.0.1:8010/v1/systemone \
JEV_MODEL=jev-1 JEV_RESPONSE_MODEL=laya-rl-agent \
python3 -B ~/.claude/skills/jev-fast-decision/scripts/jev_review.py <<'JSON'
{"reviewed_head":"<SHA>","items":[
 {"id":"F1","criterion":"This finding is a real bug, not a false positive.",
  "evidence":"<summarized evidence for F1 only>"}]}
JSON
```

- The `/v1/systemone` path comes from the skill's example, which uses port 8000, so the 8010 port and path are not live-verified. If the first call comes back `unavailable`, I'd read its `reason` and fix the URL, rather than retry blindly.
- I'd keep `-B` and not touch the script's `User-Agent` header.

**5. Read the JSON status first, then act on each answer.**
- `disabled` or `unavailable`: reason through it myself. For `invalid_input`, fix the item named in `item`.
- `ok` with `needs_fallback: true` (winning probability below the default `JEV_MIN_CONFIDENCE` of 0.7): ignore the answer and reason it through myself.
- `ok` with `unsupported`, `unclear` or low confidence: never auto-dismiss. It means "investigate myself", not "no".
- `ok` with high confidence: treat it as a prioritisation hint only. I still confirm with my own check, such as reading the code path or running the relevant test.

**6. Report.** One line per finding with my own verdict, my verification, and Jev's answer as a side note. I'd read `reference.md` only if I record an `ok` receipt in a durable artifact. I'd use `./tmp/` for any scratch file, and there are no background processes to clean up.

**Not covered:** I haven't seen the findings, so the evidence and the verdicts are still open. I also haven't verified the Laya URL or path.
