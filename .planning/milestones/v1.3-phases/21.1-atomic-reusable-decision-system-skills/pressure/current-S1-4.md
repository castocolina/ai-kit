I read `baseline-SKILL.md`. Your message didn't include the four findings themselves, so the commands below use placeholders (`F1` to `F4`, `<...>`). Nothing has been run.

**Constraints from the skill that shape the plan**
- **One item per call.** Laya reads the whole `state` for every question, so one finding's context bleeds into the others. Four findings with different files and evidence therefore mean four separate calls, not one batch.
- **Endpoint.** You said Laya is at `127.0.0.1:8010`. The skill's example uses `:8000/v1/systemone`. I'd keep the `/v1/systemone` path but use your port, and that path is unverified until the first call returns `ok`.
- **Consent.** The target is loopback, and your request is the go-ahead. I'd send only a short summary per finding, never raw files, diffs or credentials.
- **Advisory only.** An `ok` answer never dismisses or confirms a finding. I verify each finding myself afterward.

**Step 1: preflight.** All of this is read-only.
```bash
ls skills/jev-fast-decision/scripts ~/.claude/skills/jev-fast-decision/scripts   # find the real jev_review.py
sed -n '1,200p' <path-to>/jev-fast-decision/reference.md                         # skill says read it before interpreting score or recording receipts
git rev-parse HEAD                                                               # 40-hex reviewed_head
```

**Step 2: gather my own evidence for each finding.** For each finding I read the cited lines with `sed -n '<a>,<b>p' <file>` or `codegraph_explore`. Then I write two or three plain sentences of evidence per finding. These sentences must be self-contained, since Jev has no tools. I'd leave out anything secret-like.

**Step 3: run four calls, one per finding.** The shorthand `criterion` + `evidence` form puts the material into that item's own context, so nothing is judged against nothing.
```bash
GSD_PATH_JEV=1 GSD_PATH_JEV_TIMEOUT_SECONDS=20 \
JEV_API_URL=http://127.0.0.1:8010/v1/systemone JEV_MODEL=jev-1 JEV_RESPONSE_MODEL=laya-rl-agent \
JEV_MIN_CONFIDENCE=0.7 \
python3 -B <path-to>/jev-fast-decision/scripts/jev_review.py <<'JSON'
{"reviewed_head": "<sha from step 1>",
 "items": [{"id": "F1",
            "criterion": "This finding is a real bug, not a false positive.",
            "evidence": "<my summary for finding 1: file, claim, what I saw>"}]}
JSON
```
I repeat this for F2, F3 and F4 with their own evidence. I run them sequentially, since each call takes about 12 ms. I don't set `OPENCODE_API_KEY` or `JEV_API_KEY`, because the skill says a key is optional with `JEV_API_URL` set. I never print keys.

**Step 4: read the result.**
- **Status.** I read `status` first.
  - `disabled` means the env var isn't set, so I fix it and rerun.
  - `unavailable` means I check `reason` and the `item` field and fix the cause. I don't retry blindly. If Laya is down, the fallback is TypeSafe, which sends text off the machine, so I'd ask you first.
  - `ok` means I read the per-item answer.
- **Fallback flag.** If an answer carries `needs_fallback: true` (winning probability below 0.7), I ignore it and reason through that finding myself.
- **Unsupported or unclear answers.** These are not a negative. I never auto-dismiss a finding on one `unsupported` or low-confidence answer.
- **Likely real.** A confident answer only prioritizes the finding. I still confirm it by reading and reproducing it.
- **Final decision.** Every finding's keep-or-drop decision comes from my own check of the code. Jev only orders the work.
- **Receipts.** I record no durable receipt unless you ask. If you do, I follow the exact format in `reference.md`.

**Needs your input:** send the four findings (id, file, claim, evidence), or point me at the review file that holds them.

**Skipped:** I haven't verified that the script exists at either path or that Laya answers on `:8010/v1/systemone`. Risk: Laya's confidence is not a calibrated probability, so treat it as a sorting hint only.
