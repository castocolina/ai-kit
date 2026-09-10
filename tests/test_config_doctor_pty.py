"""PTY end-to-end tests for `setup.py --config-doctor`."""

import contextlib
import json
import os
import shutil
import time
import unittest

from tests.test_wizard_pty import (
    SETUP,
    _drain,
    _tmp_config_dir,
    _uv_cmd,
    drive_until,
    spawn_pty,
    spawn_pty_piped_stdin,
)

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_MARKER = b"3650"


class TestConfigDoctorPty(unittest.TestCase):
    def setUp(self):
        self._tmpdirs = []

    def tearDown(self):
        for d in self._tmpdirs:
            shutil.rmtree(d, ignore_errors=True)

    def _mk_dir(self):
        d = _tmp_config_dir()
        self._tmpdirs.append(d)
        return d

    def _scratch_env(self):
        claude = self._mk_dir()
        with open(os.path.join(claude, "settings.json"), "w", encoding="utf-8") as handle:
            json.dump({"cleanupPeriodDays": 15}, handle)
        env = dict(
            os.environ,
            HOME=self._mk_dir(),
            CLAUDE_CONFIG_DIR=claude,
            OPENCODE_CONFIG_DIR=self._mk_dir(),
            XDG_CONFIG_HOME=self._mk_dir(),
            CODEX_HOME=self._mk_dir(),
            CURSOR_CONFIG_DIR=self._mk_dir(),
            AI_KIT_DIR=_REPO_ROOT,
            AI_KIT_UV_REEXEC="1",
        )
        return env

    def test_config_doctor_renders_one_real_row_end_to_end(self):
        uv = _uv_cmd()
        env = self._scratch_env()
        pid, master_fd = spawn_pty(
            [uv, "run", "--script", SETUP, "--config-doctor"],
            env,
        )
        boot_deadline = time.time() + 30.0
        all_captured: list[bytes] = []
        try:
            startup_output = drive_until(
                master_fd, _MARKER, boot_deadline, captured=all_captured
            )
        except AssertionError:
            startup_output = b"".join(all_captured)

        with contextlib.suppress(OSError):
            os.write(master_fd, b"q")
        tail_output = _drain(master_fd, time.time() + 10)
        with contextlib.suppress(OSError):
            os.close(master_fd)
        exit_code = None
        with contextlib.suppress(ChildProcessError):
            _, status = os.waitpid(pid, 0)
            exit_code = os.WEXITSTATUS(status)

        decoded = (startup_output + tail_output).decode("utf-8", errors="replace")
        self.assertIn("3650", decoded)
        self.assertIn("15", decoded)
        self.assertIn("code.claude.com", decoded)
        self.assertEqual(exit_code, 0)

    def test_config_doctor_renders_under_piped_stdin(self):
        uv = _uv_cmd()
        env = self._scratch_env()
        pid, master_fd = spawn_pty_piped_stdin(
            [uv, "run", "--script", SETUP, "--config-doctor"],
            env,
        )
        boot_deadline = time.time() + 30.0
        all_captured: list[bytes] = []
        try:
            startup_output = drive_until(
                master_fd, _MARKER, boot_deadline, captured=all_captured
            )
        except AssertionError:
            startup_output = b"".join(all_captured)

        with contextlib.suppress(OSError):
            os.write(master_fd, b"q")
        tail_output = _drain(master_fd, time.time() + 10)
        with contextlib.suppress(OSError):
            os.close(master_fd)
        exit_code = None
        with contextlib.suppress(ChildProcessError):
            _, status = os.waitpid(pid, 0)
            exit_code = os.WEXITSTATUS(status)

        decoded = (startup_output + tail_output).decode("utf-8", errors="replace")
        self.assertIn("3650", decoded)
        self.assertEqual(exit_code, 0)
