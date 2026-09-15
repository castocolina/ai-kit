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
import unittest

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


if __name__ == "__main__":
    unittest.main()
