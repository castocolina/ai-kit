"""Wake state (D-05, D-06, D-07, D-29): seams, session paths, atomic writers,
the one validated reader, and the per-session lock.

Every other module in this package takes its environment and clock from a
`Seams` value -- this is the only module that reads `os.environ` or calls
`time.time`, so tests steer the whole package through one scratch env and one
fixed clock (D-26).
"""

import contextlib
import fcntl
import json
import os
import re
import tempfile
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import NamedTuple

STATE_SCHEMA_VERSION = 1
WAKE_CAP = 24
ARM_WINDOW_S = 60
SESSION_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
PERMISSION_MODE_RE = re.compile(r"^[A-Za-z]{1,32}$")
_ARM_ID_RE = re.compile(r"^[0-9a-f]{16}$")


@dataclass(frozen=True)
class Seams:
    """The process seams: environment, clock and proc root.

    Every subprocess in the package gets `env=seams.env`, every PATH lookup is
    `shutil.which(name, path=seams.env.get("PATH", ""))` (so `run` and `which`
    need no seam of their own), every wall-clock read goes through `now()`,
    and every /proc read through `proc_root`.
    """

    env: Mapping[str, str]
    now: Callable[[], float] = time.time
    proc_root: str = "/proc"


def default_seams() -> Seams:
    """Seams bound to this process's real environment and clock."""
    return Seams(env=dict(os.environ))


class SessionPaths(NamedTuple):
    """The three per-session state files (D-05)."""

    state: str
    lock: str
    done: str


def state_dir(env: Mapping[str, str]) -> str:
    """`${XDG_STATE_HOME:-$HOME/.local/state}/ai-kit/session-wake` (D-05)."""
    base = env.get("XDG_STATE_HOME") or os.path.join(env.get("HOME", ""), ".local", "state")
    return os.path.join(base, "ai-kit", "session-wake")


def session_paths(env: Mapping[str, str], host: str, session_id: str) -> SessionPaths:
    """Paths for one (host, session id) pair; raises ValueError naming the id
    when it fails the safe charset, before it ever reaches a path (T-26-03)."""
    if not isinstance(session_id, str) or SESSION_ID_RE.fullmatch(session_id) is None:
        raise ValueError(
            f"refused session id {session_id!r}: only letters, digits, '_' and '-', "
            "1 to 128 characters"
        )
    stem = os.path.join(state_dir(env), f"{host}-{session_id}")
    return SessionPaths(f"{stem}.json", f"{stem}.lock", f"{stem}.done")


def _atomic_write(path: str, payload: bytes) -> None:
    """mkstemp in the target dir, write, fsync, `os.replace`; tmp removed on
    error; the directory created 0700 (D-06, the stack_cache body)."""
    dirname = os.path.dirname(path)
    os.makedirs(dirname, mode=0o700, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=dirname, suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except OSError:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


def write_json_atomic(path: str, payload: dict) -> None:
    """Atomically write one JSON object with a trailing newline."""
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    _atomic_write(path, text.encode("utf-8"))


def write_text_atomic(path: str, text: str) -> None:
    """Atomically write one text file (the unit files)."""
    _atomic_write(path, text.encode("utf-8"))


def touch_marker(path: str) -> None:
    """Atomically create (or re-create) an empty marker file."""
    _atomic_write(path, b"")


def _read_raw_json(fd: int) -> dict:
    """The module's only unvalidated reader: parse the file behind `fd`.

    Callers validate through `read_state`/`validate_state`; `update_state`
    uses this because the caller validates before and inside its callback.
    """
    os.lseek(fd, 0, os.SEEK_SET)
    chunks = []
    while True:
        chunk = os.read(fd, 65536)
        if not chunk:
            break
        chunks.append(chunk)
    payload = json.loads(b"".join(chunks).decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("state file is not a JSON object")
    return payload


def update_state(path: str, fn: Callable[[dict], dict | None]) -> dict:
    """Serialized read-modify-write of one state file.

    Opens the file, takes an exclusive flock, re-checks that the open inode is
    still the one `path` names (retries when a concurrent writer replaced it),
    reads through `_read_raw_json`, applies `fn` -- a None result writes
    nothing -- and writes the result back atomically while still holding the
    lock. Returns the effective payload (the applied result, or the current
    payload when `fn` declined to write). Callers validate first.
    """
    while True:
        fd = os.open(path, os.O_RDWR)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            try:
                if os.fstat(fd).st_ino != os.stat(path).st_ino:
                    continue
                payload = _read_raw_json(fd)
                result = fn(payload)
                if result is not None:
                    write_json_atomic(path, result)
                return result if result is not None else payload
            finally:
                fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


def _count_int(value: object) -> bool:
    """A real integer: json's only `int` subclass is bool, so `true` must
    never pass as a count (the plan's `type(x) is int` contract)."""
    return isinstance(value, int) and not isinstance(value, bool)


def _identity_problem(payload: dict, host: str, session_id: str) -> str | None:
    if payload.get("schema_version") != STATE_SCHEMA_VERSION:
        return f"unsupported schema_version {payload.get('schema_version')!r}"
    mismatches = [
        name
        for name, expected in (("host", host), ("session_id", session_id))
        if payload.get(name) != expected
    ]
    if mismatches:
        return f"state {' and '.join(mismatches)} is not this wake's"
    arm_id = payload.get("arm_id")
    if not isinstance(arm_id, str) or _ARM_ID_RE.fullmatch(arm_id) is None:
        return "arm_id is not 16 lowercase hex characters"
    return None


def _counters_problem(payload: dict) -> str | None:
    if not _count_int(payload.get("pid")) or payload["pid"] <= 0:
        return "pid is not a positive integer"
    if not _count_int(payload.get("wake_count")) or payload["wake_count"] < 0:
        return "wake_count is not a non-negative integer"
    cap = payload.get("cap")
    if not isinstance(cap, int) or isinstance(cap, bool) or not 1 <= cap <= WAKE_CAP:
        return f"cap is not an integer in 1..{WAKE_CAP}"
    return None


def _paths_problem(payload: dict) -> str | None:
    for key in ("launch_cwd", "cli_path"):
        value = payload.get(key)
        if not isinstance(value, str) or not value.startswith("/"):
            return f"{key} is not an absolute path"
    for key in ("created", "refs"):
        value = payload.get(key)
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            return f"{key} is not a list of strings"
    return None


def _scalars_problem(payload: dict) -> str | None:
    if not isinstance(payload.get("not_before"), (int, float)) or isinstance(
        payload.get("not_before"), bool
    ):
        return "not_before is not a number"
    mode = payload.get("permission_mode")
    if not isinstance(mode, str) or PERMISSION_MODE_RE.fullmatch(mode) is None:
        return "permission_mode is not 1..32 letters"
    last_exit = payload.get("last_resume_exit")
    if last_exit is not None and not _count_int(last_exit):
        return "last_resume_exit is not an integer or null"
    return None


def _record_problem(payload: dict) -> str | None:
    """The fields fire and a refresh index directly: a missing one must be a
    reason, never a KeyError or a dead host that reads as alive."""
    for key in ("pid_start", "wake_source", "permission_source"):
        if not isinstance(payload.get(key), str) or not payload[key]:
            return f"{key} is not a non-empty string"
    boot_id = payload.get("boot_id", False)
    if boot_id is not None and not (isinstance(boot_id, str) and boot_id):
        return "boot_id is not a string or null"
    armed_at = payload.get("armed_at")
    if not isinstance(armed_at, (int, float)) or isinstance(armed_at, bool):
        return "armed_at is not a number"
    return None


def validate_state(payload: object, host: str, session_id: str) -> str | None:
    """Return None when `payload` is a valid wake state named for this
    (host, session id), else a one-line reason (T-26-40)."""
    if not isinstance(payload, dict):
        return "state is not a JSON object"
    for problem in (
        _identity_problem(payload, host, session_id),
        _counters_problem(payload),
        _paths_problem(payload),
        _scalars_problem(payload),
        _record_problem(payload),
    ):
        if problem is not None:
            return problem
    return None


def read_state(path: str, host: str, session_id: str) -> tuple[dict | None, str]:
    """The one validated reader: `(state, "ok")`, `(None, "missing")` when the
    file is absent, or `(None, <reason>)` for anything invalid."""
    try:
        with open(path, encoding="utf-8") as handle:
            payload = json.load(handle)
    except FileNotFoundError:
        return None, "missing"
    except UnicodeDecodeError as exc:
        return None, f"state is not UTF-8: {exc}"
    except json.JSONDecodeError as exc:
        return None, f"invalid JSON: {exc}"
    except OSError as exc:
        return None, f"unreadable: {exc}"
    reason = validate_state(payload, host, session_id)
    if reason is not None:
        return None, reason
    return payload, "ok"


def lock_session(paths: SessionPaths, blocking: bool) -> int | None:
    """Take the exclusive flock on the `.lock` file's CURRENT inode.

    Opens the existing lock (never creates it; missing -> None), flocks it
    (plus LOCK_NB when not blocking), then requires that the locked inode is
    still the one `paths.lock` names: a replaced inode closes the fd and
    retries when blocking, or returns None when not, so no process ever holds
    a stale inode. The caller owns the returned fd (close to release).
    """
    while True:
        try:
            fd = os.open(paths.lock, os.O_RDONLY)
        except FileNotFoundError:
            return None
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))
        except OSError:
            os.close(fd)
            return None
        try:
            if os.fstat(fd).st_ino == os.stat(paths.lock).st_ino:
                return fd
        except FileNotFoundError:
            os.close(fd)
            return None
        os.close(fd)
        if not blocking:
            return None
