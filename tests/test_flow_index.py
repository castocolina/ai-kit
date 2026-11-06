"""Unit and CLI cases for the index step (30-01): codegraph choice order, graphify freshness.

Every codegraph and graphify call reaches the recording fakes in `tests/index_fakes.py`,
never a real tool: `git_env` puts the fake bin first on PATH, and the in-process cases pass
`which` pointing at that bin.
"""

import contextlib
import fcntl
import functools
import io
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

_REPO = pathlib.Path(__file__).resolve().parent.parent
_SCRIPTS = _REPO / "skills" / "ai-kit-commit-fold" / "scripts"
sys.path.insert(0, str(_SCRIPTS))
sys.path.insert(0, str(_REPO))

import flow_index

from tests import host_fakes, index_fakes
from tests.fold_fixtures import commit, git_env, make_repo, run_git

FOLD = _SCRIPTS / "fold.py"
NOT_GSD_LINE = "graphify: ran graphify update .; graphify-out only (not a GSD project)"


class _Base(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="ai-kit-p30-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.home = self.tmp / "home"
        self.home.mkdir()
        self.env = git_env(self.home)
        self.repo = make_repo(self.tmp, self.env).resolve()
        self.top = str(self.repo)
        fakes = index_fakes.fakes_dir(self.home)
        self.bin = fakes / "bin"
        self.state = fakes / "state.json"
        self.log = fakes / "calls.log"

    def which(self, name):
        path = self.bin / name
        return str(path) if path.exists() else None

    def set_state(self, **fields):
        index_fakes.set_state(self.state, **fields)

    def calls(self):
        return index_fakes.index_calls(self.log)

    def make_codegraph_dir(self):
        (self.repo / ".codegraph").mkdir(exist_ok=True)

    def refresh(self):
        return flow_index.refresh(self.top, which=self.which)


class CodegraphChoiceTests(_Base):
    def test_no_own_index_runs_init_then_graphify_builds_at_head(self):
        lines = self.refresh()
        self.assertEqual(lines[0], "codegraph: ran codegraph init -y (no index of its own)")
        self.assertEqual(lines[1], NOT_GSD_LINE)
        graph = json.loads((self.repo / "graphify-out" / "graph.json").read_text("utf-8"))
        head = run_git(self.repo, self.env, "rev-parse", "HEAD").strip()
        self.assertEqual(graph["built_at_commit"], head)

    def test_worktree_mismatch_runs_init(self):
        self.make_codegraph_dir()
        self.set_state(codegraph_status={self.top: {
            "initialized": True, "worktreeMismatch": "/elsewhere",
            "index": {"reindexRecommended": False}}})
        self.assertEqual(self.refresh()[0], "codegraph: ran codegraph init -y (worktreeMismatch)")

    def test_reindex_recommended_runs_index(self):
        self.make_codegraph_dir()
        self.set_state(codegraph_status={self.top: {
            "initialized": True, "worktreeMismatch": None,
            "index": {"reindexRecommended": True}}})
        self.assertEqual(self.refresh()[0], "codegraph: ran codegraph index (reindex recommended)")

    def test_current_index_runs_only_sync(self):
        self.make_codegraph_dir()
        self.assertEqual(self.refresh()[0], "codegraph: ran codegraph sync")
        verbs = [call["argv"][0] for call in self.calls() if call["name"] == "codegraph"]
        self.assertEqual(verbs, ["status", "sync"])

    def test_unreadable_status_runs_full_index(self):
        self.make_codegraph_dir()
        self.set_state(codegraph_status={self.top: "unreadable"})
        self.assertEqual(self.refresh()[0], "codegraph: ran codegraph index (status unreadable)")

    def test_failing_index_is_reported_and_graphify_still_runs(self):
        self.make_codegraph_dir()
        self.set_state(codegraph_status={self.top: "unreadable"},
                       codegraph_fail={"index": [1, "boom"]})
        lines = self.refresh()
        self.assertEqual(
            lines[0],
            "codegraph: codegraph index failed (exit 1: boom); retried at the next point",
        )
        self.assertEqual(lines[1], NOT_GSD_LINE)

    def test_sync_refused_by_codegraph_lock_is_retried_and_lock_is_kept(self):
        self.make_codegraph_dir()
        lock = self.repo / ".codegraph" / "codegraph.lock"
        lock.write_text("held\n", encoding="utf-8")
        self.set_state(codegraph_fail={"sync": [1, "error: database is locked"]})
        self.assertEqual(
            self.refresh()[0],
            "codegraph: codegraph sync refused: codegraph's lock is held; "
            "retried at the next point",
        )
        self.assertTrue(lock.exists())

    def test_missing_tools_report_one_line_each_and_run_nothing(self):
        lines = flow_index.refresh(self.top, which=lambda name: None)
        self.assertEqual(lines[0], "codegraph: not installed; would run codegraph init -y")
        self.assertEqual(lines[1], "graphify: not installed; would run graphify update .")
        self.assertEqual(self.calls(), [])


class GraphifyFreshnessTests(_Base):
    def test_stale_or_empty_graph_is_never_a_fresh_build(self):
        self.assertEqual(self.refresh()[1], NOT_GSD_LINE)
        commit(self.repo, self.env, {"next.txt": b"next\n"}, "chore: next")
        no_graph = "graphify: graphify update . wrote no graph; previous graph kept"
        self.set_state(graphify_no_graph=True)
        self.assertEqual(self.refresh()[1], no_graph)
        self.set_state(graphify_no_graph=False)
        (self.repo / "graphify-out" / "graph.json").write_text("{}", encoding="utf-8")
        self.set_state(graphify_no_graph=True)
        self.assertEqual(self.refresh()[1], no_graph)

    def test_failing_graphify_is_reported(self):
        self.set_state(graphify_fail=[1, "no model"])
        self.assertEqual(
            self.refresh()[1],
            "graphify: graphify update . failed (exit 1: no model); previous graph kept",
        )


class ArgvTests(_Base):
    def test_path_with_space_and_unicode_reaches_tools_as_argv_elements(self):
        spaced = self.tmp / "my repo é"
        spaced.mkdir()
        repo = make_repo(spaced, self.env).resolve()
        flow_index.refresh(str(repo), which=self.which)
        calls = self.calls()
        self.assertTrue(calls)
        for call in calls:
            self.assertEqual(os.path.realpath(call["cwd"]), os.path.realpath(repo))
            for element in call["argv"]:
                self.assertNotIn(str(repo), element)
                self.assertNotIn(" ", element)


class CliTests(_Base):
    def run_fold(self, env, *args):
        return subprocess.run(
            [sys.executable, str(FOLD), "index", "--repo", str(self.repo), *args],
            capture_output=True, text=True, env=env, check=False,
        )

    def test_index_prints_report_and_exits_zero(self):
        proc = self.run_fold(self.env)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        lines = proc.stdout.splitlines()
        self.assertEqual(lines[0], "flow index -: main")
        self.assertTrue(lines[1].startswith("codegraph: "), lines)
        self.assertEqual(lines[2], NOT_GSD_LINE)
        self.assertEqual(lines[-1], "outcome: - done")

    def test_no_tools_on_path_exits_zero_with_both_lines(self):
        env = dict(self.env)
        env["PATH"] = index_fakes.no_tool_path(self.tmp / "notools")
        proc = self.run_fold(env)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("codegraph: not installed; would run codegraph init -y", proc.stdout)
        self.assertIn("graphify: not installed; would run graphify update .", proc.stdout)

    def test_host_path_keeps_the_index_fakes_reachable(self):
        forge_bin = self.tmp / "forge-bin"
        forge_bin.mkdir()
        path = host_fakes.host_path(forge_bin, self.env["PATH"])
        self.assertEqual(shutil.which("codegraph", path=path), str(self.bin / "codegraph"))


class _FakeClock:
    """Injected clock and sleep: `sleep` advances the clock and never waits."""

    def __init__(self):
        self.now = 0.0
        self.sleeps = []

    def clock(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


class GsdCopyTests(_Base):
    def make_gsd(self, config=None):
        planning = self.repo / ".planning"
        planning.mkdir()
        (planning / "PROJECT.md").write_text("# demo\n", encoding="utf-8")
        if config is not None:
            (planning / "config.json").write_text(json.dumps(config), encoding="utf-8")

    def enabled(self):
        self.make_gsd({"graphify": {"enabled": True, "auto_update": True}})

    def graph_bytes(self, name="graph.json"):
        return (self.repo / "graphify-out" / name).read_bytes()

    def test_gsd_copy_is_byte_equal_and_status_written(self):
        self.enabled()
        lines = self.refresh()
        graphs = self.repo / ".planning" / "graphs"
        self.assertEqual(graphs.joinpath("graph.json").read_bytes(), self.graph_bytes())
        self.assertEqual(graphs.joinpath("graph.html").read_bytes(), self.graph_bytes("graph.html"))
        self.assertEqual(graphs.joinpath(".last-build-snapshot.json").read_bytes(),
                         self.graph_bytes())
        status = json.loads(graphs.joinpath(".last-build-status.json").read_text("utf-8"))
        head = run_git(self.repo, self.env, "rev-parse", "HEAD").strip()
        self.assertEqual(status["status"], "ok")
        self.assertEqual(status["exit_code"], 0)
        self.assertEqual(status["head_at_build"], head)
        self.assertIsInstance(status["duration_ms"], int)
        self.assertEqual(status["graphify_version"], "graphify 0.0.0-fake")
        self.assertTrue(lines[1].endswith(f"copied to .planning/graphs/ (built at {head[:12]})"))

    def test_graphignore_gets_milestones_once(self):
        self.enabled()
        (self.repo / ".graphifyignore").write_text("dist/", encoding="utf-8")
        first = self.refresh()
        self.assertEqual((self.repo / ".graphifyignore").read_text("utf-8"),
                         "dist/\n.planning/milestones/\n")
        self.assertIn("note: .graphifyignore: added .planning/milestones/ (commit it)", first)
        second = self.refresh()
        self.assertFalse(any(line.startswith("note: .graphifyignore") for line in second))

    def test_graphignore_holds_milestones_before_the_first_graphify_build(self):
        self.enabled()
        seen = []

        def run(argv, cwd, timeout=900):
            if argv[1:] == ["update", "."]:
                ignore = self.repo / ".graphifyignore"
                text = ignore.read_text("utf-8") if ignore.is_file() else ""
                seen.append(".planning/milestones/" in text)
            return flow_index._run_tool(argv, cwd, timeout)

        config = (self.repo / ".planning" / "config.json").read_bytes()
        flow_index.refresh(self.top, run=run, which=self.which)
        self.assertEqual(seen, [True])
        # T-30-06: the refresh only reads GSD's config
        self.assertEqual((self.repo / ".planning" / "config.json").read_bytes(), config)

    def test_non_gsd_project_leaves_planning_and_graphignore_alone(self):
        lines = self.refresh()
        self.assertTrue(lines[1].endswith("graphify-out only (not a GSD project)"), lines)
        self.assertFalse((self.repo / ".planning").exists())
        self.assertFalse((self.repo / ".graphifyignore").exists())

    def test_disabled_or_unconfigured_gsd_gets_no_graphs_directory(self):
        self.make_gsd({"graphify": {"enabled": False}})
        disabled = "graphify-out only (graphify.enabled is not true)"
        self.assertTrue(self.refresh()[1].endswith(disabled))
        self.assertFalse((self.repo / ".planning" / "graphs").exists())
        shutil.rmtree(self.repo / ".planning")
        self.make_gsd()
        tools = self.repo / ".claude" / "gsd-core" / "bin"
        tools.mkdir(parents=True)
        (tools / "gsd-tools.cjs").write_text("// fake\n", encoding="utf-8")
        self.assertTrue(self.refresh()[1].endswith(disabled))
        self.assertFalse((self.repo / ".planning" / "graphs").exists())

    def test_graph_path_set_skips_copy(self):
        self.make_gsd({"graphify": {"enabled": True, "graph_path": "../umbrella/graph.json"}})
        path_set = "graphify-out only (graphify.graph_path is set)"
        self.assertTrue(self.refresh()[1].endswith(path_set))
        self.assertFalse((self.repo / ".planning" / "graphs").exists())

    def test_failed_build_keeps_the_previous_copy(self):
        self.enabled()
        self.refresh()
        previous = (self.repo / ".planning" / "graphs" / "graph.json").read_bytes()
        self.set_state(graphify_fail=[1, "no model"])
        line = self.refresh()[1]
        self.assertEqual(line, "graphify: graphify update . failed (exit 1: no model); "
                               "previous graph kept")
        self.assertEqual((self.repo / ".planning" / "graphs" / "graph.json").read_bytes(), previous)
        status = json.loads((self.repo / ".planning" / "graphs"
                             / ".last-build-status.json").read_text("utf-8"))
        self.assertEqual((status["status"], status["exit_code"]), ("failed", 1))

    def test_empty_graph_is_never_copied(self):
        self.enabled()
        self.refresh()
        previous = (self.repo / ".planning" / "graphs" / "graph.json").read_bytes()
        (self.repo / "graphify-out" / "graph.json").write_text("{}", encoding="utf-8")
        self.set_state(graphify_no_graph=True)
        self.assertTrue(self.refresh()[1].endswith("wrote no graph; previous graph kept"))
        self.assertEqual((self.repo / ".planning" / "graphs" / "graph.json").read_bytes(), previous)

    def test_live_rebuild_lock_skips_the_build(self):
        self.enabled()
        graphs = self.repo / ".planning" / "graphs"
        graphs.mkdir()
        lock = graphs / ".rebuild.lock"
        lock.write_text(f"{os.getpid()}\n", encoding="utf-8")
        clock = _FakeClock()
        line = flow_index.refresh(self.top, which=self.which, clock=clock.clock,
                                  sleep=clock.sleep)[1]
        self.assertEqual(line, f"graphify: GSD's rebuild lock is held by pid {os.getpid()}; "
                               "build skipped, retried at the next point")
        self.assertFalse(any(c["argv"] == ["update", "."] for c in self.calls()))
        self.assertEqual(lock.read_text(encoding="utf-8"), f"{os.getpid()}\n")

    def test_dead_rebuild_lock_is_ignored(self):
        self.enabled()
        graphs = self.repo / ".planning" / "graphs"
        graphs.mkdir()
        child = subprocess.Popen([sys.executable, "-c", "pass"])
        child.wait()
        lock = graphs / ".rebuild.lock"
        lock.write_text(f"{child.pid}\n", encoding="utf-8")
        line = self.refresh()[1]
        self.assertTrue(line.startswith("graphify: ran graphify update .; copied"), line)
        self.assertEqual(lock.read_text(encoding="utf-8"), f"{child.pid}\n")

    def test_lock_taken_during_build_skips_only_the_copy(self):
        self.enabled()
        lock = self.repo / ".planning" / "graphs" / ".rebuild.lock"
        lock.parent.mkdir(parents=True)

        def run_and_lock(argv, cwd, timeout=900):
            if argv[1:3] == ["update", "."]:
                lock.write_text(f"{os.getpid()}\n", encoding="utf-8")
            return flow_index._run_tool(argv, cwd, timeout)

        clock = _FakeClock()
        line = flow_index.refresh(self.top, run=run_and_lock, which=self.which,
                                  clock=clock.clock, sleep=clock.sleep)[1]
        self.assertEqual(line, f"graphify: GSD's rebuild lock is held by pid {os.getpid()}; "
                               "copy skipped, retried at the next point")
        self.assertFalse((self.repo / ".planning" / "graphs" / "graph.json").exists())


class _Popen:
    """Records a detached-runner launch instead of starting a process."""

    def __init__(self, error=None):
        self.calls = []
        self.error = error

    def __call__(self, argv, **kwargs):
        self.calls.append((argv, kwargs))
        if self.error is not None:
            raise self.error


class WorktreeQueueTests(_Base):
    def setUp(self):
        super().setUp()
        self.common = flow_index.flow_record.common_dir(self.top)
        self.hook_env = dict(self.env, PRE_COMMIT_FROM_REF="0" * 40)
        self.addCleanup(setattr, flow_index, "SEED_HOOKS", list(flow_index.SEED_HOOKS))

    def queue_text(self):
        queue = self.common / flow_index.QUEUE_NAME
        return queue.read_text(encoding="utf-8") if queue.is_file() else ""

    def log_text(self):
        return (self.common / flow_index.LOG_NAME).read_text(encoding="utf-8")

    def test_detach_with_a_real_ref_queues_and_launches_nothing(self):
        popen = _Popen()
        env = dict(self.env, PRE_COMMIT_FROM_REF="a" * 40)
        self.assertEqual(flow_index.detach(self.top, env=env, popen=popen), 0)
        self.assertEqual(popen.calls, [])
        self.assertEqual(self.queue_text(), "")

    def test_seed_hook_runs_once_then_checkout_is_queued_and_runner_launched(self):
        seen = []
        flow_index.SEED_HOOKS.append(lambda top: seen.append(top) or ["seeded"])
        popen = _Popen()
        self.assertEqual(flow_index.detach(self.top, env=self.hook_env, popen=popen), 0)
        self.assertEqual(seen, [self.top])
        self.assertEqual(self.queue_text(), f"{self.top}\n")
        self.assertIn(f"queued {self.top}", self.log_text())
        self.assertIn("  seeded", self.log_text())
        self.assertEqual(len(popen.calls), 1)
        argv, kwargs = popen.calls[0]
        self.assertEqual(argv[1:3], [str(flow_index._FOLD), "index"])
        self.assertEqual(argv[3:], ["--drain", "--lock-fd", argv[5], "--repo", self.top])
        self.assertEqual(kwargs["pass_fds"], (int(argv[5]),))
        self.assertTrue(kwargs["start_new_session"])
        self.assertEqual(kwargs["stdin"], subprocess.DEVNULL)
        self.assertTrue(kwargs["close_fds"])

    def test_failing_seed_hook_logs_and_still_queues(self):
        def broken(top):
            raise OSError("disk full")

        flow_index.SEED_HOOKS.append(broken)
        self.assertEqual(flow_index.detach(self.top, env=self.hook_env, popen=_Popen()), 0)
        self.assertIn("seed failed: disk full", self.log_text())
        self.assertEqual(self.queue_text(), f"{self.top}\n")

    def test_runner_is_not_launched_while_the_job_lock_is_held(self):
        popen = _Popen()
        with open(self.common / flow_index.LOCK_NAME, "a+", encoding="utf-8") as holder:
            fcntl.flock(holder, fcntl.LOCK_EX)
            flow_index.detach(self.top, env=self.hook_env, popen=popen)
        self.assertEqual(popen.calls, [])
        self.assertEqual(self.queue_text(), f"{self.top}\n")

    def test_popen_error_still_exits_zero(self):
        popen = _Popen(error=OSError("no fork"))
        self.assertEqual(flow_index.detach(self.top, env=self.hook_env, popen=popen), 0)

    def test_drain_skips_gone_paths_and_indexes_present_ones_in_queue_order(self):
        gone = str(self.tmp / "removed")
        flow_index.enqueue(self.common, gone)
        flow_index.enqueue(self.common, self.top)
        flow_index.drain(self.common, which=lambda name: None)
        log = self.log_text()
        self.assertIn(f"skipped {gone}: gone", log)
        self.assertLess(log.index(f"skipped {gone}"), log.index(f"start {self.top}"))
        self.assertIn(f"start {self.top}", log)
        self.assertIn(f"end {self.top}", log)
        self.assertIn("  codegraph: not installed", log)
        self.assertEqual(self.queue_text(), "")

    def test_lock_holder_hands_queued_work_to_a_runner_on_release(self):
        popen = _Popen()
        hand_off = functools.partial(flow_index.launch_runner, self.common, self.top, popen)
        with flow_index.index_lock(self.common, on_release=hand_off) as held:
            self.assertTrue(held)
            self.assertEqual(flow_index.detach(self.top, env=self.hook_env, popen=popen), 0)
            self.assertEqual(popen.calls, [])
        self.assertEqual(len(popen.calls), 1)
        self.assertEqual(popen.calls[0][0][3], "--drain")

    def test_release_with_empty_queue_launches_nothing(self):
        popen = _Popen()
        hand_off = functools.partial(flow_index.launch_runner, self.common, self.top, popen)
        with flow_index.index_lock(self.common, on_release=hand_off) as held:
            self.assertTrue(held)
        self.assertEqual(popen.calls, [])

    def test_lock_past_deadline_yields_false_without_waiting(self):
        with open(self.common / flow_index.LOCK_NAME, "a+", encoding="utf-8") as holder:
            fcntl.flock(holder, fcntl.LOCK_EX)
            with flow_index.index_lock(self.common, deadline_s=0) as held:
                self.assertFalse(held)

    def test_bare_index_hands_off_path_queued_during_its_refresh(self):
        handoffs = []

        def queue_during_refresh(top):
            flow_index.enqueue(self.common, self.top)
            return []

        def record_launch(common, top, popen=None):
            handoffs.append((common, top))
            return True

        with mock.patch.object(flow_index, "refresh", side_effect=queue_during_refresh), \
                mock.patch.object(flow_index, "launch_runner", side_effect=record_launch), \
                contextlib.redirect_stdout(io.StringIO()):
            status = flow_index.cmd_index(types.SimpleNamespace(
                repo=self.top, detach=False, drain=False, lock_fd=None))
        self.assertEqual(status, 0)
        self.assertEqual(handoffs, [(self.common, self.top)])

    def test_post_checkout_hook_is_configured_for_the_detach_mode_only(self):
        text = (_REPO / ".pre-commit-config.yaml").read_text(encoding="utf-8")
        self.assertIn("default_install_hook_types: [pre-commit, pre-push, post-checkout]", text)
        self.assertIn("default_stages: [pre-commit, pre-push]", text)
        self.assertIn("entry: python3 skills/ai-kit-commit-fold/scripts/fold.py index --detach",
                      text)
        self.assertEqual(text.count("post-checkout"), 3)


if __name__ == "__main__":
    unittest.main()
