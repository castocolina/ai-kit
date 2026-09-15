"""Tests for `ai-kit-project-rules-all` (REQ-rules-all, Phase 15 plan 01).

Task 1's tracer contract: `TestTracer` exercises the whole dispatch/
aggregate pipeline against this repo's own 6 real, already-shipped sibling
checkers (Phases 9-14, all Complete per `.planning/ROADMAP.md`'s Progress
table) -- a live integration test, not a mock. These three cases were
written before `ai_kit_project_rules_all` existed and confirmed to fail for
the right reason (`ImportError`), then implemented against until they
passed. Task 2 adds `TestFailureIsolation` (fixture scripts exercising
D-02/D-05's degradation paths). Task 3 adds `TestAggregate` (SC4's pure-
function stub suite, 6 hand-built fixture dicts, zero subprocess calls) and
`TestCLI` (D-04's check==remediate proof plus the entry script's usage/
unknown-subcommand branches).
"""

from __future__ import annotations

import json
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

from ai_kit_project_rules_all import aggregate, dispatch

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ENTRYPOINT = [
    sys.executable,
    os.path.join(_REPO, "skills", "ai-kit-project-rules-all", "ai-kit-project-rules-all.py"),
]


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


class TestTracer(unittest.TestCase):
    """Task 1's `<behavior>` cases, dogfooding the real 6 sibling checkers."""

    def test_dispatch_all_returns_all_six_real_domains(self):
        results = dispatch.dispatch_all(repo_root=_REPO)
        self.assertEqual(set(results.keys()), set(dispatch.DOMAIN_ORDER))
        for domain, result in results.items():
            self.assertIn("remediate", result, msg=f"{domain}: {result}")
            self.assertNotEqual(
                result.get("status"), "failed", msg=f"{domain}: {result}"
            )

    def test_aggregate_of_real_dispatch_is_globally_sorted_with_no_failures(self):
        report = aggregate.aggregate(dispatch.dispatch_all(repo_root=_REPO))
        self.assertEqual(set(report.keys()), {"remediate", "blocked", "failed"})
        self.assertEqual(report["failed"], [])
        crits = [entry["criticality"] for entry in report["remediate"]]
        self.assertEqual(crits, sorted(crits))

    def test_entry_script_subprocess_check_against_this_repo(self):
        result = subprocess.run(
            [*_ENTRYPOINT, "check", _REPO],
            capture_output=True,
            text=True,
            timeout=240,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(set(report.keys()), {"remediate", "blocked", "failed"})


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

    def test_unresolvable_entrypoint_isolated_from_other_five_real_domains(self):
        real_resolve = dispatch.resolve_entrypoint

        def _break_cicd_only(skill_name):
            if skill_name == dispatch.SKILL_NAMES["cicd"]:
                return None
            return real_resolve(skill_name)

        with mock.patch.object(dispatch, "resolve_entrypoint", side_effect=_break_cicd_only):
            results = dispatch.dispatch_all(repo_root=_REPO)

        cicd_result = results["cicd"]
        self.assertEqual(cicd_result["status"], "failed")
        self.assertIsNone(cicd_result["returncode"])
        self.assertIn("entrypoint not found", cicd_result["error"].lower())

        other_domains = [d for d in dispatch.DOMAIN_ORDER if d != "cicd"]
        for domain in other_domains:
            self.assertIn("remediate", results[domain], msg=f"{domain}: {results[domain]}")
            self.assertNotEqual(
                results[domain].get("status"), "failed", msg=f"{domain}: {results[domain]}"
            )


if __name__ == "__main__":
    unittest.main()
