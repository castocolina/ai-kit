"""Tests for catalog correction and [models] CLI commands (35-22)."""

import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review"))

from ai_kit_spec import (
    catalog_build,
    catalog_cmds,
    catalog_facts,
    cli,
    model_catalog,
    optional_sources,
)

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


class TestCatalogReportCommand(_Scratch):
    def setUp(self):
        super().setUp()
        self.env["XDG_CACHE_HOME"] = os.path.join(self.root, "cache")
        os.makedirs(self.env["HOME"], exist_ok=True)
        self.runtimes_path = os.path.join(self.root, "runtimes.json")

    def _report(self, entries, snapshot=None, detect=False):
        self._write_catalog(entries)
        if snapshot is not None:
            with open(self.runtimes_path, "w", encoding="utf-8") as handle:
                json.dump(snapshot, handle)
        args = ["catalog-report", "--catalog-path", self.catalog_path]
        args += ["--detect"] if detect else ["--runtimes-json", self.runtimes_path]
        return self._call(args)

    def test_text_output_facts_and_attribution(self):
        key = "fake/placeholder-model-4"
        entry = self._entry(key, runtime="opencode", model=key)
        entry["facts"] = {
            "tier": {"value": "strong", "label": "measured", "source": "models.dev",
                     "fetched_at": T},
            "strengths": {"value": ["coding"], "label": "measured", "source": "arena",
                          "fetched_at": T},
        }
        snapshot = {"clis": {"opencode": {"listing": "none"}}}
        code, output, error = self._report({key: entry}, snapshot)
        self.assertEqual((code, error), (0, ""))
        self.assertIn("facts: tier:", output)
        self.assertIn("strengths:", output)
        self.assertLess(output.index("models.dev ("), output.index("Arena leaderboard"))
        self.assertIn("\n\nAttribution:\n", output)

    def test_json_output(self):
        key = "fake/placeholder-model-4"
        entry = self._entry(key, runtime="opencode", model=key)
        entry["facts"] = {"tier": {"value": "strong", "label": "measured",
                                     "source": "models.dev", "fetched_at": T}}
        self._write_catalog({key: entry})
        args = ["catalog-report", "--catalog-path", self.catalog_path,
                "--runtimes-json", self.runtimes_path, "--json"]
        with open(self.runtimes_path, "w", encoding="utf-8") as handle:
            json.dump({"clis": {}}, handle)
        code, output, error = self._call(args)
        self.assertEqual((code, error), (0, ""))
        data = json.loads(output)
        self.assertIn("facts", data["rows"][0])
        self.assertEqual(data["attribution"], [
            "models.dev (https://models.dev): repository license MIT; no attribution request found."
        ])

    def test_failed_refresh_keeps_credit(self):
        key = "fake/placeholder-model-4"
        entry = self._entry(key, runtime="opencode", model=key)
        entry["facts"] = {"tier": {"value": "strong", "source": "artificial-analysis"}}
        path = self.catalog_path + ".fetch-meta.json"
        with open(path, "w", encoding="utf-8") as handle:
            json.dump({"sources": {"artificial_analysis": {"ok": False}}}, handle)
        code, output, error = self._report({key: entry}, {"clis": {}})
        self.assertEqual((code, error), (0, ""))
        self.assertIn("Source: Artificial Analysis (artificialanalysis.ai)", output)
        self.assertIn("Not endorsed by Artificial Analysis", output)
        self.assertIn("caching rule not stated", output)

    def test_empty_catalog_no_attribution(self):
        code, output, error = self._report({}, {"clis": {}})
        self.assertEqual((code, error), (0, ""))
        self.assertNotIn("Attribution:", output)

    def test_optional_name_shown(self):
        path = optional_sources.store_path(self.env)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump({"copilot": {"placeholder-model-9": [{
                "name": "placeholder-model-9", "source": "web", "label": "web, unverified",
                "url": "https://example.invalid/models", "date": "2026-11-01",
            }]}}, handle)
        code, output, error = self._report({}, {"clis": {}})
        self.assertEqual((code, error), (0, ""))
        self.assertIn("copilot  placeholder-model-9  [not listed]", output)
        self.assertIn("unmatched", output)
        self.assertIn("web, unverified (https://example.invalid/models, 2026-11-01)", output)

    def test_host_row_shown(self):
        snapshot = {"clis": {"pi": {"installed": True, "listing": "ok", "models": []}}}
        code, output, error = self._report({}, snapshot)
        self.assertEqual((code, error), (0, ""))
        self.assertIn("pi  -  [listed, empty]", output)

    def test_unreadable_store_ignored(self):
        path = optional_sources.store_path(self.env)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("{not json")
        key = "fake/placeholder-model-4"
        code, output, error = self._report(
            {key: self._entry(key, runtime="opencode", model=key)}, {"clis": {}}
        )
        self.assertEqual((code, error), (0, ""))
        self.assertIn(key, output)

    def test_detect_is_run_local_proof(self):
        first = "router-env/placeholder-model-1"
        second = "router-env/placeholder-model-2"
        entries = {
            first: self._entry(first, runtime="opencode", model=first),
            second: self._entry(second, runtime="opencode", model=second),
        }
        snapshot = {"clis": {"opencode": {
            "listing": "ok", "models": [first],
            "listed_from": {"at": "2026-11-01T00:00:00Z"},
        }}}
        with mock.patch("ai_kit_spec.catalog_cmds.detection.build_runtimes_snapshot",
                        return_value=snapshot):
            code, live_output, error = self._report(entries, detect=True)
        self.assertEqual((code, error), (0, ""))
        self.assertIn("stale (not in the listing of 2026-11-01T00:00:00Z", live_output)
        code, cached_output, error = self._report(entries, snapshot)
        self.assertEqual((code, error), (0, ""))
        self.assertIn("not checked (cached 2026-11-01T00:00:00Z)", cached_output)


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


class TestOptionalSourceCommands(_Scratch):
    def _read_store(self):
        with open(optional_sources.store_path(self.env), encoding="utf-8") as handle:
            return json.load(handle)

    def setUp(self):
        super().setUp()
        self.env.update({
            "XDG_CACHE_HOME": os.path.join(self.root, "cache"),
            "PATH": os.environ.get("PATH", ""),
        })

    def test_web_query(self):
        code, output, error = self._call(["web-query", "--runtime", "copilot"])
        self.assertEqual((code, error), (0, ""))
        self.assertEqual(output, optional_sources.web_query("copilot") + "\n")

    def test_record_web_names(self):
        path = os.path.join(self.root, "web.json")
        payload = {
            "runtime": "copilot", "query": optional_sources.web_query("copilot"),
            "url": "https://example.invalid/models", "date": "2026-11-19",
            "names": ["placeholder-model-1", "placeholder-model-2"],
        }
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle)
        code, output, error = self._call(["record-web-names", "--file", path])
        self.assertEqual((code, error), (0, ""))
        self.assertEqual(json.loads(output), {
            "runtime": "copilot", "recorded": 2, "label": "web, unverified"
        })
        store = self._read_store()
        self.assertEqual(set(store["copilot"]), {"placeholder-model-1", "placeholder-model-2"})
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("{}")
        code, _, error = self._call(["record-web-names", "--file", path])
        self.assertEqual(code, 2)
        self.assertIn("web file:", error)

    def test_herdr_names_present_and_absent(self):
        from tests.herdr_fakes import write_herdr_fake

        pane = "pane-1"
        answers = {
            ("pane", "split", "--current", "--direction", "right", "--cwd", self.cwd,
             "--no-focus"): (0, json.dumps({"result": {"pane": {"pane_id": pane}}})),
            ("pane", "run", pane, "copilot --allow-all --no-auto-update"): (0, ""),
            ("pane", "wait-output", pane, "--regex", "(?i)copilot", "--timeout", "30000"): (0, ""),
            ("pane", "send-text", pane, "/model"): (0, ""),
            ("pane", "send-keys", pane, "enter"): (0, ""),
            ("pane", "wait-output", pane, "--regex", "(?i)model", "--timeout", "30000"): (0, ""),
            ("pane", "read", pane, "--source", "recent-unwrapped", "--lines", "120"):
                (0, "/model\nplaceholder-model-1\nplaceholder-model-2\n"),
            ("pane", "send-keys", pane, "esc"): (0, ""),
            ("pane", "close", pane): (0, ""),
        }
        bindir = os.path.join(self.root, "bin")
        write_herdr_fake(bindir, answers, os.path.join(self.root, "herdr.log"))
        self.env.update({"HERDR_ENV": "1", "PATH": bindir + os.pathsep + self.env["PATH"]})
        code, output, error = self._call([
            "herdr-names", "--runtime", "copilot", "--cwd", self.cwd
        ])
        self.assertEqual((code, error), (0, ""))
        self.assertEqual(json.loads(output), {"status": "ok", "recorded": 2})
        stored = self._read_store()
        self.assertTrue(all(
            rows[0]["label"] == "interactive view, unverified"
            for rows in stored["copilot"].values()
        ))
        self.env.pop("HERDR_ENV")
        code, output, error = self._call(["herdr-names", "--runtime", "copilot"])
        self.assertEqual((code, error), (0, ""))
        self.assertEqual(json.loads(output), {
            "status": "herdr absent: HERDR_ENV is not 1", "recorded": 0
        })


class TestOptionalFetchCandidates(_Scratch):
    def test_store_and_seed_candidates(self):
        record = {"name": "placeholder-model-1", "source": "web", "label": "web, unverified",
                  "url": "https://example.invalid/models", "date": "2026-11-19"}
        store = {"copilot": {"placeholder-model-1": [record]}}
        provider = "fake" + "-copilot"
        sources = catalog_build.CatalogSources(
            {provider: {"models": {"placeholder-model-2": {}}}}, True, [], False
        )
        found = catalog_cmds.optional_fetch_candidates(
            {"clis": {"copilot": {"installed": True, "listing": "none"}}}, store, sources
        )
        self.assertEqual(found, [
            {"runtime": "copilot", "model_id": "placeholder-model-1",
             "listed_from": [record], "label": "web, unverified"},
            {"runtime": "copilot", "model_id": "placeholder-model-2",
             "listed_from": [{"name": "placeholder-model-2", "source": "seed",
                              "label": "seed, unverified"}], "label": "seed, unverified"},
        ])

    def test_claude_store_names_included(self):
        record = {"name": "placeholder-model-3", "source": "web", "label": "web, unverified"}
        found = catalog_cmds.optional_fetch_candidates(
            {"clis": {"claude": {"installed": True, "listing": "none"}}},
            {"claude": {"placeholder-model-3": [record]}},
            catalog_build.CatalogSources({}, True, [], False),
        )
        self.assertEqual([item["model_id"] for item in found], ["placeholder-model-3"])

    def test_no_models_dev_only_store(self):
        record = {"name": "placeholder-model-1", "source": "web", "label": "web, unverified"}
        found = catalog_cmds.optional_fetch_candidates(
            {"clis": {"copilot": {"installed": True, "listing": "none"}}},
            {"copilot": {"placeholder-model-1": [record]}},
            catalog_build.CatalogSources({}, False, [], False),
        )
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["model_id"], "placeholder-model-1")

    def test_only_unlisted_runtimes(self):
        snapshot = {"clis": {
            "copilot": {"installed": True, "listing": "none"},
            "claude": {"installed": True, "listing": "ok"},
            "cursor": {"installed": True, "listing": "failed"},
            "placeholder-runtime": {"installed": True, "listing": "none"},
        }}
        record = {"name": "placeholder-model-1", "source": "web", "label": "web, unverified"}
        found = catalog_cmds.optional_fetch_candidates(
            snapshot, {"copilot": {"placeholder-model-1": [record]}},
            catalog_build.CatalogSources({}, False, [], False),
        )
        self.assertEqual([item["runtime"] for item in found], ["copilot"])

    def test_duplicate_pair_keeps_records(self):
        key = "fake/placeholder-model-1"
        entry = {"provider": "fake", "runtimes": {"claude": {"model_id": "placeholder-model-1"}},
                 "source": {}, "confidence": "low", "last_verified": "2026-11-20"}
        record = {"name": "placeholder-model-1", "source": "web", "label": "web, unverified",
                  "url": "https://example.invalid/models", "date": "2026-11-19"}
        optional = [{"runtime": "claude", "model_id": "placeholder-model-1",
                     "listed_from": [record], "label": "web, unverified"}]
        taken = {("claude", "placeholder-model-1")}
        self.assertEqual(catalog_cmds.builder_candidates(optional, taken), [])
        catalog, reasons = catalog_cmds.attach_listed_from({key: entry}, optional)
        self.assertEqual(reasons, [])
        self.assertEqual(catalog[key]["runtimes"]["claude"], {
            "model_id": "placeholder-model-1", "listed_from": [record]
        })

    def test_fetch_command_keeps_labels(self):
        provider = "fake" + "-copilot"
        key = provider + "/placeholder-model-2"
        sources = catalog_build.CatalogSources(
            {provider: {"models": {"placeholder-model-2": {"cost": {}}}}},
            True, [], False,
            arena_data={"config": "text", "split": "latest", "categories": {}},
            arena_ok=True,
        )
        discovered = catalog_cmds.optional_fetch_candidates(
            {"clis": {"copilot": {"installed": True, "listing": "none"}}}, {}, sources
        )
        built = catalog_cmds.builder_candidates(discovered, set())
        catalog, _, _ = catalog_build.build_model_catalog(built, sources, {})
        catalog, reasons = catalog_cmds.attach_listed_from(catalog, discovered)
        self.assertEqual(reasons, [])
        self.assertEqual(catalog[key]["runtimes"]["copilot"]["listed_from"][0]["label"],
                         "seed, unverified")
        self.assertNotIn("placeholder-model-1", catalog)


if __name__ == "__main__":
    unittest.main()
