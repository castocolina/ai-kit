"""Lossless Cursor agent-transcripts JSONL capture.

This module never reads `~/.cursor/chats/**/store.db` — that file's `blobs`
table holds opaque BLOB data with no documented or reverse-engineered
structure (live-verified 2026-09-10: `meta` table empty, `blobs` table has
no queryable sub-structure). Parsing it would produce a
confidently-labeled result this module has no basis to stand behind,
directly contradicting `PROJECT.md`'s core value. If Cursor ever documents
this format, or a future session successfully reverse-engineers it, adding
it here is additive — this module's own capture of
`agent-transcripts/*.jsonl` needs no change.
"""

from __future__ import annotations

import glob
import json
import os
from datetime import UTC, datetime

from ai_kit_usage_metrics import paths
from ai_kit_usage_metrics.raw_store import CaptureResult


def _empty_stats() -> dict:
    return {
        "captured": 0,
        "malformed": 0,
        "recognized_no_data": 0,
        "unreadable_files": [],
    }


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _session_id_from_path(file_path: str) -> str | None:
    parent = os.path.basename(os.path.dirname(file_path))
    return parent or None


def _envelope(
    source_file: str,
    source_line: int,
    raw_text: str,
    captured_at: str,
    session_id: str | None,
) -> dict:
    try:
        payload = json.loads(raw_text)
        status = "ok"
    except json.JSONDecodeError:
        payload = None
        status = "malformed"
    return {
        "raw_ref": f"cursor:{source_file}:{source_line}",
        "captured_at": captured_at,
        "runtime": "cursor",
        "source_file": source_file,
        "source_line": source_line,
        "parse_status": status,
        "raw_text": raw_text,
        "payload": payload,
        "source_confidence": "low",
        "session_id": session_id,
        "timestamp": None,
    }


def capture(env: dict, cursor: dict) -> CaptureResult:
    """Glob `projects/*/agent-transcripts/*/*.jsonl` and emit one envelope per new line.

    A missing projects directory is zero records, not an error. A present but
    unreadable file is skipped and counted. A present but unreadable-as-JSON
    line is still captured (`parse_status="malformed"`) so the pipeline stays
    lossless (D-02). Every envelope carries `source_confidence="low"` because
    the transcript format is community-reverse-engineered, not officially
    documented.
    """
    stats = _empty_stats()
    records: list[dict] = []
    new_cursor = dict(cursor)
    projects = paths.cursor_projects_dir(env)
    if not os.path.isdir(projects):
        return CaptureResult(records=[], cursor=new_cursor, stats=stats)

    captured_at = _now_iso()
    pattern = os.path.join(projects, "*", "agent-transcripts", "*", "*.jsonl")
    for path in sorted(glob.glob(pattern)):
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8", errors="strict") as handle:
                lines = handle.readlines()
        except (OSError, UnicodeDecodeError):
            stats["unreadable_files"].append(path)
            continue
        session_id = _session_id_from_path(path)
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
