"""Engine tracer and report tests for ai-kit-commit-fold, on temp git repos (plan 29-01)."""

import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from tests import fold_fixtures
from tests.fold_fixtures import git_env, isolated_fold, make_repo, run_git, write_checkpoint

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skills" / "ai-kit-commit-fold" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import fold_engine
import fold_group
from fold_engine import Commit, FoldError

CANDIDATES = [
    {"id": "t1", "title": "Alpha feature", "files": ["a.py", "tests/test_a.py"]},
    {"id": "t2", "title": "Beta feature", "files": ["b.py", "tests/test_b.py"]},
]
ALICE = ("Alice Example", "alice@example.com")
TWO = [
    ({"a.py": b"a\n"}, "feat: add a", ALICE),
    ({"tests/test_a.py": b"test a\n"}, "test: cover a", None),
    ({"b.py": b"b\n"}, "feat: add b", None),
    ({"tests/test_b.py": b"test b\n"}, "test: cover b", None),
]
REORDERED = [TWO[2], TWO[3], TWO[0], TWO[1]]
WITH_DOCS = [*TWO, ({".planning/STATE.md": b"state\n"}, "docs: note state", None)]
HEX12 = r"[0-9a-f]{12}"


def checkpoint_fields(base, end, tip, docs=()):
    return {"schema": 1, "unit": "29-01", "ref": "refs/heads/plan", "base": base, "end": end,
            "tip": tip, "base_branch": "main", "candidates": CANDIDATES,
            "docs_paths": list(docs)}


class TestFoldTracer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="ai-kit-p29-")
        cls.addClassCleanup(shutil.rmtree, cls.tmp, ignore_errors=True)
        cls.env = git_env(os.path.join(cls.tmp, "home"))
        patcher = mock.patch.dict(os.environ, cls.env)
        patcher.start()
        cls.addClassCleanup(patcher.stop)
        cls.two = cls._build("two", TWO)
        cls.reordered = cls._build("reordered", REORDERED)
        cls.docs = cls._build("docs", WITH_DOCS)

    @classmethod
    def _build(cls, name, specs):
        """A repo on main with branch plan holding one commit per spec: (repo, base, shas)."""
        repo = make_repo(os.path.join(cls.tmp, name), cls.env)
        base = run_git(repo, cls.env, "rev-parse", "main").strip()
        run_git(repo, cls.env, "checkout", "-q", "-b", "plan")
        shas = [fold_fixtures.commit(repo, cls.env, files, message, author)
                for files, message, author in specs]
        return repo, base, shas

    def _git(self, repo, *args):
        return run_git(repo, self.env, *args).strip()

    def _changed(self, repo, sha):
        return set(self._git(repo, "show", "--name-only", "--format=", sha).split())

    def _fold(self, fixture, end=None, docs=()):
        source, base, shas = fixture
        copy = pathlib.Path(tempfile.mkdtemp(dir=self.tmp)) / "repo"
        shutil.copytree(source, copy)
        cp = fold_engine.load_checkpoint(
            checkpoint_fields(base, end or shas[-1], shas[-1], docs))
        return copy, base, shas, fold_engine.fold(copy, cp, fold_group.group_features, "inline")

    def test_two_features_fold_into_two_commits(self):
        copy, base, shas, result = self._fold(self.two)
        self.assertEqual(result.outcome, "folded", msg=result.reason)
        self.assertEqual(self._git(copy, "rev-list", "--count", f"{base}..plan"), "2")
        first, second = self._git(copy, "rev-list", "--reverse", f"{base}..plan").split()
        self.assertEqual(self._changed(copy, first), {"a.py", "tests/test_a.py"})
        self.assertEqual(self._changed(copy, second), {"b.py", "tests/test_b.py"})
        self.assertEqual(self._git(copy, "rev-parse", "plan^{tree}"),
                         self._git(copy, "rev-parse", f"{shas[-1]}^{{tree}}"))
        tag = f"ai-kit-fold/29-01/{shas[-1][:12]}"
        self.assertEqual(self._git(copy, "rev-parse", f"{tag}^{{commit}}"), shas[-1])
        self.assertEqual(self._git(copy, "status", "--porcelain", "--untracked-files=no"), "")

    def test_first_feature_commit_keeps_author_and_trailer(self):
        copy, base, _shas, result = self._fold(self.two)
        self.assertEqual(result.outcome, "folded", msg=result.reason)
        first = self._git(copy, "rev-list", "--reverse", f"{base}..plan").split()[0]
        self.assertEqual(self._git(copy, "log", "-1", "--format=%an <%ae>", first),
                         "Alice Example <alice@example.com>")
        self.assertEqual(self._git(copy, "log", "-1", "--format=%cn", first),
                         "Fixture Committer")
        message = self._git(copy, "log", "-1", "--format=%B", first)
        self.assertIn("feat(29-01): Alpha feature", message)
        self.assertIn("feat: add a", message)
        self.assertIn("test: cover a", message)
        self.assertTrue(message.endswith("Ai-Kit-Fold: 29-01"), msg=message)

    def test_first_feature_commit_comes_first(self):
        copy, base, _shas, result = self._fold(self.reordered)
        self.assertEqual(result.outcome, "folded", msg=result.reason)
        first, second = self._git(copy, "rev-list", "--reverse", f"{base}..plan").split()
        self.assertEqual(self._changed(copy, first), {"b.py", "tests/test_b.py"})
        self.assertEqual(self._changed(copy, second), {"a.py", "tests/test_a.py"})

    def test_docs_path_lands_in_last_commit(self):
        copy, base, shas, result = self._fold(self.docs, docs=[".planning/"])
        self.assertEqual(result.outcome, "folded", msg=result.reason)
        self.assertEqual(result.after, 2)
        self.assertEqual(self._git(copy, "rev-list", "--count", f"{base}..plan"), "2")
        last = self._git(copy, "rev-parse", "plan")
        self.assertEqual(self._changed(copy, last),
                         {"b.py", "tests/test_b.py", ".planning/STATE.md"})
        self.assertEqual(self._git(copy, "rev-parse", "plan^{tree}"),
                         self._git(copy, "rev-parse", f"{shas[-1]}^{{tree}}"))

    def test_end_before_tip_refuses_without_moving_the_ref(self):
        copy, _base, shas, result = self._fold(self.two, end=self.two[2][1])
        self.assertEqual(result.outcome, "refused")
        self.assertEqual(result.reason, "tree_mismatch")
        self.assertEqual(self._git(copy, "rev-parse", "plan"), shas[-1])
        self.assertEqual(self._git(copy, "tag", "--list", "ai-kit-fold/*"), "")

    def test_moved_branch_refuses_without_touching_the_ref(self):
        source, base, shas = self.two
        copy = pathlib.Path(tempfile.mkdtemp(dir=self.tmp)) / "repo"
        shutil.copytree(source, copy)
        run_git(copy, self.env, "update-ref", "refs/heads/plan", shas[0])
        cp = fold_engine.load_checkpoint(checkpoint_fields(base, shas[-1], shas[-1]))
        result = fold_engine.fold(copy, cp, fold_group.group_features, "inline")
        self.assertEqual(result.reason, "branch_moved")
        self.assertEqual(self._git(copy, "rev-parse", "plan"), shas[0])
        self.assertEqual(self._git(copy, "tag", "--list", "ai-kit-fold/*"), "")

    def test_cli_prints_the_five_line_report(self):
        source, base, shas = self.two
        root = pathlib.Path(tempfile.mkdtemp(dir=self.tmp))
        copy = root / "repo"
        shutil.copytree(source, copy)
        fold_py = isolated_fold(root)
        checkpoint = write_checkpoint(root / "cp.json",
                                      **checkpoint_fields(base, shas[-1], shas[-1]))
        proc = subprocess.run(
            [sys.executable, str(fold_py), "fold", str(checkpoint), "--repo", str(copy)],
            capture_output=True, text=True, env=self.env, check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertEqual(proc.stderr, "")
        lines = proc.stdout.splitlines()
        self.assertEqual(len(lines), 5, msg=proc.stdout)
        self.assertEqual(lines[0], "fold 29-01: refs/heads/plan")
        self.assertEqual(lines[1], "commits: 4 -> 2 (grouping: rules)")
        self.assertRegex(lines[2], rf"^tree: equal {HEX12}$")
        self.assertRegex(lines[3], rf"^tag: ai-kit-fold/29-01/{HEX12}$")
        self.assertEqual(lines[4], "outcome: 29-01 folded (inline)")

    def test_stdin_checkpoint_folds(self):
        source, base, shas = self.two
        root = pathlib.Path(tempfile.mkdtemp(dir=self.tmp))
        copy = root / "repo"
        shutil.copytree(source, copy)
        fold_py = isolated_fold(root)
        payload = checkpoint_fields(base, shas[-1], shas[-1])
        proc = subprocess.run(
            [sys.executable, str(fold_py), "fold", "-", "--repo", str(copy)],
            input=json.dumps(payload), capture_output=True, text=True,
            env=self.env, check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertEqual(proc.stdout.splitlines()[-1], "outcome: 29-01 folded (inline)")

    def test_unreadable_input_exits_2_with_one_stderr_line(self):
        root = pathlib.Path(tempfile.mkdtemp(dir=self.tmp))
        fold_py = isolated_fold(root)
        bad = root / "bad.json"
        bad.write_text("{not json", encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(fold_py), "fold", str(bad), "--repo", str(root)],
            capture_output=True, text=True, env=self.env, check=False,
        )
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(proc.stdout, "")
        self.assertEqual(len(proc.stderr.splitlines()), 1, msg=proc.stderr)


class TestCheckpointShape(unittest.TestCase):
    def _raw(self, **changes):
        fields = checkpoint_fields("a" * 40, "b" * 40, "b" * 40)
        fields.update(changes)
        return fields

    def test_end_defaults_to_tip(self):
        fields = self._raw()
        del fields["end"]
        self.assertEqual(fold_engine.load_checkpoint(fields).end, "b" * 40)

    def test_unknown_keys_are_ignored(self):
        cp = fold_engine.load_checkpoint(self._raw(range="a..b", future_field=1))
        self.assertEqual(cp.unit, "29-01")

    def test_bad_sha_is_refused(self):
        with self.assertRaises(FoldError) as caught:
            fold_engine.load_checkpoint(self._raw(base="xyz"))
        self.assertEqual(caught.exception.reason, "bad_checkpoint")

    def test_bool_schema_is_refused(self):
        with self.assertRaises(FoldError) as caught:
            fold_engine.load_checkpoint(self._raw(schema=True))
        self.assertEqual(caught.exception.reason, "bad_checkpoint")

    def test_unmatched_commits_form_one_feature_titled_with_unit(self):
        commits = [
            Commit("1" * 40, (), "x", b"x\n", ("n", "e", "0 +0000"), ("zz.txt",)),
            Commit("2" * 40, ("1" * 40,), "y", b"y\n", ("n", "e", "0 +0000"), ("yy.txt",)),
        ]
        cp = fold_engine.load_checkpoint(self._raw(candidates=[]))
        features, source, note = fold_group.rule_features(
            commits, cp, frozenset({"zz.txt", "yy.txt"}))
        self.assertEqual(source, "rules")
        self.assertTrue(note)
        self.assertEqual(len(features), 1)
        self.assertEqual(features[0].title, "29-01")
        self.assertEqual(features[0].paths, frozenset({"zz.txt", "yy.txt"}))
        self.assertEqual(features[0].commits, ("1" * 40, "2" * 40))


def report_shape_ok(text):
    """True for the fixed report: five plain-text lines in order, with well-formed fields."""
    if re.search(r"[\x00-\x09\x0b-\x1f\x7f]", text):
        return False
    lines = text.split("\n")
    if len(lines) != 5:
        return False
    prefixes = ("fold ", "commits: ", "tree: ", "tag: ", "outcome: ")
    if not all(line.startswith(prefix) for line, prefix in zip(lines, prefixes, strict=True)):
        return False
    return bool(
        re.fullmatch(r"commits: \d+ -> \d+.*", lines[1])
        and len(lines[1]) - len("commits: ") <= 200
        and re.fullmatch(r"tree: (equal [0-9a-f]{12}|not checked)", lines[2])
        and re.fullmatch(r"tag: (none|ai-kit-fold/[A-Za-z0-9._-]+/[0-9a-f]{12})", lines[3])
        and re.fullmatch(r"outcome: \S+ .+ \((inline|subagent)\)", lines[4])
    )


class TestReport(unittest.TestCase):
    def _result(self, **changes):
        fields = {"unit": "29-01", "ref": "refs/heads/plan", "before": 4, "after": 2,
                  "tree": "a" * 40, "tag": "ai-kit-fold/29-01/" + "b" * 12,
                  "outcome": "folded", "reason": "", "grouping": "rules", "note": "",
                  "mode": "inline"}
        fields.update(changes)
        return fold_engine.Result(**fields)

    def test_every_outcome_and_reason_renders_the_five_line_report(self):
        refusals = [self._result(outcome="refused", reason=reason, tree="", tag="",
                                 grouping="", note="detail")
                    for reason in sorted(fold_engine.REASONS)]
        cases = [self._result(), self._result(outcome="nothing_to_fold", after=4, tree="",
                                              tag="", grouping=""), *refusals]
        self.assertEqual(len(refusals), 11)
        for result in cases:
            with self.subTest(outcome=result.outcome, reason=result.reason):
                self.assertTrue(report_shape_ok(fold_engine.render_report(result)))

    def test_checker_rejects_a_six_line_report_and_colour_codes(self):
        text = fold_engine.render_report(self._result())
        self.assertTrue(report_shape_ok(text))
        self.assertFalse(report_shape_ok(text + "\nextra line"))
        self.assertFalse(report_shape_ok(text.replace("folded", "\x1b[31mfolded\x1b[0m")))

    def test_refusal_outcome_names_unit_and_reason_side_by_side(self):
        text = fold_engine.render_report(self._result(
            outcome="refused", reason="tree_mismatch", tree="", tag="", grouping="",
            note="folded segment tree differs"))
        self.assertEqual(text.split("\n")[4], "outcome: 29-01 refused tree_mismatch (inline)")
        self.assertEqual(text.split("\n")[2], "tree: not checked")
        self.assertEqual(text.split("\n")[3], "tag: none")

    def test_nothing_to_fold_report(self):
        text = fold_engine.render_report(self._result(
            outcome="nothing_to_fold", before=1, after=1, tree="", tag="", grouping=""))
        self.assertEqual(text.split("\n")[1:], [
            "commits: 1 -> 1",
            "tree: not checked",
            "tag: none",
            "outcome: 29-01 nothing to fold (inline)",
        ])

    def test_long_or_control_note_stays_on_one_line(self):
        for note in ("x" * 500, "line one\nline two\x1b[31m tail"):
            with self.subTest(note=note[:12]):
                text = fold_engine.render_report(self._result(note=note))
                lines = text.split("\n")
                self.assertEqual(len(lines), 5)
                self.assertLessEqual(len(lines[1]) - len("commits: "), 200)
                self.assertNotIn("\x1b", text)
                self.assertNotIn("\n", lines[1])


if __name__ == "__main__":
    unittest.main()
