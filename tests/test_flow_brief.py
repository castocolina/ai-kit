"""The unit brief (plan 30-04 Task 2): explore names, capped whole-word mentions, worktree seeding.

Explore output is canned through a recording `run`, so no codegraph process runs; the repositories
are temporary git checkouts built with the git CLI.
"""

import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

_REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "skills" / "ai-kit-commit-fold" / "scripts"))

import flow_brief
import flow_index
import flow_record

from tests import index_fakes

_IDENT = ["-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid"]


def _git(repo, *args):
    proc = subprocess.run(["git", "-C", str(repo), *_IDENT, *args], capture_output=True,
                          text=True, check=True)
    return proc.stdout.strip()


def _write(repo, rel, text):
    path = pathlib.Path(repo) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _runner(rc, out):
    calls = []

    def run(argv, cwd, timeout=900):  # pylint: disable=unused-argument
        calls.append(argv)
        return rc, out, ""

    run.calls = calls
    return run


def _found(_name):
    return "/usr/bin/codegraph"


def _missing(_name):
    return None


def _facts(**fields):
    return flow_brief.BriefFacts(unit="B", branch="b", head="0" * 12, point="plan",
                                 written="now", **fields)


class ExploreNamesTests(unittest.TestCase):
    def test_parses_names_in_any_kind_and_labels_the_dropped_tail(self):
        out = ("**Exploration: pkg/alpha.py**\n"
               "**`pkg/alpha.py`** — alpha_one(function), Gamma(class), helper(method), "
               "x(calls), y(instantiates), z(function), +2 more\n")
        run = _runner(0, out)
        names, label = flow_brief.explore_names("/repo", ["pkg/alpha.py"], run, _found)
        self.assertEqual(names, ["Gamma", "alpha_one", "helper", "x", "y", "z"])
        self.assertIn("partial: 2 more not listed by codegraph", label)
        self.assertEqual(run.calls, [["codegraph", "explore", "pkg/alpha.py"]])

    def test_no_codegraph_cli_makes_no_call(self):
        run = _runner(0, "")
        names, label = flow_brief.explore_names("/repo", ["pkg/alpha.py"], run, _missing)
        self.assertEqual(names, [])
        self.assertEqual(label, "file names only: the codegraph CLI is not installed")
        self.assertEqual(run.calls, [])

    def test_zero_names_from_a_zero_exit_is_labeled(self):
        names, label = flow_brief.explore_names("/repo", ["a.py"], _runner(0, "no headers here"),
                                                _found)
        self.assertEqual(names, [])
        self.assertEqual(label, "file names only: codegraph explore listed no names")

    def test_exploration_line_alone_is_never_a_file_header(self):
        names, label = flow_brief.explore_names("/repo", ["a.py"],
                                                _runner(0, "**Exploration: alpha_one**\n"), _found)
        self.assertEqual(names, [])
        self.assertEqual(label, "file names only: codegraph explore listed no names")

    def test_failed_call_is_labeled_with_its_exit(self):
        names, label = flow_brief.explore_names("/repo", ["a.py"], _runner(3, ""), _found)
        self.assertEqual(names, [])
        self.assertEqual(label, "file names only: codegraph explore failed, exit 3")


class RepoBriefTests(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp(prefix="ai-kit-p30-"))
        self.repo = self.root / "repo"
        self.repo.mkdir()
        _git(self.repo, "init", "-q", "-b", "main")
        _write(self.repo, "base.txt", "base\n")
        _git(self.repo, "add", "base.txt")
        _git(self.repo, "commit", "-q", "-m", "base")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_mentions_are_whole_word_literal_and_skip_planning(self):
        _write(self.repo, "docs/a.md", "call _atomic_write_json() here\n")
        _write(self.repo, "docs/b.md", "call atomic_write() here\n")
        _write(self.repo, "docs/c.md", "the a.b pair\n")
        _write(self.repo, "docs/d.md", "the axb pair\n")
        _write(self.repo, ".planning/notes.md", "atomic_write again\n")
        _git(self.repo, "add", "docs")
        _git(self.repo, "add", "-f", ".planning/notes.md")
        _git(self.repo, "commit", "-q", "-m", "docs")
        found = flow_brief.mentions(self.repo, ["atomic_write", "a.b"])
        self.assertEqual(found, {"atomic_write": ["docs/b.md"], "a.b": ["docs/c.md"]})

    def test_cap_lists_ten_and_counts_eleven(self):
        for index in range(11):
            _write(self.repo, f"docs/d{index:02d}.md", "shared_name here\n")
        _git(self.repo, "add", "docs")
        _git(self.repo, "commit", "-q", "-m", "docs")
        paths = flow_brief.mentions(self.repo, ["shared_name"])["shared_name"]
        text = flow_brief.render(_facts(names=("shared_name",), names_label="x",
                                        mentions={"shared_name": paths}))
        self.assertIn("in 11 documents; first 10:", text)
        self.assertIn("`docs/d09.md`", text)
        self.assertNotIn("`docs/d10.md`", text)

    def test_exactly_ten_lists_all_ten(self):
        for index in range(10):
            _write(self.repo, f"docs/d{index:02d}.md", "shared_name here\n")
        _git(self.repo, "add", "docs")
        _git(self.repo, "commit", "-q", "-m", "docs")
        paths = flow_brief.mentions(self.repo, ["shared_name"])["shared_name"]
        text = flow_brief.render(_facts(names=("shared_name",), mentions={"shared_name": paths}))
        self.assertIn("`docs/d09.md`", text)
        self.assertNotIn("in 10 documents", text)

    def test_wording_never_says_describes_and_names_the_mention_rule(self):
        text = flow_brief.render(_facts(names=("alpha",), names_label="x"))
        self.assertNotIn("describes", text)
        self.assertNotIn("describes", flow_brief.NO_BRIEF)
        self.assertIn("mentions", text)
        self.assertIn("No tracked document outside `.planning/` mentions them.", text)

    def test_docs_only_range_says_nothing_to_explore(self):
        text = flow_brief.render(_facts(changed=(("A", "docs/x.md", None),
                                                 ("A", "config.toml", None))))
        self.assertIn("No code file changed in this range", text)
        self.assertIn("`docs/x.md`", text)

    def test_seed_copies_the_brief_from_a_worktree_at_the_same_head(self):
        flow_brief.write_brief(self.repo, "BRIEF-MARK\n")
        _git(self.repo, "worktree", "add", "-q", str(self.root / "wt1"), "-b", "wt-one")
        flow_brief.write_brief(self.root / "wt1", "BRIEF-MARK\n")
        _git(self.repo, "worktree", "add", "-q", str(self.root / "wt2"), "-b", "wt-two")
        notes = flow_brief.seed_worktree(self.root / "wt2")
        copied = (self.root / "wt2" / flow_brief.BRIEF_REL).read_text(encoding="utf-8")
        self.assertEqual(copied, "BRIEF-MARK\n")
        self.assertTrue(any(line.startswith("brief: copied from") for line in notes))

    def test_seed_writes_the_no_brief_file_when_no_worktree_shares_the_head(self):
        _git(self.repo, "worktree", "add", "-q", str(self.root / "wt1"), "-b", "wt-one")
        flow_brief.write_brief(self.root / "wt1", "OLD\n")
        _write(self.repo, "later.txt", "later\n")
        _git(self.repo, "add", "later.txt")
        _git(self.repo, "commit", "-q", "-m", "later")
        _git(self.repo, "worktree", "add", "-q", str(self.root / "wt2"), "-b", "wt-two")
        notes = flow_brief.seed_worktree(self.root / "wt2")
        text = (self.root / "wt2" / flow_brief.BRIEF_REL).read_text(encoding="utf-8")
        self.assertEqual(text, flow_brief.NO_BRIEF)
        self.assertTrue(any("wrote the no-brief file" in line for line in notes))

    def test_seed_hook_is_registered_once_and_ignored_by_git(self):
        hooks = [hook for hook in flow_index.SEED_HOOKS if hook is flow_brief.seed_worktree]
        self.assertEqual(len(hooks), 1)
        flow_brief.seed_worktree(self.repo)
        excluded = _git(self.repo, "check-ignore", "-v", ".aikit/brief/SKILL.md")
        self.assertIn(".aikit", excluded)

    def test_rename_and_non_ascii_names_are_listed_once_and_found_literally(self):
        body = "def f():\n" + "".join(f"    x{index} = {index}\n" for index in range(20))
        _write(self.repo, "pkg/viejo é.py", body)
        _write(self.repo, "docs/guía.md", "see `nuevo ñ.py` for details\n")
        _git(self.repo, "add", "-A")
        _git(self.repo, "commit", "-q", "-m", "add")
        base = _git(self.repo, "rev-parse", "HEAD")
        _git(self.repo, "mv", "pkg/viejo é.py", "pkg/nuevo ñ.py")
        _write(self.repo, "pkg/nuevo ñ.py", body + "    y = 1\n")  # similar enough to rename
        _git(self.repo, "add", "-A")
        _git(self.repo, "commit", "-q", "-m", "rename")
        end = _git(self.repo, "rev-parse", "HEAD")
        changed = flow_brief.changed_files(self.repo, base, end)
        self.assertEqual(changed, [("R", "pkg/nuevo ñ.py", "pkg/viejo é.py")])
        names, label, found = flow_brief.search(self.repo, changed, _runner(0, ""), _missing)
        self.assertIn("nuevo ñ.py", names)
        self.assertIn("viejo é.py", names)
        self.assertEqual(found["nuevo ñ.py"], ["docs/guía.md"])
        self.assertEqual(found["viejo é.py"], [])
        text = flow_brief.render(flow_brief.BriefFacts(
            unit="B", branch="b", head="0" * 12, point="plan", written="now",
            changed=tuple(changed), names=tuple(names), names_label=label, mentions=found))
        self.assertIn("- renamed `pkg/viejo é.py` -> `pkg/nuevo ñ.py`", text)
        self.assertIn("- `nuevo ñ.py`: `docs/guía.md`", text)

    def test_two_renders_at_one_head_differ_only_in_the_written_line(self):
        def render_at(stamp):
            return flow_brief.render(flow_brief.BriefFacts(
                unit="B", branch="b", head="0" * 12, point="plan", written=stamp,
                names=("alpha",), names_label="x"))

        first, second = render_at("2026-01-01T00:00:00Z"), render_at("2026-01-02T00:00:00Z")

        def without_written(text):
            return [line for line in text.splitlines() if not line.startswith("written:")]

        self.assertNotEqual(first, second)
        self.assertEqual(without_written(first), without_written(second))


class FakeExploreTests(unittest.TestCase):
    """Explore output from the codegraph fake (tests/index_fakes.py), not canned text."""

    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp(prefix="ai-kit-p30-"))
        self.addCleanup(shutil.rmtree, self.root, True)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        _git(self.repo, "init", "-q", "-b", "main")
        defs = "".join(f"def func_{index}():\n    return {index}\n" for index in range(8))
        _write(self.repo, "pkg/many.py", defs)
        self.bin = self.root / "bin"
        self.state = self.root / "state.json"
        self.state.write_text("{}", encoding="utf-8")
        log = self.root / "calls.log"
        index_fakes.write_index_fakes(self.bin, self.state, log)
        patch = mock.patch.dict(os.environ, {"PATH": index_fakes.tool_path(self.bin)})
        patch.start()
        self.addCleanup(patch.stop)

    def which(self, name):
        return os.path.join(self.bin, name)

    def test_file_with_eight_functions_lists_six_names_and_labels_the_tail(self):
        names, label = flow_brief.explore_names(str(self.repo), ["pkg/many.py"],
                                                flow_index._run_tool, self.which)
        self.assertEqual(names, [f"func_{index}" for index in range(6)])
        self.assertIn("partial: 2 more not listed by codegraph", label)

    def test_explore_text_without_names_is_labeled_as_file_names_only(self):
        index_fakes.set_state(self.state, explore_raw="no headers here")
        names, label = flow_brief.explore_names(str(self.repo), ["pkg/many.py"],
                                                flow_index._run_tool, self.which)
        self.assertEqual(names, [])
        self.assertEqual(label, "file names only: codegraph explore listed no names")


class DetachWithoutDrainTests(unittest.TestCase):
    """A new worktree holds its brief when `detach` returns; the drain is never run here."""

    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp(prefix="ai-kit-p30-"))
        self.addCleanup(shutil.rmtree, self.root, True)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        _git(self.repo, "init", "-q", "-b", "main")
        _write(self.repo, "base.txt", "base\n")
        _git(self.repo, "add", "base.txt")
        _git(self.repo, "commit", "-q", "-m", "base")
        self.worktree = self.root / "wt-new"
        _git(self.repo, "worktree", "add", "-q", "--detach", str(self.worktree))
        self.env = {"PRE_COMMIT_FROM_REF": "0" * 40}

    def test_brief_exists_before_the_runner_is_started_and_detach_returns_zero(self):
        seen = []

        def popen(argv, **kwargs):  # pylint: disable=unused-argument
            seen.append((self.worktree / flow_brief.BRIEF_REL).is_file())
            return mock.Mock(pid=0)

        rc = flow_index.detach(str(self.worktree), env=self.env, popen=popen)
        self.assertEqual(rc, 0)
        self.assertTrue((self.worktree / flow_brief.BRIEF_REL).is_file())
        self.assertEqual(seen, [True])

    def test_a_failing_seed_hook_is_logged_and_the_path_is_still_queued(self):
        def broken(top):  # pylint: disable=unused-argument
            raise OSError("disk full")

        with mock.patch.object(flow_index, "SEED_HOOKS", [broken, flow_brief.seed_worktree]):
            rc = flow_index.detach(str(self.worktree), env=self.env,
                                   popen=lambda argv, **kwargs: mock.Mock(pid=0))
        self.assertEqual(rc, 0)
        common = flow_record.common_dir(str(self.worktree))
        log = (common / flow_index.LOG_NAME).read_text(encoding="utf-8")
        self.assertIn("seed failed: disk full", log)
        self.assertIn("queued", log)
        self.assertTrue((self.worktree / flow_brief.BRIEF_REL).is_file())


if __name__ == "__main__":
    unittest.main()
