"""The runner's own --sweep closes a pane leftover written by herdr_pane's record writer."""

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-spec-review"))

from ai_kit_spec import herdr_pane

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from tests.cross_ai_selftest import _real_node_executable
from tests.herdr_fakes import herdr_calls, write_herdr_fake

NODE = _real_node_executable()
TEMPLATE = REPO / "skills" / "ai-kit-spec-review" / "references" / "cross-ai.mjs"
TOKEN = "0123456789ab"


class TestRunnerSweep(unittest.TestCase):
    """The real template's sweep against a real run.json written by herdr_pane."""

    def setUp(self):
        if NODE is None:
            self.skipTest("no real node executable on PATH")

    def test_sweep_closes_the_pane_leftover(self):
        assert NODE is not None
        label = herdr_pane.pane_label("review", "placeholder-cli-1", TOKEN)
        with tempfile.TemporaryDirectory(prefix="herdr-sweep-") as tmp:
            env = {
                "HERDR_ENV": "1",
                "XDG_STATE_HOME": os.path.join(tmp, "state"),
                "HOME": os.path.join(tmp, "home"),
                "AI_KIT_REFUSE_REAL_HOME": "1",
                "PATH": os.pathsep.join([os.path.join(tmp, "bin"), os.path.dirname(NODE),
                                         "/usr/bin:/bin"]),
            }
            os.makedirs(env["HOME"], exist_ok=True)
            run_dir = herdr_pane.run_dir_for(env, TOKEN)
            os.makedirs(run_dir, mode=herdr_pane.DIR_MODE)
            dead = subprocess.Popen(["/bin/true"])
            dead.wait()
            record = {
                "version": herdr_pane.RUN_RECORD_VERSION,
                "token": TOKEN,
                "created_ms": int(time.time() * 1000) - 60000,
                "checkout_root": str(REPO),
                "host_name": os.uname().nodename,
                "role": "review",
                "runtime": "placeholder-cli-1",
                "label": label,
                "runner_pid": dead.pid,
                "runner_start": "-",
                "tab_id": "t1",
                "pane_id": "p1",
                "launcher_pid": None,
                "launcher_pgid": None,
                "launcher_start": None,
            }
            herdr_pane._write_record(run_dir, record)
            answers = {
                ("tab", "list"): (0, json.dumps({"result": {"tabs": [
                    {"tab_id": "t1", "label": label},
                    {"tab_id": "t9", "label": "aikit:review:placeholder-cli-2:ffffffffffff"},
                ]}})),
                ("tab", "close", "t1"): (0, "{}"),
            }
            log_path = os.path.join(tmp, "herdr.log")
            write_herdr_fake(os.path.join(tmp, "bin"), answers, log_path)
            proc = subprocess.run([NODE, str(TEMPLATE), "--sweep"], stdin=subprocess.DEVNULL,
                                  capture_output=True, text=True, timeout=60, check=False,
                                  env=env)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("cross-ai: sweep: closed 1 tab(s), removed 1 run director(ies), "
                          "kept 0 (-)", proc.stderr)
            close_calls = [call for call in herdr_calls(log_path)
                           if call[:2] == ["tab", "close"]]
            self.assertEqual(close_calls, [["tab", "close", "t1"]])
            self.assertFalse(any("t9" in call for call in close_calls))
            self.assertFalse(os.path.exists(run_dir))


if __name__ == "__main__":
    unittest.main()
