# Skill Evaluation Report: ai-kit-gsd-spec-discuss

**Summary** — 114/120 (95%), Grade A. Pattern: Process (~280 lines) with Tool-style decision trees in references. Knowledge ratio ≈ 85:13:2 (E:A:R). All three change areas since 5b4ec21 were live-verified against the installed gsd-core (`.claude/gsd-core/bin/lib/init.cjs`) and hold up: the reason/warning taxonomy in `agent-skills-diagnostics.md` matches `cmdAgentSkills`/`buildAgentSkillsBlock` exactly (including the stderr-only `configured_empty` warning at init.cjs:3860-3863 and the non-claude persona fallback producing `resolved`-with-warnings at init.cjs:3808-3833+3865-3870); the symlink-escape / `trusted_global_roots` skip is init.cjs:3717-3726; `decide.py` never names a forced column in `decided_by` (decide.py:524 — winner only when `fallback is False`); and the two agents named as jev-wired match `skill_affinity.json:42-50` exactly. Verdict: expert-grade orchestration skill, one stale summary line away from clean.

## Dimension scores

| Dimension | Score | Max | Notes |
|---|---|---|---|
| D1: Knowledge Delta | 19 | 20 | Nearly pure expert content (gsd-core internals, client semantics, fail-closed gates), all verified |
| D2: Mindset + Procedures | 14 | 15 | "You are the decider; evidence beats confident Laya" + exact verified command sequences |
| D3: Anti-Pattern Quality | 15 | 15 | Nine NEVERs, each with a non-obvious mechanism (`--assumptions` routes to a no-write listing workflow; config flips crash mid-run) |
| D4: Specification Compliance | 15 | 15 | Valid frontmatter; 719-char description with WHAT + WHEN + keywords + negative scope |
| D5: Progressive Disclosure | 15 | 15 | Mandatory/conditional triggers at the workflow point of use + explicit "Do NOT load" rules |
| D6: Freedom Calibration | 15 | 15 | Exact literals and exit-code gates where fragile; principles where judgment applies |
| D7: Pattern Recognition | 9 | 10 | Process hybrid; slight reference-detail duplication in §3 |
| D8: Practical Usability | 12 | 15 | Verified end-to-end, but two contradictions/omissions around the new semantics |

## Findings

**Critical** — none.

1. **Important — stale "low" definition contradicts the forced-column rules.** `SKILL.md:199-200` says: "Every answering column low (`fallback: true`, the client's `needs_fallback`) or errored → own reasoning". But a *forced* column also has `fallback: true` (decide.py:478 maps the client's `needs_fallback` straight to the column's `fallback`; forced = `fallback: true` with `top` ≥ threshold), and the new forced branches (`references/decision-table.md:16-30`) say a forced-consistent column is *taken*, not reasoned-over. Read literally, the bullet routes every forced column to own reasoning — for a blocking item that means an unnecessary stop-and-ask in an otherwise unattended run. The mandatory-loaded decision-table has the correct rule and SKILL.md:188-191 defers to it, but the summary line contradicts it two paragraphs later. **Fix:** qualify the bullet — "Every answering column low (`fallback: true` with `top` below its backend's threshold, or errored; a forced column takes the forced-branch check in decision-table.md first) → own reasoning".

2. **Important — the trusted-roots acceptance NOTE is undocumented in the stderr taxonomy.** gsd-core writes `[agent-skills] NOTE: Global skill "…" accepted via trusted_global_roots (resolves outside the default skills dir)` directly to stderr (init.cjs:3726 — deliberately not a warning, never in JSON `warnings`). Step 8's cleanliness rule (`SKILL.md:84-85`) scans `<tmp>.err` for warnings, and `references/agent-skills-diagnostics.md:18-27` enumerates every warning cause except this one line — which is precisely the line that appears in the *blessed* symlinked-ai-kit configuration this change set exists for. An executor can misreport a clean agent as not clean and suggest a needless curated-config re-run. **Fix:** add one bullet to `agent-skills-diagnostics.md`: "A `[agent-skills] NOTE … accepted via trusted_global_roots` line in `<tmp>.err` is an acceptance trace, not a warning; the agent is clean."

3. **Minor — decision-table header definition doesn't name the third state.** `references/decision-table.md:3-5` defines "High" as "a column's `fallback` is false", which leaves a forced column (fallback true, top ≥ threshold) in an undefined limbo until the Forced-columns paragraph rescues it. **Fix:** append "(a forced column is a third state — see Forced columns below)".

4. **Minor — dangling "its" in the interactive-path sentence.** `SKILL.md:158-160`: "In the interactive path the analyzer runs only when the user asks for it; otherwise its prompts come straight from the user." Standard discuss-phase never spawns the analyzer (no `gsd-assumptions-analyzer` reference in gsd-core's `discuss-phase.md`), so "its prompts" has no clear referent — it means the workflow's prompts. **Fix:** "…otherwise the workflow's prompts are answered straight by the user."

Ponytail footer — Skipped: running the three scripts' full test suites (read-only task; their CLI contracts were verified by reading the argparse/exit paths instead) and the `jev-fast-decision` client's own code (its `reference.md` owns the threshold numbers; the claims here are interface-level and match decide.py). Risk: findings 1–2 are judged on gsd-core as installed at `.claude/gsd-core` today; a different gsd-core version could shift the exact warning strings.

DIGEST e503d04af5ca6b78
CURRENT 114/120
CRITICAL 0 IMPORTANT 2
