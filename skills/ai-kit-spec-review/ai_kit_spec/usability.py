"""35 D-10 / R2: per-(runtime, model) records from check-reviewer's real call.

Only an answered call is verified; errors are first-line, control-free, redacted and capped.
"""

import re

from ai_kit_spec import model_catalog, secret_shapes
from ai_kit_spec.model_catalog import join_catalog_meta, merge_catalog_entry, split_catalog_meta

ERROR_MAX = 200
_CONTROL_RX = re.compile(r"[\x00-\x1f\x7f-\x9f]")


def sanitize_error(detail) -> str | None:
    """Keep only a safe, bounded first line of provider error text."""
    if not detail or not isinstance(detail, str):
        return None
    lines = detail.splitlines()
    if not lines:
        return None
    line = _CONTROL_RX.sub("", lines[0])
    line = secret_shapes.redact(line, "[redacted]").strip()[:ERROR_MAX]
    return line or None


def record_for(result: dict, runtime, now: str) -> dict | None:
    """Map one probe outcome to its runtime-scoped usability evidence."""
    if runtime is None:
        return None
    if result.get("available") is True:
        reason = result.get("reason")
        if reason:
            via_reason = sanitize_error(reason) or "reason"
            return {"state": "unverified", "at": now,
                    "via": f"check-reviewer ({via_reason})", "error": None}
        if result.get("answered") is True:
            return {"state": "verified", "at": now, "via": "check-reviewer", "error": None}
        return {"state": "unverified", "at": now,
                "via": "check-reviewer (no answer text)", "error": None}
    return {"state": "rejected", "at": now, "via": "check-reviewer",
            "error": sanitize_error(result.get("detail") or result.get("reason"))}


def find_runtime_key(entries: dict, runtime: str, model_id: str) -> str | None:
    """Find the first well-shaped entry mapping this runtime to the requested id."""
    for key in sorted(entries):
        entry = entries[key]
        if not isinstance(entry, dict):
            continue
        runtimes = entry.get("runtimes")
        if not isinstance(runtimes, dict):
            continue
        row = runtimes.get(runtime)
        if isinstance(row, dict) and row.get("model_id") == model_id:
            return key
    return None


class _NotInCatalog(Exception):
    """Abort a locked update without writing when its pair cannot be safely matched."""


def record_usability(catalog_path: str, runtime: str, model_id: str, record: dict) -> tuple:
    """Atomically merge a usability record into the matching pair under the catalog lock."""
    found_key = None

    def update(current):
        nonlocal found_key
        entries, meta = split_catalog_meta(current)
        key = find_runtime_key(entries, runtime, model_id)
        if key is None:
            raise _NotInCatalog()
        incoming = {**entries[key], "runtimes": {
            runtime: {"model_id": model_id, "usability": record}
        }}
        updated, reason = merge_catalog_entry(entries, key, incoming)
        if reason:
            raise _NotInCatalog(reason)
        found_key = key
        return join_catalog_meta(updated, meta)

    try:
        model_catalog.locked_catalog_update(catalog_path, update)
    except _NotInCatalog as exc:
        text = str(exc)
        if text:
            return None, text
        return None, f"not in catalog: {runtime} {model_id}"
    except ValueError as exc:
        return None, str(exc)
    return found_key, None
