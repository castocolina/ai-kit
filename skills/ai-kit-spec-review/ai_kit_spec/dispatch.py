"""Generic process dispatcher shared by review's future JSONL-findings work and
ai-kit-spec-execute: deadlock-safe stdin prompt delivery, timestamped heartbeat while draining
output, process-GROUP timeout enforcement. Never CLI-specific -- takes an already-built command
string as an opaque unit."""
import datetime
import os
import signal
import subprocess
import time

from ai_kit_spec.cache import cache_write_json


def _default_kill_process_group(proc) -> None:
    """Kills the WHOLE process group, not just the direct child -- under shell=True, proc.kill()
    alone only kills the shell; a descendant it spawned (e.g. sleep) can survive holding
    stdout/stderr open, hanging the post-kill communicate() drain (confirmed by live
    reproduction, 2026-08-29). Requires the Popen call to have used start_new_session=True."""
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        proc.kill()  # fallback: at least kill the direct child if group-kill isn't possible


def dispatch_with_heartbeat(command: str, prompt: str, heartbeat_interval: int, timeout: int,
                             popen_fn=subprocess.Popen, time_fn=time.time,
                             kill_fn=_default_kill_process_group, print_fn=print) -> dict:
    """Runs `command` (shell=True, in its own process group via start_new_session=True).

    Deadlock-safe by construction: `prompt` is delivered via `communicate(input=prompt,
    timeout=...)` -- NEVER via a manual `proc.stdin.write()` -- because CPython's own
    communicate() writes stdin and drains stdout/stderr concurrently (a background thread on
    POSIX). A direct `stdin.write()` call has no such concurrent draining and deadlocks for any
    prompt larger than the OS pipe buffer once the child's own stdout fills (confirmed by live
    reproduction with an ~8 MiB prompt against a real `cat` process, 2026-08-29 -- an earlier
    revision of this function had exactly this bug).

    On `TimeoutExpired` (raised WITHOUT killing the child), `input` is left as `None` on every
    retry call -- CPython's communicate() already remembers and resumes any partially-sent input
    internally across calls on the same Popen object; re-passing it would be wrong. Only the
    FIRST call ever passes `input=prompt`.

    On real timeout (elapsed >= `timeout`), `kill_fn` kills the whole process group (not just
    the shell), then a final `communicate()` drains and returns whatever output was actually
    collected before the kill -- never force-discarded to empty strings, which would erase real
    diagnostics from a dispatch that ran a while before timing out."""
    start = time_fn()
    proc = popen_fn(command, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE, text=True, start_new_session=True)
    pending_input = prompt
    while True:
        elapsed = time_fn() - start
        remaining = timeout - elapsed
        if remaining <= 0:
            kill_fn(proc)
            # Bounded, not indefinite -- killing the process group doesn't guarantee every
            # pipe-holding descendant exits immediately (a grandchild that outlived its own
            # setsid parent can still hold stdout/stderr open); confirmed by live reproduction
            # to hang the drain otherwise. 5s is generous for draining an already-terminated
            # process's remaining buffered output.
            try:
                stdout, stderr = proc.communicate(timeout=5)
            except subprocess.TimeoutExpired as exc:
                stdout, stderr = exc.stdout or "", exc.stderr or ""
            return {"returncode": proc.returncode, "stdout": stdout, "stderr": stderr,
                    "timed_out": True}
        try:
            stdout, stderr = proc.communicate(input=pending_input,
                                               timeout=min(heartbeat_interval, remaining))
        except subprocess.TimeoutExpired:
            pending_input = None  # already delivered/buffered internally -- never re-send
            ts = datetime.datetime.now().strftime("%H:%M:%S")
            print_fn(f"[{ts}] still running, {int(elapsed)}s elapsed")
            continue
        return {"returncode": proc.returncode, "stdout": stdout, "stderr": stderr,
                "timed_out": False}


def write_resumable_state(path: str, state: dict, write_fn=cache_write_json) -> None:
    """Persists the minimal state needed to resume after a quota-exhaustion auto-wake
    (design spec Section 10): framework, plan/phase reference, candidates already tried,
    iteration. A thin, documented wrapper around cache_write_json -- the resumability
    guarantee lives in what the caller puts in `state`, not in this function's own logic."""
    write_fn(path, state)
