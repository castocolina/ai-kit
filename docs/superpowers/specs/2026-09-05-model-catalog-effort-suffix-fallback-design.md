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

**Confirmed id shape (closes an ambiguity raised during review):** the
candidate's raw `model_id`, as `cursor-agent` reports it, is the *bare*
string `claude-opus-5-high` — no `"<vendor>/"` prefix at all (confirmed
against the live catalog: `runtimes: {"cursor-agent": {"model_id":
"claude-opus-5-high", ...}}`). `cli.py`'s existing fallback of deriving
`provider_hint` from the id's own `"/"`-prefix (`model_id.split("/", 1)[0]
if "/" in model_id else None`) therefore yields `None` for this candidate
— there is no simpler, already-available hint to pass at the first
`match_models_dev` call. The retry mechanism in §3.2, which sources its
hint from Artificial Analysis's *own* independent resolution instead of
the raw id, is what supplies a hint where the id itself carries none — it
is necessary for this exact case, not incidental scope creep. (A CLI that
*does* report a vendor-prefixed id, e.g. `anthropic/claude-opus-5-high`,
would already resolve via `match_models_dev` step 1 without needing §3.2
at all — §3.2 only ever activates for the bare-id case.)

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

A new pure function, alongside the existing `_normalize`/`_fuzzy_candidate_indices`.
**Revised after cross-AI review** (both `opencode-grok` and native-opus
flagged the original `_TIER_TOKENS` refusal list as both unnecessary and
actively harmful — see rationale below):

```python
_EFFORT_TOKENS = {"minimal", "low", "medium", "high", "xhigh", "thinking"}
# "max" is deliberately NOT a standalone effort token -- it collides with
# real base-model names that end in "-max" (e.g. Alibaba's qwen-max /
# qwen3-max, a genuinely different, smaller-catalog model). It is only
# ever stripped as part of the two-token compound "thinking-max"
# (Anthropic's own reasoning-effort naming, e.g. "claude-opus-5-thinking-max"),
# never as a bare trailing "-max".


def _strip_known_effort_suffix(bare: str) -> str | None:
    """Repeatedly strips trailing reasoning-EFFORT tokens from a bare model
    id -- a single token from _EFFORT_TOKENS, or the two-token compound
    "thinking-max". Returns the stripped id, or None when nothing was
    stripped. Vendor-agnostic: OpenAI's own reasoning-effort models use the
    same minimal/low/medium/high vocabulary.

    Safety is structural, not a separate denylist: the loop only ever pops
    a token it POSITIVELY recognizes as a reasoning-effort word, and stops
    at the first token that isn't one -- a service-tier suffix (`-fast`),
    a real size/tier designation that is simply part of the base model's
    own name (`-mini`, `-flash`), or anything unrecognized is left exactly
    where it was, never stripped away. This is why a candidate like
    `claude-opus-5-thinking-low-fast` is never touched at all (`fast` is
    the very first trailing token and isn't an effort word, so the loop
    never starts), while `o3-mini-high` correctly strips to `o3-mini`
    (only `high` is popped; `mini` is preserved verbatim in the returned
    id, so a subsequent models.dev lookup finds -- or fails to find --
    `o3-mini`'s own real, tier-specific entry, never a different tier's)."""
    parts = bare.split("-")
    stripped_any = False
    while len(parts) > 1:
        last = parts[-1].lower()
        if last == "max" and len(parts) > 2 and parts[-2].lower() == "thinking":
            parts.pop()
            parts.pop()
            stripped_any = True
            continue
        if last in _EFFORT_TOKENS:
            parts.pop()
            stripped_any = True
            continue
        break
    return "-".join(parts) if stripped_any else None
```

Worked examples:
- `claude-opus-5-high` → strips `high` → `claude-opus-5`.
- `claude-opus-5-thinking-xhigh` → strips `xhigh`, then `thinking` (both are
  effort tokens) → `claude-opus-5`.
- `claude-opus-5-thinking-max` → the `max`/`thinking` pair strips as one
  compound → `claude-opus-5`.
- `claude-opus-5-thinking-low-fast` → the trailing token is `fast`, not a
  recognized effort word → loop never starts → `None`. Untouched, exactly
  as before, but now because `fast` was never a candidate to pop, not
  because of a separate tier denylist.
- `qwen3-max` → trailing token is `max`, but `len(parts) == 2` (no
  `thinking` two tokens back) → the compound special-case doesn't apply,
  and bare `max` isn't in `_EFFORT_TOKENS` → `None`. A real, distinct model
  is never misattributed to `qwen3`.
- `o3-mini-high` → strips `high` → `o3-mini` (`mini` is preserved, not
  stripped — this is a genuine, different-from-`o3` model in its own
  right, and models.dev is queried for exactly that id).

`match_models_dev` gains an internal fallback stage: if its existing three
steps (hinted exact / pool exact / pool fuzzy — **only the pool-exact and
pool-fuzzy steps consult `provider_hint` for collision disambiguation; the
first, hinted-exact step is unambiguous by construction and never needs
it** — corrected wording per review, see §3.1 note above) produce no
single match for the given id, and `_strip_known_effort_suffix` returns a
non-`None` value, retry — but **only the two exact steps (hinted-exact,
pool-exact), never the pool-fuzzy step** — against the stripped id (same
`provider_hint`, if any, still applies). Excluding fuzzy matching from the
stripped-id retry is deliberate: the strip itself is already an inference,
and compounding it with `difflib`'s fuzzy fallback would re-open the exact
false-match hazard `_fuzzy_candidate_indices`'s threshold/margin exist to
close (a stripped `claudeopus5` fuzzed pool-wide would itself surface
`claude-opus-4-5` and other siblings) — two stacked inferences is a
guess, not a recovery. This keeps the effort-aware retry entirely
self-contained: any caller that already passes a `provider_hint` benefits
automatically, with no caller-side changes.

### 3.2 Retry orchestration (`cli.py`)

`build_model_catalog`'s per-candidate loop calls `match_models_dev` before
`match_artificial_analysis` resolves a vendor, so the first call has no
`provider_hint` to break a cross-provider collision (confirmed: even after
stripping the effort suffix, "claude-opus-5" bare-matches dozens of
providers on models.dev — a hint is required, stripping alone is
insufficient; and per §1, this candidate's raw id carries no `"/"` prefix
of its own to fall back on either). One new block, after `aa_match` is
computed:

```python
md_match = match_models_dev(model_id, models_dev_data) if models_dev_ok else None
provider_hint = (md_match or {}).get("provider") or (
    model_id.split("/", 1)[0] if "/" in model_id else None)
aa_match = (match_artificial_analysis(model_id, aa_models, provider_hint=provider_hint)
            if aa_ok else None)
# NEW: an ENRICHMENT-ONLY retry, deliberately kept in its own variable
# (`md_enrich_match`), never assigned into `md_match` itself. This is the
# load-bearing fix from cross-AI review: an earlier draft reassigned
# `md_match` directly, which -- because `provider`, canonical `key`, and
# `pricing` below are ALL derived from `md_match` when it's truthy (`if
# md_match: provider = md_match["provider"]`; `key =
# canonical_key(provider, bare_model_part(model_id))`; `pricing =
# md_pricing or aa_pricing` where `md_pricing` reads `md_match["cost"]`)
# -- would have silently let a models.dev-sourced price/provider override
# AA's effort-specific ones, contradicting this spec's own Non-goals.
# Keeping `md_enrich_match` a distinct name makes that impossible: nothing
# below this block reads it except the two calls that consume it
# explicitly (below).
md_enrich_match = None
if models_dev_ok and md_match is None and aa_match:
    aa_provider_hint = _slugify((aa_match.get("model_creator") or {}).get("name", "")) or None
    if aa_provider_hint:
        md_enrich_match = match_models_dev(model_id, models_dev_data, provider_hint=aa_provider_hint)
```

`_preserved_or_fresh_md_fields` and `_preserved_or_fresh_ctx_window` each
gain one new optional parameter, `md_enrich_match=None`, consulted **only**
when the primary `md_match` is `None` (source genuinely found no exact
match) — never when `md_match` is truthy, and never as a substitute for
`md_match` anywhere else in the function. Sketch (existing `not
models_dev_ok` and genuinely-no-match-at-all branches are unchanged):

```python
def _preserved_or_fresh_md_fields(md_match, models_dev_ok, existing_entry,
                                   md_enrich_match=None):
    if not models_dev_ok:
        ...  # unchanged
    source = md_match or md_enrich_match
    if not source:
        return {"tool_calling": None, "structured_output": None, "max_output_tokens": None}
    return {"tool_calling": source.get("tool_call"),
            "structured_output": source.get("structured_output"),
            "max_output_tokens": source.get("limit", {}).get("output")}
```

(`_preserved_or_fresh_ctx_window` follows the identical pattern for
`ctx_window`.) Everywhere else in `build_model_catalog` — `provider`
derivation, `key = canonical_key(...)`, and `md_cost`/`md_pricing` —
continues to read `md_match` alone, completely untouched by
`md_enrich_match`'s existence.

Why this now genuinely holds (re-verified line-by-line against
`cli.py` after the fix above, per review feedback that the original
claims were asserted, not verified):
- **Canonical key unchanged**: `key = canonical_key(provider,
  bare_model_part(model_id))` reads `provider` (derived from `md_match`,
  never `md_enrich_match`) and the CLI's *original* `model_id` — every
  effort variant keeps its own catalog entry, exactly as today (confirmed
  live: `-low`/`-medium`/`-high` are already three separate canonical keys
  with three different AA scores).
- **Provider unchanged**: `provider = md_match["provider"]` only fires
  when the *primary* `md_match` is truthy — `md_enrich_match` is never
  read by this branch at all, so the retry cannot move provider
  derivation onto a different branch than today, regardless of whether
  the retry's own resolved provider happens to agree with
  `aa_provider_hint` or not.
- **Pricing unchanged**: `md_cost = (md_match or {}).get("cost", {})`
  reads `md_match`, never `md_enrich_match` — a successful enrichment
  retry cannot override AA's effort-specific price with the base model's
  price, closing the CRITICAL finding directly.
- **`source.models_dev` stays accurate**: it's computed from `md_match is
  not None`, unaffected by `md_enrich_match` — an enrichment-only backfill
  does not claim a "real" models.dev match happened for this exact id (it
  didn't); `confidence`/`last_verified`'s `matched_this_run` already
  becomes `True` via `aa_match` regardless, so no behavior changes there.
- **Composes with the existing preserve-on-source-down contract**:
  `_preserved_or_fresh_md_fields`/`_preserved_or_fresh_ctx_window` already
  handle `not models_dev_ok` (preserve cached fields) vs a genuine
  no-match-anywhere (clear stale fields) vs a real match (fresh fields) —
  `md_enrich_match` only ever substitutes inside the "no match" case's
  `source` lookup, never replaces the other two branches.

### 3.3 Safety rule (restated plainly)

This fallback recovers **only** `context_window` / `tool_calling` /
`structured_output` / `max_output_tokens` — via `md_enrich_match`, which
(per §3.2) is structurally incapable of influencing `provider`, canonical
`key`, or `pricing`, not merely documented not to — and only when the sole
difference between the CLI-reported id and a real models.dev entry is a
recognized reasoning-effort suffix (§3.1; never a service-tier suffix,
which the stripping function structurally never pops in the first place).
It never changes canonical keys, and never touches price or AA-sourced
scores. A candidate that still can't resolve after this fallback
(genuinely absent from models.dev under any effort-stripped form, or
still ambiguous even with a hint) is left exactly as today —
`context_window`/`tool_calling` stay `null`, defaulting to 49.0 in
ranking. Closing that residual gap is deferred to the (separate,
not-yet-scoped) inferred-search idea.

## 4. Testing

- **`_strip_known_effort_suffix`** (pure, `model_matcher.py`): single
  strip (`-high`), compound strip (`-thinking-xhigh`), `thinking-max`
  compound strip, no strippable trailing token (→ `None`), a service-tier
  suffix as the trailing token (`-thinking-low-fast` → `None`, untouched —
  `fast` is simply never a token the loop recognizes), a real base model
  ending in a token that coincides with an effort word but isn't preceded
  by `thinking` (`qwen3-max` → `None`, not stripped), and a real base
  model whose own name happens to end in what could look like a
  tier/size word, correctly preserved after an effort strip (`o3-mini-high`
  → `o3-mini`, not `o3` and not refused).
- **`match_models_dev`'s new fallback stage**: direct id fails but
  stripped id succeeds unambiguously via an exact step (with and without
  `provider_hint`); stripped id still collides across providers with no
  hint (→ `None`, never guesses); stripped id resolves via `provider_hint`
  after an unhinted collision (mirrors the real `claude-opus-5-high`
  scenario); a stripped id that would only resolve via the pool-*fuzzy*
  step is explicitly asserted to return `None` (fuzzy is excluded from
  the retry — see §3.1).
- **`cli.py`'s new retry block**: `aa_match` present with a usable
  `model_creator.name` → `md_enrich_match` populated, backfills
  `ctx_window`/`tool_calling` only; `aa_match` present but
  `model_creator.name` missing/empty → `md_enrich_match` stays `None`;
  first (unhinted) `md_match` already succeeded → retry never attempted
  (`md_enrich_match` stays `None`, no wasted second lookup);
  `models_dev_ok=False` → retry never attempted (respects the existing
  source-down contract).
- **The two invariants most at risk, tested directly** (per review — these
  were previously asserted in prose but not exercised): (a) a case where
  `md_enrich_match`'s own resolved `provider` field *differs* from
  `aa_provider_hint` (a models.dev provider key that doesn't match
  `_slugify(model_creator.name)`) — asserts the canonical key and
  `provider` are still derived exactly as they would be with no retry at
  all, proving `md_enrich_match` is structurally inert for those two
  fields, not merely coincidentally equal; (b) a case where the retry
  succeeds — asserts the entry's `pricing` still equals AA's
  effort-specific price, never the models.dev base model's `cost`.
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
`context_window`/`tool_calling` self-heal on the **next genuinely-fetched**
`fetch-model-catalog` run — specifically, one where models.dev is actually
re-queried, not skipped. The wizard's own default path uses
`--if-stale`, which no-ops (leaves `models_dev_ok=False` for that run,
per `cli.py`'s `skip_fetch` handling) until `CATALOG_TTL_SECONDS` has
elapsed since the last real fetch — self-heal is bounded by that TTL, not
instant on the very next invocation. No backfill script is needed either
way; this is a data-completeness fix that resolves itself once a real
fetch runs.

## 6. Note on `reasoning_modes` (cross-document consistency)

`docs/superpowers/specs/2026-09-02-model-discovery-curation-design.md`'s
schema (§5) models reasoning effort as a `reasoning_modes: ["low",
"medium", "high"]` field *within one* catalog entry. In practice (§3.2,
confirmed against live data), each effort variant a CLI reports becomes
its *own* canonical catalog entry (`anthropic/claude-opus-5-low`,
`.../claude-opus-5-medium`, `.../claude-opus-5-high` are three separate
keys with three different AA scores) — `reasoning_modes` is not populated
anywhere in `build_model_catalog` today. This spec's design supersedes
that part of the upstream schema in practice: one-entry-per-effort-variant
is the settled representation going forward, and `reasoning_modes`
(still schema-validated in `model_catalog.py`) is vestigial. Removing the
field is out of scope here (no active writer to migrate away from) — this
note exists so a future cleanup pass doesn't mistake it for a gap to fill.
