"""The branches.md write steps run with the real fold.py on a fixture repo."""

import pathlib
import subprocess
import sys

_REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "skills" / "ai-kit-commit-fold" / "scripts"))
sys.path.insert(0, str(_REPO / "tools"))
sys.path.insert(0, str(_REPO))

from tests import fold_fixtures as f
from tests.test_flow_contract import _FlowCase


class TestBranchesWriteSteps(_FlowCase):
    """An amendment of the first unit, made from the third, reaches the whole stack."""

    def _phase(self, number, slug):
        spec = f".planning/phases/{number}-{slug}/{number}-SPEC.md"
        context = f".planning/phases/{number}-{slug}/{number}-CONTEXT.md"
        (self.repo / spec).parent.mkdir(parents=True, exist_ok=True)
        (self.repo / spec).write_text("R1 original\n", encoding="utf-8")
        for command in (("start", "--phase", number), ("guard", "--phase", number)):
            code, text = self.fold(*command)
            self.assertEqual(code, 0, text)
        self._branch_check(number)
        self.commit({spec: b"R1 original\n", context: b"context\n"},
                    f"docs({number}): spec and context")

    def _show(self):
        code, text = self.fold("show", "--all")
        self.assertEqual(code, 0, text)
        return [line for line in text.splitlines() if line]

    def _unit(self, number):
        padded = number.zfill(2)
        for line in self._show():
            if line.split()[1] == f"phase-{padded}":
                return line.split()
        self.fail(f"no unit for phase {number}")
        return []

    def _branch_check(self, number):
        current = f.run_git(self.repo, self.env, "branch", "--show-current").strip()
        branch = self._unit(number)[3]
        self.assertEqual(current, branch, f"branch check for phase {number}")

    def _docs(self, number):
        parts = self._unit(number)
        branch = parts[3]
        padded = number.zfill(2)
        listing = f.run_git(self.repo, self.env, "ls-tree", "--name-only",
                            f"refs/heads/{branch}", ".planning/phases/").splitlines()
        found = [line for line in listing if line.rsplit("/", 1)[-1].startswith(f"{padded}-")]
        self.assertEqual(len(found), 1, found)
        directory = found[0]

        def present(name):
            code = subprocess.run(
                ["git", "-C", str(self.repo), "cat-file", "-e",
                 f"refs/heads/{branch}:{directory}/{name}"],
                capture_output=True, env=self.env, check=False).returncode
            return code == 0

        spec = present(f"{padded}-SPEC.md")
        context = present(f"{padded}-CONTEXT.md") or present("CONTEXT.md")
        if spec and context:
            return branch
        if spec:
            return f"split (SPEC on {branch}, CONTEXT none)"
        if context:
            return f"split (SPEC none, CONTEXT on {branch})"
        return "none"

    def _where_am_i(self, phases):
        current = f.run_git(self.repo, self.env, "branch", "--show-current").strip() or "(detached)"
        lines = [f"current: {current}", "stack:", *self._show()]
        for number in phases:
            lines.append(f"phase {number} unit phase-{number.zfill(2)} docs {self._docs(number)}")
        return lines

    def _report(self, phases):
        where = self._where_am_i(phases)
        return [f"checkout: {where[0].removeprefix('current: ')}", "stack:", *self._show(),
                *[f"docs {number}: {self._docs(number)}" for number in phases],
                "goal file: none", "unit flow off: none"]

    def setUp(self):
        super().setUp()
        self.grant()
        self.commit({".planning/config.json":
                     b'{"git": {"branching_strategy": "phase", '
                     b'"phase_branch_template": "gsd/phase-{phase}-{slug}"}}\n'},
                    "chore: phase branching")
        f.run_git(self.repo, self.env, "push", "-q", "origin", "main")
        self._phase("21", "alpha")
        self._phase("22", "beta")
        self._phase("23", "gamma")

    def _amend(self):
        code, text = self.fold("start", "--phase", "21")
        self.assertEqual(code, 0, text)
        code, text = self.fold("guard", "--phase", "21")
        self.assertEqual(code, 0, text)
        self._branch_check("21")
        return self.commit({".planning/phases/21-alpha/21-SPEC.md": b"R1 original\nR1 amended\n"},
                           "docs(21): amend R1")

    def test_amendment_from_the_third_lands_on_the_first_and_reaches_all_three(self):
        remote = f.run_git(self.bare, self.env, "for-each-ref")
        amend = self._amend()
        code, text = self.fold("restack")
        self.assertEqual(code, 0, text)
        self.assertFalse(any(line.startswith("conflict") for line in text.splitlines()), text)
        self.assertEqual(f.run_git(self.bare, self.env, "for-each-ref"), remote)  # restack: no push
        # Going back up from the amended unit: its tree has no phase-23 directory, so start
        # refuses bad_checkpoint (branches.md); create only that directory and re-run start.
        code, text = self.fold("start", "--phase", "23")
        self.assertEqual(code, 2, text)
        self.assertIn("refused: bad_checkpoint: phase dir not found for phase 23", text)
        (self.repo / ".planning" / "phases" / "23-gamma").mkdir(parents=True, exist_ok=True)
        # The return start runs with the push go-ahead and publishes nothing: the units above
        # were never pushed, and a restack never makes a unit's first push.
        code, text = self.fold("start", "--phase", "23")
        self.assertEqual(code, 0, text)
        self.assertNotIn("caught up", text)
        self.assertEqual(f.run_git(self.bare, self.env, "for-each-ref"), remote)
        self.assertEqual([c for c in self.gh_calls() if c["argv"][:2] == ["pr", "create"]], [])
        code, text = self.fold("guard", "--phase", "23")
        self.assertEqual(code, 0, text)
        self._branch_check("23")
        self.assertEqual(self.ref_sha("refs/heads/gsd/phase-21-alpha"), amend)
        for branch in ("gsd/phase-21-alpha", "gsd/phase-22-beta", "gsd/phase-23-gamma"):
            code = subprocess.run(
                ["git", "-C", str(self.repo), "merge-base", "--is-ancestor", amend, branch],
                capture_output=True, env=self.env, check=False).returncode
            self.assertEqual(code, 0, branch)
            shown = f.run_git(self.repo, self.env, "show",
                              f"{branch}:.planning/phases/21-alpha/21-SPEC.md")
            self.assertIn("R1 amended", shown)
        self.assertEqual(
            self._where_am_i(["21", "22", "23"]),
            ["current: gsd/phase-23-gamma", "stack:", *self._show(),
             "phase 21 unit phase-21 docs gsd/phase-21-alpha",
             "phase 22 unit phase-22 docs gsd/phase-22-beta",
             "phase 23 unit phase-23 docs gsd/phase-23-gamma"])
        self.assertEqual([line.split()[1] for line in self._show()],
                         ["phase-21", "phase-22", "phase-23"])
        code, text = self.fold("start", "--phase", "21")
        self.assertEqual(code, 0, text)
        code, text = self.fold("guard", "--phase", "21")
        self.assertEqual(code, 0, text)
        self._branch_check("21")
        report = self._report(["21", "22", "23"])
        self.assertEqual(
            report,
            ["checkout: gsd/phase-21-alpha", "stack:", *self._show(),
             "docs 21: gsd/phase-21-alpha", "docs 22: gsd/phase-22-beta",
             "docs 23: gsd/phase-23-gamma", "goal file: none", "unit flow off: none"])

    def test_spec_only_phase_is_docs_split(self):
        code, text = self.fold("start", "--phase", "22")
        self.assertEqual(code, 0, text)
        code, text = self.fold("guard", "--phase", "22")
        self.assertEqual(code, 0, text)
        self._branch_check("22")
        f.run_git(self.repo, self.env, "rm", "-q", ".planning/phases/22-beta/22-CONTEXT.md")
        f.run_git(self.repo, self.env, "commit", "-q", "-m", "docs(22): drop context")
        code, text = self.fold("restack")
        self.assertEqual(code, 0, text)
        self.assertIn("phase 22 unit phase-22 docs split (SPEC on gsd/phase-22-beta, CONTEXT none)",
                      self._where_am_i(["22"]))

    def test_without_the_restack_the_amendment_does_not_reach_the_top(self):
        amend = self._amend()
        code = subprocess.run(
            ["git", "-C", str(self.repo), "merge-base", "--is-ancestor", amend,
             "gsd/phase-23-gamma"],
            capture_output=True, env=self.env, check=False).returncode
        self.assertEqual(code, 1)
