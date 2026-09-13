# Constraints (from SPECs)

One SPEC-type document in this ingest set:
`docs/superpowers/specs/2026-09-12-ai-kit-rules-skill-family-design.md`
(manifest precedence `0` — higher precedence than the sibling DOC in this
same batch, precedence `1`; see `context.md` for the DOC's recorded
deviations from this SPEC, auto-resolved in this SPEC's favor per
precedence, and `../INGEST-CONFLICTS.md` INFO section for the rationale
trail).

---

## Checker-skill scope boundary
- source: docs/superpowers/specs/2026-09-12-ai-kit-rules-skill-family-design.md
- type: protocol
- content: Each checker skill in the `ai-kit-project-rules-*` family **detects
  and reports findings only** — it never edits the target repo's files.
  Applying a fix is a decision for whoever invoked the checker. The one
  existing exception that carries forward unchanged: `ai-kit-project-rules-
  agents`'s hand-off to `/agent-md-refactor` for AGENTS.md content, since
  that is a pre-existing, already-designed mechanism specific to that one
  file type.

## Shared package import convention
- source: docs/superpowers/specs/2026-09-12-ai-kit-rules-skill-family-design.md
- type: protocol
- content: Domain-agnostic infrastructure lives in `skills/_shared/
  ai_kit_rules_common/`. Every checker skill imports it via a relative
  `sys.path` insert from its own `__file__` — no skill imports another
  skill's package directly, so each checker skill remains independently
  copyable to a different host (only `_shared/` must travel with it).
  Components: classification engine (`evaluate_condition`, `_classify_flat`,
  `_classify_plain_groups`, `_classify_tool_scoped_groups`, generalized to
  take any rules tuple + text), `tool_presence.py` (binary/marker-on-PATH
  detection), `stack_cache.py` (generic per-`(skill_name, stack)` cache
  read/write/validate helpers, one cache namespace per skill at
  `~/.cache/ai-kit/<skill-name>/stack-refs/<stack>.json`), `remediation.py`
  (single-domain criticality-sort + `auto_apply` split ordering helper).

## Stack-tooling cache schema and staleness convention
- source: docs/superpowers/specs/2026-09-12-ai-kit-rules-skill-family-design.md
- type: schema
- content: Cache payload validation contract — `ALL_TOOLING_KEYS` membership,
  non-empty strings, `(source: ...)` provenance required — keyed generically
  per skill instead of hardcoded to Makefile tooling categories. Research
  step (WebFetch/WebSearch for current recommended tool per category) fires
  only when no per-stack cache entry exists, or the cached entry's timestamp
  is older than **180 days**.

## Cross-skill remediation merging ownership
- source: docs/superpowers/specs/2026-09-12-ai-kit-rules-skill-family-design.md
- type: protocol
- content: The single-domain `remediation.py` ordering helper (criticality-
  sort + `auto_apply` split) is scoped to one skill's own `remediate` output
  only. Cross-skill merging of findings from multiple checkers is explicitly
  **the orchestrator's (`ai-kit-project-rules-all`) job, not this helper's**.

## Tooling taxonomy (6-category, cross-language)
- source: docs/superpowers/specs/2026-09-12-ai-kit-rules-skill-family-design.md
- type: schema
- content: Every detected tool classifies into exactly one of 6 categories —
  (1) Formatting, (2) Type-checking, (3) Linting/code-quality, (4) Security
  (SAST), (5) Duplicate-code, (6) Dead-code — generalizing to languages not
  yet researched without adding new categories. Two baseline (no-research)
  heuristics apply universally: flag "enable-everything" configs (ruff
  `select = ["ALL"]`, unpinned PMD wildcard, etc.); flag complete absence of
  Duplicate-code or Dead-code category tooling (the two most commonly
  skipped across every ecosystem surveyed). Two tools covering the same
  category is NOT auto-flagged as redundant when they are a confirmed
  complementary fast/narrow + slow/wide pair (see the SPEC's "Confirmed
  redundant-vs-complementary pairs" table for the full per-ecosystem list).
  Known gap, explicitly flagged rather than silently dropped: no equally
  canonical architecture-fitness tool surfaced for Rust or Go (unlike
  Python/import-linter, Node-TS/dependency-cruiser, Java/ArchUnit).
