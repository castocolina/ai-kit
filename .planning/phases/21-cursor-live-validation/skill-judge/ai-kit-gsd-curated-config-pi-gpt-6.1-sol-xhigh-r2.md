# Skill Evaluation Report: ai-kit-gsd-curated-config

## Summary

- **Score:** 114/120 — **95%, Grade A**
- **Pattern:** Tool, organized around a phased Process workflow.
- **Knowledge ratio:** approximately **Expert 80% / Activation 15% / Redundant 5%**.
- **Verdict:** Strong, operationally useful skill with domain-specific safeguards. Remaining findings are minor clarity and token-efficiency issues.
- **Verification:** Read-only inspection; commands were checked against implementation where relevant, not executed.

### Structure

Under `skills/ai-kit-gsd-curated-config/`:
- `SKILL.md`: **317 lines**
- `references/runner.md`: **61 lines**
- `references/v1-path.md`: **47 lines**

Both references have scenario-based loading instructions. The v1 reference is explicitly restricted to that secondary flow.

## Dimension Scores

Citations below are relative to `skills/ai-kit-gsd-curated-config/`.

| Dimension | Score | Evidence and justification |
|---|---:|---|
| **D1: Knowledge Delta** | **18/20** | Strong expert content: managed-family removals (`SKILL.md:127–134`), committed-versus-rolled-back outcomes (`176–182`), and runner readiness floors (`references/runner.md:35–43`). Repeated approval warnings introduce some redundancy; consolidate them. |
| **D2: Mindset + Appropriate Procedures** | **14/15** | The preflight questions (`SKILL.md:60–67`) establish trust, migration and artifact-location reasoning before execution. Procedures encode non-obvious dependencies and approval boundaries. The profile question at line 84 needs a brief selection framework. |
| **D3: Anti-Pattern Quality** | **15/15** | Specific prohibitions explain consequential failure modes: `--force` bypasses named guards (`SKILL.md:283–286`), and v1 execution can overwrite v2 routing (`287–289`). These are operational landmines, not generic warnings. |
| **D4: Specification Compliance** | **15/15** | Valid frontmatter and matching lowercase, hyphenated name (`SKILL.md:1–4`). The description explicitly covers capabilities, trigger scenarios, filenames, cross-AI terminology and the boundary with full GSD settings. |
| **D5: Progressive Disclosure** | **15/15** | The primary workflow remains self-contained; v1 is loaded “only when running it” (`SKILL.md:12–13`). Runner details have explicit conditional triggers (`224–227`), keeping upgrade and customization details out of normal setup. |
| **D6: Freedom Calibration** | **14/15** | Fragile operations are appropriately constrained: no autonomous `needs_choice` resolution (`SKILL.md:276–279`), separate dry-run approval (`136–144`), and fingerprint-bound follow-ups (`159–164`). Unquoted path substitutions slightly weaken command precision. |
| **D7: Pattern Recognition** | **10/10** | A well-executed Tool pattern: precise subcommands, branching rules, state interpretation, recovery guidance and scoped references. The phased structure supports rather than obscures the tooling. |
| **D8: Practical Usability** | **13/15** | Excellent coverage of refusal recovery, rollback failures, cleanup warnings, inactive `.new` artifacts and uncertain runtime behavior. Minor path-quoting and flag-description issues remain. |

## Findings

### Minor 1 — Path substitutions should be shell-quoted

**Exact line:** `skills/ai-kit-gsd-curated-config/SKILL.md:80`

> `python3 "$ENTRYPOINT" inventory --project-dir <target> > "$WORK/inventory.json"`

Replacing `<target>` with an unquoted path containing spaces or shell metacharacters produces an incorrect command. The same pattern appears at lines **149** and **156**; a detected path is likewise unquoted in `references/v1-path.md:43`.

**Improve:** Show quoted path placeholders, such as `--project-dir "<target>"` and `--path "<detected path>"`, so substitution preserves a single argument.

### Minor 2 — The profile choice lacks decision guidance

**Exact line:** `skills/ai-kit-gsd-curated-config/SKILL.md:84`

> `model_profile`: quality / balanced / budget / adaptive (adaptive recommended);

The skill explains rigor’s concrete effects but does not explain the profile trade-off, particularly **balanced versus adaptive**, or how profile differs from rigor. This leaves a central user choice less informed than the surrounding workflow.

**Improve:** Add a compact, verified profile-selection rule, drawing actual behavior from the installed GSD inventory rather than assuming fixed model assignments.

### Minor 3 — Consecutive mistake rows repeat an already-detailed safeguard

**Exact lines:** `skills/ai-kit-gsd-curated-config/SKILL.md:304–305`

These two rows repeat the separate-turn approval and full-dotted-key requirements already explained at **136–144**, with another reminder at **276–279**. The second adjacent row adds little beyond the first.

**Improve:** Combine them into one short mistake entry pointing back to step 4. Retain the detailed rule there and the concise NEVER reminder.

### Minor 4 — The runner’s flag count is misleading

**Exact line:** `skills/ai-kit-gsd-curated-config/references/runner.md:14`

> The template understands three flags (since template 3).

The template supports more than three flags. Even this reference additionally uses `--no-preamble` at **line 25** and `--print-argv` at **line 59**. The sentence incorrectly presents the selected list as the complete interface.

**Improve:** Replace it with “Relevant hook-control flags include…” rather than expanding the reference into an exhaustive CLI manual.

## Top 3 Improvements

1. Quote substituted filesystem paths throughout command examples.
2. Add brief, verified guidance for choosing `model_profile` independently of rigor.
3. Consolidate repeated approval warnings while preserving the authoritative safeguard in step 4.

CURRENT 114/120
CRITICAL 0
IMPORTANT 0

DIGEST 7d1a986df40b63a8
