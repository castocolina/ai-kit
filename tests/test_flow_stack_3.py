"""Stack reconciliation tests, part 3: the cascade conflict and the gh-stack merge chain.

Split from tests/test_flow_stack.py by test class so the parts run in parallel; the shared
template fixture `_StackCase` stays there.
"""

import argparse
import contextlib
import io
import json
import os
import pathlib
import shlex
import subprocess
import sys
import unittest
from unittest import mock

_REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "skills" / "ai-kit-commit-fold" / "scripts"))
sys.path.insert(0, str(_REPO))

import flow_stack

from tests import fold_fixtures as f
from tests import forge_fakes, host_fakes
from tests.test_flow_stack import BR_A, BR_B, BR_C, FAKE_TOKEN, _StackCase


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


class TestMergeChainGhStack(_StackCase):
    """PRs linked into a GitHub stack: the ready prefix merges in one merge-async call, since
    GitHub refuses `gh pr merge` on a stacked PR."""

    def setUp(self):
        super().setUp()
        self.state = self.dest / "forge.json"
        self.log = self.dest / "gh.log"
        self.bin = self.dest / "bin"
        forge_fakes.write_forge_fakes(self.bin, self.state, self.log, gh_stack=True)
        self.env["PATH"] = host_fakes.host_path(self.bin, self.env["PATH"])
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


if __name__ == "__main__":
    unittest.main()
