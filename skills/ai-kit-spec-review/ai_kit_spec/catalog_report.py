"""35 R1, R2, R6, R8 / D-12: catalog report rows per (runtime, model): listing state and
source, usability, stale only on proof of a successful listing, stale providers, source-marked
status, context. Pure; sorted by runtime then id."""

from typing import NamedTuple

from ai_kit_spec.catalog_labels import show

REPORT_FACTS = ("tier", "class", "cost_band", "modalities", "reasoning", "strengths")


class ReportRow(NamedTuple):
    runtime: str
    model_id: str
    key: str
    listing: str
    listed_from: str
    usability: str
    stale: str
    marked: str
    context: str
    efforts: str
    facts: str
    match: str


def facts_text(entry: dict) -> str:
    facts = entry.get("facts", {})
    text = "; ".join(
        f"{name}: {show(facts[name])}" for name in REPORT_FACTS if name in facts
    )
    return text or "none"


def listing_state(cli_row: dict) -> str:
    if not isinstance(cli_row, dict) or cli_row.get("installed") is False:
        return "not installed"
    listing = cli_row.get("listing")
    if listing == "ok":
        return "listed, empty" if cli_row.get("models") == [] else "listed"
    if listing == "failed":
        return "listing failed: " + str(cli_row.get("listing_error") or "unknown error")
    if listing == "none":
        return "installed, no listing"
    if listing is None and "listing" not in cli_row:
        return "not checked"
    return "not checked"


def _source_records(records: list) -> str:
    parts = []
    for record in records:
        if not isinstance(record, dict):
            continue
        label = str(record.get("label") or "unknown source")
        url = record.get("url")
        date = record.get("date")
        if url:
            suffix = f"{url}, {date}" if date else str(url)
            label += f" ({suffix})"
        parts.append(label)
    return "; ".join(parts) or "none"


def listed_from_text(cli_row: dict, rt_row: dict) -> str:
    sources = rt_row.get("listed_from") if isinstance(rt_row, dict) else None
    if isinstance(sources, list):
        return _source_records(sources)
    source = cli_row.get("listed_from") if isinstance(cli_row, dict) else None
    if isinstance(source, dict):
        command = source.get("command") or "command unknown"
        version = source.get("version") or "version unknown"
        at = source.get("at") or "date unknown"
        return f"{command} ({version}) at {at}"
    if isinstance(rt_row, dict):
        if rt_row.get("models_source"):
            return str(rt_row["models_source"])
        if rt_row.get("note"):
            return str(rt_row["note"])
    return "none"


def stale_state(model_id: str, cli_row: dict, last_seen: str | None, fresh: bool) -> str:
    if not isinstance(cli_row, dict) or cli_row.get("listing") != "ok":
        return "not checked"
    models = cli_row.get("models")
    if not isinstance(models, list):
        return "not checked"
    if model_id in models:
        return ""
    source = cli_row.get("listed_from")
    at = source.get("at") if isinstance(source, dict) else None
    if not fresh:
        return f"not checked (cached {at or 'date unknown'})"
    return f"stale (not in the listing of {at or 'date unknown'}; last seen {last_seen or 'never'})"


def stale_providers(rid: str, entries: dict, cli_row: dict, fresh: bool) -> set:
    if not fresh or listing_state(cli_row) not in ("listed", "listed, empty"):
        return set()
    catalogued = set()
    for entry in entries.values():
        runtimes = entry.get("runtimes", {}) if isinstance(entry, dict) else {}
        row = runtimes.get(rid) if isinstance(runtimes, dict) else None
        model_id = row.get("model_id") if isinstance(row, dict) else None
        if isinstance(model_id, str) and "/" in model_id:
            provider = model_id.split("/", 1)[0]
            if provider != "router-env":
                catalogued.add(provider)
    listed = {
        model.split("/", 1)[0] for model in cli_row.get("models", [])
        if isinstance(model, str) and "/" in model and model.split("/", 1)[0] != "router-env"
    }
    return catalogued - listed


def marked_state(entry: dict) -> str:
    status = entry.get("facts", {}).get("status")
    if isinstance(status, dict) and status.get("value") is not None:
        return f"marked by source: {status['value']} (models.dev)"
    return ""


def usability_state(rt_row: dict, cli_row: dict, model_id: str) -> str:
    records = cli_row.get("model_records", {}) if isinstance(cli_row, dict) else {}
    model_record = records.get(model_id) if isinstance(records, dict) else None
    if isinstance(model_record, dict) and model_record.get("enabled") is False:
        return "listed disabled by host"
    usability = rt_row.get("usability") if isinstance(rt_row, dict) else None
    if not isinstance(usability, dict):
        return "unverified"
    state = usability.get("state")
    if state == "verified":
        return f"verified {usability.get('at', '')} via {usability.get('via', '')}".strip()
    if state == "rejected":
        at = usability.get("at", "")
        error = usability.get("error") or "unknown error"
        return f"rejected {at}: {error}".strip()
    return "unverified"


def context_line(rt_row: dict) -> str:
    return show(rt_row.get("context")) if isinstance(rt_row, dict) else "unknown"


class _RowInputs(NamedTuple):
    key: str
    entry: dict
    rid: str
    runtime_row: dict
    cli_row: dict
    stale_prefixes: set
    fresh: bool


def _runtime_row(inputs: _RowInputs) -> ReportRow:
    key, entry, rid, rt_row, cli_row, stale_prefixes, fresh = inputs
    model_id = rt_row.get("model_id", "")
    stale = stale_state(model_id, cli_row, rt_row.get("last_seen"), fresh)
    provider = model_id.split("/", 1)[0] if isinstance(model_id, str) and "/" in model_id else None
    if provider in stale_prefixes:
        stale = f"stale-provider (no listed model from {provider})"
    match_fact = rt_row.get("match")
    return ReportRow(
        rid, model_id, key, listing_state(cli_row), listed_from_text(cli_row, rt_row),
        usability_state(rt_row, cli_row, model_id), stale, marked_state(entry),
        context_line(rt_row), ", ".join(rt_row.get("efforts", [])), facts_text(entry),
        show(match_fact) if match_fact is not None else "",
    )


def _extra_row(rid: str, model_id: str, cli_row: dict, *, optional=False) -> ReportRow:
    records = cli_row
    if optional:
        records = {"listed_from": {}}
    listed_from = listed_from_text(records, cli_row)
    if optional:
        listed_from = _source_records(cli_row.get("sources", []))
    return ReportRow(
        rid, model_id, "", "not listed" if optional else listing_state(cli_row), listed_from,
        "", "unmatched", "", "", "", "none", "",
    )


def _catalog_rows(catalog: dict, clis: dict, fresh: bool) -> list:
    rows = []
    for key, entry in catalog.items():
        if key == "_meta" or not isinstance(entry, dict):
            continue
        runtimes = entry.get("runtimes", {})
        if not isinstance(runtimes, dict):
            continue
        for rid, rt_row in runtimes.items():
            if not isinstance(rt_row, dict):
                continue
            cli_row = clis.get(rid, {})
            prefixes = stale_providers(rid, catalog, cli_row, fresh)
            rows.append(_runtime_row(_RowInputs(
                key, entry, rid, rt_row, cli_row, prefixes, fresh)))
    return rows


def _optional_rows(optional: dict | None, rows: list) -> list:
    extra = []
    for rid, candidates in (optional or {}).items():
        present = {row.model_id for row in rows if row.runtime == rid}
        for candidate in candidates if isinstance(candidates, list) else []:
            if not isinstance(candidate, dict) or candidate.get("name") in present:
                continue
            extra.append(_extra_row(rid, candidate.get("name", ""), candidate, optional=True))
    return extra


def _listed_rows(clis: dict, rows: list) -> list:
    extra = []
    for rid, cli_row in clis.items():
        models = cli_row.get("models") if isinstance(cli_row, dict) else None
        if cli_row.get("listing") == "ok" and isinstance(models, list):
            present = {row.model_id for row in rows if row.runtime == rid}
            for model_id in models:
                if isinstance(model_id, str) and model_id not in present:
                    extra.append(_extra_row(rid, model_id, cli_row))
        if cli_row.get("installed") and not any(row.runtime == rid for row in rows):
            extra.append(ReportRow(
                rid, "-", "", listing_state(cli_row), listed_from_text(cli_row, {}),
                "", "", "", "", "", "", "",
            ))
    return extra


def report_rows(catalog: dict, snapshot: dict, optional: dict | None = None,
                fresh: bool = False) -> list:
    clis = snapshot.get("clis", {}) if isinstance(snapshot, dict) else {}
    if not isinstance(clis, dict):
        clis = {}
    rows = _catalog_rows(catalog, clis, fresh)
    rows.extend(_optional_rows(optional, rows))
    rows.extend(_listed_rows(clis, rows))
    return sorted(rows, key=lambda row: (row.runtime, row.model_id))


def render_lines(rows: list) -> list:
    lines = []
    for row in rows:
        line = f"{row.runtime}  {row.model_id}  [{row.listing}]  usability: {row.usability}"
        if row.stale:
            line += f"; {row.stale}"
        if row.marked:
            line += f"; {row.marked}"
        if row.match:
            line += f"; match: {row.match}"
        line += (f"; facts: {row.facts}; context: {row.context}; efforts: "
                 f"{row.efforts or 'none'}; listed from: {row.listed_from}")
        lines.append(line)
    return lines
