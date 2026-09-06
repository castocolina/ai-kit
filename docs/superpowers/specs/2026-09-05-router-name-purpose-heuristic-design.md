# Router/Gateway Name-Declared Purpose Heuristic — Design

**Date:** 2026-09-05
**Status:** Draft, pending user review

## 1. Problem

Live use of `ai-kit-spec-config`'s wizard (macOS, this week) surfaced a
ranking defect distinct from, and downstream of, the effort-suffix fallback
shipped earlier the same day
(`docs/superpowers/specs/2026-09-05-model-catalog-effort-suffix-fallback-design.md`).

A router/gateway-style CLI (self-identifying via
`model_heuristics.infer_is_router`'s existing `_ROUTER_NAME_HINTS =
("router", "-env", "local-llm")`) exposed two distinctly-named endpoints —
one whose id declared it a review/planning endpoint (e.g.
`router-env-plan-review`), one whose id declared it a coding endpoint
(e.g. `router-env-coding`). Both landed in the **same** purpose's ranked
list during `ai-kit-spec-config` Step 2.2 (both in EXECUTE, when only the
`-coding`-suffixed one belonged there) — not because
`ranking-weights.toml`'s REVIEW/EXECUTE weight profiles fail to
differentiate (they do: `coding_index` weight triples for EXECUTE,
0.10→0.30, while `intelligence_index` is halved, 0.30→0.15 — confirmed
live against `model_ranker.py`'s `DEFAULT_WEIGHTS`), but because
models.dev/Artificial Analysis have no distinct entry for either
router-specific endpoint. Both candidates' axis scores (`intelligence_index`,
`coding_index`, `agentic_index`, etc.) either come back `None` (falling to
`_MISSING_AXIS_DEFAULT = 49.0` for every axis) or resolve, via fuzzy
matching, to the same generic upstream row — either way, the two
candidates end up with near-identical weighted scores under **both**
weight profiles, so the CLI operator's own explicit purpose labeling in the
model id has zero influence on where either candidate ranks.

This is not a weighting bug and not a matching bug in the sense the
effort-suffix spec fixed (that spec recovers axis DATA a legitimate,
externally-cataloged model is missing; this spec addresses a candidate
whose real "capability" IS its operator-assigned purpose, which no
external source models at all — a router's `-coding` endpoint is not
"a coding-specialist model methodologically evaluated at coding_index=X",
it is an operator's routing label, and treating it as a scorable axis
candidate is a category error).

**Explicit user requirement (not just a fix for the misrank):** this
candidate's own name should also be treated as a signal to **skip external
enrichment entirely** — `match_models_dev`/`match_artificial_analysis` are
network calls (the latter quota-limited), and spending either on a
candidate whose purpose is already unambiguous from its own name, and
whose "capability" was never going to be found in a general model catalog
anyway, wastes resources for data this design will never use to place it.

## 2. Goals

- A router/gateway candidate whose raw CLI-reported id contains an
  explicit, unambiguous purpose word gets that word as an authoritative
  `name_declared_purpose`, decided by pure string matching — no network
  call attempted for it.
- `build_model_catalog` never calls `match_models_dev`/
  `match_artificial_analysis` for such a candidate.
- The wizard (`ai-kit-spec-config` Step 2.2) presents a name-declared
  candidate directly under its declared list, never through
  `score_candidates`'s ranking, and marks it visibly as declared-not-scored.
- Existing behavior for every other candidate (non-router, or a router
  whose name carries no unambiguous purpose word) is completely unchanged.

## 3. Non-Goals

- Not modifying `ranking-weights.toml`'s weight profiles (§1 already
  confirmed they're correctly differentiated; the problem is upstream of
  weighting).
- Not attempting to infer purpose for a non-router candidate's name
  (e.g. a real vendor model that happens to contain the substring
  "coding" — see §4.1's gating rule).
- Not changing `infer_is_router`/`_ROUTER_NAME_HINTS` itself.
- Not building a general "trust the CLI's own naming over any external
  source" mechanism for anything beyond purpose — `is_router`/
  `batch_mode`/`fallback_quota` heuristics are untouched and still exist
  independently.

## 4. Design

### 4.1 `infer_purpose_from_name` (`model_heuristics.py`)

A new pure heuristic, same shape and file as the three existing ones
(`infer_is_router`, `infer_batch_mode`, `infer_fallback_quota`):

```python
import re

_PURPOSE_NAME_HINTS = {
    "review": ("review", "plan-review"),
    "execute": ("coding", "execute"),
}


def _hint_matches(hint: str, lowered: str) -> bool:
    """Delimiter-bounded match: `hint` must not be embedded inside a larger
    alphanumeric run. Plain substring matching would let "review" fire on
    "preview" or "coding" fire on "encoding" -- both real router/gateway
    naming collisions, not purpose declarations."""
    return re.search(rf"\b{re.escape(hint)}\b", lowered) is not None


def infer_purpose_from_name(model_id: str) -> str | None:
    """Only meaningful for a candidate ALREADY confirmed as a router/gateway via
    infer_is_router -- this function does not check is_router itself (keeps the two
    heuristics independently testable/composable; every caller gates on infer_is_router
    first, exactly like build_model_catalog's wiring below). Checks for an explicit,
    unambiguous purpose word in the id, as a delimiter-bounded token (never a raw
    substring): "review"/"plan-review" -> "review"; "coding"/"execute" -> "execute".
    Returns None when neither group matches, OR when both do (a genuine naming
    contradiction must never be silently resolved by picking one) -- callers that get
    None fall through to the ordinary external-matching path, exactly as if this
    heuristic didn't exist."""
    lowered = model_id.lower()
    is_review = any(_hint_matches(h, lowered) for h in _PURPOSE_NAME_HINTS["review"])
    is_execute = any(_hint_matches(h, lowered) for h in _PURPOSE_NAME_HINTS["execute"])
    if is_review == is_execute:   # neither matched, or both did (contradiction) -> None
        return None
    return "review" if is_review else "execute"
```

**Why `\b`-bounded, not raw substring:** `\b` matches at a transition
between a word character (`[A-Za-z0-9_]`) and a non-word character (or
string start/end). Router/gateway ids in this codebase delimit words with
`-`/`/`/`.`, none of which are word characters, so a genuine hyphen- or
slash-delimited purpose token (`router-env-plan-review`,
`router-env/coding`) still matches — but `"review"` no longer fires
inside `"gemini-3-pro-preview"` (the `r` in `review` is preceded by `p`,
a word character, so no boundary exists there) and `"coding"` no longer
fires inside `"encoding"`. This replaces the plain-`in` check from an
earlier draft of this spec, which had exactly this false-positive gap.

**Why gate on `infer_is_router` externally, not internally:** a real vendor
model's name is not a reliable purpose signal (nothing stops a future
model from being named `some-vendor/code-review-7b`), so this heuristic
must never run unqualified against every candidate — only against one
already independently confirmed to be a router/gateway by name. Mirrors
`infer_fallback_quota`'s existing pattern of delegating to
`infer_is_router` rather than re-deriving router-ness itself.

**Why token match, not suffix-only or raw substring:** a router operator's
naming convention isn't guaranteed to put the purpose word at the very
end (e.g. `review-router-env` vs `router-env-review`), so this can't be
suffix-only like `_MODEL_TIER_SUFFIXES`. It also can't be a raw substring
check like `_ROUTER_NAME_HINTS` uses, because raw substring matching is
exactly what let `"review"` fire inside `"preview"` in an earlier draft
of this spec (caught in review) — `_ROUTER_NAME_HINTS`'s own hints
(`"router"`, `"-env"`, `"local-llm"`) don't happen to collide with common
model-name words the way `"review"`/`"coding"` do, so that risk was latent
there but never triggered. The delimiter-bounded match in §4.1 is the
minimal fix: still a substring-family check (consistent with the rest of
this file), just anchored to word boundaries so it can't match inside a
larger word.

### 4.2 Wiring into `build_model_catalog` (`cli.py`)

At the top of the per-candidate loop (`skills/ai-kit-spec-review/ai_kit_spec/cli.py`,
currently starting `for candidate in discovered_models:` at line 235),
**before** the existing `md_match = match_models_dev(...)` call:

```python
for candidate in discovered_models:
    model_id = candidate["model_id"]
    cli_name = candidate["cli"]
    provider_hint = model_id.split("/", 1)[0] if "/" in model_id else None
    name_purpose = (infer_purpose_from_name(model_id)
                    if infer_is_router(provider_hint or "") or infer_is_router(model_id)
                    else None)
    if name_purpose:
        # Skip match_models_dev/match_artificial_analysis ENTIRELY for this candidate --
        # its purpose is unambiguous from its own name, and neither external source
        # models a router's operator-assigned routing label as a scorable capability
        # anyway, so querying either would spend a network call (Artificial Analysis:
        # quota-limited) for data this candidate will never use to decide its role.
        existing_key = _find_existing_key_for_runtime(existing_catalog, cli_name, model_id)
        provider = (existing_catalog[existing_key]["provider"] if existing_key
                    else provider_hint)
        if provider is None:
            unmatched.append({"cli": cli_name, "model_id": model_id, "provider": None,
                               "key": None, "vendor_unknown": True,
                               **_infer_heuristics("", model_id)})
            continue
        key = existing_key or canonical_key(provider, bare_model_part(model_id))
        existing_entry = catalog.get(key)
        heuristics = {field: (existing_entry or {}).get(field, inferred)
                      for field, inferred in _infer_heuristics(provider, model_id).items()}
        # Reuses the EXISTING preserve-on-source-down contract by passing models_dev_ok=
        # False / aa_ok=False for THIS candidate specifically -- exactly matches that
        # contract's own semantics ("the source wasn't queried this run, keep whatever's
        # cached"), which is literally true here: neither source was ever called. No new
        # field-preservation helper needed.
        md_fields = _preserved_or_fresh_md_fields(None, False, existing_entry)
        aa_fields = _preserved_or_fresh_aa_fields(None, False, existing_entry)
        aa_fields.pop("aa_pricing", None)
        ctx_window = _preserved_or_fresh_ctx_window(None, False, existing_entry, cli_name)
        entry = {
            "provider": (existing_entry or {}).get("provider", provider),
            "runtimes": {cli_name: {"model_id": model_id, "ctx_window": ctx_window}},
            **heuristics,
            "name_declared_purpose": name_purpose,
            "source": {
                "models_dev": (existing_entry or {}).get("source", {}).get(
                    "models_dev", False),
                "artificial_analysis": (existing_entry or {}).get("source", {}).get(
                    "artificial_analysis", False),
                "manual": (existing_entry or {}).get("source", {}).get("manual", False),
            },
            "confidence": (existing_entry or {}).get("confidence", "low"),
            "last_verified": (existing_entry or {}).get("last_verified", today),
            **md_fields,
        }
        entry.update(aa_fields)
        pricing = (existing_entry or {}).get("pricing")
        if pricing:
            entry["pricing"] = pricing
        catalog, reason = merge_catalog_entry(catalog, key, entry)
        if reason:
            rejections.append(reason)
        continue
    md_match = match_models_dev(model_id, models_dev_data) if models_dev_ok else None
    # ... existing body, entirely unchanged ...
```

**Global constraint this implies:** the existing body (from `md_match =
match_models_dev(...)` onward, currently lines 238–395) is **not
modified at all** — the new block above is a pure prepend that `continue`s
before reaching it. This keeps the effort-suffix-fallback logic
(`md_enrich_match`, shipped hours earlier the same day) completely
untouched and out of scope for this feature.

**Why derive `provider` this way, never from a match:** by construction
this branch never has `md_match`/`aa_match` to derive a provider from —
provider comes only from `existing_key`'s cached provider (a candidate
already known from a prior run) or the raw id's own `<vendor>/` prefix,
falling through to `unmatched` (exactly like the existing `vendor_unknown`
path) when neither is available, rather than guessing.

**Why `source.*` all preserve-from-existing rather than force `False`:**
a name-declared-purpose classification is a property of the id itself and
does not change whether a PRIOR run (before this feature existed, or
before the id was recognized as a router) already had real
models.dev/Artificial Analysis data cached for this exact key. Forcibly
zeroing `source.models_dev`/`source.artificial_analysis` here would
discard real prior data for no reason; preserving whatever's cached (and
simply never overwriting it with a fresh but never-attempted lookup)
matches the same non-destructive intent as every other preserve-on-down
path in this function.

### 4.3 Catalog schema (`model_catalog.py`)

Add `"name_declared_purpose": str` to `_FIELD_TYPES` (optional field, one
of `"review"`/`"execute"` when present — the literal validity check
belongs in `validate_catalog_entry`, not just the type table):

```python
_VALID_NAME_DECLARED_PURPOSE = {"review", "execute"}
```

and, in `validate_catalog_entry`, alongside the existing
`_VALID_CONFIDENCE` check:

```python
if "name_declared_purpose" in entry and entry["name_declared_purpose"] is not None \
        and entry["name_declared_purpose"] not in _VALID_NAME_DECLARED_PURPOSE:
    return f"{model_id}: 'name_declared_purpose' must be one of {sorted(_VALID_NAME_DECLARED_PURPOSE)}"
```

An absent `name_declared_purpose` means exactly what it means today for
every existing entry: "no name-based purpose declaration" — never treated
as a validation failure, consistent with every other optional field.

### 4.4 Wizard presentation (`ai-kit-spec-config/SKILL.md`, Step 2.2 items 5–6)

Before ranking (item 5's `python3 -c` snippet), partition `entries` by
`name_declared_purpose`:

```python
name_declared = [e for e in entries if e.get('name_declared_purpose')]
scored = [e for e in entries if not e.get('name_declared_purpose')]
```

`score_candidates` runs on `scored` only (unchanged call, smaller input).
For item 6's presentation, prepend each purpose's `name_declared` entries
(those whose `name_declared_purpose` matches that list) to the scored top-5,
labeled distinctly:

```
REVIEW (flagship/reasoning) — top candidates:
  • router-env-plan-review  via opencode  (declared by name — not scored)
  1. openai/gpt-5.6-sol     via codex     score 87  (intelligence 91 [via Artificial Analysis], ...)
  ...

EXECUTE (coding-agent) — top candidates:
  • router-env-coding       via opencode  (declared by name — not scored)
  1. anthropic/router-env   via opencode  score 90  (coding 89 [via Artificial Analysis], ...)
  ...
```

A name-declared candidate is **never** also checked against the other
purpose's list, never annotated with a cross-reference (unlike a genuine
scored "combo" model — §4.5 below), and never competes for a numbered
rank slot — it's presented, confirmed or declined by the user exactly like
any other candidate, but its position is fixed by its own declaration, not
earned by a score.

This replaces the "detect a name/list mismatch after scoring and re-route
it" mitigation added earlier the same day to Step 2.2 item 6 — that prose
is now dead code once this design prevents the misclassification at its
source (the candidate never enters `score_candidates` in the first place).
The existing "same key in both lists is expected" combo-model guidance
(§4.5) is unaffected and stays as-is; it addresses a different
condition entirely (a single key genuinely scored well under both weight
profiles), not a router's name-declared identity.

### 4.5 Interaction with the existing "combo model" guidance

No behavioral overlap: a name-declared candidate never enters
`score_candidates`, so it can never be the subject of a "same key ranked
in both lists" annotation — those two presentation paths are mutually
exclusive per candidate (a candidate either has `name_declared_purpose`
set, or it goes through scoring; never both).

## 5. Testing

- `model_heuristics.py`: new `TestInferPurposeFromName` class (pattern:
  `TestInferIsRouter`, `tests/test_ai_kit_spec.py:3589`) — covers both
  hint groups, the both-match contradiction (`None`), the neither-match
  case (`None`), case-insensitivity, AND a pinning test for the
  delimiter-boundary fix: `infer_purpose_from_name("router-env/gemini-3-pro-preview")`
  must be `None` (embedded `"review"` inside `"preview"` must NOT match),
  and `infer_purpose_from_name("router-env/some-encoding-model")` must
  also be `None` (embedded `"coding"` inside `"encoding"` must NOT match).
- `cli.py`'s `build_model_catalog`: new tests in the existing
  `TestBuildModelCatalog` class covering: (a) a router-named candidate
  with an unambiguous purpose word never calls `match_models_dev`/
  `match_artificial_analysis` (assert via a spy/mock or by constructing
  `models_dev_data`/`aa_models` fixtures that WOULD match if queried, and
  asserting the resulting entry's `source.models_dev`/
  `source.artificial_analysis` stay exactly whatever `existing_catalog`
  already had — proving the lookup never ran, not just that its result
  was discarded); (b) `name_declared_purpose` is set correctly for both
  groups; (c) a router-named candidate with NO purpose word (or a
  contradictory one) falls through to the unchanged existing path
  unaffected; (d) a non-router candidate whose name happens to contain
  "coding"/"review" is NOT affected by this heuristic at all (proves the
  `infer_is_router` gate holds); (e) cross-run preservation — a
  name-declared entry's cached `ctx_window`/pricing/`tool_calling` (from
  before this feature existed, or from a manual correction) survive a
  later run unchanged.
- `model_catalog.py`: `validate_catalog_entry` rejects an invalid
  `name_declared_purpose` value, accepts the two valid ones and an absent
  field.

## 6. Global Constraints (for the implementation plan)

- `infer_purpose_from_name` gains no network access and no dependency on
  `infer_is_router`'s own implementation beyond calling it externally —
  every caller gates on `infer_is_router` themselves; the function itself
  only inspects the string it's given.
- `_PURPOSE_NAME_HINTS` is exactly `{"review": ("review", "plan-review"),
  "execute": ("coding", "execute")}` — no additional tokens without a new
  round of design.
- Every hint match in `infer_purpose_from_name` MUST be delimiter-bounded
  (`\b`-anchored regex, per §4.1's `_hint_matches`), never a raw `in`
  substring check — a raw substring check is the exact defect this round
  of design fixed (`"review"` was matching inside `"preview"`).
- `build_model_catalog`'s existing body (from `md_match = ...` onward) is
  never modified — only prepended to. The effort-suffix-fallback logic
  (`md_enrich_match`) must remain byte-for-byte unchanged by this feature.
- A name-declared candidate must NEVER have `match_models_dev`/
  `match_artificial_analysis` called for it, under any circumstance —
  this is the feature's core resource-saving property and must be
  verifiable directly from a test, not just inferred from output shape.
- `name_declared_purpose` is optional, defaults to absent, and its
  presence/absence must never change validation behavior for any entry
  that doesn't set it.
- Single-file-set change: `model_heuristics.py`, `cli.py`,
  `model_catalog.py`, `ai-kit-spec-config/SKILL.md`, plus tests. No new
  CLI flags, no schema migration for existing entries (an entry written
  before this feature simply has no `name_declared_purpose` key, which is
  a valid absent-optional-field state already).
