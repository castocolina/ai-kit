"""Tests for `ai-kit-project-rules-all` (REQ-rules-all, Phase 15 plan 01).

Unit tier: fixture-driven `TestFailureIsolation` (D-02/D-05 degradation paths via small
scripts), `TestAggregate` (SC4 pure-function stubs, zero subprocess calls) and `TestCLI`
(D-04 check==remediate with `dispatch_all` mocked, plus the entry script's usage branches).
The real dispatch against this repo's six checkers lives in
`tests/test_ai_kit_project_rules_all_e2e.py` (e2e tier, 26-08: the agents domain runs the
project-local gsd-core through node).
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "skills", "ai-kit-project-rules-all"),
)

from ai_kit_project_rules_all import aggregate, cli, dispatch

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ENTRYPOINT = [
    sys.executable,
    os.path.join(_REPO, "skills", "ai-kit-project-rules-all", "ai-kit-project-rules-all.py"),
]


def _ok(remediate: list[dict] | None = None, blocked: list[dict] | None = None) -> dict:
    """A real sibling `remediate` payload shape: `{"remediate": [...],
    "blocked": [...]}`."""
    return {"remediate": remediate or [], "blocked": blocked or []}


def _failed(domain: str, error: str = "boom", returncode: int | None = 1) -> dict:
    """A D-05 failure-entry marker -- no `"remediate"` key."""
    return {"domain": domain, "status": "failed", "error": error, "returncode": returncode}


def _entry(kind: str, id_: str, criticality: int) -> dict:
    return {"kind": kind, "id": id_, "criticality": criticality}


def _blocked_entry(kind: str, id_: str, criticality: int) -> dict:
    return {"kind": kind, "id": id_, "criticality": criticality, "stacks": []}


def _write_fixture_script(content: str) -> str:
    """A standalone `.py` file under a fresh temp dir, subprocess-invoked
    by `run_domain` exactly like a real sibling entry script -- the
    `resolve_entrypoint`/`SKILL_NAMES` machinery is left untouched; only
    `dispatch.resolve_entrypoint`'s return value is monkeypatched to point
    at this fixture, so `run_domain` still exercises the real subprocess
    path (`subprocess.run` is never mocked)."""
    tmpdir = tempfile.mkdtemp()
    path = os.path.join(tmpdir, "fixture.py")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)
    return path


class TestFailureIsolation(unittest.TestCase):
    """Task 2's `<behavior>` cases -- D-02/D-05's degradation paths, each
    driven through the real subprocess path against a small fixture
    script rather than a mocked `subprocess` call."""

    def test_nonzero_exit_degrades_to_d05_shape(self):
        fixture = _write_fixture_script("import sys\nsys.exit(1)\n")
        with mock.patch.object(dispatch, "resolve_entrypoint", return_value=fixture):
            result = dispatch.run_domain("cicd", ".")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["domain"], "cicd")
        self.assertEqual(result["returncode"], 1)
        self.assertTrue(result["error"])

    def test_malformed_json_stdout_degrades_to_d05_shape(self):
        fixture = _write_fixture_script("print('not json')\n")
        with mock.patch.object(dispatch, "resolve_entrypoint", return_value=fixture):
            result = dispatch.run_domain("cicd", ".")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["domain"], "cicd")
        self.assertEqual(result["returncode"], 0)
        self.assertIn("json", result["error"].lower())

    def test_timeout_degrades_to_d05_shape(self):
        fixture = _write_fixture_script("import time\ntime.sleep(5)\nprint('{}')\n")
        with (
            mock.patch.object(dispatch, "resolve_entrypoint", return_value=fixture),
            mock.patch.object(dispatch, "DOMAIN_TIMEOUT_SECONDS", 1),
        ):
            result = dispatch.run_domain("cicd", ".")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["domain"], "cicd")
        self.assertIsNone(result["returncode"])
        self.assertIn("timed out", result["error"].lower())


class TestAggregate(unittest.TestCase):
    """Task 3's `<behavior>` cases (SC4): `aggregate.aggregate()` called
    directly with 6 hand-built fixture dicts -- never `subprocess`, never
    `dispatch_all`."""

    def test_cross_domain_ordering_is_one_global_sort(self):
        domains = {
            "agents": _ok(),
            "makefile": _ok(
                remediate=[_entry("makefile", "mk-a", 1), _entry("makefile", "mk-b", 4)]
            ),
            "precommit": _ok(remediate=[_entry("precommit", "pc-a", 2)]),
            "arch": _ok(remediate=[_entry("arch", "arch-a", 3)]),
            "docker": _ok(),
            "cicd": _ok(),
        }
        report = aggregate.aggregate(domains)
        crits = [entry["criticality"] for entry in report["remediate"]]
        self.assertEqual(crits, [1, 2, 3, 4])

    def test_workflow_kind_alone_gets_hand_off_tag(self):
        domains = {
            "agents": _ok(remediate=[_entry("workflow", "R01", 1)]),
            "makefile": _ok(remediate=[_entry("makefile", "mk-a", 2)]),
            "precommit": _ok(),
            "arch": _ok(),
            "docker": _ok(),
            "cicd": _ok(),
        }
        report = aggregate.aggregate(domains)
        workflow_entries = [e for e in report["remediate"] if e["kind"] == "workflow"]
        other_entries = [e for e in report["remediate"] if e["kind"] != "workflow"]
        self.assertEqual(len(workflow_entries), 1)
        self.assertEqual(workflow_entries[0]["hand_off"], "agent-md-refactor")
        self.assertTrue(other_entries)
        for entry in other_entries:
            self.assertNotIn("hand_off", entry)

    def test_failed_domain_isolated_from_remediate_and_blocked(self):
        domains = {
            "agents": _ok(remediate=[_entry("workflow", "R01", 1)]),
            "makefile": _ok(remediate=[_entry("makefile", "mk-a", 2)]),
            "precommit": _ok(remediate=[_entry("precommit", "pc-a", 3)]),
            "arch": _failed("arch"),
            "docker": _ok(remediate=[_entry("docker", "dk-a", 4)]),
            "cicd": _ok(remediate=[_entry("cicd", "ci-a", 5)]),
        }
        report = aggregate.aggregate(domains)
        self.assertEqual(len(report["failed"]), 1)
        self.assertEqual(report["failed"][0]["domain"], "arch")
        self.assertEqual(report["failed"][0]["status"], "failed")
        self.assertEqual(len(report["remediate"]), 5)
        remediate_kinds = {entry["kind"] for entry in report["remediate"]}
        self.assertNotIn("arch", remediate_kinds)

    def test_blocked_list_combined_and_sorted(self):
        domains = {
            "agents": _ok(),
            "makefile": _ok(blocked=[_blocked_entry("makefile", "mk-b", 5)]),
            "precommit": _ok(),
            "arch": _ok(blocked=[_blocked_entry("arch", "arch-b", 2)]),
            "docker": _ok(),
            "cicd": _ok(),
        }
        report = aggregate.aggregate(domains)
        crits = [entry["criticality"] for entry in report["blocked"]]
        self.assertEqual(crits, [2, 5])


class TestCLI(unittest.TestCase):
    """Task 3's `<behavior>` cases: D-04's check==remediate proof, and the
    entry script's usage/unknown-subcommand branches."""

    def test_check_and_remediate_are_byte_identical_d04(self):
        fixed_domains = {
            "agents": _ok(),
            "makefile": _ok(
                remediate=[_entry("makefile", "mk-a", 1), _entry("makefile", "mk-b", 4)]
            ),
            "precommit": _ok(remediate=[_entry("precommit", "pc-a", 2)]),
            "arch": _ok(remediate=[_entry("arch", "arch-a", 3)]),
            "docker": _ok(),
            "cicd": _ok(),
        }
        with mock.patch.object(dispatch, "dispatch_all", return_value=fixed_domains):
            check_result = cli.check(".")
            remediate_result = cli.remediate(".")
        self.assertEqual(check_result, remediate_result)

    def test_entry_script_unknown_subcommand_and_no_args(self):
        unknown = subprocess.run(
            [*_ENTRYPOINT, "bogus"], capture_output=True, text=True, timeout=30
        )
        self.assertEqual(unknown.returncode, 2)
        self.assertIn("unknown subcommand", unknown.stderr)

        no_args = subprocess.run(_ENTRYPOINT, capture_output=True, text=True, timeout=30)
        self.assertEqual(no_args.returncode, 0)
        self.assertIn("check|remediate", no_args.stdout)


if __name__ == "__main__":
    unittest.main()
