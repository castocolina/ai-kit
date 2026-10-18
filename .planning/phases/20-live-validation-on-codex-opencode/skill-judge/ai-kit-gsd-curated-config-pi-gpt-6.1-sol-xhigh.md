# CURRENT skill evaluation

Reviewed `skills/ai-kit-gsd-curated-config/SKILL.md` and both files in its `references/` directory against the supplied rubric. Command guidance was checked statically against the bundled CLI and runner; nothing was executed or modified.

**Score: 116/120 — Grade A (96.7%)**  
**Pattern:** Tool, organized around a gated Process workflow.  
**Estimated knowledge ratio:** Expert 85% / Activation 10% / Redundant 5%.

The package delivers substantial project-specific knowledge: migration removals, trusted-root decisions, fingerprint-bound approvals, rollback recovery, runner readiness, and flow-dependent permissions. Its remaining weaknesses are minor compression and wording issues.

## Dimension scores

Paths below are relative to `skills/ai-kit-gsd-curated-config/`.

| Dimension | Score | Evidence and assessment |
|---|---:|---|
| **D1: Knowledge Delta** | **19/20** | `SKILL.md:114–132`, `174–188`, and `229–245` capture non-obvious behavior rather than basic tutorials. Small deduction for repeating approval and runner-state guidance across workflow, reference table, NEVER list, and mistakes table. |
| **D2: Mindset + Appropriate Procedures** | **15/15** | `SKILL.md:60–67` frames trust, configuration provenance, and artifact placement before action. The workflow at `69–169` supplies domain-specific sequencing, user decisions, dry-run approval, and follow-ups—not generic file-editing steps. |
| **D3: Anti-Pattern Quality** | **15/15** | `SKILL.md:269–288` gives specific prohibitions with consequences: hand edits bypass validation, untrusted inventory executes project JavaScript, and v1 execution overwrites v2 routing. Recovery guidance explicitly distinguishes failed rollback from committed cleanup warnings. |
| **D4: Specification Compliance** | **15/15** | Frontmatter at `SKILL.md:1–4` is valid; the name matches the directory and naming requirements. The description states capabilities, explicit use scenarios, searchable filenames/commands, and the boundary with full GSD settings. |
| **D5: Progressive Disclosure** | **14/15** | The 314-line main file routes explicitly to `references/v1-path.md` (47 lines) at `12–13`, and `references/runner.md` (58 lines) at `222–225`. Both references have conditional reading instructions. Some detailed runner-readiness content remains duplicated in the main subcommand table. |
| **D6: Freedom Calibration** | **15/15** | `SKILL.md:97–169` appropriately constrains fragile configuration changes through validated commands, explicit choices, a separate approval turn, and unchanged fingerprint-bound follow-up commands. `--force` requires an expressly chosen user value (`123–124`, `280–283`). |
| **D7: Pattern Recognition** | **10/10** | A coherent Tool/Process combination: entrypoint resolution, staged workflow, branch-specific references, failure handling, command reference, and anti-patterns. The structure fits configuration operations rather than imposing an unrelated creative or philosophy pattern. |
| **D8: Practical Usability** | **13/15** | Strong coverage of stale inventory, unresolved choices, migration removals, inactive `.new` files, partial skill isolation, workstream limits, and degraded success. Small deductions for ambiguous ordinary `plan-unset` semantics and an inaccurate flag-count statement in the runner reference. |

## Findings

**Critical:** None.  
**Important:** None.

### Minor 1 — Consolidate repeated operational detail
**Lines:** `SKILL.md:222–225`, `266`, `288`; `references/runner.md:32–40`.

Runner readiness and `.new` handling appear in several places, including a lengthy `ensure-runner` table cell that largely repeats the conditional reference. Similar approval instructions recur in the workflow, NEVER list, and mistakes table. Keep brief safety reminders, but make the reference authoritative for readiness variants and shorten the repeated descriptions. This would improve knowledge density without weakening safeguards.

### Minor 2 — State ordinary `plan-unset` preservation semantics explicitly
**Lines:** `SKILL.md:98–106`, `263`.

“Decline / remove a plan entry” does not explicitly distinguish declining a proposed change from deleting a configuration key. For ordinary keys, the implementation retains the existing value with `op: keep` (`ai_kit_gsd_curated_config/plan_edit.py:118–130`).

Add: **“For ordinary keys, `plan-unset` cancels the proposed change and preserves the existing config value; it does not delete the config key.”** Keep the separately documented runner-model exception.

### Minor 3 — Correct the runner flag inventory
**Lines:** `references/runner.md:12–23`.

“The template understands three flags” is misleading: the section also relies on `--no-preamble`, and the template supports additional flags. Rename this introduction to **“Relevant runner flags”**, or list the four discussed flags explicitly, including `--no-preamble`.

CURRENT 116/120
CRITICAL 0
IMPORTANT 0
