"""The unit brief (plan 30-04 Task 2): index names, capped whole-word mentions, worktree seeding.

Index answers are canned through a recording `run`, so no codebase-memory-mcp process runs; the
repositories are temporary git checkouts built with the git CLI.
"""

import json
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


def _tool_runner(answers):
    """Answer each call by its tool (argv[2]): one (rc, out) pair, or a list in call order."""
    calls = []
    queues = {tool: list(answer) if isinstance(answer, list) else [answer]
              for tool, answer in answers.items()}

    def run(argv, cwd, timeout=900):  # pylint: disable=unused-argument
        calls.append(argv)
        queue = queues.get(argv[2], [(2, "")])
        rc, out = queue.pop(0) if len(queue) > 1 else queue[0]
        return rc, out, ""

    run.calls = calls
    return run


def _projects(*rows, has_more=False):
    return json.dumps({"projects": [{"name": name, "root_path": root, "branch": "main"}
                                    for name, root in rows],
                       "total": len(rows), "offset": 0, "limit": 500, "returned": len(rows),
                       "has_more": has_more})


def _query(rows, has_more=False):
    return json.dumps({"columns": ["f.file_path", "f.name"], "rows": rows, "returned": len(rows),
                       "total": len(rows), "total_relation": "eq", "has_more": has_more,
                       "truncated": False})


def _found(_name):
    return "/usr/bin/codebase-memory-mcp"


def _missing(_name):
    return None


def _facts(**fields):
    return flow_brief.BriefFacts(unit="B", branch="b", head="0" * 12, point="plan",
                                 written="now", **fields)


CBM = flow_index.CBM
_NO_INDEX = "file names only: no codebase-memory-mcp index for this checkout"
_ALPHA_QUERY = ("MATCH (f) WHERE f.file_path IN ['pkg/alpha.py'] AND "
                "(f:Function OR f:Method OR f:Class) RETURN f.file_path, f.name")


class IndexNamesTests(unittest.TestCase):
    def test_names_come_from_the_checkouts_project_in_two_calls(self):
        run = _tool_runner({
            "list_projects": (0, _projects(("p-repo", "/repo"))),
            "query_graph": (0, _query([["pkg/alpha.py", "alpha_one"],
                                       ["pkg/alpha.py", "Gamma"], ["pkg/alpha.py", "helper"]])),
        })
        names, label = flow_brief.explore_names("/repo", ["pkg/alpha.py"], run, _found)
        self.assertEqual(names, ["Gamma", "alpha_one", "helper"])
        self.assertEqual(label, "symbol names from codebase-memory-mcp plus file names")
        self.assertEqual(run.calls, [
            [CBM, "cli", "list_projects", "--format", "json", "--limit", "500", "--offset", "0"],
            [CBM, "cli", "query_graph", "--project", "p-repo", "--format", "json",
             "--max-rows", "2000", "--offset", "0", "--query", _ALPHA_QUERY],
        ])

    def test_checkout_on_the_second_page_of_projects_is_found(self):
        page_one = _projects(*[(f"other-{i}", f"/nonexistent/p{i}") for i in range(500)],
                             has_more=True)
        run = _tool_runner({
            "list_projects": [(0, page_one), (0, _projects(("p-repo", "/repo")))],
            "query_graph": (0, _query([["pkg/alpha.py", "alpha_one"]])),
        })
        names, _label = flow_brief.explore_names("/repo", ["pkg/alpha.py"], run, _found)
        self.assertEqual(names, ["alpha_one"])
        self.assertEqual(run.calls[1][-4:], ["--limit", "500", "--offset", "500"])
        self.assertEqual(len(run.calls), 3)

    def test_a_page_with_more_and_no_rows_stops_the_search(self):
        run = _tool_runner({"list_projects": (0, _projects(has_more=True))})
        self.assertEqual(flow_brief.explore_names("/repo", ["a.py"], run, _found),
                         ([], _NO_INDEX))
        self.assertEqual(len(run.calls), 1)

    def test_query_pages_follow_next_offset_until_no_more(self):
        def page(names, **extra):
            data = json.loads(_query([["pkg/alpha.py", name] for name in names]))
            data.update(extra)
            return json.dumps(data)

        run = _tool_runner({
            "list_projects": (0, _projects(("p-repo", "/repo"))),
            "query_graph": [
                (0, page(["a1", "a2"], has_more=True, truncated=True, next_offset=2, total=3)),
                (0, page(["a3"], total=3)),
            ],
        })
        names, label = flow_brief.explore_names("/repo", ["pkg/alpha.py"], run, _found)
        self.assertEqual(names, ["a1", "a2", "a3"])
        self.assertEqual(label, "symbol names from codebase-memory-mcp plus file names")
        offsets = [call[call.index("--offset") + 1] for call in run.calls[1:]]
        self.assertEqual(offsets, ["0", "2"])

    def test_rows_past_the_cap_are_labeled_with_the_real_counts(self):
        rows = [["pkg/alpha.py", f"n{index}"] for index in range(flow_brief.MAX_QUERY_ROWS)]
        data = json.loads(_query(rows, has_more=True))
        data.update(total=5103, next_offset=len(rows))
        run = _tool_runner({
            "list_projects": (0, _projects(("p-repo", "/repo"))),
            "query_graph": (0, json.dumps(data)),
        })
        _names, label = flow_brief.explore_names("/repo", ["pkg/alpha.py"], run, _found)
        self.assertEqual(label, "symbol names from codebase-memory-mcp, partial: 2000 of "
                                "5103 rows; plus file names")
        self.assertEqual(len(run.calls), 2)

    def test_no_cli_makes_no_call(self):
        run = _tool_runner({})
        self.assertEqual(flow_brief.explore_names("/repo", ["pkg/alpha.py"], run, _missing),
                         ([], "file names only: the codebase-memory-mcp CLI is not installed"))
        self.assertEqual(run.calls, [])

    def test_no_project_for_this_checkout_is_one_list_call(self):
        run = _tool_runner({"list_projects": (0, _projects(("other", "/elsewhere")))})
        self.assertEqual(flow_brief.explore_names("/repo", ["a.py"], run, _found),
                         ([], _NO_INDEX))
        self.assertEqual(len(run.calls), 1)

    def test_list_projects_failure_or_unreadable_output_is_no_index(self):
        for answer in ((1, ""), (0, "not json"), (0, "[]")):
            run = _tool_runner({"list_projects": answer})
            self.assertEqual(flow_brief.explore_names("/repo", ["a.py"], run, _found),
                             ([], _NO_INDEX), answer)
            self.assertEqual(len(run.calls), 1, answer)

    def test_query_failure_is_labeled_with_its_exit(self):
        run = _tool_runner({
            "list_projects": (0, _projects(("p-repo", "/repo"))),
            "query_graph": (3, ""),
        })
        self.assertEqual(flow_brief.explore_names("/repo", ["a.py"], run, _found),
                         ([], "file names only: codebase-memory-mcp query_graph failed, exit 3"))

    def test_query_output_that_is_not_json_is_labeled(self):
        run = _tool_runner({
            "list_projects": (0, _projects(("p-repo", "/repo"))),
            "query_graph": (0, "not json"),
        })
        self.assertEqual(flow_brief.explore_names("/repo", ["a.py"], run, _found),
                         ([], "file names only: codebase-memory-mcp query_graph output unreadable"))

    def test_zero_rows_and_null_rows_both_list_no_names(self):
        for rows_text in (_query([]), json.dumps({"rows": None})):
            run = _tool_runner({
                "list_projects": (0, _projects(("p-repo", "/repo"))),
                "query_graph": (0, rows_text),
            })
            self.assertEqual(flow_brief.explore_names("/repo", ["a.py"], run, _found),
                             ([], "file names only: codebase-memory-mcp listed no names"))

    def test_cypher_quote_escapes_quotes_and_backslashes(self):
        self.assertEqual(flow_brief.cypher_quote("pkg/it's.py"), "'pkg/it\\'s.py'")
        self.assertEqual(flow_brief.cypher_quote("a\\b.py"), "'a\\\\b.py'")

    def test_a_path_with_a_quote_and_a_backslash_is_quoted_in_the_query(self):
        run = _tool_runner({
            "list_projects": (0, _projects(("p-repo", "/repo"))),
            "query_graph": (0, _query([])),
        })
        flow_brief.explore_names("/repo", ["pkg/it's\\x.py"], run, _found)
        query = run.calls[1][run.calls[1].index("--query") + 1]
        self.assertIn("IN ['pkg/it\\'s\\\\x.py']", query)


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


class FakeIndexTests(unittest.TestCase):
    """Index answers from the codebase-memory-mcp fake (tests/index_fakes.py), not canned text."""

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

    def names(self, paths):
        return flow_brief.explore_names(str(self.repo), paths, flow_index._run_tool, self.which)

    def test_file_with_eight_functions_lists_all_eight_names(self):
        names, label = self.names(["pkg/many.py"])
        self.assertEqual(names, [f"func_{index}" for index in range(8)])
        self.assertEqual(label, "symbol names from codebase-memory-mcp plus file names")

    def test_quoted_and_accented_file_name_is_found_literally(self):
        _write(self.repo, "pkg/it's é.py", "def quoted_one():\n    return 1\n")
        names, _label = self.names(["pkg/it's é.py"])
        self.assertEqual(names, ["quoted_one"])

    def test_output_budget_cut_is_paged_to_all_names(self):
        index_fakes.set_state(self.state, cbm_query_budget=3)
        names, label = self.names(["pkg/many.py"])
        self.assertEqual(names, [f"func_{index}" for index in range(8)])
        self.assertEqual(label, "symbol names from codebase-memory-mcp plus file names")

    def test_output_budget_cut_past_the_cap_is_labeled_partial(self):
        index_fakes.set_state(self.state, cbm_query_budget=3)
        with mock.patch.object(flow_brief, "MAX_QUERY_ROWS", 6):
            names, label = self.names(["pkg/many.py"])
        self.assertEqual(len(names), 6)
        self.assertEqual(label, "symbol names from codebase-memory-mcp, partial: 6 of 8 rows; "
                                "plus file names")

    def test_query_output_that_is_not_json_is_labeled(self):
        index_fakes.set_state(self.state, cbm_query_raw="not json")
        names, label = self.names(["pkg/many.py"])
        self.assertEqual(names, [])
        self.assertEqual(label,
                         "file names only: codebase-memory-mcp query_graph output unreadable")

    def test_no_project_is_labeled_as_no_index(self):
        index_fakes.set_state(self.state, cbm_projects=[])
        names, label = self.names(["pkg/many.py"])
        self.assertEqual(names, [])
        self.assertEqual(label, _NO_INDEX)

    def test_checkout_on_the_second_page_is_found_end_to_end(self):
        roots = [f"/nonexistent/p{index}" for index in range(501)]
        roots.append(os.path.realpath(self.repo))
        index_fakes.set_state(self.state, cbm_projects=roots)
        names, label = self.names(["pkg/many.py"])
        self.assertEqual(names, [f"func_{index}" for index in range(8)])
        self.assertEqual(label, "symbol names from codebase-memory-mcp plus file names")


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
