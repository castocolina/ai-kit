"""SPEC R12 / D-04 / ruling 3 tests: `make setup-dev` installs missing tools through guarded steps.

Every installer is a fake (an injected runner, or fake executables on a scratch PATH).
No test runs a real package manager, sudo, or a real `make setup-dev`.
"""

import errno
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load():
    path = os.path.join(_ROOT, "tools", "setup_dev.py")
    spec = importlib.util.spec_from_file_location("setup_dev_under_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


setup_dev = _load()


def _executable(path):
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("#!/bin/sh\nexit 0\n")
    os.chmod(path, 0o755)


def _scratch_bin(root, with_tools=("uv", "brew", "pnpm")):
    bin_dir = os.path.join(root, "bin dir")
    os.mkdir(bin_dir)
    for name in with_tools:
        _executable(os.path.join(bin_dir, name))
    for name in ("git", "make"):
        found = shutil.which(name)
        if found:
            os.symlink(found, os.path.join(bin_dir, name))
    return bin_dir


class _FakeInstallers:
    """A runner that records argv and fakes each installer; `fail` maps argv prefix -> rc."""

    def __init__(self, bin_dir, fail=None, raise_for=None):
        self.bin_dir = bin_dir
        self.fail = fail or {}
        self.raise_for = raise_for or {}
        self.calls = []
        self.extensions = set()

    def __call__(self, argv, **_kwargs):
        argv = list(argv)
        self.calls.append(argv)
        for prefix, error in self.raise_for.items():
            if tuple(argv[:len(prefix)]) == prefix:
                raise error
        for prefix, rc in self.fail.items():
            if tuple(argv[:len(prefix)]) == prefix:
                return subprocess.CompletedProcess(argv, rc, "", "boom")
        if argv[:3] == ["gh", "extension", "install"]:
            self.extensions.add("gh-stack")
        if argv[:3] == ["gh", "extension", "list"]:
            text = "gh stack github/gh-stack v0.3.0\n" if self.extensions else ""
            return subprocess.CompletedProcess(argv, 0, text, "")
        if argv[:3] == ["uv", "tool", "install"]:
            _executable(os.path.join(self.bin_dir, argv[-1].replace("graphifyy", "graphify")))
        if argv[:2] == ["brew", "install"]:
            _executable(os.path.join(self.bin_dir, argv[-1]))
        return subprocess.CompletedProcess(argv, 0, "", "")

    def installs(self):
        return [" ".join(argv) for argv in self.calls
                if argv[:3] != ["gh", "extension", "list"]]


class TestSetupDevGuardedSteps(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="ai-kit-p30-")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        subprocess.run(["git", "init", "-q", self.root], check=True)
        self.bin_dir = _scratch_bin(self.root)
        self.env = {"PATH": self.bin_dir, "AI_KIT_REFUSE_REAL_HOME": "1"}

    def _run(self, runner):
        lines = []
        rc = setup_dev.run(self.env, runner=runner, out=lines.append, root=self.root)
        return rc, lines

    def test_fresh_run_installs_four_reports_one_and_exits_zero(self):
        fake = _FakeInstallers(self.bin_dir, fail={("pnpm",): 1})
        rc, lines = self._run(fake)
        self.assertEqual(rc, 0)
        self.assertTrue(any(line.startswith("codegraph: install failed (exit 1); manual:")
                            for line in lines), lines)
        self.assertTrue(any(line.startswith("gh: installed") and "[unverified command]" in line
                            for line in lines), lines)
        self.assertIn("hooks: installed (uv run pre-commit install)", lines)
        self.assertEqual(lines[-1], "setup-dev: 4 installed, 0 present, 1 need a manual step")
        installs = fake.installs()
        self.assertEqual(installs[0], "uv sync")
        self.assertEqual(installs[-1], "uv run pre-commit install")
        order = [item for item in installs if item.startswith(
            ("uv tool install", "brew install", "gh extension install", "pnpm add"))]
        self.assertEqual(order, ["uv tool install pre-commit", "brew install gh",
                                 "gh extension install github/gh-stack",
                                 "pnpm add -g @colbymchenry/codegraph",
                                 "uv tool install graphifyy"])
        lock = os.path.join(self.root, ".git", "ai-kit-setup-dev.lock")
        self.assertTrue(os.path.exists(lock))

    def test_second_run_retries_only_the_failed_tool(self):
        first = _FakeInstallers(self.bin_dir, fail={("pnpm",): 1})
        self._run(first)
        second = _FakeInstallers(self.bin_dir, fail={("pnpm",): 1})
        rc, lines = self._run(second)
        self.assertEqual(rc, 0)
        self.assertEqual(second.installs()[-2:], ["pnpm add -g @colbymchenry/codegraph",
                                                  "uv run pre-commit install"])
        self.assertFalse(any(item.startswith(("uv tool install", "brew install"))
                             for item in second.installs()))
        self.assertIn("pre-commit: present (left alone)", lines)
        self.assertTrue(any(line.startswith("codegraph: install failed") for line in lines))

    def test_timeout_and_permission_are_reported_and_exit_zero(self):
        fake = _FakeInstallers(
            self.bin_dir,
            raise_for={("pnpm",): subprocess.TimeoutExpired(["pnpm"], 600),
                       ("brew",): OSError(errno.EACCES, "Permission denied")})
        rc, lines = self._run(fake)
        self.assertEqual(rc, 0)
        self.assertTrue(any(line.startswith(
            "codegraph: install timed out after 600 s; manual:") for line in lines), lines)
        self.assertTrue(any(line.startswith(
            "gh: install failed (Permission denied); manual:") for line in lines), lines)
        self.assertTrue(any(line.startswith("gh-stack: skipped: gh is not available")
                            for line in lines), lines)

    def test_failed_sync_and_hook_install_still_run_later_steps(self):
        fake = _FakeInstallers(self.bin_dir, fail={("uv", "sync"): 1,
                                                   ("uv", "run"): 1})
        rc, lines = self._run(fake)
        self.assertEqual(rc, 0)
        self.assertIn("env: uv sync failed (exit 1); manual: make setup-env", lines)
        self.assertIn("hooks: install failed (exit 1); manual: make dev", lines)
        self.assertTrue(any(item.startswith("uv tool install") for item in fake.installs()))

    def test_no_uv_reports_manual_steps_without_running_anything(self):
        for name in ("uv", "brew", "pnpm"):
            os.remove(os.path.join(self.bin_dir, name))
        fake = _FakeInstallers(self.bin_dir)
        rc, lines = self._run(fake)
        self.assertEqual(rc, 0)
        self.assertIn("env: not run: no uv; manual: install uv, then make setup-env", lines)
        self.assertIn("hooks: not run: no uv; manual: make dev", lines)
        self.assertTrue(any(line.startswith("gh: not installed: no brew") for line in lines))
        self.assertEqual(fake.installs(), [])

    def test_installer_argv_never_uses_sudo_or_a_shell(self):
        for tool in setup_dev.TOOLS:
            with self.subTest(tool=tool.name):
                self.assertNotIn("sudo", tool.install)
                self.assertNotIn("curl", tool.install)
                self.assertNotIn("wget", tool.install)
                self.assertNotIn("sh", tool.install)
                self.assertNotIn("bash", tool.install)
                self.assertNotIn("-c", tool.install)

    def test_make_setup_dev_in_a_temp_repo_exits_zero_with_fake_uv(self):
        repo = tempfile.mkdtemp(prefix="ai-kit-p30-make-")
        self.addCleanup(shutil.rmtree, repo, ignore_errors=True)
        os.mkdir(os.path.join(repo, "tools"))
        shutil.copy(os.path.join(_ROOT, "Makefile"), os.path.join(repo, "Makefile"))
        shutil.copy(os.path.join(_ROOT, "tools", "setup_dev.py"),
                    os.path.join(repo, "tools", "setup_dev.py"))
        subprocess.run(["git", "init", "-q", repo], check=True)
        log = os.path.join(repo, "uv.log")
        bin_dir = _scratch_bin(repo, with_tools=())
        fake_uv = os.path.join(bin_dir, "uv")
        with open(fake_uv, "w", encoding="utf-8") as handle:
            handle.write("#!/bin/sh\necho \"$*\" >> \"$AI_KIT_FAKE_UV_LOG\"\nexit 0\n")
        os.chmod(fake_uv, 0o755)
        python = os.path.join(bin_dir, "python3")
        os.symlink(sys.executable, python)
        home = os.path.join(repo, "scratch home")
        os.mkdir(home)
        env = {"PATH": bin_dir, "HOME": home, "AI_KIT_REFUSE_REAL_HOME": "1",
               "AI_KIT_FAKE_UV_LOG": log, "GIT_CONFIG_GLOBAL": os.devnull,
               "GIT_CONFIG_SYSTEM": os.devnull}
        completed = subprocess.run(["make", "setup-dev"], cwd=repo, env=env,
                                   capture_output=True, text=True, check=False, timeout=120)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        with open(log, encoding="utf-8") as handle:
            calls = handle.read().splitlines()
        self.assertEqual(calls[0], "sync")
        self.assertEqual(calls[-1], "run pre-commit install")

    def test_unopenable_lock_is_noted_and_every_later_step_still_runs(self):
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            self.skipTest("root bypasses the read-only git common dir this test relies on")
        git_dir = os.path.join(self.root, ".git")
        os.chmod(git_dir, 0o555)
        self.addCleanup(os.chmod, git_dir, 0o755)
        fake = _FakeInstallers(self.bin_dir)
        rc, lines = self._run(fake)
        self.assertEqual(rc, 0)
        notes = [line for line in lines if line.startswith("note: setup-dev lock unavailable (")]
        self.assertEqual(len(notes), 1, lines)
        self.assertTrue(notes[0].endswith("); running without it"), notes[0])
        self.assertIn("env: synced (uv sync)", lines)
        self.assertIn("hooks: installed (uv run pre-commit install)", lines)
        self.assertTrue(any(item.startswith("uv tool install") for item in fake.installs()))
        self.assertTrue(lines[-1].startswith("setup-dev: "), lines)


FAKE_TOOL = """#!{python}
import os
import shutil
import sys

name = os.path.basename(sys.argv[0])
argv = sys.argv[1:]
state = os.environ["AI_KIT_FAKE_STATE"]
bin_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
with open(os.environ["AI_KIT_FAKE_LOG"], "a", encoding="utf-8") as handle:
    handle.write(" ".join([name, *argv]) + "\\n")


def make(tool_name):
    target = os.path.join(bin_dir, tool_name)
    shutil.copy(os.path.abspath(sys.argv[0]), target)
    os.chmod(target, 0o755)


if name == "uv" and argv[:2] == ["tool", "install"]:
    make({{"graphifyy": "graphify"}}.get(argv[2], argv[2]))
elif name == "brew" and argv[:2] == ["install", "gh"]:
    make("gh")
elif name == "pnpm" and argv[:3] == ["add", "-g", "@colbymchenry/codegraph"]:
    make("codegraph")
elif name == "gh" and argv[:2] == ["extension", "install"]:
    open(os.path.join(state, "gh-stack"), "w", encoding="utf-8").close()
elif name == "gh" and argv[:2] == ["extension", "list"]:
    if os.path.exists(os.path.join(state, "gh-stack")):
        print("gh stack github/gh-stack v0.3.0")
sys.exit(0)
"""

INSTALLS = (
    "uv tool install pre-commit",
    "brew install gh",
    "gh extension install github/gh-stack",
    "pnpm add -g @colbymchenry/codegraph",
    "uv tool install graphifyy",
)


class TestSetupDevRealProcesses(unittest.TestCase):
    """Real `python3 tools/setup_dev.py` processes with fake executables on a scratch PATH."""

    def setUp(self):
        self.repo = tempfile.mkdtemp(prefix="ai-kit-p30-")
        self.addCleanup(shutil.rmtree, self.repo, ignore_errors=True)
        subprocess.run(["git", "init", "-q", self.repo], check=True)
        os.mkdir(os.path.join(self.repo, "tools"))
        shutil.copy(os.path.join(_ROOT, "tools", "setup_dev.py"),
                    os.path.join(self.repo, "tools", "setup_dev.py"))
        self.bin_dir = _scratch_bin(self.repo, with_tools=())
        for name in ("uv", "brew", "pnpm"):
            path = os.path.join(self.bin_dir, name)
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(FAKE_TOOL.format(python=sys.executable))
            os.chmod(path, 0o755)
        self.state = os.path.join(self.repo, "fake state")
        os.mkdir(self.state)
        self.log = os.path.join(self.repo, "fake.log")
        home = os.path.join(self.repo, "scratch home")
        os.mkdir(home)
        self.env = {"PATH": self.bin_dir, "HOME": home, "AI_KIT_REFUSE_REAL_HOME": "1",
                    "AI_KIT_FAKE_LOG": self.log, "AI_KIT_FAKE_STATE": self.state,
                    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull}

    def _start(self):
        return subprocess.Popen(
            [sys.executable, os.path.join(self.repo, "tools", "setup_dev.py")],
            cwd=self.repo, env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True)

    def test_two_runs_at_once_install_each_tool_once_under_one_lock(self):
        first, second = self._start(), self._start()
        outputs = [process.communicate(timeout=120) for process in (first, second)]
        for process, (stdout, stderr) in zip((first, second), outputs, strict=True):
            self.assertEqual(process.returncode, 0, stdout + stderr)
        with open(self.log, encoding="utf-8") as handle:
            calls = [line.strip() for line in handle if line.strip()]
        for install in INSTALLS:
            with self.subTest(install=install):
                self.assertEqual(calls.count(install), 1, calls)
        lock = os.path.join(self.repo, ".git", "ai-kit-setup-dev.lock")
        self.assertTrue(os.path.exists(lock))
        summaries = [line for stdout, _stderr in outputs for line in stdout.splitlines()
                     if line.startswith("setup-dev: ")]
        self.assertEqual(len(summaries), 2, outputs)
        self.assertTrue(any("[unverified command]" in stdout for stdout, _ in outputs))

    def test_fake_executables_install_gh_and_gh_stack_in_one_real_run(self):
        completed = subprocess.run(
            [sys.executable, os.path.join(self.repo, "tools", "setup_dev.py")],
            cwd=self.repo, env=self.env, capture_output=True, text=True, check=False,
            timeout=120)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("gh-stack: installed (gh extension install github/gh-stack)",
                      completed.stdout)
        self.assertIn("gh: installed (brew install gh) [unverified command]", completed.stdout)
        self.assertEqual(completed.stdout.splitlines()[-1],
                         "setup-dev: 5 installed, 0 present, 0 need a manual step")


if __name__ == "__main__":
    unittest.main()
