# Skill Evaluation: ai-kit-gsd-curated-config

**Current: 104/120 — B (86.7%)**  
**Baseline `d164697`: 85/120 — C (70.8%)**  
**Change: +19 points; no dimension regressed.**

Reviewed both skill texts, the baseline’s referenced source files, and the relevant CLI implementation and shared dependencies. Verification was read-only and offline; I did not run the configuration CLI or modify files.

Both versions follow a **Tool pattern with a Process workflow**. Estimated knowledge ratios, Expert:Activation:Redundant: **current 80:15:5**, **baseline 70:20:10**.

## Dimension scores

| Dimension | Baseline | One-line reason | Current | One-line reason |
|---|---:|---|---:|---|
| **D1: Knowledge Delta** | **15/20** | Strong GSD-specific knowledge—live tier overrides, detection ladders, sparse-config hazards—but repeated explanations dilute it. | **17/20** | Adds valuable transaction, trust-root, runner, and approval knowledge; some duplication remains across workflow, NEVER, and mistakes. |
| **D2: Mindset + Appropriate Procedures** | **12/15** | “Ensure first” and detect-before-apply transfer useful reasoning alongside exact domain procedures. | **14/15** | Trust, provenance, unresolved choices, dry-run, commit state, and approval binding form a strong decision framework. |
| **D3: Anti-Pattern Quality** | **12/15** | Concrete prohibitions explain guessed models, direct config writes, and implicit targets; recovery hazards receive less coverage. | **14/15** | “Never restore” after committed cleanup warnings, cautious `--force`, and `.new` inactivity warnings capture consequential failure modes. |
| **D4: Specification Compliance** | **4/15** | WHAT/WHEN/keywords are strong, but the description contains an unquoted `: ` and fails YAML parsing. | **15/15** | Valid YAML, compliant name, and specific capabilities, activation scenarios, and trigger phrases. |
| **D5: Progressive Disclosure** | **11/15** | The 194-line body is manageable, but source references lack explicit loading triggers and several safeguards are repeated. | **12/15** | Clear sections keep 282 lines navigable, but legacy v1 and detailed command reference remain loaded for every v2 invocation. |
| **D6: Freedom Calibration** | **12/15** | Exact commands and prescribed detection constrain fragile writes appropriately, but partial-failure recovery is underspecified. | **12/15** | Strong validation and approval constraints fit the risk, but side-effect descriptions and target-scoped verification have gaps. |
| **D7: Pattern Recognition** | **9/10** | Recognizable, appropriately constrained Tool/Process structure; dense paragraphs occasionally hinder navigation. | **9/10** | The six-stage workflow, command examples, safeguards, and error branches apply the pattern effectively. |
| **D8: Practical Usability** | **10/15** | Common paths are actionable, but contradictory instructions and limited partial-write recovery reduce reliability. | **11/15** | Broad failure coverage improves usability, but the runner-check command can inspect the wrong project and declining runner choices lacks a complete branch. |
| **Total** | **85/120** | **C** | **104/120** | **B** |

### Structure and reference checks

- Neither version has a dedicated `references/` directory.
- The baseline points to `preference_match.py` (**132 lines, 6,203 bytes**) and `workflow_defaults.py` (**60 lines, 2,387 bytes**); both were read at the baseline revision.
- The current frontmatter parsed successfully using the installed YAML parser. The baseline failed with **“mapping values are not allowed here”** at its description’s colon.

## Critical findings

### C1 — Baseline only: invalid frontmatter can prevent skill discovery

**Location:** `d164697:skills/ai-kit-gsd-curated-config/SKILL.md:3`

The plain YAML description contains:

> `` `config-set`/`config-new-project`: critical-agent ``

The colon followed by a space invalidates the scalar. This is a functional loading defect, not merely formatting.

**Concrete fix:** If restoring that version, use `description: >-` with indented text, or quote and escape the complete value. The current version already avoids this defect.

**Current Critical findings: none.**

## Important findings

### I1 — Current: “read-only/stdout-only” inventory wording hides cache writes and network activity

**Locations:** `skills/ai-kit-gsd-curated-config/SKILL.md:63,241`

The skill calls inventory:

> “writes JSON to stdout only”  
> “Read-only snapshot to stdout”

However, `ai_kit_gsd_curated_config/catalog_adapter.py:128–175` invokes both runtime detection and catalog fetching, including without `--refresh` through their stale-cache paths.

The delegated implementation confirms:
- runtime-cache writes in `skills/ai-kit-spec-review/ai_kit_spec/cli.py:399`;
- external catalog fetches at lines **443–444**;
- catalog writes at line **477**, including when external fetching is skipped.

**Impact:** An agent cannot safely interpret the documented inventory operation as filesystem-read-only or suitable for an offline/no-write request. The JEV TCP disclosure does not describe these other effects.

**Concrete fix:** Replace the broad label with:

> “Does not modify project configuration. Refreshes ai-kit caches and may contact runtime/catalog services; `--refresh` forces refresh.”

Put that disclosure before the first invocation, and distinguish the additional JEV reachability probe.

### I2 — Current: active-runner verification loses the explicit target

**Location:** `skills/ai-kit-gsd-curated-config/SKILL.md:172–177`

Configuration commands consistently use `--project-dir <target>`, but verification switches to:

```bash
node .planning/scripts/cross-ai.mjs --print-argv
```

The runner resolves its configuration and argv workspace using `process.cwd()`—see `skills/ai-kit-spec-review/references/cross-ai.mjs:2316–2323`.

**Impact:** When configuring another checkout, this command either fails or inspects the caller’s runner and timeout settings rather than the target’s active runner.

**Concrete fix:**

```bash
(cd "<target>" && node .planning/scripts/cross-ai.mjs --print-argv)
```

Explicitly perform the `.new` merge and deletion in that same target checkout.

## Minor findings

### M1 — Current: complete the “decline runner choice” branch

**Location:** `SKILL.md:89–106,272`

The general instruction says to decline choices with `plan-unset`, but the runner-specific explanation correctly notes that unsetting a runner model **reopens** its choice. The missing step is how to decline that runner.

**Concrete fix:** Add:
- To decline one runner, remove it from `script:cross-ai.prefer`.
- If declining every runner, use `plan-set workflow.cross_ai_execution false`; an empty preference list is refused.

This matches `plan_edit.py`’s preference-editing and execution-disable paths.

### M2 — Current: qualify the stated gsd-core resolution order

**Location:** `SKILL.md:24–25`

The stated common order omits v2’s host-specific first candidates. `host.py:21–25,74–80` prepends `<root>/.pi/gsd-core` for pi and `<root>/.opencode/gsd-core` for opencode.

**Concrete fix:** Document these host-specific prefixes before the shared order; retain the existing “unverified install root” qualification for opencode.

### M3 — Both: reduce repeated content and make loading conditional

The current body keeps the secondary v1 procedure and full command reference in every v2 load. The baseline repeatedly explains the sparse-config hazard and uses “see source” pointers without explicit loading conditions.

**Concrete fix:** Keep the primary workflow and essential safety invariants in `SKILL.md`; move legacy v1 details and extended reference material into conditionally loaded files. Specify exactly when to load them and when not to.

### M4 — Baseline only: reconcile contradictory instructions

- **Line 114:** empty paths are not accepted.
- **Line 136:** an empty path produces a successful `empty_path` no-op.
- **Line 154:** never route to settings.
- **Line 186:** route deeper tuning to `gsd-settings --advanced`.

**Concrete fix:** State that absent detection should skip the command, while an explicit empty string is a no-op. Prohibit wrapping settings commands, not directing users to them for unsupported tuning.

## Final assessment

The current version materially improves the baseline’s validity, decision framework, and recovery guidance. Its **104/120** meets your **≥96 alternative threshold**, with no score regression. The two Important findings remain unresolved, so this is a **threshold-based pass, not a finding-free review**.

VERDICT: PASS
