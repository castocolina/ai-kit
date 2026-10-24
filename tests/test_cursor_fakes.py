"""Behavioral tests for the loopback Cursor fakes."""

import json
import pathlib
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request

from tests.cursor_fakes import (
    FakeDashboard,
    load_dashboard_fixture,
    redact_payload,
    run_like_cursor,
)


class TestFakeDashboard(unittest.TestCase):
    def test_scripted_method_returns_and_records_connect_request(self):
        with FakeDashboard() as server:
            server.script("GetCurrentPeriodUsage", body=load_dashboard_fixture("usage_pro"))
            request = urllib.request.Request(
                f"{server.url}/aiserver.v1.DashboardService/GetCurrentPeriodUsage",
                data=b"{}",
                headers={"Authorization": "Bearer synthetic",
                         "Content-Type": "application/json",
                         "Connect-Protocol-Version": "1"}, method="POST")
            with urllib.request.urlopen(request) as response:
                data = json.load(response)
            self.assertIn("planUsage", data)
            self.assertEqual(server.requests[0]["method"], "POST")
            self.assertEqual(server.requests[0]["authorization"], "Bearer synthetic")

    def test_status_delay_and_redirect_are_scriptable(self):
        with FakeDashboard() as second, FakeDashboard() as first:
            second.script("redirect", body={"hardLimit": 20})
            first.script("GetHardLimit", status=302, location=f"{second.url}/redirect")
            request = urllib.request.Request(
                f"{first.url}/aiserver.v1.DashboardService/GetHardLimit", data=b"{}", method="POST")
            with urllib.request.urlopen(request) as response:
                self.assertEqual(json.load(response), {"hardLimit": 20})
            self.assertEqual(len(second.requests), 1)
            first.script("GetPlanInfo", status=401, body={"error": "unauthorized"})
            request = urllib.request.Request(
                f"{first.url}/aiserver.v1.DashboardService/GetPlanInfo", data=b"{}", method="POST")
            with self.assertRaises(urllib.error.HTTPError) as caught:
                urllib.request.urlopen(request)
            self.assertEqual(caught.exception.code, 401)
            first.script("Slow", delay_s=0.02, body={"ok": True})
            before = time.monotonic()
            request = urllib.request.Request(f"{first.url}/x/Slow", data=b"{}", method="POST")
            with urllib.request.urlopen(request) as response:
                self.assertTrue(json.load(response)["ok"])
            self.assertGreaterEqual(time.monotonic() - before, 0.015)


class TestPayloadRedaction(unittest.TestCase):
    def test_only_named_label_strings_survive(self):
        source = {"version": "1", "model": {"id": "m", "display_name": "Model"},
                  "output_style": {"name": "default"}, "other": "private",
                  "items": ["private"]}
        self.assertEqual(redact_payload(source), {
            "version": "1", "model": {"id": "m", "display_name": "Model"},
            "output_style": {"name": "default"}, "other": "<redacted>",
            "items": ["<redacted>"]})


class TestRunnerSimulator(unittest.TestCase):
    def _script(self, directory, source):
        path = pathlib.Path(directory) / "child.py"
        path.write_text(source, encoding="utf-8")
        return [sys.executable, str(path)]

    def _run(self, source, **kwargs):
        with tempfile.TemporaryDirectory() as directory:
            result = run_like_cursor(self._script(directory, source), {"hello": "world"},
                                     cwd=directory, env=None, **kwargs)
            return result

    def test_normalizes_output_and_stdin_is_json(self):
        source = "import json,sys; json.load(sys.stdin); "
        source += "sys.stdout.buffer.write(b'a\\rb\\n\\n')"
        result = self._run(source)
        self.assertEqual(result.text, "ab")
        self.assertFalse(result.blocked)

    def test_kills_only_direct_child_and_reports_it(self):
        result = self._run("import time; time.sleep(10)", kill_after_ms=30, timeout_s=1)
        self.assertTrue(result.killed)
        self.assertNotEqual(result.returncode, 0)

    def test_grandchild_inheriting_pipe_blocks_but_devnull_new_session_does_not(self):
        child = "import time; time.sleep(1)"
        hanging = ("import subprocess,sys; "
                   "subprocess.Popen([sys.executable, '-c', " + repr(child) + "]); "
                   "print('ready', flush=True)")
        result = self._run(hanging, timeout_s=0.05)
        self.assertTrue(result.blocked)
        detached = ("import subprocess,sys; "
                    "subprocess.Popen([sys.executable, '-c', " + repr(child) + "], "
                    "start_new_session=True, stdin=subprocess.DEVNULL, "
                    "stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); "
                    "print('ready')")
        before = time.monotonic()
        result = self._run(detached, timeout_s=0.5)
        self.assertFalse(result.blocked)
        self.assertLess(time.monotonic() - before, 0.5)


if __name__ == "__main__":
    unittest.main()
