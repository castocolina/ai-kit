"""Tests for catalog correction and [models] CLI commands (35-22)."""

import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review"))

from ai_kit_spec import catalog_build, catalog_facts, cli, model_catalog

T = "2026-11-20T00:00:00Z"


def _arena_data():
    path = os.path.join(_REPO_ROOT, "tests", "fixtures", "arena_rows.json")
    with open(path, encoding="utf-8") as handle:
        rows = json.load(handle)["rows"]
    categories = {}
    for row in rows:
        if isinstance(row.get("model_name"), str):
            categories.setdefault(row["category"], {})[row["model_name"]] = {
                "rating": row.get("rating")
            }
    return {"categories": categories}


class _Scratch(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="ai-kit-p35-catalog-cmds-")
        self.addCleanup(shutil.rmtree, self.root, True)
        self.catalog_path = os.path.join(self.root, "model-catalog.json")
        self.cwd = os.path.join(self.root, "project")
        os.makedirs(self.cwd)
        self.env = {
            "HOME": os.path.join(self.root, "home"),
            "XDG_CONFIG_HOME": os.path.join(self.root, "config"),
            "AI_KIT_REFUSE_REAL_HOME": "1",
        }

    def _entry(self, model_id, runtime="pi", model=None):
        return {
            "provider": "fake",
            "runtimes": {runtime: {"model_id": model or model_id}},
            "source": {"models_dev": False, "artificial_analysis": False},
            "confidence": "low",
            "last_verified": "2026-11-20",
        }

    def _write_catalog(self, entries):
        data = {**entries, "_meta": {"schema_version": model_catalog.CATALOG_SCHEMA_VERSION}}
        with open(self.catalog_path, "w", encoding="utf-8") as handle:
            json.dump(data, handle)

    def _read_catalog(self):
        with open(self.catalog_path, encoding="utf-8") as handle:
            return json.load(handle)

    def _call(self, argv):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = cli.main(argv, env_fn=lambda: dict(self.env))
        return code, stdout.getvalue(), stderr.getvalue()


class TestConfirmModel(_Scratch):
    def test_confirm_heuristic_field(self):
        key = "router-env/placeholder-model-1"
        self._write_catalog({key: self._entry(key)})
        code, output, _ = self._call([
            "confirm-model", "--catalog-path", self.catalog_path, "--model-id", key,
            "--field", "fallback_quota", "--value", "false", "--note", "owner answer",
        ])
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(output)["confirmed"])
        entry = self._read_catalog()[key]
        self.assertIs(entry["fallback_quota"], False)
        self.assertIn("fallback_quota", entry["heuristic_confirmed"])
        self.assertEqual(entry["confirmed_fields"]["fallback_quota"]["by"], "confirm-model")
        self.assertEqual(entry["confirmed_fields"]["fallback_quota"]["note"], "owner answer")
        self.assertTrue(entry["confirmed_fields"]["fallback_quota"]["at"].endswith("Z"))

    def test_survives_refresh(self):
        key = "router-env/placeholder-model-1"
        self._write_catalog({key: self._entry(key)})
        code, _, error = self._call([
            "confirm-model", "--catalog-path", self.catalog_path, "--model-id", key,
            "--field", "fallback_quota", "--value", "false",
        ])
        self.assertEqual((code, error), (0, ""))
        existing = {key: self._read_catalog()[key]}
        refreshed, _, _ = catalog_build.build_model_catalog(
            [{"runtime": "pi", "model_id": key}],
            catalog_build.CatalogSources({}, False, [], False), existing,
        )
        self.assertIs(refreshed[key]["fallback_quota"], False)

    def test_confirm_class_user_stated(self):
        key = "fake/placeholder-model-4"
        self._write_catalog({key: self._entry(key, runtime="opencode", model=key)})
        code, _, error = self._call([
            "confirm-model", "--catalog-path", self.catalog_path, "--model-id", key,
            "--field", "class", "--value", "coding",
        ])
        self.assertEqual((code, error), (0, ""))
        entry = self._read_catalog()[key]
        self.assertEqual(entry["facts"]["class"]["value"], "coding")
        self.assertEqual(entry["facts"]["class"]["label"], "user-stated")
        self.assertEqual(entry["facts"]["class"]["source"], "confirm-model")

    def test_confirmed_class_survives_rebuild(self):
        key = "fake/placeholder-model-4"
        self._write_catalog({key: self._entry(key, runtime="opencode", model=key)})

        def rebuild(existing):
            sources = catalog_build.CatalogSources({}, False, [], False,
                                                   arena_data=_arena_data(), arena_ok=True)
            inputs = catalog_facts.FactsInputs({}, now=T, source_at={"arena": T})
            discovered = [{"runtime": "opencode", "model_id": key}]
            return catalog_build.build_model_catalog(
                discovered, sources, existing, facts_inputs=inputs)[0][key]

        before = rebuild({key: self._read_catalog()[key]})
        self.assertNotEqual(before["facts"].get("class", {}).get("value"), "coding")
        code, _, error = self._call([
            "confirm-model", "--catalog-path", self.catalog_path, "--model-id", key,
            "--field", "class", "--value", "coding",
        ])
        self.assertEqual((code, error), (0, ""))
        after = rebuild({key: self._read_catalog()[key]})
        self.assertEqual(after["facts"]["class"]["value"], "coding")
        self.assertEqual(after["facts"]["class"]["label"], "user-stated")

    def test_earlier_confirmed_fields_kept(self):
        key = "router-env/placeholder-model-1"
        self._write_catalog({key: self._entry(key)})
        for field in ("fallback_quota", "batch_mode"):
            code, _, error = self._call([
                "confirm-model", "--catalog-path", self.catalog_path, "--model-id", key,
                "--field", field, "--value", "false",
            ])
            self.assertEqual((code, error), (0, ""))
        confirmed = self._read_catalog()[key]["confirmed_fields"]
        self.assertEqual(set(confirmed), {"fallback_quota", "batch_mode"})

    def test_unknown_key_nearest(self):
        key = "router-env/placeholder-model-1"
        self._write_catalog({key: self._entry(key)})
        code, _, error = self._call([
            "confirm-model", "--catalog-path", self.catalog_path,
            "--model-id", "router-env/placeholder-model-", "--field", "batch_mode",
            "--value", "false",
        ])
        self.assertEqual(code, 1)
        self.assertIn("nearest:", error)
        self.assertIn(key, error)

    def test_bad_value(self):
        key = "router-env/placeholder-model-1"
        self._write_catalog({key: self._entry(key)})
        original = self._read_catalog()
        code, _, error = self._call([
            "confirm-model", "--catalog-path", self.catalog_path, "--model-id", key,
            "--field", "fallback_quota", "--value", "maybe",
        ])
        self.assertEqual(code, 2)
        self.assertIn("fallback_quota needs true or false", error)
        self.assertEqual(self._read_catalog(), original)


class TestModelsConfigCommand(_Scratch):
    def test_write_and_show_project(self):
        args = ["models-config", "--cwd", self.cwd, "--sources", "models.dev,arena",
                "--cache-days", "arena=3", "--context", "pi",
                "router-env/placeholder-model-1", "64000"]
        code, output, error = self._call(args)
        self.assertEqual((code, error), (0, ""))
        written = json.loads(output)["written"]
        expected_suffix = os.path.join(".aikit", "config.toml")
        self.assertTrue(written.endswith(expected_suffix))
        code, output, error = self._call(["models-config", "--cwd", self.cwd, "--show"])
        self.assertEqual((code, error), (0, ""))
        settings = json.loads(output)
        self.assertEqual(settings["sources"], ["models.dev", "arena"])
        self.assertEqual(settings["cache_days"]["arena"], 3)
        self.assertEqual(settings["context"], [{
            "runtime": "pi", "model": "router-env/placeholder-model-1", "tokens": 64000,
        }])

    def test_global_and_unknown_source(self):
        code, output, error = self._call([
            "models-config", "--cwd", self.cwd, "--global", "--sources", "arena",
        ])
        self.assertEqual((code, error), (0, ""))
        self.assertIn(os.path.join("config", "ai-kit", "config.toml"),
                      json.loads(output)["written"])
        code, _, error = self._call([
            "models-config", "--cwd", self.cwd, "--sources", "lmsys",
        ])
        self.assertEqual(code, 2)
        self.assertIn("unknown source 'lmsys'", error)

    def test_bad_context_tokens(self):
        code, _, error = self._call([
            "models-config", "--cwd", self.cwd, "--context", "pi",
            "router-env/placeholder-model-1", "64k",
        ])
        self.assertEqual(code, 2)
        self.assertIn("bad --context tokens: 64k", error)
        self.assertFalse(os.path.exists(os.path.join(self.cwd, ".aikit", "config.toml")))


if __name__ == "__main__":
    unittest.main()
