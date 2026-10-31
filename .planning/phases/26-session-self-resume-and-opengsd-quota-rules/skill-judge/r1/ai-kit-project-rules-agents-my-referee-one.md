Judge: my-referee-one
Reviewed-sha256: 06ef499ae59c57f92188a9ec3fb8005423d08d836e3a9264f0f476c404604eeb
Lane: AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-one exit=0 cli_rc=0 elapsed=296s out=317262 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 94
Critical: 0
Important: 4

## Dimension scores

Reviewed file: `skills/ai-kit-project-rules-agents/SKILL.md` — 106 lines.

| Dimension | Score | Rationale |
|---|---:|---|
| D1: Knowledge Delta | 17/20 | Strong repository-specific knowledge: rule conditions, literal signals, near-miss evidence, and delegation constraints. Some hand-off instructions are repeated. |
| D2: Mindset + Appropriate Procedures | 12/15 | Explains why confirmation belongs in the wrapper and why repeated whole-file refactors are unsafe. The procedure lacks a final acceptance checkpoint. |
| D3: Anti-Pattern Quality | 11/15 | Specific, reasoned prohibitions, but the signal-matching guidance oversimplifies the actual rule schema. |
| D4: Specification Compliance | 15/15 | Valid frontmatter, compliant name, and a description with clear functionality, activation scenarios, and searchable keywords. |
| D5: Progressive Disclosure | 13/15 | Compact body that avoids reproducing the ruleset. However, it does not explicitly require loading the signal definitions before constructing insertions. |
| D6: Freedom Calibration | 9/15 | Appropriate constraints on confirmations and verbatim entries, but inadequate gating when every proposed insertion is declined. |
| D7: Pattern Recognition | 9/10 | Clear Process/Tool hybrid: resolve, inspect, confirm, assemble, delegate. Exit and verification checkpoints need completion. |
| D8: Practical Usability | 8/15 | Actionable main path, with material gaps in installation resolution, grouped-signal handling, and post-edit verification. |
| **Total** | **94/120** | **Grade C — useful specialist guidance, but correctness and workflow gaps remain.** |

Approximate knowledge ratio: **Expert 80% / Activation 10% / Redundant 10%**.

## Findings

1. **Important — The final empty-list case still triggers a whole-file refactor.**  
   **Location:** `skills/ai-kit-project-rules-agents/SKILL.md:59–61`

   Step B removes declined near-misses, but Step C unconditionally invokes `/agent-md-refactor`. If the only findings are near-misses and the user declines all of them, the accepted remediation list is empty, yet the workflow still performs a structural refactor. The earlier gate at line 53 does not explicitly re-evaluate the list after confirmation.

   **Fix:** After Step B, stop when the final list is empty and report the declined entries inline. Invoke the refactor only when at least one accepted remediation remains.

2. **Important — The blanket ≥50%-of-signals guidance does not cover required signal groups.**  
   **Location:** `skills/ai-kit-project-rules-agents/SKILL.md:67–74`

   The anti-pattern presents a general threshold without distinguishing flat signals from independently required clauses or tool-scoped groups. The repository explicitly documents these different shapes in `skills/ai-kit-project-rules-agents/ai_kit_project_rules_agents/rules.py:4–11`. R04 requires separate review, execution, and path-portability clauses (`rules.py:94–98`); R06 scopes requirements to individual installed tools (`rules.py:122–127`). Covering half the groups is not equivalent to satisfying every required clause.

   **Fix:** State the shape-specific requirements: use the applicable threshold for flat tuples, satisfy every required clause group, and satisfy each active tool-scoped group. Explicitly load the relevant rule’s signal definition before drafting its insertion.

3. **Important — Entrypoint resolution stops at existence, even for layouts the document says cannot run.**  
   **Location:** `skills/ai-kit-project-rules-agents/SKILL.md:17–28`

   The loop stops at the first existing script. Line 28 then says several candidate layouts lack required shared dependencies. For example, an existing plugin copy can be selected before a usable Claude symlink; the resolver never continues to that usable candidate.

   The categorical assertion that particular host directories necessarily contain copy-installs is also too strong. Dependency availability depends on the actual layout and symlink target, not the directory’s name. The shared imports are visible in `skills/ai-kit-project-rules-agents/ai_kit_project_rules_agents/rules.py:19–29`; the installer’s configurable Claude directory and symlink behavior appear in `tools/setup.py:117` and `tools/setup.py:1268–1295`.

   **Fix:** Resolve symlinks and validate the required shared layout before accepting a candidate. Continue past unusable candidates, or stop with an actionable dependency error. Describe copy-install limitations conditionally rather than assigning them categorically to host paths.

4. **Important — The workflow never verifies that the completed refactor satisfies the accepted rules.**  
   **Location:** `skills/ai-kit-project-rules-agents/SKILL.md:61`

   Step C requires paraphrasing most summaries and delegates their placement to another skill, but specifies no subsequent `check`. This is particularly consequential because lines 67–76 acknowledge that semantically correct refactoring previously produced false missing results.

   The summaries alone are not guaranteed to supply the document’s stated signal threshold. For example, R01’s summary contains `English-only`, but its three signals are `english only`, `english-only`, and `non-negotiable` (`skills/ai-kit-project-rules-agents/ai_kit_project_rules_agents/rules.py:55–59`). Merely inserting that summary would supply only one of those signals.

   **Fix:** After the single refactor invocation, rerun `check` and verify each accepted rule is reported present, using `include_present` where available or checking that it no longer appears as missing/near-miss. Repair residual signal gaps directly without invoking `/agent-md-refactor` again, and report unresolved results rather than implying completion.

**Verification limits:** Read-only source inspection only; no CLI execution or installed-skill inspection. The documented JSON outputs, runtime-identity behavior, and external refactor implementation remain independently unverified.
