"""Black-box tests for the fail-open decision-probe SessionStart hook."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOKS = ROOT / "tools" / "hooks"
SCRIPT = HOOKS / "claude_decision_probe.py"
STUB = ROOT / "tests" / "fixtures" / "precompact" / "stub_client.py"


class DecisionProbeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.bin = self.base / "bin"
        self.bin.mkdir()
        for executable in ("python3",):
            os.symlink(sys.executable, self.bin / executable)
        self.env = {"PATH": str(self.bin), "HOME": str(self.base / "home"),
                    "XDG_CONFIG_HOME": str(self.base / "config"),
                    "XDG_CACHE_HOME": str(self.base / "cache"),
                    "XDG_RUNTIME_DIR": str(self.base / "runtime"),
                    "AI_KIT_PRECOMPACT_CLIENT": str(STUB)}
        for key in ("HOME", "XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_RUNTIME_DIR"):
            Path(self.env[key]).mkdir(parents=True)
        os.chmod(self.env["XDG_RUNTIME_DIR"], 0o700)

    def run_probe(self, mode="up", script=SCRIPT, payload=None):
        env = dict(self.env)
        env["STUB_PROBE"] = mode
        return subprocess.run([sys.executable, "-S", str(script)], input=json.dumps(
            payload or {"hook_event_name": "SessionStart", "source": "startup"}),
            text=True, capture_output=True, env=env, timeout=8, check=False)

    def test_probe_tracer_names_laya(self):
        proc = self.run_probe()
        self.assertEqual((proc.returncode, proc.stderr), (0, ""))
        output = json.loads(proc.stdout)
        self.assertEqual(set(output), {"systemMessage", "hookSpecificOutput"})
        self.assertEqual(set(output["hookSpecificOutput"]), {"hookEventName", "additionalContext"})
        self.assertEqual(output["hookSpecificOutput"]["hookEventName"], "SessionStart")
        user = output["systemMessage"]
        context = output["hookSpecificOutput"]["additionalContext"]
        self.assertTrue(user.isascii() and "\n" not in user and len(user) <= 200)
        for text in (user, context):
            for name in ("jev-fast-decision", "laya", "typesafe"):
                self.assertIn(name, text)
            self.assertNotIn("127.0.0.1", text)
            self.assertNotIn("api.example", text)

    def test_probe_nothing_usable_gives_empty(self):
        for mode in ("down", "pinned_down", "consent_needed"):
            with self.subTest(mode=mode):
                proc = self.run_probe(mode)
                self.assertEqual((proc.returncode, proc.stdout, proc.stderr), (0, "{}", ""))

    def test_probe_timeout_gives_empty_within_bound(self):
        started = time.monotonic()
        proc = self.run_probe("hang")
        self.assertEqual((proc.returncode, proc.stdout, proc.stderr), (0, "{}", ""))
        self.assertLess(time.monotonic() - started, 3.5)

    def test_probe_missing_client_gives_empty(self):
        install_hooks = self.base / "install" / "tools" / "hooks"
        install_hooks.mkdir(parents=True)
        for source in HOOKS.glob("*.py"):
            shutil.copy(source, install_hooks / source.name)
        env = dict(self.env)
        env.pop("AI_KIT_PRECOMPACT_CLIENT")
        proc = subprocess.run([sys.executable, "-S", str(install_hooks / SCRIPT.name)],
                              input='{"source":"startup"}', text=True, capture_output=True,
                              env=env, timeout=5, check=False)
        self.assertEqual((proc.returncode, proc.stdout, proc.stderr), (0, "{}", ""))


if __name__ == "__main__":
    unittest.main()
