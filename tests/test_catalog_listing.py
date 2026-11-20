"""Tests for opencode API records and startup retries."""

import io
import json
import os
import sys
import tempfile
import unittest
import urllib.error
from email.message import Message
from unittest import mock

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review"))
from ai_kit_spec import detection

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "opencode_api_model_v2.json")


def _payload():
    with open(FIXTURE, encoding="utf-8") as handle:
        return json.load(handle)


class _FakeProcess:
    def __init__(self):
        self.stdout = io.StringIO(
            "server listening on http://127.0.0.1:41234\nserver password secret\n")
        self.pid = None
        self.calls = []

    def terminate(self):
        self.calls.append("terminate")

    def kill(self):
        self.calls.append("kill")

    def wait(self, timeout=None):
        self.calls.append(("wait", timeout))


class _Response(io.BytesIO):
    pass


def _popen(*_args, **_kwargs):
    return _FakeProcess()


class TestOpencodeApiRecords(unittest.TestCase):
    def test_retry_after_503(self):
        fixture = json.dumps(_payload()).encode()
        calls = []

        def urlopen(_request, timeout):
            calls.append(timeout)
            if len(calls) == 1:
                raise urllib.error.HTTPError("http://127.0.0.1", 503, "starting", Message(), None)
            return _Response(fixture)

        with mock.patch.object(detection, "_opencode_sleep") as sleeper:
            result = detection.probe_opencode_api(
                "/fake/opencode", popen_fn=_popen, urlopen_fn=urlopen,
                env={"HOME": tempfile.gettempdir()})
        self.assertEqual(result["image"]["router-env/placeholder-model-1"], True)
        self.assertEqual(result["records"]["router-env/placeholder-model-1"]["efforts"],
                         ["low", "high"])
        sleeper.assert_called_once_with(2.0)
        self.assertEqual(len(calls), 2)

    def test_snapshot_stores_records(self):
        records = {"router-env/placeholder-model-1": {"efforts": ["low"]}}
        with mock.patch.object(detection, "probe_opencode_api",
                               return_value={"image": {"router-env/placeholder-model-1": True},
                                             "records": records}):
            snapshot = detection.build_runtimes_snapshot(
                which_fn=lambda name, **_kwargs: "/fake/opencode" if name == "opencode" else None,
                run_fn=lambda argv, **_kw: type("Result", (), {
                    "returncode": 0, "stdout": "opencode v2.3.2"})())
        entry = snapshot["clis"]["opencode"]
        self.assertEqual(entry["image_input"], {"router-env/placeholder-model-1": True})
        self.assertEqual(entry["image_input_source"], "opencode-api")
        self.assertEqual(entry["model_records"], records)

    def test_failed_probe_recorded(self):
        with mock.patch.object(detection, "probe_opencode_api", return_value={}):
            snapshot = detection.build_runtimes_snapshot(
                which_fn=lambda name, **_kwargs: "/fake/opencode" if name == "opencode" else None,
                run_fn=lambda argv, **_kw: type("Result", (), {
                    "returncode": 0, "stdout": "opencode v2.3.2"})())
        entry = snapshot["clis"]["opencode"]
        self.assertEqual(entry["image_input_probe"], "failed")
        self.assertNotIn("model_records", entry)


class TestOpencodeRecordEdges(unittest.TestCase):
    def test_disabled_item(self):
        records = detection.parse_opencode_api_records(_payload())
        self.assertFalse(records["router-env/placeholder-model-2"]["enabled"])

    def test_variant_names_as_listed_and_bad_limits(self):
        records = detection.parse_opencode_api_records(_payload())
        self.assertEqual(records["router-env/placeholder-model-3"]["efforts"], ["none", "thinking"])
        self.assertEqual(records["router-env/placeholder-model-3"]["limit"],
                         {"context": None, "input": None, "output": None})
        self.assertEqual(records["router-env/placeholder-model-3"]["status"], "deprecated")

    def test_malformed_payloads(self):
        self.assertEqual(detection.parse_opencode_api_records(None), {})
        self.assertEqual(detection.parse_opencode_api_records({"data": "bad"}), {})
        records = detection.parse_opencode_api_records(_payload())
        self.assertNotIn("router-env/placeholder-model-4", records)

    def test_other_http_error_not_retried(self):
        calls = []

        def urlopen(*_args, **_kwargs):
            calls.append(True)
            raise urllib.error.HTTPError("http://127.0.0.1", 500, "error", Message(), None)

        with mock.patch.object(detection, "_opencode_sleep") as sleeper:
            result = detection.probe_opencode_api("/fake/opencode", _popen, urlopen,
                                                   {"HOME": tempfile.gettempdir()})
        self.assertEqual(result, {})
        self.assertEqual(len(calls), 1)
        sleeper.assert_not_called()

    def test_503_exhausted(self):
        calls = []

        def urlopen(*_args, **_kwargs):
            calls.append(True)
            raise urllib.error.HTTPError("http://127.0.0.1", 503, "starting", Message(), None)

        clock = [0.0]

        def fake_sleep(seconds):
            clock[0] += seconds

        with mock.patch.object(detection, "_opencode_clock", side_effect=lambda: clock[0]), \
                mock.patch.object(detection, "_opencode_sleep", side_effect=fake_sleep) as sleeper:
            result = detection.probe_opencode_api("/fake/opencode", _popen, urlopen,
                                                   {"HOME": tempfile.gettempdir()})
        self.assertEqual(result, {})
        self.assertEqual(len(calls), 6)
        self.assertEqual(sleeper.call_count, 5)

    def test_deadline_bounds_retries(self):
        calls = []
        clock = [0.0]

        def urlopen(_request, timeout):
            calls.append(timeout)
            clock[0] += 6
            raise urllib.error.HTTPError("http://127.0.0.1", 503, "starting", Message(), None)

        with mock.patch.object(detection, "_opencode_clock", side_effect=lambda: clock[0]), \
                mock.patch.object(detection, "_opencode_sleep"):
            result = detection.probe_opencode_api("/fake/opencode", _popen, urlopen,
                                                   {"HOME": tempfile.gettempdir()})
        self.assertEqual(result, {})
        self.assertLessEqual(len(calls), 3)
        self.assertTrue(all(timeout <= 15 for timeout in calls))

    def test_deadline_counts_banner_time(self):
        clock = [0.0]
        process = _FakeProcess()
        original_readline = process.stdout.readline

        def readline():
            line = original_readline()
            clock[0] = 10.0
            return line

        calls = []

        def urlopen(_request, timeout):
            calls.append(timeout)
            clock[0] += 6
            raise urllib.error.HTTPError("http://127.0.0.1", 503, "starting", Message(), None)

        with mock.patch.object(detection, "_read_opencode_banner",
                               side_effect=lambda _stream: (clock.__setitem__(0, 10.0) or
                                                            ("41234", "secret"))), \
                mock.patch.object(detection, "_opencode_clock", side_effect=lambda: clock[0]), \
                mock.patch.object(detection, "_opencode_sleep") as sleeper:
            detection.probe_opencode_api("/fake/opencode", lambda *_a, **_k: process, urlopen,
                                         {"HOME": tempfile.gettempdir()})
        self.assertEqual(len(calls), 1)
        self.assertLessEqual(calls[0], 5)
        sleeper.assert_not_called()

    def test_none_version_takes_verbose_path(self):
        seen = []

        def run(argv, **_kwargs):
            seen.append(argv[1:])
            return type("Result", (), {"returncode": 0, "stdout": "unparsed"})()

        with mock.patch.object(detection, "probe_opencode_api") as probe:
            detection.build_runtimes_snapshot(
                which_fn=lambda name, **_kwargs: "/fake/opencode" if name == "opencode" else None,
                run_fn=run)
        probe.assert_not_called()
        self.assertIn(["models", "--verbose"], seen)

    def test_bad_items_inside_data(self):
        payload = {"data": ["bad", 5,
                            {"providerID": "router-env", "id": "placeholder-model-4",
                             "variants": [], "limit": "x"},
                            {"providerID": "router-env", "id": "placeholder-model-5",
                             "variants": [], "limit": {"context": 10}}]}
        records = detection.parse_opencode_api_records(payload)
        self.assertEqual(set(records), {"router-env/placeholder-model-4",
                                        "router-env/placeholder-model-5"})
        self.assertEqual(records["router-env/placeholder-model-4"]["limit"],
                         {"context": None, "input": None, "output": None})
        self.assertEqual(records["router-env/placeholder-model-5"]["limit"]["context"], 10)


if __name__ == "__main__":
    unittest.main()
