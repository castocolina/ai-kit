"""Unit tests of the push timing tool (tools/time_prepush.py, SPEC R3; D-14).

No test runs a real hook. `run_hook` is exercised with a trivial child that prints the summary
line the runner prints, over synthetic report folders; `main` is exercised with `run_hook`
replaced by canned results.
"""

import contextlib
import importlib.util
import io
import json
import os
import pathlib
import sys
import tempfile
import unittest
import unittest.mock

REPO = pathlib.Path(__file__).resolve().parent.parent
TIMING = REPO / "tools" / "time_prepush.py"


def load_timing():
    spec = importlib.util.spec_from_file_location("time_prepush", TIMING)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {TIMING}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def child(summary: str, rc: int = 0) -> list[str]:
    """A child process that prints the runner's summary line and exits with rc."""
    return [sys.executable, "-c", f"print({summary!r}); raise SystemExit({rc})"]


def write_report(folder: pathlib.Path, module: str, ran: int = 1, skips=(), rc: int = 0,
                 name: str | None = None) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    data = {"module": module, "rc": rc, "skips": list(skips), "ran": ran}
    (folder / (name or f"{module}.json")).write_text(json.dumps(data), encoding="utf-8")


class TestMatrixHelper(unittest.TestCase):
    def test_the_matrix_helper_is_loaded_from_tools_env_matrix_py(self) -> None:
        # Names tools/env_matrix.py so the staged mapper selects this module for that file.
        module = load_timing().env_matrix
        self.assertEqual(pathlib.Path(module.__file__), REPO / "tools" / "env_matrix.py")


class TestVerdict(unittest.TestCase):
    def setUp(self) -> None:
        self.t = load_timing()

    def run_of(self, secs: float, *, rc: int = 0, passed: int = 2, total: int = 2,
               problems: tuple[str, ...] = (), skipped: int = 0):
        return self.t.HookRun("hook", rc, secs, passed, total, problems, skipped)

    def test_sixty_seconds_in_total_passes(self) -> None:
        verdict, total = self.t.verdict(self.run_of(30.0), self.run_of(30.0))
        self.assertEqual((verdict, total), ("pass", 60.0))

    def test_sixty_point_one_fails(self) -> None:
        verdict, _ = self.t.verdict(self.run_of(30.0), self.run_of(30.1))
        self.assertEqual(verdict, "fail")

    def test_sixty_point_zero_one_fails_on_the_unrounded_total(self) -> None:
        verdict, total = self.t.verdict(self.run_of(30.0), self.run_of(30.01))
        self.assertEqual(verdict, "fail")
        self.assertGreater(total, 60.0)

    def test_a_nonzero_rc_is_invalid_whatever_the_time(self) -> None:
        verdict, _ = self.t.verdict(self.run_of(1.0, rc=1), self.run_of(1.0))
        self.assertEqual(verdict, "invalid")

    def test_passed_below_total_is_invalid(self) -> None:
        verdict, _ = self.t.verdict(self.run_of(1.0, passed=1, total=2), self.run_of(1.0))
        self.assertEqual(verdict, "invalid")

    def test_total_zero_is_invalid(self) -> None:
        verdict, _ = self.t.verdict(self.run_of(1.0, passed=0, total=0), self.run_of(1.0))
        self.assertEqual(verdict, "invalid")

    def test_any_problem_is_invalid(self) -> None:
        bad = self.run_of(1.0, problems=("no report for tests.test_a",))
        verdict, _ = self.t.verdict(bad, self.run_of(1.0))
        self.assertEqual(verdict, "invalid")

    def test_a_custom_limit_is_used(self) -> None:
        verdict, _ = self.t.verdict(self.run_of(1.0), self.run_of(1.0), limit=1.5)
        self.assertEqual(verdict, "fail")


class TestRunHookReports(unittest.TestCase):
    """run_hook over synthetic report folders; the child only prints a summary line."""

    def setUp(self) -> None:
        self.t = load_timing()
        self.temp = tempfile.TemporaryDirectory(prefix="time-prepush-test-")
        self.addCleanup(self.temp.cleanup)
        self.folder = pathlib.Path(self.temp.name) / "reports"
        self.expected = {"tests.test_a", "tests.test_b"}

    def run_with(self, summary: str, rc: int = 0):
        env = dict(os.environ)
        env[self.t.runner.REPORT_DIR_ENV] = str(self.folder)
        with contextlib.redirect_stdout(io.StringIO()):
            return self.t.run_hook("unittest", child(summary, rc), env, self.expected)

    def test_a_complete_green_run_has_no_problem(self) -> None:
        write_report(self.folder, "tests.test_a", ran=2, skips=("needs mmdc",))
        write_report(self.folder, "tests.test_b", ran=1)
        run = self.run_with("2/2 modules passed")
        self.assertEqual(run.problems, ())
        self.assertEqual((run.passed, run.total, run.skipped), (2, 2, 1))

    def test_a_missing_report_is_a_problem(self) -> None:
        write_report(self.folder, "tests.test_a")
        run = self.run_with("2/2 modules passed")
        self.assertIn("no report for tests.test_b", " ".join(run.problems))

    def test_an_unexpected_report_is_a_problem(self) -> None:
        write_report(self.folder, "tests.test_a")
        write_report(self.folder, "tests.test_b")
        write_report(self.folder, "tests.test_c")
        run = self.run_with("3/3 modules passed")
        self.assertIn("unexpected report for tests.test_c", " ".join(run.problems))

    def test_a_duplicate_report_is_a_problem(self) -> None:
        write_report(self.folder, "tests.test_a")
        write_report(self.folder, "tests.test_a", name="tests.test_a.2.json")
        write_report(self.folder, "tests.test_b")
        run = self.run_with("2/2 modules passed")
        self.assertIn("duplicate report: tests.test_a", " ".join(run.problems))

    def test_a_failing_module_is_a_problem(self) -> None:
        write_report(self.folder, "tests.test_a", rc=1)
        write_report(self.folder, "tests.test_b")
        run = self.run_with("1/2 modules passed", rc=1)
        self.assertIn("failing module: tests.test_a", " ".join(run.problems))
        self.assertEqual(self.t.verdict(run, run)[0], "invalid")

    def test_a_total_that_differs_from_the_inventory_is_a_problem(self) -> None:
        write_report(self.folder, "tests.test_a")
        write_report(self.folder, "tests.test_b")
        run = self.run_with("2/3 modules passed")
        self.assertIn("total mismatch", " ".join(run.problems))

    def test_a_module_with_no_test_run_is_all_skipped(self) -> None:
        write_report(self.folder, "tests.test_a", ran=0, skips=("class skipped in setUpClass",))
        write_report(self.folder, "tests.test_b")
        run = self.run_with("2/2 modules passed")
        self.assertIn("all skipped: tests.test_a", " ".join(run.problems))

    def test_a_module_whose_every_test_skipped_is_all_skipped(self) -> None:
        write_report(self.folder, "tests.test_a", ran=3, skips=("a", "b", "c"))
        write_report(self.folder, "tests.test_b")
        run = self.run_with("2/2 modules passed")
        self.assertIn("all skipped: tests.test_a", " ".join(run.problems))

    def test_a_module_with_some_named_skips_stays_valid(self) -> None:
        write_report(self.folder, "tests.test_a", ran=3, skips=("needs mmdc",))
        write_report(self.folder, "tests.test_b", ran=2)
        run = self.run_with("2/2 modules passed")
        self.assertEqual(run.problems, ())
        self.assertEqual(run.skipped, 1)

    def test_an_all_skip_ok_entry_is_not_a_problem(self) -> None:
        write_report(self.folder, "tests.test_a", ran=0, skips=("by design",))
        write_report(self.folder, "tests.test_b")
        with unittest.mock.patch.dict(self.t.ALL_SKIP_OK, {"tests.test_a": "by design"}):
            run = self.run_with("2/2 modules passed")
        self.assertEqual(run.problems, ())

    def test_a_nonzero_hook_rc_is_a_problem_even_with_clean_reports(self) -> None:
        write_report(self.folder, "tests.test_a")
        write_report(self.folder, "tests.test_b")
        run = self.run_with("2/2 modules passed", rc=3)
        self.assertIn("unittest exited 3", " ".join(run.problems))


class TestAllSkipOk(unittest.TestCase):
    def setUp(self) -> None:
        self.t = load_timing()

    def test_all_skip_ok_entries_are_listed(self) -> None:
        groups = self.t.runner.hook_groups()
        inventory = set(groups["unittest"]) | set(groups["unittest-wizard"])
        self.assertEqual(self.t.stale_all_skip_ok(inventory), [])

    def test_a_stale_entry_is_reported(self) -> None:
        entries = {"tests.test_gone": "not in any hook"}
        with unittest.mock.patch.dict(self.t.ALL_SKIP_OK, entries):
            self.assertEqual(self.t.stale_all_skip_ok(set()), ["tests.test_gone"])


class TestHookCommand(unittest.TestCase):
    def setUp(self) -> None:
        self.t = load_timing()
        self.config = (REPO / ".pre-commit-config.yaml").read_text(encoding="utf-8")

    def test_the_six_hook_commands_come_from_the_config(self) -> None:
        expected = {
            "unittest": ["python3", "tools/run_unittest_parallel.py", "--group", "unit",
                         "--group", "arch"],
            "unittest-wizard": ["uv", "run", "python", "tools/run_unittest_parallel.py",
                                "--group", "unit-uv", "--group", "integration"],
            "pyright": ["uv", "run", "pyright"],
            "vulture": ["uv", "run", "vulture"],
            "check-dogfood": ["python3", "tools/check_dogfood.py"],
            "deferred-e2e": ["python3", "tools/run_unittest_parallel.py", "--pushed"],
        }
        for hook_id, argv in expected.items():
            with self.subTest(hook=hook_id):
                self.assertEqual(self.t.hook_command(self.config, hook_id), argv)

    def test_an_unknown_hook_is_an_error(self) -> None:
        with self.assertRaises(ValueError):
            self.t.hook_command(self.config, "no-such-hook")


class TestHookEnv(unittest.TestCase):
    def setUp(self) -> None:
        self.t = load_timing()
        self.temp = tempfile.TemporaryDirectory(prefix="time-prepush-env-")
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)

    def test_the_timing_env_drops_the_share_and_the_push_refs(self) -> None:
        source = {"HOME": str(self.root), "PATH": "/usr/bin",
                  "AI_KIT_TEST_CPU_SHARE": "0.10", "PRE_COMMIT_FROM_REF": "a",
                  "PRE_COMMIT_TO_REF": "b", self.t.runner.REPORT_DIR_ENV: "/inherited"}
        env = self.t.hook_env(source, self.root / "fresh", None)
        for name in ("AI_KIT_TEST_CPU_SHARE", "PRE_COMMIT_FROM_REF", "PRE_COMMIT_TO_REF",
                     self.t.runner.REPORT_DIR_ENV):
            self.assertNotIn(name, env)
        self.assertEqual(env["HOME"], str(self.root / "fresh"))
        self.assertEqual(env["AI_KIT_REFUSE_REAL_HOME"], "1")

    def test_a_test_hook_gets_its_own_report_folder(self) -> None:
        env = self.t.hook_env({"HOME": str(self.root)}, self.root / "fresh",
                              self.root / "reports")
        self.assertEqual(env[self.t.runner.REPORT_DIR_ENV], str(self.root / "reports"))

    def test_the_caller_volta_home_is_forwarded_from_the_caller_home(self) -> None:
        caller = self.root / "caller"
        (caller / ".volta").mkdir(parents=True)
        env = self.t.hook_env({"HOME": str(caller), "PATH": "/usr/bin"},
                              self.root / "fresh", None)
        self.assertEqual(env["VOLTA_HOME"], os.path.join(str(caller), ".volta"))


class TestMain(unittest.TestCase):
    def setUp(self) -> None:
        self.t = load_timing()

    def fake_runs(self, aux_rc: dict[str, int] | None = None, core_secs: float = 1.0):
        aux_rc = aux_rc or {}

        def fake(name, argv, env, expected=None):
            if expected is not None:
                total = len(expected)
                return self.t.HookRun(name, 0, core_secs, total, total, (), 0)
            return self.t.HookRun(name, aux_rc.get(name, 0), 0.5, 0, 0, (), 0)

        return fake

    def run_main(self, fake) -> tuple[int, str]:
        out = io.StringIO()
        with unittest.mock.patch.object(self.t, "run_hook", side_effect=fake), \
                contextlib.redirect_stdout(out):
            code = self.t.main([])
        return code, out.getvalue()

    def test_a_pass_with_every_auxiliary_hook_green_exits_zero(self) -> None:
        code, out = self.run_main(self.fake_runs())
        self.assertEqual(code, 0)
        self.assertIn("verdict=pass", out)
        self.assertNotIn("auxiliary hooks failed", out)

    def test_a_pass_with_a_failed_deferred_e2e_exits_one(self) -> None:
        code, out = self.run_main(self.fake_runs({"deferred-e2e": 1}))
        self.assertEqual(code, 1)
        self.assertIn("verdict=pass", out)
        self.assertIn("auxiliary hooks failed: deferred-e2e", out)

    def test_a_fail_verdict_exits_one_whatever_the_auxiliary_hooks_did(self) -> None:
        code, out = self.run_main(self.fake_runs(core_secs=40.0))
        self.assertEqual(code, 1)
        self.assertIn("verdict=fail", out)
        self.assertNotIn("auxiliary hooks failed", out)

    def test_the_record_line_carries_the_six_hook_times(self) -> None:
        _, out = self.run_main(self.fake_runs())
        record = next(line for line in out.splitlines() if line.startswith("push-timing"))
        for part in ("core=", "wizard=", "test-hooks=", "pyright=", "vulture=", "dogfood=",
                     "deferred-e2e=", "push-worst=", "verdict=pass"):
            self.assertIn(part, record)

    def test_usage_on_an_argument(self) -> None:
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(self.t.main(["--fast"]), 2)


if __name__ == "__main__":
    unittest.main()
