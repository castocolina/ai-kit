Judge: my-referee-two
Reviewed-sha256: 35f2ccd9681d61563642bded80f66bce63378c741719b6ca7613d8058a565823
Lane: AIKIT-XAI status=ok cli=pi model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=59s out=5907 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 104
Critical: 0
Important: 2

# Skill Evaluation Report: ai-kit-spec-execute-superpowers

## Summary
- **Total Score**: 104/120 (87%)
- **Grade**: B
- **Pattern**: Process (phased adapter with low-freedom checkpoints)
- **Knowledge Ratio**: E:A:R ≈ 80:15:5
- **Verdict**: A real operational brain for a fragile dispatch adapter, with load triggers and verified CLI contracts, but two contradictions can send an agent down the wrong stop or resume path.

## Dimension Scores

| Dimension | Score | Max | Notes |
|-----------|-------|-----|-------|
| D1: Knowledge Delta | 18 | 20 | Ladder-key vs runtime, wave vs permanent exclusions, pinned re-dispatch, capability floor. Paragraph at SKILL.md:211 restates a shared definition. |
| D2: Mindset + Procedures | 14 | 15 | "Before touching an exclusion, ask permanent vs same-wave" plus exact bash the model would not invent. |
| D3: Anti-Pattern Quality | 14 | 15 | NEVER list with non-obvious reasons (KeyError, permanent quota lockout, status-word false DONE). |
| D4: Specification Compliance | 14 | 15 | name valid; description has WHAT, WHEN, and negative trigger (`executing-plans`). Slightly dense, no user-facing trigger phrases. |
| D5: Progressive Disclosure | 13 | 15 | Mandatory reads are scenario-gated and most say Do NOT load. design-notes and cross-ai are conditional. No Do NOT load on the always-required cross-ai file. |
| D6: Freedom Calibration | 14 | 15 | Low freedom matches a wrong-byte stop. Placeholders are guarded. Compose step is prose where the rest is exact bash. |
| D7: Pattern Recognition | 8 | 10 | Clear Process pattern; longer than ~200 because the procedures are domain-specific and mostly offloaded. |
| D8: Practical Usability | 9 | 15 | Modes, exits, and fallbacks are covered, but two internal contradictions mis-route resume and quota stops. |

Claims checked and held: shim subcommands and flags (`cli.py:388-466`); `quota_exhausted` / `no_candidate` shapes (`cli.py:136-147`, `cli.py:193`); unverified still `external_cli` (`dispatch_injection.py:295-307`); classify tokens and return codes (`dispatch_injection.py:422-459`); untrusted-config prefix (`config_io.py:410`); Node absent → `dispatch_unavailable` (`runner_dispatch.py:66`, `runner_dispatch.py:589-591`); Node 24 citation (`.planning/phases/18.1-one-runtime-model/18.1-RESEARCH.md:231`); codex sandbox and pi/copilot notes (`runner_dispatch.py:170-182`, `runner_dispatch.py:215`); cross-ai sections 6 and 8 (`ai-kit-cross-ai/SKILL.md:128`, `SKILL.md:168`); session-wake `armed`/`refreshed` (`arm.py:480`).

## Critical Issues
None.

## Top 3 Improvements
1. Make the pinned-resume rule one path: a restored `injection_json` never re-enters Step 2, including at rounds 4–5.
2. State one schedule rule for return code 69: owner stop, never a wait.
3. Add a Do NOT load for `ai-kit-cross-ai` except before the first `dispatch-task` and a non-zero runner return code.

## Detailed Analysis

### D8 (below 80%)
Two procedures disagree with themselves, so an agent that follows the later sentence undoes the earlier one.

**Pinned resume vs rounds 4–5.** `SKILL.md` Step 2 says a restored `injection_json` goes straight to Step 3 and skips resolution. Step 3 and `escalation.md` then say a resume restored at round 4 or more re-enters Step 2 and re-resolves. `state-management.md` says the opposite again: a pinned file skips `resolve-injection`. Re-resolving after a failed dispatch violates the skill's own never-switch rule.

**Return code 69.** The quota branch says only return code 75 with whole-number `retry_after_s` and `cycle` waits, and that 69 is an owner stop. The next sentences say a tokenless 69 whose status is `transient` or `quota` "reaches it" as an owner stop, which reads as entering the wait branch.

## Findings

1. **Important** — `skills/ai-kit-spec-execute-superpowers/SKILL.md:230` and `references/escalation.md:8` contradict `SKILL.md:166` and `references/state-management.md:126`. A resume that already holds `injection_json` is told both to skip Step 2 and, when `FIX_ROUND >= 4`, to re-enter Step 2 and re-run `resolve-injection`. That second path switches the pair after a failed dispatch. Fix: one sentence in both files — pinned `injection_json` always re-dispatches unchanged; escalation re-resolution runs only when Step 2 is already running because there is no pin.

2. **Important** — `skills/ai-kit-spec-execute-superpowers/references/dispatch-external-cli.md:157` and `:163` disagree with `:159` and `:165`. Return code 69 is an owner stop with nothing scheduled, but "reaches it" points at the one-shot wait branch. `classify_dispatch_failure` does return `"quota"` for a bare 69 with status `transient` or `quota` and no `retry_after_s` (`dispatch_injection.py:449-452`), so the agent must not wait. Fix: replace "reaches it as an owner stop" with "is classified quota but is an owner stop: relay, write pinned state, schedule nothing."

3. Minor — `skills/ai-kit-spec-execute-superpowers/SKILL.md:275` cites `@opengsd/gsd-core` `engines.node >=24.0.0` as if this tree declared it. The runner only fails closed when `node` is missing (`runner_dispatch.py:66`, `runner_dispatch.py:589`); the `>=24` fact is only in `.planning/phases/18.1-one-runtime-model/18.1-RESEARCH.md:231`, which the same sentence admits. Fix: drop the engines citation or mark it external and unverified in this tree.

4. Minor — `skills/ai-kit-spec-execute-superpowers/SKILL.md:211` repeats the reviewer/executor pair definition already in `ai-kit-spec-config` and `ai-kit-spec-review`. Fix: one line pointing at that contract, not the full paragraph.

5. Minor — `skills/ai-kit-spec-execute-superpowers/SKILL.md:49` makes `../ai-kit-cross-ai/SKILL.md` mandatory with no Do NOT load, unlike every other reference. Fix: load it only before the first `dispatch-task` and before acting on a non-zero runner return code.
