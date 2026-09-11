"""Per-stack tooling-recommendation cache with a staleness check (D-04).

Tooling recommendations for a detected stack are never invented from
training data. This module only reads/writes a local, staleness-gated cache
of per-stack tool-name strings; the research pass that FILLS a cold/stale
entry is Plan 02's job. `REQUIRED_STATIC_TARGETS` and `RESEARCH_CATEGORIES`
together are the single canonical schema for every key a `tooling` dict may
legitimately carry -- defined here once, imported (never redefined) by
`makefile_checker.py`.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import tempfile
from datetime import UTC, datetime, timedelta

REQUIRED_STATIC_TARGETS = (
    "setup-env",
    "validate",
    "test",
    "test-unit",
    "test-integration",
    "e2e-test",
    "arch-test",
)

# Tool-category recommendations the D-04 research prompt (Plan 02) asks for
# that do NOT map 1:1 to one of the 7 static target names above.
# `validate-order` and `precommit-vs-prepush-split` are deliberately NOT
# members: both are process/structural facts readable directly from the
# target repo's own files (see makefile_checker.check_validate_order and
# check_precommit_prepush_split), not a tool pick that benefits from
# research -- a category with no research-fillable content would be a
# perpetual, unsatisfiable false positive.
RESEARCH_CATEGORIES = (
    "formatter",
    "security-scanner",
    "code-smell-detector",
    "duplicate-code-detector",
    "dead-code-detector",
)

ALL_TOOLING_KEYS = REQUIRED_STATIC_TARGETS + RESEARCH_CATEGORIES

STALE_AFTER_DAYS = 30

_STACK_ID_RE = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}")


def _default_cache_root() -> str:
    xdg_cache = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    return os.path.join(xdg_cache, "ai-kit", "agents-md-rules-checker", "stack-refs")


CACHE_ROOT = _default_cache_root()


def cache_path(stack: str, cache_root: str | None = None) -> str:
    """Return the cache file path for `stack`, after validating its shape.

    `stack` must be a bare `[a-z0-9][a-z0-9_-]{0,63}` identifier -- no `/`,
    no `.`, no leading `-`/`_`. Raises `ValueError` BEFORE ever joining the
    value into a filesystem path, so a path-traversal-shaped `stack`
    argument can never resolve to a location outside `cache_root`.
    """
    if not isinstance(stack, str) or _STACK_ID_RE.fullmatch(stack) is None:
        raise ValueError(f"invalid stack identifier: {stack!r}")
    root = cache_root or CACHE_ROOT
    return os.path.join(root, f"{stack}.json")


def read_stack_cache(stack: str, cache_root: str | None = None) -> dict:
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
        # A corrupted/unreadable cache file is indistinguishable from no
        # cache at all -- never crash the caller over it (same "never
        # trust a stale entry, never crash" contract as the rest of this
        # module's staleness handling).
        return {"state": "absent", "data": None}
    if not isinstance(payload, dict):
        return {"state": "absent", "data": None}
    cached_at = payload.get("cached_at")
    data = payload.get("tooling")
    try:
        cached_dt = datetime.fromisoformat(cached_at)
    except (TypeError, ValueError):
        return {"state": "stale", "data": data}
    if cached_dt.tzinfo is None:
        cached_dt = cached_dt.replace(tzinfo=UTC)
    age = datetime.now(UTC) - cached_dt
    state = "stale" if age > timedelta(days=STALE_AFTER_DAYS) else "fresh"
    return {"state": state, "data": data}


def write_stack_cache(stack: str, data: dict, cache_root: str | None = None) -> None:
    """Atomically write `{"cached_at": <iso now>, "stack": stack, "tooling": data}`.

    Uses `tempfile.mkstemp` + `os.replace` in the cache dir, the same atomic
    shape `tools/setup.py`'s `_atomic_write_json` already established
    (adapted locally, not imported -- no `tools/`<->`skills/` cross-import).
    """
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


def get_stack_tooling(
    stack: str, cache_root: str | None = None
) -> tuple[dict | None, bool]:
    """Return `(tooling_or_None, needs_research)`.

    `needs_research` is `True` for both `"absent"` and `"stale"` states.
    """
    result = read_stack_cache(stack, cache_root)
    needs_research = result["state"] in ("absent", "stale")
    return result["data"], needs_research
