"""36 D-08 / SPEC R7: each runner row's exec_formula matches the runner template's own
exec argv (cross-ai.mjs --print-argv, no model call, nothing written); a row named in
RUNNER_AHEAD_OF_MIRROR may have a runner formula the mirror lacks. E2E group: real node.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(_REPO_ROOT, "skills", "ai-kit-spec-review"))

from ai_kit_spec.detection import RUNTIMES, ExecFormula

from tests.cross_ai_selftest import TEMPLATE, _real_node_executable, runner_env

_PROBE_ID = {"pi": "fake/ok", "opencode": "fake/ok"}
# A runner formula the mirror does not list yet is safe (routing stays narrower);
# the reverse is drift.
RUNNER_AHEAD_OF_MIRROR = {"claude": "37-10 gives claude an execute formula; the Python mirror keeps it review-only until plan 37-18 reads the runner's --describe fact"}  # noqa: E501


def print_argv(node: str, tmp: str, args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [node, TEMPLATE, "--print-argv", *args], cwd=tmp, env=runner_env(tmp),
        capture_output=True, text=True, timeout=60, check=False,
    )


def formula_problems(rid: str, row, proc, model: str) -> list[str]:
    if row.exec_formula is None:
        return [f"{rid}: runner row has no exec_formula"]
    head = row.exec_formula.head
    if head is None:
        if (rid in RUNNER_AHEAD_OF_MIRROR and proc.returncode == 0
                and proc.stdout.startswith(f"{rid}\t")):
            return []
        if proc.returncode != 2 or "no exec formula" not in proc.stderr:
            return [f"{rid}: the table says the runner has no exec formula, "
                    f"but the runner exited {proc.returncode}"]
        return []
    fields = proc.stdout.splitlines()[0].split("\t") if proc.stdout else []
    if proc.returncode != 0 or len(fields) != 3 or fields[0] != rid:
        return [f"{rid}: --print-argv exited {proc.returncode}: {proc.stderr.strip()[:200]}"]
    argv = json.loads(fields[2])
    if argv[: len(head)] != list(head):
        return [f"{rid}: exec argv drifted: table head {list(head)}, runner {argv[: len(head)]}"]
    if head[-1] == "--model" and argv[len(head) : len(head) + 1] != [model]:
        return [f"{rid}: the argv item after --model is {argv[len(head) : len(head) + 1]}, "
                f"not {model!r}"]
    return []


class TestExecFormulaDrift(unittest.TestCase):
    def test_every_runner_row_matches_the_runner(self):
        node = _real_node_executable()
        if node is None:
            self.skipTest("no real node executable on PATH: the exec formula drift check "
                          "needs node (the clean-room container has none, like its siblings)")
        checked = []
        problems = []
        with tempfile.TemporaryDirectory() as tmp:
            for rid, row in RUNTIMES.items():
                if not row.runner:
                    continue
                checked.append(rid)
                model = _PROBE_ID.get(rid, "fake-ok")
                proc = print_argv(node, tmp, ["--mode", "exec", "--runtime", rid, "--model", model])
                problems.extend(formula_problems(rid, row, proc, model))
        self.assertEqual([rid for rid, row in RUNTIMES.items() if row.runner], checked)
        self.assertTrue(checked)
        self.assertEqual([], problems)


class TestExecFormulaDriftNonVacuity(unittest.TestCase):
    def test_runner_ahead_of_mirror_is_named(self):
        proc = subprocess.CompletedProcess(
            [], 0, stdout='claude\tMISSING\t["-p","--model","fake-ok"]\n', stderr="")
        self.assertEqual([], formula_problems("claude", RUNTIMES["claude"], proc, "fake-ok"))
        row = RUNTIMES["cursor"]._replace(exec_formula=ExecFormula(None, "test"))
        proc = subprocess.CompletedProcess(
            [], 0, stdout='cursor\tMISSING\t["-p","--model","fake-ok"]\n', stderr="")
        self.assertTrue(formula_problems("cursor", row, proc, "fake-ok")[0].startswith(
            "cursor: the table says the runner has no exec formula"))

    def test_doctored_head_is_drift(self):
        row = RUNTIMES["cursor"]._replace(exec_formula=ExecFormula(("-p", "--wrong"), "test"))
        proc = subprocess.CompletedProcess(
            [], 0, stdout='cursor\tMISSING\t["-p","--output-format","json","--model","fake-ok"]\n',
            stderr="")
        problems = formula_problems("cursor", row, proc, "fake-ok")
        self.assertEqual(len(problems), 1)
        self.assertTrue(problems[0].startswith("cursor: exec argv drifted"))

    def test_matching_head_passes(self):
        proc = subprocess.CompletedProcess(
            [], 0, stdout='cursor\tMISSING\t["-p","--output-format","json","--model","fake-ok"]\n',
            stderr="")
        self.assertEqual([], formula_problems("cursor", RUNTIMES["cursor"], proc, "fake-ok"))
        problems = formula_problems("cursor", RUNTIMES["cursor"], proc, "fake-other")
        self.assertEqual(len(problems), 1)
        self.assertTrue(problems[0].startswith("cursor: the argv item after --model"))

    def test_null_head_needs_the_runner_refusal(self):
        proc = subprocess.CompletedProcess([], 0, stdout="", stderr="")
        problems = formula_problems("claude", RUNTIMES["claude"], proc, "fake-ok")
        self.assertEqual(len(problems), 1)
        self.assertTrue(problems[0].startswith(
            "claude: the table says the runner has no exec formula"))
        proc = subprocess.CompletedProcess(
            [], 2, stdout="", stderr="cross-ai: x (no exec formula)\n")
        self.assertEqual([], formula_problems("claude", RUNTIMES["claude"], proc, "fake-ok"))

    def test_runner_row_without_formula_is_reported(self):
        row = RUNTIMES["pi"]._replace(exec_formula=None)
        proc = subprocess.CompletedProcess([], 0, stdout="", stderr="")
        self.assertEqual(["pi: runner row has no exec_formula"],
                         formula_problems("pi", row, proc, "fake/ok"))


if __name__ == "__main__":
    unittest.main()
