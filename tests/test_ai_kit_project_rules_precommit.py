import os
import sys
import tempfile
import unittest

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-project-rules-precommit"),
)

from ai_kit_project_rules_precommit import cli

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)


class TestCheckTracer(unittest.TestCase):
    """Task 1's minimum interim coverage: a real end-to-end `check` call
    against a fixture repo, so the test module the gates now name is a real
    file from the first commit. Task 3 fills this suite out."""

    def test_check_returns_precommit_key_end_to_end(self):
        with tempfile.TemporaryDirectory() as repo:
            _write(
                os.path.join(repo, "Makefile"),
                "ruff:\n\tuv run pre-commit run ruff --all-files\n",
            )
            _write(
                os.path.join(repo, ".pre-commit-config.yaml"),
                "repos:\n"
                "  - repo: local\n"
                "    hooks:\n"
                "      - id: ruff\n"
                "        entry: ruff check .\n"
                "      - id: mypy\n"
                "        entry: mypy .\n",
            )
            result = cli.check(repo)
            self.assertEqual(sorted(result), ["precommit"])
            issues = {f["issue"] for f in result["precommit"]}
            self.assertIn("hook_without_target", issues)


if __name__ == "__main__":
    unittest.main()
