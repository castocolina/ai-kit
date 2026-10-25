Judge: my-referee-two
Reviewed-sha256: 29ec2a75169bb7038d204870f064fb339adf0c02441032341c64806e07067892
Lane: AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=242s out=405094 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 114
Critical: 0
Important: 0

All claims verified against the code (`RUNNER_IDS`, `_assert_runner_target` copilot refusal, `TEMPLATE_VERSION = 8`, `_READY_TEMPLATE = 8`, `prefer→runtime` first-entry merge, retry-config precedence, exit/status map, upstream redaction, catalog + overlay paths, resolving cross-links, `--print-argv`, `CROSS_AI_COMMAND`). Report:

# Skill Evaluation Report: ai-kit-gsd-curated-config

**Total: 114/120 (95%) — Grade A** · Pattern: Tool (with a phased Process workflow) · Knowledge ratio E:A:R ≈ 88:10:2

Verdict: a dense, code-accurate operational skill whose 25.1 rewrite correctly hands the caller contract to `ai-kit-cross-ai` and keeps the never-switch invariant in three places (SKILL.md:378-380, body 221-223, policy §8); the residual cost is SKILL.md length.

## Dimension Scores

| Dimension | Score | Max | Notes |
|---|---|---|---|
| D1: Knowledge Delta | 19 | 20 | Near-pure project-only knowledge: exit/status tables, refusal semantics, trust model, template floors; only the Limits table and a few sentences echoing printed stderr are borderline |
| D2: Mindset + Procedures | 14 | 15 | "Ask yourself" gate (SKILL.md:67-71) + non-obvious ordering with WHY (v1-path.md:15-16; dry-run approval rule SKILL.md:165-168) |
| D3: Anti-Pattern Quality | 15 | 15 | 9 NEVER entries each with a reason; Common mistakes table with Why/Fix; never-switch rule precise (`--runtime`/`--prefer`/provider/model/CLI/native all named) |
| D4: Spec Compliance | 15 | 15 | Valid frontmatter; description has WHAT + WHEN + keywords + must-use triggers + explicit boundary ("a faster alternative, not a replacement") |
| D5: Progressive Disclosure | 13 | 15 | Both references have scenario triggers + "Do NOT load" (runner.md:3-7, v1-path.md:3); MANDATORY policy gate (SKILL.md:243-244); but 406 lines and the ~55-line Skills block (275-329) is reference-grade inline |
| D6: Freedom Calibration | 15 | 15 | Exact commands for fragile config writes; `--force` gated with enumerated bypasses; runtime change owner-gated and forbidden as a stop answer |
| D7: Pattern Recognition | 9 | 10 | Clean Tool pattern; hybrid with Process adds length pressure |
| D8: Practical Usability | 14 | 15 | Every command, key and pointer I checked exists and matches the code; one summary drops a policy caveat (finding 1) |

## Findings

**Critical** — none.

**Important** — none. (Verified: copilot refusal matches `_assert_runner_target` (plan_edit.py:364-376); template 8 + readiness floor 8 match `TEMPLATE_VERSION`/`_READY_TEMPLATE` (cross_ai.py:46, cross_ai_script.py:31); `--prefer` alias and `prefer[0]` upgrade mapping match the template header/upgrade code; retry precedence and `hard_waits_s` live in the policy the skill points to; `../ai-kit-cross-ai/SKILL.md` §§6-8 resolve and describe exactly what SKILL.md:244-247 says; no stale `subprocess-quota-policy.md` links remain.)

**Minor**
1. SKILL.md:245-246 — "an exit 75 with `retry_after_s=` gets one wait and the same lane again" omits the policy's no-scheduler handoff (ai-kit-cross-ai/SKILL.md:149-154: without a one-shot scheduler, print `retry_after_s`, state path and re-invoke command, and stop). An agent on a scheduler-less host may sleep inline instead of handing off. Fix: append "(one-shot where a scheduler exists; otherwise the §6 handoff)".
2. SKILL.md:331 — "Limits (as of 2026-10-23)" predates this diff's 25.1 changes (catalog evidence dated 2026-10-24/25 in cross-ai-errors.json); the snapshot label no longer covers HEAD. Fix: refresh the date and re-check the two "pending" rows after 25.1 validation.
3. SKILL.md:124-128 — lists runner ids (pi, cursor, opencode, codex) but not the default menu (`DEFAULT_PREFER = ("pi", "cursor", "opencode")`, cross_ai.py:48): an agent may expect codex choices by default. Fix: one clause "the default menu is pi, cursor, opencode; codex joins only when picked".
4. SKILL.md:275-329 — the Skills wiring block (~55 lines of refusal/resolution detail) is reference-grade; moving it to `references/skills.md` with a read-when trigger brings SKILL.md near the 300-line ideal without losing anything.

DIGEST 29ec2a75169bb703
CURRENT 114/120
CRITICAL 0 IMPORTANT 0

## Runner evidence

```
AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=242s out=405094 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
```
