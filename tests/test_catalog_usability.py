"""Regression tests for per-runtime usability records; all catalog data is synthetic."""

import contextlib
import io
import json
import os
import sys
import tempfile
import threading
import unittest
from unittest import mock

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review"))

from ai_kit_spec import cli, quota, secret_shapes, usability
from ai_kit_spec.model_catalog import CATALOG_SCHEMA_VERSION, join_catalog_meta
from ai_kit_spec.runner_dispatch import RunnerResult


class _CatalogCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="p35-12-")
        self.addCleanup(self.temp.cleanup)
        self.path = os.path.join(self.temp.name, "model-catalog.json")
        self.env = {
            "HOME": os.path.join(self.temp.name, "home"),
            "XDG_CONFIG_HOME": os.path.join(self.temp.name, "config"),
            "XDG_CACHE_HOME": os.path.join(self.temp.name, "cache"),
            "AI_KIT_REFUSE_REAL_HOME": "1",
        }
        os.makedirs(self.env["HOME"])
        self.entries = {
            "router-env/placeholder-model-1": {
                "provider": "router-env",
                "runtimes": {
                    "opencode": {"model_id": "router-env/placeholder-model-1"},
                    "pi": {"model_id": "router-env/placeholder-model-1"},
                },
                "source": {}, "confidence": "low", "last_verified": "2026-11-19",
            },
            "router-env/placeholder-model-2": {
                "provider": "router-env",
                "runtimes": {"opencode": {"model_id": "router-env/placeholder-model-2"}},
                "source": {}, "confidence": "low", "last_verified": "2026-11-19",
            },
        }
        self.write_catalog()

    def write_catalog(self):
        with open(self.path, "w", encoding="utf-8") as handle:
            catalog = join_catalog_meta(self.entries, {"schema_version": CATALOG_SCHEMA_VERSION})
            json.dump(catalog, handle)

    def read_catalog(self):
        with open(self.path, encoding="utf-8") as handle:
            return json.load(handle)

    def read_bytes(self):
        with open(self.path, "rb") as handle:
            return handle.read()

    def run_check(self, result, model="router-env/placeholder-model-1",
                  runtime: str | None = "opencode", catalog=True):
        argv = ["check-reviewer", "--model", model]
        if runtime is not None:
            argv.extend(["--runtime", runtime])
        if catalog:
            argv.extend(["--catalog-path", self.path])
        output = io.StringIO()
        with (mock.patch.object(cli, "probe_reviewer_quota", return_value=dict(result)) as probe,
              contextlib.redirect_stdout(output)):
            code = cli.main(argv, deps=cli.CliDeps(env_fn=lambda: self.env))
        return code, json.loads(output.getvalue()), probe


class TestUsabilityRecord(_CatalogCase):
    def test_verified_written(self):
        code, output, probe = self.run_check({
            "available": True, "checked_at": 1, "reason": None, "detail": "", "answered": True,
        })
        self.assertEqual(code, 0)
        probe.assert_called_once()
        row = self.read_catalog()["router-env/placeholder-model-1"]["runtimes"]["opencode"]
        self.assertEqual(row["usability"]["state"], "verified")
        self.assertEqual(row["usability"]["via"], "check-reviewer")
        self.assertIsNone(row["usability"]["error"])
        self.assertRegex(row["usability"]["at"], r"^\d{4}-\d\d-\d\dT")
        self.assertTrue(output["usability"]["recorded"])
        self.assertEqual(output["usability"]["state"], "verified")

    def test_only_the_probed_pair_changes(self):
        self.run_check({"available": True, "reason": None, "detail": "", "answered": True})
        rows = self.read_catalog()
        self.assertIn("usability", rows["router-env/placeholder-model-1"]["runtimes"]["opencode"])
        self.assertNotIn("usability", rows["router-env/placeholder-model-1"]["runtimes"]["pi"])
        self.assertNotIn("usability", rows["router-env/placeholder-model-2"]
                         ["runtimes"]["opencode"])


class TestUsabilityStates(_CatalogCase):
    def test_rejected_error_sanitized(self):
        planted = "xai-" + "a" * 24
        detail = f"Error 401: key {planted} refused\x07\nsecond line"
        result = usability.record_for({"available": False, "reason": "error", "detail": detail},
                                      "opencode", "2026-11-20T00:00:00Z")
        assert result is not None
        model = "router-env/placeholder-model-1"
        key, problem = usability.record_usability(self.path, "opencode", model, result)
        assert key is not None
        error = self.read_catalog()[key]["runtimes"]["opencode"]["usability"]["error"]
        self.assertIsNone(problem)
        self.assertNotIn(planted, error)
        self.assertNotIn("\n", error)
        self.assertNotIn("\x07", error)
        self.assertIn("[redacted]", error)
        self.assertLessEqual(len(error), usability.ERROR_MAX)
        self.assertEqual(secret_shapes.detect(error), [])

    def test_error_capped(self):
        record = usability.record_for({"available": False, "detail": "x" * 500}, "opencode", "now")
        assert record is not None
        usability.record_usability(self.path, "opencode", "router-env/placeholder-model-1", record)
        self.assertEqual(len(self.read_catalog()["router-env/placeholder-model-1"]
                             ["runtimes"]["opencode"]["usability"]["error"]), 200)

    def test_answer_with_reason_is_unverified(self):
        record = usability.record_for(
            {"available": True, "reason": "quota unknown", "answered": True}, "opencode", "now"
        )
        assert record is not None
        self.assertEqual(record["state"], "unverified")
        self.assertEqual(record["via"], "check-reviewer (quota unknown)")

    def test_native_records_nothing(self):
        before = self.read_bytes()
        code, output, _probe = self.run_check({"available": True, "reason": None, "detail": ""},
                                              runtime=None)
        self.assertEqual(code, 0)
        self.assertNotIn("usability", output)
        self.assertEqual(self.read_bytes(), before)

    def test_missing_pair_reported(self):
        before = self.read_bytes()
        _code, output, _probe = self.run_check({"available": True, "reason": None,
                                                "detail": "", "answered": True},
                                               model="router-env/placeholder-model-9")
        self.assertFalse(output["usability"]["recorded"])
        self.assertTrue(output["usability"]["problem"].startswith("not in catalog:"))
        self.assertEqual(self.read_bytes(), before)

    def test_state_is_per_runtime(self):
        model = "router-env/placeholder-model-1"
        rejected = usability.record_for({"available": False, "detail": "no"}, "opencode", "one")
        assert rejected is not None
        usability.record_usability(self.path, "opencode", model, rejected)
        verified = usability.record_for({"available": True, "reason": None, "answered": True},
                                        "pi", "two")
        assert verified is not None
        usability.record_usability(self.path, "pi", model, verified)
        rows = self.read_catalog()["router-env/placeholder-model-1"]["runtimes"]
        self.assertEqual(rows["opencode"]["usability"]["state"], "rejected")
        self.assertEqual(rows["pi"]["usability"]["state"], "verified")

    def test_order_independent(self):
        snapshot = join_catalog_meta(self.entries, {"schema_version": CATALOG_SCHEMA_VERSION})
        outputs = []
        for sequence in ((1, 2), (2, 1)):
            self.entries = json.loads(json.dumps(snapshot))
            self.write_catalog()
            for index in sequence:
                model = f"router-env/placeholder-model-{index}"
                rec = {"state": "verified", "at": "same", "via": "check-reviewer", "error": None}
                usability.record_usability(self.path, "opencode", model, rec)
            outputs.append(self.read_catalog())
        self.assertEqual(outputs[0], outputs[1])

    def test_real_adapter_answer_evidence(self):
        answer = quota._probe_entry(RunnerResult(0, "Hello world!", None, None, False, [], ""), "")
        verified = usability.record_for(answer, "opencode", "now")
        assert verified is not None
        self.assertEqual(verified["state"], "verified")
        blank = quota._probe_entry(RunnerResult(0, "", None, None, False, [], ""), "")
        record = usability.record_for(blank, "opencode", "now")
        assert record is not None
        self.assertEqual(record["state"], "unverified")
        self.assertEqual(record["via"], "check-reviewer (no answer text)")

    def test_stdout_redacted(self):
        planted = "xai-" + "b" * 24
        for catalog in (False, True):
            _code, _output, _probe = self.run_check({
                "available": False, "reason": "error", "detail": f"key {planted} refused",
            }, catalog=catalog)
            # The helper returns parsed JSON; capture it via a fresh call below to assert raw bytes.
            with mock.patch.object(cli, "probe_reviewer_quota", return_value={
                "available": False, "reason": "error", "detail": f"key {planted} refused",
            }):
                captured = io.StringIO()
                args = ["check-reviewer", "--runtime", "opencode", "--model",
                        "router-env/placeholder-model-1"]
                if catalog:
                    args.extend(["--catalog-path", self.path])
                with contextlib.redirect_stdout(captured):
                    cli.main(args, deps=cli.CliDeps(env_fn=lambda: self.env))
            self.assertNotIn(planted, captured.getvalue())
            self.assertIn("[redacted]", captured.getvalue())

    def test_concurrent_records_both_kept(self):
        failures = []

        def write(model):
            try:
                usability.record_usability(self.path, "opencode", model, {
                    "state": "verified", "at": "same", "via": "check-reviewer", "error": None,
                })
            except Exception as exc:  # surfaced in the main test thread
                failures.append(exc)

        threads = [threading.Thread(target=write, args=(f"router-env/placeholder-model-{n}",))
                   for n in (1, 2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(failures, [])
        rows = self.read_catalog()
        for n in (1, 2):
            self.assertEqual(rows[f"router-env/placeholder-model-{n}"]
                             ["runtimes"]["opencode"]["usability"]["state"], "verified")

    def test_unreadable_catalog_untouched(self):
        with open(self.path, "wb") as handle:
            handle.write(b"{not json")
        before = self.read_bytes()
        _code, output, _probe = self.run_check({"available": True, "reason": None,
                                                "detail": "", "answered": True})
        self.assertFalse(output["usability"]["recorded"])
        self.assertTrue(output["usability"]["problem"].startswith("catalog unreadable"))
        self.assertEqual(self.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
