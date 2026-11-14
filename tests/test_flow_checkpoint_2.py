"""Checkpoint flow tests, part 2: the start keeps a local plan, the fetch-push race, PR backends,
bottom-up ready and the MVP fast path.

Split from tests/test_flow_checkpoint.py by test class so the parts run in parallel.
"""

import pathlib
import shutil
import subprocess
import sys
import unittest

_REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "skills" / "ai-kit-commit-fold" / "scripts"))
sys.path.insert(0, str(_REPO))

from tests import fold_fixtures as f
from tests import forge_fakes
from tests.test_flow_checkpoint import PLAN_BRANCH, _PlanCase
from tests.test_flow_contract import BRANCH, _FlowCase

SP_SPEC = "docs/superpowers/specs/2026-11-04-demo-design.md"


FAKE_TOKEN = "ghp_" + "A" * 36  # token-shaped, never real


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


class TestStartKeepsLocalPlan(_FlowCase):
    """start --plan / --phase keeps a plan committed only locally (the planning skills commit)."""

    def _log(self, ref):
        return f.run_git(self.repo, self.env, "log", "--format=%s", ref).splitlines()

    def _local_plan(self, text=f.SP_PLAN_TEXT):
        f.run_git(self.repo, self.env, "switch", "-q", "main")
        return self.commit({f.SP_PLAN: text.encode()}, "docs: add plan (local)")

    def test_unpushed_plan_on_main_starts_the_unit_at_head_and_stays_outside_the_fold(self):
        self.grant()
        plan_commit = self._local_plan()
        code, text = self.fold("start", "--plan", f.SP_PLAN)
        self.assertEqual(code, 0, text)
        self.assertIn("carried 1 local commit(s) from main", text)
        self.assertTrue((self.repo / f.SP_PLAN).is_file())
        self.assertEqual(self.record()["units"][0]["carried"], 1)
        self.assertEqual(self.ref_sha("HEAD"), plan_commit)
        self.commit({"a.py": b"a\n"}, "feat: add a")
        self.commit({"tests/test_a.py": b"ta\n"}, "test: cover a")
        code, text = self.fold("checkpoint", "--plan", f.SP_PLAN, "--final")
        self.assertEqual(code, 0, text)
        self.assertIn("docs: add plan (local)", self._log(PLAN_BRANCH))
        f.run_git(self.repo, self.env, "merge-base", "--is-ancestor", plan_commit, PLAN_BRANCH)

    def test_unpushed_plan_below_a_stacked_unit_is_cherry_picked_and_main_keeps_it(self):
        self.grant()
        code, text = self.fold("start", "--unit", self.unit())
        self.assertEqual(code, 0, text)
        self.commit({"x.py": b"x\n"}, "feat: unit a")
        plan_commit = self._local_plan()
        code, text = self.fold("start", "--plan", f.SP_PLAN)
        self.assertEqual(code, 0, text)
        self.assertIn("by cherry-pick", text)
        self.assertTrue((self.repo / f.SP_PLAN).is_file())
        self.assertEqual(self.ref_sha("refs/heads/main"), plan_commit)
        self.assertEqual(self._log(PLAN_BRANCH)[:2], ["docs: add plan (local)", "feat: unit a"])
        self.assertEqual(self.record()["units"][1]["parent"], BRANCH)

    def test_unrelated_local_commit_stays_off_the_unit_while_the_plan_is_carried(self):
        self.grant()
        f.run_git(self.repo, self.env, "switch", "-q", "main")
        wip = self.commit({"wip.py": b"wip\n"}, "wip: unrelated local work")
        plan_commit = self._local_plan()
        code, text = self.fold("start", "--plan", f.SP_PLAN)
        self.assertEqual(code, 0, text)
        self.assertIn("by cherry-pick", text)
        self.assertEqual(self._log(PLAN_BRANCH)[:2], ["docs: add plan (local)", "chore: base"])
        self.assertFalse((self.repo / "wip.py").exists())
        self.assertEqual(self.record()["units"][0]["carried"], 1)
        self.assertEqual(f.run_git(self.repo, self.env, "branch", "--show-current").strip(),
                         PLAN_BRANCH)
        self.assertEqual(self.ref_sha("refs/heads/main"), plan_commit)
        f.run_git(self.repo, self.env, "merge-base", "--is-ancestor", wip, "main")

    def _spec_then_plan(self, between=None):
        """superpowers' order: the spec committed alone, then the plan naming it (**Spec:**)."""
        f.run_git(self.repo, self.env, "switch", "-q", "main")
        self.commit({SP_SPEC: b"# Demo design\n"}, "docs: add demo design spec")
        if between:
            self.commit(between, "wip: unrelated local work")
        text = f.SP_PLAN_TEXT.replace("\n\n", f"\n\n**Spec:** `{SP_SPEC}`\n\n", 1)
        return self.commit({f.SP_PLAN: text.encode()}, "docs: add plan (local)")

    def test_separately_committed_spec_is_carried_with_the_plan(self):
        self.grant()
        plan_commit = self._spec_then_plan()
        code, text = self.fold("start", "--plan", f.SP_PLAN)
        self.assertEqual(code, 0, text)
        self.assertIn("carried 2 local commit(s) from main", text)
        self.assertEqual(self.ref_sha("HEAD"), plan_commit)
        self.assertTrue((self.repo / SP_SPEC).is_file())
        self.assertEqual(self.record()["units"][0]["carried"], 2)

    def test_spec_is_cherry_picked_with_the_plan_and_unrelated_work_stays_off(self):
        self.grant()
        self._spec_then_plan(between={"wip.py": b"wip\n"})
        code, text = self.fold("start", "--plan", f.SP_PLAN)
        self.assertEqual(code, 0, text)
        self.assertIn("carried 2 local commit(s) from main by cherry-pick", text)
        self.assertEqual(self._log(PLAN_BRANCH)[:3],
                         ["docs: add plan (local)", "docs: add demo design spec", "chore: base"])
        self.assertTrue((self.repo / SP_SPEC).is_file())
        self.assertFalse((self.repo / "wip.py").exists())

    def test_plan_that_cannot_be_carried_cleanly_refuses_and_changes_nothing(self):
        self.grant()
        self.fold("start", "--unit", self.unit())
        self.commit({f.SP_PLAN: b"# Other plan\n"}, "docs: other plan on unit a")
        self._local_plan()
        before = self.ref_sha("refs/heads/main")
        code, text = self.fold("start", "--plan", f.SP_PLAN)
        self.assertEqual(code, 1, text)
        self.assertIn("refused plan_not_carried", text)
        self.assertIn("git cherry-pick", text)
        self.assertEqual(f.run_git(self.repo, self.env, "branch", "--show-current").strip(),
                         "main")
        self.assertEqual(self.ref_sha("refs/heads/main"), before)
        self.assertEqual(f.run_git(self.repo, self.env, "branch", "--list", PLAN_BRANCH), "")
        self.assertEqual(len(self.record()["units"]), 1)

    def test_unpushed_gsd_phase_dir_on_main_is_kept_and_the_plan_folds(self):
        self.grant()
        f.run_git(self.repo, self.env, "switch", "-q", "main")
        plan = f.gsd_plan_text("01", ["a", "b"]).encode()
        self.commit({f"{f.PHASE_DIR}/07-01-PLAN.md": plan}, "docs(07): create phase plan")
        code, text = self.fold("start", "--phase", "07")
        self.assertEqual(code, 0, text)
        self.assertIn("carried 1 local commit(s)", text)
        self.assertTrue((self.repo / f.PHASE_DIR / "07-01-PLAN.md").is_file())
        for files, message, _author in f.gsd_plan_commits("01", ["a", "b"]):
            self.commit(files, message)
        code, text = self.fold("checkpoint", "--phase", "07")
        self.assertEqual(code, 0, text)
        self.assertIn("folded", text)
        self.assertIn("docs(07): create phase plan", self._log(f.PHASE_BRANCH))


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

    def _stack_one(self):
        self.grant()
        code, text = self.fold("start", "--unit", self.unit("unit-a", "demo/unit-a", "Unit A"))
        self.assertEqual(code, 0, text)
        f.run_git(self.repo, self.env, "switch", "-q", "demo/unit-a")
        self.commit({"a.py": b"a\n"}, "feat: add a")
        self.commit({"tests/test_a.py": b"ta\n"}, "test: cover a")
        return self._checkpoint_unit("unit-a", "demo/unit-a", "main",
                                     ["a.py", "tests/test_a.py"])

    def _stack_two(self, env=None):
        code, text = self._stack_one()
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

    def test_gh_stack_with_one_unit_calls_no_stack_verb(self):
        self.env["AI_KIT_FLOW_PR_BACKEND"] = "gh-stack"
        code, text = self._stack_one()
        self.assertEqual(code, 0, text)
        self.assertIn("draft PR 1 (pr backend: gh-stack, nothing to link yet)", text)
        self.assertEqual([c for c in self.gh_calls() if c["argv"][:1] == ["stack"]], [])

    def test_gh_stack_links_the_chain_by_pr_url_once_a_second_unit_exists(self):
        self.env["AI_KIT_FLOW_PR_BACKEND"] = "gh-stack"
        code, text = self._stack_two()
        self.assertEqual(code, 0, text)
        calls = [c["argv"] for c in self.gh_calls() if c["argv"][:1] == ["stack"]]
        links = [argv for argv in calls if argv[1] == "link"]
        self.assertEqual(len(links), 1, calls)
        self.assertEqual(links[0][2:4], ["--base", "main"])
        self.assertTrue(links[0][-2].endswith("/pull/1"), links[0])
        self.assertTrue(links[0][-1].endswith("/pull/2"), links[0])
        for argv in calls:
            self.assertNotIn(argv[1], ("init", "submit", "push"), argv)

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
            "    print('gh stack: progress on stdout')\n"
            f"    sys.stderr.write('gh stack: simulated failure {FAKE_TOKEN}\\n')\n"
            "    sys.exit(1)\n"
            f"sys.exit(subprocess.run([{str(real)!r}, *args]).returncode)\n",
            encoding="utf-8")
        wrapper.chmod(0o755)
        self.env["PATH"] = f"{wrapper_dir}:{self.env['PATH']}"
        self.env["AI_KIT_FLOW_PR_BACKEND"] = "gh-stack"
        code, text = self._stack_two()
        self.assertEqual(code, 0, text)
        self.assertEqual(self._bases(), [("main", True), ("demo/unit-a", True)])
        self.assertIn("pr backend: gh (gh-stack failed: gh stack: simulated failure [redacted])",
                      text)
        self.assertNotIn(FAKE_TOKEN, text)

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
                                           ["a.py", "tests/test_a.py"], final=True)
        self.assertEqual(code, 0, text)
        self.assertEqual(self.remote_sha("demo/unit-a"), self.ref_sha("refs/heads/demo/unit-a"))
        self.assertEqual([c for c in self.gh_calls() if c["argv"][:1] == ["pr"]], [])
        self.assertIn("PRs not supported on this remote", text)
        code, text = self.fold("ready", "--unit", self.unit("unit-a", "demo/unit-a", "Unit A"))
        self.assertEqual(code, 0, text)
        self.assertIn("no PR to mark ready", text)


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
