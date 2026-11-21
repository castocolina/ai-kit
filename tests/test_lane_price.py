"""Phase 36: lane_price (sourced zero price and the free pool key)."""

import os
import sys
import unittest

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review"))

from ai_kit_spec import lane_price
from ai_kit_spec.lane_price import ZERO_LOCALITY, Price
from ai_kit_spec.model_catalog import canonical_key

T = "2026-11-20T00:00:00Z"
KEY = "fake/placeholder-model-1"


def _band(value, source="models.dev"):
    return {"value": value, "label": "judged", "source": source, "fetched_at": T,
            "confidence": "rule"}


def _entry(band=None, pricing=None):
    result = {"provider": "fake", "runtimes": {}, "source": {}, "confidence": "low",
              "last_verified": "2026-11-20", "facts": {}}
    if band is not None:
        result["facts"]["cost_band"] = band
    if pricing is not None:
        result["pricing"] = pricing
    return result


def _cli(model_id, cost):
    return {"installed": True, "listing": "ok", "listed_from": {
        "command": "opencode models", "version": "v1", "at": T},
        "model_records": {model_id: {"cost": cost}}}


class TestSourcedZero(unittest.TestCase):
    def test_models_dev_zero_with_source_and_date(self):
        entry = _entry(_band("free_or_local"), {"input_per_1m": 0, "output_per_1m": 0})
        self.assertEqual(lane_price.price_of(KEY, entry, KEY, {}, "pi"),
                         Price("zero", 0, 0, ({"source": "models.dev", "date": T,
                                               "reading": "zero"},), ZERO_LOCALITY, ""))

    def test_host_listing_zero_with_source_and_date(self):
        result = lane_price.price_of(KEY, _entry(), KEY, _cli(KEY, [{"input": 0, "output": 0,
                                    "cache": 0, "tier": "base"}]), "opencode")
        self.assertEqual(result, Price("zero", 0, 0, ({"source":
                         "opencode listing (opencode models v1)",
                         "date": T, "reading": "zero"},), ZERO_LOCALITY, ""))


class TestPriceStates(unittest.TestCase):
    def test_one_positive_figure_is_not_zero(self):
        for inp, out in ((0, 3), (0.0001, 0)):
            result = lane_price.price_of(KEY, _entry(), KEY,
                                         _cli(KEY, [{"input": inp, "output": out}]), "opencode")
            self.assertEqual((result.state, result.input, result.output), ("nonzero", inp, out))

    def test_missing_price_is_unknown(self):
        entries = [_entry(), _entry(_band("unknown")),
                   _entry(pricing={"input_per_1m": 0, "output_per_1m": 0}),
                   _entry(_band("free_or_local", "artificial-analysis"))]
        for label in (None, [], {}, 3):
            fact: dict = _band("free_or_local")
            if label is None:
                del fact["label"]
            else:
                fact["label"] = label
            entries.append(_entry(fact))
        for entry in entries:
            self.assertEqual(lane_price.price_of(KEY, entry, KEY, _cli(KEY, []), "pi"),
                             Price("unknown", None, None, (), "", ""))

    def test_models_dev_figures_rule(self):
        result = lane_price.price_of(KEY, _entry(_band("free_or_local")), KEY, {}, "pi")
        self.assertEqual((result.state, result.input, result.note),
                         ("zero", None, "figure not stored"))
        result = lane_price.price_of(KEY, _entry(_band("free_or_local"),
                                     {"input_per_1m": 0, "output_per_1m": 0.5}), KEY, {}, "pi")
        self.assertEqual((result.state, result.sources[0]["reading"]), ("conflict", "conflict"))
        result = lane_price.price_of(KEY, _entry(_band("high"),
                                     {"input_per_1m": 3, "output_per_1m": 15}), KEY, {}, "pi")
        self.assertEqual((result.state, result.input, result.note),
                         ("nonzero", None, "figure not stored"))

    def test_conflict_is_not_zero(self):
        result = lane_price.price_of(KEY, _entry(_band("free_or_local")), KEY,
                                     _cli(KEY, [{"input": 1, "output": 2}]), "opencode")
        self.assertEqual((result.state, result.locality), ("conflict", ""))
        self.assertEqual([x["reading"] for x in result.sources], ["nonzero", "zero"])

    def test_name_wording_never_read(self):
        key = canonical_key("fake", "placeholder-model-1-free")
        self.assertEqual(lane_price.price_of(key, _entry(_band("high")), key, {}, "pi").state,
                         "nonzero")
        key = canonical_key("fake", "placeholder-model-2")
        result = lane_price.price_of(key, _entry(_band("free_or_local")), key, {}, "pi")
        self.assertEqual(result.state, "zero")

    def test_several_cost_tiers(self):
        cases = [([{"input": 0, "output": 0}] * 2, "zero"),
                 ([{"input": 0, "output": 0}, {"input": "n/a", "output": 0}], "unknown"),
                 ([{"input": 0, "output": 0}, {"input": 2, "output": 2}], "nonzero"),
                 ([{"input": 10**400, "output": 0}], "unknown"),
                 ([{"input": True, "output": 0}], "unknown"),
                 ([{"input": -1, "output": 0}], "unknown")]
        for cost, expected in cases:
            result = lane_price.price_of(KEY, _entry(), KEY, _cli(KEY, cost), "opencode")
            self.assertEqual(result.state, expected)
            if expected == "nonzero":
                self.assertEqual((result.input, result.output, result.note),
                                 (None, None, "multiple tiers"))

    def test_other_provider_row_has_its_own_price(self):
        other = canonical_key("fake-free", "placeholder-model-1")
        entry = _entry(_band("high"))
        result = lane_price.price_of(KEY, entry, other,
                                     _cli(other, [{"input": 0, "output": 0}]), "opencode")
        self.assertEqual((result.state, len(result.sources)), ("zero", 1))
        self.assertEqual(lane_price.price_of(KEY, entry, KEY, {}, "pi").state, "nonzero")
        result = lane_price.price_of(KEY, _entry(_band("free_or_local")),
                                     "placeholder-model-1", {}, "codex")
        self.assertEqual(result.state, "zero")

    def test_pool_key(self):
        other = canonical_key("fake-free", "placeholder-model-1")
        for item, provider, expected in ((KEY, "fake", "fake:free"),
                                         ("placeholder-model-1", "fake", "fake:free"),
                                         (other, "fake", "fake-free:free"),
                                         ("placeholder-model-1", "bad provider", None),
                                         ("placeholder-model-1", None, None)):
            result = lane_price.pool_key(item, provider)
            self.assertEqual(result, expected)
            if result is not None:
                self.assertIsNotNone(lane_price.POOL_KEY_RX.fullmatch(result))


if __name__ == "__main__":
    unittest.main()
