# Skill evaluation: ai-kit-gsd-spec-discuss

**105/120 — B (Good).** Strong **Process/Tool** skill with substantial GSD-specific knowledge, effective safety rules, and useful reference layering. Estimated Expert:Activation:Redundant ratio: **85:10:5**.

Reviewed all **308 lines of SKILL.md**, four references, three scripts, and the requested diff. The new global-skill containment/trusted-root explanation matches the installed gsd-core implementation. Both agent prompts now explicitly prohibit independent jev calls, including when `jev-fast-decision` is wired.

| Dimension | Score | Assessment |
|---|---:|---|
| D1: Knowledge Delta | 19/20 | Valuable routing, consent, amendment, and engine-floor knowledge; slight repetition. |
| D2: Mindset + Procedures | 13/15 | Strong evidence-first judgment; setup ordering remains inconsistent. |
| D3: Anti-Pattern Quality | 15/15 | Specific prohibitions with concrete failure mechanisms (`SKILL.md:270–289`). |
| D4: Specification Compliance | 15/15 | Valid frontmatter; description clearly covers capabilities, triggers, and exclusions. |
| D5: Progressive Disclosure | 13/15 | Mandatory reference triggers and explicit non-loading guidance; setup diagnostics are becoming dense. |
| D6: Freedom Calibration | 12/15 | Appropriate advisory freedom, but contradictory continuation and precedence rules weaken safeguards. |
| D7: Pattern Recognition | 9/10 | Clear phased Process/Tool structure with focused supporting resources. |
| D8: Practical Usability | 9/15 | Common paths are actionable; wiring, workstream, selector, and forced-answer branches need correction. |
| **Total** | **105/120** | **Good, with important operational gaps.** |

### Findings

1. **Important — Wiring checks give contradictory continuation instructions and precede mode selection.**  
   **Evidence:** `skills/ai-kit-gsd-spec-discuss/SKILL.md:53–58` selects agents by run mode, but mode is chosen at `:110–117`. At `:81–82`, “Continue only then” requires complete resolution; `:84–86` instead says the run continues without skipped skills. Optional, unconfigured wiring can therefore stop the run, depending on interpretation.  
   **Fix:** Move wiring checks after mode selection. State one policy: report unconfigured/empty/skipped entries and continue with resolved entries; never imply skipped skills were loaded.

2. **Important — Workstream diagnostics are not reliably connected to workstream execution.**  
   **Evidence:** `skills/ai-kit-gsd-spec-discuss/SKILL.md:56–62` expands `GSD_WS` while explicitly saying this skill does not set it. A user’s textual `--ws <name>` does not initialize a shell variable. Workflow arguments at `:123–125` and `:144–148` contain only the phase and optional `--auto`, dropping `--ws`.  
   **Fix:** Parse and retain the workstream argument before setup queries, then explicitly forward it to both workflows and other workstream-scoped queries. Ensure range discovery uses that workstream’s phase directory.

3. **Important — Forced-answer routing can bypass the user-lock rule and lacks a contradiction branch.**  
   **Evidence:** `skills/ai-kit-gsd-spec-discuss/references/decision-table.md:16–30` says forced branches run before all numbered rows, including the user-locked-decision safeguard at `:34–37`. It also specifies acceptance when evidence agrees and fallback when answers remain split, but not a single forced answer contradicted by evidence.  
   **Fix:** Apply the user-lock safeguard first. Apply forced branches before rows **2–5**, and explicitly route contradicted or unsupported forced answers to evidence-based own reasoning, with the normal ledger/stop rules.

4. **Important — Explicit phase selection omits a required CLI argument.**  
   **Evidence:** `skills/ai-kit-gsd-spec-discuss/SKILL.md:87–90` supplies only selectors for explicit ranges and places roadmap acquisition in the “Otherwise” branch. However, `skills/ai-kit-gsd-spec-discuss/scripts/phase_range.py:152` requires `--roadmap` for every invocation.  
   **Fix:** Acquire roadmap JSON for both paths and show the complete invocation: `phase_range.py --roadmap <tmp>.json --from N --to M` or its `--list` equivalent.

5. **Minor — The new forced example contradicts the original evidence for the same case.**  
   **Evidence:** `skills/ai-kit-gsd-spec-discuss/references/worked-examples.md:8–14` explains why Phase 17 K08’s `every_pair` answer is wrong; `:61–63` reuses that case but says evidence supports it.  
   **Fix:** Use a different, explicitly hypothetical case for forced acceptance, or preserve K08’s original evidence and demonstrate rejection.

No files changed or credential files read. Runtime execution was not tested; the findings identify unresolved instruction-level risks.

DIGEST 6d04a697fd72294b
CURRENT 105/120
CRITICAL 0 IMPORTANT 4
