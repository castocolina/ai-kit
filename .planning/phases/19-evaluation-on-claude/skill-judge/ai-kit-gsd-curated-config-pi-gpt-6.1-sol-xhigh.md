# Skill evaluation: CURRENT

**Score: 111/120 (92.5%, A).** Strong, domain-specific guidance for the primary v2 workflow. The main weakness is an inconsistent approval contract between the supported v1 path and the unconditional safety rules.

- **Pattern:** Process + Tool, with conditional reference navigation.
- **Estimated knowledge ratio:** Expert 80% / Activation 12% / Redundant 8%.
- **Reviewed completely:** `SKILL.md` (306 lines), `references/runner.md` (53 lines), and `references/v1-path.md` (40 lines).
- **Verification:** Read-only inspection; selected implementation files were checked for consistency. No commands or tests were executed.

## Dimension scores

Line references below are relative to `skills/ai-kit-gsd-curated-config/`.

| Dimension | Score | Evidence and justification |
|---|---:|---|
| **D1: Knowledge Delta** | **18/20** | Genuine project-specific knowledge: managed-family removals, runner pseudo-keys, trusted-root merging, and committed-versus-rolled-back recovery (`SKILL.md:109–132, 173–188`). Some expanded instructions repeat without adding knowledge; see F2. |
| **D2: Mindset + Appropriate Procedures** | **15/15** | The preflight asks whether the checkout is trusted and whether v1 wrote its config (`SKILL.md:60–67`). The workflow transfers consequential domain procedures: resolve choices, preview individual keys, obtain approval, then approve fingerprint-bound follow-ups. |
| **D3: Anti-Pattern Quality** | **15/15** | Specific prohibitions explain non-obvious consequences: hand edits bypass validation, `--force` bypasses security checks, and v1 execution overwrites v2 routing (`SKILL.md:269–278`). Recovery warnings distinguish cleanup failures from failed transactions. |
| **D4: Specification Compliance** | **15/15** | Valid frontmatter and matching skill name. The description states WHAT, explicit WHEN scenarios, and searchable triggers such as `.planning/config.json`, GSD agents, and cross-AI execution (`SKILL.md:1–4`). |
| **D5: Progressive Disclosure** | **14/15** | Explicit conditional loading for the legacy path and runner maintenance (`SKILL.md:12–13, 215–218`). References are short and purposeful. Repeated primary-body guidance slightly weakens context efficiency; see F2. |
| **D6: Freedom Calibration** | **14/15** | Appropriately restrictive around config writes, user choices, full-permission execution, and approval boundaries. The supported v1 path does not fit the unconditional approval constraint; see F1. |
| **D7: Pattern Recognition** | **9/10** | A clear six-stage Process workflow backed by Tool-style command templates and troubleshooting. Repeated contracts across workflow, NEVER, and Common mistakes make it less economical than an exemplary implementation; see F2. |
| **D8: Practical Usability** | **11/15** | Excellent primary-path recovery and edge-case guidance, including inactive `.new` files and uncertain git state. The v1 contradiction, inaccurate flag inventory, and unquoted path templates leave concrete execution ambiguities; see F1, F3, and F4. |
| **Total** | **111/120** | |

## Findings

### F1 — Important: The v1 recipe conflicts with the unconditional approval rule

**Sections and lines:**
- `skills/ai-kit-gsd-curated-config/SKILL.md:266–268` — **NEVER**
- `skills/ai-kit-gsd-curated-config/references/v1-path.md:10–17, 28–38` — **Order and safeguards / command sequence**

The body says **“Never skip the plan review or the dry run”** without limiting this requirement to v2. However, the supported v1 recipe proceeds directly through `apply-profile`, `apply-critical-agents`, and other writing commands. It provides neither a plan-review step nor a dry-run mechanism.

An agent cannot follow both instructions literally. This also leaves unclear what approval covers the legacy preset writes.

**Fix:** Explicitly scope the v2 contract and define a separate v1 preview/approval contract, or stop offering v1 for new configuration writes.

### F2 — Minor: Approval-format instructions are unnecessarily duplicated

**Sections and lines:**
- `skills/ai-kit-gsd-curated-config/SKILL.md:134–142` — **Dry-run apply**
- `skills/ai-kit-gsd-curated-config/SKILL.md:266–268` — **NEVER**
- `skills/ai-kit-gsd-curated-config/SKILL.md:293–294` — **Common mistakes**

The requirement to display every full dotted key, avoid grouped summaries, and wait for another user turn is explained in the workflow and repeated through two overlapping troubleshooting rows. A short safety reminder earns its place; multiple expanded restatements add little knowledge.

**Fix:** Keep the authoritative contract in step 4, retain a brief NEVER reminder, and collapse the two troubleshooting rows.

### F3 — Minor: The runner reference incorrectly claims there are only three flags

**Section and lines:**
- `skills/ai-kit-gsd-curated-config/references/runner.md:10–20, 50–51` — **Template flags / Runner upgrade**

“Template 3 understands three flags” reads as an exhaustive inventory, but the same reference also uses `--no-preamble` and `--print-argv`. The implementation supports additional flags as well.

**Fix:** Say “Three integration-relevant flags are described below,” or document the supported flag set accurately.

### F4 — Minor: Path placeholders do not consistently preserve shell argument boundaries

**Sections and lines:**
- `skills/ai-kit-gsd-curated-config/SKILL.md:78, 147, 154` — **Inventory / Dry-run apply / Apply**
- `skills/ai-kit-gsd-curated-config/references/v1-path.md:28–38` — **Command sequence**
- `skills/ai-kit-gsd-curated-config/references/runner.md:50–51` — **Runner upgrade**

Templates leave `<target>` and `<detected path>` unquoted. Substituting a legitimate path containing spaces or shell metacharacters can split arguments or change shell interpretation. The guide carefully quotes entrypoint and scratch paths but does not extend that protection to project paths.

**Fix:** Establish a resolved target variable and consistently use `--project-dir "$TARGET"` and `cd "$TARGET"`; quote detected paths too.

CURRENT 111/120
CRITICAL 0
IMPORTANT 1
