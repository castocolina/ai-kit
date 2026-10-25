# Skill Evaluation Report: ai-kit-gsd-spec-discuss

## Summary
- **Total Score**: 111/120 (92%) — **Grade A**
- **Pattern**: Process (§0–§7 phased workflow) with Tool-pattern decision tables and exact low-freedom scripts
- **Knowledge Ratio**: E:A:R ≈ 90:8:2
- **Verdict**: A dense, verified expert brain for chaining GSD spec/discuss phases with the jev ladder — nearly every paragraph is gsd-core/jev internals Claude cannot know; the 5b4ec21..HEAD changes are live-verified correct against the checkout's gsd-core.

## Dimension Scores

| Dimension | Score | Max | Notes |
|-----------|-------|-----|-------|
| D1: Knowledge Delta | 19 | 20 | `--assumptions` routing trap, `--auto`→plan-phase chain, ladder item schema + rejection codes, forced-fallback semantics, SPEC-newer false positives, Laya non-determinism with real numbers, `CLAUDE_ENV_FILE` alias persistence, agent-skills symlink-escape skip. Mindset paragraph is the only activation-level content. |
| D2: Mindset + Procedures | 14 | 15 | "You are the decider; Laya… sometimes confidently wrong" is a real thinking pattern; blocking × unresolved stop rule; procedures (one client call per step, edge-floor gate ordering, commit-replacement rules) are domain-only knowledge. |
| D3: Anti-Pattern Quality | 14 | 15 | Nine NEVERs, each specific with a non-obvious reason ("the run looks complete and produces no CONTEXT"; "a crash leaves them flipped"). Landmine documentation, not vague warnings. |
| D4: Spec Compliance | 15 | 15 | Description has WHAT, WHEN (quoted trigger phrases), KEYWORDS (jev/Laya/TypeSafe/System One/GSD), exclusions, and degradation mode. Exemplary. |
| D5: Progressive Disclosure | 14 | 15 | 272-line SKILL.md; four references with MANDATORY triggers embedded at the exact workflow step; conditional blocks; explicit "Do NOT load" section. Trailing reference list slightly duplicates the inline triggers. |
| D6: Freedom Calibration | 13 | 15 | Fragile ops (consent, secrets, engine gate) are low-freedom exact scripts, fail-closed; judgment is a ranked decision table. The auto-path pre-answer rules (SKILL.md:136-144) are tied to the literal `--analyze --all --batch` wording with no stated variant if the user's intent differs. |
| D7: Pattern Recognition | 9 | 10 | Clean Process pattern, ~272 lines, checkpoints and mandatory gates; hybrid with Tool tables is intentional and appropriate. |
| D8: Practical Usability | 13 | 15 | Decision table + worked examples per branch; fail-closed exit codes documented; edge cases (SPEC-newer disambiguation, host gaps, no-backend degradation). Three minor seams below. |

## Findings

1. **Minor** — SKILL.md:49-51: the new wiring-check loop invokes `gsd_run` literally, but step 2 (SKILL.md:36-38) says the alias survives across shell calls only with `CLAUDE_ENV_FILE` and instructs using the resolved literal path in later calls, like `S`. On hosts without that mechanism the block as written fails. **Fix**: introduce a resolved-path variable in step 2 (e.g. `$GSD`) and use it in the loop.

2. **Minor** — SKILL.md:153: "(SKL-04)" cites an ai-kit `.planning` phase-research artifact id (18-RESEARCH.md:373) that an agent executing this skill in any other project cannot resolve. **Fix**: drop the parenthetical or inline the one-line reason; the analyzer-brief.md:47-48 wording already carries the rule without it.

3. **Minor** — SKILL.md:53-55: the two named warning causes omit gsd-core's other realistic skip warning, `Skipping unsafe path "...": not confined to the project directory` (`.claude/gsd-core/bin/lib/init.cjs:3740`), leaving an operator who hits it without a cause mapping. **Fix**: add it as a third bullet, or phrase the two as "the expected causes".

4. **Minor** — SKILL.md:46-55: the wiring check never states the success condition; a reader can mistake an empty loop output for a broken check. **Fix**: one clause — "no WARNING lines means every entry resolved; continue".

## Diff verification (5b4ec21..HEAD, commit ce6984e)

All three behavioral claims live-verified against this checkout's gsd-core: skipped global skills warn "failed path check (symlink escape?)" unless `agent_skills_security.trusted_global_roots` accepts them (init.cjs:3715-3726); the query exits 0 and only drops the entry from the prompt (buildAgentSkillsBlock / cmdAgentSkills, init.cjs:3648-3775); `references/gsd-run-resolver.md` exists in the install; the two checked agent types match the ones the two discuss workflows actually spawn; `ai-kit-gsd-curated-config` exists and itself refuses plans wiring entries gsd-core would skip. The stderr-grep redirection (`2>&1 >/dev/null`) is correct. The analyzer-never-calls-jev policy change is consistent with decide.py's consent architecture.

Skipped: no test suite run (read-only judge); scoring rests on source review only — the four Minors are cosmetic, none undermines a run.

DIGEST 4c33bda55ff6ed04
CURRENT 111/120
CRITICAL 0 IMPORTANT 0
