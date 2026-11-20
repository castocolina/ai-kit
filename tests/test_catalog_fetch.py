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

from ai_kit_spec import catalog_fetch, cli, model_catalog, models_config


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


class TestFetchCommand(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="p35-command-")
        self.addCleanup(__import__("shutil").rmtree, self.root, True)
        self.env = {
            "HOME": os.path.join(self.root, "home"),
            "XDG_CONFIG_HOME": os.path.join(self.root, "config"),
            "XDG_CACHE_HOME": os.path.join(self.root, "cache"),
            "AI_KIT_REFUSE_REAL_HOME": "1",
        }
        os.makedirs(os.path.join(self.root, ".aikit"), exist_ok=True)
        self.runtimes = os.path.join(self.root, "runtimes.json")
        with open(self.runtimes, "w", encoding="utf-8") as handle:
            json.dump({"clis": {}}, handle)
        self.catalog = os.path.join(self.root, "catalog.json")

    def _read_json(self, path):
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)

    def _run(self, **overrides):
        import io
        from contextlib import redirect_stdout

        output = io.StringIO()
        defaults = {
            "env_fn": lambda: self.env,
            "load_secret_fn": lambda _env, _name: None,
            "fetch_models_dev_fn": lambda: ({}, False),
            "fetch_artificial_analysis_fn": lambda _key: ([], False),
            "fetch_arena_fn": lambda **_kwargs: (
                {"config": "text", "split": "latest", "categories": {}},
                False,
            ),
        }
        defaults.update(overrides)
        argv = [
            "fetch-model-catalog",
            "--runtimes-json",
            self.runtimes,
            "--catalog-path",
            self.catalog,
            "--cwd",
            self.root,
        ]
        if defaults.pop("if_stale", False):
            argv.append("--if-stale")
        if defaults.pop("jev", False):
            argv.append("--jev")
        with redirect_stdout(output):
            code = cli.main(argv, **defaults)
        return code, json.loads(output.getvalue())

    def test_command_prints_sources_and_attribution(self):
        code, result = self._run(
            fetch_models_dev_fn=lambda: ({"fake": {"models": {"placeholder-model-1": {}}}}, True),
            fetch_arena_fn=lambda **_kw: (
                {"config": "text", "split": "latest", "categories": {}},
                True,
            ),
        )
        self.assertEqual(0, code)
        self.assertTrue(result["arena_ok"])
        self.assertEqual(
            {"fetched": True, "ok": True, "reason": ""}, result["sources"]["models.dev"]
        )
        self.assertEqual(
            "no ARTIFICIAL_ANALYSIS_API_KEY in secrets.env",
            result["sources"]["artificial-analysis"]["reason"],
        )
        written = model_catalog.split_catalog_meta(self._read_json(self.catalog))[0]
        from ai_kit_spec.catalog_attribution import attribution_lines, catalog_sources

        self.assertEqual(attribution_lines(catalog_sources(written)), result["attribution"])

    def test_v3_cache_rebuild_keeps_confirmed_and_verified(self):
        key = "fake/placeholder-model-1"
        entry = {
            "provider": "fake",
            "runtimes": {
                "opencode": {
                    "model_id": "placeholder-model-1",
                    "usability": {
                        "state": "verified",
                        "at": "2026-11-01T00:00:00Z",
                        "via": "check-reviewer",
                        "error": None,
                    },
                }
            },
            "source": {},
            "confidence": "low",
            "last_verified": "2026-11-01",
            "fallback_quota": False,
            "heuristic_confirmed": ["fallback_quota"],
        }
        with open(self.catalog, "w", encoding="utf-8") as handle:
            json.dump({"_meta": {"schema_version": 3}, key: entry}, handle)
        code, _result = self._run()
        self.assertEqual(0, code)
        written = self._read_json(self.catalog)
        self.assertEqual(model_catalog.CATALOG_SCHEMA_VERSION, written["_meta"]["schema_version"])
        self.assertEqual(entry["fallback_quota"], written[key]["fallback_quota"])
        self.assertEqual(entry["heuristic_confirmed"], written[key]["heuristic_confirmed"])
        self.assertEqual(
            entry["runtimes"]["opencode"]["usability"],
            written[key]["runtimes"]["opencode"]["usability"],
        )
        self.assertFalse(
            self._read_json(self.catalog + ".fetch-meta.json")["sources"]["models_dev"]["ok"]
        )

    def test_arena_disabled_by_config(self):
        with open(
            os.path.join(self.root, ".aikit", "config.toml"), "w", encoding="utf-8"
        ) as handle:
            handle.write('[models]\nsources = ["models.dev"]\n')
        calls = []
        code, result = self._run(fetch_arena_fn=lambda **_kw: calls.append(True))
        self.assertEqual(0, code)
        self.assertEqual([], calls)
        self.assertEqual("disabled in [models] sources", result["sources"]["arena"]["reason"])

    def test_jev_only_with_flag(self):
        with (
            mock.patch.object(cli.jev_names, "name_judge", return_value="judge") as name,
            mock.patch.object(cli.jev_names, "class_judge", return_value="class") as klass,
        ):
            self._run()
            name.assert_not_called()
            klass.assert_not_called()
            self._run(jev=True)
            name.assert_called_once()
            klass.assert_called_once()

    def test_fresh_sidecar_and_raw_cache_stay_offline(self):
        os.makedirs(os.path.join(self.root, "sources"), exist_ok=True)
        model_catalog.cache_write_json(
            self.catalog, {"_meta": {"schema_version": model_catalog.CATALOG_SCHEMA_VERSION}}
        )
        now = __import__("time").time()
        for key, data in (
            ("models_dev", {"fake": {"models": {}}}),
            ("arena", {"config": "text", "split": "latest", "categories": {}}),
        ):
            with open(
                os.path.join(self.root, "sources", key + ".json"), "w", encoding="utf-8"
            ) as handle:
                json.dump({"fetched_at": now, "data": data}, handle)
        with open(self.catalog + ".fetch-meta.json", "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "schema_version": 4,
                    "sources": {
                        key: {"last_fetched": now, "ok": True}
                        for key in ("models_dev", "artificial_analysis", "arena")
                    },
                },
                handle,
            )
        calls = []
        with mock.patch.object(cli, "build_model_catalog", wraps=cli.build_model_catalog) as build:
            code, result = self._run(
                if_stale=True,
                fetch_models_dev_fn=lambda: calls.append("md") or ({}, True),
                fetch_arena_fn=lambda **_kw: (
                    calls.append("arena")
                    or ({"config": "text", "split": "latest", "categories": {}}, True)
                ),
            )
            self.assertEqual(0, code)
            self.assertTrue(result["fetch_skipped"])
            build.assert_called_once()
        self.assertEqual([], calls)

    def test_sidecar_written_after_catalog(self):
        original = cli.cache_write_json

        def ordered(path, value):
            if path == self.catalog + ".fetch-meta.json":
                self.assertTrue(os.path.isfile(self.catalog))
                raise RuntimeError("sidecar position reached")
            return original(path, value)

        with (
            mock.patch.object(cli, "cache_write_json", side_effect=ordered),
            self.assertRaisesRegex(RuntimeError, "sidecar position"),
        ):
            self._run(fetch_models_dev_fn=lambda: ({}, True))

    def test_publish_keeps_concurrent_confirmation(self):
        key = "fake/placeholder-model-1"
        original_build = cli.build_model_catalog

        def build(*args, **kwargs):
            catalog, rejected, unmatched = original_build(*args, **kwargs)

            def confirm(current):
                base = current.get(
                    key,
                    {
                        "provider": "fake",
                        "runtimes": {"opencode": {"model_id": "placeholder-model-1"}},
                        "source": {},
                        "confidence": "low",
                        "last_verified": "2026-11-20",
                    },
                )
                current, _ = model_catalog.merge_catalog_entry(
                    current,
                    key,
                    {
                        **base,
                        "confirmed_fields": {
                            "class": {"by": "user", "at": "2026-11-20", "note": "confirmed"}
                        },
                        "facts": {
                            "class": {
                                "value": "general",
                                "label": "user-stated",
                                "source": "user",
                                "fetched_at": "2026-11-20T00:00:00Z",
                            }
                        },
                    },
                )
                return current

            model_catalog.locked_catalog_update(self.catalog, confirm)
            return catalog, rejected, unmatched

        with open(self.runtimes, "w", encoding="utf-8") as handle:
            json.dump(
                {"clis": {"opencode": {"installed": True, "models": ["placeholder-model-1"]}}},
                handle,
            )
        with mock.patch.object(cli, "build_model_catalog", side_effect=build):
            code, _result = self._run(
                fetch_models_dev_fn=lambda: (
                    {"fake": {"models": {"placeholder-model-1": {}}}},
                    True,
                ),
                env_fn=lambda: self.env,
            )
        self.assertEqual(0, code)
        written = self._read_json(self.catalog)
        self.assertIn("class", written[key]["confirmed_fields"])
        self.assertEqual("user-stated", written[key]["facts"]["class"]["label"])


if __name__ == "__main__":
    unittest.main()
