import ast
import json
import os
import re
import shutil
import sqlite3
import stat
import subprocess
import sys
import tempfile
import tomllib
import unittest
from datetime import UTC, datetime
from html.parser import HTMLParser
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
from ai_kit_usage_metrics.classify_loop import (
    infer_family_for_group,
    mine_recurring_shapes,
    normalize_skeleton,
    run_classification,
)
from ai_kit_usage_metrics.cli import CAPTURE_SOURCES, main
from ai_kit_usage_metrics.cwd_state import CwdState
from ai_kit_usage_metrics.dashboard import generate
from ai_kit_usage_metrics.decomposer import classify_segment, decompose, scan_command
from ai_kit_usage_metrics.raw_store import CaptureResult
from ai_kit_usage_metrics.refiner import refine_all

SIMPLE_COMMAND = "ls -la"
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


# SD-1 spec table (15.1-02-PLAN.md shared_definitions) -- the oracle both the
# Python subfamily_of() and Plan 03's JavaScript mirror are checked against.
# Module-level (not inline in the test method) so Plan 03 can import this same
# case list for its cross-language parity test.
SUBFAMILY_SPEC_CASES = [
    ("git commit -m msg", "commit"),
    ("git -C /path commit", "commit"),
    ("git -C mydir commit", "commit"),
    ("git --git-dir=/x status", "status"),
    ("sudo git -C /srv pull", "pull"),
    ("FOO=bar git -c user.name=x log", "log"),
    ("nice -n10 git push", "push"),
    ("make -C build test", "test"),
    ("rg -n pattern", "pattern"),
    ("python3 -m unittest tests.x", "unittest"),
    ("git -- status", "status"),
    ("ls -la /tmp", ""),
    ("python3 -c 'import os'", ""),
    ("git", ""),
    ("git --version", ""),
    ("", ""),
    ("   ", ""),
]


class TestFamily(unittest.TestCase):
    def test_rg_and_grep_share_grep_family(self):
        self.assertEqual(family.family_of("grep -r x"), "grep")
        self.assertEqual(family.family_of("rg -r x"), "grep")
        self.assertEqual(family.family_of("/usr/bin/rg -r x"), "grep")

    def test_unmatched_command_is_its_own_family(self):
        self.assertEqual(family.family_of("git status"), "git")

    def test_wrapper_and_env_assignment_prefixes_do_not_mask_family(self):
        # WR-04 regression: sudo/env-var-assignment/wrapper-binary prefixes
        # must not become the reported family instead of the real command.
        self.assertEqual(family.family_of("sudo grep x"), "grep")
        self.assertEqual(family.family_of("FOO=bar grep x"), "grep")
        self.assertEqual(family.family_of("time grep x"), "grep")
        self.assertEqual(family.family_of("nice -n10 rg x"), "grep")
        self.assertEqual(family.family_of("env FOO=bar sudo grep x"), "grep")
        self.assertEqual(family.family_of(""), "")

    def test_subfamily_of_matches_spec_table(self):
        for command_text, expected in SUBFAMILY_SPEC_CASES:
            with self.subTest(command_text=command_text):
                self.assertEqual(family.subfamily_of(command_text), expected)

    def test_command_substitution_glued_to_assignment_resolves_to_real_command(self):
        # Live-found regression (2026-09-21): naive whitespace tokenizing
        # glues a command substitution's command name onto the preceding
        # assignment token when there is no space after "$(" ("FOO=\"$(jq"),
        # so the substitution's own FLAG ("-cSn") was wrongly read as the
        # family instead of "jq".
        self.assertEqual(
            family.family_of(
                'intended_projection="$(jq -cSn --argjson t "$t" \'{}\')"'
            ),
            "jq",
        )
        self.assertEqual(family.family_of("x=$(rg -n foo bar)"), "grep")

    def test_export_prefix_does_not_mask_family(self):
        # "export FOO=bar" is a shell keyword wrapping an assignment the
        # same way "sudo"/"env" wrap a command -- it must not itself become
        # the reported family, and a bare export-only line (no command
        # after the assignment) must degrade to "" rather than "export".
        self.assertEqual(family.family_of("export FOO=bar grep x"), "grep")
        self.assertEqual(family.family_of("export PNPM_HOME=/x/bin"), "")

    def test_implausible_fragment_returns_empty_family(self):
        # Live-found regression (2026-09-21): a decomposer fragment left
        # over from a shell construct it could not structurally close (an
        # unclosed process substitution, a bare flag, a quoted fragment)
        # must not populate the family filter/chart as if it were a real
        # command name -- SKILL.md already documents this as a known
        # decomposer limitation, not something family_of() should present
        # with the same confidence as a real command.
        self.assertEqual(family.family_of("sort) <(git diff --name-only A..B"), "")
        self.assertEqual(family.family_of("-cSn"), "")
        self.assertEqual(family.family_of("Read()"), "")
        self.assertEqual(family.family_of('"quoted fragment'), "")
        self.assertEqual(family.family_of(">"), "")


class TestDecomposer(unittest.TestCase):
    def test_scan_command_prd_compound_and(self):
        result = scan_command("cd src && grep -r TODO .")
        self.assertEqual(len(result.segments), 2)
        self.assertEqual(result.segments[0], ("cd src", None))
        self.assertEqual(result.segments[1], ("grep -r TODO .", "&&"))
        self.assertFalse(result.unterminated_quote)
        self.assertFalse(result.has_unsupported_shape)

    def test_scan_command_does_not_split_inside_double_quotes(self):
        result = scan_command('echo "a && b"')
        self.assertEqual(len(result.segments), 1)
        self.assertEqual(result.segments[0], ('echo "a && b"', None))
        self.assertFalse(result.unterminated_quote)
        self.assertFalse(result.has_unsupported_shape)

    def test_scan_command_does_not_split_inside_single_quotes(self):
        result = scan_command("echo 'a ; b'")
        self.assertEqual(len(result.segments), 1)
        self.assertEqual(result.segments[0], ("echo 'a ; b'", None))
        self.assertFalse(result.unterminated_quote)
        self.assertFalse(result.has_unsupported_shape)

    def test_classify_segment_control_flow_keywords(self):
        self.assertEqual(classify_segment("if true; then echo x; fi"), "control_flow_script")
        self.assertEqual(classify_segment("for f in *.py; do rg x; done"), "control_flow_script")
        self.assertEqual(classify_segment("while true; do echo x; done"), "control_flow_script")
        self.assertEqual(classify_segment("case x in a) echo;; esac"), "control_flow_script")
        self.assertEqual(classify_segment("until false; do echo x; done"), "control_flow_script")
        self.assertEqual(classify_segment("select x in a b; do echo; done"), "control_flow_script")
        self.assertEqual(classify_segment("grep -r TODO ."), "simple")
        self.assertEqual(classify_segment("cd src"), "simple")

    def test_decompose_simple_command(self):
        steps = decompose("grep -r TODO .")
        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0]["step_index"], 0)
        self.assertEqual(steps[0]["text"], "grep -r TODO .")
        self.assertIsNone(steps[0]["operator"])
        self.assertEqual(steps[0]["command_shape"], "simple")

    def test_decompose_prd_cd_and_grep(self):
        steps = decompose("cd src && grep -r TODO .")
        self.assertEqual(len(steps), 2)
        self.assertEqual(steps[0]["step_index"], 0)
        self.assertEqual(steps[0]["text"], "cd src")
        self.assertIsNone(steps[0]["operator"])
        self.assertEqual(steps[0]["command_shape"], "simple")
        self.assertEqual(steps[1]["step_index"], 1)
        self.assertEqual(steps[1]["text"], "grep -r TODO .")
        self.assertEqual(steps[1]["operator"], "&&")
        self.assertEqual(steps[1]["command_shape"], "simple")

    def test_decompose_prd_for_loop_is_one_control_flow_script(self):
        text = 'for f in *.py; do rg pattern "$f"; done'
        steps = decompose(text)
        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0]["text"], text)
        self.assertIsNone(steps[0]["operator"])
        self.assertEqual(steps[0]["command_shape"], "control_flow_script")

    def test_decompose_prd_mixed_cd_and_for(self):
        for_text = 'for f in *.py; do rg pattern "$f"; done'
        steps = decompose(f"cd src && {for_text}")
        self.assertEqual(len(steps), 2)
        self.assertEqual(steps[0]["text"], "cd src")
        self.assertEqual(steps[0]["command_shape"], "simple")
        self.assertIsNone(steps[0]["operator"])
        self.assertEqual(steps[1]["text"], for_text)
        self.assertEqual(steps[1]["command_shape"], "control_flow_script")
        self.assertEqual(steps[1]["operator"], "&&")

    def test_decompose_or_is_unclassified(self):
        steps = decompose("a || b")
        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0]["text"], "a || b")
        self.assertEqual(steps[0]["command_shape"], "unclassified")
        self.assertIsNone(steps[0]["operator"])

    def test_decompose_heredoc_is_unclassified(self):
        text = "cat <<EOF\nhello\nEOF"
        steps = decompose(text)
        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0]["text"], text)
        self.assertEqual(steps[0]["command_shape"], "unclassified")

    def test_decompose_dollar_paren_subshell_is_unclassified(self):
        steps = decompose("echo $(pwd)")
        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0]["text"], "echo $(pwd)")
        self.assertEqual(steps[0]["command_shape"], "unclassified")

    def test_decompose_backtick_subshell_is_unclassified(self):
        steps = decompose("echo `pwd`")
        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0]["text"], "echo `pwd`")
        self.assertEqual(steps[0]["command_shape"], "unclassified")

    def test_decompose_parenthesized_subshell_is_unclassified(self):
        steps = decompose("(echo hi)")
        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0]["command_shape"], "unclassified")

    def test_decompose_unterminated_quote_is_unclassified(self):
        steps = decompose('echo "unterminated')
        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0]["text"], 'echo "unterminated')
        self.assertEqual(steps[0]["command_shape"], "unclassified")
        self.assertNotEqual(steps[0]["command_shape"], "control_flow_script")

    def test_decompose_empty_string(self):
        self.assertEqual(decompose(""), [])

    def test_decompose_nested_control_flow(self):
        text = 'for f in *; do if [ -f "$f" ]; then rg x "$f"; fi; done'
        steps = decompose(text)
        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0]["text"], text)
        self.assertEqual(steps[0]["command_shape"], "control_flow_script")

    def test_decompose_until_and_select_are_control_flow(self):
        until_text = "until false; do echo x; done"
        until_steps = decompose(until_text)
        self.assertEqual(len(until_steps), 1)
        self.assertEqual(until_steps[0]["text"], until_text)
        self.assertEqual(until_steps[0]["command_shape"], "control_flow_script")
        select_text = "select x in a b; do echo $x; done"
        select_steps = decompose(select_text)
        self.assertEqual(len(select_steps), 1)
        self.assertEqual(select_steps[0]["text"], select_text)
        self.assertEqual(select_steps[0]["command_shape"], "control_flow_script")

    def test_decompose_never_emits_compound_decomposed(self):
        samples = [
            "grep -r TODO .",
            "cd src && grep -r TODO .",
            'for f in *.py; do rg pattern "$f"; done',
            "a || b",
            "echo $(pwd)",
            "",
        ]
        shapes = set()
        for sample in samples:
            for step in decompose(sample):
                shapes.add(step["command_shape"])
                self.assertNotEqual(step["command_shape"], "compound_decomposed")
        self.assertTrue(shapes <= {"simple", "control_flow_script", "unclassified"})

    def test_decompose_pipe_and_semicolon(self):
        pipe_steps = decompose("ls | grep x")
        self.assertEqual(len(pipe_steps), 2)
        self.assertEqual(pipe_steps[0]["text"], "ls")
        self.assertEqual(pipe_steps[1]["text"], "grep x")
        self.assertEqual(pipe_steps[1]["operator"], "|")
        self.assertEqual(pipe_steps[0]["command_shape"], "simple")
        self.assertEqual(pipe_steps[1]["command_shape"], "simple")
        semi_steps = decompose("cd src; ls")
        self.assertEqual(len(semi_steps), 2)
        self.assertEqual(semi_steps[0]["text"], "cd src")
        self.assertEqual(semi_steps[1]["text"], "ls")
        self.assertEqual(semi_steps[1]["operator"], ";")


class TestCwdState(unittest.TestCase):
    def test_constructs_with_initial_dir(self):
        state = CwdState("/repo")
        self.assertEqual(state.current, "/repo")

    def test_prd_cd_then_grep_same_compound(self):
        state = CwdState("/repo")
        resolved = []
        for step in ["cd src", "grep -r TODO ."]:
            resolved.append(state.resolve_for(step))
            state.observe(step)
        self.assertEqual(resolved[0], "/repo")
        self.assertEqual(resolved[1], "/repo/src")

    def test_prd_later_separate_call_reuses_carried_cwd(self):
        state = CwdState("/repo")
        for step in ["cd src", "grep -r TODO ."]:
            state.resolve_for(step)
            state.observe(step)
        later = "grep -r FIXME ."
        self.assertEqual(state.resolve_for(later), "/repo/src")
        state.observe(later)
        self.assertEqual(state.current, "/repo/src")

    def test_relative_vs_absolute_cd(self):
        state = CwdState("/repo")
        state.resolve_for("cd src")
        state.observe("cd src")
        self.assertEqual(state.current, "/repo/src")
        state.resolve_for("cd /tmp/other")
        state.observe("cd /tmp/other")
        self.assertEqual(state.current, "/tmp/other")

    def test_bare_cd_is_noop(self):
        state = CwdState("/repo")
        state.resolve_for("cd")
        state.observe("cd")
        self.assertEqual(state.current, "/repo")

    def test_nonexistent_path_still_recorded(self):
        state = CwdState("/repo")
        missing = "/repo/does-not-exist-xyz"
        self.assertFalse(os.path.exists(missing))
        state.resolve_for("cd does-not-exist-xyz")
        state.observe("cd does-not-exist-xyz")
        self.assertEqual(state.current, missing)
        self.assertFalse(os.path.exists(missing))

    def test_quoted_cd_argument(self):
        state = CwdState("/repo")
        state.resolve_for('cd "my dir"')
        state.observe('cd "my dir"')
        self.assertEqual(state.current, "/repo/my dir")


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

    def test_null_time_created_rows_are_captured_not_dropped(self):
        # CR-01 regression: a row whose time_created is SQL NULL must not be
        # silently and permanently excluded by the cursor-pagination WHERE
        # clause (NULL comparisons evaluate to NULL/false in SQLite).
        def seed(conn):
            conn.execute(
                "INSERT INTO session (id, time_created, time_updated) "
                "VALUES (?, ?, ?)",
                ("ses_null", None, None),
            )
            conn.execute(
                "INSERT INTO message (id, session_id, time_created, time_updated, data) "
                "VALUES (?, ?, ?, ?, ?)",
                ("msg_null", "ses_null", None, None, "{}"),
            )
            conn.execute(
                "INSERT INTO part (id, message_id, session_id, time_created, "
                "time_updated, data) VALUES (?, ?, ?, ?, ?, ?)",
                ("prt_null", "msg_null", "ses_null", None, None, "{}"),
            )

        _write_opencode_db(self.env, seed)
        result = capture_opencode.capture(self.env, {})
        record_ids = sorted(rec["record_id"] for rec in result.records)
        self.assertEqual(record_ids, ["msg_null", "prt_null", "ses_null"])
        self.assertEqual(result.stats["captured"], 3)
        self.assertEqual(result.stats["null_time_created"], 3)
        for rec in result.records:
            self.assertIsNone(rec["time_created"])

        # A row with a NULL time_created must not be re-yielded on a
        # subsequent run once it has been captured (deduped via null_seen_ids,
        # independent of the time-ordered cursor).
        second = capture_opencode.capture(self.env, result.cursor)
        self.assertEqual(second.records, [])
        self.assertEqual(second.stats["captured"], 0)

    def test_null_time_created_row_arriving_after_cursor_advances_is_captured(self):
        # CR-01 residual regression (iteration 2): a NULL time_created row
        # inserted AFTER the cursor has already advanced past a real
        # (non-zero) timestamp for that table must still be captured on a
        # later run, not permanently excluded by the time-ordered WHERE
        # clause.
        def seed(conn):
            conn.execute(
                "INSERT INTO session (id, time_created, time_updated) "
                "VALUES (?, ?, ?)",
                ("ses_a", _OPENCODE_TIME, _OPENCODE_TIME),
            )

        _write_opencode_db(self.env, seed)
        first = capture_opencode.capture(self.env, {})
        self.assertEqual(
            [rec["record_id"] for rec in first.records], ["ses_a"]
        )
        self.assertGreater(first.cursor["session"]["last_time_created"], 0)

        db_path = paths.opencode_db_path(self.env)
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO session (id, time_created, time_updated) "
            "VALUES (?, ?, ?)",
            ("ses_null_late", None, None),
        )
        conn.commit()
        conn.close()

        second = capture_opencode.capture(self.env, first.cursor)
        self.assertEqual(
            [rec["record_id"] for rec in second.records], ["ses_null_late"]
        )
        self.assertEqual(second.stats["captured"], 1)
        self.assertEqual(second.stats["null_time_created"], 1)

        third = capture_opencode.capture(self.env, second.cursor)
        self.assertEqual(third.records, [])
        self.assertEqual(third.stats["captured"], 0)

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


def _codex_custom_tool_call_line(
    cmd, workdir=None, tool_name="exec_command", timestamp="2026-01-15T12:00:02Z", call_id="call_ctc_1"
):
    """Verbatim-shaped codex `custom_tool_call`/"exec" record (RESEARCH.md Pitfall 5).

    `input` is a JavaScript source STRING (not a JSON document) that awaits a
    `tools.<tool_name>({...})` call whose single argument is a JSON object literal.
    """
    args = {"cmd": cmd}
    if workdir is not None:
        args["workdir"] = workdir
    js_body = f"const r = await tools.{tool_name}({json.dumps(args)}); text(r.output);"
    return json.dumps(
        {
            "timestamp": timestamp,
            "type": "response_item",
            "payload": {
                "type": "custom_tool_call",
                "id": "ctc_test",
                "status": "completed",
                "call_id": call_id,
                "name": "exec",
                "input": js_body,
            },
        }
    )


def _codex_custom_tool_call_web_run_line(timestamp="2026-01-15T12:00:02Z"):
    """Real non-shell sample from the same wrapper shape (RESEARCH.md Pitfall 5)."""
    js_body = (
        'const r = await tools.web__run({"search_query":[{"q":"test"}],'
        '"response_length":"long"}); text(r);'
    )
    return json.dumps(
        {
            "timestamp": timestamp,
            "type": "response_item",
            "payload": {
                "type": "custom_tool_call",
                "id": "ctc_web_test",
                "status": "completed",
                "call_id": "call_web_1",
                "name": "exec",
                "input": js_body,
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
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
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

    def test_refined_store_docstring_states_the_two_branch_dedup_rule(self):
        # This is the gate that keeps refined_store.py's own canonical
        # dedup-identity statement from drifting away from turnKey() again --
        # the Round-2 cross-AI review finding that motivated this task.
        doc = " ".join((refined_store.__doc__ or "").split())
        self.assertIn("turn_id", doc)
        self.assertIn("raw_ref", doc)
        self.assertIn("turnKey", doc)
        self.assertIn("step_index", doc)
        self.assertTrue(
            "SELECT DISTINCT session_id, turn_id, tokens_input" not in doc
            or "NOT sufficient" in doc
            or "not sufficient" in doc,
            "the obsolete pair-only SELECT DISTINCT prescription is still "
            "stated as the rule, unretracted",
        )


class TestRefinerFull(unittest.TestCase):
    def test_claude_cd_and_grep_two_steps_with_cwd(self):
        rec = capture_claude._envelope(
            "/a.jsonl",
            1,
            _assistant_bash_line("cd src && grep -r TODO .", cwd="/repo"),
            datetime.now(UTC).isoformat(),
        )
        rows = refine_all([rec])
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["command_text"], "cd src")
        self.assertEqual(rows[0]["resolved_cwd"], "/repo")
        self.assertIsNone(rows[0]["operator"])
        self.assertTrue(rows[0]["execution_certain"])
        self.assertEqual(rows[1]["command_text"], "grep -r TODO .")
        self.assertEqual(rows[1]["resolved_cwd"], "/repo/src")
        self.assertEqual(rows[1]["operator"], "&&")
        self.assertFalse(rows[1]["execution_certain"])
        self.assertEqual(rows[0]["raw_ref"], rows[1]["raw_ref"])
        self.assertEqual(rows[0]["step_count"], 2)
        self.assertEqual(rows[1]["step_count"], 2)
        self.assertEqual(rows[0]["step_index"], 0)
        self.assertEqual(rows[1]["step_index"], 1)
        self.assertEqual(rows[0]["command_shape"], "simple")
        self.assertEqual(rows[1]["command_shape"], "simple")
        self.assertEqual(rows[0]["family"], "cd")
        self.assertEqual(rows[1]["family"], "grep")

    def test_opencode_later_separate_call_reuses_cwd(self):
        captured_at = datetime.now(UTC).isoformat()
        session_id = "ses_cwd"
        message_id = "msg_cwd"
        message = capture_opencode._base_envelope(
            "/opencode.db",
            "message",
            message_id,
            json.dumps(
                {
                    "role": "assistant",
                    "tokens": {"input": 5, "output": 5},
                    "modelID": MODEL,
                    "providerID": "anthropic",
                    "path": {"cwd": "/repo"},
                }
            ),
            captured_at,
            session_id,
            None,
            10,
        )
        cd_part = capture_opencode._base_envelope(
            "/opencode.db",
            "part",
            "prt_cd",
            json.dumps(
                {
                    "type": "tool",
                    "tool": "bash",
                    "state": {"input": {"command": "cd src"}},
                }
            ),
            captured_at,
            session_id,
            message_id,
            20,
        )
        grep_part = capture_opencode._base_envelope(
            "/opencode.db",
            "part",
            "prt_grep",
            json.dumps(
                {
                    "type": "tool",
                    "tool": "bash",
                    "state": {"input": {"command": "grep -r FIXME ."}},
                }
            ),
            captured_at,
            session_id,
            message_id,
            30,
        )
        rows = refine_all([message, cd_part, grep_part])
        by_text = {row["command_text"]: row for row in rows}
        self.assertEqual(by_text["cd src"]["resolved_cwd"], "/repo")
        self.assertEqual(by_text["grep -r FIXME ."]["resolved_cwd"], "/repo/src")

    def test_for_loop_is_one_control_flow_script_row(self):
        command = 'for f in *.py; do rg pattern "$f"; done'
        rec = capture_claude._envelope(
            "/a.jsonl",
            1,
            _assistant_bash_line(command, cwd="/repo"),
            datetime.now(UTC).isoformat(),
        )
        rows = refine_all([rec])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["command_text"], command)
        self.assertEqual(rows[0]["command_shape"], "control_flow_script")
        self.assertEqual(rows[0]["step_count"], 1)
        # D-16 family: a control_flow_script row's `family` is gated to empty
        # rather than the mechanically-derived "for" keyword (Task 1, Defect A).
        self.assertEqual(rows[0]["family"], "")

    def test_family_empty_for_non_simple_command_shape(self):
        control_flow_command = 'for f in *.py; do rg pattern "$f"; done'
        control_flow_rec = capture_claude._envelope(
            "/a.jsonl",
            1,
            _assistant_bash_line(control_flow_command, cwd="/repo"),
            datetime.now(UTC).isoformat(),
        )
        unclassified_command = "echo $(git status)"
        unclassified_rec = capture_claude._envelope(
            "/a.jsonl",
            2,
            _assistant_bash_line(
                unclassified_command,
                cwd="/repo",
                session_id="sess-unclassified",
                uuid="turn-uuid-unclassified",
                tool_id="toolu_unclassified",
            ),
            datetime.now(UTC).isoformat(),
        )
        simple_rec = capture_claude._envelope(
            "/a.jsonl",
            3,
            _assistant_bash_line(
                "grep -r TODO .",
                cwd="/repo",
                session_id="sess-simple-family",
                uuid="turn-uuid-simple-family",
                tool_id="toolu_simple_family",
            ),
            datetime.now(UTC).isoformat(),
        )
        rows = refine_all([control_flow_rec, unclassified_rec, simple_rec])
        by_text = {row["command_text"]: row for row in rows}
        self.assertEqual(by_text[control_flow_command]["command_shape"], "control_flow_script")
        self.assertEqual(by_text[control_flow_command]["family"], "")
        self.assertEqual(by_text[unclassified_command]["command_shape"], "unclassified")
        self.assertEqual(by_text[unclassified_command]["family"], "")
        self.assertEqual(by_text["grep -r TODO ."]["command_shape"], "simple")
        self.assertEqual(by_text["grep -r TODO ."]["family"], "grep")

    def test_cursor_timestamp_inherited_from_preceding_user_turn(self):
        timestamp_line = json.dumps(
            {
                "role": "user",
                "message": {
                    "content": [
                        {
                            "type": "text",
                            "text": "<timestamp>Monday, Aug 31, 2026, 1:24 AM (UTC-4)</timestamp>",
                        }
                    ]
                },
            }
        )
        shell_line = _cursor_tool_use_line("Shell", {"command": "ls -la"})
        ts_rec = capture_cursor._envelope(
            "/transcript.jsonl", 1, timestamp_line, datetime.now(UTC).isoformat(),
            _CURSOR_SESSION_UUID,
        )
        shell_rec = capture_cursor._envelope(
            "/transcript.jsonl", 2, shell_line, datetime.now(UTC).isoformat(),
            _CURSOR_SESSION_UUID,
        )
        rows = refine_all([ts_rec, shell_rec])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["timestamp"], "2026-08-31T01:24:00-04:00")
        self.assertEqual(rows[0]["date"], "2026-08-31")
        self.assertEqual(rows[0]["source_confidence"], "low")

    def test_cursor_command_without_preceding_timestamp_keeps_null_date(self):
        shell_line = _cursor_tool_use_line("Shell", {"command": "ls -la"})
        shell_rec = capture_cursor._envelope(
            "/transcript.jsonl", 1, shell_line, datetime.now(UTC).isoformat(),
            _CURSOR_SESSION_UUID,
        )
        rows = refine_all([shell_rec])
        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0]["timestamp"])
        self.assertIsNone(rows[0]["date"])

    def test_cursor_unparseable_timestamp_block_yields_null_date(self):
        timestamp_line = json.dumps(
            {
                "role": "user",
                "message": {
                    "content": [
                        {
                            "type": "text",
                            "text": "<timestamp>not a real timestamp</timestamp>",
                        }
                    ]
                },
            }
        )
        shell_line = _cursor_tool_use_line("Shell", {"command": "ls -la"})
        ts_rec = capture_cursor._envelope(
            "/transcript.jsonl", 1, timestamp_line, datetime.now(UTC).isoformat(),
            _CURSOR_SESSION_UUID,
        )
        shell_rec = capture_cursor._envelope(
            "/transcript.jsonl", 2, shell_line, datetime.now(UTC).isoformat(),
            _CURSOR_SESSION_UUID,
        )
        rows = refine_all([ts_rec, shell_rec])
        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0]["timestamp"])
        self.assertIsNone(rows[0]["date"])

    def test_opencode_workdir_rebase(self):
        captured_at = datetime.now(UTC).isoformat()
        session_id = "ses_rebase"
        message_id = "msg_rebase"
        message = capture_opencode._base_envelope(
            "/opencode.db",
            "message",
            message_id,
            json.dumps({"path": {"cwd": "/repo"}}),
            captured_at,
            session_id,
            None,
            10,
        )
        with_workdir = capture_opencode._base_envelope(
            "/opencode.db",
            "part",
            "prt_wd",
            json.dumps(
                {
                    "type": "tool",
                    "tool": "bash",
                    "state": {
                        "input": {"command": "echo hi", "workdir": "/rebased"},
                    },
                }
            ),
            captured_at,
            session_id,
            message_id,
            20,
        )
        without_workdir = capture_opencode._base_envelope(
            "/opencode.db",
            "part",
            "prt_later",
            json.dumps(
                {
                    "type": "tool",
                    "tool": "bash",
                    "state": {"input": {"command": "grep -r TODO ."}},
                }
            ),
            captured_at,
            session_id,
            message_id,
            30,
        )
        rows = refine_all([message, with_workdir, without_workdir])
        by_text = {row["command_text"]: row for row in rows}
        self.assertEqual(by_text["echo hi"]["resolved_cwd"], "/rebased")
        self.assertEqual(by_text["grep -r TODO ."]["resolved_cwd"], "/rebased")

    def test_compound_steps_share_turn_id_and_tokens(self):
        rec = capture_claude._envelope(
            "/a.jsonl",
            1,
            _assistant_bash_line("cd src && grep -r TODO .", cwd="/repo"),
            datetime.now(UTC).isoformat(),
        )
        rows = refine_all([rec], env={"HOME": "/no/such/home", "XDG_CACHE_HOME": "/no"})
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["turn_id"], rows[1]["turn_id"])
        self.assertEqual(rows[0]["turn_id"], TURN_UUID)
        self.assertEqual(rows[0]["tokens_input"], rows[1]["tokens_input"])
        self.assertEqual(rows[0]["tokens_output"], rows[1]["tokens_output"])
        self.assertEqual(rows[0]["price"], rows[1]["price"])
        self.assertEqual(rows[0]["tokens_input"], 100)
        self.assertEqual(rows[0]["tokens_output"], 50)
        self.assertIsNone(rows[0]["price"])
        self.assertEqual(rows[0]["price_confidence"], "unknown")

    def test_codex_incremental_token_delta(self):
        captured_at = datetime.now(UTC).isoformat()
        session_id = _CODEX_SESSION_UUID
        path = f"/sessions/{_CODEX_ROLLOUT_NAME}"
        meta = capture_codex._envelope(
            path, 1, _codex_session_meta_line(), captured_at, session_id
        )
        token_a = capture_codex._envelope(
            path,
            2,
            json.dumps(
                {
                    "timestamp": "2026-01-15T12:00:01Z",
                    "type": "event_msg",
                    "payload": {
                        "type": "token_count",
                        "info": {
                            "total_token_usage": {
                                "input_tokens": 80,
                                "output_tokens": 20,
                                "total_tokens": 100,
                            }
                        },
                    },
                }
            ),
            captured_at,
            session_id,
        )
        cmd_a = capture_codex._envelope(
            path, 3, _codex_function_call_line(), captured_at, session_id
        )
        token_b = capture_codex._envelope(
            path,
            4,
            json.dumps(
                {
                    "timestamp": "2026-01-15T12:00:03Z",
                    "type": "event_msg",
                    "payload": {
                        "type": "token_count",
                        "info": {
                            "total_token_usage": {
                                "input_tokens": 180,
                                "output_tokens": 70,
                                "total_tokens": 250,
                            }
                        },
                    },
                }
            ),
            captured_at,
            session_id,
        )
        cmd_b = capture_codex._envelope(
            path,
            5,
            json.dumps(
                {
                    "timestamp": "2026-01-15T12:00:04Z",
                    "type": "response_item",
                    "payload": {
                        "type": "function_call",
                        "name": "exec_command",
                        "arguments": json.dumps({"cmd": "pwd"}),
                        "call_id": "call_2",
                    },
                }
            ),
            captured_at,
            session_id,
        )
        rows = refine_all([meta, token_a, cmd_a, token_b, cmd_b])
        by_text = {row["command_text"]: row for row in rows}
        self.assertEqual(by_text["ls -la"]["tokens_input"], 80)
        self.assertEqual(by_text["ls -la"]["tokens_output"], 20)
        self.assertEqual(by_text["pwd"]["tokens_input"], 100)
        self.assertEqual(by_text["pwd"]["tokens_output"], 50)
        self.assertNotEqual(by_text["pwd"]["tokens_input"], 180)
        self.assertEqual(by_text["ls -la"]["turn_id"], 2)
        self.assertEqual(by_text["pwd"]["turn_id"], 4)
        self.assertEqual(by_text["ls -la"]["model"], "unknown")
        self.assertIsNone(by_text["ls -la"]["rtk_input_tokens"])

    def test_cursor_tokens_and_price_none(self):
        line = _cursor_tool_use_line(
            "Shell",
            {"command": "ls -la", "working_directory": "/tmp/proj"},
        )
        rec = capture_cursor._envelope(
            "/transcript.jsonl",
            1,
            line,
            datetime.now(UTC).isoformat(),
            _CURSOR_SESSION_UUID,
        )
        rows = refine_all([rec])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["command_text"], "ls -la")
        self.assertIsNone(rows[0]["tokens_input"])
        self.assertIsNone(rows[0]["tokens_output"])
        self.assertIsNone(rows[0]["price"])
        self.assertEqual(rows[0]["price_confidence"], "unknown")
        self.assertEqual(rows[0]["source_confidence"], "low")
        self.assertEqual(rows[0]["resolved_cwd"], "unknown")
        self.assertIsNone(rows[0]["turn_id"])
        self.assertIsNone(rows[0]["rtk_input_tokens"])

    def test_rtk_history_populates_rtk_columns_tee_produces_none(self):
        captured_at = datetime.now(UTC).isoformat()
        history_payload = {
            "source_type": "history",
            "id": 1,
            "original_cmd": "ls -la",
            "input_tokens": 10,
            "output_tokens": 5,
            "saved_tokens": 2,
            "savings_pct": 20.0,
        }
        history = capture_rtk._envelope(
            "/rtk/history.db",
            "history",
            "1",
            history_payload,
            captured_at,
            json.dumps(history_payload),
        )
        tee_payload = {
            "source_type": "tee",
            "filename": "1_cmd.log",
            "content": "ignored",
        }
        tee = capture_rtk._envelope(
            "/rtk/tee/1_cmd.log",
            "tee",
            "1_cmd.log:abc",
            tee_payload,
            captured_at,
            "ignored",
        )
        failure_payload = {"source_type": "parse_failure", "id": 1, "raw_command": "x"}
        failure = capture_rtk._envelope(
            "/rtk/history.db",
            "parse_failure",
            "1",
            failure_payload,
            captured_at,
            json.dumps(failure_payload),
        )
        rows = refine_all([history, tee, failure])
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["runtime"], "rtk")
        self.assertEqual(row["command_text"], "ls -la")
        self.assertEqual(row["command_shape"], "simple")
        self.assertEqual(row["step_count"], 1)
        self.assertIsNone(row["operator"])
        self.assertTrue(row["execution_certain"])
        self.assertIsNone(row["model"])
        self.assertIsNone(row["tokens_input"])
        self.assertIsNone(row["tokens_output"])
        self.assertEqual(row["rtk_input_tokens"], 10)
        self.assertEqual(row["rtk_output_tokens"], 5)
        self.assertEqual(row["rtk_saved_tokens"], 2)
        self.assertEqual(row["rtk_savings_pct"], 20.0)
        self.assertIsNone(row["price"])
        self.assertEqual(row["price_confidence"], "not_applicable")
        self.assertTrue(
            (row["tokens_input"] is None) or (row["rtk_input_tokens"] is None)
        )

    def test_opencode_walk_orders_by_time_created_not_record_id(self):
        captured_at = datetime.now(UTC).isoformat()
        session_id = "ses_chrono"
        message_id = "msg_chrono"
        message = capture_opencode._base_envelope(
            "/opencode.db",
            "message",
            message_id,
            json.dumps({"path": {"cwd": "/repo"}}),
            captured_at,
            session_id,
            None,
            1,
        )
        later_grep = capture_opencode._base_envelope(
            "/opencode.db",
            "part",
            "b",
            json.dumps(
                {
                    "type": "tool",
                    "tool": "bash",
                    "state": {"input": {"command": "grep -r TODO ."}},
                }
            ),
            captured_at,
            session_id,
            message_id,
            300,
        )
        middle = capture_opencode._base_envelope(
            "/opencode.db",
            "part",
            "a",
            json.dumps(
                {
                    "type": "tool",
                    "tool": "bash",
                    "state": {"input": {"command": "echo mid"}},
                }
            ),
            captured_at,
            session_id,
            message_id,
            200,
        )
        first_cd = capture_opencode._base_envelope(
            "/opencode.db",
            "part",
            "c",
            json.dumps(
                {
                    "type": "tool",
                    "tool": "bash",
                    "state": {"input": {"command": "cd src"}},
                }
            ),
            captured_at,
            session_id,
            message_id,
            100,
        )
        rows = refine_all([message, later_grep, middle, first_cd])
        by_text = {row["command_text"]: row for row in rows}
        self.assertEqual(by_text["grep -r TODO ."]["resolved_cwd"], "/repo/src")

    def test_codex_malformed_arguments_does_not_abort(self):
        captured_at = datetime.now(UTC).isoformat()
        session_id = _CODEX_SESSION_UUID
        path = f"/sessions/{_CODEX_ROLLOUT_NAME}"
        meta = capture_codex._envelope(
            path, 1, _codex_session_meta_line(), captured_at, session_id
        )
        good_a = capture_codex._envelope(
            path, 2, _codex_function_call_line(), captured_at, session_id
        )
        bad = capture_codex._envelope(
            path,
            3,
            json.dumps(
                {
                    "timestamp": "2026-01-15T12:00:03Z",
                    "type": "response_item",
                    "payload": {
                        "type": "function_call",
                        "name": "exec_command",
                        "arguments": '{"cmd":',
                        "call_id": "call_bad",
                    },
                }
            ),
            captured_at,
            session_id,
        )
        good_b = capture_codex._envelope(
            path,
            4,
            json.dumps(
                {
                    "timestamp": "2026-01-15T12:00:04Z",
                    "type": "response_item",
                    "payload": {
                        "type": "function_call",
                        "name": "exec_command",
                        "arguments": json.dumps({"cmd": "pwd"}),
                        "call_id": "call_2",
                    },
                }
            ),
            captured_at,
            session_id,
        )
        rows = refine_all([meta, good_a, bad, good_b])
        texts = [row["command_text"] for row in rows]
        self.assertEqual(texts, ["ls -la", "pwd"])
        self.assertNotIn(None, texts)

    def test_codex_legacy_function_call_still_refines(self):
        # Confirms the pre-existing shape keeps priority and is unaffected by
        # the new custom_tool_call dispatch branch (Task 2).
        captured_at = datetime.now(UTC).isoformat()
        session_id = _CODEX_SESSION_UUID
        path = f"/sessions/{_CODEX_ROLLOUT_NAME}"
        meta = capture_codex._envelope(
            path, 1, _codex_session_meta_line(), captured_at, session_id
        )
        legacy = capture_codex._envelope(
            path, 2, _codex_function_call_line(), captured_at, session_id
        )
        rows = refine_all([meta, legacy])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["command_text"], "ls -la")
        self.assertEqual(rows[0]["resolved_cwd"], "/tmp/proj")

    def test_codex_custom_tool_call_exec_produces_command(self):
        captured_at = datetime.now(UTC).isoformat()
        session_id = _CODEX_SESSION_UUID
        path = f"/sessions/{_CODEX_ROLLOUT_NAME}"
        meta = capture_codex._envelope(
            path, 1, _codex_session_meta_line(), captured_at, session_id
        )
        ctc = capture_codex._envelope(
            path,
            2,
            _codex_custom_tool_call_line("rg -n pattern file.py", workdir="/repo"),
            captured_at,
            session_id,
        )
        rows = refine_all([meta, ctc])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["command_text"], "rg -n pattern file.py")
        self.assertEqual(rows[0]["resolved_cwd"], "/repo")

    def test_codex_custom_tool_call_compound_command_cwd_follows_cd(self):
        captured_at = datetime.now(UTC).isoformat()
        session_id = _CODEX_SESSION_UUID
        path = f"/sessions/{_CODEX_ROLLOUT_NAME}"
        meta = capture_codex._envelope(
            path, 1, _codex_session_meta_line(), captured_at, session_id
        )
        ctc = capture_codex._envelope(
            path,
            2,
            _codex_custom_tool_call_line("cd src && pwd", workdir="/repo"),
            captured_at,
            session_id,
        )
        rows = refine_all([meta, ctc])
        self.assertEqual(len(rows), 2)
        by_index = sorted(rows, key=lambda row: row["step_index"])
        self.assertEqual(by_index[0]["command_text"], "cd src")
        self.assertEqual(by_index[0]["resolved_cwd"], "/repo")
        self.assertEqual(by_index[1]["command_text"], "pwd")
        self.assertEqual(by_index[1]["resolved_cwd"], "/repo/src")

    def test_codex_custom_tool_call_without_workdir_falls_back_to_cwd_state(self):
        captured_at = datetime.now(UTC).isoformat()
        session_id = _CODEX_SESSION_UUID
        path = f"/sessions/{_CODEX_ROLLOUT_NAME}"
        meta = capture_codex._envelope(
            path, 1, _codex_session_meta_line(), captured_at, session_id
        )
        ctc = capture_codex._envelope(
            path,
            2,
            _codex_custom_tool_call_line("pwd"),
            captured_at,
            session_id,
        )
        rows = refine_all([meta, ctc])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["command_text"], "pwd")
        # Falls back to the session-seeded CwdState directory (from
        # session_meta's cwd), never an empty string.
        self.assertEqual(rows[0]["resolved_cwd"], "/tmp/proj")

    def test_codex_custom_tool_call_web_run_is_not_a_command(self):
        captured_at = datetime.now(UTC).isoformat()
        session_id = _CODEX_SESSION_UUID
        path = f"/sessions/{_CODEX_ROLLOUT_NAME}"
        meta = capture_codex._envelope(
            path, 1, _codex_session_meta_line(), captured_at, session_id
        )
        web_run = capture_codex._envelope(
            path, 2, _codex_custom_tool_call_web_run_line(), captured_at, session_id
        )
        rows = refine_all([meta, web_run])
        self.assertEqual(rows, [])

    def test_codex_custom_tool_call_malformed_body_does_not_abort(self):
        captured_at = datetime.now(UTC).isoformat()
        session_id = _CODEX_SESSION_UUID
        path = f"/sessions/{_CODEX_ROLLOUT_NAME}"
        meta = capture_codex._envelope(
            path, 1, _codex_session_meta_line(), captured_at, session_id
        )
        malformed = capture_codex._envelope(
            path,
            2,
            json.dumps(
                {
                    "timestamp": "2026-01-15T12:00:02Z",
                    "type": "response_item",
                    "payload": {
                        "type": "custom_tool_call",
                        "id": "ctc_bad",
                        "status": "completed",
                        "call_id": "call_bad_ctc",
                        "name": "exec",
                        "input": "const r = await tools.exec_command({\"cmd\":); text(r.output);",
                    },
                }
            ),
            captured_at,
            session_id,
        )
        good = capture_codex._envelope(
            path,
            3,
            _codex_custom_tool_call_line("pwd", workdir="/repo"),
            captured_at,
            session_id,
        )
        rows = refine_all([meta, malformed, good])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["command_text"], "pwd")

    def test_opencode_time_created_populates_date(self):
        # D-16 / D-19 regression: an opencode raw envelope whose ONLY
        # timestamp-shaped field is "time_created" (epoch-ms int, no
        # "timestamp" key anywhere -- matching the real capture shape from
        # capture_opencode.py's _base_envelope) must still produce a
        # non-NULL date/timestamp on the refined row.
        captured_at = datetime.now(UTC).isoformat()
        session_id = "ses_date_check"
        message_id = "msg_date_check"
        time_created = 1758000000000
        rec = capture_opencode._base_envelope(
            "/opencode.db",
            "part",
            "prt_date_check",
            json.dumps(
                {
                    "type": "tool",
                    "tool": "bash",
                    "state": {"input": {"command": "echo hi"}},
                }
            ),
            captured_at,
            session_id,
            message_id,
            time_created,
        )
        self.assertNotIn("timestamp", rec)
        self.assertIsNone(rec["payload"].get("timestamp"))
        rows = refine_all([rec])
        self.assertEqual(len(rows), 1)
        expected_ts = datetime.fromtimestamp(time_created / 1000, tz=UTC).isoformat()
        self.assertEqual(rows[0]["timestamp"], expected_ts)
        self.assertEqual(rows[0]["date"], expected_ts[:10])
        self.assertIsNotNone(rows[0]["date"])


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


_DASHBOARD_PY = os.path.join(
    os.path.dirname(__file__),
    "..",
    "skills",
    "ai-kit-usage-metrics",
    "ai_kit_usage_metrics",
    "dashboard.py",
)

# Markers wrapping the shipped pure JS functions so tests can extract them.
_JS_PURE_START = "/* PURE_FUNCTIONS_START */"
_JS_PURE_END = "/* PURE_FUNCTIONS_END */"

# Void HTML elements: no closing tag, so a naive stack-based nesting walker
# must not push them (there is no matching end tag to pop them back off).
_VOID_ELEMENTS = frozenset(
    {
        "area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr",
    }
)

_FULL_SCHEMA_COLUMNS = (
    "id",
    "raw_ref",
    "runtime",
    "session_id",
    "turn_id",
    "date",
    "timestamp",
    "model",
    "command_text",
    "family",
    "command_shape",
    "step_index",
    "step_count",
    "operator",
    "execution_certain",
    "resolved_cwd",
    "source_confidence",
    "tokens_input",
    "tokens_output",
    "price",
    "price_confidence",
    "rtk_input_tokens",
    "rtk_output_tokens",
    "rtk_saved_tokens",
    "rtk_savings_pct",
    "rtk_rewrote",
    "inferred_family",
    "inferred_confidence",
    "exec_duration_ms",
)


def _dashboard_row(**overrides):
    row = {
        "raw_ref": "claude:/a.jsonl:1",
        "runtime": "claude",
        "session_id": "sess-a",
        "turn_id": "turn-a",
        "date": "2026-09-10",
        "timestamp": TS_USE,
        "model": MODEL,
        "command_text": "rg TODO",
        "family": "grep",
        "command_shape": "simple",
        "step_index": 0,
        "step_count": 1,
        "operator": None,
        "execution_certain": True,
        "resolved_cwd": CWD,
        "source_confidence": "high",
        "tokens_input": 100,
        "tokens_output": 50,
        "price": 0.01,
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
    row.update(overrides)
    return row


def _this_month_prefix():
    return datetime.now().strftime("%Y-%m")


def _this_month_day(day=10):
    return f"{_this_month_prefix()}-{day:02d}"


def _last_month_day(day=10):
    year, month = datetime.now().year, datetime.now().month
    if month == 1:
        year, month = year - 1, 12
    else:
        month -= 1
    return f"{year:04d}-{month:02d}-{day:02d}"


def _parse_embedded_rows(html):
    start = html.find('<script type="application/json" id="usage-metrics-data">')
    if start < 0:
        raise AssertionError("embedded JSON script tag missing")
    open_end = html.find(">", start)
    close = html.find("</script>", open_end)
    payload = html[open_end + 1 : close].replace("<\\/script", "</script")
    return json.loads(payload)


def _extract_pure_js(html):
    # Marker convention: dashboard.py wraps filterRows/sortRows/groupBySession/
    # displayFamily between PURE_FUNCTIONS_START and PURE_FUNCTIONS_END comments.
    start = html.find(_JS_PURE_START)
    end = html.find(_JS_PURE_END)
    if start < 0 or end < 0 or end <= start:
        raise AssertionError("pure-function markers missing from generated HTML")
    return html[start + len(_JS_PURE_START) : end]


def _extract_block_after(text, marker):
    # Same brace-depth slicer as _extract_js_function_body, but anchored on
    # an arbitrary literal marker string rather than a "function <name>("
    # prefix -- used for anonymous callbacks (event listeners) that have no
    # function name of their own to search for.
    start = text.index(marker)
    brace_open = text.index("{", start)
    depth = 0
    i = brace_open
    while i < len(text):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[brace_open : i + 1]
        i += 1
    raise AssertionError("unterminated block for marker: " + marker)


def _extract_js_function_body(text, function_name):
    # Shared brace-depth slicer: locates `function <name>(` and returns the
    # exact source span from its opening `{` to the matching closing `}`.
    # Used wherever a test needs to assert something about a single named
    # function's body without executing it.
    marker = "function " + function_name + "("
    start = text.index(marker)
    brace_open = text.index("{", start)
    depth = 0
    i = brace_open
    while i < len(text):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[brace_open : i + 1]
        i += 1
    raise AssertionError("unterminated function body: " + function_name)


class TestDashboardFull(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="ai-kit-um-dash-full-")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.env = _scratch_env(self.root)
        self.this_month = _this_month_day(10)
        self.last_month = _last_month_day(10)
        self.rows = [
            _dashboard_row(
                raw_ref="claude:/a.jsonl:1",
                session_id="sess-grep-a",
                turn_id="turn-grep-a",
                date=self.this_month,
                command_text="rg TODO",
                family="grep",
                tokens_input=100,
                tokens_output=50,
                price=0.01,
            ),
            _dashboard_row(
                raw_ref="claude:/a.jsonl:2",
                session_id="sess-grep-b",
                turn_id="turn-grep-b",
                date=self.this_month,
                command_text="rg FIXME",
                family="grep",
                tokens_input=80,
                tokens_output=20,
                price=0.008,
            ),
            _dashboard_row(
                raw_ref="claude:/a.jsonl:3",
                session_id="sess-ls",
                turn_id="turn-ls",
                date=self.this_month,
                command_text="ls -la",
                family="ls",
                model="claude-sonnet-4-5",
                tokens_input=10,
                tokens_output=5,
                price=0.001,
            ),
            _dashboard_row(
                raw_ref="claude:/a.jsonl:4",
                session_id="sess-old",
                turn_id="turn-old",
                date=self.last_month,
                command_text="rg OLD",
                family="grep",
                tokens_input=40,
                tokens_output=10,
                price=0.004,
            ),
            _dashboard_row(
                raw_ref="claude:/a.jsonl:5",
                session_id="sess-inferred",
                turn_id="turn-inferred",
                date=self.this_month,
                command_text='for f in *.py; do rg pattern "$f"; done',
                family="",
                command_shape="control_flow_script",
                inferred_family="grep",
                inferred_confidence="LOW",
                tokens_input=200,
                tokens_output=30,
                price=0.02,
            ),
            _dashboard_row(
                raw_ref="cursor:/t.jsonl:1",
                runtime="cursor",
                session_id="sess-cursor",
                turn_id="turn-cursor",
                date=self.this_month,
                command_text="cat notes.md",
                family="cat",
                model="cursor-composer",
                source_confidence="low",
                tokens_input=None,
                tokens_output=None,
                price=None,
            ),
            _dashboard_row(
                raw_ref="claude:/a.jsonl:6",
                session_id="sess-compound",
                turn_id="turn-compound",
                date=self.this_month,
                command_text="cd src",
                family="cd",
                step_index=0,
                step_count=2,
                operator=None,
                execution_certain=True,
                tokens_input=300,
                tokens_output=100,
                price=0.05,
            ),
            _dashboard_row(
                raw_ref="claude:/a.jsonl:6",
                session_id="sess-compound",
                turn_id="turn-compound",
                date=self.this_month,
                command_text="rg TODO",
                family="grep",
                step_index=1,
                step_count=2,
                operator="&&",
                execution_certain=False,
                tokens_input=300,
                tokens_output=100,
                price=0.05,
            ),
        ]

    def _seed_and_generate(self):
        conn = refined_store.open_refined_db(self.env)
        refined_store.insert_commands(conn, self.rows)
        conn.close()
        ro = refined_store.open_refined_db_readonly(self.env)
        self.addCleanup(ro.close)
        out = os.path.join(self.root, "dashboard.html")
        generate(ro, out)
        with open(out, encoding="utf-8") as handle:
            html = handle.read()
        return html, out

    def test_readonly_generate_roundtrips_full_schema(self):
        html, _out = self._seed_and_generate()
        embedded = _parse_embedded_rows(html)
        self.assertEqual(len(embedded), len(self.rows))
        for col in _FULL_SCHEMA_COLUMNS:
            self.assertTrue(
                any(col in row for row in embedded),
                f"column {col!r} missing from embedded JSON",
            )
        inferred = [row for row in embedded if row.get("inferred_family") == "grep"]
        self.assertEqual(len(inferred), 1)
        self.assertEqual(inferred[0]["inferred_confidence"], "LOW")
        cursor_rows = [row for row in embedded if row.get("runtime") == "cursor"]
        self.assertEqual(len(cursor_rows), 1)
        self.assertEqual(cursor_rows[0]["source_confidence"], "low")

    def test_each_mvp_axis_has_filter_and_sortable_header(self):
        html, _out = self._seed_and_generate()
        # D-10/D-11: runtime already carries a sortable header (Plan 01);
        # subfamily's sortable header is added by Task 3's column reorder
        # and is asserted there (test_column_order_matches_d12) rather than
        # duplicated here -- Task 2 only owns the filter bar, not <thead>.
        axes = {
            "runtime": ("filter-runtime", "runtime"),
            "model": ("filter-model", "model"),
            "family": ("filter-family", "family"),
            "tokens": ("filter-tokens-min", "tokens_input"),
            "price": ("filter-price-min", "price"),
        }
        self.assertIn('id="filter-command"', html)
        self.assertIn('data-sort-key="command_text"', html)
        self.assertIn('data-sort-key="tokens_output"', html)
        self.assertIn('id="filter-tokens-max"', html)
        self.assertIn('id="filter-price-max"', html)
        self.assertIn('id="group-by-session"', html)
        self.assertIn('id="filter-subfamily"', html)
        # D-13: the 4 separate date controls are replaced by a single
        # from/to range -- no preset/day/start/end id survives.
        self.assertIn('id="filter-date-from"', html)
        self.assertIn('id="filter-date-to"', html)
        self.assertNotIn('id="filter-date-preset"', html)
        self.assertNotIn('id="filter-date-day"', html)
        self.assertNotIn('id="filter-date-start"', html)
        self.assertNotIn('id="filter-date-end"', html)
        for axis, (filter_id, sort_key) in axes.items():
            self.assertIn(
                f'id="{filter_id}"',
                html,
                f"{axis} filter control missing",
            )
            self.assertIn(
                f'data-sort-key="{sort_key}"',
                html,
                f"{axis} sortable header missing",
            )

    def test_inferred_family_and_source_confidence_and_conditional_markers(self):
        html, _out = self._seed_and_generate()
        self.assertIn("(inferred,", html)
        self.assertIn("LOW", html)
        self.assertIn("source_confidence", html)
        # Copywriting Contract: the execution-uncertain marker is now an
        # error-tinted "conditional" badge, not the old parenthesised text.
        self.assertNotIn("(conditional)", html)
        with open(_DASHBOARD_PY, encoding="utf-8") as handle:
            source = handle.read()
        exec_body = _extract_js_function_body(source, "flatRowBuilder")
        self.assertIn('"conditional"', exec_body)
        self.assertIn('exec.className = "badge"', exec_body)

    def test_group_by_session_dedups_turn_tokens(self):
        html, _out = self._seed_and_generate()
        pure = _extract_pure_js(html)
        rows = _parse_embedded_rows(html)
        compound = [r for r in rows if r.get("session_id") == "sess-compound"]
        self.assertEqual(len(compound), 2)
        wrapper = os.path.join(self.root, "group_check.js")
        fixture = os.path.join(self.root, "compound.json")
        with open(fixture, "w", encoding="utf-8") as handle:
            json.dump(compound, handle)
        with open(wrapper, "w", encoding="utf-8") as handle:
            handle.write(pure)
            handle.write(
                "\nconst rows = require("
                + json.dumps(fixture)
                + ");\n"
                + "const grouped = groupBySession(rows);\n"
                + "console.log(JSON.stringify(grouped));\n"
            )
        if shutil.which("node") is None:
            self.skipTest("node not available — shipped-JS execution test skipped")
        proc = subprocess.run(
            ["node", wrapper], capture_output=True, text=True, check=True
        )
        grouped = json.loads(proc.stdout)
        self.assertEqual(len(grouped), 1)
        session = grouped[0]
        self.assertEqual(session["count"], 2)
        self.assertEqual(session["tokens_input"], 300)
        self.assertEqual(session["tokens_output"], 100)
        self.assertEqual(session["price"], 0.05)

    def test_turn_key_and_group_by_session_null_turn_via_node(self):
        if shutil.which("node") is None:
            self.skipTest("node not available — shipped-JS execution test skipped")
        html, _out = self._seed_and_generate()
        pure = _extract_pure_js(html)
        rows = [
            # (a) three sibling null-turn rows sharing raw_ref r1 -- must
            # contribute their shared figures exactly ONCE, not 3x.
            {
                "session_id": "sess-null-mix",
                "turn_id": None,
                "raw_ref": "r1",
                "step_index": 0,
                "tokens_input": 100,
                "tokens_output": 20,
                "price": 0.01,
            },
            {
                "session_id": "sess-null-mix",
                "turn_id": None,
                "raw_ref": "r1",
                "step_index": 1,
                "tokens_input": 100,
                "tokens_output": 20,
                "price": 0.01,
            },
            {
                "session_id": "sess-null-mix",
                "turn_id": None,
                "raw_ref": "r1",
                "step_index": 2,
                "tokens_input": 100,
                "tokens_output": 20,
                "price": 0.01,
            },
            # (b) two sibling null-turn rows sharing raw_ref r2 -- a DIFFERENT
            # command, must contribute its own figures once, separately.
            {
                "session_id": "sess-null-mix",
                "turn_id": None,
                "raw_ref": "r2",
                "step_index": 0,
                "tokens_input": 50,
                "tokens_output": 10,
                "price": 0.005,
            },
            {
                "session_id": "sess-null-mix",
                "turn_id": None,
                "raw_ref": "r2",
                "step_index": 1,
                "tokens_input": 50,
                "tokens_output": 10,
                "price": 0.005,
            },
            # (c) one null-turn row, its own raw_ref, own figures.
            {
                "session_id": "sess-null-mix",
                "turn_id": None,
                "raw_ref": "r3",
                "step_index": 0,
                "tokens_input": 7,
                "tokens_output": 3,
                "price": 0.002,
            },
            # A second, independent session covering the ALREADY-correct
            # non-null-turn compound case -- proves this change did not
            # regress it (test_group_by_session_dedups_turn_tokens above is
            # left byte-for-byte unchanged as the primary regression guard).
            {
                "session_id": "sess-turn-ok",
                "turn_id": "t1",
                "raw_ref": "r4",
                "step_index": 0,
                "tokens_input": 40,
                "tokens_output": 5,
                "price": 0.002,
            },
            {
                "session_id": "sess-turn-ok",
                "turn_id": "t1",
                "raw_ref": "r4",
                "step_index": 1,
                "tokens_input": 40,
                "tokens_output": 5,
                "price": 0.002,
            },
        ]
        fixture = os.path.join(self.root, "turn_key_rows.json")
        with open(fixture, "w", encoding="utf-8") as handle:
            json.dump(rows, handle)
        wrapper = os.path.join(self.root, "turn_key_check.js")
        with open(wrapper, "w", encoding="utf-8") as handle:
            handle.write(pure)
            handle.write(
                "\nconst rows = require("
                + json.dumps(fixture)
                + ");\n"
                "const grouped = groupBySession(rows);\n"
                "console.log(JSON.stringify(grouped));\n"
            )
        proc = subprocess.run(
            ["node", wrapper], capture_output=True, text=True, check=True
        )
        grouped = {item["session_id"]: item for item in json.loads(proc.stdout)}

        null_mix = grouped["sess-null-mix"]
        self.assertEqual(null_mix["count"], 6)
        self.assertEqual(null_mix["tokens_input"], 157)
        self.assertEqual(null_mix["tokens_output"], 33)
        self.assertAlmostEqual(null_mix["price"], 0.017)
        # The no-dedup regression: summing all 6 raw rows instead of the 3
        # distinct raw_refs.
        self.assertNotEqual(null_mix["tokens_input"], 407)
        # The old collapse-everything regression: keying only on session_id
        # (or session_id + turn_id with turn_id always null) would have kept
        # just the first row's figures.
        self.assertNotEqual(null_mix["tokens_input"], 100)

        turn_ok = grouped["sess-turn-ok"]
        self.assertEqual(turn_ok["count"], 2)
        self.assertEqual(turn_ok["tokens_input"], 40)
        self.assertEqual(turn_ok["tokens_output"], 5)
        self.assertAlmostEqual(turn_ok["price"], 0.002)

    def test_subfamily_js_matches_spec_table_and_python(self):
        # Round-1 review finding: a parity test that only proves the JS and
        # Python outputs agree can pass while BOTH violate the real spec
        # table (e.g. both porting a wrong "skip flags, take next token"
        # rule). Assertion (a) against the hardcoded expectations is what
        # closes that gap.
        if shutil.which("node") is None:
            self.skipTest("node not available — shipped-JS execution test skipped")
        html, _out = self._seed_and_generate()
        pure = _extract_pure_js(html)
        cases_fixture = os.path.join(self.root, "subfamily_cases.json")
        with open(cases_fixture, "w", encoding="utf-8") as handle:
            json.dump([cmd for cmd, _expected in SUBFAMILY_SPEC_CASES], handle)
        wrapper = os.path.join(self.root, "subfamily_check.js")
        with open(wrapper, "w", encoding="utf-8") as handle:
            handle.write(pure)
            handle.write(
                "\nconst cases = require("
                + json.dumps(cases_fixture)
                + ");\n"
                + "console.log(JSON.stringify(cases.map(subfamilyOf)));\n"
            )
        proc = subprocess.run(
            ["node", wrapper], capture_output=True, text=True, check=True
        )
        js_results = json.loads(proc.stdout)
        expected = [expected for _cmd, expected in SUBFAMILY_SPEC_CASES]
        python_results = [family.subfamily_of(cmd) for cmd, _expected in SUBFAMILY_SPEC_CASES]
        # (a) JavaScript vs the hardcoded spec-table expectations.
        self.assertEqual(js_results, expected)
        # (b) Python vs the same hardcoded spec-table expectations.
        self.assertEqual(python_results, expected)
        # (c) JavaScript vs Python, element-for-element.
        self.assertEqual(js_results, python_results)

    def test_decorate_subfamily_gates_on_command_shape_via_node(self):
        if shutil.which("node") is None:
            self.skipTest("node not available — shipped-JS execution test skipped")
        html, _out = self._seed_and_generate()
        pure = _extract_pure_js(html)
        fixture = os.path.join(self.root, "decorate_rows.json")
        rows = [
            {"command_shape": "simple", "command_text": "git -C /path commit"},
            {
                "command_shape": "control_flow_script",
                "command_text": "for f in *.py; do rg x; done",
            },
            {"command_shape": "unclassified", "command_text": "echo $( git status )"},
        ]
        with open(fixture, "w", encoding="utf-8") as handle:
            json.dump(rows, handle)
        wrapper = os.path.join(self.root, "decorate_check.js")
        with open(wrapper, "w", encoding="utf-8") as handle:
            handle.write(pure)
            handle.write(
                "\nconst rows = require("
                + json.dumps(fixture)
                + ");\n"
                + "function subs(r) { return r.map(function (x) { return x.subfamily; }); }\n"
                + "const first = subs(decorateSubfamily(rows));\n"
                + "const second = subs(decorateSubfamily(rows));\n"
                + "console.log(JSON.stringify({first: first, second: second}));\n"
            )
        proc = subprocess.run(
            ["node", wrapper], capture_output=True, text=True, check=True
        )
        result = json.loads(proc.stdout)
        self.assertEqual(result["first"], ["commit", "", ""])
        self.assertEqual(result["second"], ["commit", "", ""])

    def test_filter_rows_runtime_subfamily_and_date_range_via_node(self):
        if shutil.which("node") is None:
            self.skipTest("node not available — shipped-JS execution test skipped")
        html, _out = self._seed_and_generate()
        pure = _extract_pure_js(html)
        rows = [
            {"id": "r1", "runtime": "claude", "subfamily": "commit", "date": "2026-01-01"},
            {"id": "r2", "runtime": "opencode", "subfamily": "commit", "date": "2026-01-05"},
            {"id": "r3", "runtime": "claude", "subfamily": "status", "date": "2026-01-10"},
            {"id": "r4", "runtime": "claude", "subfamily": "status", "date": None},
            {"id": "r5", "runtime": "opencode", "subfamily": "pull", "date": "2026-01-03"},
        ]
        fixture = os.path.join(self.root, "filter_axes_rows.json")
        with open(fixture, "w", encoding="utf-8") as handle:
            json.dump(rows, handle)
        wrapper = os.path.join(self.root, "filter_axes_check.js")
        with open(wrapper, "w", encoding="utf-8") as handle:
            handle.write(pure)
            handle.write(
                "\nconst rows = require("
                + json.dumps(fixture)
                + ");\n"
                "function ids(r) { return r.map(function (x) { return x.id; }); }\n"
                "const result = {\n"
                "  runtimeClaude: ids(filterRows(rows, {runtime: 'claude'})),\n"
                "  runtimeAll: ids(filterRows(rows, {runtime: 'all'})),\n"
                "  subfamilyCommit: ids(filterRows(rows, {subfamily: 'commit'})),\n"
                "  dateFromOnly: ids(filterRows(rows, {dateFrom: '2026-01-05'})),\n"
                "  dateToOnly: ids(filterRows(rows, {dateTo: '2026-01-05'})),\n"
                "  dateSingleDay: ids(filterRows(rows, "
                "{dateFrom: '2026-01-05', dateTo: '2026-01-05'})),\n"
                "  noDateConstraint: ids(filterRows(rows, {})),\n"
                "  clearedReturnsAll: ids(filterRows(rows, clearedCriteria())),\n"
                "};\n"
                "console.log(JSON.stringify(result));\n"
            )
        proc = subprocess.run(
            ["node", wrapper], capture_output=True, text=True, check=True
        )
        result = json.loads(proc.stdout)
        self.assertEqual(set(result["runtimeClaude"]), {"r1", "r3", "r4"})
        self.assertEqual(set(result["runtimeAll"]), {"r1", "r2", "r3", "r4", "r5"})
        self.assertEqual(set(result["subfamilyCommit"]), {"r1", "r2"})
        # from-only: keeps every row on or after that date; null date (r4)
        # is excluded once a bound is set.
        self.assertEqual(set(result["dateFromOnly"]), {"r2", "r3"})
        # to-only: keeps every row on or before that date; null date
        # excluded the same way.
        self.assertEqual(set(result["dateToOnly"]), {"r1", "r2", "r5"})
        # both ends set to the same value expresses a single day.
        self.assertEqual(set(result["dateSingleDay"]), {"r2"})
        # neither end set -> no date constraint at all; the null-date row
        # is included.
        self.assertEqual(
            set(result["noDateConstraint"]), {"r1", "r2", "r3", "r4", "r5"}
        )
        self.assertEqual(
            set(result["clearedReturnsAll"]), {"r1", "r2", "r3", "r4", "r5"}
        )

    def test_clear_filters_covers_every_filter_control(self):
        html, _out = self._seed_and_generate()
        filter_ids = sorted(set(re.findall(r'id="(filter-[a-z-]+)"', html)))
        self.assertTrue(filter_ids, "no filter-* ids found in generated HTML")
        body = _extract_js_function_body(html, "clearFilters")
        for filter_id in filter_ids:
            self.assertIn(
                filter_id,
                body,
                f"clearFilters does not reset {filter_id!r}",
            )
        # SD-9: group-by-session is a view mode, not a filter -- clearFilters
        # must never touch it.
        self.assertNotIn("group-by-session", body)

    def test_material_selects_are_populated_with_select_options(self):
        html, _out = self._seed_and_generate()
        self.assertIn('@material/web@2.5.0/select/select-option.js?module', html)
        with open(_DASHBOARD_PY, encoding="utf-8") as handle:
            source = handle.read()
        body = _extract_js_function_body(source, "fillSelect")
        self.assertIn('createElement("md-select-option")', body)
        self.assertIn('slot = "headline"', body)
        self.assertNotIn('createElement("option")', body)

    def test_three_chart_canvases_and_pinned_chartjs(self):
        html, _out = self._seed_and_generate()
        self.assertIn('id="runtime-chart"', html)
        self.assertIn('id="per-day-chart"', html)
        self.assertIn('id="family-chart"', html)
        self.assertIn("chart.js@4.5.1", html)
        self.assertEqual(len(re.findall(r"<canvas\b", html)), 3)

    def test_per_day_aggregation_dedups_before_summing_via_node(self):
        if shutil.which("node") is None:
            self.skipTest("node not available — shipped-JS execution test skipped")
        html, _out = self._seed_and_generate()
        pure = _extract_pure_js(html)
        rows = []
        # Three sibling rows sharing raw_ref r1/turn_id t1 on one date -- must
        # contribute their turn-level figures ONCE, not three times.
        for step in range(3):
            rows.append(
                {
                    "raw_ref": "r1",
                    "session_id": "s1",
                    "turn_id": "t1",
                    "date": "2026-02-01",
                    "runtime": "claude",
                    "step_index": step,
                    "tokens_input": 100,
                    "tokens_output": 10,
                    "price": 0.5,
                }
            )
        # Two sibling rows sharing raw_ref r2, NULL turn_id -- dedup on
        # (session_id, raw_ref) instead.
        for step in range(2):
            rows.append(
                {
                    "raw_ref": "r2",
                    "session_id": "s1",
                    "turn_id": None,
                    "date": "2026-02-01",
                    "runtime": "claude",
                    "step_index": step,
                    "tokens_input": 50,
                    "tokens_output": 5,
                    "price": 0.25,
                }
            )
        # A single row, raw_ref r3, NULL turn_id -- its own distinct key.
        rows.append(
            {
                "raw_ref": "r3",
                "session_id": "s1",
                "turn_id": None,
                "date": "2026-02-01",
                "runtime": "claude",
                "step_index": 0,
                "tokens_input": 7,
                "tokens_output": 1,
                "price": 0.1,
            }
        )
        # A null-price row contributes nothing; a genuine zero-price row
        # still contributes a zero -- these must be distinguishable.
        rows.append(
            {
                "raw_ref": "r4",
                "session_id": "s2",
                "turn_id": "t4",
                "date": "2026-02-02",
                "runtime": "claude",
                "step_index": 0,
                "tokens_input": 10,
                "tokens_output": 0,
                "price": None,
            }
        )
        rows.append(
            {
                "raw_ref": "r5",
                "session_id": "s2",
                "turn_id": "t5",
                "date": "2026-02-03",
                "runtime": "claude",
                "step_index": 0,
                "tokens_input": 10,
                "tokens_output": 0,
                "price": 0,
            }
        )
        # A null-date row is omitted from the per-day chart entirely.
        rows.append(
            {
                "raw_ref": "r6",
                "session_id": "s3",
                "turn_id": "t6",
                "date": None,
                "runtime": "claude",
                "step_index": 0,
                "tokens_input": 999,
                "tokens_output": 999,
                "price": 9,
            }
        )
        fixture = os.path.join(self.root, "per_day_rows.json")
        with open(fixture, "w", encoding="utf-8") as handle:
            json.dump(rows, handle)
        wrapper = os.path.join(self.root, "per_day_check.js")
        with open(wrapper, "w", encoding="utf-8") as handle:
            handle.write(pure)
            handle.write(
                "\nconst rows = require("
                + json.dumps(fixture)
                + ");\n"
                + "console.log(JSON.stringify(aggregateTokensAndPriceByDay(rows)));\n"
            )
        proc = subprocess.run(["node", wrapper], capture_output=True, text=True, check=True)
        agg = json.loads(proc.stdout)
        self.assertEqual(agg["dates"], ["2026-02-01", "2026-02-02", "2026-02-03"])
        idx1 = agg["dates"].index("2026-02-01")
        total_tokens = sum(series[idx1] for series in agg["tokensByRuntime"])
        self.assertEqual(total_tokens, 173)
        self.assertAlmostEqual(agg["price"][idx1], 0.85)
        # The no-dedup regression: naively summing all 6 raw rows directly.
        self.assertNotEqual(total_tokens, 448)
        idx2 = agg["dates"].index("2026-02-02")
        self.assertIsNone(agg["price"][idx2])
        idx3 = agg["dates"].index("2026-02-03")
        self.assertEqual(agg["price"][idx3], 0)
        # r6's null date never introduces a fourth date.
        self.assertEqual(len(agg["dates"]), 3)

    def test_family_distribution_cap_and_tie_order_via_node(self):
        if shutil.which("node") is None:
            self.skipTest("node not available — shipped-JS execution test skipped")
        html, _out = self._seed_and_generate()
        pure = _extract_pure_js(html)
        labels_counts = [(f"fam{i:02d}", 20 - i) for i in range(14)]
        # A deliberate count tie straddling the 15/16 cutoff: famTieA must
        # win rank 15 (ascending label), famTieB falls into the remainder.
        labels_counts += [("famTieA", 6), ("famTieB", 6), ("famRest", 5)]
        rows = []
        for label, count in labels_counts:
            for _ in range(count):
                rows.append({"family": label, "subfamily": ""})
        fixture = os.path.join(self.root, "family_dist_rows.json")
        with open(fixture, "w", encoding="utf-8") as handle:
            json.dump(rows, handle)
        wrapper = os.path.join(self.root, "family_dist_check.js")
        with open(wrapper, "w", encoding="utf-8") as handle:
            handle.write(pure)
            handle.write(
                "\nconst rows = require("
                + json.dumps(fixture)
                + ");\n"
                + "console.log(JSON.stringify(aggregateFamilyDistribution(rows)));\n"
            )
        proc = subprocess.run(["node", wrapper], capture_output=True, text=True, check=True)
        agg = json.loads(proc.stdout)
        self.assertEqual(len(agg["labels"]), 16)
        self.assertEqual(agg["labels"][14], "famTieA")
        self.assertNotIn("famTieB", agg["labels"][:15])
        self.assertEqual(agg["labels"][15], "other (2 more)")
        self.assertEqual(agg["counts"][15], 11)

    def test_sort_event_does_not_recompute_charts(self):
        html, _out = self._seed_and_generate()
        self.assertIn('id="per-day-chart"', html)
        with open(_DASHBOARD_PY, encoding="utf-8") as handle:
            source = handle.read()
        th_click_block = _extract_block_after(
            source, 'th.addEventListener("click", function () {'
        )
        self.assertIn("applySort", th_click_block)
        self.assertNotIn("applyFilters", th_click_block)
        apply_sort_body = _extract_js_function_body(source, "applySort")
        for forbidden in ("buildRuntimeChart", "buildPerDayChart", "buildFamilyDistributionChart"):
            self.assertNotIn(forbidden, apply_sort_body)
        self.assertIn(
            'filtersForm.addEventListener("input", debouncedApplyFilters)', source
        )
        self.assertIn("debounce(applyFilters, 150)", source)

    def test_charts_row_and_filters_are_layout_siblings(self):
        # D-20: #filters and #charts-row are siblings inside one flex/grid
        # parent (#dashboard-top), not two independently stacked full-width
        # blocks -- a source-level structural check rather than a rendered
        # layout measurement, since this suite has no browser harness.
        html, _out = self._seed_and_generate()
        wrap_start = html.index('id="dashboard-top"')
        wrap_open = html.rindex("<div", 0, wrap_start)
        charts_row_pos = html.index('id="charts-row"', wrap_open)
        filters_pos = html.index('id="filters"', wrap_open)
        wrap_close = html.index("</div>", filters_pos)
        # Both live between the wrapper's opening tag and its first closing
        # </div> that follows the filter bar -- i.e. inside the same parent.
        self.assertTrue(wrap_open < charts_row_pos < wrap_close)
        self.assertTrue(wrap_open < filters_pos < wrap_close)
        # Charts row first per UI-SPEC.md's focal-point ordering -- D-20
        # only moves filters from stacked-below to beside, not reorders.
        self.assertLess(charts_row_pos, filters_pos)
        with open(_DASHBOARD_PY, encoding="utf-8") as handle:
            source = handle.read()
        self.assertIn("#dashboard-top {", source)
        self.assertIn("display: flex", _extract_block_after(source, "#dashboard-top {"))

    def test_chart_canvases_have_no_fixed_pixel_dimensions(self):
        html, _out = self._seed_and_generate()
        for match in re.finditer(r"<canvas\b[^>]*>", html):
            tag = match.group(0)
            self.assertNotIn("width=", tag)
            self.assertNotIn("height=", tag)
            style_match = re.search(r'style="([^"]*)"', tag)
            if style_match:
                self.assertNotRegex(style_match.group(1), r"(width|height):\s*\d+px")
        with open(_DASHBOARD_PY, encoding="utf-8") as handle:
            source = handle.read()
        # The shared wrapper's height is clamp()-based, never a bare
        # fixed-pixel value.
        wrap_block = _extract_block_after(source, ".chart-canvas-wrap {")
        self.assertNotRegex(wrap_block, r"height:\s*\d+px")
        self.assertIn("clamp(", wrap_block)
        # Every new Chart(...) options object opts into Chart.js's own
        # responsive resize handling (>= one per chart; a comment may also
        # mention the phrase, so this is a floor, not an exact count).
        self.assertGreaterEqual(source.count("responsive: true"), 3)

    def test_column_order_matches_d12(self):
        html, _out = self._seed_and_generate()
        expected_order = [
            "runtime",
            "model",
            "family",
            "subfamily",
            "command_text",
            "exec_duration_ms",
            "date",
            "tokens_input",
            "tokens_output",
            "price",
            "source_confidence",
            "execution_certain",
            "session_id",
        ]
        found = re.findall(r'data-sort-key="([a-z_]+)"', html)
        # #thead-grouped repeats session_id/count/tokens_input/tokens_output/
        # price after the flat #thead-flat row -- only the first 13 entries
        # (the flat header) are checked against D-12's locked order.
        self.assertEqual(found[:13], expected_order)

    def test_null_and_zero_price_and_null_date_render_distinctly(self):
        if shutil.which("node") is None:
            self.skipTest("node not available — shipped-JS execution test skipped")
        html, _out = self._seed_and_generate()
        pure = _extract_pure_js(html)
        wrapper = os.path.join(self.root, "null_zero_check.js")
        with open(wrapper, "w", encoding="utf-8") as handle:
            handle.write(pure)
            handle.write(
                "\nconst result = {\n"
                "  nullPrice: priceCellText(null),\n"
                "  zeroPrice: priceCellText(0),\n"
                "  nullDate: dateCellText(null),\n"
                "  realDate: dateCellText('2026-09-10'),\n"
                "};\n"
                "console.log(JSON.stringify(result));\n"
            )
        proc = subprocess.run(
            ["node", wrapper], capture_output=True, text=True, check=True
        )
        result = json.loads(proc.stdout)
        self.assertEqual(result["nullPrice"], "—")
        self.assertEqual(result["zeroPrice"], "0")
        self.assertEqual(result["nullDate"], "—")
        self.assertEqual(result["realDate"], "2026-09-10")
        # RESEARCH.md: 16,366 rows have a genuine zero price alongside
        # 37,231 rows with no price at all -- these must never collapse to
        # the same rendered text.
        self.assertNotEqual(result["nullPrice"], result["zeroPrice"])

    def test_price_tooltip_distinguishes_rtk_not_applicable_from_catalog_miss(self):
        html, _out = self._seed_and_generate()
        body = _extract_js_function_body(html, "priceTd")
        self.assertIn("PRICE_NOT_APPLICABLE_TOOLTIP", body)
        self.assertIn("PRICE_UNKNOWN_TOOLTIP", body)
        self.assertIn("not_applicable", body)
        # rtk rows carry price_confidence "not_applicable" (refiner.py never
        # attempts a catalog lookup for them) and must not show the same
        # "not in catalog" tooltip a genuine claude/codex/cursor catalog
        # miss shows -- that would falsely imply rtk should have a
        # priceable model.
        self.assertIn("not applicable", html)
        self.assertIn("not in catalog", html)

    def test_command_cell_wraps_to_two_lines(self):
        with open(_DASHBOARD_PY, encoding="utf-8") as handle:
            source = handle.read()
        style_start = source.index("<style>")
        style_end = source.index("</style>")
        style = source[style_start:style_end]
        style = re.sub(r"/\*.*?\*/", "", style, flags=re.S)
        rules = re.findall(r"([^{}]+)\{([^{}]*)\}", style)
        clamp_rules = [(sel.strip(), body) for sel, body in rules if "line-clamp" in body]
        self.assertTrue(clamp_rules, "no -webkit-line-clamp rule found")
        for selector, body in clamp_rules:
            self.assertIn(".command-text", selector)
            self.assertNotIn("td", selector)
            self.assertRegex(body, r"-webkit-line-clamp:\s*2\b")
        command_text_rules = [
            (sel.strip(), body) for sel, body in rules if ".command-text" in sel
        ]
        self.assertTrue(command_text_rules, "no .command-text rule found")
        for _selector, body in command_text_rules:
            # The Round-1 review's flagged contradiction with D-12 -- a
            # single-line no-wrap command cell must never come back.
            self.assertNotIn("white-space: nowrap", body)

    def test_step_marker_is_outside_the_clamped_element(self):
        with open(_DASHBOARD_PY, encoding="utf-8") as handle:
            source = handle.read()
        body = _extract_js_function_body(source, "commandCell")
        # The marker is appended to the cell itself -- a sibling of
        # .command-text -- never inside .command-text, so a two-line clamp
        # can never swallow it.
        self.assertIn("cell.appendChild(marker)", body)
        self.assertNotIn("text.appendChild(marker)", body)
        style_start = source.index("<style>")
        style_end = source.index("</style>")
        style = source[style_start:style_end]
        style = re.sub(r"/\*.*?\*/", "", style, flags=re.S)
        rules = re.findall(r"([^{}]+)\{([^{}]*)\}", style)
        marker_rules = [(sel.strip(), body) for sel, body in rules if ".step-marker" in sel]
        self.assertTrue(marker_rules, "no .step-marker rule found")
        _selector, marker_body = marker_rules[0]
        self.assertRegex(marker_body, r"flex:\s*0\s+0\s+auto")
        self.assertIn("min-width", marker_body)

    def test_slice_for_items_materializes_only_virtual_items_via_node(self):
        # Dependency-free proof that materialization is bounded by the
        # virtual window (20 items) rather than by the row count (84,082
        # rows) -- the production path (sliceForItems) is exercised
        # directly, not a parallel test-only implementation.
        if shutil.which("node") is None:
            self.skipTest("node not available — shipped-JS execution test skipped")
        html, _out = self._seed_and_generate()
        pure = _extract_pure_js(html)
        wrapper = os.path.join(self.root, "slice_check.js")
        row_count = 84082
        item_count = 20
        offset = 500
        with open(wrapper, "w", encoding="utf-8") as handle:
            handle.write(pure)
            handle.write(
                "\nconst rowCount = "
                + str(row_count)
                + ";\nconst rows = [];\n"
                "for (let i = 0; i < rowCount; i++) { rows.push({index: i}); }\n"
                "const offset = "
                + str(offset)
                + ";\nconst items = [];\n"
                "for (let i = 0; i < "
                + str(item_count)
                + "; i++) { items.push({index: offset + i, start: i * 56}); }\n"
                "const result = sliceForItems(rows, items);\n"
                "console.log(JSON.stringify(result));\n"
            )
        proc = subprocess.run(
            ["node", wrapper], capture_output=True, text=True, check=True
        )
        result = json.loads(proc.stdout)
        self.assertEqual(len(result), item_count)
        for i, entry in enumerate(result):
            self.assertEqual(entry["index"], offset + i)
            self.assertEqual(entry["start"], i * 56)
            self.assertEqual(entry["row"]["index"], offset + i)

    def test_single_tbody_paint_path_and_valid_table_nesting(self):
        html, _out = self._seed_and_generate()
        script_start = html.find("<script>\n")
        self.assertNotEqual(script_start, -1)
        script = html[script_start:]

        append_sites = [m.start() for m in re.finditer(r"tbody\.appendChild\(", script)]
        self.assertEqual(
            len(append_sites),
            1,
            "expected exactly one call site appending rows to usage-tbody",
        )

        _named_function_re = re.compile(r"function\s+[A-Za-z_$][\w$]*\s*\([^)]*\)\s*\{")

        def _function_body_containing(text, index):
            # Climb to the nearest ENCLOSING NAMED function (skip anonymous
            # callbacks like the forEach(function (entry) {...}) the append
            # call itself sits inside) -- the named function is the one
            # whose body is asserted to iterate sliceForItems.
            matches = list(_named_function_re.finditer(text[:index]))
            self.assertTrue(matches, "append site is not inside a named function")
            func_start = matches[-1].start()
            brace_open = matches[-1].end() - 1
            depth = 0
            i = brace_open
            while i < len(text):
                if text[i] == "{":
                    depth += 1
                elif text[i] == "}":
                    depth -= 1
                    if depth == 0:
                        return text[func_start : i + 1]
                i += 1
            raise AssertionError("unterminated function body")

        func_body = _function_body_containing(script, append_sites[0])
        self.assertIn("sliceForItems(", func_body)

        # renderGrouped's append-every-row loop is deleted, not kept
        # alongside -- both modes now route through the one painter above.
        self.assertNotIn("function renderGrouped", script)
        self.assertNotIn("function renderFlat", script)

        class _TableNestingParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.stack = []
                self.table_parent = None
                self.table_children = []
                self.has_thead = False
                self.has_usage_tbody = False
                self._table_depth = None

            def handle_starttag(self, tag, attrs):
                attr_dict = dict(attrs)
                if tag == "table" and attr_dict.get("id") == "usage-table":
                    if self.stack:
                        parent_tag, parent_attrs = self.stack[-1]
                        self.table_parent = (parent_tag, parent_attrs.get("id"))
                    else:
                        self.table_parent = (None, None)
                    self._table_depth = len(self.stack)
                elif (
                    self._table_depth is not None
                    and len(self.stack) == self._table_depth + 1
                ):
                    self.table_children.append(tag)
                    if tag == "thead":
                        self.has_thead = True
                    if tag == "tbody" and attr_dict.get("id") == "usage-tbody":
                        self.has_usage_tbody = True
                if tag not in _VOID_ELEMENTS:
                    self.stack.append((tag, attr_dict))

            def handle_endtag(self, tag):
                if self.stack and self.stack[-1][0] == tag:
                    self.stack.pop()
                    # Stop tracking "direct children of the table" once the
                    # table itself has closed -- otherwise a later sibling
                    # at the same stack depth (e.g. the D-14 dialog markup
                    # that now follows #table-scroll) would be misidentified
                    # as a table child just because the depths happen to
                    # coincide.
                    if (
                        tag == "table"
                        and self._table_depth is not None
                        and len(self.stack) == self._table_depth
                    ):
                        self._table_depth = None

        parser = _TableNestingParser()
        parser.feed(html)
        # #table-scroll wraps the ENTIRE <table>; a wrapper is never placed
        # between <table> and <tbody> (that would be invalid HTML, re-parented
        # by the browser).
        self.assertEqual(parser.table_parent, ("div", "table-scroll"))
        legal_children = {"caption", "colgroup", "thead", "tbody", "tfoot", "tr"}
        self.assertTrue(parser.table_children, "table had no direct element children")
        for child in parser.table_children:
            self.assertIn(child, legal_children)
        # Deliberately NOT asserting tbody is the first child or that no tag
        # intervenes between <table> and <tbody> -- SD-2's sticky <thead>
        # legitimately precedes <tbody>. The property proven here is legal
        # table ancestry, not source ordering.
        self.assertTrue(parser.has_thead)
        self.assertTrue(parser.has_usage_tbody)

    def test_group_by_session_checkbox_has_visible_unfocused_styling(self):
        # D-22 regression: the checkbox must have visible border/fill
        # contrast in its DEFAULT (unfocused, unchecked) state -- a rule
        # scoped only to :focus/:hover would still leave it invisible on
        # first paint, which is exactly the bug this guards against.
        with open(_DASHBOARD_PY, encoding="utf-8") as handle:
            source = handle.read()
        style_start = source.index("<style>")
        style_end = source.index("</style>")
        style = source[style_start:style_end]
        # Strip CSS comments first -- a descriptive comment mentioning
        # ":focus"/":hover" in prose must not be mistaken for a pseudo-class
        # qualifying the selector itself.
        style = re.sub(r"/\*.*?\*/", "", style, flags=re.S)
        rules = re.findall(r"([^{}]+)\{([^{}]*)\}", style)
        unfocused_rules = [
            (selector, body)
            for selector, body in rules
            if "#group-by-session" in selector
            and ":focus" not in selector
            and ":hover" not in selector
        ]
        self.assertTrue(
            unfocused_rules,
            "no unfocused #group-by-session CSS rule found — checkbox would "
            "be invisible until it receives focus",
        )
        self.assertTrue(
            any(
                re.search(r"\bborder\b", body) or re.search(r"\bbackground\b", body)
                for _selector, body in unfocused_rules
            ),
            "expected visible border/fill contrast in the unfocused rule body",
        )

    def test_result_count_reflects_matching_rows(self):
        html, _out = self._seed_and_generate()
        self.assertIn('id="result-count"', html)
        body = _extract_js_function_body(html, "repaintTable")
        self.assertIn("resultCount", body)
        self.assertIn("currentFiltered.length", body)
        self.assertIn("currentRows.length", body)
        # grouped and flat modes count different things (sessions vs raw
        # matching commands) -- the text must distinguish them, not print
        # the same phrase for both.
        self.assertIn("matching commands", body)
        self.assertIn("sessions", body)

    def test_date_range_presets_exist_and_default_to_last_30_days(self):
        # User-directed feature: airline/hotel-booking-style quick-select
        # chips beside the from/to range control, with "last 30 days" (not
        # an unfiltered view of the full embedded dataset) as the default
        # active state on initial page load.
        html, _out = self._seed_and_generate()
        for preset in ("today", "week", "month", "current-month", "all"):
            self.assertIn('data-preset="%s"' % preset, html)
        body = _extract_js_function_body(html, "applyDatePreset")
        self.assertIn('"filter-date-from"', body)
        self.assertIn('"filter-date-to"', body)
        self.assertIn("markActiveDatePreset", body)
        self.assertIn("applyFilters", body)
        # The bootstrap must call the "month" preset, not a bare
        # applyFilters() over the unfiltered dataset, so the initial paint
        # is already narrowed to the last 30 days.
        self.assertIn('applyDatePreset("month");', html)

    def test_grouped_mode_header_matches_grouped_cell_count(self):
        # D-23 regression: <thead>'s visible header row must always match
        # the cell count/meaning of whichever builder (flat vs grouped) is
        # currently painting -- never flat's fixed 11-column header shown
        # over grouped's 5-cell rows (or vice versa).
        html, _out = self._seed_and_generate()
        thead_start = html.index("<thead>")
        thead_end = html.index("</thead>", thead_start)
        thead = html[thead_start:thead_end]

        flat_row_match = re.search(r'<tr id="thead-flat"[^>]*>(.*?)</tr>', thead, re.S)
        grouped_row_match = re.search(
            r'<tr id="thead-grouped"[^>]*>(.*?)</tr>', thead, re.S
        )
        self.assertIsNotNone(flat_row_match, "no #thead-flat header row found")
        self.assertIsNotNone(grouped_row_match, "no #thead-grouped header row found")

        flat_header_count = len(re.findall(r"<th\b", flat_row_match.group(1)))
        grouped_header_count = len(re.findall(r"<th\b", grouped_row_match.group(1)))

        with open(_DASHBOARD_PY, encoding="utf-8") as handle:
            source = handle.read()

        flat_body = _extract_js_function_body(source, "flatRowBuilder")
        grouped_body = _extract_js_function_body(source, "groupedRowBuilder")
        flat_cell_count = len(re.findall(r"tr\.appendChild\(", flat_body))
        grouped_cell_count = len(re.findall(r"tr\.appendChild\(", grouped_body))

        self.assertEqual(flat_header_count, flat_cell_count)
        self.assertEqual(grouped_header_count, grouped_cell_count)
        self.assertEqual(grouped_header_count, 5)
        # D-10/D-12 (Plan 03 Task 3): flat mode grew from 11 to 13 columns
        # (+subfamily, +exec time).
        self.assertEqual(flat_header_count, 13)

        # No padding/placeholder cell added solely to preserve flat mode's
        # column count in grouped mode.
        self.assertNotEqual(grouped_header_count, flat_header_count)

    def test_no_data_driven_innerhtml_assignment(self):
        html, _out = self._seed_and_generate()
        script_start = html.find("<script>\n")
        self.assertNotEqual(script_start, -1)
        script = html[script_start:]
        self.assertIsNone(re.search(r"innerHTML\s*=\s*[`]", script))
        self.assertIsNone(re.search(r"innerHTML\s*=\s*.*\brow\b", script))
        with open(_DASHBOARD_PY, encoding="utf-8") as handle:
            source = handle.read()
        self.assertIsNone(re.search(r"innerHTML\s*=\s*[`]", source))
        self.assertEqual(
            len(re.findall(r"\.innerHTML\s*=", source)),
            0,
        )

    def test_shipped_js_canonical_query_via_node(self):
        if shutil.which("node") is None:
            self.skipTest("node not available — shipped-JS execution test skipped")
        html, _out = self._seed_and_generate()
        pure = _extract_pure_js(html)
        rows = _parse_embedded_rows(html)
        wrapper = os.path.join(self.root, "canonical.js")
        fixture = os.path.join(self.root, "rows.json")
        with open(fixture, "w", encoding="utf-8") as handle:
            json.dump(rows, handle)
        # D-13: the removed 'current_month' preset is expressed as an
        # explicit dateFrom/dateTo range covering this calendar month.
        month_prefix = self.this_month[:7]
        date_from = month_prefix + "-01"
        date_to = month_prefix + "-31"
        with open(wrapper, "w", encoding="utf-8") as handle:
            handle.write(pure)
            handle.write(
                "\nconst rows = require("
                + json.dumps(fixture)
                + ");\n"
                + "const filtered = filterRows(rows, "
                "{family: 'grep', dateFrom: " + json.dumps(date_from) + ", "
                "dateTo: " + json.dumps(date_to) + "});\n"
                + "const grouped = groupBySession(filtered);\n"
                + "console.log(JSON.stringify({filtered: filtered.length, grouped: grouped}));\n"
            )
        proc = subprocess.run(
            ["node", wrapper], capture_output=True, text=True, check=True
        )
        result = json.loads(proc.stdout)
        # grep-family this month: sess-grep-a, sess-grep-b, sess-compound (rg step).
        # last-month rg OLD is excluded. inferred-family row has family="" so
        # the mechanical family filter does not match it.
        self.assertEqual(result["filtered"], 3)
        by_session = {item["session_id"]: item for item in result["grouped"]}
        self.assertEqual(set(by_session), {"sess-grep-a", "sess-grep-b", "sess-compound"})
        self.assertEqual(by_session["sess-grep-a"]["count"], 1)
        self.assertEqual(by_session["sess-grep-b"]["count"], 1)
        self.assertEqual(by_session["sess-compound"]["count"], 1)
        self.assertEqual(by_session["sess-compound"]["tokens_input"], 300)
        self.assertEqual(by_session["sess-compound"]["tokens_output"], 100)
        self.assertEqual(by_session["sess-compound"]["price"], 0.05)

    def test_generate_ignores_missing_raw_jsonl(self):
        conn = refined_store.open_refined_db(self.env)
        refined_store.insert_commands(conn, self.rows)
        conn.close()
        raw = paths.raw_dir(self.env)
        os.makedirs(raw, exist_ok=True)
        dummy = os.path.join(raw, "claude.jsonl")
        with open(dummy, "w", encoding="utf-8") as handle:
            handle.write("{}\n")
        os.unlink(dummy)
        ro = refined_store.open_refined_db_readonly(self.env)
        self.addCleanup(ro.close)
        out = os.path.join(self.root, "dashboard.html")
        generate(ro, out)
        with open(out, encoding="utf-8") as handle:
            html = handle.read()
        embedded = _parse_embedded_rows(html)
        self.assertEqual(len(embedded), len(self.rows))

    def test_dashboard_py_imports_no_network_modules(self):
        with open(_DASHBOARD_PY, encoding="utf-8") as handle:
            tree = ast.parse(handle.read())
        forbidden = {"urllib", "http", "requests", "socket"}
        found = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    found.add(alias.name.split(".", 1)[0])
            elif isinstance(node, ast.ImportFrom) and node.module:
                found.add(node.module.split(".", 1)[0])
        self.assertEqual(found & forbidden, set())

    def test_command_dialog_markup_copy_and_step_section(self):
        html, _out = self._seed_and_generate()
        self.assertIn('<md-dialog id="command-dialog">', html)
        self.assertIn(">Copy command<", html)
        self.assertIn('aria-label="Close dialog"', html)
        self.assertIn('aria-label="Copy command"', html)
        self.assertIn('id="table-scroll" tabindex="-1"', html)
        with open(_DASHBOARD_PY, encoding="utf-8") as handle:
            source = handle.read()
        cell_body = _extract_js_function_body(source, "commandCell")
        self.assertIn('setAttribute("tabindex", "0")', cell_body)
        style_start = source.index("<style>")
        style_end = source.index("</style>")
        style = source[style_start:style_end]
        style = re.sub(r"/\*.*?\*/", "", style, flags=re.S)
        rules = re.findall(r"([^{}]+)\{([^{}]*)\}", style)
        dialog_rules = [(sel.strip(), body) for sel, body in rules if "#command-dialog" in sel]
        self.assertTrue(dialog_rules, "no #command-dialog CSS rule found")
        self.assertTrue(
            any("max-height" in body for _sel, body in dialog_rules),
            "no max-height constraint on the dialog surface",
        )
        steps_rules = [(sel.strip(), body) for sel, body in rules if ".dialog-steps" in sel]
        self.assertTrue(steps_rules, "no .dialog-steps CSS rule found")
        self.assertTrue(
            any("overflow-y" in body for _sel, body in steps_rules),
            "step list does not scroll internally",
        )

    def test_dialog_restores_focus_and_handles_clipboard_refusal(self):
        html, _out = self._seed_and_generate()
        script_start = html.find("<script>\n")
        self.assertNotEqual(script_start, -1)
        script = html[script_start:]

        self.assertIn("var dialogTrigger = null;", script)
        self.assertIn("dialogTrigger = trigger;", script)

        closed_body = _extract_block_after(
            script, 'dialogEl.addEventListener("closed", function () {'
        )
        self.assertIn("dialogTrigger.isConnected", closed_body)
        self.assertIn("dialogTrigger.focus()", closed_body)
        self.assertIn("scrollEl.focus()", closed_body)
        self.assertIn("dialogTrigger = null;", closed_body)

        activate_body = _extract_js_function_body(script, "activateCommandCell")
        self.assertIn('closest("[tabindex]")', activate_body)

        keydown_body = _extract_block_after(
            script, 'tbody.addEventListener("keydown", function (event) {'
        )
        self.assertIn('event.key !== "Enter" && event.key !== " "', keydown_body)
        self.assertIn("event.preventDefault()", keydown_body)
        self.assertIn("activateCommandCell(event)", keydown_body)

        copy_body = _extract_block_after(
            script, 'dialogCopyButton.addEventListener("click", function () {'
        )
        self.assertIn("navigator.clipboard", copy_body)
        self.assertIn("typeof navigator.clipboard.writeText", copy_body)
        self.assertIn(".catch(showFailure)", copy_body)
        self.assertIn("showFailure", copy_body)
        self.assertIn("showSuccess", copy_body)

    def test_step_entries_resolve_siblings_via_node(self):
        if shutil.which("node") is None:
            self.skipTest("node not available — shipped-JS execution test skipped")
        html, _out = self._seed_and_generate()
        pure = _extract_pure_js(html)
        rows = [
            {
                "raw_ref": "rr1",
                "step_index": 0,
                "step_count": 3,
                "operator": None,
                "command_text": "cd src",
            },
            {
                "raw_ref": "rr1",
                "step_index": 2,
                "step_count": 3,
                "operator": "||",
                "command_text": "rg TODO",
            },
            {
                "raw_ref": "rr1",
                "step_index": 1,
                "step_count": 3,
                "operator": "&&",
                "command_text": "ls -la",
            },
            {
                "raw_ref": "rr2",
                "step_index": 0,
                "step_count": 1,
                "operator": None,
                "command_text": "echo hi",
            },
        ]
        fixture = os.path.join(self.root, "step_entries_rows.json")
        with open(fixture, "w", encoding="utf-8") as handle:
            json.dump(rows, handle)
        wrapper = os.path.join(self.root, "step_entries_check.js")
        with open(wrapper, "w", encoding="utf-8") as handle:
            handle.write(pure)
            handle.write(
                "\nconst rows = require("
                + json.dumps(fixture)
                + ");\n"
                "const fullIdx = indexByRawRef(rows);\n"
                "const bucketOrder = fullIdx.get('rr1').map(function (r) "
                "{ return r.step_index; });\n"
                "const forStep0 = stepEntries(fullIdx, rows[0]);\n"
                "const forStep2Row = stepEntries(fullIdx, rows[1]);\n"
                "const forSingle = stepEntries(fullIdx, rows[3]);\n"
                "// Prove the index must be built over the FULL payload: an\n"
                "// index built over a filtered subset that dropped 2 of the\n"
                "// 3 rr1 siblings resolves an incomplete breakdown, while\n"
                "// the full-payload index resolves all 3.\n"
                "const filteredRows = [rows[0], rows[3]];\n"
                "const filteredIdx = indexByRawRef(filteredRows);\n"
                "const filteredEntries = stepEntries(filteredIdx, rows[0]);\n"
                "console.log(JSON.stringify({\n"
                "  bucketOrder: bucketOrder,\n"
                "  forStep0: forStep0,\n"
                "  forStep2Row: forStep2Row,\n"
                "  forSingle: forSingle,\n"
                "  filteredEntries: filteredEntries,\n"
                "}));\n"
            )
        proc = subprocess.run(
            ["node", wrapper], capture_output=True, text=True, check=True
        )
        result = json.loads(proc.stdout)
        self.assertEqual(result["bucketOrder"], [0, 1, 2])
        self.assertEqual(len(result["forStep0"]), 3)
        self.assertEqual(len(result["forStep2Row"]), 3)
        self.assertEqual(result["forStep0"], result["forStep2Row"])
        self.assertEqual(
            [entry["position"] for entry in result["forStep0"]], [1, 2, 3]
        )
        self.assertEqual(
            [entry["operator"] for entry in result["forStep0"]], ["", "&&", "||"]
        )
        self.assertEqual(result["forSingle"], [])
        # The full-payload index resolves all 3 siblings even though this
        # particular call activated the row via a filtered subset elsewhere.
        self.assertEqual(len(result["filteredEntries"]), 1)
        self.assertNotEqual(len(result["filteredEntries"]), len(result["forStep0"]))

    def test_empty_error_and_loading_states_present(self):
        html, _out = self._seed_and_generate()
        self.assertIn("No commands match these filters", html)
        self.assertIn("Widen the date range or clear a filter to see more.", html)
        self.assertIn("Couldn't load usage data.", html)
        self.assertIn("ai-kit-usage-metrics dashboard", html)
        self.assertIn("md-linear-progress", html)
        self.assertIn('id="loading-progress"', html)
        self.assertIn('id="page-error-state"', html)
        self.assertIn('id="table-empty-state"', html)
        # Both states start hidden -- the loading bar is what's visible
        # first, not the empty/error copy.
        self.assertIn('id="page-error-state" class="state-panel state-panel--error" hidden', html)
        self.assertIn('id="table-empty-state" class="state-panel" hidden', html)

        if shutil.which("node") is None:
            self.skipTest("node not available — shipped-JS execution test skipped")
        pure = _extract_pure_js(html)
        wrapper = os.path.join(self.root, "empty_state_check.js")
        with open(wrapper, "w", encoding="utf-8") as handle:
            handle.write(pure)
            handle.write(
                "\nconsole.log(JSON.stringify({\n"
                "  empty: shouldShowEmptyState([]),\n"
                "  nonEmpty: shouldShowEmptyState([{id: 1}]),\n"
                "}));\n"
            )
        proc = subprocess.run(
            ["node", wrapper], capture_output=True, text=True, check=True
        )
        result = json.loads(proc.stdout)
        self.assertTrue(result["empty"])
        self.assertFalse(result["nonEmpty"])

    def test_bootstrap_defers_initialization_behind_two_frames(self):
        html, _out = self._seed_and_generate()
        script_start = html.find("<script>\n")
        self.assertNotEqual(script_start, -1)
        script = html[script_start:]
        self.assertRegex(
            script,
            r"requestAnimationFrame\(function \(\) \{\s*requestAnimationFrame\(initialize\);",
        )
        self.assertIn("setTimeout(initialize, 0)", script)
        init_body = _extract_js_function_body(script, "initialize")
        self.assertIn("decorateSubfamily(data)", init_body)
        self.assertIn("indexByRawRef(data)", init_body)
        self.assertIn("loadingBar.remove()", init_body)
        self.assertIn("setFilterControlsDisabled(false)", init_body)
        # The removal/re-enable happens INSIDE the deferred callback, never
        # at the top level of the inline script (which would defeat SD-10's
        # paint guarantee — the whole point is that nothing heavy runs
        # before the browser has painted the bar at least once).
        top_level_after_init = script[script.index("function initialize()") :]
        defer_call_index = top_level_after_init.index("setFilterControlsDisabled(true)")
        self.assertLess(
            top_level_after_init.index("function initialize()"), defer_call_index
        )

    def test_empty_state_predicate_hides_filter_events_from_top_level(self):
        # Filter controls are disabled for the SAME duration the loading bar
        # is present (UI-SPEC.md's explicit sub-decision) -- proven at the
        # source level via the same setFilterControlsDisabled(true) call
        # immediately preceding the deferred bootstrap.
        html, _out = self._seed_and_generate()
        script_start = html.find("<script>\n")
        script = html[script_start:]
        bootstrap_tail = script[script.index("setFilterControlsDisabled(true);") :]
        self.assertIn("requestAnimationFrame", bootstrap_tail[:400])


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
        with patch("ai_kit_usage_metrics.cli.webbrowser.open"):
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
        with patch("ai_kit_usage_metrics.cli.webbrowser.open"):
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

        with patch("ai_kit_usage_metrics.cli.webbrowser.open"):
            rc2 = main(["run"], env=self.env)
        self.assertEqual(rc2, 0)
        self.assertEqual(_count_jsonl_lines(raw_path), raw_count)
        self.assertEqual(_refined_row_count(self.env), 1)


class TestTracer151(unittest.TestCase):
    """Phase 15.1 Plan 01 tracer: opencode date fix + Material/virtualized/
    auto-opened dashboard, proven end-to-end through one real `run` path."""

    def test_run_end_to_end_opencode_date_material_virtualized_autoopen(self):
        root = tempfile.mkdtemp(prefix="ai-kit-um-tracer151-")
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        env = _scratch_env(root)
        _write_opencode_db(env, _seed_standard_opencode)

        with patch("ai_kit_usage_metrics.cli.webbrowser.open") as mock_open:
            rc = main(["run"], env=env)
        self.assertEqual(rc, 0)

        mock_open.assert_called_once()
        (opened_url,), _kwargs = mock_open.call_args
        self.assertTrue(opened_url.startswith("file://"))
        self.assertTrue(opened_url.endswith(paths.dashboard_html_path(env)))

        conn = sqlite3.connect(paths.refined_db_path(env))
        try:
            row = conn.execute(
                "SELECT date FROM refined_commands WHERE runtime = 'opencode'"
            ).fetchone()
        finally:
            conn.close()
        self.assertIsNotNone(row)
        self.assertIsNotNone(row[0])

        with open(paths.dashboard_html_path(env), encoding="utf-8") as handle:
            html = handle.read()
        self.assertIn("@material/web@2.5.0", html)
        self.assertIn("@tanstack/virtual-core@3.17.11", html)
        self.assertIn("chart.js@4.5.1", html)

        thead_start = html.index("<thead>") + len("<thead>")
        first_th_tag = re.search(r"<th[^>]*>", html[thead_start:])
        self.assertIsNotNone(first_th_tag)
        self.assertIn('data-sort-key="runtime"', first_th_tag.group(0))

        self.assertIn("md-checkbox", html)
        self.assertIn("prefers-color-scheme: dark", html)
        self.assertIn('id="table-scroll"', html)


PRD_LOOP_RG_PY = 'for f in *.py; do rg pattern "$f"; done'
PRD_LOOP_RG_MD = 'for x in *.md; do rg other "$x"; done'
PRD_LOOP_GREP = 'for f in *.py; do grep pattern "$f"; done'
PRD_SKELETON = "for <VAR> in <ARG>; do rg <ARG> <STR>; done"
SINGLETON_LOOP = 'for z in *.txt; do echo hello "$z"; done'


def _classify_row(raw_ref, command_text, command_shape="control_flow_script", family="for"):
    return {
        "raw_ref": raw_ref,
        "runtime": "claude",
        "session_id": SESSION_ID,
        "turn_id": TURN_UUID,
        "date": "2026-09-10",
        "timestamp": TS_USE,
        "model": MODEL,
        "command_text": command_text,
        "family": family,
        "command_shape": command_shape,
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


class TestClassifyLoop(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="ai-kit-um-classify-")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.env = _scratch_env(self.root)

    def _seed(self, rows):
        conn = refined_store.open_refined_db(self.env)
        self.addCleanup(conn.close)
        refined_store.insert_commands(conn, rows)
        return conn

    def _fetch(self, conn, raw_ref):
        return conn.execute(
            "SELECT family, command_shape, inferred_family, inferred_confidence "
            "FROM refined_commands WHERE raw_ref = ?",
            (raw_ref,),
        ).fetchone()

    def test_normalize_skeleton_matches_prd_examples(self):
        self.assertEqual(
            normalize_skeleton(PRD_LOOP_RG_PY),
            normalize_skeleton(PRD_LOOP_RG_MD),
        )

    def test_normalize_skeleton_does_not_rewrite_existing_placeholders(self):
        self.assertEqual(normalize_skeleton(PRD_LOOP_RG_PY), PRD_SKELETON)
        self.assertIn("<STR>", normalize_skeleton(PRD_LOOP_RG_PY))
        self.assertNotIn(
            "<ARG>; done",
            normalize_skeleton(PRD_LOOP_RG_PY).replace("<ARG>; do", ""),
        )

    def test_infer_family_for_group_recognizes_literal_curated_member(self):
        family_name, confidence = infer_family_for_group(
            normalize_skeleton(PRD_LOOP_GREP),
            PRD_LOOP_GREP,
        )
        self.assertEqual(family_name, "grep")
        self.assertEqual(confidence, "LOW")

    def test_infer_family_for_group_ambiguous_returns_none(self):
        sample = 'for f in *.py; do grep pattern "$f"; cat "$f"; done'
        family_name, confidence = infer_family_for_group(
            normalize_skeleton(sample),
            sample,
        )
        self.assertIsNone(family_name)
        self.assertIsNone(confidence)

    def test_mine_recurring_shapes_filters_by_min_occurrences(self):
        rows = [
            {"id": 1, "command_text": PRD_LOOP_RG_PY, "command_shape": "control_flow_script"},
            {"id": 2, "command_text": PRD_LOOP_RG_MD, "command_shape": "control_flow_script"},
            {"id": 3, "command_text": SINGLETON_LOOP, "command_shape": "control_flow_script"},
        ]
        groups = mine_recurring_shapes(rows, min_occurrences=2)
        self.assertEqual(len(groups), 1)
        skeleton, grouped = next(iter(groups.items()))
        self.assertEqual(skeleton, PRD_SKELETON)
        self.assertEqual(len(grouped), 2)

    def test_prd_for_loop_attaches_low_confidence_grep(self):
        conn = self._seed(
            [
                _classify_row("claude:/a.jsonl:1", PRD_LOOP_RG_PY),
                _classify_row("claude:/a.jsonl:2", PRD_LOOP_RG_MD),
                _classify_row("claude:/a.jsonl:3", SINGLETON_LOOP),
            ]
        )
        summary = run_classification(conn)
        self.assertEqual(summary["groups_found"], 1)
        self.assertEqual(summary["rows_reclassified"], 2)
        row1 = self._fetch(conn, "claude:/a.jsonl:1")
        row2 = self._fetch(conn, "claude:/a.jsonl:2")
        row3 = self._fetch(conn, "claude:/a.jsonl:3")
        self.assertEqual(row1[2], "grep")
        self.assertEqual(row1[3], "LOW")
        self.assertEqual(row2[2], "grep")
        self.assertEqual(row2[3], "LOW")
        self.assertIsNone(row3[2])
        self.assertIsNone(row3[3])

    def test_family_and_command_shape_unchanged(self):
        conn = self._seed(
            [
                _classify_row("claude:/a.jsonl:1", PRD_LOOP_RG_PY, family="for"),
                _classify_row("claude:/a.jsonl:2", PRD_LOOP_RG_MD, family="for"),
                _classify_row("claude:/a.jsonl:3", SINGLETON_LOOP, family="for"),
            ]
        )
        before = conn.execute(
            "SELECT raw_ref, family, command_shape FROM refined_commands ORDER BY id"
        ).fetchall()
        run_classification(conn)
        after = conn.execute(
            "SELECT raw_ref, family, command_shape FROM refined_commands ORDER BY id"
        ).fetchall()
        self.assertEqual(before, after)

    def test_rollback_on_partial_failure(self):
        conn = self._seed(
            [
                _classify_row("claude:/a.jsonl:1", PRD_LOOP_RG_PY),
                _classify_row("claude:/a.jsonl:2", PRD_LOOP_RG_MD),
                _classify_row(
                    "claude:/a.jsonl:3",
                    'for a in *.c; do cat "$a"; done',
                ),
                _classify_row(
                    "claude:/a.jsonl:4",
                    'for b in *.h; do cat "$b"; done',
                ),
            ]
        )
        calls = {"n": 0}

        def _boom(conn, row_id, inferred_family, inferred_confidence):
            calls["n"] += 1
            if calls["n"] > 1:
                raise RuntimeError("injected failure")
            refined_store.update_inferred_family(
                conn, row_id, inferred_family, inferred_confidence
            )

        with (
            patch(
                "ai_kit_usage_metrics.classify_loop.refined_store.update_inferred_family",
                side_effect=_boom,
            ),
            self.assertRaises(RuntimeError),
        ):
            run_classification(conn)
        rows = conn.execute(
            "SELECT inferred_family, inferred_confidence FROM refined_commands"
        ).fetchall()
        self.assertTrue(all(family_val is None and conf is None for family_val, conf in rows))

    def test_idempotent_rerun(self):
        conn = self._seed(
            [
                _classify_row("claude:/a.jsonl:1", PRD_LOOP_RG_PY),
                _classify_row("claude:/a.jsonl:2", PRD_LOOP_RG_MD),
                _classify_row("claude:/a.jsonl:3", SINGLETON_LOOP),
            ]
        )
        first = run_classification(conn)
        second = run_classification(conn)
        self.assertEqual(first, second)
        row1 = self._fetch(conn, "claude:/a.jsonl:1")
        self.assertEqual(row1[2], "grep")
        self.assertEqual(row1[3], "LOW")

    def test_lower_threshold_reclassifies_below_threshold_group(self):
        conn = self._seed(
            [
                _classify_row("claude:/a.jsonl:1", PRD_LOOP_RG_PY),
                _classify_row("claude:/a.jsonl:2", SINGLETON_LOOP),
            ]
        )
        first = run_classification(conn, min_occurrences=2)
        self.assertEqual(first["rows_reclassified"], 0)
        self.assertIsNone(self._fetch(conn, "claude:/a.jsonl:1")[2])
        second = run_classification(conn, min_occurrences=1)
        self.assertEqual(second["rows_reclassified"], 1)
        self.assertEqual(self._fetch(conn, "claude:/a.jsonl:1")[2], "grep")
        self.assertEqual(self._fetch(conn, "claude:/a.jsonl:1")[3], "LOW")

    def test_higher_threshold_clears_stale_annotation(self):
        conn = self._seed(
            [
                _classify_row("claude:/a.jsonl:1", PRD_LOOP_RG_PY),
                _classify_row("claude:/a.jsonl:2", PRD_LOOP_RG_MD),
            ]
        )
        run_classification(conn, min_occurrences=2)
        self.assertEqual(self._fetch(conn, "claude:/a.jsonl:1")[2], "grep")
        run_classification(conn, min_occurrences=3)
        self.assertIsNone(self._fetch(conn, "claude:/a.jsonl:1")[2])
        self.assertIsNone(self._fetch(conn, "claude:/a.jsonl:1")[3])
        self.assertIsNone(self._fetch(conn, "claude:/a.jsonl:2")[2])
        self.assertIsNone(self._fetch(conn, "claude:/a.jsonl:2")[3])

    def test_unclassified_rows_are_mined(self):
        conn = self._seed(
            [
                _classify_row(
                    "claude:/a.jsonl:1",
                    PRD_LOOP_RG_PY,
                    command_shape="unclassified",
                ),
                _classify_row(
                    "claude:/a.jsonl:2",
                    PRD_LOOP_RG_MD,
                    command_shape="unclassified",
                ),
            ]
        )
        summary = run_classification(conn)
        self.assertEqual(summary["rows_reclassified"], 2)
        self.assertEqual(self._fetch(conn, "claude:/a.jsonl:1")[2], "grep")
        self.assertEqual(self._fetch(conn, "claude:/a.jsonl:1")[3], "LOW")

    def test_cli_classify_subcommand_prints_summary(self):
        conn = self._seed(
            [
                _classify_row("claude:/a.jsonl:1", PRD_LOOP_RG_PY),
                _classify_row("claude:/a.jsonl:2", PRD_LOOP_RG_MD),
            ]
        )
        conn.close()
        from io import StringIO

        buf = StringIO()
        with patch("sys.stdout", buf):
            rc = main(["classify"], env=self.env)
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("groups_found", out)
        self.assertIn("rows_reclassified", out)

    def test_run_subcommand_does_not_invoke_classify(self):
        import inspect

        from ai_kit_usage_metrics import cli as cli_mod

        src = inspect.getsource(cli_mod.main)
        run_idx = src.find('cmd == "run"')
        classify_idx = src.find('cmd == "classify"')
        self.assertNotEqual(run_idx, -1)
        self.assertNotEqual(classify_idx, -1)
        run_block = src[run_idx:src.find("return 0", run_idx) + len("return 0")]
        self.assertNotIn("cmd_classify", run_block)
        self.assertIn("cmd_capture", run_block)
        self.assertIn("cmd_refine", run_block)
        self.assertIn("cmd_dashboard", run_block)


_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_MAKEFILE_PATH = os.path.join(_REPO, "Makefile")
_PRECOMMIT_PATH = os.path.join(_REPO, ".pre-commit-config.yaml")
_PYPROJECT_PATH = os.path.join(_REPO, "pyproject.toml")
_PATHS_PY_CANDIDATE = (
    "skills/ai-kit-usage-metrics/ai_kit_usage_metrics/paths.py"
)
_CLASSIFY_LOOP_PY_CANDIDATE = (
    "skills/ai-kit-usage-metrics/ai_kit_usage_metrics/classify_loop.py"
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


class TestPhaseGateRegistration(unittest.TestCase):
    """Regression: Task 1's classify_loop.py must stay inside Wave 1's gates."""

    def test_classify_loop_module_matches_makefile_precommit_pyright(self):
        with open(_MAKEFILE_PATH, encoding="utf-8") as handle:
            makefile = handle.read()
        self.assertIn("tests.test_ai_kit_usage_metrics", makefile)
        self.assertIn("skills/ai-kit-usage-metrics/", makefile)
        for hook_id in ("ruff", "py-compile"):
            regex = _precommit_hook_files_regex(hook_id)
            self.assertIsNotNone(
                re.match(regex, _CLASSIFY_LOOP_PY_CANDIDATE),
                f"{_CLASSIFY_LOOP_PY_CANDIDATE} did not match {hook_id} files: {regex}",
            )
        with open(_PYPROJECT_PATH, "rb") as handle:
            data = tomllib.load(handle)
        self.assertIn("skills/ai-kit-usage-metrics", data["tool"]["pyright"]["include"])


_SKILL_MD = os.path.join(
    os.path.dirname(__file__),
    "..",
    "skills",
    "ai-kit-usage-metrics",
    "SKILL.md",
)
_REFINED_STORE_PY = os.path.join(
    os.path.dirname(__file__),
    "..",
    "skills",
    "ai-kit-usage-metrics",
    "ai_kit_usage_metrics",
    "refined_store.py",
)


def _schema_column_names():
    with open(_REFINED_STORE_PY, encoding="utf-8") as handle:
        source = handle.read()
    match = re.search(
        r"CREATE TABLE IF NOT EXISTS refined_commands \((.*?)UNIQUE",
        source,
        re.DOTALL,
    )
    if match is None:
        raise AssertionError("CREATE TABLE statement not found in refined_store.py")
    names = []
    for line in match.group(1).splitlines():
        stripped = line.strip().rstrip(",")
        if not stripped:
            continue
        names.append(stripped.split()[0])
    return names


class TestSkillDocumentation(unittest.TestCase):
    def test_skill_md_documents_every_schema_column_and_classify_loop(self):
        with open(_SKILL_MD, encoding="utf-8") as handle:
            text = handle.read()
        for col in _schema_column_names():
            self.assertIn(col, text, f"SKILL.md missing column {col!r}")
        self.assertIn("classify", text)
        self.assertIn("trigger", text)

    def test_skill_md_documents_subfamily_autoopen_and_codex_limits(self):
        with open(_SKILL_MD, encoding="utf-8") as handle:
            text = handle.read()
        # Subfamily axis, and its explicit non-column status.
        self.assertIn("subfamily", text)
        self.assertIn("NOT a `refined_commands` column", text)
        # Automatic browser open, both subcommands, no opt-out.
        self.assertIn("automatically", text)
        self.assertIn("no opt-out flag", text)
        # Current codex custom_tool_call shape + its turn-id limitation.
        self.assertIn("custom_tool_call", text)
        self.assertIn("exec_command", text)
        self.assertIn("token-count-interval proxy", text)
        # Cursor inherited-timestamp statement.
        self.assertIn("inherited from the most recent preceding", text)
        # Turn-identity dedup invariant, including the null-turn fallback.
        self.assertIn("(session_id, turn_id)", text)
        self.assertIn("(session_id, raw_ref)", text)
        # D-13: the removed date-preset paragraph is gone; the Dashboard
        # section instead names the from/to range control.
        dashboard_start = text.index("## Dashboard")
        dashboard_end = text.index("## Subfamily")
        dashboard_section = text[dashboard_start:dashboard_end]
        self.assertIn("from/to date range", dashboard_section)
        self.assertNotIn("current month", dashboard_section.lower())
        self.assertNotIn("browser-clock", dashboard_section.lower())


if __name__ == "__main__":
    unittest.main()

