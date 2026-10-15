"""The parallel runner must fail the gate when any module fails."""
import contextlib
import importlib.util
import io
import pathlib
import subprocess
import sys
import tempfile
import unittest
import unittest.mock

RUNNER = pathlib.Path(__file__).resolve().parent.parent / "tools" / "run_unittest_parallel.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("run_unittest_parallel", RUNNER)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {RUNNER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run(*args: str, cwd: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(RUNNER), *args],
                          capture_output=True, text=True, check=False, cwd=cwd)


class RunUnittestParallelTest(unittest.TestCase):
    def test_all_pass_exits_zero(self) -> None:
        proc = run("tests.test_arch")
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("1/1 modules passed", proc.stdout)

    def test_one_failure_exits_nonzero_and_names_it(self) -> None:
        proc = run("tests.test_arch", "tests.no_such_module")
        self.assertEqual(proc.returncode, 1, proc.stdout)
        self.assertIn("failed: tests.no_such_module", proc.stdout)

    def test_no_modules_is_usage_error(self) -> None:
        self.assertEqual(run().returncode, 2)


class WorkerCountTest(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = load_runner()

    def test_share_of_synthetic_cpu_counts(self) -> None:
        counts = [self.runner.worker_count(20, cpus) for cpus in (24, 4, 1, None)]
        self.assertEqual(counts, [9, 1, 1, 1])

    def test_override_can_lower_but_never_raise(self) -> None:
        self.assertEqual(self.runner.worker_count(20, 24, share_env="0.9"), 9)
        self.assertEqual(self.runner.worker_count(20, 24, share_env="0.25"), 6)

    def test_unusable_override_keeps_the_cap(self) -> None:
        for share_env in ("abc", "0", "-1"):
            self.assertEqual(self.runner.worker_count(20, 24, share_env=share_env), 9, share_env)

    def test_never_more_workers_than_modules(self) -> None:
        self.assertEqual(self.runner.worker_count(3, 24), 3)


class AvailableCpusTest(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = load_runner()

    def test_prefers_process_cpu_count(self) -> None:
        with unittest.mock.patch.object(
            self.runner.os, "process_cpu_count", lambda: 7, create=True
        ):
            self.assertEqual(self.runner.available_cpus(), 7)

    def test_falls_back_to_affinity_then_cpu_count(self) -> None:
        with self._without("process_cpu_count"), unittest.mock.patch.object(
            self.runner.os, "sched_getaffinity", lambda _pid: {0, 1, 2}, create=True
        ):
            self.assertEqual(self.runner.available_cpus(), 3)
        with self._without("process_cpu_count"), self._without("sched_getaffinity"), \
                unittest.mock.patch.object(self.runner.os, "cpu_count", lambda: 5):
            self.assertEqual(self.runner.available_cpus(), 5)

    def _without(self, name: str) -> unittest.mock._patch:
        return unittest.mock.patch.object(self.runner.os, name, None, create=True)


class GroupingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = load_runner()

    def test_every_module_in_exactly_one_group(self) -> None:
        discovered = self.runner.discover_modules()
        groups = self.runner.group_modules(discovered)
        assigned = [module for names in groups.values() for module in names]
        self.assertCountEqual(assigned, discovered)
        self.assertEqual(len(assigned), len(set(assigned)))

    def test_unit_excludes_every_explicit_set(self) -> None:
        groups = self.runner.group_modules(self.runner.discover_modules())
        explicit = set().union(*self.runner.EXPLICIT_GROUPS.values())
        self.assertTrue(explicit.isdisjoint(groups["unit"]))


class GroupModeTest(unittest.TestCase):
    def test_arch_group_passes(self) -> None:
        proc = run("--group", "arch")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("1/1 modules passed", proc.stdout)

    def test_unknown_group_is_usage_error(self) -> None:
        self.assertEqual(run("--group", "nope").returncode, 2)

    def test_mixing_group_and_module_names_is_usage_error(self) -> None:
        self.assertEqual(run("--group", "arch", "tests.test_arch").returncode, 2)

    def test_module_with_no_tests_fails_its_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tests_dir = pathlib.Path(tmp) / "tests"
            tests_dir.mkdir()
            (tests_dir / "__init__.py").write_text("")
            (tests_dir / "test_empty.py").write_text("# no TestCase in here\n")
            _, rc, output, _ = load_runner().run_module("tests.test_empty", cwd=pathlib.Path(tmp))
        self.assertNotEqual(rc, 0, output)
        self.assertIn("NO TESTS RAN", output)

    def test_runs_from_a_foreign_cwd(self) -> None:
        # Modules resolve against the repo root, not the caller's cwd (C-WR-07).
        with tempfile.TemporaryDirectory() as tmp:
            proc = run("--group", "arch", cwd=tmp)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("1/1 modules passed", proc.stdout)

    def test_a_hung_module_fails_with_a_timeout_line(self) -> None:
        runner = load_runner()
        with unittest.mock.patch.object(runner, "MODULE_TIMEOUT_SECS", 0.01):
            _, rc, output, _ = runner.run_module("tests.test_arch")
        self.assertEqual(rc, 124)
        self.assertIn("timed out", output)

    def test_stale_exception_name_exits_2(self) -> None:
        runner = load_runner()
        stale = runner.EXPLICIT_GROUPS["arch"] | {"tests.test_does_not_exist"}
        err = io.StringIO()
        with unittest.mock.patch.dict(runner.EXPLICIT_GROUPS, {"arch": stale}), \
                contextlib.redirect_stderr(err):
            rc = runner.main(["--group", "arch"])
        self.assertEqual(rc, 2)
        self.assertIn("tests.test_does_not_exist", err.getvalue())


if __name__ == "__main__":
    unittest.main()
