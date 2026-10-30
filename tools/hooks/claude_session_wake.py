#!/usr/bin/env python3
"""Claude Code StopFailure hook (rate_limit): passes the host's reset text to an armed wake.

Opt-in (26-07, D-30). It refreshes only a session its orchestrator already armed
(`arm --only-if-armed`), so it never arms a wake of its own. The main agent gets
no working turn during a usage limit, so this hook is the only actor that sees
the reset text at the stall (spike item 12). The payload fields that carry that
text are unverified (RESEARCH Q5); when they do not, nothing happens.

Fail open: any malformed input, missing shim or child failure exits 0 with no
output. Stdlib only; the shim is run as an argv list, never through a shell.
"""

import contextlib
import importlib
import json
import os
import signal
import subprocess
import sys
import time

# The row's registered timeout is 10 s (tools/setup.py); the hook exits by itself
# first, so the host never has to kill it. One monotonic deadline covers the
# stdin read and the arm child.
HOOK_DEADLINE_S = 8.0
HOOK_MIN_CHILD_S = 1.0
_RESET_MARKER = "resets "
_TEXT_CAP = 4000
_FIELDS = ("error", "error_details", "last_assistant_message")


def _fail_open(*_exc_info):
    """Process-level backstop: silence and exit 0 on any uncaught error."""
    os._exit(0)


sys.excepthook = _fail_open
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
_session_start = importlib.import_module("claude_session_start")
read_stdin = _session_start.read_stdin


def _shim_path():
    """The session-wake shim beside the skills tree, from this file's real path."""
    here = os.path.dirname(os.path.realpath(__file__))
    return os.path.realpath(
        os.path.join(here, "..", "..", "skills", "ai-kit-session-wake", "ai-kit-session-wake.py")
    )


def _payload(raw):
    """The (session id, reset text) pair, or None when the hook must do nothing."""
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    sid = data.get("session_id")
    if not isinstance(sid, str) or not sid:
        return None
    parts = []
    for name in _FIELDS:
        value = data.get(name)
        if value is None:
            continue
        parts.append(value if isinstance(value, str) else json.dumps(value, sort_keys=True))
    text = " ".join(parts)
    if _RESET_MARKER not in text:
        return None
    return sid, text[:_TEXT_CAP]


def _run_arm(shim, sid, text, started):
    """Run `arm --only-if-armed` in its own session; the group dies at the deadline."""
    left = HOOK_DEADLINE_S - (time.monotonic() - started)
    if left < HOOK_MIN_CHILD_S or not os.path.isfile(shim):
        return
    argv = [
        sys.executable, shim, "arm", "--host", "claude", "--session-id", sid,
        "--reset-text", text, "--only-if-armed",
    ]
    try:
        with subprocess.Popen(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
            env=dict(os.environ),
        ) as proc:
            _wait_or_kill(proc, HOOK_DEADLINE_S - (time.monotonic() - started))
    except OSError:
        return


def _wait_or_kill(proc, timeout):
    """Wait for the arm child; at the deadline SIGKILL its whole group, reap it."""
    try:
        proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        with contextlib.suppress(OSError):
            os.killpg(proc.pid, signal.SIGKILL)
        with contextlib.suppress(subprocess.TimeoutExpired, OSError, ValueError):
            proc.communicate(timeout=1)


def main():
    """Read one StopFailure event; refresh an armed wake or do nothing."""
    started = time.monotonic()
    parsed = _payload(read_stdin(1024 * 1024))
    if parsed is None:
        return 0
    sid, text = parsed
    _run_arm(_shim_path(), sid, text, started)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
