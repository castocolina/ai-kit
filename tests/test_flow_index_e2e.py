"""E2E for the index step (30-01): real `node` and the checkout's project-local gsd-tools.

`fold.py index` runs against a GSD fixture (a temp repo with `.planning/`), with the fakes
from `tests/index_fakes.py` standing in for codegraph and graphify. Then the real
`gsd-tools graphify status` must read the copy as built at HEAD and not stale.
"""

import importlib.util
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

_REPO = pathlib.Path(__file__).resolve().parent.parent
_GSD_TOOLS = _REPO / ".claude" / "gsd-core" / "bin" / "gsd-tools.cjs"
_SCRIPTS = _REPO / "skills" / "ai-kit-commit-fold" / "scripts"
FOLD = _SCRIPTS / "fold.py"
sys.path.insert(0, str(_REPO))
sys.path.insert(0, str(_SCRIPTS))

import flow_index

from tests import index_fakes
from tests.fold_fixtures import commit, git_env, make_repo, run_git

HOOK_BLOCK_START = "      # post-checkout: queue a new worktree"


@unittest.skipUnless(shutil.which("node") and _GSD_TOOLS.is_file(),
                     "node or the checkout's project-local gsd-core is missing")
class TestGsdGraphStatus(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="ai-kit-p30-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.home = self.tmp / "home"
        self.home.mkdir()
        self.env = git_env(self.home)
        self.repo = make_repo(self.tmp, self.env).resolve()
        commit(self.repo, self.env, {
            ".planning/PROJECT.md": b"# demo\n",
            ".planning/config.json": json.dumps(
                {"graphify": {"enabled": True, "auto_update": True}}).encode(),
        }, "docs: gsd fixture")
        for name in ("gsd-core", "scripts"):
            source = _REPO / ".claude" / name
            if source.is_dir():
                shutil.copytree(source, self.repo / ".claude" / name, symlinks=True)

    def test_gsd_status_reports_the_copy_built_at_head(self):
        index = subprocess.run([sys.executable, str(FOLD), "index", "--repo", str(self.repo)],
                               capture_output=True, text=True, env=self.env, check=False)
        self.assertEqual(index.returncode, 0, index.stderr)
        env = dict(self.env, GSD_HOME=str(self.tmp / "gsd-home"))
        status = subprocess.run(
            ["node", str(self.repo / ".claude" / "gsd-core" / "bin" / "gsd-tools.cjs"),
             "graphify", "status", "--raw"],
            cwd=self.repo, capture_output=True, text=True, env=env, check=False,
        )
        self.assertEqual(status.returncode, 0, status.stderr)
        data = json.loads(status.stdout)
        head = run_git(self.repo, self.env, "rev-parse", "--short=7", "HEAD").strip()
        self.assertEqual(data["built_at_commit"], head)
        self.assertIs(data["stale"], False)


@unittest.skipUnless(importlib.util.find_spec("pre_commit"),
                     "pre_commit not importable (run under uv: make e2e-test)")
class TestWorktreeHook(unittest.TestCase):
    """Real `git worktree add` through the real post-checkout hook (SPEC R6)."""

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="ai-kit-p30-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.home = self.tmp / "home"
        self.home.mkdir()
        self.env = git_env(self.home)
        self.repo = make_repo(self.tmp, self.env).resolve()
        # cleanups run last-in first-out: the barrier runs before the removal above
        self.addCleanup(self.settle)
        self.common = flow_index.flow_record.common_dir(str(self.repo))
        self.state = index_fakes.fakes_dir(self.home) / "state.json"
        self.install_hook()

    def install_hook(self):
        # no __pycache__: a committed .pyc that the runner rewrites fails pre-commit's diff check
        shutil.copytree(_SCRIPTS.parent, self.repo / "skills" / "ai-kit-commit-fold",
                        ignore=shutil.ignore_patterns("__pycache__"))
        real = (_REPO / ".pre-commit-config.yaml").read_text(encoding="utf-8")
        block = real[real.index(HOOK_BLOCK_START):]
        config = ("default_install_hook_types: [post-checkout]\n"
                  "default_stages: [pre-commit, pre-push]\n"
                  "repos:\n  - repo: local\n    hooks:\n" + block)
        (self.repo / ".pre-commit-config.yaml").write_text(config, encoding="utf-8")
        run_git(self.repo, self.env, "add", "--", "skills/ai-kit-commit-fold",
                ".pre-commit-config.yaml")
        run_git(self.repo, self.env, "commit", "-q", "-m", "chore: install index hook fixture")
        subprocess.run([sys.executable, "-m", "pre_commit", "install", "-t", "post-checkout"],
                       cwd=self.repo, env=self.env, capture_output=True, check=True)

    def settle(self):
        """Wait (up to 60 s) for the detached runner to release the job lock."""
        with flow_index.index_lock(self.common, deadline_s=60) as held:
            self.assertTrue(held, "detached runner still holds the index lock after 60 s")

    def add_worktree(self, name, *extra):
        path = self.tmp / name
        started = time.monotonic()
        proc = subprocess.Popen(["git", "-C", str(self.repo), "worktree", "add", "-q",
                                 "--detach", *extra, str(path)],
                                env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = proc.communicate()
        # measured, not slept: SPEC R6 under-1-s bound for the git command
        elapsed = time.monotonic() - started
        self.assertEqual(proc.returncode, 0, err.decode("utf-8", "replace") + out.decode())
        return path, elapsed

    def log_lines(self):
        log = self.common / flow_index.LOG_NAME
        return log.read_text(encoding="utf-8").splitlines() if log.is_file() else []

    def test_two_concurrent_adds_return_fast_and_each_worktree_is_indexed_in_order(self):
        index_fakes.set_state(self.state, delay_s=1.5)
        started = time.monotonic()
        procs = [subprocess.Popen(["git", "-C", str(self.repo), "worktree", "add", "-q",
                                   "--detach", str(self.tmp / name)],
                                  env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                 for name in ("wt-a", "wt-b")]
        for proc in procs:
            _, err = proc.communicate()
            self.assertEqual(proc.returncode, 0, err.decode("utf-8", "replace"))
        # measured, not slept: both adds return within the SPEC R6 bound
        self.assertLess(time.monotonic() - started, 1.0)
        self.settle()
        for name in ("wt-a", "wt-b"):
            path = self.tmp / name
            self.assertTrue((path / ".codegraph").is_dir(), name)
            self.assertTrue((path / "graphify-out" / "graph.json").is_file(), name)
        queued = [line.split(" queued ", 1)[1] for line in self.log_lines() if " queued " in line]
        starts = [line.split(" start ", 1)[1] for line in self.log_lines() if " start " in line]
        self.assertEqual(len(queued), 2)
        self.assertEqual(starts, queued)
        self.assertEqual(sum(" end " in line for line in self.log_lines()), 2)
        queue = self.common / flow_index.QUEUE_NAME
        self.assertEqual(queue.read_text(encoding="utf-8") if queue.is_file() else "", "")

    def test_no_checkout_add_is_not_queued(self):
        _, elapsed = self.add_worktree("wt-first")
        self.assertLess(elapsed, 1.0)
        self.settle()
        before = sum(" queued " in line for line in self.log_lines())
        self.add_worktree("wt-no-checkout", "--no-checkout")
        self.settle()
        self.assertEqual(sum(" queued " in line for line in self.log_lines()), before)

    def test_main_checkout_gets_no_index_output_in_git_status(self):
        self.add_worktree("wt-status")
        self.settle()
        status = run_git(self.repo, self.env, "status", "--porcelain")
        self.assertEqual(status.strip(), "")


if __name__ == "__main__":
    unittest.main()
