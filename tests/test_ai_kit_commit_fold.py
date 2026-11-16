"""Engine, guard, report and grouping tests for ai-kit-commit-fold on temp git repos."""

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
from tests.fold_fixtures import (
    git_env,
    isolated_fold,
    make_repo,
    merge_no_ff,
    run_git,
    set_ref,
    write_checkpoint,
)

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


def checkpoint_fields(base, end, tip, docs=(), **extra):
    fields = {"schema": 1, "unit": "29-01", "ref": "refs/heads/plan", "base": base, "end": end,
              "tip": tip, "base_branch": "main", "candidates": CANDIDATES,
              "docs_paths": list(docs)}
    fields.update(extra)
    return fields


def build_repo(parent, env, name, specs):
    """A repo on main with one base commit, then branch plan with one commit per spec.

    Returns (repo, base, shas).
    """
    repo = make_repo(os.path.join(parent, name), env)
    base = run_git(repo, env, "rev-parse", "main").strip()
    run_git(repo, env, "checkout", "-q", "-b", "plan")
    shas = [fold_fixtures.commit(repo, env, files, message, author)
            for files, message, author in specs]
    return repo, base, shas


def copy_repo(source, parent):
    """A fresh copy of a class-built repo, so each test folds its own."""
    copy = pathlib.Path(tempfile.mkdtemp(dir=parent)) / "repo"
    shutil.copytree(source, copy)
    return copy


FAKE_JEV_BODY = """
import json
import sys


def main():
    payload = sys.stdin.read()
    with open(LOG, "a", encoding="utf-8") as handle:
        handle.write(payload + "\\n")
    items = {}
    for item in json.loads(payload)["items"]:
        answer = next((value for key, value in TABLE.items() if key in item["context"]),
                      "own_reasoning")
        if answer == "own_reasoning":
            items[item["id"]] = {"decided_by": "own_reasoning"}
        else:
            column = {"choice": answer, "top": 0.9, "fallback": False, "forced": False,
                      "model": "fake-model"}
            items[item["id"]] = {"fake": column, "decided_by": "fake"}
    print(json.dumps({"advisory": True, "items": items, "order": list(items)}))


main()
"""


def write_fake_jev(skills_root, table, log_path):
    """Write a fake jev client under skills_root. It logs each stdin payload to log_path and
    answers each item with the table value of the first key (a commit-subject substring) that
    the item's context holds, else own_reasoning. Returns the entry point's path."""
    entry = pathlib.Path(skills_root) / "jev-fast-decision" / "scripts" / "jev_review.py"
    entry.parent.mkdir(parents=True, exist_ok=True)
    header = f"TABLE = {table!r}\nLOG = {str(log_path)!r}\n"
    entry.write_text(header + FAKE_JEV_BODY, encoding="utf-8")
    return str(entry)


class RepoCase(unittest.TestCase):
    """Builds shared repos once per class and gives each test a copy of them."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="ai-kit-p29-")
        cls.addClassCleanup(shutil.rmtree, cls.tmp, ignore_errors=True)
        cls.env = git_env(os.path.join(cls.tmp, "home"))
        patcher = mock.patch.dict(os.environ, cls.env)
        patcher.start()
        cls.addClassCleanup(patcher.stop)

    def git(self, repo, *args):
        return run_git(repo, self.env, *args).strip()

    def state(self, repo):
        """What a refusal must leave alone: the branch tip, the status and the backup tags."""
        return (self.git(repo, "rev-parse", "plan"), self.git(repo, "status", "--porcelain"),
                self.git(repo, "tag", "--list", "ai-kit-fold/*"))

    def fold(self, repo, **fields):
        cp = fold_engine.load_checkpoint(checkpoint_fields(**fields))
        return fold_engine.fold(repo, cp, fold_group.group_features, "inline")

    def one_byte_off(self, repo, path="a.py"):
        """Patch the blob that the segment takes for `path` to one changed byte (a wrong fold)."""
        blob = run_git(repo, self.env, "hash-object", "-w", "--stdin",
                       data=b"a changed\n").strip()
        real_entry = fold_engine._entry

        def patched(repo_, end, name):
            mode, sha = real_entry(repo_, end, name)
            return (mode, blob) if name == path else (mode, sha)

        return mock.patch.object(fold_engine, "_entry", side_effect=patched)


class TestFoldTracer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="ai-kit-p29-")
        cls.addClassCleanup(shutil.rmtree, cls.tmp, ignore_errors=True)
        cls.env = git_env(os.path.join(cls.tmp, "home"))
        patcher = mock.patch.dict(os.environ, cls.env)
        patcher.start()
        cls.addClassCleanup(patcher.stop)
        cls.two = build_repo(cls.tmp, cls.env, "two", TWO)
        cls.reordered = build_repo(cls.tmp, cls.env, "reordered", REORDERED)
        cls.docs = build_repo(cls.tmp, cls.env, "docs", WITH_DOCS)

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

    def test_end_before_tip_replays_the_later_commits(self):
        copy, base, shas, result = self._fold(self.two, end=self.two[2][1])
        self.assertEqual(result.outcome, "folded", msg=result.reason)
        self.assertEqual(self._git(copy, "rev-list", "--count", f"{base}..plan"), "3")
        self.assertEqual(self._git(copy, "rev-parse", "plan^{tree}"),
                         self._git(copy, "rev-parse", f"{shas[-1]}^{{tree}}"))
        self.assertEqual(self._git(copy, "log", "-1", "--format=%s", "plan"), "test: cover b")
        tag = f"ai-kit-fold/29-01/{shas[-1][:12]}"
        self.assertEqual(self._git(copy, "rev-parse", f"{tag}^{{commit}}"), shas[-1])

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


class TestFoldGuards(RepoCase):
    """Every refusal leaves the branch, the working tree and the backup tags unchanged."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.repo, cls.base, cls.shas = build_repo(cls.tmp, cls.env, "guards", TWO)
        cls.docs_repo, cls.docs_base, cls.docs_shas = build_repo(
            cls.tmp, cls.env, "docs-only", [({"docs/notes.md": b"n\n"}, "docs(07-01): note", None)])

    def _range(self, repo, **extra):
        return self.fold(repo, base=self.base, end=self.shas[-1], tip=self.shas[-1], **extra)

    def test_policy_missing_refuses_through_the_cli(self):
        copy = copy_repo(self.repo, self.tmp)
        root = pathlib.Path(tempfile.mkdtemp(dir=self.tmp))
        scripts = root / "skills" / "x" / "scripts"
        shutil.copytree(SCRIPTS, scripts)
        checkpoint = write_checkpoint(root / "cp.json",
                                      **checkpoint_fields(self.base, self.shas[-1], self.shas[-1]))
        before = self.state(copy)
        proc = subprocess.run(
            [sys.executable, str(scripts / "fold.py"), "fold", str(checkpoint),
             "--repo", str(copy)],
            capture_output=True, text=True, env=self.env, check=False,
        )
        self.assertEqual(proc.returncode, 1, msg=proc.stderr)
        self.assertEqual(proc.stdout.splitlines()[-1],
                         "outcome: 29-01 refused policy_missing (inline)")
        self.assertEqual(self.state(copy), before)

    def test_tracked_change_refuses_staged_or_not(self):
        for staged in (False, True):
            with self.subTest(staged=staged):
                copy = copy_repo(self.repo, self.tmp)
                (copy / "a.py").write_bytes(b"dirty\n")
                if staged:
                    self.git(copy, "add", "a.py")
                before = self.state(copy)
                result = self._range(copy)
                self.assertEqual((result.outcome, result.reason), ("refused", "dirty_tree"))
                self.assertEqual(self.state(copy), before)
                self.assertEqual((copy / "a.py").read_bytes(), b"dirty\n")

    def test_untracked_file_does_not_refuse(self):
        copy = copy_repo(self.repo, self.tmp)
        (copy / "notes.txt").write_bytes(b"scratch\n")
        result = self._range(copy)
        self.assertEqual(result.outcome, "folded", msg=result.reason)
        self.assertTrue((copy / "notes.txt").exists())

    def test_branch_not_at_tip_refuses(self):
        copy = copy_repo(self.repo, self.tmp)
        self.git(copy, "checkout", "-q", "--detach")
        set_ref(copy, self.env, "refs/heads/plan", self.shas[0])
        self.git(copy, "checkout", "-q", "plan")
        before = self.state(copy)
        result = self._range(copy)
        self.assertEqual(result.reason, "branch_moved")
        self.assertEqual(self.state(copy), before)

    def test_missing_base_branch_refuses(self):
        copy = copy_repo(self.repo, self.tmp)
        before = self.state(copy)
        result = self._range(copy, base_branch="trunk")
        self.assertEqual(result.reason, "no_base_branch")
        self.assertEqual(self.state(copy), before)

    def test_range_commit_on_local_base_branch_refuses(self):
        copy = copy_repo(self.repo, self.tmp)
        set_ref(copy, self.env, "refs/heads/main", self.shas[0])
        before = self.state(copy)
        result = self._range(copy)
        self.assertEqual(result.reason, "range_on_base_branch")
        self.assertEqual(self.state(copy), before)

    def test_range_commit_on_remote_base_branch_refuses(self):
        copy = copy_repo(self.repo, self.tmp)
        set_ref(copy, self.env, "refs/remotes/origin/main", self.shas[0])
        before = self.state(copy)
        result = self._range(copy)
        self.assertEqual(result.reason, "range_on_base_branch")
        self.assertEqual(self.state(copy), before)

    def test_range_commit_on_merged_branch_refuses(self):
        copy = copy_repo(self.repo, self.tmp)
        set_ref(copy, self.env, "refs/heads/wt-1", self.shas[1])
        before = self.state(copy)
        result = self._range(copy, merged_refs=["refs/heads/wt-1"])
        self.assertEqual(result.reason, "range_on_merged_branch")
        self.assertEqual(self.state(copy), before)

    def test_pushed_unmerged_range_folds(self):
        copy = copy_repo(self.repo, self.tmp)
        set_ref(copy, self.env, "refs/remotes/origin/plan", self.shas[1])
        result = self._range(copy)
        self.assertEqual(result.outcome, "folded", msg=result.reason)

    def test_base_not_an_ancestor_of_end_refuses(self):
        copy = copy_repo(self.repo, self.tmp)
        result = self.fold(copy, base=self.shas[2], end=self.shas[1], tip=self.shas[-1])
        self.assertEqual(result.reason, "bad_checkpoint")

    def test_end_off_the_first_parent_chain_refuses(self):
        copy = copy_repo(self.repo, self.tmp)
        self.git(copy, "checkout", "-q", "-b", "side", self.base)
        side = fold_fixtures.commit(copy, self.env, {"side.py": b"s\n"}, "feat: side")
        self.git(copy, "checkout", "-q", "plan")
        result = self.fold(copy, base=self.base, end=side, tip=self.shas[-1])
        self.assertEqual(result.reason, "bad_checkpoint")

    def test_one_byte_wrong_segment_refuses_with_tree_mismatch(self):
        copy = copy_repo(self.repo, self.tmp)
        before = self.state(copy)
        with self.one_byte_off(copy):
            result = self._range(copy)
        self.assertEqual(result.reason, "tree_mismatch")
        self.assertEqual(self.state(copy), before)
        self.assertEqual((copy / "a.py").read_bytes(), b"a\n")

    def test_branch_moved_before_the_swap_deletes_the_new_tag(self):
        copy = copy_repo(self.repo, self.tmp)

        def move(repo):
            set_ref(repo, self.env, "refs/heads/plan", self.shas[0])

        with mock.patch.object(fold_engine, "_before_swap", side_effect=move):
            result = self._range(copy)
        self.assertEqual(result.reason, "branch_moved")
        self.assertEqual(self.git(copy, "rev-parse", "plan"), self.shas[0])
        self.assertEqual(self.git(copy, "tag", "--list", "ai-kit-fold/*"), "")

    def test_reused_backup_tag_survives_a_moved_branch(self):
        copy = copy_repo(self.repo, self.tmp)
        tag = f"ai-kit-fold/29-01/{self.shas[-1][:12]}"
        self.git(copy, "tag", tag, self.shas[-1])

        def move(repo):
            set_ref(repo, self.env, "refs/heads/plan", self.shas[0])

        with mock.patch.object(fold_engine, "_before_swap", side_effect=move):
            result = self._range(copy)
        self.assertEqual(result.reason, "branch_moved")
        self.assertEqual(self.git(copy, "rev-parse", tag), self.shas[-1])

    def test_single_commit_range_is_nothing_to_fold(self):
        copy = copy_repo(self.repo, self.tmp)
        before = self.state(copy)
        result = self.fold(copy, base=self.shas[-2], end=self.shas[-1], tip=self.shas[-1])
        self.assertEqual(result.outcome, "nothing_to_fold")
        self.assertEqual(self.state(copy), before)

    def test_docs_only_range_is_nothing_to_fold(self):
        copy = copy_repo(self.docs_repo, self.tmp)
        tip = self.docs_shas[-1]
        result = self.fold(copy, base=self.docs_base, end=tip, tip=tip)
        self.assertEqual(result.outcome, "nothing_to_fold")
        self.assertEqual(self.git(copy, "tag", "--list", "ai-kit-fold/*"), "")


MERGE_SUBJECT = "chore: merge executor worktree ("
RAW_MESSAGE = "feat: añade ü\n\nlínea 2\n"


def _commit_obj(sha, paths):
    return Commit(sha, (), "feat: change", b"feat: change\n", ("n", "e", "0 +0000"),
                  tuple(paths))


class TestFoldMerges(RepoCase):
    """GSD's own merge-backs fold away; commits after end are replayed tree-identically."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.merge_repo, cls.merge_base, cls.merge_tip = cls._merge_repo()
        cls.track_repo, cls.track_base, cls.track_shas = cls._tracking_repo(
            "tracking", merge_back=False)
        cls.after_repo, cls.after_base, cls.after_shas = cls._tracking_repo(
            "merge-after", merge_back=True)

    @classmethod
    def _merge_repo(cls):
        """Plan: a.py, then a merge-back of wt-1 (b.py, tests/test_b.py) from base."""
        repo = make_repo(os.path.join(cls.tmp, "merge"), cls.env)
        base = run_git(repo, cls.env, "rev-parse", "main").strip()
        run_git(repo, cls.env, "checkout", "-q", "-b", "plan")
        fold_fixtures.commit(repo, cls.env, {"a.py": b"a\n"}, "feat: add a")
        run_git(repo, cls.env, "checkout", "-q", "-b", "wt-1", base)
        fold_fixtures.commit(repo, cls.env, {"b.py": b"b\n"}, "feat: add b")
        fold_fixtures.commit(repo, cls.env, {"tests/test_b.py": b"test b\n"}, "test: cover b")
        run_git(repo, cls.env, "checkout", "-q", "plan")
        return repo, base, merge_no_ff(repo, cls.env, "wt-1", MERGE_SUBJECT + "wt-1)")

    @classmethod
    def _tracking_repo(cls, name, merge_back):
        """Plan: a.py, b.py, then a tracking commit; with merge_back, a merge-back of wt-2 too."""
        repo = make_repo(os.path.join(cls.tmp, name), cls.env)
        base = run_git(repo, cls.env, "rev-parse", "main").strip()
        run_git(repo, cls.env, "checkout", "-q", "-b", "plan")
        first = fold_fixtures.commit(repo, cls.env, {"a.py": b"a\n"}, "feat: add a")
        second = fold_fixtures.commit(repo, cls.env, {"b.py": b"b\n"}, "feat: add b")
        tracking = fold_fixtures.commit(
            repo, cls.env, {".planning/STATE.md": b"state\n"},
            "docs(phase-7): update tracking after wave 1", ("Bob Example", "bob@example.com"))
        shas = [first, second, tracking]
        if not merge_back:
            return repo, base, shas
        run_git(repo, cls.env, "checkout", "-q", "-b", "wt-2", second)
        side = fold_fixtures.commit(repo, cls.env, {"x.py": b"x\n"}, "feat: add x")
        run_git(repo, cls.env, "checkout", "-q", "plan")
        merge = merge_no_ff(repo, cls.env, "wt-2", MERGE_SUBJECT + "wt-2)")
        return repo, base, [*shas, side, merge]

    def test_own_merge_back_folds_to_a_linear_history(self):
        copy = copy_repo(self.merge_repo, self.tmp)
        result = self.fold(copy, base=self.merge_base, end=self.merge_tip, tip=self.merge_tip,
                           own_merge_subjects=[MERGE_SUBJECT])
        self.assertEqual(result.outcome, "folded", msg=result.reason)
        self.assertEqual((result.before, result.after), (3, 2))
        self.assertEqual(self.git(copy, "rev-list", "--merges", f"{self.merge_base}..plan"), "")
        self.assertEqual(self.git(copy, "rev-list", "--count", f"{self.merge_base}..plan"), "2")
        self.assertEqual(self.git(copy, "rev-parse", "plan^{tree}"),
                         self.git(copy, "rev-parse", f"{self.merge_tip}^{{tree}}"))

    def test_foreign_merge_refuses_without_moving_the_branch(self):
        for subjects in ([], ["chore: merge other ("]):
            with self.subTest(own_merge_subjects=subjects):
                copy = copy_repo(self.merge_repo, self.tmp)
                before = self.state(copy)
                result = self.fold(copy, base=self.merge_base, end=self.merge_tip,
                                   tip=self.merge_tip, own_merge_subjects=subjects)
                self.assertEqual(result.reason, "foreign_merge")
                self.assertEqual(self.state(copy), before)

    def test_root_commit_in_the_range_refuses_instead_of_crashing(self):
        root = self.git(self.merge_repo, "rev-list", "--max-parents=0", "HEAD").split()[0]
        with self.assertRaises(FoldError) as caught:
            fold_engine._commit(self.merge_repo, root)
        self.assertEqual(caught.exception.reason, "foreign_merge")

    def test_tracking_commit_after_end_is_replayed_unchanged(self):
        copy = copy_repo(self.track_repo, self.tmp)
        _first, second, tracking = self.track_shas
        result = self.fold(copy, base=self.track_base, end=second, tip=tracking)
        self.assertEqual(result.outcome, "folded", msg=result.reason)
        self.assertEqual(result.after, 3)
        self.assertEqual(self.git(copy, "rev-parse", "plan^{tree}"),
                         self.git(copy, "rev-parse", f"{tracking}^{{tree}}"))
        self.assertEqual(self.git(copy, "rev-parse", "plan^^{tree}"),
                         self.git(copy, "rev-parse", f"{second}^{{tree}}"))
        self.assertEqual(self.git(copy, "log", "-1", "--format=%B", "plan"),
                         self.git(copy, "log", "-1", "--format=%B", tracking))
        self.assertEqual(self.git(copy, "log", "-1", "--format=%an <%ae>", "plan"),
                         "Bob Example <bob@example.com>")

    def test_merge_back_after_end_forking_inside_the_range_refuses(self):
        # its second parent would keep the unfolded range alive beside the folded one
        copy = copy_repo(self.after_repo, self.tmp)
        _first, second, _tracking, _side, merge = self.after_shas
        before = self.state(copy)
        result = self.fold(copy, base=self.after_base, end=second, tip=merge)
        self.assertEqual(result.reason, "foreign_merge")
        self.assertIn(f"merge {merge[:12]} after the range forks from inside it", result.note)
        self.assertEqual(self.state(copy), before)

    def test_bad_segment_with_tracking_commit_refused(self):
        copy = copy_repo(self.track_repo, self.tmp)
        _first, second, tracking = self.track_shas
        before = self.state(copy)
        with self.one_byte_off(copy):
            result = self.fold(copy, base=self.track_base, end=second, tip=tracking)
        self.assertEqual(result.reason, "tree_mismatch")
        self.assertEqual(self.state(copy), before)


class TestFoldGrouping(unittest.TestCase):
    """Rule grouping: shared paths and code-with-test pairs stay whole; unmatched commits place."""

    @staticmethod
    def _features(commits, candidates, docs=()):
        fields = checkpoint_fields("a" * 40, "b" * 40, "b" * 40, docs, candidates=candidates)
        cp = fold_engine.load_checkpoint(fields)
        changed = frozenset(path for commit in commits for path in commit.paths)
        return fold_group.rule_features(commits, cp, changed)

    def test_shared_changed_path_merges_the_features(self):
        candidates = [{"id": "t1", "title": "One", "files": ["a.py", "shared.py"]},
                      {"id": "t2", "title": "Two", "files": ["b.py", "shared.py"]}]
        commits = [_commit_obj("1" * 40, ["a.py", "shared.py"]),
                   _commit_obj("2" * 40, ["b.py", "shared.py"])]
        features, source, note = self._features(commits, candidates)
        self.assertEqual(source, "rules")
        self.assertEqual(note, "merged t1+t2: shared shared.py")
        self.assertEqual(len(features), 1)
        self.assertEqual(features[0].title, "One; Two")
        self.assertEqual(features[0].paths, frozenset({"a.py", "b.py", "shared.py"}))

    def test_code_file_stays_with_its_test(self):
        candidates = [{"id": "t1", "title": "One", "files": ["x.py"]},
                      {"id": "t2", "title": "Two", "files": ["tests/test_x.py"]}]
        commits = [_commit_obj("1" * 40, ["x.py"]), _commit_obj("2" * 40, ["tests/test_x.py"])]
        features, _source, note = self._features(commits, candidates)
        self.assertEqual(note, "merged t1+t2: x.py with its test")
        self.assertEqual(len(features), 1)

    def test_unmatched_commit_joins_the_feature_holding_its_path(self):
        candidates = [{"id": "t1", "title": "One", "files": ["a.py"]},
                      {"id": "t2", "title": "Two", "files": ["b.py"]}]
        commits = [_commit_obj("1" * 40, ["a.py", "util.py"]),
                   _commit_obj("2" * 40, ["b.py"]),
                   _commit_obj("3" * 40, ["util.py"])]
        features, _source, note = self._features(commits, candidates)
        self.assertEqual(note, "")
        self.assertEqual(len(features), 2)
        self.assertEqual(features[0].commits, ("1" * 40, "3" * 40))
        self.assertEqual(features[1].commits, ("2" * 40,))


class TestFoldEncoding(RepoCase):
    """Multi-line, non-ASCII messages and paths survive the fold byte for byte."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.repo, cls.base, cls.shas = build_repo(cls.tmp, cls.env, "encoding", [
            ({"a.py": b"a\n"}, "feat: add a", None),
            ({"b.py": b"b\n", "docs/ñandú.md": b"nota\n"}, RAW_MESSAGE, None),
        ])

    def test_raw_message_and_non_ascii_path_survive(self):
        copy = copy_repo(self.repo, self.tmp)
        result = self.fold(copy, base=self.base, end=self.shas[-1], tip=self.shas[-1])
        self.assertEqual(result.outcome, "folded", msg=result.reason)
        last = self.git(copy, "rev-parse", "plan")
        self.assertIn(RAW_MESSAGE, run_git(copy, self.env, "cat-file", "commit", last))
        names = run_git(copy, self.env, "ls-tree", "-r", "-z", "--name-only", "plan").split("\0")
        self.assertIn("docs/ñandú.md", names)


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

    def test_merged_refs_must_be_full_ref_names(self):
        for bad in (["--output=/dev/null"], ["plan"]):
            with self.subTest(merged_refs=bad), self.assertRaises(FoldError) as caught:
                fold_engine.load_checkpoint(self._raw(merged_refs=bad))
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
        self.assertEqual(len(refusals), 13)
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


JEV_TWO_FOLDED = [{"a.py", "tests/test_a.py"}, {"b.py", "tests/test_b.py"}]
JEV_TABLE = {"feat: add a": "t1", "test: cover a": "t1",
             "feat: add b": "t2", "test: cover b": "t2"}
JEV_ITEMS = [("feat: add a", ["a.py"]), ("test: cover a", ["tests/test_a.py"]),
             ("feat: add b", ["b.py"]), ("test: cover b", ["tests/test_b.py"])]
MARKER = "MARKER_IN_FILE_BODY"
OLD_CLIENT = (
    "import sys\n"
    "sys.stderr.write(\"jev_review.py: error: argument command: invalid choice: 'ladder'\\n\")\n"
    "sys.exit(2)\n"
)
OLD_NOTE = ("jev: entry point missing; update jev-fast-decision "
            "(re-run the ai-kit installer)")


def _no_jev(root):
    """Leave the copied fold skill alone: no jev-fast-decision beside it."""


def _real_jev(root):
    shutil.copytree(ROOT / "skills" / "jev-fast-decision", root / "skills" / "jev-fast-decision")


def _fake_jev(table):
    return lambda root: write_fake_jev(root / "skills", table, root / "calls.log")


def _old_jev(root):
    entry = root / "skills" / "jev-fast-decision" / "scripts" / "jev_review.py"
    entry.parent.mkdir(parents=True)
    entry.write_text(OLD_CLIENT, encoding="utf-8")


class TestJevGrouping(RepoCase):
    """jev proposes the feature grouping through its ladder entry point; the rules decide
    whenever jev is missing, silent, old or wrong."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.two = build_repo(cls.tmp, cls.env, "jev-two", TWO)
        cls.marked = build_repo(cls.tmp, cls.env, "jev-marked", [
            ({"a.py": f"{MARKER} = 1\n".encode()}, "feat: add a", ALICE),
            *TWO[1:],
        ])
        cls.keyed = build_repo(cls.tmp, cls.env, "jev-keyed", [
            ({"a.py": b"a\n"}, "feat: add a sk-" + "x" * 30, ALICE),
            *TWO[1:],
        ])

    def _fold_cli(self, install, fixture=None):
        """fold.py on a copy of the fixture, from a fold skill copy whose skills dir `install`
        prepared. Returns (process, folded path sets, the temp root)."""
        source, base, shas = fixture or self.two
        root = pathlib.Path(tempfile.mkdtemp(dir=self.tmp))
        copy = root / "repo"
        shutil.copytree(source, copy)
        fold_py = isolated_fold(root)
        install(root)
        checkpoint = write_checkpoint(root / "cp.json",
                                      **checkpoint_fields(base, shas[-1], shas[-1]))
        proc = subprocess.run(
            [sys.executable, str(fold_py), "fold", str(checkpoint), "--repo", str(copy)],
            capture_output=True, text=True, env=self.env, check=False,
        )
        folded = [set(self.git(copy, "show", "--name-only", "--format=", sha).split())
                  for sha in self.git(copy, "rev-list", "--reverse", f"{base}..plan").split()]
        return proc, folded, root

    def test_no_jev_installed_the_rules_decide(self):
        proc, folded, _root = self._fold_cli(_no_jev)
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertEqual(proc.stdout.splitlines()[1], "commits: 4 -> 2 (grouping: rules)")
        self.assertEqual(folded, JEV_TWO_FOLDED)

    def test_real_jev_without_a_backend_the_rules_decide(self):
        proc, folded, _root = self._fold_cli(_real_jev)
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertEqual(proc.stdout.splitlines()[1],
                         "commits: 4 -> 2 (grouping: rules; jev: no answer for c0)")
        self.assertEqual(folded, JEV_TWO_FOLDED)

    def test_jev_answer_decides_the_grouping(self):
        proc, folded, _root = self._fold_cli(_fake_jev(JEV_TABLE))
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertEqual(proc.stdout.splitlines()[1], "commits: 4 -> 2 (grouping: jev)")
        self.assertEqual(folded, JEV_TWO_FOLDED)

    def test_wrong_split_is_rejected_and_the_rules_decide(self):
        table = {**JEV_TABLE, "test: cover a": "t2"}
        proc, folded, _root = self._fold_cli(_fake_jev(table))
        self.assertEqual(proc.stdout.splitlines()[1],
                         "commits: 4 -> 2 (grouping: rules; "
                         "jev rejected: splits a.py from its test)")
        self.assertEqual(folded, JEV_TWO_FOLDED)

    def test_partial_answer_is_rejected_and_the_rules_decide(self):
        table = {"feat: add a": "t1", "test: cover a": "t1", "feat: add b": "t2"}
        proc, folded, _root = self._fold_cli(_fake_jev(table))
        self.assertEqual(proc.stdout.splitlines()[1],
                         "commits: 4 -> 2 (grouping: rules; jev: no answer for c3)")
        self.assertEqual(folded, JEV_TWO_FOLDED)

    def test_old_client_without_the_ladder_entry_is_named(self):
        proc, folded, _root = self._fold_cli(_old_jev)
        self.assertEqual(proc.stdout.splitlines()[1],
                         f"commits: 4 -> 2 (grouping: rules; {OLD_NOTE})")
        self.assertEqual(folded, JEV_TWO_FOLDED)

    def test_a_timed_out_call_is_named_as_a_timeout(self):
        def slow(argv, **_kwargs):
            raise subprocess.TimeoutExpired(argv, 1)

        cp = fold_engine.load_checkpoint(checkpoint_fields("a" * 40, "b" * 40, "b" * 40))
        commits = [_commit_obj("1" * 40, ["a.py"])]
        _picks, _assignment, note = fold_group._ask_commits("jev.py", commits, cp, {}, slow)
        self.assertEqual(note, "jev: timeout for c0")

    def test_partition_check_names_each_refusal(self):
        cp = fold_engine.load_checkpoint(checkpoint_fields("a" * 40, "b" * 40, "b" * 40))
        commits = [_commit_obj("1" * 40, ["a.py"]), _commit_obj("2" * 40, ["tests/test_a.py"]),
                   _commit_obj("3" * 40, ["b.py"]), _commit_obj("4" * 40, ["tests/test_b.py"])]
        changed = frozenset(path for commit in commits for path in commit.paths)
        one, two, three, four = (commit.sha for commit in commits)
        cases = {
            None: [(one, "t1"), (two, "t1"), (three, "t2"), (four, "t2")],
            "commit placed twice": [(one, "t1"), (one, "t1"), (three, "t2"), (four, "t2")],
            "commit left out": [(one, "t1"), (two, "t1"), (three, "t2")],
            "commit not in range": [(one, "t1"), (two, "t1"), (three, "t2"), (four, "t2"),
                                    ("9" * 40, "t2")],
            "splits a.py from its test": [(one, "t1"), (two, "t2"), (three, "t2"), (four, "t2")],
        }
        for expected, assignment in cases.items():
            with self.subTest(expected=expected):
                self.assertEqual(
                    fold_group.validate_partition(assignment, commits, cp, changed), expected)

    def test_each_item_carries_only_subject_paths_and_titles(self):
        proc, _folded, root = self._fold_cli(_fake_jev(JEV_TABLE), fixture=self.marked)
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        raw = (root / "calls.log").read_text(encoding="utf-8")
        self.assertNotIn(MARKER, raw)
        calls = [json.loads(line) for line in raw.splitlines()]
        self.assertEqual(len(calls), len(JEV_ITEMS))
        for call, (subject, paths) in zip(calls, JEV_ITEMS, strict=True):
            (item,) = call["items"]
            self.assertEqual(set(item), {"id", "type", "instructions", "context", "criteria"})
            self.assertEqual(item["criteria"], {"t1": "Alpha feature", "t2": "Beta feature"})
            self.assertEqual(
                item["context"],
                f"Commit subject: {subject}. Paths: {', '.join(paths)}. "
                "Features: t1 = Alpha feature; t2 = Beta feature")

    def test_key_shaped_subject_is_rejected_by_the_ladder_guard(self):
        subject = "feat: add a sk-" + "x" * 30
        commit = Commit("1" * 40, (), subject, subject.encode(), ("n", "e", "0 +0000"),
                        ("a.py",))
        cp = fold_engine.load_checkpoint(checkpoint_fields("a" * 40, "b" * 40, "b" * 40))
        item = fold_group.jev_item(commit, cp.candidates, 0)
        entry = ROOT / "skills" / "jev-fast-decision" / "scripts" / "jev_review.py"
        proc = subprocess.run(
            [sys.executable, str(entry), "ladder"], input=json.dumps({"items": [item]}),
            capture_output=True, text=True, env=self.env, check=False,
        )
        self.assertEqual(json.loads(proc.stdout)["items"]["c0"]["reason"],
                         "secret_pattern_context")
        proc, folded, _root = self._fold_cli(_real_jev, fixture=self.keyed)
        self.assertEqual(proc.stdout.splitlines()[1],
                         "commits: 4 -> 2 (grouping: rules; jev: no answer for c0)")
        self.assertEqual(folded, JEV_TWO_FOLDED)


class TestFoldSkillText(unittest.TestCase):
    """SPEC R1 (the skill points to the policy and never restates it) and R6 (dispatch to a
    subagent, with a named inline fallback), pinned in the skill text itself."""

    SKILL_TEXT = SCRIPTS.parent / "SKILL.md"
    POLICY_TEXT = SCRIPTS.parent / "references" / "folding-policy.md"

    @classmethod
    def setUpClass(cls):
        cls.skill = cls.SKILL_TEXT.read_text(encoding="utf-8")
        cls.policy = cls.POLICY_TEXT.read_text(encoding="utf-8")

    @staticmethod
    def _points_to_policy(text):
        return "references/folding-policy.md" in text

    @staticmethod
    def _restated_lines(text, policy):
        lines = (line.strip() for line in policy.splitlines())
        return [line for line in lines if len(line) >= 40 and line in text]

    @staticmethod
    def _dispatches_with_inline_fallback(text):
        return "--mode subagent" in text and "--mode inline" in text

    def test_points_to_policy(self):
        self.assertTrue(self._points_to_policy(self.skill))
        # non-vacuity: the same text without the pointer fails the check
        self.assertFalse(self._points_to_policy(self.skill.replace("references/folding-policy.md",
                                                                   "the policy")))

    def test_does_not_restate_policy(self):
        self.assertEqual(self._restated_lines(self.skill, self.policy), [])
        # non-vacuity: one long policy line appended to the skill is found
        long_line = next(line.strip() for line in self.policy.splitlines()
                         if len(line.strip()) >= 40)
        self.assertEqual(self._restated_lines(self.skill + "\n" + long_line + "\n",
                                              self.policy), [long_line])

    def test_dispatches_subagent_with_inline_fallback(self):
        self.assertTrue(self._dispatches_with_inline_fallback(self.skill))
        # non-vacuity: the same text without the inline fallback fails the check
        self.assertFalse(self._dispatches_with_inline_fallback(
            self.skill.replace("--mode inline", "")))


if __name__ == "__main__":
    unittest.main()
