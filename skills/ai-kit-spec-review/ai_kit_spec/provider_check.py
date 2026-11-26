"""Stale opencode provider report for `ai-kit-spec.py check-providers` (SPEC R5, D-02, D-03).

Read-only: each config.toml (or the old roster still pending beside it) and catalog file is read
once and nothing is written. The report prints provider ids and the reviewer/catalog model
reference only; it never opens opencode's auth.json and never prints a key or an apiKey value.
Stdlib only.

It matches on the provider part of each model id (`provider/model`), never a substring.
"""

import os
from typing import NamedTuple

from ai_kit_spec import cache, config_io, config_migrate, detection, jsonc_read, trust
from ai_kit_spec.model_catalog import cache_catalog_path

UNCONFIRMED_SUFFIX = (
    " (unconfirmed: config file only; built-in, login and environment providers not checked)"
)
LOCAL_ONLY_REASON = 'project config.toml sets strategy = "local-only"'
UNTRUSTED_REASON = "project config.toml is not trusted"


class SourceStatus(str):
    """The printed status text of one source; `.reason` names why its references are inactive."""

    reason: str | None

    def __new__(cls, value: str, reason: str | None = None) -> "SourceStatus":
        obj = str.__new__(cls, value)
        obj.reason = reason
        return obj


class Reference(NamedTuple):
    source_path: str
    locator: str
    field: str
    value: str
    provider: str


class _Scan(NamedTuple):
    local_path: str
    global_path: str
    catalog_path: str
    local_status: SourceStatus
    local_refs: list
    global_status: SourceStatus
    global_refs: list
    cat_status: SourceStatus
    cat_refs: list


def lanes_strategy(lanes: dict) -> str:
    """The [lanes] `strategy`; `global-merge` when absent or not a string."""
    strategy = lanes.get("strategy", "global-merge")
    return strategy if isinstance(strategy, str) else "global-merge"


def _first_line(message: str) -> str:
    lines = str(message).splitlines()
    return lines[0] if lines else ""


def _opencode_refs(path: str, lanes: dict) -> list[Reference]:
    """One Reference per opencode lane (review, then execute) whose model names a provider
    (`provider/model`); a (key, model) pair already reported is not repeated."""
    refs: list[Reference] = []
    seen: set[tuple[str, str]] = set()
    for role in ("review", "execute"):
        entries = lanes.get(role, [])
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            if entry.get("runtime") != "opencode" and entry.get("cli") != "opencode":
                continue
            model = entry.get("model")
            if not isinstance(model, str) or "/" not in model:
                continue
            key = str(entry.get("key", ""))
            if (key, model) in seen:
                continue
            seen.add((key, model))
            refs.append(Reference(path, key, "model", model, model.split("/", 1)[0]))
    return refs


def _is_trusted(env: dict, path: str, raw: bytes, legacy: bool = False) -> bool:
    """Trust of path's bytes; legacy reads the old roster's trust store (old raw-byte rule)."""
    try:
        store = config_io.cfg_trust_store_dir(env)
    except config_io.ConfigError:
        return False
    if legacy:
        store = config_migrate.legacy_trust_dir(store)
    return trust.is_trusted(store, os.path.realpath(path), raw)


def _unreadable(message: str) -> SourceStatus:
    return SourceStatus(f"scanned (unreadable: {_first_line(message)})")


def _gated(status: SourceStatus, refs: list, lanes: dict, trusted: bool) -> tuple:
    """The given status when trusted, else the untrusted status (its references are inactive)."""
    if trusted:
        return status, refs, lanes, True
    return SourceStatus("scanned-inactive (untrusted)", reason=UNTRUSTED_REASON), refs, lanes, False


def _scan_lanes(path: str, env: dict, lanes: dict, gate_trust: bool) -> tuple:
    """A config.toml with a [lanes] table: trusted when it has no command-bearing entry or its
    canonical bytes are trusted (D-11); only the project layer is gated."""
    status = SourceStatus("scanned")
    refs = _opencode_refs(path, lanes)
    if not gate_trust:
        return status, refs, lanes, True
    try:
        canonical = config_io.cfg_project_trust_bytes(lanes, env)
    except config_io.ConfigError as exc:
        return _unreadable(exc.message), [], None, False
    return _gated(status, refs, lanes, canonical is None or _is_trusted(env, path, canonical))


def _scan_pending(path: str, env: dict, gate_trust: bool) -> tuple:
    """No [lanes] in config.toml: a pending old roster is read in memory and reported (migration
    pending, or held when it names a removed runtime; nothing written); with no old roster the
    source is absent."""
    old = config_migrate.pending(path)
    if old is None:
        return SourceStatus("absent"), [], None, False
    try:
        found = config_migrate.read_legacy(path)
    except config_migrate.LegacyRosterError as exc:
        return _unreadable(exc.message), [], None, False
    if found is None:  # removed between the two reads
        return SourceStatus("absent"), [], None, False
    lanes, raw = found
    held = "held" if config_io.cfg_names_removed_runtime(lanes) else "pending"
    status = SourceStatus(f"scanned (migration {held}: {old})")
    refs = _opencode_refs(old, lanes)
    if not gate_trust:
        return status, refs, lanes, True
    try:
        canonical = config_io.cfg_project_trust_bytes(lanes, env)
    except config_io.ConfigError as exc:
        return _unreadable(exc.message), [], None, False
    return _gated(status, refs, lanes,
                  canonical is None or _is_trusted(env, old, raw, legacy=True))


def scan_config(
    path: str, env: dict, gate_trust: bool = False
) -> tuple[SourceStatus, list[Reference], dict | None, bool]:
    """Read one config.toml (or the pending old roster beside it) once. Returns (status, refs,
    the [lanes] table or None, trusted).

    `trusted` is only decided for the project layer (`gate_trust`), as cfg_resolve does; an
    untrusted [lanes] is reported as inactive and is never trusted for its strategy. Nothing is
    migrated or written.
    """
    if os.path.exists(path):
        try:
            raw = config_io.cfg_read_bytes(path)
            lanes = config_io.cfg_lanes_table(config_io.cfg_parse_toml_bytes(raw, path), path)
        except config_io.ConfigError as exc:
            return _unreadable(exc.message), [], None, False
        if lanes:
            return _scan_lanes(path, env, lanes, gate_trust)
    return _scan_pending(path, env, gate_trust)


def scan_catalog(path: str) -> tuple[SourceStatus, list[Reference]]:
    """Catalog entries whose runtimes.opencode.model_id names a provider; `_meta` is skipped."""
    if not os.path.exists(path):
        return SourceStatus("absent"), []
    data = cache.cache_read_json(path)
    if data is None:
        return SourceStatus("scanned (unreadable: not valid JSON)"), []
    if not isinstance(data, dict):
        return SourceStatus("scanned (unreadable: not a JSON object)"), []
    refs: list[Reference] = []
    for key, entry in data.items():
        if key == "_meta" or not isinstance(entry, dict):
            continue
        runtimes = entry.get("runtimes")
        opencode = runtimes.get("opencode") if isinstance(runtimes, dict) else None
        model_id = opencode.get("model_id") if isinstance(opencode, dict) else None
        if isinstance(model_id, str) and "/" in model_id:
            provider = model_id.split("/", 1)[0]
            refs.append(Reference(path, key, "runtimes.opencode.model_id", model_id, provider))
    return SourceStatus("scanned"), refs


def _names_from(paths: list[str]) -> set[str]:
    names: set[str] = set()
    for path in paths:
        found = jsonc_read.read_provider_names(path)
        if found:
            names.update(found)
    return names


def served_providers(deps, env: dict, cwd: str) -> tuple[set[str] | None, str, bool]:
    """(provider ids or None, label for the served line, confirmed by the live listing)."""
    binary = detection.resolve_runtime_binary("opencode", which_fn=deps.which_fn)
    listed = None
    if binary:
        listed = detection.detect_opencode_models(binary, run_fn=deps.run_fn, env=env)
    ids = {line.split("/", 1)[0] for line in listed or [] if "/" in line}
    if ids:
        extra = _names_from(jsonc_read.project_config_paths(cwd)) - ids
        label = "listed by opencode plus project config files" if extra else "listed by opencode"
        return ids | extra, label, True
    if listed is not None:  # exit 0 but no provider/model line: nothing confirmed
        return None, "not checked: opencode listed no models", True
    names = _names_from(jsonc_read.opencode_config_paths(env, cwd))
    if names:
        return names, "config file only; login and environment providers not checked", False
    reason = "opencode not installed" if binary is None else "opencode models failed"
    return None, f"not checked: {reason} and no opencode config file", True


def _global_source(path: str, env: dict, local_only: bool) -> tuple[SourceStatus, list]:
    status, refs, _lanes, _trusted = scan_config(path, env)
    if local_only and (status == "scanned" or status.startswith("scanned (migration ")):
        status = SourceStatus("scanned-inactive", reason=LOCAL_ONLY_REASON)
    return status, refs


def _scan_sources(env: dict, cwd: str) -> _Scan:
    local_path = config_io.cfg_local_path(cwd)
    global_path = config_io.cfg_global_path(env)
    catalog_path = cache_catalog_path(env)
    local_status, local_refs, local_lanes, trusted = scan_config(
        local_path, env, gate_trust=True
    )
    local_only = trusted and local_lanes is not None and (
        lanes_strategy(local_lanes) == "local-only"
    )
    global_status, global_refs = _global_source(global_path, env, local_only)
    cat_status, cat_refs = scan_catalog(catalog_path)
    return _Scan(
        local_path, global_path, catalog_path,
        local_status, local_refs, global_status, global_refs, cat_status, cat_refs,
    )


def _warning_lines(refs_with_reasons, providers, confirmed: bool) -> list[str]:
    if providers is None:
        return []
    lines = []
    for ref, reason in refs_with_reasons:
        if not ref.provider or ref.provider in providers:
            continue
        suffix = f" (not active: {reason})" if reason else ""
        if not confirmed:
            suffix += UNCONFIRMED_SUFFIX
        lines.append(
            f'warning: "{ref.provider}" is referenced in {ref.source_path}: '
            f"{ref.locator} {ref.field}={ref.value}{suffix}"
        )
    return lines


def _report_lines(scan: _Scan, providers, label: str, confirmed: bool) -> list[str]:
    refs_with_reasons = (
        [(ref, scan.local_status.reason) for ref in scan.local_refs]
        + [(ref, scan.global_status.reason) for ref in scan.global_refs]
        + [(ref, None) for ref in scan.cat_refs]
    )
    if providers is None:
        served = f"served providers: {label}"
    else:
        served = f"served providers: {label} ({', '.join(sorted(providers))})"
    lines = [
        f"cross-reference: {scan.local_path} {scan.local_status}",
        f"cross-reference: {scan.global_path} {scan.global_status}",
        f"cross-reference: {scan.catalog_path} {scan.cat_status}",
        served,
    ]
    return lines + _warning_lines(refs_with_reasons, providers, confirmed)


def check_providers_report(deps, env: dict, cwd: str) -> list[str]:
    """Report lines in fixed order: the three sources, one served line, then warnings."""
    scan = _scan_sources(env, cwd)
    providers, label, confirmed = served_providers(deps, env, cwd)
    return _report_lines(scan, providers, label, confirmed)
