"""The two new start refusals: stale_parent and unrecorded_head (SPEC R5b, R8).

Split from tests/test_flow_stack.py by test class so the parts run in parallel; the shared
template fixture `_StackCase` stays there.
"""

import json
import os
import pathlib
import sys
import unittest
from unittest import mock

_REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "skills" / "ai-kit-commit-fold" / "scripts"))
sys.path.insert(0, str(_REPO))

import flow_record
import flow_unit

from tests import fold_fixtures as f
from tests.test_flow_stack import BR_A, BR_B, BR_C, _StackCase


class TestStartRefusals(_StackCase):
    """start refuses a missing newest parent and an unrecorded HEAD before anything moves."""

    def _start_new(self, unit_id, branch):
        path = self.dest / f"{unit_id}.json"
        path.write_text(json.dumps({"schema": 1, "id": unit_id, "kind": "stacked",
                                    "branch": branch, "title": f"Unit {unit_id}"}),
                        encoding="utf-8")
        return self.fold("start", "--unit", str(path))

    def _snapshot(self):
        record = self.repo / ".git" / "ai-kit-stack.json"
        config = self.repo / ".planning" / "config.json"
        record_bytes = record.read_bytes() if record.exists() else None
        config_bytes = config.read_bytes() if config.exists() else None
        refs = f.run_git(self.repo, self.env, "for-each-ref",
                         "--format=%(refname) %(objectname)")
        head = f.run_git(self.repo, self.env, "branch", "--show-current")
        return record_bytes, config_bytes, refs, head

    def test_stale_parent_names_the_unit_and_its_branch(self):
        self.build_stack()
        f.run_git(self.repo, self.env, "switch", BR_B)
        f.run_git(self.repo, self.env, "branch", "-D", BR_C)
        before = self._snapshot()
        code, text = self._start_new("unit-d", "demo/unit-d")
        self.assertEqual(code, 1, text)
        self.assertIn("refused stale_parent", text)
        self.assertIn(
            "unit unit-c branch demo/unit-c does not exist; it is the newest unmerged unit "
            "in the stack record", text)
        self.assertNotIn("no_trunk", text)
        self.assertEqual(self._snapshot(), before)

    def test_stale_parent_is_decided_before_the_sync(self):
        self.build_stack()
        f.run_git(self.repo, self.env, "switch", BR_B)
        f.run_git(self.repo, self.env, "branch", "-D", BR_C)
        self.remote_commit("main", {"z.py": b"z\n"}, "feat: trunk moved")
        before = self._snapshot()
        code, text = self._start_new("unit-d", "demo/unit-d")
        self.assertEqual(code, 1, text)
        self.assertIn("refused stale_parent", text)
        self.assertEqual(self._snapshot(), before)

    def test_stale_parent_prints_a_dotted_slashed_branch_verbatim(self):
        self.start_unit("phase-02.1", "feat/phase-02.1-x.y")
        self.commit({"x.py": b"x\n"}, "feat: x")
        f.run_git(self.repo, self.env, "switch", "main")
        f.run_git(self.repo, self.env, "branch", "-D", "feat/phase-02.1-x.y")
        code, text = self._start_new("unit-e", "demo/unit-e")
        self.assertEqual(code, 1, text)
        self.assertIn("unit phase-02.1 branch feat/phase-02.1-x.y does not exist", text)

    def test_no_unmerged_unit_starts_as_today(self):
        code, text = self._start_new("unit-a", BR_A)
        self.assertEqual(code, 0, text)
        self.assertIn("started unit unit-a on main", text)

    def test_missing_remote_target_keeps_no_trunk(self):
        code, text = self.fold("settings", "set", "--target", "nosuch")
        self.assertEqual(code, 0, text)
        code, text = self._start_new("unit-a", BR_A)
        self.assertEqual(code, 1, text)
        self.assertIn("refused no_trunk", text)
        self.assertIn("no remote nosuch ref to stack on", text)
        self.assertNotIn("stale_parent", text)

    def test_unrecorded_head_with_a_local_commit_is_refused(self):
        self.start_unit("unit-a", BR_A)
        self.commit({"a.py": b"a\n"}, "feat: a")
        self.publish(BR_A)
        f.run_git(self.repo, self.env, "switch", "-c", "side", "main")
        self.commit({"side.txt": b"s\n"}, "feat: side work")
        before = self._snapshot()
        code, text = self._start_new("unit-b", BR_B)
        self.assertEqual(code, 1, text)
        self.assertIn("refused unrecorded_head", text)
        self.assertIn(
            f"HEAD branch side is not a recorded unit and holds 1 commit(s) the trunk lacks: "
            f"{self.rev('side')[:12]} feat: side work", text)
        self.assertEqual(self._snapshot(), before)

    def test_missing_local_tracking_ref_does_not_skip_the_head_check(self):
        f.run_git(self.repo, self.env, "switch", "-c", "side", "main")
        self.commit({"side.txt": b"s\n"}, "feat: side work")
        origin_head = f.run_git(self.repo, self.env, "for-each-ref", "--format=%(refname)",
                                "refs/remotes/origin/HEAD")
        if origin_head.strip():
            f.run_git(self.repo, self.env, "symbolic-ref", "-d", "refs/remotes/origin/HEAD")
        f.run_git(self.repo, self.env, "update-ref", "-d", "refs/remotes/origin/main")
        self.assertIsNotNone(self.remote_tip("main"))
        before = self._snapshot()
        code, text = self._start_new("unit-a", BR_A)
        self.assertEqual(code, 1, text)
        self.assertIn("refused unrecorded_head", text)
        self.assertIn("feat: side work", text)
        self.assertEqual(self._snapshot(), before)

    def test_no_configured_remote_refuses_no_remote_before_the_head_check(self):
        f.run_git(self.repo, self.env, "remote", "remove", "origin")
        f.run_git(self.repo, self.env, "switch", "-c", "side", "main")
        self.commit({"side.txt": b"s\n"}, "feat: side work")
        before = self._snapshot()
        code, text = self._start_new("unit-a", BR_A)
        self.assertEqual(code, 1, text)
        self.assertIn("refused no_remote", text)
        self.assertNotIn("unrecorded_head", text)
        self.assertEqual(self._snapshot(), before)

    def test_plan_path_commits_are_exempt(self):
        self.start_unit("unit-a", BR_A)
        self.commit({"a.py": b"a\n"}, "feat: a")
        f.run_git(self.repo, self.env, "switch", "-c", "side", "main")
        self.commit({"plans/p.md": b"plan\n"}, "docs: plan")
        record = flow_record.read_record(self.repo)
        settings = flow_record.read_settings(self.repo)
        unit = flow_record.load_unit(
            {"schema": 1, "id": "unit-b", "kind": "stacked", "branch": BR_B,
             "title": "Unit unit-b"}, "main")
        with mock.patch.dict(os.environ, self.env):
            self.assertIsNone(
                flow_unit._refuse_before_sync(self.repo, settings, record, unit, ("plans",)))
            self.commit({"other.txt": b"o\n"}, "feat: unrelated")
            with self.assertRaises(flow_record.FlowError) as caught:
                flow_unit._refuse_before_sync(
                    self.repo, settings, record, unit, ("plans",))
        self.assertEqual(caught.exception.reason, "unrecorded_head")
        self.assertIn("1 commit(s)", caught.exception.detail)
        self.assertIn("feat: unrelated", caught.exception.detail)
        self.assertNotIn("docs: plan", caught.exception.detail)

    def test_head_on_a_recorded_unit_with_local_commits_starts(self):
        self.build_stack()
        self.commit({"c2.py": b"c2\n"}, "feat: more c")
        self.start_unit("unit-d", "demo/unit-d")

    def test_restart_of_a_recorded_unit_from_an_unrecorded_branch_reuses_it(self):
        self.start_unit("unit-a", BR_A)
        self.commit({"a.py": b"a\n"}, "feat: a")
        f.run_git(self.repo, self.env, "switch", "-c", "side", "main")
        self.commit({"side.txt": b"s\n"}, "feat: side work")
        code, text = self._start_new("unit-a", BR_A)
        self.assertEqual(code, 0, text)
        self.assertIn("reuses unit unit-a", text)

    def test_unrecorded_head_subjects_are_redacted(self):
        self.start_unit("unit-a", BR_A)
        self.commit({"a.py": b"a\n"}, "feat: a")
        self.publish(BR_A)
        f.run_git(self.repo, self.env, "switch", "-c", "side", "main")
        self.commit({"side.txt": b"s\n"}, "feat: side " + "ghp_" + "a" * 36)
        code, text = self._start_new("unit-b", BR_B)
        self.assertEqual(code, 1, text)
        self.assertIn("[redacted]", text)
        self.assertNotIn("ghp_", text)

    def test_phase_selector_refusal_keeps_a_normalized_config(self):
        self.build_stack()
        f.run_git(self.repo, self.env, "switch", BR_B)
        f.run_git(self.repo, self.env, "branch", "-D", BR_C)
        planning = self.repo / ".planning"
        planning.mkdir()
        (planning / "config.json").write_text(
            json.dumps({"git": {"branching_strategy": "none"}}), encoding="utf-8")
        phase = planning / "phases" / "05-demo"
        phase.mkdir(parents=True)
        (phase / "05-CONTEXT.md").write_text("# context\n", encoding="utf-8")
        before = self._snapshot()
        code, text = self.fold("start", "--phase", "5")
        self.assertEqual(code, 1, text)
        self.assertIn("refused stale_parent", text)
        self.assertEqual(self._snapshot(), before)


if __name__ == "__main__":
    unittest.main()
