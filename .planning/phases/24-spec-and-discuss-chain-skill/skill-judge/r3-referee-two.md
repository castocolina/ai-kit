DIGEST 7fc3f03ffb2fb714
# Skill Evaluation Report: ai-kit-gsd-spec-discuss

## Summary
- **Total**: 109/120 (91%) — Grade **A**
- **Pattern**: Process (~257 lines, phased workflow, medium freedom) with Tool-pattern reference depth
- **Knowledge Ratio**: E:A:R ≈ 88:10:2
- **Verdict**: A compressed expert runbook — nearly every line encodes a landmine or rule specific to this repo's GSD + jev client stack that no model could know; its one real cost is clause density that taxes a cheap executor.

## Dimension Scores

| Dimension | Score | Max | Notes |
|-----------|-------|-----|-------|
| D1: Knowledge Delta | 19 | 20 | Almost pure delta: proprietary workflows, client exit-code semantics, real Laya non-determinism data (L175-176), forced-column semantics. No tutorial content. |
| D2: Mindset + Procedures | 14 | 15 | "You are the decider" mindset up front (L16-20) plus non-obvious procedures: step replacements (skip `git_commit`, per-phase `update_state`, `auto_advance` — L109-117), pacing ordering (§7). |
| D3: Anti-Pattern Quality | 14 | 15 | Nine NEVERs (L219-238), each with a hard-won WHY: silent CONTEXT regeneration loses user-locked decisions (L234-235); config flip leaves keys flipped after a crash (L231-233); `--assumptions` routing trap makes the run *look* complete (L221-223). One near-generic item (never print a key, L238). |
| D4: Specification Compliance | 14 | 15 | Description (L3) has WHAT + WHEN + verbatim trigger phrases ("spec/discuss phases 17-24", "--analyze --all --batch --assumptions") + negative scope ("Not for plan-phase or execute-phase"). Deducted for density/ordering — see Important #1. |
| D5: Progressive Disclosure | 15→14 | 15 | MANDATORY triggers embedded at point of use (L77, 90, 112-113, 137) *and* a final trigger table (L247-254); conditional load for worked-examples ("only when a case is unclear"); a Do-NOT-load line (L256-257). Near-textbook. |
| D6: Freedom Calibration | 13 | 15 | Exact commands/JSON shapes and fixed log formats where a wrong flag silently corrupts the run; decision-table and principles where judgment matters. §0's 7-step setup is heavy but genuinely fragile setup. |
| D7: Pattern Recognition | 9 | 10 | Clear Process pattern executed well; slightly over the ~200-line norm and denser than typical — minor deviation only. |
| D8: Practical Usability | 12 | 15 | Exceptional edge-case and error coverage (forced columns, SPEC-newer false positive with a `git log` check, L52-53; exit 1 vs exit 2 semantics, L94-97; host-gap fallbacks, L240-245). Deducted for the gaps below. |

## Findings

### Critical
None.

### Important
1. **D4 — Description trigger placement (L3).** The WHEN/keywords (the part that actually fires activation) sit in the back half of a ~830-char description; a host that truncates the listing view cuts exactly those trigger phrases and shows only mechanism. Move a compact "Use when spec-ing/discussing multiple GSD phases…" clause to the front.
2. **D8 — `no_client`/`incompatible_client` action gap (L42-45).** The sentence defines the degraded state ("own reasoning only") and dangles the remedy (the owner's `tools/setup.py install …` command) but never says what the agent does with it — proceed silently, or tell the user, and where (step 5's ask? end-of-run ledger?). The description advertises "Works with no decision backend installed," so this is a common path, not an edge case. State the action explicitly.

### Minor
3. **D8 — Resolver path indirection (L32-34).** `references/gsd-run-resolver.md` is "inside the gsd-core install" with no path formula, unlike the workflows dir which gets one (`<dir of gsd-tools.cjs>/../workflows/`). The executor must guess `../references/`.
4. **D8 — score-item shape underspecified (L155-156).** "a list of 2-10 levels" doesn't say what a level is; relies on `decide.py`'s reject-and-reason loop to teach the format.
5. **D5 — narrow "Do NOT load" (L256-257).** Only covers skipped phases; the other negatives are "only when" conditionals. Works, but one explicit do-not-load line for the three always-triggered references when unneeded would complete it.
6. **D2 — unexplained policy link (L72-74).** "recommend the auto path when … `mvp-mode` is active" states the rule without its why — the only expert rule in the file lacking a reason.

## D8 Drivers (lowest dimension)
Beyond findings 2-4: general clause density — several sentences carry 3-4 load-bearing rules each (e.g. the mvp-mode fallback semantics L63-68, the fallback/ledger condition L176-179). Correct, but the most likely failure mode for the repo's stated cheap-model executor is dropping a clause, not misreading a rule.

CURRENT 109/120
CRITICAL 0
IMPORTANT 2
