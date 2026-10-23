#!/usr/bin/env python3
"""Cursor sessionStart wrapper for the modern-tool briefing.

Reads and discards the host's stdin payload, runs the shared detector and
composer, and emits the model context in Cursor's additional_context field.
Every failure path exits 0 with parseable JSON.

Output schema: `{ additional_context?: string }`; Cursor has no user-visible
briefing field. Empty output is a bare `{}`.

Host coverage: Claude Code and Cursor are wired. opencode has no documented
session-start injection point today, an accepted and documented gap.
"""

import importlib
import json
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
_drain_stdin = _session_start.__dict__["_drain_stdin"]


def emit(message):
    """Write the sessionStart envelope, or `{}` when there is nothing to say."""
    payload = {"additional_context": message} if message else {}
    sys.stdout.write(json.dumps(payload))
    sys.stdout.flush()


def main():
    """Detect, compose, emit. Failures reach the shared ``_fail_open``."""
    detect = importlib.import_module("detect")
    _drain_stdin()
    _user_line, context = detect.compose_message(detect.detect_substitutions())
    emit(context)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
