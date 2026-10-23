# CURRENT skill evaluation

Reviewed `skills/ai-kit-gsd-curated-config/SKILL.md` completely (313 lines), plus `references/runner.md` and `references/v1-path.md` (approximately 50 lines each). Supporting implementation was inspected read-only to check factual claims; no commands or tests were executed.

**Grade: A — 95%.** Strong domain-specific guidance, especially around approval boundaries, rollback, runner permissions, and degraded outcomes. Remaining issues are minor reference inaccuracies and repetition.

**Pattern:** Tool + Process.  
**Estimated knowledge ratio:** Expert 85% / Activation 10% / Redundant 5%.

Paths below are relative to `skills/ai-kit-gsd-curated-config/`.

## Dimension scores

| Dimension | Score | Evidence and assessment |
|---|---:|---|
| **D1: Knowledge Delta** | **18/20** | High-value specifics include managed-family removals (`SKILL.md:124–132`), committed-versus-rolled-back failures (`174–180`), and skill trust-root behavior (`228–244`). No basic tutorials. Repeated approval instructions reduce token efficiency; consolidate as described below. |
| **D2: Mindset + Appropriate Procedures** | **15/15** | The preflight questions about trust, v1 migration, and scratch placement (`60–67`) establish a useful decision framework. The inventory → recommendation → choices → dry run → apply → follow-up sequence supplies non-obvious operational ordering. |
| **D3: Anti-Pattern Quality** | **15/15** | The NEVER list (`268–287`) explains concrete consequences: bypassed validation, execution of project JavaScript, lost v2 runner configuration, and inactive `.new` files. These are domain-specific landmines rather than generic warnings. |
| **D4: Specification Compliance** | **15/15** | Valid frontmatter and matching lowercase, hyphenated name. The description (`3`) identifies functionality, explicit invocation scenarios, searchable filenames, and boundaries relative to `gsd-settings`/`gsd-config`. |
| **D5: Progressive Disclosure** | **14/15** | The main file stays below 500 lines. “Only when running” v1 (`12–13`) and scenario-triggered runner loading (`221–224`) prevent orphan references. Repeated recovery and approval guidance slightly weakens default-context economy. |
| **D6: Freedom Calibration** | **15/15** | Fragile writes receive appropriately strict controls: explicit choices, complete dry-run rows, a separate approval turn (`97–143`), and unchanged fingerprint-bound follow-up commands (`157–165`). Full-permission execution is disclosed rather than described as sandboxed (`197–208`). |
| **D7: Pattern Recognition** | **10/10** | A coherent Tool/Process hybrid: entrypoint resolution, ordered checkpoints, parameterized commands, exit-code interpretation, recovery rules, and conditional references. The pattern fits configuration mutation well. |
| **D8: Practical Usability** | **12/15** | Strong common-case and failure coverage, including cleanup warnings, work-tree uncertainty, and degraded v1 execution. Two runner-reference claims do not fully match the bundled implementation; correct them as detailed below. |

## Findings

### Critical
None found.

### Important
None found.

### Minor

1. **Runner readiness is incorrectly equated with template currency.**  
   **Lines:** `references/runner.md:33–34`; `SKILL.md:265`.

   Both say an edited older-template runner receives `.new` and is **not ready**. However, `ai_kit_gsd_curated_config/cross_ai_script.py:31,299–303` uses a readiness floor of template **3**, while the bundled template is **4**. An edited template-3 runner can therefore receive `.new` while remaining `ready: true`.

   **Fix:** Distinguish “upgrade available” from “incompatible runner.” Keep the existing instruction to trust the returned `ready` field, and remove the blanket prediction that every older template is unready. This is minor because the authoritative-JSON instruction already provides the correct operational rule.

2. **The live-timeout lookup omits supported project scoping and fallback behavior.**  
   **Lines:** `references/runner.md:38–40`.

   The reference describes only root and workstream config paths. The bundled runner also uses `GSD_PROJECT`, falls back to the root key when a workstream lacks its own value, and defaults to 300 seconds when no valid value is available (`skills/ai-kit-spec-review/references/cross-ai.mjs:442–463`). Troubleshooting from the reference alone can therefore direct an agent to the wrong config or explain the effective timeout incorrectly.

   **Fix:** Document the scoped lookup ladder, root inheritance condition, default, and CONFIG cap together.

3. **The detailed dry-run approval rule is repeated beyond useful reinforcement.**  
   **Lines:** `SKILL.md:134–143`, `272–275`, `300–301`.

   The workflow, NEVER list, and two adjacent common-mistake rows repeat the separate-turn/full-dotted-key requirement. The rule is valuable, but its repeated elaboration adds default-loaded tokens without introducing another decision.

   **Fix:** Keep the complete procedure in step 4, retain a short NEVER reminder, and combine the two common-mistake rows into one concise reference to step 4.

CURRENT 114/120
CRITICAL 0
IMPORTANT 0
