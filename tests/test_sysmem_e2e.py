"""T5.4 — End-to-end install + render of the sysmem example external segment.

Hermetic: one self-contained tmpdir is the fake HOME and the ai-kit install dir,
so the suite never touches the live workspace. Runs the REAL setup.py installer
non-interactively with `--examples=all` (in a fresh session so it can never grab
a controlling /dev/tty and block on the wizard), asserts the sysmem provider
lands executable under ~/.config/ai-kit/segments/, then renders the REAL
status-line.py and asserts the sysmem segment shows up in the output line.

The render assertion needs a platform whose available memory the provider can
read (Linux /proc/meminfo); it is skipped elsewhere. The install/executable
assertions are platform-independent.
"""
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest

_HERE = os.path.dirname(__file__)
_REPO = os.path.abspath(os.path.join(_HERE, ".."))
_ANSI = re.compile(r"\033\[[0-9;]*m")


class TestSysmemInstallE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="aikit-sysmem-e2e-")
        cls.home = os.path.join(cls.tmp, "home")
        cls.inst = os.path.join(cls.tmp, "share", "ai-kit")
        os.makedirs(cls.home)
        os.makedirs(os.path.join(cls.inst, "examples", "segments"))
        shutil.copy(os.path.join(_REPO, "examples", "segments", "sysmem"),
                    os.path.join(cls.inst, "examples", "segments", "sysmem"))
        shutil.copytree(os.path.join(_REPO, "tools"),
                        os.path.join(cls.inst, "tools"))
        cls.setup_py = os.path.join(cls.inst, "tools", "setup.py")
        cls.status_line = os.path.join(cls.inst, "tools", "status-line.py")
        cls.env = {
            **os.environ,
            "HOME": cls.home,
            "AI_KIT_DIR": cls.inst,
            "CLAUDE_CONFIG_DIR": os.path.join(cls.home, ".claude"),
            "XDG_CACHE_HOME": os.path.join(cls.home, ".cache"),
        }
        # Drop XDG_CONFIG_HOME so config lands at ~/.config/ai-kit — the path the
        # done-definition names and that status-line.py's default segments dir uses.
        cls.env.pop("XDG_CONFIG_HOME", None)
        # start_new_session detaches the controlling terminal, so open_tty() can't
        # succeed and the installer runs headless (no interactive wizard to block).
        cls.proc = subprocess.run(
            [sys.executable, cls.setup_py, "install", "--examples=all"],
            env=cls.env, stdin=subprocess.DEVNULL, capture_output=True, text=True,
            timeout=60, start_new_session=True)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _seg(self):
        return os.path.join(self.home, ".config", "ai-kit", "segments", "sysmem")

    def test_install_succeeded(self):
        self.assertEqual(self.proc.returncode, 0, self.proc.stderr)

    def test_sysmem_installed_and_executable(self):
        self.assertTrue(os.path.isfile(self._seg()),
                        f"sysmem not installed.\nstdout:\n{self.proc.stdout}\n"
                        f"stderr:\n{self.proc.stderr}")
        self.assertTrue(os.stat(self._seg()).st_mode & stat.S_IXUSR,
                        "installed sysmem is not executable")

    @unittest.skipUnless(os.path.exists("/proc/meminfo"),
                         "sysmem reads /proc/meminfo (Linux) to render")
    def test_sysmem_renders_in_status_line(self):
        sample = json.dumps({
            "model": {"display_name": "Opus 4.8", "id": "claude-opus-4-8"},
            "workspace": {"current_dir": self.home},
            "context_window": {"used_percentage": 10, "context_window_size": 200000},
            "transcript_path": "", "session_id": "e2e",
        })
        env = {**self.env, "STATUSLINE_COLS": "200", "STATUSLINE_LINES": "50"}
        p = subprocess.run([sys.executable, self.status_line], input=sample,
                           capture_output=True, text=True, env=env, cwd=self.home)
        self.assertEqual(p.returncode, 0, p.stderr)
        plain = _ANSI.sub("", p.stdout)
        self.assertIn("💻", plain)              # the sysmem segment's glyph
        self.assertIn("free", plain)            # "<N> GiB free" — the long form


if __name__ == "__main__":
    unittest.main()
