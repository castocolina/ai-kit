Judge: my-referee-two
Reviewed-sha256: 17d7161a3b98c5573e3914240a8e0772571594c1e45996303013a032fb000bc3
Lane: AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=268s out=204532 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 116
Critical: 0
Important: 0

All spot-checks pass. The skill's claims — exit table, `stopped=` values, state-file protocol, defaults/bounds, overlay limits, catalog tiers, copilot argv-prompt and unverified labeling, `stderr_tail` 2048, `template=8` line-2 header, self-test case names cited as example sources — all match the runner and catalog. Final report:

# Skill Evaluation Report: ai-kit-cross-ai

## Summary
- **Total Score**: 116/120 (96.7%) — **Grade A**
- **Pattern**: Tool (navigation core + heavy detail in references/, with the runner script itself as the executable layer)
- **Knowledge Ratio**: E:A:R ≈ 90:10:0
- **Verdict**: A pure-contract skill for a bespoke runner — every paragraph is knowledge no model could have, and ~25 spot-checked factual claims all matched `cross-ai.mjs` / `cross-ai-errors.json` / its self-tests. The never-switch invariant is stated in the description, §1, §8, and the policy reference, and the skill correctly points other skills at itself as canonical policy (8 inbound links verified).

## Dimension Scores

| Dimension | Score | Max | Notes |
|---|---|---|---|
| D1: Knowledge Delta | 20 | 20 | AIKIT-XAI grammar, exit semantics, hard-tier protocol, state-file shape — zero tutorial filler |
| D2: Mindset + Procedures | 14 | 15 | Owner-ownership mindset up front (§1); retry/abort/skip decision spread across §6+§7 |
| D3: Anti-Pattern Quality | 14 | 15 | Pitfalls are expert-grade with whys; "never stash" lacks its why here |
| D4: Specification Compliance | 15 | 15 | Description has WHAT + WHEN + keywords (pi/opencode/codex/cursor/copilot, 429, exit 75/69, retry_after_s) + negative scope |
| D5: Progressive Disclosure | 15 | 15 | Conditional triggers ("a plain launch and read does not need it"), MANDATORY trigger, per-host routing |
| D6: Freedom Calibration | 15 | 15 | Exact where fragile (wait once, verbatim notice, whole-minute rule), principle where judgment applies |
| D7: Pattern Recognition | 9 | 10 | Tool/Navigation hybrid well executed; minor snippet duplication |
| D8: Practical Usability | 14 | 15 | Exit-table decision tree, examples copied from hermetic self-test runs, fallbacks; exit 127 row lacks a caller action |

## Findings

**Critical** — none.

**Important** — none.

**Minor**

1. **§7's "section 6 notice" cross-reference is loose for non-hard-tier exits** — `SKILL.md:161-163`: "Every other non-zero exit (a bare 75, any 69 ..., 1, 2, 124, 127) gets the section 6 notice". §6's notice is defined for `stopped=hard-waits|cap` and includes "mark the lane stopped", which doesn't apply to 124/127. Fix: in §7 say "print the evidence lines verbatim (§4) and answer abort; only `stopped=hard-waits|cap` also marks the lane stopped."
2. **Exit 127 row states a fact, not an action** — `SKILL.md:113`: "| 127 | not_installed | the runtime's binary is missing |" while the table's header promises "what the caller does with each". Fix: "report it and stop; do not retry".
3. **"Every copilot pattern reads `unverified`" reads as if copilot-specific catalog rows exist** — `references/subprocess-quota-policy.md:152-153`. The catalog has zero `cli: copilot` rows; copilot captures fall through to generic `cli: "*"` rows (pinned by self-test `classify-only-copilot-unverified`). Fix: "every pattern that matches a copilot capture reads `unverified`; the catalog ships no copilot-specific rows."
4. **Identical bash launch block appears three times** — `SKILL.md:59-63`, `references/launch-and-wait.md:26-30`, `:82-86`. Two are defensible (skill self-sufficiency + foreground path); the third is redundancy. Fix: drop the Claude Code section's copy and point at §2 of SKILL.md, or keep deliberately and note the copies must stay identical.
5. **External section-number coupling is undocumented** — other skills cite "ai-kit-cross-ai section 6" by number (`skills/ai-kit-spec-execute-gsd/SKILL.md:462`, `skills/ai-kit-spec-review/SKILL.md:351`, `skills/ai-kit-spec-execute-superpowers/SKILL.md:365`); renumbering SKILL.md silently breaks them. Fix: one line in SKILL.md ("other skills cite these sections by number; renumbering is a breaking change") or switch inbound references to named anchors.
6. **Every launch example hardcodes `--mode exec`** — `SKILL.md:61`, `launch-and-wait.md:28,84` — so a caller copying a snippet for a review lane (§5) silently gets the exec tools profile. Fix: one comment line in the snippet (`# --mode review for a review lane`).

## Verification basis
Read fully: `SKILL.md` (191 lines), both references (180 + 86). Checked the whole Phase 25.1 diff (457 insertions, all three files new). Verified against the runner it points at (`cross-ai.mjs`, 10,406 lines, `template=8` on line 2) and `cross-ai-errors.json`: STATUS_TABLE exits, `stopped=` values, `--prefer` first-entry alias, state-file naming/protocol, default waits and bounds, capS 14400, overlay 50 ms/200 ms, redaction, pi/opencode model grammars, copilot `argvPrompt`/`COPILOT_ALLOW_ALL`/unverified labeling, `--classify-only`/`--self-test`, cited self-test case names, and `stderr_tail` 2048 in `runner_dispatch.py`/`error_classifier.py`. No discrepancies found.

DIGEST 17d7161a3b98c557
CURRENT 116/120
CRITICAL 0 IMPORTANT 0

## Runner evidence

```
AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=268s out=204532 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
```
