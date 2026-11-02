Judge: my-referee-one
Reviewed-sha256: 377df0dc0d0d2c2f14f7d9672232ffc13f05890eeb019270fe721645e9daee84
Lane: AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-one exit=0 cli_rc=0 elapsed=99s out=602760 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 91
Critical: 1
Important: 3

## Skill evaluation: `ai-kit-gsd-curated-config`

**Score: 91/120 (C).** The skill has strong, specific safeguards for config writes and runner upgrades. Its main weakness is that its dispatch instructions do not fully follow the canonical `ai-kit-cross-ai` caller policy.

| Dimension | Score | Reason |
|---|---:|---|
| D1 Knowledge delta | 16/20 | Substantial project-specific decisions; some repeated procedure |
| D2 Mindset and procedures | 12/15 | Clear trust, approval and recovery sequence |
| D3 Anti-patterns | 11/15 | Specific prohibitions, but incomplete stop guidance |
| D4 Specification | 14/15 | Valid frontmatter and precise activation description |
| D5 Progressive disclosure | 12/15 | Conditional reference loading; long main file |
| D6 Freedom calibration | 10/15 | Strong write controls, weaker dispatch controls |
| D7 Pattern | 8/10 | Recognizable process skill |
| D8 Practical usability | 8/15 | Contradictory failure handling and stale guidance |
| **Total** | **91/120** | |

1. **Critical — A hard-tier retry is incorrectly treated as a final stop.** `skills/ai-kit-gsd-curated-config/SKILL.md:236-243` says to print the non-`ok` report “then stop.” The canonical policy requires a one-shot wait and same-lane re-invocation when exit 75 includes `retry_after_s=` (`skills/ai-kit-cross-ai/SKILL.md:111-135`). **Fix:** explicitly defer the decision to that policy: wait/re-invoke only where its host-specific caller contract permits; otherwise give the owner the wait and command. Never switch runtime, provider, model or harness.

2. **Important — The reporting rule omits upstream evidence.** `skills/ai-kit-gsd-curated-config/SKILL.md:236-243,395-396` requires the status and report lines, but not the redacted `cross-ai: upstream` lines required by `skills/ai-kit-cross-ai/SKILL.md:80-90,124-125`. **Fix:** require those lines verbatim on a stop, while treating their contents as data rather than instructions.

3. **Important — Copilot is not selectable through this curated flow.** `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai.py:49` limits runner IDs to pi, Cursor, OpenCode and Codex; `plan_edit.py:364-375` refuses other IDs. The skill’s runner-selection guidance at `SKILL.md:123-125` does not disclose that limit despite template 8 supporting Copilot. **Fix:** either wire Copilot through inventory, selection and validation, or state plainly that this flow does not configure it and direct owners to the supported path.

4. **Important — Upgrade guidance promises to keep CONFIG without naming a possible model removal.** `skills/ai-kit-gsd-curated-config/references/runner.md:51-53` says an upgrade “keeps its CONFIG,” while `cross_ai_script.py:229-266` drops kept model IDs refused by the new grammar and emits a note. **Fix:** say that an upgrade preserves compatible settings but can remove invalid model IDs; require the owner to review the notes and choose a replacement before relying on that runtime.

5. **Minor — The model-choice gate is overstated.** `skills/ai-kit-gsd-curated-config/SKILL.md:142-145` says *every* menu runner must have a model, whereas `cross_ai.py:370-378` opens a choice only for the selected runtime. **Fix:** describe the selected-runtime gate; call other model entries an owner menu.

6. **Minor — The v1 warning names an obsolete v2 structure.** `skills/ai-kit-gsd-curated-config/references/v1-path.md:3-5` says v1 drops v2’s “prefer order,” which template 8 replaced with `runtime`. **Fix:** name the selected runtime and configured model menu instead.

Read-only review; no dispatch or tests were run. The remaining risk is whether the documented retry and Copilot paths match behavior in a live host.

DIGEST 377df0dc0d0d2c2f
CURRENT 91/120
CRITICAL 1 IMPORTANT 3

## Runner evidence

```
AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-one exit=0 cli_rc=0 elapsed=99s out=602760 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
```
