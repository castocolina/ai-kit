"""Checkpoint flow tests (plan 29.1-02): push at every checkpoint, PR backends, MVP fast path.

Each class builds on the template fixture of tests.test_flow_contract (one copy of a repo with
a local bare remote per test, fresh fake forge state and log, consent granted in the copy).
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


class _UnitCase(_FlowCase):
    """Unit-contract checkpoints: one checkpoint file per call, the HEAD commit as its tip."""

    def _checkpoint_unit(self, unit_id, branch, base_rev, files, mvp=False, kind="stacked",
                         final=False):
        tip = f.run_git(self.repo, self.env, "rev-parse", "HEAD").strip()
        base = f.run_git(self.repo, self.env, "rev-parse", base_rev).strip()
        cp = f.write_checkpoint(
            self.dest / f"cp-{unit_id}.json", schema=1, unit=unit_id, ref=f"refs/heads/{branch}",
            base=base, end=tip, tip=tip, base_branch="main", merged_refs=[],
            own_merge_subjects=[], docs_paths=[],
            candidates=[{"id": "t1", "title": unit_id, "files": files}])
        extra = {"kind": kind, **({"mvp": True} if mvp else {})}
        args = ["checkpoint", "--unit", self.unit(unit_id, branch, unit_id.title(), **extra),
                "--checkpoint", str(cp)]
        return self.fold(*(args + (["--final"] if final else [])))


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


class TestFetchPushRace(_PlanCase):
    """A remote move that lands between the checkpoint's fetch and its push is refused."""

    def test_remote_moved_right_after_the_fetch_is_refused_by_the_recorded_lease(self):
        self._plan_unit()
        self.commit({"a.py": b"a\n"}, "feat: add a")
        code, text = self.checkpoint_plan()
        self.assertEqual(code, 0, text)
        clone = self.dest / "clone"
        subprocess.run(["git", "clone", "-q", str(self.bare), str(clone)], env=self.env,
                       check=True, capture_output=True)
        f.run_git(clone, self.env, "checkout", "-q", "-b", PLAN_BRANCH, f"origin/{PLAN_BRANCH}")
        other = f.commit(clone, self.env, {"other.py": b"o\n"}, "feat: other clone")
        real_git = shutil.which("git")
        wrap_dir = self.dest / "racewrap"
        wrap_dir.mkdir()
        mark = self.dest / "raced"
        wrapper = wrap_dir / "git"
        wrapper.write_text(
            "#!/bin/sh\n"
            f"'{real_git}' \"$@\"\n"
            "rc=$?\n"
            "case \" $* \" in\n"
            "  *\" fetch \"*)\n"
            f"    if [ ! -e '{mark}' ]; then\n"
            f"      touch '{mark}'\n"
            f"      '{real_git}' -C '{clone}' push -q origin {PLAN_BRANCH} || true\n"
            "    fi;;\n"
            "esac\n"
            "exit $rc\n", encoding="utf-8")
        wrapper.chmod(0o755)
        self.env["PATH"] = f"{wrap_dir}:{self.env['PATH']}"
        self.commit({"b.py": b"b\n"}, "feat: add b")
        code, text = self.checkpoint_plan()
        self.assertEqual(code, 1, text)
        self.assertIn("stale_lease", text)
        self.assertTrue(mark.exists())
        self.assertEqual(self.remote_sha(PLAN_BRANCH), other)


class TestPrBackends(_UnitCase):
    """Two units stacked (demo/unit-a then demo/unit-b): both PR backends give the same bases."""

    def _stack_two(self, env=None):
        self.grant()
        code, text = self.fold("start", "--unit", self.unit("unit-a", "demo/unit-a", "Unit A"))
        self.assertEqual(code, 0, text)
        f.run_git(self.repo, self.env, "switch", "-q", "demo/unit-a")
        self.commit({"a.py": b"a\n"}, "feat: add a")
        self.commit({"tests/test_a.py": b"ta\n"}, "test: cover a")
        code, text = self._checkpoint_unit("unit-a", "demo/unit-a", "main",
                                           ["a.py", "tests/test_a.py"])
        self.assertEqual(code, 0, text)
        code, text = self.fold("start", "--unit", self.unit("unit-b", "demo/unit-b", "Unit B"))
        self.assertEqual(code, 0, text)
        self.commit({"b.py": b"b\n"}, "feat: add b")
        self.commit({"tests/test_b.py": b"tb\n"}, "test: cover b")
        tip_a = self.ref_sha("refs/heads/demo/unit-a")
        code, text = self._checkpoint_unit("unit-b", "demo/unit-b", tip_a,
                                           ["b.py", "tests/test_b.py"])
        return code, text

    def _bases(self):
        prs = forge_fakes.forge_state(self.state)["prs"]
        return [(pr["baseRefName"], pr["isDraft"]) for pr in prs]

    def test_gh_stack_gives_one_chained_draft_per_unit(self):
        self.env["AI_KIT_FLOW_PR_BACKEND"] = "gh-stack"
        code, text = self._stack_two()
        self.assertEqual(code, 0, text)
        self.assertEqual(self._bases(), [("main", True), ("demo/unit-a", True)])
        self.assertIn("pr backend: gh-stack", text)

    def test_plain_gh_gives_the_same_bases_per_pr(self):
        self.env["AI_KIT_FLOW_PR_BACKEND"] = "gh"
        code, text = self._stack_two()
        self.assertEqual(code, 0, text)
        self.assertEqual(self._bases(), [("main", True), ("demo/unit-a", True)])
        self.assertIn("pr backend: gh", text)

    def test_gh_stack_init_adopts_recorded_branches_and_link_gets_pr_urls_only(self):
        self.env["AI_KIT_FLOW_PR_BACKEND"] = "gh-stack"
        code, text = self._stack_two()
        self.assertEqual(code, 0, text)
        calls = [c["argv"] for c in self.gh_calls() if c["argv"][:1] == ["stack"]]
        inits = [argv for argv in calls if argv[1] == "init"]
        links = [argv for argv in calls if argv[1] == "link"]
        self.assertEqual(inits[-1][-2:], ["demo/unit-a", "demo/unit-b"])
        self.assertTrue(links[-1][-2].endswith("/pull/1"), links[-1])
        self.assertTrue(links[-1][-1].endswith("/pull/2"), links[-1])
        for argv in calls:
            self.assertNotIn(argv[1], ("submit", "push"), argv)

    def test_failing_gh_stack_verb_falls_back_to_plain_gh_with_the_same_bases(self):
        real = pathlib.Path(self.bin) / "gh"
        wrapper_dir = self.dest / "wrap"
        wrapper_dir.mkdir()
        wrapper = wrapper_dir / "gh"
        wrapper.write_text(
            "#!" + sys.executable + "\n"
            "import subprocess, sys\n"
            "args = sys.argv[1:]\n"
            "if args[:1] == ['stack'] and args[1:2] != ['--help']:\n"
            "    sys.stderr.write('gh stack: simulated failure\\n')\n"
            "    sys.exit(1)\n"
            f"sys.exit(subprocess.run([{str(real)!r}, *args]).returncode)\n",
            encoding="utf-8")
        wrapper.chmod(0o755)
        self.env["PATH"] = f"{wrapper_dir}:{self.env['PATH']}"
        self.env["AI_KIT_FLOW_PR_BACKEND"] = "gh-stack"
        code, text = self._stack_two()
        self.assertEqual(code, 0, text)
        self.assertEqual(self._bases(), [("main", True), ("demo/unit-a", True)])
        self.assertIn("pr backend: gh (gh-stack failed: gh stack: simulated failure)", text)

    def _no_gh_path(self):
        bare_dir = self.dest / "nogh"
        bare_dir.mkdir()
        for tool in ("git", "sh"):
            found = shutil.which(tool)
            if found:
                (bare_dir / tool).symlink_to(found)
        self.env["PATH"] = str(bare_dir)

    def test_no_gh_on_path_pushes_and_says_no_pr_was_opened(self):
        self.grant()
        self._no_gh_path()
        code, text = self.fold("start", "--unit", self.unit("unit-a", "demo/unit-a", "Unit A"))
        self.assertEqual(code, 0, text)
        f.run_git(self.repo, self.env, "switch", "-q", "demo/unit-a")
        self.commit({"a.py": b"a\n"}, "feat: add a")
        self.commit({"tests/test_a.py": b"ta\n"}, "test: cover a")
        code, text = self._checkpoint_unit("unit-a", "demo/unit-a", "main",
                                           ["a.py", "tests/test_a.py"])
        self.assertEqual(code, 0, text)
        self.assertEqual(self.remote_sha("demo/unit-a"), self.ref_sha("refs/heads/demo/unit-a"))
        self.assertIn("no PR opened: gh not found", text)

    def test_gh_not_signed_in_pushes_and_says_so(self):
        forge_fakes.write_forge_fakes(self.bin, self.state, self.log, gh_stack=True,
                                      signed_in=False)
        self.grant()
        code, text = self.fold("start", "--unit", self.unit("unit-a", "demo/unit-a", "Unit A"))
        self.assertEqual(code, 0, text)
        f.run_git(self.repo, self.env, "switch", "-q", "demo/unit-a")
        self.commit({"a.py": b"a\n"}, "feat: add a")
        self.commit({"tests/test_a.py": b"ta\n"}, "test: cover a")
        code, text = self._checkpoint_unit("unit-a", "demo/unit-a", "main",
                                           ["a.py", "tests/test_a.py"])
        self.assertEqual(code, 0, text)
        self.assertEqual(self.remote_sha("demo/unit-a"), self.ref_sha("refs/heads/demo/unit-a"))
        self.assertIn("no PR opened: gh not signed in", text)

    def test_non_github_primary_remote_pushes_and_opens_no_pr(self):
        self.grant()
        f.run_git(self.repo, self.env, "remote", "set-url", "origin", str(self.bare))
        code, text = self.fold("start", "--unit", self.unit("unit-a", "demo/unit-a", "Unit A"))
        self.assertEqual(code, 0, text)
        f.run_git(self.repo, self.env, "switch", "-q", "demo/unit-a")
        self.commit({"a.py": b"a\n"}, "feat: add a")
        self.commit({"tests/test_a.py": b"ta\n"}, "test: cover a")
        code, text = self._checkpoint_unit("unit-a", "demo/unit-a", "main",
                                           ["a.py", "tests/test_a.py"])
        self.assertEqual(code, 0, text)
        self.assertEqual(self.remote_sha("demo/unit-a"), self.ref_sha("refs/heads/demo/unit-a"))
        self.assertEqual([c for c in self.gh_calls() if c["argv"][:1] == ["pr"]], [])
        self.assertIn("PRs not supported on this remote", text)


class TestBottomUpReady(_UnitCase):
    """Three stacked units finished without consent, then one catch-up run with consent: the
    pending tips are pushed bottom-up and ready is set bottom-up, never above a draft."""

    def test_catch_up_run_marks_units_ready_bottom_up_and_refuses_a_unit_above_a_draft(self):
        names = ("a", "b", "c")
        for index, name in enumerate(names):
            unit_id, branch = f"unit-{name}", f"demo/unit-{name}"
            code, text = self.fold("start", "--unit", self.unit(unit_id, branch, name.upper()))
            self.assertEqual(code, 0, text)
            f.run_git(self.repo, self.env, "switch", "-q", branch)
            self.commit({f"{name}.py": b"x\n"}, f"feat: add {name}")
            self.commit({f"tests/test_{name}.py": b"t\n"}, f"test: cover {name}")
            base = "main" if index == 0 else f"demo/unit-{names[index - 1]}"
            code, text = self._checkpoint_unit(unit_id, branch, base,
                                               [f"{name}.py", f"tests/test_{name}.py"],
                                               final=True)
            self.assertEqual(code, 0, text)
            self.assertIn("skipped (no consent)", text)
        self.grant()
        code, text = self.fold("ready", "--unit", self.unit("unit-c", "demo/unit-c", "C"))
        self.assertEqual(code, 1, text)
        self.assertIn("signal_order", text)
        for name in names:
            code, text = self.fold("ready", "--unit", self.unit(f"unit-{name}",
                                                                 f"demo/unit-{name}"))
            self.assertEqual(code, 0, text)
        readies = [c["argv"][2] for c in self.gh_calls() if c["argv"][:2] == ["pr", "ready"]]
        self.assertEqual(readies, ["1", "2", "3"])
        for name in names:
            self.assertEqual(self.remote_sha(f"demo/unit-{name}"),
                             self.ref_sha(f"refs/heads/demo/unit-{name}"))


class TestMvp(_UnitCase):
    """The MVP fast path: the target fast-forwards to the unit tip, pushed plainly, no PR."""

    def _mvp_start(self, unit_id="unit-a", branch="demo/unit-a", kind="stacked"):
        self.grant()
        code, text = self.fold("start", "--unit",
                               self.unit(unit_id, branch, unit_id.title(), mvp=True, kind=kind))
        self.assertEqual(code, 0, text)
        f.run_git(self.repo, self.env, "switch", "-q", branch)

    def _pr_creates(self):
        return [c["argv"] for c in self.gh_calls() if c["argv"][:2] == ["pr", "create"]]

    def _main_tip(self):
        return self.ref_sha("refs/heads/main")

    def test_main_only_fixture_moves_main_to_the_unit_tip_at_each_checkpoint_with_no_pr(self):
        self._mvp_start()
        self.commit({"a.py": b"a\n"}, "feat: add a")
        self.commit({"tests/test_a.py": b"ta\n"}, "test: cover a")
        code, text = self._checkpoint_unit("unit-a", "demo/unit-a", "main",
                                           ["a.py", "tests/test_a.py"], mvp=True)
        self.assertEqual(code, 0, text)
        tip = self.ref_sha("refs/heads/demo/unit-a")
        self.assertEqual((self.remote_sha("main"), self._main_tip()), (tip, tip))
        self.commit({"b.py": b"b\n"}, "feat: add b")
        self.commit({"tests/test_b.py": b"tb\n"}, "test: cover b")
        code, text = self._checkpoint_unit("unit-a", "demo/unit-a", "main",
                                           ["b.py", "tests/test_b.py"], mvp=True)
        self.assertEqual(code, 0, text)
        tip = self.ref_sha("refs/heads/demo/unit-a")
        self.assertEqual((self.remote_sha("main"), self._main_tip()), (tip, tip))
        self.assertEqual(self._pr_creates(), [])

    def test_mvp_unit_above_an_unmerged_unit_is_refused_and_opens_a_draft_pr_instead(self):
        self.grant()
        code, text = self.fold("start", "--unit", self.unit("unit-a", "demo/unit-a", "A"))
        self.assertEqual(code, 0, text)
        f.run_git(self.repo, self.env, "switch", "-q", "demo/unit-a")
        self.commit({"a.py": b"a\n"}, "feat: add a")
        self.commit({"tests/test_a.py": b"ta\n"}, "test: cover a")
        code, text = self._checkpoint_unit("unit-a", "demo/unit-a", "main",
                                           ["a.py", "tests/test_a.py"])
        self.assertEqual(code, 0, text)
        main_before = self.remote_sha("main")
        code, text = self.fold("start", "--unit",
                               self.unit("unit-b", "demo/unit-b", "B", mvp=True))
        self.assertEqual(code, 0, text)
        self.commit({"b.py": b"b\n"}, "feat: add b")
        self.commit({"tests/test_b.py": b"tb\n"}, "test: cover b")
        code, text = self._checkpoint_unit("unit-b", "demo/unit-b", "demo/unit-a",
                                           ["b.py", "tests/test_b.py"], mvp=True)
        self.assertEqual(code, 0, text)
        self.assertIn("mvp_below_unmerged", text)
        self.assertEqual(self.remote_sha("main"), main_before)
        self.assertEqual(len(self._pr_creates()), 2)

    def test_remote_main_moved_beyond_the_unit_is_refused_and_main_stays(self):
        self._mvp_start()
        self.commit({"a.py": b"a\n"}, "feat: add a")
        clone = self.dest / "clone"
        subprocess.run(["git", "clone", "-q", str(self.bare), str(clone)], env=self.env,
                       check=True, capture_output=True)
        other = f.commit(clone, self.env, {"hotfix.txt": b"x\n"}, "fix: other main commit")
        f.run_git(clone, self.env, "push", "-q", "origin", "main")
        code, text = self._checkpoint_unit("unit-a", "demo/unit-a", "main",
                                           ["a.py"], mvp=True)
        self.assertEqual(code, 1, text)
        # sync cascades the unit onto the moved trunk before the MVP checks (plan 03), so the
        # tested-tip guard refuses branch_moved; mvp_diverged covers the local-target-ahead case.
        self.assertIn("branch_moved", text)
        self.assertEqual(self.remote_sha("main"), other)

    def test_mvp_checkpoint_with_nothing_new_makes_no_push(self):
        self._mvp_start()
        self.commit({"a.py": b"a\n"}, "feat: add a")
        code, text = self._checkpoint_unit("unit-a", "demo/unit-a", "main", ["a.py"], mvp=True)
        self.assertEqual(code, 0, text)
        main_before = self.remote_sha("main")
        code, text = self._checkpoint_unit("unit-a", "demo/unit-a", "main", ["a.py"], mvp=True)
        self.assertEqual(code, 0, text)
        self.assertIn("nothing to push", text)
        self.assertEqual(self.remote_sha("main"), main_before)

    def test_hotfix_unit_fast_forwards_into_its_target(self):
        self._mvp_start("hot-1", "demo/hot-1", kind="hotfix")
        self.commit({"fix.py": b"fix\n"}, "fix: hot")
        code, text = self._checkpoint_unit("hot-1", "demo/hot-1", "main", ["fix.py"],
                                           mvp=True, kind="hotfix")
        self.assertEqual(code, 0, text)
        tip = self.ref_sha("refs/heads/demo/hot-1")
        self.assertEqual(self.remote_sha("main"), tip)

    def test_local_target_ahead_is_refused_and_its_commit_stays(self):
        self._mvp_start()
        f.run_git(self.repo, self.env, "switch", "-q", "main")
        extra = self.commit({"extra.txt": b"e\n"}, "docs: local main only")
        f.run_git(self.repo, self.env, "switch", "-q", "demo/unit-a")
        remote_before = self.remote_sha("main")
        self.commit({"a.py": b"a\n"}, "feat: add a")
        code, text = self._checkpoint_unit("unit-a", "demo/unit-a", remote_before, ["a.py"],
                                           mvp=True)
        self.assertEqual(code, 1, text)
        self.assertIn("mvp_diverged", text)
        self.assertEqual(self._main_tip(), extra)
        self.assertEqual(self.remote_sha("main"), remote_before)

    def test_target_checked_out_in_a_worktree_is_refused_and_named(self):
        self._mvp_start()
        self.commit({"a.py": b"a\n"}, "feat: add a")
        worktree = self.dest / "main-wt"
        f.run_git(self.repo, self.env, "worktree", "add", str(worktree), "main")
        main_before = self.remote_sha("main")
        local_before = self._main_tip()
        code, text = self._checkpoint_unit("unit-a", "demo/unit-a", "main", ["a.py"], mvp=True)
        self.assertEqual(code, 1, text)
        self.assertIn("mvp_target_checked_out", text)
        self.assertIn(worktree.name, text)
        self.assertEqual(self._main_tip(), local_before)
        self.assertEqual(self.remote_sha("main"), main_before)

    def test_failed_target_push_leaves_local_ahead_and_an_unchanged_rerun_pushes(self):
        self._mvp_start()
        self.commit({"a.py": b"a\n"}, "feat: add a")
        hook = self.bare / "hooks" / "pre-receive"
        hook.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
        hook.chmod(0o755)
        main_before = self.remote_sha("main")
        code, text = self._checkpoint_unit("unit-a", "demo/unit-a", "main", ["a.py"], mvp=True)
        self.assertEqual(code, 1, text)
        self.assertIn("target push failed; local main is ahead", text)
        tip = self.ref_sha("refs/heads/demo/unit-a")
        self.assertEqual(self._main_tip(), tip)
        self.assertEqual(self.remote_sha("main"), main_before)
        hook.unlink()
        code, text = self._checkpoint_unit("unit-a", "demo/unit-a", "main", ["a.py"], mvp=True)
        self.assertEqual(code, 0, text)
        self.assertEqual(self.remote_sha("main"), tip)


if __name__ == "__main__":
    unittest.main()
