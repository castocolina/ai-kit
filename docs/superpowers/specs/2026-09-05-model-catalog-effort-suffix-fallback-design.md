# Model Catalog — Effort-Suffix Cross-Source Fallback — Design

**Date:** 2026-09-05
**Status:** Draft, pending user review

## 1. Problem

`docs/superpowers/specs/2026-09-02-model-discovery-curation-design.md` shipped
purpose-based ranking (`skills/ai-kit-spec-review/ai_kit_spec/model_ranker.py`,
`model_matcher.py`, `model_sources.py`, `cli.py`), later hardened by a
production-readiness review that normalized the three Artificial Analysis
(AA) axes and defaulted a genuinely missing axis to `(max/2)-1 = 49.0`
instead of excluding it from the weighted average (see git history on
`skills/ai-kit-spec-review/ai_kit_spec/model_ranker.py`, commit
`f3c2567`).

Live verification against a real 188-entry catalog, gathered while
confirming that fix, surfaced a residual anomaly: `anthropic/claude-opus-5-high`
ranks #41/188 despite carrying the catalog's single highest
`intelligence_index` (61.5) and strong `coding_index`/`agentic_index`
(76.5/56.1). Two of its seven ranking axes — `context_window` and
`tool_calling` — are `null` and fall to the 49.0 default, dragging its
otherwise-excellent weighted score down.

Root cause (confirmed against a live models.dev fetch, 2026-09-04): this
candidate matched Artificial Analysis (which encodes reasoning effort in its
own model slugs, e.g. `claude-opus-5-high`) but never matched models.dev,
which does **not** model reasoning effort as a distinct `model_id` at all —
Anthropic's real API takes effort as a request parameter, not a model
selector, so models.dev lists a single bare `anthropic/claude-opus-5`
entry covering every effort level. `match_models_dev`'s existing fuzzy
fallback (`difflib.SequenceMatcher`, threshold 0.82, margin 0.05) very
nearly bridges this gap — `ratio("claudeopus5high", "claudeopus5") = 0.846`
clears the threshold — but the pool-wide search (every provider, every
model) finds a near-tied competing candidate (`claude-opus-4-5`, ratio
0.815, inside the 0.05 margin) and refuses to guess between them, exactly
as designed. No `provider_hint` is available at that point in `cli.py` to
break the tie, because `match_models_dev` is called *before*
`match_artificial_analysis` resolves a vendor.

This is a data-completeness gap, not a ranking-math bug — the 49.0 default
fix from the prior round is working correctly on incomplete inputs. This
spec closes the gap for the specific, common case of a reasoning-effort
suffix that AA/CLIs encode but models.dev doesn't.

**Explicitly out of scope for this spec** (raised during design, deferred):
- A general "any missing axis, any source" backfill mechanism. This spec
  is scoped to `context_window`/`tool_calling`/`structured_output`/
  `max_output_tokens` recoverable from models.dev via effort-suffix
  normalization only — not a generic cross-source merge engine.
- Using OpenRouter's own model rankings (openrouter.ai/models) as a
  supplementary intelligence/coding signal. Not exposed as a structured
  API — would require scraping a UI-only ranking, a separate and more
  fragile undertaking. Noted as a candidate future source, possibly tied
  to the (separate, not-yet-scoped) "flag free/no-data models for
  inferred search" idea.
- Purpose-weighted axis re-tuning (a separate, already-deferred spec).
- Reseller/service-tier catalog-key deduplication in general (e.g.
  collapsing `venice/claude-opus-5-high-fast` into `anthropic/claude-opus-5-high`).
  This spec deliberately does **not** merge across service tiers — see §3,
  Safety rule — because a tier variant (e.g. `-fast`) can carry a
  genuinely different `context_window` than the base model (confirmed:
  models.dev lists `venice/claude-opus-5-fast` as a distinct row from
  `venice/claude-opus-5`, with its own context/pricing). Conflating them
  would trade one silent inaccuracy for another.

## 2. Goals / Non-goals

**Goals:**
- When a CLI-reported model matches Artificial Analysis but not
  models.dev, and the gap is attributable to an AA/CLI-only reasoning-
  effort suffix (`-high`, `-thinking-xhigh`, etc.), recover
  `context_window`/`tool_calling`/`structured_output`/`max_output_tokens`
  from the effort-stripped base model's real models.dev entry.
- Never let a recovered value cross a service-tier boundary (e.g. never
  attribute a `-fast` variant's context window to the non-`-fast` base
  model, or vice versa).
- Never change which canonical catalog key, price, or AA score a
  candidate resolves to — this is a pure enrichment backfill for four
  specific fields, layered on top of the existing matched/unmatched
  decision tree, not a new matching mode.
- Vendor-agnostic: the effort-token vocabulary is not Anthropic-specific
  (OpenAI's reasoning models use the same `minimal/low/medium/high`
  convention).

**Non-goals:**
- Backfilling `intelligence_index`/`coding_index`/`agentic_index`/pricing
  this way — those legitimately vary by effort level and must only ever
  come from AA's own effort-specific entry (confirmed: AA gives opus-5-low
  intelligence_index=52.5, medium=58.6, high=61.5 — genuinely different
  models for ranking purposes, sharing only their base context/tool-calling
  capability).
- A UI/wizard-facing "this value was inferred" indicator. Discussed and
  deliberately deferred (YAGNI) — `source.models_dev` stays a plain
  boolean meaning "models.dev contributed data to this entry," which
  remains true and honest whether the contribution came from an exact
  hit or a safely-scoped effort-suffix fallback.

## 3. Design

### 3.1 Effort-suffix stripping (`model_matcher.py`)

A new pure function, alongside the existing `_normalize`/`_fuzzy_candidate_indices`:

```python
_EFFORT_TOKENS = {"minimal", "low", "medium", "high", "max", "xhigh", "thinking"}
_TIER_TOKENS = {"fast", "turbo", "mini", "nano", "flash", "lite", "air"}


def _strip_known_effort_suffix(bare: str) -> str | None:
    """Repeatedly strips trailing '-<token>' segments that are known
    reasoning-EFFORT tokens (never tier tokens) from a bare model id.
    Returns the stripped id, or None when nothing was stripped, or when a
    TIER token would be left trailing (refuses -- a tier boundary must
    never be crossed by this fallback, see design rationale in
    docs/superpowers/specs/2026-09-05-model-catalog-effort-suffix-fallback-design.md
    Section 3.1). Vendor-agnostic: OpenAI's own reasoning-effort models use
    the same minimal/low/medium/high vocabulary."""
    parts = bare.split("-")
    stripped_any = False
    while len(parts) > 1 and parts[-1].lower() in _EFFORT_TOKENS:
        parts.pop()
        stripped_any = True
    if not stripped_any:
        return None
    if parts[-1].lower() in _TIER_TOKENS:
        return None
    return "-".join(parts)
```

Worked examples:
- `claude-opus-5-high` → strips `high` → `claude-opus-5`.
- `claude-opus-5-thinking-xhigh` → strips `xhigh`, then `thinking` (both are
  effort tokens) → `claude-opus-5`.
- `claude-opus-5-thinking-low-fast` → first trailing token is `fast` (a
  tier token, not in `_EFFORT_TOKENS`) → loop never starts → `stripped_any`
  stays `False` → returns `None`. This candidate is never touched by the
  fallback at all, by construction — the tier boundary is structurally
  protected, not policed after the fact.

`match_models_dev` gains an internal fallback stage: if its existing
three steps (hinted exact / pool exact / pool fuzzy, each already
collision-safe via the existing `provider_hint` disambiguation) produce no
single match for the given id, and `_strip_known_effort_suffix` returns a
non-`None` value, retry the *same three steps* against the stripped id
(same `provider_hint`, if any, still applies). This keeps the effort-aware
retry entirely self-contained: any caller that already passes a
`provider_hint` benefits automatically, with no caller-side changes.

### 3.2 Retry orchestration (`cli.py`)

`build_model_catalog`'s per-candidate loop calls `match_models_dev` before
`match_artificial_analysis` resolves a vendor, so the first call has no
`provider_hint` to break a cross-provider collision (confirmed: even after
stripping the effort suffix, "claude-opus-5" bare-matches dozens of
providers on models.dev — a hint is required, stripping alone is
insufficient). One new block, after `aa_match` is computed:

```python
md_match = match_models_dev(model_id, models_dev_data) if models_dev_ok else None
provider_hint = (md_match or {}).get("provider") or (
    model_id.split("/", 1)[0] if "/" in model_id else None)
aa_match = (match_artificial_analysis(model_id, aa_models, provider_hint=provider_hint)
            if aa_ok else None)
# NEW: models.dev retry using AA's resolved vendor as a hint, when the
# first (unhinted) attempt found nothing. Enrichment-only: does not
# change `provider`/canonical `key` decisions below, which continue to
# derive from aa_match's model_creator exactly as before -- the retried
# md_match is consulted only by _preserved_or_fresh_md_fields /
# _preserved_or_fresh_ctx_window further down, for context_window /
# tool_calling / structured_output / max_output_tokens.
if models_dev_ok and md_match is None and aa_match:
    aa_provider_hint = _slugify((aa_match.get("model_creator") or {}).get("name", "")) or None
    if aa_provider_hint:
        md_match = match_models_dev(model_id, models_dev_data, provider_hint=aa_provider_hint)
```

Why this doesn't disturb existing behavior:
- **Canonical key unchanged**: `key = canonical_key(provider, bare_model_part(model_id))`
  always uses the CLI's *original* `model_id` (e.g. `claude-opus-5-high`),
  never the stripped one — every effort variant keeps its own catalog
  entry, exactly as today (confirmed live: `-low`/`-medium`/`-high` are
  already three separate canonical keys with three different AA scores).
- **Provider/price/scores unchanged**: `provider` is set from `md_match["provider"]`
  when `md_match` is truthy — but the retried `md_match`'s provider is the
  *same* vendor `aa_provider_hint` already derived, so this is a no-op on
  the value, not a new source of truth. Pricing and AA scores never read
  from `md_match` for anything but its own `cost`/`limit` fields, which
  this retry does legitimately have permission to contribute (a real
  models.dev entry for the base model, honestly matched).
- **`source.models_dev` becomes `True`** where it was `False` — this is an
  intentional, honest signal ("models.dev contributed real data to this
  entry"), not a new provenance category (see Non-goals: no separate
  "inferred" flag).
- **Composes with the existing preserve-on-source-down contract**:
  `_preserved_or_fresh_md_fields`/`_preserved_or_fresh_ctx_window` already
  handle `md_match is None` (clear stale fields) vs `models_dev_ok=False`
  (preserve cached fields) vs a real match (fresh fields) — the retry only
  changes what `md_match` *is* before it reaches those functions; no new
  branches are needed inside them.

### 3.3 Safety rule (restated plainly)

This fallback recovers **only** `context_window` / `tool_calling` /
`structured_output` / `max_output_tokens`, and **only** when the sole
difference between the CLI-reported id and a real models.dev entry is a
reasoning-effort suffix. It never fires across a service-tier boundary
(`_TIER_TOKENS` guard), never changes canonical keys, and never touches
price or AA-sourced scores. A candidate that still can't resolve after
this fallback (genuinely absent from models.dev under any effort-stripped
form, or still ambiguous even with a hint) is left exactly as today —
`context_window`/`tool_calling` stay `null`, defaulting to 49.0 in ranking.
Closing that residual gap is deferred to the (separate, not-yet-scoped)
inferred-search idea.

## 4. Testing

- **`_strip_known_effort_suffix`** (pure, `model_matcher.py`): single
  strip (`-high`), compound strip (`-thinking-xhigh`), tier-token present
  (`-thinking-low-fast` → `None`, untouched), no strippable trailing token
  (→ `None`), tier token as the very first trailing token (→ `None`,
  confirms `_TIER_TOKENS` is checked before any stripping happens for that
  case too).
- **`match_models_dev`'s new fallback stage**: direct id fails but
  stripped id succeeds unambiguously (with and without `provider_hint`);
  stripped id still collides across providers with no hint (→ `None`,
  never guesses); stripped id resolves via `provider_hint` after an
  unhinted collision (mirrors the real `claude-opus-5-high` scenario).
- **`cli.py`'s new retry block**: `aa_match` present with a usable
  `model_creator.name` → retry attempted, backfills `ctx_window`/
  `tool_calling` only, `provider`/`key`/pricing/scores unchanged;
  `aa_match` present but `model_creator.name` missing/empty → no retry
  attempted; first (unhinted) `md_match` already succeeded → retry never
  attempted (no wasted second lookup); `models_dev_ok=False` → retry never
  attempted (respects the existing source-down contract).
- **Regression test, end-to-end**: a small `models_dev_data`/`aa_models`
  fixture mirroring the real `claude-opus-5-high` / `venice/claude-opus-5-high-fast`
  shape — asserts the base-model candidate's `context_window`/
  `tool_calling` get backfilled from the bare `anthropic/claude-opus-5`
  models.dev entry, while a `-fast`-suffixed sibling candidate's own
  (different) context window is used for its own entry, unaffected by the
  fallback, and canonical keys/AA scores/pricing are unchanged for both.

## 5. Rollout

Single-file-pair change (`model_matcher.py` + `cli.py`), no schema
migration, no new config surface. Existing cached catalog entries missing
`context_window`/`tool_calling` self-heal on the next `fetch-model-catalog`
run (models.dev genuinely re-queried, not a cache read) — no backfill
script needed.
