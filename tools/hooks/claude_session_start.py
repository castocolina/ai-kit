#!/usr/bin/env python3
"""Claude Code SessionStart wrapper for the modern-tool briefing.

Reads (and discards) the host's stdin payload, runs detect + compose, and
emits a user-visible line and model context. Every failure path exits 0
with parseable JSON. Uncaught errors reach ``_fail_open`` via ``sys.excepthook``.

Empty-output evidence, per host, rather than a uniform claim:

- Cursor: a bare `{}` is an OBSERVED live precedent. Cursor's own installed
  `gsd-cursor-session-start.js` writes that shape on its error path.
- Claude Code: the same shape is INFERRED rather than observed. The
  documented envelope makes every output field optional, so a `{}` body
  carries no recognized field and is read as a no-op.

Both readings satisfy ROADMAP SC-3 (exit 0 with parseable JSON on stdout).
Labelling the Claude Code reading as an inference is the PROJECT.md
certainty rule applied to ai-kit's own claim about itself.
"""

import importlib
import json
import os
import select
import sys
import time


def _fail_open(*_exc_info):
    """Process-level SC-3 backstop: emit ``{}`` and exit 0 on any uncaught error.

    If stdout is broken, the excepthook itself fails and Python prints its
    default traceback and exits 1 (same exposure as an in-main handler).
    ``sys.excepthook`` never sees ``SystemExit``; these hooks must not gain
    argparse or any other ``SystemExit`` beyond ``raise SystemExit(main())``.
    """
    sys.stdout.write("{}")
    sys.stdout.flush()
    os._exit(0)


_STDIN_CHUNK_BYTES = 65536
_STDIN_IDLE_SECONDS = 0.5
_STDIN_TOTAL_SECONDS = 5.0


def read_stdin(limit=1024 * 1024):
    """Read stdin in bounded chunks; the bytes read (possibly more than `limit`).

    The loop ends on EOF, a 0.5 s idle select, more than `limit` bytes read, or
    5 s total by `time.monotonic` — whichever comes first. There is no fixed
    round count, so the `limit` a caller passes is the real ceiling; a result
    longer than `limit` tells the caller the payload was over it."""
    try:
        fd = sys.stdin.fileno()
    except (OSError, ValueError, AttributeError, TypeError):
        return b""
    chunks = []
    total = 0
    started = time.monotonic()
    while True:
        if total > limit or time.monotonic() - started > _STDIN_TOTAL_SECONDS:
            break
        try:
            readable, _, _ = select.select([sys.stdin], [], [], _STDIN_IDLE_SECONDS)
        except (OSError, ValueError, AttributeError, TypeError):
            break
        if not readable:
            break
        try:
            chunk = os.read(fd, _STDIN_CHUNK_BYTES)
        except (OSError, ValueError, AttributeError, TypeError):
            break
        if not chunk:
            break
        chunks.append(chunk)
        total += len(chunk)
    return b"".join(chunks)


def _drain_stdin():
    """Discard stdin so a partial payload cannot wedge us."""
    read_stdin()


def emit(message, system_message=None, event="SessionStart"):
    """Single output gate for Claude hooks; writes only context fields or `{}`."""
    payload = {}
    if message:
        payload["hookSpecificOutput"] = {
            "hookEventName": event,
            "additionalContext": message,
        }
    if system_message:
        payload["systemMessage"] = system_message
    sys.stdout.write(json.dumps(payload))
    sys.stdout.flush()


def main():
    """Detect, compose, emit. Failures reach ``_fail_open``."""
    sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
    detect = importlib.import_module("detect")
    _drain_stdin()
    detection = detect.detect_substitutions()
    user_line, context = detect.compose_message(detection)
    emit(context, user_line)
    return 0


if __name__ == "__main__":
    sys.excepthook = _fail_open
    raise SystemExit(main())
