All verification complete; the working tree is clean. Here is the evaluation report.

---

# Skill Evaluation Report: ai-kit-gsd-curated-config (target vs baseline d164697)

**Verification method:** every load-bearing claim in both SKILL.md versions was spot-checked read-only against the CLI (`cli.py`, `presets.py`, `plan_edit.py`, `apply.py`, `followups.py`, `config_backup.py`, `skill_scan.py`, `skills.py`, `cross_ai*.py`, `preference_match.py`, `critical_agents.py`, `plan_io.py`) and the bundled runner template (`ai-kit-spec-review/references/cross-ai.mjs`). No claim was found false. The repo also carries `TestSkillDocCommands` (`tests/test_curated_config_apply.py:2280`), which machine-pins every documented command against the real argparse parser — rare, strong evidence the doc is executable as written.

## Dimension Scores

| Dimension | Target | Baseline | Target one-line reason | Baseline one-line reason |
|---|---|---|---|---|
| D1: Knowledge Delta | **19/20** | 16/20 | ~90% Expert — exit semantics, marker/rollback protocol, `.new` merge, Jev gate all verified in code; near-zero redundancy | Dense expert content diluted by ladder internals the acting agent never needs, maintainer narrative, and description repetition |
| D2: Mindset + Procedures | **14/15** | 12/15 | Pre-action trust/scratch-dir questions plus a 6-stage pipeline with non-obvious ordering (fingerprint-bound approval, dry-run digest gate) | Detect→show→apply pass-through discipline is real, but thinking framing is buried in long prose |
| D3: Anti-Pattern Quality | **15/15** | 13/15 | 7 NEVERs each with a verified non-obvious WHY (v1 `apply-execution` silently displacing the runner is a genuine silent landmine) + 8-row mistake table | 5 specific NEVERs (PATH/venv-rebuild rationale is superb); fewer and one digresses into maintainer trivia |
| D4: Spec Compliance | **15/15** | 14/15 | Description has WHAT + WHEN + trigger keywords + explicit scope boundary vs `gsd-settings`/`gsd-config` | All three elements present, but trigger scenarios buried under implementation detail in the description |
| D5: Progressive Disclosure | **13/15** | 13/15 | 282 lines, self-contained; implementation correctly stays in code the agent never reads; cross-AI maintenance + v1 sub-scenarios could be on-demand references | 194 lines self-contained; source-file pointers exist but with no load/don't-load guidance |
| D6: Freedom Calibration | **15/15** | 14/15 | Exact commands, "run `approve_with` unchanged", `--force` policy — low freedom for full-permission config writes, judgment only where it belongs | Well-calibrated exact commands, but wrapped in more explanatory prose freedom |
| D7: Pattern Recognition | **10/10** | 9/10 | Textbook Tool pattern (tables, decision rules, exact commands) at 282 lines | Clean Tool pattern |
| D8: Practical Usability | **14/15** | 13/15 | Exit-code→action mapping, fallbacks at every refusal, commands drift-tested; one table cell incomplete (see Minor 1) | Complete for the v1 surface incl. degraded/no-candidate paths; exit codes live in prose, commands not machine-pinned at that commit |
| **Total** | **115/120 (95.8%, A)** | **104/120 (86.7%, B)** | | |

**Regression check:** target ≥ baseline on every dimension (D5 equal). No regression.

## Findings

**Critical:** none.

**Important:** none.

**Minor:**

1. **[Target] v1 exit-2 cell is incomplete.** The table says v1 exit 2 = "install problem … do not retry", but `apply-execution` also exits 2 for an unsupported `--cli` (`cli.py` `reject_execute_cli`, before any write) — a fixable input error where "do not retry" is the wrong action. The baseline documented this case. **Fix:** extend the v1 exit-2 cell: "…or a refused `--cli` on `apply-execution` (fix the value, not an install problem)".
2. **[Target] "Live timeout" oversimplifies the runner's config lookup.** The template reads `workflow.cross_ai_timeout` via `.planning[/$GSD_PROJECT][/workstreams/$GSD_WORKSTREAM]/config.json` and falls back to 300 s (`cross-ai.mjs` lines 34–36, 79, 411); the SKILL.md mentions only `.planning/config.json` and the workstream variant. **Fix:** add "via `GSD_PROJECT`/`GSD_WORKSTREAM` scoping, 300 s default" — or drop the mechanics and just say "the runner resolves it the way gsd-tools config-get does".
3. **[Target] `recommend --out` refusal scope slightly simplified.** Code guards the resolved config dir itself when the config is not under a `.planning/` ancestor (`plan_io._planning_root`); SKILL.md says only "inside the project's `.planning/`". The refusal stderr names the real dir, so impact is informational. **Fix:** "(the resolved GSD config dir, not just `.planning/`)".

## Summary

The target is a genuine compressed-expert document: trust model, refusal-vs-failure exit semantics, rollback/marker protocol, and the `.new` merge workflow are exactly the knowledge an operator earns by breaking things, and every spot-checked claim is true against the code. The baseline was already good (B); the v2 rewrite raised it to A by replacing prose about *how the tool works internally* with *what the agent must do and never do*, at the cost of three minor simplifications above — none load-bearing, since each refusal prints a self-describing stderr line.

VERDICT: PASS
