#!/usr/bin/env python3
"""Claude Code PostToolUse reminder; advice only, never decides or rewrites anything."""

import importlib
import os
import sys


def _fail_open(*_exc_info):
    try:
        sys.stdout.write("{}")
        sys.stdout.flush()
    except OSError:
        pass
    os._exit(0)


sys.excepthook = _fail_open
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
_session_start = importlib.import_module("claude_session_start")
emit = _session_start.emit
read_stdin = _session_start.read_stdin


def main():
    """Read one PostToolUse event and emit context-only reminder, failing open."""
    advisor_core = importlib.import_module("advisor_core")
    message = advisor_core.run_claude(
        read_stdin(advisor_core.MAX_STDIN_BYTES), "reminder", os.environ)
    emit(message, event="PostToolUse")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
