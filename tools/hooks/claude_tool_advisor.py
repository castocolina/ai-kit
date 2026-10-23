#!/usr/bin/env python3
"""Claude Code PreToolUse advisor: advice only, never permission or input changes."""

import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
# pylint: disable=wrong-import-position
from claude_session_start import _fail_open, emit, read_stdin


def main():
    """Read one event and emit context-only advice; failures exit successfully."""
    advisor_core = importlib.import_module("advisor_core")
    message = advisor_core.run_claude(
        read_stdin(advisor_core.MAX_STDIN_BYTES), "advisor", os.environ)
    emit(message, event="PreToolUse")
    return 0


if __name__ == "__main__":
    sys.excepthook = _fail_open
    raise SystemExit(main())
