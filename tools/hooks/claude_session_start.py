#!/usr/bin/env python3
"""Claude Code SessionStart wrapper for the tool-substitution briefing.

Reads (and discards) the host's stdin payload, runs detect + compose, and
emits a Claude Code SessionStart envelope on stdout. Every failure path
exits 0 with parseable JSON — a hung or missing rtk must never block
session start.

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

import json
import os
import select
import sys


def _drain_stdin():
    """Discard stdin in bounded chunks so a partial payload cannot wedge us."""
    try:
        fd = sys.stdin.fileno()
    except Exception:
        return
    total = 0
    for _ in range(16):
        if total >= 1024 * 1024:
            return
        try:
            readable, _, _ = select.select([sys.stdin], [], [], 0.5)
        except Exception:
            return
        if not readable:
            return
        try:
            chunk = os.read(fd, 65536)
        except Exception:
            return
        if not chunk:
            return
        total += len(chunk)


def emit(message):
    """Write the SessionStart envelope, or `{}` when there is nothing to say."""
    if message:
        payload = {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": message,
            }
        }
    else:
        payload = {}
    sys.stdout.write(json.dumps(payload))
    sys.stdout.flush()


def main():
    """Detect, compose, emit. Never raise, never exit non-zero."""
    sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
    import detect

    try:
        _drain_stdin()
        detection = detect.detect_substitutions()
        message = detect.compose_message(detection)
        emit(message)
    except Exception:
        sys.stdout.write("{}")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
