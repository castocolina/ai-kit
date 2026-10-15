"""E2E tier: real node and git, hermetic env for the cross-AI runner template."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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


if __name__ == "__main__":
    unittest.main()
