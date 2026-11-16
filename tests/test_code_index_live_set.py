"""IDX-06 live-set rule: a live line naming the legacy code index also names codebase-memory-mcp.

The live set is the git-tracked files under the paths below, tests/ included (this module too).
It never reads .planning/ (arch rule). The legacy name is assembled at run time so this module's
own lines need no exemption.
"""

import os
import subprocess
import unittest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LIVE_SET = (
    "skills",
    "tools",
    "tests",
    "AGENTS.md",
    "README.md",
    "Makefile",
    ".gitignore",
    ".pre-commit-config.yaml",
    "pyproject.toml",
    "docs/run-book",
    ".graphifyignore",
    ".cbmignore",
)
_LEGACY = "code" + "graph"
_REPLACEMENT = "codebase-memory-mcp"


def legacy_lines(text):
    """(line number, line) for every line that names the legacy tool, any case."""
    return [(n, line) for n, line in enumerate(text.splitlines(), start=1)
            if _LEGACY in line.lower()]


def unpaired_lines(path, text):
    """'path:line: text' for each legacy line that lacks the replacement name."""
    return [f"{path}:{n}: {line.strip()}" for n, line in legacy_lines(text)
            if _REPLACEMENT not in line.lower()]


def live_set_files(repo=_REPO):
    """Git-tracked files under the live-set paths, repo-relative."""
    listed = subprocess.run(["git", "ls-files", "-z", "--", *_LIVE_SET], cwd=repo,
                            capture_output=True, text=True, check=True).stdout
    return sorted(p for p in listed.split("\0") if p)


def scan_live_set(repo=_REPO):
    """(count of legacy lines in the live set, unpaired 'path:line: text' entries)."""
    hits, problems = 0, []
    for rel in live_set_files(repo):
        path = os.path.join(repo, rel)
        if not os.path.isfile(path):
            continue
        with open(path, "rb") as handle:
            text = handle.read().decode("utf-8", errors="replace")
        hits += len(legacy_lines(text))
        problems.extend(unpaired_lines(rel, text))
    return hits, problems


def in_work_tree(repo=_REPO):
    """Whether the repo is a git work tree (the clean-room container copies it without .git)."""
    proc = subprocess.run(["git", "-C", repo, "rev-parse", "--is-inside-work-tree"],
                          capture_output=True, text=True, check=False)
    return proc.returncode == 0 and proc.stdout.strip() == "true"


class TestLiveSet(unittest.TestCase):
    def setUp(self):
        if not in_work_tree():
            self.skipTest("not a git work tree: tracked files unknown")

    def test_every_legacy_line_names_codebase_memory_mcp(self):
        _hits, problems = scan_live_set()
        self.assertEqual([], problems, "lines lack codebase-memory-mcp:\n" + "\n".join(problems))

    def test_scan_is_not_vacuous(self):
        hits, _problems = scan_live_set()
        self.assertGreater(hits, 0)
        files = live_set_files()
        for known in ("AGENTS.md", "tools/setup.py", "tests/test_code_index_live_set.py"):
            self.assertIn(known, files)
        self.assertFalse(any(rel.startswith(".planning/") for rel in files))


class TestCheckerReportsSyntheticLines(unittest.TestCase):
    def test_an_unpaired_line_is_reported(self):
        text = f"Run the {_LEGACY} index step.\nRun the {_REPLACEMENT} index step.\n"
        self.assertEqual(unpaired_lines("docs/x.md", text),
                         [f"docs/x.md:1: Run the {_LEGACY} index step."])

    def test_the_check_is_case_insensitive_both_ways(self):
        mixed = "Code" + "Graph"
        text = f"Use {mixed} here.\nUse Codebase-Memory-MCP here.\n"
        self.assertEqual(unpaired_lines("docs/x.md", text), [f"docs/x.md:1: Use {mixed} here."])


if __name__ == "__main__":
    unittest.main()
