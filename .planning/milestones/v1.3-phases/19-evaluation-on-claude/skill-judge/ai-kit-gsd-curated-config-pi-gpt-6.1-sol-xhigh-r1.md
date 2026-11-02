# Skill evaluation: CURRENT

**Score: 113/120 — Grade A (94.2%).** Strong expert guidance for the primary v2 flow, with one Important usability gap in the retained v1 path.

Static, read-only review; runtime behavior was not exercised. All locations below are relative to `skills/ai-kit-gsd-curated-config/`.

- **Pattern:** Tool/Process hybrid.
- **Files reviewed:** `SKILL.md` — 307 lines; `references/runner.md` — 53 lines; `references/v1-path.md` — 42 lines. Relevant packaged implementation was spot-checked.
- **Estimated knowledge ratio:** Expert 85% / Activation 10% / Redundant 5%. Trust boundaries, migration behavior, runner semantics and recovery rules supply genuine knowledge delta. Shell-variable reminders are brief activation; repeated workflow warnings account for most redundancy.

## Dimension scores

| Dimension | Score | Evidence and rationale |
|---|---:|---|
| **D1: Knowledge Delta** | **18/20** | Strong domain-specific knowledge: local gsd-core execution, managed-family removals, rollback versus committed cleanup, and partial bare profiles (`SKILL.md:22–28, 125–132, 173–186, 211–213`). Some repeated instructions consume unnecessary tokens. |
| **D2: Mindset + Appropriate Procedures** | **15/15** | Preflight questions establish trust, migration history and scratch placement; the six-stage workflow makes user decisions and approval boundaries explicit (`SKILL.md:60–168`). Procedures are specific to this tooling rather than generic file operations. |
| **D3: Anti-Pattern Quality** | **15/15** | Specific prohibitions explain non-obvious consequences: schema bypass, executing checkout-owned JavaScript, weakening command guards and destroying v2 runner selection (`SKILL.md:262–281`). |
| **D4: Specification Compliance** | **15/15** | Valid name and frontmatter. Description supplies WHAT, WHEN, concrete request phrases, relevant paths and the distinction from full GSD settings (`SKILL.md:1–4`). |
| **D5: Progressive Disclosure** | **15/15** | Manageable core with explicit conditional reference loading: v1 is loaded “only when running it”; runner details are triggered by upgrade, merge, flags or customization scenarios (`SKILL.md:12–13, 215–218`). |
| **D6: Freedom Calibration** | **13/15** | Appropriately constrained config writes, per-key approval and fingerprint-bound follow-ups (`SKILL.md:134–168`). The v1 approval requirement lacks a defined way to obtain its complete write payload before approval. |
| **D7: Pattern Recognition** | **10/10** | Appropriate Tool/Process structure: resolve the executable, follow a staged workflow, branch into specialized references, handle failures, then report results. |
| **D8: Practical Usability** | **12/15** | Excellent recovery guidance, refusal handling and degraded-success distinctions. The v1 preview gap and several small wording inconsistencies prevent full marks. |

## Findings

### 1. Important — v1 requires informed approval without providing a pre-write effects preview

**Section:** “v1 path,” approval rule and ordered safeguards  
**Location:** `references/v1-path.md:7–19, 30–40`

The reference requires showing “the command and the values it sets” before every write, but supplies neither the preset payloads nor instructions for obtaining them without writing. In particular, `apply-critical-agents` includes live-catalog-dependent overrides, while `apply-workflow-defaults` writes substantially more than its two visible UI arguments.

The packaged implementation confirms material effects absent from this reference, including clearing `workflow.code_review_command` and `workflow.plan_bounce_script`. An agent must discover additional implementation details to satisfy the skill’s own approval gate.

**Fix:** Provide a read-only effects-preview procedure, or explicitly route to the exact preset sources and live-catalog query needed to enumerate every affected key before approval.

### 2. Minor — entrypoint substitution instructions are ambiguous

**Section:** “Resolve the entrypoint”  
**Location:** `SKILL.md:44, 53–56`

The snippet applies `dirname` to an **absolute SKILL.md file path**, but the prose says to substitute the **directory containing SKILL.md** into the first candidate. Substituting that directory into the placeholder would take its parent and could incorrectly select a fallback installation.

**Fix:** Say to replace the placeholder with the full file path, or replace the whole first candidate with the containing directory.

### 3. Minor — runner creation is described as unconditional

**Section:** “Cross-AI execution”  
**Location:** `SKILL.md:192–194`

“v2 `apply` sets” the hook and renders the runner is unconditional wording, despite the supported execution opt-out (`SKILL.md:86–89, 119–122`). The implementation does not propose that artifact when execution is disabled.

**Fix:** Qualify this paragraph with “When cross-AI execution is enabled and execution targets are selected.”

### 4. Minor — the runner flag count is misleading

**Section:** “Template flags”  
**Location:** `references/runner.md:12–20, 50–51`

“Template 3 understands three flags” reads as an exhaustive count, but the same reference also uses `--no-preamble` and `--print-argv`.

**Fix:** Call these “three integration flags,” or distinguish the selected integration flags from other supported switches.

### 5. Minor — repeated warnings dilute otherwise dense expert content

**Sections:** “Run the v2 flow,” “NEVER,” and “Common mistakes”  
**Location:** `SKILL.md:69–78, 134–144, 173–179, 266–281, 287–296`

The common-mistakes table largely repeats earlier instructions, including inventory redirection, unresolved choices, cleanup behavior and per-key approval. The dry-run presentation rule receives particularly extensive repetition.

**Fix:** Keep the authoritative rules beside the relevant workflow steps; retain troubleshooting rows only where they add a distinct symptom, diagnosis or recovery action.

CURRENT 113/120
CRITICAL 0
IMPORTANT 1
