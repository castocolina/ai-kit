import json
import os
import re
import shutil
import sqlite3
import stat
import sys
import tempfile
import tomllib
import unittest
from datetime import UTC, datetime
from unittest.mock import patch

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-usage-metrics"),
)

from ai_kit_usage_metrics import (
    capture_claude,
    capture_codex,
    capture_cursor,
    capture_opencode,
    capture_rtk,
    family,
    paths,
    pricing,
    raw_store,
    refined_store,
)
from ai_kit_usage_metrics.cli import CAPTURE_SOURCES, main
from ai_kit_usage_metrics.dashboard import generate
from ai_kit_usage_metrics.raw_store import CaptureResult
from ai_kit_usage_metrics.refiner import refine_simple_commands

SIMPLE_COMMAND = "ls -la"
COMPOUND_COMMAND = "ls && echo hi"
SCRIPT_COMMAND = "</script>alert(1)</script>"
SESSION_ID = "sess-simple-1"
TURN_UUID = "turn-uuid-1"
TOOL_USE_ID = "toolu_01"
MODEL = "claude-opus-4-7"
CWD = "/tmp/proj"
TS_USE = "2026-09-10T12:00:00.000Z"
TS_RESULT = "2026-09-10T12:00:01.500Z"


def _scratch_env(root):
    return {
        "HOME": os.path.join(root, "home"),
        "XDG_DATA_HOME": os.path.join(root, "data"),
        "XDG_CACHE_HOME": os.path.join(root, "cache"),
        "CLAUDE_CONFIG_DIR": os.path.join(root, "claude"),
    }


def _write_session(env, project, filename, lines):
    directory = os.path.join(paths.claude_projects_dir(env), project)
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, filename)
    with open(path, "w", encoding="utf-8") as handle:
        for line in lines:
            handle.write(line if line.endswith("\n") else line + "\n")
    return path


def _assistant_bash_line(command, session_id=SESSION_ID, uuid=TURN_UUID, tool_id=TOOL_USE_ID,
                         timestamp=TS_USE, model=MODEL, cwd=CWD, extra_input=None):
    tool_input = {"command": command} if extra_input is None else extra_input
    payload = {
        "type": "assistant",
        "message": {
            "model": model,
            "content": [
                {
                    "type": "tool_use",
                    "id": tool_id,
                    "name": "Bash",
                    "input": tool_input,
                }
            ],
            "usage": {"input_tokens": 100, "output_tokens": 50},
        },
        "uuid": uuid,
        "timestamp": timestamp,
        "cwd": cwd,
        "sessionId": session_id,
    }
    return json.dumps(payload)


def _tool_result_line(tool_id=TOOL_USE_ID, session_id=SESSION_ID, timestamp=TS_RESULT, cwd=CWD):
    payload = {
        "type": "user",
        "message": {
            "content": [
                {"type": "tool_result", "tool_use_id": tool_id, "content": "ok"}
            ]
        },
        "uuid": "user-uuid-1",
        "timestamp": timestamp,
        "cwd": cwd,
        "sessionId": session_id,
    }
    return json.dumps(payload)


def _queue_operation_line(session_id="sess-queue"):
    return json.dumps(
        {
            "type": "queue-operation",
            "operation": "enqueue",
            "timestamp": TS_USE,
            "sessionId": session_id,
        }
    )


def _count_jsonl_lines(path):
    with open(path, encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def _refined_row_count(env):
    conn = sqlite3.connect(paths.refined_db_path(env))
    try:
        return conn.execute("SELECT COUNT(*) FROM refined_commands").fetchone()[0]
    finally:
        conn.close()


class TestPaths(unittest.TestCase):
    def test_usage_metrics_base_honors_xdg_data_home(self):
        env = {"XDG_DATA_HOME": "/scratch/xdg-data", "HOME": "/scratch/home"}
        self.assertEqual(
            paths.usage_metrics_base(env),
            os.path.join("/scratch/xdg-data", "ai-kit", "usage-metrics"),
        )

    def test_usage_metrics_base_falls_back_to_home(self):
        env = {"HOME": "/scratch/home"}
        self.assertEqual(
            paths.usage_metrics_base(env),
            os.path.join("/scratch/home", ".local", "share", "ai-kit", "usage-metrics"),
        )

    def test_claude_projects_dir_honors_claude_config_dir(self):
        env = {"CLAUDE_CONFIG_DIR": "/scratch/claude", "HOME": "/scratch/home"}
        self.assertEqual(
            paths.claude_projects_dir(env),
            os.path.join("/scratch/claude", "projects"),
        )
        env = {"HOME": "/scratch/home"}
        self.assertEqual(
            paths.claude_projects_dir(env),
            os.path.join("/scratch/home", ".claude", "projects"),
        )

    def test_derived_paths(self):
        env = {"XDG_DATA_HOME": "/scratch/xdg-data"}
        base = paths.usage_metrics_base(env)
        self.assertEqual(paths.raw_dir(env), os.path.join(base, "raw"))
        self.assertEqual(
            paths.refined_db_path(env), os.path.join(base, "refined", "refined.db")
        )
        self.assertEqual(paths.cursors_dir(env), os.path.join(base, "cursors"))
        self.assertEqual(
            paths.dashboard_html_path(env), os.path.join(base, "dashboard.html")
        )
        self.assertEqual(
            paths.raw_jsonl_path(env, "claude"),
            os.path.join(base, "raw", "claude.jsonl"),
        )

    def test_opencode_source_paths(self):
        env = {"XDG_DATA_HOME": "/scratch/xdg-data", "HOME": "/scratch/home"}
        self.assertEqual(
            paths.opencode_db_path(env),
            os.path.join("/scratch/xdg-data", "opencode", "opencode.db"),
        )
        self.assertEqual(
            paths.opencode_storage_dir(env),
            os.path.join("/scratch/xdg-data", "opencode", "storage"),
        )
        env = {"HOME": "/scratch/home"}
        self.assertEqual(
            paths.opencode_db_path(env),
            os.path.join("/scratch/home", ".local", "share", "opencode", "opencode.db"),
        )
        self.assertEqual(
            paths.opencode_storage_dir(env),
            os.path.join("/scratch/home", ".local", "share", "opencode", "storage"),
        )

    def test_rtk_source_paths(self):
        env = {"XDG_DATA_HOME": "/scratch/xdg-data", "HOME": "/scratch/home"}
        self.assertEqual(
            paths.rtk_history_db_path(env),
            os.path.join("/scratch/xdg-data", "rtk", "history.db"),
        )
        self.assertEqual(
            paths.rtk_tee_dir(env),
            os.path.join("/scratch/xdg-data", "rtk", "tee"),
        )
        env = {"HOME": "/scratch/home"}
        self.assertEqual(
            paths.rtk_history_db_path(env),
            os.path.join("/scratch/home", ".local", "share", "rtk", "history.db"),
        )
        self.assertEqual(
            paths.rtk_tee_dir(env),
            os.path.join("/scratch/home", ".local", "share", "rtk", "tee"),
        )

    def test_codex_sessions_dir_honors_codex_home(self):
        env = {"CODEX_HOME": "/scratch/codex", "HOME": "/scratch/home"}
        self.assertEqual(
            paths.codex_sessions_dir(env),
            os.path.join("/scratch/codex", "sessions"),
        )
        env = {"HOME": "/scratch/home"}
        self.assertEqual(
            paths.codex_sessions_dir(env),
            os.path.join("/scratch/home", ".codex", "sessions"),
        )

    def test_cursor_projects_dir_honors_cursor_config_dir_not_xdg(self):
        env = {
            "CURSOR_CONFIG_DIR": "/scratch/cursor",
            "HOME": "/scratch/home",
            "XDG_CONFIG_HOME": "/scratch/xdg-config",
        }
        self.assertEqual(
            paths.cursor_projects_dir(env),
            os.path.join("/scratch/cursor", "projects"),
        )
        env = {"HOME": "/scratch/home", "XDG_CONFIG_HOME": "/scratch/xdg-config"}
        self.assertEqual(
            paths.cursor_projects_dir(env),
            os.path.join("/scratch/home", ".cursor", "projects"),
        )
        self.assertNotEqual(
            paths.cursor_projects_dir(env),
            os.path.join("/scratch/xdg-config", "cursor", "projects"),
        )


class TestFamily(unittest.TestCase):
    def test_rg_and_grep_share_grep_family(self):
        self.assertEqual(family.family_of("grep -r x"), "grep")
        self.assertEqual(family.family_of("rg -r x"), "grep")
        self.assertEqual(family.family_of("/usr/bin/rg -r x"), "grep")

    def test_unmatched_command_is_its_own_family(self):
        self.assertEqual(family.family_of("git status"), "git")


class TestCapture(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="ai-kit-um-capture-")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.env = _scratch_env(self.root)

    def test_missing_directory_returns_empty_result(self):
        result = capture_claude.capture(self.env, {})
        self.assertIsInstance(result, CaptureResult)
        self.assertEqual(result.records, [])
        self.assertEqual(result.cursor, {})
        self.assertEqual(result.stats["captured"], 0)
        self.assertEqual(result.stats["malformed"], 0)
        self.assertEqual(result.stats["recognized_no_data"], 0)
        self.assertEqual(result.stats["unreadable_files"], [])

    def test_simple_bash_and_lossless_queue_operation_and_malformed(self):
        simple_path = _write_session(
            self.env,
            "proj-a",
            "session-a.jsonl",
            [_assistant_bash_line(SIMPLE_COMMAND), _tool_result_line()],
        )
        malformed_text = "this is not json{{{"
        mixed_path = _write_session(
            self.env,
            "proj-b",
            "session-b.jsonl",
            [_queue_operation_line(), malformed_text],
        )

        result = capture_claude.capture(self.env, {})
        self.assertIsInstance(result, CaptureResult)
        self.assertTrue(hasattr(result, "records"))
        self.assertTrue(hasattr(result, "cursor"))
        self.assertTrue(hasattr(result, "stats"))
        self.assertGreaterEqual(result.stats["captured"], 4)
        self.assertEqual(result.stats["malformed"], 1)
        self.assertEqual(result.stats["recognized_no_data"], 1)
        self.assertEqual(result.cursor[simple_path], 2)
        self.assertEqual(result.cursor[mixed_path], 2)

        by_status = {}
        for rec in result.records:
            self.assertIn("raw_ref", rec)
            self.assertIn("captured_at", rec)
            self.assertIn("runtime", rec)
            self.assertIn("source_file", rec)
            self.assertIn("source_line", rec)
            self.assertIn("parse_status", rec)
            self.assertIn("raw_text", rec)
            self.assertIn("payload", rec)
            by_status.setdefault(rec["parse_status"], []).append(rec)

        self.assertGreaterEqual(len(by_status.get("ok", [])), 2)
        recognized = by_status["recognized_no_data"]
        self.assertEqual(len(recognized), 1)
        self.assertIsNotNone(recognized[0]["payload"])
        self.assertEqual(recognized[0]["payload"]["type"], "queue-operation")
        self.assertIn("queue-operation", recognized[0]["raw_text"])
        self.assertTrue(recognized[0]["raw_ref"].startswith("claude:"))

        malformed = by_status["malformed"]
        self.assertEqual(len(malformed), 1)
        self.assertIsNone(malformed[0]["payload"])
        self.assertEqual(malformed[0]["raw_text"], malformed_text)
        self.assertTrue(malformed[0]["raw_ref"].startswith("claude:"))

    def test_unreadable_utf8_file_is_skipped_and_reported(self):
        simple_path = _write_session(
            self.env,
            "proj-a",
            "session-a.jsonl",
            [_assistant_bash_line(SIMPLE_COMMAND), _tool_result_line()],
        )
        bad_dir = os.path.join(paths.claude_projects_dir(self.env), "proj-bin")
        os.makedirs(bad_dir, exist_ok=True)
        bad_path = os.path.join(bad_dir, "binary.jsonl")
        with open(bad_path, "wb") as handle:
            handle.write(b"\xff\xfe\x00\x01 not utf-8")
        result = capture_claude.capture(self.env, {})
        self.assertIn(bad_path, result.stats["unreadable_files"])
        self.assertTrue(any(rec["source_file"] == simple_path for rec in result.records))
        self.assertFalse(any(rec["source_file"] == bad_path for rec in result.records))


_OPENCODE_SESSION_ID = "ses_fixture_1"
_OPENCODE_MESSAGE_ID = "msg_fixture_1"
_OPENCODE_PART_BASH_ID = "prt_bash_1"
_OPENCODE_PART_TEXT_ID = "prt_text_1"
_OPENCODE_PART_BAD_ID = "prt_bad_1"
_OPENCODE_TIME = 1789000000000
_OPENCODE_BASH_DATA = (
    '{"type":"tool","tool":"bash","callID":"call_1",'
    '"state":{"status":"completed","input":{"command":"ls -la","workdir":"/tmp"},'
    '"output":"ok","metadata":{"exit":0,"truncated":false},'
    '"time":{"start":1789000000000,"end":1789000000500}}}'
)
_OPENCODE_TEXT_DATA = '{"type":"text","text":"hello"}'
_OPENCODE_MALFORMED_DATA = "this is not json{{{"
_OPENCODE_MESSAGE_DATA = (
    '{"role":"assistant","cost":0,'
    '"tokens":{"total":10,"input":5,"output":5,"reasoning":0,'
    '"cache":{"write":0,"read":0}},'
    '"modelID":"claude-opus-4-7","providerID":"anthropic",'
    '"path":{"cwd":"/tmp","root":"/tmp"},'
    '"time":{"created":1789000000000,"completed":1789000000500},'
    '"finish":"stop"}'
)


def _opencode_schema_sql():
    return """
    CREATE TABLE session (
        id TEXT PRIMARY KEY,
        project_id TEXT,
        workspace_id TEXT,
        directory TEXT,
        title TEXT,
        cost REAL,
        tokens_input INTEGER,
        tokens_output INTEGER,
        tokens_reasoning INTEGER,
        tokens_cache_read INTEGER,
        tokens_cache_write INTEGER,
        model TEXT,
        time_created INTEGER,
        time_updated INTEGER
    );
    CREATE TABLE message (
        id TEXT PRIMARY KEY,
        session_id TEXT,
        time_created INTEGER,
        time_updated INTEGER,
        data TEXT
    );
    CREATE TABLE part (
        id TEXT PRIMARY KEY,
        message_id TEXT,
        session_id TEXT,
        time_created INTEGER,
        time_updated INTEGER,
        data TEXT
    );
    """


def _write_opencode_db(env, seed_fn):
    db_path = paths.opencode_db_path(env)
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(_opencode_schema_sql())
        seed_fn(conn)
        conn.commit()
    finally:
        conn.close()
    return db_path


def _seed_standard_opencode(conn):
    conn.execute(
        "INSERT INTO session (id, project_id, directory, title, model, "
        "time_created, time_updated) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            _OPENCODE_SESSION_ID,
            "prj_1",
            "/tmp",
            "fixture",
            "claude-opus-4-7",
            _OPENCODE_TIME,
            _OPENCODE_TIME,
        ),
    )
    conn.execute(
        "INSERT INTO message (id, session_id, time_created, time_updated, data) "
        "VALUES (?, ?, ?, ?, ?)",
        (
            _OPENCODE_MESSAGE_ID,
            _OPENCODE_SESSION_ID,
            _OPENCODE_TIME,
            _OPENCODE_TIME,
            _OPENCODE_MESSAGE_DATA,
        ),
    )
    conn.execute(
        "INSERT INTO part (id, message_id, session_id, time_created, time_updated, data) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            _OPENCODE_PART_BASH_ID,
            _OPENCODE_MESSAGE_ID,
            _OPENCODE_SESSION_ID,
            _OPENCODE_TIME,
            _OPENCODE_TIME,
            _OPENCODE_BASH_DATA,
        ),
    )
    conn.execute(
        "INSERT INTO part (id, message_id, session_id, time_created, time_updated, data) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            _OPENCODE_PART_TEXT_ID,
            _OPENCODE_MESSAGE_ID,
            _OPENCODE_SESSION_ID,
            _OPENCODE_TIME + 1,
            _OPENCODE_TIME + 1,
            _OPENCODE_TEXT_DATA,
        ),
    )
    conn.execute(
        "INSERT INTO part (id, message_id, session_id, time_created, time_updated, data) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            _OPENCODE_PART_BAD_ID,
            _OPENCODE_MESSAGE_ID,
            _OPENCODE_SESSION_ID,
            _OPENCODE_TIME + 2,
            _OPENCODE_TIME + 2,
            _OPENCODE_MALFORMED_DATA,
        ),
    )


class TestCaptureOpencode(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="ai-kit-um-opencode-")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.env = _scratch_env(self.root)

    def test_absent_db_returns_zero_without_connecting(self):
        with patch("sqlite3.connect", side_effect=AssertionError("must not connect")):
            result = capture_opencode.capture(self.env, {})
        self.assertIsInstance(result, CaptureResult)
        self.assertEqual(result.records, [])
        self.assertEqual(result.stats["captured"], 0)
        self.assertEqual(result.stats["malformed"], 0)

    def test_session_message_part_lossless_and_verbatim(self):
        db_path = _write_opencode_db(self.env, _seed_standard_opencode)
        result = capture_opencode.capture(self.env, {})
        self.assertIsInstance(result, CaptureResult)
        self.assertEqual(len(result.records), 5)
        self.assertEqual(result.stats["captured"], 5)
        self.assertEqual(result.stats["malformed"], 1)

        by_kind = {}
        by_status = {}
        for rec in result.records:
            for key in (
                "raw_ref",
                "captured_at",
                "runtime",
                "source_file",
                "source_line",
                "parse_status",
                "raw_text",
                "payload",
                "source_kind",
                "record_id",
                "session_id",
                "message_id",
                "time_created",
            ):
                self.assertIn(key, rec)
            self.assertEqual(rec["runtime"], "opencode")
            by_kind.setdefault(rec["source_kind"], []).append(rec)
            by_status.setdefault(rec["parse_status"], []).append(rec)

        self.assertEqual(len(by_kind["session"]), 1)
        self.assertEqual(len(by_kind["message"]), 1)
        self.assertEqual(len(by_kind["part"]), 3)
        self.assertEqual(len(by_status["ok"]), 4)
        self.assertEqual(len(by_status["malformed"]), 1)

        session = by_kind["session"][0]
        self.assertEqual(session["record_id"], _OPENCODE_SESSION_ID)
        self.assertEqual(session["session_id"], _OPENCODE_SESSION_ID)
        self.assertIsNone(session["message_id"])
        self.assertEqual(session["time_created"], _OPENCODE_TIME)
        self.assertEqual(
            session["raw_ref"],
            f"opencode:{db_path}:session:{_OPENCODE_SESSION_ID}",
        )
        self.assertEqual(session["parse_status"], "ok")

        message = by_kind["message"][0]
        self.assertEqual(message["record_id"], _OPENCODE_MESSAGE_ID)
        self.assertEqual(message["session_id"], _OPENCODE_SESSION_ID)
        self.assertIsNone(message["message_id"])
        self.assertEqual(message["raw_text"], _OPENCODE_MESSAGE_DATA)
        self.assertEqual(message["parse_status"], "ok")
        self.assertEqual(
            message["raw_ref"],
            f"opencode:{db_path}:message:{_OPENCODE_MESSAGE_ID}",
        )

        parts = {rec["record_id"]: rec for rec in by_kind["part"]}
        bash = parts[_OPENCODE_PART_BASH_ID]
        self.assertEqual(bash["session_id"], _OPENCODE_SESSION_ID)
        self.assertEqual(bash["message_id"], _OPENCODE_MESSAGE_ID)
        self.assertEqual(bash["raw_text"], _OPENCODE_BASH_DATA)
        self.assertEqual(bash["parse_status"], "ok")
        self.assertEqual(bash["payload"]["tool"], "bash")

        text = parts[_OPENCODE_PART_TEXT_ID]
        self.assertEqual(text["session_id"], _OPENCODE_SESSION_ID)
        self.assertEqual(text["message_id"], _OPENCODE_MESSAGE_ID)
        self.assertEqual(text["raw_text"], _OPENCODE_TEXT_DATA)
        self.assertEqual(text["parse_status"], "ok")

        bad = parts[_OPENCODE_PART_BAD_ID]
        self.assertEqual(bad["raw_text"], _OPENCODE_MALFORMED_DATA)
        self.assertEqual(bad["parse_status"], "malformed")
        self.assertIsNone(bad["payload"])

        ok_parts_and_message = [
            rec
            for rec in result.records
            if rec["source_kind"] in ("part", "message") and rec["parse_status"] == "ok"
        ]
        expected_data = {
            ("message", _OPENCODE_MESSAGE_ID): _OPENCODE_MESSAGE_DATA,
            ("part", _OPENCODE_PART_BASH_ID): _OPENCODE_BASH_DATA,
            ("part", _OPENCODE_PART_TEXT_ID): _OPENCODE_TEXT_DATA,
        }
        for rec in ok_parts_and_message:
            self.assertEqual(
                rec["raw_text"],
                expected_data[(rec["source_kind"], rec["record_id"])],
            )

    def test_tuple_cursor_does_not_reyield_same_timestamp_rows(self):
        def seed(conn):
            conn.execute(
                "INSERT INTO session (id, time_created, time_updated) VALUES (?, ?, ?)",
                ("ses_a", _OPENCODE_TIME, _OPENCODE_TIME),
            )
            conn.execute(
                "INSERT INTO session (id, time_created, time_updated) VALUES (?, ?, ?)",
                ("ses_b", _OPENCODE_TIME, _OPENCODE_TIME),
            )
            conn.execute(
                "INSERT INTO message (id, session_id, time_created, time_updated, data) "
                "VALUES (?, ?, ?, ?, ?)",
                ("msg_a", "ses_a", _OPENCODE_TIME, _OPENCODE_TIME, "{}"),
            )
            conn.execute(
                "INSERT INTO part (id, message_id, session_id, time_created, time_updated, data) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                ("prt_a", "msg_a", "ses_a", _OPENCODE_TIME, _OPENCODE_TIME, "{}"),
            )
            conn.execute(
                "INSERT INTO part (id, message_id, session_id, time_created, time_updated, data) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                ("prt_b", "msg_a", "ses_a", _OPENCODE_TIME, _OPENCODE_TIME, "{}"),
            )

        _write_opencode_db(self.env, seed)
        first = capture_opencode.capture(self.env, {})
        part_ids = sorted(
            rec["record_id"] for rec in first.records if rec["source_kind"] == "part"
        )
        self.assertEqual(part_ids, ["prt_a", "prt_b"])
        session_ids = sorted(
            rec["record_id"] for rec in first.records if rec["source_kind"] == "session"
        )
        self.assertEqual(session_ids, ["ses_a", "ses_b"])
        second = capture_opencode.capture(self.env, first.cursor)
        self.assertEqual(second.records, [])
        self.assertEqual(second.stats["captured"], 0)

    def test_nested_storage_json_captured_losslessly(self):
        storage = paths.opencode_storage_dir(self.env)
        nested = os.path.join(storage, "session_diff")
        os.makedirs(nested, exist_ok=True)
        good_rel = os.path.join("session_diff", "x.json")
        bad_rel = os.path.join("session_diff", "bad.json")
        good_path = os.path.join(storage, good_rel)
        bad_path = os.path.join(storage, bad_rel)
        with open(good_path, "w", encoding="utf-8") as handle:
            handle.write("[]")
        malformed_text = "not-json{{{"
        with open(bad_path, "w", encoding="utf-8") as handle:
            handle.write(malformed_text)

        result = capture_opencode.capture(self.env, {})
        legacy = [rec for rec in result.records if rec["source_kind"] == "legacy_storage_file"]
        self.assertEqual(len(legacy), 2)
        by_id = {rec["record_id"]: rec for rec in legacy}

        good = by_id[good_rel]
        self.assertEqual(good["raw_text"], "[]")
        self.assertEqual(good["parse_status"], "ok")
        self.assertEqual(good["payload"], [])
        self.assertEqual(
            good["raw_ref"],
            f"opencode:{storage}:legacy_storage_file:{good_rel}",
        )

        bad = by_id[bad_rel]
        self.assertEqual(bad["raw_text"], malformed_text)
        self.assertEqual(bad["parse_status"], "malformed")
        self.assertIsNone(bad["payload"])

        second = capture_opencode.capture(self.env, result.cursor)
        self.assertEqual(
            [rec for rec in second.records if rec["source_kind"] == "legacy_storage_file"],
            [],
        )


_RTK_HISTORY_SCHEMA = """
CREATE TABLE commands (
    id INTEGER PRIMARY KEY,
    timestamp TEXT,
    original_cmd TEXT,
    rtk_cmd TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER,
    saved_tokens INTEGER,
    savings_pct REAL,
    exec_time_ms INTEGER,
    project_path TEXT
);
CREATE TABLE parse_failures (
    id INTEGER PRIMARY KEY,
    timestamp TEXT,
    raw_command TEXT,
    error_message TEXT,
    fallback_succeeded INTEGER
);
"""


def _write_rtk_history_db(env, seed_fn):
    db_path = paths.rtk_history_db_path(env)
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(_RTK_HISTORY_SCHEMA)
        seed_fn(conn)
        conn.commit()
    finally:
        conn.close()
    return db_path


def _seed_rtk_history(conn):
    conn.execute(
        "INSERT INTO commands (id, timestamp, original_cmd, rtk_cmd, input_tokens, "
        "output_tokens, saved_tokens, savings_pct, exec_time_ms, project_path) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            1,
            "2026-09-10T12:00:00Z",
            "ls -la",
            "ls -la",
            10,
            5,
            2,
            20.0,
            15,
            "/tmp/proj",
        ),
    )
    conn.execute(
        "INSERT INTO parse_failures (id, timestamp, raw_command, error_message, "
        "fallback_succeeded) VALUES (?, ?, ?, ?, ?)",
        (1, "2026-09-10T12:01:00Z", "weird {{{", "parse error", 0),
    )


class TestCaptureRtk(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="ai-kit-um-rtk-")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.env = _scratch_env(self.root)

    def test_neither_source_present_yields_zero(self):
        result = capture_rtk.capture(self.env, {})
        self.assertIsInstance(result, CaptureResult)
        self.assertEqual(result.records, [])
        self.assertEqual(result.stats["captured"], 0)

    def test_history_and_parse_failures_tagged(self):
        db_path = _write_rtk_history_db(self.env, _seed_rtk_history)
        result = capture_rtk.capture(self.env, {})
        self.assertEqual(len(result.records), 2)
        by_type = {rec["payload"]["source_type"]: rec for rec in result.records}
        self.assertEqual(set(by_type), {"history", "parse_failure"})

        history = by_type["history"]
        self.assertEqual(history["runtime"], "rtk")
        self.assertEqual(history["payload"]["original_cmd"], "ls -la")
        self.assertEqual(history["payload"]["id"], 1)
        self.assertTrue(history["raw_ref"].startswith(f"rtk:{db_path}:history:"))

        failure = by_type["parse_failure"]
        self.assertEqual(failure["payload"]["raw_command"], "weird {{{")
        self.assertEqual(failure["payload"]["id"], 1)
        self.assertEqual(failure["parse_status"], "ok")

        second = capture_rtk.capture(self.env, result.cursor)
        self.assertEqual(second.records, [])

    def test_tee_logs_matching_and_nonmatching_filenames(self):
        tee_dir = paths.rtk_tee_dir(self.env)
        os.makedirs(tee_dir, exist_ok=True)
        matching = "1788953554_brew_install_--help.log"
        nonmatching = "odd-name.log"
        with open(os.path.join(tee_dir, matching), "w", encoding="utf-8") as handle:
            handle.write("matching tee content\n")
        with open(os.path.join(tee_dir, nonmatching), "w", encoding="utf-8") as handle:
            handle.write("nonmatching tee content\n")

        result = capture_rtk.capture(self.env, {})
        tee_recs = [
            rec for rec in result.records if rec["payload"]["source_type"] == "tee"
        ]
        self.assertEqual(len(tee_recs), 2)
        by_name = {rec["payload"]["filename"]: rec for rec in tee_recs}

        match = by_name[matching]
        self.assertEqual(match["payload"]["captured_epoch"], 1788953554)
        self.assertEqual(match["payload"]["filename_hint"], "brew_install_--help")
        self.assertEqual(match["payload"]["content"], "matching tee content\n")
        self.assertIn("sha256", match["payload"])
        self.assertEqual(len(match["payload"]["sha256"]), 64)

        odd = by_name[nonmatching]
        self.assertIsNone(odd["payload"]["captured_epoch"])
        self.assertEqual(odd["payload"]["filename_hint"], nonmatching)
        self.assertEqual(odd["payload"]["content"], "nonmatching tee content\n")

        second = capture_rtk.capture(self.env, result.cursor)
        self.assertEqual(
            [rec for rec in second.records if rec["payload"]["source_type"] == "tee"],
            [],
        )

    def test_tee_rewritten_same_filename_different_hash_recaptured(self):
        tee_dir = paths.rtk_tee_dir(self.env)
        os.makedirs(tee_dir, exist_ok=True)
        name = "1789000000_cmd.log"
        path = os.path.join(tee_dir, name)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("first content\n")
        first = capture_rtk.capture(self.env, {})
        first_tee = [
            rec for rec in first.records if rec["payload"]["source_type"] == "tee"
        ]
        self.assertEqual(len(first_tee), 1)
        first_hash = first_tee[0]["payload"]["sha256"]

        with open(path, "w", encoding="utf-8") as handle:
            handle.write("second content different\n")
        second = capture_rtk.capture(self.env, first.cursor)
        second_tee = [
            rec for rec in second.records if rec["payload"]["source_type"] == "tee"
        ]
        self.assertEqual(len(second_tee), 1)
        self.assertEqual(second_tee[0]["payload"]["filename"], name)
        self.assertNotEqual(second_tee[0]["payload"]["sha256"], first_hash)
        self.assertEqual(second_tee[0]["payload"]["content"], "second content different\n")


_CODEX_SESSION_UUID = "3f9a1c2e-8b4d-4e21-9c6a-7d1f2b3a4c5d"
_CODEX_ROLLOUT_NAME = (
    f"rollout-2026-01-15T12-00-00-{_CODEX_SESSION_UUID}.jsonl"
)
_CODEX_ENVELOPE_KEYS = (
    "raw_ref",
    "captured_at",
    "runtime",
    "source_file",
    "source_line",
    "parse_status",
    "raw_text",
    "payload",
    "session_id",
)


def _codex_session_meta_line():
    return json.dumps(
        {
            "timestamp": "2026-01-15T12:00:00Z",
            "type": "session_meta",
            "payload": {
                "session_id": _CODEX_SESSION_UUID,
                "cwd": "/tmp/proj",
                "originator": "cli",
                "cli_version": "0.1.0",
                "model_provider": "openai",
            },
        }
    )


def _codex_token_count_line():
    return json.dumps(
        {
            "timestamp": "2026-01-15T12:00:01Z",
            "type": "event_msg",
            "payload": {
                "type": "token_count",
                "info": {
                    "total_token_usage": {
                        "input_tokens": 10,
                        "cached_input_tokens": 0,
                        "cache_write_input_tokens": 0,
                        "output_tokens": 5,
                        "reasoning_output_tokens": 0,
                        "total_tokens": 15,
                    },
                    "model_context_window": 128000,
                },
            },
        }
    )


def _codex_function_call_line():
    return json.dumps(
        {
            "timestamp": "2026-01-15T12:00:02Z",
            "type": "response_item",
            "payload": {
                "type": "function_call",
                "name": "exec_command",
                "arguments": json.dumps({"cmd": "ls -la", "workdir": "/tmp/proj"}),
                "call_id": "call_1",
            },
        }
    )


def _write_codex_rollout(env, relative_dirs, filename, lines):
    directory = os.path.join(paths.codex_sessions_dir(env), *relative_dirs)
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, filename)
    with open(path, "w", encoding="utf-8") as handle:
        for line in lines:
            handle.write(line if line.endswith("\n") else line + "\n")
    return path


class TestCaptureCodex(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="ai-kit-um-codex-")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.env = _scratch_env(self.root)
        self.env["CODEX_HOME"] = os.path.join(self.root, "codex")

    def test_missing_directory_returns_empty_result(self):
        result = capture_codex.capture(self.env, {})
        self.assertIsInstance(result, CaptureResult)
        self.assertEqual(result.records, [])
        self.assertEqual(result.cursor, {})
        self.assertEqual(result.stats["captured"], 0)
        self.assertEqual(result.stats["malformed"], 0)
        self.assertEqual(result.stats["unreadable_files"], [])

    def test_rollout_verbatim_no_arguments_reparse_and_session_id(self):
        path = _write_codex_rollout(
            self.env,
            ("2026", "01", "15"),
            _CODEX_ROLLOUT_NAME,
            [
                _codex_session_meta_line(),
                _codex_token_count_line(),
                _codex_function_call_line(),
            ],
        )
        result = capture_codex.capture(self.env, {})
        self.assertIsInstance(result, CaptureResult)
        self.assertEqual(len(result.records), 3)
        self.assertEqual(result.stats["captured"], 3)
        self.assertEqual(result.stats["malformed"], 0)
        self.assertEqual(result.cursor[path], 3)
        self.assertEqual(CAPTURE_SOURCES["codex"], capture_codex.capture)

        session_ids = set()
        function_call = None
        for rec in result.records:
            for key in _CODEX_ENVELOPE_KEYS:
                self.assertIn(key, rec)
            self.assertEqual(rec["runtime"], "codex")
            self.assertEqual(rec["parse_status"], "ok")
            self.assertEqual(rec["source_file"], path)
            self.assertEqual(rec["session_id"], _CODEX_SESSION_UUID)
            session_ids.add(rec["session_id"])
            nested = rec["payload"]["payload"]
            if isinstance(nested, dict) and nested.get("type") == "function_call":
                function_call = rec

        self.assertEqual(session_ids, {_CODEX_SESSION_UUID})
        self.assertIsNotNone(function_call)
        arguments = function_call["payload"]["payload"]["arguments"]
        self.assertIsInstance(arguments, str)
        self.assertNotIsInstance(arguments, dict)

        types = {rec["payload"]["type"] for rec in result.records}
        self.assertEqual(types, {"session_meta", "event_msg", "response_item"})

    def test_malformed_line_mid_file_captured_losslessly(self):
        malformed_text = "this is not json{{{"
        path = _write_codex_rollout(
            self.env,
            ("2026", "01", "15"),
            _CODEX_ROLLOUT_NAME,
            [
                _codex_session_meta_line(),
                malformed_text,
                _codex_token_count_line(),
            ],
        )
        result = capture_codex.capture(self.env, {})
        self.assertEqual(len(result.records), 3)
        self.assertEqual(result.stats["captured"], 3)
        self.assertEqual(result.stats["malformed"], 1)
        self.assertEqual(result.cursor[path], 3)

        malformed = [rec for rec in result.records if rec["parse_status"] == "malformed"]
        self.assertEqual(len(malformed), 1)
        self.assertIsNone(malformed[0]["payload"])
        self.assertEqual(malformed[0]["raw_text"], malformed_text)
        self.assertEqual(malformed[0]["session_id"], _CODEX_SESSION_UUID)
        self.assertEqual(malformed[0]["source_line"], 2)

        ok_recs = [rec for rec in result.records if rec["parse_status"] == "ok"]
        self.assertEqual(len(ok_recs), 2)
        for rec in result.records:
            self.assertEqual(rec["session_id"], _CODEX_SESSION_UUID)

    def test_unreadable_utf8_file_is_skipped_and_reported(self):
        good_path = _write_codex_rollout(
            self.env,
            ("2026", "01", "15"),
            _CODEX_ROLLOUT_NAME,
            [_codex_session_meta_line()],
        )
        bad_dir = os.path.join(paths.codex_sessions_dir(self.env), "2026", "01", "16")
        os.makedirs(bad_dir, exist_ok=True)
        bad_path = os.path.join(bad_dir, f"rollout-2026-01-16T00-00-00-{_CODEX_SESSION_UUID}.jsonl")
        with open(bad_path, "wb") as handle:
            handle.write(b"\xff\xfe\x00\x01 not utf-8")
        result = capture_codex.capture(self.env, {})
        self.assertIn(bad_path, result.stats["unreadable_files"])
        self.assertTrue(any(rec["source_file"] == good_path for rec in result.records))
        self.assertFalse(any(rec["source_file"] == bad_path for rec in result.records))

    def test_filename_without_uuid_degrades_session_id_to_none(self):
        _write_codex_rollout(
            self.env,
            ("2026", "01", "15"),
            "rollout-test.jsonl",
            [_codex_session_meta_line()],
        )
        result = capture_codex.capture(self.env, {})
        self.assertEqual(len(result.records), 1)
        self.assertIsNone(result.records[0]["session_id"])


_CURSOR_SESSION_UUID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
_CURSOR_ENVELOPE_KEYS = (
    "raw_ref",
    "captured_at",
    "runtime",
    "source_file",
    "source_line",
    "parse_status",
    "raw_text",
    "payload",
    "source_confidence",
    "session_id",
    "timestamp",
)


def _cursor_tool_use_line(name, tool_input):
    return json.dumps(
        {
            "role": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "name": name,
                        "input": tool_input,
                    }
                ]
            },
        }
    )


def _write_cursor_transcript(env, project, session_uuid, filename, lines):
    directory = os.path.join(
        paths.cursor_projects_dir(env),
        project,
        "agent-transcripts",
        session_uuid,
    )
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, filename)
    with open(path, "w", encoding="utf-8") as handle:
        for line in lines:
            handle.write(line if line.endswith("\n") else line + "\n")
    return path


class TestCaptureCursor(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="ai-kit-um-cursor-")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.env = _scratch_env(self.root)
        self.env["CURSOR_CONFIG_DIR"] = os.path.join(self.root, "cursor")

    def test_missing_directory_returns_empty_result(self):
        result = capture_cursor.capture(self.env, {})
        self.assertIsInstance(result, CaptureResult)
        self.assertEqual(result.records, [])
        self.assertEqual(result.cursor, {})
        self.assertEqual(result.stats["captured"], 0)
        self.assertEqual(result.stats["malformed"], 0)
        self.assertEqual(result.stats["unreadable_files"], [])

    def test_transcripts_low_confidence_session_id_and_direct_payload(self):
        path = _write_cursor_transcript(
            self.env,
            "test-project",
            _CURSOR_SESSION_UUID,
            f"{_CURSOR_SESSION_UUID}.jsonl",
            [
                _cursor_tool_use_line(
                    "Shell",
                    {
                        "command": "ls -la",
                        "description": "list",
                        "working_directory": "/tmp/proj",
                    },
                ),
                _cursor_tool_use_line(
                    "Shell",
                    {"command": "pwd", "description": "print cwd"},
                ),
                _cursor_tool_use_line(
                    "StrReplace",
                    {"path": "/tmp/proj/a.py", "old_string": "x", "new_string": "y"},
                ),
            ],
        )
        result = capture_cursor.capture(self.env, {})
        self.assertIsInstance(result, CaptureResult)
        self.assertEqual(len(result.records), 3)
        self.assertEqual(result.stats["captured"], 3)
        self.assertEqual(result.stats["malformed"], 0)
        self.assertEqual(result.cursor[path], 3)
        self.assertEqual(CAPTURE_SOURCES["cursor"], capture_cursor.capture)
        self.assertEqual(
            set(CAPTURE_SOURCES),
            {"claude", "opencode", "rtk", "codex", "cursor"},
        )

        names = []
        for rec in result.records:
            for key in _CURSOR_ENVELOPE_KEYS:
                self.assertIn(key, rec)
            self.assertEqual(rec["runtime"], "cursor")
            self.assertEqual(rec["parse_status"], "ok")
            self.assertEqual(rec["source_confidence"], "low")
            self.assertEqual(rec["session_id"], _CURSOR_SESSION_UUID)
            self.assertIsNone(rec["timestamp"])
            self.assertNotIn("confidence", rec["payload"])
            self.assertNotIn("line", rec["payload"])
            self.assertEqual(rec["payload"]["role"], "assistant")
            content = rec["payload"]["message"]["content"]
            self.assertEqual(content[0]["type"], "tool_use")
            names.append(content[0]["name"])

        self.assertEqual(names, ["Shell", "Shell", "StrReplace"])
        first_input = result.records[0]["payload"]["message"]["content"][0]["input"]
        self.assertEqual(first_input["working_directory"], "/tmp/proj")
        second_input = result.records[1]["payload"]["message"]["content"][0]["input"]
        self.assertNotIn("working_directory", second_input)

    def test_malformed_line_mid_file_captured_losslessly(self):
        malformed_text = "this is not json{{{"
        path = _write_cursor_transcript(
            self.env,
            "test-project",
            _CURSOR_SESSION_UUID,
            f"{_CURSOR_SESSION_UUID}.jsonl",
            [
                _cursor_tool_use_line("Shell", {"command": "ls"}),
                malformed_text,
                _cursor_tool_use_line("StrReplace", {"path": "a.py"}),
            ],
        )
        result = capture_cursor.capture(self.env, {})
        self.assertEqual(len(result.records), 3)
        self.assertEqual(result.stats["captured"], 3)
        self.assertEqual(result.stats["malformed"], 1)
        self.assertEqual(result.cursor[path], 3)

        malformed = [rec for rec in result.records if rec["parse_status"] == "malformed"]
        self.assertEqual(len(malformed), 1)
        self.assertIsNone(malformed[0]["payload"])
        self.assertEqual(malformed[0]["raw_text"], malformed_text)
        self.assertEqual(malformed[0]["source_confidence"], "low")
        self.assertEqual(malformed[0]["session_id"], _CURSOR_SESSION_UUID)
        self.assertIsNone(malformed[0]["timestamp"])

    def test_unreadable_utf8_file_is_skipped_and_reported(self):
        good_path = _write_cursor_transcript(
            self.env,
            "test-project",
            _CURSOR_SESSION_UUID,
            f"{_CURSOR_SESSION_UUID}.jsonl",
            [_cursor_tool_use_line("Shell", {"command": "ls"})],
        )
        bad_uuid = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
        bad_dir = os.path.join(
            paths.cursor_projects_dir(self.env),
            "test-project",
            "agent-transcripts",
            bad_uuid,
        )
        os.makedirs(bad_dir, exist_ok=True)
        bad_path = os.path.join(bad_dir, f"{bad_uuid}.jsonl")
        with open(bad_path, "wb") as handle:
            handle.write(b"\xff\xfe\x00\x01 not utf-8")
        result = capture_cursor.capture(self.env, {})
        self.assertIn(bad_path, result.stats["unreadable_files"])
        self.assertTrue(any(rec["source_file"] == good_path for rec in result.records))
        self.assertFalse(any(rec["source_file"] == bad_path for rec in result.records))

    def test_no_sqlite3_import_or_attribute_access(self):
        import ast

        src_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "skills",
            "ai-kit-usage-metrics",
            "ai_kit_usage_metrics",
            "capture_cursor.py",
        )
        with open(src_path, encoding="utf-8") as handle:
            tree = ast.parse(handle.read())
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in getattr(node, "names", []):
                    self.assertNotEqual(alias.name.split(".")[0], "sqlite3")
                if isinstance(node, ast.ImportFrom) and node.module:
                    self.assertNotEqual(node.module.split(".")[0], "sqlite3")
            if isinstance(node, ast.Attribute):
                if isinstance(node.value, ast.Name):
                    self.assertNotEqual(node.value.id, "sqlite3")


class TestRawStore(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="ai-kit-um-raw-")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.path = os.path.join(self.root, "claude.jsonl")

    def test_append_records_dedups_by_raw_ref(self):
        first = [
            {
                "raw_ref": "claude:/a.jsonl:1",
                "captured_at": "t",
                "runtime": "claude",
                "source_file": "/a.jsonl",
                "source_line": 1,
                "parse_status": "ok",
                "raw_text": "{}",
                "payload": {},
            },
            {
                "raw_ref": "claude:/a.jsonl:2",
                "captured_at": "t",
                "runtime": "claude",
                "source_file": "/a.jsonl",
                "source_line": 2,
                "parse_status": "ok",
                "raw_text": "{}",
                "payload": {},
            },
        ]
        overlapping = [
            first[1],
            {
                "raw_ref": "claude:/a.jsonl:3",
                "captured_at": "t",
                "runtime": "claude",
                "source_file": "/a.jsonl",
                "source_line": 3,
                "parse_status": "ok",
                "raw_text": "{}",
                "payload": {},
            },
        ]
        raw_store.append_records(self.path, first)
        raw_store.append_records(self.path, overlapping)
        self.assertEqual(_count_jsonl_lines(self.path), 3)


class TestRefinedStore(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="ai-kit-um-refined-")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.env = _scratch_env(self.root)

    def _row(self, command_text):
        return {
            "raw_ref": "claude:/a.jsonl:1",
            "runtime": "claude",
            "session_id": SESSION_ID,
            "turn_id": TURN_UUID,
            "date": "2026-09-10",
            "timestamp": TS_USE,
            "model": MODEL,
            "command_text": command_text,
            "family": "ls",
            "command_shape": "simple",
            "step_index": 0,
            "step_count": 1,
            "operator": None,
            "execution_certain": True,
            "resolved_cwd": CWD,
            "source_confidence": "high",
            "tokens_input": 100,
            "tokens_output": 50,
            "price": None,
            "price_confidence": "unknown",
            "rtk_input_tokens": None,
            "rtk_output_tokens": None,
            "rtk_saved_tokens": None,
            "rtk_savings_pct": None,
            "rtk_rewrote": None,
            "inferred_family": None,
            "inferred_confidence": None,
            "exec_duration_ms": 1500,
        }

    def test_insert_commands_upsert_preserves_inferred_family(self):
        conn = refined_store.open_refined_db(self.env)
        self.addCleanup(conn.close)
        refined_store.insert_commands(conn, [self._row("ls")])
        refined_store.insert_commands(conn, [self._row("ls -la")])
        rows = conn.execute(
            "SELECT command_text, inferred_family FROM refined_commands"
        ).fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "ls -la")

        conn.execute(
            "UPDATE refined_commands SET inferred_family = ? WHERE raw_ref = ?",
            ("files", "claude:/a.jsonl:1"),
        )
        conn.commit()
        refined_store.insert_commands(conn, [self._row("ls -la")])
        rows = conn.execute(
            "SELECT command_text, inferred_family FROM refined_commands"
        ).fetchall()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "ls -la")
        self.assertEqual(rows[0][1], "files")


class TestRefiner(unittest.TestCase):
    def test_compound_commands_produce_no_row(self):
        raw_records = [
            {
                "raw_ref": "claude:/a.jsonl:1",
                "captured_at": datetime.now(UTC).isoformat(),
                "runtime": "claude",
                "source_file": "/a.jsonl",
                "source_line": 1,
                "parse_status": "ok",
                "raw_text": _assistant_bash_line(COMPOUND_COMMAND),
                "payload": json.loads(_assistant_bash_line(COMPOUND_COMMAND)),
            },
            {
                "raw_ref": "claude:/a.jsonl:2",
                "captured_at": datetime.now(UTC).isoformat(),
                "runtime": "claude",
                "source_file": "/a.jsonl",
                "source_line": 2,
                "parse_status": "ok",
                "raw_text": _assistant_bash_line(SIMPLE_COMMAND, tool_id="toolu_simple"),
                "payload": json.loads(
                    _assistant_bash_line(SIMPLE_COMMAND, tool_id="toolu_simple")
                ),
            },
        ]
        rows = refine_simple_commands(raw_records)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["command_text"], SIMPLE_COMMAND)
        self.assertEqual(rows[0]["command_shape"], "simple")
        self.assertEqual(rows[0]["family"], "ls")
        self.assertNotIn("&", rows[0]["command_text"])
        self.assertNotIn(";", rows[0]["command_text"])
        self.assertNotIn("|", rows[0]["command_text"])

    def test_missing_input_command_produces_no_row(self):
        ok_line = _assistant_bash_line(SIMPLE_COMMAND, tool_id="toolu_ok")
        missing_payload = json.loads(
            _assistant_bash_line(SIMPLE_COMMAND, tool_id="toolu_missing")
        )
        missing_payload["message"]["content"][0]["input"] = {}
        raw_records = [
            {
                "raw_ref": "claude:/a.jsonl:1",
                "captured_at": datetime.now(UTC).isoformat(),
                "runtime": "claude",
                "source_file": "/a.jsonl",
                "source_line": 1,
                "parse_status": "ok",
                "raw_text": json.dumps(missing_payload),
                "payload": missing_payload,
            },
            {
                "raw_ref": "claude:/a.jsonl:2",
                "captured_at": datetime.now(UTC).isoformat(),
                "runtime": "claude",
                "source_file": "/a.jsonl",
                "source_line": 2,
                "parse_status": "ok",
                "raw_text": ok_line,
                "payload": json.loads(ok_line),
            },
        ]
        rows = refine_simple_commands(raw_records)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["command_text"], SIMPLE_COMMAND)


class TestPricing(unittest.TestCase):
    def test_catalog_absent_degrades_to_unknown(self):
        env = {"HOME": "/no/such/home", "XDG_CACHE_HOME": "/no/such/cache"}
        price, confidence = pricing.estimate_price(
            "anthropic", MODEL, 100, 50, env
        )
        self.assertIsNone(price)
        self.assertEqual(confidence, "unknown")


class TestDashboard(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="ai-kit-um-dash-")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.env = _scratch_env(self.root)

    def test_script_close_escaped_in_embedded_json(self):
        conn = refined_store.open_refined_db(self.env)
        self.addCleanup(conn.close)
        refined_store.insert_commands(
            conn,
            [
                {
                    "raw_ref": "claude:/a.jsonl:1",
                    "runtime": "claude",
                    "session_id": SESSION_ID,
                    "turn_id": TURN_UUID,
                    "date": "2026-09-10",
                    "timestamp": TS_USE,
                    "model": MODEL,
                    "command_text": SCRIPT_COMMAND,
                    "family": SCRIPT_COMMAND,
                    "command_shape": "simple",
                    "step_index": 0,
                    "step_count": 1,
                    "operator": None,
                    "execution_certain": True,
                    "resolved_cwd": CWD,
                    "source_confidence": "high",
                    "tokens_input": 1,
                    "tokens_output": 1,
                    "price": None,
                    "price_confidence": "unknown",
                    "rtk_input_tokens": None,
                    "rtk_output_tokens": None,
                    "rtk_saved_tokens": None,
                    "rtk_savings_pct": None,
                    "rtk_rewrote": None,
                    "inferred_family": None,
                    "inferred_confidence": None,
                    "exec_duration_ms": None,
                }
            ],
        )
        out = os.path.join(self.root, "dashboard.html")
        generate(conn, out)
        with open(out, encoding="utf-8") as handle:
            html = handle.read()
        start = html.find('<script type="application/json" id="usage-metrics-data">')
        self.assertNotEqual(start, -1)
        end = html.find("</script>", start)
        embedded = html[start:end]
        self.assertNotIn("</script", embedded.replace("<script type", ""))
        self.assertIn("<\\/script", embedded)


class TestPermissions(unittest.TestCase):
    def test_run_creates_private_dirs_and_files(self):
        root = tempfile.mkdtemp(prefix="ai-kit-um-perm-")
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        env = _scratch_env(root)
        _write_session(
            env,
            "proj-a",
            "session-a.jsonl",
            [_assistant_bash_line(SIMPLE_COMMAND), _tool_result_line()],
        )
        previous = os.umask(0o000)
        self.addCleanup(os.umask, previous)
        rc = main(["run"], env=env)
        self.assertEqual(rc, 0)
        base = paths.usage_metrics_base(env)
        for directory in (
            paths.raw_dir(env),
            os.path.dirname(paths.refined_db_path(env)),
            paths.cursors_dir(env),
        ):
            mode = stat.S_IMODE(os.stat(directory).st_mode)
            self.assertEqual(mode, 0o700, directory)
        for file_path in (
            paths.raw_jsonl_path(env, "claude"),
            paths.refined_db_path(env),
            os.path.join(paths.cursors_dir(env), "claude.json"),
            paths.dashboard_html_path(env),
        ):
            mode = stat.S_IMODE(os.stat(file_path).st_mode)
            self.assertEqual(mode, 0o600, file_path)
        self.assertTrue(os.path.isdir(base))


class TestEndToEnd(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="ai-kit-um-e2e-")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.env = _scratch_env(self.root)
        _write_session(
            self.env,
            "proj-a",
            "session-a.jsonl",
            [_assistant_bash_line(SIMPLE_COMMAND), _tool_result_line()],
        )
        _write_session(
            self.env,
            "proj-b",
            "session-b.jsonl",
            [_queue_operation_line(), "this is not json{{{"],
        )

    def test_run_end_to_end_produces_raw_refined_and_dashboard(self):
        rc = main(["run"], env=self.env)
        self.assertEqual(rc, 0)
        raw_path = paths.raw_jsonl_path(self.env, "claude")
        db_path = paths.refined_db_path(self.env)
        html_path = paths.dashboard_html_path(self.env)
        self.assertTrue(os.path.isfile(raw_path))
        self.assertTrue(os.path.isfile(db_path))
        self.assertTrue(os.path.isfile(html_path))

        raw_count = _count_jsonl_lines(raw_path)
        self.assertGreaterEqual(raw_count, 4)
        with open(raw_path, encoding="utf-8") as handle:
            envelopes = [json.loads(line) for line in handle if line.strip()]
        statuses = {rec["parse_status"] for rec in envelopes}
        self.assertIn("ok", statuses)
        self.assertIn("malformed", statuses)
        self.assertIn("recognized_no_data", statuses)
        malformed = [rec for rec in envelopes if rec["parse_status"] == "malformed"]
        self.assertEqual(malformed[0]["payload"], None)
        self.assertEqual(malformed[0]["raw_text"], "this is not json{{{")
        recognized = [
            rec for rec in envelopes if rec["parse_status"] == "recognized_no_data"
        ]
        self.assertEqual(recognized[0]["payload"]["type"], "queue-operation")

        self.assertEqual(_refined_row_count(self.env), 1)
        conn = sqlite3.connect(db_path)
        try:
            row = conn.execute(
                "SELECT command_text, family, command_shape, model, date, "
                "step_index, step_count FROM refined_commands"
            ).fetchone()
        finally:
            conn.close()
        self.assertEqual(row[0], SIMPLE_COMMAND)
        self.assertEqual(row[1], "ls")
        self.assertEqual(row[2], "simple")
        self.assertEqual(row[3], MODEL)
        self.assertEqual(row[4], "2026-09-10")
        self.assertEqual(row[5], 0)
        self.assertEqual(row[6], 1)

        with open(html_path, encoding="utf-8") as handle:
            html = handle.read()
        self.assertIn(SIMPLE_COMMAND, html)
        self.assertIn("ls", html)
        self.assertIn(MODEL, html)
        self.assertIn("2026-09-10", html)
        self.assertIn('id="usage-metrics-data"', html)

        rc2 = main(["run"], env=self.env)
        self.assertEqual(rc2, 0)
        self.assertEqual(_count_jsonl_lines(raw_path), raw_count)
        self.assertEqual(_refined_row_count(self.env), 1)


_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_MAKEFILE_PATH = os.path.join(_REPO, "Makefile")
_PRECOMMIT_PATH = os.path.join(_REPO, ".pre-commit-config.yaml")
_PYPROJECT_PATH = os.path.join(_REPO, "pyproject.toml")
_PATHS_PY_CANDIDATE = (
    "skills/ai-kit-usage-metrics/ai_kit_usage_metrics/paths.py"
)


def _precommit_hook_block(hook_id):
    with open(_PRECOMMIT_PATH, encoding="utf-8") as handle:
        text = handle.read()
    needle = f"- id: {hook_id}"
    start = text.find(needle)
    if start < 0:
        raise AssertionError(f"hook id {hook_id!r} not found")
    rest = text[start:]
    nxt = rest.find("\n      - id:", len(needle))
    return rest if nxt < 0 else rest[:nxt]


def _precommit_hook_files_regex(hook_id):
    block = _precommit_hook_block(hook_id)
    match = re.search(r"^\s*files:\s*(\S+)\s*$", block, re.MULTILINE)
    if match is None:
        raise AssertionError(f"no files: value for hook {hook_id!r}")
    return match.group(1).strip().strip("'\"")


class TestGateRegistration(unittest.TestCase):
    def test_makefile_registers_module_and_package(self):
        with open(_MAKEFILE_PATH, encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("tests.test_ai_kit_usage_metrics", text)
        self.assertIn("skills/ai-kit-usage-metrics/", text)

    def test_precommit_ruff_and_py_compile_match_package_path(self):
        for hook_id in ("ruff", "py-compile"):
            regex = _precommit_hook_files_regex(hook_id)
            self.assertIsNotNone(
                re.match(regex, _PATHS_PY_CANDIDATE),
                f"{_PATHS_PY_CANDIDATE} did not match {hook_id} files: {regex}",
            )
        entry_block = _precommit_hook_block("unittest")
        match = re.search(r"^\s*entry:\s*(.+)$", entry_block, re.MULTILINE)
        self.assertIsNotNone(match, "no entry: value for hook unittest")
        self.assertIn("tests.test_ai_kit_usage_metrics", match.group(1))

    def test_pyright_include_contains_package_directory(self):
        with open(_PYPROJECT_PATH, "rb") as handle:
            data = tomllib.load(handle)
        include = data["tool"]["pyright"]["include"]
        self.assertIn("skills/ai-kit-usage-metrics", include)


if __name__ == "__main__":
    unittest.main()

