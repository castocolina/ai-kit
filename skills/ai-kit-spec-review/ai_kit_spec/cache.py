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


def cache_write_bytes(path: str, data: bytes, mode: int | None = None) -> None:
    """Crash-safe atomic binary write (mkstemp in the target dir, optional chmod, os.replace)."""
    parent = os.path.dirname(path)
    os.makedirs(parent, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=parent, suffix=".tmp")
    try:
        if mode is not None:
            os.chmod(tmp, mode)
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            with contextlib.suppress(OSError):
                os.unlink(tmp)
        raise


def _proc_umask() -> int | None:
    try:
        with open("/proc/self/status", encoding="ascii") as f:
            for line in f:
                if line.startswith("Umask:"):
                    return int(line.split()[1], 8)
    except (OSError, ValueError, IndexError):
        return None
    return None


def umask_file_mode() -> int:
    """The mode a plain ``open()`` would give a new file. Linux reports the umask in
    /proc/self/status; elsewhere reading it means setting it for a moment, which a
    concurrently file-creating thread could observe (single-threaded callers only)."""
    umask = _proc_umask()
    if umask is None:
        umask = os.umask(0)
        os.umask(umask)
    return 0o666 & ~umask


def cache_write_text(path: str, text: str, mode: int | None = None) -> None:
    """UTF-8 text wrapper around :func:`cache_write_bytes`."""
    cache_write_bytes(path, text.encode("utf-8"), mode=mode)


def cache_is_stale(path: str, ttl_seconds: int) -> bool:
    try:
        return time.time() - os.stat(path).st_mtime >= ttl_seconds
    except OSError:
        return True
