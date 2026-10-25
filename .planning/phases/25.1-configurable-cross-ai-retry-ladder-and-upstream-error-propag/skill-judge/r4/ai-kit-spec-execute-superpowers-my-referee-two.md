Judge: my-referee-two
Reviewed-sha256: 1f5f09727354aee6c185d4f574da6e1e6aa4c5b34fed2e90ee9e4006fcb16bd1
Lane: AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=296s out=519152 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 115
Critical: 0
Important: 0

All verification complete. I cross-checked the skill's Phase 25.1 claims against the canonical policy (`skills/ai-kit-cross-ai/`), the runner template (`cross-ai.mjs`), and the package code it drives. Producing the report now — no files were written or modified.

# Skill Evaluation Report: ai-kit-spec-execute-superpowers

**Scope reviewed:** `SKILL.md` (459 lines), `references/{design-notes,state-management,escalation}.md`, shim `ai-kit-spec-superpowers.py`, package `ai_kit_spec_superpowers/{cli,dispatch_injection,task_classification}.py`; Phase 25.1 diff `35a0368~1..HEAD` (4 commits).

**Phase 25.1 accuracy (verified against sources):** pointer to `../ai-kit-cross-ai/SKILL.md` resolves and its §6–8 match this skill's schedule/stop rules; `hard_waits_s` 600/900/1800 (design-notes.md:124 ↔ subprocess-quota-policy.md:103); exit-75-hint vs exit-69 owner-stop semantics (SKILL.md:356–361 ↔ policy §Hard tier); the runner always pairs `retry_after_s=` with `cycle=` (cross-ai.mjs:1280–1281), so the skill's stricter both-tokens rule never diverges from the policy; copilot notes match (SKILL.md:426–428 ↔ policy:150–153); one-runtime-per-call is honored (injection carries one key; escalation is pre-dispatch-only). Never-switch is stated at SKILL.md:53, 39–42, 316–319, 411–417. No stale `subprocess-quota-policy` pointers remain in this skill.

**Knowledge ratio:** E:A:R ≈ 90:10:0. Pattern: Tool/Process hybrid, correctly low-freedom for a fragile write-capable operation.

## Dimension Scores

| Dimension | Score | Max | Notes |
|-----------|-------|-----|-------|
| D1: Knowledge Delta | 19 | 20 | Nearly every rule encodes a real failure (three-set exclusion split, reason taxonomy, anchor-not-fresh-pick floor); slight restatement at :198 |
| D2: Mindset + Procedures | 15 | 15 | "Ask: permanent or same-wave?" framing + exact non-obvious orderings (evidence before fold; increment before check) |
| D3: Anti-Pattern Quality | 15 | 15 | 10-item NEVER index, each with a non-obvious why; corroborated by code recurrence guards |
| D4: Spec Compliance | 15 | 15 | Valid frontmatter; description has WHAT + WHEN + negative scope ("not for executing-plans") + keywords |
| D5: Progressive Disclosure | 14 | 15 | MANDATORY triggers embedded at point of use; 459 lines is heavy; no explicit "Do NOT load" |
| D6: Freedom Calibration | 15 | 15 | Exact bash where fragile, delegated judgment where the host harness owns it |
| D7: Pattern Recognition | 9 | 10 | Clean adapter pattern; rationale inline ("Two current rules") a purer split would move out |
| D8: Practical Usability | 13 | 15 | Decision trees verified executable and code-consistent; dense, two description imprecisions, one no-op flag |
| **Total** | **115** | **120** | **Grade A (96%)** |

## Findings

No Critical or Important findings.

1. **Minor — ambiguous "ladder".** `SKILL.md:415` says "The runner owns the ladder", but under 25.1 the runner runs exactly one runtime per call; what it owns is the soft retry series, while the *candidate* ladder is walked by `resolve-injection` at the caller. An agent could conclude the runner already tried other candidates inside the call (design-notes.md:122 says "soft ladder" correctly). Fix: change SKILL.md:415 to "the runner owns the soft retry ladder".
2. **Minor — `"quota"` bullet understates its own coverage.** SKILL.md:320–322 calls the classification "the runner's time-bound hard-tier outcome", but `classify_dispatch_failure` (dispatch_injection.py:398–430) also returns `"quota"` for an exit-69 hard-tier stop and a bare exit 75 — neither waitable; only point 4 (SKILL.md:356–361) says so. Fix: append "plus the exit-69 stop and bare-75 shapes, which point 4 routes to an owner stop", mirroring the docstring's "does not tell those apart".
3. **Minor — required-but-unused flag.** `--heartbeat-interval` is `required=True` in `cli.py:420` yet unused (admitted at SKILL.md:292); every caller passes a no-op. Fix: give it a default (or remove it) in `cli.py` and drop it from the SKILL.md:270 call.
4. **Minor — triple-maintained paragraph.** SKILL.md:198 is byte-identical in `ai-kit-spec-review/SKILL.md:243` and `ai-kit-spec-execute-gsd/SKILL.md:182`. Fix: point at the `ai-kit-cross-ai` statement of the native/external rule instead of holding a fourth copy (or accept the documented sync cost).
5. **Minor — 459-line body.** Step 3's quota branch (schedule-or-stop matrix + wake prompt, ~70 lines) is as self-contained as the state writes already delegated to `state-management.md`. Fix (optional): move it to `references/` behind a MANDATORY trigger; keep the wake prompt exact wherever it lives.

Verdict: an expert-grade, policy-consistent adapter skill; the Phase 25.1 re-pointing is complete and accurate, and nothing in it authorizes a harness, provider or model switch.

DIGEST 1f5f09727354aee6
CURRENT 115/120
CRITICAL 0 IMPORTANT 0

## Runner evidence

```
AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=296s out=519152 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
```
