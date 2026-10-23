#!/usr/bin/env python3
"""Measure-only Claude logging hook (21.2 PCH-02, D-17).

Runs as `python3 -S`. Reads the hook payload on stdin, appends one JSON line
to the file named by AI_KIT_MEASURE_LOG and prints `{}`. Never blocks, never
writes anything when AI_KIT_MEASURE_LOG is unset. Fail-open: any error prints
`{}` and exits 0.
"""
import json
import os
import sys
import time


def _record(payload, path):
    entry = {
        "ts_wall": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "ts_mono_ns": time.monotonic_ns(),
        "event": payload.get("hook_event_name"),
        "trigger": payload.get("trigger"),
        "source": payload.get("source"),
        "session_id": payload.get("session_id"),
        "compact_summary_chars": len(payload["compact_summary"])
        if isinstance(payload.get("compact_summary"), str) else None,
    }
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")


def _fail_open(exc_type, exc_value, exc_tb):
    print("{}")
    sys.exit(0)


def main():
    sys.excepthook = _fail_open
    data = sys.stdin.read()
    payload = json.loads(data) if data.strip() else {}
    path = os.environ.get("AI_KIT_MEASURE_LOG")
    if path:
        _record(payload, path)
    print("{}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
