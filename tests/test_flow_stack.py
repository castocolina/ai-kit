"""Stack reconciliation tests (plan 29.1-03 Task 1): the cascade, restore and preflights.

Each class builds one template repository with a local bare remote; each test copies it,
rebinds the remote and grants consent in its own copy. Only the plain git rebase is covered
here: the gh-stack backend, conflict resolution with gates, the hotfix and the merge chain are
not built yet (plan 29.1-03 Tasks 2 and 3).

Split by test class: tests/test_flow_stack_2.py and tests/test_flow_stack_3.py hold the cascade,
the gh-stack merge chain and the hotfix.
"""

import fcntl
import json
import os
import pathlib
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


class TestMergeChain(_StackCase):
    """The owner-started chain: bottom-up merges with the fake forge, stops by name, a lock."""

    def setUp(self):
        super().setUp()
        self.state = self.dest / "forge.json"
        self.log = self.dest / "gh.log"
        self.bin = self.dest / "bin"
        forge_fakes.write_forge_fakes(self.bin, self.state, self.log, gh_stack=False)
        self.env["PATH"] = host_fakes.host_path(self.bin, self.env["PATH"])
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


if __name__ == "__main__":
    unittest.main()
