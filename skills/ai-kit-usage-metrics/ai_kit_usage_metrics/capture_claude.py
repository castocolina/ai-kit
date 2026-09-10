"""Lossless Claude Code session-JSONL capture."""

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


def _envelope(source_file: str, source_line: int, raw_text: str, captured_at: str) -> dict:
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError:
        return {
            "raw_ref": f"claude:{source_file}:{source_line}",
            "captured_at": captured_at,
            "runtime": "claude",
            "source_file": source_file,
            "source_line": source_line,
            "parse_status": "malformed",
            "raw_text": raw_text,
            "payload": None,
        }
    if isinstance(payload, dict) and payload.get("type") == "queue-operation":
        status = "recognized_no_data"
    else:
        status = "ok"
    return {
        "raw_ref": f"claude:{source_file}:{source_line}",
        "captured_at": captured_at,
        "runtime": "claude",
        "source_file": source_file,
        "source_line": source_line,
        "parse_status": status,
        "raw_text": raw_text,
        "payload": payload,
    }


def capture(env: dict, cursor: dict) -> CaptureResult:
    """Glob `projects/*/*.jsonl` and emit one envelope per new line.

    A missing projects directory is zero records, not an error. A present but
    unreadable file is skipped and counted. A present but unreadable-as-JSON
    line is still captured (`parse_status="malformed"`) so the pipeline stays
    lossless (D-02).
    """
    stats = _empty_stats()
    records: list[dict] = []
    new_cursor = dict(cursor)
    projects = paths.claude_projects_dir(env)
    if not os.path.isdir(projects):
        return CaptureResult(records=[], cursor=new_cursor, stats=stats)

    captured_at = _now_iso()
    pattern = os.path.join(projects, "*", "*.jsonl")
    for path in sorted(glob.glob(pattern)):
        try:
            with open(path, encoding="utf-8", errors="strict") as handle:
                lines = handle.readlines()
        except (OSError, UnicodeDecodeError):
            stats["unreadable_files"].append(path)
            continue
        start = int(new_cursor.get(path, 0) or 0)
        for index, line in enumerate(lines, start=1):
            if index <= start:
                continue
            rec = _envelope(path, index, line.rstrip("\r\n"), captured_at)
            records.append(rec)
            stats["captured"] += 1
            if rec["parse_status"] == "malformed":
                stats["malformed"] += 1
            elif rec["parse_status"] == "recognized_no_data":
                stats["recognized_no_data"] += 1
        new_cursor[path] = len(lines)
    return CaptureResult(records=records, cursor=new_cursor, stats=stats)
