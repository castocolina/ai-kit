#!/usr/bin/env python3
"""SessionStart startup probe of jev-fast-decision through one bounded child process.

Never sends question content and prints backend names only. Any failure emits ``{}`` and exits 0.
"""

import importlib
import os
import re
import sys


def _fail_open(*_exc_info):
    """Emit an empty successful response even when a sibling import fails."""
    try:
        sys.stdout.write("{}")
        sys.stdout.flush()
    except OSError:
        pass
    os._exit(0)


sys.excepthook = _fail_open
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
_session_start = importlib.import_module("claude_session_start")
_drain_stdin = _session_start.__dict__["_drain_stdin"]
emit = _session_start.emit

PROBE_TIMEOUT_SECONDS = 3.0
_BACKEND_NAME = re.compile(r"^[a-z0-9_-]{1,32}$")


def compose_probe(report):
    """Return the user-visible and model-context lines for selectable backends only."""
    if not isinstance(report, dict) or report.get("status") != "ok":
        return "", ""
    candidates = report.get("candidates")
    if not isinstance(candidates, list):
        return "", ""
    names = [name for name in candidates
             if isinstance(name, str) and _BACKEND_NAME.fullmatch(name)]
    if not names:
        return "", ""
    backends = ", ".join(names)
    user_line = (f"ai-kit: decision skill jev-fast-decision is ready "
                 f"(backends: {backends}).")
    context = (f"The jev-fast-decision skill can answer typed yes/no, choice and score "
               f"questions through these backends: {backends}.")
    return user_line, context


def main():
    """Drain the host payload, run the shared bounded probe, then emit or fail open."""
    _drain_stdin()
    core = importlib.import_module("precompact_core")
    env = core.client_env(os.environ, None, PROBE_TIMEOUT_SECONDS,
                          os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                       ".never-created-config"))
    client = core.find_client(env)
    if client is None:
        emit(None)
        return 0
    report = core.run_probe(client, env, PROBE_TIMEOUT_SECONDS)
    user_line, context = compose_probe(report)
    emit(context, user_line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
