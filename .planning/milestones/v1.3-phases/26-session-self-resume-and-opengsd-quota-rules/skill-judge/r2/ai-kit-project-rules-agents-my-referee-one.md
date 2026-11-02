Judge: my-referee-one
Reviewed-sha256: 411587b8f417a8eb0de78907e5d6d76d8cefb15986499f215ef374e04749bfde
Lane: AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-one exit=0 cli_rc=0 elapsed=448s out=226551 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 100
Critical: 1
Important: 1

## Dimension scores

| Dimension | Score | Assessment |
|---|---:|---|
| D1: Knowledge Delta | 18/20 | Strong repository-specific knowledge: literal signal thresholds, symlink-aware resolution, conditional rules, and refactor hand-off constraints. Little generic instruction. |
| D2: Mindset + Procedures | 12/15 | Clear ownership and ordered confirmation/refactor/recheck workflow. Missing an initial decision between assessment and authorized remediation. |
| D3: Anti-Pattern Quality | 14/15 | Specific prohibitions with concrete reasons, particularly repeated whole-file refactors and semantic-versus-literal matching. Some repetition of earlier instructions. |
| D4: Specification Compliance | 15/15 | Valid frontmatter, conforming name, and a description covering capabilities, situations, keywords, and routing boundaries. |
| D5: Progressive Disclosure | 12/15 | Compact at 112 lines and appropriately delegates rule definitions. Long paragraphs and repeated explanations dilute otherwise useful content. |
| D6: Freedom Calibration | 9/15 | Appropriately constrains fragile matching and refactoring, but leaves target-code execution and assessment-versus-edit authorization insufficiently constrained. |
| D7: Pattern Recognition | 9/10 | Clear **Process** pattern with a resolution preflight and an A–D remediation sequence. |
| D8: Practical Usability | 11/15 | Actionable examples, evidence requirements, and verification criteria. Trust handling and assessment-only requests need explicit branches. |
| **Total** | **100/120** | **Grade B; the Critical finding blocks a production-ready verdict.** |

## Findings

1. **Critical — Target-owned code executes without an explicit trust decision.**  
   **Location:** `skills/ai-kit-project-rules-agents/SKILL.md:33–34,104`

   The prescribed commands run before any trust gate. Line 104 acknowledges that they can execute the target project's own `gsd-tools runtime-identity`. For an untrusted target, this makes an instruction-file check a path to arbitrary project-code execution. Printing the executable path on stderr provides visibility, not authorization.

   **Fix:** Before either command, require the agent to establish that executing target-owned GSD tooling is already authorized. If trust is unknown, ask first. If permission is declined, do not run these commands; report the affected checks as unverified or use a verified non-executing mode if one exists.

2. **Important — Assessment-only requests lead into automatic file remediation.**  
   **Location:** `skills/ai-kit-project-rules-agents/SKILL.md:3,58,64–66`

   The description explicitly triggers on questions such as “is my AGENTS.md missing any workflow rules,” but the workflow proceeds from findings to a whole-file refactor whenever actionable entries remain. Missing rules enter Step B automatically; only near-misses require confirmation. An informational question therefore has no defined assessment-only exit before changes.

   This finding concerns Step C’s editing workflow—not whether the Python `remediate` command itself writes files.

   **Fix:** Add an initial intent branch: assessment requests run `check` and report findings/notices, then stop. Enter Steps A–D only when the user has requested or subsequently authorized remediation.

3. **Minor — Repeated explanations consume context without adding decisions.**  
   **Location:** `skills/ai-kit-project-rules-agents/SKILL.md:58,62,66,74–89`

   The single-refactor restriction, near-miss ownership, and literal-matching requirements are explained in the workflow and then substantially repeated in the anti-pattern section.

   **Fix:** Keep the operational instructions in Steps A–D and shorten the anti-pattern bullets to their distinctive failure reason or a cross-reference.

## Repository verification

The inspected implementation supports several central claims:

- **Twenty rules, including R02’s non-workflow category:** `skills/ai-kit-project-rules-agents/ai_kit_project_rules_agents/rules.py:49–305`; R02’s category and prose signals appear at lines **63–70**.
- **Flat-list and grouped signal thresholds:** `skills/_shared/ai_kit_rules_common/classification.py:109–163`.
- **Filtering by non-empty signals rather than category, with present findings omitted:** `skills/_shared/ai_kit_rules_common/classification.py:306–360`.
- **R20’s composed summary, hardcoded-count evidence, and unverified-stack fields:** `skills/_shared/ai_kit_rules_common/classification.py:229–303`.
- **Stack-specific parallel-test clauses:** `skills/_shared/ai_kit_rules_common/tool_catalog.py:757–869`.
- **Installer symlinking:** `tools/setup.py:1268–1295,1627–1640` supports the stated symlink-install mechanism.

Not checked: CLI execution, the full check/remediate implementation, or installed `agent-md-refactor` behavior; no project commands were executed or files modified.  
Principal risk: the advertised checking workflow can execute target-owned code before an explicit trust decision.
