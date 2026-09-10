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

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-usage-metrics"),
)

from ai_kit_usage_metrics import capture_claude, family, paths, pricing, raw_store, refined_store
from ai_kit_usage_metrics.cli import main
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

