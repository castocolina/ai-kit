"""Stack reconciliation tests, part 2: the clean and refused cascade and the hotfix.

Split from tests/test_flow_stack.py by test class so the parts run in parallel; the shared
template fixture `_StackCase` stays there.
"""

import os
import pathlib
import subprocess
import sys
import unittest
from unittest import mock

_REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "skills" / "ai-kit-commit-fold" / "scripts"))
sys.path.insert(0, str(_REPO))

import flow_record
import flow_stack

from tests import fold_fixtures as f
from tests.test_flow_stack import BR_A, BR_B, BR_C, _StackCase


class TestCascadeClean(_StackCase):
    """A moved trunk or a refolded lower unit restacks the units above it, nothing else."""

    def test_trunk_move_cascades_every_unit_onto_the_new_trunk(self):
        self.build_stack()
        self.remote_commit("main", {"z.py": b"z\n"}, "feat: trunk moved")
        code, text = self.fold("restack")
        self.assertEqual(code, 0, text)
        self.assertIn("restacked: unit-a, unit-b, unit-c", text)
        new_main = self.remote_tip("main")
        self.assertEqual(self.count(new_main, BR_A), 1)
        self.assertEqual(self.count(BR_A, BR_B), 1)
        self.assertEqual(self.count(BR_B, BR_C), 1)
        self.assertEqual(self.entry("unit-a")["parent_tip"], new_main)
        self.assertEqual(self.entry("unit-b")["parent_tip"], self.rev(BR_A))
        self.assertEqual(self.entry("unit-c")["parent_tip"], self.rev(BR_B))
        for unit_id, branch in (("unit-a", BR_A), ("unit-b", BR_B), ("unit-c", BR_C)):
            self.assertEqual(self.entry(unit_id)["pushed"], self.rev(branch))
            self.assertEqual(self.remote_tip(branch), self.rev(branch))
        self.assertFalse(self.restack_file_exists())

    def test_an_empty_unit_at_the_boundary_moves_with_the_cascade(self):
        self.start_unit("unit-a", BR_A)
        self.start_unit("unit-b", BR_B)
        self.commit({"b.py": b"b\n"}, "feat: unit-b")
        self.remote_commit("main", {"z.py": b"z\n"}, "feat: trunk moved")
        code, text = self.fold("restack")
        self.assertEqual(code, 0, text)
        new_main = self.remote_tip("main")
        self.assertEqual(self.rev(BR_A), new_main)
        self.assertEqual(self.count(BR_A, BR_B), 1)
        self.assertEqual(self.entry("unit-a")["parent_tip"], new_main)
        self.assertEqual(self.entry("unit-b")["parent_tip"], new_main)
        self.assertEqual(self.entry("unit-b")["parent_tip"], self.rev(BR_A))
        code, text = self.fold("restack")
        self.assertIn("nothing to do", text)

    def test_restack_with_nothing_moved_changes_no_ref_and_pushes_nothing(self):
        self.build_stack()
        before = self.local_tips()
        remote_before = {b: self.remote_tip(b) for b in (BR_A, BR_B, BR_C)}
        code, text = self.fold("restack")
        self.assertEqual(code, 0, text)
        self.assertIn("nothing to do", text)
        self.assertEqual(self.local_tips(), before)
        self.assertEqual({b: self.remote_tip(b) for b in (BR_A, BR_B, BR_C)}, remote_before)

    def test_restack_continue_or_abort_without_a_pause_is_refused(self):
        self.build_stack()
        for flag in ("--continue", "--abort"):
            code, text = self.fold("restack", flag)
            self.assertEqual(code, 1, text)
            self.assertIn("restack_not_paused", text)

    def test_merge_commit_on_the_trunk_does_not_cascade(self):
        self.build_stack()
        f.merge_on_remote(self.dest, self.env, self.bare, BR_A, "main")
        before = self.local_tips()
        code, text = self.fold("restack")
        self.assertEqual(code, 0, text)
        self.assertIn("nothing to do", text)
        self.assertEqual(self.entry("unit-a")["state"], "merged")
        self.assertEqual(self.local_tips()[BR_B], before[BR_B])
        self.assertEqual(self.local_tips()[BR_C], before[BR_C])

    def test_refolded_lower_unit_cascades_only_the_units_above_it(self):
        self.start_unit("unit-a", BR_A)
        self.commit({"a.py": b"a\n"}, "feat: add a")
        self.commit({"tests/test_a.py": b"ta\n"}, "test: cover a")
        self.publish(BR_A)
        self.start_unit("unit-b", BR_B)
        self.commit({"b.py": b"b\n"}, "feat: add b")
        self.publish(BR_B)
        old_a = self.rev(BR_A)
        tree = self.rev(f"{old_a}^{{tree}}")
        folded_a = f.run_git(self.repo, self.env, "commit-tree", tree, "-p",
                             self.rev("main"), "-m", "feat: add a (folded)").strip()
        f.run_git(self.repo, self.env, "update-ref", f"refs/heads/{BR_A}", folded_a, old_a)
        with mock.patch.dict(os.environ, self.env):
            record = flow_record.read_record(self.repo)
            settings = flow_record.read_settings(self.repo)
            restacked = flow_stack.cascade(self.repo, settings, record,
                                           moved_unit="unit-a", old_tip=old_a)
        self.assertEqual(restacked, ["unit-b"])
        self.assertEqual(self.count(folded_a, BR_B), 1)
        self.assertEqual(self.remote_tip(BR_A), folded_a)
        self.assertEqual(self.remote_tip(BR_B), self.rev(BR_B))
        self.assertEqual(self.entry("unit-b")["parent_tip"], folded_a)
        self.assertEqual(self.entry("unit-b")["pushed"], self.rev(BR_B))
        self.assertEqual(self.entry("unit-a")["pushed"], folded_a)


class TestCascadeRefusals(_StackCase):
    """Every refusal happens before a ref moves, and leaves no restack file behind."""

    def test_stale_remote_branch_refuses_the_push_and_restores_every_branch(self):
        self.build_stack()
        self.remote_commit("main", {"z.py": b"z\n"}, "feat: trunk moved")
        self.remote_commit(BR_B, {"x.py": b"x\n"}, "feat: remote b moved")
        before = self.local_tips()
        code, text = self.fold("restack")
        self.assertEqual(code, 1, text)
        self.assertIn("stale_lease", text)
        self.assertEqual(self.local_tips(), before)
        head = f.run_git(self.repo, self.env, "symbolic-ref", "HEAD").strip()
        self.assertEqual(head, f"refs/heads/{BR_C}")
        self.assertEqual(self.status(), "")
        self.assertEqual(f.run_git(self.repo, self.env, "diff", before[BR_C]), "")
        self.assertNotEqual(self.remote_tip(BR_B), before[BR_B])
        self.assertFalse(self.restack_file_exists())

    def test_rebase_conflict_pauses_and_lists_the_conflicting_path(self):
        self.start_unit("unit-a", BR_A)
        self.commit({"shared.txt": b"a side\n"}, "feat: a shared")
        self.publish(BR_A)
        self.start_unit("unit-b", BR_B)
        self.commit({"b.py": b"b\n"}, "feat: add b")
        self.publish(BR_B)
        self.remote_commit("main", {"shared.txt": b"trunk side\n"}, "feat: trunk shared")
        before = self.local_tips((BR_A, BR_B))
        code, text = self.fold("restack")
        self.assertEqual(code, 1, text)
        self.assertIn("conflict: shared.txt", text)
        self.assertIn("fold.py restack --continue", text)
        self.assertTrue(self.restack_file_exists())
        self.assertEqual(self.record()["units"][0]["pushed"], before[BR_A])
        self.assertEqual(self.remote_tip(BR_A), before[BR_A])

    def test_dirty_tree_refuses_before_any_ref_moves(self):
        self.build_stack()
        self.remote_commit("main", {"z.py": b"z\n"}, "feat: trunk moved")
        (self.repo / "base.txt").write_bytes(b"edited\n")
        before = self.local_tips()
        code, text = self.fold("restack")
        self.assertEqual(code, 1, text)
        self.assertIn("dirty_tree", text)
        self.assertEqual(self.local_tips(), before)
        self.assertFalse(self.restack_file_exists())

    def test_unit_branch_checked_out_in_another_worktree_is_refused(self):
        self.build_stack()
        f.run_git(self.repo, self.env, "switch", "-q", "main")
        other = self.dest / "other-worktree"
        f.run_git(self.repo, self.env, "worktree", "add", "-q", str(other), BR_B)
        self.remote_commit("main", {"z.py": b"z\n"}, "feat: trunk moved")
        before = self.local_tips()
        code, text = self.fold("restack")
        self.assertEqual(code, 1, text)
        self.assertIn("branch_in_worktree", text)
        self.assertIn(BR_B, text)
        self.assertEqual(self.local_tips(), before)
        self.assertFalse(self.restack_file_exists())

    def test_unrecorded_local_branch_inside_the_range_is_refused(self):
        self.build_stack()
        a_tip = self.rev(BR_A)
        f.run_git(self.repo, self.env, "branch", "side", a_tip)
        self.remote_commit("main", {"z.py": b"z\n"}, "feat: trunk moved")
        before = self.local_tips()
        code, text = self.fold("restack")
        self.assertEqual(code, 1, text)
        self.assertIn("unrecorded_branch", text)
        self.assertIn("side", text)
        self.assertEqual(self.local_tips(), before)
        self.assertEqual(self.rev("refs/heads/side"), a_tip)
        self.assertFalse(self.restack_file_exists())


class TestHotfix(_StackCase):
    """A hotfix starts at its target's remote tip and never joins the stack order."""

    def test_hotfix_starts_at_the_target_remote_tip_outside_the_stack_order(self):
        self.build_stack()
        code, text = self.fold("hotfix", "--target", "main", "--name", "fix-1")
        self.assertEqual(code, 0, text)
        self.assertEqual(self.rev("refs/heads/hotfix/fix-1"), self.remote_tip("main"))
        kinds = {e["id"]: e["kind"] for e in self.record()["units"]}
        self.assertEqual(kinds["fix-1"], "hotfix")
        f.run_git(self.repo, self.env, "switch", "-q", BR_C)
        self.start_unit("unit-d", "demo/unit-d")
        self.assertEqual(self.entry("unit-d")["parent"], BR_C)
        self.assertEqual(self.entry("unit-d")["parent_tip"], self.rev(BR_C))

    def test_a_merged_hotfix_cascades_the_open_stack_once(self):
        self.build_stack()
        code, text = self.fold("hotfix", "--target", "main", "--name", "fix-1")
        self.assertEqual(code, 0, text)
        self.commit({"hotfix.txt": b"fix\n"}, "fix: hotfix")
        self.publish("hotfix/fix-1")
        before = self.local_tips()
        code, text = self.fold("restack")
        self.assertEqual(code, 0, text)
        self.assertIn("nothing to do", text)
        self.assertEqual(self.local_tips(), before)
        f.merge_on_remote(self.dest, self.env, self.bare, "hotfix/fix-1", "main")
        code, text = self.fold("restack")
        self.assertEqual(code, 0, text)
        self.assertIn("restacked: unit-a, unit-b, unit-c", text)
        new_main = self.remote_tip("main")
        self.assertEqual(self.count(new_main, BR_A), 1)
        self.assertEqual(self.count(BR_A, BR_B), 1)
        self.assertEqual(self.count(BR_B, BR_C), 1)
        self.assertEqual(self.entry("fix-1")["state"], "merged")
        code, text = self.fold("restack")
        self.assertIn("nothing to do", text)

    def test_a_staging_hotfix_leaves_the_stacked_units_untouched(self):
        self.build_stack()
        f.run_git(self.repo, self.env, "push", "-q", "origin", "main:refs/heads/staging")
        code, text = self.fold("settings", "set", "--target", "main", "--target", "staging")
        self.assertEqual(code, 0, text)
        tips = {name: self.rev(f"refs/heads/{name}") for name in (BR_A, BR_B, BR_C)}
        stacked = [e for e in self.record()["units"] if e["kind"] == "stacked"]
        code, text = self.fold("hotfix", "--target", "staging", "--name", "fix-s")
        self.assertEqual(code, 0, text)
        self.assertEqual(self.rev("refs/heads/hotfix/fix-s"), self.remote_tip("staging"))
        self.assertEqual(self.entry("fix-s")["target"], "staging")
        self.assertEqual({n: self.rev(f"refs/heads/{n}") for n in tips}, tips)
        self.assertEqual([e for e in self.record()["units"] if e["kind"] == "stacked"], stacked)

    def test_hotfix_to_an_unconfigured_target_is_refused(self):
        self.build_stack()
        code, text = self.fold("hotfix", "--target", "release", "--name", "fix-2")
        self.assertEqual(code, 1, text)
        self.assertIn("unknown_target", text)
        self.assertIsNone(self.rev_or_none("refs/heads/hotfix/fix-2"))

    def rev_or_none(self, name):
        proc = subprocess.run(["git", "-C", str(self.repo), "rev-parse", "--verify", "-q", name],
                              capture_output=True, text=True, env=self.env, check=False)
        return proc.stdout.strip() or None


if __name__ == "__main__":
    unittest.main()
