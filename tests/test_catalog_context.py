"""35-21 per-runtime context precedence and user-stated fact preservation tests."""

import os
import sys
import unittest

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review"))

from ai_kit_spec import catalog_build, catalog_facts, catalog_report, models_config

NOW = "2026-11-20T00:00:00Z"
MODEL = "router-env/placeholder-model-1"


def _settings(context=()):
    return models_config.ModelsSettings(("models.dev", "arena"), {}, context)


def _entry(runtimes=None, facts=None):
    return {
        "provider": "router-env",
        "runtimes": runtimes or {},
        "source": {},
        "confidence": "low",
        "last_verified": "2026-11-20",
        "facts": facts or {},
    }


def _build(entry, snapshot=None, md=None, md_ok=False, settings=None, source_at=None):
    sources = catalog_build.CatalogSources(md or {}, md_ok, [], False)
    key = "router-env/placeholder-model-1"
    if entry.get("provider") != "router-env":
        key = "fake/placeholder-model-1"
    return catalog_facts.apply_facts(
        {key: entry},
        sources,
        catalog_facts.FactsInputs(snapshot or {}, settings, NOW, source_at=source_at or {}),
    )[0][key]


class TestContextPerRuntime(unittest.TestCase):
    def test_two_runtimes_two_windows(self):
        entry = _entry(
            {
                "pi": {"model_id": MODEL},
                "opencode": {"model_id": MODEL},
            }
        )
        snapshot = {
            "clis": {
                "pi": {"context_window": {MODEL: 200000}},
                "opencode": {
                    "model_records": {MODEL: {"limit": {"context": 262144, "input": 150000}}}
                },
            }
        }
        result = _build(entry, snapshot)
        runtimes = result["runtimes"]
        self.assertEqual(runtimes["pi"]["context"]["value"], 200000)
        self.assertEqual(runtimes["pi"]["context"]["source"], "pi listing")
        self.assertEqual(runtimes["pi"]["ctx_window"], 200000)
        self.assertEqual(runtimes["opencode"]["context"]["value"], 150000)
        self.assertEqual(
            runtimes["opencode"]["context"]["source"], "opencode /api/model limit.input"
        )
        self.assertEqual(runtimes["opencode"]["ctx_window"], 150000)

    def test_report_line_per_runtime(self):
        entry = _build(
            _entry({"pi": {"model_id": MODEL}, "opencode": {"model_id": MODEL}}),
            {
                "clis": {
                    "pi": {"context_window": {MODEL: 200000}},
                    "opencode": {"model_records": {MODEL: {"limit": {"input": 150000}}}},
                }
            },
        )
        rows = catalog_report.report_rows({"router-env/placeholder-model-1": entry}, {"clis": {}})
        lines = {row.runtime: row.context for row in rows}
        self.assertIn("200000 (measured, pi listing,", lines["pi"])
        self.assertIn("150000 (measured, opencode /api/model limit.input,", lines["opencode"])


class TestContextRules(unittest.TestCase):
    def test_host_beats_models_dev(self):
        md = {"fake": {"models": {"placeholder-model-1": {"limit": {"context": 128000}}}}}
        result = _build(
            _entry({"pi": {"model_id": "placeholder-model-1"}}),
            {"clis": {"pi": {"context_window": {"placeholder-model-1": 200000}}}},
            md,
            True,
        )
        self.assertEqual(result["runtimes"]["pi"]["context"]["source"], "pi listing")

    def test_override_beats_all(self):
        override = models_config.ContextOverride("pi", MODEL, 64000)
        result = _build(
            _entry({"pi": {"model_id": MODEL}}),
            {"clis": {"pi": {"context_window": {MODEL: 200000}}}},
            {"router-env": {"models": {"placeholder-model-1": {"limit": {"context": 128000}}}}},
            True,
            _settings((override,)),
        )
        self.assertEqual(result["runtimes"]["pi"]["context"]["value"], 64000)
        self.assertEqual(result["runtimes"]["pi"]["context"]["label"], "user-stated")
        self.assertEqual(result["runtimes"]["pi"]["context"]["source"], "[[models.context]]")

    def test_invalid_values_ignored(self):
        for value in (0, -5, 1.5, "400K"):
            with self.subTest(value=value):
                result = _build(
                    _entry({"pi": {"model_id": "placeholder-model-1"}}),
                    {"clis": {"pi": {"context_window": {"placeholder-model-1": value}}}},
                    {"fake": {"models": {"placeholder-model-1": {"limit": {"context": 128000}}}}},
                    True,
                )
                row = result["runtimes"]["pi"]
                self.assertEqual(row["context"]["value"], 128000)
                self.assertIn(repr(value), row["ctx_note"])

    def test_invalid_input_falls_to_context(self):
        result = _build(
            _entry({"opencode": {"model_id": MODEL}}),
            {
                "clis": {
                    "opencode": {
                        "model_records": {MODEL: {"limit": {"input": 0, "context": 262144}}}
                    }
                }
            },
        )
        row = result["runtimes"]["opencode"]
        self.assertEqual(row["context"]["value"], 262144)
        self.assertEqual(row["context"]["source"], "opencode /api/model limit.context")
        self.assertIn("0", row["ctx_note"])

    def test_host_time_is_listing_time(self):
        result = _build(
            _entry({"pi": {"model_id": MODEL}}),
            {
                "clis": {
                    "pi": {
                        "listed_from": {"at": "2026-11-01T00:00:00Z"},
                        "context_window": {MODEL: 200000},
                    }
                }
            },
        )
        self.assertEqual(result["runtimes"]["pi"]["context"]["fetched_at"], "2026-11-01T00:00:00Z")

    def test_obsolete_note_cleared(self):
        existing = _entry({"pi": {"model_id": "placeholder-model-1", "ctx_note": "old"}})
        result = _build(
            existing, {"clis": {"pi": {"context_window": {"placeholder-model-1": 200000}}}}
        )
        self.assertNotIn("ctx_note", result["runtimes"]["pi"])

    def test_removed_override_recomputed(self):
        existing = _entry({"pi": {"model_id": MODEL}})
        first = _build(
            existing,
            {"clis": {"pi": {"context_window": {MODEL: 200000}}}},
            settings=_settings((models_config.ContextOverride("pi", MODEL, 64000),)),
        )
        second = _build(first, {"clis": {"pi": {"context_window": {MODEL: 200000}}}})
        self.assertEqual(first["runtimes"]["pi"]["context"]["label"], "user-stated")
        self.assertEqual(second["runtimes"]["pi"]["context"]["value"], 200000)
        self.assertEqual(second["runtimes"]["pi"]["context"]["label"], "measured")

    def test_unknown_stays_unknown(self):
        result = _build(
            _entry({"pi": {"model_id": "placeholder-model-1"}}),
            {},
            {"fake": {"models": {"placeholder-model-1": {}}}},
            True,
        )
        self.assertIsNone(result["runtimes"]["pi"]["context"]["value"])
        self.assertIsNone(result["runtimes"]["pi"].get("ctx_window"))

    def test_no_guess_from_name(self):
        result = _build(_entry({"pi": {"model_id": "placeholder-model-1-128k"}}))
        self.assertNotIn("context", result["runtimes"]["pi"])

    def test_preserved_when_source_down(self):
        cached = catalog_build.CatalogSources({}, False, [], False)
        old = {"value": 128000, "label": "measured", "source": "models.dev", "fetched_at": NOW}
        result = catalog_facts.apply_facts(
            {
                "router-env/placeholder-model-1": _entry(
                    {
                        "pi": {
                            "model_id": "placeholder-model-1",
                            "context": old,
                            "ctx_window": 128000,
                        }
                    }
                )
            },
            cached,
            catalog_facts.FactsInputs({}, now=NOW),
        )[0]
        row = result["router-env/placeholder-model-1"]["runtimes"]["pi"]
        self.assertEqual(row["context"], old)
        self.assertEqual(row["ctx_window"], 128000)

    def test_user_stated_fact_kept(self):
        key = "fake/placeholder-model-4"
        old_fact = {
            "value": "coding",
            "label": "user-stated",
            "source": "confirm-model",
            "fetched_at": NOW,
        }
        entry = {
            "provider": "fake",
            "runtimes": {"opencode": {"model_id": key}},
            "source": {},
            "confidence": "low",
            "last_verified": "2026-11-20",
            "facts": {"class": old_fact},
        }
        sources = catalog_build.CatalogSources(
            {},
            False,
            [],
            False,
            {
                "categories": {
                    "overall": {
                        f"placeholder-model-{n}": {"rating": 1000 + n * 100} for n in range(1, 9)
                    }
                }
            },
            True,
        )
        inputs = catalog_facts.FactsInputs({}, now=NOW)
        without = catalog_facts.apply_facts({key: {**entry, "facts": {}}}, sources, inputs)[0][key]
        with_user = catalog_facts.apply_facts({key: entry}, sources, inputs)[0][key]
        self.assertNotEqual(without["facts"]["class"]["value"], "coding")
        self.assertEqual(with_user["facts"]["class"], old_fact)

    def test_provider_specific_models_dev_window(self):
        md = {
            "fake": {"models": {"placeholder-model-1": {"limit": {"context": 100000}}}},
            "fake-two": {"models": {"placeholder-model-1": {"limit": {"context": 200000}}}},
        }
        entry = _entry(
            {
                "opencode": {"model_id": "fake/placeholder-model-1"},
                "codex": {"model_id": "placeholder-model-1"},
            }
        )
        entry["provider"] = "fake"
        result = _build(entry, {}, md, True)
        self.assertEqual(result["runtimes"]["opencode"]["context"]["value"], 100000)
        self.assertIsNone(result["runtimes"]["codex"]["context"]["value"])
        self.assertEqual(catalog_report.context_line(result["runtimes"]["codex"]), "unknown")


if __name__ == "__main__":
    unittest.main()
