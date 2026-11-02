Judge: opus
Reviewed-sha256: 7996e22222cd63cd1178a0a10cac115b814e4c26cccb511e4eaa31d588c4b5c1
Lane: native subagent completed
Score: 99
Critical: 0
Important: 2

# Skill Evaluation Report: ai-kit-spec-review

**Total: 99/120 (82.5%), grade B.** Pattern: Process. Knowledge ratio E:A:R is about 75:15:10. I found no Critical issues and two Important ones. The skill points at `ai-kit-cross-ai` correctly and never re-dispatches a failed lane on its own. Two things need fixing: its pre-dispatch probe walk can still end on the native session, and one reference line misstates when a bare exit 75 happens.

| Dimension | Score | Max | Notes |
|---|---|---|---|
| D1 Knowledge Delta | 16 | 20 | Dense, project-specific knowledge: exit branching, pending-lane resume, merge lock, the trailing-`\` redirect trap. `cross-ai-dispatch.md` points 0-1 carry narrative padding. |
| D2 Mindset + Procedures | 13 | 15 | "Before X, ask yourself" checks at Steps 0.5, 0.7, 3 and 5, plus exact domain procedures. |
| D3 Anti-Pattern Quality | 12 | 15 | The NEVER list and Hard-rules table give reasons. The "never re-dispatch a failed lane" rule is present (SKILL.md:474). The NEVER section itself is thin. |
| D4 Specification Compliance | 14 | 15 | Valid frontmatter. The description covers what, when and keywords, but it is long. |
| D5 Progressive Disclosure | 12 | 15 | MANDATORY triggers and "Do NOT load" lines exist. SKILL.md is 489 lines. The 965-line `cross-ai-errors.json` has no loading guidance. |
| D6 Freedom Calibration | 13 | 15 | Low freedom for the fragile dispatch path (`dispatch-reviewer`, never hand-render the argv), medium freedom for review judgment. |
| D7 Pattern Recognition | 8 | 10 | A clear Process pattern, but long for that pattern. |
| D8 Practical Usability | 11 | 15 | Thorough on failures, but two policy and fact mismatches, stale per-CLI profiles, and no eval for the hard tier. |

## Findings

1. **Important: the probe walk ends on the session default, which the canonical policy forbids, and the owner quote it cites does not cover that case.**
   - SKILL.md:157-168 says that when no configured entry is available, "the walk ends on the session default". It justifies this with the 2026-08-29 owner quote "try A, then B, fall back to native only if both lack quota".
   - That quote (ai_kit_spec/quota.py:146-156) was about a ladder that listed a native entry explicitly. It does not cover the implicit `NO_CONFIG_FALLBACK` when the ladder has no native entry.
   - The walk also moves on after a probe "fails for any reason, a timeout included". That counts as moving on after a failure.
   - The canonical policy, ai-kit-cross-ai/SKILL.md:146-148, says: "Never switch harness, provider or model, on any failure ... Never move the work to the native session." It records no pre-dispatch exception.
   - Fix: either record the pre-dispatch-selection exception in ai-kit-cross-ai §8 with an explicit owner ruling, or change the walk. Without a native ladder entry, it would surface `every configured reviewer unavailable` and stop rather than review with the session default. In both cases, narrow the SKILL.md wording so the quote is not claimed beyond what it says.

2. **Important: `cross-ai-dispatch.md` gives a wrong cause for a bare exit 75.**
   - cross-ai-dispatch.md:249 says an exit 75 without `retry_after_s=` means "the runner could not write its state file".
   - The runner also exits with a bare 75 in two other cases:
     - An off-router quota stop (`classStop`, cross-ai.mjs:4033/4041). Self-tests `quota` (cross-ai.mjs:5815-5818) and `live-reason-code-no-kill` (6845-6860) expect no `retry_after_s`.
     - The dirty-tree gate stop on a quota lane (cross-ai.mjs:4108-4114).
   - The previous wording ("an off-router quota stop") was correct, so this is a regression. An orchestrator would tell the owner the wrong cause.
   - Fix: replace the parenthetical with "(an off-router quota stop, a dirty-tree stop, or an unwritable state file)", or drop it and link the policy.

3. **Minor: SKILL.md:334-340 lists only the hard-tier causes of exit 69.**
   - Exit 69 also covers auth, billing, bad_model and permission_blocked (ai-kit-cross-ai/SKILL.md:99).
   - Fix: "Any exit 69 (a class stop such as `auth`, or `stopped=hard-waits`/`stopped=cap`/a `lane stopped=` refusal)".

4. **Minor: the per-CLI profiles are stale, and the new runtimes have none.**
   - references/cli-profiles/opencode.md:31-35 says the `#variant` suffix "is not validated". The runner now validates it with `OPENCODE_MODEL_ID` (cross-ai.mjs:1297).
   - The same profile's review argv leaves out `--standalone` (cross-ai.mjs:1355).
   - There is no profile for copilot, even though it is a new RUNTIMES row (detection.py:117-118), and none for pi.
   - The copilot prompt-on-argv exposure (ai-kit-cross-ai/SKILL.md:152-153) matters for private documents and is not mentioned anywhere in this skill.
   - Fix: refresh `opencode.md`, and add short copilot and pi profiles stating that the runner owns flags and grammar, plus the argv-visibility caveat.

5. **Minor: no "Do NOT load" for the error catalog.** SKILL.md:153 rules out `cross-ai.mjs` and `cli-profiles/` but not `references/cross-ai-errors.json`. Fix: add it as runner data that is never instructions, and name `--classify-only` as the owner's tool for it.

6. **Minor: size and density.**
   - SKILL.md is 489 lines, close to the 500 limit.
   - The Step 1 subprocess bullet (SKILL.md:285-349) packs all exit branching into prose.
   - cross-ai-dispatch.md:5-18, 77-84 and 97-109 contain history and narrative.
   - Fix: replace the exit prose with one exit-to-action table (0 / 69 / 75 with hint / bare 75 / other), move the rest to `cross-ai-dispatch.md`, and trim the narrative.

7. **Minor: the hard-tier path has no diagram branch and no eval.** `references/loop-diagram.md` has no pending-lane branch, and `evals/01-04` cover only fixer routing. Fix: add one eval (double mode with one lane at exit 75 plus `retry_after_s`: no fixer runs, the sibling merges as single mode, a one-shot is scheduled) and one diagram branch.

8. **Minor: scheduling wording differs from the canonical policy.**
   - cross-ai-dispatch.md:293 rounds the wait up to a whole minute, with at least 60 s.
   - The canonical policy says "exactly `retry_after_s`" (ai-kit-cross-ai/SKILL.md:120).
   - This is harmless, because the runner refuses an early call through `due_at`. Fix: add one clause saying the rounding is cron granularity and that a late wake is safe.

I did not run the runner self-test or `make test`, and I did not check the subagent-side skills (checklist, fixer). Finding 1 needs an owner ruling, not just an edit.

DIGEST 7996e22222cd63cd
CURRENT 99/120
CRITICAL 0 IMPORTANT 2
