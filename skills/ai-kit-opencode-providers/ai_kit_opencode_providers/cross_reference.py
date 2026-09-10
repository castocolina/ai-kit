"""Non-blocking cross-reference scan before provider removal."""

from __future__ import annotations

import json
import os
from typing import NamedTuple

from ai_kit_opencode_providers.config_paths import (
    catalog_path,
    global_review_spec_path,
    local_review_spec_path,
)

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


def scan_catalog(path: str, provider_id: str) -> list[Reference]:
    """One Reference per catalog field whose string value contains provider_id.

    Missing, unreadable, or malformed files return an empty list, never raise.
    Non-string field values are skipped, never coerced.
    """
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, dict):
        return []
    refs: list[Reference] = []
    for model_id, entry in data.items():
        if not isinstance(entry, dict):
            continue
        provider = entry.get("provider")
        if isinstance(provider, str) and provider_id in provider:
            refs.append(Reference(path, model_id, "provider", provider))
        runtimes = entry.get("runtimes")
        if not isinstance(runtimes, dict):
            continue
        for cli_name, runtime in runtimes.items():
            if not isinstance(runtime, dict):
                continue
            model_id_value = runtime.get("model_id")
            if isinstance(model_id_value, str) and provider_id in model_id_value:
                field = f"runtimes.{cli_name}.model_id"
                refs.append(Reference(path, model_id, field, model_id_value))
    return refs


def review_spec_strategy(path: str) -> str:
    """Top-level `strategy`, defaulting to `global-merge` when absent."""
    try:
        with open(path, encoding="utf-8") as handle:
            raw = handle.read()
    except OSError:
        return "global-merge"
    if tomllib is None:
        return "global-merge"
    try:
        data = tomllib.loads(raw)
    except tomllib.TOMLDecodeError:
        return "global-merge"
    if not isinstance(data, dict):
        return "global-merge"
    strategy = data.get("strategy", "global-merge")
    if not isinstance(strategy, str):
        return "global-merge"
    return strategy


class SourceStatus(str):
    """A `str` subclass -- every existing `status == "scanned-inactive"` (or
    `"scanned"`/`"absent"`) comparison, `in` check, and f-string interpolation
    keeps working completely unchanged, since this *is* a str.

    WR-03: carries the human-readable reason a source is inactive (or `None`
    when active/absent) as `.reason`, so a caller that wants to explain WHY a
    source is inactive (`cmd_remove`'s "(not active: ...)" qualifier) can read
    that reason from the audit entry itself instead of hardcoding the
    `local-only` strategy wording as *the* explanation for every inactive
    source. Without this, a future conditionally-active source added to
    `collect_references` would need its own hardcoded wording bolted onto
    `cmd_remove` to explain correctly -- or would silently get the wrong
    explanation if a maintainer forgot.
    """

    def __new__(cls, value: str, reason: str | None = None) -> SourceStatus:
        obj = str.__new__(cls, value)
        obj.reason = reason
        return obj


def _source_status(path: str, reason: str | None) -> SourceStatus:
    if not os.path.exists(path):
        return SourceStatus("absent")
    if reason is not None:
        return SourceStatus("scanned-inactive", reason=reason)
    return SourceStatus("scanned")


def collect_references(
    provider_id: str, cwd: str, env: dict
) -> tuple[list[Reference], list[tuple[str, str]]]:
    """Scan local review-spec, global review-spec, then the cached catalog."""
    local_path = local_review_spec_path(cwd)
    global_path = global_review_spec_path(env)
    cat_path = catalog_path(env)
    strategy = review_spec_strategy(local_path)
    global_inactive_reason = (
        'local review-spec sets strategy = "local-only"'
        if strategy == "local-only"
        else None
    )
    sources = (
        (local_path, scan_review_spec, None),
        (global_path, scan_review_spec, global_inactive_reason),
        (cat_path, scan_catalog, None),
    )
    refs: list[Reference] = []
    audit: list[tuple[str, str]] = []
    for path, scanner, reason in sources:
        audit.append((path, _source_status(path, reason)))
        refs.extend(scanner(path, provider_id))
    return refs, audit


def format_reference(ref: Reference) -> str:
    return f"{ref.source_path}: {ref.locator} {ref.field}={ref.value}"
