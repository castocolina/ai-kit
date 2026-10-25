"""Drift gate for the compiled error catalog."""

import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

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

    def test_write_keeps_the_template_mode_and_leaves_no_temp_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "cross-ai.mjs")
            with open(target, "w", encoding="utf-8") as handle:
                handle.write("old")
            os.chmod(target, 0o755)
            with mock.patch.object(cross_ai_catalog, "TEMPLATE_PATH", target):
                cross_ai_catalog._write_template("new \u00e9")
            with open(target, encoding="utf-8") as handle:
                self.assertEqual(handle.read(), "new \u00e9")
            self.assertEqual(os.stat(target).st_mode & 0o777, 0o755)
            self.assertEqual(os.listdir(tmp), ["cross-ai.mjs"])


if __name__ == "__main__":
    unittest.main()
