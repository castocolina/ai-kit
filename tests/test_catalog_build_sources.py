"""35-14 tests for catalog facts and name resolution."""

import os
import sys
import unittest

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review"))

from ai_kit_spec import catalog_build, catalog_facts, models_config, optional_sources
from ai_kit_spec.model_catalog import canonical_key

T = "2026-11-19T00:00:00Z"


def _sources(data=None, ok=True):
    return catalog_build.CatalogSources(data or {}, ok, [], False)


def _build(discovered, sources, existing=None, inputs=None):
    return catalog_build.build_model_catalog(
        discovered, sources, existing or {}, facts_inputs=inputs
    )


class TestSeedHint(unittest.TestCase):
    def test_provider_hint_unchanged(self):
        seed_provider = optional_sources.SEED_ROWS[0].models_dev_provider
        self.assertEqual(catalog_build._fixed_seed_provider("claude"), seed_provider)
        self.assertIsNone(catalog_build._fixed_seed_provider("copilot"))
        self.assertIsNone(catalog_build._fixed_seed_provider("pi"))
        self.assertIsNotNone(seed_provider)
        payload = {
            seed_provider: {"models": {"placeholder-model-1": {"source_tag": "seed"}}},
            "fake": {"models": {"placeholder-model-1": {"source_tag": "other"}}},
        }
        sources = catalog_build.CatalogSources(payload, True, [], False)
        claude_matches, _ = catalog_build._fetch_source_matches(
            {"runtime": "claude", "model_id": "placeholder-model-1"}, sources, None
        )
        copilot_matches, _ = catalog_build._fetch_source_matches(
            {"runtime": "copilot", "model_id": "placeholder-model-1"}, sources, None
        )
        assert claude_matches.md_match is not None
        self.assertEqual(claude_matches.md_match["provider"], seed_provider)
        self.assertIsNone(copilot_matches.md_match)


class TestFactsCore(unittest.TestCase):
    def test_router_alias_assumed(self):
        md = {
            "router-env": {"models": {"placeholder-model-1": {"modalities": {"input": ["text"]}}}}
        }
        result, rejected, _ = _build(
            [{"runtime": "pi", "model_id": "router-env/placeholder-model-1"}],
            _sources(md),
            inputs=catalog_facts.FactsInputs(snapshot={}, now=T),
        )
        entry = result["router-env/placeholder-model-1"]
        self.assertEqual(rejected, [])
        self.assertTrue(entry["is_router"])
        self.assertTrue(entry["fallback_quota"])
        self.assertEqual(
            entry["facts"]["class"],
            {
                "value": "router",
                "label": "assumed",
                "source": "router-env alias naming",
                "fetched_at": T,
            },
        )
        self.assertNotIn("modalities", entry["facts"])

    def test_router_alias_two_runtimes(self):
        result, _, _ = _build(
            [
                {"runtime": rid, "model_id": "router-env/placeholder-model-1"}
                for rid in ("pi", "opencode")
            ],
            _sources(),
            inputs=catalog_facts.FactsInputs(snapshot={}, now=T),
        )
        self.assertEqual(
            set(result["router-env/placeholder-model-1"]["runtimes"]), {"pi", "opencode"}
        )

    def test_router_variants_one_identity(self):
        result, _, _ = _build(
            [
                {"runtime": "opencode", "model_id": "router-env/placeholder-model-1#high"},
                {"runtime": "pi", "model_id": "router-env/placeholder-model-1"},
            ],
            _sources(),
            inputs=catalog_facts.FactsInputs(snapshot={}, now=T),
        )
        entry = result["router-env/placeholder-model-1"]
        self.assertEqual(
            entry["runtimes"]["opencode"]["model_id"], "router-env/placeholder-model-1#high"
        )
        self.assertEqual(entry["runtimes"]["opencode"]["efforts"], ["high"])
        self.assertEqual(set(entry["runtimes"]), {"opencode", "pi"})

    def test_models_dev_facts_and_two_hosts(self):
        md = {
            "fake": {
                "models": {
                    "placeholder-model-1": {
                        "modalities": {"input": ["text", "image"], "output": ["text"]},
                        "reasoning": True,
                        "status": "deprecated",
                        "canonical_model_id": "fake/placeholder-model-1",
                        "cost": {"input": 1, "output": 3},
                    }
                }
            }
        }
        result, rejected, _ = _build(
            [{"runtime": "opencode", "model_id": "fake/placeholder-model-1"}],
            _sources(md),
            inputs=catalog_facts.FactsInputs(snapshot={}, now=T),
        )
        entry = result[canonical_key("fake", "placeholder-model-1")]
        self.assertEqual(rejected, [])
        self.assertEqual(entry["identity"], "fake/placeholder-model-1")
        for name, value in (
            ("modalities", md["fake"]["models"]["placeholder-model-1"]["modalities"]),
            ("reasoning", True),
            ("status", "deprecated"),
        ):
            self.assertEqual(entry["facts"][name]["value"], value)
            self.assertEqual(entry["facts"][name]["fetched_at"], T)
        self.assertEqual(entry["facts"]["cost_band"]["value"], "unknown")
        self.assertEqual(entry["facts"]["cost_band"]["confidence"], "rule")


class TestFactsRuntimeRows(unittest.TestCase):
    def setUp(self):
        self.md = {
            "fake": {
                "models": {
                    "placeholder-model-1": {
                        "modalities": {"input": ["text"]},
                        "cost": {"input": 0, "output": 0},
                    }
                }
            }
        }

    def build(
        self,
        model_id="fake/placeholder-model-1",
        runtime="opencode",
        snapshot=None,
        existing=None,
        sources=None,
        inputs_extra=None,
    ):
        inputs = catalog_facts.FactsInputs(snapshot=snapshot or {}, now=T, **(inputs_extra or {}))
        return _build(
            [{"runtime": runtime, "model_id": model_id}],
            sources or _sources(self.md),
            existing,
            inputs,
        )[0]

    def test_opencode_efforts_and_last_seen(self):
        snap = {
            "clis": {
                "opencode": {
                    "listing": "ok",
                    "listed_from": {"at": "2026-11-18T00:00:00Z"},
                    "models": ["fake/placeholder-model-1"],
                    "model_records": {"fake/placeholder-model-1": {"efforts": ["low", "high"]}},
                }
            }
        }
        row = self.build(snapshot=snap)["fake/placeholder-model-1"]["runtimes"]["opencode"]
        self.assertEqual(row["efforts"], ["high", "low"])
        self.assertEqual(row["last_seen"], "2026-11-18T00:00:00Z")

    def test_no_last_seen_without_ok_listing(self):
        snap = {
            "clis": {
                "opencode": {
                    "listing": "failed",
                    "listed_from": {"at": T},
                    "models": ["fake/placeholder-model-1"],
                }
            }
        }
        self.assertNotIn(
            "last_seen",
            self.build(snapshot=snap)["fake/placeholder-model-1"]["runtimes"]["opencode"],
        )

    def test_cached_source_time_kept(self):
        row = self.build(inputs_extra={"source_at": {"models_dev": "2026-11-01T00:00:00Z"}})[
            "fake/placeholder-model-1"
        ]
        self.assertEqual(row["facts"]["modalities"]["fetched_at"], "2026-11-01T00:00:00Z")

    def test_known_id_not_split(self):
        md = {"fake": {"models": {"placeholder-model-6-max": {}}}}
        key = canonical_key("fake", "placeholder-model-6-max")
        result = self.build(
            "placeholder-model-6-max",
            "cursor",
            sources=_sources(md),
            existing={
                key: {
                    "provider": "fake",
                    "runtimes": {"cursor": {"model_id": "placeholder-model-6-max"}},
                    "source": {},
                    "confidence": "low",
                    "last_verified": "2026-11-19",
                }
            },
        )
        self.assertNotIn("efforts", result[key]["runtimes"]["cursor"])

    def test_cursor_effort_from_name(self):
        result = self.build("placeholder-model-1-high", "cursor", sources=_sources(self.md))
        self.assertEqual(
            result["fake/placeholder-model-1"]["runtimes"]["cursor"]["efforts"], ["high"]
        )

    def test_last_seen_only_on_listing(self):
        result = self.build(
            "placeholder-model-1",
            "codex",
            snapshot={"clis": {"codex": {"listing": "ok", "listed_from": {"at": T}}}},
        )
        self.assertNotIn("last_seen", result["fake/placeholder-model-1"]["runtimes"]["codex"])

    def test_outage_keeps_facts(self):
        key = "fake/placeholder-model-1"
        cached = {
            key: {
                "provider": "fake",
                "runtimes": {"opencode": {"model_id": "fake/placeholder-model-1"}},
                "source": {},
                "confidence": "low",
                "last_verified": "2026-11-19",
                "facts": {
                    "modalities": {
                        "value": {"input": ["text"]},
                        "label": "measured",
                        "source": "models.dev",
                        "fetched_at": T,
                    }
                },
            }
        }
        result = self.build(sources=_sources({}, False), existing=cached)
        self.assertEqual(result[key]["facts"]["modalities"], cached[key]["facts"]["modalities"])

    def test_disabled_source_removes_facts(self):
        key = "fake/placeholder-model-1"
        previous = {
            "modalities": {
                "value": ["text"],
                "label": "measured",
                "source": "models.dev",
                "fetched_at": T,
            },
            "other": {"value": True, "label": "measured", "source": "other", "fetched_at": T},
        }
        existing = {
            key: {
                "provider": "fake",
                "runtimes": {"opencode": {"model_id": key}},
                "source": {},
                "confidence": "low",
                "last_verified": "2026-11-19",
                "facts": previous,
            }
        }
        settings = models_config.ModelsSettings(
            ("arena",), dict(models_config.DEFAULT_CACHE_DAYS), ()
        )
        result = self.build(existing=existing, inputs_extra={"settings": settings})
        self.assertNotIn("modalities", result[key]["facts"])
        self.assertIn("other", result[key]["facts"])

    def test_router_confirmed_value_kept(self):
        key = "router-env/placeholder-model-1"
        existing = {
            key: {
                "provider": "router-env",
                "runtimes": {"pi": {"model_id": key}},
                "is_router": True,
                "fallback_quota": False,
                "heuristic_confirmed": ["fallback_quota"],
                "batch_mode": False,
                "source": {},
                "confidence": "low",
                "last_verified": "2026-11-19",
            }
        }
        result = _build(
            [{"runtime": "pi", "model_id": key}],
            _sources(),
            existing,
            catalog_facts.FactsInputs(snapshot={}, now=T),
        )[0]
        self.assertFalse(result[key]["fallback_quota"])

    def test_usability_survives_rebuild(self):
        key = "fake/placeholder-model-1"
        existing = {
            key: {
                "provider": "fake",
                "runtimes": {
                    "opencode": {
                        "model_id": key,
                        "usability": {"state": "verified", "at": T, "via": "test", "error": None},
                    }
                },
                "source": {},
                "confidence": "low",
                "last_verified": "2026-11-19",
            }
        }
        result = self.build(existing=existing)
        self.assertEqual(result[key]["runtimes"]["opencode"]["usability"]["state"], "verified")


class TestNameResolution(unittest.TestCase):
    def test_two_host_names_one_identity(self):
        md = {"fake": {"models": {"placeholder-model-1": {}}}}
        result, _, _ = _build(
            [
                {"runtime": "opencode", "model_id": "fake/placeholder-model-1"},
                {"runtime": "codex", "model_id": "placeholder-model-1"},
                {"runtime": "cursor", "model_id": "placeholder-model-1-high"},
            ],
            _sources(md),
            inputs=catalog_facts.FactsInputs(snapshot={}, now=T),
        )
        entry = result["fake/placeholder-model-1"]
        self.assertEqual(set(entry["runtimes"]), {"opencode", "codex", "cursor"})
        self.assertEqual(entry["runtimes"]["cursor"]["efforts"], ["high"])

    def test_judged_match_labeled(self):
        md = {"fake": {"models": {"placeholder-model-71": {}, "placeholder-model-72": {}}}}
        calls = []

        def judge(items):
            calls.extend(items)
            return [("placeholder-model-72", 0.9, "")]

        result, _, _ = _build(
            [{"runtime": "codex", "model_id": "placeholder-model-7"}],
            _sources(md),
            inputs=catalog_facts.FactsInputs(snapshot={}, now=T, name_judge=judge),
        )
        key = canonical_key("fake", "placeholder-model-72")
        match = result[key]["runtimes"]["codex"]["match"]
        self.assertEqual(match["source"], "jev")
        self.assertEqual(match["confidence"], 0.9)
        self.assertEqual(calls.__len__(), 1)

    def test_low_or_absent_judge_unmatched(self):
        md = {"fake": {"models": {"placeholder-model-71": {}, "placeholder-model-72": {}}}}
        calls = []

        def judge(items):
            calls.extend(items)
            return [(None, 0.3, "low")]

        candidates = [{"runtime": "codex", "model_id": "placeholder-model-7"}]
        resolved, matches = catalog_facts.resolve_candidates(
            candidates, _sources(md), catalog_facts.FactsInputs({}, now=T, name_judge=judge)
        )
        self.assertTrue(resolved[0]["unresolved"])
        self.assertEqual(matches[("codex", "placeholder-model-7")], ("unmatched", None))
        self.assertEqual(len(calls), 1)
        self.assertNotIn(
            "fake/placeholder-model-7",
            _build(candidates, _sources(md), inputs=catalog_facts.FactsInputs({}, now=T))[0],
        )

    def test_no_models_dev_passthrough(self):
        calls = []

        def judge(items):
            calls.extend(items)
            return []

        candidates = [{"runtime": "codex", "model_id": "placeholder-model-7"}]
        resolved, matches = catalog_facts.resolve_candidates(
            candidates, _sources({}, False), catalog_facts.FactsInputs({}, now=T, name_judge=judge)
        )
        self.assertEqual((resolved, matches, calls), (candidates, {}, []))


if __name__ == "__main__":
    unittest.main()
