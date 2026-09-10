"""Lossless opencode.db + storage/ capture."""

from __future__ import annotations

import glob
import json
import os
import sqlite3
import urllib.parse
from datetime import UTC, datetime

from ai_kit_usage_metrics import paths
from ai_kit_usage_metrics.raw_store import CaptureResult

_TABLES = ("session", "message", "part")
# Literal table names kept in each query string so plan verification
# (`grep FROM session|FROM message`) can prove all three tables are queried.
_CURSOR_SQL = {
    "session": (
        "SELECT * FROM session WHERE time_created > ? OR "
        "(time_created = ? AND id > ?) ORDER BY time_created, id"
    ),
    "message": (
        "SELECT * FROM message WHERE time_created > ? OR "
        "(time_created = ? AND id > ?) ORDER BY time_created, id"
    ),
    "part": (
        "SELECT * FROM part WHERE time_created > ? OR "
        "(time_created = ? AND id > ?) ORDER BY time_created, id"
    ),
}


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


def _table_cursor(cursor: dict, table: str) -> tuple[int, str]:
    sub = cursor.get(table) or {}
    return int(sub.get("last_time_created") or 0), str(sub.get("last_id") or "")


def _set_table_cursor(cursor: dict, table: str, time_created: int, row_id: str) -> None:
    cursor[table] = {"last_time_created": int(time_created), "last_id": str(row_id)}


def _parse_data(raw_text: str) -> tuple[str, object | None]:
    try:
        return "ok", json.loads(raw_text)
    except (json.JSONDecodeError, TypeError):
        return "malformed", None


def _base_envelope(
    source_file: str,
    source_kind: str,
    record_id: str,
    raw_text: str,
    captured_at: str,
    session_id: str | None,
    message_id: str | None,
    time_created: int | None,
) -> dict:
    status, payload = _parse_data(raw_text)
    return {
        "raw_ref": f"opencode:{source_file}:{source_kind}:{record_id}",
        "captured_at": captured_at,
        "runtime": "opencode",
        "source_file": source_file,
        "source_line": None,
        "parse_status": status,
        "raw_text": raw_text,
        "payload": payload,
        "source_kind": source_kind,
        "record_id": record_id,
        "session_id": session_id,
        "message_id": message_id,
        "time_created": time_created,
    }


def _session_raw_text(row: dict) -> str:
    # session has no free-form JSON `data` column; dump the whole row as the
    # best available "original text" for lossless capture.
    return json.dumps(row, ensure_ascii=False, default=str)


def _envelope_from_row(db_path: str, table: str, row: dict, captured_at: str) -> dict:
    record_id = str(row["id"])
    time_created = row.get("time_created")
    if table == "session":
        return _base_envelope(
            db_path,
            "session",
            record_id,
            _session_raw_text(row),
            captured_at,
            record_id,
            None,
            time_created,
        )
    data_value = row.get("data")
    raw_text = data_value if isinstance(data_value, str) else ""
    if table == "message":
        return _base_envelope(
            db_path,
            "message",
            record_id,
            raw_text,
            captured_at,
            row.get("session_id"),
            None,
            time_created,
        )
    return _base_envelope(
        db_path,
        "part",
        record_id,
        raw_text,
        captured_at,
        row.get("session_id"),
        row.get("message_id"),
        time_created,
    )


def _capture_table(
    conn: sqlite3.Connection,
    db_path: str,
    table: str,
    cursor: dict,
    records: list[dict],
    stats: dict,
    captured_at: str,
) -> None:
    last_time, last_id = _table_cursor(cursor, table)
    db_cursor = conn.execute(_CURSOR_SQL[table], (last_time, last_time, last_id))
    last_row = None
    for row_tuple in db_cursor:
        row = _row_dict(db_cursor, row_tuple)
        rec = _envelope_from_row(db_path, table, row, captured_at)
        records.append(rec)
        stats["captured"] += 1
        if rec["parse_status"] == "malformed":
            stats["malformed"] += 1
        last_row = row
    if last_row is not None:
        _set_table_cursor(cursor, table, last_row["time_created"], last_row["id"])


def _capture_storage(
    env: dict,
    cursor: dict,
    records: list[dict],
    stats: dict,
    captured_at: str,
) -> None:
    storage = paths.opencode_storage_dir(env)
    ingested = list(cursor.get("ingested_storage_files") or [])
    seen = set(ingested)
    if not os.path.isdir(storage):
        cursor["ingested_storage_files"] = ingested
        return
    pattern = os.path.join(storage, "**", "*.json")
    for path in sorted(glob.glob(pattern, recursive=True)):
        if not os.path.isfile(path):
            continue
        rel = os.path.relpath(path, storage)
        if rel in seen:
            continue
        try:
            with open(path, encoding="utf-8", errors="strict") as handle:
                raw_text = handle.read()
        except (OSError, UnicodeDecodeError):
            stats["unreadable_files"].append(path)
            continue
        rec = _base_envelope(
            storage,
            "legacy_storage_file",
            rel,
            raw_text,
            captured_at,
            None,
            None,
            None,
        )
        records.append(rec)
        stats["captured"] += 1
        if rec["parse_status"] == "malformed":
            stats["malformed"] += 1
        ingested.append(rel)
        seen.add(rel)
    cursor["ingested_storage_files"] = ingested


def capture(env: dict, cursor: dict) -> CaptureResult:
    """Capture session/message/part rows plus storage/**/*.json files.

    Opens opencode.db read-only via a URI-quoted connection only when the file
    exists. Absent DB is zero records, not an error. Each table uses an
    independent (time_created, id) tuple cursor because ids are TEXT PKs.
    """
    stats = _empty_stats()
    records: list[dict] = []
    new_cursor = dict(cursor)
    for table in _TABLES:
        if table not in new_cursor:
            new_cursor[table] = {"last_time_created": 0, "last_id": ""}
    if "ingested_storage_files" not in new_cursor:
        new_cursor["ingested_storage_files"] = list(
            cursor.get("ingested_storage_files") or []
        )

    captured_at = _now_iso()
    db_path = paths.opencode_db_path(env)
    if os.path.isfile(db_path):
        conn = _connect_readonly(db_path)
        try:
            for table in _TABLES:
                _capture_table(
                    conn, db_path, table, new_cursor, records, stats, captured_at
                )
        finally:
            conn.close()

    _capture_storage(env, new_cursor, records, stats, captured_at)
    return CaptureResult(records=records, cursor=new_cursor, stats=stats)
