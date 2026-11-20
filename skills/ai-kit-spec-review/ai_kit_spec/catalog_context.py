"""35 D-09 / R6: per-runtime context, by user override, host, models.dev, else unknown.

Exact positive integers only; never guessed from a name.
"""

from ai_kit_spec.catalog_labels import fact


def valid_tokens(value) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else None


def _runtime_values(rid: str, model_id: str, cli: dict, at: str | None) -> list:
    if rid in ("pi", "codex"):
        values = cli.get("context_window", {})
        source = "pi listing" if rid == "pi" else "codex debug models"
        return [(values.get(model_id), source, at)] if isinstance(values, dict) else []
    if rid == "opencode":
        records = cli.get("model_records", {})
        record = records.get(model_id) if isinstance(records, dict) else None
        limit = record.get("limit") if isinstance(record, dict) else None
        if isinstance(limit, dict):
            return [
                (limit.get("input"), "opencode /api/model limit.input", at),
                (limit.get("context"), "opencode /api/model limit.context", at),
            ]
    return []


def host_figures(rid: str, model_id: str, snapshot: dict) -> list:
    """Return host-declared candidate figures and their listing provenance."""
    clis = snapshot.get("clis", {}) if isinstance(snapshot, dict) else {}
    cli = clis.get(rid, {}) if isinstance(clis, dict) else {}
    if not isinstance(cli, dict):
        return []
    listed = cli.get("listed_from")
    at = listed.get("at") if isinstance(listed, dict) else None
    at = at if isinstance(at, str) else None
    return _runtime_values(rid, model_id, cli, at)


def models_dev_figure(key: str, model_id: str, sources) -> object:
    """Use this entry's provider row, or a unanimous bare-id row across providers."""
    if not getattr(sources, "models_dev_ok", False):
        return None
    data = getattr(sources, "models_dev_data", {})
    if not isinstance(data, dict):
        return None
    if "/" in model_id:
        provider, bare = model_id.split("/", 1)
        provider_row = data.get(provider)
        models = provider_row.get("models") if isinstance(provider_row, dict) else None
        row = models.get(bare) if isinstance(models, dict) else None
        if isinstance(row, dict):
            limit = row.get("limit")
            return limit.get("context") if isinstance(limit, dict) else None
    bare = key.split("/", 1)[-1]
    values = []
    for provider in data.values():
        rows = provider.get("models") if isinstance(provider, dict) else None
        row = rows.get(bare) if isinstance(rows, dict) else None
        if isinstance(row, dict):
            limit = row.get("limit")
            values.append(limit.get("context") if isinstance(limit, dict) else None)
    return values[0] if values and all(value == values[0] for value in values) else None


def override_for(settings, rid, model_id):
    for override in getattr(settings, "context", ()) if settings is not None else ():
        if override.runtime == rid and override.model == model_id:
            return override.tokens
    return None


def resolve_context(levels: list, now: str) -> tuple:
    """Resolve ordered source levels, noting invalid non-empty source claims."""
    notes = []
    for raw, label, source, at in levels:
        tokens = valid_tokens(raw)
        if tokens is not None:
            return fact(tokens, label, source, at or now), "; ".join(notes)
        if raw is not None:
            notes.append(f"ignored {raw!r} from {source}")
    return None, "; ".join(notes)
