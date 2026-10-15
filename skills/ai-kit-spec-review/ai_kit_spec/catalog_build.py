"""Model catalog build orchestration extracted from cli (16.1-13)."""
import re
import time
from typing import NamedTuple

from ai_kit_spec.model_catalog import canonical_key, merge_catalog_entry
from ai_kit_spec.model_heuristics import (
    infer_batch_mode,
    infer_fallback_quota,
    infer_is_router,
    infer_purpose_from_name,
)
from ai_kit_spec.model_matcher import (
    _strip_known_effort_suffix,
    bare_model_part,
    match_artificial_analysis,
    match_models_dev,
)


class CatalogSources(NamedTuple):
    models_dev_data: dict
    models_dev_ok: bool
    aa_models: list
    aa_ok: bool


class CatalogBuildCtx(NamedTuple):
    existing_catalog: dict
    sources: CatalogSources
    runtime_meta: dict | None
    today: str



def _find_existing_key_for_runtime(
    existing_catalog: dict, cli_name: str, model_id: str
) -> str | None:
    """CRITICAL/HIGH fix (round-2 native-opus review): a bare CLI-native id (no "<vendor>/"
    prefix, e.g. codex's "gpt-5.6-sol") carries no provider signal of its own. When BOTH
    external sources are unavailable this run -- most commonly `--if-stale` skipping the
    network fetch entirely, which is the wizard's own DEFAULT path, not an edge case -- the
    only way to recover this candidate's real vendor/model key is to look up which existing
    catalog entry already claims this exact (cli, model_id) runtime pairing. Without this
    lookup, build_model_catalog fell through to `provider = model_id`, minting an unstable
    "gpt-5.6-sol/gpt-5.6-sol" key every such run: it never matched the real
    "openai/gpt-5.6-sol" entry (permanently orphaning it and duplicating the catalog), AND it
    reclassified an already-known, already-enriched model as a brand-new `unmatched`
    candidate needing manual research + user confirmation on every single `--if-stale` run --
    exactly the per-model WebSearch pattern this design exists to eliminate."""
    for existing_key, existing_entry in existing_catalog.items():
        rt = existing_entry.get("runtimes", {}).get(cli_name)
        if isinstance(rt, dict) and rt.get("model_id") == model_id:
            return existing_key
    return None


def _slugify(name: str) -> str:
    """Best-effort vendor-name -> slug, used ONLY to derive a canonical `provider` when a bare
    (no "<vendor>/" prefix) model id matched Artificial Analysis but NOT models.dev -- AA's own
    `model_creator.name` ("OpenAI", "xAI") is free text, never a models.dev provider key, so it
    needs normalizing before it can become half of a canonical_key(). Lowercases and collapses
    every run of non-alphanumeric characters to a single hyphen."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _infer_heuristics(provider: str, model_id: str) -> dict:
    """Local naming heuristics (Task 5) for a single candidate -- factored out so both the
    matched-entry path AND the unmatched-candidate path (CRITICAL finding: an earlier draft
    computed these ONLY for matched entries, leaving the wizard's unmatched-candidate
    confirmation payload with no heuristic fields to show/confirm at all) compute them
    identically."""
    return {
        "is_router": infer_is_router(provider) or infer_is_router(model_id),
        "batch_mode": infer_batch_mode(model_id),
        "fallback_quota": infer_fallback_quota(provider) or infer_fallback_quota(model_id),
    }


def _image_input_from_models_dev(match: dict | None) -> bool | None:
    """Returns whether the string 'image' is in match's modalities.input list.
    Returns None when match is not a dict, when match.get("modalities") is not a dict,
    or when its input is not a list."""
    if not isinstance(match, dict):
        return None
    modalities = match.get("modalities")
    if not isinstance(modalities, dict):
        return None
    input_list = modalities.get("input")
    if not isinstance(input_list, list):
        return None
    return "image" in input_list


def _preserved_or_fresh_md_fields(md_match: dict | None, models_dev_ok: bool,
                                   existing_entry: dict | None,
                                   md_enrich_match: dict | None = None) -> dict:
    """CRITICAL: a models.dev fetch failure must never overwrite already-cached models.dev-
    sourced fields. If the source is down (models_dev_ok=False), copy whatever the existing
    entry already had for these fields verbatim (a key simply absent here is left absent from
    the returned dict, which merge_catalog_entry then treats as "preserve" -- correct, since a
    down source made no claim either way); only ever compute fresh values when the source
    actually answered this run.

    CRITICAL finding (Cross-Document Consistency / fresh-source no-match): when the source WAS
    queried genuinely this run (models_dev_ok=True) but found no match for this candidate
    (md_match is None), any fields it previously owned are now stale under a provenance that
    is about to flip to source.models_dev=False -- returning explicit None (not omission) for
    each is what tells merge_catalog_entry's clear-on-None contract to actually drop them,
    instead of silently retaining last run's values via plain dict-spread. `pricing` is
    deliberately NOT included here -- build_model_catalog owns pricing's combined
    models.dev-or-Artificial-Analysis fallback logic itself, since either source can supply it.

    NEW (design spec 2026-09-05): md_enrich_match is this spec's effort-suffix enrichment
    retry result (cli.py's build_model_catalog loop) -- consulted ONLY when the PRIMARY
    md_match found nothing this run. It never overrides a real md_match.

    NEW (16 D-09): image_input (optional bool; present only when models.dev stated it via
    modalities.input) and image_input_source (field-level provenance; present only when
    image_input is present) are written and cleared TOGETHER -- both keys always appear in
    the returned dict for consistency, either as a (bool, "models_dev") pair, explicit Nones
    for clear, or both omitted to preserve a cached runtime-derived value across a fetch skip."""
    if not models_dev_ok:
        existing_entry = existing_entry or {}
        result = {k: existing_entry[k] for k in
                ("tool_calling", "structured_output", "max_output_tokens")
                if k in existing_entry}
        # On skip: carry forward only a models_dev-sourced value; a runtime-derived value is
        # left out so this snapshot's opencode reading can replace it
        if (existing_entry.get("image_input_source") == "models_dev" and
                isinstance(existing_entry.get("image_input"), bool)):
            result["image_input"] = existing_entry["image_input"]
            result["image_input_source"] = "models_dev"
        return result
    if md_match:
        img = _image_input_from_models_dev(md_match)
        return {"tool_calling": md_match.get("tool_call"),
                "structured_output": md_match.get("structured_output"),
                "max_output_tokens": md_match.get("limit", {}).get("output"),
                "image_input": img,
                "image_input_source": "models_dev" if img is not None else None}
    source = md_enrich_match
    if not source:
        return {"tool_calling": None, "structured_output": None, "max_output_tokens": None,
                "image_input": None, "image_input_source": None}
    img = _image_input_from_models_dev(source)
    return {"tool_calling": source.get("tool_call"),
            "structured_output": source.get("structured_output"),
            "max_output_tokens": source.get("limit", {}).get("output"),
            "image_input": img,
            "image_input_source": "models_dev" if img is not None else None}


def _preserved_or_fresh_ctx_window(md_match: dict | None, models_dev_ok: bool,
                                    existing_entry: dict | None, cli_name: str,
                                    md_enrich_match: dict | None = None):
    """CRITICAL: same preserve-on-source-down contract as _preserved_or_fresh_md_fields, but for
    a RUNTIME-level field (ctx_window lives inside runtimes[cli_name], not at the entry's top
    level) -- an earlier draft always recomputed this from `md_match`, which is unconditionally
    None whenever models_dev_ok is False, silently blanking an already-cached runtime's
    ctx_window on every models.dev outage.

    NEW (design spec 2026-09-05): falls back to md_enrich_match's own context limit only when
    md_match itself is falsy."""
    if not models_dev_ok:
        existing_entry = existing_entry or {}
        return existing_entry.get("runtimes", {}).get(cli_name, {}).get("ctx_window")
    return (md_match or md_enrich_match or {}).get("limit", {}).get("context")


def _preserved_or_fresh_aa_fields(aa_match: dict | None, aa_ok: bool,
                                   existing_entry: dict | None) -> dict:
    """Same contract as _preserved_or_fresh_md_fields, for Artificial Analysis's fields.
    CRITICAL: `aa_ok` here means "this run's AA field values are trustworthy, use them as-is"
    -- the CALLER (fetch-model-catalog's command body, Step 5 below) is responsible for passing
    `aa_ok=False` not only on a real fetch failure but ALSO when no API key was configured at
    all (Task 4's fetch_artificial_analysis returns `ok=True` for "deliberately skipped," which
    is correct for that module's own contract, but wrong to treat as "AA was queried and found
    nothing" here -- those are different transitions and must not collapse into one)."""
    if not aa_ok:
        existing_entry = existing_entry or {}
        return {k: existing_entry[k] for k in ("scores", "tokens_per_sec") if k in existing_entry}
    if not aa_match:
        # CRITICAL finding (fresh-source no-match): aa_ok=True here means Artificial Analysis
        # WAS queried for real this run (the caller already collapsed "no API key" into
        # aa_ok=False, see this function's own docstring below) and genuinely found no match --
        # any scores/tokens_per_sec it previously supplied are now stale under a provenance
        # about to flip to source.artificial_analysis=False. Explicit None (not omission) is
        # what tells merge_catalog_entry's clear-on-None contract to actually drop them.
        return {"scores": None, "tokens_per_sec": None}
    evaluations = aa_match.get("evaluations", {})
    fields = {"scores": {
        "intelligence_index": evaluations.get("artificial_analysis_intelligence_index"),
        "coding_index": evaluations.get("artificial_analysis_coding_index"),
        "agentic_index": evaluations.get("artificial_analysis_agentic_index"),
    }}
    # MEDIUM finding (round-4): a genuine PARTIAL match -- aa_match exists (AA was queried and
    # matched this candidate this run) but this specific match's own performance payload has
    # no median_output_tokens_per_second -- must clear a stale cached tokens_per_sec the same
    # way a full no-match already does above, not silently retain it via omission.
    # merge_catalog_entry only preserves a field genuinely ABSENT from this dict; explicit None
    # is what tells it "queried, no value this run" and to actually drop it. An earlier draft
    # only ever set this key when a fresh value existed, leaving a stale tokens_per_sec
    # untouched under a source.artificial_analysis flag that's about to read True again --
    # the same staleness bug class the clear-on-None contract exists to prevent.
    perf = aa_match.get("performance", {})
    fields["tokens_per_sec"] = perf.get("median_output_tokens_per_second")
    pricing = aa_match.get("pricing", {})
    if pricing.get("price_1m_input_tokens") is not None:
        fields["aa_pricing"] = {"input_per_1m": pricing.get("price_1m_input_tokens"),
                                 "output_per_1m": pricing.get("price_1m_output_tokens")}
    return fields


def _runtime_meta_from_snapshot(runtimes: dict) -> dict:
    """Extracts per-model runtime metadata from a runtimes snapshot dict,
    keyed by `(cli_name, model_id)` tuples. Today it carries each entry's
    `reasoning_modes` value (a dict mapping model id -> effort list, which
    `build_runtimes_snapshot` populates for codex when `codex debug models`
    enumerates) and `image_input` (for opencode, from `opencode models
    --verbose`) into a flat `{"reasoning_modes": [...], "image_input": bool}`
    record per model. Anything malformed is skipped, never raised: a non-dict
    `clis` entry, a non-dict `reasoning_modes` or `image_input`, a blank/
    `str`-keyed lookup, an effort list that is not a non-empty list of
    `str`, or an `image_input` value that is not a bool."""
    meta = {}
    for cli_name, cli_data in (runtimes or {}).get("clis", {}).items():
        if not isinstance(cli_data, dict):
            continue
        modes_map = cli_data.get("reasoning_modes")
        if isinstance(modes_map, dict):
            for model_id, modes in modes_map.items():
                if not isinstance(model_id, str) or not model_id.strip():
                    continue
                if (not isinstance(modes, list) or not modes
                        or not all(isinstance(m, str) for m in modes)):
                    continue
                meta.setdefault((cli_name, model_id), {})["reasoning_modes"] = list(modes)
        # D-09 source 2: image_input is only read from opencode runtime metadata
        if cli_name == "opencode":
            image_map = cli_data.get("image_input")
            if isinstance(image_map, dict):
                for model_id, image in image_map.items():
                    if not isinstance(model_id, str) or not model_id.strip():
                        continue
                    if not isinstance(image, bool):
                        continue
                    meta.setdefault((cli_name, model_id), {})["image_input"] = image
    return meta


def _apply_runtime_meta(entry: dict, runtime_meta: dict | None, cli_name: str,
                        model_id: str, runtime_wins_image_input: bool = False) -> None:
    """Copies per-model runtime metadata (from `_runtime_meta_from_snapshot`)
    onto `entry` IN PLACE. Only a non-empty CLI-reported `reasoning_modes`
    list is applied. For `image_input` (when `runtime_wins_image_input` is
    True or when the entry's existing value is not a bool), both
    `image_input` and `image_input_source` are set — the value from metadata
    and "opencode" as the source. When the (cli_name, model_id) lookup
    misses, `entry` is left untouched — an absent key lets `merge_catalog_entry`
    preserve whatever the cache already had."""
    meta = (runtime_meta or {}).get((cli_name, model_id)) or {}
    modes = meta.get("reasoning_modes") or []
    if modes:
        entry["reasoning_modes"] = list(modes)
    if isinstance(meta.get("image_input"), bool) and (
            runtime_wins_image_input or not isinstance(entry.get("image_input"), bool)):
        entry["image_input"] = meta["image_input"]
        entry["image_input_source"] = "opencode"


# 16 D-04 (review cycle 2): claude only ever runs anthropic models, so its bare ids are
# matched against models.dev with `anthropic` as the tie-break hint. On live models.dev
# (2026-09-24) every anthropic id also appears under 9-21 reseller providers (e.g.
# `claude-sonnet-5` under `opencode`, `github-copilot`, `azure` and more), and
# match_models_dev returns no match for an unhinted multi-provider bare id -- the hint only
# breaks ties (a single match still wins regardless of the hint). Every other CLI maps to
# no hint, which is exactly the pre-16-04 call.
_FIRST_PARTY_PROVIDER_BY_CLI = {"claude": "anthropic"}


def _anthropic_model_ids(models_dev_data) -> list:
    """Sorted, de-duplicated model ids from models.dev's `anthropic` provider (16 D-04),
    keeping ONLY well-formed rows: a row must be a dict whose `limit` and `cost` values,
    for each of those two keys that is present, are dicts too. fetch_models_dev validates
    only the JSON transport, not the row shape -- match_models_dev spreads the matched row
    (`{**model, ...}`) and build_model_catalog calls `.get` on the matched row's `limit` and
    `cost`, so a `null`, string or list row (or one whose `limit`/`cost` is not an object)
    would otherwise raise inside fetch-model-catalog once its id became a materialization
    candidate (review cycle 3). A skipped row is neither recorded in `_meta` nor
    materialized. Never raises: a non-dict payload, a missing/non-dict `anthropic` provider,
    or a missing/non-dict `models` mapping yields []."""
    if not isinstance(models_dev_data, dict):
        return []
    provider = models_dev_data.get("anthropic")
    if not isinstance(provider, dict):
        return []
    models = provider.get("models")
    if not isinstance(models, dict):
        return []
    ids = set()
    for model_id, row in models.items():
        if not isinstance(model_id, str) or not model_id.strip():
            continue
        if not isinstance(row, dict):
            continue
        if not all(isinstance(row[key], dict) for key in ("limit", "cost") if key in row):
            continue
        ids.add(model_id)
    return sorted(ids)


def _process_catalog_candidate(
    candidate: dict,
    catalog: dict,
    ctx: CatalogBuildCtx,
) -> tuple[dict, str | None, dict | None]:
    existing_catalog = ctx.existing_catalog
    sources = ctx.sources
    runtime_meta = ctx.runtime_meta
    today = ctx.today
    models_dev_data = sources.models_dev_data
    models_dev_ok = sources.models_dev_ok
    aa_models = sources.aa_models
    aa_ok = sources.aa_ok
    model_id = candidate["model_id"]
    cli_name = candidate["cli"]
    provider_hint = model_id.split("/", 1)[0] if "/" in model_id else None
    # Gate on infer_is_router(model_id) alone -- provider_hint is always a prefix of
    # model_id and infer_is_router is a plain substring test (model_heuristics.py), so
    # infer_is_router(provider_hint or "") can never be true when infer_is_router(model_id)
    # is false. A two-argument OR here would be redundant, not defensive.
    name_purpose = (infer_purpose_from_name(model_id)
                    if infer_is_router(model_id)
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
            # HIGH-adjacent fix (review MEDIUM finding): a bare id with no existing catalog
            # entry to recover a provider from still has a real, unambiguous
            # name_declared_purpose -- carry it onto the unmatched payload rather than
            # silently discarding it, since Task 4's wizard partition can only act on a
            # field it can actually see. `_infer_heuristics("", model_id)` is unchanged from
            # the existing unmatched-path convention (an empty provider is the existing
            # convention for "no vendor to infer from," used identically by the ordinary
            # unmatched path a few lines below in the function's existing body).
            record = {"cli": cli_name, "model_id": model_id, "provider": None,
                      "key": None, "vendor_unknown": True,
                      "name_declared_purpose": name_purpose,
                      **_infer_heuristics("", model_id)}
            _apply_runtime_meta(record, runtime_meta, cli_name, model_id)
            return catalog, None, record
        key = existing_key or canonical_key(provider, bare_model_part(model_id))
        existing_entry = catalog.get(key)
        heuristics = {field: (existing_entry or {}).get(field, inferred)
                      for field, inferred in _infer_heuristics(provider, model_id).items()}
        # Reuses the EXISTING preserve-on-source-down contract by passing
        # models_dev_ok=False / aa_ok=False for THIS candidate specifically -- exactly
        # matches that contract's own semantics ("the source wasn't queried this run,
        # keep whatever's cached"), which is literally true here: neither source was
        # ever called. No new field-preservation helper needed.
        md_fields = _preserved_or_fresh_md_fields(None, False, existing_entry)
        # NOTE: no `aa_fields.pop("aa_pricing", None)` here (an earlier draft had one) --
        # `_preserved_or_fresh_aa_fields(None, False, existing_entry)` always takes its
        # `not aa_ok` branch, which returns only cached `scores`/`tokens_per_sec` and can
        # never contain an `aa_pricing` key, so the pop would always be a no-op.
        aa_fields = _preserved_or_fresh_aa_fields(None, False, existing_entry)
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
        _apply_runtime_meta(entry, runtime_meta, cli_name, model_id,
                            runtime_wins_image_input=True)
        catalog, reason = merge_catalog_entry(catalog, key, entry)
        return catalog, reason, None
    # 16 D-04 (review cycle 2): claude's bare ids get `anthropic` as the provider hint
    # (see _FIRST_PARTY_PROVIDER_BY_CLI above); every other CLI's hint is None, exactly
    # the pre-16-04 call. The router/name-purpose path above never consults models.dev.
    md_match = (match_models_dev(
        model_id, models_dev_data,
        provider_hint=_FIRST_PARTY_PROVIDER_BY_CLI.get(cli_name)) if models_dev_ok
        else None)
    provider_hint = (md_match or {}).get("provider") or (
        model_id.split("/", 1)[0] if "/" in model_id else None)
    aa_match = (match_artificial_analysis(model_id, aa_models, provider_hint=provider_hint)
                if aa_ok else None)
    # NEW: an ENRICHMENT-ONLY retry (design spec 2026-09-05) -- deliberately kept in its
    # own variable, never assigned into md_match itself, and using ONLY the ordinary,
    # unmodified match_models_dev (no effort-awareness lives inside that function at
    # all). Consumed exclusively by the two field-preservation helpers below; never read
    # by provider/key/pricing derivation.
    # When the retry's lookup resolves to a single models.dev row, that row's fields are
    # used even if its provider disagrees with aa_provider_hint -- match_models_dev only
    # consults provider_hint to disambiguate an actual multi-row collision. This is
    # accepted: a lone row is still better signal than no signal (fields would otherwise
    # stay null).
    md_enrich_match = None
    if models_dev_ok and md_match is None and aa_match:
        # Deliberate: aa_provider_hint is derived from Artificial Analysis's own
        # model_creator.name (the first-party/creator row), not from the CLI-reported id's
        # own vendor prefix (e.g. for "github-copilot/claude-opus-5-high" the hint used is
        # "anthropic", not "github-copilot"). The spec treats the creator row as more
        # authoritative than a reseller's own prefix.
        aa_provider_hint = _slugify(
            (aa_match.get("model_creator") or {}).get("name", "")) or None
        if aa_provider_hint:
            md_enrich_match = match_models_dev(model_id, models_dev_data,
                                                provider_hint=aa_provider_hint,
                                                allow_fuzzy=False)
            if md_enrich_match is None:
                stripped = _strip_known_effort_suffix(bare_model_part(model_id))
                if stripped:
                    md_enrich_match = match_models_dev(stripped, models_dev_data,
                                                        provider_hint=aa_provider_hint,
                                                        allow_fuzzy=False)
    existing_key = _find_existing_key_for_runtime(existing_catalog, cli_name, model_id)
    # Important finding (coordinator review): `existing_key` recovery must ONLY apply when
    # this run genuinely has no signal of its own (md_match is None AND aa_match is None) --
    # the function's own docstring already says so ("neither source matched THIS run"), but
    # the original code consulted `existing_key` unconditionally for the final `key`, so a
    # stale/mis-keyed cached entry (e.g. minted while a source was down) could never
    # self-heal once the source came back with a real, authoritative match: the stale key
    # would keep winning forever. `no_signal_this_run` gates both the provider fallback AND
    # the final key selection so a genuine fresh match always wins over a cached key.
    no_signal_this_run = md_match is None and aa_match is None
    vendor_unknown = False
    if md_match:
        provider = md_match["provider"]
    elif provider_hint:
        provider = provider_hint
    elif aa_match and _slugify((aa_match.get("model_creator") or {}).get("name", "")):
        # WR-01 fix: guard on the SLUGIFIED result, not the raw name -- mirrors the
        # already-guarded aa_provider_hint call site a few lines above. A raw name that is
        # non-empty but entirely non-alphanumeric (e.g. "—") slugifies to "", and without
        # this guard `provider` became "" (a str, not None), which passed the `if provider
        # is not None` gate below and minted a malformed "/<model>" catalog key instead of
        # routing to the vendor_unknown=True safeguard a few lines below.
        provider = _slugify(aa_match["model_creator"]["name"])
    elif no_signal_this_run and existing_key:
        # CRITICAL/HIGH fix: neither source matched this run (most commonly both were
        # skipped by `--if-stale`) and the raw id carries no vendor prefix -- recover the
        # real provider/key from the catalog entry that already claims this exact
        # (cli, model_id) runtime, instead of minting an unstable "model_id/model_id" key
        # that would orphan the real entry and misclassify it as unmatched every run.
        provider = existing_catalog[existing_key]["provider"]
    else:
        # Important finding (coordinator review): genuinely zero *usable* vendor signal --
        # this covers BOTH "no match at all this run, no '<vendor>/' prefix on the raw id,
        # and no existing catalog entry to recover from" AND (round-2 re-review finding)
        # "aa_match exists but its own model_creator.name is missing/empty," which reaches
        # this same `else` since the `aa_match and (aa_match.get("model_creator") or {}).get(
        # "name")` elif above requires BOTH truthy. Either way there is no real vendor to
        # report. Falling back to `provider = model_id` used to mint a plausible-looking but
        # entirely fabricated self-referential "model_id/model_id" key on the UNMATCHED
        # candidate payload surfaced to the wizard (Task 8); since that key looks
        # legitimate, a future wizard implementation could accidentally trust and persist it
        # as-is. `provider=None` + `vendor_unknown=True` forces whatever confirms this
        # candidate later to supply a real vendor rather than silently trusting a guess.
        provider = None
        vendor_unknown = True
    key = (existing_key if no_signal_this_run and existing_key else
           (canonical_key(provider, bare_model_part(model_id)) if provider is not None
            else None))
    existing_entry = catalog.get(key) if key else None

    # Important finding (round-2 re-review): `provider is None` (vendor_unknown) MUST route
    # here too, not just "both sources found literally nothing this run" -- an AA match with
    # no usable model_creator.name lands in the `else` branch above (aa_match truthy, so the
    # OLD `md_match is None and aa_match is None` check alone excluded it), leaving `provider`
    # None while falling through into the matched/enrichment branch below, where an unguarded
    # `_infer_heuristics(provider, model_id)` call raised `AttributeError: 'NoneType' object
    # has no attribute 'lower'` and aborted the ENTIRE run -- every other candidate in the
    # same batch lost with it. `provider is None` here always implies `key is None` (see
    # above) which always implies `existing_entry is None`, so this is a pure widening of the
    # routing condition, not a new state to reconcile with the second clause.
    if provider is None or (md_match is None and aa_match is None and existing_entry is None):
        record = {"cli": cli_name, "model_id": model_id, "provider": provider,
                  "key": key, "vendor_unknown": vendor_unknown,
                  **_infer_heuristics(provider or "", model_id)}
        _apply_runtime_meta(record, runtime_meta, cli_name, model_id)
        return catalog, None, record

    md_fields = _preserved_or_fresh_md_fields(md_match, models_dev_ok, existing_entry,
                                               md_enrich_match=md_enrich_match)
    aa_fields = _preserved_or_fresh_aa_fields(aa_match, aa_ok, existing_entry)
    aa_pricing = aa_fields.pop("aa_pricing", None)
    # CRITICAL finding (fresh-source no-match / pricing can come from EITHER source): a
    # models.dev match's own cost fields aren't returned via _preserved_or_fresh_md_fields
    # (pricing is combined here, not per-source), so recompute them directly from md_match.
    md_cost = (md_match or {}).get("cost", {}) if models_dev_ok and md_match else {}
    md_pricing = ({"input_per_1m": md_cost.get("input"), "output_per_1m": md_cost.get("output")}
                  if md_cost else None)
    pricing = md_pricing or aa_pricing
    clear_pricing = False
    if pricing is None:
        if not models_dev_ok or not aa_ok:
            # At least one source is down/unconfigured this run -- its silence says nothing
            # about whether pricing is still correct, so preserve whatever's cached (leave
            # the "pricing" key out of `entry` entirely below -- omission preserves).
            pricing = (existing_entry or {}).get("pricing")
        elif (existing_entry or {}).get("pricing") is not None:
            # CRITICAL finding: BOTH sources were genuinely queried this run and NEITHER
            # matched -- cached pricing is now stale under a provenance about to flip both
            # source.* flags to False. clear_pricing signals an explicit None below, which
            # merge_catalog_entry's clear-on-None contract then actually drops.
            clear_pricing = True
    ctx_window = _preserved_or_fresh_ctx_window(md_match, models_dev_ok, existing_entry,
                                                  cli_name, md_enrich_match=md_enrich_match)
    # MEDIUM finding: this used to reimplement _infer_heuristics' own three-line body
    # inline (a second, separately-maintained copy of the exact same heuristic calls),
    # contradicting that function's own docstring claim that both paths call it. Calling
    # it here instead removes the duplication -- an existing cached value still wins over
    # a freshly-inferred one wherever present, unchanged from before.
    heuristics = {
        field: (existing_entry or {}).get(field, inferred)
        for field, inferred in _infer_heuristics(provider, model_id).items()
    }

    matched_this_run = md_match is not None or aa_match is not None
    entry = {
        "provider": (existing_entry or {}).get("provider", provider),
        "runtimes": {cli_name: {"model_id": model_id, "ctx_window": ctx_window}},
        **heuristics,
        "source": {
            "models_dev": (md_match is not None) if models_dev_ok
                          else (existing_entry or {}).get("source", {}).get(
                              "models_dev", False),
            "artificial_analysis": (aa_match is not None) if aa_ok
                          else (existing_entry or {}).get("source", {}).get(
                              "artificial_analysis", False),
            "manual": (existing_entry or {}).get("source", {}).get("manual", False),
        },
        "confidence": "high" if matched_this_run else (existing_entry or {}).get(
            "confidence", "low"),
        "last_verified": today if matched_this_run else (existing_entry or {}).get(
            "last_verified", today),
        **md_fields,
    }
    if pricing:
        entry["pricing"] = pricing
    elif clear_pricing:
        entry["pricing"] = None    # explicit clear signal -- see merge_catalog_entry
    entry.update(aa_fields)
    _apply_runtime_meta(entry, runtime_meta, cli_name, model_id)
    catalog, reason = merge_catalog_entry(catalog, key, entry)
    return catalog, reason, None

def build_model_catalog(
    discovered_models: list,
    sources: CatalogSources,
    existing_catalog: dict,
    runtime_meta: dict | None = None,
) -> tuple:
    """Pure orchestration (design spec 2026-09-02, Section 4 steps 2-5): match each discovered
    {"cli", "model_id"} candidate against both external sources, enrich deterministically from
    whatever matched (or preserve cached fields when a source is down -- see the _preserved_
    or_fresh_* helpers), apply local naming heuristics for is_router/batch_mode/fallback_quota
    ONLY on first discovery (a value already present on `existing_entry` is a prior heuristic
    default or a user's own correction -- HIGH finding: every later rebuild must preserve it,
    never silently recompute over it), and merge into `existing_catalog` under a CANONICAL
    vendor/model key (model_catalog.canonical_key) so two CLIs reporting the same real model
    under different raw ids collapse into one entry with both runtimes merged in. A bare id
    (no "<vendor>/" prefix) with NEITHER source matched this run first tries
    `_find_existing_key_for_runtime` against `existing_catalog` before ever falling back to
    minting a fresh key (CRITICAL/HIGH fix, round-2 native-opus review) -- this is what keeps
    the `--if-stale` default path from orphaning an already-known model under an unstable
    "model_id/model_id" key and reclassifying it as needing manual research every run.
    Entries for candidates NOT in `discovered_models` this run are preserved untouched. Returns
    (new_catalog, rejections, unmatched): `unmatched` lists brand-new candidates that matched
    NEITHER source and have no prior catalog entry -- these are NEVER added to new_catalog here
    (spec Section 4/8: research + user confirmation must happen first, Task 8's wizard); each
    unmatched entry ALSO carries its own is_router/batch_mode/fallback_quota heuristic fields
    (CRITICAL finding: these must exist for the wizard's confirmation payload even though the
    candidate isn't in the catalog yet) computed via the same `_infer_heuristics` the matched
    path uses. A bare model id (no "<vendor>/" prefix, e.g. codex's own naming) that matched
    Artificial Analysis but NOT models.dev derives its `provider` from AA's `model_creator.name`
    (HIGH finding: it must never become its own vendor by falling through to the model id
    itself). Artificial Analysis pricing fills in when models.dev has no match for that
    candidate (HIGH finding: AA data must not be discarded just because models.dev didn't
    match). The optional `runtime_meta` dict (from `_runtime_meta_from_snapshot`, keyed by
    (cli_name, model_id)) carries CLI-reported per-model runtime metadata — today each
    codex model's `reasoning_modes` effort list, read from the CLI itself via
    `codex debug models` — onto BOTH the matched entries AND the `unmatched` records
    (a brand-new codex slug no external source knows exits through the unmatched branch,
    and its effort levels must still reach the wizard's confirmation payload; the wizard
    copies that CLI-reported list verbatim, per ai-kit-spec-config's own
    cli-model-selection.md). The metadata key is only added when the lookup actually has
    one, so callers that pass no `runtime_meta` see byte-identical records as before."""
    catalog = dict(existing_catalog)
    rejections = []
    unmatched = []
    today = time.strftime("%Y-%m-%d")
    for candidate in discovered_models:
        catalog, rejection, record = _process_catalog_candidate(
            candidate,
            catalog,
            CatalogBuildCtx(existing_catalog, sources, runtime_meta, today),
        )
        if rejection:
            rejections.append(rejection)
        if record:
            unmatched.append(record)
    return catalog, rejections, unmatched



