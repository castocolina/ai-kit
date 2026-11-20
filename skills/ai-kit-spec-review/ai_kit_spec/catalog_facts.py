"""35 D-04, D-08, D-12, D-15, Amend-2: labeled facts per catalog entry and per runtime row,
applied after the build. catalog_build only calls this module (D-01).
"""

from collections.abc import Callable
from typing import NamedTuple

from ai_kit_spec import catalog_bands, model_names
from ai_kit_spec.catalog_labels import fact
from ai_kit_spec.model_catalog import canonical_key, merge_catalog_entry
from ai_kit_spec.model_heuristics import infer_purpose_from_name
from ai_kit_spec.model_names import BlankNameError, split_effort

ROUTER_PREFIX = "router-env/"
ROUTER_SOURCE = "router-env alias naming"
_HEURISTIC_FIELDS = ("is_router", "batch_mode", "fallback_quota")
_NO_TIMES = {}
_NO_MATCHES = {}


class FactsInputs(NamedTuple):
    snapshot: dict
    settings: object = None
    now: str = ""
    name_judge: Callable | None = None
    class_judge: Callable | None = None
    source_at: dict = _NO_TIMES
    matches: dict = _NO_MATCHES


def _at(inputs, key: str) -> str:
    return inputs.source_at.get(key) or inputs.now


def router_alias_key(runtime: str, model_id: str) -> str:
    try:
        base = split_effort(runtime, model_id).base
    except BlankNameError:
        base = model_id
    return canonical_key("router-env", base[len(ROUTER_PREFIX) :])


def router_alias_entry(cli_name: str, model_id: str, existing: dict | None, today: str) -> dict:
    existing = existing or {}
    defaults = {"is_router": True, "fallback_quota": True, "batch_mode": False}
    confirmed = existing.get("heuristic_confirmed", [])
    heuristics = {
        field: existing[field] if field in confirmed and field in existing else value
        for field, value in defaults.items()
    }
    entry = {
        "provider": "router-env",
        "runtimes": {cli_name: {"model_id": model_id}},
        **heuristics,
        "source": existing.get("source", {}),
        "confidence": existing.get("confidence", "low"),
        "last_verified": existing.get("last_verified", today),
        "facts": dict(existing.get("facts", {})),
    }
    purpose = infer_purpose_from_name(model_id)
    if purpose:
        entry["name_declared_purpose"] = purpose
    return entry


def md_facts(key: str, sources, now: str, cost_cuts) -> tuple:
    if not sources.models_dev_ok or "/" not in key:
        return {}, None
    provider, bare = key.split("/", 1)
    row = sources.models_dev_data.get(provider, {}).get("models", {}).get(bare)
    if not isinstance(row, dict):
        return {}, None
    facts = {}
    modalities = row.get("modalities")
    if isinstance(modalities, dict):
        facts["modalities"] = fact(modalities, "measured", "models.dev", now)
    if isinstance(row.get("reasoning"), bool):
        facts["reasoning"] = fact(row["reasoning"], "measured", "models.dev", now)
    if isinstance(row.get("status"), str):
        facts["status"] = fact(row["status"], "measured", "models.dev", now)
    price, free = catalog_bands.price_per_million(row.get("cost"))
    facts["cost_band"] = fact(
        catalog_bands.cost_band(price, free, cost_cuts),
        "judged",
        "models.dev",
        now,
        confidence="rule",
    )
    identity = row.get("canonical_model_id")
    return facts, identity if isinstance(identity, str) else None


def _string_levels(value) -> list:
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []


def _last_seen(cli: dict, model_id: str) -> str | None:
    listed_from = cli.get("listed_from") or {}
    at = listed_from.get("at") if isinstance(listed_from, dict) else None
    if (
        cli.get("listing") == "ok"
        and isinstance(at, str)
        and isinstance(cli.get("models"), list)
        and model_id in cli["models"]
    ):
        return at
    return None


class _RuntimeInput(NamedTuple):
    rid: str
    model_id: str
    row: dict
    cli: dict
    inputs: FactsInputs
    known_ids: frozenset


def _runtime_row_update(item: _RuntimeInput) -> dict | None:
    try:
        parts = split_effort(item.rid, item.model_id, item.known_ids)
    except BlankNameError:
        return None
    cli = item.cli
    modes_map = cli.get("reasoning_modes", {})
    modes = modes_map.get(item.model_id, []) if isinstance(modes_map, dict) else []
    records = cli.get("model_records", {})
    record = records.get(item.model_id, {}) if isinstance(records, dict) else {}
    levels = _string_levels(modes) + _string_levels(
        record.get("efforts") if isinstance(record, dict) else None
    )
    update: dict = {"model_id": item.model_id}
    efforts = sorted(set(parts.efforts) | set(levels))
    if efforts:
        update["efforts"] = efforts
    last_seen = _last_seen(cli, item.model_id)
    if last_seen is not None:
        update["last_seen"] = last_seen
    state, confidence = item.inputs.matches.get((item.rid, item.model_id), (None, None))
    if state == "judged":
        update["match"] = fact("judged", "judged", "jev", item.inputs.now, confidence=confidence)
    elif state == "unmatched":
        update["match"] = fact(
            "unmatched", "judged", "ai-kit name rule", item.inputs.now, confidence="rule"
        )
    return update


def runtime_updates(entry: dict, inputs: FactsInputs, known_ids: frozenset) -> dict:
    updates = {}
    for rid, row in entry.get("runtimes", {}).items():
        model_id = row.get("model_id") if isinstance(row, dict) else None
        if not isinstance(model_id, str):
            continue
        snapshot = inputs.snapshot.get("clis", {})
        cli = snapshot.get(rid, {}) if isinstance(snapshot, dict) else {}
        cli = cli if isinstance(cli, dict) else {}
        update = _runtime_row_update(_RuntimeInput(rid, model_id, row, cli, inputs, known_ids))
        if update is not None:
            updates[rid] = update
    return updates


class _ApplyInput(NamedTuple):
    key: str
    entry: dict
    sources: object
    inputs: FactsInputs
    cuts: object
    known: frozenset


def _apply_entry(catalog: dict, item: _ApplyInput):
    key, entry, sources, inputs, cuts, known = item
    if entry.get("provider") == "router-env":
        facts = {
            **entry.get("facts", {}),
            "class": fact("router", "assumed", ROUTER_SOURCE, inputs.now),
        }
        incoming = {**entry, "facts": facts, "runtimes": runtime_updates(entry, inputs, known)}
    else:
        new_facts, identity = md_facts(key, sources, _at(inputs, "models_dev"), cuts)
        facts = {**entry.get("facts", {}), **new_facts}
        settings = inputs.settings
        configured_sources = getattr(settings, "sources", ())
        if settings is not None and "models.dev" not in configured_sources:
            facts = {
                name: value for name, value in facts.items() if value.get("source") != "models.dev"
            }
        incoming = {**entry, "facts": facts, "runtimes": runtime_updates(entry, inputs, known)}
        if identity is not None:
            incoming["identity"] = identity
    return merge_catalog_entry(catalog, key, incoming)


def apply_facts(catalog: dict, sources, inputs: FactsInputs) -> tuple:
    cuts = catalog_bands.cost_cuts(sources.models_dev_data) if sources.models_dev_ok else None
    known = (
        model_names.known_ids_from_models_dev(sources.models_dev_data)
        if sources.models_dev_ok
        else frozenset()
    )
    updated = dict(catalog)
    rejections = []
    for key, entry in catalog.items():
        item = _ApplyInput(key, entry, sources, inputs, cuts, known)
        updated, reason = _apply_entry(updated, item)
        if reason:
            rejections.append(reason)
    return updated, rejections


def _pool_for(sources) -> dict:
    appearances = {}
    for provider, payload in sources.models_dev_data.items():
        rows = payload.get("models") if isinstance(payload, dict) else None
        if not isinstance(rows, dict):
            continue
        for bare, row in rows.items():
            if isinstance(bare, str) and isinstance(row, dict):
                appearances.setdefault(bare, []).append((provider, row))
    pool = {}
    for bare, rows in appearances.items():
        identities = {row.get("canonical_model_id") for _, row in rows}
        if len(rows) == 1:
            pool[bare] = canonical_key(rows[0][0], bare)
        elif len(identities) == 1 and isinstance(next(iter(identities)), str):
            provider = next(
                (p for p, row in sorted(rows) if isinstance(row.get("canonical_model_id"), str)),
                None,
            )
            if provider is not None:
                pool[bare] = canonical_key(provider, bare)
    return pool


class _ResolutionInput(NamedTuple):
    candidate: dict
    base: str
    pool: dict
    known: frozenset


def _candidate_base(candidate: dict, known: frozenset) -> str | None:
    try:
        return split_effort(candidate["runtime"], candidate["model_id"], known).base
    except BlankNameError:
        return None


def _resolve_pending(pending: list, pool: dict, inputs: FactsInputs):
    pending_names = [base for _, base in pending]
    resolutions = model_names.resolve_many(pending_names, pool, inputs.name_judge)
    output, matches = [], {}
    for candidate, base in pending:
        result = resolutions[base]
        pair = (candidate["runtime"], candidate["model_id"])
        if result.state in ("matched", "judged"):
            output.append({**candidate, "match_name": result.key})
            if result.state == "judged":
                matches[pair] = (result.state, result.confidence)
        else:
            output.append({**candidate, "unresolved": True})
            matches[pair] = ("unmatched", None)
    return output, matches


def resolve_candidates(candidates: list, sources, inputs: FactsInputs) -> tuple:
    if not sources.models_dev_ok:
        return list(candidates), {}
    known = model_names.known_ids_from_models_dev(sources.models_dev_data)
    pool = _pool_for(sources)
    output, pending = [], []
    for candidate in candidates:
        model_id = candidate["model_id"]
        if model_id.startswith(ROUTER_PREFIX):
            output.append(candidate)
            continue
        base = _candidate_base(candidate, known)
        if base is None:
            output.append({**candidate, "unresolved": True})
            continue
        bare = base.rsplit("/", 1)[-1]
        if bare in pool:
            output.append({**candidate, "match_name": pool[bare]})
        else:
            pending.append((candidate, base))
    resolved, matches = _resolve_pending(pending, pool, inputs)
    return output + resolved, matches
