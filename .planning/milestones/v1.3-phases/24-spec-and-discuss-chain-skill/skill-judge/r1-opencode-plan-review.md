DIGEST 59cedabbd9b0cc53
# Skill Evaluation Report: ai-kit-gsd-spec-discuss

**Verified against**: SKILL.md (220 lines), all 4 `references/` files, `scripts/decide.py` (645 lines), `scripts/phase_range.py`, gsd-core workflows in this repo (`.claude/gsd-core/`), `git ls-files`.

## Summary

- **Total**: 116/120 (97%) — Grade A
- **Pattern**: Process (~200 lines, phased workflow, checkpoints) with Navigation-style mandatory reference triggers
- **Knowledge ratio**: E:A:R ≈ 92:7:1
- **Verdict**: A dense, expert-grade orchestration skill whose NEVER list, fallbacks, and loading triggers are all real and verified; its only real defect is one internal contradiction about ladder-call batching.

## Dimension Scores

| Dimension | Score | Evidence |
|-----------|-------|----------|
| D1: Knowledge Delta | 19/20 | Nearly every line is project-expert: resolver loop (L22-26), `config-get` unset-key quirk (L57), Laya nondeterminism 0.74→0.67 (L143), SPEC-newer false positive (L44-46). Only "summaries only" restated 4× (L51, L123, L193 + analyzer-brief L43). |
| D2: Mindset + Procedures | 15/15 | "You are the decider… Laya is often low-confidence, sometimes confidently wrong" (L12-16); "own reasoning is the rung that reads the actual code and docs" (decision-table L43-44); blocking defined as in-this-run-only (L151). Procedures are all non-generic and non-obvious (commit/state replacement, L109-113). |
| D3: Anti-Pattern Quality | 15/15 | 10-item NEVER list, each with a non-obvious why. Spot-checked against gsd-core: `--assumptions` really routes to `list-phase-assumptions.md` (usage line 19), `--auto` really writes SPEC with unresolved dimensions (spec-phase L178). |
| D4: Spec Compliance | 15/15 | name 23 chars, lowercase+hyphens; description 847 chars (within 1024), has WHAT + WHEN ("Use when asked to spec and discuss several GSD phases unattended…") + KEYWORDS (jev/Laya/TypeSafe/System One, `--analyze --all --batch`) + negative scope ("Not for plan-phase or execute-phase"). |
| D5: Progressive Disclosure | 15/15 | 220-line body; MANDATORY triggers embedded at workflow points (L59, L102, L106-107); `worked-examples.md` gated to "only when a case is unclear" (L215-216); explicit "Do NOT load" (L218-219). |
| D6: Freedom Calibration | 15/15 | Low freedom exactly where fragile (exact commands, exact pre-answers, fail-closed exits), high freedom where judgment is the point (§5 quality rule, evidence-over-models). "Ask exactly one question, only when needed" (L47). |
| D7: Pattern Recognition | 9/10 | Textbook Process pattern; one file serves both unattended batch and consent-prompting flows without a scenario split. |
| D8: Practical Usability | 13/15 | Decision trees (decision-table 5-row "which answer wins"; blocking × confidence matrix), fallbacks at every failure point (no client → own reasoning, no subagent → inline, exit 2 → stop), all commands verified to exist — except the contradiction below. |

## Findings

**Critical** — none.

**Important**
1. **SKILL.md L131** — "The ladder is **one client call per phase**" is contradicted by the skill's own instructions: §1 (L70) ladders the spec-phase open items, §2 (L106) ladders the discuss questions (two runs per phase), and L119/L141 prescribe extra `--second-opinion` calls. A literal cheap executor could merge or skip runs. Reword to "one call per ladder run" or "batch a stage's items into one call".

**Minor**
2. **worked-examples.md L18-23** — Example 2 still logs "**Laya overridden**" for a case that, under today's 0.8 TypeSafe threshold, decision-table row 3 branch 4 (L29-31) resolves as "own reasoning, ledgered". The parenthetical admits the threshold change but the example models the outdated label.
3. **SKILL.md L98** — "`init phase-op`"; the actual gsd-core verb is `init.phase-op` (validate-phase.md L23). A verbatim copy of the space spelling fails.
4. **SKILL.md L51, L123, L193 + analyzer-brief L43** — "summaries only" carried in four places; the §3 restatement adds little beyond the NEVER entry and the description.
5. **scripts/__pycache__/** — untracked bytecode dir inside the skill package; ships stale bytecode if the installer symlinks the skill directory.
6. **SKILL.md L3** — description is one 847-char sentence that front-loads mechanics ("committed per phase", rung order) over triggers; within limits and dense with keywords, but near the practical parsing ceiling.

What I skipped: no live run of `decide.py detect`/`ladder` (would hit real network/backends); `edge_floor.py` and `discuss-phase-assumptions.md` internals were not read, only their entry points verified via grep. Risk: a defect inside those two would sit below this review's line of sight.

CURRENT 116/120
CRITICAL 0
IMPORTANT 1
