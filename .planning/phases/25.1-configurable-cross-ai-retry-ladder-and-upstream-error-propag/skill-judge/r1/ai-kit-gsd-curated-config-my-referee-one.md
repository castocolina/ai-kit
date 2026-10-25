Judge: my-referee-one
Reviewed-sha256: 06342f11d7c111752e2d83b32739eb769bfc5512454bb78f264b0226391aa4a3
Lane: AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-one exit=0 cli_rc=0 elapsed=142s out=584816 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 106
Critical: 0
Important: 2

## Skill evaluation: ai-kit-gsd-curated-config

**106/120 — B (88.3%).** Strong Process/Tool pattern with substantial repository-specific knowledge (estimated Expert/Activation/Redundant ratio: **85/10/5**). Reviewed the complete 396-line `SKILL.md`, both reference files, the entrypoint, the requested diff, and relevant implementation/policy sources.

The canonical `ai-kit-cross-ai` links resolve correctly. One-runtime selection and the prohibition on autonomous harness/provider/model switching are explicit. Delegating error-catalog, overlay, model-grammar, tool-profile and Copilot details to the canonical policy is appropriate; duplicating those contracts here would invite drift.

| Dimension | Score | Assessment |
|---|---:|---|
| D1: Knowledge Delta | 18/20 | Valuable trust, migration and recovery knowledge; some repeated runner warnings. |
| D2: Mindset + Procedures | 14/15 | Strong approval checkpoints and uncertainty handling; retry-config exception is unresolved. |
| D3: Anti-Pattern Quality | 14/15 | Specific, reasoned prohibitions against destructive migration and unauthorized switching. |
| D4: Specification Compliance | 15/15 | Valid metadata; description clearly states capabilities, scenarios and trigger phrases. |
| D5: Progressive Disclosure | 14/15 | Conditional reference loading and explicit “Do NOT load”; some runner detail remains duplicated. |
| D6: Freedom Calibration | 12/15 | Appropriately restrictive writes, but conflicting stop/config instructions leave fragile decisions ambiguous. |
| D7: Pattern Recognition | 9/10 | Coherent Process/Tool structure; command reference partially repeats the workflow. |
| D8: Practical Usability | 10/15 | Main flow is actionable; caller reporting and selected-versus-menu instructions need correction. |
| **Total** | **106/120** | **Good, with two Important findings.** |

### Findings

1. **Important — Local report-and-stop instructions conflict with the canonical caller contract.**  
   **Evidence:** `skills/ai-kit-gsd-curated-config/SKILL.md:236-243` requires the status/report lines and says “then stop”; `:395-396` repeats only those two evidence lines. However, `:218-219` delegates hard-tier handling to the canonical skill, whose `skills/ai-kit-cross-ai/SKILL.md:115-130` distinguishes same-lane hard-tier re-entry from terminal stops and requires upstream evidence in the terminal notice. The local instructions can suppress both the redacted upstream body/fields and the required wait information.  
   **Fix:** Make the canonical result-handling contract controlling. Explicitly include available `cross-ai: upstream` lines verbatim as untrusted data, and distinguish a pending `retry_after_s` from terminal `stopped=hard-waits`/`cap`. Clarify that this setup skill reports a GSD-owned dispatch rather than independently scheduling its retry.

2. **Important — Retry tuning instructs a forbidden project-config write.**  
   **Evidence:** `skills/ai-kit-gsd-curated-config/references/runner.md:41-44` says to hand-edit the project or user retry source because `config-set` refuses the project key. This contradicts `skills/ai-kit-gsd-curated-config/SKILL.md:15-17` and the unconditional prohibition at `:356-357` against hand-writing `.planning/config.json`.  
   **Fix:** Direct this skill’s tuning workflow to the supported user file and canonical configuration policy. Explicitly leave manual project-block edits owner-managed, outside this skill’s config-write flow.

3. **Minor — Model-unset guidance conflates the selected runtime with inactive menu entries.**  
   **Evidence:** `skills/ai-kit-gsd-curated-config/SKILL.md:123-126` says unsetting a runner model reopens a choice, while `:144-145` says it drops a menu runner. The implementation distinguishes these: `skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/plan_edit.py:303-308` reopens only the selected runtime’s choice and removes an inactive entry.  
   **Fix:** State both cases explicitly. Dropping the selected runtime requires selecting another runtime or disabling execution; unsetting its model only reopens its choice.

4. **Minor — The v1 migration warning retains obsolete v2 selection terminology.**  
   **Evidence:** `skills/ai-kit-gsd-curated-config/references/v1-path.md:3-5` says v1 drops the “prefer order” v2 chose, although template-8 plans now use `config.runtime` plus model-menu maps (`skills/ai-kit-gsd-curated-config/ai_kit_gsd_curated_config/cross_ai.py:370-384`).  
   **Fix:** Replace “prefer order” with “selected runtime and per-runtime model menu.”

No files changed or credentials read; live dispatches and write-producing tests were not run. Runtime behavior remains statically assessed.

DIGEST 06342f11d7c11175
CURRENT 106/120
CRITICAL 0 IMPORTANT 2

## Runner evidence

```
AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-one exit=0 cli_rc=0 elapsed=142s out=584816 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
```
