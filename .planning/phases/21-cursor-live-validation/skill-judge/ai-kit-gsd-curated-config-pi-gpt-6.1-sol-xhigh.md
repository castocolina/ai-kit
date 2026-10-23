# Skill Evaluation Report: ai-kit-gsd-curated-config

## Summary

- **Score:** 114/120 (95%)
- **Grade:** A — production-ready expert Skill
- **Pattern:** Tool, organized around a Process workflow
- **Estimated knowledge ratio:** Expert 80% / Activation 12% / Redundant 8%
- **Verdict:** Strong, domain-specific guidance with unusually good approval boundaries, migration safeguards, permission disclosures, and recovery instructions. Remaining issues are minor.

Reviewed `SKILL.md` and both reference files completely using read-only tools. Command examples were assessed statically, not executed.

## Structure and knowledge scan

| File | Size | Assessment |
|---|---:|---|
| `skills/ai-kit-gsd-curated-config/SKILL.md` | 316 lines | Below the rubric’s 500-line ceiling; predominantly expert operational knowledge |
| `skills/ai-kit-gsd-curated-config/references/runner.md` | 62 lines | Expert runner flags, readiness rules, timeout resolution, and upgrade procedure |
| `skills/ai-kit-gsd-curated-config/references/v1-path.md` | 47 lines | Expert legacy sequencing, approval requirements, and degraded-success handling |

The trust model, migration behavior, plan pseudo-keys, skill wiring, permission distinctions, and recovery rules are **Expert** content. Brief reminders about shell persistence and approval discipline are useful **Activation** content. Repeated explanations in the command and mistakes tables account for most **Redundant** content.

## Dimension scores

Evidence locations below are relative to `skills/ai-kit-gsd-curated-config/`.

| Dimension | Score | Evidence and justification |
|---|---:|---|
| **D1: Knowledge Delta** | **17/20** | `SKILL.md:111–134` supplies non-obvious runner choices, trusted-root merging, and migration removals; `:239–247` distinguishes reachability, session gates, and unverified plugin layering. Repeated explanations cost tokens (Finding 1). |
| **D2: Mindset + Appropriate Procedures** | **15/15** | `SKILL.md:60–67` frames trust, migration history, and artifact placement before acting. `:116–146` combines domain-specific decisions with procedures and approval consequences. |
| **D3: Anti-Pattern Quality** | **15/15** | `SKILL.md:280–289` explains why hand edits, habitual `--force`, and mixing v1/v2 are dangerous. `:179–189` captures the less-obvious committed-cleanup and uncertain-worktree traps. |
| **D4: Specification Compliance** | **15/15** | Valid frontmatter and compliant name at `SKILL.md:1–4`. The description states WHAT, explicit WHEN scenarios, searchable configuration/runner keywords, and the boundary with full GSD settings. |
| **D5: Progressive Disclosure** | **14/15** | Explicit conditional loading at `SKILL.md:12–13` and `:224–227`; “only when” prevents unnecessary legacy loading. Some advanced readiness detail is unnecessarily repeated in the main file (Finding 2). |
| **D6: Freedom Calibration** | **14/15** | Fragile writes receive appropriately strict controls: full-key preview, a separate approval turn, candidate validation, and fingerprint-bound follow-ups (`SKILL.md:125–171`). Initial preference collection is unnecessarily rigid (Finding 3). |
| **D7: Pattern Recognition** | **10/10** | A coherent Tool pattern: executable examples, constrained mutation commands, branching choices, failure handling, and conditional references. The Process spine makes the multi-stage operation navigable. |
| **D8: Practical Usability** | **14/15** | Strong handling of unresolved choices, declined trust, rollback failure, committed cleanup warnings, inactive `.new` files, and degraded v1 success. One verification command breaks on target paths containing spaces (Finding 4). |

## Findings

**Critical:** None.  
**Important:** None.

### 1. Minor — Repeated explanations dilute knowledge density

**Location:** `skills/ai-kit-gsd-curated-config/SKILL.md:297–305`

Several mistakes-table rows repeat instructions and explanations already given in the workflow. The clearest examples are:

- **Line 303**, “Restoring the backup after a committed apply…” repeats **lines 179–182**.
- **Line 304**, “Dry run and real apply in one turn…” repeats **lines 136–144**.
- **Line 305**, “Running `approve_with` without the entrypoint…” repeats **lines 159–164**.

These are valuable safeguards, but their second explanations add little knowledge. Keep concise mistake-to-step pointers or retain only troubleshooting details not already supplied.

### 2. Minor — Advanced runner readiness is duplicated across layers

**Location:** `skills/ai-kit-gsd-curated-config/SKILL.md:269`

The `ensure-runner` table row embeds the current-template, older-template, and foreign-runner readiness rules already explained in:

`skills/ai-kit-gsd-curated-config/references/runner.md:36–44`

Keep the main row to required flags, output fields, and “read `ready`, not `.new` existence”; leave the template-version decision tree in the conditionally loaded reference.

### 3. Minor — Initial questions must be repeated even when already answered

**Location:** `skills/ai-kit-gsd-curated-config/SKILL.md:83`

> “Ask the user, in one message, four questions — nothing else”

Read literally, this requires another preference questionnaire when the invocation already supplies all four answers. That is unnecessary rigidity for a skill advertised as the faster configuration path.

Collect **missing** answers in one grouped message and reuse explicit answers already provided. Keep the later plan-choice and dry-run approval gates unchanged.

### 4. Minor — Runner verification does not quote the target path

**Location:** `skills/ai-kit-gsd-curated-config/references/runner.md:60`

```bash
cd <target> && node .planning/scripts/cross-ai.mjs --print-argv
```

After placeholder substitution, a target such as `my project` makes `cd` fail. This interrupts the active-runner verification required before deleting `.new`.

Use:

```bash
cd "<target>" && node .planning/scripts/cross-ai.mjs --print-argv
```

## Top 3 improvements

1. Quote the runner verification target path.
2. Reuse supplied preferences and ask only for missing answers.
3. Compact repeated troubleshooting explanations and move advanced readiness detail fully into `references/runner.md`.

CURRENT 114/120
CRITICAL 0
IMPORTANT 0

DIGEST 85da5a6682d937c5
