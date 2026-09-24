# Phase 16: ai_kit_spec Extensions - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-23
**Phase:** 16-ai-kit-spec-extensions
**Mode:** --analyze (a trade-off analysis was presented before each question)
**Areas discussed:** Detection order, Claude model list, Catalog fields, Ranker & cache

---

## Detection order

**Question: how should the new host precedence roll out?**
- Global spec order, replacing 01.2 D-02 for every caller ✓
- Keep the old `detect-current-runtime` and add a new ordered function only for curated-config
- You decide

**Question: which env vars mark a codex host?**
- `CODEX_THREAD_ID` or `CODEX_VERSION`; drop `CODEX_SANDBOX` ✓
- The spec as written (`CODEX_THREAD_ID`/`CODEX_SANDBOX`, replacing `CODEX_VERSION`)
- All three

**Evidence presented:**
- A grep of `~/.codex/sessions` found `CODEX_THREAD_ID` 20 times (from the shell-snapshot
  preamble), `CODEX_VERSION` 4 times and `CODEX_SANDBOX` 0 times.
- `PI_CODING_AGENT` was confirmed in the installed pi package source.

## Claude model list

**Question: where should the claude model list come from?**
- Hybrid: hardcoded aliases, full ids from models.dev via the catalog, and a dated fallback ✓
- Hardcoded only
- models.dev only

**Question: how should detection find wrapped CLIs (cursor-agent is a shell function)?**
- The user's free-text answer: "I said we need focus on opencode, codex and claude and defer
  cursor and Pi".
- Outcome: cursor wrapper handling moves to Phase 21 and pi enumeration to Phase 22
  (SPEC-05/SPEC-06 split out of SPEC-02). The pi env signal stays in the precedence tuple.

## Catalog fields

**Question: what should the reasoning-level field be called?**
- Reuse the existing `reasoning_modes` ✓
- A new `reasoning_levels` field

**Question: how is `image_input` sourced, and how is unknown handled?**
- models.dev modalities, then opencode `--verbose`; absent means unknown ✓
- models.dev only
- Default to `false`

## Ranker & cache

**Question: how should the mechanical purpose enforce "cheapest above a minimum coding score"?**
- An optional floor in the TOML; a missing floor axis means the candidate is excluded ✓
- Weights only
- Put the floor in Phase 17's `roles.py`

**Question: how do pre-existing caches get refreshed?**
- A `schema_version` bump: missing or older means stale ✓
- A manual `--refresh`

## Claude's Discretion

- The weight values for the new purposes and the mechanical floor's default.
- The `schema_version` representation.
- The codex `debug models` parser shape, taken from captured output.
- Where the claude dated fallback list lives.

## Deferred Ideas

- Pi model enumeration → Phase 22 (SPEC-05).
- Cursor wrapper resolution → Phase 21 (SPEC-06).
