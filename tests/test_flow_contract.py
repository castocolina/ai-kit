"""Unit-flow contract tests (plan 29.1-01): tracer, contract edges, stacking, bounds, consent.

Each class builds one template repository with a local bare remote in setUpClass; each test
copies it, rebinds the remote's insteadOf to the copy's bare path, writes fresh fake forge
state and log, and grants consent only in its own copy.
"""

import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest import mock

_REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "skills" / "ai-kit-commit-fold" / "scripts"))
sys.path.insert(0, str(_REPO))

import flow_git
import flow_pr
import flow_record
from flow_record import FlowError

from tests import fold_fixtures as f
from tests import (
    forge_fakes,
    host_fakes,
)

FOLD = _REPO / "skills" / "ai-kit-commit-fold" / "scripts" / "fold.py"
BRANCH = "demo/unit-a"


class _FlowCase(unittest.TestCase):
    """One copy of the template per test, with its own remote, forge, log and consent."""

    template_root: str = ""

    @classmethod
    def setUpClass(cls):
        cls.scratch = pathlib.Path(tempfile.mkdtemp(prefix="ai-kit-p29.1-flow-"))
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
        self.home = self.dest / "home"
        self.env = f.git_env(self.home)
        self.env.pop("GH_TOKEN", None)
        self.env.pop("GITHUB_TOKEN", None)
        f.rebind(self.dest, self.env, self.repo, self.bare)
        self.state = self.dest / "forge.json"
        self.log = self.dest / "gh.log"
        self.bin = self.dest / "bin"
        forge_fakes.write_forge_fakes(self.bin, self.state, self.log, gh_stack=True)
        self.env["PATH"] = host_fakes.host_path(self.bin)

    def fold(self, *args, env=None):
        proc = subprocess.run(
            [sys.executable, str(FOLD), *args, "--repo", str(self.repo)],
            capture_output=True, text=True, env=env or self.env, check=False)
        return proc.returncode, proc.stdout + proc.stderr

    def grant(self):
        code, text = self.fold("consent", "grant", "--add-exclude")
        self.assertEqual(code, 0, text)

    def unit(self, unit_id=None, branch=BRANCH, title="Demo unit", **extra):
        path = self.dest / f"{unit_id or 'unit-a'}.json"
        data = {"schema": 1, "id": unit_id or "unit-a", "kind": "stacked", "branch": branch,
                "title": title, **extra}
        path.write_text(json.dumps(data), encoding="utf-8")
        return str(path)

    def commit(self, files, message):
        return f.commit(self.repo, self.env, files, message)

    def checkpoint(self, unit_path, ref=f"refs/heads/{BRANCH}", end=None, final=False,
                   candidates=None):
        tip = f.run_git(self.repo, self.env, "rev-parse", "HEAD").strip()
        default = [
            {"id": "t1", "title": "A", "files": ["a.py", "tests/test_a.py"]},
            {"id": "t2", "title": "B", "files": ["b.py", "tests/test_b.py"]},
        ]
        cp = f.write_checkpoint(
            self.dest / "cp.json", schema=1, unit="unit-a", ref=ref,
            base=f.run_git(self.repo, self.env, "rev-parse", "main").strip(), end=end or tip,
            tip=tip, base_branch="main", merged_refs=[], own_merge_subjects=[], docs_paths=[],
            candidates=candidates or default)
        args = ["checkpoint", "--unit", unit_path, "--checkpoint", str(cp)]
        return self.fold(*(args + (["--final"] if final else [])))

    def ref_sha(self, name):
        return f.run_git(self.repo, self.env, "rev-parse", name).strip()

    def remote_sha(self, branch):
        out = f.run_git(self.repo, self.env, "ls-remote", "origin", f"refs/heads/{branch}")
        return out.split()[0] if out.strip() else None

    def gh_calls(self):
        return host_fakes.fake_calls(self.log)

    def record(self):
        return json.loads((self.repo / ".git" / "ai-kit-stack.json").read_text(encoding="utf-8"))

    def two_features(self):
        self.commit({"a.py": b"a\n"}, "feat: add a")
        self.commit({"tests/test_a.py": b"ta\n"}, "test: cover a")
        self.commit({"b.py": b"b\n"}, "feat: add b")
        return self.commit({"tests/test_b.py": b"tb\n"}, "test: cover b")


class TestFlowTracer(_FlowCase):
    """The synthetic unit end to end: start, consent, fold and push, draft PR, ready."""

    def test_start_creates_branch_on_remote_trunk_and_records_it(self):
        self.grant()
        code, text = self.fold("start", "--unit", self.unit())
        self.assertEqual(code, 0, text)
        self.assertEqual(self.ref_sha(f"refs/heads/{BRANCH}"), self.ref_sha("refs/heads/main"))
        units = self.record()["units"]
        self.assertEqual([(u["id"], u["parent"]) for u in units], [("unit-a", "main")])

    def test_checkpoint_folds_pushes_and_opens_one_draft_pr(self):
        self.grant()
        self.fold("start", "--unit", self.unit())
        f.run_git(self.repo, self.env, "switch", BRANCH)
        tip = self.two_features()
        code, text = self.checkpoint(self.unit(), final=True)
        self.assertEqual(code, 0, text)
        self.assertEqual(f.run_git(self.repo, self.env, "rev-list", "--count",
                                   f"main..{BRANCH}").strip(), "2")
        self.assertNotEqual(tip, self.ref_sha(f"refs/heads/{BRANCH}"))
        self.assertEqual(self.remote_sha(BRANCH), self.ref_sha(f"refs/heads/{BRANCH}"))
        creates = [c["argv"] for c in self.gh_calls() if c["argv"][:2] == ["pr", "create"]]
        self.assertEqual(len(creates), 1)
        argv = creates[0]
        for pair in (["--base", "main"], ["--head", BRANCH], ["--repo", "ai-kit-fixture/demo"]):
            self.assertEqual(argv[argv.index(pair[0]) + 1], pair[1])
        self.assertIn("--draft", argv)
        entry = self.record()["units"][0]
        self.assertEqual((entry["pr"], entry["state"]), (1, "finished"))
        self.assertEqual(entry["pushed"], self.ref_sha(f"refs/heads/{BRANCH}"))

    def test_ref_mismatch_refuses_with_no_local_or_remote_change(self):
        self.grant()
        self.fold("start", "--unit", self.unit())
        f.run_git(self.repo, self.env, "switch", BRANCH)
        self.two_features()
        before = f.run_git(self.repo, self.env, "for-each-ref", "--format=%(refname) %(objectname)")
        remote_before = f.run_git(self.repo, self.env, "ls-remote", "origin")
        code, text = self.checkpoint(self.unit(), ref="refs/heads/main")
        self.assertEqual(code, 1, text)
        self.assertIn("ref_mismatch", text)
        self.assertEqual(f.run_git(self.repo, self.env, "for-each-ref",
                                   "--format=%(refname) %(objectname)"), before)
        self.assertEqual(f.run_git(self.repo, self.env, "ls-remote", "origin"), remote_before)
        self.assertEqual([c for c in self.gh_calls() if c["argv"][:2] == ["pr", "create"]], [])

    def test_ready_marks_the_draft_pr_ready(self):
        self.grant()
        unit = self.unit()
        self.fold("start", "--unit", unit)
        f.run_git(self.repo, self.env, "switch", BRANCH)
        self.two_features()
        self.checkpoint(unit, final=True)
        code, text = self.fold("ready", "--unit", unit)
        self.assertEqual(code, 0, text)
        readies = [c["argv"] for c in self.gh_calls() if c["argv"][:2] == ["pr", "ready"]]
        self.assertEqual(readies, [["pr", "ready", "1", "--repo", "ai-kit-fixture/demo"]])
        self.assertFalse(forge_fakes.forge_state(self.state)["prs"][0]["isDraft"])
        self.assertEqual(self.record()["units"][0]["state"], "ready")

    def test_report_starts_with_flow_line_and_ends_with_outcome(self):
        self.grant()
        code, text = self.fold("start", "--unit", self.unit())
        lines = text.strip().splitlines()
        self.assertEqual(code, 0)
        self.assertTrue(lines[0].startswith("flow start unit-a:"), text)
        self.assertTrue(lines[-1].startswith("outcome: unit-a"), text)
        self.assertLessEqual(len(lines), 8)


class TestContractEdges(_FlowCase):
    """The unit contract refuses unknown, missing and malformed fields before any side effect."""

    def test_unknown_field_is_named(self):
        with self.assertRaises(FlowError) as raised:
            flow_record.load_unit({"schema": 1, "id": "u", "kind": "stacked", "branch": "b",
                                   "title": "t", "extra": 1}, "main")
        self.assertEqual(raised.exception.reason, "unknown_field")
        self.assertIn("extra", raised.exception.detail)

    def test_missing_field_is_named_and_nothing_is_created(self):
        self.grant()
        path = self.dest / "bad.json"
        path.write_text(json.dumps({"schema": 1, "id": "unit-a"}), encoding="utf-8")
        code, text = self.fold("start", "--unit", str(path))
        self.assertEqual(code, 2, text)
        self.assertIn("missing_field", text)
        self.assertIn("branch", text)
        self.assertEqual(self.gh_calls(), [])
        self.assertEqual(f.run_git(self.repo, self.env, "branch", "--list", BRANCH).strip(), "")

    def test_bad_kind_and_bad_id_are_refused(self):
        for overrides in ({"kind": "other"}, {"id": "has space"}):
            with self.subTest(overrides=overrides), self.assertRaises(FlowError) as raised:
                flow_record.load_unit({"schema": 1, "id": "u", "kind": "stacked",
                                       "branch": "b", "title": "t", **overrides}, "main")
            self.assertEqual(raised.exception.reason, "bad_value")

    def test_ready_before_final_checkpoint_refuses_signal_order(self):
        self.grant()
        unit = self.unit()
        self.fold("start", "--unit", unit)
        code, text = self.fold("ready", "--unit", unit)
        self.assertEqual(code, 1, text)
        self.assertIn("signal_order", text)


class TestStacking(_FlowCase):
    """A unit starts on the newest unmerged unit in record order, else on the remote trunk."""

    def test_second_unit_starts_at_first_units_tip(self):
        self.grant()
        self.fold("start", "--unit", self.unit("unit-a", BRANCH))
        f.run_git(self.repo, self.env, "switch", BRANCH)
        tip_a = self.commit({"a.py": b"a\n"}, "feat: add a")
        code, text = self.fold("start", "--unit", self.unit("unit-b", "demo/unit-b"))
        self.assertEqual(code, 0, text)
        self.assertEqual(self.ref_sha("refs/heads/demo/unit-b"), tip_a)
        self.assertEqual([u["parent"] for u in self.record()["units"]], ["main", BRANCH])

    def test_reusing_a_recorded_unit_keeps_its_entry(self):
        self.grant()
        unit = self.unit()
        self.fold("start", "--unit", unit)
        before = self.record()
        code, text = self.fold("start", "--unit", unit)
        self.assertEqual(code, 0, text)
        self.assertIn("reuses unit unit-a", text)
        self.assertEqual(self.record(), before)


class TestGuardAndMergedRefs(_FlowCase):
    """guard names a wrong parent; a unit merged outside the flow is recorded merged."""

    def test_guard_exits_zero_on_the_right_parent(self):
        self.grant()
        unit = self.unit()
        self.fold("start", "--unit", unit)
        code, text = self.fold("guard", "--unit", unit)
        self.assertEqual(code, 0, text)

    def test_unit_merged_outside_the_flow_is_recorded_and_next_starts_on_trunk(self):
        self.grant()
        self.fold("start", "--unit", self.unit())
        f.run_git(self.repo, self.env, "switch", BRANCH)
        self.commit({"a.py": b"a\n"}, "feat: add a")
        f.run_git(self.repo, self.env, "push", "-q", "origin", BRANCH)
        f.run_git(self.repo, self.env, "switch", "main")
        f.merge_on_remote(self.dest, self.env, self.bare, BRANCH, "main")
        code, text = self.fold("start", "--unit", self.unit("unit-b", "demo/unit-b"))
        self.assertEqual(code, 0, text)
        states = {u["id"]: u["state"] for u in self.record()["units"]}
        self.assertEqual(states["unit-a"], "merged")
        self.assertEqual(self.record()["units"][1]["parent"], "main")


class TestAdapterGates(_FlowCase):
    """The GSD health gate: exact summary text and the exit rule, with an injected run."""

    def test_no_config_means_no_adapter_gates(self):
        from fold_adapters import adapter_gates

        self.assertEqual(adapter_gates(str(self.repo)), [])

    def test_gsd_project_gets_one_health_gate(self):
        from fold_adapters import adapter_gates

        (self.repo / ".planning").mkdir()
        (self.repo / ".planning" / "config.json").write_text("{}", encoding="utf-8")
        gates = adapter_gates(str(self.repo))
        self.assertEqual([label for label, _argv in gates], ["gsd-tools validate health"])
        self.assertEqual(gates[0][1][2:], ["gsd-health", "--repo", str(self.repo)])

    def _health(self, stdout):
        from fold_adapters import gsd_health

        tools = self.repo / ".claude" / "gsd-core" / "bin"
        tools.mkdir(parents=True, exist_ok=True)
        (tools / "gsd-tools.cjs").write_text("", encoding="utf-8")

        def run(argv, **kwargs):
            return subprocess.CompletedProcess(argv, 0, stdout, "")

        return gsd_health(str(self.repo), run=run)

    def test_healthy_status_is_ok(self):
        self.assertEqual(self._health('{"status": "healthy"}'), (True, "health: healthy"))

    def test_degraded_status_names_the_warning_code(self):
        ok, summary = self._health('{"status": "degraded", "warnings": [{"code": "W027"}]}')
        self.assertFalse(ok)
        self.assertIn("W027", summary)

    def test_broken_and_non_json_are_not_ok(self):
        self.assertFalse(self._health('{"status": "broken"}')[0])
        self.assertFalse(self._health("not json")[0])


class TestPushBounds(_FlowCase):
    """Target and merged-branch pushes are refused; a stale lease is refused, not forced."""

    def test_leased_push_to_a_target_is_refused(self):
        self.grant()
        settings = flow_record.read_settings(self.repo)
        with self.assertRaises(FlowError) as raised:
            flow_git.push(self.repo, settings, {"units": []},
                          [("main", self.ref_sha("refs/heads/main"), None)])
        self.assertEqual(raised.exception.reason, "target_branch_push")

    def test_push_of_a_merged_unit_is_refused(self):
        self.grant()
        settings = flow_record.read_settings(self.repo)
        record = {"units": [{"branch": BRANCH, "state": "merged"}]}
        with self.assertRaises(FlowError) as raised:
            flow_git.push(self.repo, settings, record, [(BRANCH, None, None)])
        self.assertEqual(raised.exception.reason, "merged_branch_push")

    def test_second_clone_push_makes_the_lease_stale(self):
        self.grant()
        unit = self.unit()
        self.fold("start", "--unit", unit)
        f.run_git(self.repo, self.env, "switch", BRANCH)
        self.two_features()
        self.checkpoint(unit)
        recorded = self.record()["units"][0]["pushed"]
        clone = self.dest / "clone"
        f.run_git(self.dest, self.env, "clone", "-q", str(self.bare), str(clone))
        f.run_git(clone, self.env, "switch", "-q", BRANCH)
        other = f.commit(clone, self.env, {"c.py": b"c\n"}, "feat: other clone")
        f.run_git(clone, self.env, "push", "-q", "origin", BRANCH)
        local = self.commit({"d.py": b"d\n"}, "feat: local")
        settings = flow_record.read_settings(self.repo)
        with self.assertRaises(FlowError) as raised:
            flow_git.push(self.repo, settings, self.record(), [(BRANCH, recorded, local)])
        self.assertEqual(raised.exception.reason, "stale_lease")
        self.assertEqual(self.remote_sha(BRANCH), other)

    def test_missing_origin_refuses_with_no_remote_and_stays_local(self):
        self.grant()
        f.run_git(self.repo, self.env, "remote", "remove", "origin")
        code, text = self.fold("start", "--unit", self.unit())
        self.assertEqual(code, 1, text)
        self.assertIn("no_remote", text)


class TestConsent(_FlowCase):
    """No consent means no remote call; grant pushes the backlog; a foreign record is no consent."""

    def test_checkpoint_without_consent_makes_no_remote_call_and_lists_the_skip(self):
        unit = self.unit()
        self.fold("start", "--unit", unit)
        f.run_git(self.repo, self.env, "switch", BRANCH)
        self.two_features()
        before = self.remote_sha(BRANCH)
        code, text = self.checkpoint(unit)
        self.assertEqual(code, 0, text)
        self.assertIn(f"skipped: unit-a push {BRANCH}", text)
        self.assertEqual(self.gh_calls(), [])
        self.assertEqual(self.remote_sha(BRANCH), before)
        self.assertIsNotNone(self.record()["units"][0]["pending"])

    def test_grant_then_catch_up_pushes_only_the_folded_pending_tip(self):
        unit = self.unit()
        self.fold("start", "--unit", unit)
        f.run_git(self.repo, self.env, "switch", BRANCH)
        self.two_features()
        self.checkpoint(unit, final=True)
        pending = self.record()["units"][0]["pending"]
        self.commit({"e.py": b"e\n"}, "feat: after the skipped checkpoint")
        self.grant()
        code, text = self.fold("ready", "--unit", unit)
        self.assertEqual(code, 0, text)
        self.assertEqual(self.remote_sha(BRANCH), pending)
        entry = self.record()["units"][0]
        self.assertIsNone(entry["pending"])
        self.assertEqual(entry["pushed"], pending)

    def test_settings_not_ignored_refuses_grant_until_excluded(self):
        code, text = self.fold("consent", "grant")
        self.assertEqual(code, 1, text)
        self.assertIn("settings_not_ignored", text)
        code, text = self.fold("consent", "grant", "--add-exclude")
        self.assertEqual(code, 0, text)

    def test_consent_status_prints_yes_or_no_only(self):
        _code, text = self.fold("consent", "status")
        self.assertEqual(text.strip(), "consent: no")
        self.grant()
        _code, text = self.fold("consent", "status")
        self.assertEqual(text.strip(), "consent: yes")

    def test_foreign_empty_and_non_json_settings_count_as_no_consent(self):
        settings = self.repo / ".aikit" / "flow.json"
        settings.parent.mkdir(exist_ok=True)
        cases = {
            "foreign": json.dumps({"consent": True, "repo": "/somewhere/else"}),
            "empty": "",
            "non-json": "consent: yes",
        }
        for name, text in cases.items():
            with self.subTest(name=name):
                settings.write_text(text, encoding="utf-8")
                self.assertFalse(flow_record.consented(self.repo))

    def test_racing_settings_writes_leave_one_valid_record(self):
        settings = flow_record.read_settings(self.repo)
        errors = []

        def writer(value):
            try:
                for _ in range(20):
                    flow_record.write_settings(self.repo, {**settings, "remote": value})
            except OSError as exc:  # pragma: no cover - reported below
                errors.append(exc)

        threads = [threading.Thread(target=writer, args=(name,)) for name in ("a", "b")]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(errors, [])
        data = json.loads((self.repo / ".aikit" / "flow.json").read_text(encoding="utf-8"))
        self.assertIn(data["remote"], ("a", "b"))


class TestNoToken(_FlowCase):
    """Tokens never reach a report; consent status prints only yes or no."""

    def test_redact_removes_token_shaped_strings(self):
        token = "ghp_" + "a" * 36
        self.assertNotIn(token, flow_pr.redact(f"error near {token} here"))
        self.assertIn("[redacted]", flow_pr.redact(token))

    def test_report_with_token_in_env_carries_no_token(self):
        token = "ghp_" + "b" * 36
        env = dict(self.env, GH_TOKEN=token)
        self.grant()
        _code, text = self.fold("consent", "status", env=env)
        self.assertNotIn(token, text)
        self.assertEqual(text.strip(), "consent: yes")


class TestForgeFake(_FlowCase):
    """The forge fake answers gh and gh stack with the real flags and real git pushes."""

    def _pr_create(self, head, base):
        proc = subprocess.run(
            ["gh", "pr", "create", "--base", base, "--head", head, "--draft", "--title", head,
             "--repo", "ai-kit-fixture/demo"],
            cwd=str(self.repo), env=self.env, capture_output=True, text=True, check=False)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return int(proc.stdout.strip().rsplit("/", 1)[1])

    def _branch_on(self, name, base, text):
        f.run_git(self.repo, self.env, "switch", "-q", "-c", name, base)
        self.commit({f"{name}.txt": text.encode()}, f"feat: {name}")

    def test_stack_submit_chains_bases_and_pushes_for_real(self):
        self._branch_on("b1", "main", "1")
        self._branch_on("b2", "b1", "2")
        self._branch_on("b3", "b2", "3")
        f.run_git(self.repo, self.env, "switch", "-q", "b3")
        self.assertEqual(subprocess.run(
            ["gh", "stack", "init", "--base", "main", "b1", "b2", "b3"], cwd=str(self.repo),
            env=self.env, capture_output=True, check=False).returncode, 0)
        proc = subprocess.run(["gh", "stack", "submit", "--auto"], cwd=str(self.repo),
                              env=self.env, capture_output=True, text=True, check=False)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        prs = forge_fakes.forge_state(self.state)["prs"]
        self.assertEqual([p["baseRefName"] for p in prs], ["main", "b1", "b2"])
        self.assertTrue(all(p["isDraft"] for p in prs))
        for name in ("b1", "b2", "b3"):
            self.assertIsNotNone(self.remote_sha(name))

    def test_stack_link_of_pr_urls_does_not_push(self):
        self._branch_on("c1", "main", "1")
        urls = []
        for name in ("c1",):
            urls.append(self._pr_create(name, "main"))
        proc = subprocess.run(
            ["gh", "stack", "link", *[f"https://github.com/ai-kit-fixture/demo/pull/{n}"
                                      for n in urls]],
            cwd=str(self.repo), env=self.env, capture_output=True, text=True, check=False)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        link = [c for c in self.gh_calls() if c["argv"][:2] == ["stack", "link"]]
        self.assertEqual(len(link), 1)
        self.assertNotIn("pushed", link[0])

    def test_pr_merge_with_wrong_sha_is_refused_and_right_sha_merges(self):
        self._branch_on("d1", "main", "1")
        number = self._pr_create("d1", "main")
        wrong = subprocess.run(
            ["gh", "pr", "merge", str(number), "--merge", "--match-head-commit", "0" * 40,
             "--repo", "ai-kit-fixture/demo"], cwd=str(self.repo), env=self.env,
            capture_output=True, text=True, check=False)
        self.assertEqual(wrong.returncode, 1)
        f.run_git(self.repo, self.env, "push", "-q", "origin", "d1")
        forge_fakes.set_pr(self.state, number, isDraft=False)
        head = self.ref_sha("refs/heads/d1")
        right = subprocess.run(
            ["gh", "pr", "merge", str(number), "--merge", "--match-head-commit", head,
             "--repo", "ai-kit-fixture/demo"], cwd=str(self.repo), env=self.env,
            capture_output=True, text=True, check=False)
        self.assertEqual(right.returncode, 0, right.stderr)
        parents = f.run_git(self.bare, self.env, "rev-list", "--parents", "-n", "1",
                            "main").split()
        self.assertEqual(len(parents), 3)

    def test_pr_view_without_repo_exits_one(self):
        self._branch_on("e1", "main", "1")
        f.run_git(self.repo, self.env, "push", "-q", "origin", "e1")
        self._pr_create("e1", "main")
        proc = subprocess.run(["gh", "pr", "view", "1", "--json", "number"],
                              cwd=str(self.repo), env=self.env, capture_output=True,
                              text=True, check=False)
        self.assertEqual(proc.returncode, 1)


class TestEdgeCommands(_FlowCase):
    """Refusals and read-only commands at the edges: wrong parent, not started, show, revoke."""

    def test_existing_branch_on_another_parent_refuses_start(self):
        self.grant()
        f.run_git(self.repo, self.env, "checkout", "-q", "--orphan", "other")
        self.commit({"x.txt": b"x\n"}, "feat: unrelated history")
        f.run_git(self.repo, self.env, "branch", BRANCH, "other")
        f.run_git(self.repo, self.env, "checkout", "-q", "main")
        code, text = self.fold("start", "--unit", self.unit())
        self.assertEqual(code, 1, text)
        self.assertIn("wrong_parent", text)
        self.assertIn(BRANCH, text)

    def test_checkpoint_and_show_refuse_an_unrecorded_unit(self):
        self.grant()
        unit = self.unit()
        code, text = self.checkpoint(unit)
        self.assertEqual(code, 1, text)
        self.assertIn("not_started", text)
        code, text = self.fold("show", "--unit", unit)
        self.assertEqual(code, 1, text)
        self.assertIn("not_started", text)

    def test_show_prints_state_and_pr_without_any_remote_call(self):
        self.grant()
        unit = self.unit()
        self.fold("start", "--unit", unit)
        before = self.gh_calls()
        code, text = self.fold("show", "--unit", unit)
        self.assertEqual(code, 0, text)
        self.assertIn("state: open", text)
        self.assertIn("pr: none", text)
        self.assertEqual(self.gh_calls(), before)

    def test_revoke_makes_the_next_checkpoint_skip_the_push_again(self):
        self.grant()
        unit = self.unit()
        self.fold("start", "--unit", unit)
        f.run_git(self.repo, self.env, "switch", BRANCH)
        self.two_features()
        self.fold("consent", "revoke")
        code, text = self.checkpoint(unit)
        self.assertEqual(code, 0, text)
        self.assertIn(f"skipped: unit-a push {BRANCH}", text)
        self.assertIsNotNone(self.record()["units"][0]["pending"])

    def test_delete_remote_refuses_a_target_and_an_unmerged_unit(self):
        self.grant()
        settings = flow_record.read_settings(self.repo)
        record = {"units": [{"branch": BRANCH, "state": "open"}]}
        with self.assertRaises(FlowError) as target:
            flow_git.delete_remote(self.repo, settings, record, "main")
        self.assertEqual(target.exception.reason, "target_branch_push")
        with self.assertRaises(FlowError) as unmerged:
            flow_git.delete_remote(self.repo, settings, record, BRANCH)
        self.assertEqual(unmerged.exception.reason, "merged_branch_push")

    def test_stack_merge_refuses_while_a_draft_remains(self):
        self._branch_on("g1", "main", "1")
        self._branch_on("g2", "g1", "2")
        f.run_git(self.repo, self.env, "switch", "-q", "g2")
        subprocess.run(["gh", "stack", "init", "--base", "main", "g1", "g2"],
                       cwd=str(self.repo), env=self.env, capture_output=True, check=True)
        subprocess.run(["gh", "stack", "submit", "--auto"], cwd=str(self.repo),
                       env=self.env, capture_output=True, check=True)
        proc = subprocess.run(["gh", "stack", "merge", "2"], cwd=str(self.repo),
                              env=self.env, capture_output=True, text=True, check=False)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("draft", proc.stderr)

    def test_gsd_health_without_tools_exits_one_and_names_the_missing_tool(self):
        code, text = self.fold("gsd-health")
        self.assertEqual(code, 1, text)
        self.assertIn("gsd-tools.cjs", text)

    def _branch_on(self, name, base, text):
        f.run_git(self.repo, self.env, "switch", "-q", "-c", name, base)
        self.commit({f"{name}.txt": text.encode()}, f"feat: {name}")


class TestOpenBehaviours(_FlowCase):
    """The behaviour lines plan 29.1-01 left open: GSD and superpowers stacking, plan base
    rules, hotfix join, merged refs, trunk_moved, restack_needed, encodings, revoke then
    catch-up, the lease spy and gh stack submit on a second remote."""

    def _trunk(self, files, message="docs: trunk"):
        f.run_git(self.repo, self.env, "switch", "-q", "main")
        self.commit(files, message)
        f.run_git(self.repo, self.env, "push", "-q", "origin", "main")

    def _write_record(self, mutate):
        path = self.repo / ".git" / "ai-kit-stack.json"
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {
            "schema": 1, "units": []}
        mutate(data)
        path.write_text(json.dumps(data), encoding="utf-8")

    def _start_unit(self, unit_id, branch):
        code, text = self.fold("start", "--unit", self.unit(unit_id, branch))
        self.assertEqual(code, 0, text)
        return text

    def _branch_on(self, name, base, text):
        f.run_git(self.repo, self.env, "switch", "-q", "-c", name, base)
        return self.commit({f"{name}.txt": text.encode()}, f"feat: {name}")

    # 1. GSD phases and a superpowers plan stack by record order (via --phase and --plan)
    def test_gsd_phases_then_superpowers_plan_stack_in_record_order(self):
        self.grant()
        self._trunk({f"{f.PHASE_DIR}/07-01-PLAN.md": b"p\n",
                     ".planning/phases/08-demo/08-01-PLAN.md": b"p\n",
                     f.SP_PLAN: f.SP_PLAN_TEXT.encode()})
        code, text = self.fold("start", "--phase", "07")
        self.assertEqual(code, 0, text)
        f.run_git(self.repo, self.env, "switch", "-q", "gsd/phase-07-demo")
        tip_07 = self.commit({"a.py": b"a\n"}, "feat: phase 07")
        code, text = self.fold("start", "--phase", "08")
        self.assertEqual(code, 0, text)
        self.assertEqual(self.ref_sha("refs/heads/gsd/phase-08-demo"), tip_07)
        f.run_git(self.repo, self.env, "switch", "-q", "gsd/phase-08-demo")
        tip_08 = self.commit({"b.py": b"b\n"}, "feat: phase 08")
        code, text = self.fold("start", "--plan", f.SP_PLAN)
        self.assertEqual(code, 0, text)
        self.assertEqual(self.ref_sha("refs/heads/plan/demo-plan"), tip_08)
        units = self.record()["units"]
        self.assertEqual([u["id"] for u in units],
                         ["phase-07", "phase-08", "2026-11-04-demo"])
        self.assertEqual([u["parent"] for u in units],
                         ["main", "gsd/phase-07-demo", "gsd/phase-08-demo"])

    # 2. --plan base rules
    def test_plan_base_below_parent_tip_refuses_bad_value(self):
        self.grant()
        self._trunk({f.SP_PLAN: f.SP_PLAN_TEXT.encode()})
        self.fold("start", "--plan", f.SP_PLAN)
        f.run_git(self.repo, self.env, "switch", "-q", "plan/demo-plan")
        self.commit({"a.py": b"a\n"}, "feat: add a")
        below = f.run_git(self.repo, self.env, "rev-parse", "main~1").strip()
        code, text = self.fold("checkpoint", "--plan", f.SP_PLAN, "--base", below, "--final")
        self.assertEqual(code, 2, text)
        self.assertIn("bad_value", text)

    def test_plan_base_above_first_commit_folds_only_the_rest(self):
        self.grant()
        self._trunk({f.SP_PLAN: f.SP_PLAN_TEXT.encode()})
        self.fold("start", "--plan", f.SP_PLAN)
        f.run_git(self.repo, self.env, "switch", "-q", "plan/demo-plan")
        first = self.commit({"a.py": b"a\n"}, "feat: add a")
        second = self.commit({"tests/test_a.py": b"ta\n"}, "test: cover a")
        self.commit({"b.py": b"b\n"}, "feat: add b")
        self.commit({"tests/test_b.py": b"tb\n"}, "test: cover b")
        code, text = self.fold("checkpoint", "--plan", f.SP_PLAN, "--base", second, "--final")
        self.assertEqual(code, 0, text)
        kept = subprocess.run(["git", "-C", str(self.repo), "merge-base", "--is-ancestor",
                               first, "HEAD"], capture_output=True, check=False)
        self.assertEqual(kept.returncode, 0)
        count = f.run_git(self.repo, self.env, "rev-list", "--count", f"{second}..HEAD").strip()
        self.assertEqual(count, "1", text)

    # 3. hotfix join, merged refs, not_started via --phase
    def test_start_on_a_checked_out_hotfix_unit_joins_it(self):
        self.grant()
        self._trunk({f.SP_PLAN: f.SP_PLAN_TEXT.encode()})
        self._write_record(lambda data: data["units"].append({
            "id": "hot-1", "kind": "hotfix", "target": "main", "branch": "hotfix/fix-1",
            "parent": "main", "parent_tip": self.ref_sha("refs/heads/main"), "pr": None,
            "state": "open", "mvp": False, "pushed": None, "pending": None, "tags": [],
            "title": "fix", "goal": "", "checkpoints": 0}))
        f.run_git(self.repo, self.env, "branch", "hotfix/fix-1", "main")
        f.run_git(self.repo, self.env, "switch", "-q", "hotfix/fix-1")
        code, text = self.fold("start", "--plan", f.SP_PLAN)
        self.assertEqual(code, 0, text)
        self.assertIn("joins hotfix unit hot-1", text)
        self.assertEqual(len(self.record()["units"]), 1)
        self.assertEqual(f.run_git(self.repo, self.env, "branch", "--list", "plan/*").strip(),
                         "")

    def test_checkpoint_on_a_range_under_a_merged_unit_refuses(self):
        self.grant()
        self._start_unit("unit-x", "demo/unit-x")
        f.run_git(self.repo, self.env, "switch", "-q", "demo/unit-x")
        tip_x = self.two_features()
        self._write_record(lambda data: data["units"][0].update(state="merged"))
        self._start_unit("unit-y", "demo/unit-y")
        f.run_git(self.repo, self.env, "switch", "-q", "main")
        f.run_git(self.repo, self.env, "branch", "-f", "demo/unit-y", tip_x)
        f.run_git(self.repo, self.env, "switch", "-q", "demo/unit-y")
        code, text = self.checkpoint(self.unit("unit-y", "demo/unit-y"),
                                     ref="refs/heads/demo/unit-y")
        self.assertEqual(code, 1, text)
        self.assertIn("range_on_merged_branch", text)

    def test_checkpoint_by_phase_without_a_record_refuses_not_started(self):
        self.grant()
        self._trunk({f"{f.PHASE_DIR}/07-plan.md": b"p\n"})
        code, text = self.fold("checkpoint", "--phase", "07")
        self.assertEqual(code, 1, text)
        self.assertIn("not_started", text)

    # 4. trunk_moved from sync; restack_needed from a lower-unit refold
    def test_sync_refuses_trunk_moved_when_the_trunk_gained_a_commit(self):
        self.grant()
        self._start_unit("unit-a", BRANCH)
        f.run_git(self.repo, self.env, "switch", "-q", BRANCH)
        self.commit({"a.py": b"a\n"}, "feat: add a")
        clone = self.dest / "trunk-clone"
        f.run_git(self.dest, self.env, "clone", "-q", str(self.bare), str(clone))
        f.commit(clone, self.env, {"z.py": b"z\n"}, "feat: trunk moved")
        f.run_git(clone, self.env, "push", "-q", "origin", "main")
        code, text = self.fold("start", "--unit", self.unit("unit-b", "demo/unit-b"))
        self.assertEqual(code, 1, text)
        self.assertIn("trunk_moved", text)

    def test_refolding_a_lower_unit_under_an_unmerged_unit_refuses_restack_needed(self):
        self.grant()
        self._start_unit("unit-a", BRANCH)
        f.run_git(self.repo, self.env, "switch", "-q", BRANCH)
        self.two_features()
        self._start_unit("unit-b", "demo/unit-b")
        f.run_git(self.repo, self.env, "switch", "-q", BRANCH)
        code, text = self.checkpoint(self.unit(), final=True)
        self.assertEqual(code, 1, text)
        self.assertIn("restack_needed", text)

    # 5. encodings: a non-ASCII plan title; a backup remote with a space and a non-ASCII path
    def test_non_ascii_plan_title_gives_a_valid_branch_name(self):
        self.grant()
        plan = "docs/superpowers/plans/2026-11-05-accent.md"
        self._trunk({plan: "# Plan Ünïcode délai\n\n### Task 1: x\n".encode()})
        code, text = self.fold("start", "--plan", plan)
        self.assertEqual(code, 0, text)
        branch = self.record()["units"][0]["branch"]
        check = subprocess.run(["git", "check-ref-format", "--branch", branch],
                               capture_output=True, check=False)
        self.assertEqual(check.returncode, 0, branch)
        self.assertTrue(branch.startswith("plan/"))

    def test_backup_remote_with_space_and_non_ascii_path_receives_the_push(self):
        self.grant()
        remote_dir = self.dest / "remote dir ü"
        remote_dir.mkdir()
        backup = remote_dir / "remote.git"
        f.run_git(self.dest, self.env, "init", "--bare", "-q", "-b", "main", str(backup))
        f.run_git(self.repo, self.env, "remote", "add", "backup", str(backup))
        f.run_git(self.repo, self.env, "push", "-q", "backup", "main")
        code, text = self.fold("settings", "set", "--remote", "backup")
        self.assertEqual(code, 0, text)
        origin_before = self.remote_sha(BRANCH)
        self._start_unit("unit-a", BRANCH)
        f.run_git(self.repo, self.env, "switch", "-q", BRANCH)
        tip = self.commit({"a.py": b"a\n"}, "feat: add a")
        code, text = self.checkpoint(self.unit(), final=True)
        self.assertEqual(code, 0, text)
        pushed = f.run_git(self.repo, self.env, "ls-remote", "backup",
                           f"refs/heads/{BRANCH}").split()[0]
        self.assertEqual(pushed, self.ref_sha(f"refs/heads/{BRANCH}"))
        self.assertIsNotNone(tip)
        self.assertEqual(self.remote_sha(BRANCH), origin_before)
        self.assertIsNone(origin_before)

    # 6. revoke, then catch-up refused by a second clone's stale lease
    def test_catch_up_after_revoke_refuses_a_stale_lease_and_keeps_pending(self):
        self.grant()
        self._start_unit("unit-a", BRANCH)
        f.run_git(self.repo, self.env, "switch", "-q", BRANCH)
        self.commit({"a.py": b"a\n"}, "feat: add a")
        code, text = self.checkpoint(self.unit(), candidates=[
            {"id": "t1", "title": "A", "files": ["a.py"]}])
        self.assertEqual(code, 0, text)
        pushed = self.record()["units"][0]["pushed"]
        self.assertIsNotNone(pushed)
        self.fold("consent", "revoke")
        self.commit({"b.py": b"b\n"}, "feat: add b")
        code, text = self.checkpoint(self.unit(), final=True, candidates=[
            {"id": "t1", "title": "A", "files": ["a.py"]},
            {"id": "t2", "title": "B", "files": ["b.py"]}])
        self.assertEqual(code, 0, text)
        pending = self.record()["units"][0]["pending"]
        self.assertIsNotNone(pending)
        clone = self.dest / "stale-clone"
        f.run_git(self.dest, self.env, "clone", "-q", str(self.bare), str(clone))
        f.run_git(clone, self.env, "switch", "-q", BRANCH)
        other = f.commit(clone, self.env, {"c.py": b"c\n"}, "feat: second clone")
        f.run_git(clone, self.env, "push", "-q", "origin", BRANCH)
        self.grant()
        code, text = self.fold("ready", "--unit", self.unit())
        self.assertEqual(code, 1, text)
        self.assertIn("stale_lease", text)
        self.assertEqual(self.remote_sha(BRANCH), other)
        self.assertEqual(self.record()["units"][0]["pending"], pending)

    # 7. lease-value spy: the lease is the recorded pushed sha, never a fetched tip
    def test_push_argv_leases_the_recorded_pushed_sha_not_the_fetched_tip(self):
        self.grant()
        self._start_unit("unit-a", BRANCH)
        f.run_git(self.repo, self.env, "switch", "-q", BRANCH)
        self.commit({"a.py": b"a\n"}, "feat: add a")
        code, text = self.checkpoint(self.unit(), candidates=[
            {"id": "t1", "title": "A", "files": ["a.py"]}])
        self.assertEqual(code, 0, text)
        recorded = self.record()["units"][0]["pushed"]
        clone = self.dest / "spy-clone"
        f.run_git(self.dest, self.env, "clone", "-q", str(self.bare), str(clone))
        f.run_git(clone, self.env, "switch", "-q", BRANCH)
        other = f.commit(clone, self.env, {"c.py": b"c\n"}, "feat: second clone")
        f.run_git(clone, self.env, "push", "-q", "origin", BRANCH)
        f.run_git(self.repo, self.env, "fetch", "-q", "origin")
        self.assertEqual(f.run_git(self.repo, self.env, "rev-parse",
                                   f"refs/remotes/origin/{BRANCH}").strip(), other)
        local = self.commit({"d.py": b"d\n"}, "feat: local")
        settings = flow_record.read_settings(self.repo)
        real_run = subprocess.run
        calls = []

        def spy(argv, *args, **kwargs):
            calls.append(list(argv))
            return real_run(argv, *args, **kwargs)

        with mock.patch.object(flow_git.subprocess, "run", side_effect=spy), \
                self.assertRaises(FlowError) as raised:
            flow_git.push(self.repo, settings, self.record(), [(BRANCH, recorded, local)])
        self.assertEqual(raised.exception.reason, "stale_lease")
        pushes = [argv for argv in calls if "push" in argv and "--force-with-lease" in
                  " ".join(argv)]
        self.assertEqual(len(pushes), 1)
        self.assertIn(f"--force-with-lease=refs/heads/{BRANCH}:{recorded}", pushes[0])
        self.assertNotIn(other, " ".join(pushes[0]))

    # 8. gh stack submit with --open on a second remote
    def test_gh_stack_submit_open_on_a_second_remote_leaves_origin_alone(self):
        self._branch_on("h1", "main", "1")
        self._branch_on("h2", "h1", "2")
        second = self.dest / "second.git"
        f.run_git(self.dest, self.env, "init", "--bare", "-q", "-b", "main", str(second))
        f.run_git(self.repo, self.env, "remote", "add", "second", str(second))
        f.run_git(self.repo, self.env, "switch", "-q", "h2")
        origin_h1 = self.remote_sha("h1")
        subprocess.run(["gh", "stack", "init", "--base", "main", "h1", "h2"],
                       cwd=str(self.repo), env=self.env, capture_output=True, check=True)
        proc = subprocess.run(["gh", "stack", "submit", "--auto", "--open", "--remote", "second"],
                              cwd=str(self.repo), env=self.env, capture_output=True, text=True,
                              check=False)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        prs = forge_fakes.forge_state(self.state)["prs"]
        self.assertEqual([p["baseRefName"] for p in prs], ["main", "h1"])
        self.assertFalse(any(p["isDraft"] for p in prs))
        second_h1 = f.run_git(self.repo, self.env, "ls-remote", "second",
                              "refs/heads/h1").strip()
        self.assertNotEqual(second_h1, "")
        self.assertEqual(origin_h1, None)
        self.assertIsNone(self.remote_sha("h1"))


class TestRemainingBehaviours(_FlowCase):
    """Lines left open after the first fix cycle: guard wrong parent, no_trunk, no fetch without
    consent, and the delete_remote success path."""

    def test_guard_refuses_a_unit_moved_onto_another_parent(self):
        self.grant()
        unit = self.unit()
        self.fold("start", "--unit", unit)
        f.run_git(self.repo, self.env, "switch", "-q", "main")
        f.run_git(self.repo, self.env, "checkout", "-q", "--orphan", "other")
        self.commit({"x.txt": b"x\n"}, "feat: unrelated")
        f.run_git(self.repo, self.env, "branch", "-f", BRANCH, "other")
        code, text = self.fold("guard", "--unit", unit)
        self.assertEqual(code, 1, text)
        self.assertIn("wrong_parent", text)

    def test_start_without_a_remote_trunk_ref_refuses_no_trunk(self):
        f.run_git(self.repo, self.env, "update-ref", "-d", "refs/remotes/origin/main")
        code, text = self.fold("start", "--unit", self.unit())
        self.assertEqual(code, 1, text)
        self.assertIn("no_trunk", text)

    def test_checkpoint_without_consent_never_fetches(self):
        unit = self.unit()
        self.fold("start", "--unit", unit)
        f.run_git(self.repo, self.env, "switch", "-q", BRANCH)
        self.two_features()
        clone = self.dest / "fetch-clone"
        f.run_git(self.dest, self.env, "clone", "-q", str(self.bare), str(clone))
        f.commit(clone, self.env, {"trunk.txt": b"t\n"}, "docs: trunk moved")
        f.run_git(clone, self.env, "push", "-q", "origin", "main")
        before = f.run_git(self.repo, self.env, "rev-parse", "refs/remotes/origin/main")
        code, text = self.checkpoint(unit)
        self.assertEqual(code, 0, text)
        self.assertEqual(f.run_git(self.repo, self.env, "rev-parse",
                                   "refs/remotes/origin/main"), before)

    def test_delete_remote_removes_a_merged_unit_branch(self):
        self.grant()
        f.run_git(self.repo, self.env, "push", "-q", "origin", "main:refs/heads/" + BRANCH)
        settings = flow_record.read_settings(self.repo)
        record = {"units": [{"branch": BRANCH, "state": "merged"}]}
        flow_git.delete_remote(self.repo, settings, record, BRANCH)
        self.assertIsNone(self.remote_sha(BRANCH))


if __name__ == "__main__":
    unittest.main()
