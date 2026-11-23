"""35-16 tier, class and source-provenance tests."""

import json
import os
import sys
import unittest

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review"))

from ai_kit_spec import catalog_build, catalog_facts, models_config

T = "2026-11-10T00:00:00Z"


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


def _entry(model_id, provider="fake", facts=None, **fields):
    key = f"{provider}/{model_id}"
    return key, {
        "provider": provider,
        "runtimes": {"opencode": {"model_id": key}},
        "source": {},
        "confidence": "low",
        "last_verified": "2026-11-10",
        "facts": facts or {},
        **fields,
    }


def _build(entry, *, arena=None, aa=None, aa_ok=True, settings=None, inputs=None):
    key, value = entry
    sources = catalog_build.CatalogSources(
        {}, False, aa or [], aa_ok, arena_data=arena, arena_ok=arena is not None
    )
    return catalog_build.build_model_catalog(
        [{"runtime": "opencode", "model_id": value["runtimes"]["opencode"]["model_id"]}],
        sources,
        {key: value},
        facts_inputs=inputs
        or catalog_facts.FactsInputs(
            snapshot={},
            settings=settings,
            now=T,
            source_at={"arena": T, "artificial_analysis": T},
        ),
    )[0][key]


def _aa_models():
    models = []
    for number in range(1, 9):
        # synthetic: Artificial Analysis shapes, invented values
        model = {
            "slug": f"placeholder-model-{number}",
            "name": f"placeholder-model-{number}",
            "model_creator": {"name": "fake"},
            "evaluations": {"artificial_analysis_intelligence_index": number * 10},
        }
        models.append(model)
    return models


class TestTiers(unittest.TestCase):
    def test_arena_tier(self):
        entry = _entry("placeholder-model-4")
        result = _build(entry, arena=_arena_data())
        self.assertEqual(result["facts"]["tier"]["value"], "frontier")
        self.assertEqual(result["facts"]["tier"]["source"], "arena")
        self.assertEqual(result["facts"]["tier"]["note"], "effort not distinguished")

    def test_arena_effort_rows(self):
        result = _build(_entry("placeholder-model-5"), arena=_arena_data())
        self.assertIn("thinking", result["facts"]["tier"]["by_effort"])
        self.assertNotIn("note", result["facts"]["tier"])

    def test_aa_decides_when_present(self):
        md = {"fake": {"models": {f"placeholder-model-{n}": {} for n in range(1, 9)}}}
        aa = _aa_models()
        entry = _entry("placeholder-model-7", scores={"intelligence_index": 70})
        sources = catalog_build.CatalogSources(md, True, aa, True, _arena_data(), True)
        result = catalog_build.build_model_catalog(
            [{"runtime": "opencode", "model_id": "fake/placeholder-model-7"}],
            sources,
            {entry[0]: entry[1]},
            facts_inputs=catalog_facts.FactsInputs(
                {}, now=T, source_at={"arena": T, "artificial_analysis": T}
            ),
        )[0][entry[0]]
        self.assertEqual(result["facts"]["tier"]["source"], "artificial-analysis")
        self.assertEqual(result["facts"]["tier"]["value"], "frontier")

    def test_source_time_kept(self):
        facts = catalog_facts.catalog_tiers.tier_facts(
            {"fake/placeholder-model-4": _entry("placeholder-model-4")[1]},
            catalog_build.CatalogSources({}, False, [], False, _arena_data(), True),
            catalog_facts.FactsInputs({}, now="later", source_at={"arena": T}),
        )
        self.assertEqual(facts["fake/placeholder-model-4"]["tier"]["fetched_at"], T)

    def test_neither_source(self):
        result = _build(_entry("placeholder-model-9"))
        self.assertNotIn("tier", result["facts"])

    def test_class_rule_and_strengths(self):
        result = _build(
            _entry(
                "placeholder-model-4",
                facts={
                    "cost_band": {
                        "value": "low",
                        "label": "judged",
                        "confidence": "rule",
                        "source": "models.dev",
                        "fetched_at": T,
                    }
                },
            ),
            arena=_arena_data(),
        )
        self.assertEqual(result["facts"]["class"]["value"], "flagship")
        self.assertEqual(result["facts"]["strengths"]["source"], "arena")

    def test_class_judge(self):
        calls = []

        def judge(items):
            calls.extend(items)
            return [("coding", 0.8, "")]

        facts = catalog_facts.catalog_tiers.tier_facts(
            {"fake/placeholder-model-9": _entry("placeholder-model-9")[1]},
            catalog_build.CatalogSources({}, False, [], False),
            catalog_facts.FactsInputs({}, now=T, class_judge=judge),
        )
        self.assertEqual(facts["fake/placeholder-model-9"]["class"]["source"], "jev")
        self.assertEqual(facts["fake/placeholder-model-9"]["class"]["value"], "coding")
        self.assertEqual(len(calls), 1)

    def test_judged_arena_match(self):
        def judge(items):
            return [("placeholder-model-72", 0.9, "")]

        categories = {
            "overall": {
                "placeholder-model-71": {"rating": 1100},
                "placeholder-model-72": {"rating": 1400},
                "placeholder-model-73": {"rating": 1200},
                "placeholder-model-74": {"rating": 1300},
            }
        }
        data = {"categories": categories}
        key, entry = _entry("placeholder-model-7")
        sources = catalog_build.CatalogSources({}, False, [], False, data, True)
        facts = catalog_facts.catalog_tiers.tier_facts(
            {key: entry}, sources, catalog_facts.FactsInputs({}, now=T, name_judge=judge)
        )
        self.assertEqual(facts[key]["tier"]["match_confidence"], 0.9)
        unmatched = catalog_facts.catalog_tiers.tier_facts(
            {key: entry}, sources, catalog_facts.FactsInputs({}, now=T)
        )
        self.assertNotIn("tier", unmatched[key])

    def test_aa_outage_keeps_tier(self):
        old = {
            "tier": {
                "value": "frontier",
                "label": "judged",
                "confidence": "rule",
                "source": "artificial-analysis",
                "fetched_at": T,
            }
        }
        result = _build(_entry("placeholder-model-9", facts=old), aa_ok=False)
        self.assertEqual(result["facts"]["tier"], old["tier"])

    def test_aa_outage_with_arena_keeps_aa_tier(self):
        old = {
            "tier": {
                "value": "strong",
                "label": "judged",
                "confidence": "rule",
                "source": "artificial-analysis",
                "fetched_at": T,
            }
        }
        result = _build(_entry("placeholder-model-4", facts=old), arena=_arena_data(), aa_ok=False)
        self.assertEqual(result["facts"]["tier"], old["tier"])

    def test_arena_disabled_removes_facts(self):
        old = {
            "tier": {
                "value": "light",
                "label": "judged",
                "confidence": "rule",
                "source": "arena",
                "fetched_at": T,
            },
            "strengths": {
                "value": ["coding"],
                "label": "judged",
                "confidence": "rule",
                "source": "arena",
                "fetched_at": T,
            },
            "class": {
                "value": "general",
                "label": "judged",
                "confidence": "rule",
                "source": "ai-kit class rule",
                "fetched_at": T,
                "inputs": ["arena"],
            },
        }
        settings = models_config.ModelsSettings(
            ("models.dev", "artificial-analysis"), dict(models_config.DEFAULT_CACHE_DAYS), ()
        )
        result = _build(
            _entry("placeholder-model-4", facts=old), arena=_arena_data(), settings=settings
        )
        self.assertFalse(set(result["facts"]) & {"tier", "strengths"})
        self.assertNotIn("arena", result["facts"].get("class", {}).get("inputs", []))

    def test_router_untouched(self):
        key = "router-env/placeholder-model-1"
        entry = {
            "provider": "router-env",
            "runtimes": {"opencode": {"model_id": key}},
            "source": {},
            "confidence": "low",
            "last_verified": "2026-11-10",
            "facts": {
                "class": {
                    "value": "router",
                    "label": "assumed",
                    "source": "router-env alias naming",
                    "fetched_at": T,
                }
            },
        }
        result = catalog_facts.catalog_tiers.tier_facts(
            {key: entry},
            catalog_build.CatalogSources({}, False, [], False),
            catalog_facts.FactsInputs({}, now=T),
        )
        self.assertNotIn(key, result)

    def test_aa_disabled_ignores_raw_inputs(self):
        settings = models_config.ModelsSettings(
            ("models.dev", "arena"), dict(models_config.DEFAULT_CACHE_DAYS), ()
        )
        entry = _entry(
            "placeholder-model-9",
            scores={"intelligence_index": 70, "coding_index": 90},
            tokens_per_sec=500.0,
        )
        result = _build(entry, settings=settings)
        self.assertNotIn("tier", result["facts"])
        self.assertNotIn("artificial-analysis", result["facts"]["class"]["inputs"])

    def test_judge_only_without_measured_fields(self):
        calls = []

        def judge(items):
            calls.extend(items)
            return []

        entry = _entry(
            "placeholder-model-9",
            facts={
                "modalities": {
                    "value": {"input": ["text"]},
                    "label": "measured",
                    "source": "models.dev",
                    "fetched_at": T,
                }
            },
        )
        facts = catalog_facts.catalog_tiers.tier_facts(
            {entry[0]: entry[1]},
            catalog_build.CatalogSources({}, False, [], False),
            catalog_facts.FactsInputs({}, now=T, class_judge=judge),
        )
        self.assertEqual(facts[entry[0]]["class"]["value"], "unknown")
        self.assertEqual(calls, [])


class TestTiersOutageAndCuts(unittest.TestCase):
    def test_arena_cuts_use_overall_ratings_only(self):
        categories = {
            category: {f"placeholder-model-{n}": {"rating": base + 10 * n} for n in range(1, 9)}
            for category, base in (("overall", 1000), ("coding", 2000))
        }
        catalog = {
            f"fake/placeholder-model-{n}": _entry(f"placeholder-model-{n}")[1] for n in range(1, 9)
        }
        sources = catalog_build.CatalogSources(
            {}, False, [], False, {"categories": categories}, True
        )
        facts = catalog_facts.catalog_tiers.tier_facts(
            catalog, sources, catalog_facts.FactsInputs({}, now=T)
        )
        self.assertEqual(
            [facts[f"fake/placeholder-model-{n}"]["tier"]["value"] for n in range(1, 9)],
            ["light", "light", "capable", "capable", "strong", "strong", "frontier", "frontier"],
        )

    def test_arena_outage_keeps_class_tier_and_strengths(self):
        cost = {
            "value": "low",
            "label": "judged",
            "confidence": "rule",
            "source": "models.dev",
            "fetched_at": T,
        }
        first = _build(
            _entry("placeholder-model-4", facts={"cost_band": cost}), arena=_arena_data()
        )
        second = _build(("fake/placeholder-model-4", first), arena=None)
        for name in ("tier", "class", "strengths"):
            self.assertEqual(first["facts"][name], second["facts"][name])
        self.assertEqual(first["facts"]["tier"]["value"], "frontier")
        self.assertEqual(first["facts"]["class"]["value"], "flagship")
        self.assertIn("arena", second["facts"]["class"]["inputs"])

    def test_tier_time_is_the_deciding_sources_time(self):
        key, entry = _entry("placeholder-model-4", scores={"intelligence_index": 70})
        sources = catalog_build.CatalogSources({}, False, [], False, _arena_data(), True)
        inputs = catalog_facts.FactsInputs(
            {},
            now=T,
            settings=models_config.ModelsSettings(
                ("arena", "artificial-analysis"), dict(models_config.DEFAULT_CACHE_DAYS), ()
            ),
            source_at={"arena": T, "artificial_analysis": "2026-11-01T00:00:00Z"},
        )
        result = catalog_facts.catalog_tiers.tier_facts({key: entry}, sources, inputs)
        self.assertEqual(result[key]["tier"]["source"], "arena")
        self.assertEqual(result[key]["tier"]["fetched_at"], T)

    def test_class_inputs_name_the_tier_source(self):
        data = {
            "categories": {
                "overall": {
                    f"placeholder-model-{n}": {"rating": 1000 + 100 * n} for n in range(1, 5)
                }
            }
        }
        result = _build(_entry("placeholder-model-4"), arena=data)
        self.assertIn("arena", result["facts"]["class"]["inputs"])

    def test_router_entries_are_not_matched(self):
        calls = []

        def judge(items):
            calls.extend(items)
            return []

        key = "router-env/placeholder-model-4"
        entry = {"provider": "router-env"}
        data = {
            "categories": {
                "overall": {
                    "placeholder-model-41": {"rating": 1000},
                    "placeholder-model-42": {"rating": 1100},
                }
            }
        }
        sources = catalog_build.CatalogSources({}, False, [], False, data, True)
        result = catalog_facts.catalog_tiers.tier_facts(
            {key: entry}, sources, catalog_facts.FactsInputs({}, now=T, name_judge=judge)
        )
        self.assertEqual(calls, [])
        self.assertNotIn(key, result)

    def test_cached_judged_class_survives_a_refresh_without_a_judge_answer(self):
        first = _build(
            _entry("placeholder-model-9"),
            inputs=catalog_facts.FactsInputs(
                {}, now=T, class_judge=lambda items: [("coding", 0.8, "")]
            ),
        )
        self.assertEqual(first["facts"]["class"]["source"], "jev")
        self.assertEqual(first["facts"]["class"]["value"], "coding")

        second = _build(
            ("fake/placeholder-model-9", first),
            inputs=catalog_facts.FactsInputs({}, now="2026-11-12T00:00:00Z"),
        )
        self.assertEqual(second["facts"]["class"], first["facts"]["class"])

        third = _build(
            ("fake/placeholder-model-9", first),
            inputs=catalog_facts.FactsInputs(
                {},
                now="2026-11-12T00:00:00Z",
                class_judge=lambda items: [("not-a-class", 0.8, "")],
            ),
        )
        self.assertEqual(third["facts"]["class"], first["facts"]["class"])

        unknown = _build(
            _entry("placeholder-model-8"), inputs=catalog_facts.FactsInputs({}, now=T)
        )
        self.assertEqual(unknown["facts"]["class"]["value"], "unknown")


if __name__ == "__main__":
    unittest.main()
