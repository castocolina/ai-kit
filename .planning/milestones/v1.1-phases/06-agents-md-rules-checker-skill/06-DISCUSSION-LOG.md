# Phase 6: AGENTS.md Rules Checker Skill - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-10
**Phase:** 6-AGENTS.md Rules Checker Skill
**Areas discussed:** Wrap mechanism, Stack-aware tooling research, Report format, Ruleset scope, Enforcement mode

---

## Wrap mechanism

Options presented:
- Programmatic invoke — checker calls `/agent-md-refactor` as step 1, then runs the house-rule check as step 2 (recommended)
- Sequenced but independent — documented two-step workflow, no runtime coupling
- Check-only, refactor optional — house-rule check standalone, refactor only recommended

**User's choice (free text):** Reframed the mechanism entirely — the checker maintains a ruleset and feeds missing rules to `/agent-md-refactor` as input, letting that skill do the actual placement concisely, respecting its own format, preserving rule intent, most-critical-first.
**Notes:** For near-miss existing wording: recommend/warn rather than force a rewrite; start lenient, iterate later.

---

## Stack-aware tooling research

Options presented:
- Cache + staleness re-check (recommended) — research once per stack, cache findings, re-research if stale
- Always fresh research — dispatch a research subagent every invocation
- Skip research for hardcoded example stacks (go/python/node/java)

**User's choice:** Cache + staleness re-check (recommended option).
**Notes:** User raised this area spontaneously, drawing a direct parallel to the ruleset's own theory→hypothesis→spike (rule 15) and stale-knowledge-verification (rule 14) rules — recommending tooling for an unresearched stack from training data alone would repeat the mistake those rules exist to prevent. Research scope: formatting, security-leak detection, code-smell/dead-code/duplication, full test pyramid (unit/integration/e2e/arch), fail-fastest ordering, pre-commit vs. pre-push split.

---

## Report format

Options presented:
- Both: inline + opt-in file (recommended)
- Inline only
- Always written to a file

**User's choice:** Inline only.
**Notes:** User rejected a persisted report file outright — git already is the history of AGENTS.md changes; a file explaining why another file was edited is exactly the kind of file not wanted. Extended rule 10 to explicitly call out `./tmp/docs` for any ephemeral documentation. Also gave direct feedback to stop using markdown pipe-tables for trade-off analysis — switched to header/bullet format for the rest of this session (saved as a feedback memory).

---

## Ruleset scope

Options presented:
- Hardcoded, as structured data (recommended)
- Hardcoded, as prose
- Externalized from day one

**User's choice:** Hardcoded, as structured data (recommended option), deferring to the recommendation after asking for clarification on prose-vs-data.
**Notes:** User's real ask was conditionality — rules should be applicable under conditions (tool presence, project applicability), not flagged universally. Drew a parallel to Phase 3's Tool-Substitution Awareness Hook (live rtk verification) as the pattern to reuse for tool-presence conditions.

---

## Enforcement mode

Options presented:
- Always confirm before writing (recommended, citing PROJECT.md's Core Value)
- Auto-apply, confirm only on near-miss

**User's choice:** Auto-apply, confirm only on near-miss.
**Notes:** Went against the recommendation. PROJECT.md's "every config write confirmed" Core Value line is scoped to runtime CLI config files (opencode.jsonc/Codex TOML/Claude JSON) — a different artifact class from AGENTS.md — so this isn't a contradiction of that constraint.

---

## Claude's Discretion

- Exact schema/shape of the per-rule data structure and the stack-refs cache file format/location.
- Exact closeness heuristic for near-miss wording detection — explicitly meant to be a first-pass approximation, improved iteratively.

## Deferred Ideas

None — discussion stayed within Phase 6 scope.
