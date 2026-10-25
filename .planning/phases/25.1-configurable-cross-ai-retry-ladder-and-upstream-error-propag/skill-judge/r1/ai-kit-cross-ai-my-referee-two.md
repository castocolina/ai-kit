Judge: my-referee-two
Reviewed-sha256: 5d18a6276c145c97dbc38991579989c8c093267004f9a4428d4de651c5e0bd1e
Lane: AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=314s out=347021 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
Score: 105
Critical: 0
Important: 2

All claims verified against the runner source. Here is the evaluation report.

# Skill Evaluation Report: ai-kit-cross-ai

**Scope judged:** `skills/ai-kit-cross-ai/SKILL.md` (163 lines) + `references/launch-and-wait.md` (113) + `references/subprocess-quota-policy.md` (175), diffed at `35a0368~1..HEAD` (all three files new in Phase 25.1). Every load-bearing factual claim was checked against the runner template `skills/ai-kit-spec-review/references/cross-ai.mjs` (9,985 lines): exit table (STATUS_TABLE :1159–1182, exact match), retry defaults (:2915–2916), `--runtime`/`--prefer` first-entry semantics (:4258–4274), heartbeat format (:3605), copilot stdin-ignored (:3267–3271), pi `--skill`-only review extras (:1382), overlay 50 ms (:1656), `--classify-only` (:4220), 300 s GSD default (:111), self-test case names `auth`/`hard-tier-transient-cycle0`/`hard-tier-stopped-refused` (:5768/:6161/:6309). The never-switch rule (SKILL.md §8, policy ref) matches runner behavior, and the skill nowhere instructs a harness/provider/model switch. Sibling pointers (`ai-kit-spec-review`, `ai-kit-spec-config`, `ai-kit-spec-execute-gsd`, `ai-kit-spec-execute-superpowers`, `ai-kit-gsd-curated-config`) all point back correctly with "Never switch harness, provider or model."

## Summary
- **Total Score:** 105/120 (87.5%) — Grade B
- **Pattern:** Tool (decision table + exact commands + on-demand policy references)
- **Knowledge Ratio:** E:A:R ≈ 78:17:5
- **Verdict:** An accurate, high-delta operational contract for the cross-AI runner — verified correct against the code it documents — with two clarity gaps in its core "read the result" path and ~half of one reference file spent on duplication.

## Dimension Scores

| Dimension | Score | Max | Notes |
|-----------|-------|-----|-------|
| D1: Knowledge Delta | 17 | 20 | Nearly all runner-specific semantics; only real waste is the repeated foreground-wait blocks |
| D2: Mindset + Procedures | 13 | 15 | Ownership thinking ("config edit, never a post-failure choice"; "only action past a stop is notify") + an 8-step caller procedure |
| D3: Anti-Pattern Quality | 14 | 15 | Expert NEVERs with non-obvious whys (skip→harness switch, argv-prompt/stdin, PID-not-pattern, upstream hints are data) |
| D4: Spec Compliance / Description | 14 | 15 | WHAT+WHEN+keywords+negative scope; valid frontmatter |
| D5: Progressive Disclosure | 12 | 15 | Contextual links at point of need; no "Do NOT load" guidance; duplication inside one reference |
| D6: Freedom Calibration | 14 | 15 | Fragile protocol → exact commands, exact table, verbatim notice; correctly rigid |
| D7: Pattern Recognition | 9 | 10 | Disciplined Tool pattern at 163 lines |
| D8: Practical Usability | 12 | 15 | Full exit-code decision tree and real self-test samples; two unresolved ambiguities (findings 1–2) |

## Findings

**Critical** — none. The policy is described correctly, the pointers are correct, and nothing in the skill switches harness, provider or model.

1. **Important** — "Status file" is used four times but never defined, and the runner writes no such file. SKILL.md:64–65 reads "Both are already on disk: the status file, the `.err` file and the last stderr line" — three nouns for "both", and launch-and-wait.md:23 implies the "status file" *is* `lane.err`. Evidence: `skills/ai-kit-cross-ai/SKILL.md:58,64-65,104`, `references/launch-and-wait.md:8`; no `status file`/`statusFile` exists in `cross-ai.mjs` (only the hard-tier state file, a different thing). A fresh agent will hunt for a file that doesn't exist. **Fix:** define once in §2/§4 — "the lane's `.err` file is the status file" — and delete the two other namings.

2. **Important** — Lane scratch-file placement is unaddressed and can trip the skill's own dirty-tree rule. The examples write `lane.out`/`lane.err`/`lane.pid` into cwd (repo root, since the command resolves `.planning/scripts/cross-ai.mjs` relatively), and `echo $! > lane.pid` lands *after* the runner starts — a new untracked file mid-run, which the tree signature (`stateSig`, cross-ai.mjs:3171–3178, porcelain-based) may catch as `contract_violation tree=dirty` on a review lane. SKILL.md:58–60 says "Never edit the tree while a review lane runs" but never says where lane files go. Evidence: `skills/ai-kit-cross-ai/references/launch-and-wait.md:17-21` vs `SKILL.md:151-152`. **Fix:** one line in §2: write lane files outside the repo (or a gitignored dir), because a file created mid-run dirties the tree.

3. **Minor** — `launch-and-wait.md` repeats the identical 5-line foreground-wait block six times (~55 of 113 lines); only `--runtime` differs. Evidence: `references/launch-and-wait.md:43-100,108-112`. **Fix:** one parameterized block with `--runtime "$RUNTIME"` plus a one-line list of runtime ids; keep the Claude Code and copilot-argv notes.

4. **Minor** — Ambiguous pronoun: "`--timeout` is the inner deadline and `--outer-timeout` replaces it as the outer deadline" (`SKILL.md:53-54`). "It" reads as the inner deadline; the runner says `--outer-timeout` "replaces the GSD lookup" (cross-ai.mjs:36). **Fix:** "`--outer-timeout` replaces the GSD-derived deadline as the outer deadline."

5. **Minor** — Unresolved decision-log ids: `(D-02)`, `(D-03)`, `(D-10)`, `D-13`, `D-08` appear with no pointer to where the D-series is defined. Evidence: `references/subprocess-quota-policy.md:47,74-75,83`; `subprocess-quota-policy.md:12` context. **Fix:** one footer line naming the decisions file, or drop the ids.

DIGEST 5d18a6276c145c97
CURRENT 105/120
CRITICAL 0 IMPORTANT 2

## Runner evidence

```
AIKIT-XAI status=ok cli=opencode model=router-env/my-referee-two exit=0 cli_rc=0 elapsed=314s out=347021 tree=clean action=stop route=router rule=- pattern=none attempts=1 cycles=0
```
