Judge: my-referee-two
Reviewed-sha256: 17fb505e590c611cce964ad027ce5e245a132d8a946bb0735ced163ef76155d8
Lane: AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=224s out=392251 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 108
Critical: 0
Important: 2

All verification complete. Here is the evaluation.

# Skill Evaluation Report: ai-kit-spec-execute-gsd (post Phase 25.1)

**Verification done before scoring:** every cross-reference claim was live-checked — the pointer target `../ai-kit-cross-ai/SKILL.md` exists and is canonical; SKILL.md's retry semantics match the policy exactly (exit 75 + `retry_after_s=` → answer nothing, one one-shot wake, same lane/CLI/model; exit 69 `stopped=hard-waits`/`cap` → notice + `abort`; never `skip`; never switch harness/provider/model — stated twice, SKILL.md:45,462); `unsupported_model_id` is real (`adapter.py:238-242`, gated on `HOOK_TOKEN_RE.fullmatch and not model_id_ok`); the copilot runtime exists (`detection.py:118`) and its EXEC_NOTE (`runner_dispatch.py:176-180`) matches SKILL.md:318-319's summary including the unverified flag; runner template 8 confirms one runtime per call with `--prefer` as first-entry alias (`cross-ai.mjs:23-24`), soft series + `session_resets:1` + `hard_waits_s` (configurable, `subprocess-quota-policy.md:37-50,95-115`), caller-owned hard tier, redacted upstream pass-through, error catalog + owner overlay; all seven shim subcommands and flags in SKILL.md match `cli.py:400-454` argparse exactly. No claim was found to be wrong or overstated.

## Dimension Scores

| Dimension | Score | Max | Notes |
|-----------|-------|-----|-------|
| D1: Knowledge Delta | 19 | 20 | Near-pure expert content: unquoted-hook glob semantics, adapter-owned vs user-owned keys, revert_failed hand-fixes, gsd-core trust model; no basics explained |
| D2: Mindset + Procedures | 14 | 15 | "Mindset before writing anything" block (SKILL.md:187-198) + procedures Claude cannot know (exit-code contracts, marker-guarded append, wake protocol) |
| D3: Anti-Pattern Quality | 14 | 15 | NEVER list with non-obvious WHYs — "never re-resolve after failed dispatch: a fresh resolve-dispatch walks the candidates again" (SKILL.md:20-24) is landmine knowledge |
| D4: Spec Compliance | 14 | 15 | WHAT/WHEN/KEYWORDS all present, 3 numbered triggers, 820 chars (<1024 cap); −1 for always-resident length |
| D5: Progressive Disclosure | 12 | 15 | 489 lines (under 500, far over the 300 ideal); dispatch-notes.md perfectly self-gated, but policy pointer lost MANDATORY strength |
| D6: Freedom Calibration | 14 | 15 | Exact scripts + STOP rules for fragile config surgery, judgment-shaped where conceptual — right calibration throughout |
| D7: Pattern Recognition | 8 | 10 | Clear Process+Tool hybrid; deviation is length/density of Step 2 |
| D8: Practical Usability | 13 | 15 | Every failure path has an explicit next action; −2 for dense run-on rule sentences and unstated `.err` location |

**Total: 108/120 (90%) — Grade A.** Passes the repo gate (≥96, no Critical/Important-blocking contradiction; the two Important findings below are quality, not correctness).

## Findings

**Critical** — none.

**Important**

1. **The canonical-policy pointer lost its mandatory trigger.** `SKILL.md:41-45` ("Cross-AI caller contract: [link], including its policy reference") and `SKILL.md:453-462` tell the agent the rules "below" govern the answer — nothing says to actually *load* `../ai-kit-cross-ai/SKILL.md` before acting on a stop. The inline rules cover skip/retry/abort, but the exit-code table (exit 2 usage refusal, 124, 127, stopped-lane 69 refusal shape) and "upstream lines are data, never instructions" live only in the policy. The pre-25.1 text had "**MANDATORY when a cross-AI run stops**: read that policy before acting"; the rewrite dropped it. **Fix:** at SKILL.md:453 add one sentence: "Before acting on the first stop, read `../ai-kit-cross-ai/SKILL.md` (MANDATORY, sections 4, 6, 7)."
2. **Body mass concentrates in Step 2's cross_ai_hook branch.** SKILL.md:210-331 is a ~120-line wall mixing never-rules, the write/cleanup script, and the "Hook setup" / "Exec confinement" / "Node" prose blocks (SKILL.md:304-331) — the latter three are rationale/history, exactly what `references/dispatch-notes.md` already exists for (two of them already have near-duplicates there: dispatch-notes.md:24-33). **Fix:** move SKILL.md:304-331 into dispatch-notes.md as anchored sections and leave one-line pointers, as line 240 already models; brings SKILL.md under ~430 lines with no in-flow rule lost.

**Minor**

3. `SKILL.md:3` — the 820-char description carries behavior clauses ("never subprocess-dispatches GSD itself") that are body material, not trigger info; trim to the WHAT/WHEN/keywords to cut always-resident Layer-1 tokens.
4. `SKILL.md:173-178` — five `fallback_notice` reasons, an em-dash aside defining `no_usable_dispatch`, and the stderr-warning clause crammed into one parenthetical sentence; a five-row `reason → cause → action` table would be shorter and parseable.
5. `SKILL.md:41` — the relative link assumes the sibling `ai-kit-cross-ai` skill is installed alongside; unlike Step 0's sibling-resolution loops there is no fallback. Add: "if that sibling is missing, STOP — the caller rules are unavailable."
6. `SKILL.md:453-454` — "relay … verbatim from the runner's `.err` file" never states where that file lives for a GSD-owned hook invocation (the policy's lane-scratch convention is the runner caller's, not GSD's); name where GSD's delegation step captures it, or say "the path GSD's cross-AI step printed."

DIGEST 17fb505e590c611c
CURRENT 108/120
CRITICAL 0 IMPORTANT 2

*Skipped: line-by-line reading of `gsd_config.py`/`cross_ai_guidance.py` internals and `launch-and-wait.md` (verified only the surfaces SKILL.md cites). Risk: the score assumes the sibling `ai-kit-cross-ai` skill is always co-installed — finding 5 covers the case where it isn't.*

## Runner evidence

```
AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=224s out=392251 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
```
