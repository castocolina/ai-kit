## Assessment

**CURRENT is stronger overall, but still has three Important findings.** It fixes BASELINE’s invalid YAML description, improves cross-call value capture, and replaces an installed-path-dependent hook with the project runner.

This was a **read-only, static review** of both complete skills and their references. Relevant implementation files were inspected to check command contracts; no scripts were executed.

Paths used below:
- **B:** `tmp/judge/baseline/skills/ai-kit-spec-execute-gsd/SKILL.md`
- **C:** `skills/ai-kit-spec-execute-gsd/SKILL.md`

Both follow a **Process/Tool hybrid** pattern. BASELINE has 296 body-file lines and a 46-line reference; CURRENT has 385 and 66 respectively. Estimated Expert:Activation:Redundant content ratios are approximately **85:10:5** and **80:12:8**.

## Scores by rubric dimension

| Dimension | Max | BASELINE | CURRENT | Evidence and rationale |
|---|---:|---:|---:|---|
| **D1: Knowledge Delta** | 20 | 17 | 17 | Both provide substantial repository-specific knowledge: ownership-aware config writes, native versus cross-AI dispatch, trust boundaries, and GSD’s unquoted hook expansion. Repeated rationale and implementation narration dilute otherwise strong content. |
| **D2: Mindset + Appropriate Procedures** | 15 | 14 | 14 | B:152–162 and C:166–176 teach useful invariants: resolve afresh, distinguish workflow wiring from per-plan activation, and remove stale hooks. Procedures explain the non-obvious adapter/GSD boundary rather than generic coding steps. |
| **D3: Anti-Pattern Quality** | 15 | 14 | 14 | B:8–31 and C:8–34 contain specific prohibitions with consequences: no subprocess-dispatching GSD, no direct config edits, no implicit trust, and no raw vendor hook. Some warnings are repeated rather than sharpened. |
| **D4: Specification Compliance** | 15 | 5 | 15 | **B:3 is invalid YAML:** the unquoted description contains the colon-space sequence in `` `cross_ai: true` ``; Markdown backticks do not quote YAML. C:3 quotes the description correctly and supplies clear WHAT, WHEN, and trigger keywords. |
| **D5: Progressive Disclosure** | 15 | 13 | 12 | Both keep references explicitly optional and link rationale at relevant steps. CURRENT retains more duplicated setup/confinement explanation in the main file and reference. Neither is an indiscriminate dump, but CURRENT could layer more efficiently. |
| **D6: Freedom Calibration** | 15 | 11 | 11 | Exact shims, ownership checks, and configuration contracts appropriately constrain fragile operations. BASELINE leaves whitespace-sensitive hooks insufficiently guarded; CURRENT improves this but still under-constrains cleanup failures and phase-file publication. |
| **D7: Pattern Recognition** | 10 | 9 | 9 | Both have a coherent resolve → configure → prepare → handoff structure. Long branch-specific shell blocks make navigation less efficient than an ideal Process/Tool skill. |
| **D8: Practical Usability** | 15 | 8 | 9 | BASELINE needs `RESULT_JSON` again at B:191 without printing it for the documented fresh-shell boundary, and leaves tooling guidance stale after its first append. CURRENT fixes value capture and refreshes guidance, but its recovery and mutation examples still contain the defects below. |
| **Total** | **120** | **91** | **101** | **BASELINE: C, 75.8%. CURRENT: B, 84.2%.** |

## CURRENT findings

### Critical

None identified.

### Important

1. **Successful cleanup is incorrectly classified as failure.**  
   **Lines:** `skills/ai-kit-spec-execute-gsd/SKILL.md:223` and `:253`  
   Both recovery branches use `grep -q 'revert_failed'`. The real cleanup command always serializes that field, including `"revert_failed": []` on success. Consequently, missing guidance or a not-ready runner causes an unconditional STOP even after successful cleanup, contradicting the promised native fallback.  
   **Fix:** Check the exit status and parse the JSON field’s contents; an empty list is not a failure.

2. **The ordinary mode-transition cleanup does not gate handoff on success.**  
   **Lines:** `skills/ai-kit-spec-execute-gsd/SKILL.md:304–312`  
   This command has no explicit handling for exit 1 or failed rollback. The global exit-2 rule does not cover that case. Following the workflow can therefore reach Step 3 while a previous adapter-owned cross-AI hook remains active—the exact stale-dispatch condition this cleanup is meant to prevent.  
   **Fix:** Capture and validate the cleanup result, and explicitly STOP on any unsuccessful cleanup before invoking GSD.

3. **Phase-file writes are non-atomic, while failures are reported as leaving the file untouched.**  
   **Lines:** `skills/ai-kit-spec-execute-gsd/SKILL.md:336–347`, especially `:344–346`  
   `Path.write_text()` truncates the actual phase file before completing the replacement. An interrupted or failed write can leave partial planning content. The catch-all shell handler then incorrectly attributes the failure to a missing end marker and says “phase file untouched.”  
   **Fix:** Validate markers before writing, publish through a sibling temporary file plus atomic replacement, and distinguish validation errors from read/write failures.

### Minor

1. **Existing BASELINE guidance blocks are not migrated or detected.**  
   **Lines:** `skills/ai-kit-spec-execute-gsd/SKILL.md:334–344`  
   The replacement recognizes only the new `:start`/`:end` markers. BASELINE’s marker at B:256 remains intact, so upgrading an already-used phase file preserves old guidance alongside the refreshed block.  
   **Fix:** Detect the legacy marker and provide a safe migration or explicit cleanup instruction.

2. **Background explanation is duplicated across disclosure layers.**  
   **Lines:** `skills/ai-kit-spec-execute-gsd/SKILL.md:271–284`; `skills/ai-kit-spec-execute-gsd/references/dispatch-notes.md:24–33,47–60`  
   Runner setup and confinement details substantially repeat across both files. Keep execution-critical constraints in the body; move extended rationale to the reference with a conditional loading instruction.

BASELINE 91/120
CURRENT 101/120
CRITICAL 0
IMPORTANT 3
