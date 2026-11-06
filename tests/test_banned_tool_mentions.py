"""No tracked file names rtk outside the exemptions below (SPEC R7, D-06, D-07).

The scan reads `git ls-files` from the repo root this module resolves itself, whole
word and case-insensitive. Exemptions are history, or files that read rtk data already
stored on the owner's machine without using rtk. Each carries its reason.
"""

import re
import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PATTERN = re.compile(r"\brtk\b", re.IGNORECASE)
USAGE_INVITES = re.compile(r"\binstall rtk\b|\brtk init\b|`rtk [a-z][\w-]*", re.IGNORECASE)
NUL_SNIFF_BYTES = 8192
NOT_A_WORK_TREE = "not a git work tree: tracked files unknown"

EXEMPTIONS = (
    (".planning/", "history: phase records and milestone archives"),
    ("docs/prds/", "history: PRDs written before rtk was dropped"),
    ("docs/superpowers/", "history: superpowers plans and specs"),
    ("tests/test_banned_tool_mentions.py", "this test names the pattern"),
    ("skills/ai-kit-usage-metrics/", "reads rtk history already stored; does not use rtk"),
    (
        "tests/test_ai_kit_usage_metrics.py",
        "tests the reader of rtk history already stored; does not use rtk",
    ),
)


def is_exempt(path):
    return any(path.startswith(prefix) for prefix, _reason in EXEMPTIONS)


def banned_mentions(paths, reader):
    """Return `path:line` for each non-exempt line naming rtk. `reader(path)` gives bytes."""
    hits = []
    for path in paths:
        if is_exempt(path):
            continue
        try:
            data = reader(path)
        except FileNotFoundError:
            # git ls-files lists a path the working tree no longer has: skip it.
            continue
        if b"\0" in data[:NUL_SNIFF_BYTES]:
            continue
        text = data.decode("utf-8", errors="replace")
        for number, line in enumerate(text.splitlines(), start=1):
            if PATTERN.search(line):
                hits.append(f"{path}:{number}")
    return hits


def usage_metrics_invites_rtk(text):
    """True when skill text tells the agent to install, initialise or run rtk."""
    return USAGE_INVITES.search(text) is not None


def in_work_tree():
    proc = subprocess.run(
        ["git", "-C", str(REPO), "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode == 0 and proc.stdout.strip() == "true"


def tracked_files():
    out = subprocess.run(
        ["git", "-C", str(REPO), "ls-files", "-z"],
        capture_output=True,
        check=True,
    ).stdout
    return [path for path in out.decode("utf-8", errors="replace").split("\0") if path]


def read_repo_file(path):
    return (REPO / path).read_bytes()


class TestBannedToolMentions(unittest.TestCase):
    def setUp(self):
        if not in_work_tree():
            self.skipTest(NOT_A_WORK_TREE)

    def test_tracked_tree_names_no_rtk_outside_exemptions(self):
        self.assertEqual(banned_mentions(tracked_files(), read_repo_file), [])

    def test_usage_metrics_skill_does_not_invite_rtk(self):
        skill = (REPO / "skills" / "ai-kit-usage-metrics" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertFalse(usage_metrics_invites_rtk(skill))


class TestBannedToolMentionsNonVacuity(unittest.TestCase):
    @staticmethod
    def _reader(files):
        return lambda path: files[path]

    def test_tracked_hit_is_reported_with_its_line(self):
        hits = banned_mentions(["src/x.py"], self._reader({"src/x.py": b"use RTK here\n"}))
        self.assertEqual(hits, ["src/x.py:1"])

    def test_whole_word_only(self):
        hits = banned_mentions(["src/y.py"], self._reader({"src/y.py": b"artkit\n"}))
        self.assertEqual(hits, [])

    def test_exempt_prefixes_are_not_reported(self):
        paths = [".planning/a.md", "docs/prds/p.md", "skills/ai-kit-usage-metrics/k.py"]
        hits = banned_mentions(paths, self._reader({path: b"rtk\n" for path in paths}))
        self.assertEqual(hits, [])

    def test_archived_fixtures_are_not_exempt(self):
        path = "tests/fixtures/archived/z.md"
        hits = banned_mentions([path], self._reader({path: b"rtk\n"}))
        self.assertEqual(hits, [f"{path}:1"])

    def test_binary_file_is_skipped_by_nul_sniff(self):
        hits = banned_mentions(["bin/x"], self._reader({"bin/x": b"\x00\x01 rtk"}))
        self.assertEqual(hits, [])

    def test_listed_but_missing_file_is_skipped(self):
        def gone(path):
            raise FileNotFoundError(path)

        self.assertEqual(banned_mentions(["gone.md"], gone), [])

    def test_invalid_utf8_around_rtk_still_hits(self):
        hits = banned_mentions(["a.md"], self._reader({"a.md": b"\xff rtk \xfe\n"}))
        self.assertEqual(hits, ["a.md:1"])

    def test_every_exemption_names_a_reason(self):
        self.assertEqual(len(EXEMPTIONS), 6)
        for prefix, reason in EXEMPTIONS:
            self.assertTrue(reason.strip(), prefix)

    def test_usage_metrics_patterns_catch_install_init_and_subcommand(self):
        for sample in ("run `rtk gain` first", "install rtk", "rtk init -g"):
            self.assertTrue(usage_metrics_invites_rtk(sample), sample)
        self.assertFalse(usage_metrics_invites_rtk("reads rtk history.db"))


if __name__ == "__main__":
    unittest.main()
