"""Run cst-refactor's codemods for real (LibCST from uv's dev group); compare bytes exactly."""

import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
SKILL = REPO / "skills" / "cst-refactor"
TEMPLATE = SKILL / "codemod_template.py.txt"
FIXTURES = REPO / "tests" / "fixtures" / "cst_refactor"


class _CodemodCase(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp(prefix="ai-kit-p321-cst-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        shutil.copyfile(TEMPLATE, self.tmp / "codemod_template.py")

    def place(self, case, name, dest):
        target = self.tmp / dest
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(FIXTURES / case / name, target)

    def expected(self, case, name):
        return (FIXTURES / case / name).read_bytes()

    def codemod(self, *args):
        return subprocess.run(
            [sys.executable, str(self.tmp / "codemod_template.py"), *args],
            cwd=self.tmp,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
            env={**os.environ, "AI_KIT_REFUSE_REAL_HOME": "1"},
        )


class TestRenameSymbol(_CodemodCase):
    NAMES = ("rename-symbol", "--old-name", "old_fn", "--new-name", "new_fn")
    RENAME = (*NAMES, "--paths", "pkg")

    def place_package(self):
        self.place("rename_symbol", "a.py.txt", "pkg/a.py")
        self.place("rename_symbol", "b.py.txt", "pkg/b.py")
        self.place("rename_symbol", "c.py.txt", "pkg/c.py")

    def assert_renamed(self):
        self.assertEqual((self.tmp / "pkg/a.py").read_bytes(),
                         self.expected("rename_symbol", "a.expected.txt"))
        self.assertEqual((self.tmp / "pkg/b.py").read_bytes(),
                         self.expected("rename_symbol", "b.expected.txt"))
        self.assertEqual((self.tmp / "pkg/c.py").read_bytes(),
                         self.expected("rename_symbol", "c.py.txt"))

    def test_renames_names_but_not_comments_or_strings(self):
        self.place_package()
        proc = self.codemod(*self.RENAME)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assert_renamed()

    def test_second_run_changes_nothing(self):
        self.place_package()
        self.assertEqual(self.codemod(*self.RENAME).returncode, 0)
        proc = self.codemod(*self.RENAME)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assert_renamed()

    def test_include_tests_renames_the_tests_folder(self):
        self.place_package()
        self.place("rename_symbol", "tests_test_a.py.txt", "tests/test_a.py")
        proc = self.codemod(*self.RENAME, "--include-tests")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual((self.tmp / "tests/test_a.py").read_bytes(),
                         self.expected("rename_symbol", "tests_test_a.expected.txt"))

    def test_include_tests_without_a_tests_folder_stops(self):
        self.place_package()
        proc = self.codemod(*self.RENAME, "--include-tests")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("Path does not exist: tests", proc.stderr)
        self.assertEqual((self.tmp / "pkg/a.py").read_bytes(),
                         self.expected("rename_symbol", "a.expected.txt"))

    def test_equal_names_stop(self):
        self.place_package()
        proc = self.codemod(
            "rename-symbol", "--old-name", "old_fn", "--new-name", "old_fn", "--paths", "pkg"
        )
        self.assertEqual(proc.returncode, 1)
        self.assertIn("Old and new names must differ.", proc.stderr)

    def test_missing_path_stops(self):
        proc = self.codemod(*self.NAMES, "--paths", "nope")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("Path does not exist: nope", proc.stderr)

    def test_missing_paths_flag_is_a_usage_error(self):
        proc = self.codemod(*self.NAMES)
        self.assertEqual(proc.returncode, 2)


class TestRenameParameter(_CodemodCase):
    def test_signature_body_and_keyword_calls(self):
        self.place("rename_parameter", "m.py.txt", "m.py")
        proc = self.codemod(
            "rename-parameter", "--function", "greet", "--old-name", "name",
            "--new-name", "person", "--paths", "m.py",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual((self.tmp / "m.py").read_bytes(),
                         self.expected("rename_parameter", "m.expected.txt"))

    def test_star_args_are_renamed(self):
        self.place("rename_parameter", "star.py.txt", "star.py")
        proc = self.codemod(
            "rename-parameter", "--function", "f", "--old-name", "args",
            "--new-name", "rest", "--paths", "star.py",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual((self.tmp / "star.py").read_bytes(),
                         self.expected("rename_parameter", "star.expected.txt"))


class TestAddParameter(_CodemodCase):
    def test_without_call_value_leaves_call_sites(self):
        self.place("add_parameter", "m.py.txt", "m.py")
        proc = self.codemod(
            "add-parameter", "--function", "f", "--param", "flag", "--default", "False",
            "--paths", "m.py",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual((self.tmp / "m.py").read_bytes(),
                         self.expected("add_parameter", "m.no_call_value.expected.txt"))

    def test_with_call_value_updates_call_sites(self):
        self.place("add_parameter", "m.py.txt", "m.py")
        proc = self.codemod(
            "add-parameter", "--function", "f", "--param", "flag", "--default", "False",
            "--call-value", "False", "--paths", "m.py",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual((self.tmp / "m.py").read_bytes(),
                         self.expected("add_parameter", "m.call_value.expected.txt"))


class TestRemoveParameter(_CodemodCase):
    def test_keyword_removed_positional_kept(self):
        self.place("remove_parameter", "m.py.txt", "m.py")
        proc = self.codemod(
            "remove-parameter", "--function", "f", "--param", "c", "--paths", "m.py"
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual((self.tmp / "m.py").read_bytes(),
                         self.expected("remove_parameter", "m.expected.txt"))

    def test_star_parameter_is_never_removed(self):
        self.place("remove_parameter", "star.py.txt", "star.py")
        proc = self.codemod(
            "remove-parameter", "--function", "f", "--param", "kwargs", "--paths", "star.py"
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual((self.tmp / "star.py").read_bytes(),
                         self.expected("remove_parameter", "star.py.txt"))


class TestRewriteDocstring(_CodemodCase):
    def test_class_only(self):
        self.place("rewrite_docstring", "m.py.txt", "m.py")
        proc = self.codemod(
            "rewrite-docstring", "--class", "Box", "--match", "Old", "--replace", "New",
            "--paths", "m.py",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual((self.tmp / "m.py").read_bytes(),
                         self.expected("rewrite_docstring", "m.class.expected.txt"))

    def test_method_only(self):
        self.place("rewrite_docstring", "m.py.txt", "m.py")
        proc = self.codemod(
            "rewrite-docstring", "--class", "Box", "--function", "run", "--match", "Old",
            "--replace", "New", "--paths", "m.py",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual((self.tmp / "m.py").read_bytes(),
                         self.expected("rewrite_docstring", "m.method.expected.txt"))

    def test_fstring_docstring_is_skipped(self):
        self.place("rewrite_docstring", "m.py.txt", "m.py")
        proc = self.codemod(
            "rewrite-docstring", "--function", "fs", "--match", "Old", "--replace", "New",
            "--paths", "m.py",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual((self.tmp / "m.py").read_bytes(),
                         self.expected("rewrite_docstring", "m.py.txt"))

    def test_neither_flag_stops(self):
        self.place("rewrite_docstring", "m.py.txt", "m.py")
        proc = self.codemod(
            "rewrite-docstring", "--match", "Old", "--replace", "New", "--paths", "m.py"
        )
        self.assertEqual(proc.returncode, 1)
        self.assertIn("Provide --class or --function", proc.stderr)


class TestAbort(_CodemodCase):
    def test_unparseable_file_aborts_after_earlier_files(self):
        self.place("rename_symbol", "a.py.txt", "p/a.py")
        self.place("abort", "bad.source.txt", "p/bad.py")
        self.place("rename_symbol", "c.py.txt", "p/c.py")
        proc = self.codemod(
            "rename-symbol", "--old-name", "old_fn", "--new-name", "new_fn",
            "--paths", "p/a.py", "p/bad.py", "p/c.py",
        )
        self.assertEqual(proc.returncode, 1)
        self.assertIn("ParserSyntaxError", proc.stderr)
        self.assertEqual((self.tmp / "p/a.py").read_bytes(),
                         self.expected("rename_symbol", "a.expected.txt"))
        self.assertEqual((self.tmp / "p/c.py").read_bytes(),
                         self.expected("rename_symbol", "c.py.txt"))
