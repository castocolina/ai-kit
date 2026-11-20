"""Phase 35 stub; plan 35-18 replaces this body."""

import os
import sys
import unittest

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review"))


from ai_kit_spec.catalog_attribution import (
    AA_DERIVED_LINE,
    AA_TERMS_LINE,
    ATTRIBUTION,
    SOURCE_ORDER,
    attribution_lines,
    catalog_sources,
)


class TestAttribution(unittest.TestCase):
    def test_fixed_order(self):
        self.assertEqual(
            [ATTRIBUTION["models.dev"], ATTRIBUTION["arena"]],
            attribution_lines(["arena", "models.dev"]),
        )

    def test_aa_lines(self):
        self.assertEqual(
            [ATTRIBUTION["artificial-analysis"], AA_DERIVED_LINE, AA_TERMS_LINE],
            attribution_lines(["artificial-analysis"]),
        )

    def test_none_and_unknown(self):
        self.assertEqual([], attribution_lines([]))
        with self.assertRaisesRegex(ValueError, r"^unknown source: unknown$"):
            attribution_lines(["unknown"])

    def test_ascii(self):
        for source in SOURCE_ORDER:
            for line in attribution_lines([source]):
                with self.subTest(source=source, line=line):
                    self.assertTrue(line.isascii())

    def test_catalog_sources(self):
        catalog = {
            "_meta": {},
            "fake/placeholder-model-1": {
                "facts": {
                    "tier": {"source": "artificial-analysis"},
                    "class": {
                        "source": "ai-kit class rule",
                        "inputs": ["arena", "models.dev"],
                    },
                }
            },
        }
        self.assertEqual(["models.dev", "artificial-analysis", "arena"], catalog_sources(catalog))
        self.assertEqual([], catalog_sources({}))


if __name__ == "__main__":
    unittest.main()
