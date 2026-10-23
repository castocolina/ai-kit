"""Lossless rtk history.db + tee/ capture."""

from __future__ import annotations

import glob
import hashlib
import json
import os
import re
import sqlite3
import urllib.parse
from datetime import UTC, datetime
from typing import NamedTuple

from ai_kit_usage_metrics import paths
from ai_kit_usage_metrics.raw_store import CaptureResult

_TEE_EPOCH_RE = re.compile(r"^(\d+)_(.+)\.log$")


class _RtkEnvelopeArgs(NamedTuple):
    source_file: str
    source_type: str
    record_id: str
    payload: dict
    captured_at: str
    raw_text: str


class _RtkDbSource(NamedTuple):
    conn: sqlite3.Connection
    db_path: str
    cursor: dict
    records: list[dict]
    stats: dict
    captured_at: str


class _RtkTeeSource(NamedTuple):
    env: dict
    cursor: dict
    records: list[dict]
    stats: dict
    captured_at: str


def _empty_stats() -> dict:
    return {
        "captured": 0,
        "malformed": 0,
        "recognized_no_data": 0,
        "unreadable_files": [],
    }


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _connect_readonly(path: str) -> sqlite3.Connection:
    uri = f"file:{urllib.parse.quote(path)}?mode=ro"
    return sqlite3.connect(uri, uri=True)


def _row_dict(cursor: sqlite3.Cursor, row: tuple) -> dict:
    return {col[0]: row[i] for i, col in enumerate(cursor.description)}


def _envelope(args: _RtkEnvelopeArgs) -> dict:
    return {
        "raw_ref": f"rtk:{args.source_file}:{args.source_type}:{args.record_id}",
        "captured_at": args.captured_at,
        "runtime": "rtk",
        "source_file": args.source_file,
        "source_line": None,
        "parse_status": "ok",
        "raw_text": args.raw_text,
        "payload": args.payload,
    }


def _capture_commands(source: _RtkDbSource) -> None:
    last_id = int(source.cursor.get("last_command_id") or 0)
    db_cursor = source.conn.execute(
        "SELECT * FROM commands WHERE id > ? ORDER BY id",
        (last_id,),
    )
    for row_tuple in db_cursor:
        row = _row_dict(db_cursor, row_tuple)
        payload = dict(row)
        payload["source_type"] = "history"
        raw_text = json.dumps(row, ensure_ascii=False, default=str)
        source.records.append(
            _envelope(
                _RtkEnvelopeArgs(
                    source.db_path,
                    "history",
                    str(row["id"]),
                    payload,
                    source.captured_at,
                    raw_text,
                )
            )
        )
        source.stats["captured"] += 1
        last_id = int(row["id"])
    source.cursor["last_command_id"] = last_id


def _capture_parse_failures(source: _RtkDbSource) -> None:
    last_id = int(source.cursor.get("last_parse_failure_id") or 0)
    db_cursor = source.conn.execute(
        "SELECT * FROM parse_failures WHERE id > ? ORDER BY id",
        (last_id,),
    )
    for row_tuple in db_cursor:
        row = _row_dict(db_cursor, row_tuple)
        payload = dict(row)
        payload["source_type"] = "parse_failure"
        raw_text = json.dumps(row, ensure_ascii=False, default=str)
        source.records.append(
            _envelope(
                _RtkEnvelopeArgs(
                    source.db_path,
                    "parse_failure",
                    str(row["id"]),
                    payload,
                    source.captured_at,
                    raw_text,
                )
            )
        )
        source.stats["captured"] += 1
        last_id = int(row["id"])
    source.cursor["last_parse_failure_id"] = last_id


def _tee_filename_fields(basename: str) -> tuple[int | None, str]:
    match = _TEE_EPOCH_RE.match(basename)
    if match:
        return int(match.group(1)), match.group(2)
    return None, basename


def _read_tee_file(path: str, stats: dict) -> bytes | None:
    try:
        with open(path, "rb") as handle:
            return handle.read()
    except OSError:
        stats["unreadable_files"].append(path)
        return None


def _tee_record_from_file(
    path: str,
    file_bytes: bytes,
    captured_at: str,
) -> tuple[dict, str, str]:
    basename = os.path.basename(path)
    digest = hashlib.sha256(file_bytes).hexdigest()
    try:
        content = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        content = file_bytes.decode("utf-8", errors="replace")
    epoch, hint = _tee_filename_fields(basename)
    payload = {
        "source_type": "tee",
        "filename": basename,
        "sha256": digest,
        "captured_epoch": epoch,
        "filename_hint": hint,
        "content": content,
    }
    rec = _envelope(
        _RtkEnvelopeArgs(path, "tee", f"{basename}:{digest}", payload, captured_at, content)
    )
    return rec, basename, digest


def _capture_tee(source: _RtkTeeSource) -> None:
    tee_dir = paths.rtk_tee_dir(source.env)
    ingested = list(source.cursor.get("ingested_tee_files") or [])
    seen = {(entry["filename"], entry["sha256"]) for entry in ingested if isinstance(entry, dict)}
    if not os.path.isdir(tee_dir):
        source.cursor["ingested_tee_files"] = ingested
        return
    pattern = os.path.join(tee_dir, "*.log")
    for path in sorted(glob.glob(pattern)):
        if not os.path.isfile(path):
            continue
        file_bytes = _read_tee_file(path, source.stats)
        if file_bytes is None:
            continue
        rec, basename, digest = _tee_record_from_file(path, file_bytes, source.captured_at)
        if (basename, digest) in seen:
            continue
        source.records.append(rec)
        source.stats["captured"] += 1
        ingested.append({"filename": basename, "sha256": digest})
        seen.add((basename, digest))
    source.cursor["ingested_tee_files"] = ingested


def capture(env: dict, cursor: dict) -> CaptureResult:
    """Capture rtk history.db commands/parse_failures plus tee/*.log files.

    Each sub-source is independently short-circuited when absent. history.db
    opens read-only via a URI-quoted connection. Tee idempotency is
    (filename, sha256) membership so a rewritten file is re-captured.
    """
    stats = _empty_stats()
    records: list[dict] = []
    new_cursor = {
        "last_command_id": int(cursor.get("last_command_id") or 0),
        "last_parse_failure_id": int(cursor.get("last_parse_failure_id") or 0),
        "ingested_tee_files": list(cursor.get("ingested_tee_files") or []),
    }
    captured_at = _now_iso()

    db_path = paths.rtk_history_db_path(env)
    if os.path.isfile(db_path):
        conn = _connect_readonly(db_path)
        try:
            db_source = _RtkDbSource(conn, db_path, new_cursor, records, stats, captured_at)
            _capture_commands(db_source)
            _capture_parse_failures(db_source)
        finally:
            conn.close()

    tee_source = _RtkTeeSource(env, new_cursor, records, stats, captured_at)
    _capture_tee(tee_source)
    return CaptureResult(records=records, cursor=new_cursor, stats=stats)
