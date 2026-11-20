"""Optional model-name sources for runtimes without a listing (35 D-11, D-20, Amend-4 / R3).

Seed rows, an agent-written web-names file, and pane names are sanitized and labeled; nothing
here marks a model verified.
"""

import json
import os
import re
from typing import NamedTuple

from ai_kit_spec.cache import cache_base, cache_read_json, cache_write_json
from ai_kit_spec.detection import KNOWN_CLIS


class SeedRow(NamedTuple):
    runtime: str
    models_dev_provider: str | None
    source: str
    label: str


# model-example: seed rows map a runtime to its models.dev provider (data with a source label;
# live evidence overrides them; 35 D-11)
SEED_ROWS = (
    SeedRow(
        "claude",
        "anthropic",
        "first-party provider of the claude CLI (16 D-04)",
        "seed, unverified",
    ),
    SeedRow(
        "copilot",
        None,
        "the one models.dev provider key holding the token copilot",
        "seed, unverified",
    ),
)


def seed_provider(runtime: str, models_dev_data) -> str | None:
    """Resolve a seed row's provider, requiring a unique token match for inferred rows."""
    row = next((item for item in SEED_ROWS if item.runtime == runtime), None)
    if row is None or not isinstance(models_dev_data, dict):
        return None
    if row.models_dev_provider is not None:
        return row.models_dev_provider if row.models_dev_provider in models_dev_data else None
    matches = [
        key
        for key in models_dev_data
        if isinstance(key, str) and runtime in key.split("-")
    ]
    return matches[0] if len(matches) == 1 else None


def seed_candidates(runtime: str, models_dev_data) -> list:
    """Return sorted ids from the resolved provider's well-shaped models mapping."""
    provider = seed_provider(runtime, models_dev_data)
    provider_data = models_dev_data.get(provider) if provider else None
    models = provider_data.get("models") if isinstance(provider_data, dict) else None
    if not isinstance(models, dict):
        return []
    return sorted(model_id for model_id in models if isinstance(model_id, str))


MODEL_ID_RX = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/#@+=\[\]-]{0,127}")
_ANSI_RX = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
_CONTROL_RX = re.compile(r"[\x00-\x1f\x7f-\x9f]")


def sanitize_name(raw) -> str | None:
    """Remove terminal/control text and accept only a bounded model identifier."""
    if not isinstance(raw, str):
        return None
    name = _CONTROL_RX.sub("", _ANSI_RX.sub("", raw)).strip()
    return name if MODEL_ID_RX.fullmatch(name) else None


WEB_QUERY_TEMPLATE = "{runtime} CLI available models list"
_RUNTIME_RX = re.compile(r"[a-z][a-z0-9-]{1,30}")


def web_query(runtime: str) -> str:
    """Build a generic query only for a known public runtime id."""
    valid_pattern = isinstance(runtime, str) and _RUNTIME_RX.fullmatch(runtime)
    if not valid_pattern or runtime not in KNOWN_CLIS:
        raise ValueError("web query: bad runtime id")
    return WEB_QUERY_TEMPLATE.format(runtime=runtime)


def ingest_web_file(path: str) -> tuple:
    """Validate an agent-written web result and retain sanitized, unique names only."""
    try:
        with open(path, encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, ValueError) as exc:
        raise ValueError("web file: unreadable") from exc
    if not isinstance(payload, dict):
        raise ValueError("web file: invalid fields")
    runtime = payload.get("runtime")
    if not isinstance(runtime, str) or not _RUNTIME_RX.fullmatch(runtime):
        raise ValueError("web file: invalid fields")
    try:
        expected_query = web_query(runtime)
    except ValueError:
        expected_query = None
    if payload.get("query") != expected_query:
        raise ValueError("web file: query is not the fixed template")
    url = payload.get("url")
    date = payload.get("date")
    names = payload.get("names")
    valid_url = isinstance(url, str) and url.startswith("https://") and len(url) <= 300
    valid_date = isinstance(date, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", date)
    if not valid_url or not valid_date or not isinstance(names, list):
        raise ValueError("web file: invalid fields")
    records = []
    seen = set()
    for raw in names:
        name = sanitize_name(raw)
        if name is None or name in seen:
            continue
        seen.add(name)
        records.append(
            {"name": name, "source": "web", "label": "web, unverified", "url": url, "date": date}
        )
    return runtime, records


STORE_NAME = "optional-names.json"
SOURCE_LABELS = {
    "web": "web, unverified",
    "interactive view": "interactive view, unverified",
    "seed": "seed, unverified",
}


def store_path(env) -> str:
    return os.path.join(cache_base(env), STORE_NAME)


def record_names(path: str, runtime: str, records: list) -> dict:
    """Validate optional provenance, merge unique records, and atomically persist the store."""
    if runtime not in KNOWN_CLIS:
        raise ValueError("optional sources: unknown source or label")
    prepared = []
    for record in records:
        label = record.get("label") if isinstance(record, dict) else None
        if isinstance(label, str) and label.startswith("verified"):
            raise ValueError("optional sources never mark verified")
        source = record.get("source") if isinstance(record, dict) else None
        if source not in SOURCE_LABELS or label != SOURCE_LABELS[source]:
            raise ValueError("optional sources: unknown source or label")
        name = sanitize_name(record.get("name"))
        if name is None:
            continue
        allowed = ("name", "source", "label", "url", "date")
        cleaned = {key: value for key, value in record.items() if key in allowed}
        cleaned["name"] = name
        prepared.append(cleaned)
    store = cache_read_json(path) or {}
    if not isinstance(store, dict):
        store = {}
    runtime_records = store.setdefault(runtime, {})
    if not isinstance(runtime_records, dict):
        runtime_records = {}
        store[runtime] = runtime_records
    for record in prepared:
        items = runtime_records.setdefault(record["name"], [])
        if not isinstance(items, list):
            items = []
            runtime_records[record["name"]] = items
        identity = (record["source"], record.get("url"))
        duplicate = any(
            (item.get("source"), item.get("url")) == identity
            for item in items
            if isinstance(item, dict)
        )
        if not duplicate:
            items.append(record)
    cache_write_json(path, store)
    return store


LABEL_ORDER = ("verified", "host listing", "interactive view", "web", "seed")


def strongest(labels) -> str:
    """Return the strongest label, keeping input order for equal-strength labels."""
    def rank(label):
        prefix = label.split(",", 1)[0] if isinstance(label, str) else ""
        try:
            return LABEL_ORDER.index(prefix)
        except ValueError:
            return len(LABEL_ORDER)

    return min(labels, key=rank, default="unknown")


def optional_candidates(store: dict, runtime: str, seed=()) -> list:
    """Merge names by id while retaining every provenance record for downstream consumers."""
    combined = {}
    runtime_data = store.get(runtime, {}) if isinstance(store, dict) else {}
    if isinstance(runtime_data, dict):
        for name, records in runtime_data.items():
            safe_name = sanitize_name(name)
            if safe_name is not None and isinstance(records, list):
                combined[safe_name] = [dict(item) for item in records if isinstance(item, dict)]
    for raw in seed:
        name = sanitize_name(raw)
        if name is not None:
            combined.setdefault(name, []).append(
                {"name": name, "source": "seed", "label": "seed, unverified"}
            )
    result = []
    for name in sorted(combined):
        records = combined[name]
        labels = [item.get("label", "") for item in records]
        result.append({"name": name, "sources": records, "label": strongest(labels)})
    return result
