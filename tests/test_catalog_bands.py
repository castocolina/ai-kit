"""Tests for pure catalog banding rules."""

import os
import sys
import unittest

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review"))

from ai_kit_spec.catalog_bands import (
    ClassInputs,
    class_for,
    cost_band,
    cost_cuts,
    delta_cuts,
    price_per_million,
    quartile_cuts,
    strengths_for,
    tier_for,
)


class TestTiersAndCost(unittest.TestCase):
    def test_quartile_cuts(self):
        self.assertEqual(quartile_cuts([10, 20, 30, 40, 50, 60, 70, 80]), (30, 50, 70))
        self.assertIsNone(quartile_cuts([1, 2, 3]))
        self.assertIsNone(quartile_cuts([]))
        self.assertEqual(quartile_cuts([80, 10, 70, 20, 60, 30, 50, 40]), (30, 50, 70))

    def test_tier_edges(self):
        cuts = (30, 50, 70)
        self.assertEqual(tier_for(70, cuts), "frontier")
        self.assertEqual(tier_for(69.99, cuts), "strong")
        self.assertEqual(tier_for(50, cuts), "strong")
        self.assertEqual(tier_for(30, cuts), "capable")
        self.assertEqual(tier_for(29, cuts), "light")
        self.assertEqual(tier_for(None, cuts), "unknown")
        self.assertEqual(tier_for(80, None), "unknown")

    def test_equal_scores_share_tier(self):
        self.assertEqual(tier_for(55, (30, 50, 70)), tier_for(55, (30, 50, 70)))

    def test_price_per_million(self):
        self.assertEqual(price_per_million({"input": 1.0, "output": 3.0}), (4.0, False))
        self.assertEqual(price_per_million({"input": 0, "output": 0}), (0.0, True))
        self.assertEqual(price_per_million(None), (None, False))
        self.assertEqual(price_per_million({"input": "x"}), (None, False))

    def test_cost_band(self):
        cuts = (1, 3, 8)
        self.assertEqual(cost_band(4.0, False, cuts), "high")
        self.assertEqual(cost_band(8, False, cuts), "premium")
        self.assertEqual(cost_band(0.5, False, cuts), "low")
        self.assertEqual(cost_band(0.0, True, cuts), "free_or_local")
        self.assertEqual(cost_band(None, False, cuts), "unknown")
        self.assertEqual(cost_band(5, False, None), "unknown")

    def test_cost_cuts_median_per_id(self):
        md_payload = {
            "fake-provider-a": {
                "models": {
                    "placeholder-model-1": {
                        "canonical_model_id": "fake/shared",
                        "cost": {"input": 1, "output": 1},
                    },
                    "placeholder-model-2": {
                        "canonical_model_id": "fake/model-two",
                        "cost": {"input": 9, "output": 1},
                    },
                    "placeholder-model-3": {
                        "canonical_model_id": "fake/model-three",
                        "cost": {"input": 19, "output": 1},
                    },
                    "placeholder-model-4": {
                        "canonical_model_id": "fake/model-four",
                        "cost": {"input": 29, "output": 1},
                    },
                    "placeholder-model-7": {
                        "canonical_model_id": "fake/a",
                        "cost": {"input": 39, "output": 1},
                    },
                    "placeholder-model-8": {
                        "canonical_model_id": "fake/b",
                        "cost": {"input": 59, "output": 1},
                    },
                    "placeholder-model-5": {
                        "canonical_model_id": "fake/a",
                        "cost": {"input": 0, "output": 0},
                    },
                    "placeholder-model-6": {
                        "canonical_model_id": "fake/b",
                        "cost": {"input": 0, "output": 0},
                    },
                }
            },
            "fake-provider-b": {
                "models": {
                    "placeholder-model-1": {
                        "canonical_model_id": "fake/shared",
                        "cost": {"input": 2, "output": 2},
                    }
                }
            },
            "fake-provider-c": {
                "models": {
                    "placeholder-model-1": {
                        "canonical_model_id": "fake/shared",
                        "cost": {"input": 4, "output": 5},
                    }
                }
            },
        }
        self.assertEqual(cost_cuts(md_payload), (10, 30, 40))

    def test_non_finite_and_negative_refused(self):
        self.assertEqual(
            quartile_cuts([float("nan"), 10, 20, 30, 40]), quartile_cuts([10, 20, 30, 40])
        )
        self.assertEqual(tier_for(float("nan"), (30, 50, 70)), "unknown")
        self.assertEqual(tier_for(float("inf"), (30, 50, 70)), "unknown")
        self.assertEqual(price_per_million({"input": -1.0, "output": 3.0}), (None, False))
        self.assertEqual(price_per_million({"input": float("inf"), "output": 1.0}), (None, False))


class TestClassAndStrengths(unittest.TestCase):
    def test_router(self):
        inputs = ClassInputs(True, "unknown", "unknown", None, None, None, None)
        self.assertEqual(class_for(inputs), "router")

    def test_unknown(self):
        inputs = ClassInputs(False, "unknown", "unknown", None, None, None, None)
        self.assertEqual(class_for(inputs), "unknown")

    def test_flagship(self):
        inputs = ClassInputs(False, "frontier", "unknown", None, None, None, None)
        self.assertEqual(class_for(inputs), "flagship")

    def test_coding_edge(self):
        self.assertEqual(
            class_for(ClassInputs(False, "strong", "unknown", 30, 26, None, None)), "coding"
        )
        self.assertEqual(
            class_for(ClassInputs(False, "strong", "unknown", 20, 26, None, None)), "general"
        )

    def test_fast(self):
        self.assertEqual(
            class_for(ClassInputs(False, "light", "unknown", None, None, 90, 80)), "fast"
        )
        self.assertEqual(
            class_for(ClassInputs(False, "light", "unknown", None, None, None, 80)), "general"
        )

    def test_small_and_general(self):
        self.assertEqual(
            class_for(ClassInputs(False, "light", "low", None, None, None, None)), "small"
        )
        self.assertEqual(
            class_for(ClassInputs(False, "light", "unknown", None, None, None, None)), "general"
        )

    def test_capable_general(self):
        inputs = ClassInputs(False, "capable", "unknown", None, None, None, None)
        self.assertEqual(class_for(inputs), "general")

    def test_strengths(self):
        categories = {
            "overall": {f"placeholder-model-{index}": 1300 + index for index in range(6)},
            "coding": {
                f"placeholder-model-{index}": 1300 + index + delta
                for index, delta in enumerate((1, 2, 3, 4, 5, 40))
            },
        }
        self.assertEqual(delta_cuts(categories), {"coding": 5})
        self.assertEqual(
            strengths_for(
                {"overall": 1300, "coding": 1340, "math": 1290},
                {"coding": 26.0, "math": 10.0},
            ),
            ["coding"],
        )
        self.assertEqual(strengths_for({"coding": 1300}, {"coding": 1}), [])
        self.assertEqual(delta_cuts({}), {})
        self.assertEqual(delta_cuts({"coding": {"placeholder-model-1": 1300}}), {})
        self.assertEqual(delta_cuts({"overall": "x"}), {})


if __name__ == "__main__":
    unittest.main()
