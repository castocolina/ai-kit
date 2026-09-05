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

Root cause (confirmed against a live models.dev fetch, 2026-09-05): this
candidate matched Artificial Analysis (which encodes reasoning effort in its
own model slugs, e.g. `claude-opus-5-high`) but never matched models.dev,
which does **not** model reasoning effort as a distinct `model_id` at all —
Anthropic's real API takes effort as a request parameter, not a model
selector, so models.dev lists a single bare `claude-opus-5` entry (no
effort suffix) covering every effort level — but that same bare id is
listed under **16 different providers** (`anthropic`, `abacus`,
`agentrouter`, `aihubmix`, `azure`, `azure-cognitive-services`, `cortecs`,
`github-copilot`, `kenari`, `llmgateway`, `neon`, `opencode`, `pioneer`,
`requesty`, `snowflake-cortex`, `venice` — confirmed live, 2026-09-05).

**Correction (round-3 review caught this — the mechanism below was
previously misdescribed):** `match_models_dev`'s existing fuzzy fallback
(`difflib.SequenceMatcher`, threshold 0.82, margin 0.05) very nearly
bridges this gap on its own — `ratio("claudeopus5high", "claudeopus5") =
0.846` clears the threshold — but the pool-wide search (every provider,
every model) returns **all 16** of those identically-scored
`claude-opus-5` rows (one per provider, each an exact string match against
the fuzzy target, so all tied at precisely 0.846 — well within the 0.05
margin of *each other*, since they're identical), not a near-miss against
a *different* model name. (An earlier draft of this document claimed the
competing candidate was `claude-opus-4-5` at ratio 0.815 — that number is
correct, but 0.815 is *below* the 0.82 threshold, so
`_fuzzy_candidate_indices` excludes it outright; it was never a real
competitor and never entered the tied set. Verified directly against
`_fuzzy_candidate_indices` and a live models.dev fetch before writing this
correction, to avoid repeating the same mistake.) `match_models_dev`
refuses to guess among 16 tied, same-named, different-provider candidates
— exactly as designed, this is precisely the ambiguity
`provider_hint`-based disambiguation exists for. No `provider_hint` is
available at the point `cli.py:219` calls `match_models_dev`, though,
because that call happens *before* `match_artificial_analysis` resolves a
vendor.

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
is necessary for this exact case, not incidental scope creep.

**Correction (round-2 review caught this):** a vendor-prefixed id (e.g.
`anthropic/claude-opus-5-high`) does **not** skip the need for §3.2
either. `match_models_dev` step 1 is an *exact* lookup of the bare token
under the prefix (`model_matcher.py:73-77`) — it has no effort-awareness
at all, so a prefixed id carrying an effort suffix misses step 1 exactly
as a bare one misses the pool-exact step, for the identical reason
(models.dev's entry has no suffix to match against). §3.2's retry is
therefore needed whenever an effort suffix is present, regardless of
whether the raw id happens to carry a vendor prefix — the prefix only
ever helps the (unrelated) case of an exact id colliding across
providers, which isn't this spec's concern.

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
  deliberately deferred (YAGNI). **Correction (both reviewers caught this
  stated two contradictory ways in an earlier draft):** `source.models_dev`
  is computed from `md_match is not None` only, unaffected by
  `md_enrich_match` — it is **`False`** for an enrichment-only backfill,
  exactly as it is today for any candidate models.dev didn't exactly
  match. This is intentional, not a gap: `source.models_dev=False` already
  and correctly means "no exact models.dev id match for this candidate,"
  which remains true for the enrichment case — the candidate's id
  genuinely isn't in models.dev, only its effort-stripped base is. A
  reader should understand a `False` `source.models_dev` alongside a
  non-null `context_window`/`tool_calling` as "recovered via this spec's
  effort-suffix fallback," not as a data-integrity anomaly — exactly the
  UI-indicator role this bullet already declines to add a dedicated flag
  for.

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

    Safety against crossing a SERVICE-TIER boundary is structural, not a
    denylist: the loop only ever pops a token it positively recognizes as
    a reasoning-effort word, and stops at the first token that isn't one
    -- a service-tier suffix (`-fast`), a real size/tier designation that
    is simply part of the base model's own name (`-mini`, `-flash`), or
    anything unrecognized is left exactly where it was, never stripped
    away. This is why a candidate like `claude-opus-5-thinking-low-fast`
    is never touched at all (`fast` is the very first trailing token and
    isn't an effort word, so the loop never starts), while `o3-mini-high`
    correctly strips to `o3-mini` (only `high` is popped; `mini` is
    preserved verbatim in the returned id, so a subsequent models.dev
    lookup finds -- or fails to find -- `o3-mini`'s own real,
    tier-specific entry, never a different tier's).

    Collision-freedom of the vocabulary ITSELF is a heuristic, not a
    proof, for six of these seven tokens (accepted, per review): `max` is
    demonstrably excluded from bare stripping because a concrete
    real-world collision is known (`qwen-max`/`qwen3-max`); no equivalent
    audit was done to confirm no real base-model id ends in
    `minimal`/`low`/`medium`/`high`/`xhigh`/`thinking` as its OWN name
    rather than an effort suffix. This is the same category of accepted
    risk `_fuzzy_candidate_indices`'s own threshold/margin already carry
    (a heuristic tuned against known cases, not a guarantee against every
    unknown one) -- not a new, unmitigated exposure this spec introduces."""
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

**Revised again after round-2 review** (native-opus's second CRITICAL: the
previous draft embedded the effort-strip retry as an internal fallback
*inside* `match_models_dev` itself — meaning it also fired on the
*primary*, unhinted call at `cli.py:219` for any vendor-prefixed id, e.g.
`openai/gpt-5-high`, letting the base model's entry become `md_match`
itself rather than `md_enrich_match`, and reopening the exact same
pricing/provider leak the round-1 fix closed — just for a different id
shape. Confining the stripping logic to `match_models_dev`'s own control
flow made it impossible to guarantee which variable it would ever
populate.)

**`match_models_dev` itself is not given any effort-awareness at all.**
It gains exactly one new parameter, `allow_fuzzy: bool = True` (default
preserves today's behavior for every existing call site, including the
primary call at `cli.py:219`, which never passes it) — when `False`, only
its existing hinted-exact and pool-exact steps run; the pool-fuzzy step is
skipped. `_strip_known_effort_suffix` (§3.1 above) is a standalone
utility with no relationship to `match_models_dev` — it is called only
from the §3.2 orchestration below, which explicitly builds the
effort-stripped *string* and passes it as an ordinary `cli_model_id`
argument to an ordinary, unmodified `match_models_dev` call. This means
the entire effort-suffix fallback mechanism is reachable from exactly one
call site (§3.2's enrichment block) and can only ever populate
`md_enrich_match` — there is no code path by which it can reach `md_match`
for any id shape, prefixed or bare.

Excluding fuzzy matching from both retry attempts (`allow_fuzzy=False`) is
deliberate defense-in-depth, not something this spec's own motivating case
happens to require (see §3.2 below — that case resolves via an *exact*
match once stripped and hinted, fuzzy never enters into it): the strip
itself is already an inference, and compounding it with `difflib`'s fuzzy
fallback on top would re-open the exact false-match hazard
`_fuzzy_candidate_indices`'s threshold/margin exist to close, for
*whatever other* model family's naming this fallback eventually
encounters — two stacked inferences is a guess, not a recovery, even when
today's one confirmed example doesn't happen to trigger it.

### 3.2 Retry orchestration (`cli.py`)

`build_model_catalog`'s per-candidate loop calls `match_models_dev` before
`match_artificial_analysis` resolves a vendor, so the first call has no
`provider_hint` to break a cross-provider collision (confirmed: even after
stripping the effort suffix, `claude-opus-5` exact-matches **16** different
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
# (`md_enrich_match`), never assigned into `md_match` itself, and using
# ONLY the ordinary, unmodified `match_models_dev` (see §3.1's "revised
# again" note -- no effort-awareness lives inside that function at all).
# When this block finds nothing (or never runs -- AA down/unmatched this
# run), the field-preservation logic below clears any previously-fresh
# fields exactly like today's existing contract; see §3.2's round-3 note
# for why a smarter preserve-on-AA-outage mechanism was tried and reverted.
md_enrich_match = None
if models_dev_ok and md_match is None and aa_match:
    aa_provider_hint = _slugify((aa_match.get("model_creator") or {}).get("name", "")) or None
    if aa_provider_hint:
        # Attempt 1: exact id, now with a hint the unhinted primary call
        # (cli.py:219) didn't have -- covers a same-id collision across
        # providers that only needed a vendor hint, no stripping at all.
        # For THIS spec's own motivating case this attempt still returns
        # None -- not because the hint fails to disambiguate anything, but
        # because "claude-opus-5-high" (unstripped) has no EXACT match
        # under any provider at all, and allow_fuzzy=False keeps this
        # attempt from reaching outside that (deliberately -- see §3.1's
        # defense-in-depth rationale, corrected after round-3 review: the
        # candidate that made the unhinted PRIMARY call ambiguous was a
        # genuine ~16-way tie of providers all listing the identical exact
        # string "claude-opus-5", not a fuzzy near-miss against a
        # different model name -- see §1). Every step in this enrichment
        # block is exact-only; fuzzy matching is never used anywhere in
        # the retry, only (unchanged) in the primary call.
        md_enrich_match = match_models_dev(model_id, models_dev_data,
                                            provider_hint=aa_provider_hint,
                                            allow_fuzzy=False)
        if md_enrich_match is None:
            stripped = _strip_known_effort_suffix(bare_model_part(model_id))
            if stripped:
                # Attempt 2: the effort-stripped id, exact-only (no fuzzy --
                # see §3.1). This is the ONLY place `_strip_known_effort_suffix`
                # is ever called.
                md_enrich_match = match_models_dev(stripped, models_dev_data,
                                                    provider_hint=aa_provider_hint,
                                                    allow_fuzzy=False)
```

**Round-3 correction — the preserve-across-an-AA-outage mechanism in an
earlier draft is dropped entirely.** That draft added an `enrich_attempted`
flag, `True` only when the enrichment block actually ran, and preserved
cached fields whenever it was `False` — intending to cover "Artificial
Analysis is down this run." Native-opus's third-round review found this
reintroduces the exact staleness bug the existing clear-on-fresh-no-match
contract exists to prevent, for a *much broader* class of candidates than
intended: `enrich_attempted` is `False` for **every** candidate where
`aa_match` is falsy for *any* reason — including an ordinary candidate
that has nothing to do with effort suffixes at all, whose *primary*
`md_match` genuinely disappeared on this run (`models_dev_ok=True`,
`md_match is None`, `aa_match` also `None` or unmatched). The "preserve"
branch cannot distinguish "these cached fields came from a real match that
is now stale" from "these cached fields came from a prior enrichment
recovery" — and this spec's own Non-goals deliberately declines to add
the provenance tracking (a dedicated "inferred" marker) that would be
needed to make that distinction. Attempting the preserve logic without
that provenance is worse than not attempting it at all.

**Accepted, documented limitation instead:** `_preserved_or_fresh_md_fields`
and `_preserved_or_fresh_ctx_window` gain exactly **one** new optional
parameter, `md_enrich_match=None`, consulted only when the primary
`md_match` is `None`. Whenever neither the primary match nor the
enrichment retry finds anything this run (`models_dev_ok=True`), the
existing contract applies unchanged: clear the stale fields. This means a
run where Artificial Analysis is transiently down (or matches nothing for
this candidate) *does* clear any previously effort-suffix-recovered
`context_window`/`tool_calling`/`structured_output`/`max_output_tokens` —
identical to how any other candidate's stale fields are already treated
today. This is a real, accepted tradeoff (the round-2 HIGH finding this
was meant to close is not fully closed), not a silent gap: fixing it
properly needs cross-run provenance this spec's Non-goals explicitly
opt out of, and is left to a future spec if the tradeoff proves costly in
practice. Self-heal still happens the moment both sources are up together
on some later run (§5).

```python
def _preserved_or_fresh_md_fields(md_match, models_dev_ok, existing_entry,
                                   md_enrich_match=None):
    if not models_dev_ok:
        ...  # unchanged: preserve from existing_entry (source itself down)
    if md_match:
        ...  # unchanged: fresh fields from the primary match
    source = md_enrich_match
    if not source:
        return {"tool_calling": None, "structured_output": None, "max_output_tokens": None}
    return {"tool_calling": source.get("tool_call"),
            "structured_output": source.get("structured_output"),
            "max_output_tokens": source.get("limit", {}).get("output")}
```

(`_preserved_or_fresh_ctx_window` follows the identical pattern for
`ctx_window`, reading `existing_entry.get("runtimes", {}).get(cli_name,
{}).get("ctx_window")` in the "preserve" branch, same as its existing
`not models_dev_ok` case.) Their call sites (`cli.py:284`'s
`md_fields = _preserved_or_fresh_md_fields(...)` and `cli.py:307`'s
`ctx_window = _preserved_or_fresh_ctx_window(...)`) both gain
`md_enrich_match=md_enrich_match` as an added keyword argument — an
implementation-level detail left to the eventual plan, not spelled out
further here. Everywhere else in `build_model_catalog` —
`provider` derivation (the full expression, including its
`provider_hint`/`model_creator.name`/`existing_key`-recovery branches at
`cli.py:237-247`, unabridged and unaffected by any of this), `key =
(existing_key if no_signal_this_run and existing_key else
(canonical_key(provider, bare_model_part(model_id)) if provider is not
None else None))` (the full expression, `cli.py:263-265`), and
`md_cost = (md_match or {}).get("cost", {}) if models_dev_ok and md_match
else {}` (the full expression, `cli.py:290`) — continues to read
`md_match` alone. `md_enrich_match` is never passed to, or read by, any of
these three; it is consumed exclusively by the two field-preservation
helpers above.

Why this now genuinely holds (re-verified against the **full**,
unabridged expressions in `cli.py`, per round-2 feedback that quoting
partial expressions as "verified line-by-line" wasn't actually
sufficient):
- **Canonical key unchanged**: the full `key = (...)` expression above
  reads `provider` and the CLI's *original* `model_id` — neither of which
  `md_enrich_match` ever touches — so every effort variant keeps its own
  catalog entry, exactly as today (confirmed live: `-low`/`-medium`/`-high`
  are already three separate canonical keys with three different AA
  scores).
- **Provider unchanged**: none of `provider`'s branches (`md_match`
  truthy, `provider_hint`, AA `model_creator.name`, `existing_key`
  recovery) ever reads `md_enrich_match` — it is simply not a name that
  appears anywhere in that derivation.
- **Pricing unchanged**: the full `md_cost = (...)` expression reads
  `md_match`, never `md_enrich_match` — a successful enrichment retry
  cannot override AA's effort-specific price with the base model's price.
- **`source.models_dev` is `False` for an enrichment-only backfill** — see
  the corrected Non-goals bullet above; this is now stated as a fact, not
  asserted two different ways.
- **Cost is bounded**: at most two additional `match_models_dev` calls per
  candidate, and only for candidates where the primary attempt found
  nothing *and* Artificial Analysis resolved a usable vendor name this
  run — never for an already-matched or already-unmatchable-anywhere
  candidate.

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
- **`match_models_dev`'s new `allow_fuzzy` parameter**: default (omitted)
  preserves today's behavior exactly, including the pool-fuzzy step, for
  every existing call site (in particular, the primary call at
  `cli.py:219` must be asserted unchanged by this spec); `allow_fuzzy=False`
  skips pool-fuzzy, so a case that would only resolve via that step
  returns `None` under `allow_fuzzy=False` but the same non-`None` match
  under the default.
- **`cli.py`'s new retry block, exercising both attempts explicitly**:
  Attempt 1 (exact id + hint, no stripping) resolves an inter-provider
  exact-id collision the primary call couldn't; Attempt 1 correctly
  returns `None` and falls through to Attempt 2 when the *unstripped* id
  has no exact match anywhere (mirrors this spec's own motivating case —
  `claude-opus-5-high` itself, unstripped, matches nothing exactly under
  any provider, and `allow_fuzzy=False` keeps this attempt from reaching
  for a fuzzy hit); Attempt 2 (stripped id, exact-only) succeeds where
  Attempt 1 didn't, filtered from a real multi-provider exact-id
  collision (16 providers list the bare stripped id in the live
  fixture's shape) down to one via the hint; a case that
  would only resolve via fuzzy on the *stripped* id is asserted to return
  `None` (never reached — fuzzy is excluded from both attempts, per
  §3.1/§3.2). All four recovered fields (`context_window`, `tool_calling`,
  `structured_output`, `max_output_tokens`) are asserted on a successful
  retry, not just two of them.
- **The lifecycle across runs, including the accepted round-3 tradeoff**:
  run 1 (both sources up) — retry succeeds, all four fields backfilled and
  persisted to the catalog under some key `K`. Run 2 (`aa_ok=False` or
  `aa_match=None`, `models_dev_ok=True`, **same `(cli_name, model_id)`
  pair, run-1's persisted entry still present in `existing_catalog`**):
  `_find_existing_key_for_runtime` recovers `existing_key=K` (this is
  *required* for the candidate to reach the field-rebuild path at all —
  per `cli.py:278`, with `md_match`/`aa_match` both `None` this run, a
  candidate that *couldn't* recover an `existing_key` would have
  `provider is None` and route to `unmatched` instead, leaving the old
  entry completely untouched rather than exercising any clearing logic;
  round-4 review caught an earlier draft describing this fixture
  backwards, as lacking that recovery), so `provider`/`key`/`existing_entry`
  all resolve — and *because* `md_match` and `md_enrich_match` are both
  `None` this run, the entry is rebuilt with `md_fields = {"tool_calling":
  None, "structured_output": None, "max_output_tokens": None}` (and
  `ctx_window = None`), asserting the four previously recovered fields are
  **cleared**. This matches today's existing contract for any candidate
  whose primary match disappears — the documented, accepted limitation
  from §3.2's round-3 correction, not a bug; a dedicated regression test
  exists specifically so a future change doesn't accidentally "fix" this
  into the broader staleness bug round 3 found and reverted. A second,
  unrelated candidate in the *same* two-run fixture — one whose fields
  came from a genuine primary `md_match` on run 1 (never touched
  `md_enrich_match` at all) that disappears on run 2 — must also clear
  identically, proving the enrichment mechanism doesn't special-case or
  protect fields it never touched.
- **The invariants most at risk, tested directly** (per review — these
  were previously asserted in prose but not exercised): (a) a case where
  `md_enrich_match`'s own resolved `provider` field *differs* from
  `aa_provider_hint` (a models.dev provider key that doesn't match
  `_slugify(model_creator.name)`) — asserts the canonical key and
  `provider` are still derived exactly as they would be with no retry at
  all, proving `md_enrich_match` is structurally inert for those two
  fields, not merely coincidentally equal; (b) a case where the retry
  succeeds — asserts the entry's `pricing` still equals AA's
  effort-specific price, never the models.dev base model's `cost`; (c) a
  case with a vendor-*prefixed* id carrying an effort suffix (e.g.
  `openai/gpt-5-high`) — asserts the primary call still yields `md_match
  is None`: step 1's exact lookup misses the suffix exactly as the bare
  case does, *and* the pool-fuzzy step also finds nothing for this
  example (`ratio("gpt5high", "gpt5") ≈ 0.667`, well under the 0.82
  threshold) — both conditions are asserted, not just the first, since
  a real fuzzy hit on the unstripped prefixed id would populate `md_match`
  even though step 1 missed — and the retry populates `md_enrich_match`
  the same way as the bare case.
- **Regression test, end-to-end**: a small `models_dev_data`/`aa_models`
  fixture mirroring the real `claude-opus-5-high` / `venice/claude-opus-5-high-fast`
  shape — asserts the base-model candidate's `context_window`/
  `tool_calling`/`structured_output`/`max_output_tokens` get backfilled
  from the bare `anthropic/claude-opus-5` models.dev entry, while a
  `-fast`-suffixed sibling candidate's own (different) context window is
  used for its own entry, unaffected by the fallback, and canonical
  keys/AA scores/pricing are unchanged for both.

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
