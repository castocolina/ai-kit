# Skill Evaluation Report: ai-kit-gsd-spec-discuss

**Total Score**: 112/120 (93%) · **Grade**: A · **Pattern**: Process (~289 lines) · **Knowledge Ratio**: E:A:R ≈ 88:9:3

Every factual claim the diff added was live-verified against the actual gsd-core checkout and passed: `query agent-skills --json` field names (`configured`/`reason`/`warnings`), the exact WARNING strings (`failed path check (symlink escape?)`, `not confined to the project directory`, init.cjs:3716/3742), `reason: not_configured` printing nothing and warning nothing (live query confirmed), `agent_skills_security.trusted_global_roots` (security.cjs:166-179), the `${GSD_WS:+--ws=...}` pattern (discuss-phase.md:123-125), `GSD_TOOLS` as the resolver's variable, `not_configured` (init.cjs:3849), `list-phase-assumptions.md` writing no files ("No file output" in its purpose), `--auto` chaining via the `auto_advance` step, the 0.4 todo constant, and the curated-config fix path being real and consistent.

## Dimension Scores

| Dimension | Score | Max | Notes |
|-----------|-------|-----|-------|
| D1: Knowledge Delta | 18 | 20 | Nearly pure delta: host-portability gotchas, gsd-core query semantics, forced-column semantics, consent state machine; tiny mindset/NEVER overlap |
| D2: Mindset + Procedures | 14 | 15 | "You are the decider" + non-obvious procedures (commit replaces workflow steps, edge-floor gating, pacing) |
| D3: Anti-Pattern Quality | 15 | 15 | 10-item NEVER list, all specific with verified WHY; "never call jev even when wired" is a genuine expert landmine |
| D4: Specification Compliance | 14 | 15 | WHAT/WHEN/keywords/negative-scope all present; description slightly over-long |
| D5: Progressive Disclosure | 15 | 15 | 289 lines, MANDATORY triggers at each decision point, explicit "Do NOT load" conditional |
| D6: Freedom Calibration | 14 | 15 | Low freedom where fragile (exact commands, fail-closed gates), decision-table rules for judgment |
| D7: Pattern Recognition | 9 | 10 | Clean Process pattern; 289 vs ~200 lines justified by two run paths |
| D8: Practical Usability | 13 | 15 | Decision trees, fallbacks, error paths all verified working — except one false claim (finding 1) |

## Findings

**Critical** — none.

1. **Important — false claim about where the analyzer model comes from.**
   `skills/ai-kit-gsd-spec-discuss/SKILL.md:159-161`: "when `init.phase-op` reports it installed; **its output also carries the resolved analyzer model value** — omit `model` when that is `inherit` or empty."
   Live-verified false: `query init.phase-op` returns only `agent_runtime`, `agents_dir`, `agents_installed`, `missing_agents` (no model key); `query init.discuss-phase-assumptions` returns none either. The value actually comes from a separate query — `workflows/discuss-phase-assumptions.md:78`: `ANALYZER_MODEL=$(gsd_run query resolve-model gsd-assumptions-analyzer --raw)`, with the omit-when-`inherit`-or-empty rule at line 273. Fix: replace "its output also carries the resolved analyzer model value" with "resolve the analyzer model with `gsd_run query resolve-model gsd-assumptions-analyzer --raw`". Risk if unfixed: an orchestrator trusting this line skips the workflow's resolve-model call and guesses the spawn model.

2. **Minor — description verbosity.**
   `SKILL.md:3`: ~110 words; the two run-mode mechanics parenthetical ("auto (spec `--auto`, discuss in assumptions mode) or interactive…") is body-level detail. Fix: keep WHAT/WHEN/keywords plus "two run modes (auto/interactive)" and let §0/§7 carry the mechanics.

3. **Minor — `consent_used` filter conflates run-level and per-item state.**
   `SKILL.md:88-89`: "announce `consent_used` only for backends whose column is non-null" — `consent_used` is a per-call list (decide.py:553), while "column" is per item; a consented backend can appear in `consent_used` with a null column on a given item. Fix: say "only for backends that answered at least one item in the run".

Note on the repo's own gate (no remaining Important finding, or score ≥ 96): finding 1 predates commit 5b4ec21 (the diff left that sentence as unchanged context) — it is not a regression from this round's changes, but it does keep the skill one Important finding away from that bar.

Skipped: no re-run of the ladder/edge-floor scripts end-to-end (read + code-path checked only); untracked `__pycache__` .pyc files under `scripts/` are on disk but not committed, so not scored. Risk: scores for jev-fast-decision client internals (thresholds, truncation semantics) rest on the skill's own cross-references, not a live client run.

DIGEST fd393fba782b5b56
CURRENT 112/120
CRITICAL 0 IMPORTANT 1
