## Comparative evaluation

Read-only, static review of both complete `SKILL.md` files, with targeted checks against supporting source. Neither version has a `references/` directory; there are no reference files to evaluate.

- **BASELINE:** `tmp/judge/baseline/skills/ai-kit-gsd-curated-config/SKILL.md` — 295 lines.
- **CURRENT:** `skills/ai-kit-gsd-curated-config/SKILL.md` — 326 lines.
- **Pattern:** Both use an appropriate **Tool/Process hybrid**.
- **Estimated Expert:Activation:Redundant ratio:** approximately **85:10:5** for both.
- **Grade:** Both **A**. CURRENT improves operational accuracy, especially degraded-success reporting and runner readiness, with a small increase in context overhead.

In the table, **B** and **C** identify line numbers in the respective files.

| Rubric dimension | Max | BASELINE | CURRENT | Evidence and rationale |
|---|---:|---:|---:|---|
| **D1: Knowledge Delta** | 20 | 18 | 18 | High-value, project-specific knowledge: runner pseudo-keys, trusted-root merging, rollback versus committed cleanup, and workstream limitations (B105–163; C107–167). CURRENT adds useful readiness semantics (C187–194), but workflow, reference-table, and troubleshooting repetition prevents full marks. |
| **D2: Mindset + Appropriate Procedures** | 15 | 15 | 15 | Trust, config provenance, scratch placement, candidate approval, dry-run, and fingerprinted follow-ups form a substantive decision framework—not generic file-editing instructions (B58–148; C58–150). |
| **D3: Anti-Pattern Quality** | 15 | 15 | 15 | Specific prohibitions explain non-obvious consequences: bypassing validation, disabling the intended runner, dropping v2 model preferences, and mishandling recovery markers (B263–276; C294–307). |
| **D4: Specification Compliance** | 15 | 15 | 15 | Valid frontmatter and name. Both descriptions explicitly cover functionality, activation scenarios, searchable terms, and the boundary with `gsd-settings`/`gsd-config` (line 3). |
| **D5: Progressive Disclosure** | 15 | 13 | 12 | Both remain below 500 lines and have clear headings and primary/secondary routing. However, every v2 invocation loads the optional v1 procedure and runner-maintenance detail. CURRENT adds more of that material and repeats readiness rules (C187–194, C259–263, C289). Conditional references would improve layering. |
| **D6: Freedom Calibration** | 15 | 14 | 14 | Fragile config operations are tightly constrained through validated commands, explicit choices, approval fingerprints, and restricted `--force`. Manual runner merging is comparatively underspecified: the post-merge check is essentially `--print-argv` (B180–189; C205–214). A short acceptance checklist would tighten this boundary. |
| **D7: Pattern Recognition** | 10 | 9 | 9 | A coherent tool-oriented workflow with checkpoints, failure branches, command examples, and troubleshooting. Interleaving the main setup flow with legacy and maintenance material slightly weakens the otherwise strong pattern. |
| **D8: Practical Usability** | 15 | 12 | 14 | BASELINE labels v1 exit 0 simply “success” (B34), although its implementation can leave execution unconfigured. CURRENT explicitly requires checking `cross_ai_command_written` and degradation reasons (C34, C259–263), and explains runner readiness. Small inconsistencies remain below. |
| **Total** | **120** | **111** | **112** | CURRENT’s reliability improvements outweigh its additional disclosure overhead. |

## CURRENT findings

**Critical:** None identified.

**Important:** None identified.

### Minor

1. **Overgeneralized edited-runner behavior — `skills/ai-kit-gsd-curated-config/SKILL.md:59–61`.**  
   The preflight says a user-edited script “gets `.new`,” but lines 190–192 correctly distinguish an edited current-template runner, which is retained without `.new`, from an edited older or foreign runner. Qualify the preflight statement or point to the detailed readiness rule.

2. **Timeout rule needs its explicit exception — `skills/ai-kit-gsd-curated-config/SKILL.md:201–203`.**  
   The live-timeout paragraph states the minimum-of-config-and-baked-cap rule without mentioning the `--outer-timeout` override correctly documented at line 178. Start it with “Without `--outer-timeout`…” so the two descriptions cannot be read as conflicting guarantees.

3. **Optional material and repeated readiness detail dilute the primary path — `skills/ai-kit-gsd-curated-config/SKILL.md:246–290`, especially line 289.**  
   The complete v1 procedure is always loaded, and the `ensure-runner` table row repeats the detailed upgrade rules already given at lines 187–194. Extract optional legacy/maintenance detail into conditionally loaded references, or shorten the table to command syntax and a section link. Missing `references/` alone is not the defect; unnecessary default loading and duplication are.

BASELINE 111/120
CURRENT 112/120
CRITICAL 0
IMPORTANT 0
