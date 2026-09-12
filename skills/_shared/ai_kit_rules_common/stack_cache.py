"""Generic per-(namespace, stack) tooling-recommendation cache with a
staleness check. Never invents a recommendation from training data -- this
module only reads/writes a local, staleness-gated cache of per-stack
tool-name strings; filling a cold/stale entry is each consuming skill's own
research-dispatch job.

Domain-agnostic: every function takes `cache_root` explicitly. There is no
module-global default here, since this module is shared across skills with
different cache namespaces -- call `default_cache_root(namespace)` once per
skill and thread the result through.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import tempfile
from datetime import UTC, datetime, timedelta

STALE_AFTER_DAYS = 30

_STACK_ID_RE = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}")


def default_cache_root(namespace: str) -> str:
    """Return `~/.cache/ai-kit/<namespace>/stack-refs` (or `$XDG_CACHE_HOME`
    equivalent). `namespace` is each consuming skill's own cache-directory
    segment (e.g. `"agents-md-rules-checker"`, `"makefile-rules-checker"`)."""
    xdg_cache = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    return os.path.join(xdg_cache, "ai-kit", namespace, "stack-refs")


def cache_path(stack: str, cache_root: str) -> str:
    """Return the cache file path for `stack` under `cache_root`, after
    validating `stack`'s shape.

    `stack` must be a bare `[a-z0-9][a-z0-9_-]{0,63}` identifier -- no `/`,
    no `.`, no leading `-`/`_`. Raises `ValueError` BEFORE ever joining the
    value into a filesystem path, so a path-traversal-shaped `stack`
    argument can never resolve to a location outside `cache_root`.
    """
    if not isinstance(stack, str) or _STACK_ID_RE.fullmatch(stack) is None:
        raise ValueError(f"invalid stack identifier: {stack!r}")
    return os.path.join(cache_root, f"{stack}.json")


def read_stack_cache(stack: str, cache_root: str) -> dict:
    """Return `{"state": "absent"|"stale"|"fresh", "data": dict|None}`.

    `data` is populated whenever the file parses, regardless of staleness --
    a stale cache is still returned so a caller CAN fall back to it, but
    must see the `state` flag.
    """
    path = cache_path(stack, cache_root)
    if not os.path.isfile(path):
        return {"state": "absent", "data": None}
    try:
        with open(path, encoding="utf-8") as handle:
            payload = json.load(handle)
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return {"state": "absent", "data": None}
    if not isinstance(payload, dict):
        return {"state": "absent", "data": None}
    cached_at = payload.get("cached_at")
    data = payload.get("tooling")
    if not isinstance(cached_at, str):
        return {"state": "stale", "data": data}
    try:
        cached_dt = datetime.fromisoformat(cached_at)
    except ValueError:
        return {"state": "stale", "data": data}
    if cached_dt.tzinfo is None:
        cached_dt = cached_dt.replace(tzinfo=UTC)
    age = datetime.now(UTC) - cached_dt
    state = "stale" if age > timedelta(days=STALE_AFTER_DAYS) else "fresh"
    return {"state": state, "data": data}


def write_stack_cache(stack: str, data: dict, cache_root: str) -> None:
    """Atomically write `{"cached_at": <iso now>, "stack": stack, "tooling": data}`
    under `cache_root`, via `tempfile.mkstemp` + `os.replace`."""
    path = cache_path(stack, cache_root)
    dirname = os.path.dirname(path)
    os.makedirs(dirname, exist_ok=True)
    payload = {
        "cached_at": datetime.now(UTC).isoformat(),
        "stack": stack,
        "tooling": data,
    }
    fd, tmp = tempfile.mkstemp(dir=dirname, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except OSError:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


def get_stack_tooling(stack: str, cache_root: str) -> tuple[dict | None, bool]:
    """Return `(tooling_or_None, needs_research)`.

    `needs_research` is `True` for both `"absent"` and `"stale"` states.
    """
    result = read_stack_cache(stack, cache_root)
    needs_research = result["state"] in ("absent", "stale")
    return result["data"], needs_research


__all__ = [
    "STALE_AFTER_DAYS",
    "cache_path",
    "default_cache_root",
    "get_stack_tooling",
    "read_stack_cache",
    "write_stack_cache",
]
