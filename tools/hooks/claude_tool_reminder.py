#!/usr/bin/env python3
"""Claude Code PostToolUse reminder; advice only, never decides or rewrites anything."""

import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
# pylint: disable=wrong-import-position
from claude_session_start import _fail_open, emit, read_stdin


def main():
    """Read one PostToolUse event and emit context-only reminder, failing open."""
    advisor_core = importlib.import_module("advisor_core")
    message = advisor_core.run_claude(
        read_stdin(advisor_core.MAX_STDIN_BYTES), "reminder", os.environ)
    emit(message, event="PostToolUse")
    return 0


if __name__ == "__main__":
    sys.excepthook = _fail_open
    raise SystemExit(main())
