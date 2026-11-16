"""Checkpoint flow tests (plan 29.1-02): push at every checkpoint, PR backends, MVP fast path.

Each class builds on the template fixture of tests.test_flow_contract (one copy of a repo with
a local bare remote per test, fresh fake forge state and log, consent granted in the copy).

Split by test class: tests/test_flow_checkpoint_2.py holds the start, fetch race, PR backend,
bottom-up ready and MVP tests.
"""

import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

_REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "skills" / "ai-kit-commit-fold" / "scripts"))
sys.path.insert(0, str(_REPO))

from tests import fold_fixtures as f
from tests import forge_fakes
from tests.test_flow_contract import _FlowCase

PLAN_BRANCH = "plan/demo-plan"
SP_SPEC_NAME = "docs/specs/d.md"


class TestFlowScriptsImport(unittest.TestCase):
    def test_flow_scripts_import(self):
        import flow_git  # noqa: F401
        import flow_pr  # noqa: F401
        import flow_record  # noqa: F401
        import flow_stack  # noqa: F401
        import flow_unit  # noqa: F401
        import fold

        args = fold.build_parser().parse_args(["checkpoint", "--unit", "-"])
        self.assertEqual(args.command, "checkpoint")
        self.assertEqual(args.unit_file, "-")


class TestSuperpowersSpecPath(unittest.TestCase):
    """The plan's **Spec:** line names the spec file start carries with the plan."""

    def setUp(self):
        import fold_adapters

        self.spec_path = fold_adapters.superpowers_spec_path
        self.repo = pathlib.Path(tempfile.mkdtemp(prefix="spec-path-"))
        self.addCleanup(shutil.rmtree, self.repo)
        (self.repo / "docs" / "plans").mkdir(parents=True)
        (self.repo / "docs" / "specs").mkdir()
        (self.repo / SP_SPEC_NAME).write_text("# spec\n", encoding="utf-8")

    def _plan(self, line):
        (self.repo / "docs/plans/p.md").write_text(f"# P\n\n{line}\n", encoding="utf-8")
        return self.spec_path(str(self.repo), "docs/plans/p.md")

    def test_bare_code_and_link_forms_resolve_repo_relative(self):
        for line in (f"**Spec:** {SP_SPEC_NAME}", f"**Spec:** `{SP_SPEC_NAME}`",
                     f"**Spec:** [design]({SP_SPEC_NAME})"):
            self.assertEqual(self._plan(line), SP_SPEC_NAME, line)

    def test_plan_relative_path_resolves(self):
        self.assertEqual(self._plan("**Spec:** ../specs/d.md"), SP_SPEC_NAME)

    def test_missing_line_missing_file_and_outside_paths_give_none(self):
        self.assertIsNone(self._plan("**Goal:** none"))
        self.assertIsNone(self._plan("**Spec:** docs/specs/absent.md"))
        self.assertIsNone(self._plan("**Spec:** ../../../../etc/hostname"))


class _PlanCase(_FlowCase):
    """A superpowers plan unit on the plan branch, consent granted, one checkpoint pending."""

    def _plan_unit(self):
        f.run_git(self.repo, self.env, "switch", "-q", "main")
        self.commit({f.SP_PLAN: f.SP_PLAN_TEXT.encode()}, "docs: trunk")
        f.run_git(self.repo, self.env, "push", "-q", "origin", "main")
        self.grant()
        code, text = self.fold("start", "--plan", f.SP_PLAN)
        self.assertEqual(code, 0, text)
        f.run_git(self.repo, self.env, "switch", "-q", PLAN_BRANCH)

    def checkpoint_plan(self, *extra):
        return self.fold("checkpoint", "--plan", f.SP_PLAN, *extra)

    def pr_edits(self):
        return [c["argv"] for c in self.gh_calls() if c["argv"][:2] == ["pr", "edit"]]

    def pr_creates(self):
        return [c["argv"] for c in self.gh_calls() if c["argv"][:2] == ["pr", "create"]]

    def local_tip(self):
        return self.ref_sha(f"refs/heads/{PLAN_BRANCH}")


class TestCheckpointPush(_PlanCase):
    """Every checkpoint folds, then pushes the unit branch; the PR text follows the unit."""

    def test_each_checkpoint_pushes_its_folded_tip_and_opens_one_draft_pr(self):
        self._plan_unit()
        self.commit({"a.py": b"a\n"}, "feat: add a")
        self.commit({"tests/test_a.py": b"ta\n"}, "test: cover a")
        code, text = self.checkpoint_plan()
        self.assertEqual(code, 0, text)
        self.assertEqual(self.remote_sha(PLAN_BRANCH), self.local_tip())
        self.commit({"b.py": b"b\n"}, "feat: add b")
        self.commit({"tests/test_b.py": b"tb\n"}, "test: cover b")
        code, text = self.checkpoint_plan()
        self.assertEqual(code, 0, text)
        self.assertEqual(self.remote_sha(PLAN_BRANCH), self.local_tip())
        self.assertEqual(len(self.pr_creates()), 1)

    def test_pr_number_is_recorded_although_gh_warns_on_stderr(self):
        self._plan_unit()
        self.commit({"a.py": b"a\n"}, "feat: add a")
        code, text = self.checkpoint_plan()
        self.assertEqual(code, 0, text)
        self.assertEqual(self.record()["units"][0]["pr"], 1)

    def test_pr_text_follows_the_unit_after_each_checkpoint(self):
        self._plan_unit()
        self.commit({"a.py": b"a\n"}, "feat: add a")
        self.checkpoint_plan()
        self.commit({"b.py": b"b\n"}, "feat: add b")
        code, text = self.checkpoint_plan()
        self.assertEqual(code, 0, text)
        entry = self.record()["units"][0]
        body = forge_fakes.forge_state(self.state)["prs"][0]["body"]
        self.assertIn(entry["title"], body)
        self.assertIn(entry["goal"], body)
        self.assertIn("checkpoints: 2", body)
        self.assertEqual(len(self.pr_edits()), 1)
        self.assertIn("--body-file", self.pr_edits()[0])

    def test_nothing_new_since_the_last_push_makes_no_push_and_says_so(self):
        self._plan_unit()
        self.commit({"a.py": b"a\n"}, "feat: add a")
        self.checkpoint_plan()
        remote_before = self.remote_sha(PLAN_BRANCH)
        edits_before = len(self.pr_edits())
        code, text = self.checkpoint_plan()
        self.assertEqual(code, 0, text)
        self.assertIn("nothing to push", text)
        self.assertEqual(self.remote_sha(PLAN_BRANCH), remote_before)
        self.assertEqual(len(self.pr_edits()), edits_before)

    def test_fold_refusal_pushes_nothing_and_the_report_carries_the_reason(self):
        self._plan_unit()
        self.commit({"a.py": b"a\n"}, "feat: add a")
        self.checkpoint_plan()
        self.commit({"b.py": b"b\n"}, "feat: add b")
        remote_before = self.remote_sha(PLAN_BRANCH)
        (self.repo / f.SP_PLAN).write_text("dirty\n", encoding="utf-8")
        code, text = self.checkpoint_plan()
        self.assertEqual(code, 1, text)
        self.assertIn("refused", text)
        self.assertEqual(self.remote_sha(PLAN_BRANCH), remote_before)

    def test_second_clone_push_makes_the_next_checkpoint_refuse_stale_lease(self):
        self._plan_unit()
        self.commit({"a.py": b"a\n"}, "feat: add a")
        code, text = self.checkpoint_plan()
        self.assertEqual(code, 0, text)
        clone = self.dest / "clone"
        subprocess.run(["git", "clone", "-q", str(self.bare), str(clone)], env=self.env,
                       check=True, capture_output=True)
        f.run_git(clone, self.env, "checkout", "-q", "-b", PLAN_BRANCH,
                  f"origin/{PLAN_BRANCH}")
        other = f.commit(clone, self.env, {"other.py": b"o\n"}, "feat: other clone")
        f.run_git(clone, self.env, "push", "-q", "origin", PLAN_BRANCH)
        self.commit({"b.py": b"b\n"}, "feat: add b")
        code, text = self.checkpoint_plan()
        self.assertEqual(code, 1, text)
        self.assertIn("stale_lease", text)
        self.assertEqual(self.remote_sha(PLAN_BRANCH), other)


class TestRecordBeforeForge(_PlanCase):
    """A push is recorded before any gh call, so a gh failure never wedges the lease."""

    def test_failed_pr_edit_after_a_push_keeps_the_record_and_the_next_checkpoint_pushes(self):
        self._plan_unit()
        self.commit({"a.py": b"a\n"}, "feat: add a")
        self.checkpoint_plan()
        self.commit({"b.py": b"b\n"}, "feat: add b")
        forge_fakes.fail_next_edit(self.state)
        code, text = self.checkpoint_plan()
        self.assertEqual(code, 0, text)
        self.assertIn("PR step failed: pr_failed", text)
        self.assertEqual(self.record()["units"][0]["pushed"], self.remote_sha(PLAN_BRANCH))
        self.commit({"c.py": b"c\n"}, "feat: add c")
        code, text = self.checkpoint_plan()
        self.assertEqual(code, 0, text)
        self.assertNotIn("stale_lease", text)
        self.assertEqual(self.remote_sha(PLAN_BRANCH), self.local_tip())


class TestReadyAndBackend(_PlanCase):
    """ready on a superpowers plan marks the PR; the gh-stack probe picks the backend."""

    def test_ready_on_a_superpowers_plan_marks_the_pr_non_draft(self):
        self._plan_unit()
        self.commit({"a.py": b"a\n"}, "feat: add a")
        code, text = self.checkpoint_plan("--final")
        self.assertEqual(code, 0, text)
        self.assertTrue(forge_fakes.forge_state(self.state)["prs"][0]["isDraft"])
        code, text = self.fold("ready", "--plan", f.SP_PLAN)
        self.assertEqual(code, 0, text)
        self.assertFalse(forge_fakes.forge_state(self.state)["prs"][0]["isDraft"])

    def test_backend_probe_picks_gh_stack_only_when_stack_help_exits_zero(self):
        import os
        from unittest import mock

        import flow_pr

        def runner(stack_code):
            return lambda _repo, *args: (stack_code, "") if args[:1] == ("stack",) else (0, "")

        for stack_code, expected in ((0, "gh-stack"), (1, "gh")):
            with mock.patch.dict("os.environ"), mock.patch.object(
                    flow_pr, "run_gh", runner(stack_code)):
                os.environ.pop("AI_KIT_FLOW_PR_BACKEND", None)
                self.assertEqual(flow_pr.backend(self.repo), expected)


class TestBranchGuards(_PlanCase):
    """A deleted or rewound local branch never rewinds the remote; HEAD must be the unit."""

    def _pushed_unit_without_local_branch(self):
        self._plan_unit()
        self.commit({"a.py": b"a\n"}, "feat: add a")
        self.checkpoint_plan()
        pushed = self.remote_sha(PLAN_BRANCH)
        f.run_git(self.repo, self.env, "switch", "-q", "main")
        f.run_git(self.repo, self.env, "branch", "-D", PLAN_BRANCH)
        return pushed

    def test_start_recreates_a_deleted_branch_at_the_pushed_tip(self):
        pushed = self._pushed_unit_without_local_branch()
        code, text = self.fold("start", "--plan", f.SP_PLAN)
        self.assertEqual(code, 0, text)
        self.assertEqual(self.local_tip(), pushed)
        self.commit({"b.py": b"b\n"}, "feat: add b")
        code, text = self.checkpoint_plan()
        self.assertEqual(code, 0, text)
        self.assertEqual(self.remote_sha(PLAN_BRANCH), self.local_tip())

    def test_start_refuses_a_deleted_branch_the_record_holds_no_tip_for(self):
        self._plan_unit()
        f.run_git(self.repo, self.env, "switch", "-q", "main")
        f.run_git(self.repo, self.env, "branch", "-D", PLAN_BRANCH)
        code, text = self.fold("start", "--plan", f.SP_PLAN)
        self.assertEqual(code, 1, text)
        self.assertIn("branch_missing", text)

    def test_push_that_would_rewind_the_remote_is_refused(self):
        pushed = self._pushed_unit_without_local_branch()
        f.run_git(self.repo, self.env, "branch", PLAN_BRANCH, "main")
        f.run_git(self.repo, self.env, "switch", "-q", PLAN_BRANCH)
        self.commit({"z.py": b"z\n"}, "feat: unrelated")
        code, text = self.checkpoint_plan()
        self.assertEqual(code, 1, text)
        self.assertIn("not_descendant", text)
        self.assertEqual(self.remote_sha(PLAN_BRANCH), pushed)

    def test_checkpoint_with_head_off_the_unit_branch_refuses_ref_mismatch(self):
        self._plan_unit()
        self.commit({"a.py": b"a\n"}, "feat: add a")
        f.run_git(self.repo, self.env, "switch", "-q", "main")
        before = self.local_tip()
        code, text = self.checkpoint_plan()
        self.assertEqual(code, 1, text)
        self.assertIn("ref_mismatch", text)
        self.assertEqual(self.local_tip(), before)

    def test_fold_error_from_the_plan_checkpoint_becomes_a_flow_refusal(self):
        import types

        import flow_record
        import fold

        self._plan_unit()
        f.run_git(self.repo, self.env, "switch", "-q", "--detach")
        args = types.SimpleNamespace(repo=str(self.repo), plan=f.SP_PLAN, base=None)
        unit = types.SimpleNamespace(id="demo-plan", target="main")
        with self.assertRaises(flow_record.FlowError) as raised:
            fold._plan_step(args, unit)([])
        self.assertEqual(raised.exception.reason, "detached_head")


GSD_PLANS = [{"plan": "01", "stems": ["a", "b"]},
             {"plan": "02", "stems": ["c", "d"], "summary": False}]


class _GsdCase(_FlowCase):
    """A GSD phase 07 on gsd/phase-07-demo: plan 01 finished, plan 02 unfinished (no SUMMARY)."""

    @classmethod
    def setUpClass(cls):
        cls.scratch = pathlib.Path(tempfile.mkdtemp(prefix="ai-kit-p29.1-gsd-"))
        cls.addClassCleanup(shutil.rmtree, cls.scratch, True)
        template = cls.scratch / "template"
        template.mkdir()
        env = f.git_env(template / "home")
        (template / "home").mkdir()
        repo = f.gsd_project(template, env, "sequential", GSD_PLANS)
        f.make_remote(template, env, repo)
        cls.template_root = str(template)

    def _start_phase(self):
        self.grant()
        code, text = self.fold("start", "--phase", "07")
        self.assertEqual(code, 0, text)

    def _finish_plan_two(self):
        self.commit({f"{f.PHASE_DIR}/07-02-SUMMARY.md": b"summary 07-02\n"},
                    "docs(07-02): complete plan")

    def _verification(self, status):
        path = self.repo / f.PHASE_DIR / "07-VERIFICATION.md"
        path.write_text(f"---\nstatus: {status}\n---\n", encoding="utf-8")


class TestGsdPhase(_GsdCase):
    """A GSD phase checkpoints per finished plan; ready follows the verification signal."""

    def test_checkpoint_after_each_plan_pushes_the_phase_branch(self):
        self._start_phase()
        code, text = self.fold("checkpoint", "--phase", "07")
        self.assertEqual(code, 0, text)
        first = self.remote_sha(f.PHASE_BRANCH)
        self.assertEqual(first, self.ref_sha(f"refs/heads/{f.PHASE_BRANCH}"))
        self._finish_plan_two()
        code, text = self.fold("checkpoint", "--phase", "07")
        self.assertEqual(code, 0, text)
        second = self.remote_sha(f.PHASE_BRANCH)
        self.assertNotEqual(first, second)
        self.assertEqual(second, self.ref_sha(f"refs/heads/{f.PHASE_BRANCH}"))

    def test_ready_refuses_gaps_found_and_marks_ready_after_passed(self):
        self._start_phase()
        self._finish_plan_two()
        code, text = self.fold("checkpoint", "--phase", "07")
        self.assertEqual(code, 0, text)
        self._verification("gaps_found")
        code, text = self.fold("ready", "--phase", "07")
        self.assertEqual(code, 1, text)
        self.assertIn("not_verified", text)
        self.assertTrue(forge_fakes.forge_state(self.state)["prs"][0]["isDraft"])
        self.assertEqual(self.record()["units"][0]["state"], "finished")
        self._verification("passed")
        code, text = self.fold("ready", "--phase", "07")
        self.assertEqual(code, 0, text)
        self.assertFalse(forge_fakes.forge_state(self.state)["prs"][0]["isDraft"])
        self.assertEqual(self.record()["units"][0]["state"], "ready")


if __name__ == "__main__":
    unittest.main()
