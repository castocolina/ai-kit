"""Tests for opencode API records and startup retries."""

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
import urllib.error
from contextlib import redirect_stdout
from email.message import Message
from unittest import mock

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review"))
from ai_kit_spec import detection
from ai_kit_spec.cache import cache_read_json, cache_write_json
from ai_kit_spec.cli import main

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



class TestListingProvenance(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="p35-listing-")
        import shutil
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.fixture_dir = os.path.join(os.path.dirname(__file__), "fixtures")

    def _which(self, runtimes):
        return lambda name, **_kwargs: f"/fake/bin/{name}" if name in runtimes else None

    def _run_for(self, listing_argv, listing_result):
        def run(argv, **kwargs):
            if argv[-1:] == ["--version"]:
                return subprocess.CompletedProcess(argv, 0, stdout="2026.1.1\n", stderr="")
            if tuple(argv[1:]) == tuple(listing_argv):
                return listing_result(argv)
            return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")
        return run

    def test_cursor_listing_ok(self):
        fixture = os.path.join(self.fixture_dir, "cursor_models.txt")
        with open(fixture, encoding="utf-8") as handle:
            listing = handle.read()
        snapshot = detection.build_runtimes_snapshot(
            which_fn=self._which({"cursor-agent"}),
            run_fn=self._run_for(("models",), lambda argv: subprocess.CompletedProcess(
                argv, 0, stdout=listing, stderr="")))
        entry = snapshot["clis"]["cursor"]
        self.assertEqual(entry["listing"], "ok")
        self.assertTrue(entry["models"])
        self.assertEqual(entry["listed_from"]["command"], "cursor-agent models")
        self.assertEqual(entry["listed_from"]["version"], "2026.1.1")
        self.assertRegex(entry["listed_from"]["at"], r"^\d{4}-\d\d-\d\dT.*Z$")

    def test_failed_listing_error(self):
        snapshot = detection.build_runtimes_snapshot(
            which_fn=self._which({"cursor-agent"}),
            run_fn=self._run_for(("models",), lambda argv: subprocess.CompletedProcess(
                argv, 1, stdout="", stderr="boom\nmore")))
        entry = snapshot["clis"]["cursor"]
        self.assertEqual(entry["listing"], "failed")
        self.assertEqual(entry["listing_error"], "exit 1: boom")
        self.assertIn("listed_from", entry)
        self.assertNotIn("models", entry)

    def test_empty_listing_ok(self):
        snapshot = detection.build_runtimes_snapshot(
            which_fn=self._which({"opencode"}),
            run_fn=self._run_for(("models",), lambda argv: subprocess.CompletedProcess(
                argv, 0, stdout="", stderr="")))
        self.assertEqual(snapshot["clis"]["opencode"]["listing"], "ok")
        self.assertEqual(snapshot["clis"]["opencode"]["models"], [])

    def test_copilot_has_no_listing(self):
        snapshot = detection.build_runtimes_snapshot(which_fn=self._which({"copilot"}),
                                                       run_fn=lambda *a, **k: None)
        entry = snapshot["clis"]["copilot"]
        self.assertEqual(entry["listing"], "none")
        self.assertNotIn("listed_from", entry)
        self.assertNotIn("models", entry)

    def test_codex_context_maps(self):
        fixture = os.path.join(self.fixture_dir, "codex_debug_models.json")
        with open(fixture, encoding="utf-8") as handle:
            payload = json.load(handle)
        parsed = detection.parse_codex_debug_models(json.dumps(payload))
        self.assertIsNotNone(parsed)
        expected = {item["slug"]: item["context_window"] for item in payload["models"]
                    if item.get("visibility") == "list" and type(item.get("context_window")) is int}
        snapshot = detection.build_runtimes_snapshot(
            which_fn=self._which({"codex"}),
            run_fn=self._run_for(("debug", "models"), lambda argv: subprocess.CompletedProcess(
                argv, 0, stdout=json.dumps(payload), stderr="")))
        entry = snapshot["clis"]["codex"]
        self.assertEqual(entry["context_window"], expected)
        self.assertNotIn("max_context_window", entry)

    def test_schema_version(self):
        self.assertEqual(detection.build_runtimes_snapshot(which_fn=self._which(set()))[
            "schema_version"], 8)

    def test_unlisted_runtime_found(self):
        self.assertEqual(detection.detect_unlisted_runtimes(["fake-cli"],
                         lambda _name: "/fake/bin/fake-cli"), {
            "fake-cli": {"installed": True, "path": "/fake/bin/fake-cli",
                         "listing": "none", "note": "installed, no listing"}})

    def test_unlisted_runtime_filters(self):
        result = detection.detect_unlisted_runtimes(
            ["cursor", "fake-cli", "Fake", "bad/name", "missing"],
            lambda name: "/fake/bin/" + name if name != "missing" else None)
        self.assertEqual(result, {"fake-cli": {"installed": True, "path": "/fake/bin/fake-cli",
                                               "listing": "none", "note": "installed, no listing"},
                                 "missing": {"installed": False}})

    def test_detect_runtimes_flag(self):
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(main(["detect-runtimes", "--runtime", "fake-cli"],
                which_fn=lambda name, **_kw: "/fake/bin/" + name if name == "fake-cli" else None,
                run_fn=lambda *a, **k: None), 0)
        self.assertEqual(json.loads(output.getvalue())["clis"]["fake-cli"]["listing"], "none")

    def test_named_runtime_skips_fresh_cache(self):
        path = os.path.join(self.root, "runtimes.json")
        cache_write_json(path, {"schema_version": 8, "clis": {}})
        output = io.StringIO()
        with redirect_stdout(output):
            main(["detect-runtimes", "--if-stale", path, "--runtime", "fake-cli"],
                 which_fn=lambda name, **_kw: "/fake/bin/fake-cli" if name == "fake-cli" else None,
                 run_fn=lambda *a, **k: None)
        cached = cache_read_json(path)
        self.assertIsNotNone(cached)
        assert cached is not None
        self.assertIn("fake-cli", cached["clis"])

    def test_pi_rpc_and_sanitized_version(self):
        rpc = '{"command":"get_available_models","success":true,"data":{"models":[]}}'
        def run(argv, **_kwargs):
            if argv[-1:] == ["--version"]:
                version = "ver\x1b sk_live_12345678901234567890\n"
                return subprocess.CompletedProcess(argv, 0, stdout=version, stderr="")
            return subprocess.CompletedProcess(argv, 0, stdout=rpc, stderr="")
        entry = detection.build_runtimes_snapshot(self._which({"pi"}), run)["clis"]["pi"]
        self.assertTrue(entry["listed_from"]["command"].endswith("(rpc get_available_models)"))
        self.assertNotIn("\x1b", entry["listed_from"]["version"])
        self.assertIn("[redacted]", entry["listed_from"]["version"])

    def test_claude_is_never_listing_proof(self):
        snapshot = detection.build_runtimes_snapshot(
            which_fn=self._which({"claude"}), run_fn=lambda *a, **k: None,
            catalog_fn=lambda: {"_meta": {"anthropic_model_ids": ["placeholder-model-1"]}})
        entry = snapshot["clis"]["claude"]
        self.assertEqual(entry["listing"], "none")
        self.assertIn("models", entry)
        self.assertNotIn("listed_from", entry)

if __name__ == "__main__":
    unittest.main()
