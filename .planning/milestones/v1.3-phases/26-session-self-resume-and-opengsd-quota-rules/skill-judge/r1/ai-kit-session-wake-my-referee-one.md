Judge: my-referee-one
Reviewed-sha256: a43a86648745ab18e0923768b17e9200870d4419896a30a1a68ed97d6cb13631
Lane: AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-one exit=0 cli_rc=0 elapsed=213s out=123082 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 104
Critical: 0
Important: 1

## Dimension scores

| Dimension | Score | Assessment |
|---|---:|---|
| **D1: Knowledge Delta** | **18/20** | Mostly project-specific knowledge: session identity, child-process restrictions, reset handling, and wake primitives. Small redundancy around subagent restrictions and shell-variable handling. |
| **D2: Mindset + Appropriate Procedures** | **13/15** | Strong distinction between orchestrator recovery and cross-AI retry. The arm/reset/finish workflow is actionable, but companion scheduling lacks a complete lifecycle. |
| **D3: Anti-Pattern Quality** | **14/15** | Specific prohibitions address wrong-session resumes, premature cleanup, and harness switching. Several include useful reasons or explicitly acknowledged enforcement limits. |
| **D4: Specification Compliance** | **14/15** | Valid frontmatter and name. Description clearly covers WHAT, WHEN, and trigger keywords. Evidence qualifications are less precise than the text claims. |
| **D5: Progressive Disclosure** | **14/15** | Compact, well-sectioned 139-line document. No unnecessary reference hierarchy. The cross-AI reference would benefit from an explicit conditional reading instruction. |
| **D6: Freedom Calibration** | **12/15** | Exact session IDs, shim use, and prohibited manual operations appropriately constrain persistent automation. Companion-job cleanup remains underspecified. |
| **D7: Pattern Recognition** | **9/10** | Clear **Tool** pattern: commands, host-specific branches, exit codes, and operational restrictions. A unified completion path would strengthen it. |
| **D8: Practical Usability** | **10/15** | Main operations and refusal cases are understandable. Companion cleanup is missing, and the document explicitly leaves actual firing and cleanup unverified. |
| **Total** | **104/120** | **Grade B — useful, focused guidance with one important lifecycle defect.** |

Approximate knowledge ratio: **Expert 85% / Activation 10% / Redundant 5%**.

## Findings

1. **Important — Companion scheduling has no cancellation or completion guard.**  
   **Location:** `skills/ai-kit-session-wake/SKILL.md:71–75`, `skills/ai-kit-session-wake/SKILL.md:95–104`

   The skill instructs the agent to create an in-session one-shot with a “short resume prompt.” Its completion and disarm workflow subsequently covers only the Python shim. It never instructs the agent to retain the companion’s job identifier, cancel that job, or make its prompt check whether the work has already finished.

   If the orchestrator completes or the user disarms the wake before the companion fires, the documented workflow leaves a scheduled resume prompt outstanding. That can produce an unwanted continuation despite completion or disarm.

   **Fix:** Record the companion job identifier and cancel it during completion and explicit disarm. Where cancellation is unavailable, require the companion prompt to check the recorded wake/completion state and stop without continuing completed or disarmed work.

2. **Minor — The claimed inline evidence labelling is not consistently present.**  
   **Location:** `skills/ai-kit-session-wake/SKILL.md:124–128`; related statements at `skills/ai-kit-session-wake/SKILL.md:3`, `skills/ai-kit-session-wake/SKILL.md:8–10`, and `skills/ai-kit-session-wake/SKILL.md:95–96`

   “Each is labelled where it appears” is inaccurate. The description and opening explain resumption without an evidence qualifier, while the completion instructions state that the next wake removes itself. Only the later **Unverified** section says that first-fire resumption and removal after `done` have not been verified on this machine.

   The explicit caveat prevents this from being an undisclosed reliability claim, but the evidence presentation is internally inconsistent.

   **Fix:** Either qualify those statements locally as intended, not live-verified behavior, or replace “Each is labelled where it appears” with an accurate statement that the limitations are collected in this section.

## Repository checks

- The named shim exists and dispatches execution: `skills/ai-kit-session-wake/ai-kit-session-wake.py:18–31`. This confirms the entrypoint, not the downstream scheduling behavior.
- The cross-AI distinction and same-runtime/model retry rule agree with `skills/ai-kit-cross-ai/SKILL.md:130–156` and `skills/ai-kit-cross-ai/SKILL.md:168–172`.

Not checked: imported implementation files, installer wiring, or live scheduling; these were outside the permitted review scope.  
Risk: actual resumption and cleanup remain unverified, as the package itself acknowledges.
