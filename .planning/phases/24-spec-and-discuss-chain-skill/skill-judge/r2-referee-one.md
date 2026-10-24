DIGEST 4ce07543b1aafd75
# Skill evaluation: `ai-kit-gsd-spec-discuss`

**Score: 97/120 — Grade B.** A strong, domain-specific Process skill with effective safety rules and reference loading. Its main weaknesses are oversized metadata and incomplete safeguards around interactive execution and background analysis.

Reviewed all **241 lines** of `SKILL.md` and all four references:

| Reference | Lines |
|---|---:|
| `references/analyzer-brief.md` | 53 |
| `references/decision-table.md` | 85 |
| `references/log-formats.md` | 113 |
| `references/worked-examples.md` | 51 |

Estimated **Expert : Activation : Redundant** ratio: **80 : 15 : 5**.

## Rubric dimensions

Paths below are relative to `skills/ai-kit-gsd-spec-discuss/`.

| Dimension | Score | Evidence and assessment |
|---|---:|---|
| **D1: Knowledge Delta** | **18/20** | Non-obvious routing traps, engine-derived coverage, backend confidence interpretation and cross-phase amendments provide genuine expertise (`SKILL.md:85–91, 98–105`; `references/decision-table.md:18–45`). Some repeated descriptions of modes and safeguards consume tokens without adding decisions. |
| **D2: Mindset + Appropriate Procedures** | **14/15** | “You are the decider” establishes evidence-led judgment, supported by executable procedures and a blocking/confidence matrix (`SKILL.md:14–18`; `references/decision-table.md:54–65`). Background scheduling does not fully preserve the required spec-before-analysis dependency. |
| **D3: Anti-Pattern Quality** | **15/15** | Excellent specific prohibitions with consequences: `--assumptions` writes nothing, discuss `--auto` advances into planning, config mutation survives crashes, and replacing CONTEXT loses locked decisions (`SKILL.md:203–222`). These are operational landmines, not generic warnings. |
| **D4: Specification Compliance** | **5/15** | The name is valid and the description supplies WHAT, WHEN and trigger keywords. However, the decoded description is **1,167 characters**, exceeding the Agent Skills specification’s **1,024-character maximum** (`SKILL.md:3`). That is specification noncompliance despite valid YAML syntax. |
| **D5: Progressive Disclosure** | **14/15** | Explicit mandatory reference triggers, a conditional worked-examples route and “Do NOT load” guidance are strong (`SKILL.md:72, 118, 122–123, 231–241`). Workflow mechanics in the description undermine the lightweight metadata layer. |
| **D6: Freedom Calibration** | **11/15** | Appropriate flexibility for design choices and strict constraints for consent, locked decisions and coverage generation. However, interactive workflow delegation and speculative analyzer scheduling leave consequential behavior insufficiently constrained (`SKILL.md:96–101, 198–201`). |
| **D7: Pattern Recognition** | **9/10** | A clear **Process** pattern: setup, spec, discuss, decision ladder, ledger and completion, with focused supporting references. Repeated mode explanations slightly weaken its otherwise clean structure. |
| **D8: Practical Usability** | **11/15** | Strong handling of unavailable clients, malformed items, backend errors, low confidence and host limitations (`SKILL.md:37–43, 138–164, 224–229`). Interactive auto-advance, analyzer prerequisites and auto-only log wording leave realistic execution gaps. |
| **Total** | **97/120** | **80.8% — B** |

## Findings

### Critical

None identified.

### Important

1. **Description exceeds the portable specification limit.**  
   **Location:** `SKILL.md:3`  
   The description is **1,167 characters**, 143 over the maximum. A conforming validator can reject the skill; permissive loading on one host does not establish portability. Move run-mode mechanics, config queries and backend sequencing into the body, retaining capabilities, triggers and exclusions in metadata.

2. **The no-planning safeguard is scoped to the auto path, leaving interactive execution exposed to auto-advance.**  
   **Location:** `SKILL.md:96–101`  
   Line 97 explicitly says “the rules below are the auto path,” which scopes the subsequent instruction to skip `auto_advance`. The interactive path instead runs standard `discuss-phase.md`. The checkout’s workflow explicitly dispatches its auto-advance step when `workflow.auto_advance` is enabled (`.claude/gsd-core/workflows/discuss-phase.md:489–492`), even without passing `--auto`. This can violate the skill’s promise never to plan or execute. Make the auto-advance prohibition unconditional across both paths.

3. **Background analysis can start before its required SPEC exists or is current.**  
   **Location:** `SKILL.md:198–201`; `references/analyzer-brief.md:10–11`  
   The pacing rule permits phase K+1’s analyzer to start while phase K’s SPEC is being written. In a fresh range, K+1 has not yet completed its own spec step, yet the analyzer must read K+1’s locked SPEC first. “Coupling is low” does not establish that prerequisite. Require K+1’s spec step to finish before spawning its analyzer, and revalidate background output if upstream decisions change its inputs.

### Minor

4. **The SPEC Interview Log template can misreport an interactive run as automatic.**  
   **Location:** `references/log-formats.md:20–22`; `SKILL.md:76–84`  
   The shared format hardcodes “`--auto`, one round,” although the skill also supports interactive spec generation and directs Interview Log entries to this reference. Parameterize mode and round count, or explicitly restrict this template to auto runs.

5. **Repeated run-mode mechanics dilute otherwise strong compression.**  
   **Location:** `SKILL.md:3, 10–12, 64–70, 76–78, 96–100`  
   Some repetition usefully reinforces dangerous flag distinctions, but the long metadata description repeats execution details already explained in setup and phase routing. Removing those details from metadata fixes the compliance issue and improves knowledge density without losing safeguards.

**Priority:** shorten metadata, enforce no-auto-advance on both paths, then gate background analysis on completed spec prerequisites.

No files were changed; workflows and backend calls were not executed. Runtime behavior beyond the inspected workflow remains unverified.

CURRENT 97/120
CRITICAL 0
IMPORTANT 3
