"""Generic JSON cache read/write with TTL staleness, shared by detection.py and quota.py."""
import contextlib
import json
import os
import tempfile
import time


def cache_base(env: dict) -> str:
    xdg = env.get("XDG_CACHE_HOME")
    base = xdg if xdg else os.path.join(env.get("HOME", ""), ".cache")
    return os.path.join(base, "ai-kit", "spec")


def cache_read_json(path: str) -> dict | None:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def cache_write_json(path: str, data: dict) -> None:
    cache_write_text(path, json.dumps(data, indent=2))


def cache_write_text(path: str, text: str) -> None:
    """Crash-safe atomic write: each writer gets its own mkstemp temp file (unique name,
    mode 0600) in the target directory, then os.replace moves it over the target, so two
    concurrent sessions writing the same cache or trust record never collide on a shared
    temp name and a crash mid-write never leaves a half-written cache file behind."""
    parent = os.path.dirname(path)
    os.makedirs(parent, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            with contextlib.suppress(OSError):
                os.unlink(tmp)
        raise


def cache_is_stale(path: str, ttl_seconds: int) -> bool:
    try:
        return time.time() - os.stat(path).st_mtime >= ttl_seconds
    except OSError:
        return True
