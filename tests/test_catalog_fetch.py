"""Per-source catalog freshness and raw-cache tests."""

import json
import os
import sys
import tempfile
import types
import unittest
from unittest import mock

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review"))

from ai_kit_spec import catalog_fetch, models_config


class TestSourcePlan(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="p35-fetch-")
        self.addCleanup(__import__("shutil").rmtree, self.root, True)
        self.path = os.path.join(self.root, "meta.json")
        self.settings = models_config.ModelsSettings(
            models_config.KNOWN_SOURCES,
            dict(models_config.DEFAULT_CACHE_DAYS),
            (),
        )

    def test_read_old_and_absent_meta(self):
        self.assertEqual({}, catalog_fetch.read_fetch_meta(self.path, now=1000.0))
        with open(self.path, "w", encoding="utf-8") as handle:
            json.dump({"last_fetched": 100.0}, handle)
        self.assertEqual({}, catalog_fetch.read_fetch_meta(self.path, now=1000.0))

    def test_bad_records_dropped(self):
        data = {
            "sources": {
                "models_dev": {"last_fetched": "x", "ok": True},
                "artificial_analysis": {"last_fetched": -1, "ok": True},
                "arena": {"last_fetched": 2000.0, "ok": True},
                "other": {"last_fetched": 5.0, "ok": "yes"},
            }
        }
        with open(self.path, "w", encoding="utf-8") as handle:
            json.dump(data, handle)
        self.assertEqual({}, catalog_fetch.read_fetch_meta(self.path, now=1000.0))
        data["sources"] = {"models_dev": {"last_fetched": 5.0, "ok": True}}
        with open(self.path, "w", encoding="utf-8") as handle:
            json.dump(data, handle)
        self.assertEqual(data["sources"], catalog_fetch.read_fetch_meta(self.path, now=1000.0))

    def test_plan_ages_and_key(self):
        meta = {
            key: {"last_fetched": 100.0, "ok": True} for key in models_config.SOURCE_KEYS.values()
        }
        flags = catalog_fetch.PlanFlags(True, True)
        planned = catalog_fetch.source_plan(meta, self.settings, flags, "", 100 + 3 * 86400)
        self.assertEqual((False, "cached, fetched 1970-01-01T00:01:40Z"), planned["models.dev"])
        self.assertEqual(
            (False, "no ARTIFICIAL_ANALYSIS_API_KEY in secrets.env"), planned["artificial-analysis"]
        )
        self.assertEqual((False, "cached, fetched 1970-01-01T00:01:40Z"), planned["arena"])
        planned = catalog_fetch.source_plan(meta, self.settings, flags, "", 100 + 8 * 86400)
        self.assertEqual((True, ""), planned["models.dev"])
        self.assertEqual((True, ""), planned["arena"])

    def test_plan_disabled(self):
        settings = self.settings._replace(sources=("models.dev",))
        planned = catalog_fetch.source_plan(
            {}, settings, catalog_fetch.PlanFlags(True, True), "", 10
        )
        self.assertEqual((False, "disabled in [models] sources"), planned["arena"])

    def test_plan_retry_missing_and_schema(self):
        meta = {"models_dev": {"last_fetched": 1.0, "ok": False}}
        flags = catalog_fetch.PlanFlags(True, True)
        planned = catalog_fetch.source_plan(meta, self.settings, flags, "key", 100)
        self.assertEqual((True, ""), planned["models.dev"])
        self.assertEqual((True, ""), planned["arena"])
        stale_schema = catalog_fetch.source_plan(
            {"models_dev": {"last_fetched": 1.0, "ok": True}},
            self.settings,
            catalog_fetch.PlanFlags(True, False),
            "key",
            100,
        )
        self.assertTrue(all(value == (True, "") for value in stale_schema.values()))


class TestFetchSources(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="p35-fetch-")
        self.addCleanup(__import__("shutil").rmtree, self.root, True)
        self.catalog_path = os.path.join(self.root, "catalog.json")
        self.calls = []
        self.md = {"placeholder-model-1": {}}

        def fetch_md():
            self.calls.append("models.dev")
            return self.md, True

        def fetch_aa(key):
            self.calls.append(("artificial-analysis", key))
            return [], True

        def fetch_arena(progress):
            self.calls.append("arena")
            progress("synthetic progress")
            return None, False

        self.deps = types.SimpleNamespace(
            fetch_models_dev_fn=fetch_md,
            fetch_artificial_analysis_fn=fetch_aa,
            fetch_arena_fn=fetch_arena,
        )

    def test_fetch_and_raw_cache_written(self):
        plan = {
            "models.dev": (True, ""),
            "artificial-analysis": (False, "no key"),
            "arena": (True, ""),
        }
        with mock.patch.object(catalog_fetch.time, "time", return_value=1000.0):
            result = catalog_fetch.fetch_sources(self.deps, plan, "", self.catalog_path)
        self.assertTrue(result.sources.models_dev_ok)
        self.assertFalse(result.sources.arena_ok)
        self.assertEqual(
            {"fetched": True, "ok": False, "reason": "fetch failed"}, result.results["arena"]
        )
        with open(
            catalog_fetch.raw_cache_path(self.catalog_path, "models_dev"), encoding="utf-8"
        ) as handle:
            self.assertEqual({"fetched_at": 1000.0, "data": self.md}, json.load(handle))
        self.assertEqual({}, result.source_at)

    def test_fresh_source_read_from_raw_cache(self):
        path = catalog_fetch.raw_cache_path(self.catalog_path, "models_dev")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump({"fetched_at": 1000.0, "data": self.md}, handle)
        plan = {
            "models.dev": (False, "cached, fetched 1970-01-01T00:16:40Z"),
            "artificial-analysis": (False, "no key"),
            "arena": (False, "disabled"),
        }
        with mock.patch.object(catalog_fetch.time, "time", return_value=2000.0):
            result = catalog_fetch.fetch_sources(self.deps, plan, "", self.catalog_path)
        self.assertEqual([], self.calls)
        self.assertEqual(self.md, result.sources.models_dev_data)
        self.assertTrue(result.sources.models_dev_ok)
        self.assertEqual(
            "cached, fetched 1970-01-01T00:16:40Z", result.results["models.dev"]["reason"]
        )
        self.assertEqual({"models_dev": "1970-01-01T00:16:40Z"}, result.source_at)

    def test_missing_raw_cache_stays_offline(self):
        plan = {
            "models.dev": (False, "disabled"),
            "artificial-analysis": (False, "no key"),
            "arena": (False, "cached, fetched 1970-01-01T00:16:40Z"),
        }
        result = catalog_fetch.fetch_sources(self.deps, plan, "", self.catalog_path)
        self.assertEqual([], self.calls)
        self.assertFalse(result.sources.arena_ok)
        self.assertEqual(
            {
                "fetched": False,
                "ok": None,
                "reason": "cached, fetched 1970-01-01T00:16:40Z; raw data not cached",
            },
            result.results["arena"],
        )

    def test_aa_never_raw_cached(self):
        plan = {
            "models.dev": (False, "disabled"),
            "artificial-analysis": (False, "cached, fetched 1970-01-01T00:16:40Z"),
            "arena": (False, "disabled"),
        }
        result = catalog_fetch.fetch_sources(self.deps, plan, "", self.catalog_path)
        self.assertEqual([], self.calls)
        self.assertFalse(result.sources.aa_ok)
        self.assertEqual(
            "cached, fetched 1970-01-01T00:16:40Z", result.results["artificial-analysis"]["reason"]
        )
        self.assertFalse(
            os.path.exists(catalog_fetch.raw_cache_path(self.catalog_path, "artificial_analysis"))
        )

    def test_meta_update(self):
        meta = {
            "models_dev": {"last_fetched": 100.0, "ok": True},
            "arena": {"last_fetched": 200.0, "ok": True},
        }
        results = {
            "models.dev": {"fetched": True, "ok": True},
            "arena": {"fetched": True, "ok": False},
            "artificial-analysis": {"fetched": False, "ok": None},
        }
        updated = catalog_fetch.updated_fetch_meta(meta, results, 300.0)
        self.assertEqual({"last_fetched": 300.0, "ok": True}, updated["sources"]["models_dev"])
        self.assertEqual({"last_fetched": 200.0, "ok": False}, updated["sources"]["arena"])
        self.assertNotIn("artificial_analysis", updated["sources"])


if __name__ == "__main__":
    unittest.main()
