"""Drift gate for the compiled error catalog."""

import os
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-spec-review"))

from ai_kit_spec import cross_ai_catalog


def _template_text():
    with open(cross_ai_catalog.TEMPLATE_PATH, encoding="utf-8") as handle:
        return handle.read()


class CrossAiCatalogTest(unittest.TestCase):
    def test_rendered_block_matches_template(self):
        rows = cross_ai_catalog.load_rows(cross_ai_catalog.CATALOG_PATH)
        rendered = cross_ai_catalog.splice(
            _template_text(), cross_ai_catalog.render_block(rows),
        )
        self.assertEqual(rendered, _template_text())

    def test_changed_evidence_changes_the_block(self):
        rows = cross_ai_catalog.load_rows(cross_ai_catalog.CATALOG_PATH)
        changed = [dict(row) for row in rows]
        changed[0]["evidence"] = changed[0]["evidence"] + " (changed)"
        original = _template_text()
        spliced = cross_ai_catalog.splice(original, cross_ai_catalog.render_block(changed))
        self.assertNotEqual(spliced, original)

    def test_check_cli_reports_ok(self):
        env = dict(os.environ, PYTHONPATH=os.path.join(
            os.path.dirname(__file__), "..", "skills", "ai-kit-spec-review",
        ))
        proc = subprocess.run(
            [sys.executable, "-m", "ai_kit_spec.cross_ai_catalog", "--check"],
            capture_output=True, text=True, env=env, check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("catalog ok ", proc.stdout)


if __name__ == "__main__":
    unittest.main()
