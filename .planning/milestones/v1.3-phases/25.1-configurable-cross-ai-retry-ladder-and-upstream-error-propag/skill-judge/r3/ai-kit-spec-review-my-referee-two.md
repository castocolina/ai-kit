Judge: my-referee-two
Reviewed-sha256: ee1794d8f5e1b061433573bd295203633909ba9675b7da446cfd4a399675f4dd
Lane: AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=273s out=448381 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 114
Critical: 0
Important: 1

# Skill Evaluation Report: ai-kit-spec-review

## Summary
- **Total Score**: 114/120 (95%)
- **Grade**: A — production-ready
- **Pattern**: Process (phased 0→5 workflow with Tool-pattern command discipline)
- **Knowledge Ratio**: E:A:R ≈ 85:12:3
- **Verdict**: A dense, expert-grade orchestration skill whose Phase 25.1 changes are accurately documented and correctly point at the new canonical `ai-kit-cross-ai` policy; residual risk is duplication-driven drift, not correctness.

**Phase 25.1 verification** (all confirmed against code, not just docs): one runtime per call with `--prefer` as first-entry alias (`cross-ai.mjs:4258-4334`); soft series + one session reset (`RETRY_DEFAULTS`, `cross-ai.mjs:2954-2958`); caller-owned hard tier with `hard_waits_s` and `stopped=hard-waits`/`stopped=cap`, never a switch (`hardWaitFor`, `cross-ai.mjs:3087-3095`); upstream body pass-through after redaction (`cross-ai.mjs:1252-1258, 1518-1560`); error catalog + owner overlay at `~/.config/ai-kit/cross-ai-errors.json` (`cross-ai.mjs:61-62, 1122, 1637+`, `references/cross-ai-errors.json`); script-owned model grammars (`runner_dispatch.py` `_MODEL_ID_SRC`) and `--tools-profile` (`cross-ai.mjs:33, 4266-4269`); Copilot runtime (`detection.py:117-118`). The pointer `../ai-kit-cross-ai/SKILL.md` sections 4/6/8 exists and matches; the owner-ruling quote at SKILL.md:164-166 is genuinely in `quota.py:146,155`; the never-switch rule (SKILL.md:352, 477) is intact, and the pre-dispatch ladder walk is explicitly fenced off from it (SKILL.md:157-170).

## Dimension Scores

| Dimension | Score | Max | Notes |
|---|---|---|---|
| D1: Knowledge Delta | 19 | 20 | Nearly pure expert knowledge (worktree-root phantom findings, archetype ceiling, fresh-shell variable trap, exit-file-as-completion-token); slight dilution from restated exit-75/69 detail |
| D2: Mindset + Procedures | 14 | 15 | Thinking prompts embedded at decision points (SKILL.md:68, 404, 436); pending-lane mechanics spread over 3 files buries the "caller only waits" model |
| D3: Anti-Pattern Quality | 14 | 15 | Hard-landmine framing with real reasons ("a switch hides the stop and reviews with a lane nobody chose", SKILL.md:477); upstream-text-as-data injection hazard |
| D4: Spec Compliance / Description | 15 | 15 | Valid frontmatter; description has WHAT + WHEN + trigger keywords + flags |
| D5: Progressive Disclosure | 14 | 15 | MANDATORY read triggers + explicit "Do NOT load" (SKILL.md:153); 492-line body sits at the 500 ceiling |
| D6: Freedom Calibration | 15 | 15 | Verbatim commands and templates for fragile ops; principled freedom (with reasons) for judgment calls (fixer model, SKILL.md:189) |
| D7: Pattern Recognition | 9 | 10 | Clear Process pattern, appropriate Tool elements; body overshoots the ~200-line Process norm |
| D8: Practical Usability | 14 | 15 | Exhaustive error/edge coverage (partial installs, both-lanes-pending, merge lock, resume); drift risk from triple-stated exit contract |

## Findings

1. **Important — exit-75/69 contract restated in three files; drift risk on the most safety-critical branch.** SKILL.md:330-352, `references/cross-ai-dispatch.md:244-258`, and `ai-kit-cross-ai/SKILL.md` §4 each restate the exit-code → action mapping. The 25.1 diff itself had to rename "pending router lane" → "pending lane (hard tier)" in all of them (it caught every copy — verified — but at triple cost), and the canonical policy's own contract is "A skill links here; it does not copy the rules" (`ai-kit-cross-ai/references/subprocess-quota-policy.md:7`). Fix: keep SKILL.md Step 1 down to "branch before deleting; exit 75 with `retry_after_s=` → pending-lane section; everything else per the caller contract" and let `cross-ai-dispatch.md`'s pending-lane section own the one full restatement.

2. **Minor — `loop-diagram.md` predates the hard tier.** The diagram (`references/loop-diagram.md:9-68`) shows no pending-lane path, yet SKILL.md:395 makes it the first-checked row of Step 2 (skip Step 3, surface the hard-tier wait). It self-declares as optional, but it is now stale on exactly the branch a reader would consult it for. Fix: add the pending-lane branch to the dot graph or a one-line note that it covers the pre-25.1 loop.

3. **Minor — no `cli-profiles/copilot.md` while the runtime ships.** `detection.py:117-118` adds copilot (flagged unverified) and `subprocess-quota-policy.md:145-146` says every copilot pattern reads `unverified`, but SKILL.md:153 routes "a named CLI's flags are in doubt" to `references/cli-profiles/`, which has no copilot entry. Fix: add a stub `copilot.md` mirroring `detection.py`'s own caveat (no host signal, runner rows unverified) so that lookup doesn't dead-end.

4. **Minor — 492-line body at the rubric's ceiling with reference-grade content inline.** The SEEDS_DIR three-candidate bash block and its failure mode (SKILL.md:192-208) are path-resolution mechanics, not loop decisions; they duplicate the pattern `cross-ai-dispatch.md:19-33` already self-contains for `TOOLS_PY`. Fix: move the seeds-dir block into a reference file (or fold it into cross-ai-dispatch.md point 0) and keep one sentence in SKILL.md, buying ~20 lines of headroom.

DIGEST ee1794d8f5e1b061
CURRENT 114/120
CRITICAL 0 IMPORTANT 1

## Runner evidence

```
AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=273s out=448381 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
```
