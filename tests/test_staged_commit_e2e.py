"""Real git commits through the real pre-commit hook in a temp repo.

The temp repo holds copies of the real runner and mapper and the real `staged-tests` hook block
cut by text from the real config, so the hook under test is the real one. Requires `git` and an
importable `pre_commit` (the uv env); skipped with a named reason otherwise.
"""
import importlib.util
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
RUNNER = REPO_ROOT / "tools" / "run_unittest_parallel.py"
MAPPER = REPO_ROOT / "tools" / "staged_mapper.py"
HOOKS = REPO_ROOT / ".pre-commit-config.yaml"
HOOK_ID = "staged-tests"
COMMIT_TIMEOUT_SECS = 300
TRIVIAL_TEST = (
    "import unittest\n\n\nclass T(unittest.TestCase):\n    def test_ok(self):\n        pass\n"
)
ALPHA_TEST = (
    "import pathlib\nimport unittest\n\n"
    "SRC = pathlib.Path(__file__).resolve().parent.parent / 'tools' / 'alpha.py'\n\n\n"
    "class T(unittest.TestCase):\n    def test_not_broken(self):\n"
    "        self.assertNotIn('BROKEN', SRC.read_text())\n"
)
BETA_TEST = (
    "import pathlib\nimport unittest\n\n"
    "ROOT = pathlib.Path(__file__).resolve().parent\n"
    "BETA = ROOT.parent / 'tools' / 'beta.py'\nGAMMA = ROOT / 'data' / 'gamma.txt'\n\n\n"
    "class T(unittest.TestCase):\n    def test_reads(self):\n"
    "        self.assertTrue(BETA.exists())\n        self.assertTrue(GAMMA.read_text())\n"
)
# Tracked files the tests touch; tearDown restores exactly these from HEAD.
TOUCHED = (
    "tools/alpha.py", "tools/beta.py", "tests/test_alpha.py", "tests/data/gamma.txt",
    "tools/run_unittest_parallel.py", ".planning/STATE.md",
)


def load_by_path(path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def hook_block(text: str, hook_id: str = HOOK_ID) -> str:
    """The lines of one hook, from its `- id:` line to the next hook, trailing comments dropped."""
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if re.match(rf"\s*- id: {hook_id}$", line))
    end = next((i for i in range(start + 1, len(lines)) if re.match(r"\s*- id: ", lines[i])),
               len(lines))
    block = lines[start:end]
    while block and (not block[-1].strip() or block[-1].lstrip().startswith("#")):
        block.pop()
    return "\n".join(block) + "\n"


def listed_modules(output: str) -> set[str]:
    """The `staged: tests.x` selection lines of a hook run."""
    return set(re.findall(r"^\s*staged: (tests\.\w+)\s*$", output, re.MULTILINE))


def ran_modules(output: str) -> set[str]:
    """The modules the runner actually ran (its `=== tests.x: ...` lines)."""
    return set(re.findall(r"^=== (tests\.\w+): ", output, re.MULTILINE))


@unittest.skipUnless(shutil.which("git"), "git not available")
@unittest.skipUnless(importlib.util.find_spec("pre_commit"),
                     "pre_commit not importable (run under uv: make e2e-test)")
class TestStagedCommit(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = pathlib.Path(tempfile.mkdtemp(prefix="aikit-staged-e2e-"))
        cls.repo = cls.tmp / "repo"
        cls.env = {
            **{k: v for k, v in os.environ.items() if not k.startswith("GIT_")},
            "PRE_COMMIT_HOME": str(cls.tmp / "pre-commit-home"),
            "GIT_AUTHOR_NAME": "e2e", "GIT_COMMITTER_NAME": "e2e",
            "GIT_AUTHOR_EMAIL": "e2e@test.invalid", "GIT_COMMITTER_EMAIL": "e2e@test.invalid",
        }
        cls._build_repo()
        cls.mapper = load_by_path(cls.repo / "tools" / "staged_mapper.py")

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.tmp, ignore_errors=True)

    @classmethod
    def write(cls, rel: str, text: str) -> None:
        path = cls.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    @classmethod
    def _build_repo(cls) -> None:
        cls.repo.mkdir()
        (cls.repo / "tools").mkdir()
        shutil.copy(RUNNER, cls.repo / "tools" / RUNNER.name)
        shutil.copy(MAPPER, cls.repo / "tools" / MAPPER.name)
        runner = load_by_path(RUNNER)
        cls.shared = runner.SHARED_MACHINERY
        for names in runner.EXPLICIT_GROUPS.values():
            for name in names:
                cls.write(f"tests/{name.removeprefix('tests.')}.py", TRIVIAL_TEST)
        cls.write("tools/alpha.py", "VALUE = 1\n")
        cls.write("tools/beta.py", "VALUE = 2\n")
        cls.write("tests/__init__.py", "")
        cls.write("tests/test_alpha.py", ALPHA_TEST)
        cls.write("tests/test_beta.py", BETA_TEST)
        cls.write("tests/data/gamma.txt", "gamma\n")
        cls.write(".planning/STATE.md", "state\n")
        for rel in sorted(cls.shared):  # the copied runner's stale check needs every entry
            if not (cls.repo / rel).exists():
                cls.write(rel, "")
        cls.write(".gitignore", "__pycache__/\n")
        cls.write(
            ".pre-commit-config.yaml",
            "repos:\n  - repo: local\n    hooks:\n" + hook_block(HOOKS.read_text()),
        )
        cls.git("init", "-q")
        cls.git("config", "user.email", "e2e@test.invalid")
        cls.git("config", "user.name", "e2e")
        cls.git("add", "-A")
        cls.git("commit", "-q", "-m", "init")
        installed = subprocess.run(
            [sys.executable, "-m", "pre_commit", "install"], cwd=cls.repo, env=cls.env,
            capture_output=True, text=True, check=False,
        )
        assert installed.returncode == 0, installed.stdout + installed.stderr

    @classmethod
    def git(cls, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        proc = subprocess.run(
            ["git", *args], cwd=cls.repo, env=cls.env, capture_output=True, text=True,
            timeout=COMMIT_TIMEOUT_SECS, check=False,
        )
        if check and proc.returncode != 0:
            raise AssertionError(f"git {' '.join(args)}: {proc.stdout}{proc.stderr}")
        return proc

    def tearDown(self) -> None:
        self.git("checkout", "-q", "HEAD", "--", *TOUCHED)

    def head(self) -> str:
        return self.git("rev-parse", "HEAD").stdout.strip()

    def stage_append(self, rel: str, text: str) -> None:
        with (self.repo / rel).open("a", encoding="utf-8") as handle:
            handle.write(text)
        self.git("add", rel)

    def commit(self, *args: str) -> tuple[int, str]:
        proc = self.git("commit", "-q", *args, check=False)
        return proc.returncode, proc.stdout + proc.stderr

    def expected(self, *paths: str) -> set[str]:
        """The copied mapper's own answer: covering modules plus the arch group when due."""
        decision = self.mapper.decide(self.repo, list(paths), self.shared)
        return {*decision.modules, *(["tests.test_arch"] if decision.arch else [])}

    def test_a_commit_runs_only_the_modules_covering_the_staged_file(self) -> None:
        self.stage_append("tools/alpha.py", "# touched\n")
        code, out = self.commit("-m", "touch alpha")
        self.assertEqual(code, 0, out)
        self.assertIn("staged tests (covering modules)", out)
        listed = listed_modules(out)
        self.assertIn("tests.test_alpha", listed)
        self.assertNotIn("tests.test_beta", listed)
        self.assertEqual(listed, self.expected("tools/alpha.py"))

    def test_b_a_failing_covering_module_refuses_the_commit(self) -> None:
        before = self.head()
        self.stage_append("tools/alpha.py", "BROKEN = True\n")
        code, out = self.commit("-m", "break alpha")
        self.assertNotEqual(code, 0, out)
        self.assertEqual(self.head(), before)
        self.assertIn("failed: tests.test_alpha", out)

    def test_c_a_data_file_runs_the_module_that_reads_it(self) -> None:
        self.stage_append("tests/data/gamma.txt", "more\n")
        code, out = self.commit("-m", "touch gamma")
        self.assertEqual(code, 0, out)
        self.assertEqual(listed_modules(out), {"tests.test_beta"})

    def test_d_a_planning_only_commit_runs_zero_modules(self) -> None:
        self.stage_append(".planning/STATE.md", "more\n")
        code, out = self.commit("-m", "planning")
        self.assertEqual(code, 0, out)
        self.assertIn("staged: 1 files -> 0 modules", out)
        self.assertEqual(ran_modules(out), set())

    def test_e_shared_machinery_runs_the_full_unit_and_arch_groups(self) -> None:
        self.stage_append("tools/run_unittest_parallel.py", "# touched\n")
        code, out = self.commit("-m", "touch the runner")
        self.assertEqual(code, 0, out)
        self.assertIn("full unit+arch run: shared test machinery", out)
        every = {"tests.test_alpha", "tests.test_beta", "tests.test_arch"}
        self.assertEqual(ran_modules(out), every)

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0,
                     "root reads a mode 000 file, so the mapper input stays readable")
    def test_f_an_unreadable_test_source_runs_the_full_groups_and_refuses(self) -> None:
        bad = self.repo / "tests" / "test_unreadable.py"
        bad.write_text(TRIVIAL_TEST, encoding="utf-8")
        bad.chmod(0)  # untracked, so pre-commit's stash of unstaged changes cannot hide it
        self.addCleanup(lambda: (bad.chmod(0o600), bad.unlink()))
        before = self.head()
        self.stage_append("tools/alpha.py", "# touched\n")
        code, out = self.commit("-m", "unreadable")
        self.assertNotEqual(code, 0, out)
        self.assertEqual(self.head(), before)
        self.assertIn("full unit+arch run: mapper error", out)
        self.assertLessEqual({"tests.test_alpha", "tests.test_beta"}, ran_modules(out))

    def test_g_a_commit_with_nothing_staged_runs_zero_modules(self) -> None:
        code, out = self.commit("--allow-empty", "-m", "message only")
        self.assertEqual(code, 0, out)
        self.assertIn("staged: no staged files; 0 modules", out)

    def test_h_the_hook_does_not_exist_at_the_push_stage(self) -> None:
        proc = subprocess.run(
            [sys.executable, "-m", "pre_commit", "run", HOOK_ID, "--hook-stage", "pre-push"],
            cwd=self.repo, env=self.env, capture_output=True, text=True, check=False,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertRegex(proc.stdout + proc.stderr, rf"No hook with id `{HOOK_ID}` in stage")


if __name__ == "__main__":
    unittest.main()
