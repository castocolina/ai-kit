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
import types
import unittest
import unittest.mock
from typing import Any

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


@contextlib.contextmanager
def fake_uv_child(runner, uv: str | None = "/usr/bin/uv", returncode: int = 0,
                  output: str = "1/1 modules passed\n"):
    """uv is `uv` (None: absent); the `uv run` child exits `returncode`. Yields the Popen mock."""
    proc = unittest.mock.MagicMock()
    proc.communicate.return_value = (output, "")
    proc.returncode = returncode
    with unittest.mock.patch.object(runner.shutil, "which", lambda _name: uv), \
            unittest.mock.patch.object(runner.subprocess, "Popen", return_value=proc) as popen:
        yield popen


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

    def test_a_tight_skill_is_read_by_path_or_join_others_keep_the_bare_name(self) -> None:
        # A synthetic tight folder: a fixture naming the real one by path would select this module.
        make_tree(self.root, {
            "tests/test_path.py": "P = 'skills/tight-skill/x'\n",
            "tests/test_join.py": "J = ('skills', 'tight-skill')\n",
            "tests/test_bare.py": "CANDIDATES = ['tight-skill', 'plain-skill']\n",
        })
        index = self.mapper.build_index(self.root)
        with unittest.mock.patch.object(self.mapper, "TIGHT_SKILL_FOLDERS",
                                        frozenset({"tight-skill"})):
            self.assertEqual(
                self.mapper.covering_modules(index, "skills/tight-skill/run.py"),
                frozenset({"tests.test_path", "tests.test_join"}))
            self.assertIn("tests.test_bare",
                          self.mapper.covering_modules(index, "skills/plain-skill/run.py"))

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
        "helper_attr": "value = setup._detect()\n",
    }

    def test_a_private_helper_attribute_selects_its_tool(self) -> None:
        make_tree(self.root, {"tests/test_helper_attr.py": "value = setup._zed_probe()\n",
                              "tools/zed_probe.py": ""})
        index = self.mapper.build_index(self.root)
        self.assertEqual(self.mapper.covering_modules(index, "tools/zed_probe.py"),
                         frozenset({"tests.test_helper_attr"}))

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

    def test_a_full_run_still_names_its_covering_modules(self) -> None:
        decision = self.decide(["tests/util.py"])
        self.assertEqual(decision.full_reason,
                         "shared test helper or fixture: tests/util.py (2 modules)")
        self.assertEqual(len(decision.modules), 2)

    def test_shared_machinery_keeps_its_reason_when_the_index_cannot_be_built(self) -> None:
        (self.root / "tests" / "test_bad.py").write_bytes(b"\xff\xfe")
        decision = self.decide(["Makefile", "tools/alpha.py"], self.SHARED)
        self.assertEqual((decision.full_reason, decision.index_built),
                         ("shared test machinery: Makefile", False))
        with self.assertRaises(self.mapper.MapperError):
            self.decide(["tools/alpha.py"], self.SHARED)


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
        # A fixed table, so these cases do not move when the measured table is refreshed.
        table = unittest.mock.patch.object(self.runner, "E2E_RECORDED_SECS", {
            "tests.test_precompact_shims_e2e": 58, "tests.test_cross_ai_runner_e2e": 361,
        })
        table.start()
        self.addCleanup(table.stop)

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
        groups = self.runner.group_modules(sorted({*self.full_groups(), "tests.test_beta"}))
        self.assertEqual(self.ran, [groups["unit"] + groups["arch"]])
        self.assertGreater(len(self.ran[0]), 10)

    def test_a_mapper_exception_runs_the_full_groups_never_zero(self) -> None:
        patch = self.stand_in(error=RuntimeError("boom"))
        with patch, self.fake_uv() as popen:
            code, out = self.main("--staged", "tools/alpha.py")
        self.assertEqual(code, 0)
        self.assertIn("staged: full unit+arch run: mapper error: RuntimeError: boom", out)
        self.assertEqual(self.ran, [self.full_groups()])
        self.assertEqual(popen.call_args.args[0][4:], ["tests.test_precompact_shims_e2e"])

    def test_a_mapper_that_cannot_be_imported_runs_the_full_groups(self) -> None:
        def broken():
            raise ImportError("no mapper")

        with unittest.mock.patch.object(self.runner, "_load_mapper", broken), self.fake_uv():
            code, out = self.main("--staged", "tools/alpha.py")
        self.assertIn("mapper error: ImportError: no mapper", out)
        self.assertEqual(self.ran, [self.full_groups()])
        self.assertEqual(code, 0)

    def test_unreadable_mapper_input_runs_the_full_groups(self) -> None:
        (self.root / "tests" / "test_bad.py").write_bytes(b"\xff\xfe")
        with self.fake_uv():
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

    def fake_uv(self, uv: str | None = "/usr/bin/uv", returncode: int = 0,
                output: str = "1/1 modules passed\n"):
        return fake_uv_child(self.runner, uv=uv, returncode=returncode, output=output)

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
        self.assertEqual(argv[4:], ["tests.test_wizard_app"])
        self.assertNotIn("--staged", argv)
        self.assertIs(popen.call_args.kwargs["start_new_session"], True)
        self.assertIn("staged: under uv: tests.test_wizard_app", out)
        self.assertIn("staged: deferred to push (over the 60 s commit budget): "
                      "tests.test_worktree_e2e (no recorded time)", out)

    def test_a_uv_only_selection_never_reaches_the_pool(self) -> None:
        with unittest.mock.patch.object(
            self.runner, "_run_all", side_effect=AssertionError("pool must not start")
        ):
            code, out, popen = self.run_with_uv("tests.test_wizard_app", uv="/usr/bin/uv")
        self.assertEqual(code, 0, out)
        popen.assert_called_once()

    def test_a_chosen_e2e_module_is_run_or_named_never_dropped(self) -> None:
        code, out, popen = self.run_with_uv(
            "tests.test_precompact_shims_e2e", "tests.test_worktree_e2e", uv="/usr/bin/uv",
        )
        self.assertEqual(code, 0, out)
        self.assertIn("tests.test_precompact_shims_e2e", popen.call_args.args[0])
        self.assertIn("tests.test_worktree_e2e (no recorded time); run now:", out)

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

    def test_split_e2e_defers_unrecorded_and_over_budget_modules(self) -> None:
        table = {"tests.test_a_e2e": 60, "tests.test_b_e2e": 61}
        with unittest.mock.patch.object(self.runner, "E2E_RECORDED_SECS", table):
            within, deferred = self.runner.split_e2e(
                ["tests.test_b_e2e", "tests.test_c_e2e", "tests.test_a_e2e"])
        self.assertEqual(within, ["tests.test_a_e2e"])
        self.assertEqual(deferred, ["tests.test_b_e2e", "tests.test_c_e2e"])

    def test_the_commit_budget_splits_the_e2e_part_of_a_covering_set(self) -> None:
        under, over, unrecorded = (
            "tests.test_precompact_shims_e2e", "tests.test_cross_ai_runner_e2e",
            "tests.test_worktree_e2e",
        )
        patch = self.stand_in(self.decision("tests.test_alpha", under, over, unrecorded))
        table = {under: 60, over: 61}
        with patch, unittest.mock.patch.object(self.runner, "E2E_RECORDED_SECS", table), \
                self.fake_uv() as popen:
            code, out = self.main("--staged", "tools/alpha.py")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.ran, [["tests.test_alpha"]])
        self.assertEqual(popen.call_args.args[0][4:], [under])
        self.assertIn(f"staged: deferred to push (over the 60 s commit budget): {over}"
                      f" (recorded 61 s); run now: uv run python tools/run_unittest_parallel.py"
                      f" {over}", out)
        self.assertIn(f"{unrecorded} (no recorded time); run now:", out)
        self.assertNotIn(f"=== {over}", out)

    def test_a_full_run_still_runs_its_within_budget_e2e_modules(self) -> None:
        under, over = "tests.test_precompact_shims_e2e", "tests.test_cross_ai_runner_e2e"
        decision = self.mapper.Decision(
            (under, over), {}, False, "shared test machinery: tools/run_unittest_parallel.py",
        )
        with self.stand_in(decision), \
                unittest.mock.patch.object(self.runner, "E2E_RECORDED_SECS",
                                           {under: 58, over: 361}), \
                self.fake_uv() as popen:
            code, out = self.main("--staged", "tools/run_unittest_parallel.py")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.ran, [self.full_groups()])
        self.assertEqual(popen.call_args.args[0][4:], [under])
        self.assertIn(f"{over} (recorded 361 s)", out)

    def test_a_full_run_keeps_a_covering_uv_and_integration_module(self) -> None:
        uv_mod = sorted(self.runner.UNIT_UV_MODULES)[0]
        integ = sorted(self.runner.INTEGRATION_MODULES)[0]
        decision = self.mapper.Decision(
            (uv_mod, integ), {}, False, "shared test machinery: tools/run_unittest_parallel.py",
        )
        with self.stand_in(decision), unittest.mock.patch.object(
            self.runner, "_run_staged_modules", return_value=0
        ) as run:
            code, _out = self.main("--staged", "tools/run_unittest_parallel.py")
        self.assertEqual(code, 0)
        modules = run.call_args.args[0]
        self.assertTrue({uv_mod, integ} <= set(modules))
        self.assertGreater(len(modules), 10)

    def test_a_mapper_error_runs_within_budget_e2e_and_names_every_other(self) -> None:
        under = "tests.test_precompact_shims_e2e"
        with self.stand_in(error=RuntimeError("boom")), \
                unittest.mock.patch.object(self.runner, "E2E_RECORDED_SECS", {under: 58}), \
                self.fake_uv() as popen:
            code, out = self.main("--staged", "tools/alpha.py")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.ran, [self.full_groups()])
        self.assertEqual(popen.call_args.args[0][4:], [under])
        for module in sorted(self.runner.E2E_MODULES - {under}):
            self.assertIn(f"{module} (no recorded time); run now:", out)


STATS_TREE = {
    # tools/alpha.py: 1 module; tools/beta.py: 2 (one of them e2e); skills/s3: 4; tools/gamma.py: 0.
    "tests/test_one.py": "# covers tools/alpha.py\nNAME = 'alpha.py'\n",
    "tests/test_two.py": "NAME = 'beta.py'\n",
    "tests/test_a.py": "NAMES = ['skills/s3/SKILL.md', 'README.md']\n",
    "tests/test_b.py": "NAME = 'skills/s3'\nREADME = 'README.md'\n",
    "tests/test_c.py": "NAME = 'skills/s3'\nREADME = 'README.md'\n",
    "tests/test_d.py": "NAME = 'skills/s3'\n",
    "tests/test_e2e_x.py": "NAMES = ['beta.py', 'AGENTS.md']\n",
    "skills/s3/SKILL.md": "",
    "tools/alpha.py": "",
    "tools/beta.py": "",
    "tools/gamma.py": "",
}
STATS_TRACKED = [
    "AGENTS.md", "README.md", "docs/x.md", "skills/s3/SKILL.md", "tests/test_a.py",
    "tools/alpha.py",
]


class StatsTest(MapperCase):
    def setUp(self) -> None:
        super().setUp()
        self.stats_root = make_tree(self.tmp / "stats", STATS_TREE)

    def test_unit_stats_reports_medians_max_uncovered_e2e_and_data_files(self) -> None:
        index = self.mapper.build_index(self.stats_root)
        stats = self.mapper.unit_stats(index, self.stats_root, STATS_TRACKED,
                                       {"tests.test_e2e_x"})
        self.assertEqual(stats.unit_count, 4)
        self.assertEqual(stats.median_all, 1.5)  # over 0, 1, 2, 4
        self.assertEqual(stats.median_covered, 2)  # over 1, 2, 4
        self.assertEqual((stats.max_count, stats.max_unit), (4, "skills/s3"))
        self.assertEqual(stats.uncovered, ("tools/gamma.py",))
        self.assertEqual(stats.e2e_sets, 1)
        self.assertEqual(stats.top_data_files[:2], (("README.md", 3), ("AGENTS.md", 1)))

    def test_stats_and_path_decisions_print_their_lines(self) -> None:
        root = str(self.stats_root)
        out = io.StringIO()
        tables = (frozenset({"tests.test_e2e_x"}), frozenset())
        with unittest.mock.patch.object(self.mapper, "tracked_paths",
                                        lambda _root: STATS_TRACKED), \
                unittest.mock.patch.object(self.mapper, "_runner_tables", lambda: tables), \
                contextlib.redirect_stdout(out):
            code = self.mapper.main(["--stats", "--root", root])
            decided = self.mapper.main(["--root", root, "tools/alpha.py"])
        self.assertEqual((code, decided), (0, 0))
        text = out.getvalue()
        self.assertIn("mapper: 4 units; covering modules per unit: median 1.5 (all units),"
                      " median 2 (covered units), max 4 (skills/s3); 1 covering sets hold"
                      " an e2e module", text)
        self.assertIn("mapper: uncovered unit tools/gamma.py", text)
        self.assertIn("mapper: data file README.md: 3 modules", text)
        self.assertIn("modules: tests.test_one", text)

    def test_usage_and_mapper_errors_exit_2_and_1(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(self.mapper.main([]), 2)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = self.mapper.main(["--root", str(self.tmp / "missing"), "tools/alpha.py"])
        self.assertEqual(code, 1)
        self.assertIn("mapper error:", out.getvalue())


class PushedGitTest(MapperCase):
    """The argv lists of the push proof, with subprocess.run patched."""

    def completed(self, stdout: bytes = b"", returncode: int = 0):
        return subprocess.CompletedProcess([], returncode, stdout=stdout, stderr=b"fatal")

    def test_pushed_paths_runs_the_three_dot_diff_argv(self) -> None:
        run_result = self.completed(b"tools/a.py\0tests/b.py\0")
        with unittest.mock.patch.object(self.mapper.subprocess, "run",
                                        return_value=run_result) as run:
            got = self.mapper.pushed_paths(self.root, "aaa", "bbb")
        self.assertEqual(got, ["tools/a.py", "tests/b.py"])
        self.assertEqual(run.call_args.args[0],
                         ["git", "diff", "--name-only", "-z", "--no-renames", "aaa...bbb"])

    def test_outside_commits_leaves_tags_and_the_stash_out_before_all(self) -> None:
        with unittest.mock.patch.object(self.mapper.subprocess, "run",
                                        return_value=self.completed(b"abc\ndef\n")) as run:
            got = self.mapper.outside_commits(self.root, "HEAD")
        self.assertEqual(got, ["abc", "def"])
        self.assertEqual(run.call_args.args[0], [
            "git", "rev-list", "--exclude=refs/stash", "--exclude=refs/tags/*", "--all",
            "--not", "--remotes", "HEAD",
        ])

    def test_a_ref_starting_with_dash_is_refused_before_git_runs(self) -> None:
        calls = (
            lambda: self.mapper.pushed_paths(self.root, "-x", "b"),
            lambda: self.mapper.outside_commits(self.root, "-x"),
            lambda: self.mapper.commit_sha(self.root, "-x"),
        )
        with unittest.mock.patch.object(self.mapper.subprocess, "run",
                                        side_effect=AssertionError("git must not run")):
            for call in calls:
                with self.assertRaises(self.mapper.MapperError):
                    call()

    def test_a_non_zero_git_exit_is_a_mapper_error(self) -> None:
        with unittest.mock.patch.object(self.mapper.subprocess, "run",
                                        return_value=self.completed(returncode=128)):
            with self.assertRaises(self.mapper.MapperError):
                self.mapper.pushed_paths(self.root, "a", "b")
            with self.assertRaises(self.mapper.MapperError):
                self.mapper.outside_commits(self.root, "b")


class PushedModeTest(unittest.TestCase):
    """The runner's --pushed mode, with the mapper, the refs and the uv child faked."""

    REFS = ("PRE_COMMIT_FROM_REF", "PRE_COMMIT_TO_REF")
    WITHIN = "tests.test_precompact_shims_e2e"  # patched to 58 s below: within the budget
    OVER = "tests.test_cross_ai_runner_e2e"  # patched to 361 s below: over it

    def setUp(self) -> None:
        self.runner = load_tool(RUNNER)
        self.mapper = load_tool(MAPPER)
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="aikit-pushed-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        pool = unittest.mock.patch.object(
            self.runner, "_run_all", side_effect=AssertionError("the pool must not start"))
        pool.start()
        self.addCleanup(pool.stop)
        table = unittest.mock.patch.object(
            self.runner, "E2E_RECORDED_SECS", {self.WITHIN: 58, self.OVER: 361})
        table.start()
        self.addCleanup(table.stop)

    def refs(self, from_ref: str | None, to_ref: str | None):
        env = {k: v for k, v in os.environ.items() if k not in self.REFS}
        if from_ref is not None:
            env[self.REFS[0]] = from_ref
        if to_ref is not None:
            env[self.REFS[1]] = to_ref
        return unittest.mock.patch.dict(os.environ, env, clear=True)

    def covering(self, *modules: str):
        return self.mapper.Decision(modules, {}, False, None)

    def mapper_stub(self, head="h1", to="h1", outside=(), paths=("tools/alpha.py",),
                    decision=None, error=None):
        def decide(_root, _paths, _shared):
            if error is not None:
                raise error
            return decision

        return types.SimpleNamespace(
            commit_sha=lambda _root, ref: head if ref == "HEAD" else to,
            outside_commits=lambda _root, _to: list(outside),
            pushed_paths=lambda _root, _from, _to: list(paths),
            decide=decide,
        )

    def push(self, mapper, from_ref: str | None = "a", to_ref: str | None = "b",
             uv: str | None = "/usr/bin/uv"):
        out = io.StringIO()
        with self.refs(from_ref, to_ref), \
                unittest.mock.patch.object(self.runner, "_load_mapper", lambda: mapper), \
                fake_uv_child(self.runner, uv=uv) as popen, \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            code = self.runner.main(["--pushed"], cwd=self.tmp)
        return code, out.getvalue(), popen

    def test_a_narrowed_push_runs_only_the_over_budget_covering_modules(self) -> None:
        mapper = self.mapper_stub(
            decision=self.covering(self.WITHIN, self.OVER, "tests.test_alpha"),
            paths=("tools/alpha.py", "tools/beta.py", "tools/gamma.py"),
        )
        code, out, popen = self.push(mapper)
        self.assertEqual(code, 0, out)
        self.assertEqual(popen.call_args.args[0][4:], [self.OVER])
        self.assertIn("pushed: 3 files in a...b -> 1 deferred e2e modules", out)
        self.assertIn(f"pushed: {self.OVER}", out)

    def test_an_empty_narrowed_result_prints_no_deferred_and_starts_nothing(self) -> None:
        code, out, popen = self.push(self.mapper_stub(decision=self.covering("tests.test_alpha")))
        self.assertEqual(code, 0, out)
        self.assertIn("pushed: no deferred e2e modules", out)
        popen.assert_not_called()

    def test_every_fallback_reason_runs_every_over_budget_module(self) -> None:
        every_over_budget = sorted(self.runner.E2E_MODULES - {self.WITHIN})
        cases: tuple[tuple[str, dict[str, Any], dict[str, Any]], ...] = (
            ("pushed: no push range", {}, {"from_ref": None}),
            ("pushed: no push range", {}, {"to_ref": None}),
            ("pushed: bad ref -x", {}, {"from_ref": "-x"}),
            ("pushed: the checkout HEAD is not the pushed commit b",
             {"head": "h1", "to": "h2"}, {}),
            ("pushed: 1 unpushed local commits lie outside b"
             " (another ref may be in this push)", {"outside": ["c1"]}, {}),
            ("pushed: mapper error: RuntimeError: boom", {"error": RuntimeError("boom")}, {}),
        )
        for reason, stub, refs in cases:
            with self.subTest(reason=reason, refs=refs):
                mapper = self.mapper_stub(decision=self.covering(self.WITHIN, self.OVER), **stub)
                code, out, popen = self.push(mapper, **{"from_ref": "a", "to_ref": "b"} | refs)
                self.assertEqual(code, 0, out)
                self.assertIn(f"{reason}; running every e2e module over the commit budget", out)
                self.assertEqual(popen.call_args.args[0][4:], every_over_budget)

    def test_a_decision_without_a_covering_set_falls_back(self) -> None:
        decision = self.mapper.Decision((), {}, False, "shared test machinery: Makefile",
                                        index_built=False)
        code, out, popen = self.push(self.mapper_stub(decision=decision))
        self.assertEqual(code, 0, out)
        self.assertIn("pushed: mapper error: RuntimeError: no covering set"
                      " (shared test machinery: Makefile); running every e2e module", out)
        self.assertIn(self.OVER, popen.call_args.args[0])

    def test_no_uv_with_a_chosen_module_is_refused_with_the_pointer(self) -> None:
        mapper = self.mapper_stub(decision=self.covering(self.WITHIN, self.OVER))
        code, out, popen = self.push(mapper, uv=None)
        self.assertEqual(code, 1)
        self.assertIn(f"pushed: uv not found; the modules {self.OVER} need it; run make setup-env",
                      out)
        popen.assert_not_called()

    def test_pushed_takes_no_other_argument(self) -> None:
        for argv in (["--pushed", "--group", "unit"], ["--pushed", "--staged"],
                     ["--pushed", self.OVER]):
            with self.subTest(argv=argv), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(self.runner.main(argv, cwd=self.tmp), 2)


if __name__ == "__main__":
    unittest.main()
