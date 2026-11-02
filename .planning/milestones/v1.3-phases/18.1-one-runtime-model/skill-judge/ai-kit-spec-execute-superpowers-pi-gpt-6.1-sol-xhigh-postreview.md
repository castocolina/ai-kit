## Assessment

Read both `SKILL.md` files and all three references in each version. This is a **read-only document review**, not runtime verification.

Both use a **Process/Tool hybrid**: a constrained dispatch workflow with conditional references. CURRENT improves materially through persistent escalation anchors, cleaner resume-state handling, and explicit cross-host routing and verification caveats.

### Scores

| Rubric dimension | BASELINE | CURRENT | Rationale |
|---|---:|---:|---|
| **D1: Knowledge Delta** | **16/20** | **18/20** | Both contain substantial expert knowledge: exclusion provenance, report preservation, quota recovery, and capability floors. Baseline spends more tokens repeating regression history; Current compresses that material, though some contract duplication remains. |
| **D2: Mindset + Appropriate Procedures** | **13/15** | **14/15** | Both teach the crucial permanent-versus-wave exclusion distinction. Current additionally distinguishes the stuck implementer from a fresh resolution, with a concrete counterexample in `references/escalation.md:29–37`. The shared round-start procedure could be positioned more clearly. |
| **D3: Anti-Pattern Quality** | **15/15** | **15/15** | The NEVER index provides specific prohibitions with non-obvious consequences: permanent quota lockout, ineffective exclusions, lost evidence, and futile scheduling. These are operational failure modes, not generic cautions. |
| **D4: Specification Compliance** | **15/15** | **15/15** | Both have valid frontmatter, compliant names, and descriptions covering WHAT, WHEN, searchable integration terms, and the explicitly unsupported harness. |
| **D5: Progressive Disclosure** | **13/15** | **14/15** | Both bodies remain below 500 lines and mandate reference loading at relevant decisions. Current shortens the mandatory references and reserves design notes for optional rationale. Repeated custom-entry explanations prevent maximum efficiency. |
| **D6: Freedom Calibration** | **10/15** | **14/15** | Baseline leaves fragile escalation state tied to a freshly resolved key. Current persists a round-start anchor, preserves it across retries/resumes, and requires user judgment when the anchor is unknown (`references/escalation.md:55–60`). Shared native/external bookkeeping still requires some inference. |
| **D7: Pattern Recognition** | **8/10** | **9/10** | Both have a recognizable resolution → injection → harness-owned review structure. Current’s references are more focused and easier to navigate; a few repeated or misplaced instructions remain. |
| **D8: Practical Usability** | **9/15** | **13/15** | Baseline has a consequential escalation-resume flaw. Current fixes that case and improves state capture, reason filtering, and failure guidance. The path-template and native-path presentation issues below remain. |
| **Total** | **99/120** | **112/120** | **Baseline: B. Current: A.** |

**Baseline’s principal weakness:** `tmp/judge/baseline/skills/ai-kit-spec-execute-superpowers/references/escalation.md:87–96` recomputes the floor from the freshly resolved `$INJECTION_KEY`. With ladder `A > B`, if B gets stuck and round 4 waits for A’s quota, a resume that selects recovered A then excludes A itself. CURRENT’s persisted `$ESCALATION_ANCHOR_KEY` fixes this reasoning error.

## CURRENT findings

No Critical or Important findings identified in this document review.

1. **Minor — Path substitution is implicit, and an unsubstituted placeholder silently selects the wrong directory.**  
   **Location:** `skills/ai-kit-spec-execute-superpowers/SKILL.md:49–57`  
   The block is presented as an executable command, but `<absolute path to THIS SKILL.md>` requires an unstated substitution. Taken literally, `dirname` returns `.`, which passes the directory check and prevents the fallbacks from running. Explicitly instruct substitution before execution, and check for the expected shim file rather than merely an existing directory.

2. **Minor — Universal round-start bookkeeping is nested inside the external-dispatch instructions.**  
   **Location:** `skills/ai-kit-spec-execute-superpowers/SKILL.md:242–244`; compare `references/escalation.md:8–13`  
   Incrementing `$FIX_ROUND` and capturing `$ESCALATION_ANCHOR_KEY` also matter for native execution on non-Claude hosts, but the instruction appears under the `external_cli` prompt-composition branch. Move this shared transition before the native/external split so native callers need not infer its applicability.

3. **Minor — The NEVER index overgeneralizes non-quota failures as permanent.**  
   **Location:** `skills/ai-kit-spec-execute-superpowers/SKILL.md:39–40`  
   “No wait fixes a permanent failure” does not accurately summarize every `any_quota_recoverable == False` case: lines 167–174 explicitly acknowledge that capacity failures may clear later. The scheduling decision is correct; change the explanation to “only quota qualifies for automatic recovery.”

4. **Minor — The custom-entry “exception” repeats an exclusion rather than describing a reachable execution path.**  
   **Location:** `skills/ai-kit-spec-execute-superpowers/SKILL.md:323–325`  
   Custom entries never execute here, so calling them “the one exception” to subprocess supervision is unnecessarily confusing. Their rejection is already covered at lines 124–126 and explained in `references/design-notes.md:28–32`. Remove this repeated paragraph or state simply that all executable subprocess candidates use the supervised runner.

BASELINE 99/120
CURRENT 112/120
CRITICAL 0
IMPORTANT 0
