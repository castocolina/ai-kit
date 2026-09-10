"""Non-blocking review-spec cross-reference scan before provider removal."""

from __future__ import annotations

from typing import NamedTuple

try:
    import tomllib as _tomllib_impl
    tomllib = _tomllib_impl
except ModuleNotFoundError:  # Python < 3.11 — degrade to no-scan.
    tomllib = None  # type: ignore[assignment]


class Reference(NamedTuple):
    source_path: str
    locator: str
    field: str
    value: str


def scan_review_spec(path: str, provider_id: str) -> list[Reference]:
    """One Reference per [[reviewers]] whose cli or model contains provider_id.

    Missing, unreadable, or malformed files return an empty list, never raise.
    """
    try:
        with open(path, encoding="utf-8") as handle:
            raw = handle.read()
    except OSError:
        return []
    if tomllib is None:
        return []
    try:
        data = tomllib.loads(raw)
    except tomllib.TOMLDecodeError:
        return []
    if not isinstance(data, dict):
        return []
    refs: list[Reference] = []
    reviewers = data.get("reviewers", [])
    if not isinstance(reviewers, list):
        return []
    for entry in reviewers:
        if not isinstance(entry, dict):
            continue
        locator = entry.get("key", "")
        if not isinstance(locator, str):
            locator = str(locator)
        for field in ("cli", "model"):
            value = entry.get(field)
            if isinstance(value, str) and provider_id in value:
                refs.append(Reference(path, locator, field, value))
    return refs


def format_reference(ref: Reference) -> str:
    return f"{ref.source_path}: {ref.locator} {ref.field}={ref.value}"
