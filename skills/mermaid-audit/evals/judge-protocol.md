# Consensus eval — judge protocol

Measures whether the color/shape rules are objective enough that independent
agents agree. The orchestrator dispatches **K=5** fresh `general-purpose`
subagents (model: `sonnet`), each judging the SAME fixtures with NO shared
context, then scores agreement with `score_consensus.py`.

## Per-judge prompt (verbatim; substitute `<FIXTURES_DIR>` and `<RULES_TABLE>`)

```
You are a Mermaid diagram reviewer. For each .md file in <FIXTURES_DIR>, read the
```mermaid block and decide which of these rules it violates. Apply each rule as a
binary gate — flag only a clear hit.

<RULES_TABLE>   # the C1/C2/C3/C5/S1/S3/S4 rows from SKILL.md

Return ONLY JSON: {"<filename>": ["<rule-id>", ...], ...}. Empty list if clean.
Do NOT run any script; judge by reading. Do not explain.
```

## Scoring

1. Save each judge's JSON to `evals/verdicts/judgeN.json`.
2. Run:
   `python3 evals/score_consensus.py --gold evals/fixtures/gold.json --verdicts evals/verdicts/`
3. **Pass bar:** every rule in gold is `rule_well_formed: true` (≥80% of judges
   concur on each violating fixture) AND every clean fixture has
   `false_positive_rate ≤ 0.2`. A WEAK rule means the wording is too subjective —
   tighten it in SKILL.md and re-run.
4. Cross-check judges against the deterministic analyzer:
   `python3 scripts/mermaid_style.py evals/fixtures/` — the analyzer's flags are the
   reference for the computable rules (C1/C2/C3/C5/S1/S3/S4); judges should match it.

## Note on geometry (R-rules)

R1/R2/R3 are **pixel-measured** from the rendered PNG, not judged by reading source —
so they're validated by the deterministic tests in `tests/test_mermaid_style.py` and a
render check (`audit_mermaid.py` on a deliberately-wide diagram), **not** by this judge
panel. Judges can't reliably estimate rendered dimensions from text.
