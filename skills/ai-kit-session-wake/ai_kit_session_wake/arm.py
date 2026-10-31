"""arm (D-13, D-21): record the session, write the persistent timer, enable it.

One arm per (host, session id): a first arm mints a fresh `arm_id`; a refresh
(an existing valid state) keeps it, so a fire can tell a re-armed wake from the
one it started on (review round 2). The lock file is created once with
O_CREAT|O_EXCL and never replaced.
"""

import contextlib
import os
import secrets
import shutil
import sys
from collections.abc import Callable, Mapping
from typing import NamedTuple

from ai_kit_spec.detection import RUNTIMES, detect_current_runtime

from .hosts import HOSTS, permission_from_cmdline, session_exists
from .liveness import cross_ai_ancestor, find_host_ancestor, identify, launch_cwd, read_cmdline
from .matrix import best_primitive
from .reset_parse import RESET_MARGIN_S, calendar_line, iso_z, parse_reset_at, parse_reset_text
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


class ResetArg(NamedTuple):
    """One reset flag (D-30): `kind` is `"text"` or `"at"`, `value` the raw
    flag value."""

    kind: str
    value: str


class ArmOptions(NamedTuple):
    """What the caller (or the CLI) passes to one arm. `only_if_armed` (26-07)
    refreshes an existing wake and refuses to create one."""

    host: str | None
    session_id: str | None
    pid: int | None
    permission_mode: str | None
    refs: tuple[str, ...]
    reset: ResetArg | None = None
    only_if_armed: bool = False


class _ArmRefresh(NamedTuple):
    opts: ArmOptions
    target: "_ArmTarget"
    old_state: dict
    payload: dict


class _SavedUnits(NamedTuple):
    """The unit bytes a refresh is about to replace; the rollback writes them
    back when a systemctl call fails."""

    service: str | None
    timer: str | None


class _FinishPlan(NamedTuple):
    """How one `_finish_arm` ends: a refresh restores the previous wake on a
    failure; a first arm undoes itself (SPEC R3/R6, T-26-41). `rollback`
    receives whether the timer text had changed and returns a description of
    the step that failed, or None."""

    refreshed: bool = False
    rollback: Callable[[bool], str | None] | None = None


# immutable default for _finish_arm (ruff B008: no calls in argument defaults)
_NO_ROLLBACK = _FinishPlan()


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
    if opts.only_if_armed and _not_armed(paths, host, session_id):
        return 0
    return _verify_session(opts, seams, host, session_id, paths)


def _not_armed(paths: SessionPaths, host: str, session_id: str) -> bool:
    """`--only-if-armed` (26-07): print the notice when no state file exists;
    True means the caller returns 0 before any probe."""
    _state, reason = read_state(paths.state, host, session_id)
    if reason != "missing":
        return False
    print("not armed; nothing refreshed")
    return True


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
        # 26-07: a refresh from a hook may not see the host pid; keep the recorded one
        return _recorded_target(opts, seams, host, session_id, paths)
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


def _recorded_target(
    opts: ArmOptions, seams: Seams, host: str, session_id: str, paths: SessionPaths
) -> _ArmTarget | int:
    """The refresh target built from the recorded state (26-07): the host pid,
    its start time, boot id, launch dir and CLI stay as the first arm recorded
    them. The permission mode stays too unless the caller passes one."""
    if not opts.only_if_armed:
        return _refuse(f"cannot resolve the {host} host process; pass --pid")
    state, reason = read_state(paths.state, host, session_id)
    if state is None:
        return _refuse(f"invalid state ({reason}); run disarm first")
    cli_path = shutil.which(RUNTIMES[host].binaries[0], path=seams.env.get("PATH", ""))
    return _ArmTarget(
        host,
        session_id,
        paths,
        int(state["pid"]),
        state["pid_start"],
        state.get("boot_id"),
        state["launch_cwd"],
        cli_path or state.get("cli_path", ""),
        state["permission_mode"],
        state["permission_source"],
        tuple(opts.refs),
        state.get("pid_source", ""),
    )


def _hourly_fields(now: float) -> dict:
    """The four reset-related fields of the plain hourly wake (D-29)."""
    return {
        "not_before": now + ARM_WINDOW_S,
        "wake_source": "hourly",
        "reset_evidence": None,
        "reset_at": None,
    }


def _reset_fields(reset: ResetArg | None, seams: Seams) -> tuple[dict | None, str | None]:
    """The fields an arm applies for the reset flags (D-29, D-30).

    `(None, None)`: no flags, keep whatever exists. `(fields, None)`: an
    accepted reset. `(hourly_fields, reason)`: a refused reset — the hourly
    wake stands (SC 5), and the caller prints the reason."""
    if reset is None:
        return None, None
    now = seams.now()
    result = (
        parse_reset_text(reset.value, now)
        if reset.kind == "text"
        else parse_reset_at(reset.value, now)
    )
    if result.reason is not None:
        return _hourly_fields(now), result.reason
    assert result.at is not None  # a result without a reason always carries one
    not_before = result.at + RESET_MARGIN_S
    return {
        "not_before": not_before,
        "wake_source": "reset_inferred",
        "reset_evidence": result.evidence,
        "reset_at": iso_z(result.at),
    }, None


def _arm_payload(
    target: _ArmTarget, seams: Seams, env: Mapping[str, str], fields: dict | None
) -> dict:
    """The state document (D-07, D-29); `created` lists the six paths arm
    writes or systemd creates, so disarm removes exactly those (D-07).
    `fields` overrides the four reset-related fields (an accepted reset, or
    the hourly fields after a refusal); None means the hourly defaults."""
    now = seams.now()
    timer, service = unit_names(target.host, target.session_id)
    ud = unit_dir(env)
    previous, _reason = read_state(target.paths.state, target.host, target.session_id)
    applied = fields if fields is not None else _hourly_fields(now)
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
        "not_before": applied["not_before"],
        "wake_source": applied["wake_source"],
        "reset_evidence": applied["reset_evidence"],
        "reset_at": applied["reset_at"],
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


def _refresh_payload(
    payload: dict, previous: dict, opts: ArmOptions, target: _ArmTarget, fields: dict | None
) -> dict:
    applied = (
        fields
        if fields is not None
        else {
            # no reset flags: the previous wake's reset fields stand (26-03)
            "not_before": previous["not_before"],
            "wake_source": previous["wake_source"],
            "reset_evidence": previous["reset_evidence"],
            "reset_at": previous.get("reset_at"),
        }
    )
    payload.update(
        {
            "armed_at": previous["armed_at"],
            "wake_count": previous["wake_count"],
            "cap": previous["cap"],
            "created": previous["created"],
            "not_before": applied["not_before"],
            "wake_source": applied["wake_source"],
            "reset_evidence": applied["reset_evidence"],
            "reset_at": applied["reset_at"],
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
    seams: Seams, target: _ArmTarget, shim_path: str, refreshed: bool, payload: dict
) -> tuple[str, str, bool]:
    timer, service = unit_names(target.host, target.session_id)
    ud = unit_dir(seams.env)
    service_path = os.path.join(ud, service)
    timer_path = os.path.join(ud, timer)
    service_text = render_service(
        sys.executable, shim_path, target.host, target.session_id, seams.env
    )
    reset_line = None
    if payload["wake_source"] == "reset_inferred":
        reset_line = calendar_line(payload["not_before"])
    timer_text = render_timer(target.host, target.session_id, reset_line)
    timer_changed = _read_text(timer_path) != timer_text
    if _read_text(service_path) != service_text:
        write_text_atomic(service_path, service_text)
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
    if payload["wake_source"] == "reset_inferred":
        wake_iso = iso_z(payload["not_before"])
        print(
            f"reset: {payload['reset_at']} (inferred); next wake {wake_iso} = "
            "host-reported reset + 60 s margin; the host did not state this wake time"
        )
    if best is not None:
        print(f"primitive: {best['primitive']} (unverified: {', '.join(best['unverified'])})")
        if payload["wake_source"] == "reset_inferred":
            print(
                "companion: create one one-shot in-session wake at "
                f"{iso_z(payload['not_before'])} (inferred); a fire inside the limit is lost "
                "(spike 004)"
            )
        else:
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
    """Arm (or idempotently refresh) the wake for one session (D-13, D-30)."""
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
    fields, refusal = _reset_fields(opts.reset, seams)
    if refusal is not None:
        print(f"reset refused: {refusal}; the hourly wake stands")
    if old_state is None:
        # a `.done` with no state is stale; left in place, the first fire would disarm unresumed
        with contextlib.suppress(FileNotFoundError):
            os.unlink(target.paths.done)
    payload = _arm_payload(target, seams, env, fields)
    refreshed = old_state is not None
    if refreshed:
        return _refresh_arm(seams, shim_path, _ArmRefresh(opts, target, old_state, payload), fields)
    plan = _FinishPlan(rollback=lambda changed: _rollback_first_arm(seams, target))
    return _finish_arm(seams, shim_path, target, payload, plan)


def _rollback_first_arm(seams: Seams, target: _ArmTarget) -> str | None:
    """Undo a failed first arm (SPEC R3/R6): `disable --now` (a partial
    `enable --now`), delete every file this call wrote, `daemon-reload`.
    Best effort; every rollback step that also failed is named."""
    timer, service = unit_names(target.host, target.session_id)
    ud = unit_dir(seams.env)
    failed: list[str] = []
    disable = systemctl(seams, "disable", "--now", timer)
    if disable.returncode != 0:
        failed.append(f"disable --now {timer}")
    for path in (
        target.paths.state,
        target.paths.lock,
        os.path.join(ud, service),
        os.path.join(ud, timer),
        os.path.join(ud, "timers.target.wants", timer),
        stamp_path(seams.env, timer),
    ):
        with contextlib.suppress(FileNotFoundError):
            os.unlink(path)
    reload_proc = systemctl(seams, "daemon-reload")
    if reload_proc.returncode != 0:
        failed.append("daemon-reload")
    if failed:
        return "rollback failed: " + ", ".join(failed)
    return None


def _rollback_refresh(
    seams: Seams, target: _ArmTarget, old_state: dict, saved: _SavedUnits, timer_changed: bool
) -> str | None:
    """Restore the previous wake after a failed refresh (SPEC R3/R6): the
    fields go back through `update_state` (a concurrent fire's count is
    kept), the saved unit bytes are written back, then `daemon-reload` and,
    when the timer text had changed, `restart`. No file of the existing wake
    is ever deleted."""
    timer, service = unit_names(target.host, target.session_id)
    ud = unit_dir(seams.env)
    failed: list[str] = []

    def apply(current: dict) -> dict:
        restored = dict(old_state)
        restored["wake_count"] = current["wake_count"]
        return restored

    try:
        update_state(target.paths.state, apply)
    except (OSError, ValueError):
        failed.append("state restore")
    for name, text in ((service, saved.service), (timer, saved.timer)):
        path = os.path.join(ud, name)
        if text is not None and _read_text(path) != text:
            write_text_atomic(path, text)
    reload_proc = systemctl(seams, "daemon-reload")
    if reload_proc.returncode != 0:
        failed.append("daemon-reload")
    if timer_changed:
        restart_proc = systemctl(seams, "restart", timer)
        if restart_proc.returncode != 0:
            failed.append(f"restart {timer}")
    if failed:
        return "rollback failed: " + ", ".join(failed)
    return None


def _refresh_arm(
    seams: Seams, shim_path: str, refresh: _ArmRefresh, fields: dict | None
) -> int:
    target = refresh.target
    timer, service = unit_names(target.host, target.session_id)
    ud = unit_dir(seams.env)
    saved = _SavedUnits(
        _read_text(os.path.join(ud, service)),
        _read_text(os.path.join(ud, timer)),
    )

    def rollback(changed: bool) -> str | None:
        return _rollback_refresh(seams, target, refresh.old_state, saved, changed)

    payload = _refresh_payload(
        refresh.payload, refresh.old_state, refresh.opts, target, fields
    )

    def apply(current: dict) -> dict:
        payload["wake_count"] = current["wake_count"]
        return payload

    update_state(refresh.target.paths.state, apply)
    plan = _FinishPlan(refreshed=True, rollback=rollback)
    return _finish_arm(seams, shim_path, target, payload, plan)


def _finish_arm(
    seams: Seams,
    shim_path: str,
    target: _ArmTarget,
    payload: dict,
    plan: _FinishPlan = _NO_ROLLBACK,
) -> int:
    if not plan.refreshed:
        write_json_atomic(target.paths.state, payload)
    try:
        lock_fd = os.open(target.paths.lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(lock_fd)
    except FileExistsError:
        pass  # never replace the lock: holders must keep the same inode
    timer, _service, timer_changed = _write_units(seams, target, shim_path, plan.refreshed, payload)
    restart = timer_changed and plan.refreshed
    failure = _enable_timer(seams, timer, restart=restart)
    if failure is not None:
        note = plan.rollback(restart) if plan.rollback is not None else None
        if note is not None:
            return _refuse(f"{failure}; {note}")
        if plan.refreshed:
            return _refuse(f"{failure}; previous wake restored")
        return _refuse(failure)
    _report_arm(target, payload, plan.refreshed, seams)
    return 0
