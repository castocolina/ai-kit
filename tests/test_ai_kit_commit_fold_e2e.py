"""Real GSD run for the ai-kit-commit-fold capability (the e2e tier). It runs real `node` against
the checkout's project-local gsd-core, copied into a temp fixture project. HOME and GSD_HOME are
temp dirs; nothing is installed into this repository. Skips with a named reason when `node` or the
project-local gsd-core is missing."""

import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

from tests.fold_fixtures import ROOT, SKILL, git_env, gsd_project, run_git

GSD_TOOLS = ROOT / ".claude" / "gsd-core" / "bin" / "gsd-tools.cjs"
BUNDLE = SKILL / "gsd" / "ai-kit-commit-fold"
MODULE = BUNDLE / "ai-kit-fold.cjs"


def _gsd_env(home, gsd_home):
    env = git_env(home)
    env.update(GSD_HOME=str(gsd_home), AI_KIT_REFUSE_REAL_HOME="1")
    return env


def _gsd(repo, env, *args):
    return subprocess.run(["node", str(GSD_TOOLS), *args], cwd=repo, env=env,
                          capture_output=True, text=True, check=False)


def _fixture(root, env):
    """A phase-07 fixture project with the checkout's project-local gsd-core copied in."""
    repo = gsd_project(root, env, "sequential", [{"plan": "01", "stems": ("a", "b")}])
    for part in (".claude/gsd-core", ".claude/scripts"):
        shutil.copytree(ROOT / part, repo / part, symlinks=True)
    return repo


def _json(text):
    """The first JSON object in `text` (gsd-tools may print a line before it)."""
    return json.JSONDecoder().raw_decode(text[text.index("{"):])[0]


def _skills_roots(env):
    """The fold's skills-root list from the command module, computed by a node child."""
    script = ("const m = require(process.argv[1]);"
              " process.stdout.write(JSON.stringify(m.skillsRoots(JSON.parse(process.argv[2]))));")
    proc = subprocess.run(["node", "-e", script, str(MODULE), json.dumps(env)],
                          capture_output=True, text=True, check=True)
    return json.loads(proc.stdout)


@unittest.skipUnless(shutil.which("node") and GSD_TOOLS.is_file()
                     and (ROOT / ".claude" / "scripts").is_dir(),
                     "node or the checkout's project-local gsd-core is missing")
class TestCapabilityE2E(unittest.TestCase):
    # Slow on purpose: setUpClass runs real gsd-tools several times, about a second each.
    @classmethod
    def setUpClass(cls):
        cls.tmp = pathlib.Path(tempfile.mkdtemp(prefix="ai-kit-p29-"))
        cls.addClassCleanup(shutil.rmtree, cls.tmp, ignore_errors=True)
        cls.home = cls.tmp / "home"
        cls.gsd_home = cls.tmp / "gsd-home"
        cls.home.mkdir()
        cls.gsd_home.mkdir()
        cls.env = _gsd_env(cls.home, cls.gsd_home)
        repo = _fixture(cls.tmp / "fixture", cls.env)
        shutil.copytree(SKILL, cls.home / ".claude" / "skills" / "ai-kit-commit-fold",
                        ignore=shutil.ignore_patterns("__pycache__"))
        cls.install_no_yes = _gsd(repo, cls.env, "capability", "install", str(BUNDLE),
                                  "--scope", "project")
        cls.install_yes = _gsd(repo, cls.env, "capability", "install", str(BUNDLE),
                               "--scope", "project", "--yes")
        cls.hooks = _gsd(repo, cls.env, "loop", "render-hooks", "execute:wave:post", "--raw")
        cls.fold = _gsd(repo, cls.env, "ai-kit-fold", "run", "--phase", "7", "--raw")
        cls.repo = repo
        # The same installed capability, but HOME holds no fold skill: the command must refuse.
        missing_home = cls.tmp / "home-empty"
        missing_home.mkdir()
        cls.missing_env = _gsd_env(missing_home, cls.gsd_home)
        cls.missing = _fixture(cls.tmp / "missing", cls.missing_env)
        _gsd(cls.missing, cls.missing_env, "capability", "install", str(BUNDLE),
             "--scope", "project", "--yes")
        cls.missing_head = run_git(cls.missing, cls.missing_env, "rev-parse", "HEAD").strip()
        cls.missing_run = _gsd(cls.missing, cls.missing_env, "ai-kit-fold", "run", "--phase", "7",
                               "--raw")

    def test_install_without_yes_is_refused_and_names_the_command_module(self):
        self.assertEqual(self.install_no_yes.returncode, 1)
        self.assertIn("command module", (self.install_no_yes.stdout + self.install_no_yes.stderr)
                      .lower())

    def test_install_with_yes_installs(self):
        self.assertEqual(self.install_yes.returncode, 0, self.install_yes.stderr)
        self.assertEqual(_json(self.install_yes.stdout)["status"], "installed")

    def test_render_hooks_lists_the_fold_step(self):
        self.assertEqual(self.hooks.returncode, 0, self.hooks.stderr)
        hooks = [hook for hook in _json(self.hooks.stdout)["activeHooks"]
                 if hook.get("capId") == "ai-kit-commit-fold"]
        self.assertEqual(len(hooks), 1)
        self.assertEqual(hooks[0]["kind"], "step")
        self.assertEqual(hooks[0]["ref"], {"command": "ai-kit-fold run"})

    def test_fold_run_folds_the_fixture_plan_into_two_commits(self):
        self.assertEqual(self.fold.returncode, 0, self.fold.stderr)
        lines = self.fold.stdout.splitlines()
        self.assertEqual(len(lines), 5)
        self.assertEqual(lines[-1], "outcome: 07-01 folded (inline)")
        subjects = run_git(self.repo, self.env, "log", "--format=%s", "HEAD").splitlines()
        self.assertEqual(subjects.index("docs(07): create phase plan"), 2)

    def test_fold_run_rejects_a_phase_id_with_three_parts(self):
        proc = _gsd(self.repo, self.env, "ai-kit-fold", "run", "--phase", "1.2.3", "--raw")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("usage", proc.stderr)

    def test_fold_run_without_the_skill_refuses_and_moves_nothing(self):
        self.assertNotEqual(self.missing_run.returncode, 0)
        self.assertIn("fold script not found", self.missing_run.stdout)
        head = run_git(self.missing, self.env, "rev-parse", "HEAD").strip()
        self.assertEqual(head, self.missing_head)

    def test_skills_roots_with_a_full_env_list_the_five_host_dirs(self):
        env = {"HOME": "/h", "CLAUDE_CONFIG_DIR": "/cc", "XDG_CONFIG_HOME": "/xdg",
               "CURSOR_CONFIG_DIR": "/cur", "PI_CODING_AGENT_DIR": "/pi"}
        self.assertEqual(_skills_roots(env), [
            os.path.join("/cc", "skills"),
            os.path.join("/h", ".agents", "skills"),
            os.path.join("/xdg", "opencode", "skills"),
            os.path.join("/cur", "skills"),
            os.path.join("/pi", "skills"),
        ])

    def test_skills_roots_with_only_home_list_the_fallback_dirs(self):
        self.assertEqual(_skills_roots({"HOME": "/h"}), [
            os.path.join("/h", ".claude", "skills"),
            os.path.join("/h", ".agents", "skills"),
            os.path.join("/h", ".config", "opencode", "skills"),
            os.path.join("/h", ".cursor", "skills"),
            os.path.join("/h", ".pi", "agent", "skills"),
        ])


if __name__ == "__main__":
    unittest.main()
