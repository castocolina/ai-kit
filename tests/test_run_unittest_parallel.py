"""The parallel runner must fail the gate when any module fails."""
import pathlib
import subprocess
import sys
import unittest

RUNNER = pathlib.Path(__file__).resolve().parent.parent / "tools" / "run_unittest_parallel.py"


def run(*modules: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(RUNNER), *modules],
                          capture_output=True, text=True, check=False)


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


if __name__ == "__main__":
    unittest.main()
