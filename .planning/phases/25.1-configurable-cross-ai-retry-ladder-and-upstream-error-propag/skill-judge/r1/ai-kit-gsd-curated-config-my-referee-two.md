Judge: my-referee-two
Reviewed-sha256: 06342f11d7c111752e2d83b32739eb769bfc5512454bb78f264b0226391aa4a3
Lane: AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=324s out=403374 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 110
Critical: 0
Important: 3

# Skill Evaluation Report: ai-kit-gsd-curated-config

## Summary
- **Total Score**: 110/120 (92%) — Grade A
- **Pattern**: Tool (decision tables + exact commands, low freedom) with a Navigation layer to `references/`
- **Knowledge Ratio**: E:A:R ≈ 88:10:2 — essentially pure project-expert knowledge (exit-code semantics, refusal lattices, template-version archaeology, trust model)
- **Verdict**: A dense, highly accurate operator's manual for a fragile config-writing pipeline; the 25.1 rewrite (one runtime per call, template 8, canonical-policy pointer) is described correctly in every claim I could check against code, with three Important gaps left.

**Phase 25.1 verification (all checked against source, all accurate):** `--runtime` pseudo-key and `plan-set script:cross-ai.runtime` match `plan_edit.py:26,196+`; "template 8 = first with `--runtime` and retry config" matches `_READY_TEMPLATE = 8` (`cross_ai_script.py`) and `template=8` (`cross-ai.mjs:2`); "one runtime per call, never replaced" matches `script_artifact()`/`runner_config()` (`cross_ai.py`, `cross_ai_script.py`); `--prefer` alias-first-entry matches the template help (`cross-ai.mjs:24`); pointer `../ai-kit-cross-ai/SKILL.md` (SKILL.md:218) and `../../ai-kit-cross-ai/SKILL.md` (runner.md:47) both resolve; "never switch" NEVER (SKILL.md:369-371) mirrors the canonical §8; the extraArgs review-allowlist claim (runner.md:80-81) matches `reviewExtras: ['--skill']` (`cross-ai.mjs:1382`); no stale `subprocess-quota-policy.md` pointers remain.

## Dimension Scores

| Dimension | Score | Max | Notes |
|---|---|---|---|
| D1: Knowledge Delta | 19 | 20 | Nearly every line is unknowable-without-the-repo; trivial redundancy only |
| D2: Mindset + Procedures | 14 | 15 | "Ask yourself: trusted checkout? where do scratch files live?" + ordering-critical pipeline |
| D3: Anti-Pattern Quality | 14 | 15 | 9-item NEVER list with mechanisms; Common-mistakes table with cause+fix |
| D4: Spec Compliance / Description | 15 | 15 | WHAT + WHEN + trigger phrases + positioning, all in the description |
| D5: Progressive Disclosure | 14 | 15 | Explicit read-when triggers + "Do NOT load" guard; 396-line body slightly heavy |
| D6: Freedom Calibration | 14 | 15 | Exact commands and approval gating where fragile; one calibration hole (finding 2) |
| D7: Pattern Recognition | 9 | 10 | Clean Tool pattern with navigation layer |
| D8: Practical Usability | 11 | 15 | Strong tables/failure states; four literal-following gaps below |

## Findings

**Critical — none.**

**Important**

1. **The verbatim-report duties omit the new `cross-ai: upstream` lines.** The canonical contract this skill defers to requires printing "the `cross-ai: report`, the `cross-ai: upstream` lines and the `AIKIT-XAI` line" on a stop (`skills/ai-kit-cross-ai/SKILL.md:119-120`, `references/subprocess-quota-policy.md:129,161`), but this skill enumerates only two line families — `SKILL.md:206` ("report the `cross-ai: report` and `AIKIT-XAI` lines only"), `SKILL.md:238-241`, and the Reporting rule `SKILL.md:395-396`. An agent that follows the local enumeration instead of chasing the pointer will drop the redacted error body that 25.1 explicitly passes through. **Fix:** in all three spots, change the enumeration to "the `cross-ai: report`, any `cross-ai: upstream` lines and the `AIKIT-XAI` line".
2. **`references/runner.md:42-44` instructs hand-editing the project config, contradicting the global NEVER at `SKILL.md:356-357`** ("Never hand-write `.planning/config.json` or `plan.json`"). New in 25.1: retry tuning says "hand-edit these sources because `config-set` refuses the project key," with no carve-out signalled. An agent will either refuse a legitimate owner tune or believe blanket hand-edits sanctioned. **Fix:** scope the NEVER ("…except `workflow.cross_ai_retry`, which `config-set` refuses — see runner.md") and have runner.md name the exception explicitly.
3. **The Copilot runtime is silently unconfigurable and unrecorded.** The bundled runner supports copilot (`cross-ai.mjs:1433`) and detection v7 knows it (`ai-kit-spec-review/ai_kit_spec/detection.py:118`), but `RUNNER_IDS = ("pi", "cursor", "opencode", "codex")` (`ai_kit_gsd_curated_config/cross_ai.py:33`) excludes it, `plan-set script:cross-ai.runtime copilot` and `_validate_runtime` refuse it, and the Limits table (`SKILL.md:324-333`) — the skill's own mechanism for exactly this — has no copilot row. **Fix:** add a Limits row ("copilot runtime: runner rows unverified; not a curated-config target until live-validated") so the refusal has a documented reason.

**Minor**

4. **Ambiguous parenthetical next to a prescribed command.** `SKILL.md:142-143` "(`plan-unset` is refused while execution is on)" sits directly above "To drop a menu runner, `plan-unset script:cross-ai.model.<id>`" (`SKILL.md:144-145`); the refusals are actually key-specific (`plan_edit.py:343-361`). Also "every runner in `artifacts[0].choices`" is a stale plural — choices now holds at most the runtime (`plan_io.py` `_choice_row_problem`). **Fix:** "(`plan-unset workflow.cross_ai_command` is refused while execution is on)".
5. **Stale no-target message omits codex.** `cross_ai.py:59` `NO_TARGET_TEXT = "no installed cross-AI target (pi, cursor, opencode)"` — codex is a RUNNER_IDS member. **Fix:** derive the names from `RUNNER_IDS`.
6. **`--prefer` alias never explained here.** The NEVER warns against "reordering `prefer`" (`SKILL.md:369-370`) but no doc in this skill says `--prefer` survives as an alias whose first entry runs (only the template help, `cross-ai.mjs:24`, does). **Fix:** one clause in runner.md's Template flags.
7. **Unsourced flat claim.** `runner.md:44` "`config-set` refuses the project key" is stated as verified fact with no test or note pinning how it's known — per this repo's own certainty rule it should carry its sourcing or an unverified flag.

Not checked: the four `evals/*.md` files' content, gsd-tools' actual refusal behavior (external dependency), and a live run of any command (read-only brief). Risk: scores assume the ai-kit-cross-ai policy file is final; if it changes, finding 1's cross-reference moves.

DIGEST 06342f11d7c11175
CURRENT 110/120
CRITICAL 0 IMPORTANT 3

## Runner evidence

```
AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=324s out=403374 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
```
