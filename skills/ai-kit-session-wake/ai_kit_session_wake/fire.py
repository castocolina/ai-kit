"""One timer wake: the final D-10 order, written once (D-10, D-11, D-29,
D-31; later plans add tests, host rows and the desktop notice, never a
reorder). Disarm lives here because `fire` removes its own wake while holding
the session lock, and must never `stop` its own service (D-13).
"""
import contextlib
import fcntl
import os
import shutil
import signal
import subprocess
from datetime import UTC, datetime
from typing import NamedTuple

from .hosts import FIRE_MARKER_ENV, child_env, resume_argv, session_exists
from .liveness import is_alive
from .state import (
    WAKE_CAP,
    Seams,
    SessionPaths,
    lock_session,
    read_state,
    session_paths,
    touch_marker,
    update_state,
)
from .units import stamp_path, systemctl, unit_dir, unit_names

RESUME_PROMPT = (
    "ai-kit session wake: this session stalled and its wake timer resumed it. "
    "Read the wake state at {state_path} and every state file listed in its refs, "
    "including pending cross-AI waits. Continue only unfinished work. Continue a pending "
    "cross-AI hard-tier wait from its own state file (cycle, due_at); never restart it at "
    "cycle 0, and never switch harness, provider or model. Re-run the ai-kit-session-wake "
    "skill's arm to refresh this session's wake. When nothing remains, run its done."
)
RESUME_TIMEOUT_S = 14400
NOTIFY_TIMEOUT_S = 5
NOTIFY_SUMMARY = "ai-kit session wake gave up"


class _Wake(NamedTuple):
    """One fire's fixed identity."""

    host: str
    session_id: str
    tag: str
    paths: SessionPaths
    seams: Seams


class _Count(NamedTuple):
    """What step (4)'s counted increment decided."""

    kind: str  # counted | abandon | early | gone
    n: int = 0
    not_before: float = 0.0
    state: dict | None = None


def _log(tag: str, event: str) -> None:
    print(f"ai-kit-session-wake: {tag} {event}")


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=UTC).isoformat()


def _wake(host: str, session_id: str, seams: Seams) -> _Wake:
    return _Wake(
        host, session_id, f"{host}-{session_id}", session_paths(seams.env, host, session_id), seams
    )


# ── teardown ────────────────────────────────────────────────────────────────


def _teardown(seams: Seams, timer: str, delete: list[str], foreign: list[str]) -> None:
    """disable --now, clean --what=state, delete the named paths (lock last is
    the caller's job), daemon-reload; never `stop` on the service (D-13)."""
    for path in foreign:
        print(f"skipped foreign path {path}")
    disable = systemctl(seams, "disable", "--now", timer)
    if disable.returncode != 0:
        _log(timer, f"systemctl disable --now failed: {disable.stderr.strip()}")
    clean = systemctl(seams, "clean", "--what=state", timer)
    if clean.returncode != 0:
        _log(timer, f"systemctl clean --what=state failed: {clean.stderr.strip()}")
    for path in delete:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(path)
            print(f"removed {path}")
    systemctl(seams, "daemon-reload")


def owned_path(path: str, host: str, session_id: str, seams: Seams) -> bool:
    """True only when `path` equals one of the wake's seven own absolute paths,
    derived from the seams env and (host, id): the state, lock and done files,
    the timer and service, the wants link and the stamp. A same-named file in
    any other folder is foreign and survives (review round 2, T-26-40)."""
    env = seams.env
    paths = session_paths(env, host, session_id)
    timer, service = unit_names(host, session_id)
    ud = unit_dir(env)
    owned = (
        os.path.abspath(paths.state),
        os.path.abspath(paths.lock),
        os.path.abspath(paths.done),
        os.path.join(ud, timer),
        os.path.join(ud, service),
        os.path.join(ud, "timers.target.wants", timer),
        stamp_path(env, timer),
    )
    return os.path.abspath(path) in owned


def _split_created(state: dict, host: str, session_id: str, seams: Seams) -> tuple[list, list]:
    created = state["created"]
    owned = [p for p in created if owned_path(p, host, session_id, seams)]
    foreign = [p for p in created if not owned_path(p, host, session_id, seams)]
    return owned, foreign


def _remove_owned(
    paths: SessionPaths, state: dict, host: str, session_id: str, seams: Seams
) -> None:
    owned, foreign = _split_created(state, host, session_id, seams)
    owned += [paths.done, paths.state, paths.lock]
    timer, _service = unit_names(host, session_id)
    _teardown(seams, timer, owned, foreign)


def notify(seams: Seams, summary: str, body: str) -> None:
    """The best-effort desktop notice (D-31, D-32): `notify-send <summary>
    <body>` only when notify-send is on the seams PATH and a session bus is
    reachable (DBUS_SESSION_BUS_ADDRESS, or <XDG_RUNTIME_DIR>/bus), bounded by
    NOTIFY_TIMEOUT_S. Every error is ignored; without a login session the
    journal line is the record (D-31)."""
    exe = shutil.which("notify-send", path=seams.env.get("PATH", ""))
    if exe is None:
        return
    env = seams.env
    runtime_dir = env.get("XDG_RUNTIME_DIR", "")
    bus_file = os.path.join(runtime_dir, "bus") if runtime_dir else ""
    if not env.get("DBUS_SESSION_BUS_ADDRESS") and not (bus_file and os.path.exists(bus_file)):
        return
    with contextlib.suppress(OSError, subprocess.TimeoutExpired):
        subprocess.run(
            [exe, summary, body],
            capture_output=True,
            env=dict(env),
            timeout=NOTIFY_TIMEOUT_S,
            check=False,
        )


def give_up(host: str, session_id: str, reason: str, seams: Seams) -> None:
    """The give-up notice (the journal line, then the bounded desktop
    notice; D-31, D-32), then the removal. Runs only under the lock and
    removes the state, so a wake gives up once."""
    wake = _wake(host, session_id, seams)
    state, _reason = read_state(wake.paths.state, host, session_id)
    last_exit = state["last_resume_exit"] if state else None
    body = f"{reason}; state {wake.paths.state}; last resume exit {last_exit}"
    print(f"ai-kit-session-wake: NOTICE ai-kit session wake gave up: {body}")
    notify(seams, NOTIFY_SUMMARY, body)
    if state is None:
        disarm_by_name(host, session_id, seams)
        return
    _remove_owned(wake.paths, state, host, session_id, seams)


def disarm_by_name(host: str, session_id: str, seams: Seams) -> int:
    """Remove the wake derived from (host, id) alone: the only route when no
    valid state says what was created (T-26-40: an invalid state is removed by
    name only)."""
    wake = _wake(host, session_id, seams)
    timer, service = unit_names(host, session_id)
    ud = unit_dir(seams.env)
    derived = [
        wake.paths.state,
        wake.paths.lock,
        wake.paths.done,
        os.path.join(ud, timer),
        os.path.join(ud, service),
        os.path.join(ud, "timers.target.wants", timer),
        stamp_path(seams.env, timer),
    ]
    _teardown(seams, timer, derived, [])
    return 0


def _disarm_locked(wake: _Wake) -> int:
    """The 26-02 removal with the nothing-armed empty edge (SPEC R5)."""
    state, reason = read_state(wake.paths.state, wake.host, wake.session_id)
    timer, _service = unit_names(wake.host, wake.session_id)
    unit_file = os.path.join(unit_dir(wake.seams.env), timer)
    if state is None:
        if reason == "missing" and not os.path.exists(unit_file):
            print("nothing to disarm")
            return 0
        return disarm_by_name(wake.host, wake.session_id, wake.seams)
    _remove_owned(wake.paths, state, wake.host, wake.session_id, wake.seams)
    return 0


def disarm(host: str, session_id: str, seams: Seams) -> int:
    """Full cleanup (D-13, SPEC R5 concurrency): inside a fire child write
    `.done` and stop there (D-02), instead of waiting on its own parent's
    lock; otherwise take the session lock blocking -- a running resume
    finishes first -- then remove everything. A lock file that vanished
    meanwhile means another disarm finished: re-read and report what is
    left."""
    wake = _wake(host, session_id, seams)
    if seams.env.get(FIRE_MARKER_ENV) == f"{host}-{session_id}":
        touch_marker(wake.paths.done)
        print(
            f"{wake.paths.done} written; the running wake removes everything "
            "when its resume exits"
        )
        return 0
    fd = lock_session(wake.paths, blocking=True)
    if fd is not None:
        try:
            return _disarm_locked(wake)
        finally:
            os.close(fd)
    return _disarm_locked(wake)


def done(host: str, session_id: str, seams: Seams) -> int:
    """Write the `.done` marker; inside a fire child stop there (the resume's
    own finish step disarms, D-10 step 7); when no resume holds the lock,
    disarm at once; when one does, say so and let it disarm on exit."""
    wake = _wake(host, session_id, seams)
    touch_marker(wake.paths.done)
    print(wake.paths.done)
    if seams.env.get(FIRE_MARKER_ENV) == f"{host}-{session_id}":
        return 0
    fd = lock_session(wake.paths, blocking=False)
    if fd is None:
        print("a wake resume is running; it disarms when the resume exits")
        return 0
    try:
        state, _reason = read_state(wake.paths.state, host, session_id)
        if state is None:
            return disarm_by_name(host, session_id, seams)
        _remove_owned(wake.paths, state, host, session_id, seams)
        return 0
    finally:
        os.close(fd)


# ── the fire ────────────────────────────────────────────────────────────────


def _count_wake(wake: _Wake, arm_id: str) -> _Count:
    """Step (4): increment `wake_count` under the state lock only while the
    `arm_id` step (1) read and `now >= not_before` still hold; anything else
    writes nothing (review round 3)."""
    outcome = _Count("gone")

    def _apply(current: dict) -> dict | None:
        nonlocal outcome
        if current.get("arm_id") != arm_id:
            outcome = _Count("abandon", state=current)
            return None
        if wake.seams.now() < current.get("not_before", 0):
            outcome = _Count("early", not_before=current["not_before"], state=current)
            return None
        current["wake_count"] = int(current.get("wake_count", 0)) + 1
        outcome = _Count("counted", n=current["wake_count"], state=current)
        return current

    with contextlib.suppress(FileNotFoundError, NotADirectoryError):
        update_state(wake.paths.state, _apply)
    return outcome


def _recheck(wake: _Wake, arm_id: str) -> tuple[str, dict | None]:
    """Steps (7)/(9): the state, `arm_id`, `not_before`, `.done` and liveness,
    re-tested under the session lock (review rounds 1 and 2)."""
    state, _reason = read_state(wake.paths.state, wake.host, wake.session_id)
    if state is None:
        return "gone", None
    if state["arm_id"] != arm_id:
        return "abandon", state
    if wake.seams.now() < state["not_before"]:
        return "early", state
    if os.path.exists(wake.paths.done):
        return "done", state
    if is_alive(state, wake.seams):
        return "alive", state
    return "ok", state


def _stop_for(wake: _Wake, verdict: str, state: dict, n: int, fd: int) -> int | None:
    """Everything a re-check can decide short of resuming; None means go on."""
    if verdict == "abandon":
        os.close(fd)
        _log(wake.tag, "wake re-armed since this fire began; not resuming this wake")
        return 0
    if verdict == "early":
        os.close(fd)
        _log(wake.tag, f"not resuming this wake: not before {_iso(state['not_before'])}")
        return _finish(wake, f"wake {n}/{state['cap']}")
    if verdict == "done":
        return _finish(wake, "done marker present", fd=fd)
    if verdict == "alive":
        _log(wake.tag, f"host alive; log only (wake {n}/{state['cap']})")
        return _finish(wake, f"wake {n}/{state['cap']}", fd=fd)
    return None


def _store_exit(wake: _Wake, arm_id: str, code: int) -> None:
    def _apply(current: dict) -> dict | None:
        if current.get("arm_id") != arm_id:
            return None  # a re-arm owns the state now; leave its record alone
        current["last_resume_exit"] = code
        return current

    with contextlib.suppress(FileNotFoundError, NotADirectoryError):
        update_state(wake.paths.state, _apply)


def _kill_group(proc: subprocess.Popen) -> None:
    """SIGTERM the resume's process group, then SIGKILL after 10 s."""
    with contextlib.suppress(OSError, ProcessLookupError):
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        with contextlib.suppress(OSError, ProcessLookupError):
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        proc.wait()


def _spawn(wake: _Wake, state: dict, fd: int) -> int:
    """Step (9)'s one resume: exact argv (D-03, D-15), the launch directory,
    stdin from /dev/null, the scrubbed child env, its own session (D-09,
    D-15; spike 001, RESEARCH Pitfall 6)."""
    prompt = RESUME_PROMPT.format(state_path=wake.paths.state)
    argv = resume_argv(state, prompt)
    try:
        # Deliberately not a `with`: the resume child may outlive the fire's
        # own pipes and is waited explicitly below (D-10 step 6).
        proc = subprocess.Popen(  # pylint: disable=consider-using-with
            argv,
            cwd=state["launch_cwd"],
            stdin=subprocess.DEVNULL,
            env=child_env(wake.seams.env, wake.host, wake.session_id),
            start_new_session=True,
        )
    except OSError as exc:
        _log(wake.tag, f"resume could not start: {exc}")
        _store_exit(wake, state["arm_id"], 127)
        return _finish(wake, "resume could not start", fd=fd)
    try:
        code = proc.wait(timeout=RESUME_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        _kill_group(proc)
        code = 124
    _store_exit(wake, state["arm_id"], code)
    _log(wake.tag, f"resume exit {code}")
    return _finish(wake, f"resume exit {code}", fd=fd)


def _under_lock(wake: _Wake, arm_id: str, n: int, fd: int) -> int:
    """Steps (7)-(9) holding the session lock: the re-check runs twice, once
    before and once after the session probe (the probe can take 30 s)."""
    for probe_pass in range(2):
        verdict, state = _recheck(wake, arm_id)
        if state is None:
            os.close(fd)
            _log(wake.tag, "no valid wake state under the lock; nothing to resume")
            return 0
        stop = _stop_for(wake, verdict, state, n, fd)
        if stop is not None:
            return stop
        if probe_pass == 1:
            continue
        status, why = session_exists(
            wake.host, wake.session_id, state["launch_cwd"], wake.seams
        )
        if status == "missing":
            give_up(
                wake.host, wake.session_id, f"session {wake.session_id} not found", wake.seams
            )
            os.close(fd)
            return 0
        if status == "unknown":
            _log(wake.tag, f"cannot check the session ({why}); not resuming this wake")
            return _finish(wake, f"wake {n}/{state['cap']}", fd=fd)
    return _spawn(wake, state, fd)


def _resume(wake: _Wake, arm_id: str, n: int) -> int:
    """Steps (5)-(9): liveness, then the non-blocking session lock."""
    state, _reason = read_state(wake.paths.state, wake.host, wake.session_id)
    if state is None:
        return 0
    if is_alive(state, wake.seams):
        _log(wake.tag, f"host alive; log only (wake {n}/{state['cap']})")
        return _finish(wake, f"wake {n}/{state['cap']}")
    fd = lock_session(wake.paths, blocking=False)
    if fd is None:
        _log(
            wake.tag,
            "a resume is already running, or the wake was disarmed or re-armed; "
            "not resuming this wake",
        )
        return 0
    return _under_lock(wake, arm_id, n, fd)


def _finish(wake: _Wake, event: str, fd: int | None = None) -> int:
    """The one cap step every exit after (4) takes (review round 1): take the
    lock unless held, re-read, then `.done` -> the removal; count at or above
    the cap -> give up; else stay armed."""
    if fd is None:
        fd = lock_session(wake.paths, blocking=False)
        if fd is None:
            _log(wake.tag, "another wake process holds the lock; it finishes this wake")
            return 0
    state, _reason = read_state(wake.paths.state, wake.host, wake.session_id)
    if state is None:
        os.close(fd)
        return 0
    if os.path.exists(wake.paths.done):
        _remove_owned(wake.paths, state, wake.host, wake.session_id, wake.seams)
        os.close(fd)
        return 0
    if state["wake_count"] >= state["cap"]:
        give_up(
            wake.host,
            wake.session_id,
            f"cap {state['cap']} reached; last wake: {event}",
            wake.seams,
        )
        os.close(fd)
        return 0
    with contextlib.suppress(OSError):
        fcntl.flock(fd, fcntl.LOCK_UN)
    os.close(fd)
    return 0


def fire(host: str, session_id: str, seams: Seams) -> int:
    """One wake, in the final D-10 order (D-10; 26-CONTEXT)."""
    wake = _wake(host, session_id, seams)
    state, reason = read_state(wake.paths.state, host, session_id)
    if state is None:
        if reason == "missing":
            _log(wake.tag, "no wake state; disarming by name")
        else:
            _log(wake.tag, f"invalid state ({reason}); disarming")
        return disarm_by_name(host, session_id, seams)
    if os.path.exists(wake.paths.done):
        return _finish(wake, "done marker present")
    if seams.now() < state["not_before"]:
        _log(wake.tag, f"fire before not_before {_iso(state['not_before'])}; not counted")
        return 0
    counted = _count_wake(wake, state["arm_id"])
    if counted.kind != "counted":
        if counted.kind == "gone":
            _log(wake.tag, "wake state vanished; nothing to resume")
        if counted.kind == "early":
            _log(wake.tag, f"fire before not_before {_iso(counted.not_before)}; not counted")
        return 0
    current = counted.state or {}
    cap = int(current.get("cap", WAKE_CAP))
    if counted.n > cap:
        return _finish(wake, f"wake {counted.n}/{cap}")
    return _resume(wake, state["arm_id"], counted.n)
