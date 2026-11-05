"""Stack reconciliation tests (plan 29.1-03 Task 1): the cascade, restore and preflights.

Each class builds one template repository with a local bare remote; each test copies it,
rebinds the remote and grants consent in its own copy. Only the plain git rebase is covered
here: the gh-stack backend, conflict resolution with gates, the hotfix and the merge chain are
not built yet (plan 29.1-03 Tasks 2 and 3).
"""

import argparse
import contextlib
import io
import json
import os
import pathlib
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

_REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "skills" / "ai-kit-commit-fold" / "scripts"))
sys.path.insert(0, str(_REPO))

import flow_record
import flow_stack

from tests import fold_fixtures as f
from tests import forge_fakes, host_fakes

FOLD = _REPO / "skills" / "ai-kit-commit-fold" / "scripts" / "fold.py"
BR_A = "demo/unit-a"
BR_B = "demo/unit-b"
BR_C = "demo/unit-c"


class _StackCase(unittest.TestCase):
    """One copy of the template per test: own remote, own consent, own record."""

    template_root: str = ""

    @classmethod
    def setUpClass(cls):
        cls.scratch = pathlib.Path(tempfile.mkdtemp(prefix="ai-kit-p29.1-stack-"))
        cls.addClassCleanup(shutil.rmtree, cls.scratch, True)
        template = cls.scratch / "template"
        template.mkdir()
        env = f.git_env(template / "home")
        (template / "home").mkdir()
        repo = f.make_repo(template, env)
        f.make_remote(template, env, repo)
        cls.template_root = str(template)

    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp(prefix="case-", dir=self.scratch))
        self.dest = self.root / "copy"
        shutil.copytree(self.template_root, self.dest)
        self.repo = self.dest / "repo"
        self.bare = self.dest / "remote.git"
        self.env = f.git_env(self.dest / "home")
        self.env.pop("GH_TOKEN", None)
        self.env.pop("GITHUB_TOKEN", None)
        f.rebind(self.dest, self.env, self.repo, self.bare)
        self.clones = 0
        code, text = self.fold("consent", "grant", "--add-exclude")
        self.assertEqual(code, 0, text)

    def fold(self, *args):
        proc = subprocess.run(
            [sys.executable, str(FOLD), *args, "--repo", str(self.repo)],
            capture_output=True, text=True, env=self.env, check=False)
        return proc.returncode, proc.stdout + proc.stderr

    def start_unit(self, unit_id, branch):
        path = self.dest / f"{unit_id}.json"
        path.write_text(json.dumps({"schema": 1, "id": unit_id, "kind": "stacked",
                                    "branch": branch, "title": f"Unit {unit_id}"}),
                        encoding="utf-8")
        code, text = self.fold("start", "--unit", str(path))
        self.assertEqual(code, 0, text)

    def commit(self, files, message):
        return f.commit(self.repo, self.env, files, message)

    def publish(self, branch):
        """Push a unit branch to origin and record its pushed sha, as a checkpoint would."""
        f.run_git(self.repo, self.env, "push", "-q", "origin", branch)
        path = self.repo / ".git" / "ai-kit-stack.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        for entry in data["units"]:
            if entry["branch"] == branch:
                entry["pushed"] = self.rev(f"refs/heads/{branch}")
        path.write_text(json.dumps(data), encoding="utf-8")

    def build_stack(self):
        """Three pushed units a, b, c, each with one commit, stacked on main."""
        for unit_id, branch, name in (("unit-a", BR_A, "a.py"), ("unit-b", BR_B, "b.py"),
                                      ("unit-c", BR_C, "c.py")):
            self.start_unit(unit_id, branch)
            self.commit({name: name.encode() + b"\n"}, f"feat: {unit_id}")
            self.publish(branch)

    def remote_commit(self, branch, files, message):
        """Push one commit to `branch` on the remote from a second clone."""
        self.clones += 1
        clone = self.dest / f"clone-{self.clones}"
        f.run_git(self.dest, self.env, "clone", "-q", str(self.bare), str(clone))
        f.run_git(clone, self.env, "checkout", "-q", "-B", branch, f"origin/{branch}")
        f.commit(clone, self.env, files, message)
        f.run_git(clone, self.env, "push", "-q", "origin", f"HEAD:refs/heads/{branch}")

    def rev(self, name):
        return f.run_git(self.repo, self.env, "rev-parse", "--verify", name).strip()

    def count(self, first, second):
        out = f.run_git(self.repo, self.env, "rev-list", "--count", f"{first}..{second}")
        return int(out.strip())

    def remote_tip(self, branch):
        out = f.run_git(self.repo, self.env, "ls-remote", "origin", f"refs/heads/{branch}")
        return out.split()[0]

    def local_tips(self, branches=(BR_A, BR_B, BR_C)):
        return {name: self.rev(f"refs/heads/{name}") for name in branches}

    def status(self):
        return f.run_git(self.repo, self.env, "status", "--porcelain").strip()

    def record(self):
        path = self.repo / ".git" / "ai-kit-stack.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def entry(self, unit_id):
        return next(e for e in self.record()["units"] if e["id"] == unit_id)

    def restack_file_exists(self):
        return (self.repo / ".git" / "ai-kit-restack.json").exists()


class TestFlowScriptsImport(unittest.TestCase):
    def test_flow_scripts_import(self):
        import flow_git  # noqa: F401
        import flow_pr  # noqa: F401
        import flow_unit  # noqa: F401
        import fold

        args = fold.build_parser().parse_args(["checkpoint", "--unit", "-"])
        self.assertEqual(args.command, "checkpoint")
        self.assertEqual(args.unit_file, "-")


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


class TestCascadeConflict(_StackCase):
    """A conflicting cascade pauses, resolves through --continue, gates, and pushes or restores."""

    def conflict(self):
        self.start_unit("unit-a", BR_A)
        self.commit({"shared.txt": b"a side\n"}, "feat: a shared")
        self.publish(BR_A)
        self.start_unit("unit-b", BR_B)
        self.commit({"b.py": b"b\n"}, "feat: add b")
        self.publish(BR_B)
        self.remote_commit("main", {"shared.txt": b"trunk side\n"}, "feat: trunk shared")
        code, text = self.fold("restack")
        self.assertEqual(code, 1, text)
        self.assertIn("conflict: shared.txt", text)
        return self.local_tips((BR_A, BR_B))

    def gate(self, *argv):
        code, text = self.fold("settings", "set", "--gate", shlex.join(argv))
        self.assertEqual(code, 0, text)

    def resolve(self, text=b"both sides kept\n"):
        (self.repo / "shared.txt").write_bytes(text)

    def test_continue_with_a_resolution_gates_then_pushes_atomically(self):
        before = self.conflict()
        self.resolve()
        gate = [sys.executable, "-c", "pass"]
        self.gate(*gate)
        code, text = self.fold("settings", "show")
        self.assertIn(f"gates: {shlex.join(gate)}", text)
        code, text = self.fold("restack", "--continue", "--note",
                               "shared.txt=both sides kept")
        self.assertEqual(code, 0, text)
        self.assertIn("resolved: shared.txt (both sides kept)", text)
        self.assertIn(f"gates: {shlex.join(gate)} pass", text)
        self.assertNotEqual(self.local_tips((BR_A, BR_B)), before)
        self.assertEqual(self.remote_tip(BR_A), self.rev(BR_A))
        self.assertEqual(self.remote_tip(BR_B), self.rev(BR_B))
        self.assertEqual(self.status(), "")
        self.assertFalse(self.restack_file_exists())

    def test_marker_left_in_a_file_refuses_bad_resolution_and_restores(self):
        before = self.conflict()
        self.resolve(b"<<<<<<< ours\nboth\n=======\n>>>>>>> theirs\n")
        code, text = self.fold("restack", "--continue", "--note", "shared.txt=kept")
        self.assertEqual(code, 1, text)
        self.assertIn("bad_resolution", text)
        self.assertIn("gates: none run", text)
        self.assertEqual(self.local_tips((BR_A, BR_B)), before)
        self.assertEqual(self.status(), "")
        self.assertFalse(self.restack_file_exists())

    def test_change_outside_the_conflicting_files_refuses_bad_resolution(self):
        before = self.conflict()
        self.resolve()
        (self.repo / "base.txt").write_bytes(b"edited\n")
        code, text = self.fold("restack", "--continue", "--note", "shared.txt=kept")
        self.assertEqual(code, 1, text)
        self.assertIn("bad_resolution", text)
        self.assertEqual(self.local_tips((BR_A, BR_B)), before)
        self.assertFalse(self.restack_file_exists())

    def test_no_project_gates_keeps_the_resolved_stack_local_and_unpushed(self):
        before = self.conflict()
        self.resolve()
        code, text = self.fold("restack", "--continue", "--note", "shared.txt=kept")
        self.assertEqual(code, 1, text)
        self.assertIn("refused no_gates", text)
        self.assertIn("gates: none configured", text)
        self.assertIn('fold.py settings set --gate "CMD"', text)
        self.assertNotEqual(self.remote_tip(BR_A), self.rev(BR_A))
        self.assertNotEqual(self.local_tips((BR_A, BR_B)), before)
        state = json.loads((self.repo / ".git" / "ai-kit-restack.json").read_text("utf-8"))
        self.assertTrue(state["resolved"])
        code, text = self.fold("restack")
        self.assertEqual(code, 1, text)
        self.assertIn("restack_pending", text)
        self.gate(sys.executable, "-c", "pass")
        code, text = self.fold("restack", "--continue")
        self.assertEqual(code, 0, text)
        self.assertEqual(self.remote_tip(BR_A), self.rev(BR_A))
        self.assertEqual(self.remote_tip(BR_B), self.rev(BR_B))
        self.assertFalse(self.restack_file_exists())

    def test_failing_gate_restores_every_branch(self):
        before = self.conflict()
        self.resolve()
        failing = [sys.executable, "-c", "raise SystemExit(1)"]
        self.gate(*failing)
        code, text = self.fold("restack", "--continue", "--note", "shared.txt=kept")
        self.assertEqual(code, 1, text)
        self.assertIn("gate_failed", text)
        self.assertIn(f"gates: {shlex.join(failing)} fail", text)
        self.assertEqual(self.local_tips((BR_A, BR_B)), before)
        self.assertEqual(self.remote_tip(BR_A), before[BR_A])
        self.assertEqual(self.status(), "")
        self.assertFalse(self.restack_file_exists())

    def test_branch_moved_after_the_resolution_refuses_and_names_it(self):
        before = self.conflict()
        self.resolve()
        self.fold("restack", "--continue", "--note", "shared.txt=kept")
        f.run_git(self.repo, self.env, "switch", "-q", BR_B)
        self.commit({"tamper.py": b"t\n"}, "chore: tamper")
        self.gate(sys.executable, "-c", "pass")
        code, text = self.fold("restack", "--continue")
        self.assertEqual(code, 1, text)
        self.assertIn("bad_resolution", text)
        self.assertIn(BR_B, text)
        self.assertEqual(self.local_tips((BR_A, BR_B)), before)
        self.assertFalse(self.restack_file_exists())

    def test_failing_adapter_gate_fails_before_the_project_gate(self):
        before = self.conflict()
        self.resolve()
        project = [sys.executable, "-c", "pass"]
        self.gate(*project)
        failing = [sys.executable, "-c", "raise SystemExit(1)"]
        args = argparse.Namespace(repo=self.repo, abort=False, continue_=True,
                                  note=["shared.txt=kept"], adapter_gates=[("health", failing)])
        out = io.StringIO()
        with mock.patch.dict(os.environ, self.env), contextlib.redirect_stdout(out):
            code = flow_stack.cmd_restack(args)
        text = out.getvalue()
        self.assertEqual(code, 1, text)
        self.assertIn("gate_failed", text)
        self.assertIn(f"gates: health fail; {shlex.join(project)} not run", text)
        self.assertEqual(self.local_tips((BR_A, BR_B)), before)
        self.assertEqual(self.status(), "")

    def test_passing_adapter_gate_runs_first_and_the_gates_line_lists_both(self):
        self.conflict()
        self.resolve()
        project = [sys.executable, "-c", "pass"]
        self.gate(*project)
        args = argparse.Namespace(repo=self.repo, abort=False, continue_=True,
                                  note=["shared.txt=kept"],
                                  adapter_gates=[("health", [sys.executable, "-c", "pass"])])
        out = io.StringIO()
        with mock.patch.dict(os.environ, self.env), contextlib.redirect_stdout(out):
            code = flow_stack.cmd_restack(args)
        text = out.getvalue()
        self.assertEqual(code, 0, text)
        self.assertIn(f"gates: health pass; {shlex.join(project)} pass", text)
        self.assertEqual(self.remote_tip(BR_A), self.rev(BR_A))
        self.assertEqual(self.remote_tip(BR_B), self.rev(BR_B))

    def test_abort_while_paused_restores_every_branch(self):
        before = self.conflict()
        code, text = self.fold("restack", "--abort")
        self.assertEqual(code, 0, text)
        self.assertEqual(self.local_tips((BR_A, BR_B)), before)
        self.assertEqual(self.status(), "")
        self.assertFalse(self.restack_file_exists())


class TestMergeChain(_StackCase):
    """The owner-started chain: bottom-up merges with the fake forge, stops by name, a lock."""

    def setUp(self):
        super().setUp()
        self.state = self.dest / "forge.json"
        self.log = self.dest / "gh.log"
        self.bin = self.dest / "bin"
        forge_fakes.write_forge_fakes(self.bin, self.state, self.log, gh_stack=False)
        self.env["PATH"] = host_fakes.host_path(self.bin)
        self.build_stack()
        for unit_id, branch, base in (("unit-a", BR_A, "main"), ("unit-b", BR_B, BR_A),
                                      ("unit-c", BR_C, BR_B)):
            number = self.open_pr(branch, base)
            self.set_pr_number(unit_id, number)

    def open_pr(self, head, base):
        gh = str(self.bin / "gh")
        proc = subprocess.run([gh, "pr", "create", "--repo", "ai-kit-fixture/demo", "--base",
                               base, "--head", head, "--draft", "--title", head],
                              capture_output=True, text=True, env=self.env, check=False)
        return int(proc.stdout.strip().rsplit("/", 1)[-1])

    def set_pr_number(self, unit_id, number):
        path = self.repo / ".git" / "ai-kit-stack.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        for entry in data["units"]:
            if entry["id"] == unit_id:
                entry["pr"] = number
        path.write_text(json.dumps(data), encoding="utf-8")

    def states(self):
        return {e["id"]: e["state"] for e in self.record()["units"]}

    def test_ready_units_merge_bottom_up_with_merge_commits(self):
        for number in (1, 2, 3):
            forge_fakes.set_pr(self.state, number, isDraft=False)
        code, text = self.fold("merge-chain")
        self.assertEqual(code, 0, text)
        self.assertIn("merged: unit-a (#1)", text)
        self.assertIn("merged: unit-b (#2)", text)
        self.assertIn("merged: unit-c (#3)", text)
        self.assertEqual(set(self.states().values()), {"merged"})
        self.assertEqual(
            {pr["state"] for pr in forge_fakes.forge_state(self.state)["prs"]}, {"MERGED"})

    def test_a_draft_in_the_middle_stops_the_chain_after_the_bottom_unit(self):
        forge_fakes.set_pr(self.state, 1, isDraft=False)
        code, text = self.fold("merge-chain")
        self.assertEqual(code, 0, text)
        self.assertIn("merged: unit-a (#1)", text)
        self.assertIn("stopped at unit-b: draft", text)
        self.assertEqual(self.states(), {"unit-a": "merged", "unit-b": "open", "unit-c": "open"})

    def test_a_base_mismatch_refuses_before_any_merge(self):
        forge_fakes.set_pr(self.state, 1, isDraft=False)
        forge_fakes.set_pr(self.state, 2, isDraft=False, baseRefName="main")
        code, text = self.fold("merge-chain")
        self.assertEqual(code, 1, text)
        self.assertIn("base_mismatch", text)
        self.assertEqual(set(self.states().values()), {"open"})

    def test_a_live_lock_refuses_a_second_run(self):
        lock = self.repo / ".git" / "ai-kit-flow.lock"
        lock.write_text(str(os.getpid()), encoding="utf-8")
        try:
            code, text = self.fold("merge-chain")
        finally:
            lock.unlink()
        self.assertEqual(code, 1, text)
        self.assertIn("chain_locked", text)

    def test_unit_id_refuses_a_stacked_unit(self):
        code, text = self.fold("merge-chain", "--unit-id", "unit-a")
        self.assertEqual(code, 1, text)
        self.assertIn("not_hotfix", text)

    def ready(self, *numbers):
        for number in numbers:
            forge_fakes.set_pr(self.state, number, isDraft=False)

    def rev_or_none(self, name):
        proc = subprocess.run(["git", "-C", str(self.repo), "rev-parse", "--verify", "-q", name],
                              capture_output=True, text=True, env=self.env, check=False)
        return proc.stdout.strip() or None

    def edit_units(self, edit):
        path = self.repo / ".git" / "ai-kit-stack.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        for entry in data["units"]:
            edit(entry)
        path.write_text(json.dumps(data), encoding="utf-8")

    def test_local_trunk_is_fast_forwarded_to_the_remote_trunk(self):
        self.ready(1, 2, 3)
        code, text = self.fold("merge-chain")
        self.assertEqual(code, 0, text)
        self.assertEqual(self.rev("refs/heads/main"), self.remote_tip("main"))

    def test_checkout_on_a_merged_unit_moves_to_the_next_unit_branch(self):
        f.run_git(self.repo, self.env, "switch", "-q", BR_A)
        self.ready(1, 2)
        code, text = self.fold("merge-chain")
        self.assertEqual(code, 0, text)
        self.assertIn("stopped at unit-c: draft", text)
        self.assertEqual(f.run_git(self.repo, self.env, "symbolic-ref", "HEAD").strip(),
                         f"refs/heads/{BR_C}")
        self.assertIsNone(self.rev_or_none(f"refs/heads/{BR_A}"))
        self.assertIsNone(self.rev_or_none(f"refs/heads/{BR_B}"))

    def test_a_merged_branch_checked_out_in_another_worktree_is_kept_and_named(self):
        f.run_git(self.repo, self.env, "switch", "-q", "main")
        other = self.dest / "other-worktree"
        f.run_git(self.repo, self.env, "worktree", "add", "-q", str(other), BR_A)
        self.ready(1)
        code, text = self.fold("merge-chain", "--until", "unit-a")
        self.assertEqual(code, 0, text)
        self.assertIn("merged: unit-a (#1)", text)
        self.assertIn(f"kept local {BR_A}: checked out in", text)
        self.assertIsNotNone(self.rev_or_none(f"refs/heads/{BR_A}"))

    def test_recorded_tags_of_a_merged_unit_are_deleted_and_the_others_remain(self):
        a_tip, b_tip = self.rev(f"refs/heads/{BR_A}"), self.rev(f"refs/heads/{BR_B}")
        for name, sha in (("ai-kit-fold/07-01/aaaa", a_tip), ("ai-kit-fold/07-02/aaaa", a_tip),
                          ("ai-kit-fold/08-01/bbbb", b_tip)):
            f.run_git(self.repo, self.env, "tag", name, sha)
        tags = {"unit-a": ["ai-kit-fold/07-01/aaaa", "ai-kit-fold/07-02/aaaa"],
                "unit-b": ["ai-kit-fold/08-01/bbbb"]}
        self.edit_units(lambda e: e.update(tags=tags.get(e["id"], [])))
        self.ready(1, 2)
        code, text = self.fold("merge-chain", "--until", "unit-a")
        self.assertEqual(code, 0, text)
        listed = f.run_git(self.repo, self.env, "tag", "-l", "ai-kit-fold/*").split()
        self.assertEqual(listed, ["ai-kit-fold/08-01/bbbb"])

    def test_until_merges_only_the_named_unit(self):
        self.ready(1, 2, 3)
        code, text = self.fold("merge-chain", "--until", "unit-a")
        self.assertEqual(code, 0, text)
        self.assertEqual(self.states(), {"unit-a": "merged", "unit-b": "open", "unit-c": "open"})

    def test_until_above_a_draft_is_capped_at_the_draft(self):
        self.ready(1, 3)
        code, text = self.fold("merge-chain", "--until", "unit-c")
        self.assertEqual(code, 0, text)
        self.assertIn("stopped at unit-b: draft", text)
        self.assertEqual(self.states(), {"unit-a": "merged", "unit-b": "open", "unit-c": "open"})


class TestMergeChainGhStack(_StackCase):
    """The gh-stack backend: the ready prefix merges in one `gh stack merge` call."""

    def setUp(self):
        super().setUp()
        self.state = self.dest / "forge.json"
        self.log = self.dest / "gh.log"
        self.bin = self.dest / "bin"
        forge_fakes.write_forge_fakes(self.bin, self.state, self.log, gh_stack=True)
        self.env["PATH"] = host_fakes.host_path(self.bin)
        self.build_stack()
        gh = str(self.bin / "gh")
        for branch, base in ((BR_A, "main"), (BR_B, BR_A), (BR_C, BR_B)):
            subprocess.run([gh, "pr", "create", "--repo", "ai-kit-fixture/demo", "--base", base,
                            "--head", branch, "--draft", "--title", branch],
                           capture_output=True, text=True, env=self.env, check=False)
        stack_init = ["stack", "init", BR_A, BR_B, BR_C]
        stack_submit = ["stack", "submit", "--remote", "origin"]
        for args in (stack_init, stack_submit):
            proc = subprocess.run([gh, *args], cwd=str(self.repo), capture_output=True,
                                  text=True, env=self.env, check=False)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        for unit_id, number in (("unit-a", 1), ("unit-b", 2), ("unit-c", 3)):
            path = self.repo / ".git" / "ai-kit-stack.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            for entry in data["units"]:
                if entry["id"] == unit_id:
                    entry["pr"] = number
            path.write_text(json.dumps(data), encoding="utf-8")
        settings_path = self.repo / ".aikit" / "flow.json"
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
        settings["stack_backend"] = "gh-stack"
        settings_path.write_text(json.dumps(settings), encoding="utf-8")

    def test_the_ready_stack_merges_in_one_stack_merge_call(self):
        for number in (1, 2, 3):
            forge_fakes.set_pr(self.state, number, isDraft=False)
        code, text = self.fold("merge-chain")
        self.assertEqual(code, 0, text)
        self.assertIn("merged: unit-a (#1)", text)
        self.assertIn("merged: unit-c (#3)", text)
        states = {e["id"]: e["state"] for e in self.record()["units"]}
        self.assertEqual(set(states.values()), {"merged"})
        self.assertEqual(
            {pr["state"] for pr in forge_fakes.forge_state(self.state)["prs"]}, {"MERGED"})
        stack_merges = [c for c in host_fakes.fake_calls(self.log)
                        if c["argv"][:2] == ["stack", "merge"]]
        pr_merges = [c for c in host_fakes.fake_calls(self.log)
                     if c["argv"][:2] == ["pr", "merge"]]
        self.assertEqual(len(stack_merges), 1)
        self.assertEqual(pr_merges, [])

    def test_a_draft_caps_the_stack_merge_at_the_ready_prefix(self):
        forge_fakes.set_pr(self.state, 1, isDraft=False)
        code, text = self.fold("merge-chain")
        self.assertEqual(code, 0, text)
        self.assertIn("merged: unit-a (#1)", text)
        self.assertIn("stopped at unit-b: draft", text)
        states = {e["id"]: e["state"] for e in self.record()["units"]}
        self.assertEqual(states, {"unit-a": "merged", "unit-b": "open", "unit-c": "open"})


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
