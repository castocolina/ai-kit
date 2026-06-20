"""T2.6 — End-to-end worktree display with REAL git worktrees.

Hermetic: every path lives under one self-contained tmpdir, so the suite never
touches the live workspace. Renders the real status-line.py as a subprocess with
its `workspace.current_dir` pointed at each location, and asserts the `worktree`
segment for all four cases:

  * `.claude/worktrees/feat-x`            -> `⎇ feat-x`
  * `../worktrees/.ai-kit/feat-y`         -> `⎇ feat-y`
  * the main checkout                     -> struck `⎇ wt`
  * outside any git repo                  -> no worktree segment

Requires `git` on PATH (skipped otherwise).
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

_HERE = os.path.dirname(__file__)
_STATUS_LINE = os.path.abspath(os.path.join(_HERE, "..", "tools", "status-line.py"))
_ANSI = re.compile(r"\033\[[0-9;]*m")


def _have_git():
    return shutil.which("git") is not None


@unittest.skipUnless(_have_git(), "git not available")
class TestWorktreeDisplayE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="aikit-wt-e2e-")
        cls.home = os.path.join(cls.tmp, "home")
        os.makedirs(cls.home, exist_ok=True)
        cls.repo = os.path.join(cls.tmp, "repo")

        def git(*args, cwd=None):
            subprocess.run(["git", *args], cwd=cwd, check=True,
                           capture_output=True, text=True)

        git("init", "-q", cls.repo)
        # Deterministic identity + an initial commit so worktrees can be added.
        git("config", "user.email", "e2e@test", cwd=cls.repo)
        git("config", "user.name", "e2e", cwd=cls.repo)
        git("commit", "-q", "--allow-empty", "-m", "init", cwd=cls.repo)

        # Convention 1: <repo>/.claude/worktrees/feat-x  (absolute under tmpdir).
        cls.wt_x = os.path.join(cls.repo, ".claude", "worktrees", "feat-x")
        git("worktree", "add", "-q", cls.wt_x, cwd=cls.repo)
        # Convention 2: ../worktrees/.ai-kit/feat-y, resolved relative to <repo>.
        cls.wt_y = os.path.join(cls.tmp, "worktrees", ".ai-kit", "feat-y")
        git("worktree", "add", "-q", cls.wt_y, cwd=cls.repo)

        # A directory outside any repo (sibling of <repo>, not git-tracked).
        cls.outside = os.path.join(cls.tmp, "outside")
        os.makedirs(cls.outside, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _render(self, current_dir):
        sample = json.dumps({
            "model": {"display_name": "Opus 4.8", "id": "claude-opus-4-8"},
            "workspace": {"current_dir": current_dir},
            "context_window": {"used_percentage": 10, "context_window_size": 200000},
            "transcript_path": "", "session_id": "e2e",
        })
        env = {
            **os.environ,
            "HOME": self.home,
            "XDG_CACHE_HOME": os.path.join(self.home, ".cache"),
            "CC_AI_KIT_CONFIG": "/no/such.toml",   # built-in defaults (worktree ON)
            "STATUSLINE_COLS": "200", "STATUSLINE_LINES": "50",
        }
        p = subprocess.run([sys.executable, _STATUS_LINE], input=sample,
                           capture_output=True, text=True, env=env, cwd=current_dir)
        self.assertEqual(p.returncode, 0, p.stderr)
        return p.stdout

    def test_claude_worktrees_convention_shows_name(self):
        out = self._render(self.wt_x)
        self.assertIn("⎇ feat-x", _ANSI.sub("", out))
        self.assertNotIn("\033[9m", out)            # active form is NOT struck

    def test_dot_ai_kit_worktrees_convention_shows_name(self):
        out = self._render(self.wt_y)
        self.assertIn("⎇ feat-y", _ANSI.sub("", out))
        self.assertNotIn("\033[9m", out)

    def test_main_checkout_shows_struck_placeholder(self):
        out = self._render(self.repo)
        self.assertIn("⎇ wt", _ANSI.sub("", out))
        self.assertIn("\033[9m", out)               # struck-through placeholder

    def test_outside_repo_hides_worktree_segment(self):
        out = self._render(self.outside)
        self.assertNotIn("⎇", out)                  # no worktree glyph at all


if __name__ == "__main__":
    unittest.main()
