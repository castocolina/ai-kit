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

from .hosts import HOSTS, permission_from_cmdline, session_exists
from .liveness import cross_ai_ancestor, find_host_ancestor, identify, launch_cwd, read_cmdline
from .matrix import best_primitive
from .state import (
    ARM_WINDOW_S,
    PERMISSION_MODE_RE,
    STATE_SCHEMA_VERSION,
    WAKE_CAP,
    Seams,
    SessionPaths,
    read_state,
    session_paths,
    update_state,
    write_json_atomic,
    write_text_atomic,
)
from .units import (
    linger_enabled,
    render_service,
    render_timer,
    service_environment,
    stamp_path,
    systemctl,
    systemd_available,
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


class _ArmRefresh(NamedTuple):
    opts: ArmOptions
    target: "_ArmTarget"
    old_state: dict
    payload: dict


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
    pid_source: str = "flag"


def _refuse(message: str) -> int:
    print(f"ai-kit-session-wake: {message}", file=sys.stderr)
    return 2


def _resolve_pid(opts: ArmOptions, seams: Seams, pid_env: str) -> int | None:
    if opts.pid is not None:
        return opts.pid
    raw = seams.env.get(pid_env, "")
    return int(raw) if raw.isdigit() else None


def _check_interpreter(cli_path: str, env: Mapping[str, str]) -> str | None:
    try:
        with open(cli_path, "rb") as handle:
            first = handle.readline(256).decode("utf-8").strip()
    except (OSError, UnicodeDecodeError):
        return None
    if not first.startswith("#!"):
        return None
    words = first[2:].split()
    if not words:
        return None
    interpreter = words[0]
    name = interpreter
    if os.path.basename(interpreter) == "env":
        args = words[1:]
        if args and args[0] == "-S":
            args = args[1:]
        if not args:
            return None
        name = args[0]
        wake_path = dict(service_environment(env)).get("PATH", "")
        resolved = shutil.which(name, path=wake_path)
    elif os.path.isabs(interpreter):
        resolved = (
            interpreter if os.path.isfile(interpreter) and os.access(interpreter, os.X_OK) else None
        )
    else:
        resolved = shutil.which(interpreter, path=env.get("PATH", ""))
    if resolved is None:
        wake_path = dict(service_environment(env)).get("PATH", "")
        return (
            f"refused: {cli_path} runs through {name}, which the wake's PATH ({wake_path}) "
            "does not resolve; per-shell entries such as fnm_multishells are dropped; "
            f"put {name} on a stable PATH entry and re-run arm"
        )
    return None


def _resolve_target(opts: ArmOptions, seams: Seams) -> _ArmTarget | int:  # pylint: disable=too-many-return-statements
    """Resolve the (host, session id) pair, or return the refusal code."""
    env = seams.env
    marker = env.get("AI_KIT_CROSS_AI_CHILD", "")
    if marker not in ("", "0"):
        return _refuse(
            "refused: this process runs inside a cross-AI runner child "
            "(AI_KIT_CROSS_AI_CHILD); only the orchestrating session arms its wake"
        )
    runner_pid = cross_ai_ancestor(os.getpid(), seams)
    if runner_pid is not None:
        return _refuse(
            f"refused: this process runs inside cross-ai.mjs pid {runner_pid}; "
            "only the orchestrating session arms its wake"
        )
    if not os.path.isdir(seams.proc_root):
        print("ancestor scan unverified off Linux")
    # Ignore CLAUDE_CODE_CHILD_SESSION: Claude Code sets it in every Bash-tool subprocess.
    host = opts.host or detect_current_runtime(env)
    if host == "cursor":
        print("no surviving primitive for cursor")
        return 3
    row = HOSTS.get(host)
    if row is None:
        return _refuse(f"unknown or unsupported host {host!r}; pass --host")
    session_id = opts.session_id or (env.get(row.session_env, "") if row.session_env else "")
    if not session_id and host == "pi":
        return _refuse("no session id: pass --session-id (pi exposes no verified session variable)")
    if not session_id:
        return _refuse(f"no session id: pass --session-id or set {row.session_env}")
    try:
        paths = session_paths(env, host, session_id)
    except ValueError as exc:
        return _refuse(str(exc))
    return _verify_session(opts, seams, host, session_id, paths)


def _verify_cli_session(
    host: str, session_id: str, cwd: str, seams: Seams, cli_path: str
) -> str | None:
    problem = _check_interpreter(cli_path, seams.env)
    status, why = session_exists(host, session_id, cwd, seams)
    if status == "unknown":
        return (
            f"cannot verify session {session_id} ({why}); a resume of a missing id "
            "would create a new session"
        )
    if status != "exists":
        return (
            f"session {session_id} not found ({why}); a resume of a missing id "
            "would create a new session"
        )
    return problem


def _verify_session(  # pylint: disable=too-many-locals
    opts: ArmOptions, seams: Seams, host: str, session_id: str, paths: SessionPaths
) -> _ArmTarget | int:
    """Verify the host process, its launch dir, the CLI and the transcript
    exist; record the explicit permission mode (D-08, D-09, D-21)."""
    env = seams.env
    row = HOSTS[host]
    pid = _resolve_pid(opts, seams, row.pid_env) if row.pid_env else opts.pid
    pid_source = (
        "flag"
        if opts.pid is not None
        else (f"env:{row.pid_env}" if pid is not None and row.pid_env else "")
    )
    if pid is None:
        pid = find_host_ancestor(RUNTIMES[host].binaries, os.getpid(), seams)
        if pid is not None:
            pid_source = "ancestor-unverified"
    if pid is None:
        return _refuse(f"cannot resolve the {host} host process; pass --pid")
    identity = identify(pid, seams)
    if identity is None:
        return _refuse(f"no process {pid} to arm a wake for")
    cwd = launch_cwd(pid, seams)[0]
    cli_path = shutil.which(RUNTIMES[host].binaries[0], path=env.get("PATH", ""))
    if cli_path is None:
        return _refuse(f"the {host} CLI is not on PATH")
    problem = _verify_cli_session(host, session_id, cwd, seams, cli_path)
    if problem:
        return _refuse(problem)
    mode = opts.permission_mode or "unknown"
    source = "flag" if opts.permission_mode else "unknown"
    if not opts.permission_mode:
        argv = read_cmdline(pid, seams)
        mode = permission_from_cmdline(host, argv)
        source = "host-cmdline" if argv else "unknown"
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
        pid_source,
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
        "liveness_source": "proc" if target.boot_id else "ps-unverified",
        "pid_source": target.pid_source,
        "armed_at": now,
        "wake_count": previous["wake_count"] if previous else 0,
        "cap": WAKE_CAP,
        "not_before": now + ARM_WINDOW_S,
        "wake_source": "hourly",
        "reset_evidence": None,
        "reset_at": None,
        "launch_cwd": target.cwd,
        "launch_cwd_verified": True,
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


def _read_text(path: str) -> str | None:
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except FileNotFoundError:
        return None


def _enable_timer(seams: Seams, timer: str, restart: bool = False) -> str | None:
    """Reload units, optionally restart a changed timer, then enable it."""
    reload_proc = systemctl(seams, "daemon-reload")
    if reload_proc.returncode != 0:
        return f"systemctl daemon-reload failed: {reload_proc.stderr.strip()}"
    if restart:
        restart_proc = systemctl(seams, "restart", timer)
        if restart_proc.returncode != 0:
            return f"systemctl restart {timer} failed: {restart_proc.stderr.strip()}"
    enable_proc = systemctl(seams, "enable", "--now", timer)
    if enable_proc.returncode != 0:
        return f"systemctl enable --now {timer} failed: {enable_proc.stderr.strip()}"
    return None


def _refresh_payload(payload: dict, previous: dict, opts: ArmOptions, target: _ArmTarget) -> dict:
    payload.update(
        {
            "armed_at": previous["armed_at"],
            "wake_count": previous["wake_count"],
            "cap": previous["cap"],
            "created": previous["created"],
            "not_before": previous["not_before"],
            "wake_source": previous["wake_source"],
            "reset_evidence": previous["reset_evidence"],
            "reset_at": previous.get("reset_at"),
            "last_resume_exit": previous["last_resume_exit"],
            "permission_mode": target.mode if opts.permission_mode else previous["permission_mode"],
            "permission_source": target.source
            if opts.permission_mode
            else previous["permission_source"],
            "refs": list(dict.fromkeys([*previous["refs"], *payload["refs"]])),
        }
    )
    return payload


def _write_units(
    seams: Seams, target: _ArmTarget, shim_path: str, refreshed: bool
) -> tuple[str, str, bool]:
    env = seams.env
    timer, service = unit_names(target.host, target.session_id)
    ud = unit_dir(env)
    service_path = os.path.join(ud, service)
    timer_path = os.path.join(ud, timer)
    service_text = render_service(sys.executable, shim_path, target.host, target.session_id, env)
    timer_text = render_timer(target.host, target.session_id)
    old_timer_text = _read_text(timer_path)
    if _read_text(service_path) != service_text:
        write_text_atomic(service_path, service_text)
    timer_changed = old_timer_text != timer_text
    if timer_changed:
        write_text_atomic(timer_path, timer_text)
    return timer, service, timer_changed and refreshed


def _report_arm(target: _ArmTarget, payload: dict, refreshed: bool, seams: Seams) -> None:
    print(f"{'refreshed' if refreshed else 'armed'} {target.host}-{target.session_id}")
    for path in payload["created"][:4]:
        print(f"wrote {path}")
    for path in payload["created"][4:]:
        print(f"systemctl creates {path}")
    row = HOSTS[target.host]
    certainty = "verified" if row.verified else "unverified"
    print(f"resume argv: {' '.join(row.resume)} ({certainty}: {row.evidence})")
    if target.pid_source == "ancestor-unverified":
        print(
            f"host pid: {target.pid} (unverified: nearest ancestor matching the "
            f"{target.host} binary)"
        )
    not_applied = (
        ""
        if target.host == "claude"
        else f" (not applied: no verified permission flag for {target.host})"
    )
    if target.mode == "bypassPermissions" and target.source == "host-cmdline":
        print(
            "permission_mode: bypassPermissions (copied from the host command line; "
            "the resume runs with it; pass --permission-mode to change it)"
        )
    elif target.mode == "unknown":
        print(
            "permission_mode: unknown (no flags readable from the host; "
            f"the resume uses the host's default checks){not_applied}"
        )
    else:
        print(f"permission_mode: {target.mode} ({target.source}){not_applied}")
    best = best_primitive(target.host, systemd_ok=True)
    if best is not None:
        print(f"primitive: {best['primitive']} (unverified: {', '.join(best['unverified'])})")
        print(
            "companion: none (the OS timer is the wake; an in-session fire during a usage "
            "limit is lost, spike 004)"
        )
    linger = linger_enabled(seams)
    if linger is False:
        user = seams.env.get("USER") or seams.env.get("LOGNAME") or "<user>"
        print(f"warning: linger is off; the wake stops at logout (loginctl enable-linger {user})")
    elif linger is None:
        print("linger: unknown")


def arm(opts: ArmOptions, seams: Seams, shim_path: str) -> int:
    """Arm (or idempotently refresh) the wake for one session (D-13)."""
    resolved = _resolve_target(opts, seams)
    if isinstance(resolved, int):
        return resolved
    target = resolved
    env = seams.env
    old_state, state_reason = read_state(target.paths.state, target.host, target.session_id)
    if state_reason not in ("ok", "missing"):
        return _refuse(f"invalid state ({state_reason}); run disarm first")
    if not systemd_available(seams):
        fallback = best_primitive(target.host, systemd_ok=False)
        print(f"no surviving primitive for {target.host}")
        if fallback is not None:
            print(
                f"fall back to the in-session primitive {fallback['primitive']} "
                "(survives a stall only; dies with the process)"
            )
            print("warning: the wake will not outlive the session")
        return 3
    payload = _arm_payload(target, seams, env)
    refreshed = old_state is not None
    if refreshed:
        return _refresh_arm(seams, shim_path, _ArmRefresh(opts, target, old_state, payload))
    return _finish_arm(seams, shim_path, target, payload)


def _refresh_arm(seams: Seams, shim_path: str, refresh: _ArmRefresh) -> int:
    payload = _refresh_payload(refresh.payload, refresh.old_state, refresh.opts, refresh.target)

    def apply(current: dict) -> dict:
        payload["wake_count"] = current["wake_count"]
        return payload

    update_state(refresh.target.paths.state, apply)
    return _finish_arm(seams, shim_path, refresh.target, payload, refreshed=True)


def _finish_arm(
    seams: Seams,
    shim_path: str,
    target: _ArmTarget,
    payload: dict,
    refreshed: bool = False,
) -> int:
    if not refreshed:
        write_json_atomic(target.paths.state, payload)
    try:
        lock_fd = os.open(target.paths.lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(lock_fd)
    except FileExistsError:
        pass  # never replace the lock: holders must keep the same inode
    timer, _service, restart = _write_units(seams, target, shim_path, refreshed)
    failure = _enable_timer(seams, timer, restart=restart)
    if failure is not None:
        return _refuse(failure)
    _report_arm(target, payload, refreshed, seams)
    return 0
