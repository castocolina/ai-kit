Judge: my-referee-two
Reviewed-sha256: 2aed7941ce4547821e04d7ec86d5741ad40e979393a065827aabf25e6688c3d8
Lane: AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=297s out=495098 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 110
Critical: 0
Important: 1

# Skill Evaluation Report: ai-kit-spec-execute-superpowers

## Summary
- **Total Score**: 110/120 (91.7%) — Grade A
- **Pattern**: Process (phased Step 0–4 workflow) with tool-grade exactness
- **Knowledge Ratio**: E:A:R ≈ 85:13:2
- **Verdict**: A dense, code-verified state-machine skill whose Phase 25.1 repointing to `ai-kit-cross-ai` is accurate everywhere I checked against the runner, the classifier, and the policy — the never-switch rule is airtight.

Every load-bearing claim I tested holds: `status`/`reason` are nested in the dispatch result (`execute_dispatch.py:149-152`); the runner always emits `cycle=` alongside `retry_after_s=` (`cross-ai.mjs:1281`), so the "exit 75 with whole-number RETRY_AFTER_S and CYCLE" gate matches emission; a pending-`due_at` refusal exits 75 with both tokens (`cross-ai.mjs:6705-6720` self-test `hard-tier-early-reentry`), so it correctly schedules; bare-75/exit-69 shapes land as owner stops in both the classifier (`dispatch_injection.py:424-427`) and the prose; the cross-AI pointer names the right sections (4, 6, 8); `design-notes.md:125`'s `../../ai-kit-cross-ai/SKILL.md` link resolves; the copilot note (unverified rows, argv-visible prompt) matches `EXEC_NOTES` and the policy; grok still never executes (`detection.py:1153`); the "eight placeholders" count is correct.

## Dimension Scores

| Dimension | Score | Max | Notes |
|-----------|-------|-----|-------|
| D1: Knowledge Delta | 18 | 20 | Three-set exclusion split, digest-stable `<objective>` block, anchor-vs-fresh-pick floor — all hard-won; tiny arch restatement |
| D2: Mindset + Procedures | 14 | 15 | "Ask: permanent or same-wave?" before touching state; why delegated to design-notes |
| D3: Anti-Pattern Quality | 14 | 15 | 9-item NEVER index, each with a concrete silent-failure mechanism |
| D4: Spec Compliance | 14 | 15 | WHAT/WHEN/keywords plus negative scope ("not for executing-plans"); one ~90-word sentence |
| D5: Progressive Disclosure | 13 | 15 | MANDATORY triggers at exact decision points, condition-scoped; 460-line body over the 300 ideal |
| D6: Freedom Calibration | 14 | 15 | Verbatim blocks where bytes corrupt state; judgment kept for owner-relay; one dead flag carried |
| D7: Pattern Recognition | 9 | 10 | Process pattern with tool-grade exactness, consistently executed |
| D8: Practical Usability | 14 | 15 | Decision tree code-verified end-to-end; one edge shape lives only in the script |

## Findings

**Critical** — none.

**Important**

1. **Classifier fallback shapes undocumented in the skill's prose.** `dispatch_injection.py:423-428` has two branches the SKILL.md `"quota"` bullet (SKILL.md:321-324, 358-363) never names: a *malformed* `retry_after_s` hint (not bare, not whole-number) and the final `reason == "quota"` fallback. No wrong action results today — every unlisted shape reaches the owner stop — but an agent reasoning from the skill text alone cannot predict the classification of an exit 75 with a malformed hint; it must open the script, in the most fragile branch (wait-vs-stop). Fix: add one clause to the quota bullet: "a malformed hint behaves like a bare one (classified quota, never scheduled); the classifier's last fallback is `reason == "quota"`."

**Minor**

2. **Layer-2 weight.** SKILL.md is 460 lines (ideal <300); the NEVER index (SKILL.md:18-43) is by design duplicated at every point of use, and Step 3 point 4's ordering prose overlaps `references/state-management.md` §Quota-branch state write. Fix: keep the index, shrink point 4's prose to the decision rule plus the existing pointer.
3. **Dead flag.** `--heartbeat-interval 60` is passed (SKILL.md:270) then explained away as "required but unused" (SKILL.md:293). Fix: drop it from the shim's required arguments, then from the skill.
4. **Description density.** SKILL.md:3 is one ~90-word sentence. Excellent WHAT/WHEN/negative scope, but split into two sentences for faster activation scanning.
5. **Architecture restatement.** SKILL.md:198 re-explains the reviewer/executor entry-shape rule already owned by AGENTS.md and `detection.py`; keep only the dispatch-decision consequence.
6. **Unexplained grok mention.** SKILL.md:133 lists grok among never-executing entries without why; one clause ("grok: confirmed unsupported as a dispatch target, `detection.py`") would stop a future reader re-verifying.

DIGEST 2aed7941ce454782
CURRENT 110/120
CRITICAL 0 IMPORTANT 1

## Runner evidence

```
AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=297s out=495098 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
```
