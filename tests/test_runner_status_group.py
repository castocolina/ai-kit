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
CHECK_KEYS = ("coverage", "findings")


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

    def test_check_group_follows_escalate(self):
        with tempfile.TemporaryDirectory() as tmp:
            line = last_status(self.node, tmp, ["--runtime", "pi", "--model", "fake/ok"])
            status = parse_status_line(line)
            assert status is not None
            keys = list(status)
            pos = keys.index("escalate") + 1
            self.assertEqual(keys[pos:pos + len(CHECK_KEYS)], list(CHECK_KEYS))
            self.assertEqual(status["coverage"], "-")
            self.assertEqual(status["findings"], "-")
            self.assertTrue(line.endswith(" escalate=- coverage=- findings=-"))

    def test_trailer_counts_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            line = last_status(self.node, tmp, ["--runtime", "pi", "--model", "fake/ok"])
            status = parse_status_line(line)
            self.assertIsNotNone(status)
            assert status is not None
            spec = RunnerSpec("pi", "fake/ok", "exec", 0)
            # --print-argv names no lane, so its line counts only through the "-" fallback.
            self.assertEqual((status["cli"], status["model"]), ("-", "-"))
            self.assertTrue(_trailer_counts(status, spec, 0))
            self.assertFalse(_trailer_counts(status, spec, 1))
            # A named lane must match this run's runtime and model; the group keys change nothing.
            named = {**status, "cli": "pi", "model": "fake/ok"}
            self.assertTrue(_trailer_counts(named, spec, 0))
            self.assertFalse(_trailer_counts({**named, "cli": "codex"}, spec, 0))
            self.assertFalse(_trailer_counts({**named, "model": "fake/other"}, spec, 0))

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


class TestCheckGroupLine(unittest.TestCase):
    def test_findings_parse_and_trailer_counts(self):
        line = (
            "AIKIT-XAI status=partial cli=pi model=fake/ok exit=1 cli_rc=0 elapsed=3s out=10 "
            "tree=dirty action=stop route=unknown rule=- pattern=none attempts=1 cycles=0 "
            "session=- applied=model ignored=- unknown=- escalate=- coverage=1/3 "
            "findings=task_uncovered,outside_plan_files"
        )
        status = parse_status_line(line)
        assert status is not None
        self.assertEqual(status["coverage"], "1/3")
        self.assertEqual(status["findings"].split(","), ["task_uncovered", "outside_plan_files"])
        spec = RunnerSpec("pi", "fake/ok", "exec", 0)
        self.assertTrue(_trailer_counts(status, spec, 1))
        self.assertFalse(_trailer_counts(status, spec, 0))

    def test_group_sits_before_retry(self):
        line = (
            "AIKIT-XAI status=transient cli=pi model=fake/ok exit=75 cli_rc=1 elapsed=3s out=0 "
            "tree=clean action=stop route=unknown rule=- pattern=none attempts=1 cycles=0 "
            "session=- applied=model ignored=- unknown=- escalate=- coverage=- findings=- "
            "retry_after_s=600 cycle=0"
        )
        status = parse_status_line(line)
        assert status is not None
        self.assertEqual(status["retry_after_s"], "600")
        self.assertEqual(status["coverage"], "-")
        keys = list(status)
        self.assertEqual(keys.index("findings") + 1, keys.index("retry_after_s"))


if __name__ == "__main__":
    unittest.main()
