# Skill Evaluation Report: ai-kit-gsd-curated-config

## Summary
- **Score**: 109/120 (91%) — Grade A, but **not pass-ready**: one Critical defect remains
- **Pattern**: Process (phased v2 pipeline with checkpoints) + Tool-style decision tables
- **Knowledge ratio**: E:A:R ≈ 85:13:2
- **Changes since 5b4ec21 verified against gsd-core source** (`.claude/gsd-core/bin/lib/init.cjs:3681-3762`, `security.cjs:177-233`): the skip rules, `~`/`~/` expansion, non-existent/fs-root/home-dir root rejection, namespaced-skip-on-non-claude, and project-path containment claims are all accurate. The refusal wiring (plan_edit.py:137,178; apply.py:907; exit-2 mapping cli.py:635) matches SKILL.md's exit-code and "before any write" claims.

## Dimension Scores

| Dimension | Score | Max | Notes |
|---|---|---|---|
| D1: Knowledge Delta | 18 | 20 | Near-pure verified operational delta (rollback states, permissions matrix, skip rules); minor restatement cost |
| D2: Mindset + Procedures | 14 | 15 | "Ask yourself: trusted checkout?" prompts + refusal→action map with non-obvious ordering |
| D3: Anti-Pattern Quality | 14 | 15 | Specific NEVER list with non-obvious whys ("never describe a v2 codex target as sandboxed") |
| D4: Spec Compliance / Description | 15 | 15 | WHAT + WHEN + four quoted trigger phrases + boundary statement |
| D5: Progressive Disclosure | 14 | 15 | 354 lines; both references have read-when triggers and a Do-NOT-load line |
| D6: Freedom Calibration | 15 | 15 | Fragile config writes get exact argv, code-enforced refusals, gated `--force` |
| D7: Pattern Recognition | 9 | 10 | Clean Process pattern + subcommand reference table |
| D8: Practical Usability | 10 | 15 | Excellent failure-state tables, but the printed fix in Finding 1 is destructive when followed as SKILL.md instructs |

## Findings

**1. CRITICAL — the refusal's printed "second fix" drops every healthy bare-name skill.** `plan_io.py:716-746`: `_round_trip_name` recognizes only `skills/<name>` and `global:<name>` forms, but a fresh recommend plan's `agent_skills.*` entries hold **bare names** (`recommend.py:1102-1111` passes `names` verbatim). Empirically verified: `_kept_names(["jev","ponytail"], ["jev"], inv)` → `keep: []`, note "ponytail cannot round-trip through a bare name". So when a trusted root is declined (or apply refuses a stale plan), the printed fix is `plan-set agent_skills.<agent> []` — and SKILL.md:261-263 explicitly directs "declining means the second one, `plan-set agent_skills.<agent> ...`". Following the skill verbatim wipes the agent's healthy skills, contradicting `plan_io.py:728-735`'s "never dropped … silently" and SKILL.md:263-267. **Fix**: in `_kept_names`, append a non-skipped bare item straight to `keep` when `skills_mod.locate(item, inv)` resolves (guard shadowing as the `global:` branch does); pin with a test using a bare name in a `set` entry.

**2. IMPORTANT — SKILL.md:263-267 blesses the buggy enumeration.** "keeps every healthy reference whose bare name re-resolves to it (`skills/<name>`, and a `global:<name>` …)" omits bare names — the primary plan form — so the doc contradicts both the code docstring and its own "never dropped or switched" sentence in the same bullet. **Fix**: after Finding 1, amend the enumeration to "a bare name, `skills/<name>`, and a `global:<name>` …".

**3. IMPORTANT — the test suite pins the wrong surface.** `tests/test_curated_config_apply.py:2748-2762` and `tests/test_curated_config_plan_edit.py:1161` feed `_kept_names`/`skipped_skill_problem` only `global:`/`skills:`/path forms — never the bare-name form every fresh plan uses, which is exactly why Finding 1 shipped. **Fix**: add the bare-name `set`-entry case asserting the healthy name survives `keep` and does not appear in the "cannot round-trip" note.

**4. Minor — live re-check is conditional, doc states it unconditionally.** SKILL.md:271-275 says kept entries are "revalidated live", but `plan_io.py:606-608` (`_live_global_problem`) returns None when inventory recorded no host skills dir (`host_skills_dir` → None), degrading to snapshot-only with no disclosure. Add "(when inventory recorded the host skills dir)".

**5. Minor — trusted-root decline rules stated three times** (SKILL.md:35, 122-128, 258-267) with overlapping wording; ~10 lines savable without losing a rule.

**6. Minor — "detected by two marker skills" (SKILL.md:246)** never names them; they live only in `skill_scan.py:38`. Name them once so an executor can verify the trust claim.

Top improvement: fix Finding 1 — it is the only blocker; everything else is polish on an otherwise rigorously verified skill.

DIGEST 7d0b37f068c3f41b
CURRENT 109/120
CRITICAL 1 IMPORTANT 2
