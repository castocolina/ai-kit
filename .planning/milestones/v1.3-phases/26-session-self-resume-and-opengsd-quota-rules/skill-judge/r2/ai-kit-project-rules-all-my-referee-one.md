Judge: my-referee-one
Reviewed-sha256: 65138f8de4f47675096c37ffb13c17825c9e169b25e92c6aa10238a6bf2dbd82
Lane: AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-one exit=0 cli_rc=0 elapsed=276s out=166929 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 101
Critical: 0
Important: 2

## Dimension scores

| Dimension | Score | Evidence and assessment |
|---|---:|---|
| **D1: Knowledge Delta** | **18/20** | Valuable repository-specific knowledge: sibling ownership, field preservation, install resolution, and reporting semantics. Some repeated boundaries add little after their first explanation. |
| **D2: Mindset + Procedures** | **13/15** | Strong separation of classification, orchestration, and remediation ownership. The resolve → run → interpret workflow is actionable, but the audit-versus-edit decision is ambiguous. |
| **D3: Anti-Pattern Quality** | **13/15** | Specific warnings address misleading clean reports, inappropriate auto-application, and repeated refactoring. The unconditional failure-isolation instruction exceeds the implementation’s protection. |
| **D4: Specification Compliance** | **15/15** | Valid frontmatter and name. The description provides capabilities, explicit whole-repository triggers, and useful single-domain exclusions. |
| **D5: Progressive Disclosure** | **12/15** | The 181-line document is organized, with a mandatory conditional reference to the agents sibling. Repeated invariants and lengthy example payloads could be compressed. |
| **D6: Freedom Calibration** | **11/15** | Exact entrypoint and hand-off instructions suit fragile operations. However, the promised read-only boundary conflicts with the editing workflow it delegates. |
| **D7: Pattern Recognition** | **9/10** | Clear **Tool** pattern with Navigation elements: command examples, output contracts, failure handling, and conditional delegation. |
| **D8: Practical Usability** | **10/15** | Common paths are well documented, including missing siblings and incomplete checks. The editing ambiguity and incomplete failure-isolation guarantee leave meaningful operational gaps. |
| **Total** | **101/120** | **Grade B — useful, but the two Important defects should be resolved.** |

Approximate knowledge ratio: **Expert 80% / Activation 15% / Redundant 5%**.

## Findings

1. **Important — The read-only promise conflicts with the delegated editing workflow.**  
   **Package:** `skills/ai-kit-project-rules-all/SKILL.md:10–11`, `127–132`, `168–169`.

   The scope states that the skill “never edits the target repo.” However, “Act on the report” directs the agent to follow the agents sibling’s Steps A–D, including insertion and `/agent-md-refactor`. The non-workflow prohibition further implies that workflow findings are an editing exception.

   **Repository evidence:** `skills/ai-kit-project-rules-agents/SKILL.md:64–70` explicitly assembles insertions, invokes the whole-file refactor, and requires direct edits during rechecking. Its confirmation step at line 62 concerns near-misses, not permission to turn a whole-repository audit into remediation.

   This leaves an agent choosing between the advertised read-only contract and the delegated procedure. The conditional wording “before acting” prevents this from being an unequivocal instruction to edit immediately, but it does not establish when editing becomes authorized.

   **Fix:** Make the boundary explicit: report workflow findings by default and execute the hand-off only when remediation is requested or authorized. Alternatively, state clearly that only the Python checker is read-only and that the interactive workflow may edit AGENTS.md.

2. **Important — The unconditional per-domain failure-isolation guarantee is not implemented for decoding and process-launch failures.**  
   **Package:** `skills/ai-kit-project-rules-all/SKILL.md:27–28`, `83–87`, `173–174`.

   The document presents subprocess failures as isolated `failed` entries and instructs the agent never to lose the other domains’ results.

   **Repository evidence:** `skills/ai-kit-project-rules-all/ai_kit_project_rules_all/dispatch.py:103–117` uses `subprocess.run(..., text=True)` but catches only `TimeoutExpired`. An undecodable stdout/stderr stream raises `UnicodeDecodeError`; a process-launch failure can raise `OSError`. Neither reaches the JSON error handler at lines 131–139. Because `dispatch_all()` uses an unguarded comprehension at line 146, either exception terminates dispatch before remaining domains run.

   **Fix:** Normalize these exceptions into per-domain `failed` entries if isolation is the required contract. Until then, narrow the documentation to the failure classes actually handled and explain that an overall dispatcher failure means coverage is incomplete.

3. **Minor — Repeated invariants and duplicate command examples consume unnecessary context.**  
   **Package:** `skills/ai-kit-project-rules-all/SKILL.md:10–30`, `60–76`, `136–176`.

   Field ownership, report-only behavior, resolution order, and failure isolation recur across Scope, Act, Limits, and Anti-patterns. The command block also lists both commands consecutively, although they perform equivalent work and each reruns all siblings.

   **Fix:** Give each invariant one authoritative explanation, retain only brief safety reminders, and label `check` and `remediate` as alternatives. Shorten the long non-workflow JSON summary while preserving the contrasting output shape.

## Factual checks

Static inspection confirmed the documented sibling order, five-candidate resolution without `$PATH`, `remediate` invocation, captured output, and 30-second per-domain timeout in `skills/ai-kit-project-rules-all/ai_kit_project_rules_all/dispatch.py:25–40`, `43–80`, `103–109`, and `142–146`. The referenced Wrap mechanism exists and contains the described insertion and recheck procedures.

Not checked: runtime execution, CLI alias equivalence, or aggregation internals; no files were changed.  
Main risk: an audit may be interpreted as authorization to edit, and some subprocess failures can prevent complete coverage.
