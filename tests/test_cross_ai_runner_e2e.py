"""E2E tier: real node and git, hermetic env for the cross-AI runner template."""

from __future__ import annotations

import glob
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "skills", "ai-kit-gsd-curated-config"))
sys.path.insert(0, os.path.join(REPO_ROOT, "skills", "ai-kit-spec-review"))

from ai_kit_gsd_curated_config import cross_ai_script
from ai_kit_spec.detection import HOST_SIGNAL_ENV_VARS


def _real_node_executable() -> str | None:
    if shutil.which("node") is None:
        return None
    try:
        proc = subprocess.run(
            ["node", "-e", "process.stdout.write(process.execPath)"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return proc.stdout if proc.returncode == 0 and os.path.isfile(proc.stdout) else None

TEMPLATE = os.path.join(
    REPO_ROOT, "skills", "ai-kit-spec-review", "references", "cross-ai.mjs"
)


def runner_env(tmp: str) -> dict[str, str]:
    """Hermetic env matching cross-ai.mjs --self-test (fakes + node + git only)."""
    bin_dir = os.path.join(tmp, "bin")
    os.makedirs(bin_dir, exist_ok=True)
    node_bin = _real_node_executable()
    git_bin = shutil.which("git")
    if node_bin:
        link = os.path.join(bin_dir, "node")
        if not os.path.lexists(link):
            os.symlink(node_bin, link)
    if git_bin:
        link = os.path.join(bin_dir, "git")
        if not os.path.lexists(link):
            os.symlink(git_bin, link)
    home = os.path.join(tmp, "home")
    os.makedirs(home, exist_ok=True)
    return {
        "PATH": bin_dir,
        "HOME": home,
        "XDG_CONFIG_HOME": os.path.join(home, ".config"),
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "xai-selftest",
        "GIT_COMMITTER_NAME": "xai-selftest",
        "GIT_AUTHOR_EMAIL": "xai-selftest@example.invalid",
        "GIT_COMMITTER_EMAIL": "xai-selftest@example.invalid",
        "LANG": "C",
    }


def run_group(argv: list[str], timeout: int, **kwargs) -> subprocess.CompletedProcess:
    """`subprocess.run` in a new session; a timeout kills the whole group, not just the
    leader, so no fake CLI outlives the test."""
    with subprocess.Popen(
        argv,
        start_new_session=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        **kwargs,
    ) as proc:
        try:
            out, err = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            out, err = proc.communicate()
            raise
        return subprocess.CompletedProcess(argv, proc.returncode, out, err)


def pids_with_cwd_under(root: str) -> list[int]:
    out = []
    for name in os.listdir("/proc"):
        if not name.isdigit():
            continue
        try:
            cwd = os.readlink(f"/proc/{name}/cwd")
        except OSError:
            continue
        if cwd == root or cwd.startswith(root + os.sep):
            out.append(int(name))
    return out


class TestRunnerTemplate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._skip = None
        if _real_node_executable() is None:
            cls._skip = "no node executable"
        elif shutil.which("git") is None:
            cls._skip = "git not on PATH"

    def setUp(self):
        if self._skip:
            self.skipTest(self._skip)

    def test_self_test(self):
        node_bin = _real_node_executable()
        assert node_bin is not None
        with tempfile.TemporaryDirectory() as tmp:
            proc = run_group(
                [node_bin, TEMPLATE, "--self-test"], 180, cwd=REPO_ROOT, env=runner_env(tmp)
            )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertIn("self-test ok", proc.stdout)

    @unittest.skipUnless(os.path.isdir("/proc/self"), "needs /proc to find survivors")
    def test_interrupted_self_test_leaves_nothing(self):
        node_bin = _real_node_executable()
        assert node_bin is not None
        with tempfile.TemporaryDirectory() as tmp:
            st_tmp = os.path.join(tmp, "st")
            os.makedirs(st_tmp)
            env = {
                **runner_env(tmp),
                "TMPDIR": st_tmp,
                "AIKIT_XAI_SELFTEST_CASES": "sigterm-hang",
            }
            with subprocess.Popen(
                [node_bin, TEMPLATE, "--self-test"],
                cwd=REPO_ROOT,
                env=env,
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            ) as proc:
                try:
                    deadline = time.monotonic() + 30
                    pattern = os.path.join(st_tmp, "xai-st-*", "r-sigterm-hang", "gc.pid")
                    while not glob.glob(pattern):
                        self.assertLess(time.monotonic(), deadline, "fake CLI never started")
                        time.sleep(0.05)
                    proc.send_signal(signal.SIGTERM)
                    rc = proc.wait(timeout=15)
                finally:
                    if proc.poll() is None:
                        os.killpg(proc.pid, signal.SIGKILL)
            survivors = pids_with_cwd_under(st_tmp)
            for pid in survivors:
                os.kill(pid, signal.SIGKILL)
            self.assertEqual(rc, 128 + signal.SIGTERM)
            self.assertEqual(survivors, [])
            self.assertEqual(os.listdir(st_tmp), [])


class TestRenderedRunner(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._skip = None
        if _real_node_executable() is None:
            cls._skip = "no node executable"
        elif shutil.which("git") is None:
            cls._skip = "git not on PATH"
        with open(TEMPLATE, "rb") as f:
            cls._template = f.read()

    def setUp(self):
        if self._skip:
            self.skipTest(self._skip)

    def _artifact(self) -> dict:
        return {
            "kind": "cross-ai-script",
            "path": ".planning/scripts/cross-ai.mjs",
            "template": "cross-ai.mjs",
            "version": 2,
            "config": {
                "prefer": ["pi", "cursor"],
                "models": {"pi": "router-env/my-coding"},
                "outer_timeout_s": 1800,
                "router_backed": {"pi": True},
            },
            "choices": {},
            "status": "ok",
            "source": "preset",
            "why": "e2e render",
        }

    def test_render_and_self_test(self):
        node_bin = _real_node_executable()
        assert node_bin is not None
        with tempfile.TemporaryDirectory() as tmp:
            plan = cross_ai_script.plan_script(
                tmp, self._artifact(), self._template, HOST_SIGNAL_ENV_VARS
            )
            self.assertEqual(plan.kind, "add")
            cross_ai_script.write_script(plan)
            script_path = os.path.join(tmp, ".planning", "scripts", "cross-ai.mjs")
            with open(script_path, "rb") as f:
                written = f.read()
            self.assertEqual(cross_ai_script.script_state(written), "pristine")
            proc = run_group(
                [node_bin, script_path, "--self-test"], 180, cwd=tmp, env=runner_env(tmp)
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)

    def test_rendered_deadline_below_timeout(self):
        node_bin = _real_node_executable()
        assert node_bin is not None
        with tempfile.TemporaryDirectory() as tmp:
            cfg_dir = os.path.join(tmp, ".planning")
            os.makedirs(cfg_dir, exist_ok=True)
            with open(os.path.join(cfg_dir, "config.json"), "w", encoding="utf-8") as f:
                json.dump({"workflow": {"cross_ai_timeout": 1800}}, f)
            plan = cross_ai_script.plan_script(
                tmp, self._artifact(), self._template, HOST_SIGNAL_ENV_VARS
            )
            cross_ai_script.write_script(plan)
            script_path = os.path.join(tmp, ".planning", "scripts", "cross-ai.mjs")
            proc = subprocess.run(
                [node_bin, script_path, "--print-argv"],
                cwd=tmp,
                env=runner_env(tmp),
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr)
            match = re.search(r"cross-ai: deadline (\d+)s \(outer (\d+)s\)", proc.stderr)
            assert match is not None, proc.stderr
            self.assertEqual(int(match.group(2)), 1800)
            self.assertLess(int(match.group(1)), 1800)  # SPEC R6: strictly below the timeout


if __name__ == "__main__":
    unittest.main()
