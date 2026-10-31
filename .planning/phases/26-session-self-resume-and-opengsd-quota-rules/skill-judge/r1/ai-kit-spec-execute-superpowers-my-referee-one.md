Judge: my-referee-one
Reviewed-sha256: 14d9f06f85826c766e6865b7161e3eae5fc6cc20d6938a87ddcad79e9073f35a
Lane: AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-one exit=0 cli_rc=0 elapsed=899s out=364817 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 94
Critical: 1
Important: 4

## Dimension scores

| Dimension | Score | Evidence and assessment |
|---|---:|---|
| **D1: Knowledge Delta** | **17/20** | Strong domain-specific knowledge: permanent versus wave exclusions, pinned injections, report preservation, and escalation anchors. Repeated explanations reduce information density. |
| **D2: Mindset + Appropriate Procedures** | **13/15** | Transfers useful decision principles alongside concrete procedures, especially the exclusion-classification question at `SKILL.md:143–152`. Capability escalation needs a sounder prerequisite. |
| **D3: Anti-Pattern Quality** | **15/15** | Specific, consequential prohibitions with explanations: losing exclusion reasons, confusing runtime IDs with ladder keys, overwriting reports, and switching after failure (`SKILL.md:22–43`). |
| **D4: Specification Compliance** | **15/15** | Valid frontmatter and name. The description specifies functionality, activation conditions, plan-path keywords, and the excluded execution workflow (`SKILL.md:1–4`). |
| **D5: Progressive Disclosure** | **10/15** | References have explicit mandatory or conditional loading triggers. However, the 521-line main file still contains substantial recovery machinery and repeated rationale. |
| **D6: Freedom Calibration** | **10/15** | Appropriately restrictive about trust, evidence, and failed dispatches. Less reliable where preference order substitutes for capability evidence and where failed-run restoration is incomplete. |
| **D7: Pattern Recognition** | **8/10** | Recognizable **Tool/Process hybrid**, with mode branches, exact commands, and checkpoints. The oversized dispatch section makes the main control flow harder to follow. |
| **D8: Practical Usability** | **6/15** | Covers many failure cases, but the status parser, invisible shell results, and incomplete resume handling prevent dependable execution as written. |
| **Total** | **94/120** | **Grade C — substantial expert content, but execution defects need correction.** |

**Estimated knowledge ratio:** Expert 80% / Activation 15% / Redundant 5%.

**Package structure:** `SKILL.md`: 521 lines; `references/design-notes.md`: 139; `references/escalation.md`: 105; `references/state-management.md`: 146. Total: 911 lines.

## Findings

1. **Critical — The status parser can route an explicitly blocked result into the DONE handler.**  
   **Location:** `skills/ai-kit-spec-execute-superpowers/SKILL.md:350–356`

   The command extracts every occurrence of any status word and takes the last one, rather than parsing a status declaration. For example:

   ```text
   BLOCKED: checks failed; task is not DONE
   ```

   The exact extraction command returns `DONE`. This was confirmed with an in-memory shell check that changed no files. Similarly, explanatory text containing `BLOCKED` can override a genuine completion declaration. Reading stdout rather than the report is correct, but stdout is still prose unless its structure is constrained.

   **Fix:** Require a standalone status token or an explicitly prefixed status field, then parse that exact structure. Reject missing, conflicting, or multiple declarations as `BLOCKED`; do not choose the last incidental word.

2. **Important — Classification and status assignments produce no observable result across fresh shell calls.**  
   **Location:** `skills/ai-kit-spec-execute-superpowers/SKILL.md:343–345,350–353`

   Both blocks assign shell variables using command substitution but never print them. Under the skill’s explicit fresh-shell convention (`SKILL.md:93–94`), the variables disappear after the call, and the agent receives neither the classification nor the parsed status. The next instruction nevertheless requires branching on those values.

   This affects the ordinary successful path, not merely an unusual recovery case.

   **Fix:** Print `CLASSIFICATION` and `STATUS` explicitly, as the surrounding blocks already do for other variables, or perform their complete branching within the same shell call.

3. **Important — A preferred ladder position does not establish a more-capable model.**  
   **Location:** `skills/ai-kit-spec-execute-superpowers/references/escalation.md:20–25,71–75`

   The reference acknowledges that `policy.ladder` is ordered by preference and that no machine-readable capability tier exists, but then treats every candidate above the anchor as a valid capability bump.

   A valid preference ladder could put a cheaper or faster model above a stronger model. In that configuration, the prescribed “bump” dispatches a weaker implementer while claiming to satisfy the stronger-model requirement. Calling the ordering a proxy does not supply the missing guarantee.

   **Fix:** Require an explicitly confirmed capability ordering before using ladder position this way. Without that confirmation, ask the owner to identify the stronger candidate, as the reference already does for an unknown anchor at lines 56–61.

4. **Important — Non-quota failures lack the pinned resume handoff promised by the state contract.**  
   **Location:** `skills/ai-kit-spec-execute-superpowers/SKILL.md:449–455`  
   **Related package location:** `skills/ai-kit-spec-execute-superpowers/references/state-management.md:61–67,118–138`

   The quota branch explicitly persists `injection_json`. The `real_error` branch only relays evidence and stops; it does not create an equivalent pinned record or give a complete same-pair resume procedure.

   This leaves authentication failures, timeouts, crashes, and other failed dispatches without a durable record distinguishing them from a pre-dispatch stop. That distinction matters because the state reference permits Step 2 selection when no pinned injection exists.

   **Repository check:** The named caller contract also forbids changing harness, provider, or model after failure: `skills/ai-kit-cross-ai/SKILL.md:168–172`. Its same-lane hard-tier instruction appears at lines 137–144. The quota instructions agree with that contract; the non-quota handoff is incomplete.

   **Fix:** Before every failed-dispatch stop, preserve the injection and sufficient artifact references to resume the same task and pair. Define an explicit restoration path for those failures, rather than relying on retained conversation context.

5. **Important — Resume-state filenames collide between different plans in the same workspace.**  
   **Location:** `skills/ai-kit-spec-execute-superpowers/references/state-management.md:82–83,123–124`

   `PROJECT_KEY` hashes only `$CWD`, and the filename adds only `$TASK_N`. Two different plans executed in the same workspace therefore use the same state path for, for example, task 1.

   Writing a later plan’s state can replace an earlier plan’s outstanding recovery record. Although the JSON contains `plan_path`, the filename does not distinguish plans, and the restore instructions do not require checking the stored plan against the intended one.

   **Fix:** Include the canonical plan identity in the state-path key, and validate `framework`, `plan_path`, and `task_index` before restoring a record.

6. **Minor — The main file carries too much detailed recovery material despite having good reference triggers.**  
   **Location:** `skills/ai-kit-spec-execute-superpowers/SKILL.md:20,360–448,460–500`

   The NEVER index explicitly repeats rules explained again in their branches, while much of the dispatch and wake recovery protocol remains in the main file. Several explanations also recur in `references/design-notes.md`.

   This is not a missing-reference problem: the loading triggers are good. It is a density problem that makes the central mode-selection and dispatch flow harder to scan.

   **Fix:** Keep the short safety index and routing decisions in `SKILL.md`; move the detailed quota-wake recipe behind one mandatory reference trigger and trim duplicated rationale.

Not checked: live dispatch or scheduler behavior; the downstream superpowers skills/templates were not located in this repository. No files were changed.  
Risk: the current status parser can select the wrong handler, and failed-run restoration does not consistently preserve the pinned pair.
