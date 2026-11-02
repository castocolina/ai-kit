# Skill evaluation: ai-kit-gsd-spec-discuss

**109/120 — A (90.8%).** Strong Process/Tool hybrid with substantial GSD-specific knowledge, clear safety boundaries, and effective conditional references. Estimated Expert:Activation:Redundant ratio: **85:12:3**.

Reviewed the complete 286-line `SKILL.md`, all five references, all three Python scripts, and the diff since `5b4ec21`.

| Dimension | Score | Assessment |
|---|---:|---|
| D1: Knowledge Delta | 18/20 | Valuable resolver, workflow, consent, and decision-ladder knowledge; some repeated rules. |
| D2: Mindset + Procedures | 14/15 | Evidence-first judgment complements precise GSD procedures. |
| D3: Anti-Pattern Quality | 15/15 | Specific prohibitions explain consequential, non-obvious failure modes. |
| D4: Specification Compliance | 15/15 | Valid frontmatter; description clearly covers capabilities, triggers, and exclusions. |
| D5: Progressive Disclosure | 14/15 | References have explicit loading conditions; core remains relatively dense. |
| D6: Freedom Calibration | 13/15 | Good separation of mechanical constraints and judgment; commit-state handling is incomplete. |
| D7: Pattern Recognition | 9/10 | Coherent phased process with tool-oriented safeguards. |
| D8: Practical Usability | 11/15 | Generally actionable, but two supported paths lack complete handling. |
| **Total** | **109/120** | |

### Findings

Paths below are relative to `skills/ai-kit-gsd-spec-discuss/`.

1. **Important — Forced-local/high-remote case falls through the decision table.**  
   **Evidence:** `references/decision-table.md:17–21` explicitly defines forced columns as neither high nor low, but row 4 at **38–40** accepts only a local rung that is “low, errored or not called.” Consequently, a forced local answer plus a high remote answer matches none of rows 1–5 for an otherwise ordinary item. `references/worked-examples.md:60–62` nevertheless says row 4 applies. A read-only synthetic check confirmed that `decide.py` produces precisely this combination.  
   **Fix:** Add **“forced”** to row 4’s local-rung conditions, and include forced-only outcomes in row 5’s explanatory parenthesis. Add a regression check covering the table’s forced-local/high-remote path, not merely propagation of the `forced` field.

2. **Important — The committed-SPEC invariant does not handle `commit_docs: false`.**  
   **Evidence:** `SKILL.md:115` says the underlying workflow commits the SPEC; **240–241** requires that SPEC to be committed before analysis. However, the actual checkout’s `.claude/gsd-core/workflows/spec-phase.md:517–520` explicitly permits the commit command to return `skipped` when `commit_docs` is false. The skill supplies no branch for this supported outcome.  
   **Fix:** Inspect the SPEC commit result before starting analysis. If skipped, preserve the user’s configuration and stop with an explanation that this skill requires a committed SPEC; do not silently override `commit_docs`. Alternatively, explicitly support uncommitted operation and revise every committed-input/resumption guarantee consistently.

### Focused change assessment

The new wiring diagnostics accurately reflect the checkout’s GSD implementation: escaping global symlinks require trusted-root coverage, acceptance notes are not warnings, empty-entry warnings can be stderr-only, and persona fallback can obscure unresolved entries behind `reason: resolved`. See `.claude/gsd-core/bin/lib/init.cjs:3717–3726,3785–3867`.

The analyzer and advisor no-jev restrictions are explicit and correctly placed in their spawn instructions (`references/analyzer-brief.md:47–48`; `SKILL.md:158–165`). They preserve orchestrator ownership of consent, ladder calls, and logging.

No files were changed or credential files read. Full tests and live backend calls were not run; runtime prompt compliance remains unverified.

DIGEST 6b2fa1326df86c35
CURRENT 109/120
CRITICAL 0 IMPORTANT 2
