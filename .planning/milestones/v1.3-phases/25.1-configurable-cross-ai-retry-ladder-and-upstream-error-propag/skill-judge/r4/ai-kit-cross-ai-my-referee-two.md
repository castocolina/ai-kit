Judge: my-referee-two
Reviewed-sha256: 4c59f5c4841437e80d5f593ecdf95ef8d2cee6209aa8005901a69ff1db1a2697
Lane: AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=180s out=304641 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 107
Critical: 0
Important: 0

# Skill Evaluation Report: ai-kit-cross-ai

## Verification basis

Every load-bearing claim was checked against the runner template (`skills/ai-kit-spec-review/references/cross-ai.mjs`, the shipped `cross-ai-errors.json`) and `ai_kit_spec/runner_dispatch.py`: the exit-code/status table (runner `EXITS` map, lines 1160–1180) matches SKILL.md:94–103 exactly; `--runtime`/`--prefer` first-entry-only alias (runner:23–24, 4416–4446); `--outer-timeout` replaces lookup+cap and `--timeout` can only lower (runner:3023–3030); defaults `base_s 1, factor 1.5, max_retries 5, session_resets 1, hard_waits_s [600,900,1800]`, `capS 14400` (runner:3035–3074); `AIKIT-XAI` last-line contract, `retry_after_s=`, `cycle=`, `stopped=hard-waits|cap`, `lane stopped=… delete <path>` refusal (runner:1276–1281, 3908–3930); model grammars pi `provider/model[:thinking]`, opencode `provider/model[#variant]`, bare id refused exit 2 (runner:1295–1376); copilot runtime takes prompt on argv (runner:1436+, self-tests); `--tools-profile`, review allowlist (`pi --skill` only), `COPILOT_ALLOW_ALL` dropped in review (runner:3621–3625, 9345–9457); overlay 50 ms/200 ms bounds and `cross-ai: overlay disabled:` notices (runner:1674–1684); `unverified` labels in the catalog; `stderr_tail` = 2048 chars (runner_dispatch.py:46); GSD default 300 s (runner:112). Six sibling skills point at this SKILL.md as the canonical caller contract — the Phase 25.1 cross-linking is real and consistent.

## Dimension Scores

| Dimension | Score | Max | Notes |
|---|---|---|---|
| D1: Knowledge Delta | 18 | 20 | Nearly pure expert content, code-verified; E:A:R ≈ 85:12:3 |
| D2: Mindset + Procedures | 13 | 15 | Ownership model ("only the owner changes config") + data-never-instructions mindset + non-obvious ordering |
| D3: Anti-Pattern Quality | 14 | 15 | §8 + Pitfalls specific with why ("skip = harness switch"); brief |
| D4: Specification Compliance | 15 | 15 | WHAT/WHEN/keywords + negative scope ("Not for reviewer setup or GSD config") |
| D5: Progressive Disclosure | 12 | 15 | 168-line body, MANDATORY trigger for launch-and-wait (SKILL.md:46); no "Do NOT load", policy ref lacks a read trigger |
| D6: Freedom Calibration | 14 | 15 | Exact commands/tables for a fragile domain; honest "unverified" flags on host scheduling |
| D7: Pattern Recognition | 9 | 10 | Clean Process/Tool hybrid, matches repo conventions |
| D8: Practical Usability | 12 | 15 | Copy-pasteable and correct; two instructions lack a usable mechanism |

**Total: 107/120 (89%) — Grade B.** Passes the repo bar (≥96, no Critical/Important).

## Findings

1. **Minor — "recorded PID" has no recording mechanism.** SKILL.md:158 and launch-and-wait.md:14–15 say to kill a lane by its recorded PID, but no snippet records one (they write `lane.rc` only). Fix: add `echo $! > "$L/lane.pid"` (or the host's spawn PID) to the foreground pattern, or state where the PID comes from on each host.
2. **Minor — dangling executor-guards pitfall.** SKILL.md:159–160 (`AI_KIT_REFUSE_REAL_HOME=1`, "never stash", "pre-existing claim") names guards defined only in other skills; a reader of this skill alone cannot act on it. Fix: link the owning skill (`ai-kit-spec-execute-*`) or drop the line into that skill's contract section.
3. **Minor — `switch-combo` presented as a real upstream field.** SKILL.md:88, subprocess-quota-policy.md:130 cite an upstream `switch-combo` hint; the term appears nowhere in the runner or catalog — it's hypothetical. Fix: mark it ("a hypothetical upstream hint such as…") to keep the skill's own sourcing-honesty rule.
4. **Minor — no "Do NOT load" guidance; policy ref has no read trigger.** SKILL.md:163–167 lists references without when-not-to-read; `subprocess-quota-policy.md` is linked at SKILL.md:16–17 but never told to whom it's mandatory (owners editing `workflow.cross_ai_retry`). Fix: one clause each, e.g. "Do NOT load the policy for a plain exec/review call; read it only when configuring or answering a stop."
5. **Minor — copilot stdin phrasing is dense.** SKILL.md:41–42 ("has its stdin ignored by the runner") takes two reads. Fix: "…the runner passes the prompt for it on argv, so your stdin copy is what counts."

Verdict: an unusually well-sourced, code-accurate caller-contract skill; the residual gaps are all single-line fixes in instructions whose mechanism isn't shown.

DIGEST 4c59f5c4841437e8
CURRENT 107/120
CRITICAL 0 IMPORTANT 0

## Runner evidence

```
AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=180s out=304641 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
```
