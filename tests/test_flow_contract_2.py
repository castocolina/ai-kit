"""Unit-flow contract tests, part 2: the open behaviours and the third adapter's full flow.

Split from tests/test_flow_contract.py by test class so the parts run in parallel; the shared
template fixture `_FlowCase` stays there.
"""

import json
import pathlib
import subprocess
import sys
import unittest
from unittest import mock

_REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "skills" / "ai-kit-commit-fold" / "scripts"))
sys.path.insert(0, str(_REPO / "tools"))
sys.path.insert(0, str(_REPO))

import flow_git
import flow_record
from flow_record import FlowError

from tests import fold_fixtures as f
from tests import forge_fakes, host_fakes
from tests.test_flow_contract import BRANCH, _FlowCase


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
        self.assertIn("HEAD is not on gsd/phase-07-demo", text)

    def test_checkpoint_by_phase_on_its_branch_without_a_record_starts_the_unit(self):
        # A phase discussed before the discuss:pre hook existed: HEAD is on its branch, no record.
        self.grant()
        self._trunk({f"{f.PHASE_DIR}/07-plan.md": b"p\n"})
        trunk = self.ref_sha("refs/heads/main")
        f.run_git(self.repo, self.env, "switch", "-q", "-c", "gsd/phase-07-demo")
        self.commit({"a.py": b"a\n"}, "feat: phase 07")
        code, text = self.fold("checkpoint", "--phase", "07")
        self.assertEqual(code, 0, text)
        self.assertIn("started unit phase-07 on main", text)
        units = self.record()["units"]
        self.assertEqual([(u["id"], u["parent"], u["parent_tip"], u["checkpoints"])
                          for u in units], [("phase-07", "main", trunk, 1)])

    def test_checkpoint_on_an_unrecorded_branch_off_the_stack_top_refuses_wrong_parent(self):
        self.grant()
        self._trunk({f"{f.PHASE_DIR}/07-plan.md": b"p\n"})
        f.run_git(self.repo, self.env, "switch", "-q", "-c", "gsd/phase-07-demo")
        self.commit({"a.py": b"a\n"}, "feat: phase 07")
        self._trunk({"z.py": b"z\n"}, "feat: trunk moved past the phase branch")
        f.run_git(self.repo, self.env, "switch", "-q", "gsd/phase-07-demo")
        code, text = self.fold("checkpoint", "--phase", "07")
        self.assertEqual(code, 1, text)
        self.assertIn("wrong_parent", text)
        self.assertEqual(flow_record.read_record(self.repo)["units"], [])

    # re-discuss: start (the discuss:pre step) on a recorded unit never blocks the discussion
    def _started_phase(self):
        self.grant()
        self._trunk({f"{f.PHASE_DIR}/07-plan.md": b"p\n"})
        code, text = self.fold("start", "--phase", "07")
        self.assertEqual(code, 0, text)
        self.commit({"a.py": b"a\n"}, "feat: phase 07")
        f.run_git(self.repo, self.env, "switch", "-q", "main")

    def test_rediscuss_of_an_open_unit_reuses_it(self):
        self._started_phase()
        code, text = self.fold("start", "--phase", "07")
        self.assertEqual(code, 0, text)
        self.assertIn("reuses unit phase-07", text)
        self.assertEqual(f.run_git(self.repo, self.env, "branch", "--show-current").strip(),
                         "gsd/phase-07-demo")
        self.assertEqual(len(self.record()["units"]), 1)

    def test_rediscuss_of_a_finished_unit_reuses_its_branch(self):
        self._started_phase()
        self._write_record(lambda data: data["units"][0].update(state="finished"))
        code, text = self.fold("start", "--phase", "07")
        self.assertEqual(code, 0, text)
        self.assertIn("reuses unit phase-07", text)
        self.assertEqual(self.record()["units"][0]["state"], "finished")

    def test_rediscuss_of_a_merged_unit_with_its_branch_gone_reports_and_stays(self):
        self._started_phase()
        self._write_record(lambda data: data["units"][0].update(state="merged"))
        f.run_git(self.repo, self.env, "branch", "-D", "gsd/phase-07-demo")
        before = self.record()
        code, text = self.fold("start", "--phase", "07")
        self.assertEqual(code, 0, text)
        self.assertIn("unit phase-07 is merged; this run stays on main; nothing changed", text)
        self.assertEqual(f.run_git(self.repo, self.env, "branch", "--show-current").strip(),
                         "main")
        self.assertEqual(self.record(), before)

    def test_rediscuss_of_a_ready_unit_whose_branch_is_unrecoverable_reports_and_stays(self):
        self._started_phase()
        self._write_record(lambda data: data["units"][0].update(state="ready"))
        f.run_git(self.repo, self.env, "branch", "-D", "gsd/phase-07-demo")
        code, text = self.fold("start", "--phase", "07")
        self.assertEqual(code, 0, text)
        self.assertIn("is ready and its branch cannot be reused (branch_missing)", text)
        self.assertEqual(f.run_git(self.repo, self.env, "branch", "--show-current").strip(),
                         "main")

    def test_rediscuss_of_an_open_unit_whose_branch_is_gone_still_refuses(self):
        self._started_phase()
        f.run_git(self.repo, self.env, "branch", "-D", "gsd/phase-07-demo")
        code, text = self.fold("start", "--phase", "07")
        self.assertEqual(code, 1, text)
        self.assertIn("branch_missing", text)

    # 4. a moved trunk cascades from sync (plan 03 Task 1); a refolded lower unit cascades above it
    def test_start_restacks_the_stack_when_the_trunk_gained_a_commit(self):
        self.grant()
        self._start_unit("unit-a", BRANCH)
        f.run_git(self.repo, self.env, "switch", "-q", BRANCH)
        self.commit({"a.py": b"a\n"}, "feat: add a")
        clone = self.dest / "trunk-clone"
        f.run_git(self.dest, self.env, "clone", "-q", str(self.bare), str(clone))
        f.commit(clone, self.env, {"z.py": b"z\n"}, "feat: trunk moved")
        f.run_git(clone, self.env, "push", "-q", "origin", "main")
        code, text = self.fold("start", "--unit", self.unit("unit-b", "demo/unit-b"))
        self.assertEqual(code, 0, text)
        new_main = self.remote_sha("main")
        self.assertEqual(self.record()["units"][0]["parent_tip"], new_main)

    def test_refolding_a_lower_unit_under_an_unmerged_unit_restacks_the_units_above(self):
        self.grant()
        self._start_unit("unit-a", BRANCH)
        f.run_git(self.repo, self.env, "switch", "-q", BRANCH)
        self.two_features()
        self._start_unit("unit-b", "demo/unit-b")
        f.run_git(self.repo, self.env, "switch", "-q", BRANCH)
        code, text = self.checkpoint(self.unit(), final=True)
        self.assertEqual(code, 0, text)
        unit_b = next(u for u in self.record()["units"] if u["id"] == "unit-b")
        self.assertEqual(unit_b["parent_tip"], self.ref_sha(f"refs/heads/{BRANCH}"))
        self.assertEqual(self.ref_sha("refs/heads/demo/unit-b"),
                         self.ref_sha(f"refs/heads/{BRANCH}"))

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


ADAPTER_UNITS = (("unit-x", "demo/unit-x", "x.py"), ("unit-y", "demo/unit-y", "y.py"),
                 ("unit-z", "demo/unit-z", "z.py"))


MERGE_VERBS = (["pr", "merge"], ["stack", "merge"])


class TestThirdAdapterFullFlow(_FlowCase):
    """A synthetic third system (unit and checkpoint JSON only) drives the whole flow.

    The adapter is test-side code: it writes the unit and checkpoint JSON for each unit and runs
    the same fold.py commands an owner runs. No flow code is changed for it (FLOW-10).
    """

    def setUp(self):
        super().setUp()
        # Plain gh for the merges: the owner-started chain merges each PR on its own.
        forge_fakes.write_forge_fakes(self.bin, self.state, self.log, gh_stack=False)
        self.env["PATH"] = host_fakes.host_path(self.bin, self.env["PATH"])

    def build_unit(self, unit_id, branch, path):
        """start, two commits, the final checkpoint, then ready: the adapter's per-unit steps."""
        unit = self.unit(unit_id, branch, title=f"Adapter {unit_id}")
        code, text = self.fold("start", "--unit", unit)
        self.assertEqual(code, 0, text)
        stem = path[:-3]
        self.commit({path: f"{stem}\n".encode()}, f"feat: add {stem}")
        self.commit({f"tests/test_{stem}.py": f"t {stem}\n".encode()}, f"test: cover {stem}")
        entry = next(e for e in self.record()["units"] if e["id"] == unit_id)
        tip = self.ref_sha(f"refs/heads/{branch}")
        cp = f.write_checkpoint(
            self.dest / f"cp-{unit_id}.json", schema=1, unit=unit_id,
            ref=f"refs/heads/{branch}", base=entry["parent_tip"], end=tip, tip=tip,
            base_branch=entry["parent"], merged_refs=[], own_merge_subjects=[], docs_paths=[],
            candidates=[{"id": "t1", "title": stem, "files": [path, f"tests/test_{stem}.py"]}])
        code, text = self.fold("checkpoint", "--unit", unit, "--checkpoint", str(cp), "--final")
        self.assertEqual(code, 0, text)
        code, text = self.fold("ready", "--unit", unit)
        self.assertEqual(code, 0, text)

    def build_stack(self):
        for unit_id, branch, path in ADAPTER_UNITS:
            self.build_unit(unit_id, branch, path)

    def merge_calls(self):
        return [c["argv"] for c in self.gh_calls() if c["argv"][:2] in MERGE_VERBS]

    def merge_commits_on_remote_main(self):
        out = f.run_git(self.bare, self.env, "rev-list", "--merges", "--first-parent", "--count",
                        self.remote_sha("main"))
        return int(out.strip())

    def test_three_unit_stack_merges_through_merge_chain(self):
        self.grant()
        self.build_stack()
        self.assertEqual(self.merge_calls(), [])
        code, text = self.fold("merge-chain")
        self.assertEqual(code, 0, text)
        self.assertEqual(self.merge_commits_on_remote_main(), 3)
        self.assertEqual(self.ref_sha("refs/heads/main"), self.remote_sha("main"))
        for _unit_id, branch, _path in ADAPTER_UNITS:
            self.assertIsNone(self.remote_sha(branch), branch)
        self.assertEqual({e["state"] for e in self.record()["units"]}, {"merged"})
        self.assertTrue(self.merge_calls())
        for argv in self.merge_calls():
            self.assertFalse({"--squash", "--rebase", "--auto"} & set(argv), argv)

    def test_no_merge_call_before_the_chain_even_after_a_trunk_restack(self):
        self.grant()
        self.build_stack()
        clone = self.dest / "trunk-clone"
        f.run_git(self.dest, self.env, "clone", "-q", str(self.bare), str(clone))
        f.commit(clone, self.env, {"trunk.txt": b"t\n"}, "docs: trunk moved")
        f.run_git(clone, self.env, "push", "-q", "origin", "main")
        code, text = self.fold("restack")
        self.assertEqual(code, 0, text)
        self.assertEqual(self.merge_calls(), [], "no merge before merge-chain starts")
        code, text = self.fold("merge-chain")
        self.assertEqual(code, 0, text)
        self.assertEqual(self.merge_commits_on_remote_main(), 3)
        self.assertEqual(len(self.merge_calls()), 3)


if __name__ == "__main__":
    unittest.main()
