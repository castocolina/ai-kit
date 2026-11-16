"""Unit tests of the six-environment matrix tool (tools/env_matrix.py, SPEC R7).

No test runs make: the inner make is replaced by a fake that writes the reports the runner would
write, so the comparison, the baseline rule, the order and the environment builders are checked
without the minutes a real matrix run takes.
"""

import contextlib
import importlib.util
import io
import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest
import unittest.mock

REPO = pathlib.Path(__file__).resolve().parent.parent
MATRIX = REPO / "tools" / "env_matrix.py"


def load_matrix():
    spec = importlib.util.spec_from_file_location("env_matrix", MATRIX)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {MATRIX}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_reports(folder: pathlib.Path, modules, failing=(), skips=None) -> None:
    """The per-module reports the runner writes: one `<module>.json` each."""
    folder.mkdir(parents=True, exist_ok=True)
    for module in modules:
        data = {
            "module": module,
            "rc": 1 if module in failing else 0,
            "skips": list((skips or {}).get(module, ())),
            "ran": 1,
        }
        (folder / f"{module}.json").write_text(json.dumps(data), encoding="utf-8")


class TestCompareReports(unittest.TestCase):
    def setUp(self) -> None:
        self.m = load_matrix()
        self.r = self.m.Report

    def test_identical_results_give_no_line(self) -> None:
        base = {"tests.test_a": self.r(True, ("no host",), 2)}
        self.assertEqual(self.m.compare_reports(base, dict(base)), [])

    def test_a_pass_against_a_fail_is_one_line(self) -> None:
        base = {"tests.test_a": self.r(True, (), 1)}
        other = {"tests.test_a": self.r(False, (), 1)}
        lines = self.m.compare_reports(base, other)
        self.assertEqual(len(lines), 1)
        self.assertIn("tests.test_a", lines[0])

    def test_a_changed_skip_reason_is_one_line(self) -> None:
        base = {"tests.test_a": self.r(True, ("needs <tmp>",), 1)}
        other = {"tests.test_a": self.r(True, ("needs /elsewhere",), 1)}
        lines = self.m.compare_reports(base, other)
        self.assertEqual(len(lines), 1)
        self.assertIn("skip reasons differ", lines[0])

    def test_a_missing_and_an_extra_module_are_one_line_each(self) -> None:
        base = {"tests.test_a": self.r(True, (), 1)}
        other = {"tests.test_b": self.r(True, (), 1)}
        lines = self.m.compare_reports(base, other)
        self.assertEqual(len(lines), 2)
        self.assertTrue(any("tests.test_a: missing" in line for line in lines))
        self.assertTrue(any("tests.test_b: extra" in line for line in lines))

    def test_the_ran_count_is_not_compared(self) -> None:
        base = {"tests.test_a": self.r(True, (), 1)}
        other = {"tests.test_a": self.r(True, (), 9)}
        self.assertEqual(self.m.compare_reports(base, other), [])


class TestBaselineProblems(unittest.TestCase):
    def setUp(self) -> None:
        self.m = load_matrix()
        self.r = self.m.Report
        self.expected = {"tests.test_a", "tests.test_b"}
        self.green = {m: self.r(True, (), 1) for m in self.expected}

    def test_a_green_complete_baseline_is_empty(self) -> None:
        self.assertEqual(self.m.baseline_problems(self.green, 0, self.expected, []), [])

    def test_make_rc_alone_is_one_line(self) -> None:
        lines = self.m.baseline_problems(self.green, 2, self.expected, [])
        self.assertEqual(lines, ["make exited 2"])

    def test_one_failing_module_is_one_line_naming_it(self) -> None:
        reports = dict(self.green, **{"tests.test_b": self.r(False, (), 1)})
        lines = self.m.baseline_problems(reports, 0, self.expected, [])
        self.assertEqual(lines, ["failing module: tests.test_b"])

    def test_an_empty_report_set_gives_one_line_per_expected_module(self) -> None:
        lines = self.m.baseline_problems({}, 0, self.expected, [])
        self.assertEqual(sorted(lines), ["no report for tests.test_a",
                                         "no report for tests.test_b"])

    def test_an_unexpected_report_and_a_duplicate_each_give_one_line(self) -> None:
        reports = dict(self.green, **{"tests.test_zzz": self.r(True, (), 1)})
        lines = self.m.baseline_problems(reports, 0, self.expected, [])
        self.assertEqual(lines, ["unexpected report for tests.test_zzz"])
        dup = ["duplicate report: tests.test_a (tests.test_a.json, tests.test_a.2.json)"]
        self.assertEqual(self.m.baseline_problems(self.green, 0, self.expected, dup), dup)


class TestLoadReports(unittest.TestCase):
    def setUp(self) -> None:
        self.m = load_matrix()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.folder = pathlib.Path(self._tmp.name)

    def test_the_first_report_is_kept_and_a_duplicate_is_one_line(self) -> None:
        for name, ran in (("tests.test_a.json", 3), ("tests.test_a.2.json", 5)):
            data = {"module": "tests.test_a", "rc": 0, "skips": ["s"], "ran": ran}
            (self.folder / name).write_text(json.dumps(data), encoding="utf-8")
        reports, duplicates = self.m.load_reports(self.folder)
        self.assertEqual(reports, {"tests.test_a": self.m.Report(True, ("s",), 3)})
        self.assertEqual(len(duplicates), 1)
        self.assertIn("tests.test_a", duplicates[0])

    def test_a_tenth_duplicate_still_ranks_after_the_second(self) -> None:
        for name, ran in (("tests.test_a.json", 1), ("tests.test_a.2.json", 2),
                          ("tests.test_a.10.json", 10)):
            data = {"module": "tests.test_a", "rc": 0, "skips": [], "ran": ran}
            (self.folder / name).write_text(json.dumps(data), encoding="utf-8")
        reports, _ = self.m.load_reports(self.folder)
        self.assertEqual(reports["tests.test_a"].ran, 1)


class TestEnvironmentBuilders(unittest.TestCase):
    def setUp(self) -> None:
        self.m = load_matrix()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.scratch = pathlib.Path(self._tmp.name)
        self.caller = {
            "PATH": "/usr/bin", "HOME": "/home/owner", "MAKEFLAGS": "-j8", "MFLAGS": "-j8",
            "MAKELEVEL": "1", "GIT_INDEX_FILE": "/owner/index", "GIT_EXEC_PATH": "/exec",
            "CLAUDECODE": "1", "CODEX_HOME": "/owner/codex", "JEV_API_KEY": "secret",
        }

    def _spec(self, name: str, caller=None):
        return self.m.build_spec(name, caller or self.caller, {}, self.scratch, REPO)

    def test_plain_removes_every_host_signal_and_make_and_git_state(self) -> None:
        env = self._spec("plain").env
        for name in self.m.runner.HOST_SIGNAL_VARS | {"MAKEFLAGS", "MFLAGS", "MAKELEVEL",
                                                     "GIT_INDEX_FILE", "CODEX_HOME",
                                                     "JEV_API_KEY"}:
            self.assertNotIn(name, env, name)
        self.assertEqual(env["GIT_EXEC_PATH"], "/exec")

    def test_host_session_sets_every_host_signal_to_one(self) -> None:
        env = self._spec("host-session").env
        for name in self.m.runner.HOST_SIGNAL_VARS:
            self.assertEqual(env[name], "1", name)

    def test_every_environment_has_a_scratch_home_and_its_own_reports(self) -> None:
        spec = self._spec("plain")
        self.assertEqual(spec.env["HOME"], str(self.scratch / "plain" / "home"))
        self.assertEqual(spec.env["AI_KIT_REFUSE_REAL_HOME"], "1")
        self.assertEqual(pathlib.Path(spec.env[self.m.runner.REPORT_DIR_ENV]), spec.reports)
        self.assertEqual(spec.reports, self.scratch / "plain" / "reports")

    def test_the_shim_folder_is_first_on_path(self) -> None:
        spec = self._spec("plain")
        self.assertTrue(spec.env["PATH"].startswith(str(spec.shims / "bin") + os.pathsep))
        self.assertTrue(spec.env["PATH"].endswith("/usr/bin"))

    def test_run_order_puts_plain_first_and_keeps_it(self) -> None:
        self.assertEqual(self.m.run_order(None), list(self.m.ENV_NAMES))
        self.assertEqual(self.m.run_order(["outside-git", "host-session"]),
                         ["plain", "host-session", "outside-git"])
        self.assertEqual(self.m.run_order(["plain"]), ["plain"])

    def test_names_are_the_six_environments(self) -> None:
        self.assertEqual(self.m.ENV_NAMES, ("plain", "host-session", "no-host-cli",
                                            "long-path", "custom-tmpdir", "outside-git"))


class TestMatrixRuns(unittest.TestCase):
    """main() with the inner make replaced by a fake that writes reports."""

    def setUp(self) -> None:
        self.m = load_matrix()
        self.expected = sorted(self.m.expected_modules(REPO))

    def _fake(self, seen: list, failing=()):
        def fake(argv, env, cwd):
            folder = pathlib.Path(env[self.m.runner.REPORT_DIR_ENV])
            seen.append((folder.parent.name, argv, dict(env), cwd))
            write_reports(folder, self.expected, failing=failing)
            return 0
        return fake

    def _main(self, argv, fake):
        out = io.StringIO()
        # The scratch root comes from TMPDIR, which the custom-tmpdir environment puts inside a
        # repository. The guard has its own test: test_a_scratch_root_inside_a_work_tree_is_refused.
        with unittest.mock.patch.object(self.m, "run_make", fake), \
                unittest.mock.patch.object(self.m, "inside_git_worktree", return_value=False), \
                contextlib.redirect_stdout(out):
            code = self.m.main(argv)
        return code, out.getvalue()

    def test_a_scratch_root_inside_a_work_tree_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = pathlib.Path(tmp) / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)
            scratch = repo / "scratch"
            scratch.mkdir()
            err = io.StringIO()
            with unittest.mock.patch.object(self.m.tempfile, "mkdtemp",
                                            return_value=str(scratch)), \
                    contextlib.redirect_stderr(err):
                code = self.m.main(["--only", "host-session"])
        self.assertEqual(code, 2)
        self.assertIn("inside a git work tree", err.getvalue())

    def test_identical_green_environments_exit_zero(self) -> None:
        code, out = self._main(["--only", "host-session"], self._fake([]))
        self.assertEqual(code, 0, out)
        self.assertIn("matrix: identical in 2 environments", out)
        self.assertIn("env host-session: identical", out)

    def test_two_identical_failing_environments_still_exit_one(self) -> None:
        code, out = self._main(["--only", "host-session"],
                               self._fake([], failing=("tests.test_arch",)))
        self.assertEqual(code, 1, out)
        self.assertIn("env plain: baseline not green:", out)
        self.assertIn("failing module: tests.test_arch", out)
        self.assertIn("matrix: differences found", out)

    def test_environments_run_one_after_another(self) -> None:
        events: list[tuple[str, str]] = []
        fake = self._fake([])

        def recording(argv, env, cwd):
            name = pathlib.Path(env[self.m.runner.REPORT_DIR_ENV]).parent.name
            events.append(("start", name))
            code = fake(argv, env, cwd)
            events.append(("end", name))
            return code

        self._main(["--only", "host-session"], recording)
        self.assertEqual(events, [("start", "plain"), ("end", "plain"),
                                  ("start", "host-session"), ("end", "host-session")])

    def test_the_inner_make_is_serial_and_inherits_no_make_state(self) -> None:
        seen: list = []
        caller = {"MAKEFLAGS": "-j8", "MFLAGS": "-j8", "MAKELEVEL": "1", "PATH": "/usr/bin"}
        with unittest.mock.patch.dict(os.environ, caller, clear=True):
            self._main(["--only", "host-session"], self._fake(seen))
        for _name, argv, env, _cwd in seen:
            self.assertIn("-j1", argv)
            for name in ("MAKEFLAGS", "MFLAGS", "MAKELEVEL"):
                self.assertNotIn(name, env)

    def test_the_toolchain_forwards_survive_the_scratch_home(self) -> None:
        seen: list = []
        with tempfile.TemporaryDirectory() as tmp:
            home = pathlib.Path(tmp) / "owner"
            (home / ".volta").mkdir(parents=True)
            (home / ".local" / "share" / "uv" / "python").mkdir(parents=True)
            patch = {"HOME": str(home), "VOLTA_HOME": "", "UV_PYTHON_INSTALL_DIR": ""}
            with unittest.mock.patch.dict(os.environ, patch):
                self._main(["--only", "host-session"], self._fake(seen))
        self.assertTrue(seen)
        for _name, _argv, env, _cwd in seen:
            self.assertEqual(env["VOLTA_HOME"], str(home / ".volta"))
            self.assertEqual(env["UV_PYTHON_INSTALL_DIR"],
                             str(home / ".local" / "share" / "uv" / "python"))

    def test_the_scratch_root_is_removed_after_the_run(self) -> None:
        seen: list = []
        self._main(["--only", "host-session"], self._fake(seen))
        scratch = pathlib.Path(seen[0][2][self.m.runner.REPORT_DIR_ENV]).parent.parent
        self.assertFalse(scratch.exists())

    def test_help_names_all_six_environments(self) -> None:
        out = io.StringIO()
        with contextlib.redirect_stdout(out), self.assertRaises(SystemExit) as exit_info:
            self.m.main(["--help"])
        self.assertEqual(exit_info.exception.code, 0)
        for name in self.m.ENV_NAMES:
            self.assertIn(name, out.getvalue())

    def test_an_unknown_environment_is_a_usage_error(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as info:
            self.m.main(["--only", "no-such-environment"])
        self.assertEqual(info.exception.code, 2)


def _clean_env() -> dict[str, str]:
    return {name: value for name, value in os.environ.items() if not name.startswith("GIT_")}


def git(repo: pathlib.Path, *args: str) -> None:
    """A git command in `repo` with a test identity; raises CalledProcessError on failure."""
    subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=ai-kit test",
         "-c", "user.email=test@ai-kit.invalid", *args],
        check=True, capture_output=True, env=_clean_env(),
    )


def write(path: pathlib.Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def make_source(root: pathlib.Path) -> pathlib.Path:
    """A source repo with every state the long-path clone must reproduce: staged-only changes,
    unstaged and worktree deletions, untracked and ignored files, symlinks (retargeted, dangling,
    untracked, replaced by files), a staged rename, a file replaced by a symlink, a tracked
    .planning/ and a symlink whose old target lies outside the repo."""
    src = root / "source"
    src.mkdir()
    git(src, "init", "-q")
    for name, text in (
        ("a.txt", "a"), ("keep.txt", "keep"), ("staged.txt", "v1"), ("unstaged.txt", "v1"),
        ("wt_del.txt", "x"), ("staged_del.txt", "x"), ("rename_a.txt", "r"),
        ("file_to_link.txt", "f"), ("tests/test_one.py", "import unittest\n"),
        (".planning/STATE.md", "state\n"), (".planning/config.json", "{}\n"),
        (".gitignore", "ignored.log\n"),
    ):
        write(src / name, text)
    os.symlink("a.txt", src / "retarget")
    os.symlink("a.txt", src / "link_to_file")
    os.symlink(str(root / "outside.txt"), src / "escape")
    write(root / "outside.txt", "keep")
    git(src, "add", "-A")
    git(src, "commit", "-q", "-m", "base")

    write(src / "staged.txt", "v2")
    git(src, "add", "staged.txt")
    write(src / "new_staged.txt", "n")
    git(src, "add", "new_staged.txt")
    git(src, "rm", "-q", "staged_del.txt")
    git(src, "mv", "rename_a.txt", "rename_b.txt")
    write(src / "unstaged.txt", "v2")
    os.remove(src / "wt_del.txt")
    write(src / "untracked.txt", "u")
    write(src / "ignored.log", "i")
    os.symlink("a.txt", src / "new_link")
    os.symlink("missing-target", src / "dangling")
    os.unlink(src / "retarget")
    os.symlink("keep.txt", src / "retarget")
    os.unlink(src / "file_to_link.txt")
    os.symlink("a.txt", src / "file_to_link.txt")
    os.unlink(src / "link_to_file")
    write(src / "link_to_file", "now a file")
    os.unlink(src / "escape")
    write(src / "escape", "new content")
    write(src / ".planning" / "config.json", '{"x": 1}\n')
    write(src / ".planning" / "new.md", "new")
    return src


def tree_state(root: pathlib.Path) -> dict[str, tuple]:
    """Every tracked-or-untracked, non-ignored path that exists: its bytes, or its link target."""
    out = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z", "-c", "-o", "--exclude-standard"],
        capture_output=True, check=True, env=_clean_env(),
    ).stdout
    state: dict[str, tuple] = {}
    for raw in out.split(b"\0"):
        if not raw:
            continue
        name = os.fsdecode(raw)
        path = root / name
        if os.path.islink(path):
            state[name] = ("link", os.readlink(path))
        elif os.path.isfile(path):
            state[name] = ("file", path.read_bytes())
    return state


def make_executable(path: pathlib.Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    path.chmod(0o755)


class TestLongCheckoutPath(unittest.TestCase):
    def test_the_path_is_at_least_200_characters_under_the_scratch_root(self) -> None:
        m = load_matrix()
        path = m.long_checkout_path(pathlib.Path("/scratch/root"))
        self.assertGreaterEqual(len(str(path)), 200)
        self.assertTrue(str(path).startswith("/scratch/root/"))


class TestHostFreePath(unittest.TestCase):
    def test_host_names_are_left_out_and_the_first_copy_wins(self) -> None:
        m = load_matrix()
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            first, second = root / "first", root / "second"
            make_executable(first / "claude")
            make_executable(first / "git")
            make_executable(second / "git")
            make_executable(second / "make")
            write(first / "notes", "not executable")
            farm = root / "farm"
            path = os.pathsep.join([str(first), str(second)])
            result = m.host_free_path(farm, path, m.runner.HOST_CLI_NAMES)
            self.assertEqual(result, str(farm))
            self.assertFalse(os.path.lexists(farm / "claude"))
            self.assertFalse(os.path.lexists(farm / "notes"))
            self.assertEqual(os.readlink(farm / "git"), str(first / "git"))
            self.assertEqual(os.readlink(farm / "make"), str(second / "make"))
            for name in m.runner.HOST_CLI_NAMES:
                self.assertIsNone(shutil.which(name, path=result), name)


class TestLongCheckoutClone(unittest.TestCase):
    def setUp(self) -> None:
        self.m = load_matrix()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = pathlib.Path(self._tmp.name)
        self.src = make_source(self.root)

    def test_the_clone_holds_the_working_tree_bytes_without_planning(self) -> None:
        clone = self.m.make_long_checkout(self.src, self.root / "deep" / "clone")
        want = {k: v for k, v in tree_state(self.src).items() if not k.startswith(".planning/")}
        self.assertEqual(tree_state(clone), want)
        self.assertFalse(os.path.lexists(clone / ".planning"))
        self.assertNotIn("ignored.log", tree_state(clone))
        self.assertNotIn("rename_a.txt", tree_state(clone))

    def test_no_write_goes_through_a_symlink_into_the_outside(self) -> None:
        self.m.make_long_checkout(self.src, self.root / "clone")
        self.assertEqual((self.root / "outside.txt").read_text(encoding="utf-8"), "keep")

    def test_a_source_as_target_fails_before_anything_is_removed(self) -> None:
        before = tree_state(self.src)
        with self.assertRaises(subprocess.CalledProcessError):
            self.m.make_long_checkout(self.src, self.src)
        self.assertEqual(tree_state(self.src), before)

    def test_expected_modules_discovers_from_the_clone(self) -> None:
        clone = self.m.make_long_checkout(self.src, self.root / "clone")
        write(clone / "tests" / "test_only_in_clone.py", "")
        self.assertIn("tests.test_only_in_clone", self.m.expected_modules(clone))
        self.assertNotIn("tests.test_only_in_clone", self.m.expected_modules(self.src))


class TestTheOtherFourEnvironments(unittest.TestCase):
    def setUp(self) -> None:
        self.m = load_matrix()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = pathlib.Path(self._tmp.name)
        self.src = make_source(self.root)
        self.scratch = self.root / "scratch"
        self.caller = {"HOME": "/home/owner", "PATH": "/usr/bin", "MAKEFLAGS": "-j8"}

    def test_no_host_cli_has_no_host_on_path_and_no_shim_folder(self) -> None:
        bin_dir = self.root / "bin"
        make_executable(bin_dir / "claude")
        make_executable(bin_dir / "git")
        spec = self.m.build_spec("no-host-cli", dict(self.caller, PATH=str(bin_dir)), {},
                                 self.scratch, self.src)
        self.assertIsNone(spec.shims)
        self.assertEqual(spec.env["PATH"], str(self.scratch / "no-host-cli" / "farm"))
        for name in self.m.runner.HOST_CLI_NAMES:
            self.assertIsNone(shutil.which(name, path=spec.env["PATH"]), name)
        self.assertIsNotNone(shutil.which("git", path=spec.env["PATH"]))

    def test_long_path_uses_a_long_clone_and_the_source_venv_without_sync(self) -> None:
        spec = self.m.build_spec("long-path", self.caller, {}, self.scratch, self.src)
        self.assertGreaterEqual(len(str(spec.checkout)), 200)
        self.assertEqual(spec.cwd, spec.checkout)
        self.assertEqual(spec.env["UV_PROJECT_ENVIRONMENT"], str(self.src / ".venv"))
        self.assertEqual(spec.env["UV_NO_SYNC"], "1")
        self.assertTrue((spec.checkout / "tests" / "test_one.py").is_file())
        self.assertFalse(os.path.lexists(spec.checkout / ".planning"))

    def test_custom_tmpdir_has_a_space_and_sits_inside_a_repository(self) -> None:
        spec = self.m.build_spec("custom-tmpdir", self.caller, {}, self.scratch, self.src)
        tmp_dir = pathlib.Path(spec.env["TMPDIR"])
        self.assertIn(" ", str(tmp_dir))
        self.assertTrue(tmp_dir.is_dir())
        self.assertTrue(self.m.inside_git_worktree(tmp_dir))
        self.assertTrue((tmp_dir.parent / ".planning" / "config.json").is_file())

    def test_outside_git_starts_from_a_cwd_outside_every_repository(self) -> None:
        spec = self.m.build_spec("outside-git", self.caller, {}, self.scratch, self.src)
        self.assertTrue(spec.cwd.is_dir())
        # The cwd sits under the scratch root, so it lies in a work tree exactly when the scratch
        # root does; main refuses a scratch root inside one (its own test), so a matrix run
        # starts outside every repository. make still runs in the checkout.
        self.assertEqual(self.m.inside_git_worktree(spec.cwd),
                         self.m.inside_git_worktree(self.scratch))
        self.assertEqual(spec.checkout, self.src)

    def test_every_environment_is_built_and_run_in_order(self) -> None:
        seen: list[str] = []

        def fake(argv, env, cwd):
            checkout = pathlib.Path(argv[argv.index("-C") + 1])
            folder = pathlib.Path(env[self.m.runner.REPORT_DIR_ENV])
            seen.append(folder.parent.name)
            write_reports(folder, sorted(self.m.expected_modules(checkout)))
            return 0

        out = io.StringIO()
        with unittest.mock.patch.object(self.m, "REPO_ROOT", self.src), \
                unittest.mock.patch.object(self.m, "run_make", fake), \
                unittest.mock.patch.object(self.m, "inside_git_worktree", return_value=False), \
                contextlib.redirect_stdout(out):
            code = self.m.main([])
        self.assertEqual(code, 0, out.getvalue())
        self.assertEqual(seen, list(self.m.ENV_NAMES))
        self.assertIn("matrix: identical in 6 environments", out.getvalue())


if __name__ == "__main__":
    unittest.main()
