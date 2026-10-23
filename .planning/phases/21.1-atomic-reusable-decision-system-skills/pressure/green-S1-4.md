I read `skills/jev-fast-decision/SKILL.md`. Nothing below has been run. Your message says "these 4 review findings" but doesn't include them, so F1 to F4 below are placeholders until I have the finding text and the files they point to.

## Setup, before any call

1. **Probe the backends.** Run this from the skill directory, because `scripts/jev_review.py` in the SKILL.md looks relative to it:
   ```bash
   python3 -B scripts/jev_review.py --probe
   ```
   I'd expect `laya` to be selected. Laya needs no consent because it's local, so there's no grant or `JEV_ALLOW_REMOTE` step. I would not export `JEV_ALLOW_REMOTE` at all.
2. **Read the backend notes** with `Read backends/laya.md`. The skill requires this before the first call with that backend. I'd also read `reference.md`, since I'll be interpreting scores or receipts.
3. **Get the head hash.** Run `git rev-parse HEAD` for `reviewed_head`. I'd use the real hash rather than the `0*40hex` placeholder. I'd check `reference.md` first to see whether the zero placeholder is the intended value.

## Evidence for each finding

The four findings have different evidence, so I'd collect each one separately with `Read` or `rg`, which are read-only and don't count as running anything against the findings. The SKILL.md says to send value-free question text. For each finding I'd write a short summary that names the pattern and leaves out raw hunks, secrets, `.env` values and raw source. Laya is local, but the rule applies regardless.

## The one call

I'd send all four findings as items in a single request. The client already fans out one Laya call per item, so I would not wrap or batch them myself. That is a NEVER in the skill, because Laya bleeds state between items.

```bash
GSD_PATH_JEV=1 JEV_BACKEND=laya JEV_LAYA_URL=http://127.0.0.1:8010 GSD_PATH_JEV_TIMEOUT_SECONDS=20 \
python3 -B scripts/jev_review.py <<'JSON'
{"reviewed_head": "<git rev-parse HEAD>", "items": [
 {"id": "F1", "criterion": "This finding is a real bug.", "evidence": "<value-free summary of F1's evidence>"},
 {"id": "F2", "criterion": "This finding is a real bug.", "evidence": "<value-free summary of F2's evidence>"},
 {"id": "F3", "criterion": "This finding is a real bug.", "evidence": "<value-free summary of F3's evidence>"},
 {"id": "F4", "criterion": "This finding is a real bug.", "evidence": "<value-free summary of F4's evidence>"}]}
JSON
```

- `JEV_BACKEND=laya` pins the backend and never falls back to a remote.
- Each criterion is written in English and names concrete signals. I'd tailor it per finding instead of using one generic line.
- If I also wanted severity, I'd add `type: "score"` items with `criteria` like `["cosmetic","minor","major","critical"]`. I'd do that only after reading `reference.md`.

## Reading the result

- **`ok`:** for each item I look at `needs_fallback` and `top`. If `needs_fallback` is true, I decide that finding with my own reasoning. Otherwise the answer is advisory input only. I'd also announce `consent_used` and check `trail`.
- **`consent_required_for_remote`:** I would not retry on my own. I'd ask you first.
- **`unsupported_feature` or `disabled`:** I reason about it myself.
- **Any other `unavailable`:** I read `reason` and either fix it or reason myself. I never retry blindly.

## What I won't do with the answers

- No answer is a verdict or gate. I'd verify each finding against the code with `Read` or `rg` before dispositioning it.
- No finding gets auto-dismissed on a single low or `unsupported` answer. I'd investigate it myself.
- Nothing goes off-machine without consent. "The key is set" or "the user said use Jev today" doesn't count as consent.

## Unverified

I haven't confirmed that `scripts/jev_review.py` exists at the path I assumed. I also haven't checked whether Laya is reachable on 8010. The probe will tell us the second. For the first, I'd glance at the directory before running anything.
