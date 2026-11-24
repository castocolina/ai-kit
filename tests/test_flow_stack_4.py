"""Restack of the units above a lower unit that moved (a plain commit), locally (SPEC R6)."""

import argparse
import contextlib
import io
import json
import os
import pathlib
import shlex
import sys
from unittest import mock

_REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "skills" / "ai-kit-commit-fold" / "scripts"))
sys.path.insert(0, str(_REPO))

import flow_stack

from tests import fold_fixtures as f
from tests import forge_fakes, host_fakes
from tests.test_flow_stack import BR_A, BR_B, BR_C, _StackCase


class TestRestackMovedLowerUnit(_StackCase):
    """A plain commit on a lower unit restacks the units above it, with no push."""

    def _commit_on(self, branch, files, message):
        f.run_git(self.repo, self.env, "switch", branch)
        return self.commit(files, message)

    def _remote_tips(self):
        return {b: self.remote_tip(b) for b in (BR_A, BR_B, BR_C)}

    def test_plain_commit_on_the_bottom_restacks_the_units_above_without_a_push(self):
        self.build_stack()
        remote = self._remote_tips()
        own = (f.run_git(self.repo, self.env, "diff", BR_A, BR_B),
               f.run_git(self.repo, self.env, "diff", BR_B, BR_C))
        self._commit_on(BR_A, {"a2.py": b"a2\n"}, "feat: more a")
        self.assertNotEqual(self.rev(BR_A), self.entry("unit-b")["parent_tip"])
        self.assertEqual(self.count(BR_B, BR_A), 1)
        code, text = self.fold("restack")
        self.assertEqual(code, 0, text)
        self.assertIn("restacked: unit-b, unit-c", text)
        self.assertEqual(self.count(BR_A, BR_B), 1)
        self.assertEqual(self.count(BR_B, BR_C), 1)
        self.assertEqual(self.count(BR_B, BR_A), 0)
        self.assertEqual(self.count(BR_C, BR_B), 0)
        self.assertEqual(self.entry("unit-b")["parent_tip"], self.rev(BR_A))
        self.assertEqual(self.entry("unit-c")["parent_tip"], self.rev(BR_B))
        self.assertEqual(self._remote_tips(), remote)
        self.assertEqual(self.entry("unit-b")["pending"], self.rev(BR_B))
        self.assertEqual(self.entry("unit-c")["pending"], self.rev(BR_C))
        self.assertEqual((f.run_git(self.repo, self.env, "diff", BR_A, BR_B),
                          f.run_git(self.repo, self.env, "diff", BR_B, BR_C)), own)
        self.assertFalse(self.restack_file_exists())
        current = f.run_git(self.repo, self.env, "branch", "--show-current").strip()
        self.assertEqual(current, BR_A)

    def test_detector_off_leaves_the_units_above_unmoved(self):
        self.build_stack()
        self._commit_on(BR_A, {"a2.py": b"a2\n"}, "feat: more a")
        self.assertNotEqual(self.rev(BR_A), self.entry("unit-b")["parent_tip"])
        self.assertEqual(self.count(BR_B, BR_A), 1)
        before = self.local_tips((BR_B, BR_C))
        with (mock.patch.dict(os.environ, self.env),
              mock.patch.object(flow_stack, "_moved_lower", return_value=None),
              contextlib.redirect_stdout(io.StringIO()) as out):
            code = flow_stack.cmd_restack(argparse.Namespace(
                repo=str(self.repo), abort=False, continue_=False, note=[], adapter_gates=[]))
        self.assertEqual(code, 0)
        self.assertIn("nothing to do", out.getvalue())
        self.assertEqual(self.local_tips((BR_B, BR_C)), before)

    def test_two_moved_units_restack_in_one_run(self):
        self.build_stack()
        self._commit_on(BR_A, {"a2.py": b"a2\n"}, "feat: more a")
        self._commit_on(BR_B, {"b2.py": b"b2\n"}, "feat: more b")
        code, text = self.fold("restack")
        self.assertEqual(code, 0, text)
        self.assertEqual(self.count(BR_A, BR_B), 2)
        self.assertEqual(self.count(BR_B, BR_C), 1)
        self.assertEqual(self.count(BR_B, BR_A), 0)
        self.assertEqual(self.count(BR_C, BR_B), 0)
        self.assertEqual(self.entry("unit-b")["parent_tip"], self.rev(BR_A))
        self.assertEqual(self.entry("unit-c")["parent_tip"], self.rev(BR_B))
        for unit_id in ("unit-b", "unit-c"):
            code, text = self.fold("guard", "--unit-id", unit_id)
            self.assertEqual(code, 0, text)

    def test_trunk_and_lower_moved_together_end_consistent_and_push_nothing(self):
        self.build_stack()
        remote = self._remote_tips()
        self._commit_on(BR_A, {"a2.py": b"a2\n"}, "feat: more a")
        self.remote_commit("main", {"z.py": b"z\n"}, "feat: trunk moved")
        code, text = self.fold("restack")
        self.assertEqual(code, 0, text)
        self.assertEqual(self.count(BR_A, "refs/remotes/origin/main"), 0)
        self.assertEqual(self.count(BR_B, BR_A), 0)
        self.assertEqual(self.count(BR_C, BR_B), 0)
        self.assertEqual(self.entry("unit-b")["parent_tip"], self.rev(BR_A))
        self.assertEqual(self.entry("unit-c")["parent_tip"], self.rev(BR_B))
        self.assertEqual(self._remote_tips(), remote)
        for unit_id, branch in (("unit-a", BR_A), ("unit-b", BR_B), ("unit-c", BR_C)):
            self.assertEqual(self.entry(unit_id)["pending"], self.rev(branch))

    def test_unit_off_its_boundary_is_refused_not_skipped(self):
        self.start_unit("unit-a", BR_A)
        self.commit({"a.py": b"a\n"}, "feat: a")
        self.start_unit("unit-b", BR_B)
        self.commit({"b.py": b"b\n"}, "feat: b")
        f.run_git(self.repo, self.env, "rebase", "-q", "--onto", "main", BR_A, BR_B)
        self._commit_on(BR_A, {"a2.py": b"a2\n"}, "feat: more a")
        before = (self.local_tips((BR_A, BR_B)), self.record())
        code, text = self.fold("restack")
        self.assertEqual(code, 1, text)
        self.assertIn("refused wrong_parent", text)
        self.assertIn("unit unit-b branch", text)
        self.assertNotIn("nothing to do", text)
        self.assertEqual((self.local_tips((BR_A, BR_B)), self.record()), before)
        self.assertFalse(self.restack_file_exists())

    def test_later_pass_conflict_abort_restores_command_entry(self):
        self.start_unit("unit-a", BR_A)
        self.commit({"shared.txt": b"a\n"}, "feat: a")
        self.publish(BR_A)
        self.start_unit("unit-b", BR_B)
        self.commit({"shared.txt": b"b\n"}, "feat: b")
        self.publish(BR_B)
        self.start_unit("unit-c", BR_C)
        self.commit({"c.py": b"c\n"}, "feat: c")
        self.publish(BR_C)
        self._commit_on(BR_B, {"b2.py": b"b2\n"}, "feat: more b")
        self._commit_on(BR_A, {"shared.txt": b"a2\n"}, "feat: a again")
        before = (self.local_tips(), self.record(),
                  f.run_git(self.repo, self.env, "branch", "--show-current"))
        code, text = self.fold("restack")
        self.assertEqual(code, 1, text)
        self.assertIn("conflict: shared.txt", text)
        code, text = self.fold("restack", "--abort")
        self.assertEqual(code, 0, text)
        self.assertEqual((self.local_tips(), self.record(),
                          f.run_git(self.repo, self.env, "branch", "--show-current")), before)
        self.assertFalse(self.restack_file_exists())

    def test_later_pass_refusal_keeps_the_command_entry_state_for_abort(self):
        self.build_stack()
        self._commit_on(BR_A, {"a2.py": b"a2\n"}, "feat: more a")
        self._commit_on(BR_B, {"b2.py": b"b2\n"}, "feat: more b")
        f.run_git(self.repo, self.env, "worktree", "add", "-q",
                  str(self.root / "wt-a"), BR_A)
        before = (self.local_tips(), self.record(),
                  f.run_git(self.repo, self.env, "branch", "--show-current"))
        code, text = self.fold("restack")
        self.assertEqual(code, 1, text)
        self.assertIn("branch_in_worktree", text)
        if self.rev(BR_C) == before[0][BR_C]:
            print(text)
            self.fail("the first pass did not run")
        self.assertTrue(self.restack_file_exists())
        code, text = self.fold("restack")
        self.assertEqual(code, 1, text)
        self.assertIn("restack_pending", text)
        code, text = self.fold("restack", "--abort")
        self.assertEqual(code, 0, text)
        self.assertEqual((self.local_tips(), self.record(),
                          f.run_git(self.repo, self.env, "branch", "--show-current")), before)
        self.assertFalse(self.restack_file_exists())

    def test_start_restacks_the_units_above_through_sync(self):
        self.build_stack()
        code, text = self.fold("consent", "revoke")
        self.assertEqual(code, 0, text)
        remote = self._remote_tips()
        self._commit_on(BR_A, {"a2.py": b"a2\n"}, "feat: more a")
        f.run_git(self.repo, self.env, "switch", BR_C)
        self.start_unit("unit-d", "demo/unit-d")
        self.assertEqual(self.count(BR_B, BR_A), 0)
        self.assertEqual(self.count(BR_C, BR_B), 0)
        self.assertEqual(self.count(BR_A, BR_B), 1)
        self.assertEqual(self._remote_tips(), remote)
        self.assertEqual(self.entry("unit-d")["parent"], BR_C)

    def test_consented_start_keeps_the_units_above_a_moved_lower_unit_pending(self):
        forge_fakes.write_forge_fakes(self.dest / "bin", self.dest / "forge.json",
                                      self.dest / "gh.log", gh_stack=False)
        self.env["PATH"] = host_fakes.host_path(self.dest / "bin", self.env["PATH"])
        self.build_stack()
        remote = self._remote_tips()
        self._commit_on(BR_A, {"a2.py": b"a2\n"}, "feat: plain commit on a")
        f.run_git(self.repo, self.env, "switch", BR_C)
        path = self.dest / "unit-b.json"
        path.write_text(json.dumps({"schema": 1, "id": "unit-b", "kind": "stacked",
                                    "branch": BR_B, "title": "Unit unit-b"}), encoding="utf-8")
        code, text = self.fold("start", "--unit", str(path))
        self.assertEqual(code, 0, text)
        self.assertEqual(self._remote_tips(), remote)
        self.assertNotIn("caught up", text)
        self.assertIn("kept unit-b, unit-c pending: unit unit-a below is not pushed at its "
                      "local tip", text)
        self.assertEqual(self.count(BR_B, BR_A), 0)
        self.assertEqual(self.entry("unit-b")["pending"], self.rev(BR_B))
        self.assertEqual(self.entry("unit-c")["pending"], self.rev(BR_C))
        self.publish(BR_A)  # unit-a pushed at its local tip, as its own checkpoint would
        code, text = self.fold("start", "--unit", str(path))
        self.assertEqual(code, 0, text)
        self.assertIn("caught up unit unit-b", text)
        self.assertIn("caught up unit unit-c", text)
        self.assertEqual(self._remote_tips(), self.local_tips())
        self.assertIsNone(self.entry("unit-c")["pending"])

    def test_lower_pass_creates_no_first_push_and_keeps_a_pending_tip_current(self):
        self.start_unit("unit-a", BR_A)
        self.commit({"a.py": b"a\n"}, "feat: a")
        self.publish(BR_A)
        self.start_unit("unit-b", BR_B)
        self.commit({"b.py": b"b\n"}, "feat: b")
        self.start_unit("unit-c", BR_C)
        self.commit({"c.py": b"c\n"}, "feat: c")
        path = self.repo / ".git" / "ai-kit-stack.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["units"][1]["pending"] = self.rev(BR_B)  # a folded checkpoint whose push was skipped
        path.write_text(json.dumps(data), encoding="utf-8")
        self._commit_on(BR_A, {"a2.py": b"a2\n"}, "feat: more a")
        code, text = self.fold("restack")
        self.assertEqual(code, 0, text)
        self.assertIn("restacked: unit-b, unit-c", text)
        self.assertEqual(self.entry("unit-b")["pending"], self.rev(BR_B))
        self.assertIsNone(self.entry("unit-c")["pending"])
        self.assertIsNone(self.entry("unit-c")["pushed"])

    def test_start_recreates_a_deleted_unit_branch_after_a_lower_unit_moved(self):
        self.build_stack()
        remote = self._remote_tips()
        f.run_git(self.repo, self.env, "switch", BR_C)
        f.run_git(self.repo, self.env, "branch", "-D", BR_B)
        self._commit_on(BR_A, {"a2.py": b"a2\n"}, "feat: plain commit on a")
        f.run_git(self.repo, self.env, "switch", BR_C)
        code, text = self.fold("restack")
        self.assertEqual(code, 1, text)
        self.assertIn("refused branch_missing", text)
        self.assertIn(f"unit unit-b branch {BR_B} does not exist", text)
        self.assertFalse(self.restack_file_exists())
        path = self.dest / "unit-b.json"
        path.write_text(json.dumps({"schema": 1, "id": "unit-b", "kind": "stacked",
                                    "branch": BR_B, "title": "Unit unit-b"}), encoding="utf-8")
        code, text = self.fold("start", "--unit", str(path))
        self.assertEqual(code, 0, text)
        self.assertIn("reuses unit unit-b", text)
        current = f.run_git(self.repo, self.env, "branch", "--show-current").strip()
        self.assertEqual(current, BR_B)
        self.assertEqual(self.count(BR_B, BR_A), 0)
        self.assertEqual(self.count(BR_C, BR_B), 0)
        self.assertEqual(self.count(BR_A, BR_B), 1)
        self.assertEqual(self._remote_tips(), remote)

    def test_every_own_commit_of_b_and_c_is_kept(self):
        self.build_stack()
        self._commit_on(BR_C, {"fix.txt": b"fix\n"}, "fix: shared fix on c")
        f.run_git(self.repo, self.env, "tag", "demo-folded", BR_B)
        own_b = f.run_git(self.repo, self.env, "diff", BR_A, BR_B)
        subjects = {b: f.run_git(self.repo, self.env, "log", "--format=%s", f"{p}..{b}")
                    for p, b in ((BR_A, BR_B), (BR_B, BR_C))}
        self._commit_on(BR_A, {"fix.txt": b"fix\n"}, "fix: shared fix on a")
        a_tip = self.rev(BR_A)
        tagged = self.rev("refs/tags/demo-folded")
        code, text = self.fold("restack")
        self.assertEqual(code, 0, text)
        self.assertEqual(self.rev(BR_A), a_tip)
        self.assertEqual(self.rev("refs/tags/demo-folded"), tagged)
        self.assertEqual(f.run_git(self.repo, self.env, "diff", BR_A, BR_B), own_b)
        self.assertEqual(
            {b: f.run_git(self.repo, self.env, "log", "--format=%s", f"{p}..{b}")
             for p, b in ((BR_A, BR_B), (BR_B, BR_C))}, subjects)
        self.assertEqual(f.run_git(self.repo, self.env, "show", f"{BR_C}:fix.txt"), "fix\n")

    def test_refold_over_an_older_pushed_tip_restacks_without_a_push(self):
        self.build_stack()
        old_a = self.rev(BR_A)
        remote = self._remote_tips()
        subjects = {b: f.run_git(self.repo, self.env, "log", "--format=%s", f"{p}..{b}")
                    for p, b in ((BR_A, BR_B), (BR_B, BR_C))}
        f.run_git(self.repo, self.env, "switch", BR_A)
        (self.repo / "a.py").write_bytes(b"a folded\n")
        f.run_git(self.repo, self.env, "commit", "-q", "-a", "--amend", "-m",
                  "feat: unit-a (folded)")
        self.assertEqual(self.count(BR_A, old_a), 1)
        code, text = self.fold("restack")
        self.assertEqual(code, 0, text)
        self.assertIn("restacked: unit-b, unit-c", text)
        self.assertEqual(self.count(BR_B, BR_A), 0)
        self.assertEqual(self.count(BR_C, BR_B), 0)
        self.assertEqual(self.count(BR_A, BR_B), 1)
        self.assertEqual(self.count(BR_B, BR_C), 1)
        self.assertEqual(
            {b: f.run_git(self.repo, self.env, "log", "--format=%s", f"{p}..{b}")
             for p, b in ((BR_A, BR_B), (BR_B, BR_C))}, subjects)
        self.assertEqual(self._remote_tips(), remote)
        self.assertEqual(self.entry("unit-b")["parent_tip"], self.rev(BR_A))
        self.assertEqual(self.entry("unit-c")["parent_tip"], self.rev(BR_B))

    def _conflict_stack(self):
        self.start_unit("unit-a", BR_A)
        self.commit({"shared.txt": b"a\n"}, "feat: a")
        self.publish(BR_A)
        self.start_unit("unit-b", BR_B)
        self.commit({"shared.txt": b"b\n"}, "feat: b")
        self.publish(BR_B)
        self.start_unit("unit-c", BR_C)
        self.commit({"c.py": b"c\n"}, "feat: c")
        self.publish(BR_C)
        self._commit_on(BR_A, {"shared.txt": b"a2\n"}, "feat: a again")

    def _passing_gate(self):
        path = pathlib.Path(self.repo).parent / "gate_ok.py"
        path.write_text("import sys\nsys.exit(0)\n", encoding="utf-8")
        code, text = self.fold("settings", "set", "--gate",
                               shlex.join([sys.executable, str(path)]))
        self.assertEqual(code, 0, text)

    def test_conflict_pauses_refuses_a_second_start_and_abort_restores(self):
        self._conflict_stack()
        before = self.local_tips()
        code, text = self.fold("restack")
        self.assertEqual(code, 1, text)
        self.assertIn("conflict: shared.txt", text)
        self.assertTrue(self.restack_file_exists())
        code, text = self.fold("restack")
        self.assertEqual(code, 1, text)
        self.assertIn("restack_pending", text)
        path = self.dest / "unit-d.json"
        path.write_text(json.dumps({"schema": 1, "id": "unit-d", "kind": "stacked",
                                    "branch": "demo/unit-d", "title": "Unit unit-d"}),
                        encoding="utf-8")
        code, text = self.fold("start", "--unit", str(path))
        self.assertEqual(code, 1, text)
        self.assertIn("restack_pending", text)
        code, text = self.fold("restack", "--abort")
        self.assertEqual(code, 0, text)
        self.assertEqual(self.local_tips(), before)
        self.assertFalse(self.restack_file_exists())

    def test_continue_after_a_resolved_pause_pushes_nothing(self):
        self._conflict_stack()
        remote = self._remote_tips()
        self._passing_gate()
        code, text = self.fold("restack")
        self.assertEqual(code, 1, text)
        (self.repo / "shared.txt").write_bytes(b"both sides kept\n")
        code, text = self.fold("restack", "--continue", "--note", "shared.txt=kept")
        self.assertEqual(code, 0, text)
        self.assertIn("restacked:", text)
        self.assertEqual(self._remote_tips(), remote)
        self.assertEqual(self.entry("unit-b")["pending"], self.rev(BR_B))
        self.assertEqual(self.entry("unit-c")["pending"], self.rev(BR_C))

    def test_unit_with_no_commit_of_its_own_moves_to_the_new_tip(self):
        self.start_unit("unit-a", BR_A)
        self.commit({"a.py": b"a\n"}, "feat: a")
        self.start_unit("unit-b", BR_B)
        self._commit_on(BR_A, {"a2.py": b"a2\n"}, "feat: more a")
        code, text = self.fold("restack")
        self.assertEqual(code, 0, text)
        self.assertEqual(self.rev(BR_B), self.rev(BR_A))
        self.assertEqual(self.entry("unit-b")["parent_tip"], self.rev(BR_A))

    def test_nothing_above_and_a_second_run_report_nothing_to_do(self):
        self.build_stack()
        self._commit_on(BR_C, {"c2.py": b"c2\n"}, "feat: more c")
        before = self.local_tips()
        code, text = self.fold("restack")
        self.assertEqual(code, 0, text)
        self.assertIn("nothing to do", text)
        self.assertEqual(self.local_tips(), before)
        self._commit_on(BR_A, {"a2.py": b"a2\n"}, "feat: more a")
        code, text = self.fold("restack")
        self.assertEqual(code, 0, text)
        self.assertIn("restacked: unit-b, unit-c", text)
        code, text = self.fold("restack")
        self.assertEqual(code, 0, text)
        self.assertIn("nothing to do", text)

    def test_decimal_unit_ids_restack(self):
        self.start_unit("phase-02", "demo/phase-02-x")
        self.commit({"x.py": b"x\n"}, "feat: x")
        self.start_unit("phase-02.1", "demo/phase-02.1-y")
        self.commit({"y.py": b"y\n"}, "feat: y")
        self._commit_on("demo/phase-02-x", {"x2.py": b"x2\n"}, "feat: more x")
        code, text = self.fold("restack")
        self.assertEqual(code, 0, text)
        self.assertIn("restacked: phase-02.1", text)
        self.assertEqual(self.count("demo/phase-02-x", "demo/phase-02.1-y"), 1)
        self.assertEqual(self.count("demo/phase-02.1-y", "demo/phase-02-x"), 0)
