"""Lossless Codex rollout-JSONL capture."""

from __future__ import annotations

import glob
import json
import os
import re
from datetime import UTC, datetime

from ai_kit_usage_metrics import paths
from ai_kit_usage_metrics.raw_store import CaptureResult

_SESSION_UUID_RE = re.compile(
    r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\.jsonl$",
    re.IGNORECASE,
)


def _empty_stats() -> dict:
    return {
        "captured": 0,
        "malformed": 0,
        "recognized_no_data": 0,
        "unreadable_files": [],
    }


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _session_id_from_filename(file_path: str) -> str | None:
    match = _SESSION_UUID_RE.search(os.path.basename(file_path))
    if match is None:
        return None
    return match.group(1)


def _envelope(
    source_file: str,
    source_line: int,
    raw_text: str,
    captured_at: str,
    session_id: str | None,
) -> dict:
    # function_call.arguments is a JSON-encoded STRING in the live-verified
    # Codex rollout shape (verbatim capture vs. interpretation). This module
    # never json.loads that inner string — 05-04's refiner does that.
    try:
        payload = json.loads(raw_text)
        status = "ok"
    except json.JSONDecodeError:
        payload = None
        status = "malformed"
    return {
        "raw_ref": f"codex:{source_file}:{source_line}",
        "captured_at": captured_at,
        "runtime": "codex",
        "source_file": source_file,
        "source_line": source_line,
        "parse_status": status,
        "raw_text": raw_text,
        "payload": payload,
        "session_id": session_id,
    }


def capture(env: dict, cursor: dict) -> CaptureResult:
    """Glob `sessions/**/rollout-*.jsonl` and emit one envelope per new line.

    A missing sessions directory is zero records, not an error. A present but
    unreadable file is skipped and counted. A present but unreadable-as-JSON
    line is still captured (`parse_status="malformed"`) so the pipeline stays
    lossless (D-02).
    """
    stats = _empty_stats()
    records: list[dict] = []
    new_cursor = dict(cursor)
    sessions = paths.codex_sessions_dir(env)
    if not os.path.isdir(sessions):
        return CaptureResult(records=[], cursor=new_cursor, stats=stats)

    captured_at = _now_iso()
    pattern = os.path.join(sessions, "**", "rollout-*.jsonl")
    for path in sorted(glob.glob(pattern, recursive=True)):
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8", errors="strict") as handle:
                lines = handle.readlines()
        except (OSError, UnicodeDecodeError):
            stats["unreadable_files"].append(path)
            continue
        session_id = _session_id_from_filename(path)
        start = int(new_cursor.get(path, 0) or 0)
        for index, line in enumerate(lines, start=1):
            if index <= start:
                continue
            rec = _envelope(
                path, index, line.rstrip("\r\n"), captured_at, session_id
            )
            records.append(rec)
            stats["captured"] += 1
            if rec["parse_status"] == "malformed":
                stats["malformed"] += 1
            elif rec["parse_status"] == "recognized_no_data":
                stats["recognized_no_data"] += 1
        new_cursor[path] = len(lines)
    return CaptureResult(records=records, cursor=new_cursor, stats=stats)
