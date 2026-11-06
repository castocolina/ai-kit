"""The boundary step (plan 30-04): refresh, branch binding, lock, brief, wave-1 rule, start report.

Every index tool is a recorder: `which` finds nothing, so no codegraph or graphify process runs.
"""

import argparse
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

import flow_boundary
import flow_brief
import flow_index
import flow_record
import flow_unit
import fold_adapters
from flow_record import FlowError, Unit

from tests import fold_fixtures as f
from tests import index_fakes

FOLD = _REPO / "skills" / "ai-kit-commit-fold" / "scripts" / "fold.py"

_IDENT = ["-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid"]
_NOW = "2026-11-05T00:00:00Z"


def _git(repo, *args):
    proc = subprocess.run(["git", "-C", repo, *_IDENT, *args], capture_output=True, text=True,
                          check=True)
    return proc.stdout.strip()


def _commit(repo, rel, text, message):
    path = pathlib.Path(repo) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    _git(repo, "add", rel)
    _git(repo, "commit", "-q", "-m", message)


def _entry(unit_id, branch, parent_tip, kind="stacked"):
    return {"id": unit_id, "kind": kind, "target": "main", "branch": branch, "parent": "main",
            "parent_tip": parent_tip, "pr": None, "state": "open", "mvp": False, "pushed": None,
            "pending": None, "tags": [], "title": unit_id, "goal": "", "checkpoints": 0,
            "carried": []}


def _unit(unit_id, branch):
    return Unit(id=unit_id, kind="stacked", target="main", branch=branch, title=unit_id,
                goal="", mvp=False)


class _Recorder:
    """A stand-in for flow_index._run_tool: records argv, never runs anything."""

    def __init__(self):
        self.calls = []

    def __call__(self, argv, cwd, timeout=900):
        self.calls.append((tuple(argv), cwd))
        return 0, "", ""


def _seams(recorder, deadline=600):
    return flow_boundary.Seams(run=recorder, which=lambda name: None, clock=lambda: 0.0,
                               sleep=lambda seconds: None, now=lambda: _NOW,
                               lock_deadline_s=deadline)


class _StackedFixture(unittest.TestCase):
    """Repo on main; unit A (feat/a) adds pkg/alpha.py and is recorded; B (feat/b) is on A."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()  # removed in tearDownClass
        cls.repo = os.path.join(cls._tmp.name, "repo")
        os.makedirs(cls.repo)
        _git(cls.repo, "init", "-q", "-b", "main")
        _commit(cls.repo, "README.md", "base\n", "base")
        cls.base = _git(cls.repo, "rev-parse", "HEAD")
        _git(cls.repo, "checkout", "-q", "-b", "feat/a")
        _commit(cls.repo, "pkg/alpha.py", "def alpha_one():\n    return 1\n", "add alpha")
        cls.a_tip = _git(cls.repo, "rev-parse", "HEAD")
        _git(cls.repo, "checkout", "-q", "-b", "feat/b")
        _commit(cls.repo, "pkg/beta.py", "def beta():\n    return 2\n", "add beta")
        _git(cls.repo, "checkout", "-q", "feat/a")
        flow_record.write_record(cls.repo, {"schema": 1,
                                            "units": [_entry("A", "feat/a", cls.base)]})

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def setUp(self):
        _git(self.repo, "checkout", "-q", "feat/b")

    def brief_path(self):
        return pathlib.Path(self.repo) / flow_brief.BRIEF_REL


class TestBoundaryBrief(_StackedFixture):
    def test_brief_names_previous_unit_range_and_changed_file(self):
        recorder = _Recorder()
        lines, outcome = flow_boundary.boundary(self.repo, _unit("B", "feat/b"), "plan",
                                                seams=_seams(recorder))
        self.assertEqual(outcome, "done")
        self.assertIn(
            "brief: .aikit/brief/SKILL.md (previous unit A, 1 changed file)", lines)
        text = self.brief_path().read_text(encoding="utf-8")
        self.assertIn("unit: B\n", text)
        self.assertIn("point: plan\n", text)
        self.assertIn(f"head: {_git(self.repo, 'rev-parse', 'HEAD')[:12]}\n", text)
        self.assertIn(f"## Previous unit\nPrevious unit A (`feat/a`), range "
                      f"`{self.base[:12]}..{self.a_tip[:12]}`.", text)
        self.assertIn("## Changed files\n- added `pkg/alpha.py`", text)

    def test_next_briefs_top_stacked_unit_with_next_stamp(self):
        recorder = _Recorder()
        _, outcome = flow_boundary.boundary(self.repo, None, "plan", seams=_seams(recorder))
        self.assertEqual(outcome, "done")
        text = self.brief_path().read_text(encoding="utf-8")
        self.assertIn("unit: next (for whoever writes the next unit's plan)\n", text)
        self.assertIn("Previous unit A (`feat/a`)", text)

    def test_no_previous_unit_still_writes_brief(self):
        empty = {"schema": 1, "units": []}
        recorder = _Recorder()
        with mock.patch.object(flow_boundary, "read_record", return_value=empty):
            lines, _ = flow_boundary.boundary(self.repo, _unit("B", "feat/b"), "start",
                                              seams=_seams(recorder))
        self.assertIn("brief: .aikit/brief/SKILL.md (no previous unit)", lines)
        text = self.brief_path().read_text(encoding="utf-8")
        self.assertIn("No previous unit: this is the first unit on `main`.", text)

    def test_missing_tools_are_reported_without_a_call(self):
        recorder = _Recorder()
        lines, _ = flow_boundary.boundary(self.repo, _unit("B", "feat/b"), "plan",
                                          seams=_seams(recorder))
        self.assertTrue(any(line.startswith("codegraph:") for line in lines))
        self.assertTrue(any(line.startswith("graphify:") for line in lines))
        self.assertEqual(recorder.calls, [])  # no tool found, so nothing ran


class TestAikitExcludeIsReported(unittest.TestCase):
    """The boundary adds `.aikit/` to `.git/info/exclude` and reports it once."""

    def test_first_boundary_reports_the_exclude_and_the_next_one_does_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = os.path.join(tmp, "repo")
            os.makedirs(repo)
            _git(repo, "init", "-q", "-b", "main")
            _commit(repo, "README.md", "base\n", "base")
            _git(repo, "checkout", "-q", "-b", "feat/b")
            flow_record.write_record(repo, {"schema": 1, "units": []})
            unit = _unit("B", "feat/b")
            first, _ = flow_boundary.boundary(repo, unit, "start", seams=_seams(_Recorder()))
            second, _ = flow_boundary.boundary(repo, unit, "plan", seams=_seams(_Recorder()))
        exclude_note = "ignored .aikit/ in .git/info/exclude"
        self.assertTrue(any(exclude_note in line for line in first), first)
        self.assertFalse(any(exclude_note in line for line in second), second)


class TestBranchBinding(_StackedFixture):
    def test_recorded_unit_on_another_branch_is_refused_before_any_write(self):
        _git(self.repo, "checkout", "-q", "main")
        self.brief_path().unlink(missing_ok=True)
        recorder = _Recorder()
        with self.assertRaises(FlowError) as raised:
            flow_boundary.boundary(self.repo, _unit("A", "feat/a"), "plan",
                                   seams=_seams(recorder))
        self.assertEqual(raised.exception.reason, "ref_mismatch")
        self.assertIn("HEAD is on main, not the unit branch feat/a; switch to it",
                      raised.exception.detail)
        self.assertEqual(recorder.calls, [])
        self.assertFalse(self.brief_path().exists())


class TestIndexLock(_StackedFixture):
    def test_lock_held_past_deadline_skips_refresh_and_still_writes_brief(self):
        common = flow_record.common_dir(self.repo)
        recorder = _Recorder()
        with open(common / flow_index.LOCK_NAME, "a+", encoding="utf-8") as held:
            fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
            lines, _ = flow_boundary.boundary(self.repo, _unit("B", "feat/b"), "plan",
                                              seams=_seams(recorder, deadline=0))
            fcntl.flock(held, fcntl.LOCK_UN)
        self.assertIn("index: lock held past 0 s; indexes not refreshed, retried at the next "
                      "point", lines)
        self.assertTrue(self.brief_path().is_file())


class TestBriefRender(unittest.TestCase):
    def test_changed_file_lines_for_add_modify_remove_and_rename(self):
        facts = flow_brief.BriefFacts(
            unit="B", branch="feat/b", head="0" * 12, point="plan", written=_NOW,
            base_branch="main", previous="A", previous_branch="feat/a",
            unit_range=("1" * 40, "2" * 40),
            changed=(("A", "a.py", None), ("M", "b.py", None), ("D", "c.py", None),
                     ("R", "new.py", "old.py")))
        text = flow_brief.render(facts)
        self.assertIn("- added `a.py`\n- modified `b.py`\n- removed `c.py`\n"
                      "- renamed `old.py` -> `new.py`", text)


class TestWaveOneRule(unittest.TestCase):
    """Plans 07-01 (wave 1), 07-02 (wave 2) and 07-03 (no wave key, so wave 1)."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()  # removed in tearDownClass
        cls.repo = os.path.join(cls._tmp.name, "repo")
        os.makedirs(cls.repo)
        _git(cls.repo, "init", "-q", "-b", "main")
        _commit(cls.repo, "README.md", "base\n", "base")
        _git(cls.repo, "checkout", "-q", "-b", "feat/w")
        cls.phase_dir = pathlib.Path(cls.repo) / ".planning" / "phases" / "07-wave-fixture"
        cls.phase_dir.mkdir(parents=True)
        plans = {"07-01": "---\nphase: 07\nwave: 1\n---\n",
                 "07-02": "---\nphase: 07\nwave: 2\n---\n",
                 "07-03": "---\nphase: 07\n---\n"}
        for unit, text in plans.items():
            (cls.phase_dir / f"{unit}-PLAN.md").write_text(text, encoding="utf-8")
        flow_record.write_record(cls.repo, {"schema": 1, "units": []})

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def _set_summaries(self, units):
        for path in self.phase_dir.glob("*-SUMMARY.md"):
            path.unlink()
        for unit in units:
            (self.phase_dir / f"{unit}-SUMMARY.md").write_text("done\n", encoding="utf-8")

    def test_wave_one_done_needs_every_wave_one_summary(self):
        self._set_summaries(["07-02"])
        self.assertFalse(fold_adapters.index_wave_one_done(self.repo, "7"))
        self._set_summaries(["07-01"])
        self.assertFalse(fold_adapters.index_wave_one_done(self.repo, "7"))  # 07-03 has no wave key
        self._set_summaries(["07-01", "07-03"])
        self.assertTrue(fold_adapters.index_wave_one_done(self.repo, "7"))

    def test_wave_point_runs_while_a_wave_one_summary_is_missing(self):
        self._set_summaries(["07-01"])
        recorder = _Recorder()
        lines, outcome = flow_boundary.boundary(self.repo, None, "wave", phase="7",
                                                seams=_seams(recorder))
        self.assertEqual(outcome, "done")
        self.assertTrue(any(line.startswith("brief: ") for line in lines))

    def test_wave_point_is_skipped_once_wave_one_is_finished(self):
        self._set_summaries(["07-01", "07-03"])
        recorder = _Recorder()
        lines, outcome = flow_boundary.boundary(self.repo, None, "wave", phase="7",
                                                seams=_seams(recorder))
        self.assertEqual(lines, ["wave 1 finished: boundary skipped"])
        self.assertEqual(outcome, "nothing to do")
        self.assertEqual(recorder.calls, [])


class TestBriefNamesFunctionThroughFakes(_StackedFixture):
    """R1 in miniature: the previous unit's new function is named in the brief, via the fakes."""

    def setUp(self):
        super().setUp()
        tmp = pathlib.Path(tempfile.mkdtemp(prefix="ai-kit-p30-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        self.bin = tmp / "bin"
        state = tmp / "state.json"
        state.write_text("{}", encoding="utf-8")
        index_fakes.write_index_fakes(self.bin, state, tmp / "calls.log")
        patch = mock.patch.dict(os.environ, {"PATH": index_fakes.tool_path(self.bin)})
        patch.start()
        self.addCleanup(patch.stop)
        self.seams = flow_boundary.Seams(which=lambda name: os.path.join(self.bin, name),
                                         clock=lambda: 0.0, sleep=lambda seconds: None,
                                         now=lambda: _NOW)

    def test_brief_names_the_previous_units_function_and_leaves_main_alone(self):
        lines, outcome = flow_boundary.boundary(self.repo, _unit("B", "feat/b"), "plan",
                                                seams=self.seams)
        self.assertEqual(outcome, "done")
        self.assertTrue(any(line.startswith("codegraph: ran codegraph") for line in lines))
        text = self.brief_path().read_text(encoding="utf-8")
        names_line = next(line for line in text.splitlines() if line.startswith("Names searched"))
        self.assertIn("alpha_one", names_line)
        self.assertEqual(_git(self.repo, "rev-parse", "main"), self.base)

    def test_worktree_without_hooks_is_indexed_and_briefed_at_the_next_point(self):
        worktree = pathlib.Path(tempfile.mkdtemp(prefix="ai-kit-p30-")) / "wt"
        self.addCleanup(shutil.rmtree, worktree.parent, True)
        _git(self.repo, "worktree", "add", "-q", "--detach", str(worktree), "main")
        flow_boundary.boundary(str(worktree), None, "plan", seams=self.seams)
        self.assertTrue((worktree / ".codegraph").is_dir())
        self.assertTrue((worktree / flow_brief.BRIEF_REL).is_file())


class TestGsdBoundaryThroughFakes(_StackedFixture):
    """R1 in a GSD checkout: the plan and wave points brief the previous unit's function, and the
    GSD status file records the unit branch's HEAD (the codegraph and graphify fakes run)."""

    def setUp(self):
        super().setUp()
        tmp = pathlib.Path(tempfile.mkdtemp(prefix="ai-kit-p30-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        self.bin = tmp / "bin"
        state = tmp / "state.json"
        state.write_text("{}", encoding="utf-8")
        index_fakes.write_index_fakes(self.bin, state, tmp / "calls.log")
        patch = mock.patch.dict(os.environ, {"PATH": index_fakes.tool_path(self.bin)})
        patch.start()
        self.addCleanup(patch.stop)
        self.seams = flow_boundary.Seams(which=lambda name: os.path.join(self.bin, name),
                                         clock=lambda: 0.0, sleep=lambda seconds: None,
                                         now=lambda: _NOW)
        planning = pathlib.Path(self.repo) / ".planning"
        phase = planning / "phases" / "07-demo"
        phase.mkdir(parents=True, exist_ok=True)
        (planning / "PROJECT.md").write_text("# Demo\n", encoding="utf-8")
        (planning / "config.json").write_text(
            '{"graphify": {"enabled": true, "auto_update": true}}', encoding="utf-8")
        (phase / "07-01-PLAN.md").write_text("---\nphase: 07\nwave: 1\n---\n", encoding="utf-8")

    def test_plan_and_wave_points_brief_the_function_and_record_the_head(self):
        status = pathlib.Path(self.repo) / ".planning" / "graphs" / ".last-build-status.json"
        for point in ("plan", "wave"):
            lines, outcome = flow_boundary.boundary(self.repo, _unit("B", "feat/b"), point,
                                                    phase="7", seams=self.seams)
            self.assertEqual(outcome, "done", point)
            self.assertTrue(any(line.startswith("graphify: ran") for line in lines), point)
            text = self.brief_path().read_text(encoding="utf-8")
            names_line = next(line for line in text.splitlines() if line.startswith("Names"))
            self.assertIn("alpha_one", names_line, point)
            head = _git(self.repo, "rev-parse", "HEAD")
            recorded = json.loads(status.read_text(encoding="utf-8"))["head_at_build"]
            self.assertEqual(recorded, head, point)
        self.assertEqual(_git(self.repo, "rev-parse", "main"), self.base)


class TestExcludeOfIndexDirectory(unittest.TestCase):
    """A codegraph directory with its own `*` .gitignore: excluded once, status stays clean."""

    def test_entry_is_added_once_and_status_stays_clean(self):
        with tempfile.TemporaryDirectory(prefix="ai-kit-p30-") as tmp:
            repo = os.path.join(tmp, "repo")
            os.makedirs(repo)
            _git(repo, "init", "-q", "-b", "main")
            index = pathlib.Path(repo) / ".codegraph"
            index.mkdir()
            (index / ".gitignore").write_text("*\n!.gitignore\n", encoding="utf-8")
            first = flow_index.ensure_excluded(repo, [".codegraph"])
            second = flow_index.ensure_excluded(repo, [".codegraph"])
            exclude = flow_record.common_dir(repo) / "info" / "exclude"
            lines = exclude.read_text(encoding="utf-8").splitlines()
            self.assertEqual(first, ["note: ignored .codegraph/ in .git/info/exclude"])
            self.assertEqual(second, [])
            self.assertEqual(lines.count(".codegraph/"), 1)
            self.assertEqual(_git(repo, "status", "--porcelain"), "")


class TestStartBoundary(unittest.TestCase):
    """`start` runs the boundary last; its failures are one report line, never a refusal."""

    def setUp(self):
        self.args = argparse.Namespace(repo="/unused", phase=None)

    def test_success_appends_one_boundary_line(self):
        with mock.patch.object(flow_unit, "_start",
                               return_value=(["started unit B on main"], "done")), \
                mock.patch.object(flow_boundary, "boundary",
                                  return_value=(["codegraph: ran", "brief: x"], "done")) as run:
            lines, outcome = flow_unit._start_and_boundary(self.args, _unit("B", "feat/b"))
        self.assertEqual(outcome, "done")
        self.assertEqual(lines, ["started unit B on main", "boundary: codegraph: ran | brief: x"])
        self.assertEqual(run.call_args.args[1].id, "B")
        self.assertEqual(run.call_args.args[2], "start")

    def test_flow_error_becomes_a_skipped_line(self):
        with mock.patch.object(flow_unit, "_start", return_value=(["started"], "done")), \
                mock.patch.object(flow_boundary, "boundary",
                                  side_effect=FlowError("ref_mismatch", "boom")):
            lines, outcome = flow_unit._start_and_boundary(self.args, _unit("B", "feat/b"))
        self.assertEqual(outcome, "done")
        self.assertEqual(lines[-1], "boundary: skipped: ref_mismatch: boom")

    def test_os_error_becomes_a_skipped_line(self):
        with mock.patch.object(flow_unit, "_start", return_value=(["started"], "done")), \
                mock.patch.object(flow_boundary, "boundary", side_effect=OSError("disk gone")):
            lines, _ = flow_unit._start_and_boundary(self.args, _unit("B", "feat/b"))
        self.assertEqual(lines[-1], "boundary: skipped: os_error: disk gone")

    def test_joined_hotfix_unit_is_the_one_briefed(self):
        record = {"schema": 1, "units": [_entry("HF", "fix/hf", "0" * 40, kind="hotfix")]}
        with mock.patch.object(flow_unit, "_start",
                               return_value=(["joins hotfix unit HF"], "done")), \
                mock.patch.object(flow_unit, "read_record", return_value=record), \
                mock.patch.object(flow_boundary, "boundary",
                                  return_value=(["brief: y"], "done")) as run:
            flow_unit._start_and_boundary(self.args, _unit("B", "feat/b"))
        self.assertEqual(run.call_args.args[1].id, "HF")


def _names_line(text):
    return next(line for line in text.splitlines() if line.startswith("Names"))


class TestCliFlows(unittest.TestCase):
    """The unit flow through the CLI (plan 30-04 Task 3): the superpowers fixture's three points,
    a commit on the previous unit after this one started, argparse exit codes, and a real `start`
    on a checked-out hotfix unit. Every codegraph and graphify call is the fake's."""

    @classmethod
    def setUpClass(cls):
        cls.scratch = pathlib.Path(tempfile.mkdtemp(prefix="ai-kit-p30-cli-"))
        cls.addClassCleanup(shutil.rmtree, cls.scratch, True)
        template = cls.scratch / "template"
        template.mkdir()
        (template / "home").mkdir()
        env = f.git_env(template / "home")
        repo = f.make_repo(template, env)
        f.commit(repo, env, {f.SP_PLAN: f.SP_PLAN_TEXT.encode()}, "docs: add plan")
        f.make_remote(template, env, repo)
        cls.template = template

    def setUp(self):
        self.dest = pathlib.Path(tempfile.mkdtemp(prefix="case-", dir=self.scratch))
        shutil.copytree(self.template, self.dest, dirs_exist_ok=True)
        self.repo = self.dest / "repo"
        self.env = f.git_env(self.dest / "home")
        f.rebind(self.dest, self.env, self.repo, self.dest / "remote.git")

    def fold(self, *args):
        proc = subprocess.run(
            [sys.executable, str(FOLD), *args, "--repo", str(self.repo)],
            capture_output=True, text=True, env=self.env, check=False)
        return proc.returncode, proc.stdout + proc.stderr

    def unit_file(self, unit_id, branch):
        path = self.dest / f"{unit_id}.json"
        path.write_text(json.dumps({"schema": 1, "id": unit_id, "kind": "stacked",
                                    "branch": branch, "title": f"Unit {unit_id}"}),
                        encoding="utf-8")
        return str(path)

    def switch(self, branch):
        f.run_git(self.repo, self.env, "switch", "-q", branch)

    def commit(self, files, message):
        return f.commit(self.repo, self.env, files, message)

    def brief(self):
        return (self.repo / flow_brief.BRIEF_REL).read_text(encoding="utf-8")

    def start_a_with_alpha(self):
        code, text = self.fold("start", "--unit", self.unit_file("A", "demo/unit-a"))
        self.assertEqual(code, 0, text)
        self.switch("demo/unit-a")
        self.commit({"pkg/alpha.py": b"def alpha_one():\n    return 1\n"}, "feat: add alpha")

    def test_superpowers_plan_and_wave_points_brief_the_previous_unit(self):
        self.start_a_with_alpha()
        code, text = self.fold("boundary", "--next", "--point", "plan")
        self.assertEqual(code, 0, text)
        self.assertIn("unit: next (for whoever writes the next unit's plan)", self.brief())
        self.assertIn("Previous unit A (`demo/unit-a`)", self.brief())
        self.assertIn("alpha_one", _names_line(self.brief()))
        code, text = self.fold("start", "--plan", f.SP_PLAN)
        self.assertEqual(code, 0, text)
        self.assertNotIn("boundary: skipped", text)
        self.switch("plan/demo-plan")
        code, text = self.fold("boundary", "--plan", f.SP_PLAN, "--point", "wave")
        self.assertEqual(code, 0, text)
        self.assertIn("point: wave\n", self.brief())
        self.assertIn("Previous unit A (`demo/unit-a`)", self.brief())
        self.assertIn("alpha_one", _names_line(self.brief()))
        self.assertFalse((self.repo / ".planning").exists())

    def test_commit_on_previous_unit_after_start_is_listed_by_next_boundary(self):
        self.start_a_with_alpha()
        code, text = self.fold("start", "--unit", self.unit_file("B", "demo/unit-b"))
        self.assertEqual(code, 0, text)
        self.switch("demo/unit-a")
        self.commit({"pkg/late.py": b"def late_one():\n    return 2\n"}, "feat: late")
        self.switch("demo/unit-b")
        code, text = self.fold("boundary", "--unit-id", "B", "--point", "plan")
        self.assertEqual(code, 0, text)
        self.assertIn("- added `pkg/late.py`", self.brief())
        # the file is not in this checkout (it sits on unit A's branch only), so codegraph
        # explores nothing for it and the names line carries its file name alone
        self.assertIn("late.py", _names_line(self.brief()))
        self.assertNotIn("late_one", _names_line(self.brief()))

    def _raw(self, *args):
        proc = subprocess.run(
            [sys.executable, str(FOLD), "boundary", *args, "--repo", str(self.repo)],
            capture_output=True, text=True, env=self.env, check=False)
        return proc.returncode, proc.stderr

    def test_point_outside_the_three_exits_two(self):
        code, stderr = self._raw("--unit-id", "B", "--point", "bogus")
        self.assertEqual(code, 2)
        self.assertIn("invalid choice", stderr)

    def test_missing_selector_exits_two(self):
        code, stderr = self._raw("--point", "plan")
        self.assertEqual(code, 2)
        self.assertIn("required", stderr)

    def test_start_on_a_checked_out_hotfix_unit_briefs_the_hotfix_unit(self):
        head = f.run_git(self.repo, self.env, "rev-parse", "main").strip()
        flow_record.write_record(self.repo, {"schema": 1, "units": [
            _entry("hot-1", "hotfix/fix-1", head, kind="hotfix")]})
        f.run_git(self.repo, self.env, "branch", "hotfix/fix-1", "main")
        self.switch("hotfix/fix-1")
        code, text = self.fold("start", "--unit", self.unit_file("B", "demo/unit-b"))
        self.assertEqual(code, 0, text)
        self.assertIn("joins hotfix unit hot-1", text)
        self.assertNotIn("boundary: skipped", text)
        self.assertIn("boundary: ", text)
        self.assertIn("unit: hot-1\n", self.brief())
        self.assertNotIn("unit: B\n", self.brief())


if __name__ == "__main__":
    unittest.main()
