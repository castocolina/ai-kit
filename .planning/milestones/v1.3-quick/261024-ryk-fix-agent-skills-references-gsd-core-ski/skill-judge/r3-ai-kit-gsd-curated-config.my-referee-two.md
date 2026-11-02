# Skill Judge Report — `ai-kit-gsd-curated-config`

Scope: `SKILL.md`, `references/v1-path.md`, `references/runner.md`, the `ai_kit_gsd_curated_config/` package, `evals/`, `skill_affinity.json`. Diff focus: `5b4ec21..HEAD` (trusted-global-roots rewrite). I live-verified the diff's core claims against `.claude/gsd-core/bin/lib/init.cjs` (`buildAgentSkillsBlock`: global `SKILL.md` containment vs. `loadTrustedGlobalRoots`, namespaced `global:` claude-only, project-path confinement — all match SKILL.md's statements), and confirmed the refusal chain is force-immune and test-pinned (`plan_edit.py:186`, `apply.py:907`, `prepare()` shared by dry-run and apply, `cli.py:635` exit 2; `tests/test_curated_config_plan_edit.py`, `test_curated_config_skills.py`).

| Dimension | Score | Max | Notes |
|---|---|---|---|
| D1 Knowledge Delta | 18 | 20 | Near-pure expert content: gsd-core skip semantics, trust-root security model, hook permission matrix, marker/rollback discipline, per-host validation limits. Minor duplication of the trusted-root rule (SKILL.md:124-128 vs 255-262). |
| D2 Mindset + Procedures | 13 | 15 | "Is `<target>` a trusted checkout?" + non-obvious pipeline ordering + failure-state decision rules. Mostly procedural; few thinking prompts, though here the procedures are the domain knowledge. |
| D3 Anti-Pattern Quality | 14 | 15 | 8 NEVERs, each with non-obvious why; mistakes table with cause+fix. |
| D4 Specification / Description | 14 | 15 | WHAT/WHEN/KEYWORDS all present, boundary stated ("alternative, not a replacement"), quoting fix in this diff makes the YAML robust. Deduction: trusted-root/agent_skills-security surface now central but absent from the description. |
| D5 Progressive Disclosure | 13 | 15 | Both refs have conditional triggers + "Do NOT load" (v1-path.md:3, runner.md:3-4). SKILL.md 352 lines exceeds the 300 ideal; `evals/` unreferenced. |
| D6 Freedom Calibration | 14 | 15 | Fragile writes → exact commands, force-immune refusals; choices → user with candidates. Correct for a config-destroying operation. |
| D7 Pattern Recognition | 9 | 10 | Clean Tool pattern (exit-code table, subcommand table, decision rules) with an embedded Process flow. |
| D8 Practical Usability | 13 | 15 | Every new claim checked out against gsd-core and code; edge cases and error handling comprehensive. Deduction: several new sentences are compressed to re-read territory; set-vs-kept live-validation asymmetry undocumented. |
| **Total** | **108** | **120** | **Grade A (90.0%)** |

## Findings

1. **[Important] Over-compressed prose in the new Skills section.** SKILL.md:257-262 — "The refusal offers two fixes joined by 'or': re-approve the root … or drop the skills it covers …; declining means the second. Re-run the printed command with the entrypoint and `--plan`, as the trusted-roots text says." Circular and cryptic for the cheap cross-AI executors this repo targets. Mitigated by the runtime refusal messages (`plan_io.py` `_skip_message` prints exact commands), but the doc should stand alone. **Fix:** split into a refusal → action bullet map: "declined the root → remove the covered skills from each `agent_skills.<agent>`; the refusal prints the exact `plan-set`; run it unchanged."

2. **[Important] Live-revalidation asymmetry not disclosed.** SKILL.md:267-269 correctly scopes live re-checking to *kept* entries, but `plan_io.py` `_skipped_items` checks *set* entries only against the inventory snapshot (`skills_mod.skip_reason`), so a skill deleted/retargeted after `inventory` passes the new refusals on a set entry (gsd-core still warns/skips at use — nothing unsafe, just a preview gap the headline "only through a reference gsd-core resolves" reads broader than). **Fix:** one Limits-table row (SKILL.md:286-294): "set entries validated against the inventory snapshot; kept entries revalidated live — re-run inventory after filesystem changes."

3. **[Minor] Description misses the trusted-root surface.** SKILL.md:3 — the diff made `agent_skills_security.trusted_global_roots` approval a headline behavior, but the description only says "wires installed skills to GSD agents". **Fix:** add "approves machine-specific trusted skill roots (`agent_skills_security`)" to the WHAT clause.

4. **[Minor] Trusted-root decline rule stated twice.** SKILL.md:124-128 and SKILL.md:255-262 repeat the same refusal; the step-3 bullet already carries the pointer "(the full rule is in Skills)". **Fix:** keep one line + pointer in step 3; full rule only in Skills.

5. **[Minor] `evals/` unreferenced in SKILL.md.** Four dev-time scenario files (~203 lines) sit in the distributed package with no loading guidance — rubric Pattern 8 in miniature. **Fix:** one line in SKILL.md ("run `evals/` after editing this skill") or move them out of the installed tree.

6. **[Minor] Hygiene, not scored:** untracked `__pycache__/*.pyc` on disk inside the skill tree (0 tracked per `git ls-files`); sweep or gitignore since a checkout is an install source for the marker-skill detection.

DIGEST 9ae11c2977b8de1d
CURRENT 108/120
CRITICAL 0 IMPORTANT 2
