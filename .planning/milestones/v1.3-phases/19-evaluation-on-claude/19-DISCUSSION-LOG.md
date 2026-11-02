# Phase 19: Evaluation on Claude - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-23
**Phase:** 19-evaluation-on-claude
**Mode:** --analyze (a trade-off analysis was presented before each question). The discussion
was held in Spanish at the user's choice; this log is in English per the project constraint.
**Areas discussed:** Pressure scenarios, Smoke target, resolve-model matrix, skill-judge gate

---

## Pressure scenarios

- RED/GREEN was explained first:
  - RED: a subagent without the skill, recording failures and rationalizations;
  - GREEN: the same scenario with the skill.
- **Scenarios** (multi-select): B (Claude Rigorous) ✓, C (opencode + routers) ✓,
  D (existing v1 config) ✓, E ("just apply it") ✓. Option A (Claude MVP) was not offered as a
  separate choice because E covers it.
- **Baseline:**
  - both, on B and D ✓
  - no skill only
  - v1 only

## Smoke target

- **Question: where does the live smoke run?**
  - a copy of this repo's config plus an empty scratch project; dry-run only on ai-kit ✓
  - an empty scratch project only
  - include a real apply on ai-kit

## resolve-model matrix

- **Combinations:**
  - 5 (3 rigors × adaptive, plus quality and budget in Standard) ✓
  - 3
  - all 12
- **Run as:**
  - an automated test plus a live run ✓
  - a test only

## skill-judge gate

- **Bar:**
  - ≥96 with v1 as reference ✓
  - no regression, ≥105
- **On failure after 3 iterations:**
  - ask with the evidence ✓
  - block the phase

## Claude's Discretion

- The evidence file names and locations.
- The subagent model and effort.
- The scenario prompts and fixtures.
- The test module layout.

## Deferred Ideas

- The decision on v1's future → a later milestone.
- The cursor and pi scenarios → Phases 21/22.

---

# Update 2026-10-14 (assumptions mode)

**Mode:** assumptions (`--analyze --all --batch`, lean calibration), jev screening, best over easy, CodeGraph
**Input:** `19-SPEC.md` (a5b3fab) plus the locked D-01..D-07. The analyzer (sonnet, 49 tool calls) verified the `GSD_HOME` copy source, the policy-before-omit order, `config-set model_policy null` rejection, which values gsd-tools rejects at write time, and the installed-skill symlink pointing at the main checkout.

| Item | Laya | TypeSafe | Outcome |
|---|---|---|---|
| C1 matrix | both_plus_controls 0.61 (fb) | both_plus_controls 0.97 | D-09 |
| C2 oracle | expected_field 0.45 (fb) | independent_oracle 0.79 | D-10 |
| C3 fixtures | frozen 0.82 | runtime_builder 0.99 (second opinion) | **Laya overridden:** frozen fixtures can make a scenario unfailable (D-11) |
| C4 harness | agent_jsonl 0.38 (fb) | headless_claude_p 0.99 | D-12 (refines the "subagent" wording) |
| C5 smoke home | bash 0.40 (fb) | tests_helper 0.59 (fb) | **Own reasoning:** dev-only `tests/` helper, following the `wizard_fixtures.py` precedent (D-13, ledger) |
| C6 forced failure | real_rejection 0.69 (fb) | real_rejection 1.00 | D-14 |

No user corrections. D-01/D-02 were refined (headless fresh-context runs), not replaced.
