I read `skills/jev-fast-decision/SKILL.md` and have not run any command. This is the plan.

**0. Setup**
- The shell starts in `tmp/p211/pressure-staging`. I'd resolve the skill path from the repo root with `git rev-parse --show-toplevel` instead of hardcoding it. Then I'd use `skills/jev-fast-decision/scripts/jev_review.py`.
- I'd confirm that is where `scripts/jev_review.py` lives before using it. The SKILL.md doesn't say whether the path is relative to the skill or to the repo.

**1. Gather evidence per finding**
- I'd collect a separate piece of evidence for each of the 4 findings: a `rg -n` or `sed -n` excerpt from that finding's own file, plus what the reviewer claimed.
- I would not paste raw hunks, secrets or `.env` values. I'd write each `evidence` as value-free text that names the pattern, not the value.

**2. Probe, once per session**
```bash
python3 -B skills/jev-fast-decision/scripts/jev_review.py --probe
```
- I expect `laya` to be selected, since you said it's up at 127.0.0.1:8010.
- If the probe selects something else, I stop and read `reason`. I don't switch backends myself.

**3. Read the backend notes before the first call**
- `skills/jev-fast-decision/backends/laya.md`.
- `skills/jev-fast-decision/reference.md`, only if I use `score` or have to interpret a receipt. The 4 items below are plain yes/no criteria, so it's optional.

**4. One call with 4 items**
```bash
GSD_PATH_JEV=1 JEV_BACKEND=laya JEV_LAYA_URL=http://127.0.0.1:8010 GSD_PATH_JEV_TIMEOUT_SECONDS=20 \
python3 -B skills/jev-fast-decision/scripts/jev_review.py <<'JSON'
{"reviewed_head": "<output of git rev-parse HEAD>", "items": [
 {"id": "F1", "criterion": "<English: concrete signal that finding 1 is a real bug>", "evidence": "<F1 file's value-free grep/excerpt>"},
 {"id": "F2", "criterion": "...", "evidence": "<F2 evidence>"},
 {"id": "F3", "criterion": "...", "evidence": "<F3 evidence>"},
 {"id": "F4", "criterion": "...", "evidence": "<F4 evidence>"}
]}
JSON
```
- `JEV_BACKEND=laya` pins the backend. It never falls back, so nothing can go off-machine.
- Laya is local, so no consent is needed. I won't set `JEV_ALLOW_REMOTE` and won't run `consent grant`.
- I send the 4 items as plain items in one request. The client makes one Laya call per item, so I don't batch them myself.
- Criteria are in English and name concrete signals, for example "the cited line in file X actually performs the unchecked write".

**5. Read the result**
- On `ok`, I read each item's `answers` entry (`needs_fallback`, `top`).
- Any item with `needs_fallback: true` I decide myself by reading that file and reasoning. I don't treat it as a verdict.
- I'd report that the `trail` and `consent_used` show local Laya only.
- On `consent_required_for_remote` or a `backend_unavailable` reason, I'd stop and ask you. I wouldn't retry blindly.
- On `unsupported_feature`, `disabled` or another `unavailable`, I'd read `reason`, fix it if it's something I can fix, or reason about the findings myself.

**6. Use the answers as advice only**
- I'd confirm every finding by reading the code, whatever Laya says.
- I would not dismiss a finding because of one low or `unsupported` answer.
- The final triage is my own verification, with Laya's answers listed beside each finding as advisory input.

I haven't seen the 4 findings, so the criteria and evidence above are placeholders. I'd fill them from the actual reports.

I skipped any check of whether `scripts/jev_review.py` actually sits in the skill directory. The main risk is evidence that is too thin or contains a raw value. A weak Laya answer on a real bug is advisory only, which is why step 6 verifies by hand.
