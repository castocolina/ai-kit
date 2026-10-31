"""Tests for skills/ai-kit-spec-goal-prompt/scripts/gp_e2e.py (plan 27-04, GPS-03).

Every project is a temp directory built with tests/goal_prompt_fixtures.py, except the dogfood
test, which reads this repository's own Makefile read-only. Detection never executes anything:
no subprocess, no network, no write into the project.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "skills" / "ai-kit-spec-goal-prompt" / "scripts"
sys.path.insert(0, str(SCRIPTS))
import gp_e2e

from tests import goal_prompt_fixtures as fx


class _Project(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def detect(self):
        return gp_e2e.detect_e2e(str(self.root))

    def commands(self):
        return [entry["command"] for entry in self.detect()["commands"]]


class TestSignals(_Project):
    def test_makefile_e2e_targets_listed_in_declaration_order(self):
        fx.makefile(self.root, {"test": "x", "e2e": "x", "e2e-test": "x", "e2e-docker": "x"})
        self.assertEqual(
            self.detect()["commands"],
            [
                {"command": "make e2e", "source": "Makefile:e2e", "kind": "make",
                 "confidence": "detected"},
                {"command": "make e2e-test", "source": "Makefile:e2e-test", "kind": "make",
                 "confidence": "detected"},
                {"command": "make e2e-docker", "source": "Makefile:e2e-docker", "kind": "make",
                 "confidence": "detected"},
            ],
        )

    def test_end2end_and_similar_names_are_not_e2e(self):
        fx.makefile(self.root, {"end2end": "x", "my-e2e-test": "x", "e2elike": "x"})
        self.assertEqual(self.commands(), [])

    def test_package_scripts_use_the_lockfile_runner_and_never_copy_the_body(self):
        scripts = {"e2e": "rm -rf / && x", "e2e:smoke": "x", "smoke:e2e": "x",
                   "ui": "playwright test", "lint": "eslint ."}
        fx.package_json(self.root, scripts, lockfile="pnpm-lock.yaml")
        self.assertEqual(
            self.commands(),
            ["pnpm run e2e", "pnpm run e2e:smoke", "pnpm run smoke:e2e", "pnpm run ui"],
        )
        self.assertTrue(all(e["kind"] == "package" for e in self.detect()["commands"]))

    def test_lint_script_is_a_gate_not_an_e2e_command(self):
        fx.package_json(self.root, {"lint": "eslint .", "test": "vitest"},
                        lockfile="pnpm-lock.yaml")
        result = self.detect()
        self.assertEqual(result["commands"], [])
        self.assertIn("pnpm run lint", result["gates"])
        self.assertTrue(result["none"])

    def test_playwright_config_alone_gives_npx_playwright(self):
        fx.playwright_config(self.root)
        self.assertEqual(
            self.detect()["commands"],
            [{"command": "npx playwright test", "source": "playwright.config.*",
              "kind": "playwright", "confidence": "detected"}],
        )

    def test_playwright_runner_follows_the_lockfile(self):
        cases = [
            ("pnpm-lock.yaml", "pnpm exec playwright test"),
            ("yarn.lock", "yarn playwright test"),
            ("bun.lock", "bunx playwright test"),
            (None, "npx playwright test"),
        ]
        for lockfile, expected in cases:
            with self.subTest(lockfile=lockfile), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                fx.playwright_config(root)
                if lockfile:
                    fx.write(root, lockfile, "")
                commands = gp_e2e.detect_e2e(str(root))["commands"]
                self.assertEqual([entry["command"] for entry in commands], [expected])

    def test_cypress_config_gives_npx_cypress_run(self):
        fx.cypress_config(self.root)
        self.assertEqual(
            self.detect()["commands"],
            [{"command": "npx cypress run", "source": "cypress.config.*",
              "kind": "cypress", "confidence": "detected"}],
        )

    def test_browser_config_is_not_duplicated_by_a_package_script_running_it(self):
        fx.package_json(self.root, {"ui": "playwright test"})
        fx.playwright_config(self.root)
        self.assertEqual([entry["kind"] for entry in self.detect()["commands"]], ["package"])

    def test_empty_project_has_no_signal(self):
        fx.empty_project(self.root)
        self.assertEqual(self.detect(), {"commands": [], "gates": [], "none": True})

    def test_gates_use_a_fixed_order_and_never_include_e2e(self):
        fx.makefile(self.root, {"validate": "x", "e2e": "x", "lint": "x", "test": "x",
                                "test-unit": "x"})
        self.assertEqual(
            self.detect()["gates"],
            ["make test", "make lint", "make validate", "make test-unit"],
        )

    def test_package_gates_apply_only_when_the_makefile_has_none(self):
        fx.makefile(self.root, {"build": "x"})
        fx.package_json(self.root, {"test": "x", "lint": "y"}, lockfile="yarn.lock")
        self.assertEqual(self.detect()["gates"], ["yarn run test", "yarn run lint"])

    def test_makefile_gates_win_over_package_gates(self):
        fx.makefile(self.root, {"test": "x"})
        fx.package_json(self.root, {"lint": "y"})
        self.assertEqual(self.detect()["gates"], ["make test"])

    def test_script_names_with_shell_metacharacters_are_skipped(self):
        fx.package_json(self.root, {"e2e;rm -rf x": "playwright test", "e2e": "x"})
        self.assertEqual(self.commands(), ["npm run e2e"])

    def test_every_value_is_a_plain_string(self):
        fx.makefile(self.root, {"e2e": "x"})
        fx.package_json(self.root, {"e2e": "x", "lint": "y"}, lockfile="bun.lockb")
        fx.playwright_config(self.root)
        result = self.detect()
        for entry in result["commands"]:
            for value in entry.values():
                self.assertIsInstance(value, str)
        for gate in result["gates"]:
            self.assertIsInstance(gate, str)
        json.dumps(result)

    def test_none_is_false_once_any_signal_exists(self):
        fx.makefile(self.root, {"e2e": "x"})
        self.assertIs(self.detect()["none"], False)


class TestPtyAndMarkers(_Project):
    def test_unmapped_unittest_pty_driver_is_inferred(self):
        fx.pty_driver(self.root, "tests/test_wiz.py", "pty")
        self.assertEqual(
            self.detect()["commands"],
            [{"command": "python3 -m unittest tests.test_wiz", "kind": "pty",
              "confidence": "inferred", "source": "PTY driver tests/test_wiz.py"}],
        )

    def test_pexpect_and_ptyprocess_imports_are_drivers(self):
        fx.write(self.root, "tests/test_a.py", "import pexpect\n")
        fx.write(self.root, "tests/test_b.py", "from ptyprocess import PtyProcess\n")
        self.assertEqual(
            self.commands(),
            ["python3 -m unittest tests.test_a", "python3 -m unittest tests.test_b"],
        )

    def test_a_mention_in_a_comment_or_string_is_not_a_driver(self):
        fx.write(self.root, "tests/test_c.py", '# import pty\nx = "import pexpect"\n')
        self.assertEqual(self.commands(), [])

    def test_textual_pilot_file_is_not_a_driver(self):
        fx.write(self.root, "tests/test_d.py",
                 "from textual.pilot import Pilot\nimport pty\n")
        self.assertEqual(self.commands(), [])

    def test_driver_named_by_an_e2e_target_gains_driver_key_without_a_duplicate(self):
        fx.makefile(self.root, {"e2e-pty": "python3 -m unittest tests.test_wiz"})
        fx.pty_driver(self.root, "tests/test_wiz.py")
        self.assertEqual(
            self.detect()["commands"],
            [{"command": "make e2e-pty", "source": "Makefile:e2e-pty", "kind": "make",
              "confidence": "detected", "driver": "tests/test_wiz.py"}],
        )

    def test_driver_named_by_its_basename_is_mapped(self):
        fx.makefile(self.root, {"e2e-pty": "cd tests && python3 test_wiz.py"})
        fx.pty_driver(self.root, "tests/test_wiz.py")
        entries = self.detect()["commands"]
        self.assertEqual([entry["command"] for entry in entries], ["make e2e-pty"])
        self.assertEqual(entries[0]["driver"], "tests/test_wiz.py")

    def test_driver_named_only_by_a_non_e2e_target_stays_inferred(self):
        fx.makefile(self.root, {"test-integration": "python3 -m unittest tests.test_wiz",
                                "e2e-docker": "x"})
        fx.pty_driver(self.root, "tests/test_wiz.py")
        entries = self.detect()["commands"]
        self.assertEqual(entries[0]["command"], "make e2e-docker")
        self.assertNotIn("driver", entries[0])
        self.assertEqual(entries[1]["confidence"], "inferred")

    def test_node_pty_driver_is_inferred_as_a_node_command(self):
        fx.write(self.root, "tests/e2e/run.mjs", "import pty from 'node-pty';\n")
        self.assertEqual(
            self.detect()["commands"],
            [{"command": "node tests/e2e/run.mjs", "kind": "pty", "confidence": "inferred",
              "source": "PTY driver tests/e2e/run.mjs"}],
        )

    def test_driver_file_over_200_kilobytes_is_skipped(self):
        fx.write(self.root, "tests/test_big.py", "import pty\n" + "x = 1\n" * 40000)
        self.assertEqual(self.commands(), [])

    def test_only_the_first_80_lines_are_read(self):
        fx.write(self.root, "tests/test_late.py", "x = 1\n" * 80 + "import pty\n")
        self.assertEqual(self.commands(), [])

    def test_symlinked_driver_is_not_followed(self):
        with tempfile.TemporaryDirectory() as outside:
            target = Path(outside) / "outside.py"
            target.write_text("import pty\n", encoding="utf-8")
            (self.root / "tests").mkdir()
            (self.root / "tests" / "link.py").symlink_to(target)
            self.assertEqual(self.commands(), [])

    def test_zero_test_marker_table_labels_each_runner(self):
        verified = {row["runner"] for row in gp_e2e.ZERO_TEST_MARKERS if row["verified"]}
        unverified = {row["runner"] for row in gp_e2e.ZERO_TEST_MARKERS if not row["verified"]}
        self.assertEqual(verified, {"unittest", "node --test", "go test", "shell harness"})
        self.assertEqual(unverified, {"pytest", "jest", "vitest", "playwright", "cypress",
                                      "cargo"})
        for row in gp_e2e.ZERO_TEST_MARKERS:
            self.assertEqual(set(row), {"runner", "exit_code", "marker", "verified"})

    def test_markers_for_text_finds_the_matching_runner_only(self):
        def runners(text):
            return [row["runner"] for row in gp_e2e.markers_for_text(text)]

        self.assertEqual(runners("python3 -m unittest discover"), ["unittest"])
        self.assertEqual(runners("go test ./..."), ["go test"])
        self.assertEqual(runners("npx playwright test"), ["playwright"])
        self.assertEqual(runners("echo hi"), [])

    def test_dogfood_finds_this_repositorys_own_e2e_targets(self):
        result = gp_e2e.detect_e2e(str(REPO))
        commands = [entry["command"] for entry in result["commands"]]
        self.assertIn("make e2e-test", commands)
        self.assertIn("make e2e-docker", commands)
        self.assertIs(result["none"], False)

    def test_result_text_carries_no_absolute_path(self):
        fx.makefile(self.root, {"e2e-pty": "python3 -m unittest tests.test_wiz"})
        fx.pty_driver(self.root, "tests/test_wiz.py")
        fx.pty_driver(self.root, "tests/test_other.py")
        self.assertNotIn(str(self.root), json.dumps(self.detect()))
        self.assertNotIn(str(REPO), json.dumps(gp_e2e.detect_e2e(str(REPO))))


if __name__ == "__main__":
    unittest.main()
