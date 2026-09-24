# Phase 17: Curated-Config Inventory & Recommendation Engine - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-23
**Phase:** 17-curated-config-inventory-recommendation-engine
**Mode:** --analyze (a trade-off analysis was presented before each question)
**Areas discussed:** Native tier maps, Price ceiling, Undecidable slots, Existing config

---

## Native tier maps

**Question: when should `model_profile_overrides.<host>.<tier>` be written on non-claude hosts?**
- Only when the native slot is invalid (not on the host's list, or over the ceiling) ✓
- Always write all three slots
- Native slot plus a score-margin upgrade

**Evidence presented:** gsd-core 1.14's `RUNTIME_PROFILE_MAP`:
- claude = `claude-opus-4-8`, `claude-sonnet-5`, `claude-haiku-4-5` (stale, but aliases are
  used);
- codex = `gpt-5.6-sol`/`terra`/`luna`;
- opencode = `anthropic/claude-*`, which is not in the user's 81-model opencode list.

## Price ceiling

**Question: how should the rigor price ceiling work?**
- A relative percentile of the host's eligible models ✓
- Absolute $/1M caps
- A price weight only

**Question: how are models with unknown price (e.g. router-env/*) handled?**
- The user's free-text answer: "That models are ready analyzed by user".
- Follow-up question: how should user-analyzed router models be treated?
  - Preferred for their declared role, exempt from the cap ✓
  - Exempt from the cap only
  - Let me explain

## Undecidable slots

**Question: how should `plan.json` represent slots `recommend` can't decide?**
- `needs_choice` entries; `apply` refuses until they are resolved; deterministic ties; missing
  specialists get a warning ✓
- A low-confidence guess
- Omit the key and add a note

## Existing config

**Question: how should existing values in plan-managed families be treated?**
- Authoritative, with a visible `op: unset` for stale entries and the existing value on every
  entry ✓
- Additive only
- Ask per conflict

## Claude's Discretion

- The percentile values per rigor.
- plan.json schema details.
- Skill-scan depth.
- The layout of the mapping tables.

## Deferred Ideas

None.
