#!/usr/bin/env python3
"""Claude Code PreToolUse advisor: advice only, never permission or input changes."""

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
    """Read one event and emit context-only advice; failures exit successfully."""
    advisor_core = importlib.import_module("advisor_core")
    message = advisor_core.run_claude(
        read_stdin(advisor_core.MAX_STDIN_BYTES), "advisor", os.environ)
    emit(message, event="PreToolUse")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
