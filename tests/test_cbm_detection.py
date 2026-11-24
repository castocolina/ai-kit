"""codebase-memory-mcp registration reader and index helper (SPEC R3, D-05).

Every file is synthetic and lives in a scratch HOME; each env holds HOME and PATH only, and
every run_fn is a recording fake, so no test starts a process or reaches a real host config.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-spec-review"))

from ai_kit_spec import detection

from tests import host_fakes

HOSTS = ("claude", "opencode", "cursor", "copilot", "codex", "pi")
SERVER = "codebase-memory-mcp"


class _ScratchHome(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp(prefix="ai-kit-cbm-")
        self.addCleanup(shutil.rmtree, self.home, True)
        self.env = {"HOME": self.home, "PATH": ""}

    def _write(self, relative, text):
        path = os.path.join(self.home, relative)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return path


class TestRegistrationReads(_ScratchHome):
    def test_each_host_reads_registered_after_write(self):
        host_fakes.write_cbm_registration(self.home, HOSTS)
        for host in HOSTS:
            with self.subTest(host=host):
                self.assertIs(detection.cbm_registration(host, self.env).registered, True)
        self.assertIn("inferred", detection.cbm_registration("pi", self.env).detail)

    def test_claude_reads_dot_claude_json_under_claude_config_dir(self):
        base = os.path.join(self.home, "cfg")
        os.makedirs(base)
        with open(os.path.join(base, ".claude.json"), "w", encoding="utf-8") as handle:
            json.dump({"mcpServers": {SERVER: {}}}, handle)
        env = {**self.env, "CLAUDE_CONFIG_DIR": base}
        self.assertIs(detection.cbm_registration("claude", env).registered, True)
        # HOME's own file is not consulted once the variable is set
        self.assertIs(detection.cbm_registration("claude", self.env).registered, False)

    def test_relative_claude_config_dir_is_dropped_not_read_from_the_cwd(self):
        host_fakes.write_cbm_registration(self.home, ["claude"])
        env = {**self.env, "CLAUDE_CONFIG_DIR": "rel"}
        self.assertIsNone(detection.cbm_registration("claude", env).registered)

    def test_no_file_reads_not_registered(self):
        result = detection.cbm_registration("claude", self.env)
        self.assertIs(result.registered, False)
        self.assertTrue(result.detail.startswith("not registered"))

    def test_file_with_the_key_but_no_entry_reads_not_registered(self):
        self._write(".claude.json", json.dumps({"mcpServers": {"other": {}}}))
        self.assertIs(detection.cbm_registration("claude", self.env).registered, False)

    def test_disabled_entry_reads_not_registered_with_a_disabled_detail(self):
        hosts = ("claude", "opencode", "cursor", "copilot", "codex")
        host_fakes.write_cbm_registration(self.home, hosts, disabled=hosts)
        for host in hosts:
            with self.subTest(host=host):
                result = detection.cbm_registration(host, self.env)
                self.assertIs(result.registered, False)
                self.assertTrue(result.detail.startswith("disabled in "), result.detail)

    def test_malformed_entries_read_unknown(self):
        self._write(".claude.json", json.dumps({"mcpServers": {SERVER: "x"}}))
        self.assertIsNone(detection.cbm_registration("claude", self.env).registered)
        self._write(".claude.json", json.dumps({"mcpServers": []}))
        self.assertIsNone(detection.cbm_registration("claude", self.env).registered)

    def test_unparsable_file_reads_unknown(self):
        host_fakes.write_cbm_registration(self.home, ["claude"], unreadable=("claude",))
        self.assertIsNone(detection.cbm_registration("claude", self.env).registered)

    def test_a_runtime_without_a_reader_reads_unknown_never_not_registered(self):
        result = detection.cbm_registration("placeholder-cli-1", self.env)
        self.assertIsNone(result.registered)
        self.assertEqual(result.detail, "no registration reader for placeholder-cli-1")

    def test_cursor_agent_reads_like_cursor(self):
        host_fakes.write_cbm_registration(self.home, ["cursor"])
        self.assertEqual(
            detection.cbm_registration("cursor-agent", self.env),
            detection.cbm_registration("cursor", self.env),
        )

    def test_check_is_true_only_when_registered(self):
        host_fakes.write_cbm_registration(self.home, ["claude"])
        self.assertTrue(detection.check_cbm_registered("claude", self.env))
        self.assertFalse(detection.check_cbm_registered("codex", self.env))
        host_fakes.write_cbm_registration(self.home, ["cursor"], unreadable=("cursor",))
        self.assertFalse(detection.check_cbm_registered("cursor", self.env))


class TestOpencodePrecedence(_ScratchHome):
    def test_registered_only_in_the_user_opencode_json(self):
        self._write(
            ".config/opencode/opencode.json",
            json.dumps({"mcp": {SERVER: {"type": "local"}}}),
        )
        self.assertIs(detection.cbm_registration("opencode", self.env).registered, True)

    def test_registered_only_in_the_file_named_by_opencode_config(self):
        extra = self._write("elsewhere/opencode.json", json.dumps({"mcp": {SERVER: {}}}))
        env = {**self.env, "OPENCODE_CONFIG": extra}
        self.assertIs(detection.cbm_registration("opencode", env).registered, True)

    def test_opencode_config_disabling_the_entry_beats_the_user_jsonc(self):
        host_fakes.write_cbm_registration(self.home, ["opencode"])
        extra = self._write(
            "elsewhere/opencode.json", json.dumps({"mcp": {SERVER: {"enabled": False}}}))
        env = {**self.env, "OPENCODE_CONFIG": extra}
        result = detection.cbm_registration("opencode", env)
        self.assertIs(result.registered, False)
        self.assertTrue(result.detail.startswith("disabled in "), result.detail)


class TestNoWrite(_ScratchHome):
    def test_reading_every_runtime_writes_nothing_and_starts_no_process(self):
        host_fakes.write_cbm_registration(
            self.home, HOSTS, disabled=("cursor",), unreadable=("codex",))
        before = _snapshot(self.home)
        with mock.patch.object(subprocess, "run", side_effect=AssertionError("subprocess.run")), \
                mock.patch.object(subprocess, "Popen", side_effect=AssertionError("Popen")):
            for runtime in detection.RUNTIMES:
                detection.cbm_registration(runtime, self.env)
        self.assertEqual(before, _snapshot(self.home))


def _snapshot(root):
    """relative path -> (mtime_ns, bytes) for every file under `root`."""
    out = {}
    for folder, _dirs, files in os.walk(root):
        for name in files:
            path = os.path.join(folder, name)
            with open(path, "rb") as handle:
                data = handle.read()
            out[os.path.relpath(path, root)] = (os.stat(path).st_mtime_ns, data)
    return out


class TestRunCbmIndex(unittest.TestCase):
    def _recording(self, outcome):
        calls = []

        def run_fn(argv, **kwargs):
            calls.append((argv, kwargs))
            if isinstance(outcome, BaseException):
                raise outcome
            return outcome

        return run_fn, calls

    def test_runs_one_index_call_and_reports_indexed(self):
        run_fn, calls = self._recording(
            subprocess.CompletedProcess([], 0, stdout='{"status": "indexed"}\n', stderr=""))
        self.assertTrue(detection.run_cbm_index("target", run_fn=run_fn))
        self.assertEqual(len(calls), 1)
        argv, kwargs = calls[0]
        self.assertEqual(argv, [SERVER, "cli", "index_repository", "--repo-path", ".",
                                "--mode", "full"])
        self.assertEqual(kwargs["cwd"], "target")
        self.assertEqual(kwargs["timeout"], detection.CBM_INDEX_TIMEOUT_SECONDS)

    def test_nonzero_exit_is_false(self):
        run_fn, _ = self._recording(
            subprocess.CompletedProcess([], 1, stdout="", stderr='{"error": "boom"}'))
        self.assertFalse(detection.run_cbm_index("target", run_fn=run_fn))

    def test_unparsable_output_is_false(self):
        run_fn, _ = self._recording(subprocess.CompletedProcess([], 0, stdout="not json"))
        self.assertFalse(detection.run_cbm_index("target", run_fn=run_fn))

    def test_a_status_other_than_indexed_is_false(self):
        run_fn, _ = self._recording(
            subprocess.CompletedProcess([], 0, stdout='{"status": "stale"}'))
        self.assertFalse(detection.run_cbm_index("target", run_fn=run_fn))

    def test_timeout_and_oserror_are_false(self):
        for outcome in (subprocess.TimeoutExpired([SERVER], 1), OSError("no binary")):
            with self.subTest(outcome=type(outcome).__name__):
                run_fn, _ = self._recording(outcome)
                self.assertFalse(detection.run_cbm_index("target", run_fn=run_fn))


if __name__ == "__main__":
    unittest.main()
