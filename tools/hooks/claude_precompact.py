#!/usr/bin/env python3
"""Claude Code PreCompact / SessionStart(compact) hook for the pre-summary (D-05).

One script, two wired entries. ``PreCompact`` (matchers ``manual|auto``) prepares
the classified pre-summary file through ``precompact_core.run_claude`` and prints
``{}``. ``SessionStart`` with source ``compact`` injects that session's file as
``additionalContext`` and deletes it. A compaction must never be blocked: no path
prints a ``decision`` field, every path exits 0, and uncaught errors reach the
shared ``_fail_open`` excepthook. Claude Code still writes its own compaction
summary; this hook only adds context after it.
"""

import contextlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
# pylint: disable=wrong-import-position
import precompact_core
from claude_session_start import _fail_open, emit, read_stdin


def _read_payload():
    """The hook event payload from stdin, or None when it is not a JSON object."""
    try:
        payload = json.loads(read_stdin().decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


def _session_files(directory, session_id):
    """Every file of this session: name prefix/suffix match plus the in-file header's
    session_id equality, so an id that is a prefix of another never matches (T-21.2-15)."""
    matched = []
    try:
        entries = list(os.scandir(directory))
    except OSError:
        return matched
    for entry in entries:
        name = entry.name
        if not (name.startswith(f"{session_id}-") and name.endswith("-compact.md")):
            continue
        header = precompact_core.read_header(entry.path)
        if header and header.get("session_id") == session_id:
            try:
                matched.append((entry.stat().st_mtime, entry.path))
            except OSError:
                continue
    return matched


def _read_newest(matched):
    """The newest matched file's text (None on a read error), plus every path to delete."""
    newest_path = max(matched)[1]
    try:
        with open(newest_path, encoding="utf-8", errors="replace") as handle:
            text = handle.read()
    except OSError:
        text = None
    return text, [path for _mtime, path in matched]


def inject(payload, env):
    """The compact-SessionStart injector: this session's pre-summary text, or None.

    No file for this session -> None -> the host prints ``{}``. Every matched file
    is deleted after reading; a body over CAP_CHARS is never injected and is deleted."""
    session_id = payload.get("session_id")
    if not precompact_core.safe_session_id(session_id):
        return None
    directory = precompact_core.private_dir(env)
    if directory is None:
        return None
    precompact_core.sweep(directory)
    matched = _session_files(directory, session_id)
    if not matched:
        return None
    text, paths = _read_newest(matched)
    for path in paths:
        with contextlib.suppress(OSError):
            os.unlink(path)
    if text is None or len(text) > precompact_core.CAP_CHARS:
        return None
    return text


def _print_empty():
    sys.stdout.write("{}")
    sys.stdout.flush()


def main():
    """Branch on the event: PreCompact prepares, compact SessionStart injects."""
    payload = _read_payload()
    event = payload.get("hook_event_name") if payload else None
    if event == "PreCompact":
        precompact_core.run_claude(payload, dict(os.environ))
        _print_empty()
        return 0
    if event == "SessionStart" and payload.get("source") == "compact":
        emit(inject(payload, dict(os.environ)))
        return 0
    _print_empty()
    return 0


if __name__ == "__main__":
    sys.excepthook = _fail_open
    raise SystemExit(main())
