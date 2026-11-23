"""Phase 35 labeled catalog facts."""

import os
import sys
import unittest

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review"))

from ai_kit_spec.catalog_labels import fact, fact_problem, show

TIME = "2026-11-19T00:00:00Z"


class TestCatalogLabels(unittest.TestCase):
    def test_fact_shapes(self):
        self.assertEqual(fact(5, "measured", "models.dev", TIME), {
            "value": 5, "label": "measured", "source": "models.dev", "fetched_at": TIME
        })
        self.assertEqual(fact("frontier", "judged", "arena", TIME, confidence="rule"), {
            "value": "frontier", "label": "judged", "source": "arena", "fetched_at": TIME,
            "confidence": "rule",
        })

    def test_fact_errors(self):
        with self.assertRaisesRegex(ValueError, "judged needs a confidence"):
            fact("frontier", "judged", "arena", TIME)
        with self.assertRaisesRegex(ValueError, "unknown label: guessed"):
            fact(1, "guessed", "arena", TIME)

    def test_fact_problem(self):
        self.assertIsNone(fact_problem(fact(5, "measured", "models.dev", TIME)))
        problem = fact_problem({"value": 1})
        self.assertIsNotNone(problem)
        assert problem is not None
        self.assertTrue(problem.startswith("bad fact:"))
        malformed = fact("frontier", "judged", "arena", TIME, confidence=1.5)
        problem = fact_problem(malformed)
        self.assertIsNotNone(problem)
        assert problem is not None
        self.assertTrue(problem.startswith("bad fact:"))

    def test_show(self):
        self.assertEqual(show(None), "unknown")
        self.assertEqual(show(fact(None, "measured", "models.dev", TIME)), "unknown")
        self.assertEqual(show(fact(["text", "image"], "measured", "models.dev", TIME)),
                         f"text, image (measured, models.dev, {TIME})")
        self.assertEqual(show(fact("frontier", "judged", "arena", TIME, confidence="rule")),
                         f"frontier (judged rule, arena, {TIME})")


if __name__ == "__main__":
    unittest.main()
