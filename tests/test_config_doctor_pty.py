"""PTY end-to-end tests for `setup.py --config-doctor`."""

import contextlib
import json
import os
import shutil
import stat
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

    def test_full_catalog_renders_under_pty_without_crashing(self):
        uv = _uv_cmd()
        claude = self._mk_dir()
        opencode = self._mk_dir()
        codex = self._mk_dir()
        cursor = self._mk_dir()
        home = self._mk_dir()
        bin_dir = os.path.join(home, "bin")
        os.makedirs(bin_dir)
        rtk_path = os.path.join(bin_dir, "rtk")
        with open(rtk_path, "w", encoding="utf-8") as handle:
            handle.write(
                "#!/bin/sh\n"
                "if [ \"$1\" = init ] && [ \"$2\" = --show ]; then\n"
                "cat <<'EOF'\n"
                "rtk Configuration:\n"
                "\n"
                "[ok] Hook: rtk hook claude (native binary command)\n"
                "[ok] Cursor hook: registered in hooks.json\n"
                "EOF\n"
                "fi\n"
                "exit 0\n"
            )
        os.chmod(rtk_path, stat.S_IRWXU)
        with open(os.path.join(claude, "settings.json"), "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "cleanupPeriodDays": 15,
                    "promptCacheTtl": "1h",
                    "sandbox": {"enabled": True},
                },
                handle,
            )
        with open(os.path.join(opencode, "opencode.jsonc"), "w", encoding="utf-8") as handle:
            json.dump({"share": "disabled"}, handle)
        with open(os.path.join(codex, "config.toml"), "w", encoding="utf-8") as handle:
            handle.write('sandbox_mode = "workspace-write"\n')
        with open(os.path.join(cursor, "cli-config.json"), "w", encoding="utf-8") as handle:
            json.dump({"approvalMode": "allowlist"}, handle)
        with open(os.path.join(cursor, "sandbox.json"), "w", encoding="utf-8") as handle:
            json.dump({"type": "workspace_readonly"}, handle)
        safe_path = os.pathsep.join(
            [bin_dir, "/usr/bin", "/bin", os.environ.get("PATH", "")]
        )
        env = dict(
            os.environ,
            HOME=home,
            PATH=safe_path,
            CLAUDE_CONFIG_DIR=claude,
            OPENCODE_CONFIG_DIR=opencode,
            XDG_CONFIG_HOME=self._mk_dir(),
            CODEX_HOME=codex,
            CURSOR_CONFIG_DIR=cursor,
            AI_KIT_DIR=_REPO_ROOT,
            AI_KIT_UV_REEXEC="1",
        )
        pid, master_fd = spawn_pty(
            [uv, "run", "--script", SETUP, "--config-doctor"],
            env,
        )
        boot_deadline = time.time() + 30.0
        all_captured: list[bytes] = []
        try:
            startup_output = drive_until(
                master_fd, b"registered", boot_deadline, captured=all_captured
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
        self.assertIn("cleanupPeriodDays", decoded)
        self.assertIn("share", decoded)
        self.assertIn("sandbox_mode", decoded)
        self.assertIn("approvalMode", decoded)
        self.assertIn("registered", decoded)
        self.assertEqual(exit_code, 0)

    def test_apply_confirm_flow_writes_the_target_value(self):
        uv = _uv_cmd()
        claude = self._mk_dir()
        settings = os.path.join(claude, "settings.json")
        with open(settings, "w", encoding="utf-8") as handle:
            json.dump({"cleanupPeriodDays": 5}, handle)
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
        pid, master_fd = spawn_pty(
            [uv, "run", "--script", SETUP, "--config-doctor"],
            env,
        )
        boot_deadline = time.time() + 30.0
        all_captured: list[bytes] = []
        with contextlib.suppress(AssertionError):
            drive_until(master_fd, b"3650", boot_deadline, captured=all_captured)
        with contextlib.suppress(OSError):
            os.write(master_fd, b"a")
        confirm_deadline = time.time() + 10.0
        try:
            confirm_output = drive_until(
                master_fd, b"Confirm apply", confirm_deadline, captured=all_captured
            )
        except AssertionError:
            confirm_output = b"".join(all_captured)
        decoded_confirm = confirm_output.decode("utf-8", errors="replace")
        self.assertIn("Confirm apply", decoded_confirm)
        self.assertIn("3650", decoded_confirm)
        with contextlib.suppress(OSError):
            os.write(master_fd, b"y")
        applied_deadline = time.time() + 10.0
        with contextlib.suppress(AssertionError):
            drive_until(master_fd, b"3650", applied_deadline, captured=all_captured)
        with contextlib.suppress(OSError):
            os.write(master_fd, b"q")
        tail_output = _drain(master_fd, time.time() + 10)
        with contextlib.suppress(OSError):
            os.close(master_fd)
        exit_code = None
        with contextlib.suppress(ChildProcessError):
            _, status = os.waitpid(pid, 0)
            exit_code = os.WEXITSTATUS(status)
        decoded = (b"".join(all_captured) + tail_output).decode(
            "utf-8", errors="replace"
        )
        self.assertIn("3650", decoded)
        self.assertEqual(exit_code, 0)
        with open(settings, encoding="utf-8") as handle:
            on_disk = json.load(handle)
        self.assertEqual(on_disk["cleanupPeriodDays"], 3650)
        self.assertEqual(list(on_disk.keys()), ["cleanupPeriodDays"])

