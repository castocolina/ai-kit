"""37-06: the status line's settings group parses with runner_dispatch's own readers (SPEC R2, R10)."""  # noqa: E501

import os
import subprocess
import sys
import tempfile
import unittest

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review"))

from ai_kit_spec.runner_dispatch import RunnerSpec, _trailer_counts, parse_status_line

from tests.cross_ai_selftest import TEMPLATE, _real_node_executable, runner_env

GROUP_KEYS = ("session", "applied", "ignored", "unknown", "escalate")


def last_status(node: str, tmp: str, args: list[str]) -> str:
    proc = subprocess.run(
        [node, TEMPLATE, "--print-argv", *args], cwd=tmp, env=runner_env(tmp),
        capture_output=True, text=True, timeout=60, check=False,
    )
    return [line for line in proc.stderr.splitlines() if line.strip()][-1]


class TestStatusGroup(unittest.TestCase):
    def setUp(self):
        node = _real_node_executable()
        if node is None:
            self.skipTest("no real node executable on PATH")
            return
        self.node = node

    def test_group_keys_follow_cycles(self):
        with tempfile.TemporaryDirectory() as tmp:
            line = last_status(self.node, tmp, ["--runtime", "pi", "--model", "fake/ok"])
            status = parse_status_line(line)
            self.assertIsNotNone(status)
            assert status is not None
            keys = list(status)
            pos = keys.index("cycles") + 1
            self.assertEqual(keys[pos:pos + len(GROUP_KEYS)], list(GROUP_KEYS))
            self.assertTrue(all("=" in token for token in line.split()[1:]))
            self.assertEqual(status["escalate"], "-")
            self.assertTrue({"model", "role"}.issubset(status["applied"].split(",")))

    def test_trailer_counts_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            line = last_status(self.node, tmp, ["--runtime", "pi", "--model", "fake/ok"])
            status = parse_status_line(line)
            self.assertIsNotNone(status)
            assert status is not None
            spec = RunnerSpec("pi", "fake/ok", "exec", 0)
            self.assertTrue(_trailer_counts(status, spec, 0))
            self.assertFalse(_trailer_counts(status, spec, 1))

    def test_escalation_echo_parses(self):
        with tempfile.TemporaryDirectory() as tmp:
            line = last_status(self.node, tmp, [
                "--runtime", "pi", "--model", "fake/ok", "--escalate-runtime", "--escalate-model",
            ])
            status = parse_status_line(line)
            self.assertIsNotNone(status)
            assert status is not None
            self.assertEqual(status["escalate"], "runtime,model")
            self.assertTrue(
                {"escalate_runtime", "escalate_model"}.issubset(status["ignored"].split(","))
            )


if __name__ == "__main__":
    unittest.main()
