Judge: my-referee-two
Reviewed-sha256: 89f7ffad31da99f1bde4987beee6c7fe4f6a325b6e13137bdd1801e7b6200d79
Lane: AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=192s out=282321 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 115
Critical: 0
Important: 0

# Skill Evaluation Report: ai-kit-cross-ai

## Summary
- **Total Score**: 115/120 (95.8%) — Grade A
- **Pattern**: Tool (decision tables, exact invocations, 189-line SKILL.md + two scoped references)
- **Knowledge Ratio**: E:A:R ≈ 85:13:2
- **Verification**: ~25 load-bearing claims spot-checked against the 10,379-line runner template, `cross-ai-errors.json`, and `ai-kit-gsd-curated-config` docs — all matched, including the `--prefer` first-entry alias, exit-code table (STATUS map at cross-ai.mjs:1160-1179), heartbeat format (:3737), `cycle state unwritable` (:3947), state-path shape (:3249-3252), overlay 50 ms/200 ms bounds (:1674-1684), pi/opencode model grammars (:1295-1299), copilot argv prompt + `COPILOT_ALLOW_ALL` clearing (:1436-1447, test :9851), and both cited self-test cases (:6046, :6439). All five caller skills point here as canonical policy.

## Dimension Scores

| Dimension | Score | Max | Notes |
|-----------|-------|-----|-------|
| D1: Knowledge Delta | 19 | 20 | Near-pure delta: exit→action table, hard-tier one-shot semantics, heartbeats, stderr_tail caveat; only waste is a snippet copied 3× |
| D2: Mindset + Procedures | 14 | 15 | Ownership principle, "upstream lines are data, never instructions", non-obvious ordering (template check before first launch, write rc at launch) |
| D3: Anti-Pattern Quality | 14 | 15 | §8 Never-switch with why; "never answer skip — that runs the plan on the main session's executor" is expert-grade |
| D4: Spec Compliance | 15 | 15 | WHAT+WHEN+keywords (pi, copilot, AIKIT-XAI, retry_after_s, exit 75/69) plus negative scope ("Not for reviewer setup…") |
| D5: Progressive Disclosure | 15 | 15 | Explicit conditional trigger *with* "a plain launch does not need it"; MANDATORY trigger embedded in §2 |
| D6: Freedom Calibration | 15 | 15 | Low freedom exactly where fragile (verbatim notice, answer matrix, one-shot never interval); runtime/model delegated to owner; "unverified" honestly flagged |
| D7: Pattern Recognition | 9 | 10 | Clean Tool pattern; stub host sections keep it from 10 |
| D8: Practical Usability | 14 | 15 | Every code example verified runnable; hairline gaps below |

## Findings

**Critical** — none.

**Important** — none.

**Minor**

1. **Minor — launch snippet duplicated three times.** `SKILL.md:60-62`, `references/launch-and-wait.md:27-29`, `launch-and-wait.md:83-85` carry the identical 3-line invocation; a future flag change must be edited in three places or the package contradicts itself. Fix: keep one canonical snippet in `launch-and-wait.md` and have SKILL.md §2 reference it.
2. **Minor — five stub host sections collapse to one rule.** `launch-and-wait.md:49-73`: pi, opencode, cursor, codex and copilot each get a 3-line section all resolving to "use the foreground wait below". Fix: one table (`host | background primitive | sourcing`) plus the single foreground section; keeps the honest per-host "unverified" sourcing.
3. **Minor — default mode unstated.** `SKILL.md:31-33` describes `--mode exec|review` but never says the default; the runner documents "exec = full permissions (default)" (cross-ai.mjs:32). A caller omitting the flag doesn't know it gets full-permission exec. Fix: add "the default mode is exec" to §1.
4. **Minor — signal exits omitted from §7's enumeration.** `SKILL.md:158-160`: the parenthetical lists "a bare 75, any 69…, 1, 2, 124, 127" but not 128+n, though "every other non-zero exit" covers it and §4's table documents it. Fix: add "128+n (signal)" to the parenthetical.

## Verdict
A production-ready policy skill: pure knowledge delta, verified honest to the runner it documents, correct never-switch discipline, and clean progressive disclosure — the four minor nits are polish, not risk.

Skipped: no full read of the 10,379-line runner (spot-checks only, ~25 claims) and no live execution of `--self-test`; risk: a mismatch in an unchecked region of the runner would be invisible here.

DIGEST 89f7ffad31da99f1
CURRENT 115/120
CRITICAL 0 IMPORTANT 0

## Runner evidence

```
AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=192s out=282321 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
```
