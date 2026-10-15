"""E2E tier: real node and git, hermetic env for the cross-AI runner template."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
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
            proc = subprocess.run(
                [node_bin, TEMPLATE, "--self-test"],
                cwd=REPO_ROOT,
                env=runner_env(tmp),
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        self.assertIn("self-test ok", proc.stdout)


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
            proc = subprocess.run(
                [node_bin, script_path, "--self-test"],
                cwd=tmp,
                env=runner_env(tmp),
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
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
            self.assertIn("cross-ai: deadline 1770s (outer 1800s)", proc.stderr)
            self.assertLess(1770, 1800)


if __name__ == "__main__":
    unittest.main()
