# Skill Evaluation Report: ai-kit-gsd-spec-discuss

## Summary
- **Total Score**: 114/120 (95%) — **Grade A**
- **Pattern**: Process (phased workflow: setup → per-phase spec/discuss → close-out) with a Tool-pattern core (decision table + exact scripts)
- **Knowledge Ratio**: E:A:R ≈ 80:18:2
- **Verdict**: A dense, verified expert brain — nearly every line carries machine-specific knowledge I could check against the actual gsd-core source, and it all matched.

## Dimension Scores

| Dimension | Score | Max | Notes |
|-----------|-------|-----|-------|
| D1: Knowledge Delta | 19 | 20 | Near-pure expert delta: resolver/host behaviors, forced-vs-fb semantics, measured Laya non-determinism, workflow routing traps |
| D2: Mindset + Procedures | 14 | 15 | "You are the decider" framing; non-obvious orderings (skip workflow's `git_commit`/`update_state`/`auto_advance`; pacing constraint §7) |
| D3: Anti-Pattern Quality | 15 | 15 | 9-item NEVER list, each with a mechanism-level why; neutral-labels rule with the mirroring rationale |
| D4: Spec Compliance | 15 | 15 | name valid; description 719 chars with WHAT/WHEN/KEYWORDS, negative scope, no-backend note |
| D5: Progressive Disclosure | 15 | 15 | 286 lines; every reference has a conditional trigger incl. "only when an agent is not clean" and "only when a case is unclear"; Do-NOT-load guidance present |
| D6: Freedom Calibration | 14 | 15 | Lowest freedom exactly where bytes are parsed (log formats, edge floor, consent); highest where judgment is the product; one fragile manual-parse task under-specified (finding 1) |
| D7: Pattern Recognition | 9 | 10 | Clean Process skeleton + Tool core; deliberate, coherent hybrid |
| D8: Practical Usability | 13 | 15 | Mentally-testable decision rows, closed-set error codes with next actions, host-gap disclosures; two guidance gaps below |

## Verification of the diff's core claims (all checked against the live gsd-core checkout)
- `query agent-skills <agent> --json` exists (`gsd-tools.cjs:3019,4812`); the four reason values, the stderr-only `configured_empty` warning, and the non-claude persona-fallback that can mask all-skipped as `resolved` all match `init.cjs:3648–3867` exactly. The `NOTE … trusted_global_roots` line uses raw `stderr.write`, not `warn()`, so it truly never lands in the JSON warnings — the skill's "not a warning" carve-out is code-true.
- Quoted warning causes ("failed path check (symlink escape?)", "not confined to the project directory", "not found") match `init.cjs:3714–3759` verbatim; `agent_skills_security.trusted_global_roots` is real (`security.cjs:166–179`), and the fix pointer `ai-kit-gsd-curated-config` exists and owns exactly that wiring.
- "Analyzer never calls jev even when wired in": consistent across SKILL.md:158–165, analyzer-brief.md:47–48, with the advisor one-liner; `init.phase-op` indeed carries no analyzer model while `discuss-phase-assumptions.md:74` resolves it via `resolve-model --raw`, as §2 states. `phase.mvp-mode`, `state record-session`, `roadmap analyze`, `commit --files` all exist; `spec-phase.md` indeed never parses `--ws`.
- `decide.py`'s new `forced` flag matches the client's emitted field (`jev_review.py:1578`), and `fill_columns` (decide.py:528) never lets a forced rung become `decided_by` — the decision-table's central new claim holds. The `(fb)`/(forced) vocabulary is consistent across SKILL.md §3, decision-table.md, and log-formats.md.
- The `phase_range.py` `.strip()` fix verified live: `--list "17, 17.1"` (space after comma) now parses; previously it died as "invalid roadmap JSON".

## Critical Issues
None.

## Findings

1. **Important** — §0 step 8's cleanliness predicate is underspecified at the `.err` boundary. SKILL.md:88–89 says clean = "`reason: resolved` with no warnings in the JSON **or in its `.err` file**", and agent-skills-diagnostics.md:28 says "any other warning: report it verbatim" — but neither says a warning must carry the `[agent-skills] WARNING` prefix, while the same `query agent-skills` invocation can put unrelated gsd-core stderr (degraded-config notices, deprecation output) in the same `.err` file. Risk: false "not clean" verdicts, spurious reference loads, noise reported verbatim to the user. **Fix**: scope both mentions — "`.err` lines beginning `[agent-skills] WARNING`" (the NOTE carve-out already establishes the prefix pattern; finish it).

2. **Important** — Explicit range vs an executed/complete phase is a decision point with no guidance (predates this diff, but the diff's "get the roadmap first, for every case" now routes every explicit request through the filter). phase_range.py:137–139 places executed/complete phases in `skipped` even when explicitly requested, while SKILL.md:286 says "An explicit range or list still runs that phase" — narrowly about SPEC/CONTEXT-current skips, but easy to over-read as overriding all skip reasons. **Fix**: one clause in §0 step 4, e.g. "a phase the script skips as executed/complete under an explicit request needs the user's confirmation before re-running".

3. **Minor** — worked-examples.md:1–3 claims the file is "from the ai-kit v1.3 run" and "each shows what the models said", but §6 (added in this diff) is illustrative-only and honestly says so; the file header overclaims provenance for the whole file. **Fix**: "examples 1–5 from the v1.3 run; 6 illustrative" in the intro line.

4. **Minor** — Two different sibling-discovery root lists coexist: SKILL.md:26–27 hardcodes `$HOME/.claude/skills`, … with no `CLAUDE_CONFIG_DIR`/`CURSOR_CONFIG_DIR` overrides, while decide.py:95–105 honors those env vars. Benign today (the own-dir probe in step 1 hits first), but the lists can drift apart. **Fix**: a one-line note that step 1's loop mirrors decide.py's fallback order, or drop the redundant host roots and keep only the own-dir probe.

5. **Minor** — Untracked `scripts/__pycache__/*.pyc` files (8) sit inside the skill directory. The skill is symlinked into host skills dirs, so stale bytecode ships beside the scripts. **Fix**: delete them; decide.py already runs the client with `-B`.

Skipped: no baseline score to compare regression against (none provided); did not run the Textual/PTY test tiers or execute a real ladder call against a live backend (would need network + consent). Risk: findings 1–2 rest on code reading, not a reproduced misfire.
