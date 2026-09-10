#!/usr/bin/env python3
"""Cursor sessionStart wrapper for the tool-substitution briefing.

Reads (and discards) the host's stdin payload, runs detect + compose, and
emits a Cursor sessionStart envelope on stdout. Every failure path exits
0 with parseable JSON — a hung or missing rtk must never block session
start.

Output schema: `{ additional_context?: string }`, from Cursor's own
already-installed `gsd-cursor-session-start.js` header. Because the field
is optional, a bare `{}` is contract-valid on this host.

Empty-output evidence, per host, rather than a uniform claim:

- Cursor: a bare `{}` is an OBSERVED live precedent. Cursor's own installed
  `gsd-cursor-session-start.js` writes that shape on its error path.
- Claude Code: the same shape is INFERRED rather than observed. The
  documented envelope makes every output field optional, so a `{}` body
  carries no recognized field and is read as a no-op.

Host coverage: Claude Code and Cursor are both wired. opencode has no
documented session-start injection point today, an accepted and documented
gap (ROADMAP SC-4, PROJECT.md Out of Scope).
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
    """Write the sessionStart envelope, or `{}` when there is nothing to say."""
    payload = {"additional_context": message} if message else {}
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
