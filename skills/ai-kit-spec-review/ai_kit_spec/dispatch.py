"""Generic process dispatcher shared by review's future JSONL-findings work and
ai-kit-spec-execute: deadlock-safe stdin prompt delivery, timestamped heartbeat while draining
output, process-GROUP timeout enforcement. Never CLI-specific -- takes an already-built command
string as an opaque unit."""
import datetime
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time

from ai_kit_spec.cache import cache_write_json

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
                             kill_fn=_default_kill_process_group,
                             print_fn=_default_print_fn) -> dict:
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


def dispatch_with_polling(command: str, prompt: str, timeout_tiers: list[int],
                           poll_interval: int = 150, popen_fn=subprocess.Popen,
                           time_fn=time.time, sleep_fn=time.sleep,
                           kill_fn=_default_kill_process_group, print_fn=_default_print_fn,
                           tmp_dir_fn=tempfile.mkdtemp, rmtree_fn=shutil.rmtree) -> dict:
    """Escalates across `timeout_tiers` (seconds, in order), each tier a FRESH process -- a
    killed CLI cannot resume its own reasoning state, so a tier restart is a real, accepted
    cost (design spec §4/§14), not an oversight. `stdout`/`stderr` are redirected to real
    files (never PIPE): this removes the deadlock condition `dispatch_with_heartbeat`'s own
    docstring documents (stdin fill racing an undrained stdout pipe) because nothing routes
    through our own process's pipes here, so `prompt` is delivered via a plain file handed to
    the child as its own stdin (`stdin=<open file>`) -- no manual write, no blocking-write risk
    on our side at all. The same file-backed stdout also makes real interim progress
    inspectable while the subprocess is alive: `print_fn` gets a one-line size-delta report
    every `poll_interval` seconds. Informational ONLY -- never aborts an attempt early, even at
    zero growth (design decision: a false "stalled" verdict on a genuinely slow-but-working
    model is worse than the wasted wait).

    `poll_interval` governs ONLY how often that progress line is emitted (and how often the
    size delta is measured) -- never how often the child is checked for completion. The wait
    itself is sliced into `_POLL_SLICE_SECONDS` chunks with a `proc.poll()` between each, so a
    process that exits in one second is noticed in about one second instead of up to
    `poll_interval` (150s) later. Without that split, a fast-failing dispatch (bad model id,
    auth error -- the CLI exits immediately) would cost the caller a full poll interval of dead
    time for nothing, and every normal review would pay it once at the end.

    Raises `ValueError` for an empty `timeout_tiers`: with no tier there is nothing to run and
    no result to return, and silently returning None would surface downstream as an opaque
    TypeError in whichever caller subscripts the result."""
    if not timeout_tiers:
        raise ValueError("timeout_tiers must name at least one tier -- got an empty list")
    tmp_dir = tmp_dir_fn(prefix="ai-kit-spec-dispatch-")
    try:
        prompt_path = os.path.join(tmp_dir, "prompt")
        with open(prompt_path, "w", encoding="utf-8") as f:
            f.write(prompt)
        stdout_path = os.path.join(tmp_dir, "stdout")
        stderr_path = os.path.join(tmp_dir, "stderr")
        last_result = None
        for tier_index, tier_timeout in enumerate(timeout_tiers, start=1):
            start = time_fn()
            last_size = 0
            next_report_at = poll_interval
            # "rb": the child never sees this Python file object at all -- Popen dups its
            # fileno() -- so text decoding here would be pure overhead on a prompt we only
            # ever hand over as a raw file descriptor.
            with open(prompt_path, "rb") as in_f, \
                 open(stdout_path, "wb") as out_f, \
                 open(stderr_path, "wb") as err_f:
                proc = popen_fn(command, shell=True, stdin=in_f, stdout=out_f, stderr=err_f,
                                 start_new_session=True)
                timed_out = False
                while proc.poll() is None:
                    elapsed = time_fn() - start
                    remaining = tier_timeout - elapsed
                    if remaining <= 0:
                        kill_fn(proc)
                        try:
                            proc.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            pass
                        timed_out = True
                        break
                    # Short slice, NOT poll_interval -- see the docstring: this is the
                    # completion-detection latency, and it must stay small regardless of how
                    # rarely we report progress.
                    sleep_fn(min(_POLL_SLICE_SECONDS, remaining))
                    if elapsed < next_report_at:
                        continue
                    next_report_at = elapsed + poll_interval
                    # No out_f.flush() here: nothing is ever written through THIS file object
                    # (the child writes to the dup'd fd directly), so our own buffer is always
                    # empty and getsize() already sees everything the child has flushed.
                    size = os.path.getsize(stdout_path) if os.path.exists(stdout_path) else 0
                    delta = size - last_size
                    ts_elapsed = int(elapsed)
                    if delta:
                        print_fn(f"tier {tier_index} ({tier_timeout}s): +{delta} bytes "
                                 f"since last check (total {size}, {ts_elapsed}s elapsed)")
                    else:
                        print_fn(f"tier {tier_index} ({tier_timeout}s): no growth "
                                 f"({ts_elapsed}s elapsed)")
                    last_size = size
            with open(stdout_path, "rb") as f:
                stdout = f.read().decode("utf-8", errors="replace")
            with open(stderr_path, "rb") as f:
                stderr = f.read().decode("utf-8", errors="replace")
            last_result = {"returncode": proc.returncode, "stdout": stdout, "stderr": stderr,
                            "timed_out": timed_out, "tiers_tried": tier_index,
                            "final_timeout": tier_timeout}
            if not timed_out:
                return last_result
            if tier_index < len(timeout_tiers):
                print_fn(f"tier {tier_index} ({tier_timeout}s) timed out -- escalating to "
                         f"tier {tier_index + 1} ({timeout_tiers[tier_index]}s)")
        return last_result
    finally:
        rmtree_fn(tmp_dir, ignore_errors=True)


def write_resumable_state(path: str, state: dict, write_fn=cache_write_json) -> None:
    """Persists the minimal state needed to resume after a quota-exhaustion auto-wake
    (design spec Section 10): framework, plan/phase reference, candidates already tried,
    iteration. A thin, documented wrapper around cache_write_json -- the resumability
    guarantee lives in what the caller puts in `state`, not in this function's own logic."""
    write_fn(path, state)
