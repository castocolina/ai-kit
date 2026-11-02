Judge: my-referee-two
Reviewed-sha256: 411587b8f417a8eb0de78907e5d6d76d8cefb15986499f215ef374e04749bfde
Lane: AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=303s out=248163 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 116
Critical: 0
Important: 0

# Skill Evaluation Report: ai-kit-project-rules-agents

## Summary
- **Total Score**: 116/120 (96.7%)
- **Grade**: A
- **Pattern**: Process (phased wrap workflow) with Tool-style decision thresholds
- **Knowledge Ratio**: E:A:R ≈ 88:10:2 (112 lines, self-contained, no references/)
- **Verdict**: A rare case where every factual claim about the engine survived line-level verification against the code; the skill is compressed, repo-specific expert knowledge with a verification loop and real failure-prevention reasoning.

## Dimension Scores

| Dimension | Score | Max | Notes |
|-----------|-------|-----|-------|
| D1: Knowledge Delta | 19 | 20 | Nearly pure delta: engine semantics, payload shapes, install traps, hand-off constraints; two activation-level clauses at most |
| D2: Mindset + Procedures | 15 | 15 | Steps A–D are non-obvious domain ordering (confirm before invoke, re-check after, direct-edit never re-refactor) each with its why |
| D3: Anti-Pattern Quality | 15 | 15 | Five NEVERs, all specific, all reasoned from engine internals; the paraphrase trap even carries its provenance (9 false-"missing" findings) |
| D4: Specification Compliance | 15 | 15 | Valid frontmatter; description has WHAT + WHEN + keywords + sibling routing ("check everything" → rules-all) |
| D5: Progressive Disclosure | 14 | 15 | Defers rule text to `rules.py` and stack forms to the payload instead of restating; Steps A/C are dense single paragraphs |
| D6: Freedom Calibration | 15 | 15 | Low freedom exactly where the engine is brittle (verbatim blocks, thresholds, exactly-once), "phrase it naturally" where safe |
| D7: Pattern Recognition | 9 | 10 | Clean Process pattern; hybrid engine-thresholds + wrapper-phases works but interleaves two shapes |
| D8: Practical Usability | 14 | 15 | JSON shapes, decision gates, two fallbacks, edge cases (no root file, unverified stacks, post-refactor links); "CPU-share form" undefined in-text |

## Factual Claim Verification (all against the repo)

Every checkable engine claim verified, with line-precise agreement:

| SKILL.md claim | Verified at |
|---|---|
| 20 rules; R01 crit 1, signals `english only/english-only/non-negotiable`; R05 crit 3, `rtk/token killer/tool substitution` | `skills/ai-kit-project-rules-agents/ai_kit_project_rules_agents/rules.py:49-304` (R01 :51-55, R05 :106-110) |
| R18/R19/R20 are the `verbatim: true` rules | `rules.py:278,292,303` |
| Literal lowercase substring classification; flat all-or-⌈n/2⌉(n≥3); one phrase per inner list; one per installed tool | `skills/_shared/ai_kit_rules_common/classification.py:110-163,318` (`math.ceil` at :115) |
| R01/R12 summaries alone don't classify `present` | Confirmed by applying :115 to `rules.py:56-60,200-204` (R01 → near_miss 1/3; R12 → missing 0/3) |
| `check` → `{"workflow", "links"}`; `remediate` → `{"remediate","blocked","notices"}`, drops `links` | `ai_kit_project_rules_agents/cli.py:196,209-217`; `skills/_shared/ai_kit_rules_common/remediation.py:152` |
| `blocked` always empty here | `remediation.py:125-149` (blocked only from STRUCTURAL_KINDS; this `check` emits only `workflow`/`links`) |
| `auto_apply`: missing→true, near_miss→false; most-critical-first order | `remediation.py:118,151` |
| `notices` = unverified rules with `reason` (R18/R19 opengsd-unverified) | `remediation.py:96-107`; `classification.py:48-53,63-74` |
| `check_workflow_rules` filters by non-empty `signals`, not `category`; R02 category "makefile" still prose-checked | `rule_checker.py:19-22`; `classification.py:312-323`; `rules.py:64,67-70` |
| AGENTS.md beats CLAUDE.md; empty text → always-on rules `missing`; one hop, first 20 distinct targets, fences ignored, anchors stripped, anchor-only skipped, same-repo only, images included | `cli.py:22-26,29-63,82-127,130-158` |
| R20 `hardcoded_counts` (literal count or share > 40%), any line left keeps `near_miss`; `unverified_stacks` clause pre-marked | `classification.py:23,209-226,255-262,31-34,243-247` |
| gsd probe only when `.planning/` exists; runs `runtime-identity`; path on stderr | `cli.py:169-175`; `tests/test_ai_kit_rules_common.py:2407` |
| `_shared` needed beside symlink-resolved dir; copy-install raises `ImportError`; fix = `python3 tools/setup.py` | `ai_kit_project_rules_agents/__init__.py:11-26`; `tools/setup.py:1269-1295` (symlink into checkout) |
| `PARALLEL_TEST_FORMS` composes R20 per stack | `skills/_shared/ai_kit_rules_common/tool_catalog.py:757` |
| `workflow` "lists only rules that are not present" (Step D gate) | `classification.py:358-360` |
| `ai-kit-project-rules-all` routing target exists with that role | `skills/ai-kit-project-rules-all/SKILL.md:3` |

**Verification limit**: `/agent-md-refactor` is external to this repo (installed at `~/.claude/skills/agent-md-refactor/SKILL.md`). Its five phase names, "no CLI/importable interface", and Phase 1 confirmation gate (SKILL.md:58,62,66) are corroborated only by in-repo planning docs recording a direct read of that file (`.planning/milestones/v1.1-phases/06-agents-md-rules-checker-skill/06-02-PLAN.md:33,309`), not by my own inspection. Not a finding; noted for sourcing honesty.

## Findings

1. **[minor] SKILL.md:58** — "only when `remediate`'s payload is non-empty does it proceed toward `/agent-md-refactor`" and Step B's gate (list empty → stop) are two different gates: a notices-only run has a non-empty payload but an empty Step B list. Step B resolves the behavior correctly, so no wrong action results. **Fix**: say "only when the Step B list (auto-apply plus confirmed near-misses) is non-empty" once, at line 58.

2. **[minor] SKILL.md:62** — "rewriting each of those lines to the CPU-share form" references a form the document never defines or points to; the executor must infer it from R20's composed payload (whose `summary` embeds the per-stack clauses, `classification.py:295`). **Fix**: add "(the form shown in the entry's own `summary` clauses, e.g. the `AI_KIT_TEST_CPU_SHARE` wording)".

3. **[minor] SKILL.md:17-21** — the resolve loop's first candidate is a literal placeholder; an executor that runs the block verbatim silently falls through to an installed copy that may be on another branch — the exact case line 28 warns about. The follow-up paragraph does instruct substitution. **Fix**: prefix the block with `# replace <absolute path to THIS SKILL.md> before running`.

4. **[minor] SKILL.md:68** — no stated behavior when `agent-md-refactor` is installed nowhere (the entrypoint loop's "stop and report" precedent at line 28 is not restated for the wrapped skill). **Fix**: one clause — "if no candidate resolves, stop and report that the wrapped skill is not installed".

5. **[minor] SKILL.md:37** — "the first 20 distinct targets" slightly over-specifies: the budget also counts relative targets that parse but resolve outside the repo and are then skipped (`cli.py:103-110` adds to `seen` before the containment check). Practically invisible; noted for exactness only. **Fix**: none needed, or "the first 20 distinct link targets".

## Top 3 Improvements
1. Unify the two "proceed?" gates (finding 1) so a notices-only run can't be misread.
2. Define or point at "the CPU-share form" (finding 2).
3. Add the placeholder guard and the wrapped-skill-absent fallback (findings 3-4).

Skipped: no live CLI execution (read-only mandate) — all claims verified by source inspection; `/agent-md-refactor`'s internals taken from in-repo corroborating docs, not read directly.
