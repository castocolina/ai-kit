"""Per-call routing (D-08, D-15, D-19, D-20, D-22, D-31).

Native versus subprocess is decided here from the current host and the runtimes inventory,
never stored. The bounded refresh re-lists only the runtime that missed, at most once per
process and never inside REFRESH_FLOOR_S of the cache write.
"""
import os
import re
import time
from collections.abc import Mapping
from typing import NamedTuple

from ai_kit_spec.cache import cache_is_stale, cache_read_json, cache_write_json
from ai_kit_spec.detection import (
    CLAUDE_FALLBACK_MODEL_IDS,
    CLAUDE_MODEL_ALIASES,
    RUNTIMES,
    RUNTIMES_TTL_SECONDS,
    build_runtimes_snapshot,
    cache_runtimes_path,
    claude_runtime_fields,
    claude_runtime_is_current,
    list_runtime_models,
    normalize_runtime_keys,
    resolve_runtime_binary,
    runtimes_schema_is_current,
)
from ai_kit_spec.model_catalog import cache_catalog_path

REFRESH_FLOOR_S = 60

SKIP_ROUTES = frozenset({
    "bad_model", "no_inventory", "not_installed", "unknown_runtime", "no_model", "review_only",
})

_REFRESHED: set[str] = set()


def host_can_select(runtime, model, host) -> bool:
    """Whether the host has a verified per-call selector for this model.

    Verified only for Claude Code aliases on Claude Code. Every other host is
    session-default-only until Phases 20-22 (R3).
    """
    return (
        isinstance(runtime, str)
        and runtime == host
        and runtime in RUNTIMES
        and isinstance(model, str)
        and model in RUNTIMES[runtime].native_selectors
    )


class RouteInput(NamedTuple):
    runtime: str | None
    model: str
    command: str | None = None

    @classmethod
    def of(cls, resolved) -> "RouteInput":
        """From a ResolvedReviewer or a reviewer entry dict."""
        if isinstance(resolved, dict):
            return cls(runtime=resolved.get("runtime"), model=resolved.get("model", ""),
                       command=resolved.get("command"))
        return cls(runtime=resolved.runtime, model=resolved.model, command=resolved.command)


class Inventory(NamedTuple):
    installed: frozenset[str]
    models: Mapping[str, tuple[str, ...] | None]


def _deduped(items) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if isinstance(item, str) and item not in seen:
            seen.add(item)
            ordered.append(item)
    return tuple(ordered)


def _claude_models(row: dict) -> tuple[str, ...] | None:
    """Aliases plus recorded full ids. None when the row records nothing at all, so a
    models-less row (a failed refresh) stays unverified instead of falling back silently."""
    aliases = row.get("aliases")
    recorded = row.get("models")
    if not isinstance(aliases, list) and not isinstance(recorded, list):
        return None
    if not isinstance(aliases, list):
        aliases = list(CLAUDE_MODEL_ALIASES)
    full_ids = recorded if isinstance(recorded, list) else list(CLAUDE_FALLBACK_MODEL_IDS)
    return _deduped([*aliases, *full_ids])


def inventory_from_snapshot(snapshot: dict | None) -> Inventory:
    """Installed runtimes and their model lists. Malformed data is an empty inventory."""
    if not isinstance(snapshot, dict):
        return Inventory(frozenset(), {})
    clis = normalize_runtime_keys(snapshot.get("clis"))
    installed: set[str] = set()
    models: dict[str, tuple[str, ...] | None] = {}
    for rid, row in clis.items():
        if not isinstance(rid, str) or rid not in RUNTIMES or not isinstance(row, dict):
            continue
        if row.get("installed") is True:
            installed.add(rid)
        if rid == "claude":
            models[rid] = _claude_models(row)
        else:
            recorded = row.get("models")
            models[rid] = tuple(item for item in recorded if isinstance(item, str)) \
                if isinstance(recorded, list) else None
    return Inventory(frozenset(installed), models)


def strip_model_suffix(runtime, model) -> str:
    """Drop a row's model_suffix (cursor brackets, opencode variant, pi level) before lookup."""
    row = RUNTIMES.get(runtime) if isinstance(runtime, str) else None
    if row is None or not row.model_suffix or not isinstance(model, str):
        return model
    return re.sub(row.model_suffix, "", model)


def _is_custom(entry: RouteInput) -> bool:
    return isinstance(entry.command, str) and entry.command != "" and entry.runtime is None


def _route_shape(entry: RouteInput, mode: str) -> str | None:
    """Routes decided before any inventory lookup, or None to keep going."""
    if _is_custom(entry):
        return "review_only" if mode == "exec" else "custom"
    runtime = entry.runtime
    # An out-of-table runtime is a visible skip even without a model (D-20).
    if runtime is not None and (not isinstance(runtime, str) or runtime not in RUNTIMES):
        return "unknown_runtime"
    if runtime is not None and (not isinstance(entry.model, str) or entry.model == ""):
        return "no_model"
    # No runtime and no model: the session default (D-07).
    if entry.model == "" or entry.model is None:
        return "native"
    return None


def _route_inventory(entry: RouteInput, inventory: Inventory) -> str:
    """Routes that need the inventory: installed, listed, then membership."""
    runtime = entry.runtime
    if runtime not in inventory.installed:
        return "not_installed"
    if RUNTIMES[runtime].list_argv is None and not RUNTIMES[runtime].runner:
        return "no_inventory"
    known = inventory.models.get(runtime)
    if known is None:
        return "unverified"
    bare = strip_model_suffix(runtime, entry.model)
    if bare in known or entry.model in known:
        return "subprocess"
    return "bad_model"


def route(entry: RouteInput, host: str, mode: str, inventory: Inventory) -> str:
    """One entry's route. Order is load-bearing: see the module docstring's decision list."""
    decided = _route_shape(entry, mode)
    if decided is not None:
        return decided
    runtime = entry.runtime
    if not isinstance(runtime, str):
        return "unknown_runtime"
    if host_can_select(runtime, entry.model, host):
        return "native"
    if mode == "exec" and RUNTIMES[runtime].review_only:
        return "review_only"
    return _route_inventory(entry, inventory)


def unroutable_quota(quota: dict, routes: Mapping[str, str]) -> dict:
    """In-memory overlay: skip routes become unavailable, native rows are dropped.

    A stale cached row (an `auth` result still inside its hour TTL) must not hide a native
    reviewer, and a skip must not win the ladder walk. Never written to the quota cache.
    """
    overlaid = dict(quota)
    for key, decision in routes.items():
        if decision in SKIP_ROUTES:
            overlaid[key] = {"available": False, "reason": decision}
        elif decision == "native":
            overlaid.pop(key, None)
    return overlaid


class RuntimesSeams(NamedTuple):
    which_fn: object
    run_fn: object
    popen_fn: object
    urlopen_fn: object


class RouteContext(NamedTuple):
    host: str
    mode: str
    env: dict
    seams: RuntimesSeams


def _catalog_reader(env):
    def read():
        return cache_read_json(cache_catalog_path(env))
    return read


def runtimes_cache_is_fresh(path, env) -> bool:
    """The three-part freshness test shared by detect-runtimes and the refresh."""
    cached = cache_read_json(path)
    return (
        not cache_is_stale(path, RUNTIMES_TTL_SECONDS)
        and runtimes_schema_is_current(cached)
        and claude_runtime_is_current(cached, catalog_fn=_catalog_reader(env))
    )


def load_runtimes_snapshot(env, seams, force=False) -> tuple[dict, bool]:
    """The cached snapshot, or a fresh build. The bool says this call built it."""
    path = cache_runtimes_path(env)
    if not force and runtimes_cache_is_fresh(path, env):
        return cache_read_json(path) or {}, False
    snapshot = build_runtimes_snapshot(
        which_fn=seams.which_fn, run_fn=seams.run_fn, catalog_fn=_catalog_reader(env),
        popen_fn=seams.popen_fn, urlopen_fn=seams.urlopen_fn)
    cache_write_json(path, snapshot)
    _REFRESHED.update(rid for rid in RUNTIMES if rid in snapshot.get("clis", {}))
    return snapshot, True


def _row_changed(before, after) -> bool:
    return before != after


def _refresh_runtime(snapshot, rid, ctx: RouteContext) -> bool:
    """Re-resolve one runtime's binary and, when found, its model fields. True when changed."""
    _REFRESHED.add(rid)
    clis = snapshot.setdefault("clis", {})
    before = clis.get(rid)
    binary = resolve_runtime_binary(rid, ctx.seams.which_fn)
    if not binary and isinstance(before, dict) and before.get("installed"):
        # A failed re-resolution must not wipe a runtime the snapshot already records as
        # installed: the lookup can miss for reasons that say nothing about the install.
        binary = before.get("path")
    if not binary:
        row = {"installed": False}
    else:
        # Start from the cached row: reasoning_modes and the image_input fields survive.
        row = {**(before if isinstance(before, dict) else {}), "installed": True,
               "path": binary}
        if rid == "claude":
            row.update(claude_runtime_fields(cache_read_json(cache_catalog_path(ctx.env))))
        else:
            listed = list_runtime_models(rid, binary, run_fn=ctx.seams.run_fn)
            recorded = before.get("models") if isinstance(before, dict) else None
            if isinstance(listed, list) and (listed or not isinstance(recorded, list)):
                row["models"] = listed
            elif isinstance(recorded, list):
                # The re-list found nothing or failed. A verified inventory stands until a
                # re-list names something.
                row["models"] = recorded
    if not _row_changed(before, row):
        return False
    clis[rid] = row
    return True


def _entry_runtime(entry) -> str | None:
    runtime = entry.get("runtime")
    return runtime if isinstance(runtime, str) and runtime in RUNTIMES else None


def _refresh_targets(entries, routes) -> list[str]:
    """Runtimes whose miss is worth one more look. A claude bad_model is final: its ids come
    from the catalog, so re-listing it would only risk wiping the recorded ones."""
    targets: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict) or "key" not in entry:
            continue
        decision = routes.get(entry["key"])
        runtime = _entry_runtime(entry)
        if runtime is None or runtime in targets:
            continue
        if decision == "not_installed" or (
            decision in ("bad_model", "unverified") and runtime != "claude"
        ):
            targets.append(runtime)
    return targets


def _within_floor(path) -> bool:
    try:
        return time.time() - os.stat(path).st_mtime < REFRESH_FLOOR_S
    except OSError:
        return False


def route_all(entries: list[dict], ctx: RouteContext) -> dict[str, str]:
    """key -> route for every dict entry that carries a key, with one bounded refresh."""
    snapshot, built = load_runtimes_snapshot(ctx.env, ctx.seams)
    state = {"inventory": inventory_from_snapshot(snapshot)}

    def decide(entry):
        return route(RouteInput.of(entry), ctx.host, ctx.mode, state["inventory"])

    routes = {entry["key"]: decide(entry) for entry in entries
              if isinstance(entry, dict) and "key" in entry}
    if built or _within_floor(cache_runtimes_path(ctx.env)):
        return routes
    targets = [rid for rid in _refresh_targets(entries, routes) if rid not in _REFRESHED]
    if not targets:
        return routes
    changed = [rid for rid in targets if _refresh_runtime(snapshot, rid, ctx)]
    if not changed:
        return routes
    cache_write_json(cache_runtimes_path(ctx.env), snapshot)
    state["inventory"] = inventory_from_snapshot(snapshot)
    for entry in entries:
        if isinstance(entry, dict) and _entry_runtime(entry) in changed and "key" in entry:
            routes[entry["key"]] = decide(entry)
    return routes
