"""AGENTS.md's relative links resolve, and none points into a gitignored path (SPEC R14, D-10).

Parsing reuses the rules-agents CLI's link helpers, so both agree on what a link is.
"""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "skills" / "ai-kit-project-rules-agents"))

from ai_kit_project_rules_agents.cli import (
    _LINK_RE,
    _parse_link_target,
    _without_fenced_code,
)


def is_ignored(repo_root, target):
    proc = subprocess.run(
        ["git", "-C", str(repo_root), "check-ignore", "-q", target],
        capture_output=True,
        check=False,
    )
    return proc.returncode == 0


def bad_links(agents_md_text, repo_root):
    """`<target> (missing)` or `<target> (ignored)` for each bad relative link, in file order.

    Existence is checked first, so a path that is both missing and ignored reports `missing`.
    """
    problems = []
    for match in _LINK_RE.finditer(_without_fenced_code(agents_md_text)):
        target = _parse_link_target(match.group(1))
        if target is None:
            continue
        if not os.path.exists(os.path.join(repo_root, target)):
            problems.append(f"{target} (missing)")
        elif is_ignored(repo_root, target):
            problems.append(f"{target} (ignored)")
    return problems


def in_work_tree(path):
    proc = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode == 0 and proc.stdout.strip() == "true"


def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], capture_output=True, check=True)


class TestAgentsMdLinks(unittest.TestCase):
    def setUp(self):
        if not in_work_tree(REPO):
            self.skipTest("not a git work tree: ignore status unknown")

    def test_real_agents_md_has_no_bad_link(self):
        text = (REPO / "AGENTS.md").read_text(encoding="utf-8")
        self.assertEqual(bad_links(text, REPO), [])

    def test_ignored_then_missing_reported_in_file_order(self):
        with tempfile.TemporaryDirectory() as root:
            _scratch_repo(Path(root))
            text = (
                "[a](secret/x.md)\n"
                "[b](missing.md)\n"
                "[c](ok.md#part)\n"
                "[d](https://example.com)\n"
            )
            self.assertEqual(
                bad_links(text, root),
                ["secret/x.md (ignored)", "missing.md (missing)"],
            )

    def test_missing_wins_over_ignored(self):
        with tempfile.TemporaryDirectory() as root:
            _scratch_repo(Path(root))
            self.assertEqual(
                bad_links("[g](secret/gone.md)\n", root),
                ["secret/gone.md (missing)"],
            )

    def test_no_relative_links_passes(self):
        with tempfile.TemporaryDirectory() as root:
            _scratch_repo(Path(root))
            text = "Only [an external](https://example.com) link.\n"
            self.assertEqual(bad_links(text, root), [])

    def test_link_inside_fenced_code_is_not_checked(self):
        with tempfile.TemporaryDirectory() as root:
            _scratch_repo(Path(root))
            text = "```\n[example](missing.md)\n```\n"
            self.assertEqual(bad_links(text, root), [])


def _scratch_repo(root):
    _git(root, "init", "-q")
    (root / ".gitignore").write_text("secret/\n", encoding="utf-8")
    (root / "secret").mkdir()
    (root / "secret" / "x.md").write_text("ignored\n", encoding="utf-8")
    (root / "ok.md").write_text("ok\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
