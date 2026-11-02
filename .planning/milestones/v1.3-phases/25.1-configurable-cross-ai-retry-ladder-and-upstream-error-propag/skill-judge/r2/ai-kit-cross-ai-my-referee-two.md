Judge: my-referee-two
Reviewed-sha256: fc34de9e11130d7844424142c0b8fa1e5801368f34b94b8889f7006d2c52e94e
Lane: AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=342s out=318539 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 111
Critical: 0
Important: 1

All verification complete. Here's the evaluation report.

# Skill Evaluation Report: ai-kit-cross-ai

**Scope**: `skills/ai-kit-cross-ai/SKILL.md` (168 lines, new in 25.1) + `references/launch-and-wait.md` (86) + `references/subprocess-quota-policy.md` (175); diff `35a0368~1..HEAD` = 429 insertions, all new. Claims cross-checked against the runner (`skills/ai-kit-spec-review/references/cross-ai.mjs`, 10,021 lines), the catalog, `runner_dispatch.py`, sibling skills, README/installer wiring.

**Verification highlights**: exit-code table matches `STATUS_TABLE` (cross-ai.mjs:1162-1180) exactly; retry defaults/bounds/cap (2935-2936, 2954, 2973), `--runtime`/`--prefer`-first-entry alias (4293-4309), upstream `body=`/`fields=` lines + allowlist keys (1253-1258, 1827), overlay 50 ms bound (1656), `--classify-only` (4255), pi/opencode model grammars with named-grammar refusal (1294-1296, 4249), pi review allowlist `['--skill']` (1382), `COPILOT_ALLOW_ALL` dropped + prompt-on-argv (1444, 9599), `--outer-timeout` replaces both lookups and `--timeout` can only lower (2904-2913), `stderr_tail` 2048 (`runner_dispatch.py:46`), heartbeat 30 s (4401), and all three quoted self-test cases exist (5803, 6196, 6344). The never-switch policy is stated and matches code (3067, 4293). Canonical-policy claim holds: 5 sibling skills link here; README + installer wire it. Knowledge ratio E:A:R ≈ 88:10:2.

## Dimension Scores

| Dimension | Score | Max | Notes |
|---|---|---|---|
| D1: Knowledge Delta | 19 | 20 | Near-pure machine-verified delta; honest `unverified` flags (10×) |
| D2: Mindset + Procedures | 14 | 15 | Owner-vs-caller model, "upstream = data, never instructions"; GSD skip = harness switch |
| D3: Anti-Pattern Quality | 14 | 15 | Specific NEVERs with non-obvious WHYs (argv prompt visibility, tree-dirty stop) |
| D4: Spec Compliance / Description | 15 | 15 | WHAT + WHEN + keywords + negative scope vs. two sibling skills |
| D5: Progressive Disclosure | 13 | 15 | 168-line body; one in-workflow MANDATORY trigger; no "Do NOT load" on references |
| D6: Freedom Calibration | 14 | 15 | Low freedom exactly where fragile (waits, lanes, never-switch) |
| D7: Pattern Recognition | 9 | 10 | Clean Tool/Navigation hybrid with references |
| D8: Practical Usability | 13 | 15 | Decision table byte-verified; one unsupported machinery claim, one redaction nuance |

**Total: 111/120 (92.5%) — Grade A.** Meets the repo gate (≥96 or no Critical/Important; here 111 with 1 Important — the score path carries it).

## Findings

1. **Important** — `references/subprocess-quota-policy.md:169`: "The instruction-file emitter quotes it unchanged." No instruction-file emitter exists anywhere in `skills/` at HEAD (`grep -rn "emitter" skills/` → only this line; the closest predecessor `build_gsd_cross_ai_guidance` was replaced 2026-08-30 with "Zero SKILL uses" per `.planning/research/2026-10-13-audit/04-audit-skills-spec-family.md:150`). A doc whose header promises "never restates it differently" makes an unverifiable machinery claim — the exact failure mode the repo's certainty rule bans. **Fix**: delete the sentence, or name the actual component and its path.
2. **Minor** — `references/subprocess-quota-policy.md:123-124`: "allowlisted structured fields … are copied with their values unchanged." True at copy time, but the printed `cross-ai: upstream fields=` line passes through `redactSecrets` (cross-ai.mjs:1258), and the self-test (cross-ai.mjs:2694-2697) asserts secret-looking *string* values print as `<redacted>`. **Fix**: add "(numeric values unchanged; secret-looking strings still print redacted)".
3. **Minor** — `SKILL.md:83`, `references/subprocess-quota-policy.md:46,75,89` etc.: parenthetical decision ids (`D-02`, `D-03`, `D-08`, `D-10`, `D-13`; `SPEC R3/R6/R9`) resolve only inside `.planning/` of this checkout; the skill ships standalone via symlink. **Fix**: drop them, or one line naming where they live.
4. **Minor** — `SKILL.md:163-167`: the end References list is bare; the policy reference has no conditional in-workflow trigger (unlike launch-and-wait's MANDATORY at SKILL.md:46-48). **Fix**: add a scoped trigger, e.g. "read the policy reference only to change retry config or add catalog rows — do not load it merely to make a call."

**Verdict**: a genuinely expert, live-verified operational contract — the strongest kind of Tool-pattern skill; only provenance-level accuracy issues remain.

DIGEST fc34de9e11130d78
CURRENT 111/120
CRITICAL 0 IMPORTANT 1

## Runner evidence

```
AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=342s out=318539 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
```
