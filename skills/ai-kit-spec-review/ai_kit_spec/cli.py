import json
import os
import re
import shutil
import subprocess
import sys
import time

from ai_kit_spec.cache import cache_is_stale, cache_read_json, cache_write_json
from ai_kit_spec.commands import (
    ResolvedReviewer,
    build_reviewer_command,
    build_reviewer_model_id,
    render_reviewer_command,
)
from ai_kit_spec.config_io import (
    cfg_render_toml,
    cfg_resolve,
    cfg_write_toml,
    resolve_timeout_tiers,
)
from ai_kit_spec.detection import (
    RUNTIMES_TTL_SECONDS,
    build_runtimes_snapshot,
    cache_runtimes_path,
    detect_current_runtime,
    detect_tool_availability,
    find_codegraph_alternative,
    group_models_by_family,
)
from ai_kit_spec.execute_dispatch import dispatch_execute
from ai_kit_spec.local_secrets import load_secret
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
from ai_kit_spec.model_sources import fetch_artificial_analysis, fetch_models_dev
from ai_kit_spec.quota import (
    QUOTA_TTL_SECONDS,
    cache_quota_path,
    probe_reviewer_quota,
    refresh_quota_cache,
    resolve_reviewers,
)
from ai_kit_spec.review_reports import (
    merge_findings,
    render_merged_report,
    report_declares_issues,
    report_has_status,
)
from ai_kit_spec.reviewer_dispatch import dispatch_reviewer
from ai_kit_spec.vendor import infer_vendor_from_model


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
    md_match found nothing this run. It never overrides a real md_match."""
    if not models_dev_ok:
        existing_entry = existing_entry or {}
        return {k: existing_entry[k] for k in
                ("tool_calling", "structured_output", "max_output_tokens")
                if k in existing_entry}
    if md_match:
        return {"tool_calling": md_match.get("tool_call"),
                "structured_output": md_match.get("structured_output"),
                "max_output_tokens": md_match.get("limit", {}).get("output")}
    source = md_enrich_match
    if not source:
        return {"tool_calling": None, "structured_output": None, "max_output_tokens": None}
    return {"tool_calling": source.get("tool_call"),
            "structured_output": source.get("structured_output"),
            "max_output_tokens": source.get("limit", {}).get("output")}


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


def build_model_catalog(discovered_models: list, models_dev_data: dict, models_dev_ok: bool,
                         aa_models: list, aa_ok: bool, existing_catalog: dict) -> tuple:
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
    match)."""
    catalog = dict(existing_catalog)
    rejections = []
    unmatched = []
    today = time.strftime("%Y-%m-%d")
    for candidate in discovered_models:
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
                unmatched.append({"cli": cli_name, "model_id": model_id, "provider": None,
                                   "key": None, "vendor_unknown": True,
                                   "name_declared_purpose": name_purpose,
                                   **_infer_heuristics("", model_id)})
                continue
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
            catalog, reason = merge_catalog_entry(catalog, key, entry)
            if reason:
                rejections.append(reason)
            continue
        md_match = match_models_dev(model_id, models_dev_data) if models_dev_ok else None
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
        elif aa_match and (aa_match.get("model_creator") or {}).get("name"):
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
            unmatched.append({"cli": cli_name, "model_id": model_id, "provider": provider,
                               "key": key, "vendor_unknown": vendor_unknown,
                               **_infer_heuristics(provider or "", model_id)})
            continue

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
        catalog, reason = merge_catalog_entry(catalog, key, entry)
        if reason:
            rejections.append(reason)
    return catalog, rejections, unmatched


def main(argv: list, which_fn=shutil.which, run_fn=subprocess.run,
         dispatch_execute_fn=dispatch_execute, dispatch_reviewer_fn=dispatch_reviewer,
         env_fn=lambda: dict(os.environ),
         load_secret_fn=load_secret, fetch_models_dev_fn=fetch_models_dev,
         fetch_artificial_analysis_fn=fetch_artificial_analysis) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="review-spec")
    sub = parser.add_subparsers(dest="command", required=True)

    p_cache_path = sub.add_parser("cache-path")
    p_cache_path.add_argument("--kind", choices=["runtimes", "quota", "catalog"], required=True)

    sub.add_parser("detect-tools")
    sub.add_parser("detect-current-runtime")

    p_detect = sub.add_parser("detect-runtimes")
    p_detect.add_argument(
        "--save", default=None, help="write the snapshot to this path via cache_write_json"
    )
    p_detect.add_argument(
        "--if-stale", default=None, metavar="PATH",
        help=(
            "skip detection entirely (print {} and exit 0) when PATH exists "
            "and is fresher than RUNTIMES_TTL_SECONDS; else detect and --save to PATH"
        ),
    )

    p_catalog = sub.add_parser("fetch-model-catalog")
    p_catalog.add_argument(
        "--runtimes-json", required=True,
        help="path to a detect-runtimes snapshot (as saved via --save/--if-stale)")
    p_catalog.add_argument("--catalog-path", required=True)
    p_catalog.add_argument("--cwd", default=None,
                            help="for resolving review-spec.toml's already-registered "
                                 "single-provider-CLI models; defaults to the process cwd")
    p_catalog.add_argument(
        "--extra-candidate", action="append", default=[], metavar="CLI:MODEL_ID",
        help="repeatable; a wizard-typed single-provider-CLI candidate not yet in "
             "review-spec.toml (e.g. a first-time codex/grok setup with nothing registered "
             "yet) -- still goes through the same matching/enrichment path as anything else.")
    p_catalog.add_argument(
        "--if-stale", action="store_true",
        help="gate NETWORK CALLS ONLY: when --catalog-path exists and is fresher than "
             "CATALOG_TTL_SECONDS, skip fetching models.dev/Artificial Analysis and reuse "
             "cached fields for every already-known candidate -- candidate DISCOVERY/"
             "RECONCILIATION (runtimes snapshot + registered single-provider-CLI models + "
             "--extra-candidate) always runs regardless of this flag, every invocation, so a "
             "brand-new candidate is never silently missed just because the catalog is fresh "
             "(CRITICAL finding: an earlier draft exited before even building the candidate "
             "list when fresh, which is wrong -- freshness should only ever skip re-fetching, "
             "never skip reconciling what's newly installed).")
    # MEDIUM finding: spec Section 8 names a `fetch-model-catalog --force` flag for manual
    # refresh. This plan deliberately does NOT add a separate `--force` flag: the command's
    # default behavior (no flag at all) already re-fetches both external sources unconditionally
    # -- `skip_fetch` below is only ever true when `--if-stale` is explicitly passed AND the
    # cache is fresh. So "run without `--if-stale`" IS the manual-refresh/force path the spec
    # names; a dedicated `--force` flag would be a same-effect alias, not new behavior, and is
    # intentionally omitted here rather than left as a silent, unrecorded gap.

    p_confirm = sub.add_parser("confirm-catalog-entry")
    p_confirm.add_argument("--catalog-path", required=True)
    p_confirm.add_argument("--entry-json", required=True,
                            help="path to a temp JSON file: {\"model_id\": ..., \"entry\": {...}} "
                                 "-- same JSON-temp-file convention as render-toml's --json-config")

    p_apply_correction = sub.add_parser("apply-heuristic-correction")
    p_apply_correction.add_argument("--catalog-path", required=True)
    p_apply_correction.add_argument("--model-id", required=True)
    p_apply_correction.add_argument(
        "--corrections-json", required=True,
        help="path to a temp JSON file: a flat object of any subset of "
             "is_router/batch_mode/fallback_quota, e.g. {\"is_router\": false}")

    p_quota = sub.add_parser("probe-quota")
    p_quota.add_argument("--cwd", required=True)
    p_quota.add_argument("--quota-path", required=True)

    p_resolve = sub.add_parser("resolve-reviewers")
    p_resolve.add_argument("--cwd", required=True)
    p_resolve.add_argument("--quota-path", required=True)
    p_resolve.add_argument("--source-vendor", default="")  # "" = no same-vendor skip
    p_resolve.add_argument("--cross-ai", action="store_true")

    p_merge = sub.add_parser("merge-reports")
    p_merge.add_argument("--doc-paths", required=True)
    p_merge.add_argument("reports", nargs="+", help="key=path/to/report.md")

    p_toml = sub.add_parser("render-toml")
    p_toml.add_argument(
        "--json-config", required=True, help="path to a JSON file shaped like the TOML config"
    )
    p_toml.add_argument(
        "--out", default=None,
        help=(
            "write the rendered TOML to this path via cfg_write_toml (creating parent dirs) "
            "instead of only printing it"
        ),
    )

    p_render = sub.add_parser("render-command")
    p_render.add_argument("--reviewers-json", required=True,
                           help="path to resolve-reviewers' saved JSON array output")
    p_render.add_argument("--index", type=int, required=True,
                           help="0 for the primary/only reviewer, 1 for the secondary")
    p_render.add_argument("--prompt-file", required=True)

    p_tiers = sub.add_parser("resolve-timeout-tiers")
    p_tiers.add_argument("--cwd", required=True)
    p_tiers.add_argument("--reviewers-json", required=True,
                          help="path to resolve-reviewers' saved JSON array output")
    p_tiers.add_argument("--index", type=int, required=True)

    p_vendor = sub.add_parser("infer-vendor")
    p_vendor.add_argument("--model", required=True)

    p_build_cmd = sub.add_parser("build-command")
    p_build_cmd.add_argument("--cli", required=True)
    p_build_cmd.add_argument("--effort", default=None)
    p_build_cmd.add_argument("--service-tier", default=None)
    p_build_cmd.add_argument("--mode", default="plan",
                              help="cursor-agent only: 'plan' or 'ask' (both read-only)")

    p_build_model = sub.add_parser("build-model-id")
    p_build_model.add_argument("--cli", required=True)
    p_build_model.add_argument("--base-model", required=True)
    p_build_model.add_argument("--effort", default=None)
    p_build_model.add_argument("--fast", choices=["true", "false"], default=None)
    p_build_model.add_argument("--context", default=None)

    p_group = sub.add_parser("group-models")
    p_group.add_argument(
        "--runtimes-json", required=True,
        help="path to a detect-runtimes snapshot (as saved via --save/--if-stale)"
    )
    p_group.add_argument("--cli", required=True,
                          help="which CLI's models array to group, e.g. opencode, cursor-agent")

    p_alt = sub.add_parser("check-codegraph-alternative")
    p_alt.add_argument("--cli", required=True)
    p_alt.add_argument("--model", required=True)
    p_alt.add_argument("--runtimes-json", required=True)

    p_dispatch = sub.add_parser("dispatch-execute")
    p_dispatch.add_argument("--cli", required=True,
                             help="never 'native'/None here -- a native candidate executes "
                                  "in-process and never reaches this subcommand at all")
    p_dispatch.add_argument("--model", required=True)
    p_dispatch.add_argument("--effort", default=None,
                             help="structural param a builder may or may not use, same as "
                                  "build-command's own --effort -- codex's execute builder "
                                  "honors it, others silently ignore it")
    p_dispatch.add_argument("--service-tier", default=None)
    p_dispatch.add_argument("--target-dir", required=True)
    p_dispatch.add_argument("--prompt-file", required=True,
                             help="the phase task prompt -- kept as a file (like render-command's "
                                  "own --prompt-file) since a real prompt can be large; pass '-' "
                                  "to read the prompt from this process's own stdin instead -- "
                                  "the shape needed to drop this subcommand straight into a "
                                  "target framework's own stdin-piping hook (e.g. GSD's "
                                  "workflow.cross_ai_command, which always pipes its task prompt "
                                  "via stdin into whatever command that key names)")
    p_dispatch.add_argument("--heartbeat-interval", type=int, default=30)
    p_dispatch.add_argument("--timeout", type=int, required=True)
    p_dispatch.add_argument("--format-block-file", default=None,
                             help="e.g. GSD's own real SUMMARY.md shape -- omit for a dispatch "
                                  "mode whose caller already knows its own output convention")
    p_dispatch.add_argument("--tool-availability-json", default=None)
    p_dispatch.add_argument("--agents-tooling-path", default=None)
    p_dispatch.add_argument("--codegraph-registered", action="store_true")
    p_dispatch.add_argument(
        "--stdout-only", action="store_true",
        help="print ONLY the dispatched CLI's own stdout (result['stdout'], verbatim, no JSON "
             "envelope) and exit with its own returncode, instead of printing the full JSON "
             "result and always exiting 0/1 -- the exact contract a caller capturing this "
             "subcommand's stdout as a real artifact needs (e.g. GSD's own cross_ai_delegation "
             "step, which redirects workflow.cross_ai_command's raw stdout straight into a "
             "SUMMARY.md candidate file and inspects the real exit code, never a JSON wrapper)")

    p_dispatch_reviewer = sub.add_parser("dispatch-reviewer")
    p_dispatch_reviewer.add_argument(
        "--reviewers-json", required=True,
        help="path to resolve-reviewers' saved JSON array output -- this subcommand renders "
             "the entry's own command template itself (never take a pre-rendered --command "
             "string: the render must happen AFTER the tooling-guidance prefix is composed, "
             "or a CLI that inlines {prompt} into its command line never receives it)")
    p_dispatch_reviewer.add_argument(
        "--index", type=int, required=True,
        help="0 for the primary/only reviewer, 1 for the secondary")
    p_dispatch_reviewer.add_argument("--prompt-file", required=True,
                                      help="pass '-' to read the prompt from this process's "
                                           "own stdin")
    p_dispatch_reviewer.add_argument(
        "--timeout-tiers", required=True,
        help="comma-separated seconds, e.g. '600,1200,1800' -- escalation order")
    p_dispatch_reviewer.add_argument("--tool-availability-json", default=None)
    p_dispatch_reviewer.add_argument("--agents-tooling-path", default=None)
    p_dispatch_reviewer.add_argument(
        "--stdout-only", action="store_true",
        help="print ONLY the dispatched reviewer's own stdout and exit with its real "
             "returncode, same contract as dispatch-execute's own --stdout-only")

    p_check = sub.add_parser("check-reviewer")
    p_check.add_argument("--key", default="candidate")
    p_check.add_argument("--model", default="")
    p_check.add_argument("--vendor", default="")
    p_check.add_argument("--cli", default=None,
                          help="omit for a native (no-CLI) candidate — always available")
    p_check.add_argument("--command", dest="reviewer_command", default=None,
                          help="required when --cli is set; the command template to test")
    p_check.add_argument("--extra-json", default=None,
                          help="JSON object of extra {placeholder} fields the template needs")

    args = parser.parse_args(argv)

    if args.command == "cache-path":
        env = dict(os.environ)
        from ai_kit_spec.model_catalog import cache_catalog_path
        if args.kind == "runtimes":
            print(cache_runtimes_path(env))
        elif args.kind == "catalog":
            print(cache_catalog_path(env))
        else:
            print(cache_quota_path(env))
        return 0

    if args.command == "detect-tools":
        print(json.dumps(detect_tool_availability(which_fn=which_fn)))
        return 0

    if args.command == "detect-current-runtime":
        print(json.dumps({"native_runtime": detect_current_runtime(env_fn())}))
        return 0

    if args.command == "detect-runtimes":
        if args.if_stale and not cache_is_stale(args.if_stale, RUNTIMES_TTL_SECONDS):
            print(json.dumps({}))  # fresh — caller should treat this as "nothing to do"
            return 0
        snapshot = build_runtimes_snapshot(which_fn=which_fn, run_fn=run_fn)
        save_path = args.if_stale or args.save
        if save_path:
            cache_write_json(save_path, snapshot)
        print(json.dumps(snapshot))
        return 0

    if args.command == "fetch-model-catalog":
        # MEDIUM finding: cache_is_stale is already imported at module level (`from
        # ai_kit_spec.cache import cache_is_stale, cache_read_json, cache_write_json` --
        # confirmed live in the current cli.py) -- no local re-import needed here.
        # load_secret/fetch_models_dev/fetch_artificial_analysis are now imported at module
        # level too (Important finding, coordinator review: this subcommand's real-I/O calls
        # had no injection hook, so the "no API key" branch below was never actually exercised
        # by the test suite -- every existing test dodged it via `--if-stale`). They're threaded
        # through as `load_secret_fn`/`fetch_models_dev_fn`/`fetch_artificial_analysis_fn`
        # parameters on `main()` itself, same which_fn/run_fn/env_fn convention this repo
        # already uses everywhere else.
        from ai_kit_spec.model_catalog import CATALOG_TTL_SECONDS

        runtimes = cache_read_json(args.runtimes_json) or {}
        discovered = [
            {"cli": cli_name, "model_id": model_id}
            for cli_name, cli_data in runtimes.get("clis", {}).items()
            for model_id in cli_data.get("models", [])
        ]
        # Single-provider CLIs (codex, grok, claude/native, or any future CLI with no "models"
        # array -- confirmed live: detect_installed_clis' build_runtimes_snapshot only ever
        # populates "models" for opencode/cursor-agent) have no discoverable catalog to
        # enumerate. Their EXACT candidate source is whatever review-spec.toml already has
        # registered for that CLI -- re-running this subcommand re-enriches/re-ranks a model
        # the wizard already confirmed once. A model not yet registered for a single-provider
        # CLI stays on ai-kit-spec-config's existing manual per-model research path (SKILL.md
        # Step 2.2) until the user adds it as a reviewer -- the NEXT run of this subcommand
        # then picks it up here. This reconciliation ALWAYS runs -- see the --if-stale note
        # above; only the two external-source fetches below are gated by it.
        single_provider_clis = {name for name, data in runtimes.get("clis", {}).items()
                                 if data.get("installed") and "models" not in data}
        if single_provider_clis:
            cwd = args.cwd or os.getcwd()
            resolved = cfg_resolve(cwd, env_fn())
            for reviewer in resolved.get("reviewers", []):
                if reviewer.get("cli") in single_provider_clis and reviewer.get("model"):
                    discovered.append({"cli": reviewer["cli"], "model_id": reviewer["model"]})
        for raw in args.extra_candidate:
            cli_name, _, model_id = raw.partition(":")
            if cli_name and model_id:
                discovered.append({"cli": cli_name, "model_id": model_id})

        existing_catalog = cache_read_json(args.catalog_path) or {}
        # Important finding (coordinator review): `cache_is_stale(args.catalog_path, ...)` is
        # mtime-based, but `cache_write_json(args.catalog_path, catalog)` below runs on EVERY
        # invocation -- including a skip_fetch run where nothing external was ever queried.
        # That resets the catalog file's own mtime every run regardless of whether a real fetch
        # happened, so once `--if-stale` is invoked more often than every CATALOG_TTL_SECONDS,
        # the external-source data looks perpetually fresh and never actually re-fetches.
        # Freshness for THIS purpose (should we re-fetch from models.dev/Artificial Analysis?)
        # is tracked via a dedicated sidecar file instead, written ONLY when a fetch actually
        # ran this invocation AND at least one source came back genuinely ok -- never touched
        # on a skipped-fetch run, so its own mtime reflects the last REAL fetch, not the last
        # catalog write.
        fetch_meta_path = args.catalog_path + ".fetch-meta.json"
        skip_fetch = args.if_stale and not cache_is_stale(fetch_meta_path, CATALOG_TTL_SECONDS)
        if skip_fetch:
            models_dev_data, models_dev_ok = {}, False
            aa_models, aa_ok = [], False
        else:
            api_key = load_secret_fn(env_fn(), "ARTIFICIAL_ANALYSIS_API_KEY")
            models_dev_data, models_dev_ok = fetch_models_dev_fn()
            aa_models, aa_fetch_ok = fetch_artificial_analysis_fn(api_key)
            # CRITICAL finding: "no API key configured" (aa_fetch_ok=True, aa_models=[] --
            # Task 4's own "deliberately skipped, not a failure" contract) must NOT be treated
            # as "Artificial Analysis was queried and genuinely found no match" -- that would
            # silently wipe every already-cached AA score/pricing/attribution on every run
            # until a key is added. Both a real fetch failure AND no key at all take the same
            # "preserve whatever's cached, don't touch it" path inside build_model_catalog.
            aa_ok = aa_fetch_ok and bool(api_key)
            if models_dev_ok or aa_ok:
                cache_write_json(fetch_meta_path, {"last_fetched": time.time()})

        catalog, rejections, unmatched = build_model_catalog(
            discovered, models_dev_data, models_dev_ok, aa_models, aa_ok, existing_catalog)
        cache_write_json(args.catalog_path, catalog)
        print(json.dumps({"catalog_path": args.catalog_path, "entry_count": len(catalog),
                           "rejections": rejections, "unmatched": unmatched,
                           "discovered": discovered,
                           "models_dev_ok": models_dev_ok, "artificial_analysis_ok": aa_ok,
                           "fetch_skipped": skip_fetch}))
        return 0

    if args.command == "confirm-catalog-entry":
        payload = cache_read_json(args.entry_json) or {}
        # Important finding (coordinator review): every other failure mode across these three
        # subcommands returns structured JSON + exit 1 -- a malformed/empty --entry-json used to
        # raise a bare KeyError traceback here instead, via unguarded payload["model_id"]/
        # payload["entry"] access. Validate the payload's shape before ever touching those keys.
        if (not isinstance(payload, dict) or not isinstance(payload.get("model_id"), str)
                or not isinstance(payload.get("entry"), dict)):
            print(json.dumps({
                "confirmed": False,
                "reason": "--entry-json must be an object with a string 'model_id' and an "
                          "object 'entry'"}))
            return 1
        catalog = cache_read_json(args.catalog_path) or {}
        catalog, reason = merge_catalog_entry(catalog, payload["model_id"], payload["entry"])
        if reason:
            print(json.dumps({"confirmed": False, "reason": reason}))
            return 1
        cache_write_json(args.catalog_path, catalog)
        print(json.dumps({"confirmed": True, "model_id": payload["model_id"]}))
        return 0

    if args.command == "apply-heuristic-correction":
        from ai_kit_spec.model_catalog import apply_heuristic_corrections

        # HIGH finding: a raw json.dump(..., open(path, "w")) bypasses this repo's atomic,
        # validated cache-write path -- a crash mid-write can corrupt the catalog file, and
        # nothing here would ever re-validate the result. cache_write_json (already imported,
        # used by every other catalog-writing subcommand) is the ONE write path for
        # model-catalog.json; this subcommand is the ONLY way a heuristic correction is
        # ever persisted, matching confirm-catalog-entry's contract for unmatched candidates.
        # CRITICAL finding: apply_heuristic_corrections now returns (catalog, reason) -- a
        # correction that would produce a schema-invalid entry is rejected here exactly like
        # confirm-catalog-entry rejects an invalid new entry, never silently written.
        corrections = cache_read_json(args.corrections_json) or {}
        catalog = cache_read_json(args.catalog_path) or {}
        catalog, reason = apply_heuristic_corrections(catalog, args.model_id, corrections)
        if reason:
            print(json.dumps({"applied": False, "reason": reason}))
            return 1
        cache_write_json(args.catalog_path, catalog)
        print(json.dumps({"applied": True, "model_id": args.model_id}))
        return 0

    if args.command == "probe-quota":
        config = cfg_resolve(args.cwd, dict(os.environ))
        ladder = config.get("policy", {}).get("ladder", [])
        existing = cache_read_json(args.quota_path) or {}
        updated = refresh_quota_cache(config, ladder, existing, QUOTA_TTL_SECONDS, run_fn=run_fn)
        cache_write_json(args.quota_path, updated)
        print(json.dumps(updated))
        return 0

    if args.command == "resolve-reviewers":
        config = cfg_resolve(args.cwd, dict(os.environ))
        quota = cache_read_json(args.quota_path) or {}
        reviewers = resolve_reviewers(config, quota, args.source_vendor, args.cross_ai)
        print(json.dumps([r._asdict() for r in reviewers]))
        return 0

    if args.command == "merge-reports":
        reports = []
        unreadable = []
        for item in args.reports:
            key, _, path = item.partition("=")
            try:
                with open(path, encoding="utf-8") as f:
                    text = f.read()
            except OSError:
                unreadable.append(key)
                continue
            if not report_has_status(text):
                unreadable.append(key)
                continue
            reports.append((key, text))
        if unreadable:
            # Deliberately prints NO "### Status:" line — review-spec/SKILL.md's
            # existing Step 2 already treats "No Status line" as a failure to
            # surface (its own long-standing rule), so a failed/unreadable
            # external reviewer can never silently merge into a false
            # "### Status: Approved". No new orchestrator special-case needed.
            print(f"merge-reports: reviewer(s) {', '.join(unreadable)} produced "
                  f"no readable report with a Status line — cannot merge.")
            return 0
        merged = merge_findings(reports)
        any_source_issues = any(report_declares_issues(text) for _, text in reports)
        print(render_merged_report(merged, args.doc_paths, any_source_issues))
        return 0

    if args.command == "render-toml":
        with open(args.json_config, encoding="utf-8") as f:
            config = json.load(f)
        rendered = cfg_render_toml(config)
        if args.out:
            cfg_write_toml(args.out, config)
        print(rendered)
        return 0

    if args.command == "render-command":
        with open(args.reviewers_json, encoding="utf-8") as f:
            reviewers = json.load(f)
        r = reviewers[args.index]
        resolved = ResolvedReviewer(key=r["key"], model=r["model"], vendor=r["vendor"],
                                     cli=r["cli"], command=r["command"], extra=r["extra"])
        with open(args.prompt_file, encoding="utf-8") as f:
            prompt = f.read()
        try:
            print(render_reviewer_command(resolved, prompt))
        except ValueError as exc:
            # Deliberately no "### Status:" substring — same fail-closed
            # convention as merge-reports: review-spec/SKILL.md's existing
            # "No Status line -> Surface failure" rule catches this
            # without any new special-casing at the dispatch step.
            print(f"render-command: {exc}", file=sys.stderr)
            return 1
        return 0

    if args.command == "resolve-timeout-tiers":
        with open(args.reviewers_json, encoding="utf-8") as f:
            reviewers = json.load(f)
        r = reviewers[args.index]
        config = cfg_resolve(args.cwd, dict(os.environ))
        tiers = resolve_timeout_tiers(r, config.get("policy", {}))
        print(",".join(str(t) for t in tiers))
        return 0

    if args.command == "infer-vendor":
        print(json.dumps({"vendor": infer_vendor_from_model(args.model)}))
        return 0

    if args.command == "build-command":
        params = {}
        if args.effort:
            params["effort"] = args.effort
        if args.service_tier:
            params["service_tier"] = args.service_tier
        if args.cli == "cursor-agent":
            params["mode"] = args.mode
        try:
            print(build_reviewer_command(args.cli, **params))
        except ValueError as exc:
            print(f"build-command: {exc}", file=sys.stderr)
            return 1
        return 0

    if args.command == "build-model-id":
        fast = {"true": True, "false": False, None: None}[args.fast]
        print(build_reviewer_model_id(args.cli, args.base_model, effort=args.effort,
                                       fast=fast, context=args.context))
        return 0

    if args.command == "group-models":
        snapshot = cache_read_json(args.runtimes_json) or {}
        models = snapshot.get("clis", {}).get(args.cli, {}).get("models", [])
        print(json.dumps(group_models_by_family(models)))
        return 0

    if args.command == "check-codegraph-alternative":
        snapshot = cache_read_json(args.runtimes_json) or {}
        alternative = find_codegraph_alternative(args.cli, args.model, snapshot)
        print(json.dumps({"alternative_cli": alternative}))
        return 0

    if args.command == "dispatch-execute":
        if args.prompt_file == "-":
            prompt = sys.stdin.read()
        else:
            with open(args.prompt_file, encoding="utf-8") as f:
                prompt = f.read()
        format_block = None
        if args.format_block_file:
            with open(args.format_block_file, encoding="utf-8") as f:
                format_block = f.read()
        tool_availability = (json.loads(args.tool_availability_json)
                              if args.tool_availability_json else {})
        candidate = {"cli": args.cli, "model": args.model, "effort": args.effort,
                     "service_tier": args.service_tier}
        try:
            result = dispatch_execute_fn(
                candidate, prompt, args.target_dir, args.heartbeat_interval, args.timeout,
                format_block=format_block, tool_availability=tool_availability,
                agents_tooling_path=args.agents_tooling_path,
                codegraph_registered=args.codegraph_registered)
        except ValueError as exc:
            print(f"dispatch-execute: {exc}", file=sys.stderr)
            return 1
        if args.stdout_only:
            sys.stdout.write(result["stdout"])
            # Propagate the dispatched CLI's own real returncode (not a collapsed 0/1) -- GSD's
            # own cross_ai_delegation step only ever checks nonzero-vs-zero, but the real code is
            # more diagnosable than a flattened one when things go wrong. A timeout kill can leave
            # returncode negative (signal) or None depending on the platform; 1 covers both, since
            # any nonzero reads as failure either way.
            return result["returncode"] if result["returncode"] is not None else 1
        print(json.dumps(result))
        return 0

    if args.command == "dispatch-reviewer":
        with open(args.reviewers_json, encoding="utf-8") as f:
            reviewers = json.load(f)
        if not -len(reviewers) <= args.index < len(reviewers):
            print(f"dispatch-reviewer: no reviewer at index {args.index} "
                  f"({len(reviewers)} entries)", file=sys.stderr)
            return 1
        if args.prompt_file == "-":
            prompt = sys.stdin.read()
        else:
            with open(args.prompt_file, encoding="utf-8") as f:
                prompt = f.read()
        timeout_tiers = [int(t) for t in args.timeout_tiers.split(",") if t.strip()]
        tool_availability = (json.loads(args.tool_availability_json)
                              if args.tool_availability_json else {})
        try:
            result = dispatch_reviewer_fn(
                reviewers[args.index], prompt, timeout_tiers, tool_availability,
                args.agents_tooling_path)
        except ValueError as exc:
            # Deliberately no "### Status:" substring -- same fail-closed convention
            # render-command uses: a malformed reviewer entry (bad/missing command template,
            # empty timeout tiers) leaves this reviewer's report file absent/statusless, which
            # ai-kit-spec-review/SKILL.md's existing "No Status line -> Surface failure" rule
            # already handles with no new special-casing.
            print(f"dispatch-reviewer: {exc}", file=sys.stderr)
            return 1
        if args.stdout_only:
            sys.stdout.write(result["stdout"])
            return result["returncode"] if result["returncode"] is not None else 1
        print(json.dumps(result))
        return 0

    if args.command == "check-reviewer":
        extra = json.loads(args.extra_json) if args.extra_json else {}
        resolved = ResolvedReviewer(key=args.key, model=args.model, vendor=args.vendor,
                                     cli=args.cli, command=args.reviewer_command, extra=extra)
        result = probe_reviewer_quota(resolved, run_fn=run_fn)
        print(json.dumps(result))
        return 0

    return 1
