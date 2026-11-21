"""36 R6, D-07: the candidate pool of propose-lanes: one row per (catalog key, runtime),
the drop filters and the purpose groups. Pure; never reads the runtime table."""

from typing import NamedTuple

from ai_kit_spec import catalog_bands, catalog_report
from ai_kit_spec.catalog_facts import ROUTER_SOURCE
from ai_kit_spec.catalog_labels import fact_problem

POOL_CLASSES = {"review": ("flagship",), "execute": ("coding", "fast")}
ALIAS_LABEL = "assumed: " + ROUTER_SOURCE
DROP_REASONS = ("rejected", "listed disabled by host", "stale", "stale provider", "unmatched")


class Row(NamedTuple):
    key: str
    runtime: str
    model_id: str
    entry: dict
    row: dict
    tier: str
    klass: str
    cost_band: str
    strengths: tuple
    efforts: tuple
    usability: str
    provider_prefix: str | None


class PoolSplit(NamedTuple):
    pool: list
    unknown: list
    wider: list
    aliases: list


def snapshot_cli(snapshot, rid: str) -> dict:
    clis = snapshot.get("clis") if isinstance(snapshot, dict) else None
    row = clis.get(rid) if isinstance(clis, dict) else None
    return row if isinstance(row, dict) else {}


def checked_fact(entry, name: str) -> dict | None:
    facts = entry.get("facts") if isinstance(entry, dict) else None
    item = facts.get(name) if isinstance(facts, dict) else None
    if not isinstance(item, dict):
        return None
    if not all(isinstance(item.get(key), str) for key in ("label", "source", "fetched_at")):
        return None
    return item if fact_problem(item) is None else None


def fact_value(entry, name: str, allowed: tuple) -> str:
    item = checked_fact(entry, name)
    value = item.get("value") if item else None
    return value if isinstance(value, str) and value in allowed else "unknown"


def _strengths(entry) -> tuple:
    item = checked_fact(entry, "strengths")
    value = item.get("value") if item else None
    if not isinstance(value, list):
        return ()
    return tuple(x for x in value if isinstance(x, str) and x in catalog_bands.STRENGTH_CATEGORIES)


def _make_row(key, entry, rid, rt_row, snapshot) -> Row:
    model_id = rt_row["model_id"]
    efforts = rt_row.get("efforts")
    return Row(
        key, rid, model_id, entry, rt_row,
        fact_value(entry, "tier", catalog_bands.TIERS),
        fact_value(entry, "class", catalog_bands.CLASSES),
        fact_value(entry, "cost_band", catalog_bands.COST_BANDS),
        _strengths(entry),
        tuple(x for x in efforts if isinstance(x, str)) if isinstance(efforts, list) else (),
        catalog_report.usability_state(rt_row, snapshot_cli(snapshot, rid), model_id),
        model_id.split("/", 1)[0] if "/" in model_id else None,
    )


def build_rows(entries: dict, snapshot, runtimes: tuple | None = None) -> list:
    rows = []
    for key, entry in entries.items():
        if key == "_meta" or not isinstance(entry, dict):
            continue
        runtime_rows = entry.get("runtimes")
        if not isinstance(runtime_rows, dict):
            continue
        for rid, rt_row in runtime_rows.items():
            if not isinstance(rt_row, dict) or (runtimes is not None and rid not in runtimes):
                continue
            model_id = rt_row.get("model_id")
            if isinstance(model_id, str) and model_id:
                rows.append(_make_row(key, entry, rid, rt_row, snapshot))
    return sorted(rows, key=lambda row: (row.key, row.runtime))


def is_unknown(row: Row) -> bool:
    return row.klass == "unknown" or row.tier == "unknown"


def drop_reason(row: Row, cli_row: dict, stale_prefixes: set, fresh: bool) -> str | None:
    if row.usability.startswith("rejected"):
        return DROP_REASONS[0]
    if row.usability == DROP_REASONS[1]:
        return DROP_REASONS[1]
    stale = catalog_report.stale_state(row.model_id, cli_row, row.row.get("last_seen"), fresh)
    if stale.startswith("stale"):
        return DROP_REASONS[2]
    if row.provider_prefix is not None and row.provider_prefix in stale_prefixes:
        return DROP_REASONS[3]
    match = row.row.get("match")
    if isinstance(match, dict) and match.get("value") == "unmatched":
        return DROP_REASONS[4]
    return None


def _group(row: Row, purpose: str) -> str:
    if row.entry.get("provider") == "router-env":
        return "alias"
    if row.klass == "unknown":
        return "unknown"
    if row.klass in POOL_CLASSES[purpose]:
        return "unknown" if is_unknown(row) else "pool"
    if row.klass == "router":
        return "skip"
    return "wider"


def _alias_note(row: Row, purpose: str) -> str | None:
    declared = row.entry.get("name_declared_purpose")
    if declared == purpose:
        return f"purpose from the name: {purpose}"
    if declared not in ("review", "execute"):
        return "purpose unknown"
    return None


def split_pools(rows: list, purpose: str, snapshot, entries: dict, fresh: bool) -> PoolSplit:
    groups: dict = {"pool": [], "unknown": [], "wider": [], "aliases": []}
    cached: dict = {}
    for row in rows:
        cli_row = snapshot_cli(snapshot, row.runtime)
        if row.runtime not in cached:
            cached[row.runtime] = (
                catalog_report.stale_providers(row.runtime, entries, cli_row, fresh)
                if isinstance(cli_row.get("models"), list) else set()
            )
        if drop_reason(row, cli_row, cached[row.runtime], fresh):
            continue
        group = _group(row, purpose)
        if group == "alias":
            note = _alias_note(row, purpose)
            if note is not None:
                groups["aliases"].append((row, note))
        elif group != "skip":
            groups[group].append(row)
    return PoolSplit(groups["pool"], groups["unknown"], groups["wider"], groups["aliases"])
