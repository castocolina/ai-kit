"""Unit-flow contract tests, part 3: the live-check script and its run ownership.

Split from tests/test_flow_contract.py by test class so the parts run in parallel.
"""

import contextlib
import io
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

_REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "skills" / "ai-kit-commit-fold" / "scripts"))
sys.path.insert(0, str(_REPO / "tools"))
sys.path.insert(0, str(_REPO))

from tests import fold_fixtures as f
from tests import forge_fakes, host_fakes

LIVE = _REPO / "tools" / "flow_live_check.py"


STACK_PROBE = 'if [ "$1" = "stack" ] && [ "$2" = "--help" ]; then exit 0; fi'


class TestLiveCheckScript(unittest.TestCase):
    """The scripted live check in fixture mode: both rounds, the gh-stack proof, forced failures.

    setUpClass builds one bare remote; each test copies it and runs the script against the copy
    with the fake gh first on PATH. No real remote or gh write happens.
    """

    @classmethod
    def setUpClass(cls):
        cls.scratch = pathlib.Path(tempfile.mkdtemp(prefix="ai-kit-p29.1-live-"))
        cls.addClassCleanup(shutil.rmtree, cls.scratch, True)
        template = cls.scratch / "template"
        template.mkdir()
        env = f.git_env(template / "home")
        (template / "home").mkdir()
        repo = f.make_repo(template, env)
        f.make_remote(template, env, repo, github=False)
        cls.template = template

    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp(prefix="case-", dir=self.scratch))
        self.bare = self.root / "remote.git"
        shutil.copytree(self.template / "remote.git", self.bare)
        self.home = self.root / "home"
        self.home.mkdir()
        self.env = f.git_env(self.home)
        self.env.pop("GH_TOKEN", None)
        self.env.pop("GITHUB_TOKEN", None)
        self.state = self.root / "forge.json"
        self.log = self.root / "gh.log"
        self.bin = self.root / "bin"
        forge_fakes.write_forge_fakes(self.bin, self.state, self.log, gh_stack=True)
        self.env["PATH"] = host_fakes.host_path(self.bin, self.env["PATH"])
        self.base_path = self.env["PATH"]
        self.workdir = self.root / "work"
        self.install_gh(STACK_PROBE)

    def install_gh(self, *lines):
        """A `gh` on PATH in front of the fake. The shell `lines` run first and may refuse a call.

        The fake has no `stack --help` (the flow's probe seam), so STACK_PROBE answers it the way
        an installed gh-stack does, and round 1 selects the gh-stack backend by the probe.
        """
        wrap = self.root / "wrap"
        wrap.mkdir(exist_ok=True)
        gh = wrap / "gh"
        gh.write_text("#!/bin/sh\n" + "\n".join(lines) + f'\nexec "{self.bin / "gh"}" "$@"\n',
                      encoding="utf-8")
        gh.chmod(0o755)
        self.env["PATH"] = host_fakes.host_path(wrap, self.base_path)

    def run_live(self):
        return subprocess.run(
            [sys.executable, str(LIVE), "--fixture", str(self.bare), "--workdir",
             str(self.workdir)],
            capture_output=True, text=True, env=self.env, check=False)

    def heads(self):
        out = subprocess.run(["git", "--git-dir", str(self.bare), "for-each-ref",
                              "--format=%(refname) %(objectname)", "refs/heads"],
                             capture_output=True, text=True, check=True).stdout
        return dict(line.split() for line in out.splitlines())

    def test_both_rounds_pass_with_one_ok_line_per_step_and_the_gh_stack_backend(self):
        before = self.heads()
        proc = self.run_live()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        lines = proc.stdout.splitlines()
        self.assertEqual(lines[-1], "live-check: ok")
        self.assertTrue(all(line.startswith("ok ") for line in lines[:-1]), lines)
        for expected in ("ok gh-stack merge-chain live-1-hotfix", "ok gh-stack merge-chain",
                         "ok gh-stack remote check", "ok gh merge-chain",
                         "ok gh remote check"):
            self.assertIn(expected, lines)
        stack_verbs = [c["argv"][1] for c in host_fakes.fake_calls(self.log)
                       if c["argv"][:1] == ["stack"] and c["argv"][1:2] != ["--help"]]
        self.assertTrue(stack_verbs, "round 1 never called a gh stack verb")
        trunk = next(line.split()[3] for line in lines if line.startswith("ok setup trunk "))
        self.assertRegex(trunk, r"^flowlive-[0-9a-f]{8}/main$")
        links = [c["argv"] for c in host_fakes.fake_calls(self.log) if c["argv"][:2] ==
                 ["stack", "link"]]
        self.assertTrue(links)
        self.assertTrue(all(argv[2:4] == ["--base", trunk] for argv in links), links)
        # GitHub's merge-async lands the whole stack in one merge, so the check counts no commits.
        puts = [c["argv"] for c in host_fakes.fake_calls(self.log) if c["argv"][:3] ==
                ["api", "--method", "PUT"]]
        self.assertEqual(len(puts), 1, puts)
        # The merges landed on the per-run trunk, which cleanup deleted; main never moved.
        self.assertEqual(self.heads(), before)

    def test_a_refused_merge_stops_the_run_at_that_step_with_exit_1(self):
        self.install_gh(STACK_PROBE,
                        'if [ "$2" = "merge" ]; then echo "fake gh: merge refused" >&2; exit 1; fi')
        proc = self.run_live()
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertRegex(proc.stdout, r"live-check: failed at gh-stack merge-chain")
        self.assertIn("refused: pr_failed: fake gh: merge refused", proc.stdout)
        self.assertNotIn("live-check: ok", proc.stdout)

    def test_a_pr_that_is_not_merged_fails_the_remote_check(self):
        self.install_gh(STACK_PROBE, 'case "$*" in *mergeCommit*) '
                        'echo \'{"state":"OPEN","mergeCommit":null}\'; exit 0;; esac')
        proc = self.run_live()
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("live-check: failed at gh-stack remote check: PR #", proc.stdout)
        self.assertIn("is not MERGED with a merge commit", proc.stdout)

    def test_a_gh_stack_fallback_in_round_one_fails_the_gh_stack_proof(self):
        self.install_gh(STACK_PROBE, 'if [ "$1" = "stack" ]; then '
                        'echo "fake gh: stack verb refused" >&2; exit 1; fi')
        proc = self.run_live()
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("live-check: failed at gh-stack", proc.stdout)
        self.assertIn("gh-stack fallback", proc.stdout)
        self.assertIn("gh-stack failed: fake gh: stack verb refused", proc.stdout)

    def test_live_mode_without_the_owner_flag_exits_2_and_names_the_precondition(self):
        proc = subprocess.run([sys.executable, str(LIVE), "--live"], capture_output=True,
                              text=True, env=self.env, check=False)
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("precondition: gh signed in with the repo scope", proc.stdout)
        self.assertNotIn("delete_repo", proc.stdout)
        self.assertIn("private repo <owner>/ai-kit-flow-live,", proc.stdout)
        self.assertIn("no repo is ever deleted", proc.stdout)


RUN_ID = "flowlive-0000aaaa"


class TestLiveCheckOwnership(unittest.TestCase):
    """The persistent repo of the owner-attended run, offline: subprocess.run is patched in-process,
    so no gh or git command runs. No repo is ever deleted; cleanup touches only this run's PRs,
    branches and trunk."""

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="ai-kit-p29.1-own-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.work = self.tmp / "work"

    @staticmethod
    def answers(**overrides):
        """An answer function: argv -> (code, stdout). Keys name a gh/git verb pair."""
        def answer(argv):
            words = " ".join(item for item in argv if not item.startswith("-")).replace("-", " ")
            for key, value in overrides.items():
                if key.replace("_", " ") in words:
                    return value(argv) if callable(value) else value
            if argv[:3] == ["gh", "repo", "view"]:
                return 0, '{"isPrivate": true}'
            return 0, ""
        return answer

    def run_live(self, answer, rounds=0, record=None, extra=("--owner", "owner-x")):
        """main() with the patched runner; returns (rc, out, calls)."""
        import flow_live_check  # pylint: disable=import-outside-toplevel

        calls = []

        def fake_run(argv, **_kwargs):
            calls.append(list(argv))
            code, out = answer(argv)
            return subprocess.CompletedProcess(argv, code, out, "fake: refused\n")

        def fake_rounds(_slug, workdir, _run_id):
            if record is not None:  # what a run leaves in its clone's flow record
                git_dir = workdir / "repo" / ".git"
                git_dir.mkdir(parents=True)
                (git_dir / "ai-kit-stack.json").write_text(json.dumps({"units": record}),
                                                           encoding="utf-8")
            return rounds

        out = io.StringIO()
        with contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch("subprocess.run", side_effect=fake_run))
            stack.enter_context(mock.patch.object(flow_live_check, "_live_rounds",
                                                  side_effect=fake_rounds))
            stack.enter_context(mock.patch.object(flow_live_check, "_new_run_id",
                                                  return_value=RUN_ID))
            stack.enter_context(contextlib.redirect_stdout(out))
            rc = flow_live_check.main(["--live", "--yes-owner-attended", *extra,
                                       "--workdir", str(self.work)])
        return rc, out.getvalue(), calls

    @staticmethod
    def verb(calls, *head):
        return [argv for argv in calls if argv[:len(head)] == list(head)]

    def assert_no_repo_delete(self, calls):
        self.assertEqual(self.verb(calls, "gh", "repo", "delete"), [])

    def test_an_existing_private_repo_is_reused_and_never_created_or_deleted(self):
        rc, out, calls = self.run_live(self.answers())
        self.assertEqual(rc, 0, out)
        self.assertEqual(self.verb(calls, "gh", "repo", "view")[0][3], "owner-x/ai-kit-flow-live")
        self.assertEqual(self.verb(calls, "gh", "repo", "create"), [])
        self.assert_no_repo_delete(calls)
        self.assertIn(f"live-check: run {RUN_ID} in owner-x/ai-kit-flow-live on trunk "
                      f"{RUN_ID}/main", out)
        self.assertEqual(out.splitlines()[-1], "live-check: ok")

    def test_a_missing_repo_is_created_once_private_and_kept(self):
        rc, out, calls = self.run_live(self.answers(gh_repo_view=(1, "")))
        self.assertEqual(rc, 0, out)
        self.assertEqual(self.verb(calls, "gh", "repo", "create"),
                         [["gh", "repo", "create", "owner-x/ai-kit-flow-live", "--private",
                           "--add-readme"]])
        self.assert_no_repo_delete(calls)
        self.assertIn("it is kept for later runs", out)

    def test_a_failed_create_stops_before_any_round_and_exits_1(self):
        rc, out, calls = self.run_live(self.answers(gh_repo_view=(1, ""),
                                                    gh_repo_create=(1, "")))
        self.assertEqual(rc, 1)
        self.assertIn("failed at create owner-x/ai-kit-flow-live", out)
        self.assertEqual(self.verb(calls, "git"), [])
        self.assert_no_repo_delete(calls)

    def test_a_public_repo_is_refused(self):
        rc, out, calls = self.run_live(self.answers(gh_repo_view=(0, '{"isPrivate": false}')))
        self.assertEqual(rc, 1)
        self.assertIn("is not a private repo", out)
        self.assertEqual(self.verb(calls, "gh", "repo", "create"), [])

    def test_the_repo_flag_overrides_the_default_without_an_owner_lookup(self):
        rc, out, calls = self.run_live(self.answers(), extra=("--repo", "someone/flow-box"))
        self.assertEqual(rc, 0, out)
        self.assertEqual(self.verb(calls, "gh", "repo", "view")[0][3], "someone/flow-box")
        self.assertEqual(self.verb(calls, "gh", "api"), [])

    def test_cleanup_closes_and_deletes_only_what_this_run_recorded(self):
        record = [
            {"branch": f"{RUN_ID}/r1/x", "pr": 5},
            {"branch": f"hotfix/{RUN_ID}-r1-hotfix", "pr": 6},
            {"branch": f"{RUN_ID}/r1/y", "pr": None},
            {"branch": "flowlive-ffffffff/r1/x", "pr": 7},  # another run's
        ]

        def view(argv):
            return 0, '{"state": "OPEN"}' if argv[3] == "5" else '{"state": "MERGED"}'

        rc, out, calls = self.run_live(self.answers(gh_pr_view=view, ls_remote=(0, "sha ref")),
                                       record=record)
        self.assertEqual(rc, 0, out)
        self.assertEqual([argv[3] for argv in self.verb(calls, "gh", "pr", "view")], ["5", "6"])
        self.assertEqual(self.verb(calls, "gh", "pr", "close"),
                         [["gh", "pr", "close", "5", "--repo", "owner-x/ai-kit-flow-live"]])
        deleted = [argv[-1] for argv in calls if "--delete" in argv]
        self.assertEqual(deleted, [f"{RUN_ID}/r1/x", f"hotfix/{RUN_ID}-r1-hotfix",
                                   f"{RUN_ID}/r1/y", f"{RUN_ID}/main"])
        self.assertFalse(any("flowlive-ffffffff" in " ".join(argv) for argv in calls))
        self.assert_no_repo_delete(calls)

    def test_a_failed_cleanup_fails_the_check_even_when_the_rounds_passed(self):
        rc, out, _calls = self.run_live(self.answers(ls_remote=(0, "sha ref"),
                                                     push_origin=(1, "")),
                                        record=[])
        self.assertEqual(rc, 1)
        self.assertIn(f"live-check: cleanup failed for run {RUN_ID}", out)
        self.assertIn(f"delete {RUN_ID}/main", out)
        self.assertNotIn("live-check: ok", out)

    def test_a_failed_round_still_cleans_up_this_run(self):
        rc, _out, calls = self.run_live(self.answers(ls_remote=(0, "sha ref")), rounds=1,
                                        record=[])
        self.assertEqual(rc, 1)
        self.assertEqual([argv[-1] for argv in calls if "--delete" in argv], [f"{RUN_ID}/main"])


if __name__ == "__main__":
    unittest.main()
