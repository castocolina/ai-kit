## Assessment

Read both complete skills and inspected their bundled CLI implementations using read-only tools. **Neither version has a `references/` directory**, so there are no reference files or loading triggers to evaluate. No commands or tests were executed.

- **BASELINE:** 174 lines; **107/120 — B**
- **CURRENT:** 175 lines; **108/120 — A**
- **Pattern:** Tool, appropriately implemented as a thin CLI wrapper.
- **Estimated knowledge mix, both:** approximately **80% Expert / 15% Activation / 5% Redundant**.

CURRENT improves the false-positive guidance by explicitly covering `runtime`, legacy `cli`, and `model` matches. That matches its bundled scanner. No regression was found.

## Dimension scores

Line references use CURRENT’s `SKILL.md` unless marked **B** for BASELINE.

| Dimension | BASELINE | CURRENT | Evidence and justification |
|---|---:|---:|---|
| **D1: Knowledge Delta** | **18/20** | **18/20** | Substantial package-specific knowledge: config/auth separation (17–25), discovery precedence (54), inactive tiers and substring matches (124–136), duplicate IDs (149–150). Repeated non-object explanations and routine shell guidance dilute concision slightly. |
| **D2: Mindset + Appropriate Procedures** | **14/15** | **14/15** | Establishes the right decisions before execution: identify provider kind, reject unsupported operations, invoke the helper, and interpret warnings conservatively (15–48, 112–136). Missing guidance for incomplete scans and structural-validation refusal prevents full marks. |
| **D3: Anti-Pattern Quality** | **14/15** | **15/15** | Concrete safeguards against config damage, secret exposure, and misleading conclusions (159–175). CURRENT improves B:172–174’s `cli`-only prohibition by explicitly covering `runtime`, legacy `cli`, and `model` false positives (173–175). |
| **D4: Specification Compliance** | **15/15** | **15/15** | Valid frontmatter and name. Description specifies capabilities, trigger scenarios, searchable terms, and exclusions (1–4). Activation information is not hidden only in the body. |
| **D5: Progressive Disclosure** | **13/15** | **13/15** | Both are compact, self-contained skills; references are unnecessary for this scope. However, examples, edge cases, and NEVER rules repeat some explanations instead of keeping one authoritative explanation with brief reminders. |
| **D6: Freedom Calibration** | **12/15** | **12/15** | Correctly constrains fragile JSONC operations to the bundled CLI and prohibits manual substitutes (8–9, 159–160). Entrypoint precedence can select another installation, and command examples use an unassigned shell variable despite the fresh-shell warning (29–66, 85). |
| **D7: Pattern Recognition** | **9/10** | **9/10** | Clear Tool pattern: scope → resolution → commands → interpretation → failures → anti-patterns. Appropriate structure, with some avoidable repetition for a thin wrapper. |
| **D8: Practical Usability** | **12/15** | **12/15** | Strong coverage of no-ops, non-object entries, missing config, duplicate IDs, and inactive references. Remaining gaps concern scan confidence, executable examples, and the undocumented structural-safety refusal. |
| **Total** | **107/120** | **108/120** | CURRENT improves warning interpretation without materially changing the other dimensions. |

## CURRENT findings

### Critical

None found.

### Important

1. **Scan-status wording overstates what was actually checked.**  
   **Location:** `skills/ai-kit-opencode-providers/SKILL.md:114–122`, related safeguard at **166–168**.  
   The skill says the tool reports which sources it scanned, but the implementation assigns `scanned` based on file existence. Review-spec scanning can silently return no results when `tomllib` is unavailable or TOML parsing fails; unreadable or malformed sources can likewise yield no matches. Therefore, an existing source marked `scanned` does not establish successful inspection.  
   **Improve:** Explicitly describe these limitations and prohibit interpreting *any* empty scan as proof of no references—not only sources marked `absent`. State the Python/TOML prerequisite for meaningful review-spec scanning.

### Minor

2. **Entrypoint resolution can select a different skill version.**  
   **Location:** `skills/ai-kit-opencode-providers/SKILL.md:36–40`.  
   Other installed copies precede the script beside the loaded `SKILL.md`. With multiple installations, the agent may follow CURRENT’s instructions while executing an older helper.  
   **Improve:** Prefer the colocated entrypoint; use installation-location discovery only as a fallback.

3. **Command examples contradict the fresh-shell guidance.**  
   **Location:** `skills/ai-kit-opencode-providers/SKILL.md:63–66,85`.  
   Resolution prints a path but never assigns `TOOLS_PY`. Calling something a “literal absolute path” does not make `"$TOOLS_PY"` a literal; copied examples can expand it to an empty string.  
   **Improve:** Use an explicitly marked resolved-path placeholder, or assign `TOOLS_PY` within each command invocation.

4. **Exit-code documentation omits structural-validation refusal.**  
   **Location:** `skills/ai-kit-opencode-providers/SKILL.md:141`.  
   Exit `1` also occurs when `validate_removal()` rejects an unsafe or malformed edit, not just for I/O or decoding failures.  
   **Improve:** Document that refusal, confirm that nothing was written, and instruct the agent to report it without bypassing the safety check.

5. **The non-object distinction is explained repeatedly.**  
   **Location:** `skills/ai-kit-opencode-providers/SKILL.md:106–109,151–155,171–172`.  
   The distinction is valuable, but three explanations add unnecessary context cost.  
   **Improve:** Keep the output example and one short interpretation rule; consolidate the remaining repetition.

BASELINE 107/120
CURRENT 108/120
CRITICAL 0
IMPORTANT 1
