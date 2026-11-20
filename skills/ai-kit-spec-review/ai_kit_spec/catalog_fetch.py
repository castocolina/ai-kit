"""35 D-02, D-03: per-source catalog fetching and freshness.

Each source has its own [models] cache age, visible skip reasons, validated
fetch-meta records and, for models.dev and Arena, a raw source cache. cli.py
only calls this module.
"""

import math
import os
import sys
import time
from typing import NamedTuple

from ai_kit_spec.cache import cache_read_json, cache_write_json
from ai_kit_spec.catalog_build import CatalogSources
from ai_kit_spec.model_catalog import CATALOG_SCHEMA_VERSION
from ai_kit_spec.models_config import KNOWN_SOURCES, SOURCE_KEYS

FUTURE_SLACK_S = 300


def _valid_record(record, now: float) -> bool:
    if not isinstance(record, dict):
        return False
    fetched = record.get("last_fetched")
    return (
        isinstance(fetched, (int, float))
        and not isinstance(fetched, bool)
        and math.isfinite(fetched)
        and 0 <= fetched <= now + FUTURE_SLACK_S
        and isinstance(record.get("ok"), bool)
    )


def read_fetch_meta(path: str, now: float | None = None) -> dict:
    """Read only validated per-source proofs; legacy global ages prove no source fresh."""
    current = time.time() if now is None else now
    data = cache_read_json(path)
    sources = data.get("sources") if isinstance(data, dict) else None
    if not isinstance(sources, dict):
        return {}
    return {
        key: record
        for key, record in sources.items()
        if key in SOURCE_KEYS.values() and _valid_record(record, current)
    }


class PlanFlags(NamedTuple):
    if_stale: bool
    schema_current: bool


def _cached_reason(record: dict) -> str:
    fetched = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record["last_fetched"]))
    return "cached, fetched " + fetched


def source_plan(meta: dict, settings, flags: PlanFlags, api_key: str, now: float) -> dict:
    """Plan each configured source independently and explain every skipped source."""
    plans = {}
    for name in KNOWN_SOURCES:
        key = SOURCE_KEYS[name]
        record = meta.get(key)
        if name not in settings.sources:
            plans[name] = (False, "disabled in [models] sources")
        elif name == "artificial-analysis" and not api_key:
            plans[name] = (False, "no ARTIFICIAL_ANALYSIS_API_KEY in secrets.env")
        elif (
            flags.if_stale
            and flags.schema_current
            and record
            and record["ok"]
            and now - record["last_fetched"] <= settings.cache_days[key] * 86400
        ):
            plans[name] = (False, _cached_reason(record))
        else:
            plans[name] = (True, "")
    return plans


def raw_cache_path(catalog_path: str, key: str) -> str:
    return os.path.join(os.path.dirname(catalog_path) or ".", "sources", f"{key}.json")


def read_raw_source(catalog_path: str, key: str) -> tuple:
    """Return a valid raw payload and timestamp, or ``(None, None)``."""
    data = cache_read_json(raw_cache_path(catalog_path, key))
    if not isinstance(data, dict) or "data" not in data:
        return None, None
    fetched = data.get("fetched_at")
    record = {"last_fetched": fetched, "ok": True}
    if not _valid_record(record, time.time()):
        return None, None
    return data["data"], fetched


class FetchedRaw(NamedTuple):
    sources: CatalogSources
    results: dict
    source_at: dict


def _fetch_one(deps, name: str, api_key: str):
    if name == "models.dev":
        return deps.fetch_models_dev_fn()
    if name == "artificial-analysis":
        payload, ok = deps.fetch_artificial_analysis_fn(api_key)
        return payload, bool(ok and api_key)
    return deps.fetch_arena_fn(progress=lambda line: print(line, file=sys.stderr))


def _assemble_sources(payloads: dict, statuses: dict) -> CatalogSources:
    return CatalogSources(
        payloads["models.dev"] or {},
        statuses["models.dev"],
        payloads["artificial-analysis"] or [],
        statuses["artificial-analysis"],
        arena_data=payloads["arena"],
        arena_ok=statuses["arena"],
    )


def _reuse_one(name: str, reason: str, catalog_path: str):
    if name == "artificial-analysis":
        return None, False, {"fetched": False, "ok": True, "reason": reason}, None
    key = SOURCE_KEYS[name]
    payload, fetched = read_raw_source(catalog_path, key)
    if fetched is None:
        result = {"fetched": False, "ok": None, "reason": reason + "; raw data not cached"}
        return None, False, result, None
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(fetched))
    result = {"fetched": False, "ok": True, "reason": reason}
    return payload, True, result, timestamp


def _fetch_result(deps, name: str, api_key: str, catalog_path: str):
    payload, ok = _fetch_one(deps, name, api_key)
    result = {"fetched": True, "ok": bool(ok), "reason": "" if ok else "fetch failed"}
    if ok and name != "artificial-analysis":
        key = SOURCE_KEYS[name]
        cache_write_json(
            raw_cache_path(catalog_path, key), {"fetched_at": time.time(), "data": payload}
        )
    return payload if ok else None, bool(ok), result


def fetch_sources(deps, plan: dict, api_key: str, catalog_path: str) -> FetchedRaw:
    """Fetch planned sources or reuse raw data; never persist keyed raw data."""
    payloads, statuses, results, source_at = {}, {}, {}, {}
    for name in KNOWN_SOURCES:
        fetch, reason = plan[name]
        if not fetch and reason.startswith("cached"):
            payload, ok, result, fetched_at = _reuse_one(name, reason, catalog_path)
            if fetched_at is not None:
                source_at[SOURCE_KEYS[name]] = fetched_at
        elif fetch:
            payload, ok, result = _fetch_result(deps, name, api_key, catalog_path)
        else:
            payload, ok = None, False
            result = {"fetched": False, "ok": None, "reason": reason}
        payloads[name], statuses[name], results[name] = payload, ok, result
    return FetchedRaw(_assemble_sources(payloads, statuses), results, source_at)


def updated_fetch_meta(meta: dict, results: dict, now: float) -> dict:
    """Update per-source fetch proofs, retaining the last successful time on failure."""
    records = dict(meta)
    for name in KNOWN_SOURCES:
        key = SOURCE_KEYS[name]
        result = results.get(name, {})
        if result.get("fetched"):
            previous = meta.get(key, {})
            fetched = now if result.get("ok") else previous.get("last_fetched", 0)
            records[key] = {"last_fetched": fetched, "ok": bool(result.get("ok"))}
    return {"schema_version": CATALOG_SCHEMA_VERSION, "sources": records}
