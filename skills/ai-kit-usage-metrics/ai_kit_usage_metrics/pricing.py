"""Read-only model-catalog price lookup. Degrades honestly when unknown."""

from __future__ import annotations

import json
import os

from ai_kit_usage_metrics.paths import catalog_path


def canonical_key(provider: str, bare_model_id: str) -> str:
    """Ported from `skills/ai-kit-spec-review/ai_kit_spec/model_catalog.py`."""
    return f"{provider}/{bare_model_id}"


def estimate_price(provider, model, tokens_in, tokens_out, env):
    """Return `(cost, "high")` or `(None, "unknown")`.

    Catalog entry shape: `pricing.input_per_1m` / `pricing.output_per_1m`
    (`model_catalog.py`'s `_NUMERIC_SUBFIELD_TABLES`).
    """
    if tokens_in is None or tokens_out is None:
        return None, "unknown"
    path = catalog_path(env)
    if not os.path.isfile(path):
        return None, "unknown"
    try:
        with open(path, encoding="utf-8") as handle:
            catalog = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None, "unknown"
    if not isinstance(catalog, dict):
        return None, "unknown"
    entry = catalog.get(canonical_key(provider, model))
    if not isinstance(entry, dict):
        return None, "unknown"
    table = entry.get("pricing") or {}
    try:
        input_per_1m = float(table["input_per_1m"])
        output_per_1m = float(table["output_per_1m"])
    except (KeyError, TypeError, ValueError):
        return None, "unknown"
    cost = tokens_in / 1e6 * input_per_1m + tokens_out / 1e6 * output_per_1m
    return cost, "high"
