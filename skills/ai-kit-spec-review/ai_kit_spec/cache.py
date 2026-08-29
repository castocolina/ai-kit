"""Generic JSON cache read/write with TTL staleness, shared by detection.py and quota.py."""
import json
import os
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
    """Atomic write (tmp file + os.replace) so a crash mid-write never leaves a half-written
    cache file for the next reader -- preserved verbatim from the current review-spec.py
    implementation, not simplified away during the move."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def cache_is_stale(path: str, ttl_seconds: int) -> bool:
    try:
        return time.time() - os.stat(path).st_mtime >= ttl_seconds
    except OSError:
        return True
