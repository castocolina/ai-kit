"""arm (D-13, D-21): record the session, write the persistent timer, enable it.

One arm per (host, session id): a first arm mints a fresh `arm_id`; a refresh
(an existing valid state) keeps it, so a fire can tell a re-armed wake from the
one it started on (review round 2). The lock file is created once with
O_CREAT|O_EXCL and never replaced.
"""
import os
import secrets
import shutil
import sys
from collections.abc import Mapping
from typing import NamedTuple

from ai_kit_spec.detection import RUNTIMES, detect_current_runtime

from .hosts import HOSTS, session_exists
from .liveness import identify, launch_cwd
from .state import (
    ARM_WINDOW_S,
    PERMISSION_MODE_RE,
    STATE_SCHEMA_VERSION,
    WAKE_CAP,
    Seams,
    SessionPaths,
    read_state,
    session_paths,
    write_json_atomic,
    write_text_atomic,
)
from .units import (
    render_service,
    render_timer,
    stamp_path,
    systemctl,
    unit_dir,
    unit_names,
)


class ArmOptions(NamedTuple):
    """What the caller (or the CLI) passes to one arm."""

    host: str | None
    session_id: str | None
    pid: int | None
    permission_mode: str | None
    refs: tuple[str, ...]


class _ArmTarget(NamedTuple):
    """Everything arm resolved before touching the disk."""

    host: str
    session_id: str
    paths: SessionPaths
    pid: int
    pid_start: str
    boot_id: str | None
    cwd: str
    cli_path: str
    mode: str
    source: str
    refs: tuple[str, ...]


def _refuse(message: str) -> int:
    print(f"ai-kit-session-wake: {message}", file=sys.stderr)
    return 2


def _resolve_pid(opts: ArmOptions, seams: Seams, pid_env: str) -> int | None:
    if opts.pid is not None:
        return opts.pid
    raw = seams.env.get(pid_env, "")
    return int(raw) if raw.isdigit() else None


def _resolve_target(opts: ArmOptions, seams: Seams) -> _ArmTarget | int:
    """Resolve the (host, session id) pair, or return the refusal code."""
    env = seams.env
    host = opts.host or detect_current_runtime(env)
    row = HOSTS.get(host)
    if row is None:
        return _refuse(f"unknown or unsupported host {host!r}; pass --host")
    session_id = opts.session_id or env.get(row.session_env, "")
    if not session_id:
        return _refuse(f"no session id: pass --session-id or set {row.session_env}")
    try:
        paths = session_paths(env, host, session_id)
    except ValueError as exc:
        return _refuse(str(exc))
    return _verify_session(opts, seams, host, session_id, paths)


def _verify_session(
    opts: ArmOptions, seams: Seams, host: str, session_id: str, paths: SessionPaths
) -> _ArmTarget | int:
    """Verify the host process, its launch dir, the CLI and the transcript
    exist; record the explicit permission mode (D-08, D-09, D-21)."""
    env = seams.env
    pid = _resolve_pid(opts, seams, HOSTS[host].pid_env)
    if pid is None:
        return _refuse("cannot resolve the host process; pass --pid")
    identity = identify(pid, seams)
    if identity is None:
        return _refuse(f"no process {pid} to arm a wake for")
    cwd = launch_cwd(pid, seams)[0]
    cli_path = shutil.which(RUNTIMES[host].binaries[0], path=env.get("PATH", ""))
    if cli_path is None:
        return _refuse(f"the {host} CLI is not on PATH")
    status, why = session_exists(host, session_id, cwd, seams)
    if status != "exists":
        return _refuse(f"session {session_id} not found ({why})")
    mode = opts.permission_mode or "unknown"
    source = "flag" if opts.permission_mode else "unknown"
    if PERMISSION_MODE_RE.fullmatch(mode) is None:
        return _refuse(f"invalid permission mode {mode!r} (1..32 letters)")
    return _ArmTarget(
        host,
        session_id,
        paths,
        pid,
        identity.start,
        identity.boot_id,
        cwd,
        cli_path,
        mode,
        source,
        tuple(opts.refs),
    )


def _arm_payload(target: _ArmTarget, seams: Seams, env: Mapping[str, str]) -> dict:
    """The state document (D-07, D-29); `created` lists the six paths arm
    writes or systemd creates, so disarm removes exactly those (D-07)."""
    now = seams.now()
    timer, service = unit_names(target.host, target.session_id)
    ud = unit_dir(env)
    previous, _reason = read_state(target.paths.state, target.host, target.session_id)
    return {
        "schema_version": STATE_SCHEMA_VERSION,
        "host": target.host,
        "session_id": target.session_id,
        "arm_id": previous["arm_id"] if previous else secrets.token_hex(8),
        "pid": target.pid,
        "pid_start": target.pid_start,
        "boot_id": target.boot_id,
        "armed_at": now,
        "wake_count": previous["wake_count"] if previous else 0,
        "cap": WAKE_CAP,
        "not_before": now + ARM_WINDOW_S,
        "wake_source": "hourly",
        "reset_evidence": None,
        "reset_at": None,
        "launch_cwd": target.cwd,
        "cli_path": target.cli_path,
        "permission_mode": target.mode,
        "permission_source": target.source,
        "backend": "systemd-user",
        "refs": [os.path.abspath(ref) for ref in target.refs],
        "created": [
            target.paths.state,
            target.paths.lock,
            os.path.join(ud, service),
            os.path.join(ud, timer),
            os.path.join(ud, "timers.target.wants", timer),
            stamp_path(env, timer),
        ],
        "last_resume_exit": previous["last_resume_exit"] if previous else None,
    }


def _enable_timer(seams: Seams, timer: str) -> str | None:
    """daemon-reload, then enable --now; the first failure is returned as a
    message naming the verb and stderr (26-06 Task 3 adds the rollback)."""
    reload_proc = systemctl(seams, "daemon-reload")
    if reload_proc.returncode != 0:
        return f"systemctl daemon-reload failed: {reload_proc.stderr.strip()}"
    enable_proc = systemctl(seams, "enable", "--now", timer)
    if enable_proc.returncode != 0:
        return f"systemctl enable --now {timer} failed: {enable_proc.stderr.strip()}"
    return None


def arm(opts: ArmOptions, seams: Seams, shim_path: str) -> int:
    """Arm (or idempotently refresh) the wake for one session (D-13)."""
    resolved = _resolve_target(opts, seams)
    if isinstance(resolved, int):
        return resolved
    target = resolved
    env = seams.env
    payload = _arm_payload(target, seams, env)
    write_json_atomic(target.paths.state, payload)
    try:
        lock_fd = os.open(target.paths.lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(lock_fd)
    except FileExistsError:
        pass  # never replace the lock: holders must keep the same inode
    timer, service = unit_names(target.host, target.session_id)
    ud = unit_dir(env)
    service_text = render_service(
        sys.executable, shim_path, target.host, target.session_id, env
    )
    write_text_atomic(os.path.join(ud, service), service_text)
    write_text_atomic(os.path.join(ud, timer), render_timer(target.host, target.session_id))
    failure = _enable_timer(seams, timer)
    if failure is not None:
        return _refuse(failure)
    print(f"armed {target.host}-{target.session_id}")
    for path in payload["created"][:4]:
        print(f"wrote {path}")
    for path in payload["created"][4:]:
        print(f"systemctl creates {path}")
    print(f"permission_mode: {target.mode} ({target.source})")
    return 0
