"""Stack reconciliation tests (plan 29.1-03 Task 1): the cascade, restore and preflights.

Each class builds one template repository with a local bare remote; each test copies it,
rebinds the remote and grants consent in its own copy. Only the plain git rebase is covered
here: the gh-stack backend, conflict resolution with gates, the hotfix and the merge chain are
not built yet (plan 29.1-03 Tasks 2 and 3).
"""

import argparse
import contextlib
import fcntl
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

FAKE_TOKEN = "ghp_" + "A" * 36  # token-shaped, never real

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

    def states(self):
        return {e["id"]: e["state"] for e in self.record()["units"]}

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

    def test_marker_left_in_a_file_refuses_bad_resolution_and_keeps_the_rebase_paused(self):
        self.conflict()
        self.resolve(b"<<<<<<< ours\nboth\n=======\n>>>>>>> theirs\n")
        code, text = self.fold("restack", "--continue", "--note", "shared.txt=kept")
        self.assertEqual(code, 1, text)
        self.assertIn("bad_resolution", text)
        self.assertIn("gates: none run", text)
        self.assertTrue(self.restack_file_exists())
        self.resolve()
        self.gate(sys.executable, "-c", "pass")
        code, text = self.fold("restack", "--continue", "--note", "shared.txt=kept")
        self.assertEqual(code, 0, text)
        self.assertEqual(self.remote_tip(BR_A), self.rev(BR_A))
        self.assertFalse(self.restack_file_exists())

    def test_a_setext_underline_is_not_a_conflict_marker(self):
        self.conflict()
        self.resolve(b"Install\n=======\nboth sides kept\n")
        self.gate(sys.executable, "-c", "pass")
        code, text = self.fold("restack", "--continue", "--note", "shared.txt=kept")
        self.assertEqual(code, 0, text)

    def test_resolving_by_deleting_the_file_continues(self):
        self.conflict()
        (self.repo / "shared.txt").unlink()
        self.gate(sys.executable, "-c", "pass")
        code, text = self.fold("restack", "--continue", "--note", "shared.txt=deleted")
        self.assertEqual(code, 0, text)
        self.assertIn("resolved: shared.txt (deleted)", text)
        self.assertFalse((self.repo / "shared.txt").exists())
        self.assertEqual(self.remote_tip(BR_A), self.rev(BR_A))

    def test_change_outside_the_conflicting_files_refuses_bad_resolution(self):
        self.conflict()
        self.resolve()
        (self.repo / "base.txt").write_bytes(b"edited\n")
        code, text = self.fold("restack", "--continue", "--note", "shared.txt=kept")
        self.assertEqual(code, 1, text)
        self.assertIn("bad_resolution", text)
        self.assertTrue(self.restack_file_exists())

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

    def test_a_gate_whose_binary_is_missing_fails_and_restores_every_branch(self):
        before = self.conflict()
        self.resolve()
        self.gate("ai-kit-no-such-gate-binary", "--check")
        code, text = self.fold("restack", "--continue", "--note", "shared.txt=kept")
        self.assertEqual(code, 1, text)
        self.assertIn("gate_failed", text)
        self.assertIn("ai-kit-no-such-gate-binary --check fail (not found)", text)
        self.assertEqual(self.local_tips((BR_A, BR_B)), before)
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
        merges = self.pr_merge_calls()
        self.assertEqual(len(merges), 3)
        for call in merges:
            self.assertIn("--merge", call["argv"])
            for flag in ("--squash", "--rebase", "--auto"):
                self.assertNotIn(flag, call["argv"])

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

    def test_a_held_lock_refuses_a_second_run(self):
        fd = os.open(self.repo / ".git" / "ai-kit-flow.lock", os.O_CREAT | os.O_RDWR)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            code, text = self.fold("merge-chain")
        finally:
            os.close(fd)
        self.assertEqual(code, 1, text)
        self.assertIn("chain_locked", text)

    def test_an_empty_or_dead_holders_lock_file_is_taken_over(self):
        lock = self.repo / ".git" / "ai-kit-flow.lock"
        for content in ("", "999999"):
            lock.write_text(content, encoding="utf-8")
            code, text = self.fold("merge-chain")
            self.assertEqual(code, 0, text)
            self.assertIn("stopped at unit-a: draft", text)
            self.assertTrue(lock.read_text(encoding="utf-8").isdigit())

    def pr_merge_calls(self):
        return [c for c in host_fakes.fake_calls(self.log) if c["argv"][:2] == ["pr", "merge"]]

    def test_an_unknown_until_refuses_before_any_gh_call(self):
        self.ready(1, 2, 3)
        for until in ("nope", "unit-x"):
            code, text = self.fold("merge-chain", "--until", until)
            self.assertEqual(code, 1, text)
            self.assertIn("bad_value", text)
        self.assertEqual(self.pr_merge_calls(), [])
        self.assertEqual(set(self.states().values()), {"open"})

    def test_no_consent_refuses_before_any_gh_call(self):
        self.ready(1, 2, 3)
        self.fold("consent", "revoke")
        code, text = self.fold("merge-chain")
        self.assertEqual(code, 1, text)
        self.assertIn("no_consent", text)
        self.assertEqual(self.pr_merge_calls(), [])
        self.assertEqual(set(self.states().values()), {"open"})

    def test_a_unit_without_a_pr_number_refuses_no_pr_before_any_gh_call(self):
        self.ready(1, 2, 3)
        self.set_pr_number("unit-b", None)
        before = len(host_fakes.fake_calls(self.log))
        code, text = self.fold("merge-chain")
        self.assertEqual(code, 1, text)
        self.assertIn("no_pr", text)
        self.assertIn("unit-b", text)
        self.assertEqual(len(host_fakes.fake_calls(self.log)), before)

    def test_status_context_and_skipped_checks_pass_and_pending_or_failing_stop(self):
        self.ready(1, 2, 3)
        passing = [{"conclusion": "SKIPPED"}, {"conclusion": "NEUTRAL"}, {"state": "SUCCESS"}]
        forge_fakes.set_pr(self.state, 1, rollup=passing)
        forge_fakes.set_pr(self.state, 2, rollup=[{"state": "PENDING"}])
        code, text = self.fold("merge-chain")
        self.assertEqual(code, 0, text)
        self.assertIn("merged: unit-a (#1)", text)
        self.assertIn("stopped at unit-b: check pending", text)
        forge_fakes.set_pr(self.state, 2, rollup=[{"state": "FAILURE"}])
        _code, text = self.fold("merge-chain")
        self.assertIn("stopped at unit-b: check failing", text)

    def test_unknown_mergeability_stops_as_pending_and_conflicting_as_conflict(self):
        self.ready(1)
        forge_fakes.set_pr(self.state, 1, mergeable="UNKNOWN")
        _code, text = self.fold("merge-chain")
        self.assertIn("stopped at unit-a: mergeability pending", text)
        forge_fakes.set_pr(self.state, 1, mergeable="CONFLICTING")
        _code, text = self.fold("merge-chain")
        self.assertIn("stopped at unit-a: conflict", text)
        self.assertEqual(set(self.states().values()), {"open"})

    def test_a_merge_that_leaves_the_pr_open_is_not_recorded_or_retired(self):
        self.ready(1, 2, 3)
        forge_fakes.set_pr(self.state, 1, hold_merge=True)
        code, text = self.fold("merge-chain")
        self.assertEqual(code, 0, text)
        self.assertIn("stopped at unit-a: merge not confirmed", text)
        self.assertEqual(set(self.states().values()), {"open"})
        self.assertEqual(self.remote_tip(BR_A), self.rev(f"refs/heads/{BR_A}"))
        self.assertIsNotNone(self.rev_or_none(f"refs/heads/{BR_A}"))

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

    def test_a_merged_units_leftover_branches_are_cleaned_on_the_next_run(self):
        a_tip = self.rev(f"refs/heads/{BR_A}")
        self.ready(1)
        code, text = self.fold("merge-chain", "--until", "unit-a")
        self.assertEqual(code, 0, text)
        self.assertIsNone(self.rev_or_none(f"refs/heads/{BR_A}"))
        f.run_git(self.repo, self.env, "branch", BR_A, a_tip)
        f.run_git(self.repo, self.env, "push", "-q", "origin", f"{a_tip}:refs/heads/{BR_A}")
        code, text = self.fold("merge-chain")
        self.assertEqual(code, 0, text)
        self.assertIn("cleaned up: unit-a", text)
        self.assertIsNone(self.rev_or_none(f"refs/heads/{BR_A}"))
        self.assertEqual(f.run_git(self.repo, self.env, "ls-remote", "origin",
                                   f"refs/heads/{BR_A}").strip(), "")

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
    """PRs linked into a GitHub stack: the ready prefix merges in one merge-async call, since
    GitHub refuses `gh pr merge` on a stacked PR."""

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
        urls = [f"https://github.com/{forge_fakes.REPO}/pull/{n}" for n in (1, 2, 3)]
        proc = subprocess.run([gh, "stack", "link", "--base", "main", *urls], cwd=str(self.repo),
                              capture_output=True, text=True, env=self.env, check=False)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.link_units({"unit-a": 1, "unit-b": 2, "unit-c": 3})

    def link_units(self, numbers, linked=True):
        path = self.repo / ".git" / "ai-kit-stack.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        for entry in data["units"]:
            if entry["id"] in numbers:
                entry["pr"] = numbers[entry["id"]]
                entry["linked"] = linked
        path.write_text(json.dumps(data), encoding="utf-8")

    def merge_async_calls(self):
        return [c["argv"] for c in host_fakes.fake_calls(self.log)
                if c["argv"][:3] == ["api", "--method", "PUT"]]

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
        pr_merges = [c for c in host_fakes.fake_calls(self.log)
                     if c["argv"][:2] == ["pr", "merge"]]
        self.assertEqual(pr_merges, [])
        top_head = self.entry("unit-c")["pushed"]
        self.assertEqual(self.merge_async_calls(), [
            ["api", "--method", "PUT", f"repos/{forge_fakes.REPO}/pulls/3/merge-async",
             "--raw-field", "merge_method=merge", "--raw-field", f"sha={top_head}"]])

    def test_a_plain_pr_merge_on_a_linked_pr_is_refused_like_github_does(self):
        forge_fakes.set_pr(self.state, 1, isDraft=False)
        proc = subprocess.run([str(self.bin / "gh"), "pr", "merge", "1", "--merge",
                               "--match-head-commit", self.entry("unit-a")["pushed"], "--repo",
                               forge_fakes.REPO], capture_output=True, text=True, env=self.env,
                              check=False)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("part of a stack and must be merged using the asynchronous merge REST API",
                      proc.stderr)

    def test_a_failed_merge_async_result_refuses_and_records_nothing_merged(self):
        for number in (1, 2, 3):
            forge_fakes.set_pr(self.state, number, isDraft=False)
        forge_fakes.set_pr(self.state, 2, checks="FAILURE", rollup=[{"conclusion": "SUCCESS"}])
        code, text = self.fold("merge-chain")
        self.assertEqual(code, 1, text)
        self.assertIn("refused: pr_failed: merge-async: merge of #2 refused", text)
        self.assertEqual(self.states(), {"unit-a": "open", "unit-b": "open", "unit-c": "open"})

    def test_an_unlinked_unit_caps_the_stack_merge_and_is_retargeted_to_the_trunk(self):
        for number in (1, 2, 3):
            forge_fakes.set_pr(self.state, number, isDraft=False)
        self.link_units({"unit-c": 3}, linked=False)
        code, text = self.fold("merge-chain")
        self.assertEqual(code, 0, text)
        self.assertIn("stopped at unit-c: not linked into the GitHub stack", text)
        self.assertEqual(self.states(), {"unit-a": "merged", "unit-b": "merged", "unit-c": "open"})
        pr3 = forge_fakes.forge_state(self.state)["prs"][2]
        self.assertEqual(pr3["baseRefName"], "main")

    def test_a_moved_pr_head_stops_the_stack_merge_before_any_stack_merge_call(self):
        for number in (1, 2, 3):
            forge_fakes.set_pr(self.state, number, isDraft=False)
        forge_fakes.set_pr(self.state, 2, headRefOid="0" * 40)
        code, text = self.fold("merge-chain")
        self.assertEqual(code, 0, text)
        self.assertIn("stopped at unit-b: PR head differs from the recorded pushed sha", text)
        merges = self.merge_async_calls()
        self.assertEqual(len(merges), 1)
        self.assertEqual(merges[0][3], f"repos/{forge_fakes.REPO}/pulls/1/merge-async")
        states = {e["id"]: e["state"] for e in self.record()["units"]}
        self.assertEqual(states, {"unit-a": "merged", "unit-b": "open", "unit-c": "open"})

    def test_a_draft_caps_the_stack_merge_at_the_ready_prefix(self):
        forge_fakes.set_pr(self.state, 1, isDraft=False)
        code, text = self.fold("merge-chain")
        self.assertEqual(code, 0, text)
        self.assertIn("merged: unit-a (#1)", text)
        self.assertIn("stopped at unit-b: draft", text)
        states = {e["id"]: e["state"] for e in self.record()["units"]}
        self.assertEqual(states, {"unit-a": "merged", "unit-b": "open", "unit-c": "open"})


    def _failing_gh(self, verbs, line):
        """Wrap the fake gh: `verbs` exit 1 with stdout progress and `line` on stderr."""
        real = self.bin / "gh"
        wrap = self.dest / "wrap"
        wrap.mkdir(exist_ok=True)
        (wrap / "gh").write_text(
            "#!" + sys.executable + "\nimport subprocess, sys\n"
            f"if sys.argv[1:3] == {verbs!r}:\n"
            "    print('stdout progress')\n"
            f"    sys.stderr.write({line!r} + '\\nsecond line\\n')\n"
            "    sys.exit(1)\n"
            f"sys.exit(subprocess.run([{str(real)!r}, *sys.argv[1:]]).returncode)\n",
            encoding="utf-8")
        (wrap / "gh").chmod(0o755)
        self.env["PATH"] = f"{wrap}:{self.env['PATH']}"

    def test_a_failing_merge_async_refusal_carries_the_redacted_first_stderr_line(self):
        for number in (1, 2, 3):
            forge_fakes.set_pr(self.state, number, isDraft=False)
        self._failing_gh(["api", "--method"], f"gh: merge refused {FAKE_TOKEN} (HTTP 422)")
        code, text = self.fold("merge-chain")
        self.assertEqual(code, 1, text)
        self.assertIn("refused: pr_failed: gh: merge refused [redacted] (HTTP 422)", text)
        self.assertNotIn(FAKE_TOKEN, text)
        self.assertNotIn("second line", text)
        self.assertNotIn("stdout progress", text)


class TestMergeAsyncPoll(unittest.TestCase):
    """The merge-async result is polled until it settles, for at most MERGE_WAIT seconds."""

    def run_merge(self, answers):
        import flow_merge

        clock = {"t": 0.0}
        calls = []

        def fake_gh(_repo, *args):
            calls.append(args)
            return 0, json.dumps(answers.pop(0) if answers else {"status": "pending"}), ""

        def sleep(seconds):
            clock["t"] += seconds

        with mock.patch.object(flow_merge.flow_pr, "run_gh_split", fake_gh), \
                mock.patch.object(flow_merge.flow_git, "github_repo", return_value="o/r"), \
                mock.patch.object(flow_merge, "primary_remote", return_value="origin"), \
                mock.patch.object(flow_merge, "_now", lambda: clock["t"]), \
                mock.patch.object(flow_merge, "_sleep", sleep):
            status = flow_merge._merge_async("repo", {}, {"pr": 7, "pushed": "abc"})
        return status, calls, clock["t"]

    def test_a_pending_merge_is_polled_until_merged(self):
        status, calls, _ = self.run_merge([
            {"status": "pending", "details": {"uuid": "u1"}}, {"status": "pending"},
            {"status": "merged", "details": {"sha": "m"}}])
        self.assertEqual(status, "merged")
        self.assertEqual(calls[0], ("api", "--method", "PUT", "repos/o/r/pulls/7/merge-async",
                                    "--raw-field", "merge_method=merge", "--raw-field", "sha=abc"))
        self.assertEqual(calls[1:], [("api", "repos/o/r/pulls/7/merge-async/u1")] * 2)

    def test_a_merge_that_stays_pending_stops_polling_at_the_deadline(self):
        import flow_merge

        status, calls, elapsed = self.run_merge([{"status": "pending", "details": {"uuid": "u"}}])
        self.assertEqual(status, "pending")
        self.assertLessEqual(elapsed, flow_merge.MERGE_WAIT)
        self.assertEqual(len(calls), 2 + flow_merge.MERGE_WAIT // flow_merge.POLL_EVERY)

    def test_an_already_merged_answer_needs_no_poll(self):
        status, calls, _ = self.run_merge([{"status": "merged", "details": {"sha": "m"}}])
        self.assertEqual((status, len(calls)), ("merged", 1))

    def test_a_failed_result_refuses_with_its_redacted_message(self):
        with self.assertRaises(flow_record.FlowError) as caught:
            self.run_merge([{"status": "pending", "details": {"uuid": "u"}},
                            {"status": "failed", "details": {"message": f"no {FAKE_TOKEN}"}}])
        self.assertEqual(caught.exception.reason, "pr_failed")
        self.assertEqual(caught.exception.detail, "merge-async: no [redacted]")


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
