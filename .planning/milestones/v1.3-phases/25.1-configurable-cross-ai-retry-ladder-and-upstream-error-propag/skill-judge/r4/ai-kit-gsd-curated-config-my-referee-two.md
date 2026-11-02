Judge: my-referee-two
Reviewed-sha256: 377df0dc0d0d2c2f14f7d9672232ffc13f05890eeb019270fe721645e9daee84
Lane: AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=268s out=354897 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 112
Critical: 0
Important: 2

# Skill Evaluation Report: `ai-kit-gsd-curated-config`

## Summary
- **Total Score**: 112/120 (93%) — Grade A
- **Pattern**: Tool/Process hybrid (decision tables + exact commands + phased workflow)
- **Knowledge Ratio**: E:A:R ≈ 90:9:1
- **Verdict**: A dense, near-pure expert skill whose Phase 25.1 rewrite is factually accurate against the code it wraps — I live-verified every load-bearing 25.1 claim (template=8 header in `cross-ai.mjs:2`; `--runtime` with `--prefer`-first-entry alias at `cross-ai.mjs:4416-4432`; `script:cross-ai.runtime` in `plan_edit.py:26` with an old-`prefer` migration message; `workflow.cross_ai_retry`/`hard_waits_s` in the template; `cross-ai-errors.json` exists (73 rows); copilot runtime and `--tools-profile` present; both pointers to `../ai-kit-cross-ai/SKILL.md` resolve; no stale references to the old policy path). Two consistency gaps remain, both around the new canonical policy.

## Dimension Scores

| Dimension | Score | Max | Notes |
|---|---|---|---|
| D1: Knowledge Delta | 19 | 20 | Exit-code tables split v1/v2, trust model, `router_backed` semantics, template floors — near-zero redundancy |
| D2: Mindset + Procedures | 14 | 15 | "Ask yourself: trusted checkout? v1-written? where do files live?" gate + non-obvious ordering (review → dry run → end turn) |
| D3: Anti-Pattern Quality | 15 | 15 | NEVERs carry mechanisms (`--force` "bypasses the candidate check, the trusted-root drop refusal and the full-permissions guard" with keys named); Common-mistakes table has Why/Fix |
| D4: Specification Compliance | 15 | 15 | Description has WHAT + WHEN + seven quoted trigger phrases, and honestly scopes itself against `gsd-settings` |
| D5: Progressive Disclosure | 13 | 15 | runner.md/v1-path.md have excellent read-when + "Do NOT load" triggers; but SKILL.md is 396 lines with §Skills detail in the body, and one scenario (retry tuning) sits only behind triggers that don't include it |
| D6: Freedom Calibration | 13 | 15 | Low freedom exactly where writes are fragile (fingerprint-bound `approve_with`, pseudo-keys); one real contradiction between a NEVER and runner.md (finding 2) |
| D7: Pattern Recognition | 9 | 10 | Clean Tool-pattern execution; slightly above the pattern's ~300-line norm |
| D8: Practical Usability | 14 | 15 | Verified commands, exit-code decision trees, failure states, edge cases; one coverage gap (finding 1) |

## Findings

**Critical** — none.

**Important**

1. **Verbatim-print enumerations omit the `cross-ai: upstream` lines that 25.1 added.** Three places enumerate what to print on a non-ok dispatch and all stop at two lines: SKILL.md:238-241 ("print the `AIKIT-XAI status=…` line … The `cross-ai: report` line … print it verbatim too, then stop"), SKILL.md:204-206 ("report the `cross-ai: report` and `AIKIT-XAI` lines only"), and SKILL.md:395-396 (Reporting rule). The canonical policy requires all three — `ai-kit-cross-ai/SKILL.md:124-126`: "print the `cross-ai: report`, the `cross-ai: upstream` lines and the `AIKIT-XAI` line verbatim". Delegation to the policy exists, but a hurried agent executes the local enumeration and drops the redacted upstream body — the exact evidence the owner needs on a stop. **Fix**: add "and the `cross-ai: upstream` lines" to all three enumerations.

2. **The hand-write NEVER contradicts runner.md, and retry tuning has no loading trigger.** SKILL.md:356-357: "Never hand-write `.planning/config.json`" vs runner.md:41-44: "configured by `workflow.cross_ai_retry` in the project config … **hand-edit these sources** because `config-set` refuses the project key". A cheap executor holding both rules stalls or over-generalizes the exception. Worse, the runner.md read-trigger list (SKILL.md:262-266: runner upgrade, `.new` merge, `ensure-runner`, template flags, live timeout, `extraArgs`, non-ok dispatch) never fires for "user asks to tune retries", so the only page documenting that key is unreachable via routing. **Fix**: scope the NEVER with one clause ("the one exception is `workflow.cross_ai_retry`, which `config-set` refuses — see runner.md") and add "retry tuning (`workflow.cross_ai_retry`)" to the runner.md trigger list.

**Minor**

3. **runner.md:65-66 "Template 7 has neither" overstates.** Template 7 carried the old `sameSessionRetries`/`cooldownS` knobs (removed by this same diff), so "no retry config" can read as "template 7 never retries". **Fix**: "Template 7 has neither `--runtime` nor the configurable soft series (`base_s`/`factor`/`hard_waits_s`); it carries only the fixed `sameSessionRetries` knobs."

4. **Runtime-pick step omits per-runtime caveats.** At the `script:cross-ai.runtime` / model pick (SKILL.md:123-128), an owner choosing copilot is never told its prompt goes on argv and is visible in the process table (`ai-kit-cross-ai/references/launch-and-wait.md:69-73`). **Fix**: one clause at the pick step pointing to the canonical skill's runtime caveats.

5. **§Skills wiring rules (SKILL.md:268-322, ~55 self-contained lines) belong in a reference** with a "read when wiring skills" trigger; that alone would bring SKILL.md near the ~300-line ideal.

Per this repo's own gate (AGENTS.md: no remaining Critical/Important finding **or** score ≥ 96/120), the skill passes at 112 despite findings 1-2; fixing them is cheap and would clear both bars.

DIGEST 377df0dc0d0d2c2f
CURRENT 112/120
CRITICAL 0 IMPORTANT 2

## Runner evidence

```
AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=268s out=354897 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
```
