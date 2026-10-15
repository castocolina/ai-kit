"""Generic process dispatcher shared by review's future JSONL-findings work and
ai-kit-spec-execute: deadlock-safe stdin prompt delivery, timestamped heartbeat while draining
output, process-GROUP timeout enforcement. Never CLI-specific -- takes an already-built command
ARGV LIST as an opaque unit and spawns it with NO shell (D-10); the child environment is
scrubbed of the host's own identity variables (D-14, see child_env)."""
import contextlib
import datetime
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from typing import Any, NamedTuple

from ai_kit_spec.cache import cache_write_json
from ai_kit_spec.detection import HOST_SIGNAL_ENV_VARS

# How long dispatch_with_polling waits between proc.poll() checks. Deliberately NOT
# configurable and deliberately NOT poll_interval: this is completion-detection latency
# (how late we notice a finished child), whereas poll_interval is progress-reporting cadence.
_POLL_SLICE_SECONDS = 1


def _default_print_fn(*args) -> None:
    """Reads sys.stderr at CALL time, not at import/bind time -- a plain
    `functools.partial(print, file=sys.stderr)` captures whatever object sys.stderr referred to
    when this module was first imported, so a caller that later redirects sys.stderr (e.g. a
    test's `redirect_stderr`, or a harness reassigning it) would be silently ignored. Heartbeat is
    diagnostic/progress text, never part of the dispatched command's own output -- a caller piping
    this function's caller (e.g. dispatch-execute's own --stdout-only mode, used as a drop-in GSD
    workflow.cross_ai_command value) captures ONLY the dispatched CLI's stdout as a real artifact
    (GSD's own $CANDIDATE_SUMMARY); a heartbeat line landing on stdout by default would corrupt
    that capture the moment a dispatch ran long enough to tick even once."""
    print(*args, file=sys.stderr)


def _default_kill_process_group(proc) -> None:
    """Kills the WHOLE process group, not just the direct child -- proc.kill()
    alone can leave a descendant the child spawned (e.g. a grandchild tool call) alive, holding
    stdout/stderr open and hanging the post-kill communicate() drain (confirmed by live
    reproduction, 2026-08-29). Requires the Popen call to have used start_new_session=True."""
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        proc.kill()  # fallback: at least kill the direct child if group-kill isn't possible


class HeartbeatDispatchSeams(NamedTuple):
    popen_fn: Callable[..., Any] = subprocess.Popen
    time_fn: Callable[[], float] = time.time
    kill_fn: Callable[[Any], None] = _default_kill_process_group
    print_fn: Callable[..., None] = _default_print_fn


class PollingDispatchSeams(NamedTuple):
    poll_interval: int = 150
    popen_fn: Callable[..., Any] = subprocess.Popen
    time_fn: Callable[[], float] = time.time
    sleep_fn: Callable[[float], None] = time.sleep
    kill_fn: Callable[[Any], None] = _default_kill_process_group
    print_fn: Callable[..., None] = _default_print_fn
    tmp_dir_fn: Callable[..., str] = tempfile.mkdtemp
    rmtree_fn: Callable[..., None] = shutil.rmtree


def child_env(extra: dict | None = None, env: dict | None = None) -> dict:
    """Builds the environment for a cross-AI child (D-14): copies `env` (or os.environ),
    removes every HOST_SIGNAL_ENV_VARS entry so the child never mistakes itself for the host,
    then applies `extra` -- an explicit per-runtime `env` addition survives the scrub because
    it is applied last."""
    base = dict(os.environ if env is None else env)
    for name in HOST_SIGNAL_ENV_VARS:
        base.pop(name, None)
    if extra:
        base.update(extra)
    return base


def dispatch_with_heartbeat(
    argv: list[str],
    prompt: str,
    heartbeat_interval: int,
    timeout: int,
    seams: HeartbeatDispatchSeams | None = None,
) -> dict:
    """Runs `argv` with heartbeat progress and timeout enforcement (see module docstring)."""
    active = seams or HeartbeatDispatchSeams()
    start = active.time_fn()
    if not argv:
        raise ValueError("empty command argv")
    try:
        proc = active.popen_fn(
            argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            start_new_session=True,
            env=child_env(),
        )
    except OSError as exc:
        return {"returncode": 127, "stdout": "", "stderr": str(exc), "timed_out": False}
    pending_input = prompt
    while True:
        elapsed = active.time_fn() - start
        remaining = timeout - elapsed
        if remaining <= 0:
            active.kill_fn(proc)
            try:
                stdout, stderr = proc.communicate(timeout=5)
            except subprocess.TimeoutExpired as exc:
                stdout, stderr = exc.stdout or "", exc.stderr or ""
            return {
                "returncode": proc.returncode,
                "stdout": stdout,
                "stderr": stderr,
                "timed_out": True,
            }
        try:
            stdout, stderr = proc.communicate(
                input=pending_input,
                timeout=min(heartbeat_interval, remaining),
            )
        except subprocess.TimeoutExpired:
            pending_input = None
            ts = datetime.datetime.now().strftime("%H:%M:%S")
            active.print_fn(f"[{ts}] still running, {int(elapsed)}s elapsed")
            continue
        return {
            "returncode": proc.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "timed_out": False,
        }


def _read_output(path: str) -> str:
    with open(path, "rb") as f:
        return f.read().decode("utf-8", errors="replace")


class _TierProgress(NamedTuple):
    tier_index: int
    tier_timeout: int
    elapsed: float
    stdout_path: str
    last_size: int


class _PollingTierWork(NamedTuple):
    argv: list[str]
    seams: PollingDispatchSeams
    prompt_path: str
    stdout_path: str
    stderr_path: str
    tier_index: int
    tier_timeout: int


def _report_tier_progress(print_fn, progress: _TierProgress) -> int:
    path = progress.stdout_path
    size = os.path.getsize(path) if os.path.exists(path) else 0
    delta = size - progress.last_size
    ts_elapsed = int(progress.elapsed)
    idx, tmo = progress.tier_index, progress.tier_timeout
    if delta:
        print_fn(
            f"tier {idx} ({tmo}s): +{delta} bytes "
            f"since last check (total {size}, {ts_elapsed}s elapsed)"
        )
    else:
        print_fn(f"tier {idx} ({tmo}s): no growth ({ts_elapsed}s elapsed)")
    return size


class _PollLoopCtx(NamedTuple):
    proc: Any
    seams: PollingDispatchSeams
    start: float
    tier_index: int
    tier_timeout: int
    stdout_path: str


def _poll_tier_process(ctx: _PollLoopCtx) -> bool:
    next_report_at = ctx.seams.poll_interval
    last_size = 0
    while ctx.proc.poll() is None:
        elapsed = ctx.seams.time_fn() - ctx.start
        remaining = ctx.tier_timeout - elapsed
        if remaining <= 0:
            ctx.seams.kill_fn(ctx.proc)
            with contextlib.suppress(subprocess.TimeoutExpired):
                ctx.proc.wait(timeout=5)
            return True
        ctx.seams.sleep_fn(min(_POLL_SLICE_SECONDS, remaining))
        if elapsed < next_report_at:
            continue
        next_report_at = elapsed + ctx.seams.poll_interval
        progress = _TierProgress(
            tier_index=ctx.tier_index,
            tier_timeout=ctx.tier_timeout,
            elapsed=elapsed,
            stdout_path=ctx.stdout_path,
            last_size=last_size,
        )
        last_size = _report_tier_progress(ctx.seams.print_fn, progress)
    return False


def _spawn_polling_tier(work: _PollingTierWork) -> dict:
    start = work.seams.time_fn()
    with open(work.prompt_path, "rb") as in_f, open(work.stdout_path, "wb") as out_f, open(
        work.stderr_path, "wb"
    ) as err_f:
        try:
            proc = work.seams.popen_fn(
                work.argv,
                stdin=in_f,
                stdout=out_f,
                stderr=err_f,
                start_new_session=True,
                env=child_env(),
            )
        except OSError as exc:
            return {
                "returncode": 127,
                "stdout": "",
                "stderr": str(exc),
                "timed_out": False,
                "tiers_tried": work.tier_index,
                "final_timeout": work.tier_timeout,
            }
        timed_out = _poll_tier_process(
            _PollLoopCtx(
                proc, work.seams, start, work.tier_index, work.tier_timeout, work.stdout_path
            )
        )
    return {
        "returncode": proc.returncode,
        "stdout": _read_output(work.stdout_path),
        "stderr": _read_output(work.stderr_path),
        "timed_out": timed_out,
        "tiers_tried": work.tier_index,
        "final_timeout": work.tier_timeout,
    }


def dispatch_with_polling(
    argv: list[str],
    prompt: str,
    timeout_tiers: list[int],
    seams: PollingDispatchSeams | None = None,
) -> dict:
    """Escalates across `timeout_tiers` with file-backed stdout/stderr (see module docstring)."""
    active = seams or PollingDispatchSeams()
    if not timeout_tiers:
        raise ValueError("timeout_tiers must name at least one tier -- got an empty list")
    if not argv:
        raise ValueError("empty command argv")
    tmp_dir = active.tmp_dir_fn(prefix="ai-kit-spec-dispatch-")
    try:
        prompt_path = os.path.join(tmp_dir, "prompt")
        with open(prompt_path, "w", encoding="utf-8") as f:
            f.write(prompt)
        stdout_path = os.path.join(tmp_dir, "stdout")
        stderr_path = os.path.join(tmp_dir, "stderr")
        last_result: dict = {}
        for tier_index, tier_timeout in enumerate(timeout_tiers, start=1):
            last_result = _spawn_polling_tier(
                _PollingTierWork(
                    argv,
                    active,
                    prompt_path,
                    stdout_path,
                    stderr_path,
                    tier_index,
                    tier_timeout,
                )
            )
            if not last_result.get("timed_out"):
                return last_result
            if tier_index < len(timeout_tiers):
                active.print_fn(
                    f"tier {tier_index} ({tier_timeout}s) timed out -- escalating to "
                    f"tier {tier_index + 1} ({timeout_tiers[tier_index]}s)"
                )
        return last_result
    finally:
        active.rmtree_fn(tmp_dir, ignore_errors=True)


def write_resumable_state(path: str, state: dict, write_fn=cache_write_json) -> None:
    """Persists the minimal state needed to resume after a quota-exhaustion auto-wake."""
    write_fn(path, state)
