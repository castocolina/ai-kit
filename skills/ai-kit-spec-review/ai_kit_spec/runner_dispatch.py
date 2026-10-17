"""One supervised spawn path for the cross-AI runner and for custom entries (D-10, D-11).

Both paths share `_spawn_supervised`: the prompt goes in on stdin, stdout lands in a temp
file, stderr is relayed live, and a `killpg` backstop (SIGTERM, then SIGKILL) runs on every
exit path. The runner's own detached CLI groups are recorded through `--child-pgid-file` and
killed the same way, so a wedged runner leaves no full-permission CLI behind.
"""
import contextlib
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from collections import deque
from collections.abc import Callable
from typing import Any, NamedTuple

from ai_kit_spec.commands import SUPPORTED_EXECUTE_CLIS
from ai_kit_spec.dispatch import child_env
from ai_kit_spec.error_classifier import classify_error, reason_for_status
from ai_kit_spec.tooling_guidance import resolve_cross_ai_template_path

# Project-local paths a GSD hook names, relative to the project root (D-26, D-30).
PROJECT_RUNNER_PATH = ".planning/scripts/cross-ai.mjs"
PROJECT_GUIDANCE_PATH = ".planning/scripts/cross-ai-guidance.md"
# GSD word-splits and globs the hook unquoted, so a token may hold no shell or glob
# metacharacter: a cursor bracket model (`m[effort=high]`) is a glob class, so it is argv-only.
HOOK_TOKEN_RE = re.compile(r"^[A-Za-z0-9._:/@+=,#-]+$")

RUNNER_OUTER_MARGIN_S = 30
_KILL_GRACE_S = 10  # slack after the runner's own outer timeout before the backstop fires
_TERM_GRACE_S = 4  # SIGTERM to SIGKILL; above the runner's 2.5 s signal budget
_DRAIN_S = 2  # how long the stderr relay may run after the child is gone
_STDERR_TAIL_CHARS = 2048
_STDERR_TAIL_LINES = 64  # lines kept in memory; the result keeps their last _STDERR_TAIL_CHARS
_POLL_SLICE_S = 0.2
_STATUS_PREFIX = "AIKIT-XAI "

# The template's regex sources verbatim (cross-ai.mjs MODEL_ID / CURSOR_MODEL_ID).
MODEL_ID_SRC = "/^[A-Za-z0-9][A-Za-z0-9._:/#@+-]*$/"
CURSOR_MODEL_ID_SRC = "/^[A-Za-z0-9][A-Za-z0-9._:/#@+-]*(?:\\[[A-Za-z0-9._=,-]+\\])?$/"

_NO_NODE_LINE = "ai-kit-spec: subprocess dispatch needs Node (node not found on PATH)"
_NO_TEMPLATE_LINE = "ai-kit-spec: runner template not found"
_STDERR_OPEN_LINE = (
    "ai-kit-spec: stderr still open after the child exited; stopped reading"
)
_TRAILER_IGNORE_LINE = (
    "ai-kit-spec: ignoring a runner status line that does not match this run"
)


def model_id_ok(runtime: str, model: str) -> bool:
    """True when `model` matches the charset the runner itself accepts for `runtime`."""
    src = CURSOR_MODEL_ID_SRC if runtime == "cursor" else MODEL_ID_SRC
    return re.fullmatch(src[1:-1], model) is not None


class RunnerSpec(NamedTuple):
    runtime: str
    model: str
    mode: str
    timeout_s: int
    cwd: str | None = None
    effort: str | None = None
    service_tier: str | None = None
    cursor_mode: str | None = None
    codex_sandbox: str | None = None


class RunnerResult(NamedTuple):
    returncode: int | None
    stdout: str
    status: dict | None
    reason: str | None
    timed_out: bool
    argv: list[str]
    stderr_tail: str


class SpawnRequest(NamedTuple):
    argv: list[str]
    prompt: str
    deadline_s: float
    cwd: str | None = None
    pgid_file: str | None = None


class CustomSpec(NamedTuple):
    key: str
    argv: list[str]
    timeout_tiers: list[int]
    cwd: str | None = None


class _RelayState(NamedTuple):
    tail: deque[str]
    status_line: list[str | None]


class _ChildRun(NamedTuple):
    """What one supervised child did: its process, whether the deadline passed, its relay."""

    proc: Any
    timed_out: bool
    relay: tuple[Any, _RelayState] | None
    error: BaseException | None = None


def stderr_print(line: str) -> None:
    """One stderr line, read at call time so a redirected sys.stderr is honored."""
    print(line, file=sys.stderr)


_default_print = stderr_print

# pi exec uses the runner's formula, which only its hermetic self-test covers today.
PI_EXEC_NOTE = (
    "ai-kit-spec: pi exec uses the runner's pi formula, verified by its hermetic "
    "self-test only; live verification is Phase 22"
)


def project_runner_command(spec: RunnerSpec, *, guidance: bool = False) -> str | None:
    """The project-local hook string, or None when a token is unsafe or unsupported.

    GSD expands the value unquoted (word splitting and globbing), so the tokens are joined
    with single spaces and never quoted; any token outside the allowlist, a cursor bracket
    model included, returns None instead of a command."""
    if spec.runtime not in SUPPORTED_EXECUTE_CLIS:
        return None
    tokens = ["node", PROJECT_RUNNER_PATH, *runner_flags(spec)]
    if guidance:
        tokens += ["--no-preamble", "--prepend-file", PROJECT_GUIDANCE_PATH]
    if not all(HOOK_TOKEN_RE.fullmatch(token) for token in tokens):
        return None
    return " ".join(tokens)


def runner_flags(spec: RunnerSpec) -> list[str]:
    """The runner flags one `RunnerSpec` turns into. Never a shell string."""
    flags = [
        "--prefer", spec.runtime, f"--model-{spec.runtime}", spec.model, "--mode", spec.mode,
    ]
    if spec.runtime == "codex":
        if spec.effort:
            flags += ["--codex-effort", spec.effort]
        if spec.service_tier:
            flags += ["--codex-service-tier", spec.service_tier]
        if spec.codex_sandbox and spec.mode == "exec":
            flags += ["--codex-sandbox", spec.codex_sandbox]
    elif spec.runtime == "cursor" and spec.mode == "review" and spec.cursor_mode:
        flags += ["--cursor-mode", spec.cursor_mode]
    return flags


def build_runner_argv(spec: RunnerSpec, runner_path: str, node: str) -> list[str]:
    """`node`, the template, the flags, and the two timeouts. Never a shell string."""
    timeout = str(spec.timeout_s)
    outer = str(spec.timeout_s + RUNNER_OUTER_MARGIN_S)
    return [
        node, runner_path, *runner_flags(spec),
        "--timeout", timeout, "--outer-timeout", outer, "--no-preamble",
    ]


def parse_status_line(line: str) -> dict | None:
    """The `key=value` tokens of an `AIKIT-XAI ` line, or None for anything else.

    Values keep their brackets and slashes: the runner prints model ids verbatim."""
    if not line.startswith(_STATUS_PREFIX):
        return None
    return dict(token.split("=", 1) for token in line.split() if "=" in token)


class RunnerSeams(NamedTuple):
    which_fn: Callable[[str], str | None] = shutil.which
    popen_fn: Callable[..., Any] = subprocess.Popen
    time_fn: Callable[[], float] = time.monotonic
    sleep_fn: Callable[[float], None] = time.sleep
    kill_fn: Callable[[int, int], None] = os.killpg
    print_fn: Callable[[str], None] = _default_print
    runner_path_fn: Callable[[], str | None] = resolve_cross_ai_template_path
    env_fn: Callable[[], dict] = lambda: dict(os.environ)


def _start_stderr_relay(stream, seams: RunnerSeams) -> tuple[threading.Thread, _RelayState]:
    state = _RelayState(tail=deque(maxlen=_STDERR_TAIL_LINES), status_line=[None])

    def relay() -> None:
        for raw in iter(stream.readline, ""):
            line = raw.rstrip("\n")
            seams.print_fn(line)
            state.tail.append(line)
            if line.startswith(_STATUS_PREFIX):
                state.status_line[0] = line

    thread = threading.Thread(target=relay, daemon=True)
    thread.start()
    return thread, state


def _wait_for_exit(proc, seams: RunnerSeams, deadline: float) -> bool:
    """Polls until the child exits or `deadline` (monotonic) passes. True when it passed."""
    while proc.poll() is None:
        remaining = deadline - seams.time_fn()
        if remaining <= 0:
            return True
        seams.sleep_fn(min(_POLL_SLICE_S, remaining))
    return False


def _signal_group(kill_fn, pgid: int, sig: int) -> None:
    with contextlib.suppress(ProcessLookupError, PermissionError, OSError):
        kill_fn(pgid, sig)


def _reap_group(proc, seams: RunnerSeams, pgid: int) -> None:
    """SIGTERM, then SIGKILL once the child is reaped or after the grace period.

    The trailing SIGKILL also clears descendants left in the group after a normal exit.
    A wait that still does not reap is swallowed: the caller must not hang on it."""
    _signal_group(seams.kill_fn, pgid, signal.SIGTERM)
    if proc.poll() is None:
        grace_deadline = seams.time_fn() + _TERM_GRACE_S
        _wait_for_exit(proc, seams, grace_deadline)
    _signal_group(seams.kill_fn, pgid, signal.SIGKILL)
    with contextlib.suppress(subprocess.TimeoutExpired):
        proc.wait(timeout=_TERM_GRACE_S)


def _recorded_groups(path: str) -> list[int]:
    """Every `spawn N` with no matching `exit N`: ints above 1, never our own group."""
    try:
        with open(path, encoding="utf-8") as handle:
            lines = handle.read().splitlines()
    except OSError:
        return []
    spawned: list[int] = []
    exited: set[int] = set()
    own = os.getpgrp()
    for line in lines:
        parts = line.split()
        if len(parts) != 2 or parts[0] not in ("spawn", "exit"):
            continue
        try:
            number = int(parts[1])
        except ValueError:
            continue
        if number <= 1 or number == own:
            continue
        if parts[0] == "spawn":
            spawned.append(number)
        else:
            exited.add(number)
    return [pgid for pgid in spawned if pgid not in exited]


def _group_gone(pgid: int, seams: RunnerSeams) -> bool:
    """True once `kill(pgid, 0)` fails: the recorded group no longer exists."""
    try:
        seams.kill_fn(pgid, 0)
    except (ProcessLookupError, PermissionError, OSError):
        return True
    return False


def _await_group_exit(pgid: int, seams: RunnerSeams) -> None:
    """Polls until the group is gone or the grace period passes. One sleep per slice."""
    deadline = seams.time_fn() + _TERM_GRACE_S
    while not _group_gone(pgid, seams):
        remaining = deadline - seams.time_fn()
        if remaining <= 0:
            return
        seams.sleep_fn(min(_POLL_SLICE_S, remaining))


def _reap_recorded_group(pgid: int, seams: RunnerSeams) -> None:
    """SIGTERM, poll up to the grace period, then SIGKILL if the group survives."""
    _signal_group(seams.kill_fn, pgid, signal.SIGTERM)
    _await_group_exit(pgid, seams)
    _signal_group(seams.kill_fn, pgid, signal.SIGKILL)


def _kill_recorded_groups(path: str | None, seams: RunnerSeams) -> None:
    """Reaps every recorded group the runner itself did not record an exit for."""
    if not path:
        return
    for pgid in _recorded_groups(path):
        _reap_recorded_group(pgid, seams)


def _finish_relay(thread: threading.Thread | None, stream, seams: RunnerSeams) -> None:
    """Joins the relay for at most `_DRAIN_S`; a holder that escaped is abandoned.

    The pipe is closed only once the reader has finished: closing it while the relay
    thread is blocked in readline would block this thread on the reader's lock."""
    if thread is not None:
        thread.join(_DRAIN_S)
        if thread.is_alive():
            seams.print_fn(_STDERR_OPEN_LINE)
            return
    if stream is not None:
        stream.close()


def _read_text(path: str | None) -> str:
    if not path:
        return ""
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except OSError:
        return ""


def _drop_temp_files(paths: list[str]) -> None:
    for path in paths:
        with contextlib.suppress(OSError):
            os.unlink(path)


def _cleanup_spawn(run: _ChildRun | None, request: SpawnRequest, seams: RunnerSeams,
                   temp_paths: list[str]) -> str:
    """Group, recorded groups, the relay, then stdout. Runs on every exit path."""
    if run is not None and run.proc is not None:
        _reap_group(run.proc, seams, run.proc.pid)
    _kill_recorded_groups(request.pgid_file, seams)
    thread = run.relay[0] if run and run.relay else None
    stream = run.proc.stderr if run and run.proc is not None else None
    _finish_relay(thread, stream, seams)
    stdout = _read_text(temp_paths[1] if len(temp_paths) > 1 else None)
    _drop_temp_files(temp_paths)
    return stdout


class _SpawnWork(NamedTuple):
    request: SpawnRequest
    seams: RunnerSeams


def _temp_path() -> str:
    """A 0600 temp file the caller owns and deletes. Closed before it is returned."""
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False) as handle:
        return handle.name


def _reopen(path: str):
    """Reopens `path` for the child to read. The caller closes it after the spawn."""
    return open(path, encoding="utf-8")


def _open_spawn_files(prompt: str) -> tuple[Any, str, str]:
    """The prompt on a temp file (stdin) and an empty temp file (stdout). Both 0600."""
    stdin_path = _temp_path()
    with open(stdin_path, "w", encoding="utf-8") as writer:
        writer.write(prompt)
    return _reopen(stdin_path), stdin_path, _temp_path()


def _popen_supervised(work: _SpawnWork, stdin_handle, stdout_path: str):
    with open(stdout_path, "w", encoding="utf-8") as stdout_handle:
        return work.seams.popen_fn(
            work.request.argv,
            stdin=stdin_handle,
            stdout=stdout_handle,
            stderr=subprocess.PIPE,
            start_new_session=True,
            cwd=work.request.cwd,
            env=child_env(env=work.seams.env_fn()),
            text=True,
            encoding="utf-8",
            errors="replace",
        )


def _start_child(work: _SpawnWork, stdin_handle, stdout_path: str) -> _ChildRun:
    """Spawns and starts the relay. An OSError is carried back: nothing was spawned."""
    try:
        proc = _popen_supervised(work, stdin_handle, stdout_path)
    except OSError as exc:
        return _ChildRun(None, False, None, exc)
    return _ChildRun(proc, False, _start_stderr_relay(proc.stderr, work.seams))


def _spawn_supervised(request: SpawnRequest, seams: RunnerSeams) -> RunnerResult:
    """Spawns `request.argv` and supervises it. `reason` stays None; callers fill it.

    A Popen OSError propagates: nothing was spawned, so there is nothing to clean up.
    Cleanup runs on every exit path, including an exception during the wait (a
    KeyboardInterrupt in `sleep_fn`): the child is already recorded in `run` by then."""
    work = _SpawnWork(request, seams)
    stdin_handle, stdin_path, stdout_path = _open_spawn_files(work.request.prompt)
    paths = [stdin_path, stdout_path]
    run: _ChildRun | None = None
    try:
        run = _start_child(work, stdin_handle, stdout_path)
        if run.proc is not None:
            deadline = seams.time_fn() + request.deadline_s
            run = run._replace(timed_out=_wait_for_exit(run.proc, seams, deadline))
        stdin_handle.close()
        stdout = _cleanup_spawn(run, request, seams, paths)
    except BaseException:
        stdin_handle.close()
        _cleanup_spawn(run, request, seams, paths)
        raise
    if run.error is not None:
        raise run.error
    return _result_from(run, work, stdout)


def _relay_capture(relay) -> tuple[str, dict | None]:
    """The relay's stderr tail and its last parsed status line."""
    _thread, state = relay
    status = parse_status_line(state.status_line[0]) if state.status_line[0] else None
    return "\n".join(state.tail)[-_STDERR_TAIL_CHARS:], status


def _result_from(run: _ChildRun, work: _SpawnWork, stdout: str) -> RunnerResult:
    """The result, built after cleanup so the returncode is final."""
    tail, status = _relay_capture(run.relay)
    return RunnerResult(
        returncode=run.proc.returncode,
        stdout=stdout,
        status=status,
        reason=None,
        timed_out=run.timed_out,
        argv=list(work.request.argv),
        stderr_tail=tail,
    )


def _unavailable(argv: list[str], line: str, seams: RunnerSeams) -> RunnerResult:
    seams.print_fn(line)
    return RunnerResult(None, "", None, "dispatch_unavailable", False, argv, "")


def _trailer_counts(status: dict, spec: RunnerSpec, returncode: int | None) -> bool:
    """A status line counts only when it names this run and this returncode."""
    if status.get("exit") != ("" if returncode is None else str(returncode)):
        return False
    cli_ok = status.get("cli") in ("-", spec.runtime)
    model_ok = status.get("model") in ("-", spec.model)
    return cli_ok and model_ok


def _runner_reason(result: RunnerResult, spec: RunnerSpec, seams: RunnerSeams) -> RunnerResult:
    """Validates the trailer, then derives the reason. A backstop kill reads `timeout`."""
    status = result.status
    if status is not None and not _trailer_counts(status, spec, result.returncode):
        seams.print_fn(_TRAILER_IGNORE_LINE)
        status = None
    if result.timed_out:
        reason: str | None = "timeout"
    else:
        reason = reason_for_status(
            status["status"] if status else None, result.returncode
        )
    return result._replace(status=status, reason=reason)


def run_runner(spec: RunnerSpec, prompt: str, seams: RunnerSeams | None = None) -> RunnerResult:
    """Runs one candidate through the runner template. No node or template fails closed."""
    active = seams or RunnerSeams()
    node = active.which_fn("node")
    if not node:
        return _unavailable([], _NO_NODE_LINE, active)
    runner_path = active.runner_path_fn()
    if not runner_path:
        return _unavailable([], _NO_TEMPLATE_LINE, active)
    if not model_id_ok(spec.runtime, spec.model):
        active.print_fn(
            f"ai-kit-spec: model id {spec.model} is not a valid {spec.runtime} model id"
        )
        return RunnerResult(None, "", None, "configuration", False, [], "")
    argv = build_runner_argv(spec, runner_path, node)
    pgid_dir = tempfile.mkdtemp(prefix="aikit-pgid-")
    os.chmod(pgid_dir, 0o700)
    pgid_path = os.path.join(pgid_dir, "child-pgids")
    deadline = spec.timeout_s + RUNNER_OUTER_MARGIN_S + _KILL_GRACE_S
    try:
        try:
            result = _spawn_supervised(
                SpawnRequest([*argv, "--child-pgid-file", pgid_path], prompt, deadline,
                             spec.cwd, pgid_path),
                active,
            )
        except OSError as exc:
            return _unavailable(argv, str(exc), active)
        return _runner_reason(result._replace(argv=argv), spec, active)
    finally:
        shutil.rmtree(pgid_dir, ignore_errors=True)


def run_runner_tiers(spec: RunnerSpec, tiers: list[int], prompt: str,
                     seams: RunnerSeams | None = None) -> RunnerResult:
    """Re-invokes the next tier only on a `timeout` status or exit 124. One call per tier."""
    if not tiers:
        raise ValueError("timeout_tiers must name at least one tier -- got an empty list")
    active = seams or RunnerSeams()
    result = RunnerResult(None, "", None, None, False, [], "")
    for tier in tiers:
        result = run_runner(spec._replace(timeout_s=tier), prompt, active)
        timed = (result.status or {}).get("status") == "timeout" or result.returncode == 124
        if not timed:
            return result
    return result


def run_custom_command(spec: CustomSpec, prompt: str,
                       seams: RunnerSeams | None = None) -> RunnerResult:
    """Runs a custom entry's argv, escalating tiers only on its own deadline (D-21, D-28)."""
    active = seams or RunnerSeams()
    if not spec.timeout_tiers:
        raise ValueError("timeout_tiers must name at least one tier -- got an empty list")
    if not spec.argv:
        raise ValueError("empty command argv")
    result = RunnerResult(None, "", None, None, False, [], "")
    for index, tier in enumerate(spec.timeout_tiers, start=1):
        try:
            result = _spawn_supervised(
                SpawnRequest(list(spec.argv), prompt, tier, spec.cwd), active
            )
        except OSError as exc:
            return _unavailable(list(spec.argv), str(exc), active)
        if not result.timed_out:
            reason = classify_error(result.returncode, result.stderr_tail, False)
            return result._replace(reason=reason, status=None)
        if index < len(spec.timeout_tiers):
            nxt = spec.timeout_tiers[index]
            active.print_fn(
                f"tier {index} ({tier}s) timed out -- escalating to tier {index + 1} ({nxt}s)"
            )
    reason = classify_error(result.returncode, result.stderr_tail, result.timed_out)
    return result._replace(reason=reason, status=None)
