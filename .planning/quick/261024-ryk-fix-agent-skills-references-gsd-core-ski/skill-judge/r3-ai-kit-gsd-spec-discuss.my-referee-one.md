# Skill evaluation: ai-kit-gsd-spec-discuss

**110/120 — A (91.7%).** Strong **Process/Tool** pattern with approximately **85:10:5 Expert:Activation:Redundant** content.

Reviewed the complete `SKILL.md` (280 lines), all five references (372 lines), all three scripts (1,042 lines), and the requested diff since `5b4ec21`.

| Dimension | Score | Assessment |
|---|---:|---|
| D1: Knowledge Delta | 18/20 | Substantial GSD-specific knowledge; slight repetition across workflow rules and references. |
| D2: Mindset + Procedures | 14/15 | Evidence-first decisions, locked scope, and precise workflow overrides are well integrated. |
| D3: Anti-Pattern Quality | 15/15 | Specific prohibitions explain non-obvious failures and their consequences. |
| D4: Specification Compliance | 15/15 | Valid metadata; description clearly identifies capabilities, triggers, and exclusions. |
| D5: Progressive Disclosure | 14/15 | Explicit mandatory and conditional loading; one promised example is missing. |
| D6: Freedom Calibration | 14/15 | Appropriate judgment for decisions and strict controls around consent, artifacts, and dispatch. |
| D7: Pattern Recognition | 9/10 | Coherent process with useful tool-oriented references. |
| D8: Practical Usability | 11/15 | Broad fallback coverage, but workstream propagation is incomplete and list parsing has an edge-case failure. |
| **Total** | **110/120** | **Excellent overall; one important correctness gap.** |

### Changes since `5b4ec21`

The targeted changes are sound on static inspection:

- The global-skill symlink/trust explanation matches the installed gsd-core implementation at `.claude/gsd-core/bin/lib/init.cjs:3717–3726`.
- Setup checks both JSON diagnostics and stderr, covering `configured_empty` warnings and persona fallback masking unresolved entries.
- The analyzer prohibition is explicit even with `jev-fast-decision` wired (`references/analyzer-brief.md:47–48`), and the advisor receives an equivalent spawn-prompt restriction (`SKILL.md:153–158`). Backend calls remain the orchestrator’s responsibility.

### Findings

Paths below are relative to `skills/ai-kit-gsd-spec-discuss/`.

1. **Important — Workstream support does not reach local artifact paths.**  
   **Evidence:** `SKILL.md:39–40` propagates `--ws` to GSD queries and workflows, but the range commands at `SKILL.md:48–52` omit `--phases-root`. `scripts/phase_range.py:153` therefore always defaults to `.planning/phases`. Additionally, `SKILL.md:162–163` explicitly commits `.planning/STATE.md`.  
   **Impact:** A workstream-scoped roadmap can be compared against root-level phase files, producing incorrect proposals; the final state commit can target the wrong file.  
   **Fix:** Resolve the effective planning directory once, including implicit workstream selection. Pass its phases directory through the existing `--phases-root` option and commit its resolved STATE path. Add coverage with different root/workstream phase states.

2. **Minor — Whitespace in an explicit phase list passes validation but fails selection.**  
   **Evidence:** `scripts/phase_range.py:112–115` validates stripped list elements, while `scripts/phase_range.py:87–89` passes the original elements to `phase_key()`, whose strict regex rejects whitespace (`:34–36`).  
   **Impact:** `--list "17, 18"` is rejected despite passing selector validation.  
   **Fix:** Apply `part.strip()` when building the requested-phase set, consistently with validation; add one spaced-list regression case.

3. **Minor — Forced-column examples omit a promised branch.**  
   **Evidence:** `references/decision-table.md:26–31` defines the forced-remote contradiction branch and promises one example per branch. `references/worked-examples.md:62–71` supplies four cases but none for that branch.  
   **Fix:** Add one example where a forced remote contradicts verified evidence, showing the evidence re-check and ledgered own-reasoning outcome.

No tests, backend probes, or workflows were run; no credential files were read or files changed. Runtime behavior remains unverified.

DIGEST e503d04af5ca6b78
CURRENT 110/120
CRITICAL 0 IMPORTANT 1
