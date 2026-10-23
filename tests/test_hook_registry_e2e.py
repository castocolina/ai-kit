"""E2E: real `python3 tools/setup.py install --headless --with-hooks=precompact`
runs under a temp HOME (SPEC R10). Env holds only PATH plus the temp overrides
— nothing reaches the real ~/.claude, ~/.pi, ~/.cursor or opencode dirs. A
space in the temp root exercises the quoting edge (Round 4/5).
"""
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest

SETUP = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "tools", "setup.py"))
REPO = os.path.dirname(os.path.dirname(SETUP))


class HookRegistryE2E(unittest.TestCase):
    def setUp(self):
        # A space in the root path exercises the quoting edge.
        self.root = tempfile.mkdtemp(prefix="xai-hook ")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.home = os.path.join(self.root, "home")
        self.claude = os.path.join(self.root, "claude")
        self.cursor = os.path.join(self.root, "cursor")
        self.pi = os.path.join(self.root, "pi")
        self.opencode = os.path.join(self.root, "opencode")
        self.env = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": self.home,
            "AI_KIT_DIR": REPO,
            "CLAUDE_CONFIG_DIR": self.claude,
            "CURSOR_CONFIG_DIR": self.cursor,
            "PI_CODING_AGENT_DIR": self.pi,
            "OPENCODE_CONFIG_DIR": self.opencode,
            "XDG_CONFIG_HOME": os.path.join(self.root, ".config"),
            "XDG_STATE_HOME": os.path.join(self.root, "state"),
            "XDG_CACHE_HOME": os.path.join(self.root, ".cache"),
            "XDG_RUNTIME_DIR": os.path.join(self.root, ".runtime"),
        }

    def run_setup(self, *args, env=None):
        return subprocess.run(
            [sys.executable, SETUP, *args],
            env=env or self.env, capture_output=True, text=True)

    def read_settings(self):
        with open(os.path.join(self.claude, "settings.json"),
                  encoding="utf-8") as handle:
            return json.load(handle)

    def test_tracer_with_hooks_precompact_wires_two_claude_entries(self):
        os.makedirs(self.claude)
        expected_command = "python3 -S " + shlex.quote(os.path.join(
            REPO, "tools", "hooks", "claude_precompact.py"))
        proc = self.run_setup("install", "--headless", "--with-hooks=precompact")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = self.read_settings()
        self.assertEqual(set(data.get("hooks", {})),
                         {"PreCompact", "SessionStart"})
        pre = data["hooks"]["PreCompact"]
        self.assertEqual(len(pre), 1)
        self.assertEqual(pre[0]["matcher"], "manual|auto")
        self.assertEqual(len(pre[0]["hooks"]), 1)
        self.assertEqual(pre[0]["hooks"][0]["command"], expected_command)
        self.assertEqual(pre[0]["hooks"][0]["timeout"], 15)
        start = data["hooks"]["SessionStart"]
        self.assertEqual(len(start), 1)
        self.assertEqual(start[0]["matcher"], "compact")
        self.assertEqual(len(start[0]["hooks"]), 1)
        self.assertEqual(start[0]["hooks"][0]["command"], expected_command)
        self.assertEqual(start[0]["hooks"][0]["timeout"], 10)
        for absent in (self.cursor, self.pi, self.opencode):
            self.assertFalse(os.path.exists(absent))

    def test_tracer_space_in_install_dir_runs_configured_command(self):
        # AI_KIT_DIR is a symlink named `ai kit` (with a space) -> the repo.
        link = os.path.join(self.root, "ai kit")
        os.symlink(REPO, link)
        os.makedirs(self.claude)
        env = dict(self.env, AI_KIT_DIR=link)
        proc = self.run_setup("install", "--headless",
                              "--with-hooks=precompact", env=env)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = self.read_settings()
        command = data["hooks"]["SessionStart"][0]["hooks"][0]["command"]
        self.assertIn("'", command)  # the script path is shell-quoted
        # Run the stored string exactly as a host's `sh -c` would.
        bin_dir = os.path.join(self.root, "bin")
        os.makedirs(bin_dir)
        os.symlink(sys.executable, os.path.join(bin_dir, "python3"))
        hook_env = dict(env, PATH=bin_dir)
        proc = subprocess.run(
            [shutil.which("sh"), "-c", command],
            input=json.dumps({"hook_event_name": "SessionStart",
                              "source": "compact",
                              "session_id": "s-space"}),
            capture_output=True, text=True, env=hook_env, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout, "{}")
        self.assertEqual(proc.stderr, "")


if __name__ == "__main__":
    unittest.main()
