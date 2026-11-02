Judge: my-referee-two
Reviewed-sha256: 16918292c2cacdeb40792fbd1e44247c55668883d1e836e7c0521ad496ba6582
Lane: AIKIT-XAI status=ok cli=pi model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=310s out=3655 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 102
Critical: 0
Important: 1

# Skill Evaluation Report: ai-kit-project-rules-all

## Summary
- **Total Score**: 102/120 (85%)
- **Grade**: B
- **Pattern**: Tool contract with Navigation routing to six siblings
- **Knowledge Ratio**: E:A:R ≈ 75:15:10
- **Verdict**: An accurate orchestrator contract an agent can run, with one merge-path contradiction that can drop a domain's findings while still calling the audit complete.

## Dimension Scores

| Dimension | Score | Max | Notes |
|-----------|-------|-----|-------|
| D1: Knowledge Delta | 17 | 20 | Resolution walk, import gate, 30s isolation vs host kill, four-key merge, and the links-only-on-check gap are not model knowledge. |
| D2: Mindset + Procedures | 13 | 15 | Trust gate, fan-out, hand-off vs report-only, and the second `check` are procedures this host would not invent. |
| D3: Anti-Pattern Quality | 13 | 15 | Six NEVER rules, each with a non-obvious reason. |
| D4: Specification Compliance | 14 | 15 | Valid `name`. Description has WHAT, WHEN, negative routing, and trigger phrases. |
| D5: Progressive Disclosure | 12 | 15 | 238 lines, self-contained; Wrap A-D correctly not restated. The two resolve loops repeat each other. |
| D6: Freedom Calibration | 14 | 15 | Low freedom on paths, timeout, env, and which key to read; judgment left on offer vs edit. |
| D7: Pattern Recognition | 8 | 10 | Clear Tool-plus-Navigation pattern; the five act paths are a list, not a branch table. |
| D8: Practical Usability | 11 | 15 | Timeout, exits, and empty output are actionable. One failed-vs-merged rule contradicts the code. |

Checked against `skills/ai-kit-project-rules-all/ai_kit_project_rules_all/{cli,dispatch,aggregate}.py`, `_shared/ai_kit_rules_common/remediation.py`, and `skills/ai-kit-project-rules-agents/`. Timeout text, usage and exit 0/2, domain order, `hand_off` only when `kind == "workflow"`, notice shape, the arch example's `id`/`issue`/`criticality` 2, and the R01 signals/summary match. No structural sibling shells out, so the probe-skip claim holds.

## Findings

1. **Important** — `skills/ai-kit-project-rules-all/SKILL.md:120`. "A domain here never appears in `remediate` or `blocked` too" contradicts `aggregate.py:41-48`: a payload that has `remediate` is merged and is not copied into `failed`, even when it also has `status: failed`. The previous sentence says that object "is merged as a real result." An agent that follows line 120 reports the domain as failed and drops findings that were actually merged, or treats a dual-shaped payload as unchecked. Fix: say a `remediate`-bearing object is absent from `failed` and lives only in the merged lists; only objects without that key are `failed`.

2. **Minor** — `skills/ai-kit-project-rules-all/SKILL.md:13`. "Field values untouched" is immediately qualified by the `hand_off` addition, so it does not by itself mislead, but the two clauses disagree. Fix: "passed through except `aggregate()` sets `hand_off` on `workflow` entries."

3. **Minor** — `skills/ai-kit-project-rules-all/SKILL.md:166`. A `failed` entry whose error is `entrypoint not found for '<sibling>'` is attributed to the walk in "Resolve the entrypoint," but that walk is for this skill. Sibling misses come from `dispatch.resolve_entrypoint` (`dispatch.py:39-83`), which also requires `_shared/ai_kit_rules_common` for the agents sibling only. Fix: point at the dispatch walk and mention the agents import gate.

4. **Minor** — `skills/ai-kit-project-rules-all/SKILL.md:28-64` and `66-87`. Two near-copies of the same candidate loop. One loop plus "rerun with the agents name and the `_shared` test" would save tokens.
