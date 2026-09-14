import os
import sys
import tempfile
import unittest

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-project-rules-makefile"),
)

from ai_kit_project_rules_makefile import cli


class TestCheckMakefileShapeTracer(unittest.TestCase):
    def test_check_returns_makefile_key_end_to_end(self):
        with tempfile.TemporaryDirectory() as repo:
            result = cli.check(repo)
            self.assertEqual(set(result.keys()), {"makefile"})
            self.assertTrue(result["makefile"])


if __name__ == "__main__":
    unittest.main()
