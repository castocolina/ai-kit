"""37-10: claude's execute and resume formulas, the byte-equal review argv and the unverified label (SPEC R6)."""  # noqa: E501

import json
import os
import re
import subprocess
import tempfile
import unittest

from tests.cross_ai_selftest import TEMPLATE, _real_node_executable, runner_env

REVIEW_GOLDEN = ["-p", "--model", "fake-ok", "--output-format", "json", "--permission-mode", "plan"]
EXEC_GOLDEN = ["-p", "--model", "fake-ok", "--output-format", "json", "--permission-mode", "bypassPermissions"]  # noqa: E501
NOTE = "cross-ai: note: claude execute formula is unverified (no live probe record)"
RECORD_RE = re.compile(r"^const CLAUDE_EXEC_FORMULA_RECORD = (null|'[^'\n]*');$", re.M)
BASE = ["--runtime", "claude", "--model", "fake-ok"]


def run_print_argv(
    node: str, template: str, tmp: str, args: list[str]
) -> subprocess.CompletedProcess:
    return subprocess.run([node, template, "--print-argv", *args], cwd=tmp, env=runner_env(tmp),
                          capture_output=True, text=True, timeout=60, check=False)


def argv_of(proc):
    return json.loads(proc.stdout.splitlines()[0].split("\t")[2])


def rung1_of(proc):
    prefix = "cross-ai: rung1 claude argv="
    return json.loads(next(line[len(prefix):] for line in proc.stderr.splitlines()
                           if line.startswith(prefix)))


class TestClaudeArgv(unittest.TestCase):
    def setUp(self):
        node = _real_node_executable()
        if node is None:
            self.skipTest("no real node executable on PATH")
        assert node is not None
        self.node = node

    def test_review_argv_is_byte_equal(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = run_print_argv(self.node, TEMPLATE, tmp, [*BASE, "--role", "review"])
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(argv_of(proc), REVIEW_GOLDEN)

    def test_execute_argv_golden(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = run_print_argv(self.node, TEMPLATE, tmp, [*BASE, "--role", "execute"])
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(argv_of(proc), EXEC_GOLDEN)

    def test_resume_argv_on_rung1(self):
        with tempfile.TemporaryDirectory() as tmp:
            proc = run_print_argv(self.node, TEMPLATE, tmp, [*BASE, "--role", "execute"])
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(rung1_of(proc), [*EXEC_GOLDEN, "--resume", "<sid>"])

    def test_settings_follow_the_permission_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            review = run_print_argv(
                self.node, TEMPLATE, tmp, [*BASE, "--role", "review", "--effort", "high"])
            execute = run_print_argv(
                self.node, TEMPLATE, tmp, [*BASE, "--role", "execute", "--effort", "high"])
            self.assertEqual(review.returncode, 0, review.stderr)
            self.assertEqual(execute.returncode, 0, execute.stderr)
            tail = argv_of(execute)[len(EXEC_GOLDEN):]
            self.assertEqual(tail, argv_of(review)[len(REVIEW_GOLDEN):])
            self.assertIn("--effort", tail)


class TestClaudeExecLabel(unittest.TestCase):
    def setUp(self):
        node = _real_node_executable()
        if node is None:
            self.skipTest("no real node executable on PATH")
        assert node is not None
        self.node = node

    def test_note_follows_the_record(self):
        with open(TEMPLATE, encoding="utf-8") as source:
            match = RECORD_RE.search(source.read())
        self.assertIsNotNone(match)
        assert match is not None
        with tempfile.TemporaryDirectory() as tmp:
            execute = run_print_argv(self.node, TEMPLATE, tmp, [*BASE, "--role", "execute"])
            review = run_print_argv(self.node, TEMPLATE, tmp, [*BASE, "--role", "review"])
            self.assertEqual(execute.returncode, 0, execute.stderr)
            self.assertEqual(review.returncode, 0, review.stderr)
            self.assertEqual(NOTE in execute.stderr, match.group(1) == "null")
            self.assertNotIn(NOTE, review.stderr)

    def test_doctored_record_flips_the_note(self):
        with open(TEMPLATE, encoding="utf-8") as source:
            text = source.read()
        match = RECORD_RE.search(text)
        self.assertIsNotNone(match)
        assert match is not None
        value = "'2026-11-21 placeholder probe record'" if match.group(1) == "null" else "null"
        with tempfile.TemporaryDirectory() as tmp:
            copy = os.path.join(tmp, "runner-copy.mjs")
            with open(copy, "w", encoding="utf-8") as target:
                target.write(RECORD_RE.sub(
                    f"const CLAUDE_EXEC_FORMULA_RECORD = {value};", text, count=1))
            proc = run_print_argv(self.node, copy, tmp, [*BASE, "--role", "execute"])
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(NOTE in proc.stderr, value == "null")


if __name__ == "__main__":
    unittest.main()
