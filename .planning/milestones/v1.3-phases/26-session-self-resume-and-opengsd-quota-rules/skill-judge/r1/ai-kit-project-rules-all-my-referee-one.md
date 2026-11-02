Judge: my-referee-one
Reviewed-sha256: a0d23c0d4767515f02cdee66fc698a9a5a7f81ecc093893a8f36966bc4321852
Lane: AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-one exit=0 cli_rc=0 elapsed=233s out=155956 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 82
Critical: 0
Important: 3

## Dimension scores

| Dimension | Score | Assessment |
|---|---:|---|
| D1: Knowledge Delta | 14/20 | Valuable repository-specific contracts, but classification ownership, ordering, and report-only behavior are repeated extensively. |
| D2: Mindset + Procedures | 12/15 | Strong principles around preserving classifications and isolating failures; the hand-off procedure loses necessary safeguards. |
| D3: Anti-Pattern Quality | 13/15 | Concrete prohibitions with useful consequences, particularly around domain isolation and deterministic ordering. |
| D4: Specification Compliance | 4/15 | Clear activation language and a valid name, but the description is not valid YAML as written. |
| D5: Progressive Disclosure | 10/15 | Manageable at 221 lines, but repetitive; the consequential sibling hand-off lacks a mandatory loading instruction. |
| D6: Freedom Calibration | 11/15 | Appropriately constrains aggregation and non-workflow remediation, but leaves an execution trust boundary undisclosed. |
| D7: Pattern Recognition | 9/10 | Clear Tool pattern with Navigation elements for sibling ownership. |
| D8: Practical Usability | 9/15 | Useful commands, schemas, examples, and failure explanations; metadata and hand-off defects prevent dependable use. |
| **Total** | **82/120** | **Grade D — significant corrections needed.** |

Estimated knowledge ratio: **Expert 65% / Activation 15% / Redundant 20%**.

Static repository inspection supports the documented domain order, sequential dispatch, 30-second timeout, and sibling `remediate` invocation: `skills/ai-kit-project-rules-all/ai_kit_project_rules_all/dispatch.py:25-40,103-110,142-146`. Both public subcommands use the same implementation and serialization: `skills/ai-kit-project-rules-all/ai_kit_project_rules_all/cli.py:22-34,42-49`.

## Findings

1. **Important — Invalid YAML description**  
   **Package:** `skills/ai-kit-project-rules-all/SKILL.md:3`

   The unquoted description contains `question: this`. A colon followed by a space cannot appear there in a YAML plain scalar. The quotation marks around individual phrases do not quote the entire value. A conforming frontmatter parser can reject the skill before its otherwise strong activation description becomes available.

   **Fix:** Use a folded scalar, such as `description: >-`, with the description indented underneath it.

2. **Important — The abbreviated hand-off omits correctness-critical instructions without requiring the owning document to be loaded**  
   **Package:** `skills/ai-kit-project-rules-all/SKILL.md:135-151`, especially **145-147**

   Step C directs the agent to pass only the ordered `summary` strings into the refactor. The referenced sibling’s actual procedure additionally requires `verbatim: true` entries to be inserted unchanged, and its anti-patterns explain why signal wording must survive:
   - `skills/ai-kit-project-rules-agents/SKILL.md:61`
   - `skills/ai-kit-project-rules-agents/SKILL.md:67-76`

   The sibling also conditions proceeding toward refactoring on a nonempty remediation payload (`:53`). The aggregate skill’s abbreviated sequence lacks that guard and provides no explicit instruction to load the complete owning procedure. Following this document alone can therefore produce a refactor that fails the checker again or runs unnecessarily.

   **Fix:** Require reading and following the sibling’s complete **Wrap mechanism** and relevant anti-patterns before any hand-off. Preserve `verbatim` handling explicitly, and skip refactoring when the final approved list is empty.

3. **Important — The check commands omit the target-code execution trust boundary**  
   **Package:** `skills/ai-kit-project-rules-all/SKILL.md:59-88`

   These commands are not necessarily limited to static inspection of the target repository. The named agents sibling documents that `check` and `remediate` execute the target project’s own GSD `runtime-identity` tool when `.planning/` exists:
   - `skills/ai-kit-project-rules-agents/SKILL.md:96-98`

   The aggregate dispatcher invokes that sibling’s `remediate` and captures its stderr (`skills/ai-kit-project-rules-all/ai_kit_project_rules_all/dispatch.py:103-110`). On success, it returns parsed stdout without forwarding stderr (`:119-132`), so the sibling’s documented stderr disclosure does not reach the aggregate caller.

   **Fix:** Add a trust note before the run commands explaining that target-local code may execute. Require authorization for that execution, otherwise stop. Do not rely on the sibling’s stderr notice as disclosure to the user.

4. **Minor — Repetition dilutes the operational instructions**  
   **Package:** `skills/ai-kit-project-rules-all/SKILL.md:27-30,83-88,124-131,160-164,192-200,211-213`

   Classification ownership and aggregation responsibilities are restated several times. The minimum limit-count discussion and deletion-detector commentary describe documentation maintenance rather than helping an agent perform the check.

   **Fix:** State each invariant once, retain actionable limits, and remove the count-enforcement and keyword-test commentary. This would improve knowledge density without adding reference files.

**Verification limits:** Static inspection only; no files were changed and no checker commands were executed. Runtime behavior and historical “real run” claims remain unverified.
