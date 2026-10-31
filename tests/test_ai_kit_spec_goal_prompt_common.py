"""Tests for skills/ai-kit-spec-goal-prompt/scripts/gp_common.py.

Three helpers are COPIES of existing sibling code (D-03). Each parity test loads the ORIGINAL
file by path and compares outputs over a table, so a change to an original fails here. The
guards (`is_machine_path`, `scan_text`) are tested against a fake home and a sentinel key; no
real home, credential or network is touched.
"""

import ast
import importlib.util
import itertools
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "skills" / "ai-kit-spec-goal-prompt" / "scripts"
COMMON_PATH = SCRIPTS / "gp_common.py"
sys.path.insert(0, str(SCRIPTS))
import gp_common

from tests import goal_prompt_fixtures as fx

FAKE_HOME = fx.FAKE_HOME
SENTINEL = "SENTINEL-KEY-0123456789abcdef"
_COUNTER = itertools.count()


def load_original(relpath):
    """Load a repo file by path under a fresh module name (never cached, never the real home)."""
    path = REPO / relpath
    name = f"original_{next(_COUNTER)}_{path.stem}"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PHASE_RANGE = "skills/ai-kit-gsd-spec-discuss/scripts/phase_range.py"
MAKEFILE_PARSE = "skills/_shared/ai_kit_rules_common/makefile_parse.py"
PACKAGE_SCRIPTS = "skills/ai-kit-project-rules-cicd/ai_kit_project_rules_cicd/package_scripts.py"


class TestPhaseKeyParity(unittest.TestCase):
    def test_matches_original_for_valid_numbers(self):
        original = load_original(PHASE_RANGE)
        for number in ["1", "16", "16.1", "16.2", "17", "27", "12.3.4"]:
            with self.subTest(number=number):
                self.assertEqual(gp_common.phase_key(number), original.phase_key(number))

    def test_rejects_invalid_numbers_like_original(self):
        original = load_original(PHASE_RANGE)
        for number in ["", "x", "1..2", "1.", "-1", "1a"]:
            with self.subTest(number=number):
                with self.assertRaises(ValueError):
                    gp_common.phase_key(number)
                with self.assertRaises(ValueError):
                    original.phase_key(number)

    def test_decimal_phases_sort_numerically(self):
        ordered = sorted(["17", "16.1", "16", "16.2"], key=gp_common.phase_key)
        self.assertEqual(ordered, ["16", "16.1", "16.2", "17"])


MAKEFILE_TEXT = (
    ".PHONY: a\n"
    "VAR := x\n"
    "e2e-test:\n"
    "\techo one\n"
    "e2e-test:\n"
    "e2e-docker: build\n"
    "\techo two\n"
    "test-unit:\n"
)


class TestMakeTargetsParity(unittest.TestCase):
    def test_matches_original_reader_on_the_same_text(self):
        original = load_original(MAKEFILE_PARSE)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "Makefile")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(MAKEFILE_TEXT)
            self.assertEqual(
                gp_common.make_targets(MAKEFILE_TEXT),
                original.parse_makefile_targets_ordered(path),
            )

    def test_ordered_first_occurrence_only(self):
        self.assertEqual(
            gp_common.make_targets(MAKEFILE_TEXT), ["e2e-test", "e2e-docker", "test-unit"]
        )


def _package_repo(tmp, package_json=None, lockfiles=()):
    repo = tempfile.mkdtemp(dir=tmp)
    if package_json is not None:
        with open(os.path.join(repo, "package.json"), "w", encoding="utf-8") as handle:
            handle.write(package_json)
    for name in lockfiles:
        with open(os.path.join(repo, name), "w", encoding="utf-8") as handle:
            handle.write("")
    return repo


class TestPackageParity(unittest.TestCase):
    def test_scripts_match_original(self):
        original = load_original(PACKAGE_SCRIPTS)
        cases = [
            '{"scripts": {"e2e": "playwright test", "x": 1}}',
            "{not json",
            '{"scripts": ["a", "b"]}',
            '{"name": "no-scripts"}',
            "[1, 2]",
        ]
        with tempfile.TemporaryDirectory() as tmp:
            for text in cases:
                with self.subTest(text=text):
                    repo = _package_repo(tmp, package_json=text)
                    self.assertEqual(
                        gp_common.read_package_scripts(repo),
                        original.read_package_scripts(repo),
                    )
            absent = os.path.join(tmp, "absent")
            os.makedirs(absent)
            self.assertEqual(gp_common.read_package_scripts(absent), [])
            repo = _package_repo(tmp, package_json='{"scripts": {"e2e": "playwright test"}}')
            self.assertEqual(gp_common.read_package_scripts(repo), [("e2e", "playwright test")])

    def test_runner_matches_original_lockfile_order(self):
        original = load_original(PACKAGE_SCRIPTS)
        cases = [
            ((), "npm"),
            (("pnpm-lock.yaml",), "pnpm"),
            (("yarn.lock",), "yarn"),
            (("bun.lockb",), "bun"),
            (("bun.lock",), "bun"),
            (("pnpm-lock.yaml", "yarn.lock"), "pnpm"),
            (("yarn.lock", "bun.lock"), "yarn"),
        ]
        for lockfiles, expected in cases:
            with self.subTest(lockfiles=lockfiles), tempfile.TemporaryDirectory() as tmp:
                repo = _package_repo(tmp, lockfiles=lockfiles)
                self.assertEqual(gp_common.package_runner(repo), expected)
                self.assertEqual(original.resolve_package_manager_runner(repo), expected)

    def test_scripts_read_from_root_package_json_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            text = json.dumps({"bin": {"x": "y"}, "scripts": {"a": "b"}})
            repo = _package_repo(tmp, package_json=text)
            self.assertEqual(gp_common.read_package_scripts(repo), [("a", "b")])


class TestMachinePath(unittest.TestCase):
    def test_absolute_and_home_relative_paths_are_machine_paths(self):
        for value in ["/etc/passwd", "/var/home/u/x", "~/x"]:
            with self.subTest(value=value):
                self.assertTrue(gp_common.is_machine_path(value, FAKE_HOME))

    def test_windows_drive_path_is_machine_path(self):
        self.assertTrue(gp_common.is_machine_path("C:\\Users\\x", FAKE_HOME))

    def test_value_containing_the_home_is_machine_path(self):
        self.assertTrue(gp_common.is_machine_path(f"see {FAKE_HOME}/notes", FAKE_HOME))

    def test_repo_relative_values_are_not_machine_paths(self):
        values = [".planning/goals/a.md", "tmp/goals", "docs/superpowers/plans/a.md", "make test"]
        for value in values:
            with self.subTest(value=value):
                self.assertFalse(gp_common.is_machine_path(value, FAKE_HOME))


class TestScanText(unittest.TestCase):
    def test_flags_home_sentinel_and_key_shapes(self):
        texts = [
            f"cd {FAKE_HOME}/repo",
            f"token {SENTINEL} here",
            "key sk-" + "a" * 20,
            "gh ghp_" + "b" * 20,
        ]
        for text in texts:
            with self.subTest(text=text):
                problems = gp_common.scan_text(text, home=FAKE_HOME, secrets=[SENTINEL])
                self.assertTrue(problems)
                for problem in problems:
                    self.assertNotIn(SENTINEL, problem)
                    self.assertNotIn(FAKE_HOME, problem)

    def test_slash_commands_and_repo_paths_are_clean(self):
        text = "/goal\n/gsd-autonomous --from 1 --to 2 --converge\n.planning/x.md\n"
        self.assertEqual(gp_common.scan_text(text, home=FAKE_HOME, secrets=[SENTINEL]), [])

    def test_empty_or_one_character_home_never_matches_everything(self):
        text = "plain text with a and b"
        self.assertEqual(gp_common.scan_text(text, home="", secrets=[]), [])
        self.assertEqual(gp_common.scan_text(text, home="a", secrets=[]), [])

    def test_empty_secret_is_ignored(self):
        self.assertEqual(gp_common.scan_text("anything", home=FAKE_HOME, secrets=[""]), [])


class TestSlugAndUnique(unittest.TestCase):
    def test_slugify_collapses_punctuation(self):
        self.assertEqual(gp_common.slugify("Phases 16-27: One Shot!"), "phases-16-27-one-shot")

    def test_slugify_empty_and_long_input(self):
        self.assertEqual(gp_common.slugify(""), "goal")
        self.assertLessEqual(len(gp_common.slugify("x" * 100)), 40)

    def test_unique_path_never_overwrites(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = gp_common.unique_path(tmp, "a.md")
            self.assertEqual(first, os.path.join(tmp, "a.md"))
            Path(first).write_text("one", encoding="utf-8")
            second = gp_common.unique_path(tmp, "a.md")
            self.assertEqual(second, os.path.join(tmp, "a-2.md"))
            Path(second).write_text("two", encoding="utf-8")
            self.assertEqual(gp_common.unique_path(tmp, "a.md"), os.path.join(tmp, "a-3.md"))
            self.assertEqual(Path(first).read_text(encoding="utf-8"), "one")


class TestStripAnsi(unittest.TestCase):
    def test_removes_colour_codes(self):
        self.assertEqual(gp_common.strip_ansi("\x1b[31mred\x1b[0m"), "red")


class TestStdlibOnly(unittest.TestCase):
    def test_imports_are_stdlib_only(self):
        tree = ast.parse(COMMON_PATH.read_text(encoding="utf-8"))
        modules = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.extend(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                modules.append(node.module.split(".")[0])
        self.assertTrue(modules)
        for module in modules:
            with self.subTest(module=module):
                self.assertIn(module, sys.stdlib_module_names)


class TestFixtures(unittest.TestCase):
    def test_opengsd_project_marks_only_the_first_plans_cross_ai(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fx.opengsd_project(root, [fx.phase_spec("16", "Alpha", plans=2, cross_ai=1)])
            phase_dir = root / ".planning" / "phases" / "16-alpha"
            plans = sorted(phase_dir.glob("*-PLAN.md"))
            self.assertEqual(len(plans), 2)
            self.assertIn("cross_ai: true", plans[0].read_text(encoding="utf-8"))
            self.assertNotIn("cross_ai: true", plans[1].read_text(encoding="utf-8"))

    def test_phase_op_json_paths_are_absolute_under_the_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            phases = [fx.phase_spec("16", "Alpha", plans=1), fx.phase_spec("17", "Beta")]
            fx.opengsd_project(root, phases)
            docs = fx.phase_op_json(root, phases)
            self.assertEqual(set(docs), {"16", "17"})
            for doc in docs.values():
                self.assertTrue(os.path.isabs(doc["phase_dir"]))
                self.assertTrue(doc["phase_dir"].startswith(str(root)))
                self.assertTrue(os.path.isabs(doc["state_path"]))
            self.assertTrue(docs["16"]["has_plans"])
            self.assertFalse(docs["17"]["has_plans"])

    def test_roadmap_and_identity_shapes(self):
        phases = [fx.phase_spec("16", "Alpha", plans=2, context=True)]
        roadmap = fx.roadmap_json(phases)
        self.assertEqual(roadmap["phases"][0]["number"], "16")
        self.assertEqual(roadmap["phases"][0]["plan_count"], 2)
        self.assertIs(roadmap["phases"][0]["has_context"], True)
        self.assertEqual(fx.identity_json(True)["packageName"], "@opengsd/gsd-core")
        self.assertEqual(fx.identity_json(False)["packageName"], "get-shit-done-cc")

    def test_plan_text_writes_the_depends_on_line(self):
        self.assertIn("**Depends on:** `b.md`", fx.plan_text("A", "`b.md`"))

    def test_superpowers_project_creates_the_plans_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fx.superpowers_project(root, {"a.md": fx.plan_text("A")})
            self.assertTrue((root / "docs" / "superpowers" / "plans" / "a.md").is_file())

    def test_every_project_kind_builds_in_one_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fx.empty_project(root)
            fx.makefile(root, {"e2e-test": "echo ok"})
            fx.package_json(root, {"e2e": "playwright test"}, lockfile="pnpm-lock.yaml")
            fx.playwright_config(root)
            fx.cypress_config(root)
            fx.pty_driver(root, "tests/test_pty.py")
            fx.git_init(root)
            self.assertTrue((root / "README.md").is_file())
            self.assertIn("e2e-test:", (root / "Makefile").read_text(encoding="utf-8"))
            self.assertTrue((root / "pnpm-lock.yaml").is_file())
            first = (root / "tests" / "test_pty.py").read_text(encoding="utf-8").splitlines()[0]
            self.assertEqual(first, "import pty")


if __name__ == "__main__":
    unittest.main()
