"""Real git commits through the real pre-commit hook in a temp repo.

The temp repo holds copies of the real runner and mapper and the real `staged-tests` hook block
cut by text from the real config, so the hook under test is the real one. The temp repo has no
uv project, so a fake `uv` first on PATH stands in for it: `uv run python X ...` runs X with this
interpreter, and the unit tests pin the real uv argv. Requires `git` and an importable
`pre_commit` (the uv env); skipped with a named reason otherwise.
"""
import importlib.util
import os
import pathlib
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from typing import NamedTuple

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
RUNNER = REPO_ROOT / "tools" / "run_unittest_parallel.py"
MAPPER = REPO_ROOT / "tools" / "staged_mapper.py"
HOOKS = REPO_ROOT / ".pre-commit-config.yaml"
HOOK_ID = "staged-tests"
PUSH_HOOK_ID = "deferred-e2e"
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
# The commit-budget pair: both name 'delta.py', so a change to tools/delta.py selects both. The
# within-budget one passes; the over-budget one fails when tools/delta.py holds BROKEN.
DELTA_NAMED_TEST = (
    "import unittest\n\n"
    "NAMED = 'delta.py'\n\n\n"
    "class T(unittest.TestCase):\n    def test_ok(self):\n        pass\n"
)
DELTA_GUARD_TEST = (
    "import pathlib\nimport unittest\n\n"
    "SRC = pathlib.Path(__file__).resolve().parent.parent / 'tools' / 'delta.py'\n\n\n"
    "class T(unittest.TestCase):\n    def test_not_broken(self):\n"
    "        self.assertNotIn('BROKEN', SRC.read_text())\n"
)
# Tracked files the tests touch; tearDown restores exactly these from HEAD.
TOUCHED = (
    "tools/alpha.py", "tools/beta.py", "tools/delta.py", "tests/test_alpha.py",
    "tests/data/gamma.txt", "tools/run_unittest_parallel.py", ".planning/STATE.md",
)


class Repo(NamedTuple):
    env: dict[str, str]
    within: str  # an e2e module recorded at or under the commit budget: runs under uv at commit
    over: str  # an e2e module over the budget, or unrecorded: deferred to push at commit


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


def write(root: pathlib.Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_git(root: pathlib.Path, env: dict[str, str], *args: str,
            check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        ["git", *args], cwd=root, env=env, capture_output=True, text=True,
        timeout=COMMIT_TIMEOUT_SECS, check=False,
    )
    if check and proc.returncode != 0:
        raise AssertionError(f"git {' '.join(args)}: {proc.stdout}{proc.stderr}")
    return proc


def write_fake_uv(bin_dir: pathlib.Path) -> None:
    bin_dir.mkdir(parents=True, exist_ok=True)
    script = bin_dir / "uv"
    script.write_text(
        "#!/bin/sh\n"
        "# Stand-in for uv in a temp repo with no uv project: `uv run python X ...` runs X here.\n"
        'if [ "$1" = run ] && [ "$2" = python ]; then shift 2; fi\n'
        f'exec {shlex.quote(sys.executable)} "$@"\n',
        encoding="utf-8",
    )
    script.chmod(0o755)


def over_budget(runner) -> list[str]:
    """The copied runner's e2e modules the commit stage defers: over the budget or unrecorded."""
    table, budget = runner.E2E_RECORDED_SECS, runner.COMMIT_E2E_BUDGET_SECS
    return sorted(m for m in runner.E2E_MODULES if not (m in table and table[m] <= budget))


def pick_e2e(runner) -> tuple[str, str]:
    """(within, over): the first sorted e2e module recorded at or under the commit budget, and the
    first deferred one."""
    table, budget = runner.E2E_RECORDED_SECS, runner.COMMIT_E2E_BUDGET_SECS
    within = next(m for m in sorted(runner.E2E_MODULES) if m in table and table[m] <= budget)
    return within, over_budget(runner)[0]


def defer_one(path: pathlib.Path) -> None:
    """Drop the largest recorded time from the copied runner at `path`: the copy then always
    defers one e2e module to push, whatever the real table holds."""
    table = load_by_path(path).E2E_RECORDED_SECS
    module = max(sorted(table), key=table.__getitem__)
    line = f'    "{module}": {table[module]},\n'
    text = path.read_text(encoding="utf-8")
    assert text.count(line) == 1, line
    path.write_text(text.replace(line, ""), encoding="utf-8")


def build_repo(root: pathlib.Path) -> Repo:
    """A git repo at `root` with the real runner, mapper and staged-tests hook block, one trivial
    module per explicit group, the delta.py pair and the initial commit; the hook is installed."""
    env = {
        **{k: v for k, v in os.environ.items() if not k.startswith("GIT_")},
        "PATH": os.pathsep.join([str(root.parent / "fakebin"), os.environ.get("PATH", "")]),
        "PRE_COMMIT_HOME": str(root.parent / "pre-commit-home"),
        "GIT_AUTHOR_NAME": "e2e", "GIT_COMMITTER_NAME": "e2e",
        "GIT_AUTHOR_EMAIL": "e2e@test.invalid", "GIT_COMMITTER_EMAIL": "e2e@test.invalid",
    }
    write_fake_uv(root.parent / "fakebin")
    root.mkdir()
    (root / "tools").mkdir()
    shutil.copy(RUNNER, root / "tools" / RUNNER.name)
    defer_one(root / "tools" / RUNNER.name)
    shutil.copy(MAPPER, root / "tools" / MAPPER.name)
    runner = load_by_path(root / "tools" / RUNNER.name)
    within, over = pick_e2e(runner)
    for names in runner.EXPLICIT_GROUPS.values():
        for name in names:
            write(root, f"tests/{name.removeprefix('tests.')}.py", TRIVIAL_TEST)
    write(root, f"tests/{within.removeprefix('tests.')}.py", DELTA_NAMED_TEST)
    write(root, f"tests/{over.removeprefix('tests.')}.py", DELTA_GUARD_TEST)
    write(root, "tools/alpha.py", "VALUE = 1\n")
    write(root, "tools/beta.py", "VALUE = 2\n")
    write(root, "tools/delta.py", "VALUE = 3\n")
    write(root, "tests/__init__.py", "")
    write(root, "tests/test_alpha.py", ALPHA_TEST)
    write(root, "tests/test_beta.py", BETA_TEST)
    write(root, "tests/data/gamma.txt", "gamma\n")
    write(root, ".planning/STATE.md", "state\n")
    for rel in sorted(runner.SHARED_MACHINERY):  # the copied runner's stale check needs every entry
        if not (root / rel).exists():
            write(root, rel, "")
    write(root, ".gitignore", "__pycache__/\n")
    config = HOOKS.read_text()
    write(
        root, ".pre-commit-config.yaml",
        "repos:\n  - repo: local\n    hooks:\n" + hook_block(config)
        + hook_block(config, PUSH_HOOK_ID),
    )
    run_git(root, env, "init", "-q")
    run_git(root, env, "config", "user.email", "e2e@test.invalid")
    run_git(root, env, "config", "user.name", "e2e")
    run_git(root, env, "add", "-A")
    run_git(root, env, "commit", "-q", "-m", "init")
    installed = subprocess.run(
        [sys.executable, "-m", "pre_commit", "install", "-t", "pre-commit", "-t", "pre-push"],
        cwd=root, env=env, capture_output=True, text=True, check=False,
    )
    assert installed.returncode == 0, installed.stdout + installed.stderr
    return Repo(env, within, over)


@unittest.skipUnless(shutil.which("git"), "git not available")
@unittest.skipUnless(importlib.util.find_spec("pre_commit"),
                     "pre_commit not importable (run under uv: make e2e-test)")
class TestStagedCommit(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = pathlib.Path(tempfile.mkdtemp(prefix="aikit-staged-e2e-"))
        cls.repo = cls.tmp / "repo"
        built = build_repo(cls.repo)
        cls.env, cls.within, cls.over = built.env, built.within, built.over
        cls.mapper = load_by_path(cls.repo / "tools" / "staged_mapper.py")
        runner = load_by_path(cls.repo / "tools" / RUNNER.name)
        cls.shared = runner.SHARED_MACHINERY
        cls.all_over_budget = over_budget(runner)

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.tmp, ignore_errors=True)

    @classmethod
    def git(cls, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        return run_git(cls.repo, cls.env, *args, check=check)

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

    def test_i_a_within_budget_module_runs_and_an_over_budget_one_is_deferred(self) -> None:
        self.stage_append("tools/delta.py", "# touched\n")
        code, out = self.commit("-m", "touch delta")
        self.assertEqual(code, 0, out)
        self.assertIn(f"staged: under uv: {self.within}", out)
        self.assertIn(f"=== {self.within}: ok", out)
        self.assertRegex(out, rf"staged: deferred to push \(over the 60 s commit budget\): "
                              rf"{re.escape(self.over)} \(")
        self.assertIn(f"run now: uv run python tools/run_unittest_parallel.py {self.over}", out)
        self.assertNotIn(f"=== {self.over}:", out)

    def pre_push(self, from_ref: str | None = None, to_ref: str | None = None) -> tuple[int, str]:
        argv = [sys.executable, "-m", "pre_commit", "run", PUSH_HOOK_ID, "--hook-stage", "pre-push"]
        if from_ref is not None:
            argv += ["--from-ref", from_ref]
        if to_ref is not None:
            argv += ["--to-ref", to_ref]
        proc = subprocess.run(argv, cwd=self.repo, env=self.env, capture_output=True, text=True,
                              timeout=COMMIT_TIMEOUT_SECS, check=False)
        return proc.returncode, proc.stdout + proc.stderr

    def test_j_the_pushed_range_runs_only_the_over_budget_module(self) -> None:
        self.stage_append("tools/delta.py", "# touched\n")
        self.assertEqual(self.commit("-m", "touch delta")[0], 0)
        code, out = self.pre_push("HEAD~1", "HEAD")
        self.assertEqual(code, 0, out)
        self.assertIn("pushed: 1 files in HEAD~1...HEAD -> 1 deferred e2e modules", out)
        self.assertEqual(ran_modules(out), {self.over})
        self.stage_append("tools/delta.py", "BROKEN = True\n")
        code, out = self.commit("-m", "break delta")
        self.assertEqual(code, 0, out)  # the over-budget module is deferred, so the commit passes
        code, out = self.pre_push("HEAD~1", "HEAD")
        self.assertNotEqual(code, 0, out)
        self.assertIn(f"failed: {self.over}", out)
        self.write_delta("VALUE = 3\n")
        self.assertEqual(self.commit("-m", "restore delta")[0], 0)

    def test_k_a_run_with_no_range_runs_every_over_budget_module(self) -> None:
        code, out = self.pre_push()
        self.assertEqual(code, 0, out)
        self.assertIn("pushed: no push range; running every e2e module over the commit budget", out)
        self.assertEqual(ran_modules(out), set(self.all_over_budget))

    def test_l_the_pushed_hook_does_not_exist_at_the_commit_stage(self) -> None:
        proc = subprocess.run(
            [sys.executable, "-m", "pre_commit", "run", PUSH_HOOK_ID, "--hook-stage", "pre-commit"],
            cwd=self.repo, env=self.env, capture_output=True, text=True, check=False,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertRegex(proc.stdout + proc.stderr,
                         rf"No hook with id `{PUSH_HOOK_ID}` in stage")

    def write_delta(self, text: str) -> None:
        (self.repo / "tools" / "delta.py").write_text(text, encoding="utf-8")
        self.git("add", "tools/delta.py")


@unittest.skipUnless(shutil.which("git"), "git not available")
@unittest.skipUnless(importlib.util.find_spec("pre_commit"),
                     "pre_commit not importable (run under uv: make e2e-test)")
class TestDeferredPush(unittest.TestCase):
    """Real pushes to a bare remote through the real pre-push hook, in a repo of its own."""

    def setUp(self) -> None:
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="aikit-deferred-push-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.repo = self.tmp / "repo"
        built = build_repo(self.repo)
        self.env, self.over = built.env, built.over
        self.remote = self.tmp / "remote.git"
        self.git("init", "-q", "--bare", str(self.remote))
        self.git("remote", "add", "origin", str(self.remote))
        self.branch = self.git("symbolic-ref", "--short", "HEAD").stdout.strip()

    def git(self, *args: str) -> subprocess.CompletedProcess[str]:
        return run_git(self.repo, self.env, *args)

    def commit_comment(self, rel: str, text: str, message: str) -> None:
        with (self.repo / rel).open("a", encoding="utf-8") as handle:
            handle.write(text)
        self.git("add", rel)
        self.git("commit", "-q", "-m", message)

    def test_m_and_n_a_two_ref_push_runs_every_over_budget_module_and_a_narrowed_one_ignores_tags(
        self,
    ) -> None:
        # (m) the root push has no range; a two-ref push takes the fallback; both refs arrive.
        root = self.git("push", "origin", self.branch)
        self.assertIn("pushed: no push range", root.stdout + root.stderr)
        self.git("checkout", "-q", "-b", "side")
        self.commit_comment("tools/delta.py", "# side\n", "side change")
        self.git("checkout", "-q", self.branch)
        self.commit_comment("tools/beta.py", "# main\n", "main change")
        pushed = self.git("push", "origin", self.branch, "side")
        out = pushed.stdout + pushed.stderr
        self.assertIn("; running every e2e module over the commit budget", out)
        self.assertIn(f"=== {self.over}: ok", out)
        remote_refs = self.git("ls-remote", "--heads", "origin").stdout
        self.assertIn(f"refs/heads/{self.branch}", remote_refs)
        self.assertIn("refs/heads/side", remote_refs)
        # (n) an unpushed local tag on a commit no branch holds does not force the fallback.
        self.commit_comment("tools/beta.py", "# main again\n", "main again")
        probe = self.git("commit-tree", "HEAD^{tree}", "-p", "HEAD", "-m", "probe").stdout.strip()
        self.git("tag", "backup/probe", probe)
        held_by_tag = self.git("rev-list", "--tags", "--not", "--remotes", "HEAD").stdout.split()
        self.assertEqual(held_by_tag, [probe])
        narrowed = self.git("push", "origin", self.branch)
        out = narrowed.stdout + narrowed.stderr
        self.assertRegex(out, r"pushed: \d+ files in \S+\.\.\.\S+ -> \d+ deferred e2e modules")
        self.assertIn("pushed: no deferred e2e modules", out)
        self.assertNotIn(f"=== {self.over}:", out)
        self.assertEqual(self.git("ls-remote", "--tags", "origin").stdout, "")


if __name__ == "__main__":
    unittest.main()
