"""36 R12 a, D-18, contract item 2: sourced prices and free pool keys.

Pure; a model id's wording is never read.
"""

import re
from typing import NamedTuple, TypeGuard

from ai_kit_spec.catalog_bands import is_num
from ai_kit_spec.lane_pool import checked_fact

ZERO_LOCALITY = "zero price (local or hosted not known)"
POOL_TIER = "free"
POOL_KEY_RX = re.compile(r"[A-Za-z0-9._-]{1,64}:[a-z]{1,16}")
_PAID_BANDS = ("low", "medium", "high", "premium")


class Price(NamedTuple):
    state: str
    input: object
    output: object
    sources: tuple
    locality: str
    note: str


def _num(value) -> TypeGuard[float]:
    try:
        return is_num(value) and value >= 0
    except (OverflowError, ValueError):
        return False


def _item_reading(item) -> str:
    if not isinstance(item, dict):
        return "unknown"
    values = (item.get("input"), item.get("output"))
    if any(_num(value) and value > 0 for value in values):
        return "nonzero"
    if all(_num(value) and value == 0 for value in values):
        return "zero"
    return "unknown"


def _host_reading(cli_row, model_id: str, rid: str) -> tuple | None:
    records = cli_row.get("model_records") if isinstance(cli_row, dict) else None
    row = records.get(model_id) if isinstance(records, dict) else None
    cost = row.get("cost") if isinstance(row, dict) else None
    if not isinstance(cost, list) or not cost:
        return None
    states = [_item_reading(item) for item in cost]
    reading = "nonzero" if "nonzero" in states else "zero" if all(
        state == "zero" for state in states
    ) else "unknown"
    if reading == "unknown":
        return None
    pairs = [(item.get("input"), item.get("output")) for item in cost if isinstance(item, dict)]
    figures = pairs[0] if len(pairs) == len(cost) and all(
        all(_num(value) for value in pair) and pair == pairs[0] for pair in pairs
    ) else (None, None)
    listed = cli_row.get("listed_from")
    listed = listed if isinstance(listed, dict) else {}
    source = f"{rid} listing ({listed.get('command') or 'command unknown'} " \
             f"{listed.get('version') or 'version unknown'})"
    return reading, source, listed.get("at") or "date unknown", *figures


def _models_dev_reading(key: str, entry: dict, model_id: str) -> tuple | None:
    if "/" in model_id and model_id.split("/", 1)[0] != key.split("/", 1)[0]:
        return None
    fact = checked_fact(entry, "cost_band")
    if fact is None or fact["source"] != "models.dev":
        return None
    value = fact.get("value")
    pricing = entry.get("pricing")
    pricing = pricing if isinstance(pricing, dict) else {}
    figures = (pricing.get("input_per_1m"), pricing.get("output_per_1m"))
    if value == "free_or_local":
        if any(_num(n) and n > 0 for n in figures):
            return "conflict", "models.dev", fact["fetched_at"], None, None
        figures = figures if all(_num(n) and n == 0 for n in figures) else (None, None)
        return "zero", "models.dev", fact["fetched_at"], *figures
    if value in _PAID_BANDS:
        return "nonzero", "models.dev", fact["fetched_at"], None, None
    return None


def price_of(key: str, entry: dict, model_id: str, cli_row, rid: str) -> Price:
    host = _host_reading(cli_row, model_id, rid)
    band = _models_dev_reading(key, entry, model_id)
    readings = [item for item in (host, band) if item is not None]
    kinds = {item[0] for item in readings}
    state = ("conflict" if "conflict" in kinds or {"zero", "nonzero"} <= kinds else
             "zero" if "zero" in kinds else "nonzero" if "nonzero" in kinds else "unknown")
    inp, out = readings[0][3:] if readings else (None, None)
    sources = tuple({"source": s, "date": d, "reading": k} for k, s, d, _, _ in readings)
    note = ""
    if host and host[3:] == (None, None):
        note = "multiple tiers"
    elif state in ("zero", "nonzero") and inp is None and out is None:
        note = "figure not stored"
    return Price(state, inp, out, sources, ZERO_LOCALITY if state == "zero" else "", note)


def pool_key(model_id: str, provider) -> str | None:
    prefix = model_id.split("/", 1)[0] if "/" in model_id else provider
    if not isinstance(prefix, str):
        return None
    key = f"{prefix}:{POOL_TIER}"
    return key if POOL_KEY_RX.fullmatch(key) else None
