DIGEST f0c43a5da52a587d
# Skill Evaluation Report: ai-kit-gsd-curated-config

## Summary

- **Total Score**: 112/120 (93%) — Grade A
- **Pattern**: Tool (~316 lines, exact commands + decision tables) with Process-style approval gates
- **Knowledge Ratio**: E:A:R ≈ 85:12:3
- **Files judged**: `SKILL.md` (316 lines), `references/runner.md` (64), `references/v1-path.md` (47)
- **Verdict**: A genuinely expert-grade operational skill — near-total knowledge delta, exemplary NEVER list and mistake table, well-calibrated constraint; its one systematic liability is extreme sentence compression sitting exactly on the fragile paths.

## Dimension Scores

| Dimension | Score | Max | Notes |
|-----------|-------|-----|-------|
| D1: Knowledge Delta | 18 | 20 | Nearly everything is tool-specific expert knowledge (exit-code semantics, trusted-root merge refusal, key-family removal, permission model per flow, bare-profile partial coverage). Docked for changelog residue an agent can't act on. |
| D2: Mindset + Procedures | 14 | 15 | "Ask yourself: trusted checkout? v1-written? where does scratch live?" (line 60) plus approval-provenance discipline (lines 141–144) are true thinking patterns; full command sequences are un-derivable without the skill. Docked: the ask-yourself block is buried in a parenthetical. |
| D3: Anti-Pattern Quality | 15 | 15 | 8-item NEVER list, every entry with a non-obvious WHY; "whatever the user says about speed or trust ('just apply it')" (line 277) pre-empts social pressure — experience-grade. Doubled by the Common-mistakes table (8 rows, symptom→why→fix). |
| D4: Specification Compliance | 15 | 15 | Valid frontmatter; description has WHAT, quoted WHEN triggers ("configure .planning/config.json", "set up a cross-AI execution runner"), keywords, and negative scoping ("a faster alternative, not a replacement"). |
| D5: Progressive Disclosure | 14 | 15 | Scenario-conditional triggers done right ("read v1-path.md only when running it", line 13; "Read runner.md when… comes up", lines 226–227); both references self-describe their triggers. Docked: 316 lines > 300 ideal, and the ensure-runner row (line 269) duplicates runner.md content instead of deferring to it. |
| D6: Freedom Calibration | 15 | 15 | Fragile config writes get exact commands, verbatim `approve_with` strings, no-modify rules; judgment areas (report format, user choices) get principles. Correctly matched throughout. |
| D7: Pattern Recognition | 9 | 10 | Clean Tool pattern with well-executed Process gates (dry-run approval, fingerprint binding). One dock: Limits/Skills sections interleave runtime facts with provenance notes a canonical pattern would trim or push to references. |
| D8: Practical Usability | 12 | 15 | Common-case path (6 steps) is fully executable with fallbacks (offline→ask, refusal→printed merged list, marker→recovery steps). Gaps: parse density on failure paths, one edge case uncovered, exit-code scheme collision. |

## Findings

**Critical** — none. No contradictions found between SKILL.md, `runner.md`, and `v1-path.md` (the `--force` bypass list vs. "refuses it even with `--force`" at line 219 is a deliberate exception, and permission facts are consistent across both files).

**Important**

1. **Lines 61–67 (also 176–191, 269): fragile-path rules compressed into single multi-clause sentences with nested parentheticals.** The v1-detection "ask yourself" question buries three operational facts inside one parenthesis (lines 61–63); rollback/marker/git-status handling packs five distinct protocols into six prose bullets (176–191); the ensure-runner table cell runs ~100 words (269). Highest misparse risk sits exactly where mistakes cost most. Split into structured sub-bullets.
2. **Lines 30–36 vs 269: two exit-code schemes coexist without a scope note.** The main table maps v2 exit 1 to "apply write failed and rolled back", while `ensure-runner` exit 1 means "not ready" — an agent pattern-matching the table would report a rollback that never happened. Mitigated by "Readiness is the `ready` field" (line 269), but the table doesn't say it excludes ensure-runner.

**Minor**

1. Line 44–51: the entrypoint loop embeds `"<absolute path to THIS SKILL.md>"` inside the loop body — it cannot run verbatim; the agent must edit before executing (explained at line 53, still friction).
2. Line 61: "Was its config last written by v1?" asks a question the skill never teaches how to answer (only inferable from the `cross_ai_command` shapes at lines 62 and 195).
3. Lines 254, 257: citations to package-external evidence (`21-SMOKE-CURSOR.md`, `21-INTERACTIVE-CURSOR.md`, `(20 D-11)`) — unresolvable by any agent reading the installed skill; provenance noise in a table the skill requires relaying.
4. Line 34: "before calling it configured" is garbled phrasing that needs multiple passes.
5. Line 3: the ~135-word single-sentence description is complete but dense; the gsd-tools sentence ("Config keys are written only through…") is body content, not trigger information.
6. Line 269: the ensure-runner cell duplicates `runner.md` lines 38–46 — the reference already owns this; the table should defer.
7. Lines 71–73: the offline/no-write fallback for `inventory` is covered, but the empty-inventory / no-candidates-at-all edge of v2 `recommend` is not.

## Top 3 Improvements

1. Decompress the fragile paths (lines 61–67, 176–191, 269) into one-fact-per-line bullets — the knowledge is right, the packing is the risk.
2. Scope the exit-code table ("flow subcommands only — `ensure-runner` has its own semantics, see its row") or fold ensure-runner's codes into the table.
3. Strip or externalize in-package-unresolvable citations (`20 D-11`, `21-*.md`) from agent-facing rows.

CURRENT 112/120
CRITICAL 0
IMPORTANT 2

Skipped: deep-reading `evals/`, the Python script, and `skill_affinity.json` (out of the requested SKILL.md + references/ scope; evals are functional scenario files, not Pattern-8 doc bloat). Risk: scores for density-dependent dimensions (D1, D8) reflect my parse, not a runtime execution of the flow.
