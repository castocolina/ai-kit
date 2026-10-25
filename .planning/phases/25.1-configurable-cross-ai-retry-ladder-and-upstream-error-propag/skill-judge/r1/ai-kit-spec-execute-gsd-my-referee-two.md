Judge: my-referee-two
Reviewed-sha256: bc1edbe8473bef7e6dad7c829cf89b43e1f758192c7e417dbd45a84fbf235af7
Lane: AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=257s out=358570 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 110
Critical: 0
Important: 2

All claims verified against the implementation. I have everything needed for the report.

# Skill Evaluation Report: ai-kit-spec-execute-gsd

**Scope reviewed:** `SKILL.md` (485 lines), `references/dispatch-notes.md` (66), the `ai-kit-spec-gsd.py` shim, and every file it points to — `ai_kit_spec_gsd/cli.py` subcommands, `ai-kit-spec-review/ai-kit-spec.py` (`cache-path`, `trust-local`), `ai-kit-gsd-curated-config` (`ensure-runner`, `MIN_TIMEOUT_S=1800`, template-8 floor), the runner `ai-kit-spec-review/references/cross-ai.mjs` (template v8 marker; `--runtime`/`--prefer` first-entry alias at mjs:4258–4267; `hard_waits_s`/`session_resets`; redacted `cross-ai: upstream` pass-through; copilot; error catalog), and the canonical policy `skills/ai-kit-cross-ai/` — plus the Phase 25.1 diff `35a0368~1..HEAD`.

**Phase 25.1 fidelity:** the pointer `../ai-kit-cross-ai/SKILL.md` resolves (SKILL.md:41); the inlined caller rules match the canonical policy exactly (exit 75 + `retry_after_s=` → one one-shot wake, same lane/CLI/model; exit 69 `stopped=hard-waits|cap` → notice + `abort`; never `skip`; bare 75 = owner stop); every shim subcommand and flag used in the doc exists; "Never switch harness, provider or model" appears in both the contract and Step 3. No contradiction found between this skill and the canonical policy.

## Dimension Scores

| Dimension | Score | Max | Notes |
|-----------|-------|-----|-------|
| D1: Knowledge Delta | 18 | 20 | ~E:A:R = 88:10:2; near-pure project-specific machinery; token cost from duplicated cleanup block |
| D2: Mindset + Procedures | 14 | 15 | "Mindset before writing anything here" (SKILL.md:187–198) + exact, correct-order procedures |
| D3: Anti-Pattern Quality | 15 | 15 | 10-item NEVER list, each with mechanism ("skip falls back to the native executor", hook-token allowlist why) |
| D4: Specification Compliance | 14 | 15 | Valid frontmatter; description has WHAT + 3 explicit WHEN scenarios + dense keywords; one ~120-word sentence |
| D5: Progressive Disclosure | 13 | 15 | 485 lines (over 300 ideal); reference framed "read only if", exemplary delegation to canonical skill; MANDATORY stop-time read trigger was dropped |
| D6: Freedom Calibration | 14 | 15 | Fragile config writes get exact scripts; every owner decision routed to the owner |
| D7: Pattern Recognition | 9 | 10 | Process pattern with Tool-grade exactness, clean step structure |
| D8: Practical Usability | 13 | 15 | Exhaustive error/edge coverage, verified-runnable commands; stale label + two small gaps below |

**Total: 110/120 (92%, Grade A)**

## Findings

**Critical — none.**

**Important**

1. **Stop-time policy-read trigger was dropped.** The pre-25.1 text said "*MANDATORY when a cross-AI run stops*: read that policy before acting"; the 25.1 edit removed it and left only the top-of-file contract pointer (SKILL.md:41–45). Step 3's stop handling (SKILL.md:450–479) never directs the agent to open `ai-kit-cross-ai/SKILL.md` or its policy reference, so nuances owned only by the canonical policy (stopped-lane refusal exit 69 + state-file reset, `cross-ai: state` path, overlay notices) are never mandated at the point of use. Fix: in the Step 3 stop paragraph, add "MANDATORY: read [`../ai-kit-cross-ai/SKILL.md`](../ai-kit-cross-ai/SKILL.md) and its policy reference before acting on any stop."
2. **Stale pre-25.1 label "Step 3's router stop"** at SKILL.md:156 and :160. Post-25.1 the Step 3 stop that writes `RESUME_VIA=gsd-execute-phase` is *any* exit 75 carrying `retry_after_s=` (transient, quota, or deadline-cut — SKILL.md:455), not a router-specific stop; the canonical policy has no "router stop" category. An agent reading line 156 could mis-scope when that resume path applies. Fix: rename to "Step 3's cross-AI stop" in both places.

**Minor**

3. **Exit-75 cause list incomplete** — SKILL.md:455 says "(transient ladder exhausted or confirmed-router quota)" but the policy (subprocess-quota-policy.md:48–49) adds a third cause: a deadline-cut soft series also exits 75 with `retry_after_s=`. Fix: "(soft series spent or cut by the deadline)".
4. **No GSD-prompt answer for a non-hard-tier exit 69** (auth/billing/permission_blocked): the policy says "owner stop: notice, then stop", but Step 3 only covers `stopped=hard-waits|cap` ("give the notice and answer abort", SKILL.md:458). For other 69s the retry/skip/abort prompt is left dangling unaddressed. Fix: one sentence — "any other exit 69: relay the lines and leave GSD's prompt for the owner."
5. **~20-line duplicated cleanup snippet** — `clear_hook()` (SKILL.md:243–253) and the mode-transition cleanup block (SKILL.md:342–351) are near-verbatim copies; editing one and not the other silently drifts. Fix: keep one block and have the other call/reference it.
6. **Description is a single ~120-word sentence** — precise and trigger-rich, but hard to scan; splitting at "Use when (1)…" costs nothing.

DIGEST bc1edbe8473bef7e
CURRENT 110/120
CRITICAL 0 IMPORTANT 2

## Runner evidence

```
AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=257s out=358570 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
```
