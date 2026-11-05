"""GSD and superpowers adapters for ai-kit-commit-fold: fixture projects, status and parsers."""

import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from tests.fold_fixtures import (
    PHASE_BRANCH,
    SP_PLAN,
    SP_PLAN_TEXT,
    SP_SPECS,
    _plan_files,
    commit,
    git_env,
    gsd_plan_commits,
    gsd_project,
    isolated_fold,
    make_repo,
    merge_no_ff,
    run_git,
    superpowers_project,
)
from tests.test_ai_kit_commit_fold import write_fake_jev
from tests.test_jev_fast_decision import closed_port_url

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skills" / "ai-kit-commit-fold" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import fold_adapters
from fold_engine import Candidate

HEX12 = r"[0-9a-f]{12}"
FEATURE_A = ["a.py", "tests/test_a.py"]
FEATURE_B = ["b.py", "tests/test_b.py"]


def assert_two_feature_fold(case, repo, base, env):
    """Two features in first-commit order, each holding exactly its code and test paths
    (planning docs excluded). Runs on the GSD fixture and the superpowers fixture alike."""
    shas = run_git(repo, env, "rev-list", "--reverse", f"{base}..HEAD").split()
    case.assertEqual(len(shas), 2)
    features = []
    for sha in shas:
        paths = run_git(repo, env, "show", "--name-only", "--format=", sha).split()
        features.append(sorted(path for path in paths if not path.startswith(".planning/")))
    case.assertEqual(features, [sorted(FEATURE_A), sorted(FEATURE_B)])


def merge_scoped_fixture(root, env, side_specs, merge_subject):
    """Plan 07-01 with a merge-back between its first and second commit; the merged side
    commits are `side_specs`. Returns the repo."""
    repo = make_repo(root, env)
    run_git(repo, env, "checkout", "-q", "-b", PHASE_BRANCH)
    commit(repo, env, _plan_files([{"plan": "01", "stems": ("a", "b")}]),
           "docs(07): create phase plan")
    specs = gsd_plan_commits("01", ("a", "b"))
    commit(repo, env, *specs[0][:2])
    run_git(repo, env, "checkout", "-q", "-b", "side-y", PHASE_BRANCH)
    for files, message, author in side_specs:
        commit(repo, env, files, message, author)
    run_git(repo, env, "checkout", "-q", PHASE_BRANCH)
    merge_no_ff(repo, env, "side-y", merge_subject)
    for files, message, author in specs[1:]:
        commit(repo, env, files, message, author)
    return repo


class CliCase(unittest.TestCase):
    """Builds shared fixture repos once per class and runs the copied CLI on per-test copies."""

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

    def copy_of(self, source):
        """A fresh copy of a class-built repo, under its own root that also holds the skill copy."""
        root = pathlib.Path(tempfile.mkdtemp(dir=self.tmp))
        shutil.copytree(source, root / "repo")
        return root, root / "repo"

    def run_cli(self, root, repo, *args):
        fold_py = pathlib.Path(root) / "skills" / "ai-kit-commit-fold" / "scripts" / "fold.py"
        if not fold_py.exists():
            fold_py = isolated_fold(root)
        return subprocess.run(
            [sys.executable, str(fold_py), *args, "--repo", str(repo)],
            capture_output=True, text=True, env=self.env, check=False,
        )


class TestGsdAdapter(CliCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.seq1 = gsd_project(os.path.join(cls.tmp, "seq1"), cls.env, "sequential",
                               [{"plan": "01", "stems": ("a", "b")}])
        cls.seq3 = gsd_project(os.path.join(cls.tmp, "seq3"), cls.env, "sequential", [
            {"plan": "01", "stems": ("a", "b")},
            {"plan": "02", "stems": ("c", "d")},
            {"plan": "03", "stems": ("e", "f"), "summary": False},
        ])
        cls.wt = gsd_project(os.path.join(cls.tmp, "wt"), cls.env, "worktree", [
            {"plan": "01", "stems": ("a", "b")},
            {"plan": "02", "stems": ("c", "d")},
        ])
        cls.stray = gsd_project(os.path.join(cls.tmp, "stray"), cls.env, "sequential",
                                [{"plan": "01", "stems": ("a", "b")}],
                                stray=(2, {"c.py": b"c\n"}, "feat(07-02): add c"))
        cls.merge_other = merge_scoped_fixture(
            os.path.join(cls.tmp, "merge-other"), cls.env,
            [({"c.py": b"c\n"}, "feat(07-02): add c", None)],
            "chore: merge executor worktree (worktree-agent-y)")
        cls.merge_unscoped = merge_scoped_fixture(
            os.path.join(cls.tmp, "merge-unscoped"), cls.env,
            [({"c.py": b"c\n"}, "chore: tidy", None)],
            "chore: merge executor worktree (worktree-agent-y)")

    def _tree(self, repo, ref):
        return self.git(repo, "rev-parse", f"{ref}^{{tree}}")

    def test_sequential_plan_folds_into_two_commits(self):
        root, repo = self.copy_of(self.seq1)
        plan_base = self.git(repo, "rev-parse", "HEAD~5")
        tip_tree = self._tree(repo, "HEAD")
        proc = self.run_cli(root, repo, "gsd", "--phase", "7")
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        lines = proc.stdout.splitlines()
        self.assertEqual(len(lines), 5, msg=proc.stdout)
        self.assertEqual(lines[0], f"fold 07-01: refs/heads/{PHASE_BRANCH}")
        self.assertEqual(lines[1], "commits: 5 -> 2 (grouping: rules)")
        self.assertRegex(lines[2], rf"^tree: equal {HEX12}$")
        self.assertRegex(lines[3], rf"^tag: ai-kit-fold/07-01/{HEX12}$")
        self.assertEqual(lines[4], "outcome: 07-01 folded (inline)")
        self.assertEqual(self.git(repo, "rev-parse", "HEAD~2"), plan_base)
        self.assertEqual(self.git(repo, "rev-parse", "HEAD^{tree}"), tip_tree)
        assert_two_feature_fold(self, repo, plan_base, self.env)
        summary_paths = self.git(repo, "show", "--name-only", "--format=", "HEAD")
        self.assertIn(".planning/phases/07-demo/07-01-SUMMARY.md", summary_paths)
        self.assertIn(".planning/STATE.md", summary_paths)

    def test_worktree_plans_keep_each_segment_tree_and_the_tracking_commit(self):
        root, repo = self.copy_of(self.wt)
        merges = self.git(repo, "rev-list", "--merges", "--reverse", "HEAD").split()
        self.assertEqual(len(merges), 2)
        merge_trees = [self._tree(repo, merge) for merge in merges]
        tip_tree = self._tree(repo, "HEAD")
        proc = self.run_cli(root, repo, "gsd", "--phase", "7")
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertEqual(len(proc.stdout.splitlines()), 10, msg=proc.stdout)
        self.assertEqual(self.git(repo, "rev-list", "--merges", "HEAD"), "")
        self.assertEqual(self.git(repo, "log", "-1", "--format=%s"),
                         "docs(phase-07): update tracking after wave 1")
        self.assertEqual(self._tree(repo, "HEAD"), tip_tree)
        chain = self.git(repo, "rev-list", "--reverse", "--first-parent", "HEAD").split()
        self.assertEqual(self._tree(repo, chain[-4]), merge_trees[0])
        self.assertEqual(self._tree(repo, chain[-2]), merge_trees[1])

    def test_two_plans_fold_in_plan_order_and_the_unfinished_plan_stays(self):
        root, repo = self.copy_of(self.seq3)
        proc = self.run_cli(root, repo, "gsd", "--phase", "7")
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        lines = proc.stdout.splitlines()
        self.assertEqual(len(lines), 10, msg=proc.stdout)
        self.assertTrue(lines[0].startswith("fold 07-01:"))
        self.assertTrue(lines[5].startswith("fold 07-02:"))
        tags = self.git(repo, "tag", "--list", "ai-kit-fold/*").splitlines()
        self.assertEqual(len(tags), 2)
        self.assertRegex(tags[0], rf"^ai-kit-fold/07-01/{HEX12}$")
        self.assertRegex(tags[1], rf"^ai-kit-fold/07-02/{HEX12}$")
        subjects = self.git(repo, "log", "--format=%s", "--reverse", "HEAD").splitlines()
        self.assertEqual(subjects[-4:], ["feat(07-03): add e", "test(07-03): test e",
                                         "feat(07-03): add f", "test(07-03): test f"])
        self.assertFalse(any(s.startswith("docs(07-03)") for s in subjects))

    def test_second_run_reports_nothing_to_fold_and_moves_nothing(self):
        root, repo = self.copy_of(self.seq1)
        self.run_cli(root, repo, "gsd", "--phase", "7")
        head = self.git(repo, "rev-parse", "HEAD")
        proc = self.run_cli(root, repo, "gsd", "--phase", "7")
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertEqual(proc.stdout.splitlines(), [
            f"fold phase-07: refs/heads/{PHASE_BRANCH}",
            "commits: 0 -> 0",
            "tree: not checked",
            "tag: none",
            "outcome: phase-07 nothing to fold (inline)",
        ])
        self.assertEqual(self.git(repo, "rev-parse", "HEAD"), head)
        self.assertEqual(len(self.git(repo, "tag", "--list", "ai-kit-fold/*").splitlines()), 1)

    def test_commit_of_another_plan_inside_the_run_refuses(self):
        root, repo = self.copy_of(self.stray)
        head = self.git(repo, "rev-parse", "HEAD")
        proc = self.run_cli(root, repo, "gsd", "--phase", "7")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("outcome: 07-01 refused plan_not_contiguous (inline)", proc.stdout)
        self.assertEqual(self.git(repo, "rev-parse", "HEAD"), head)
        self.assertEqual(self.git(repo, "status", "--porcelain"), "")
        self.assertEqual(self.git(repo, "tag", "--list", "ai-kit-fold/*"), "")

    def test_merge_back_naming_another_plan_refuses(self):
        root, repo = self.copy_of(self.merge_other)
        head = self.git(repo, "rev-parse", "HEAD")
        proc = self.run_cli(root, repo, "gsd", "--phase", "7")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("refused plan_not_contiguous", proc.stdout)
        self.assertEqual(self.git(repo, "rev-parse", "HEAD"), head)
        self.assertEqual(self.git(repo, "tag", "--list", "ai-kit-fold/*"), "")

    def test_merge_back_without_plan_scope_refuses(self):
        root, repo = self.copy_of(self.merge_unscoped)
        head = self.git(repo, "rev-parse", "HEAD")
        proc = self.run_cli(root, repo, "gsd", "--phase", "7")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("refused plan_not_contiguous", proc.stdout)
        self.assertEqual(self.git(repo, "rev-parse", "HEAD"), head)
        self.assertEqual(self.git(repo, "status", "--porcelain"), "")

    def test_status_lists_each_plan_before_and_after_and_writes_nothing(self):
        root, repo = self.copy_of(self.seq3)
        head = self.git(repo, "rev-parse", "HEAD")
        before = self.run_cli(root, repo, "status", "--phase", "7")
        self.assertEqual(before.returncode, 0)
        self.assertEqual(before.stdout.splitlines(), [
            "07-01: unfolded (5 commits)", "07-02: unfolded (5 commits)", "07-03: unfinished"])
        self.assertEqual(self.git(repo, "rev-parse", "HEAD"), head)
        self.run_cli(root, repo, "gsd", "--phase", "7")
        after = self.run_cli(root, repo, "status", "--phase", "7")
        self.assertEqual(after.returncode, 0)
        self.assertEqual(after.stdout.splitlines(),
                         ["07-01: folded", "07-02: folded", "07-03: unfinished"])

    def test_dirty_tree_refusal_leaves_the_plan_unfolded(self):
        root, repo = self.copy_of(self.seq1)
        (repo / "base.txt").write_text("changed\n", encoding="utf-8")
        proc = self.run_cli(root, repo, "gsd", "--phase", "7")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("refused dirty_tree", proc.stdout)
        status = self.run_cli(root, repo, "status", "--phase", "7")
        self.assertEqual(status.stdout.splitlines(), ["07-01: unfolded (5 commits)"])


class TestParsers(unittest.TestCase):
    def test_gsd_tasks_keep_each_task_with_files_in_order(self):
        text = """<tasks>
<task type="auto" tdd="true">
  <name>Task 1: Add the engine</name>
  <files>engine.py, tests/test_engine.py (new)</files>
</task>
<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 2: Check the output</name>
</task>
<task type="auto">
  <name>Task 3: Wire the CLI</name>
  <files>`fold.py`, `tests/test_fold.py`</files>
</task>
</tasks>"""
        self.assertEqual(fold_adapters.parse_gsd_tasks(text), (
            Candidate("t1", "Add the engine", ("engine.py", "tests/test_engine.py")),
            Candidate("t2", "Wire the CLI", ("fold.py", "tests/test_fold.py")),
        ))

    def test_padded_phase_keeps_the_decimal_suffix(self):
        cases = {"7": "07", "2.1": "02.1", "29.1": "29.1", "29": "29"}
        for phase, padded in cases.items():
            with self.subTest(phase=phase):
                self.assertEqual(fold_adapters.padded_phase(phase), padded)


class TestSuperpowersAdapter(CliCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.sp, cls.pre_plan, _ = superpowers_project(os.path.join(cls.tmp, "sp"), cls.env)

    def test_plan_file_tasks_become_candidates(self):
        self.assertEqual(fold_adapters.parse_superpowers_tasks(SP_PLAN_TEXT), (
            Candidate("t1", "Feature A", ("a.py", "tests/test_a.py")),
            Candidate("t2", "Feature B", ("b.py", "tests/test_b.py")),
        ))

    def test_two_feature_plan_folds_and_keeps_the_pre_plan_commit(self):
        root, repo = self.copy_of(self.sp)
        tip_tree = self.git(repo, "rev-parse", "HEAD^{tree}")
        proc = self.run_cli(root, repo, "superpowers", "--plan", SP_PLAN, "--base", self.pre_plan)
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        lines = proc.stdout.splitlines()
        self.assertEqual(len(lines), 5, msg=proc.stdout)
        self.assertEqual(lines[1], "commits: 4 -> 2 (grouping: rules)")
        self.assertRegex(lines[3], rf"^tag: ai-kit-fold/2026-11-04-demo/{HEX12}$")
        self.assertEqual(lines[4], "outcome: 2026-11-04-demo folded (inline)")
        self.assertEqual(self.git(repo, "rev-parse", "HEAD~2"), self.pre_plan)
        self.assertEqual(self.git(repo, "rev-parse", "HEAD^{tree}"), tip_tree)
        assert_two_feature_fold(self, repo, self.pre_plan, self.env)

    def test_without_base_the_base_is_the_merge_base_with_main(self):
        _, repo = self.copy_of(self.sp)
        checkpoint = fold_adapters.superpowers_checkpoint(str(repo), SP_PLAN)
        self.assertEqual(checkpoint.base, self.git(repo, "merge-base", "HEAD", "main"))
        self.assertEqual(checkpoint.end, checkpoint.tip)
        self.assertEqual(checkpoint.unit, "2026-11-04-demo")

    def test_single_commit_after_base_is_nothing_to_fold(self):
        root = pathlib.Path(tempfile.mkdtemp(dir=self.tmp))
        repo, pre_plan, shas = superpowers_project(root, self.env, specs=SP_SPECS[:1])
        proc = self.run_cli(root, repo, "superpowers", "--plan", SP_PLAN, "--base", pre_plan)
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertEqual(proc.stdout.splitlines()[-1],
                         "outcome: 2026-11-04-demo nothing to fold (inline)")
        self.assertEqual(self.git(repo, "rev-parse", "HEAD"), shas[0])
        self.assertEqual(self.git(repo, "tag", "--list", "ai-kit-fold/*"), "")

    def test_detached_head_refuses(self):
        root, repo = self.copy_of(self.sp)
        self.git(repo, "checkout", "-q", "--detach")
        proc = self.run_cli(root, repo, "superpowers", "--plan", SP_PLAN, "--base", self.pre_plan)
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(proc.stdout.splitlines()[-1],
                         "outcome: 2026-11-04-demo refused detached_head (inline)")


# The fake jev answers each commit's subject with the feature's candidate id (t1 or t2).
JEV_TABLE_GSD = {"feat(07-01): add a": "t1", "test(07-01): test a": "t1",
                 "feat(07-01): add b": "t2", "test(07-01): test b": "t2"}
JEV_TABLE_SUPERPOWERS = {"feat: add a": "t1", "test: cover a": "t1",
                         "feat: add b": "t2", "test: cover b": "t2"}


def _install_real_jev(root):
    shutil.copytree(ROOT / "skills" / "jev-fast-decision", root / "skills" / "jev-fast-decision")


def _install_fake_jev(table):
    return lambda root: write_fake_jev(root / "skills", table, root / "calls.log")


class TestAdapterJev(CliCase):
    """SPEC R7 on both framework fixtures: each adapter form reaches the grouping seam. With no
    backend the rules keep the two features and the note names jev; with a faked answer the
    grouping is jev and the fake logs one call per commit that touches code."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.gsd = gsd_project(os.path.join(cls.tmp, "jev-gsd"), cls.env, "sequential",
                              [{"plan": "01", "stems": ("a", "b")}])
        cls.sp, cls.pre_plan, _ = superpowers_project(os.path.join(cls.tmp, "jev-sp"), cls.env)

    def fold_copy(self, source, install, args):
        """Run one adapter form on a fresh copy of `source`. `install(root)` places a jev client
        beside the copied fold skill, or nothing. HOME, XDG and the host config dirs point into
        the copy's temp root, so the only jev this run can find is the one installed here."""
        root, repo = self.copy_of(source)
        fold_py = isolated_fold(root)
        install(root)
        env = dict(self.env, HOME=str(root / "home"), XDG_CONFIG_HOME=str(root / "xdg"),
                   CLAUDE_CONFIG_DIR=str(root / "claude"), CURSOR_CONFIG_DIR=str(root / "cursor"),
                   PI_CODING_AGENT_DIR=str(root / "pi"), JEV_LAYA_URL=closed_port_url())
        proc = subprocess.run([sys.executable, str(fold_py), *args, "--repo", str(repo)],
                              capture_output=True, text=True, env=env, check=False)
        return proc, repo, root

    def gsd_base(self, repo):
        """The GSD plan's base: the phase plan commit that sits below the plan's first commit."""
        return self.git(repo, "rev-list", "-1", "--grep=create phase plan", "HEAD")

    def test_gsd_form_with_no_backend_keeps_the_rules_and_names_jev(self):
        proc, repo, _root = self.fold_copy(self.gsd, _install_real_jev,
                                           ["gsd", "--phase", "7"])
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertIn("grouping: rules", proc.stdout.splitlines()[1])
        self.assertIn("jev: no answer", proc.stdout.splitlines()[1])
        assert_two_feature_fold(self, repo, self.gsd_base(repo), self.env)

    def test_gsd_form_with_a_faked_answer_groups_by_jev_once_per_commit(self):
        proc, repo, root = self.fold_copy(self.gsd, _install_fake_jev(JEV_TABLE_GSD),
                                          ["gsd", "--phase", "7"])
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertIn("grouping: jev", proc.stdout.splitlines()[1])
        assert_two_feature_fold(self, repo, self.gsd_base(repo), self.env)
        calls = (root / "calls.log").read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(calls), 4)

    def test_superpowers_form_with_no_backend_keeps_the_rules_and_names_jev(self):
        proc, repo, _root = self.fold_copy(
            self.sp, _install_real_jev,
            ["superpowers", "--plan", SP_PLAN, "--base", self.pre_plan])
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertIn("grouping: rules", proc.stdout.splitlines()[1])
        self.assertIn("jev: no answer", proc.stdout.splitlines()[1])
        assert_two_feature_fold(self, repo, self.pre_plan, self.env)

    def test_superpowers_form_with_a_faked_answer_groups_by_jev_once_per_commit(self):
        proc, repo, root = self.fold_copy(
            self.sp, _install_fake_jev(JEV_TABLE_SUPERPOWERS),
            ["superpowers", "--plan", SP_PLAN, "--base", self.pre_plan])
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertIn("grouping: jev", proc.stdout.splitlines()[1])
        assert_two_feature_fold(self, repo, self.pre_plan, self.env)
        calls = (root / "calls.log").read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(calls), 4)


if __name__ == "__main__":
    unittest.main()
