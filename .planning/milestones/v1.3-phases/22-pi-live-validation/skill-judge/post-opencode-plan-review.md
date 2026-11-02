DIGEST 2e55b8f4212d167c
# Skill evaluation: ai-kit-gsd-curated-config

**Score: 114/120 — A (95%)**

The skill provides strong domain-specific guidance: approval boundaries, v1/v2 migration hazards, runner permissions, rollback states, and limits on what detection proves. Its remaining weaknesses are minor duplication and shell-example robustness.

Reviewed completely:
- `skills/ai-kit-gsd-curated-config/SKILL.md`: **321 lines**
- `references/runner.md`: **64 lines**
- `references/v1-path.md`: **47 lines**

**Pattern:** Tool/Process hybrid with conditional reference loading.  
**Estimated knowledge mix:** Expert 85% / Activation 10% / Redundant 5%.

Paths below are relative to `skills/ai-kit-gsd-curated-config/`.

## Dimension scores

| Dimension | Score | Evidence and assessment |
|---|---:|---|
| **D1: Knowledge Delta** | **18/20** | Substantial non-obvious knowledge: trusted-root merge rules (`SKILL.md:121–125`), managed-family removals (`132–139`), committed-versus-failed rollback handling (`181–194`), and session-steer limitations (`258`). Small deductions for repeated runner guidance; consolidate it as described in finding M1. |
| **D2: Mindset + Appropriate Procedures** | **15/15** | The preflight questions (`60–67`) frame trust, migration and artifact placement before execution. The dry-run approval boundary (`141–151`) and fingerprint-bound follow-ups (`164–176`) supply precise, domain-specific procedures rather than generic file-editing instructions. |
| **D3: Anti-Pattern Quality** | **15/15** | The NEVER section (`277–296`) names concrete hazards and explains their consequences: hand edits bypass validation, `--force` bypasses safeguards, and v1 execution overwrites v2’s runner selection. Recovery instructions explicitly distinguish cleanup warnings from rollback failures (`181–187`). |
| **D4: Specification Compliance** | **15/15** | Frontmatter has a compliant name and a description covering WHAT, WHEN and searchable triggers (`1–4`). The description identifies configuration, skill wiring, cross-AI execution and the relationship to existing GSD settings commands. |
| **D5: Progressive Disclosure** | **14/15** | References have clear conditional loading instructions (`12–13`, `229–232`); both references repeat their entry conditions at the top. The main file remains below 500 lines. Minor duplication of runner details weakens the otherwise effective layering; see M1. |
| **D6: Freedom Calibration** | **14/15** | Fragile writes receive appropriately strict controls: explicit choices, full-key previews, separate approval turns and unchanged approval strings (`99–176`). Candidate overrides require an explicit user choice (`130–131`). The scratch-directory example needs a fail-closed execution guard; see M2. |
| **D7: Pattern Recognition** | **10/10** | A coherent Tool/Process structure: prerequisites → entrypoint resolution → staged workflow → failure states → specialized guidance → command reference → anti-patterns. The secondary v1 workflow is appropriately separated. |
| **D8: Practical Usability** | **13/15** | Strong coverage of refusals, degraded success, `.new` activation, stale inventory and follow-up approval. The common-mistakes table gives concrete fixes (`298–310`). Two shell examples have small execution gaps: scratch creation failure and paths containing spaces; see M2–M3. |
| **Total** | **114/120** | **Excellent; minor improvements remain.** |

## Findings

### Critical

None found.

### Important

None found.

### Minor

**M1 — Runner details are partially duplicated across loading layers.**  
**Lines:** `SKILL.md:229–232, 274, 296`; `references/runner.md:38–46, 56–59`.

The main file already explains `.new` inactivity and includes detailed template-readiness rules in the subcommand table. The runner reference repeats those rules. Keeping the safety invariant in the main file is justified, but duplicating the readiness matrix creates additional maintenance work when templates change.

**Improvement:** Keep “`.new` is not active” and the reference-loading trigger in `SKILL.md`; make `runner.md` the authoritative location for the detailed readiness matrix.

**M2 — Scratch-directory creation does not guard the inventory command.**  
**Lines:** `SKILL.md:78–81`.

The example uses:

```bash
WORK="$(mktemp -d)" && printf '%s\n' "$WORK"
python3 "$ENTRYPOINT" inventory --project-dir "<target>" > "$WORK/inventory.json"
```

Without shell fail-fast behavior, a failed `mktemp` does not prevent the next line from running. An empty `WORK` makes the output path `/inventory.json`, and inventory may still perform cache/network work despite scratch setup having failed.

**Improvement:** Explicitly stop on directory-creation failure or chain inventory execution to successful creation.

**M3 — The runner-verification example leaves the target path unquoted.**  
**Line:** `references/runner.md:62`.

```bash
cd <target> && node .planning/scripts/cross-ai.mjs --print-argv
```

After literal substitution, a target path containing spaces or shell metacharacters can fail or be interpreted incorrectly. The main workflow consistently quotes `"<target>"`, so this example should follow that convention.

**Improvement:** Use `cd "<target>" && node .planning/scripts/cross-ai.mjs --print-argv`.

**Verification limit:** No files were modified and no configuration commands were executed. Implementation behavior and live-tool claims remain unverified; this score assesses the supplied documents.

CURRENT 114/120
CRITICAL 0
IMPORTANT 0
