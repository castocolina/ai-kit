"""The staged-file mapper and the runner's --staged mode: every failure runs more tests."""
import contextlib
import importlib.util
import io
import itertools
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest
import unittest.mock

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
RUNNER = REPO_ROOT / "tools" / "run_unittest_parallel.py"
MAPPER = REPO_ROOT / "tools" / "staged_mapper.py"


def load_tool(path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def make_tree(root: pathlib.Path, files: dict[str, str]) -> pathlib.Path:
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


def snapshot(root: pathlib.Path) -> dict[str, tuple[int, int]]:
    return {
        path.relative_to(root).as_posix(): (path.stat().st_size, path.stat().st_mtime_ns)
        for path in sorted(root.rglob("*")) if path.is_file()
    }


TREE = {
    "tests/test_alpha.py": "# covers tools/alpha.py\nimport util\n",
    "tests/test_beta.py": "# covers tools/beta.py\nGAMMA = 'data/gamma.txt'\n",
    "tests/test_zeta.py": "import util\nSKILL = 'skills/my-skill'\n",
    "tests/util.py": "SHARED = 'shared.dat'\n",
    "tests/one.py": "NAME = 'solo.cfg'\n",
    "tests/test_uses_one.py": "from tests import one\n",
    "tests/orphan.py": "NAME = 'lost.cfg'\n",
    "tools/alpha.py": "",
    "tools/beta.py": "",
    "skills/my-skill/run.py": "",
    ".planning/STATE.md": "",
}


class MapperCase(unittest.TestCase):
    mapper = load_tool(MAPPER)

    def setUp(self) -> None:
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="aikit-mapper-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.root = make_tree(self.tmp / "repo", TREE)

    def decide(self, paths, shared=frozenset()):
        return self.mapper.decide(self.root, paths, shared)


class CoveringTest(MapperCase):
    def test_a_tool_is_covered_by_the_module_naming_its_file(self) -> None:
        decision = self.decide(["tools/beta.py"])
        self.assertEqual(decision.modules, ("tests.test_beta",))
        self.assertTrue(decision.arch)

    def test_a_data_file_read_by_one_module_runs_that_module(self) -> None:
        self.assertEqual(self.decide(["tests/data/gamma.txt"]).modules, ("tests.test_beta",))

    def test_a_helper_reaches_the_modules_that_name_it(self) -> None:
        index = self.mapper.build_index(self.root)
        self.assertEqual(self.mapper.covering_modules(index, "tests/one.py"),
                         frozenset({"tests.test_uses_one"}))

    def test_a_helper_source_extends_the_reach_of_its_modules(self) -> None:
        index = self.mapper.build_index(self.root)
        self.assertIn("shared.dat", index.reach["tests.test_alpha"])
        self.assertEqual(self.mapper.covering_modules(index, "shared.dat"),
                         frozenset({"tests.test_alpha", "tests.test_zeta"}))

    def test_a_skill_folder_name_is_a_whole_token(self) -> None:
        make_tree(self.root, {"tests/test_other.py": "X = 'skills/my-skill-extra'\n"})
        index = self.mapper.build_index(self.root)
        self.assertEqual(self.mapper.covering_modules(index, "skills/my-skill/run.py"),
                         frozenset({"tests.test_zeta"}))

    def test_a_staged_test_module_covers_itself(self) -> None:
        index = self.mapper.build_index(self.root)
        self.assertIn("tests.test_beta", self.mapper.covering_modules(index, "tests/test_beta.py"))

    def test_a_deleted_test_module_is_not_selected(self) -> None:
        index = self.mapper.build_index(self.root)
        self.assertEqual(self.mapper.covering_modules(index, "tests/test_gone.py"), frozenset())

    def test_fixture_folder_names_select_a_module_naming_every_folder(self) -> None:
        make_tree(self.root, {
            "tests/test_by_name.py": "X = 'out.json'\n",
            "tests/test_by_folders.py": "X = 'golden'\nY = 'case1'\n",
            "tests/test_one_folder.py": "X = 'golden'\n",
        })
        index = self.mapper.build_index(self.root)
        got = self.mapper.covering_modules(index, "tests/fixtures/golden/case1/out.json")
        self.assertEqual(got, frozenset({"tests.test_by_name", "tests.test_by_folders"}))

    def test_a_planning_file_selects_nothing(self) -> None:
        decision = self.decide([".planning/STATE.md"])
        self.assertEqual((decision.modules, decision.arch, decision.full_reason),
                         ((), False, None))

    def test_a_deleted_tool_still_maps_by_name(self) -> None:
        (self.root / "tools" / "beta.py").unlink()
        self.assertEqual(self.decide(["tools/beta.py"]).modules, ("tests.test_beta",))

    def test_two_paths_with_one_covering_module_select_it_once(self) -> None:
        make_tree(self.root, {"tests/test_beta.py": "# beta.py\nX = 'beta-extra.cfg'\n"})
        decision = self.decide(["tools/beta.py", "tools/beta.py", "beta-extra.cfg"])
        self.assertEqual(decision.modules, ("tests.test_beta",))

    def test_the_index_is_not_cached_between_calls(self) -> None:
        self.assertEqual(self.decide(["tools/beta.py"]).modules, ("tests.test_beta",))
        (self.root / "tests" / "test_beta.py").write_text("X = 1\n")
        self.assertEqual(self.decide(["tools/beta.py"]).modules, ())

    def test_an_undecodable_test_source_is_a_mapper_error(self) -> None:
        (self.root / "tests" / "test_bad.py").write_bytes(b"\xff\xfe")
        with self.assertRaises(self.mapper.MapperError):
            self.decide(["tools/beta.py"])

    def test_a_missing_tests_folder_is_a_mapper_error(self) -> None:
        with self.assertRaises(self.mapper.MapperError):
            self.mapper.build_index(self.tmp)


class CodeFormsTest(MapperCase):
    FORMS = {
        "import_stmt": "import detect\n",
        "from_import": "from detect import compose_message\n",
        "tools_import": "from tools.hooks import detect as d\n",
        "paren_import": "from tools import (alpha,\n    detect)\n",
        "comma_import": "from tools.hooks import host, detect\n",
        "file_name": "NAME = 'detect.py'\n",
        "quoted_double": 'NAME = "detect"\n',
        "quoted_single": "NAME = 'detect'\n",
        "dotted": "PATH = 'tools.hooks.detect'\n",
    }

    def test_each_code_form_selects_and_prose_does_not(self) -> None:
        files = {f"tests/test_{name}.py": text for name, text in self.FORMS.items()}
        files["tests/test_prose.py"] = "# detect the host, then set up the setup file\n"
        files["tests/test_glued.py"] = "X = 'predetect'\nY = 'detect_all'\nZ = 'detect-x'\n"
        make_tree(self.root, files)
        index = self.mapper.build_index(self.root)
        got = self.mapper.covering_modules(index, "tools/hooks/detect.py")
        self.assertEqual(got, {f"tests.test_{name}" for name in self.FORMS})

    def test_a_generic_stem_in_prose_selects_nothing(self) -> None:
        make_tree(self.root, {"tests/test_prose.py": "# set up the setup, detect it\n"})
        index = self.mapper.build_index(self.root)
        for path in ("tools/setup.py", "tools/hooks/detect.py"):
            self.assertEqual(self.mapper.covering_modules(index, path), frozenset(), path)

    def test_real_checkout_regressions(self) -> None:
        index = self.mapper.build_index(REPO_ROOT)
        self.assertIn("tests.test_cursor_status_line",
                      self.mapper.covering_modules(index, "tools/common_render.py"))
        self.assertIn("tests.test_wizard_app",
                      self.mapper.covering_modules(index, "tools/wizard_app.py"))


class FailSafeTest(MapperCase):
    SHARED = frozenset({"Makefile", "tools/hooks/"})

    def test_a_shared_machinery_path_is_a_full_run(self) -> None:
        for path in ("Makefile", "tools/hooks/x.py"):
            reason = self.decide([path], self.SHARED).full_reason
            self.assertEqual(reason, f"shared test machinery: {path}")

    def test_a_helper_covering_two_modules_is_a_full_run(self) -> None:
        reason = self.decide(["tests/util.py"]).full_reason
        self.assertEqual(reason, "shared test helper or fixture: tests/util.py (2 modules)")

    def test_a_fixture_covering_two_modules_is_a_full_run(self) -> None:
        make_tree(self.root, {"tests/test_dup.py": "X = 'gamma.txt'\n"})
        reason = self.decide(["tests/data/gamma.txt"]).full_reason
        self.assertEqual(reason, "shared test helper or fixture: tests/data/gamma.txt (2 modules)")

    def test_a_helper_covering_one_module_selects_it(self) -> None:
        decision = self.decide(["tests/one.py"])
        self.assertEqual((decision.modules, decision.full_reason),
                         (("tests.test_uses_one",), None))

    def test_a_named_file_no_module_covers_is_a_full_run(self) -> None:
        reason = self.decide(["lost.cfg"]).full_reason
        self.assertEqual(reason, "empty answer for covered file lost.cfg")

    def test_an_unnamed_file_selects_zero_modules_without_a_fallback(self) -> None:
        decision = self.decide(["docs/unknown.md"])
        self.assertEqual((decision.modules, decision.full_reason), ((), None))

    def test_a_mix_of_uncovered_and_shared_is_a_full_run(self) -> None:
        reason = self.decide(["docs/unknown.md", "Makefile"], self.SHARED).full_reason
        self.assertEqual(reason, "shared test machinery: Makefile")

    def test_decisions_do_not_depend_on_staging_order(self) -> None:
        paths = ["tools/alpha.py", "Makefile", "tests/util.py", "lost.cfg", ".planning/STATE.md"]
        base = self.decide(paths, self.SHARED)
        for order in itertools.permutations(paths):
            self.assertEqual(self.decide(list(order), self.SHARED), base, order)
        calm = ["tools/alpha.py", "tools/beta.py", "tests/data/gamma.txt"]
        base = self.decide(calm)
        for order in itertools.permutations(calm):
            self.assertEqual(self.decide(list(order)), base, order)

    def test_a_mapping_run_writes_nothing(self) -> None:
        before = snapshot(self.root)
        index = self.mapper.build_index(self.root)
        self.mapper.covering_modules(index, "tools/alpha.py")
        self.decide(["tools/alpha.py", "tests/util.py", "Makefile"], self.SHARED)
        self.assertEqual(snapshot(self.root), before)


@unittest.skipUnless(shutil.which("git"), "git not available")
class StagedPathsTest(MapperCase):
    def git(self, *args: str) -> None:
        env = {**{k: v for k, v in os.environ.items() if not k.startswith("GIT_")},
               "GIT_CEILING_DIRECTORIES": str(self.tmp)}
        quiet = ["-c", "user.name=t", "-c", "user.email=t@t.invalid", "-c", "commit.gpgsign=false",
                 "-c", f"core.hooksPath={os.devnull}"]
        subprocess.run(["git", *quiet, *args], cwd=self.root, env=env, check=True,
                       capture_output=True)

    def test_lists_additions_deletions_and_both_sides_of_a_rename(self) -> None:
        self.git("init", "-q")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "i")
        (self.root / "tools" / "alpha.py").unlink()
        (self.root / "tools" / "new.py").write_text("x = 1\n")
        (self.root / "tools" / "beta.py").rename(self.root / "tools" / "beta2.py")
        self.git("add", "-A")
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        with unittest.mock.patch.dict(os.environ, env, clear=True):
            got = sorted(self.mapper.staged_paths(self.root))
        self.assertEqual(got, ["tools/alpha.py", "tools/beta.py", "tools/beta2.py", "tools/new.py"])

    def test_a_folder_that_is_not_a_repo_is_a_mapper_error(self) -> None:
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        env["GIT_CEILING_DIRECTORIES"] = str(self.tmp)
        with unittest.mock.patch.dict(os.environ, env, clear=True), \
                self.assertRaises(self.mapper.MapperError):
            self.mapper.staged_paths(self.root)


class RunnerStagedTest(unittest.TestCase):
    """The runner's --staged mode, with the module run patched out."""

    def setUp(self) -> None:
        self.runner = load_tool(RUNNER)
        self.mapper = load_tool(MAPPER)
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="aikit-staged-run-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.root = make_tree(self.tmp / "repo", TREE)
        self.ran: list[list[str]] = []
        patcher = unittest.mock.patch.object(self.runner, "_run_all", self.record)
        patcher.start()
        self.addCleanup(patcher.stop)

    def record(self, modules, cwd=None):
        self.ran.append(list(modules))
        return []

    def main(self, *argv: str) -> tuple[int, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = self.runner.main(list(argv), cwd=self.root)
        return code, out.getvalue() + err.getvalue()

    def full_groups(self) -> list[str]:
        groups = self.runner.group_modules(self.runner.discover_modules())
        return groups["unit"] + groups["arch"]

    def stand_in(self, decision=None, error=None, staged=("tools/alpha.py",)):
        class Fake:
            @staticmethod
            def staged_paths(_root):
                return list(staged)

            @staticmethod
            def decide(_root, _paths, _shared):
                if error is not None:
                    raise error
                return decision

        return unittest.mock.patch.object(self.runner, "_load_mapper", lambda: Fake)

    def test_staged_excludes_group_and_module_names(self) -> None:
        for argv in (("--staged", "--group", "unit"), ("tests.x", "--staged")):
            self.assertEqual(self.main(*argv)[0], 2, argv)
        self.assertEqual(self.ran, [])

    def test_a_planning_only_commit_runs_zero_modules(self) -> None:
        with unittest.mock.patch.object(self.runner.subprocess, "Popen") as popen:
            code, out = self.main("--staged", ".planning/STATE.md")
        self.assertEqual(code, 0)
        self.assertIn("staged: 1 files -> 0 modules", out)
        self.assertEqual(self.ran, [])
        popen.assert_not_called()

    def test_no_staged_files_runs_zero_modules(self) -> None:
        with self.stand_in(staged=()):
            code, out = self.main("--staged")
        self.assertEqual(code, 0)
        self.assertIn("staged: no staged files; 0 modules", out)
        self.assertEqual(self.ran, [])

    def test_a_covered_file_runs_its_module_and_the_arch_group_once(self) -> None:
        code, out = self.main("--staged", "tools/beta.py", "tools/beta.py")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.ran, [["tests.test_beta", "tests.test_arch"]])
        self.assertIn("staged: tests.test_beta", out)

    def test_shared_machinery_runs_the_full_unit_and_arch_groups(self) -> None:
        code, out = self.main("--staged", "tools/run_unittest_parallel.py", "tools/beta.py")
        self.assertEqual(code, 0, out)
        self.assertIn("staged: full unit+arch run: shared test machinery:", out)
        self.assertEqual(self.ran, [self.full_groups()])
        self.assertGreater(len(self.ran[0]), 10)

    def test_a_mapper_exception_runs_the_full_groups_never_zero(self) -> None:
        patch = self.stand_in(error=RuntimeError("boom"))
        with patch:
            code, out = self.main("--staged", "tools/alpha.py")
        self.assertEqual(code, 0)
        self.assertIn("staged: full unit+arch run: mapper error: RuntimeError: boom", out)
        self.assertEqual(self.ran, [self.full_groups()])

    def test_a_mapper_that_cannot_be_imported_runs_the_full_groups(self) -> None:
        def broken():
            raise ImportError("no mapper")

        with unittest.mock.patch.object(self.runner, "_load_mapper", broken):
            code, out = self.main("--staged", "tools/alpha.py")
        self.assertIn("mapper error: ImportError: no mapper", out)
        self.assertEqual(self.ran, [self.full_groups()])
        self.assertEqual(code, 0)

    def test_unreadable_mapper_input_runs_the_full_groups(self) -> None:
        (self.root / "tests" / "test_bad.py").write_bytes(b"\xff\xfe")
        code, out = self.main("--staged", "tools/beta.py")
        self.assertIn("full unit+arch run: mapper error: MapperError", out)
        self.assertEqual(self.ran, [self.full_groups()])
        self.assertEqual(code, 0)

    def test_a_stale_machinery_name_exits_2_naming_it(self) -> None:
        with unittest.mock.patch.object(
            self.runner, "SHARED_MACHINERY", frozenset({"no/such/file.cfg"})
        ):
            code, out = self.main("--staged", "tools/beta.py")
        self.assertEqual(code, 2)
        self.assertIn("error: stale shared machinery names: no/such/file.cfg", out)
        self.assertEqual(self.ran, [])

    def test_every_real_machinery_entry_exists(self) -> None:
        self.assertEqual(self.runner.stale_machinery_names(REPO_ROOT), [])
        self.assertIn("tools/run_unittest_parallel.py", self.runner.SHARED_MACHINERY)

    def decision(self, *modules: str):
        return self.mapper.Decision(modules, {}, False, None)

    def run_with_uv(self, *modules: str, uv: str | None):
        patch = self.stand_in(self.decision(*modules))
        proc = unittest.mock.MagicMock()
        proc.communicate.return_value = ("1/1 modules passed\n", "")
        proc.returncode = 0
        with patch, unittest.mock.patch.object(
            self.runner.shutil, "which", lambda _name: uv
        ), unittest.mock.patch.object(
            self.runner.subprocess, "Popen", return_value=proc
        ) as popen:
            code, out = self.main("--staged", "tools/alpha.py")
        return code, out, popen

    def test_unit_modules_run_in_process_and_uv_modules_in_one_child(self) -> None:
        code, out, popen = self.run_with_uv(
            "tests.test_alpha", "tests.test_wizard_app", "tests.test_worktree_e2e",
            uv="/usr/bin/uv",
        )
        self.assertEqual(code, 0, out)
        self.assertEqual(self.ran, [["tests.test_alpha"]])
        popen.assert_called_once()
        argv = popen.call_args.args[0]
        self.assertEqual(argv[:3], ["uv", "run", "python"])
        self.assertEqual(pathlib.Path(argv[3]).name, "run_unittest_parallel.py")
        self.assertEqual(argv[4:], ["tests.test_wizard_app", "tests.test_worktree_e2e"])
        self.assertNotIn("--staged", argv)
        self.assertIs(popen.call_args.kwargs["start_new_session"], True)
        self.assertIn("staged: under uv: tests.test_wizard_app tests.test_worktree_e2e", out)

    def test_a_uv_only_selection_never_reaches_the_pool(self) -> None:
        with unittest.mock.patch.object(
            self.runner, "_run_all", side_effect=AssertionError("pool must not start")
        ):
            code, out, popen = self.run_with_uv("tests.test_wizard_app", uv="/usr/bin/uv")
        self.assertEqual(code, 0, out)
        popen.assert_called_once()

    def test_a_chosen_e2e_module_is_never_dropped(self) -> None:
        _code, _out, popen = self.run_with_uv("tests.test_worktree_e2e", uv="/usr/bin/uv")
        self.assertIn("tests.test_worktree_e2e", popen.call_args.args[0])

    def test_without_uv_the_commit_is_refused_with_a_pointer(self) -> None:
        code, out, popen = self.run_with_uv("tests.test_alpha", "tests.test_wizard_app", uv=None)
        self.assertEqual(code, 1)
        self.assertIn("staged: uv not found; the modules tests.test_wizard_app need it;"
                      " run make setup-env", out)
        popen.assert_not_called()
        self.assertEqual(self.ran, [])

    def test_a_failing_uv_child_fails_the_run(self) -> None:
        patch = self.stand_in(self.decision("tests.test_wizard_app"))
        proc = unittest.mock.MagicMock()
        proc.communicate.return_value = ("failed: tests.test_wizard_app\n", "")
        proc.returncode = 1
        with patch, unittest.mock.patch.object(
            self.runner.shutil, "which", lambda _name: "/usr/bin/uv"
        ), unittest.mock.patch.object(self.runner.subprocess, "Popen", return_value=proc):
            code, out = self.main("--staged", "tools/alpha.py")
        self.assertEqual(code, 1)
        self.assertIn("failed: tests.test_wizard_app", out)


if __name__ == "__main__":
    unittest.main()
